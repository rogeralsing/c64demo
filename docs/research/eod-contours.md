# Edge of Disgrace: one complete marker frame from the initial state

Research date: 8 November 2026. The original stable frame can now be
reconstructed from its **`$546A` initial state**, through the independent
upstream geometry stages and scalar contour/line drawing. All **2,048
marker bytes** match original RAM after the outer edges and at the body
return. The completed native marker buffer is a comparison oracle only.

This extends [the single-line shader proof](eod-shader.md). The
[geometry model](eod-geometry.md) owns ramp, coefficient, projected-record
and visibility calculations. [The frame/custody note](eod-frame.md) owns
the new original native case and the subsequent common prefix/output pass.
Marker equality alone is not independent VIC scanout or general-pose proof.

## Two distinct input boundaries are preserved

The new producer retains both results separately:

1. **Captured-stage boundary:** start at `$5476`, immediately before
   `$5B56`. Projected vertex records, selectors and visibility flags are
   captured inputs. Independently calculate edge intersections, internal
   contours, silhouette edges and their marker writes.
2. **Complete frame chain:** start only at `$546A`. Call the pinned geometry
   producer's table initialization, ramp, coefficient, vertex and visibility
   functions, then run the same new contour/line model. Captured later-stage
   fields are never supplied as this model's input.

The two passes produce identical edge and marker results. Original stage
captures at `$5479/$547C/$547F` and `$17DB` check their outputs. The new
case acceptance is consumed by hash; its wire/VSF audit is not duplicated.

The geometry interface supplies eight six-byte records at
`$40,$46,$4C,$52,$58,$5E,$64,$6A`: offsets +1/+3 are projected X/Y, +5 is
the source intensity/depth selector. Six face flags are at `$60FD..$6102`,
twelve edge flags at `$6133..$613E`. The contour code does not consume the
upstream model's undeclared `$70..$79` scratch. Interpreting the selector as
an independently verified physical normal/light model is outside this proof.

## Edge preparation at `$5B56`

The routine visits twelve edges in descending index order, skipping flag 0.
It obtains endpoint record bases from `$613F/$614B`. Endpoint order follows
the `$A100` intensity bins, not a substitute screen-space sort.

For each active edge it writes minimum/maximum bins at `$616F/$617B`.
Flat-bin edges return. Other edges write X/Y intersections into twelve
32-byte records at `$61A0..$631F`: sixteen X slots followed by sixteen Y
slots. A boundary-exact high endpoint is explicitly stored before reducing
the interpolation limit.

The initial Q8 positions have fractional byte `$80`. A partial first
intensity interval uses the `$A010` remainder and the original three-term
coefficient arithmetic. Following intervals use the `$A200/$A300/$A400`
coefficients. Negative coordinate products use the original **one's
complement**, without an added 1. Carry/borrow and byte truncation remain
explicit; an ideal floating-point intersection is not substituted.

This frame has **nine active edges**. The comparison covers all 24 bound
bytes and 384 intersection bytes. Of the intersection bytes, **78 are
freshly written** and 306 retain incoming values. More strongly, every
intersection consumed by either later stage is checked against the fresh
write set: **all 78 consumed bytes are newly calculated for this frame**.
The preserved 306 bytes cannot seed hidden contour outputs.

The additional `$AD00..$AFFF` reciprocal table is independently rebuilt
from the `$12F6` 24-step remainder algorithm and checked against a separate
rational expression for every divisor. Its result is `$FFFFFF` at divisors
0 and 1, and `floor(2^24/d)` for 2..255. This is the original loop's finite
representation, not a mathematical definition of division by zero. All
768 table bytes match. The geometry producer separately reconstructs the
quarter-square and `$A0..$A4` tables.

## Internal shade boundaries at `$5D50`

Each nonzero face flag selects four vertex bases and four edge IDs. The
routine chooses its lowest-selector vertex with the original tie rule,
then walks forward and backward intensity chains. Completed/flat edge
intervals advance those chains rather than reading stale intersections.

For each new intensity boundary it reads both edge intersections and
forms the packed mask:

```text
pattern = ramp[level-1] XOR ramp[level]
```

Those inputs drive the scalar equivalent of `$1856`. The frame produces
**26 internal line calls and 207 marker plot operations**. Every byte of
the intermediate 2 KB marker plane matches the `$547C` capture.

## Generic lines and segmented outer edges

The earlier single-line model covered one mask-`$04` path. This model
extends the original `$1856` behavior across the retained frame's other
patterns, signs, row phases and endpoint parities:

- Descending X swaps both endpoints; zero horizontal extent returns.
- Two nibble phases select different marker halves and initial Y fractions.
- A populated two-selector nibble walks every X. A single selector walks
  only its even or odd X sites with the doubled slope. Empty nibbles skip.
- The half-X nonempty `CPY` leaves **carry 1** before the first generated
  cell. Initial parity correction and subsequent fractional/integer ADC
  carries remain distinct.
- X intervals are half-open. Ordinary `$1856` plants its terminal RTS at
  **cell+8**, after the final XOR/store and before that cell's step.

The twelve-edge outer pass `$5E65` selects **flag exactly 1**. Flat-bin
edges can use `$1856`, but this captured frame's six silhouettes use its
segmented ramp path. It orders intersections along ascending X, preserving
the special one-bin case and the original equality/direction branch, then
assigns a ramp entry to each segment.

That outer path always uses full-X cells. It plants the terminal RTS at
**cell+15**, after the final ADCs, and saves the resulting next position
between segments. Each segment explicitly starts with carry 0. Treating
these endpoints like the internal-line endpoints gives different pixels.

The model guards **154 generated cells** and their pointer entries against
the original templates and independent destination/mask formulas. They are
validated code context, not completed pixels used to choose output values.
The whole frame contains **435 plot operations**, 429 with nonzero masks,
touching **347 distinct marker addresses**. Multiple XOR writes can cancel.

## Full-buffer identity includes preserved incoming state

The initial marker plane is **not wholly zero**. It contains 17 nonzero
bytes, unchanged between `$546A` and `$5476`. The model preserves this
actual incoming state; it does not silently normalize the entire plane.
The common crop/reset contract is handled in the separate frame note.

All 2,048 final bytes match, including the 1,701 addresses this frame never
writes. This is complete-buffer equality from initial state plus predicted
writes, not a claim that every byte was drawn or cleared. Final marker
SHA-256 is:

```text
52a819a46e94201603d58aab7d68f2927f77130320b30f70c15fc04cf92dfc75
```

| Rejected interpretation | Final marker-byte errors |
|---|---:|
| Start half-X cells with carry 0 instead of the original carry 1 | 2 |
| Stop outer cells before their final step | 219 |
| Invent an all-zero incoming 2 KB marker plane | 17 |

The receipt retains counts and concrete differing addresses/values. The
zero-only assumption failed during first receipt preparation; no output
directory had yet been created. The original captures were unchanged, and
the final model retains the observed input. These controls establish
consequences in this frame, not universal error counts for other poses.

## Replay and scope

```sh
rtk proxy python3 research/eod/contours.py --output build/research/eod/contour-analysis/fresh-replay
```

Use a fresh directory. Final acceptance is
`contour-analysis/accepted-01/contour-proof.json`, **50,542 bytes**, SHA-256
`b8396182b088637ecb91aaba9f2bfd257b99efe7289b254dcd0dba612c3e5b98`.
The producer is **26,069 bytes**, SHA-256
`2fce8719143284f21b232b6a9fa80696b08cb63f9f81c5fb1ecda49270cca7d5`.
All eight outputs, **85,619 bytes**, reproduce byte for byte in a fresh
self-replay and independent root replay.
`contour-analysis/root-replay-check.json` records the latter (946 bytes,
SHA-256 `7d54b2194dad677e2281f182aea3bf12bfe54e7a59c7035eb8a997541ffd5720`).
Static peer review found no material issue in the source arithmetic,
endpoint/carry distinctions or the two input-boundary scopes.

Both input-boundary outputs remain retained. The stronger chain's
`predicted-frame-marker-7800.bin` is the input to the separate common-prefix
model. That next pass must preserve its unwritten old output and marker
cells, rather than equating software-buffer identity with drawing every
byte or independently accepted VIC fetches/palette/publication.

This is one original, in-range pose and initial state. It does not accept
arbitrary clipping, overflowed coordinates, every visibility branch or new
objects. No current-frame completed buffer seeds either model. No CPU
interpreter, emulator, downloaded host tool, subprocess, build, timing
prediction, performance improvement or product change occurs here.
