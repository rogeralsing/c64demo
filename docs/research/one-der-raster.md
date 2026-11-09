# One-Der: a complete captured software frame matches the scalar

Research date: 8 November 2026. A pure integer reconstruction of One-Der's
gradient, edge and span routines reproduces **all 2,048 bytes** of one
original draw buffer. It also matches **384 edge/intensity workspace
bytes** and the final **32 horizontal-offset bytes**. No emulator or CPU
instruction interpreter runs in this reconstruction.

The inputs are four accepted **screen X/Y/intensity triangles**, in their
captured draw order. This is a rasterizer result, not an independent
reconstruction of the preceding rotation, projection or culling. Actual
VIC scanout and full-animation correctness remain separate.

See [the original native run](one-der-gouraud.md),
[the independently reconstructed gradient](one-der-gradient.md), and
[the charset/display map](one-der-display-map.md).

## What the model consumes

The frozen original run already supplies the four triangle inputs and
completed RAM at `$09D6`. The new producer has two passes:

1. A conditional pass uses the captured gradient bytes as inputs.
2. The final integrated pass calls the pinned pure
   `gradient.gradient(vertex_triples)` implementation instead. Captured
   gradient bytes and return carry are comparison oracles only.

Both passes produce identical target and workspace data. All **32
gradient output bytes and four carry bits** match before rasterization.
The packed shade LUT is the same `$3000..$37FF` data independently
reconstructed in the earlier acceptance. Its duplicate pages remain
addressable; lookup-index sums are not prematurely masked to eight bits.

The incoming selector `$4A=0` toggles to 1, choosing buffer `$2800`.
The scalar starts that entire 2 KB target at `$FF`, matching the original
full-buffer clear. It does not seed target pixels from the completed
native image.

## Edges: both endpoint rows are constructed

For each directed triangle edge, horizontal edges are skipped. An edge
with increasing Y writes the left-bound array `$3E00` and intensity array
`$3F00`. A decreasing-Y edge is reversed for construction and writes the
right-bound array `$3E80`. Original edge order is retained, so later edges
can replace shared endpoint rows.

Geometry uses separate steep/shallow and positive/negative recurrences.
These include the original biased constants such as `abs(dx)+1`,
`height+2`, and the different shallow-edge starting error. They are not
replaced with a nearest-pixel DDA. The producer spells out those integer
recurrences and guards the retained in-range vertices and edge samples.

**Construction stores height+1 rows**, including both endpoints. The
intensity builder uses a Q8 increment of
`floor(abs(I1−I0)*256/height)`, with the original direction convention.
The generated cell's endpoint STA executes before its planted RTS.
Rasterization then consumes **minY ≤ Y < maxY**. Constructing endpoints
and drawing rows therefore have different inclusion rules.

The original fast geometry cells use undocumented NMOS **SHY abs,X**,
not STY. The setup at `$2207` tests the behavior and selects the ten-byte
templates. For these samples its `$3F` mask leaves the in-range 0..63 X
values unchanged. The model does not generalize that observation to
out-of-range vertices, arbitrary CPU variants or page-crossing SHY cases.

The native workspace contains old untouched cells. The final comparison
therefore separates **273 computed/written bytes** from **111 preserved
incoming bytes**. More strongly, the producer checks that **every left,
right and intensity row used to draw each triangle was freshly computed
by that same triangle**. Old workspace cannot supply hidden target data.

## Shade offsets and boundary masks

After calculating a gradient, the original code constructs 32 horizontal
shade offsets with generated ADC chains. The scalar preserves carry
between cells, including carry wrapping back into the fractional stage.
It does not substitute `floor(k*gradient)`.

The source bytes at `$0E6C` load `$4A` before branching. Therefore the
buffer-A offset path enters with A=0; buffer B explicitly loads A=0 too.
An earlier provisional interpretation that A retained the old gradient
integer byte was incorrect. The final producer guards these instructions.
Only buffer B's completed output is compared in this case.

For row Y and bounds L/R, the row's shade origin is:

```text
origin = (I[Y] − (oldGradientHigh if L is odd else 0)
               − horizontalOffsets[L//2]) mod 256
```

The odd-left correction subtracts the old high byte only. The preceding
LSR has already supplied carry; there is no additional subtraction of 1.
Even rows select the `$3000/$3200` table pair; odd rows select
`$3400/$3600`. The two table reads form high and low nibbles of a packed
byte. They are new shade contributions, not OR blending with the old
destination.

Interior full bytes overwrite the destination through the unrolled
kernel. Partial bytes preserve outside bits with the left masks
`00 C0 F0 FC` and right masks `3F 0F 03 00`. For combined outside mask M:

```text
new = (old AND M) OR (packedShade AND NOT M)
address = $2800 + 128*byteColumn + Y
```

The scalar expression covers both original same-byte and separate-edge
paths. Left/right X bounds are inclusive. Its source-bound signed tests
are equivalent to ordinary comparisons within this retained 0..63 range.

## Full-buffer result and rejected endpoint variant

| Compared output | Result |
|---|---:|
| Target `$2800..$2FFF` | **2,048 / 2,048 bytes equal** |
| Left/right/intensity arrays `$3E00..$3F7F` | **384 / 384 equal** |
| Last horizontal offsets `$3F80..$3F9F` | **32 / 32 equal** |
| Unique target bytes written | 844 |
| Remaining target bytes, independently cleared to `$FF` | 1,204 |

The four triangles produce 15 / 80 / 70 / 75 nonempty row spans and
81 / 375 / 150 / 388 software-byte visits. Coverage includes 6,220 unique
bits; another 10,164 bits retain the clear value. Bit coverage is distinct
from visible colored pixels: drawing can also produce the black outside
selector. Byte identity implies identity of all 8,192 encoded multicolor
selectors, not identity of a complete displayed PAL frame.

Target SHA-256 is
`6c50578370bed2300e6f2383a228343e1ad2f4d8280402e1333f85bcc77ef3af`.

A deliberately rejected edge variant stores only `height` rows. Its final
workspace differs at four addresses:

| Address | Rejected variant | Original native |
|---|---|---|
| `$3E5E` | `$09` | `$08` |
| `$3E72` | `$2E` | `$30` |
| `$3EF2` | `$2E` | `$30` |
| `$3F72` | `$8E` | `$9E` |

This is a concrete counterexample to that construction convention. The
receipt retains the mismatches. It is not presented as four independently
verified visible artifacts or a universal rule for other vector fillers.

## Reproduce and continue

```sh
rtk proxy python3 research/one-der/raster.py --output build/research/one-der/raster-analysis/fresh-replay
```

Use a fresh output directory. The producer pins the earlier native
acceptance, rehashes original RAM inputs and the independent gradient
module/receipt, and guards original generated templates and offset cells.
The previous capture already establishes the original loading, wire,
snapshot and CPU-port contract; this analysis reuses that bounded custody.

Final acceptance is `raster-analysis/accepted-03/raster-proof.json`,
**15,832 bytes**, SHA-256
`47a4771534cbf6a0e6cb784f05d4ce74a6fde5b594f76c82b2de2cbce6c63ad1`.
The checked producer is **15,720 bytes**, SHA-256
`412e47647d00f2c3a5925ef88d68b2421253fd09f22795a6435dde41894c2607`.
`accepted-01/02` preserve earlier conditional/integration observations.
Fresh root replay reproduces all four final output files exactly;
`root-replay-check.json` records their identities. Static peer review
found no material issue.

The original native case, prior producers/receipts and unrelated
sprite-ball work remain untouched. No new native execution, timing,
performance improvement or production-renderer change is claimed.

The next display task is to bind this software plane to actual committed
VIC fetches, especially the text-to-bitmap transition at raster 178.
Rotation/culling and other poses remain outside this four-triangle
acceptance. HCL's independent thirteen-level tracing-line implementation
is a separate original-code research target.
