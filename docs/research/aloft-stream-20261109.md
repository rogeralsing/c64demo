# Aloft: original compressed tokens to two verified loaded bundles

The original stream now produces concrete program bytes without running a C64 CPU: **two consecutive logical bundles, 13 source packets and 5,977 decoded RAM bytes**. An independent checker subsequently matches every predicted payload byte against the fresh natural native returns. The decoder starts with **unknown RAM**, derives its own buffer cursors, and receives no expected native bytes.

Current [accepted-01/stream-proof.json](../../build/research/aloft-decode-20261109/stream-analysis/accepted-01/stream-proof.json) is **5,432 bytes**, SHA-256 `26c58f950464d7e37d94d99ecb19c79584004f5458306c0d3979168cb5c91b09`. The frozen [depacker.py](../../research/aloft-decode-20261109/depacker.py) is **21,886 bytes**, SHA-256 `180b2835ea06f7f7ae4d15d765eb3c64c9518f8d03fc6ee350d33ce9eccef036`.

This is a typed compressed-format decoder. It handles headers, sentinel bits, paired nibbles, literals, matches and termination tags. It does not fetch or execute arbitrary 6502 instructions, emulate a drive, run a downloaded host program, or infer an effect from a bundle number.

## Separate source, transport and native responsibilities

The [original archive/bootstrap study](aloft-original-20261109.md), [loader identity](aloft-loader-20261109.md) and [historical disk catalog](aloft-catalog-20261109.md) retain their frozen boundaries. The [packet transport study](aloft-blocks-20261109.md) owns disk sectors, byte permutation, GCR/IEC value transformations, indexed stream-pointer injection and source-valid packet scheduling. This decoder consumes its exact deposited 256-byte packets.

The token source is historical Sparkle commit **`f354e3b52c9361bf89ebad4f2f1d43504c213381`**, including `resources/sl.asm`, `loader.cpp` and `packer.cpp`. The historical C++ array contains an 832-byte reference installer. Its **last 416 bytes match all 416 original Aloft resident bytes**, SHA-256 `b09c13f9f60a28aa87cf1b157b4035df325eb60bf6d79fe8f176cf7aa606db48`. The complete installers differ; resident equality does not establish an exact host-tool version or build date.

[grammar-source-anchors.json](../../build/research/aloft-decode-20261109/stream-analysis/accepted-01/grammar-source-anchors.json) preserves source identities, exact line fragments, original-bootstrap binding and resident equality. [writer-format-anchors.json](../../build/research/aloft-decode-20261109/stream-analysis/accepted-01/writer-format-anchors.json) separately retains the packer's buffer, bit, nibble and five match constructions. These files are parsed as source/data; they are not compiled or executed.

The independent [native stream binding](aloft-stream-binding-20261109.md) owns the subsequent actual packet/return comparisons. It reads the pinned predictions after their production. Native first-packet RAM, native loaded program bytes, screenshots and native cursors do not seed this decoder.

## Packet and buffer state

The resident buffer is **$0300–$03FF**. The backward byte cursor is eight bits; source absolute-indexed literal addresses and decoded target/reference addresses use the resident's 16-bit address arithmetic.

On each newly received packet, `LoadNext` resets the paired-nibble cache and starts at buffer index 0. A nonzero byte there supplies the first bitstream byte. A zero redirects through **Buffer[$FF]**, which supplies the saved cursor or indexed starting pointer. The transport's indexed first-packet patches therefore remain part of the packet input, not a guessed decoder parameter.

After taking the first bitstream byte, the cursor moves backward to the destination header. The resident clears Buffer[0] to zero. At end of a bundle, it saves the next byte cursor into Buffer[$FF]. A subsequent sequential call uses that saved value and the remaining bytes in the same packet. It does not start again from a fresh zero-filled buffer or request a packet unnecessarily.

For these original bundles, the decoder independently derives:

- After bundle 0: **LastX=$2A**, packet ordinal 1 still resident.
- After bundle 1: **LastX=$12**, packet ordinal 12 still resident.

The output [typed-tokens.json](../../build/research/aloft-decode-20261109/stream-analysis/accepted-01/typed-tokens.json) records both transitions. The native values are later comparisons, not inputs.

## Interleaved sentinel bits and paired nibbles

The initial bitstream byte has a sentinel in its low bit. A bit request shifts the current bit state left. If the sentinel is exhausted, a byte is taken from the **same backward byte cursor** that supplies headers, lengths, tags and literal data. Its high bit becomes the requested bit, and an inserted low sentinel records the remaining bits. There is no separate flat bitstream file.

After a match, a control bit selects another match (`1`) or a literal (`0`). A file/header starts directly at the literal-length selector; it omits that type bit. A literal is always followed by a match, so the following match also omits the type bit. Treating every token as a uniformly prefixed record would misalign this format.

Literal lengths are encoded as:

| Length selector | Additional input | Decoded length |
|---|---|---:|
| 0 | None | 1 |
| 1 | Nonzero length nibble `n` | `n+1`, normally 2–16 |
| 1 | Zero nibble, then byte `b` | `b+1`, writer normally 17–251 |

Two length nibbles share a byte: **low nibble first, high nibble next**. The pending high nibble survives file transitions inside a block. A new packet or a new sequential bundle call resets that cache, matching `MidLitSeq`'s source state. The implementation also preserves the resident's eight-bit Y behavior for noncanonical encoded lengths; those forms are not claimed as native-validated by this two-bundle result.

## Backward literals and matches

A header's destination is the highest byte of the next output fragment. For length `L`, the destination pointer moves backward by `L`, modulo 65,536. The copy then runs in descending Y order. Literals read their bytes from the current buffer/known memory state. Matches read already known higher/reference addresses; overlapping copies observe bytes written earlier in that same descending operation.

The match forms are:

| Match form | Backward byte sequence | Length | Distance |
|---|---|---:|---:|
| Short | `ooooooLL`, low two bits nonzero | `LL+1` | `(tag>>2)+1` |
| Near mid | `1LLLLL00`, low offset | `(tag & $7C)>>2` | `low+1` |
| Far mid | `0LLLLL00`, high offset, low offset | `(tag & $7C)>>2` | `(high<<8)+low+1` |
| Near long | `$84`, length, low offset | Encoded length | `low+1` |
| Far long | `$04`, high offset, length, low offset | Encoded length | `(high<<8)+low+1` |

Addresses wrap at 16 bits. The decoder copies one byte at a time, preserving overlap semantics rather than reading an entire match from a stale snapshot first. The two accepted bundles exercise **all five match classes**, including **58 overlapping matches**. Their class counts are 450 short, 150 near-mid, 21 near-long, 20 far-mid and two far-long. Source-derived address-wrapping support does not mean a native wrapping example was captured here.

## Headers, flags and termination

Headers read destination low byte, then high byte. A zero high-byte position introduces an extra high byte: a nonzero extra byte selects **CPU port $34**, allowing RAM beneath I/O; an extra zero denotes a zero-page destination with **$35** retained. Ordinary nonzero high bytes use $35.

Termination is part of the match grammar:

- **$00** requests another received block; the new packet reinitializes bit/nibble state and supplies a new fragment header.
- **$80** introduces another file/header inside the current block. The bit and paired-nibble state continue.
- **$84, $00** ends the bundle and saves LastX for the next sequential call. The resident's corresponding far-long zero-length path is represented as a bundle end as well.

Destination headers can restart a fragment of the same logical file after a block transition. Header counts therefore are not asserted to count independent original PRGs or named effects.

## Unknown memory stays unknown

Every RAM byte starts unknown. It becomes known only from an original source packet, an explicit buffer-metadata mutation, or a completed decoded RAM write. A match reading outside that known map stops with the exact source address, packet and token context. The decoder does not substitute zero, a VICE power-on pattern, old native RAM or an expected image.

Visible-I/O writes are recorded as raw bus writes separately from physical RAM. An I/O-visible read stops because actual device readback is outside this format model. Decoded output that aliases the active CPU ports, zero-page loader control bytes or resident code also stops rather than pretending that the token grammar survives arbitrary self-modification. The two verified bundles use $35, produce no decoded I/O writes and encounter no unknown dependency.

The three binary exports have different roles:

- `predicted-memory.bin`: byte values, with an explicit companion known mask; placeholder bytes in unknown positions have no evidentiary value.
- `known-memory-mask.bin`: current source-known RAM, including the format buffer.
- `decoded-RAM-write-mask.bin`: the decoded payload comparison mask, distinct from packet/control metadata.

Every decoded RAM write records its token, source address and source provenance. [byte-and-bit-reads.json](../../build/research/aloft-decode-20261109/stream-analysis/accepted-01/byte-and-bit-reads.json) retains the cursor/refill decisions. These are typed data operations, not an instruction execution trace.

The accepted decoder also requires a **frozen original-source transport receipt** and verifies its plan/packet output hashes. An arbitrary JSON file with self-declared packet hashes is insufficient for the accepted command-line path.

## Two-bundle result and independent native checks

The original indexed start is slot 0. The second bundle continues from the independently derived first return state, retaining its buffer and LastX; no native prestate is inserted.

| Logical bundle | Newly decoded RAM bytes | Written address spans, inclusive | Derived return cursor |
|---|---:|---|---:|
| 0 | 493 | $0800–$08DF, 224 bytes; $FE00–$FF0C, 269 bytes | $2A |
| 1 | 5,484 | $08FF–$1E6A | $12 |

The total is **5,977 distinct payload bytes**. The decoder uses 13 packets and emits 1,142 typed events. Its first three destination headers span two output regions; the second bundle's twelve headers are fragments of its contiguous span. No whole-side resource count follows.

Independent comparisons were performed only after these outputs were pinned:

1. All **493** first-bundle payload bytes match the fresh natural **$FE00** return.
2. At the subsequent natural **$FE41** request, all **749** previously known bytes remain equal to the source prediction, including all 256 buffer bytes. The unrelated application write at $08FF was to a position that was still unknown to this model and was not seeded into it.
3. All **5,977 payload bytes**, and all **6,233 known bytes** including the final format buffer, match the fresh natural **$FE44** second return. The independently derived LastX=$12 matches the actual saved byte.

The separate [binding study](aloft-stream-binding-20261109.md) owns exact native capture identities and predicates. Endpoint equality does not simulate every intervening application or interrupt write. The format model's continued source memory is explicit; arbitrary application mutation between future calls remains outside its semantics.

## Retained unknown and source-only exploration

Indexed slot 5, decoded alone from unknown RAM, stops at **$C326**, first packet, typed match event 8. Both the earlier candidate and the strict receipt-gated repeat remain retained under `candidate-02` and `candidate-04`. They preserve the source, partial outputs and exact diagnostic. No captured menu/bitmap RAM was supplied to get past the dependency.

The same frozen decoder was then run in a separate data-only exploration from slot 0 through a 128-packet source prefix. It completed logical bundles **0–4**, began bundle 5 and stopped at the explicit plan-exhaustion boundary after packet 127. It produced **58,378 RAM-write operations** without I/O writes or a native-memory seed. Crucially, source bundle **4**, packet **36**, event **3318**, writes **$C326=$CC**, providing a legitimate earlier-stream prerequisite for the isolated slot-5 stop.

[exploration-01/exploration-report.json](../../build/research/aloft-decode-20261109/stream-analysis/exploration-01/exploration-report.json), **5,749 bytes**, SHA-256 `9f8ad928b97bb5c1d991f24713e79b4797cd95f957633310de37909304cbabbf`, pins the frozen model, completed tags, partial state and failure files. Only bundles 0/1 have the independent native comparisons above. Later bytes and the partial sixth bundle are **unverified software-format predictions**, under a declared canonical packet order and without intervening application execution.

The transport provider deliberately supplies a source-valid canonical writer order. Real ordinary sectors can arrive out of order. No all-delivery-order equivalence, measured IEC waveform, full animation, scene identity or execution trace is inferred from that choice.

## Replay and continuation

Fresh self replay reproduced **all 13 accepted files / 5,524,075 bytes exactly**. [self-replay-check.json](../../build/research/aloft-decode-20261109/stream-analysis/self-replay-check.json) is 2,158 bytes, SHA-256 `6fcbcee3c0aa544981ea4c0f1191dc8b1231264b67e46f6279ac6186d7fa8b67`.

Root independently read the complete decoder and primary resident lines 363–611, then reproduced those 13 files / 5,524,075 bytes exactly. [root-replay-check.json](../../build/research/aloft-decode-20261109/stream-analysis/root-replay-check.json), **3,093 bytes**, SHA-256 `72ea223efefad657eb449c1d576ac1d5a267cc748ab01eea34555dbfa75df8b4`, records the successful fresh `root-replay-02`. The earlier root attempt used a nonexistent plan filename and decoded no tokens; its checked source, grammar anchors and failure diagnostic remain retained. No decoder change was made to repair that invocation.

The accepted two-bundle replay command is:

```sh
rtk proxy python3 -B research/aloft-decode-20261109/depacker.py \
  --packets build/research/aloft-decode-20261109/block-analysis/sequential-prefix-accepted-01/side1-slot000-plan.json \
  --bundles 2 \
  --output build/research/aloft-decode-20261109/stream-analysis/replay-NEW
```

Continue source-only exploration in a new job/output directory, using the same frozen decoder and a separately pinned original transport export. Stop at the first genuine unknown read, unsupported hardware/control dependency, source exhaustion or terminal condition; preserve partial state. Do not extend the two-bundle native-verified claim merely because later mathematical decoding succeeds. Associate later original byte ranges with actual native generations before identifying the remaining pattern/Kefrens scenes or examining their renderer. No pixel, cycle/FPS, physical hardware, optimization or product change is established by this receipt.
