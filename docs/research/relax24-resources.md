# Relax #24: resource-format checkpoint

Research date: 7 November 2026. This checkpoint derives the original **`$991D` resource format**, including why the first unavailable literal-path value is dead. **No resource has yet been fully decoded or validated.** The [strict 235-instruction boundary](relax24-articles.md) remains intact; no invented RAM value, hardware response or skipped CPU instruction is used to claim completion.

The new [decode_resources.py](../../research/relax24/decode_resources.py) is currently a **source-format checkpoint inspector**, not a finished decoder. It verifies the frozen consumer/source identities, derives the actual distance tables and matches the first literal prefix to existing CPU evidence. It runs no CPU or native process.

## Known resource inputs

The frozen inner payload establishes `$0801..$FFFE`. The consumer trace identifies five calls to `$991D`, each loading five descriptor bytes into `$D3..$D7`: initial bit buffer, remaining-byte counter and output cursor. Those descriptors and their pointer setups are preserved in [the consumer proof](../../build/research/relax24/article-analysis/consumer-proof.json).

The next useful block is:

```text
compressed bytes: $8000..$8DF0
descriptor:       $8DF1..$8DF5 = 27 F1 0D 00 D0
remaining bytes:  $0DF1
output cursor:    $D000
```

Its completed expansion is needed before interpreting the later `$C000` reader/menu entry. An output cursor alone does not establish the output extent. The relation to side-2 file headers remains unproved.

## Bit reader and literals

`$9A0B` returns bits **LSB first** through carry. `$D3` contains a sentinel above its usable bits. A right shift returns the low bit while the shifted buffer remains nonzero. When it becomes zero, the sentinel is discarded and the reader either:

- Ends `$991D` if the remaining-byte counter is zero; or
- Decrements that counter, fetches a byte through the shared descending `$00D8` reader, stores `$80 | (byte>>1)` in `$D3`, and returns `byte&1`.

There is no additional encoded EOF marker. Counter exhaustion is tested when another refill is required.

Literal length starts with zero low/high accumulators. Payload bits and continuation bits interleave; continuation one appends another payload bit, zero completes the length. A first zero means no literals. A complete implementation must retain the actual low-byte-zero/carry branch and 16-bit ROL wrapping rather than assume an unbounded generic gamma code. In the valid no-underflow domain, literal length is subtracted from the remaining-byte count before those raw bytes are copied.

The saved `$9F57` case starts with buffer `$4B`. Its usable bits are `1,1,0,1,0,0`, giving literal length **4** without a refill. That equals `$CF=4` in the already frozen original CPU prefix, which stops at `$99F2` on unknown `$0223`. This checkpoint performs no additional CPU execution.

## Match lengths and gaps

Match length also appends payload bits, stopping immediately at zero or at a value of at least 128; otherwise a continuation bit decides whether to continue. The stored length is `(n+2)&255`.

| Length | Normal distance bucket |
|---|---:|
| 2 | 0 |
| 3 | 1 |
| 4–255 | 2 |

Wrapped lengths zero and one retain bucket 1. **Zero match length emits no bytes**, unlike the zero-length wrap in Relax's earlier outer packing stage. These machine edges must not be conflated.

Three additional bits select one of eight cases inside a bucket. The packed table copied from `$990C` yields these elementary bit widths:

```text
bucket 0: 3 1 1 1 1 0 1 1
bucket 1: 4 1 1 1 1 1 2 2
bucket 2: 4 1 1 1 1 2 2 2
```

For the selected case, the original routine reads fields in descending case order, appending their bits and adding one between cases. Equivalent cumulative widths and bases are retained in the [format checkpoint](../../build/research/relax24/resource-analysis/format-checkpoint.json). The largest gaps are **1,143 / 11,247 / 21,999** for the three buckets.

The decoded quantity is a **gap**, not a distance-minus-one. For current output cursor `P`, stored length `L` and gap `g`:

```text
destination block = [P-L, P)
source block      = [P+g, P+g+L)
backward distance = L+g
```

A model must retain 16-bit addresses, mutable RAM and known masks. Every meaningful match source byte must already be established; an actually used unknown remains a stop condition.

## What is dead at $99F2, and what is not

The original code is:

```text
99F2  LDA ($D1),Y
99F4  LDX $CE
99F6  BNE $99FB
99F8  JSR $00D8
99FB  DEY
99FC  STA ($D6),Y
```

When `$CE=0`, the unavailable load changes only A/N/Z. `LDX $CE` replaces N/Z before the branch. The following byte reader begins with `LDA $E1` and eventually loads the actual compressed byte, replacing A. Carry and overflow are unaffected by the initial LDA/LDX. Thus the first load's **value and N/Z are not inputs to literal output**.

This does not erase the physical read or its timing. The existing strict CPU check still stops on it. A purely functional format model may declare that dead-value dependency absent; it must not supply a made-up value to the CPU or describe a fragment chain as continuous original execution. For `$CE!=0`, the load supplies actual match data and must pass the known-memory check.

## Exact continuation point

The next action is to implement the functional parser on `$8000..$8DF0`, using descriptor `$8DF1..$8DF5`. It should preserve both source/destination mutation, enforce known meaningful reads and explicitly record the literal dead-read abstraction. Any original-CPU fragment checks must state their entry/state and gaps. Only after obtaining a justified post-expansion image should the analysis follow `$C000` to the real filename, header and article consumers.

All five complete resource outputs, the initialized reader/menu, the side-2 article format and the original coding-review article remain open. The current checkpoint adds no article text and makes no new native, full-bootstrap or timing claim.

Recheck the saved source-format evidence with:

```sh
rtk proxy python3 research/relax24/decode_resources.py
```

The earlier archive, packing and consumer proofs remain unchanged. This is the frozen handoff state for the next research session.
