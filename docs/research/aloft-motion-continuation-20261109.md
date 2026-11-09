# Aloft motion and Perpetual Fragility: continuation

Research date: 9 November 2026. The preceding goal turn made verified progress:
it reconstructed two Aloft display bodies and independently recovered the
later body's 8,000 glyph bytes from native pixels. This continuation tackles
the earlier boundary: how original motion code chooses the 200 drawing calls.
The broad demo-research objective remains active.

## What the original motion code does

The [table study](aloft-motion-tables-20261109.md) starts from the independently
decoded original bundle, including its known and rewrite masks. It recovers
five loaded 512-byte wave assets, four generated 1,801-byte programs, the
601-byte dispatcher initializer, palette assets and controller descriptors.
Each wave asset contains two identical 256-byte periods. Their original
analytic construction is unknown; no fitted sine curve replaces their bytes.

Each generated program repeats this source-defined macro 200 times:

```asm
    lda waveA + operandA, x
    adc waveB + operandB, y
    sta $0502 + 3 * line
```

The initializer advances the low source operands modulo 256. Runtime indexed
reads can cross a page into the duplicate period. The destination is the high
byte of one JSR in a 200-call display list. Its low byte remains `$00`, except
every eighth call uses `$23` for the row-ending variant. The selected routine
comes from the independently reconstructed OR/AND mask library.

There is no CLC between these additions. Native entry carry must therefore be
an input. Original asset bounds prove every sum, including carry 1, stays
below 256. Consequently the incoming carry affects only the first call's high
byte; the remaining 199 additions receive carry 0. Decimal mode must be clear.
This is a bounded source proof, not an assumption that music leaves flags alone.

The first controller starts with X=`$07`, Y=`$5B`, then changes its embedded
phase values by −3 and +2. Three later controllers use different source-operand
steps, phase changes and fade thresholds. The complete descriptors and original
byte guards live in the table proof. Native observations in this pass cover
only two invocations of the first controller.

## Observation boundaries

The [new native case](aloft-motion-native-20261109.md) uses the original D64,
autostart, a true 1541 and default PAL x64SC. Root alone controlled the process.
Eight natural RAM/VSF pairs, all 84 completed responses and both 200-store
traces remain retained. There were no restores, restarts, disk changes,
interrupts, timeouts or RAM/PC patches. Warp was off for motion observations.
The same owner handle reached terminal exit 0; VICE was closed and reaped.

| Boundary | First invocation | Invocation index 64 |
| --- | --- | --- |
| Before JSR at `$F133` | X=`$07`, Y=`$5B`, C=1, D=0 | X=`$47`, Y=`$DB`, C=0, D=0 |
| Return at `$F136` | Before phase updates | Before phase updates |
| Wrapper return at `$F11D` | Before INC `$05` | Before INC `$05` |

The later stop follows a declared checkpoint ignore count of 63 after the
first invocation. It was not selected by searching for a matching output.
The first input carry differs from the later carry. Both are genuine CPU
states observed after music, rather than values inferred from target lists.

The [typed motion model](aloft-motion-20261109.md) separates the original
wave/program/dispatcher scaffold and genuine pre-call scalar inputs from late
native output oracles. Both complete predictions are written before parsing
the native receipt's output-bearing JSON or opening the oracle export. Prior
runtime target high bytes are never prediction inputs. All **400 ordered STA
values and per-term ADC flags** match. Both **601-byte lists** and natural
return A/X/Y/PC/SP/status match. The wrapper check covers source-defined phase
X/Y updates, unchanged counters and the generated list; palette fades and full
wrapper CPU behavior remain unmodeled.

The source macros cost 2,412 core cycles including JSR/RTS, plus indexed-read
page crossings. The first case has 6 LDA and 66 ADC crossings, giving **2,484
cycles**. The later case has 70 LDA and 162 ADC crossings, giving **2,644
cycles**. Both equal their observed call intervals. This is a bounded interval
comparison, not a general stall scheduler, delivered frame rate or whole-frame
budget. The native and model notes own exact receipts, independent replay
commands and their limitations.

There is a one-field pipeline. The current dispatcher draws first, then music
runs, then the controller constructs the next display list and advances its
phase operands. A phase value visible during a drawing call describes the
upcoming motion computation. It must not be attached retrospectively to the
already displayed list. In particular, earlier field-64 captures with phase
`$47/$DB` used the previously computed list, not this phase's following output.
The new phase's following list has 74 distinct targets; the earlier captured
display list has 69. Those counts describe different pipeline generations.

## Independent primary-source work

The [primary follow-up](aloft-motion-primary-20261109.md) retains the bounded
creator/release search, including rejected HTTP responses. No matching Aloft
author explanation or human name for the reconstructed striped scene was
recovered. The identical CSDB/Pouët release screenshots show another scene.
This negative result concerns the retained routes, not every source on the web.
The refreshed Lunatico rain material was already documented and is not counted
as a new mechanism.

The concrete new primary result concerns Linus Åkesson's **Perpetual Fragility**.
Its retained original 9,469-byte PRG contains a self-extracting Exomizer-family
stream. A typed format decoder, bound to original loader bytes and Magnus
Lind's official sources, reconstructs 9,165 packed bytes and consumes them
through the format's own end marker. It predicts **17,403 known payload bytes
at `$0801..$4BFB`**, containing 5,112 literal bytes and 12,291 match bytes.
The resulting PRG is 17,405 bytes, SHA-256
`4280209180aba0847703b7a1d6e0682df372a927cbcef25656ae04eee53a4863`.

The admitted format uses MSB-first bits, raw-byte extension, 52 coding entries
and three offset tables. It has neither an implicit first literal nor reused
offsets. Exact original host packer version remains unknown. No downloaded
host executable, native emulator or CPU interpreter was run for this decode.
All match reads have earlier reconstructed provenance, and no output overwrites
unread compressed input. Root's independent replay matches all 11 files /
1,207,395 bytes. This is a payload prediction, not native payload or graphics
acceptance. The original loader's initial stack precondition remains explicit.

## Picking up the work

1. Read the current [checkpoint](CHECKPOINT.md) and run its latest read-only
   inventory audit. Never use a previous publisher's `--write` as a check.
2. Start with the four motion/table/native/primary studies linked above. Their
   receipts bind source, inputs, comparison outputs and independent replays.
   Preserve both closed native cases and every failed candidate.
3. For Aloft, join source-predicted motion lists to the accepted cell, glyph,
   fetch and display models. Keep the one-field pipeline explicit. A future
   native comparison needs the matching following display interval and genuine
   initial state, rather than a conveniently similar old viewport.
4. If extending controller coverage, retain genuine X/Y/C/D and controller
   identity before each selected call. The three later programs have source
   reconstruction, not native runtime acceptance. Do not invent music carry.
5. For Perpetual Fragility, inspect the recovered payload and the author's
   WIZ explanation together. Recover the real coordinate/layout implementation.
   A native comparison must first validate the unpacked payload against the
   original PRG at its natural exit. A synthetic WIZ fixture is not evidence
   that the released demo uses that implementation.
6. Keep the wider backlog: the separately named moving layered scene, Aloft
   side-two joystick/flipped Kefrens, Hat composition and unfinished Lab/EOD
   cases. The Lab's colored ball remains a distinct prepared-edge bitmap and
   XOR-fill result; this Aloft glyph engine does not change that conclusion.

For that Perpetual Fragility comparison, use a new root-owned case and the
original packed PRG. The guarded loader ends with JMP `$080D`; the independently
predicted payload there starts `A9 7F 8D 0D DC 78`, while the packed entry starts
`A0 35 BA`. Bind the natural exit to the predicted byte guard, retain a complete
RAM/VSF pair and compare every one of the 17,403 known payload bytes. Keep the
earlier packed SYS entry and its stack state as separate observations. Do not
start the decoded PRG and call that validation of the original loader, and do
not put native output bytes back into the format decoder.

Partial raster 47, whole-field prefix/tail, complete animation cadence, all
poses, real-silicon equivalence and human visual naming remain separate work.
Do not mark the broad goal complete on this pass.

All 11,203 preceding artifact identities and 273 receipt rows remain immutable.
The five preceding indexes were archived under
`build/research/handoff-20261109/prior-11203/` before this pass. New work uses
only the new motion source/build scopes, new detailed notes and the five
mutable current indexes. The current handoff records final union counts and
the exact read-only integrity command.

## Follow-up prompt

> Continue the active objective: scan the web, read the blogs and articles,
> find demos that push the boundaries, reverse engineer/decompile, understand
> and document every finding. Work in `~/git/asynkron/c64demo`. Read the latest
> checkpoint and this continuation, then run the current read-only inventory
> audit. Preserve every earlier artifact and receipt. Aloft's four motion
> programs and assets are source-reconstructed; only two first-controller
> calls have genuine native inputs and output comparisons. Join predicted
> call lists to the following display interval without confusing the one-field
> phase pipeline. Separately, Perpetual Fragility's typed Exomizer-format decode
> predicts 17,403 payload bytes; verify them at the original packed PRG's natural
> `$080D` exit before claiming released native behavior. Recover the actual WIZ
> implementation, not a synthetic substitute. Keep whole-field edges, later
> controllers, animation cadence, human scene naming and the wider demo backlog
> explicit. Root alone controls native processes and sockets. Never overwrite
> a closed case or use a publisher's `--write` as a validation command.
