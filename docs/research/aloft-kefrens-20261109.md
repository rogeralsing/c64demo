# Aloft part06: source-controlled bank slots and vertical raster programs

The observed full-screen part uses a table-patched raster program. Ten horizontal instruction slots in each active vertical segment select logical VIC banks through **CIA2's data-direction register $DD02**. A second set of tables supplies $D011 values as the segment's line counter decreases. The source contains separate character and bitmap stages. This gives a concrete mechanism behind the observed Kefrens-like display, while its named association with the author's side-2 flipped Kefrens or the separate three-layer pattern remains unproved.

The finite check reconstructs **ten active segments, 164 logical rows, 100 opcode cells, ten exits/counts and 24 LDY operand bytes** from the declared pre-copy software variables. All those cells match the captured program. It also checks every byte of two 2,048-byte phase-table families and the source-driven initialization. It does not run a CPU or advance the VIC.

Current acceptance is [accepted-02/kefrens-source-proof.json](../../build/research/aloft-20261109/kefrens-analysis/accepted-02/kefrens-source-proof.json), **8,686 bytes**, SHA-256 `26d3cf4b4100a34e75feadab827fb72fcd08676c0c16817f340454c64b6c92d1`. The [producer](../../research/aloft-20261109/kefrens.py) is **18,508 bytes**, SHA-256 `76be150e50ad39f987af10adbf1b158948084a974a4f58668045b80147c3f44f`.

## Source generations and what the inputs mean

The source inputs are RAM observed during natural execution of the original side-one disk. There is no independent compressed-disk decode of this part in this lane. The [closed original native case](aloft-native-20261109.md) supplies the separate boot/wire/checkpoint and process custody. The [part-localization note](aloft-parts-20261109.md) owns wrapper counters, load handshakes and the later 8,190-byte relocation; they are not recomputed here.

| Declared source state | Observed PC | Absolute clock | Role |
|---|---:|---:|---|
| part06-entry | $0890 | 99,375,303 | Before the wrapper's `JSR $4800`; observed counter $19. |
| part06-initialized | $0893 | 99,495,185 | After that initializer returns. |
| part06-precopy | $08A4 | 109,545,058 | After three subsequent loads, counter $1C, before wrapper relocation. |

Every 65,536-byte RAM export equals its VSF RAM module. The checker independently checks the CPU PC/clock, binary arithmetic flag, and PAL beam correspondence. It uses the frozen snapshot parser and a frozen static instruction decoder. Neither executes original instructions. Physical RAM bytes at addresses 0/1 are kept distinct from the CPU-port latch/DDR stored in the VSF: the observed port latch is $35 and DDR $2F.

The byte source for static listings is the **earliest part06-entry generation**. Later snapshots supply explicit state variables and comparison targets. The region $5166–$5265 is table data, not a list of instructions. [source-contract.json](../../build/research/aloft-20261109/kefrens-analysis/accepted-02/source-contract.json) contains the guarded instruction sites and static reachable listing, with data domains separated.

## Initial setup and the fixed helper

Source $4800 initializes all four 1,024-byte screen-map regions at $0400, $4400, $8400 and $C400 to **$D6**. Its I/O-mapped writes fill all 1,024 ColorRAM cells with **5**. Its self-modified page-clear loop zeros **$6000–$7FFF, all 8,192 bytes**. Those predictions match the initialized RAM and actual device ColorRAM.

The initializer sets the shared colors through $D021=0, $D022=6 and $D023=1, writes $D016/$D018=$18, and initializes CIA2 DDRA to $3D. It installs the $4FFA IRQ route and raster compare 2. It also writes $D011=$7E; this boundary value must not be mistaken for the later active-row mode.

The helper at **$4AA0 is sixteen NOPs followed by RTS**, byte-identical at entry, after initialization and at pre-copy. There is no hidden renderer recovered inside that helper. Drawing or decoding the later data at $6000 is outside this source checker: the wrapper's later loader calls populate that region, as the separate localization proof records. The initial zero buffer and later loaded asset are different generations.

## IRQ and $D011 source structure

The $4FFA IRQ saves A/X/Y, sets the next IRQ to **$489C at raster compare $2F (47)**, acknowledges the VIC interrupt and calls an external route through $5022 → $0800. That callback is outside this model.

At $489C the program saves A/X/Y into zero page and derives a self-modified branch displacement from a **live CIA1 Timer-B low-byte read at $DC06**. No exact read value or jitter delay is inferred from a later snapshot. A repeated prelude then contains **26 identical 18-byte blocks**, each calling $4AA0, comparing Y with zero-page $10, sampling $D012, forming a $D011 value, storing it and incrementing Y. Its data expression is:

```text
$D011 = $70 | ((sampled_D012 - 1 + (Y >= ZP[$10])) & 7)
```

The source's live raster reads remain unbound external inputs. The motion routine at $5137 updates the $10 threshold from the $5166 table and patches the low-byte entry into the delay block at $4B00 from the separate $51E6 table. This source shape does not establish a chronological raster trace, hardware cycle budget, or the exact time at which each line is displayed.

The later raster body requests rows through $D011 phase tables:

| Table family | All-byte formula, page 0…7 / index 0…255 | Control bits |
|---|---|---|
| $8A00–$91FF | `$18 + ((page - index) & 7)` | ECM=0, BMM=0, DEN=1, 25-row bit set: character controls. |
| $5700–$5EFF | `$38 + ((page - index) & 7)` | ECM=0, BMM=1, DEN=1, 25-row bit set: bitmap controls. |

**All 4,096 table bytes** match these formulas in the earlier source and the pre-copy snapshot. With the separately observed $D016 multicolor bit, they describe the two source stages. The early stage at $5029 writes **$D018=$14**; the entry variables select the $8A family. The transition at $5078 writes **$D018=$18** and changes the phase-page base at $3A to **$57**. At pre-copy that base is $57.

The $D011 boundary values $7E/$76/$70 have both ECM and BMM bits set. Ordinary static multicolor-bitmap decoding cannot be assumed for the entire frame from those stopped register values. This checker derives the phase words and source consumers, without resolving VIC pipelines, badlines or pixels.

## Twelve templates, ten bank slots each

There are twelve 64-byte templates at **$4C00 + 64×i**, `i=0…11`. Each starts with a NOP and `LDY absolute`; its low address byte serves as a decreasing segment count. It then has **ten three-byte absolute slots targeting $DD02**, followed by `STY $D011`, a decrement of its own LDY low-byte operand, and a branch back. The template's exit either jumps into the next template or reads an operand as BIT and falls through to a return sequence.

The entry source initially contains `BIT $DD02` in every slot. The patcher at $5266 changes their **opcodes**, while their $DD02 operands remain fixed. The raster prefix at $4B53 supplies **X=$3E and A=$3D**. Therefore the source-selected slot values are:

| Opcode | Source operation | Requested DDRA | Logical PA low pins, PRA=$F8 | Requested VIC bank |
|---|---|---:|---:|---:|
| $8D | STA, A | $3D | %10 | $4000 |
| $8E | STX, X | $3E | %01 | $8000 |
| $8F | SAX, A AND X | $3C | %11 | $0000 |

This changes the **direction register**, with the captured PRA latch remaining $F8. The primary VICE sources independently bind SAX to `A & X`, CIA effective pins to `PRA | ~DDRA`, and the logical bank request to the inverted low two pins. [primary-source-anchors.json](../../build/research/aloft-20261109/kefrens-analysis/accepted-02/primary-source-anchors.json) preserves exact archive-member hashes and line-numbered fragments.

The addresses implied by the source are logical pointers. For D018=$14, the screen offset is $0400 and charset offset $1000; for D018=$18, the screen offset is $0400 and bitmap offset $2000. Character-ROM visibility, fetch caches and timed bank transitions are not resolved by these address formulas.

## Finite opcode patch reconstruction

$5266 copies seven motion/state bytes from **$46–$4C into $3F–$45**. Two countdowns partition the remaining logical rows using periods **35 and 45**. At each boundary, one or both pattern indices advance. The primary index selects a ten-byte word in **$8850–$892B**; the secondary selects one in **$892C–$895D**. For each horizontal slot, a nonzero primary byte is used; otherwise the secondary byte supplies the opcode. This is an explicit source priority rule, with byte values selecting STA/STX/SAX.

The pre-copy mathematical inputs at $46–$4C are **`04 10 11 03 5C 00 4C`**: countdowns 4/16, indices 17/3, initial clipping accumulator 92, and first template $4C00. They are declared observed software state, not independently predicted motion. The finite merge produces:

```text
4, 12, 23, 22, 13, 32, 3, 35, 7, 13
```

Those ten segment lengths sum to **164 = 256−92**. The last segment changes its exit from JMP ($4C) to BIT ($2C). All **100 opcode cells**, ten exit opcodes and ten count cells match the pre-copy program exactly. The remaining two templates are unused by this descriptor and retain stale values; they are not included as additional rendered rows.

The tail beginning $4F17 computes phase pages from the twelve count variables:

```text
phase starts at 6
phase = (phase + count[i]) & 7
LDY_address[i] = ((ZP[$3A] + phase) << 8) | count[i]
```

All **24 low/high LDY operand bytes** match. Counts in the two inactive templates remain explicitly declared stale inputs. [finite-patch-comparison.json](../../build/research/aloft-20261109/kefrens-analysis/accepted-02/finite-patch-comparison.json) records every predicted active word, length, exit and phase operand. This is a finite consistency result from source and declared state, not a CPU execution trace or a proof of motion across arbitrary frames.

## GLUE is a required future composition dependency

The snapshots preserve **GLUE module 1.0, type 1**: raw entry `01 00 00`, initialized `01 01 00`, and pre-copy `01 00 00`. These are type / previous logical bank / alarm-active bytes, not samples of every bank transition during the beam.

Pinned `c64gluelogic.c:86–107` has type-1 paths that can temporarily select **bank 3** for certain logical bank-1/bank-2 transitions, or delay a DDR-driven transition. Thus the table above specifies three **logical bank requests**; it does not prove that only three physical fetch banks participate. Future physical-fetch composition must include that GLUE state/path, the live source writes, and VIC pipeline/fetch state. The current receipt intentionally does not evaluate those transitions or predict their pixels.

This GLUE detail was added after root had already reviewed/replayed accepted-01. The coordinated current result is **accepted-02** and current source `76be150e…`; accepted-01, its checked source `1535a006…`, self replay and root report remain historical, unchanged evidence. Their earlier GLUE exclusion was already explicit. No historical output was overwritten or relabelled as current acceptance.

## Validation and continuation

Fresh self replay matched **all seven current outputs / 234,285 bytes exactly**. [self-replay-check-02.json](../../build/research/aloft-20261109/kefrens-analysis/self-replay-check-02.json) is 1,222 bytes, SHA-256 `b5a55aa305b8adb39c8c8bf8198abfcc2cd47181c085a788ff3665391e5c015d`.

Root reviewed the original source and the added GLUE delta/primary anchors, then ran a fresh independent replay of accepted-02. [root-replay-check-02.json](../../build/research/aloft-20261109/kefrens-analysis/root-replay-check-02.json), **2,155 bytes**, SHA-256 `92f34ec24fd6c83381b6cdfe06c7a438763b1c79dc122b6819ac2aef569c18d9`, is the current root authority. All seven outputs match. No further source expansion followed that coordinated review.

Passive replay uses a new output directory:

```sh
rtk proxy python3 -B research/aloft-20261109/kefrens.py \
  --output build/research/aloft-20261109/kefrens-analysis/replay-NEW
```

The next meaningful boundary is original-resource decoding and a source-bound raster/write history with live read inputs, followed by GLUE/VIC fetch composition if pixels are to be predicted. The [native custody](aloft-native-20261109.md), [wrapper/relocation](aloft-parts-20261109.md) and this source study remain separate. No displayed-pixel reconstruction, cycle/IRQ deadline, whole animation/FPS, named three-layer-pattern or side-2 joystick attribution, physical-hardware result, optimization or product change follows from this receipt alone.
