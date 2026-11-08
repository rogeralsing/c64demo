# Camera geometry uses the stored X/Y and geometric depth directly

For this exact fixed-origin PRG and its three captured poses, use:

```text
E = (0,0,0)
P[i] = (signed8(rxbuf[i]), signed8(rybuf[i]), signed16(sz[i] | szhi[i]<<8))
N = (P1−P0) × (P2−P0)
eye-facing side: N · (E−P0) > 0
```

All three components use the **same integer geometric/world unit**. Positive Y is up; positive depth goes away from the eye. The stored depth already includes the object's **Z=128** translation. Do not add 128 again, negate Y into screen coordinates, or move the eye to Z=−190.

The passive producer is `research/3dvibe64-camera/source_units.py`. It binds the unchanged source/PRG/symbols and authored scene, verifies **81 coordinate products and all 18 captured camera vertices**, and checks **1,536 linked table bytes** independently. This establishes a bounded source/units contract; it is not an independent ideal projection, a new renderer, or a full-rotation visibility proof.

## Runtime units and translation

The geometry coordinate tables are literal **−28,0,28**, matching the authored vertex coordinates. Matrix coefficients use **64 for 1**. `mul_s6` forms an exact signed magnitude product, shifts its magnitude down six bits and restores its sign: negative results truncate toward zero. Each coordinate term is quantized separately before the rotation loop sums the byte terms. Therefore, the runtime point cloud need not be an exact rigid rotation of the ideal input mesh.

The product arrays occupy **`$8048–$8062`**, 27 bytes: three coordinates for each of the nine axis/matrix terms. `rotate_project_vertices=$1368` combines them into signed-byte X/Y/local-Z. The authored axis vertices have only one nonzero source coordinate, and the observed terms remain in range; no byte-coordinate overflow occurs in these samples.

Object position is stored as **16.8 fixed point** for Z. Linked bytes `object_pos_z_lo/hi/ext = $00,$80,$00` mean **128 world units**, not −128. `set_active_object=$0A61` copies the fractional byte to `$81`, integer low byte to `$7E` and integer high byte to `$80`. The rotation loop sign-extends local Z, adds this integer object depth, then the motion-depth words, and stores `sz/szhi`. The object fractional byte can cause a final upward integer rounding when it is ≥128; no Z fractional bits survive in these two arrays.

For this build:

- `SCENE_OBJECT_X_ACTIVE=0` and `SCENE_OBJECT_Y_ACTIVE=0`; current object X/Y are zero.
- `SCENE_OBJECT_SCALE_ACTIVE=0`, with scale 1 / Q6 value 64.
- `CAMERA_HAS_POS=0`, `CAMERA_HAS_ROT=0`, `CAMERA_MOVABLE=0`; the scene camera is at the origin with zero rotation.
- All motion-depth start/step constants and captured motion bytes are zero.
- Object Z fraction is zero; depth is exactly **quantized local Z + 128** in every checked vertex.

Thus the stored tuple above is directly the quantized camera-space vertex for these captures. Other profiles can enable saturating X/Y translation, camera transforms, motion depth or fractional rounding; inspect their actual flags before reusing this simplification. The unsigned high-byte carry saturation and signed overflow paths are not exercised here.

## +190 is an address origin, not an eye displacement

`camera_depth_geometric_lo/hi` alias **`sz/szhi`**. Linked `load_projection_table_index=$1335` loads those arrays and jumps to `$1305`, which adds **190** to select a physical table index. Crucially, the pinned host table generator subtracts the same 190 before calculating the projection divisor:

```text
near geometric divisor = max(8, physical_index − 190)
far geometric divisor  = 256 + 32×slot + 16 − 190
scaleQ6 ≈ round(170×64 / geometric_divisor), with profile clamps
```

The producer reconstructs all **256 `scene_scale_tab` bytes** and **256 `scale_far_tab` bytes** with exact rational nearest/even rounding. Every linked byte matches. The far table at **`$BC35`** begins **120,95,75,61,52**; its geometric midpoint divisors are **82,114,146,178,210**. Its first value is clamped to 120.

For example, captured geometric depth **128** becomes physical index **318**, far slot **1**, scale **95**, approximating midpoint divisor **114**. It is neither a divisor of 318 nor an eye at −190. The 32-index buckets and clamps introduce approximation, so this remains distinct from exact continuous perspective. All 18 captured depths select the far-table range if projection is requested; some first/second vertices were not actually projected, and the receipt keeps their `projdone` flags rather than treating stale screen bytes as geometry.

The producer also independently binds all **256 `projx` and 256 `projy` bytes**: they implement clamped `80+signed_offset` and `50−signed_offset`, respectively. This confirms the Y-up sign without deriving geometry from `sx/sy`.

## Captured geometry and outward winding

| Pose | Six `(X,Y,Z)` camera vertices in geometric ID order |
|---|---|
| First | `(28,0,128), (−28,0,128), (0,28,128), (0,−28,128), (0,0,156), (0,0,100)` |
| Second | `(26,2,120), (−26,−2,136), (0,27,133), (0,−27,123), (8,−5,154), (−8,5,102)` |
| Third | `(23,4,114), (−23,−4,142), (0,26,136), (0,−26,120), (14,−7,149), (−14,7,107)` |

Opposite pairs sum to twice **C=(0,0,128)** in every sample. The authored ordering has **outward** normals for `N=(P1−P0)×(P2−P0)`: `N·(P0−C)>0` for all 24 captured triangles and for all eight original local faces about the local origin. With that winding, positive `N·(E−P0)` places the eye on the outward side. Reversing the winding or reflecting only Y reverses the sign; a screen-Y reflection must not be inserted silently.

In the first pose, face 0 has `N=(784,784,−784)` and eye dot **78,400**, while face 4 has `N=(784,784,784)` and eye dot **−122,304**. In the third pose, face 1's eye dot is **−17,214** and face 7's is **−21,566**. Strict positive-plane-side sets for the captured integer triangles are **0,1,2,3 / 0,1,2,3 / 0,2,3**. These are mathematical results on the captured point clouds, not claims that ideal continuous geometry, finite-precision rasterization and a new culling implementation are all equivalent. The independent classifier/pixel lane tests those separate implications.

The [existing conservative policy](3dvibe64-cull-policy.md) instead uses a preprojection two-dimensional cross on `(rx,−ry)`, accepting a negative tolerance. Its result need not equal this position-dependent plane-side test. The comparison does not change that frozen policy audit.

## Capture the matrix before drawing clobbers it

The existing natural **`$1153`** shade baseline contains a valid prepared matrix and coordinate-product tables before vertex rotation runs. All 81 terms reconstructed from those baseline matrices match the runtime tables; the 27-byte table block then stays identical through each `$08D4` completion. All 18 completed vertices reconstructed from the terms match `rxbuf/rybuf/sz/szhi` exactly.

However, **completed `$08D4` matrix bytes `$56–$5E` differ from the baseline in every sample**. Drawing reuses some of those zero-page cells. Reading a late matrix and using it to reinterpret an earlier rotation would be invalid. The stored camera-space arrays remain usable without that matrix.

For a future natural capture, **`$1441`** is the preferred anchor: linked `$143E` is `JSR $1368`, rotation returns through **`RTS $1420`**, and `$1441` is the next `JSR $145C` for face collection. At this boundary, all six X/Y/depth vertices are ready, the matrix is still from preparation, and `projdone` has just been cleared for each vertex. Useful compact reads are `m 802a 8062` and `m 0056 0081`; paired full RAM/VSF remains the stronger capture. No CPU/register writes or synthetic geometry are needed.

## Passive replay and pins

```sh
rtk proxy python3 -B research/3dvibe64-camera/source_units.py --output build/research/3dvibe64-camera/source-analysis/replay-01
```

Use a fresh output directory. The producer starts no SDK, build, CPU, emulator, subprocess or connection. The accepted **`source-analysis/units-proof.json`** is **22,508 bytes**, SHA-256 **`665e9233aafe5cc3e25e82b497549117a04f64f2a14fa5f0c335290970284551`**; directory names do not affect receipt bytes. An initial linked guard used an off-by-one address and failed before output creation; the corrected guard is `$13EB`.

Inputs include the same original PRG SHA **`69b0d86f79106b2bf9654d85bd631bc68c12f4efd708454a0048560b3c1bfdeb`**, emitted assembly/symbols, authored scene, pinned SDK builder SHA **`b03d5d7ce6e9e5af85d47c04950841da96f1f3e6dc7b50f5c26a1f97c5bb7e70`**, accepted profile proof and the closed 29-file case digest **`13bfd23f30bf0b7a2db7a9e8dc4ceb8dc69e77d81c76862fe9b372a1f23ef714`**. All case files are rechecked; wire/snapshot acceptance is reused from the frozen profile.

Exact emitted-source anchors: object selection **2221–2243**; Q6 coordinate terms **4550–4600**; geometric-to-physical table index **4602–4655**; rotation/depth stores **6495–6759**; depth aliases **27677–27678**; extended projection **18229–18305**. The pinned builder's minimum divisor is at line **578**, compensated near/far table generation at **1631–1657**, and origin-only contract comment at **9259–9260**. The receipt contains linked byte guards, table hashes, complete reconstructed inputs and winding arithmetic. No frozen artifact or product code was modified.
