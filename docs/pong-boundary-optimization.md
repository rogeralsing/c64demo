# Pong boundary and fill optimization, 8 November 2026

Pong now uses **2.08% fewer mean elapsed renderer cycles** than the
[previous mapping optimization](pong-optimization.md), with the same game,
geometry and rendered canvas. Presentation remains **25 fps**, two PAL
frames per image. The PRG remains 51,106 bytes.

## Changes

- Pong's boundary sampler keeps the immediate zero-quotient exit. After one
  successful subtraction it dispatches widths 2, 3, 4 and 8 to exact division,
  avoiding eight more subtraction attempts on narrow, steep edges. Other
  widths continue through the existing exact subtraction path.
- Width 3 uses 128 quotient bytes and 128 remainder bytes, indexed by
  `abs(dy)` in 0..127. Together the tables occupy one aligned 256-byte page;
  neither half crosses its page for a valid numerator. Power-of-two widths
  use shifts and masks. No slope quantization is introduced.
- Material selection prepares the four existing lane masks. Pong's internal
  `drawBoundaryCachedMasks` entry reuses them across a material's edges.
  The public entry computes masks only after a multi-column edge reaches the
  generated drawing path. Existing `lineDY` scratch distinguishes the entries.
- Pong now uses the existing fast fill-column loop below row 127. It hoists
  Y=0 and restores the known EOR opcode directly after each temporary RTS.
  Row 127 keeps the general save/restore path because its stop can reach the
  next column or the generated bank's native RTS.

The first mask-caching attempt charged the public width-1 path 154 cycles,
exceeding its existing 150-cycle fixture budget. The retained correction
defers public mask calculation again. The rejected fixture evidence remains
under `mask-first-rejected-fixtures/`.

## Measured result

Each profile covers 706 presentations. These elapsed PAL cycles include VIC-II
bus stalls and raster IRQs; stage totals can shift when earlier work changes
the raster position of later work.

| Build | Mean renderer cycles | Peak renderer cycles |
| --- | ---: | ---: |
| Verified mapping baseline | 34,132.36 | 35,615 |
| Early exact division | 33,684.71 | 35,119 |
| Division plus fast fill | 33,553.29 | 34,992 |
| **Final, including cached masks** | **33,423.39** | **34,851** |

The final mean saving is **708.97 cycles**; peak cost falls by **764 cycles
(2.15%)**. The shortest presentation wait rises from 3,342 to 4,109 cycles.
Mapping/drawing averages 20,248.85 cycles and fill/reset 10,780.75; setup,
body rotation, projection and culling retain their baseline means.

The renderer total excludes the later game/motion update. Native verification
includes that update in the observed **39,299–39,325 cycles per presentation**.
A PAL frame contains 19,656 cycles, so the renderer still needs the two-frame
schedule. The division-only and division/fill rows are measured intermediates.

## Memory and verification

The exact width-3 tables use existing prelude space. The final layout leaves
256 bytes before `$2000` and 95 bytes before mapped I/O at `$d000`; generated
fill banks remain at `$4c00` and `$8c00`. The standalone build is byte-identical
to the root Pong PRG:

`3bcbc8bbf3178102518ec934ce26e3df54f27e525416ec74e3bf04aefeabdd4c`.

Validation passes 44 polygon fixtures and 930 edge cases. The public width-1
maximum is **131 cycles**, within its 150-cycle budget. Twelve game fixtures
pass, with a maximum fixture update cost of 394 cycles. The full native run
passes **706 presentations, 705 game updates and 32 independent canvas
checks**, producing 695 distinct canvases with zero boundary parity errors.
All 33 non-cycle sample fields match the baseline for every presentation;
eleven rebuilt non-Pong PRGs are byte-identical to their saved baselines.

All 32 baseline/current RGBA canvas crops are identical. Eight whole-screen
pairs contain nine differing black/gray pixels in total, outside the canvas: retimed `$d020`
writes move MOS8565 gray-dot emulation. Those full-raster differences are
retained; whole-screenshot identity is not claimed.

Local evidence:

- [Baseline profile](../build/pong/optimizations/20261108-mapping/final-profile/profile.json)
- [Division-only profile](../build/pong/optimizations/20261108-boundary/division-profile/profile.json)
- [Division/fill profile](../build/pong/optimizations/20261108-boundary/fill-profile/profile.json)
- [Final profile](../build/pong/optimizations/20261108-boundary/final-profile/profile.json)
- [Boundary fixtures](../build/pong/optimizations/20261108-boundary/final-fixtures/boundaries/fixtures.json)
- [Game fixtures](../build/pong/optimizations/20261108-boundary/final-fixtures/game/game-fixtures.json)
- [Native verification](../build/pong/optimizations/20261108-boundary/final-verification/verification.json)
- [Scoped frame/capture comparison](../build/pong/optimizations/20261108-boundary/final-comparison.json)
- [Other-target comparison](../build/pong/optimizations/20261108-boundary/final-legacy-regression.json)
- [Final input identities](../build/pong/optimizations/20261108-boundary/final-inputs.json)
- [Rejected mask fixtures](../build/pong/optimizations/20261108-boundary/mask-first-rejected-fixtures/)

## Continue here

Profile individual edge calls inside the remaining mapping/drawing stage,
grouped by width and quotient, before adding tables or unrolling more code.
Preserve the half-open boundary/parity contract and
the current public width-1 budget. Reuse the existing fixtures and full
706-presentation reference cycle, including steep crossings, reversed edges
and the row-127 fallback.

The width-3 tables depend on the current 0..127 numerator range. Cached calls
depend on matching nonzero material masks and on mapping, projection, the
sampler and IRQ preserving those bytes. Any broader caller or geometry range
needs a fresh check of those assumptions. High runtime space remains tight;
prefer remaining prelude space or reduce existing code before expanding it.
