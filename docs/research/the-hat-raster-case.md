# The Hat: closed native03 raster-window custody and visible-I/O oracles

Research dates: 8–9 November 2026. Fresh original side-B `native-03` is
closed and reaped. The [passive producer](../../research/the-hat/raster_case.py)
accepts all **40 full RAM/VSF pairs**, 386 completed serialized commands,
one naturally completed observation wait and four bounded watched windows.
There are no interruptions, retries, cancelled commands, restores or manual
RAM/register/PC patches. Both original disks remain unchanged.

The [accepted receipt](../../build/research/the-hat/raster-case-analysis/accepted-01/raster-case-proof.json)
binds actual source generations, checkpoint generations, CPU/flags/clock,
ports, beam, model/mode queries, all **7,267 store and 117 load hooks**, and
3,626 per-hook visible-I/O readbacks in two additional windows. These are
custody and comparison observations. Independent source value reconstruction
and VIC draw-tail/pixel interpretation are separate consumers; neither a
complete displayed field nor animation/FPS follows from this receipt.

B8/B9 are the original vertical upscroll source domain, as established by
[the source study](the-hat-upscroll.md). B17's separate horizontal logo carpet
and native01/native02 proofs remain frozen. The new
[raster source graph](the-hat-raster-source.md) supplies the independent
106-site raster-read anchor domain; native stores do not construct that graph.

## Original boot, closure and complete wire

Original B is both the autostart image and drive8 disk under PAL, true-drive
1541 emulation. Its 174,848 bytes, SHA-256
`1527038ebebca1a3d3d3379b91dd1a77dffb6d6d89a4dbfc32bf3f6908eb5b21`,
match the member in the retained original release ZIP. The
[disk extraction](the-hat-files.md) and [strict decoder](the-hat-dali.md)
own the original source-byte chain. The new case does not inject a PRG or
restore an old snapshot, and uses no disk swap, keyboard or joystick command.

Owned PID 57748 starts at `2026-11-08T22:05:03.293613+00:00` and is explicitly
closed/reaped with exit−15 at `2026-11-09T05:32:17.917143+00:00`. The observer
handle is terminal. Its long wall-clock lifetime includes paused observation
and is not a rendering-rate measurement. The same process/endpoint retains
one sequence 23 wait, 30.008 seconds, which later completes naturally.

The [closed manifest](../../build/research/the-hat/native-03-files.json) is
14,485 bytes, SHA-256
`825eb76a391ed0f03a3d7c8b19fca871309c716fbb0f89b659afe195b89cb909`.
All 91 files total 21,779,310 bytes. Canonical sorted `{name,bytes,sha256}`
listing SHA-256 is
`a421461d4718ac2d52a1f83f130bde75ea495d4ada207bd826a6deb3821b83c4`.
The ordered 386-command JSON list SHA-256 is
`0018d3bd683b535f6d38063f230e51f6713adad36415b1ba2aa7879ddd962a7f`.
All raw input/sent/received intervals, original response extents and event
ordering are checked by the pinned frozen wire auditor without filtering.

The bootstrap's 2,708 loaded bytes match at SYS `$080D`. The independent
263-byte B0 output matches first-loaded `$0F00`, retaining the decoder's
explicit original-input tail distinction. Both B8/B9 ranges—36,864 bytes at
`$4000` and 6,144 at `$E000`—match all **43,008 bytes** at both natural
`b7-loaded` `$2043` and `b8-controller` `$8000`. Original B7's two-load,
flag-wait and JMP8000 bytes are also checked. No native target bytes seed an
independent source decoder.

| Boot capture | Actual PC | Clock | Raster / raw cycle |
| --- | ---: | ---: | ---: |
| sys | `$080D` | 11,336,568 | 233 / 33 |
| first-loaded | `$0F00` | 14,029,108 | 228 / 16 |
| b7-loaded | `$2043` | 124,735,855 | 294 / 13 |
| b8-controller | `$8000` | 127,840,084 | 271 / 43 |

## Four source-bound windows and motion generations

Every window uses these nine anchors: `$819D` before the current consumer;
`$81F3` after all eight current Y/pointer copies but before JSR `$E000`;
`$821C` before hardware-Y/timer-latch setup; `$8267` before LDA19/STA DC0F;
`$826C` immediately after that store; `$8516` parity selector; `$828C` CIA1
handler entry; `$8298` immediately after saved-SP TXS; then any PC at
explicit `RL == $0000`. There is no cycle constraint on that final stop.

Original source at `$819D` copies current shared Y to all eight VIC sprite-Y
registers. It then writes phase+32 through phase+39 to `$43F8..$43FF`.
Those stores precede the B9 coroutine call. The next B9 state therefore does
not describe the already-copied current Y/pointers. Cursor progression is
checked even where current and next byte pairs happen to be equal.

| Window | Current source cursor / pair | Next cursor / pair | Selector clock | Cutoff clock | Final line0 cycle |
| --- | --- | --- | ---: | ---: | ---: |
| even | 899 / `[14, 16]` | 900 / `[13, 16]` | 145,573,193 | 145,589,834 | 3 |
| odd | 942 / `[16, 24]` | 943 / `[16, 24]` | 146,418,527 | 146,435,040 | 1 |
| even-readback | 975 / `[23, 32]` | 976 / `[22, 32]` | 147,067,616 | 147,083,688 | 1 |
| odd-readback | 1015 / `[26, 40]` | 1016 / `[26, 40]` | 147,854,045 | 147,869,930 | 2 |

Original B8 code guards are checked in every window capture: the consumer
`$819D..$81DE`, latch setup `$821C..$8234`, timer start `$8267..$826C`,
handler `$828C..$8298`, and selector `$8516..$8520` (exclusive ends).
Selector-time code generation also compares all 17,060 independently sourced
raster bytes. Exactly four observed differences per selector remain explicit;
no dispatch operand is silently normalized or adopted as a predicted target.
Actual `$F200..$F7FF` table pages have per-page hashes and complete differences
from original data, rather than an assumed original generation.

Actual delay-helper bytes `$019F..$01AC` are
`60 20 9F 01 60 20 A0 01 60 20 A4 01 60`. Earlier first-loaded equality is
execution provenance, not independent initial-SFX decoding. The typed consumer
must prove any required value/carry semantics. Decimal flag clear is checked
at each selector. RAM artifacts and full VIC/CIA selector context remain
explicit declared entry inputs, separated from later store oracles.

All eight watches are armed before the first current-consumer continuation
and remain active through the following line0 RAM/VSF pair. They are deleted
only afterward. The five store ranges are `$D000..$D3FF`, `$DC00..$DC0F`,
`$DD00..$DD03`, `$43F8..$43FF` and `$47F8..$47FF`. Loads watch `$D012`,
its `$D112` mirror and calibration `$DC04`. This retains end-IRQ and successor
consumer activity after the cutoff. A later line0 RAM state can already belong
to a successor generation; its filename does not establish a completed image.

## Raw hooks, read inputs and the separate I/O oracle

| Window | Store hooks | Load hooks | Anchored raster samples | Per-hook I/O |
| --- | ---: | ---: | ---: | --- |
| even | 1,858 |31 |30 | r-only |
| odd | 1,840 |29 |28 | r-only |
| even-readback | 1,793 |30 |29 |64 visible bytes |
| odd-readback | 1,776 |27 |26 |64 visible bytes |

Every hook binds one active checkpoint generation, its exact attached command,
original instruction PC/bytes, monitored address, A/X/Y/SP, CPU clock, beam,
ports, and raw received offsets/block SHA-256. All raw trace headers across
all ordinary responses are accounted for. Hook contexts can be reported after
IRQ entry: PC is never required to equal instructionPC+length. For example,
the `$8269 STA $DC0F` hook is delivered in the later continuation response at
the same clock as the already-saved `$826C` boundary. Wire delivery order and
instruction clock remain separately available.

`raster-read-inputs.json` is a distinct directory-independent model-input
artifact. Its fields expose ordered `{instruction_PC,postPC,loaded_Y,clock,
beam,source_fallthrough_PC,block,sample,variant,read_address,rawref}` records.
All 113 observed raster samples bind the independent 106-site source anchor
file. They are selected by hook clock through the cutoff, including an equal-
cutoff-clock hook delivered after a saved boundary. Source fallthrough is
kept distinct from actual postPC. This does not claim observation of every
static anchor. Each field separately retains one `$DC04` calibration context;
SBC's post-register result is not relabelled an independently observed timer
read byte.

The input artifact contains no visible-I/O values or expected store/count
seeds. `trace-hits.json` is the separate oracle: consumers select operation
`store` and retain original PC/address/order/registers. Readback contexts stay
there as comparison data, never source-model input. Current table/helper
RAM is declared input; predicted control flow must not read native expected
store bytes or captured dispatch targets.

The original two windows use attached `r`. The later two use exactly
`r; bank io; m d000 d03f; bank ram`. Four 16-byte rows follow each hook,
covering 64 **CPU-visible** VIC bytes. All 3,626 composite contexts are parsed.
This literal whitelist restores the monitor RAM bank last. Side effects are
off; command separators are bound to retained official monitor lexer/parser
source and actual help/probe replies. No arbitrary command chain is accepted.

Visible I/O reflects readable/unused-bit behavior, not every stored raw bit.
The typed consumer may compare direct-store registers, meaningful RMW flags
and visible target state, then full stored endpoint bytes. A monitor hook is
not one physical bus write: dummy accesses do not trigger checkpoints here,
and NMOS RMW dummy/final writes are not inferred from hook count. All CIA1
and CIA2 store hooks remain even though the per-hook peek covers VIC only.

## Byte framing, ports, model and source-bound cutoff

Probe186 contains 432 original bytes; re-encoding its Unicode event text gives
512 bytes because its PETSCII column includes invalid UTF8. Every hook parser,
offset and block hash therefore uses original `received.bin` bytes decoded as
Latin1, one character per byte. The unchanged auditor still checks that raw
UTF8 replacement decode equals the retained event response. Unicode text is
never re-encoded as a substitute wire oracle.

The [bounded raw-parser diagnostic](../../build/research/the-hat/raster-case-analysis/raw-parser-probe-01/probe-report.json)
checks all four probe rows and exact CPU equality with following r187. Its
monitor-dot is `$D040` while CPU PC is `$828C`; a prompt address is not CPU
PC. The exact old interrupt helper remains pinned, with a declared raw-byte,
load-header and monitor-dot adapter. Final explicit register parsing stays
strict. Native03 has zero interruptions, so that fallback is not an observed
interruption result in this case.

No frozen reader is edited. The wire auditor's exact startup replacement
requires original B at both autostart and drive8. Full-pair adaptation removes
only the inherited fixed DDR=$2F constant and supports explicitly declared
interrupted boundaries; all natural stop, 65,536 physical-RAM, C64MEM latch/
DDR/readback, CPU/flags/clock, VIC beam and driven-bit checks remain. Port
latch, DDR, output and readback stay distinct under the pinned official
VICE3.10 schema. Every same-stop register/save/dump triple is checked without
intervening execution. All checkpoint conditions are parsed and checked,
including source cursor predicates and explicit hexadecimal raster values.

Actual queries establish Speed100, warp off at recorded instants,
VICIIBorderMode0 and VICIIModel1. The model query equals every serialized
snapshot model enum; PAL launch is not a 6569-subtype assumption. Dummy queries
literally report that checkpoints will not trigger on dummy accesses; no
`dummy on` changes observer coverage. Navigation mode changes and each query
remain in the journal. Normal viewport/draw-buffer row lifetime belongs to the
separate extended hardware reader; line0 alone does not prove 312 current rows.

Current copied Y values 14/ 16/23/26 select timer-latch source index Y−2 and
all match `$440F - 63*x`. Before-start and post-STA snapshots agree with that
latch. Cutoff CIA1 snapshots have enabled/pending TimerB; the guarded handler
reads `$DC0D`, returns A=$83 at the post-TXS observation, and clears pending/
IRQ state. Saved SP changes `$56→$59`; all 65,536 physical RAM bytes remain
equal across the 35-clock handler interval. Stacked interrupted PC and cutoff
clock are explicit per field. These observations do not independently prove
the complete timer deadline, instruction schedule or physical pixel scanout.

## Replay and preserved diagnostics

The producer is 57,507 bytes, SHA-256
`c73146a9d7b4b71b379a4b801c55bd27ef18282bd9fdd4280ae7eba2fc5c06be`.
The accepted receipt is 3,222,719 bytes, SHA-256
`44f64e23252ed23db79c7ac5a56ffa326ba0d9e863a85f6902aa628e84c92f24`.
Choose a fresh output directory:

```sh
rtk proxy python3 -B research/the-hat/raster_case.py --output build/research/the-hat/raster-case-analysis/fresh-replay
```

All five directory-independent outputs—`raster_case.checked.py`,
`trace-hits.json`, `capture-machine-context.json`, `raster-read-inputs.json`
and `raster-case-proof.json`—replay byte for byte: 19,391,728 bytes.
The [self-replay report](../../build/research/the-hat/raster-case-analysis/self-replay-check.json)
is 1,065 bytes, SHA-256
`42c5dd707307805069c0f158701a97249abf637c3379435e2592877d93e65321`.
Root independently reviewed the whole producer and
[replayed all five files](../../build/research/the-hat/raster-case-analysis/root-replay-check.json)
exactly; its 1,628-byte report SHA-256 is
`a6dfcc70bc0d6efd6c03c1fd89f548432ddc195e1fdb3c31745c441a518c8b87`.

All intermediate source/diagnostic/failure outputs remain. `source-01`
predates raw/composite support. Candidate01 counted setup descriptions as
hooks in a global membership check; candidate02 assumed a literal off-word
instead of the actual dummy-query sentence. Their checked sources and failure
receipts remain. Both were parser-preflight failures, not native execution,
source arithmetic, raster generation or renderer defects. The four PNGs are
cosmetic; neither they nor the line0 captures are an independent full-image
oracle. No new emulator, native process, socket, CPU interpreter, subprocess,
build or downloaded host program is started by this passive producer.
