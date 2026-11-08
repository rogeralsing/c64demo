# Prepared visible fragments and dynamic boundary glyphs

An original counterpart of Next Round's character-rendering trade: two projected
cubes become disjoint visible/color-pattern regions, then the C64 rasterizes
those regions using shared interior glyphs and dynamically allocated boundary
glyphs. The right face of the front cube has a slotted appearance. Where that
face overlaps the rear cube, prepared region patterns supply the rear-looking
color between the slots.

```sh
sh build.sh
sh run.sh
python3 verify.py
```

The shared builder produces `build/example.prg`. VICE runs in PAL at normal
speed. Preparation and verification use Python's standard library plus the
already-installed Pillow package; no new dependencies are installed.

## Preparation and actual runtime work

`prepare.py` constructs its own two isometric cube projections and sixteen
relative positions. Exact rational half-plane clipping produces **17–19 convex
fragments per pose**, stored as **5,184 bytes of edge commands**. Regions are
split into A-only, B-only and overlap pieces, with explicit pattern choices.
An independent original-face pixel-center classifier checks that every covered
sample belongs to exactly one prepared fragment with the selected material.
The original released scene dataset is not included.

The C64 receives fragment materials and projected edge endpoints. It walks
horizontal, vertical and unit-diagonal edges at runtime, computes row spans,
and fills the corresponding cells. Only the character rows and sample rows
inside each fragment's computed Y bounds are revisited. No complete animation
bitmaps are stored. The host performs projection and visible-region preparation;
there is no live 3D transformation, generic transparency or runtime depth sort.

The normal multicolor character screen contains a centered **128×160 logical
sample window**, or **256×160 physical pixels**. Codes 1–12 are shared two-row
patterns, expanded to eight glyph rows; code 0 is blank. A cell wholly inside
one fragment points directly at its shared pattern glyph. Such interiors need
one screen-code write instead of rasterizing all their pixels.

A partially covered cell receives one private glyph from codes **13–255**.
Its eight source rows are copied from the current shared glyph before the first
change. Further modifications of that cell reuse its private glyph. Endpoint
masks replace only the covered two-bit samples, preserving neighboring regions.
The twelve-pattern legend and a small mixed tile above the cubes make the
shared-pattern and copy/reuse behavior visible. The mixed tile begins as shared
pattern 6 and receives two partial changes while retaining private code 13.

The prepared fragments are disjoint at the declared pixel-center samples.
This makes their colors a resolved input, rather than two complete overlapping
cube faces blended by the rasterizer. Its coverage-masked boundary writes differ
from the original renderer's specialized left-store/right-OR ordering, while
preserving the shared-interior/private-boundary representation.

## Display and capacity

Two complete font/matrix pairs use `$2000` with screen `$0400`, and `$2800`
with screen `$0C00`. A completed pair is selected through `$D018` at the next
top-border boundary. The front pair stays unchanged while the back pair is
cleared and rendered. Every used private glyph and all unused font storage
are initialized on each back-buffer reuse.

The fitted `display.asm` include reuses the publication contract from our
character-rotozoom example. `glyph-spans.asm` adapts our sprite-vector endpoint
mask approach to four two-bit samples and dynamic glyph addresses. Existing
examples remain unchanged.

The scene uses **100–143 private glyphs**, within the 243-slot capacity. After
allocating code 255, a further request stops rendering with a red border before
publishing that back buffer. Shared glyphs and the previously published front
pair remain intact; allocation never wraps into the reserved codes.

## Independent native evidence

The normal, unpatched run passes **17 presentations**, all sixteen poses and
wraparound. A separate classifier derives final selectors directly from the
original cube faces and region-material rules. Native checks cover:

- Every matrix cell, all **2,048 font bytes** and all **1,024 matrix bytes** per
  presentation, including unused storage and private-glyph uniqueness/reuse.
- The immutable serialized fragment stream, shared pattern references, private
  boundary-cell capacity and the nonzero mixed-tile copy case.
- Seventeen complete VICE screenshots, including cell seams and both buffers.

A separate owned VICE run tests overload using a crafted upcoming **input frame**
of 243 disjoint one-pixel rectangles. Alongside the existing mixed tile this
requests 244 private cells. Normal decoding naturally consumes all 243 slots,
then reaches the guard without changing shared glyphs or publishing the failed
back buffer. Only the prepared input bytes are replaced for this control;
there are no PC, executable-code, caller or allocator-state edits. This control
is separate from the unmodified scene evidence.

The final cycle takes **34–40 PAL fields per scene update**, averaging **36.5
fields**, about **1.4 updates per second**. This is a readable mechanism example,
not a speed reproduction of Next Round. One measured optimization removed
whole-height rescans: pose-zero rendering fell from 1,057,766 to 760,941 elapsed
PAL clocks, a 28.1% reduction. Span calls fell from 3,042 to 698; empty calls
fell from 2,334 to 14. Native pixel/capacity proofs pass after that change.

Evidence remains under ignored `build/`: [receipt](build/verification/receipt.json),
[normal proof](build/verification/normal-proof.json),
[isolated capacity control](build/verification/capacity-proof.json),
[animation](build/verification/normal/prepared-fragments.gif),
[profile before](build/profile-before/profile.json) and
[profile after](build/profile-after/profile.json). Each verifier closes only its
owned emulator. Physical-hardware behavior, arbitrary slopes/nonconvex input,
the production's border continuation and its missing preparation exporter are
outside this bounded counterpart.

The twelve-pattern representation and allocation idea are attributed to
Bitbreaker's Next Round renderer. See the [renderer investigation](../../docs/research/next-round.md)
and [original prepared-scene analysis](../../docs/research/next-round-scene.md).
This folder contains original geometry, preparation and runtime code.
