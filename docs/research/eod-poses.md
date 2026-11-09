# Edge of Disgrace: additional original poses

Research date: 8 November 2026. This extension tests the frozen
[geometry](eod-geometry.md), [contour](eod-contours.md) and
[common-prefix](eod-frame.md) models on five further natural shader entries,
plus a newly captured baseline. Four additional targets are in the stable
shading phase; the fifth deliberately tests the departing fade. The fresh
baseline is independently recalculated; equality with an old pose is not
assumed. **All six predictions match every byte** of their 2 KB marker,
reconstructed-output and cleared-marker buffers. The frozen models required
no corrections.

The new producer is [multi_pose.py](../../research/eod/multi_pose.py).
Existing producers, receipts and native cases remain unchanged. No SDK,
Pong or product renderer is changed.

## Targets were chosen before capture

The old accepted `$546A` entry has phase `$5514=1`, counter `$5513=120`,
angles `$17EA..$17EC = 127,31,94` and motion selector `$17ED=8`.
Original `$5586` reads selector 8's velocities `1,3,4` from
`$17F6/$17FF/$1808`. Each shader body adds those values modulo 256.
The accepted next entry already checks the first increment.

Original `$5515` decrements the phase-1 counter until zero, changes to
phase 2 without reloading the counter, then counts upward. The frame's
`LDA $5514; CMP #3; RTS` epilogue exits only after phase 2 reaches counter
13. Thus phase 2/counter 6 is a naturally reachable earlier entry.
Body counts below are source arithmetic, not PAL field or clock predictions.

| Target | Entry phase/counter | Bodies after old reference | Predicted entry angles | Reason to capture |
| --- | --- | ---: | --- | --- |
| `baseline` | 1 / 120 | 0 | 127, 31, 94 | Fresh original input and output for display acceptance |
| `p110` | 1 / 110 | 10 | 137, 61, 134 | Predicted flat internal lines and uniform outer edges |
| `p096` | 1 / 96 | 24 | 151, 103, 190 | Predicted mixed ascending, descending and flat internal lines |
| `p072` | 1 / 72 | 48 | 175, 175, 30 | Predicted zero-width outer edge and angle wrapping |
| `p024` | 1 / 24 | 96 | 223, 63, 222 | Predicted single active face and one internal boundary |
| `p206` | 2 / 6 | 126 | 253, 153, 86 | Different fade/ramp window and predicted zero-mask operations |

These are hypotheses. Native checkpoint predicates use only actual
phase/counter, dispatcher state 10 and the original `$546A` code generation.
They do not filter predicted angles, face flags or rendered results.
Any disagreement must therefore remain observable.

## Input and comparison boundaries

For each target the parent captures paired full RAM/VSF states at:

1. `$546A`: begin, before ramp/geometry/contours;
2. `$17DB`: normal body return;
3. `$1A73`: before common prefix reconstruction;
4. `$1750`: after reconstruction, before marker clearing;
5. `$1753`: after the cropped marker clear.

The parent owns original boot, native process control, wire/snapshot
acceptance and actual warp/speed observations. This producer consumes the
[closed native04 case receipt](../../build/research/eod/output-case-analysis/accepted-01/output-case-proof.json)
instead of duplicating its audit. That case contains 80 files, 9,764,629
bytes and 36 full RAM/VSF pairs. Its canonical listing SHA-256 is
`c52bb838d493b5d6261b1b55f931df74b358136748ceb9f9de201b8ea499540c`.
The initial 30-second observation wait is preserved in that custody record;
it is not a discarded retry or a shader timing measurement.

Each independent prediction starts **only from that pose's begin RAM**.
It rebuilds the frozen models' declared integer tables, calculates ramp,
coefficients, projected records, visibility, edge intersections, internal
boundaries and outer boundaries, then applies the common prefix and clear.
The later native captures are comparison oracles only.

Each begin state also binds 4,910 stage-code/data bytes to the original
joined files 51/52. The only exclusions are eight operand bytes at the
four original self-modified generated-cell JSR sites; their JSR opcodes
remain checked. The frozen contour model independently checks every used
generated cell and pointer against its address/template contract.

The incoming generated crop descriptors and old `$7000` output also come
from begin RAM. Guards check that those descriptors and old output remain
unchanged before the common prefix. Full 2 KB marker/output comparisons
include the 398 cells outside the crop that preserve incoming state; they
do not imply that every byte is drawn or cleared.

## Captured results

The [accepted proof](../../build/research/eod/multi-pose-analysis/accepted-01/multi-pose-proof.json)
checks all six buffers without changing the old producers or adding a
corrective subclass. Every predicted entry-angle hypothesis agrees with
the captured input. Those agreements were checked after capture; they were
not breakpoint conditions.

| Record | Active face IDs | Internal lines | Internal Y direction | Outer path counts | Plot operations |
| --- | --- | ---: | --- | --- | ---: |
| `baseline` | 0, 4, 5 | 26 | 8 ascending, 18 descending | 6 segmented | 435 |
| `p110` | 2, 5 | 11 | 11 flat | 4 segmented, 2 uniform | 380 |
| `p096` | 1, 2, 3 | 27 | 7 ascending, 17 descending, 3 flat | 6 segmented | 436 |
| `p072` | 4, 5 | 12 | 8 ascending, 4 descending | 5 segmented, 1 zero-width | 361 |
| `p024` | 4 | 1 | 1 descending | 2 segmented, 2 uniform | 189 |
| `p206` | 0, 4, 5 | 26 | 19 ascending, 7 descending | 6 segmented | 383 |

Face IDs are the original routine's active flags, not an independent
physical-visibility claim. Direction refers to the stored internal-line
endpoints before the line routine normalizes X. Uniform edges use the
generic `$1856` routine. All internal X-endpoint parity combinations occur
in this set; both half-X and full-X generated cells are exercised.

The new inputs also exercise first-product-zero, second-product-zero and
quotient-bit visibility decisions in addition to the old paths. They do
not cover every fallback branch. All consumed intersections are freshly
calculated for the corresponding body: 78, 44, 84, 46, 4 and 78 bytes
respectively; preserved unused intersection data does not seed the output.

`p206` is explicitly a phase-2 fade, with the predicted post-ramp bytes:

```text
a6 96 95 55 51 41 40 00 00 00 00 00 00 00 00 00
```

Its 26 internal line calls include eight zero patterns. Of its 383 plot
operations, 205 use zero masks. Those operations are part of the original
workload; this experiment does not remove them or measure an optimization.

Each clear preserves the same 17 nonzero marker bytes outside the crop.
The independently recalculated fresh baseline output is
[baseline-output-7000.bin](../../build/research/eod/multi-pose-analysis/accepted-01/baseline-output-7000.bin),
2,048 bytes, SHA-256
`f49b358d502aee74860db36ce54986e310ff4e8ec96e7d154adc402a35428378`.
It happens to equal the earlier output, but the old output file is not
used to produce this new prediction. The display acceptance can consume
this new file and its proof as its software-image input.

The observed body intervals are:

| Record | `$546A → $17DB` elapsed machine cycles |
| --- | ---: |
| `baseline` | 58,218 |
| `p110` | 41,313 |
| `p096` | 61,862 |
| `p072` | 42,393 |
| `p024` | 16,804 |
| `p206` | 58,290 |

These intervals include IRQ/VIC effects, omit common reconstruction/clear
and other caller work, and are not delivered frame rates. Prefix and clear
intervals are separately retained in the proof.

## Reproduce and continue

Run only the passive producer, choosing a fresh directory:

```sh
rtk proxy python3 research/eod/multi_pose.py \
  --output build/research/eod/multi-pose-analysis/replay-new
```

The producer pins the accepted case receipt, original files 51/52, frozen
geometry/contour/prefix sources and their accepted receipts. Output prefixes
do not enter proof bytes. A fresh self replay matched all 20 files and
283,518 bytes exactly; its [report](../../build/research/eod/multi-pose-analysis/self-replay-check.json)
is retained. Parent review found no material issue, and an independent
root replay also matched all 20 files and 283,518 bytes exactly. Its
[report](../../build/research/eod/multi-pose-analysis/root-replay-check.json)
is 3,478 bytes, SHA-256
`31ebbc05094e568fb2c6b98eb2c281a6bd251d52de0074e903386f9d2a540cd8`.
Final producer SHA-256 is
`61aa635ccfecff00a44c1d06862305e1387ef2c3faf92e50f30653ef488e8742`;
accepted proof SHA-256 is
`ca3baca1dd889b3b0e9ef9fe81d5f1f3c89f27c15d7a420f105a19d670f19a11`.
The consumed case receipt SHA-256 is
`0fe2af337eb6a2674e6cb60b7f861b744457fa7ee8b65e05eed2d10bd9c6a0dd`.

A small [failed diagnostic setup](../../build/research/eod/multi-pose-analysis/diagnostic-01/diagnostic-failure.json)
is retained: an ad-hoc command passed a relative path to a helper requiring
an absolute path and stopped before any model/native comparison. The
normal producer already used absolute paths. This was not a model
counterexample, and no native input changed.

A future counterexample must retain its failed proof and predicted files
before any narrowly scoped wrapper correction. Actual VIC fetch, palette
and [display acceptance](eod-display.md) is a separate consumer of the new
baseline prediction; a finished native output must not become its model seed.

This is a finite software-buffer acceptance. It does not independently
establish physical lighting, arbitrary clipping/objects, every visibility
branch, actual VIC scanout/palette/publication, animation-wide correctness,
delivered FPS or a safe optimization policy. Recorded intervals, when
available, are elapsed machine cycles that include IRQ/VIC effects; they
are neither timing predictions nor a delivered frame-rate measurement.
