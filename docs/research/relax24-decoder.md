# Relax #24: two checked packing stages

Research date: 7 November 2026. The original main PRG now yields two independently checked decoded byte ranges. A high-level format model and original 6502 decoder fragments agree on every input/output event. **This does not complete the original hardware bootstrap or identify the coding-review article.** It advances the byte-recovery boundary left open in [the frozen reader checkpoint](relax24-reader.md), which remains unchanged.

## Inputs and preserved boundaries

The source is the exact 31,211-byte PRG extracted in [the archive proof](relax24-archive.md), SHA-256 `ea9040469d211c87cdfd1aaa2a5eca04685be741d679bc1537cb7cc280810180`. The earlier strict CPU check still stops at `$080F: INC $D030`. No hardware, ROM or unknown-memory response has been supplied to continue that boot.

Instead, the new [decode_reader.py](../../research/relax24/decode_reader.py) constructs only the file-established literal copies, then treats the compressed formats and original pure routines as separate contracts. Every RAM read requires an established byte. Every store updates the same mutable RAM model, including code operands, table state and overlapping input/output. Zero-filled storage outside the known mask is not an input oracle.

## Outer stage: backward bit/LZ

The original `$0352` body reads a backward byte stream, MSB first within each byte, using the copied width/base tables. The high-level model preserves literal and match length-byte wrapping, offset escapes, descending output and overlapping LZ references. The special returned match length zero retains the original 256-store order, including its unusual first source address; it happens not to occur in this particular stream.

| Outer result | Value |
|---|---|
| Decoded range, inclusive | `$0801..$A0DF` |
| Bytes / chronological output stores | **39,135** |
| Output SHA-256 | `bb620911707fa00abf9e9d27db0898bfe87b72bc98f6e2c765b65017ee6de7ed` |
| Format blocks, including final marker | 10,155 |
| Compressed byte refills | 30,662 |
| Refilled RAM range, inclusive | `$078B..$7F50` |
| Back-reference reads | 24,832, all from prior output |
| Termination | Match-length selector `$30` |

The low refill range matters. The original table/continuation copy supplies compressed bytes below the apparent packed-file start; decoding is not equivalent to slicing the original PRG at a guessed header and reading an immutable byte array.

The independent CPU check invokes the **original `$0352` fragment** for each block. Each invocation ends at `$0349`, before the port/border wrapper, or `$03FE`, before restoration. Across **4,082,435 original instructions**, it matches:

- All 39,135 destination/value events, in order.
- All 30,662 compressed refill address/value events.
- The bit buffer, remaining-bit count, source cursor and output cursor at every block boundary.

These are explicitly separate fragment invocations. The harness selects `$0352` for the next invocation; it does not claim to execute the omitted `$0349/$034B/$034D/$0350` instructions. The original wrapper changes visibility and border color, but leaves Y unchanged. Each completed body supplies Y=0; A/X and condition flags are overwritten before the next format use. All-RAM visibility, decimal clear, no IRQ delivery and a safe initial stack are declared routine preconditions.

The format model does not reproduce CPU scratch/stack writes. The unfiltered final images differ at **five bytes**: `$00FC` and four stack bytes. These remain recorded; only the declared output and format-state domains are equality claims. The executed fragments' nominal cycle total excludes the wrapper and hardware, and is not a bootstrap timing measurement.

The [outer proof](../../build/research/relax24/decoder-analysis/decoder-proof.json), [all CPU fragments](../../build/research/relax24/decoder-analysis/CPU-fragments.json), event logs and known mask retain this result. The original producer source is preserved at [outer-producer.py](../../build/research/relax24/decoder-analysis/outer-producer.py), hash `71f4b2fb648d065d9adca2876ffcb6a8611e032123a60ea0d418968c6fb34e7f`. That archive is an identity record; the current tracked driver is the reproduction command.

## The first output is another packing stage

The outer `$0801` output is not yet article-reader code. It begins:

```text
A2 00 78 A9 34 85 01 BD 14 08 9D E8 00 E8 D0 F7 4C 00 01
```

Its source path requests `$01=$34`, copies **`$0814..$0913 → $00E8..$01E7`**, and jumps to `$0100`. There, original instructions copy **`$9FE0..$A0DF → $07F2..$08F1`** and establish SP=`$FF` before calling the byte/RLE routines. All copy sources are inside the independently verified outer output.

The byte reader decrements its `$9FE0` cursor before fetching, so its first address is `$9FDF`. The writer decrements its `$FFFF` cursor before storing, so its first output is `$FFFE`. The format has thirteen marker bytes:

| Marker | Instruction-derived meaning |
|---|---|
| `$E1` | Following zero ends the stream; otherwise emit that byte literally. |
| `$E7` | Read count and value, then repeat. A zero value falls through into the packed-dictionary form. |
| `$31` | Read a packed dictionary index/count; emit one dictionary byte 3–10 times. |
| `$CF` | Read count, subtraction delta and initial value; emit a descending byte sequence modulo 256. |
| `$CB` | Read a zero-run count. |
| `$CC/$F2/$C7/$DC` | Emit 2/3/4/5 zeros. |
| `$EC/$A1/$C5` | Emit twice `$55/$95/$9B`, respectively. |
| `$5C` | Emit `$EA` three times. |

Explicit count zero means **256**, preserving DEX/BNE wrapping. This occurs in 38 zero runs in the actual input. Arithmetic runs require decimal clear. The model also reproduces the original `$0350+Y` history writes separately from output and preserves the branch-operand self-modification.

## Inner result and continuous pure-CPU check

| Inner result | Value |
|---|---|
| Decoded range, inclusive | `$0801..$FFFE` |
| Bytes / chronological output stores | **63,486** |
| Output SHA-256 | `970be5dec0f0204c474dd718aaa2ab1dcc45e18ac94f3357cc8fad165d6d3cf1` |
| Compressed byte reads | **38,894**, `$07F2..$9FDF` |
| Termination | `$E1,$00` |
| Original CPU instructions checked | **2,766,530** |

Here the original CPU runs **continuously from `$0100` to `$0137`**, stopping before the port-restoration sequence. Every compressed input event, output event and output byte matches the independent byte/RLE model. The continuation copy is checked at its actual post-copy point, `$0109`. Its bytes are subsequently consumed and partly overwritten by decoded output.

The original CPU and format model leave only **two different stack bytes**, neither established by the format model; those differences and their known-mask status remain in the receipt. No whole-RAM or whole-machine equality is claimed.

The fragment's declared visibility is RAM under I/O and ROM, matching the excluded source request for port `$34`. Thus output at `$D000..$DFFF` is **RAM data**, not a set of observed VIC/SID/CIA register writes. CPU-port accesses remain forbidden. The `$0806` setup store and `$0139` restoration store are neither executed nor mocked. The static successor is `CLI / JMP $2000`; it is not a native handoff observation.

The first final-stage bytes at `$2000` are:

```text
A5 BA 8D 01 25 8D 5E 25 20 00 25 4C 00 94
```

They reference setup at `$2500` and a later `$9400` path. Further consumer analysis must follow this recovered code before assigning side-2 header fields or article identities.

The [inner proof](../../build/research/relax24/decoder-analysis/inner-proof.json) pins its outer producer/input and retains all 63,486 output events, 38,894 input events and record types. The first verification attempt wrongly required the initial continuation copy to remain unchanged at the end. That assertion failed because decoded output legitimately overwrites `$0801..$08F1`. The [rejected gate and its source](../../build/research/relax24/decoder-analysis/rejected-final-continuation-check/failure.json) remain preserved. The passing check observes the copy before decoding; no original decoder algorithm was patched.

## Reproduction and remaining work

```sh
rtk proxy build/research/tower-power/cpu-venv/bin/python research/relax24/decode_reader.py --outer
rtk proxy build/research/tower-power/cpu-venv/bin/python research/relax24/decode_reader.py
```

`--outer` reconstructs and validates the bit/LZ stage. The default command consumes that saved, hash-checked proof and validates the inner byte/RLE stage; it does not repeat the four-million-instruction outer run unnecessarily. Existing proof/source identities are checked before reuse.

All output lives under `build/research/relax24/decoder-analysis/`. `inner-decoded.ram` and its known mask describe established analysis memory; unowned startup RAM remains unowned. No downloaded host executable, native emulator or process-control action is used.

The reader's file-loading and article-decompression consumers, the meaning of the twenty five-byte-looking headers, and the original file containing Clarence's coding review remain open at this checkpoint. This work supplies decoded program bytes from which those questions can now be checked; it does not validate the cached transcription or turn the review into an author explanation of Second Reality.
