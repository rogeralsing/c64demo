# Aloft: native-bound early cancellation and cached row-7 requests

Research date: 9 November 2026. The closed original-native case now binds the
first cell's `$D011` change to the early badline-cancellation mechanism. Under
the typed source execution closure, each of the two observed 200-call
intervals supports **8,000 logical row-7 graphics requests and zero matrix
fetches over raster lines 48–247**. Four independently captured return states
match the predicted VIC counters and forty cached codes/colors.

This is a logical fetch/counter/cache result. Physical RAM/ROM/GLUE mapping,
fetched byte values, pixels and the separately named moving layered scene
remain open. The result covers two declared intervals with explicit initial
hardware state and source closure; it does not establish every animation
frame or delivered FPS.

## Inputs stay separate from comparisons

The [native custody note](aloft-execution-native-20261109.md) pins the authentic
original boot, all eighteen RAM/VSF pairs, watches, complete hook framing and
actual resources. The [typed cell execution](aloft-cell-execution-20261109.md)
supplies independently predicted `$D011` values and the complete admitted
write/control footprint. It retains opaque comparison values and their flags
without substituting invented reads.

The frozen [VIC fetch contract](aloft-fetch-contract-20261109.md) supplies the
MOS8565/PAL table, counter rules and conditional schedules. The independently
[source-mapped glyph row](aloft-cell-glyphs-20261109.md) supplies the forty
expected cached codes. The new binding uses genuine pre-`$0500` hardware
state and observed instruction-completion bounds as declared inputs. Target
VIC counters/cache are evaluated only after both expected-state files have
been written. Actual hook store values are never the predicted write data.

The initial state in both intervals has RC7, idle1, VC/VCBASE/VMLI zero,
badline/allow-badlines zero, `$D011` and delayed mode `$18`, `$D018=$10`, no
sprite DMA and **`$D015=0`**. The enable-register check matters: DMA zero at
one instant alone would not exclude a later enabled sprite start. The source
footprint and full watched interval admit only `$D011` among VIC stores and
no CIA2 bank/DDRA stores, preserving these prerequisites. Actual `VICIIVSPBug`
queries all report zero.

## Why the first INC matters

The first interval supplies these natural boundaries:

| Boundary | PC | Raster line / zero-based cycle | Relevant observation |
| --- | --- | --- | --- |
| Genuine dispatcher entry | `$0500` | 47 / 24 | Declared initial hardware state |
| Before first INC | `$201D` | 48 / 6 | Badline1, active display, RC7, `$D011=$18` |
| After first INC | `$2020` | 48 / 12 | Badline0, active display, RC7, current/delayed `$D011=$19` |
| First cell return | `$0503` | 48 / 24 | RC7, active display, VC10, VCBASE0, VMLI10 |
| Whole chain return | `$F0B1` | 247 / 30 | RC7, active display, VC808, VCBASE792, VMLI16 |

The source checks badline equality before the hardware-cycle14 RC-reset
branch. The observed change is complete at zero-based cycle12, before that
cycle14 recheck at zero-based cycle13. The early equality has already entered
display; the new YSCROLL inequality prevents RC from being reset. RC7 therefore
survives into the active graphics slots. At hardware-cycle25, ten graphics
slots have completed, yielding the independently predicted VC/VMLI10.

This binds the local early-cancellation counter mechanism used by early
linecrunch. It does not assign that mechanism to a screenshot or establish
the separate named scene's identity. The original source-only contract and
its later-activation example remain unchanged historical predictions.

## The 200-line invariant uses deadlines

For every call in both intervals, the consumer associates a source-predicted
normal INC or literal `$18` reset with the actual watched instruction. Normal
INC read domains come from the completion of the immediately preceding
watched STY through INC completion. Literal-reset bounds use the preceding
STY and guarded `LDA #$18 / STA $D011` sequence. No post-INC value or flag
supplies an operand-read input.

All two hundred conservative change intervals lie within one raster line,
from zero-based cycle **6 through 12**. Before the change, source YSCROLL
equals that line's low three bits, allowing early display activation. After
the change it equals the next line's low bits, so the hardware-cycle14
recheck and all matrix-fetch opportunities see inequality. Every old and
final source value also satisfies `value & $F8 == $18`: DEN/RSEL remain set,
BMM/ECM remain clear, and the high bit is unchanged. MOS8565's delayed-mode
fetching therefore remains in the admitted character-address regime.

The source PAL table has forty phi1 graphics slots per line. RC stays at 7
and display stays active throughout them; every phi2 matrix-fetch gate is
false. The RC58 update then saves the advanced VC in VCBASE and enters idle.
On the next line, the retained scroll value permits activation before the
next bounded change. Induction over the two hundred observed call deadlines
gives **40 × 200 = 8,000 logical graphics requests**, without invoking the
matrix-cache writer during the declared window.

Each line uses the same forty cached character codes. With the admitted
logical character base and RC7, the address sequence is
`(cached_code << 3) | 7`, covering forty addresses for codes `$00..$1F` and
`$F0..$F7`. The CPU's narrow glyph/state working set can change while the VIC
continues to use those cached codes. This explains why the large displayed
area need not be redrawn as a complete bitmap. The actual bytes returned by
those requests are a later reconstruction task.

The first and later source closures are both checked explicitly: all cells
are strictly recognized; data stores use the forty admitted addresses and
are disjoint from the dispatcher, generated code, lookup and return stack;
the other cell store is `$D011`; IRQ is disabled at entry. The closure still
declares no unmodeled external NMI, reset/restore or RAM-writing DMA and keeps
the captured CPU mapping. These assumptions are retained in the prediction
files rather than hidden behind endpoint equality.

## What the native comparisons establish

Both first-cell returns and both chain returns match source-derived RC,
idle, VC, VCBASE and VMLI. All forty cached codes and colors also match at
those four states. The later interval uses a different declared target list;
the same counter/cache invariant passes. The native after-line captures
show that execution proceeded beyond the final declared graphics slot.

Endpoint clocks select the phases at which expected counters are evaluated;
this binding does not independently predict CPU instruction timing. Monitor
hooks report instruction completion, and duplicate RMW store hooks share
that clock. They bound cancellation deadlines but do not timestamp physical
operand-read, dummy-write and final-write bus phases separately.

Cache equality at two stops alone was insufficient. Here the source and
complete deadline interval additionally exclude the matrix-fetch writer,
under the stated closure. Cache origin before pre-`$0500`, later lifetime
outside lines48–247 and all-frame behavior remain unproved. The two raw
wrap captures retained for future viewport work are from the same preceding
field, 63 cycles apart; they do not supply two independently predicted
display generations.

The VIC snapshot omits physical bank/address mapping pointers. This consumer
therefore reports **logical requests** and leaves physical RAM/ROM/cartridge
and GLUE resolution false. It does not predict graphics byte data, border or
draw-pipeline evolution, or committed viewport pixels. Those limits apply
even though the observed counters and cache match.

## Accepted files and continuation

[fetch_binding.py](../../research/aloft-execution-20261109/fetch_binding.py)
is 13,461 bytes, SHA-256
`e8b688e59d3acee72384c57011d1ba7e079f18568bc456df2666646c18b2d70f`.
Its [accepted receipt](../../build/research/aloft-execution-20261109/fetch-analysis/binding-accepted-01/fetch-binding-proof.json)
is 3,416 bytes,
`31efa766ff16b02d04c834ba107c40c868d0124fb4c0ea2e499e5b6f6644916c`.
It pins native receipt `5db9694d…`, typed execution receipt `b3bf0ae5…`, the
frozen fetch contract and original glyph-mapping receipt by complete digests.

The [self replay](../../build/research/aloft-execution-20261109/fetch-analysis/binding-self-replay-check.json)
and independent [root source review/replay](../../build/research/aloft-execution-20261109/fetch-analysis/binding-root-replay-check.json)
both reproduce **five files / 1,100,477 bytes exactly**. Root report: 1,252
bytes, SHA-256
`7ba994ca306a32ed696cbd0ae28cff6a36444b041412ccf8cb1c7f3515f2f957`.
The original probe, pre-guard source snapshot and final candidate remain
retained; no frozen contract/source output was rewritten.

Reproduce into a fresh output directory:

```sh
rtk proxy python3 -B research/aloft-execution-20261109/fetch_binding.py \
  --native-sha 5db9694db276541a5fd2b5cb386e92639e6da2c0d6cd644caf758eb113cc2326 \
  --math-sha b3bf0ae5e74059bc17b29717174587bb679bfe3701a388dad0f9a3d88b8ebdf5 \
  --output build/research/aloft-execution-20261109/fetch-analysis/new-binding-replay
```

Continue by binding physical phi1 mapping and source-predicted glyph writes
to the request phases, then reconstructing fetched data and independently
committed pixels. Keep observer completion bounds separate from bus-time
claims, and keep the unresolved named scene and other demo backlogs active.
