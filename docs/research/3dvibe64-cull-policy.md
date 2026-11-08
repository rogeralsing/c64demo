# Why the conservative policy submits the fifth face

The third captured pose's face 7 has reconstructed signed cross product **−17**. This exact build's conservative area test accepts **cross ≥ −32**, so face 7 is intentionally retained by that policy. It also passes the actual depth and sliver checks. Its measured draw-call subtree costs **90,751 elapsed PAL machine cycles** and emits **45 nonempty spans / 203 logical pixel visits**.

This explains submission under the pinned integer policy; it is not a theorem about physical visibility or a culling-correctness defect. The coordinates are retained runtime inputs. No projection, rotation, CPU execution, renderer modification, build or native session is performed by this audit.

## The active policy, rather than every compiled setting

The source and linked PRG are the unchanged [stock Mode 6 product](3dvibe64-build.md). `load_face_visible` at **`$42A9`** loads each face's original three vertices from **`rxbuf=$8036`** and **`rybuf=$803C`**, negates Y, then calls `face_visible=$9000` at `$42E4`. This happens **before** lazy perspective projection at `$9051`. Consequently, the tolerance is in this rotated-coordinate cross-product scale, not projected pixel area.

For face vertices `(x0,y0),(x1,y1),(x2,y2)`, with `x=rxbuf` and `y=−rybuf`, the source computes:

```text
cross = (x1−x0)×(y2−y0) − (y1−y0)×(x2−x0)
```

The producer mirrors the linked eight-bit signed differences and sixteen-bit subtraction. It independently binds all **512 linked quarter-square bytes** and checks the **48 product operands** used across these three eight-face samples against ordinary integer multiplication. The actual operands remain within the multiplier's guarded eight-bit sum-index range. This is a passive source/data calculation, not a 6502 emulator.

| Setting | Pinned value | Active consequence |
|---|---:|---|
| `FACE_CULL_PREP` | 1 | Prepare rotated X / negated Y for the area test |
| `FORCE_FACE_RENDER` | 0 | Execute the culling test |
| `CONSERVATIVE_FACE_CULL` | 1 | Keep nonnegative cross, including zero; also keep −32..−1 |
| `CONSERVATIVE_CULL_NEG_AREA` | `$20` / 32 | Active negative tolerance |
| `CONSERVATIVE_EDGE_CULL_NEG_AREA` | `$60` / 96 | Clipped-quad alternative is compiled out here |
| `EXPLORER_SCREEN_CLIP_POLY` | 0 | No clipped-quad tolerance branch |
| `STABLE_FACE_CULL_PROFILE` / camera-space support | 0 / 0 | No normal-based fallback |
| `MIN_FACE_AREA` | 10 | Nonconservative threshold is bypassed |
| Direct XYQ2 profile | 1 | Compute span bounds, bypass integer `SCREEN_MIN_SPAN` rejection |
| `CONSERVATIVE_SLIVER_CULL` | 1 | Retain its separate span-shape test |

Linked `$9039–$9050` checks the sign, then `$FF` high byte and low byte **`CMP #$E0`**, which is the −32 boundary. The code at `$42E4–$42EE` binds the area test, depth test and start of lazy projection in that order. Flags merely present elsewhere in the emitted source are not treated as executed branches.

All original vertices of an accepted face must have safe depth **≥8**. After projection/loading, the collection pass computes `spanw/spanh`. Faces with all strictly positive depth high bytes skip the sliver test; that far-depth exception does **not** apply to these captures. Otherwise, if height ≤3, width must be ≥6; if height ≥4, width ≥4 or height ≥6 is sufficient. Third face 7 has loaded width **34**, height **45**, and safe vertex depths, so it survives. Its rounded loaded Y coordinates come from captured `syQ2`, using `(syQ2+2)>>2`, rather than assuming the separate byte `sy` is identical.

## Captured inputs reproduce the submitted ID sets

| Frame | Reconstructed cross products, IDs 0..7 | Accepted IDs | Actual draw order |
|---|---|---|---|
| First | `784,784,784,784,−784,−784,−784,−784` | 0,1,2,3 | 3,2,1,0 |
| Second | `772,340,632,1064,−632,−1064,−772,−340` | 0,1,2,3 | 1,2,0,3 |
| Third | `745,17,451,1179,−451,−1179,−745,−17` | 0,1,2,3,7 | 1,7,2,0,3 |

Third captured `rxbuf` is **`[23,−23,0,0,14,−14]`**, and `rybuf` is **`[4,−4,26,−26,−7,7]`**. Face 7's indices are `[3,0,4]`. The model's accepted sets exactly match the actual IDs in all three finite samples. The order is observed from bucket drawing; this check does not reconstruct sorting independently.

The complete snapshots are inputs, not an independent projection oracle. Some first/second projected workspace entries have `projdone=0` and can be stale. Screen-span/sliver calculations are therefore evaluated only for accepted faces whose three projected entries are all marked valid. No rejected face is assigned visibility from stale screen coordinates. Full-rotation correctness, ideal continuous geometry and the merits of the conservative tolerance remain outside this proof.

## `$0C` is the draw identity

Although its name says Mode 4, **`MODE4_FACE_ID_LATCH=1`** is active in this Mode 6 build. The bucket trampoline **`$CA1D`** stores the face ID into `sortj=$51` and **`mode4_current_face_id=$0C`**, checks it is below eight, restores Y from `$0C`, and resumes the ordinary face loop at `$4019`. The span entry dump already includes this zero-page byte.

`faceidx=$0D` is the collection cursor and stays **8** in all 530 spans. It cannot identify the current draw. The producer reads `$0C` from each captured ABI, walks that span's accepted timing-node parents to its `draw_face` node, and requires one consistent ID and contiguous span indexes throughout every subtree. All **13** observed draw-call subtrees have such a group.

## Exact observed draw subtrees

The join key is **frame + first span index + first span clock**; complete clocks and node indexes are in the receipt. Span indexes are local to each frame. These costs include geometry bounds, shade edges, row setup, material spans and bitmap spans under the actual `$9223→$4030` draw interval.

| Frame | Face | First span | Span count | Pixel visits | Observed subtree cycles |
|---|---:|---:|---:|---:|---:|
| First | 3 | 0 | 42 | 945 | 153,740 |
| First | 2 | 42 | 42 | 945 | 128,267 |
| First | 1 | 84 | 42 | 945 | 127,671 |
| First | 0 | 126 | 42 | 945 | 151,017 |
| Second | 1 | 0 | 34 | 194 | 80,954 |
| Second | 2 | 34 | 48 | 532 | 114,971 |
| Second | 0 | 82 | 29 | 672 | 115,950 |
| Second | 3 | 111 | 48 | 1,258 | 200,095 |
| Third | 1 | 0 | 35 | 136 | 82,077 |
| Third | 7 | 35 | 45 | 203 | 90,751 |
| Third | 2 | 80 | 49 | 360 | 110,821 |
| Third | 0 | 129 | 25 | 621 | 107,195 |
| Third | 3 | 154 | 49 | 1,346 | 208,066 |

Third face 7's subtree runs from clock **4,598,997** to **4,689,748**. Its first span, index 35, enters at **4,647,317**. Exclusive descendant costs sum exactly to 90,751:

| Component | Elapsed cycles |
|---|---:|
| XYQ2 geometry bounds | 26,675 |
| Shade edges | 21,198 |
| Row setup / dirty tracking | 13,766 |
| Bitmap span drawing | 23,212 |
| Screen/Color RAM material spans | 5,873 |
| Draw wrapper / residual | 27 |

This is **13.42% of the observed third render's elapsed cycles**. Its initiating JSR, previous material/reflectivity/face loading, collection and bucket traversal are outside this subtree. VIC stalls and IRQ time remain inside whichever interval contained them.

These numbers are observed costs, **not measured savings**. Omitting a group can change earlier setup, projection, bucketing, VIC phase, IRQ incidence and later work. Pixel equivalence of any omission belongs to the independent omission audit; this producer does not render an omitted-face reference. A fixed captured subtraction is not a native benchmark of a new culling policy.

## Reproduction and evidence bounds

```sh
rtk proxy python3 -B research/3dvibe64-overdraw/cull_policy.py --output build/research/3dvibe64-overdraw/cull-analysis/replay-01
```

Use a fresh directory. Output bytes do not depend on its name. The accepted `cull-analysis/cull-proof.json` is **36,749 bytes**, SHA-256 **`a8498b02b8a9c574694998af214d7b9f969292f409e1ca9b3f55e82cd23b0711`**. The initial early source-constant check failed on a named threshold alias before creating output; the corrected producer resolves that single explicit alias and completed successfully.

The receipt pins the original assembly/PRG/symbols, frozen native-profile producer, accepted profile/interval/span receipts, and closed case manifest. It rechecks all **29 case files** against case digest **`13bfd23f30bf0b7a2db7a9e8dc4ceb8dc69e77d81c76862fe9b372a1f23ef714`**. Wire/stack/CPU/snapshot acceptance is reused from the [frozen profile](3dvibe64-profile.md), not rerun as a native experiment.

Source references in this exact assembly: zero-page latch line **28**; flags **641–650,671,703,706,715**; collection **16419,16545–16689**; depth/sliver **16780–16900**; area test **18046–18140**; face loading and direct-span bypass **10244–10605**; multiplier **25761–25820**; latch trampoline **28448–28458**. The receipt records linked byte guards, quarter-square binding, complete captured workspaces and all per-group cost components. No frozen artifact, shared index, product source or emulator state was changed.
