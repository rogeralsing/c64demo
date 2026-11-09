# Aloft: the final graphics fetches survive the dispatcher return

Research date: 9 November 2026. The original dispatcher returns halfway
through the last displayed line. Its natural `$F0B1` return is raster 247,
cycle 30, while the last source-bound graphics slot is cycle 54. Treating the
return as the end of display would leave the last twenty-four cycles unbound.

The original code instead waits before resetting the glyph staging bytes:

```asm
; Original bytes at $F0B1: A2 F8 EC 12 D0 D0 FB
    ldx #$f8
wait:
    cpx $d012
    bne wait
; Fallthrough $F0B8 starts LDA #$10 / STA $D011, then glyph clearing.
```

All three admitted instructions are read-only with respect to memory.
The branch returns to `$F0B3` or falls through to `$F0B8`; there is no call,
store or alternate source control path in this seven-byte interval. A finite
write-footprint argument therefore protects the glyph state until fallthrough,
under the existing no-unmodeled-NMI/RAM-writing-DMA and stable-mapping closure.
Endpoint code equality alone is not the argument: the source has no memory
writer that could transiently change the admitted wait or glyph data.

Both retained natural windows supply the same boundaries:

| Window | Dispatcher returned | Wait fell through |
| --- | --- | --- |
| First | clock 130216935, raster 247/cycle 30 | clock 130216971, raster 248/cycle 3 |
| Later | clock 131474919, raster 247/cycle 30 | clock 131474955, raster 248/cycle 3 |

The fallthrough occurs after the final logical graphics request at
raster 247/cycle 54. No watched activity appears between either pair of stops.
Original generation 31 supplies the independently matched code bytes; genuine
pre-`$0500` RAM and both ending captures supply separate source guards.
The existing full-range watch coverage and source closure remain explicit.
No final glyph values, GBUF values or framebuffer pixels seed this proof.

The [producer](../../research/aloft-pixels-20261109/tail_guard.py) writes both
source/deadline predictions before evaluating ending captures and hooks. It
uses the already accepted logical-fetch and typed-cell contracts. It does not
interpret the CPX loop, predict individual raster-register read phases, or
advance a CPU, VIC or pixel pipeline. Observed fallthrough is a deadline;
it is not substituted for an exact physical CPX bus timestamp.

The [accepted receipt](../../build/research/aloft-pixels-20261109/tail-analysis/accepted-01/tail-guard-proof.json)
is 9,967 bytes, SHA-256
`f88ec772bd11d0c6e4669b0541578319cd6c1500e57a4ae8d66e57116c130029`.
The independent [peer review/replay](../../build/research/aloft-pixels-20261109/tail-analysis/peer-replay-check.json)
and the [self replay](../../build/research/aloft-pixels-20261109/tail-analysis/self-replay-check.json)
reproduces all three files / 23,243 bytes exactly. Candidate 01 and its checked
source remain retained: code review replaced a varying self-output path in
the receipt with output name/size/hash before acceptance. The prediction did
not change.

```sh
rtk proxy python3 -B research/aloft-pixels-20261109/tail_guard.py \
  --output build/research/aloft-pixels-20261109/tail-analysis/new-replay
```

This closes the final-row lifetime gap for the forty-byte glyph-stream join.
It does not close the earlier absolute-store bus-phase question. Protection
ends at `$F0B8`; later mode changes, glyph reset, music and field-tail pixels
remain separate work. The broad research goal and the unresolved named-scene
identity remain active.
