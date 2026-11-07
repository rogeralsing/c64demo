# Relax #24: resource recovery and the $C000 consumer

Research date: 7 November 2026. The original **`$991D` resource format** now recovers **9,216 bytes at `$AC00..$CFFF`**, including the real `$C000` display/loader consumer. Two functional models agree on every compressed-byte read and output store. This is resource-format evidence, not original CPU execution or an initialized menu. The [strict 235-instruction boundary](relax24-articles.md) remains intact; no invented RAM value, hardware response or skipped CPU instruction is used to claim completion.

The [decode_resources.py](../../research/relax24/decode_resources.py) implements a byte-state transcription and a separate integer/interval parser. They share known-memory and event-recording helpers, while using separate bit-reader, length, gap and copy formulations. The original inspector, its note and its receipt were archived before editing under [checkpoint-archive](../../build/research/relax24/resource-recovery-01/checkpoint-archive/archive.json). The earlier producer, consumer and format-checkpoint receipts remain unchanged. No CPU or native process runs in this checker.

## Recovered bytes and validation

The selected resource consumes exactly `$8000..$8DF0`: **3,569 bytes**, comprising 1,854 bit-refill bytes and 1,715 raw literals. The initial `$27` buffer contributes five usable bits, giving **14,837 returned bits**. The models process 1,095 command attempts, including the final partial command, and terminate while requesting another match-length bit with counter zero and pointer `$8000`. This retains the original counter/sentinel termination rule.

The output is one unique descending sequence of **9,216 stores**, `$CFFF` down to `$AC00`: 1,715 literal bytes and 7,501 match bytes. Its SHA-256 is `63843ddc392267cc18ac133cefa0f3109332d65cdbfa98d85bcbee00b326b069`. Every match read comes from an earlier output store of this same resource. No match needs a pre-existing nonoutput byte, no compressed byte is read after being overwritten, and no meaningful unknown read is supplied.

Initial knowledge is deliberately restricted to the independently proved `$0801..$FFFE` inner output. The producer's workspace and relocated decoder knowledge are excluded. Both models retain mutable 16-bit-addressed memory and propagate known masks through their own writes. They agree on all 3,569 input events, all 9,216 ordered output events, output addresses and bytes, final cursor, input pointer, counter, bit buffer, returned-bit count and termination stage. The event/extent gates are assertions, not just printed comparisons.

The checker also reconstructs the earlier `$9F57` call's first literal setup arithmetically. **All 39 frozen format-state bytes at `$CE..$F4`** match the already recorded original-CPU boundary, including the four-byte literal and unavailable `$0223` read. That 235-instruction CPU proof is consumed unchanged, not rerun or extended.

The [resource proof](../../build/research/relax24/resource-recovery-01/resource-proof.json) pins the source, mask, frozen proofs, current script and all generated artifacts. Output RAM, output PRG, known mask, command records, ordered input/output events and omitted dead-value addresses are retained beside it. A separate read-only peer review checked the page loop and format gates against the frozen instruction listing without rerunning CPU or native execution.

## What the recovered $C000 code consumes

The checker asserts 14 identified instruction sites in [consumer-sites.json](../../build/research/relax24/resource-recovery-01/consumer-sites.json). These are selected source intervals; graphics and padding are not swept into a code listing.

At `$C000`, the recovered code executes `SEI`; its first hardware access would be `$C003: STA $DC0D`. It sets NMI vector `$C1F8`, an initial raster IRQ vector `$AE00` and raster value `$75`, then requests port `$15`. Later foreground setup includes display RAM copies and sprite-register writes. None of this initialization, IRQ delivery or hardware behavior is executed by the resource model.

The first concrete foreground loader call is:

```text
C156  LDX #$30
C158  LDY #$30
C15A  JSR $AC00
```

The recovered `$AC00` sets A to `$02` before calling `$AC63`. That sender stores X/Y at `$ACF8/$ACF9` and sends the command byte followed by the saved X and Y through `$ACB0`, whose bit transmitter writes CIA2 `$DD00`. Thus this source requests the tuple **`02 30 30`**. The pair spells ASCII `00`; matching the uploaded drive receiver and the transferred original disk file remains the next binding step.

The receiver first obtains an output address into `$AE/$AF`; the identified store loop at `$AC4D` writes received bytes through that cursor and increments it. After the first call returns, `$C15D..$C174` subtracts two from the returned cursor, reads those two trailing bytes and patches the later `$C3B1` JMP operand. `$C17B` makes a second `$AC00` call with X/Y both `$FF`. The foreground then clears `$C800/$C900`, updates the IRQ-vector high byte and waits at `$C19C`.

Later recovered code at `$C380` contains a copy from `$2000..$ABFF` to `$0801..$9400`, followed by port `$37`, KERNAL calls and the patched JMP. Those source instructions establish a continuation to investigate; their reachability, transferred contents and resulting machine state have not been executed here. The recovered `$C000` is therefore a real display/loader consumer, while its relation to the final article reader remains open.

## Known resource inputs

The frozen inner payload establishes `$0801..$FFFE`. The consumer trace identifies five calls to `$991D`, each loading five descriptor bytes into `$D3..$D7`: initial bit buffer, remaining-byte counter and output cursor. Those descriptors and their pointer setups are preserved in [the consumer proof](../../build/research/relax24/article-analysis/consumer-proof.json).

The next useful block is:

```text
compressed bytes: $8000..$8DF0
descriptor:       $8DF1..$8DF5 = 27 F1 0D 00 D0
remaining bytes:  $0DF1
output cursor:    $D000
```

Its now recovered expansion establishes the later `$C000` code bytes. The output extent was obtained from actual format stores, rather than assumed from the cursor. The relation to side-2 file headers remains unproved.

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

This does not erase the physical read or its timing. The existing strict CPU check still stops on it. Both functional models declare that dead-value dependency absent; neither supplies a made-up value to CPU execution. The recovered resource has 1,715 such omitted value loads, of which 969 would address currently unknown bytes. The other literal values are not sampled either. For `$CE!=0`, the load supplies actual match data and passes the known-memory check.

## Limits and exact continuation point

The functional output is isolated from the pinned inner image; preceding initialization and the other four resource calls are not executed. The models include byte wrapping and the original literal page-copy gate, while rejecting unobserved literal underflow or nonordinary length edges rather than inventing valid input. They make no register, interrupt, bus, physical-read, timing, native or whole-bootstrap equality claim.

Next, match the original uploaded drive receiver's command/name handling to **`02 30 30`**, bind that transfer to the original file bytes and follow the end-pointer/trailing-JMP contract. The other four complete resource outputs, initialized display/reader state, side-2 article format and original coding-review article remain open. This resource proof adds no article text or coding-review identity.

Recheck only the functional resource and static source evidence with:

```sh
rtk proxy python3 research/relax24/decode_resources.py
```

The receipt is written under `build/research/relax24/resource-recovery-01/`; the old format checkpoint stays under `resource-analysis/`. Rechecking this parser does not rerun either multi-million-instruction packing proof.
