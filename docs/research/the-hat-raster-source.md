# The Hat upscroll: complete source raster blocks

Research date: 8 November 2026. This pass recovers the complete normal-flow
structure and guarded value operations of **both B8 raster variants**,
`$8516..$C7B9`. It covers **17,060 original bytes, 6,525 instruction sites
and 1,979 higher-level macros**, including every source register/pointer
write. It does not execute a CPU, consume expected native write values or
claim complete displayed pixels.

The new [producer](../../research/the-hat/raster_source.py) consumes the
frozen B8/B9 decoded files from the original release. The earlier
[source note](the-hat-upscroll.md) and [native custody](the-hat-upscroll-native.md)
remain unchanged. Their recorded even and odd program intervals are the
runtime target; this pass supplies complete source descriptors needed to
predict their register writes from independently observed live reads.

## Source custody and full coverage

The exact input files are:

| File | Inclusive decoded range | Bytes | SHA-256 |
|---|---|---:|---|
| B8 | $4000–$CFFF | 36,864 | `5c8150c48068c62f8a77d8c97b18de33360dcb03046e0f5e9ffcb01ca6704ba6` |
| B9 | $E000–$F7FF | 6,144 | `9d0f80b7bc33c981a7befe2274ac98f30bf00c77916702016588b5e028e9a578` |

The [source-classification receipt](../../build/research/the-hat/dali-analysis/neighbor-probe-02/accepted-01/source-classification.json)
binds these files to the original disk extraction and strict Dali decode.
The new parser recognizes only the **21 opcode encodings actually present
in the bounded raster region**. It decodes source once, groups guarded
instruction idioms, and never fetches/executes instructions against runtime
memory. Ten selector bytes, two prologues and fifteen loop blocks cover
the region exactly, without overlaps or holes.

An independent inventory directly from decoded source is compared with
the descriptor writes: **all 4,234 STA/STX/STY/SAX/INC/DEC instruction
sites are covered**. These are static sites, not executed write counts or
NMOS bus-write counts. Every macro retains its original byte span and
source PCs, including padding and external delay calls.

The primary outputs are
[raster-blocks.json](../../build/research/the-hat/raster-source-analysis/accepted-02/raster-blocks.json),
[raster-graph.json](../../build/research/the-hat/raster-source-analysis/accepted-02/raster-graph.json)
and [raster-read-anchors.json](../../build/research/the-hat/raster-source-analysis/accepted-02/raster-read-anchors.json).

## The branch selects different complete programs

The original selector is:

```text
$8516  LDA $43F8
$8519  AND #$08
$851B  BEQ $8520
$851D  JMP $A8AA
```

The even prologue at `$8520` writes initial X-low values
`F0,28,58,88,B8,E8,18,48`; the odd prologue at `$A8AA` writes
`F1,29,59,89,B9,E9,19,49`. Both set the CPU X register to `$88`, clear
carry and reset their own mutable JMP operand to the initial loop.
The prologues do not change `$D010`, so the actual X-high mask is an
external input. They also do not execute CLD: the binary addition formulas
require the runtime decimal flag to be clear.

| Variant | Block start | End, exclusive | Normal-flow exit |
|---|---:|---:|---|
| Even | $8556 | $8978 | Live raster-table dispatch |
| Even | $8978 | $8DEC | JMP $8978 |
| Even | $8DEC | $9261 | JMP $8DEC |
| Even | $9261 | $96D6 | JMP $9261 |
| Even | $96D6 | $9B4B | JMP $96D6 |
| Even | $9B4B | $9FC0 | JMP $9B4B |
| Even | $9FC0 | $A435 | JMP $9FC0 |
| Even | $A435 | $A8AA | JMP $A435 |
| Odd | $A8DF | $AD01 | Live raster-table dispatch |
| Odd | $AD01 | $B174 | JMP $AD01 |
| Odd | $B174 | $B5E9 | JMP $B174 |
| Odd | $B5E9 | $BA5D | JMP $B5E9 |
| Odd | $BA5D | $BED1 | JMP $BA5D |
| Odd | $BED1 | $C346 | JMP $BED1; absent from original dispatch |
| Odd | $C346 | $C7BA | JMP $C346 |

The initial loops can repeat through their live dispatch. Once a regular
loop is selected, it self-loops; it does not return to the dispatcher or
fall through into the next physical block. The external CIA1 Timer-B
cutoff abandons the active source path. A source loop boundary is therefore
not a complete native frame boundary.

The `$BED1` loop is a complete generated block, but **none of the original
odd dispatch table entries selects it**. It is included in source coverage
and explicitly excluded from normal reachability with those original tables.
This does not assume that runtime tables can never be modified.

## Dynamic dispatch uses the value actually read

The even loop reads mirrored raster low at **$8962**, then uses
`$F400[r] | ($F500[r]<<8)` to patch `$8976/$8977`, the operand of the JMP
at `$8975`. The odd loop reads at **$ACEB** and uses `$F600/$F700` to patch
`$ACFF/$AD00`, the operand of the JMP at `$ACFE`.

These are eight-bit raster samples. The producer checks **all 512 table
entries** and emits their complete run ranges and normal-flow edges.
For example, even samples 0–206 re-enter `$8556`; odd samples 0–212
re-enter `$A8DF`. Later values choose source-specific regular loops rather
than one common epilogue. The complete original range map remains in the
graph output; no raster value is guessed from the selected target.

Useful post-read source anchors are **$8965** and **$ACEE**. CPU Y there
contains the actual sampled byte. The full anchor file contains **106
source sites**: 104 `LDY $D012` and two `LDY $D112`. Only sites actually
reached need runtime observations. A load watchpoint's independently
recorded loaded Y can provide this input; an expected store value cannot.

## Values, carry chains and interleaved writes

Each macro is a source idiom with explicit inputs, output locations and
original PCs. The main forms are grouped copies, grouped additions,
sampled raster/table lookups, pointer transfers, coordinate/border write
trains, retained-value writes, masked mirror writes, padding, delay calls
and normal-flow edges. It is not an instruction-level runtime machine.

For binary addition, the descriptor retains:

```text
sum        = source_byte + addend + incoming_carry
byte       = sum & 255
next_carry = sum >> 8
```

An original CLC after the addition clears the outgoing carry while keeping
the computed byte. A standalone later CLC remains a separate source macro.
This distinction matters: the original code does not independently add 21
to every sprite Y and eight to every pointer with an assumed zero carry.
Carry can flow between source additions and loop iterations.

Every loop contains **16 pointer transfers**: eight from `$43F8..$43FF` to
`$47F8..$47FF`, then eight in the reverse direction, with source addend
eight and the actual carry chain. Each sprite Y is written twice per loop,
in groups using source addend `$15`. Initial loops contain four such group
calculations; regular loops contain seven. All exact group membership and
source reads are retained. These are CPU writes to Y/pointer registers or
RAM; cached VIC pointers, DMA counters and fetch timing are not inferred.

The write trains preserve ordered X-low INC/DEC, forced sprite-0 `$F0`,
forced sprite-3 CPU-X `$88`, and the interspersed DEC/STX `$D016` pulses.
Software-visible register reads must be supplied by the hardware layer:
in particular a D016 DEC after stored `$88` reads `$C8` and writes `$C7`.
The source descriptors retain the RMW operation and do not reduce it to
an ordinary RAM decrement. The hardware consumer must also account for
its physical dummy write.

Retaining values across unrelated instructions is necessary. At `$855F`,
for example, a sampled F300 color is written to seven sprite colors; a
DEC `$D016` intervenes before the eighth color store at `$857A`. A later
literal `$F0` can likewise remain live across a coordinate write train.
All **eleven SAX `$D111`** sites are source-checked to use that retained
literal and CPU X `$88`, giving `$F0 & $88 = $80` to mirrored D011.
They are additional writes, not F200 color/shade samples.

## The two table-index schedules differ

The initial loop in each variant performs **three fresh D012/F300 color
samples** and no F200/D011 writes. Each sample is copied to all eight local
sprite-color registers, with source-specific pulse interleaving. The
original F300 table contains colors 1,2,6,7,8,10,15, but its actual runtime
generation must be bound rather than assumed unchanged.

Each regular loop performs **17 F200/D011 writes**. The original F200
table contains only `$80/$88`; these control D011, including its border-size
bit, with DEN clear. The table index is not a fresh raster read every time.
Let `r0,r1,…` denote separate actual `LDY $D012` samples in source order:

```text
Even, eight fresh samples:
r0; r1,r1+1; r2,r2+1,r2+2,r2+3; r3; r4;
r5,r5+1,r5+2,r5+3; r6,r6+1; r7,r7+1

Odd, seven fresh samples:
r0,r0+1,r0+2,r0+3; r1,r1+1; r2,r2+1; r3,r3+1;
r4,r4+1; r5,r5+1,r5+2,r5+3; r6
```

All additions to the lookup index wrap modulo 256. The producer independently
checks the full schedule in **every regular block** of each family; the
macros preserve intervening INY operations instead of resampling hardware.
D018 writes alternate `$10/$00`, selecting the two pointer-array contexts
under the actual bank. Neither current pointer RAM nor a final D018 value
alone proves what the VIC fetched earlier.

## Consumer contract and remaining boundary

An independent executed-write model can consume these source macros with:

- The actual entry state, decimal flag clear, X-high mask, VIC controls,
  positions, pointer RAM and effective CIA2 bank pins.
- Each actually executed raster read's loaded Y, including the D112
  dispatcher samples; INY-derived indices remain calculated.
- The actual F200–F7FF table generation and source code/SMC lifetime guards.
- The guarded shared delay helpers at `$019F/$01A0/$01A4`, which must return
  preserving value/carry temporaries. Their bytes are outside B8/B9; the
  descriptors retain the external contract and do not invent elapsed costs.
- Hardware register read/mirror/RMW rules and the observed cutoff position.

The source graph and macro arithmetic can then predict values and order
without feeding back expected native writes. Absolute clocks still require
hardware timing, bus stalls and interrupt recognition; committed pixels
add sprite fetch, latch and shifter history. This pass does not replace
those boundaries with a current-RAM compositor.

## Replay and limits

```sh
rtk proxy python3 -B research/the-hat/raster_source.py \
  --output build/research/the-hat/raster-source-analysis/fresh-replay
```

The [accepted source receipt](../../build/research/the-hat/raster-source-analysis/accepted-02/raster-source-proof.json)
is **12,542 bytes**, SHA-256
`6c3e831d481b58ca3d297cd13d2f21a95256a1edeb806cc46c4b5ce60d8491cb`.
Producer: **23,194 bytes**, SHA-256
`3d217fac03c4637947a4303e6ded13b265f15b46732f0b720c254aabc3958b32`.
Fresh self replay reproduces all **five files / 2,419,368 bytes** exactly,
without path normalization. The
[report](../../build/research/the-hat/raster-source-analysis/self-replay-check.json)
is 927 bytes, SHA-256
`3c067ff5de75d80449e0581983fe0787aaa6396a430a50d655beae80540994f5`.
Independent root source review also passed, and its fresh replay reproduces
all five files / 2,419,368 bytes exactly. The
[root report](../../build/research/the-hat/raster-source-analysis/root-replay-check.json)
is 1,606 bytes, SHA-256
`16234e398567b21a9c723fe6ac8c5832e711b0efa492bd0032cd904f1292d5d3`.
Earlier candidate failures are retained: the recognizer initially missed
the separated eighth color store, then a literal retained across RMW.
The second failure's first diagnostic named the wrong load; its explicit
correction is retained. Both cases were resolved by representing the real
source dependence rather than changing original bytes or oracle inputs.

No prior research artifact, source decoder, product, emulator state or
shared index is changed. Full source coverage is established. The later
[typed value acceptance](the-hat-raster-values.md) checks four complete
captured paths; it does not turn this static fifteen-kernel coverage into
native execution of every dispatch target. Displayed pixels remain a
separate boundary.
