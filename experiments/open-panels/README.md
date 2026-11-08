# Detached cube panels with real XOR palette priority

Six two-sided cube-face panels rotate and breathe apart. Open gaps expose the
far panels; near panels remain opaque where the two layers overlap. This
original example demonstrates the prepared-vector and palette-priority
contracts studied in [The Lab MMS](../../docs/research/the-lab-mms.md) and
[open-panel compatibility](../../docs/research/open-panels.md).

## Build, run, verify

```sh
rtk proxy sh build.sh
rtk proxy sh run.sh
rtk proxy python3 verify.py
```

The shared KickAssembler wrapper writes `build/example.prg`. PAL VICE and the
repository's existing Python/Pillow installation provide the native check.
Verification starts and closes its own emulator.

## Geometry and prepared input

Each original cube face has half-size 25. Its center moves outward along its
normal onto a common larger box of half-size `38 + 3*sin(angle)`. The panels
remain parallel to that box's faces. Rigid yaw, pitch and roll preserve the
common convex supporting box; the camera stays outside it.

The producer projects 64 poses into a **96×128 logical** canvas, displayed as
**192×128 physical pixels** at screen position `(64,36)`. Prepared input is
only **3,456 bytes**: six records per pose, each containing a layer delta and
four projected `(x,y)` corners. No filled bitmaps or complete animation frames
are prepared. The C64 expands each quad into four perimeter edge calls,
computes exact half-open crossings, XORs packed markers, and runs a vertical
prefix fill into the hidden multicolor bitmap.

The panels are represented once each, including their back sides. They are
neither a welded closed cube nor duplicated opposite-wound faces. There is
no runtime 3D transform, painter sort, depth buffer or alpha blending.

## Why the two layers are valid

The producer assigns entry/near planes to A and exit/far planes to B. A ray
through a convex box has at most one entry and one exit face; each panel is a
subset of its corresponding supporting face. That supplies the two-layer
interpretation. The host audit additionally checks the **rounded raster
coverage of every pose**: no pixel belongs to two A panels or two B panels,
and ray/plane intersection depth places A ahead of B at every shared sample.

The native renderer emits delta **1** for A boundaries and **3** for B. Their
aggregate is filled once:

| Coverage | Bitmap selector | Actual hardware color |
| --- | --- | --- |
| Neither | `00` | Black `$D021` background |
| A only | `01` | Screen high nibble, A tone |
| B only | `11` | Color RAM, B tone |
| Both | `10` | Screen low nibble, the same A tone |

Both screen nibbles are equal in every cell. Consequently the overlap's
**actual selector is `10`**, while its visible color equals A-only `01`.
Native byte checks distinguish this from merely painting A over B with the
same final RGB colors. Edge submission order remains irrelevant.

Local palettes provide cyan/yellow A tones on opposite screen halves and
purple/light-blue B tones on opposite row bands. These fixed cell bands
demonstrate multiple local attributes; they do not give every panel an
independent material. Each 8×8 cell still has only black plus its A and B
tones, spending two selectors on the duplicated A color.

## Runtime storage and publication

The shared [edge sampler](../lib/polygon-edges.asm) owns no display layout or
zero page. Its `drawBoundary` consumes `lineX0/Y0/X1/Y1` and `boundaryColor`.
The caller's `plotBoundaryMarker` receives logical X, exact ceiling Y and the
selector transition. Coordinates use `[leftX,rightX)`; vertical edges are
skipped. Caller storage packs four multicolor lanes per marker byte.

Markers occupy 24 columns ×128 rows at `$4000..$4BFF`. Generated row stores
write the prefix into bitmap `$2000` or `$6000`; each consumed marker column
is then reset to zero. Both complete viewport rectangles are overwritten
on reuse, while the surrounding bitmap remains black. Screens at `$0400`
and `$5C00` hold identical aliased palettes. Static Color RAM allows coherent
top-border bank changes without an attribute-copy race.

## Verified behavior and limits

The 8 November 2026 native run passed **66 poses**, covering the complete
64-pose cycle and both buffers across wraparound. An independent rotation
matrix and rational polygon-coverage oracle checked all **202,752 marker
bytes and 528,000 bitmap bytes**. Fourteen full VIC images matched
**896,000 pixels**, with zero differences. Markers were empty after every
fill, and native palette registers/attributes matched the alias contract.

Every audited pose includes A-only, B-only and overlap samples. Overlap ranges
from **861 to 1,408 logical pixels**. Opaque RGB expectations select the near
surface directly, independently of the XOR marker implementation.

Presentation intervals were **157,242–157,253 PAL clocks**, eight video fields
per pose, or **6.25 poses/s**. This is the measured complete renderer cadence,
including marker generation, fill/reset and coherent publication. The example
makes no original-production frame-rate or physical-hardware claim.

The [native receipt](build/verification/20261108T081309.041175Z/verification.json),
[independent geometry audit](build/verification/20261108T081309.041175Z/geometry-audit.json)
and [sampled native animation](build/verification/20261108T081309.041175Z/animation.gif)
retain the bounded evidence. The GIF contains sampled native poses with their
measured elapsed time.

This construction supports these outward-translated, parallel panels on a
common convex shell. Independently tilted/intersecting cards, overlapping
regions within one layer, arbitrary opaque black patterns and unrestricted
per-panel colors need a different visibility or composition contract. The
original Lab's bytes, artwork and scene exporter are not used here.
