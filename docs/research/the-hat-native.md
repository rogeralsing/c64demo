# The Hat: original boot, authentic side selection and B17 native custody

Research date: 8 November 2026. The closed original side-A `native-01`
case binds the DOS bootstrap, natural resident-loader execution, an explicit
original side-B attach after the source-bound `$F1` request, and B17's
closing-logo module. All 19 full RAM/VSF pairs pass the retained wire,
CPU/flags/clock, beam and CPU-port checks. The complete independently decoded
4,350-byte A00 and 26,402-byte B17 ranges match their natural entry captures.

This is the B17 giant-H/logo-carpet lane. It does **not** identify the named
all-border vertical UpScroll effect; the original-B native02 case is separate.
A numeric PC, file index or screenshot alone is not effect identity.

The [passive producer](../../research/the-hat/native_case.py) and its
[accepted receipt](../../build/research/the-hat/native-analysis/accepted-02/native-proof.json)
retain source generations, checkpoint generations, actual mode queries,
original inputs, all events/waits, two explicit inspection interrupts and
complete trace framing. They start no emulator, socket, CPU interpreter,
subprocess or build, and execute no downloaded host program.

## Original artifacts and closure

The original ZIP is 522,048 bytes, SHA-256
`ab15a74ba10a71264ccad74cd1d3a394b8f442a2acd33fd363b671bf293b081f`.
Its two disk members equal the retained release copies byte for byte:

| Disk | Bytes | SHA-256 |
| --- | ---: | --- |
| `the-hat-7a825b1-a.d64` | 174,848 | `ce09a1819a5dcec16342ebdc6515d20c377304db68e326ca2d86a499f0c9399d` |
| `the-hat-7a825b1-b.d64` | 174,848 | `1527038ebebca1a3d3d3379b91dd1a77dffb6d6d89a4dbfc32bf3f6908eb5b21` |

The [earlier release note](february-2026.md) owns acquisition/authorship;
[the disk note](the-hat-files.md) and [strict Dali note](the-hat-dali.md) own
the independent file readers. This proof pins the final Dali `accepted-03`
source/receipt and directory-independent binary outputs. Its models retain
zero unknown bytes and zero prior-memory reads; explicitly preserved original
packed-input tails remain distinct from newly computed bytes.

Root autostarted original side A as both autostart image and drive 8 under
PAL, true-drive 1541 emulation. The same owned PID 61991 and monitor endpoint
were retained until explicit close/reap at 21:05:58.595973 UTC. There are no
ordinary resends, restarts, cancelled commands or unresolved partial responses.
The journal contains 159 ordinary commands: 157 completed, two interrupted.
All three observation notices remain: sequences 76 (30.073 s), 100 (30.020 s)
and 129 (30.098 s); sequence100 later completed naturally, while76 and129 were
explicitly interrupted on their original handles.

The [closed manifest](../../build/research/the-hat/native-01-files.json) is
7,402 bytes, SHA-256
`d36260529112029981bf746c08a89ff1dca177ab46b1bd51a07957990ee372ac`.
Its 47 files total 327,423,480 bytes, with canonical sorted
`{name,bytes,sha256}` listing SHA-256
`fac04fa90dbb6f499afe9e405fc565e2c7b99cb299e9ead4f02fcdde27f5a2e6`.
The 109,932,772-byte events journal has SHA-256
`8def54892166949c6d1a2d2545410f5e5274cffefcf97113f65e33caa8b791f3`.
All input/sent/received byte intervals, response extents and journal timestamps
are checked without filtering. The compact ordered command-list SHA-256 is
`303864357f113a2de42f530cbf426c2b8c7a47ac2c26aa79de6de86d2760330e`.

## Source lineage and actual captured states

The original DOS-chain bootstrap is 2,710 bytes including load address,
SHA-256 `32189d1101a947c3ecc02ae3e9493756dbc063008582d09c62f939068f1049cd`.
All 2,708 payload bytes match `$0801..$1295` at the initial SYS stop. BASIC
line1602 contains SYS2061 (`$080D`). Its copy loop uses offsets `$EC..$01`:
source `$0821..$090C` to `$0001..$00EC`, inclusive. Offset0 is never copied;
CPU DDR `$00` is untouched there. Destination `$01` is a CPU-port write,
not an ordinary physical-RAM byte oracle. The file's literal `$090A`
`JMP $0A00` matches relocated `$00EA`.

The natural `$0A00` entry begins `A9 18 78 D8 A2 5F 9A 20 00 10`.
Those expanded SFX/installer bytes have original-execution provenance; this
proof does not independently decode the full initial SFX payload. In
particular, it retains the real LDA18 prefix and explicit TXS rather than
assuming a generic SEI entry or an SP+2 return across installation.

The observed original installer copies 508 bytes from `$12BA..$14B6` into
`$0200..$03FC` via two overlapping copies. Installed and first-load-entry
captures match that earlier natural source except exact flag `$020B:00→07`.
That difference is retained explicitly. Later loader self-modifications are
not broadly masked or called semantically proved. The 76 callback/control
bytes `$0B02..$0B4E` match relocated `$0160..$01AC` at first-load-entry and
first-loaded, after the installer has returned.

| Capture | Actual PC | Clock | Raster / raw cycle | SP |
| --- | ---: | ---: | ---: | ---: |
| sys | `$080D` | 11,363,840 | 42 / 26 | `$F6` |
| depacked | `$0A00` | 12,272,730 | 117 / 15 | `$FF` |
| installed | `$0A0A` | 13,602,048 | 1 / 33 | `$5F` |
| first-load-entry | `$02D2` | 13,621,989 | 6 / 3 | `$5D` |
| first-loaded | `$0F00` | 14,398,599 | 165 / 12 | `$5F` |
| part01-load-return | `$0F3E` | 14,421,964 | 224 / 4 | `$5F` |
| part01-entry | `$0900` | 14,421,967 | 224 / 7 | `$5F` |
| part02-load-return | `$0940` | 15,153,526 | 292 / 10 | `$5F` |
| part02-entry | `$4000` | 15,153,529 | 292 / 13 | `$5F` |
| side-b-request | `$020C` | 405,643,554 | 42 / 36 | `$5D` |
| side-select-return | `$8842` | 405,643,828 | 46 / 58 | `$5F` |
| side-b-file2-return | `$8856` | 409,316,362 | 309 / 7 | `$5F` |
| b17-controller | `$8000` | 587,004,264 | 272 / 0 | `$5F` |
| b17-init | `$803D` | 587,033,081 | 105 / 26 | `$5F` |
| b17-raster | `$2000` | 590,998,150 | 19 / 1 | `$59` |
| b17-midfield (interrupted, requested phase rejected) | `$8043` | 602,888,834 | 0 / 2 | `$5F` |
| b17-cutoff | `$831B` | 602,905,924 | 271 / 19 | `$56` |
| b17-stack-restored | `$831F` | 602,905,930 | 271 / 25 | `$59` |
| b17-complete | `$8040` | 602,907,732 | 300 / 0 | `$5F` |

Original source guards include A00's full loaded range, A00's `$0F3B`
loader continuation, A41's `$883D LDA #$F1` / `$883F JSR $020C`, the later
A41 selector2 call at `$8853`, B16's caller/wait/JMP8000 range, and the entire
B17 `$2000..$8722` range before initialization. Later B17 captures guard the
specific initializer, raster, cutoff and controller code ranges. The mutable
A41 flag `$885E` is explicitly outside its narrow opcode guard, rather than
silently repaired. The receipt lists every source/file offset, target range,
checked-byte count and hash. Native target bytes never seed an independent
file decoder.

The original bootstrap's pushed `$0E,$FF` provides saved continuation `$0F00`;
entry/return pairs confirm SP `$5D→$5F`. At the authentic side request, A=$F1
and the saved continuation is `$8842`. Sequence84 attaches the byte-identical
original B image to drive8 after the request snapshot, before SEC at `$020C`
executes. The separate `$8842` capture confirms return/SP+2. This is an
explicit legitimate media action, not an absence claim, visual disk prompt,
drive acknowledgement, RAM/PC patch or keyboard shortcut. No keyboard input
was issued. The later `$8856` return belongs to A41's selector2 call, not an
inferred fresh-B `$0F3E` controller.

## Full-state checks and narrow frozen-reader adapters

Every save follows explicit `r` and precedes adjacent VSF without execution
between them. All65,536 physical RAM bytes, MAINCPU registers/flags/clock,
VIC beam and serialized CPU-port fields must agree. The pinned official
VICE3.10 schema keeps latch, DDR, output and readback distinct; driven-bit
relations and unused-state checks remain. DDR is `$2F` at sys/depacked and
`$37` after the original installer writes `$00`. Read01 is `$37` initially
and at installed, then `$35` throughout the later captures.

No frozen source is edited. The wire auditor receives two exact in-memory
replacements: its manual-load startup assertion becomes original side-A
`-autostart` plus the same `-8` image; its one interrupted-suffix register
call binds the **final explicit interrupt-r frame**. Ordinary register
parsing remains strict. The complete retained suffix hash/extent and number
of intervening register rows/late trace headers are exposed. Matching final
prompt address, explicit row PC and final prompt are required.

The frozen full-pair function also receives two exact replacements: remove
only its inherited fixed DDR=$2F constant, and compare interrupted pairs to
the strictly parsed final interrupt-r row. Every natural-stop parser and
remaining snapshot/CPU/port/clock/beam assertion remains. Receipt hashes and
exact source replacements make both adaptations reviewable.

Checkpoint setup/delete/reuse generations, attached-r bindings, PC ranges,
and source-memory/register/raster/cycle predicates are checked against actual
pairs. An interrupted pair retains its unhit requested breakpoint and its
actual drained PC/beam; it cannot satisfy the intended natural predicate.
Warp-off/Speed100 are actual queries at sequences9/10,26/27,102/103 and158/159.
Sequence43 enabled warp for navigation and101 disabled it. Query instants do
not prove an unqueried interval's mode or delivered frame rate.

## Interrupts, complete watched-store history and bounded cutoff

Sequence76 is an explicit inspection interrupt after its notice. Its36
original `$02D2` execution hits remain; final drained context is `$2846`,
clock395,557,344, DDR=$37/read01=$35. This register-only boundary has no
RAM/VSF pair. Its following retained disassembly shows an effect-flag wait;
that register-only point has no whole-state oracle. Sequence79
continues the same case; it is not a resend or restart.

Sequence129's requested line130/cycle31..35 breakpoint was not reached as a
natural phase. The long watched response accumulated many fields and was
explicitly interrupted. The historical `b17-midfield` filenames are retained,
but their pair is actual `$8043`, line0/cycle2. The final interrupt drain
contains4,127 late trace headers after the interrupt request; they are parsed
in original order along with every earlier header. The initial strict-reader
failure is preserved in `native-analysis/diagnostic-01`, with its checked
source and explanation. It was a parser-boundary failure, not a native or
original-model failure.

| Response sequence | Exec hits | Store hits | Retention |
| --- | ---: | ---: | --- |
| 76 | 36 | 0 | every hit |
| 100 | 14 | 0 | every hit |
| 115 | 1 | 0 | every hit |
| 129 | 0 | 441,853 | all-hit aggregates/digests and first/last contexts |
| 135 | 0 | 721 | every hit |
| 147 | 0 | 9 | every hit |

All51 exec and442,583 store headers bind an active checkpoint generation,
its exact attached-r setup, raw received offsets/block hashes, instruction
bytes, CPU A/X/Y/SP, clock, beam and read ports. All recorded hit contexts
have DDR=$37/read01=$35. The exec hits match earlier original installed
resident bytes; all store-hit instruction bytes match independent B17 source.
The four store ranges are `$D000..$D02E`, `$DD00..$DD03`, `$47F8..$47FF` and
`$4BF8..$4BFF`. A trace row is a monitor event, not a one-to-one physical bus
write count, including RMW instructions. Exec contexts precede the instruction;
store contexts expose observed post-instruction registers. Neither proves a
whole call, physical device effect or committed pixels by itself.

The 106,044,846-character response129 stays compact: every hit is loop-checked
and contributes to canonical context and raw-framing SHA-256 digests; target,
instruction and source-reference counts plus first/last contexts are retained.
All other short windows serialize every hit in `trace-hits.json`. Complete
raw journals/wire files remain unfiltered and pinned. A separate consumer can
replay the precise framing from those offsets and declared digest schema.

The later fixed-PC cutoff `$831B` and post-TXS `$831F` are valid distinct
natural captures, six clocks apart. Guarded source is LDX `$831A` then TXS;
observed SP changes `$56→$59`, and X/saved `$831A` are `$59`. Physical RAM is
unchanged across those two observations. These facts are bounded source and
state context, not a whole interrupt/DMA/pixel proof. The later line300
capture supplies another actual boundary. Cosmetic PNGs remain separate from
committed display evidence; a dedicated closing-logo consumer owns further
source/helper interpretation.

## Passive replay and remaining limits

Choose a fresh output directory:

```sh
rtk proxy python3 -B research/the-hat/native_case.py --output build/research/the-hat/native-analysis/fresh-replay
```

The three directory-independent outputs are the checked producer,
`trace-hits.json`, and `native-proof.json`. The accepted receipt's `captures`
list exposes the established full-state schema for separate consumers.
Intermediate accepted01 and the diagnostic remain retained; final acceptance
adds explicit source-memory/register/raster/cycle predicate checks.

The final producer is 45,419 bytes, SHA-256
`a5b6c4c2eb6381bfc85e03cde3e5d6a127368fe599559195950d9599c44adbd9`.
The accepted receipt is 358,877 bytes, SHA-256
`726b76be1f9560ff22697129c1de788da82e95beac7a3993fdc4ba498082e141`.
A fresh [self-replay check](../../build/research/the-hat/native-analysis/self-replay-check.json)
compares all three outputs, 986,426 bytes, exactly; no field or path is normalized.
Root independently reviewed the complete producer and predicate changes, then
[replayed all three files](../../build/research/the-hat/native-analysis/root-replay-check.json)
with the same 986,426 bytes exactly. The 791-byte root report SHA-256 is
`ff93481aa0e28b9af8afae78ec3c42e8d2faed3fb9c7183e2c2303acb565591e`.

No original all-border UpScroll identity,
independent rendered pixels, complete field/animation, physical-hardware,
wall-time/FPS or optimization result follows from this custody proof. Browser
and video setup limits belong to their separate source/UI lane.
