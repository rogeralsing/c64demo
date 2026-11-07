# Screen-aligned dither in our interlaced XOR filler

Read-only feasibility assessment, 7 November 2026. No renderer implementation, emulator session, or performance benchmark was added. This assesses the restored single-object, two-buffer interlaced icosahedron, including its existing exact edge rules and operand-reset filler.

**The proposed transfer is compatible with the current prefix cells.** Each field visits only one physical Y parity, so a two-row screen-aligned pattern has one constant packed byte for that entire field. Choose that byte per visible face, XOR the adjacent faces' bytes at each mesh edge, and mask out the sampled X lane before writing a marker. No interior postprocessing pass is necessary.

This transfers the fixed patterned-face idea from [Next Round](next-round.md). It does not copy its dynamic-character allocator or its already-prepared multi-face scene input. [The original scene investigation](next-round-scene.md) distinguishes its prepared transparency-looking fragments from general transparent overlap.

## The byte algebra

Our multicolor charset has four two-bit logical pixels per byte. The masks for logical `x & 3` are:

| Lane | Mask | Pair position |
| ---: | --- | --- |
| 0 | `$C0` | bits 7–6 |
| 1 | `$30` | bits 5–4 |
| 2 | `$0C` | bits 3–2 |
| 3 | `$03` | bits 1–0 |

Let `P[f,p]` be face `f`'s full eight-bit pattern byte on physical row parity `p`. Hidden faces contribute zero. For an edge between faces `a` and `b`, form:

```text
delta = P[a,p] XOR P[b,p]
marker at logical x = delta AND laneMask[x & 3]
```

AND with a fixed lane mask distributes over XOR. Therefore this marker is exactly the XOR transition between the two desired packed face patterns at that logical X. The usual prefix XOR reconstructs the chosen pattern for each visible face interior. Separate X lanes combine without interference because their masks are disjoint.

There is no requirement that a pattern ID be a linear function of the original color selector, or that its two phases be related. The twelve published even/odd pairs can be used directly, and any other two full-byte rows obey the same algebra. Pattern *bytes* participate in the XOR; pattern *IDs* must first be expanded to those bytes.

For example, `$CC/$33` is a checker between selectors 0 and 3. On even fields use `$CC` for that face; on odd fields use `$33`. With the current palette `(0,6,5,4)`, those selectors mean black, blue, green, and purple. Reusing the author's bytes therefore produces our palette, not the exact colors of the original production.

## What already fits, and the two assumptions that must change

The source owner is [`src/xor-fill.asm`](../../src/xor-fill.asm):

- `drawCubeBoundaries` already creates one contribution per visible face and XORs the adjacent contributions. The interlaced unrolled edge dispatch can continue to use that structure when the contributions become full-byte patterns.
- The generated boundary kernels already load one of four zero-page lane values, then EOR/STA the marker operand. Their instruction shape can remain unchanged.
- Each generated fill cell is already `EOR #marker; STA charsetByte; STX ownOperand`. A running accumulator can contain any eight-bit packed pattern. Its instructions, eight-byte cell layout, and nominal ten CPU cycles remain unchanged.

Two setup paths currently assume `boundaryColor` is only 0–3 and cannot accept a full-byte delta unchanged:

1. The general edge path stores the low pair and repeatedly shifts left twice to make the other lanes. For a full-byte delta, that can leak or discard other lanes. It must instead derive `delta & $C0`, `delta & $30`, `delta & $0C`, and `delta & $03`.
2. `xorBoundarySingle` uses `color*4 + lane` to index the 16-byte `xorPairMasks` table. A full-byte delta is not a valid color index. This path needs the delta ANDed with one of four lane masks.

The face-preparation loop must also select the even or odd byte for the **actual `interlaceFieldParity`**, not blindly use the presentation index's low bit. Our existing sequence is B-even, A-even, B-odd, A-odd. Expanded per-face even/odd arrays are one way to select bytes without a per-pixel lookup; table placement and the selection code remain implementation choices.

If adjacent face patterns happen to agree in a lane, their transition there is zero. Skipping that transition is correct. The original proper three-color model guaranteed contrast along shared edges; arbitrary dither choices do not guarantee that contrast, though the fill remains well-defined.

## Endpoints, field mapping, cleanup, and geometry

The dither does not alter the exact edge sample rule: canonical left endpoint, integer X in `[leftX,rightX)`, crossing `ceil(y0 + dy*(x-x0)/dx)`, vertical edges ignored. Nor does it alter the mapping from a full-resolution crossing `c` to field row `q = ceil((c-p)/2)`.

Same-q collisions still cancel by XOR. An even-field crossing at row 127 still maps to the existing virtual terminal sink at `$FF01`; that sink can hold any byte and is already reset after filling. The prefix must still consume the closing marker through the current ceil-max cleanup bound. These rules do not depend on whether a marker encodes a uniform color or a packed pattern.

All rows written during a selected field have the same physical parity, so their pattern phase is constant throughout that prefix chain. The other parity retains its prior same-buffer image and its correct physical-row phase. Dirty metadata remains per buffer/parity; old/current rectangle union writes zeros where an old shape or an old pattern has disappeared. A face with black pattern samples must not be omitted from dirty coverage merely because those samples are zero.

The visibility calculation and the guarded depth shortcut remain geometric. Changing a face's pattern does not change its culling decision. This reasoning relies on the current opaque visible-face coverage, rather than introducing another layer of overlapping surfaces.

## Host feasibility proof and its limits

[`research/next-round/prove_interlaced_dither.py`](../../research/next-round/prove_interlaced_dither.py) uses all 512 projected-vertex records from the previously native-verified single-object build `d5baf50b922f23ace12c829e28ef8a6796dd3431b334aff660409334a173c792`. It validates the model tables against the independent convex hull and recomputes exact signed-screen-area visibility.

The expected result comes from direct per-face rational interiors with opaque pattern assignment. The candidate result comes from the distinct mesh-edge-delta, marker, and prefix path. The assignment exercises all twelve published patterns on both physical row parities, while the original B-even/A-even/B-odd/A-odd histories are retained.

Results:

- **524,288 selected packed bytes agree** across 512 fields.
- All 24 pattern-ID/parity combinations are exercised.
- No covered integer sample belongs to multiple visible faces across the 1,733,289 covered full-resolution samples in this trajectory. This supports the opaque disjoint-coverage premise for these actual projected inputs; it is not an all-angle continuous-geometry proof.
- A negative control that feeds full-byte deltas through the existing two-bit ASL lane recipe fails immediately: 299 selected bytes differ in frame 0. This establishes why the lane-setup adaptation is necessary.

The receipt is `build/research/interlaced-dither/host-proof.json`, including program, report, pattern-table, helper, source, and script hashes. The proof runs no proposed assembly and makes no native timing, RAM-ownership, or raster-window claim. The existing native proof covers the old solid-color renderer; an eventual implementation would need its own focused lane/phase checks and native pixel/cadence validation.

## Likely cost and unsupported extensions

There is **no extra operation per filled byte** in this proposal. A straightforward general-edge mask setup uses 32 nominal CPU cycles versus the current 27, about five more per non-single edge. The one-sample path can plausibly save about ten nominal cycles by replacing the color-index calculation with a four-mask AND lookup. These are local instruction counts, not an overall measured result; face-table selection, relocation, branches, and page crossings still need a real build/profile.

The supported pattern is four logical pixels wide and two physical rows high, aligned to the screen. A different phase per face can be represented by rotating/selecting the bytes before rendering, provided the resulting bytes still describe that screen-aligned period. A larger vertical period varies within one field and would require additional transitions or another mechanism. Perspective texture mapping, per-pixel lighting, and a pattern whose phase changes along an edge are not supplied by this constant-byte scheme.

For the current disjoint visible-face geometry, black/zero samples are an opaque choice of background color. They do not reveal arbitrary rear faces. Overlapping contributions still produce their bitwise XOR, and ordering the calls does not create painter order. A specially aliased palette can nevertheless give a bounded two-layer priority, as described next. The [original Next Round scene](next-round-scene.md) separately demonstrates apparent transparency encoded in prepared visible fragments.

## A compatible palette exception: two-layer opaque priority

The [matched Lab open-panel stage](the-lab-mms.md) uses two bitmap selectors for the same color, allowing XOR to encode opaque priority. For a character-mode version, take outside byte `$FF`, binary coverage A/B, transition A=1 and B=3, Color RAM black, `$D021` as the B tone, and `$D022=$D023` as the A tone:

| Coverage | Final selector | Displayed tone |
| --- | ---: | --- |
| Outside | 3 | Black from Color RAM. |
| A only | 2 | A. |
| B only | 0 | B. |
| A and B | 1 | A. |

The ordinary XOR prefix thus gives A priority, with no extra operation in its filled-byte cells. Marker reset remains zero; seed and stale-image/blank-glyph output become `$FF`. This combines [N2's outside-code assignment](tower-power-n2-palette.md) with selector aliasing. It is a prospective encoding, not an implemented or timed renderer change.

The preconditions matter: at most one accepted region in each layer at a sample, only one global A tone and one global B tone in this character-mode setup, and layer membership selected correctly for the intended scene. It is priority A/B, not a general depth comparison. The native bitmap's varying panel colors additionally use local screen/Color RAM attributes; arbitrary face colors do not follow from this two-tone transfer. The [supporting-box panel case](open-panels.md) gives one geometry in which a near/far layer assignment can be justified.

This does **not** make arbitrary dither patterns opaque under overlap. B may stipple against empty black with lane contributions 0 or 3 when there is no further rear layer. A remains visible over either choice. But an opaque black A sample cannot simply omit A's contribution: with B present, selector `3 XOR 0 XOR 3 = 0` displays B. The constant-byte dither proof above covers disjoint visible-face interiors; a black stipple sample there has no rear layer to leak through. Opaque patterned A over B needs coverage-aware resolution, prepared visible fragments, or another separately proven mechanism. Intentional perforation is a different visual contract.

The palette truth tables and black-sample counterexample are checked in `research/the-lab/mms_open_cube.py`. Row parity, exact half-open crossings, q64 routing and per-buffer/per-parity cleanup remain necessary in either encoding. Interlaced parity stores image history and is not an extra free geometry layer.
