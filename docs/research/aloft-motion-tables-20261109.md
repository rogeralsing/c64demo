# Aloft: original motion assets, initializer and phase inputs

The original part08 motion input is now separated into **2,560 source-loaded asset bytes**, four runtime-generated **200-term programs**, the initial 200-call dispatcher, and mutable phase/counter inputs. A new finite initializer model predicts all **7,204 program bytes**, 601 dispatcher bytes, 256 bit-reversal bytes and 40 final template bytes before opening native RAM. Four retained natural contexts match the declared predictions. This establishes table/code generation and input identities; it does not evaluate a motion frame or infer an analytic sine formula, physical angles, a named scene or FPS.

The new producer is [motion_tables.py](../../research/aloft-motion-20261109/motion_tables.py). The [accepted receipt](../../build/research/aloft-motion-20261109/table-analysis/accepted-01/motion-table-proof.json) pins the original source generation, all guards, outputs and late comparisons. Its [minimal table ABI](../../build/research/aloft-motion-20261109/table-analysis/accepted-01/table-abi.json) is the downstream interface: exact binary asset/program references, addresses, source templates, operand steps, phase seeds, counter order and explicit carry requirements. The successful second candidate, accepted output and [self replay](../../build/research/aloft-motion-20261109/table-analysis/agent-replay-check.json) match **19 files / 104,372 bytes** exactly. All earlier candidates and the failed read-only listing probe remain in the new scope.

An independent [root source review and replay](../../build/research/aloft-motion-20261109/table-analysis/root-replay-check.json) repeats all 19 outputs / 104,372 bytes exactly. This verifies the bounded source initializer, ABI and declared late comparisons; it does not supply the separately required pre-motion carry or execute the generated programs.

## Original assets are distinct from generated tables

The input is the independently decoded [generation31 memory](../../build/research/aloft-decode-20261109/color-analysis/accepted-01/bundle031-memory.bin), bound by the frozen [ColorRAM-aware stream receipt](../../build/research/aloft-decode-20261109/color-analysis/accepted-01/color-stream-proof.json). Known and delta-write masks prove that every motion asset byte below is known and actually rewritten by this completed source generation. Generation31 is a decoded generation index, not an inferred effect ID or the wrapper's `$088D` value.

| Original asset | Size | Byte range | Repetition |
|---|---:|---:|---|
| `$E600..$E7FF` | 512 | 16–53 | Two identical 256-byte periods |
| `$E800..$E9FF` | 512 | 17–53 | Two identical 256-byte periods |
| `$EA00..$EBFF` | 512 | 16–91 | Two identical 256-byte periods |
| `$EC00..$EDFF` | 512 | 16–92 | Two identical 256-byte periods |
| `$EE00..$EFFF` | 512 | 16–92 | Two identical 256-byte periods |

These values are original compressed-stream assets. No runtime initializer in the admitted source synthesizes them from trigonometry. Their duplicate periods support a direct indexed lookup spanning offsets 0–510: an eight-bit operand offset plus eight-bit X/Y can cross into the second copy. The ABI retains the actual 512 bytes instead of replacing them with a guessed sine curve or a modulo rule.

The separate `$0400..$04FF` lookup **is** runtime generated. `$F676..$F685` inserts eight fresh source bits into each old byte with `LSR A / ROL $0400,X`; all previous bits are displaced. The model emits `reverse_bits8(index)` for every index. This agrees with the earlier [cell-generator result](../../build/research/aloft-cells-20261109/cell-analysis/accepted-02/cell-generator-proof.json), but does not consume its expected lookup bytes as an input.

The original palette region `$F2C2..$F43C` is retained and checked separately, all 379 bytes. The controller ABI names the actual palette bases and destination register groups. This blob includes a leading 16-byte table not referenced by the four admitted controllers and unused padding at the end of the first three sixteen-byte vectors; it is not a claim that every retained palette byte is read during an accepted frame.

## Typed initializer emissions

Source `$F000..$F02A` calls `$F43D`, `$F47C`, `$F64E`, `$F686`, then jumps to `$F676`. The existing [cell-generator note](aloft-cells-20261109.md) owns `$F47C`'s cell pages. This new model owns only the dispatcher/motion initializer and its table input contract; it does not duplicate runtime evaluation of the generated programs.

`$F64E` copies the 25-byte template `$F817..$F82F` twenty-five times at a 24-byte stride, each copy descending through offsets24..0. Adjacent copies overwrite the preceding RTS. The result is exactly 200 `JSR`s followed by one final RTS at `$0758`, or601 bytes beginning at `$0500`. Each group of eight starts with seven `$2000` calls and one `$2023` call. Runtime motion writes only the 200 high-byte locations `$0502+3*i`; it can preserve the opcode/low-byte/RTS skeleton while selecting different generated pages.

`$F686` generates the following four programs from original ten-byte templates. Every term has `LDA absolute,X; ADC absolute,Y; STA absolute`; its last RTS is overwritten by the next term. Two hundred descending ten-byte copies at a nine-byte stride therefore produce **1,801 bytes per program**, including its final RTS. The source performs 8,000 logical copy stores to 7,204 distinct addresses, with 796 overwritten RTS bytes.

| Program | Original template | LDA asset | ADC asset | Per-term low-operand steps |
|---|---|---|---|---|
| `$C000..$C708` | `$F830` | `$E600` | `$E800` | −2, +4 |
| `$C800..$CF08` | `$F83A` | `$EA00` | `$EC00` | −1, +2 |
| `$D000..$D708` | `$F844` | `$EA00` | `$EC00` | −129, +2 |
| `$D800..$DF08` | `$F84E` | `$EA00` | `$EE00` | −85, +1 |

The low operand updates wrap modulo256 without changing the source high byte. The destination starts at `$0502` and advances by three with carry, selecting the next dispatcher high byte. The final updated source templates describe an additional *unemitted* term; they are not silently copied as a 201st record. Binary arithmetic is an explicit initializer precondition. Original entry and all four comparison boundaries have D clear. The native entry's CPU port is `$35`; source `$F704 DEC $01` hides I/O before the two `$D000/$D800` program emissions, and `$F784 INC $01` restores it. The predictions describe underlying RAM program bytes, distinct from device ColorRAM.

The program ABI deliberately supplies **no incoming ADC carry default**. There is no CLC before the generated program call, and its ADC carry can propagate between records. The exact music/caller return carry must be independently bound by the runtime motion consumer; neither a target list nor a table value may choose it. The initializer predicts generated code bytes, not the results of executing that code.

## Source phase seeds and mutable counters

The four controllers use self-modified immediate operands as byte phase inputs. Their source seeds and steps are:

| Entry → program | Initial X / Y | Per-call X / Y update | Fade-out threshold |
|---|---|---|---|
| `$F12F → $C000` | `$07 / $5B` | −3 / +2 | `$05 >= $62` |
| `$F18D → $C800` | `$15 / $23` | +2 / −1 | `$05 >= $D2` |
| `$F1E9 → $D000` | `$2D / $0F` | −2 / −1 | `$06 < 2` and `$05 >= $42` |
| `$F259 → $D800` | `$34 / $57` | +1 / +1 | `$06 < 2` and `$05 >= $90` |

The phase seeds, their operand addresses, palette bases and fade counters are original source bytes. They remain separate from their captured mutable values. Initial fade indices are 14. The first three controllers eventually patch the call operand at `$F11B/$F11C` to the next controller. The last controller is different: at fade-out X==0 it stores 1 to `$088F`, requesting continuation by the wrapper. Its guard is **BNE, not BMI**. There is no invented negative-index stop if the wrapper continues beyond that request.

`$F043..$F04A` initializes `$05=0`, `$06=2` **after** the body-entry boundary `$F02B`. Later IRQ source order is: reset the 40 glyph sinks, call `$0800`, invoke the current motion controller via `$F11A`, then `INC $05`; if that wraps to zero, `DEC $06`. These are byte-counter and phase-index rules. No physical rotation angle or universal frame count is inferred from them. The `$FE/$FF → $FA/$FB` clock redirection at startup remains a distinct source operation rather than being conflated with `$05/$06` motion state.

## Late native checks and remaining input boundary

The producer first writes all asset, generated-program, dispatcher, lookup, final-template and ABI outputs. It then opens RAM only for the following already accepted natural captures. Each RAM export is independently checked against all 65,536 physical snapshot bytes, plus CPU registers, ports, clock and beam. Full wire/boot/checkpoint custody remains delegated to the pinned [original native case](../../build/research/aloft-20261109/native-analysis/accepted-01/native-proof.json) and [cell-execution native case](../../build/research/aloft-execution-20261109/native-analysis/accepted-02/native-proof.json).

| Context | Actual boundary | `$05 / $06` | Active controller | Phase0 X / Y |
|---|---|---|---|---|
| Original body | `$F02B`, clock130,163,026 | `$7B / $00` | `$F12F` | `$07 / $5B` |
| Original pre-IRQ | `$F080`, clock131,462,237 | `$40 / $02` | `$F12F` | `$47 / $DB` |
| First genuine pre0500 | `$0500`, clock130,204,329 | `$00 / $02` | `$F12F` | `$07 / $5B` |
| Later genuine pre0500 | `$0500`, clock131,462,313 | `$40 / $02` | `$F12F` | `$47 / $DB` |

All four contexts match all 2,560 original motion asset bytes, 7,204 generated program bytes, 379 palette bytes, 256 reversal bytes and 40 final template bytes. The original body and first pre0500 also match the full 601-byte initial dispatcher. At the two already changed dispatchers, the model checks only the 401 opcode/low-byte/RTS bytes; their 200 mutable high bytes are reserved for the independent runtime prediction. The original body also retains all original phase operand seeds. The [mutable observations](../../build/research/aloft-motion-20261109/table-analysis/accepted-01/native-mutable-observations.json) are emitted only after prediction and never feed the table initializer.

The body counter `$7B/$00` is a concrete counterexample to treating the pre-`$F02B` state as an initialized motion frame. The first pre0500 does show `$00/$02`, after the setup. Later values are observations of changed state, not substituted initial conditions or target bytes used to construct the tables.

The next precise boundary is genuine input immediately before the selected generated motion program, including binary-mode and incoming-carry context after `$0800` returns, followed by the resulting 200 dispatcher high bytes as an oracle. Runtime phase evolution, the generated ADC chains and future target sequences belong to the independent motion lane. This table proof does not infer them from the observed target list. It also makes no new native capture, CPU-interpreter, build, downloaded-host execution, pixel, full-animation or named layered-scene claim.

Replay in a fresh directory:

```sh
rtk proxy python3 -B research/aloft-motion-20261109/motion_tables.py --output build/research/aloft-motion-20261109/table-analysis/NEW-replay
```

The output directory must not exist. The prior 11,203-artifact/273-receipt baseline and all old source/proof paths remain unchanged.
