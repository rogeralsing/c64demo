# Edge of Disgrace: coefficient, vertex and visibility stages

Research date: 8 November 2026. This study concerns the original side-1a
shader in files 51/52, before contour preparation at `$5B56`. It follows
the original byte arithmetic and lookup tables rather than replacing the
code with floating-point rotation, ideal multiplication or an area-sign
culling test. A fresh original-disk native case supplies stage boundaries.
From its frame-entry state alone, the scalar reproduces all 128 declared
stage bytes and independently regenerates 3,328 table bytes. These are
bounded array checks for one pose, not a whole-RAM or displayed-frame proof.

The [controller proof](eod-controller.md) establishes the original loaded
payloads and dispatcher. The [shader proof](eod-shader.md) establishes the
thirteen packed levels, transition masks, sparse tracing paths and one
independent marker line. [Contour reconstruction](eod-contours.md) owns
the subsequent `$5B56/$5D50/$5E65` stages; this producer does not duplicate
them.

## Natural stage boundaries

| Original frame PC | Call | Natural continuation | Declared result |
|---:|---:|---:|---|
| `$546A` | `$5515` | `$546D` | Ramp counter/phase and optional window |
| `$546D` | `$5586` | `$5470` | Updated angles and nine coefficient words |
| `$5470` | `$5759` | `$5473` | Eight projected corner records |
| `$5473` | `$59A9` | `$5476` | Six face flags and twelve edge flags |
| `$5476` | `$5B56` | `$5479` | Outside this producer's geometry scope |

The producer pins the frozen extraction, controller and shader receipts.
It checks original opcode anchors and hashes each complete stage's file
bytes. A matching numerical PC without the correct loaded generation is
insufficient, as the earlier retained `$546A` overlay demonstrated.

## Ramp and coefficient arithmetic

`$5515` reads counter `$5513` and phase `$5514`. Phase 0 copies a sixteen-byte
window via `$555F`, then increments the counter until 13 and enters phase 1
with counter 120. Phase 1 decrements it; zero advances the phase. Phase 2
copies the departing window and advances to phase 3 after thirteen steps.
Phase 3 returns. The scalar preserves byte wrapping and the original
descending source/window indexing.

`$5586` selects three velocity bytes using `$17ED` and table bases `$17EE`,
`$17F7`, `$1800`. It adds them modulo 256 to angles `$17EA..$17EC` and
copies the resulting angles to `$90..$92`. No angle is inferred from a
completed frame.

The arithmetic then reads paired low/high tables at `$0B00+offset+phase`
and `$0D00+offset+phase`, with offsets 0, 64 or 128. These are original
prepared word tables; their extended addressing is preserved, rather than
wrapping the offset into a new 256-entry table. The scalar uses the
original entries, phase sums/differences, intermediate wrapped subtraction,
and sign-preserving right shifts. It does not synthesize replacement sine
values from a host math library.

The nine little-endian coefficient words occupy `$10..$21`:

```text
X contributions: $10/$11, $16/$17, $1C/$1D
Y contributions: $12/$13, $18/$19, $1E/$1F
Z contributions: $14/$15, $1A/$1B, $20/$21
```

Four intermediate words at `$80..$87` are arithmetically halved at their
construction sites. The final loop `$574B..$5758` arithmetically halves
all nine wrapped coefficient words again. The high-byte `ASL` supplies the
sign bit to `ROR high; ROR low`; a logical unsigned half would differ for
negative values. Scratch words `$88/$89` and `$8A/$8B` are also source-derived
in the scalar, but are not the downstream vertex-record interface.

## Runtime table roles

The original initializer at `$1283..$12F5` builds two 512-entry quarter-square
tables, split into low/high pages:

```text
$B000/$B200: Q(i) = floor(i*i/4),        i=0..511
$B400/$B600: R(i) = floor((255-i)^2/4),  i=0..511
```

The first table is built by the original fixed multiply/shift loop; the
second combines a reversal of its first half with the next positive
entries. The scalar calculates their 2,048 declared table bytes with exact
integer formulas. All agree with the native frame-entry tables. It also
checks the identity `Q(scale+2*m)−R(255−scale+2*m)=2*scale*m` for all 256
byte scales and 128 nonnegative seven-bit magnitudes: **32,768 cases**.
The high-byte check retains the low-byte borrow. This reconstruction
concerns the tables, not the other scratch state of the complete initializer.

Shader init `$549D..$5512` supplies five more pages:

```text
$A000[x] = 16*floor(x/16)
$A100[x] = floor(x/16)
$A200[x] + 256*$A300[x] + 65536*$A400[x] = floor(2^20/x), x=1..255
x=0: reciprocal bytes FF FF FF
```

All 1,280 bytes agree with the native frame-entry tables. The divide-by-zero
entry is the original restoring loop's sentinel result, not a mathematical
division. The reciprocal table is consumed by later contour
interpolation. `$A000/$A100` quantize the depth selector into shade bins;
they do not store completed screen coordinates or prerecorded frames.

The decreasing 256-byte projection scale table at `$6490..$658F` is part
of original file 52. The shader initializer places its address in `$26/$27`.
Runtime depth selects its byte; the original table remains the authority
for the selected scale, rather than an assumed focal-length formula.

## Eight records and exact projection

`$5759` constructs four corner sums with signs `(+,+,+)`, `(+,+,−)`,
`(+,−,+)`, `(+,−,−)` in each coefficient row. It stores their wrapped
sixteen-bit raw X/Y/Z values at record bases `$40,$46,$4C,$52`. The four
opposite corners use one's-complement high-byte symmetry and are stored at
`$58,$5E,$64,$6A`.

After projection, each six-byte record has this downstream interface:

| Offset | Meaning |
|---:|---|
| +1 | Projected X; projection helper output shifted right once |
| +3 | Projected Y; helper output used directly |
| +5 | Biased depth-high byte, also the contour intensity selector |

For the first four records, offsets +0/+2/+4 retain the raw low bytes.
The opposite records' low slots are preserved incoming bytes; treating all
48 bytes as a uniform array of current-frame signed X/Y/Z words is wrong.
Only the stated high-slot interface is read by the downstream contour
code.

The depth selector is `raw_Z_high XOR $80`; its opposite is that byte
XOR `$FF`. The scale byte selected through `$26/$27` is installed in the
low halves of the product pointers `$E8/$EA`, while `$EC/$EE` receive its
one's complement. Their page halves are `$B0/$B2/$B4/$B6`.

Helper `$598E..$59A8` saves the input sign, complements negative input
bytes, doubles the magnitude index, and subtracts the two quarter-square
values. The low-byte subtraction's borrow feeds the high-byte subtraction.
It then restores the original saved sign convention using complements,
XOR `$7F` and subtraction of `$40`. It does not implement a generic ideal
signed multiply-and-round operation; both one's-complement behavior and
the low-byte borrow are preserved in the scalar.

No separate light vector, normal transformation or normal-light dot
product appears in these four stages. The original contour code consumes
the depth selector through `$A100` as its intensity bin. A relation between
that depth shading and a particular geometric lighting model would require
a separate derivation; it is not established here.

## Original visibility decision

`$59A9` calls `$5A25` for six selected projected corner triples. Its returned
carry becomes a face flag: carry clear → 1, carry set → 0. The six bytes
are `$60FD..$6102`. The helper separates zero-factor and product-sign cases,
normalizes the absolute coordinate differences, and, when needed, compares
up to seven successive quotient bits. If those bits remain equal, its
original result is carry set. The scalar preserves that finite decision
tree; it does not substitute an exact cross-product sign.

The twelve edge flags `$6133..$613E` are sums of the two adjacent face
flags selected by original arrays `$6157..$6162` and `$6163..$616E`.
Each result is 0, 1 or 2. Thus no ADC carry propagates between edge entries
in the descending original loop. Downstream edge preparation skips zero
entries and uses the two endpoint-record tables at `$613F/$614B`.

## Native comparison and scope

The root-owned `frame-analysis/accepted-01/frame-proof.json` accepts a
fresh original side-1a boot, 15 RAM/VSF pairs, 99 serialized commands and
the saved natural stage boundaries. Its SHA-256 is
`ef77c7a2d93d110ce5caa8c60c313d8d7313325ba51e9d355cff9e855535bb50`.
This producer consumes that frozen proof and rehashes its five relevant
RAM files. It also compares the incoming native code, word tables,
projection scale and visibility connectivity against original files 51/52.

Every stage prediction is chained from **`begin` at `$546A`**. Native
current-frame ramp, coefficient, vertex and visibility returns are used
only as comparison targets; they never replace the next scalar input.
The original incoming tables are first replaced with the independently
calculated tables, after confirming all 3,328 bytes agree.

| Natural continuation | Compared declared state | Bytes | Observed elapsed window |
|---:|---|---:|---:|
| `$546D` | `$5513..14`, ramp window `$60ED..FC` | 18 | 32 cycles |
| `$5470` | Nine words, angle storage/copies, coefficient scratch `$80..8B` | 36 | 1,815 cycles |
| `$5473` | Eight records `$40..6F`, product pointers `$E8..EF` | 56 | 1,752 cycles |
| `$5476` | Six face flags, twelve edge flags | 18 | 1,617 cycles |

All **128 compared bytes** agree. Some declared slots are preserved rather
than newly written: the stable ramp leaves its window unchanged, the four
opposite vertex records retain twelve low slots, and product-pointer high
bytes are fixed incoming pages. This is not a claim that all 128 bytes are
distinct fresh writes.

The captured updated angles are `[128,34,98]`. The scalar obtains face
flags `[1,0,0,0,1,1]` and edge sums
`[1,2,2,1,1,0,0,1,0,1,1,2]`. Those flags are results of the original finite
decision procedure, not an independent proof of ideal geometric culling.
This pose exercises sign and normalized-order paths; it does not validate
every zero-factor or seven-bit fallback case by native execution.

The four observed windows total 5,216 elapsed machine cycles. They include
the original call/return and any intervening machine effects. The scalar
does not predict those costs. No FPS, broader workload distribution or
speedup follows from this one sample. Its pose matches the earlier native
witness, while the fresh boot's entire begin RAM differs in one old stack
byte at `$0146`; these are not two independently sampled poses or identical
whole-machine states.

Other scratch RAM, stack writes and complete CPU flags/registers are not
reproduced. In particular visibility scratch `$70..79` is unmodeled; the
separate contour scalar confirms it does not read that incoming scratch.
All contour inputs use the declared record/flag interface and source-bound
tables instead.

## Passive reproduction and next step

```sh
rtk proxy python3 -B research/eod/geometry.py --output build/research/eod/geometry-analysis/fresh-replay
```

Choose a fresh directory. No downloaded host entrypoint, emulator, CPU
instruction interpreter, build or native process is used by this producer.
The final receipt is `geometry-analysis/accepted-01/geometry-proof.json`,
**36,895 bytes**, SHA-256
`33d4119215b249e76c8093a71d655cacb6b9d8c58804c73315915ef734a55cec`.
The producer is **20,435 bytes**, SHA-256
`7c70f18cc1f586ddb8be70f8a4be5bd9ce67a456eb2d4772ef74cb3f97415d4b`.
The fresh `replay-01` reproduces all seven output files byte for byte,
**60,742 bytes**. Independent root review and a fresh root replay also pass
with the same seven files. `geometry-analysis/root-replay-check.json`
records the latter (932 bytes, SHA-256
`9905c4f2070d379bb3c22de8e5a1588d62626fb089b109fed62531b32797c510`).
Earlier source-01/source-02 outputs remain retained.

The next check should chain this predicted interface into contour and line
construction, then reconstruct the common prefix output. The root-owned
case proof owns wire, RAM/VSF and natural-return acceptance. Exact
whole-frame markers, publication and displayed pixels remain separate
acceptance boundaries from this upstream result.
