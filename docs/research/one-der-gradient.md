# One-Der's original gradient arithmetic matches four native calls

An independent pure integer scalar reproduces **all 32 captured bytes at
`$20..$27` and all four return carry bits** from One-Der's original gradient
routine. It follows the actual byte/word arithmetic, including its unusual
division guard and overflow behavior. It does not substitute ideal division
or adjust the captured inputs to obtain a match.

The new producer is [`gradient.py`](../../research/one-der/gradient.py).
The receipt is
`build/research/one-der/gradient-analysis/accepted-02/gradient-proof.json`.
The [earlier native acceptance](one-der-gouraud.md), original analyzer and
native files remain unchanged. No emulator, CPU instruction interpreter,
build or native process runs in this analysis. Static disassembly was used
only to read the original instructions; the producer itself needs only
Python's standard library.

## Input and output conventions

The three captured triples occupy `$10..$18`:
`(X0,Y0,I0), (X1,Y1,I1), (X2,Y2,I2)`. Their third bytes are varying shade
attributes; this does not independently establish a separate normal/light
calculation. Let `s8` reinterpret a stored byte as signed, and `wrap16`
retain the low 16 bits. The original `$1770` path forms:

```text
A = s8((Y2 − Y1) mod 256)
B = s8((Y0 − Y1) mod 256)
U = floor((I1 − I0) / 2)
V = floor((I2 − I1) / 2)

N = wrap16(A·U + B·V)
D = wrap16(A·s8((X1−X0) mod 256) + B·s8((X2−X1) mod 256))
```

The intensity bytes are unsigned for the subtraction before halving. The
`SBC / ROR / EOR #$80` sequence produces a **floor**, including negative odd
differences. For example, −1 becomes −1, while +1 becomes 0. This is not
round-to-nearest or truncation toward zero. Halving occurs before the
products, so later doubling cannot recover discarded odd-difference bits.

The `$17EA` multiplier uses signed magnitudes and a complemented multiplier
with eight fixed shift/add stages. The scalar separately expresses that
algorithm and checks all **65,536 byte pairs** against signed multiplication.
Each product is exact over its byte domain; the two-product sum wraps as a
stored word. A second exhaustive 65,536-pair check establishes the halving
identity against integer floor division.

After the original divider, the eight output bytes have these meanings:

| Addresses | Meaning |
|---|---|
| `$20/$21` | Wrapped Y differences A/B, still stored as bytes |
| `$22/$23` | **Fraction / signed integer**: little-endian signed Q8 gradient |
| `$24/$25` | Little-endian `wrap16(abs(D)−1)` scratch divisor |
| `$26/$27` | The same quotient in **integer / fraction** order |

The last load before RTS leaves A equal to `$22`, the fractional byte.
Carry is preserved from the divider. The four captured calls return carry
zero. Any later doubling or horizontal-table construction belongs to the
separate raster study, not this acceptance.

## The divider is not a general ideal signed division

The original `$1853` routine takes the stored N and D words, normalizes
their signed magnitudes, doubles the numerator **modulo 65,536**, and stores
`abs(D)−1` as the divisor scratch value. Its two fixed eight-step stages
generate an integer byte and a fractional byte. The scalar retains carry
between trial subtraction and rotations, including the special initial
byte-prefix rotation; there is no opcode interpreter or modeled CPU state.

For these four captured operands, the resulting signed Q8 word agrees with
truncation toward zero of `512·N/D`. That is an observed arithmetic relation
for this set, not a universal replacement for the original code.

The early guard compares the high byte of the doubled numerator with the
stored `abs(D)−1`. If it succeeds, it returns the doubled numerator bytes
without the normal quotient stages or sign correction, and sets carry.
This behavior is preserved. Selected scalar probes expose the difference
from ideal division:

| N | D | Original path | Stored signed Q8 result | Ideal signed truncation |
|---:|---:|---|---:|---:|
| −1 | 1 | Early guard; sign correction bypassed | +512 | −512 |
| 1 | −1 | Early guard; sign correction bypassed | +512 | −512 |
| 128 | 2 | Early guard | 1 | 32,768 |
| 32,767 | 32,767 | Normal path, original prefix/carry behavior | 255 | 512 |
| −32,768 | 640 | Magnitude doubling wraps to zero | 0 | −26,214 |

These are source-derived domain probes, **not additional native calls** or
claims that those operands occur in the demo. They prevent the normal path
from being advertised as an ideal general-purpose division routine.

For denominator zero, the stored divisor becomes `$FFFF`. Exhausting all
65,536 stored numerator words in the scalar yields zero integer/fraction
bytes in every case. Return carry is zero for 16,384 inputs and one for
49,152. No exception, saturation value or synthetic error path is inserted.
The zero-divisor result is an algorithm-domain finding, not a new runtime
observation.

## Four original entry/return comparisons

The existing sequence-111 response contains four `$0E53`/`$0E56` pairs.
`$0E53` is the original `JSR $1770`; `$0E56` is its natural continuation.
Both have SP `$F4`. Entry captures require all bytes `$10..$27` and
`$72..$79`; return captures require `$10..$27`. The new parser rechecks
the exact received-byte slice and all eight event payloads, then compares
the scalar with the original captured results and frozen prior receipt.

| Call | N | D | `$20..$27`, hexadecimal | Signed Q8 `$23:$22` | Carry |
|---:|---:|---:|---|---:|---:|
| 0 | 490 | −485 | `0F 0A FB FD E4 01 FD FB` | −517 | 0 |
| 1 | 4,390 | −2,365 | `4B FB 4A FC 3C 09 FC 4A` | −950 | 0 |
| 2 | −4,630 | −640 | `F1 37 78 0E 7F 02 0E 78` | 3,704 | 0 |
| 3 | −1,810 | −2,540 | `B5 EC 6C 01 EB 09 01 6C` | 364 | 0 |

Every byte and carry agrees, without a counterexample in the four native
samples. The input triples remain the captured values; all observed
counterexamples to ideal division in the domain probes remain in the
receipt.

## Byte identity, custody and replay

The original `$1770..$18EC` region is **381 bytes**, SHA-256
`aa6daf70f86b2479bd3ea9d79c52940a883376ba2f4f0747d3ed4d8b07f84988`.
The initial part-2 RAM, later-frame RAM and draw-end RAM have identical
bytes throughout that region. The only allowed runtime selfmodification
is the sign immediate at `$18DC`, written by original `STX $18DC` at
`$187F`; its allowed bytes are `$00/$01/$FF`. The signed multiply and divide
are therefore bound to the original product bytes, not a similar algorithm
selected after seeing the results.

The frozen prior One-Der receipt is pinned at **36,184 bytes**, SHA-256
`e5eaaa1c454462e84de564b0984b8d587a37993b2b42457cc504bff0925f1532`.
Its accepted native case remains the same 36-file listing, SHA-256
`3264e764ff72ae0744de5c0a3b55beabd7641ac370c79744a8fb3ba0f4b361a9`.
All files are rehashed. The earlier proof supplies the full original
loading/wire/snapshot custody; this new parser checks sequence 111's
received range **37,918..40,814** directly against the pinned raw wire.
Native clock values bind the pairs only; no timing model or speed claim is
added.

Run from the repository root with a fresh output directory:

```sh
rtk proxy python3 research/one-der/gradient.py \
  --output build/research/one-der/gradient-analysis/replay-next
```

The three outputs are the extracted original code region, checked scalar
producer and compact receipt. Output references use local filenames, with
no output-directory prefix or timestamp. Nonempty outputs are refused.
`accepted-01` is an intermediate receipt; `accepted-02` is final.

A fresh `replay-01` reproduces all **three files, 28,787 bytes**, exactly,
including the receipt and checked producer. No path normalization is
needed. Independent static review found no defect. All eight artifact
references and all 2,487 previously frozen artifact hashes checked valid
and unchanged; unrelated dirty experiments were not edited.

| Final artifact | Bytes | SHA-256 |
|---|---:|---|
| Scalar producer | 13,785 | `40f978f7f6b20cb0ae8c4dbd4fac18808513c38e5c5ab7a28890b1e33b4eca1a` |
| Gradient receipt | 14,621 | `85485febf43fcf9263b9508c823552fcb36a1443f363085e6a15214adb031071` |

The next boundary is original edge interpolation and span consumption of
this Q8 result. This finite gradient acceptance does not prove whole-frame
pixels, display geometry, a separate lighting model, stock-speed behavior
or performance improvements. No original code, native state or unrelated
experiment is changed.
