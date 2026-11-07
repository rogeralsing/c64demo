# Tower Power F1: the patterned cube-like object

The native F1 capture matches the supplied blue/purple/cyan object under the Camelot logo. Its active model has **24 body vertices plus 15 coplanar pattern points**, rather than merely eight cube corners. Large cyan triangles are explicit color stencils on its faces. F1 also contains a genuine eight-vertex cube in an earlier phase; inspecting that inactive table alone initially understated the captured object's complexity.

The input is `side2/f1.-100%-100%-10` from the validated 100% release. Its 8,077 packed bytes reconstruct 12,241 output bytes; the flat output-image SHA-256 is `e070009e62ea6e5d401220379a746b0b309c79ca5ec4bc3446b3907c6da8e034`. The entry/IRQ vectors are `$2194` / `$3C29`. The native screenshot is `build/research/tower-power/f1-live-01/f1-running.png`; its running RAM is `ram-f1-running.bin`, SHA-256 `8e11f3f030ebb598a28f3206e135cc484e1e1a013cb7d0d0e237acb2c30851e3`. Depacking provenance and limits are in [the depacker note](tower-power-depacker.md); native observations belong to [the binary ledger](tower-power-binary.md).

The original native chain reached `$2194`, but execution resumed before an entry RAM dump was saved. The later capture has 11,759 of the 12,241 established payload bytes unchanged and 482 runtime differences, recorded completely in `f1-live-01/running-comparison.json`. This is a running-state comparison, not a claim of a full entry-time payload match.

## Original route from RUN 1

The boot's BASIC line 1 is `SYS 9731`, entry `$2603`. It selects `C1.*`. The following main-part chain is established by literal filename copies into `$C000` followed by calls to the original loader at `$C010`:

| Executing part / entry | Literal request address | Loader call | Next request |
|---|---|---|---|
| C1 / `$5034` | `$50D0` | `$5043` | `M2.*`, music |
| C1 / `$5034` | `$50D4` | `$508C` | `C7.*` |
| C7 / `$8740` | `$8B77` | `$8760` | `C2.*` |
| C2 / `$5836` | `$669D` | `$59BC` | `D1.*` |
| D1 / `$882A` | `$95BF` | `$89FE` | `E1.*` |
| E1 / `$5831` | `$654B` | `$5961` | `F1.*` |

The handoffs use the returned `$C2F0` entry vector, with IRQ handling transferred by each original part. They include original display waits and effects; this is a main handoff route, not a claim that no auxiliary data is loaded. A native breakpoint at `$2194` can identify completion of the route. No loader or renderer patch is needed to select the documented boot entry.

## The captured model: convex body with face stencils

The saved state has phase counter `$2551 = $D3` (211), after the transition at `$25D9`. That transition copies three **39-byte** coordinate arrays starting at `$29D7` and rewrites the active topology operands. All 39 coordinate triples in the native capture exactly match those source arrays. `$3031 = 24` is a stale count from the earlier morph machinery; this phase's transform terminates on the zero Z sentinel instead. It processes 39 points plus an extra `$FF,$FF,$FF` record.

Following the **active operands** establishes the current layout:

| Role | Active tables | Established content |
|---|---|---|
| Body coordinates | `$FEC0`, `$FE80`, `$FF00` | First 24 vertices form the body |
| Pattern coordinates | Same arrays, IDs 24..38 | Fifteen extra points on body face planes |
| Face orientation triples | `$2AE4`, `$2AFF`, `$2B19` | 26 faces |
| Edge endpoints | `$2A4F`, `$2A9A` | 48 body edges plus 26 pattern edges |
| Face/edge contributions | `$2B33` | Variable-length records with color changes |

The body has **18 quad faces and eight triangular faces**. Its 24 vertices, 48 edges, and 26 faces give Euler characteristic 2. Every body face is a convex supporting plane; every body edge belongs to two faces. This is a more elaborate cube-like convex shape, with real corner triangles and additional colored subdivisions on its six large end faces.

`$99` inside an incidence record means “change the XOR contribution,” rather than an edge ID. The following byte becomes the mask for subsequent edges in that same face. Every pattern edge lies on its owner's plane, and each face's colored edge graph has zero XOR at every vertex: its two bitplanes close correctly.

For a concrete large triangle, face 0 is the plane `X = −64`, with outer corners `0,4,6,2`. Added point 24 is `(-64,-40,0)`, on one outer edge. Pattern edges `2–24` and `6–24` divide out triangle `(2,6,24)`. Its record uses `$55` on the ordinary boundary, `$AA` on those two internal cuts, and `$FF` on the triangle's outer edge. With an `$FF` prefix seed, the main face becomes code `10`; crossing a cut changes it to `00`. At the native cube raster, these are blue from `$D023 = 6` and cyan from `$D021 = 3`. The light-blue register is `$D022 = 14`.

The large cyan triangle is therefore an explicit **coplanar color stencil**. It does not require UV texture mapping or drawing hidden back faces through the object. Replaying the original `$2898` orientation helper on all 26 captured projected faces selects twelve and rejects fourteen; all decisions match the corresponding nonzero projected winding. The native `CMP #0` / conditional branch at `$27D5` is intact. This establishes ordinary face culling for this captured pose, not a GLENZ-style mixture of front and back surfaces.

## The logo and object use different raster modes

A register read while the logo is displayed can show bitmap mode in VIC bank 3, with screen `$C800` and bitmap `$E000`. That is not the cube's mode. The original IRQ at `$3367`, scheduled for raster 114, writes `$D011 = $13`, `$DD00 = $97`, and `$D018 = $13`: bank 0, character screen `$0400`, charset `$0800`. Multicolor remains enabled. The cube canvas starts at character row 8, immediately below that switch.

The native raster-128 capture confirms character mode with `$D011 = $13`, `$D016 = $D0`, `$D018 = $13`, and bank-select low bits 3. Its saved RAM is `f1-live-01/ram-cube-raster128.bin`; the register observations are in that session's monitor log. The bitmap's static color matrix belongs to the logo, so it does not explain the cube's large triangles.

## Earlier phase: a genuine eight-vertex cube

`$2534..$254B` copies three arrays at `$296C`, `$2975`, and `$297E` into the active coordinates at `$FEC0`, `$FE80`, and `$FF00`. The eight points are every combination of byte values 79 and 177. Around bias 128, these are precisely `(±49, ±49, ±49)`.

The edge consumers at `$2826..$285D` use endpoint lists `$2987` and `$2994`:

```text
0–1, 1–3, 3–2, 2–0
4–5, 5–7, 7–6, 6–4
0–4, 1–5, 3–7, 2–6
```

The six records at `$29B3` each contain four incident edge IDs and one XOR contribution. Each record's four corners lie on one cube plane; each corner has two edges within the face; every cube edge belongs to two faces. There are **no face-diagonal edges** in this graph.

`$2792` transforms the points, then `$279C..$27D0` selects three projected corners per face from `$29A0`, `$29A7`, and `$29AD` and calls the orientation routine `$2898`. Those six triples are subsets of the six quads. They serve to decide orientation; they are not a twelve-triangle surface mesh. Face contributions accumulate into the twelve edge masks before line drawing and prefix filling.

As in N2, the copied coordinate lists include an extra `$FF,$FF,$FF` record followed by a zero Z sentinel in the active buffers. The transform processes nine records; the cube's edge list uses only IDs 0..7.

## Earlier cube phase: repeating packed masks

At the start of the cube phase, opposite faces use contributions `$FF`, `$AA`, or `$55`. At phase counter `$60` (96), `$2556..$2563` patches four of the six face contribution bytes:

| Face pair | Earlier contribution | Patched contribution | Filled byte from FF seed |
|---|---|---|---|
| Faces 0 / 1 | `$FF` | `$9D` | `$62` |
| Faces 2 / 4 | `$AA` | `$67` | `$98` |
| Faces 3 / 5 | `$55` | `$55` | `$AA` |

The packed two-bit pixels of `$62` are `01,10,00,10`; `$98` gives `10,01,10,00`; `$AA` is uniformly `10`. Instead of one repeated two-bit contribution, a face can therefore produce a repeating four-logical-pixel pattern. The line mask setup at `$3877` ANDs these contributions with the packed lanes for the current screen position. The generated prefix fill starts with `$FF`, just as [N2's palette arrangement](tower-power-n2-palette.md) does.

This is a screen-X-anchored packed-color pattern. No UV coordinates or extra face triangles are needed for this earlier mechanism. The native screenshot instead shows the subsequent 39-point phase described above; the old `$29A0` six-face tables and these patched masks remain in RAM after their consumers have switched elsewhere.

## Perspective reuses the cosine product pages

F1's `$3438` generates the same 16 KB product table at `$8000..$BFFF` as [N2](tower-power-n2-math.md), with the same 64 half-step quarter-cosine seeds. The generated bytes have the identical SHA-256 `5e7ed80eace62cc50cc0a965ca76ee8c987c2a38e17b7636290aff0195c48c31`.

Unlike N2, F1 adds a perspective stage. `$3484` patches the three plane rotations; `$35C0..$360E` calculates rotated components. The intermediate depth byte indexes a table through the operand at `$35E2/$35E3`, initially `$4800`. Every one of the 1,024 literal values at `$4800..$4BFF` matches:

```text
factor[i] = nearest integer to 76500 / (300+i), with exact half cases downward
          = ceil(76500 / (300+i) − 1/2)
```

The result then indexes `$4F00`. Every byte in that 256-entry table matches:

```text
page[value] = 128 + min(63, floor(acos(value/255) * 128/pi))
```

This maps a requested magnitude back to the closest selected quarter-wave page under that table's rule. F1 can consequently reuse its cosine-magnitude product pages to multiply screen coordinates by a depth-dependent factor. It does not need a separate generic multiply routine for projection.

`$35E5..$35EB` patches that product-page high byte into the two final projection lookups. `$3614..$362C` adds the projected products around 64, stores vertical position, and halves horizontal position for multicolor pixels. The depth affects scale, so this is perspective rather than N2's fixed orthographic shifts. The program also advances the `$4800` table operand, changing the scale curve over time. These are exact matching descriptions of the literal tables, not recovered author source expressions.

## Stored morph targets are not stored display frames

The earlier phase uses six model pointers at `$3032/$3038`:

| Model index / address | Stored data | Points |
|---|---|---|
| 0 / `$3051` | Edge topology, contributions, coordinates | 12 |
| 1 / `$309E` | Coordinate morph target | 12 |
| 2 / `$30C3` | Edge topology, contributions, coordinates | 24 |
| 3 / `$3158` | Coordinate morph target | 24 |
| 4 / `$31A1` | Coordinate morph target | 24 |
| 5 / `$31EA` | Coordinate morph target | 24 |

`$2FAE` loads topology and coordinates; `$2F16` calculates interpolation steps toward coordinate-only targets; `$3D8B` applies those steps. The command stream at `$3044` selects these records with waits. The 24-point topology subdivides the earlier loops with additional points; those records should not be mislabeled as the later eight-vertex cube.

F1 therefore mixes stored shape targets and control data with runtime interpolation, rotation, depth scaling, orientation checks, line drawing, and prefix fill. Lookup tables and model key poses are real precomputation, but their presence does not imply a bank of complete rendered animation frames.

## Reproducible offline proof

Run the [inventory/math harness](../../research/tower-power/f1_inventory.py) with the existing isolated environment:

```sh
build/research/tower-power/cpu-venv/bin/python research/tower-power/f1_inventory.py
```

It checks the cube graph and all six face records against the actual coordinate/consumer tables, parses all six model records, and records the original main load requests. It then executes the original product generator, cube-copy code, mask-patch code, and transform in flat py65 RAM.

The original transform matches an independent carry-aware arithmetic reference for **5,105 angle/scale combinations**: 1,021 distinct angle triples at five table offsets (`0,27,256,512,768`). These cover 45,945 processed records and 3,471,281 original instructions including setup. Both perspective tables and all 16,384 product cells are checked in full. The receipt is `build/research/tower-power/static/f1/inventory.json`.

The separate [native-state harness](../../research/tower-power/f1_native.py) follows the saved active operands, checks the 39 literal coordinate triples, proves body convexity/incidence and coplanar pattern closure, and replays the captured transform and orientation helper:

```sh
build/research/tower-power/cpu-venv/bin/python research/tower-power/f1_native.py
```

At captured angles `(243,212,137)` and perspective-table offset 162, all forty processed coordinate records match both the original CPU routine and the independent arithmetic reference exactly. That replay takes 2,377 original instructions; checking all 26 orientation calls takes another 1,777. The receipt is `build/research/tower-power/static/f1/native-geometry.json`.

These instruction counts describe isolated validation, not a native frame budget. The native screenshot identifies the effect; the offline checks explain its geometry, projection and patterned faces. There is still no complete independent per-pixel rendering oracle or all-angle culling proof for F1, and no claim that the interrupted native capture preserved an untouched entry state.
