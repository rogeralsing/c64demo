# Aloft: source-derived ColorRAM copies with unknown bus high bits

A separate four-bit device adapter carries the unchanged token decoder past its genuine ColorRAM-read boundary. Starting with **unknown RAM and unknown ColorRAM**, it consumes the original 597-packet side-one plan, observes **43 completed logical bundle-end markers**, and then stops while attempting the next bundle because the packet plan is exhausted. It preserves each completed source generation for independent later comparisons. This is a bounded software prediction, not proof that side one contains 43 named resources or that every predicted state occurred unchanged at runtime.

The accepted [color-stream-proof.json](../../build/research/aloft-decode-20261109/color-analysis/accepted-01/color-stream-proof.json) is **110,630 bytes**, SHA-256 `44bbc6a94b22db33d81dc9f15178f1303a2db19fb22484292e0c6f894f00f4b2`. The new [color_memory.py](../../research/aloft-decode-20261109/color_memory.py) is **17,627 bytes**, SHA-256 `b9ff969afb07320621dad0f107fc31a343a3e34c06566356143f9d8870cbd2c6`.

The original [strict stream decoder](aloft-stream-20261109.md), its two native-verified bundles and every earlier output remain frozen. Its source hash stays `180b2835ea06f7f7ae4d15d765eb3c64c9518f8d03fc6ee350d33ce9eccef036`. This module changes only the memory interface used by those same token operations. It does not alter their grammar, cursors, lengths, offsets or scheduling.

## The preserved RAM-only stopping point

The earlier full-side source exploration completed bundles 0–21 and stopped during attempted bundle 22, packet ordinal 385. Its first two literals write I/O-visible **$DBE8=$0C** and **$DBE7=$0F**. A following short match, length 2 and distance 1, reads **$DBE7**. CPU port $35 maps that read to the ColorRAM device, not the physical RAM byte at the same address.

The frozen RAM-only model correctly refused that read. [all-side1-exploration.json](../../build/research/aloft-decode-20261109/stream-analysis/all-side1-exploration-01/all-side1-exploration.json), 58,430 bytes, SHA-256 `ffc37070df52d17beb032e521a51b3c6fc42b068ab170f471fdf5a8871a11409`, retains the diagnostic, 22 completed per-bundle states and partial state. No zero, captured device byte or native RAM was substituted. Those artifacts were not changed to make the extension pass.

The new question is narrower: after the original stream itself writes $0F to that ColorRAM cell, which bits of the subsequent read are known, and which bits does its destination actually consume?

## Primary hardware rule and partial values

Pinned VICE 3.10 cycle-exact C64 memory source, `src/c64/c64memsc.c:597–605`, implements:

```text
write: device[addr & $3FF] = value & $0F
read:  device[addr & $3FF] | (VICphi1 & $F0)
```

The normal I/O mapping in `c64meminit.c` installs those functions for pages $D8–$DB. [primary-ColorRAM-source.json](../../build/research/aloft-decode-20261109/color-analysis/accepted-01/primary-ColorRAM-source.json) retains the exact archive/member hashes and line fragments. The archive SHA-256 is `8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1`.

Thus a source-established device value $0F does **not** justify pretending that the next CPU read equals full byte $0F. Its possible high nibble comes from the live VIC bus. The adapter returns an opaque partial value:

```json
{
  "value_bits": 15,
  "known_mask": 15,
  "unknown_mask": 240,
  "full_byte_value_not_asserted": true
}
```

That represents `$0F,$1F,…,$FF`, with the low nibble fixed. The zero bits outside `known_mask` are representation placeholders, not an assertion about the bus. No native high nibble, fixed default or simulated VIC bus value is used.

A subsequent ColorRAM write consumes only the four known low bits. It can therefore propagate the known device color while retaining an explicitly partial raw bus record. A full RAM destination, or another unsupported I/O destination, requires a complete byte and stops if any required bit is unknown. The adapter does not silently extend the ColorRAM rule to other devices.

## Device state stays separate from underlying RAM

The adapter starts all **1,024 ColorRAM cells unknown**. Source writes establish their low four bits. A read of a cell whose low bits have not been established stops. Native initial colors, the emulator's power-on pattern and earlier scene screenshots are not inputs.

Physical RAM and device ColorRAM are separate planes:

- With port $35, $D800–$DBFF reads/writes use the device plane.
- With port $34, those same addresses use underlying RAM through the unchanged decoder memory interface.
- A device write establishes no RAM byte. A RAM write establishes no device color.

The [partial-bit contract](../../build/research/aloft-decode-20261109/color-analysis/accepted-01/partial-bit-contract.json) checks all 256 concrete low/high nibble combinations against the projection rule. Additional synthetic checks prove that unknown initial device reads fail, a known-low partial copy to another ColorRAM cell succeeds, partial copies to RAM/$D020 fail, and RAM-under-I/O remains distinct. These checks use their own temporary memory instance; none of their values seed the original stream run.

Other full-byte I/O writes remain raw records, as in the frozen model. Their device effects are not simulated. Other device reads still fail closed.

## Why unknown payload high bits cannot choose a different token

This extension requires more than a four-bit sink rule. A copied partial byte must not influence token control through unmodelled accumulator flags or the resident's self-modified nibble cache.

[partial-copy-control-source.json](../../build/research/aloft-decode-20261109/color-analysis/accepted-01/partial-copy-control-source.json), **5,283 bytes**, SHA-256 `58a0c92c8be919622a8701aa51251527d5b383c9399e000648a31830aa9fa37f`, binds the argument to the exact historical resident source already matched to all 416 original resident bytes. It retains these source domains:

| Source lines | Relevant dependency |
|---|---|
| 507–522 | Literal A replacement and LDA/STA/DEY/BNE copy. |
| 528–553 | A replacement from a full packet match tag; descending match copy. |
| 559–575 | Decisions from known bit state, refill from a full packet byte. |
| 581–601 | Cached nibble, forced-carry ROR marker, later replacement of A. |

Inside each copy loop, LDA may set unknown N/Z from a ColorRAM read, but **DEY replaces those flags before BNE**. The known Y counter controls loop continuation. A following match replaces A with its full packet tag; a single literal replaces A through TYA from known Y=0; bit refill likewise loads a full packet byte.

The subtle path is a pending cached nibble: it may rotate the previous partial A when saving the next cache marker. Entry to that multi-literal path has **known carry 1**, so ROR forces the marker's sign bit to 1 regardless of every old A bit. The next LDY-immediate/BPL consumes that sign only; its negative path replaces Y/A from a fresh packet nibble before using a length. Immediately after saving the marker, TYA/ANC also restores A from the known cached nibble before destination arithmetic.

An exhaustive 256-A marker domain is retained with the bit contract. The frozen decoder's cache state—no pending nibble, or one known pending nibble—preserves those dependencies. Decoded output writes of partial payload bytes into RAM/buffer/resident control are rejected. The resident's internal cache-marker STA can retain unknown lower marker bits; the typed cache models its known sign and does not claim a full known resident RAM byte. Headers, lengths, tags and pointer arithmetic remain full known values. This is a source-backed abstraction argument for the guarded copy paths, not an interpreter for arbitrary 6502 code.

## Original packet run and comparison boundary

The input is the separately pinned original [all-side1 transport proof](../../build/research/aloft-decode-20261109/block-analysis/all-side1-accepted-01/all-side1-proof.json), SHA-256 `093a3f02ef4e05987d93f9d8f58199623dab47c9502b9aee804072f0bd9bb2eb`, and its 597-packet plan, SHA-256 `6f2dcbc22c112f4c902ca0fd1d6e9e9f6d07126fa7a3a0fd91559491eab5914e`. The provider's source-valid canonical ordering remains explicit; no equivalence across every real rotational order is proved.

The adapter's original-data run produces:

| Result | Count |
|---|---:|
| Completed logical bundle-end markers | 43, labelled 0–42 |
| Source packets consumed | 597 |
| RAM write operations | 325,106 |
| I/O bus write operations | 1,281 |
| Partial ColorRAM reads | 1,233 |
| Bus writes carrying unknown high bits | 1,233 |
| Device cells with established low nibble | 1,001 of 1,024 |

It then stops in attempted bundle 43 on **original source packet-plan exhaustion**. One additional partial RAM-write operation after the last complete marker remains explicitly partial state; it is not promoted to a complete resource. The underlying transport reached its original count-zero terminal packet, leaving its separately retained unused regular sectors outside the received plan. Neither 43 markers nor that count-zero boundary is asserted to count original files, effects or meaningful application resources.

All first **22 completed RAM generations** match the earlier frozen RAM-only predictions byte for byte, **after** each new prediction is produced. The old files are comparison targets, never initial memory. Candidate-01 is retained unchanged; final accepted-01 adds the requested resident control-source anchors with identical decoded data predictions.

The two original bundles in the [strict stream/binding studies](aloft-stream-binding-20261109.md) retain their independent native checks. Everything later in this device-aware run is source-only until a separate late comparison establishes the exact matching native generation. No native colors, bus values, mismatch masks or screenshots are fed into this model.

The separate [decoded-part association study](aloft-decoded-parts-20261109.md) subsequently matches **23 complete declared code/data windows** to the old native generations. Those are specific late byte comparisons with their own masks and generation identities. They do not turn all 43 source states, device colors, or displayed fields into native-verified results.

## Preserved per-bundle generations

For each completed marker, the proof's `completed_bundles[i].files[]` lists six files by output-relative name, byte size and SHA-256:

- `bundleNNN-memory.bin`, `known-mask.bin`, `cumulative-write-mask.bin` and `delta-write-mask.bin` retain source RAM and its knowledge/write scopes.
- `bundleNNN-ColorRAM-low-bits.bin` and `ColorRAM-known-mask.bin` retain the separate device plane. A known cell has mask $0F; an unknown cell's placeholder value has no color claim.

The delta mask identifies decoded RAM destinations in that bundle. Earlier source generations remain available even after later bundles overwrite the same addresses; comparing end-of-disk RAM with an earlier native capture would be invalid.

`typed-tokens.json` preserves token chronology. `IO-write-events.json` includes explicit partial bus masks, and `partial-ColorRAM-read-events.json` preserves the device-low provenance and the unbound VIC-bus high bits. Partial final RAM/device states and the exact stop are retained separately. No pixels, CPU/IRQ execution, application mutation between loads, physical IEC transfer or hardware timing is reconstructed.

## Replay and continuation

Fresh self replay reproduced **all 272 accepted files / 35,913,692 bytes exactly**. [self-replay-check.json](../../build/research/aloft-decode-20261109/color-analysis/self-replay-check.json) is 44,837 bytes, SHA-256 `36104f5e79b349f9468c2a1ba963acdec3fe75c5b5b8c035241c59563c1a90f9`.

Root reviewed the complete final extension and its added resident ASM anchors without finding a material issue. An independent peer reviewed the partial-value/control argument and ran a fresh replay: **all 272 files / 35,913,692 bytes match exactly**. [peer-replay-check.json](../../build/research/aloft-decode-20261109/color-analysis/peer-replay-check.json), **48,264 bytes**, SHA-256 `9bfa50a89b84449eb0444b5562511746e957dc7b4129f7dd140f644058c32875`, also pins exact resident machine-byte guards and independently checks 4,096 prior-A/cached-nibble combinations. It preserves the distinction between decoded full-byte sinks and the internally abstracted cache marker. No decoder, adapter or accepted-output change was needed after review.

```sh
rtk proxy python3 -B research/aloft-decode-20261109/color_memory.py \
  --output build/research/aloft-decode-20261109/color-analysis/replay-NEW
```

Continue by pinning a completed source generation and its complete known/delta masks before opening the corresponding original native code/data as a comparison target. Identify a part through actual bytes and load boundaries, rather than assuming that a capture alias, software counter, directory slot and logical marker number are interchangeable. Keep native-verified bytes, source-only predictions, device-low knowledge and unbound high bus bits distinct. A later named-scene or renderer proof requires its own source/native binding; no complete animation, full-side output, FPS, physical-hardware, optimization or product result follows here.
