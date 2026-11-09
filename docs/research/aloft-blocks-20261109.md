# Aloft: original disk bytes to received C64 packets

The new passive reference derives the bytes deposited in the C64's `$0300..$03FF` buffer from original Aloft disk sectors. It combines the exact historical Sparkle drive tables, its four transfer phases, the C64 receiver, directory-pointer patches and block-count handling. All **1,024 GCR lane cases** and all **256 transfer byte cases** pass independently. A separately retained diagnostic compares the first predicted packet with the new native stop before depacking: **all 256 bytes match**.

The disk does **not** determine the real rotational delivery order. Sparkle deliberately fetches ordinary wanted sectors out of order and holds a transition sector until the other wanted sectors have been transferred. The exported packet plans choose ascending source-writer order. They do not claim that this was the observed native order or that all legal orders necessarily produce the same result with arbitrary prior-memory matches.

## Source boundary

The prior [loader](aloft-loader-20261109.md) and [drive/catalog](aloft-catalog-20261109.md) proofs remain frozen. The catalog proof reconstructs all six drive-code sectors on all three original disks from Sparta's historical source at commit `f354e3b52c9361bf89ebad4f2f1d43504c213381`, with zero mismatches. It also binds directory states to the exact source sector-order recurrence.

The new [disk_stream.py](../../research/aloft-decode-20261109/disk_stream.py) pins that proof and its pure catalog helper. It reads the original D64, source byte array and assembly as data. It does not invoke the upstream C++, an assembler, a 6502 interpreter, an emulator, a build or a native process.

The primary [Sparkle drive source](https://github.com/spartaomg/SparkleCPP/blob/f354e3b52c9361bf89ebad4f2f1d43504c213381/resources/sd.asm), [resident source](https://github.com/spartaomg/SparkleCPP/blob/f354e3b52c9361bf89ebad4f2f1d43504c213381/resources/sl.asm) and [packer](https://github.com/spartaomg/SparkleCPP/blob/f354e3b52c9361bf89ebad4f2f1d43504c213381/packer.cpp) supply the format and transforms. They are copyright Sparta/OMG under the [retained BSD 3-Clause license](../../build/research/aloft-20261109/loader-analysis/catalog-source-02/LICENSE).

The bit/pin cross-check uses source from the already pinned official VICE 3.10 archive, SHA-256 `8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1`. Four new copies are retained under [source-01](../../build/research/aloft-decode-20261109/block-analysis/source-01/), and each is checked byte for byte against its exact archive member:

| Official archive member | SHA-256 |
|---|---|
| `vice-3.10/src/gcr.c` | `293e5d0d447a8b482ecf7479a45638be8e109d21b4b6a1ec9081dbf331213ea7` |
| `vice-3.10/src/c64/c64cia2.c` | `5637b9e49542b6c953ef1a0ac53d5c0cdec1e5a3eecde5f6f01af5dca09d9ca4` |
| `vice-3.10/src/drive/iec/via1d1541.c` | `9e3bd44f61e4f20c64fbc7400e27c17e73f17e3db40af6284c172f7b172dd73b` |
| `vice-3.10/src/c64/c64iec.c` | `c6d79e742580474ecd7e117425391198e8e3d624a85b5eb72fb7a7122cf19950` |

These are source formulas for successful settled handshakes, not a new emulation of VICE or a timing model. Error recovery, rotation, analog signals and acknowledgement timing are outside this reference.

## Sector order and the two cancelling byte transforms

The original packer writes logical byte indices to disk in order `[0,255,254,…,1]` (`UpdateByteStream`, lines 99–127). The drive's successful data-read entry starts with SP zero; successive GCR-decoded bytes are pushed at `$0100,$01FF,$01FE,…`. The drive transfer and C64 receiver both use the same `0,255,254,…,1` destination sequence. Consequently the base received packet at index `i` corresponds to original sector byte `(-i)&255`.

The values also undergo two transforms. Define:

```text
f(v) = v XOR $7F  if (v AND $09) is $00 or $09
       v XOR $76  otherwise
```

The drive GCR tables produce `f(v)` from an ordinary raw sector byte `v`. The four-phase transfer and C64 receiver produce `f(d)` from drive-buffer byte `d`. Since `f(f(v))=v`, an unpatched byte reaches the C64 unchanged after the index permutation.

This is checked beyond repeating the writer's function name. The script takes the standard 16-entry GCR encoding table from official `gcr.c`, then evaluates **four distinct expressions over Sparkle's actual table bytes** for all 256 possible data values. The A/B, C/D, E/F and G/H lanes all yield `f(v)`, totaling 1,024 cases. The A/B lane includes the exact borrow-free subtraction from seven and its split lookup indices; an early incorrect nibble split and an off-by-one index were rejected and retained in [derivation-diagnostics.json](../../build/research/aloft-decode-20261109/block-analysis/diagnostics-01/derivation-diagnostics.json).

For the transfer, the four source write values for drive-buffer byte `d` reduce to:

```text
W1 = d AND $EF
W2 = ((d << 1) OR $10) AND $FF
W3 = (d AND $F0) >> 1
W4 = (d AND $C0) >> 3
```

The typed reference applies official VIA/IEC/CIA port equations to those four writes and the source-used C64 handshake outputs. It then combines the four received high-bit pairs using the C64 receiver's shifts and masks. All 256 values produce `f(d)`, and composition with each GCR lane reproduces the raw byte. The full [byte-transport-domain.json](../../build/research/aloft-decode-20261109/block-analysis/accepted-01/byte-transport-domain.json) retains each drive value, four port writes, four CIA input pairs and resulting received byte.

This pin contract requires the source configuration `$DD02=$3C` and one active 1541. It computes the data bits of successful transfers; it does not advance either CPU, check every bus acknowledgement or estimate elapsed cycles.

## Indexed starts, transition counts and shared blocks

The exact drive source distinguishes a randomly indexed first packet, an ordinary packet and a transition packet. The reference preserves that distinction:

| Packet kind | Received byte 0 | Received byte 1 | Received byte 255 |
|---|---|---|---|
| Indexed first | Forced to zero | Count removed; zero | Raw directory stream pointer |
| Ordinary | Original data | **Original data** | Original data |
| Transition | Original data | Count removed; zero | Original data |

`ChkLastBlock` at source lines 834–852 saves drive `$0101` as numeric `NBC`, then replaces it with drive `$7F`, which transfers as C64 zero. The original disk stores this count in the encoded domain, so `NBC=f(raw logical byte1)`. It is a transport count, not a resource count.

For a randomly indexed first block, the drive additionally replaces `$0100` with `$7F` and `$01FF` with its `BPtr`. The directory's fourth field was stored without host EOR encoding, but the GCR read transforms it: drive `BPtr=f(raw pointer)`. The final transfer transforms it again. Therefore the received C64 byte 255 is the **raw directory pointer**, not the transformed drive value. For example, raw slot-5 pointer `$3F` becomes drive `$40` and received C64 `$3F`.

The C64 decoder then owns its buffer mutations. It starts by reading byte 0; a zero makes it use byte 255 as the alternate bitstream cursor. On end-of-bundle it saves its new cursor in byte 255, and the next sequential call continues from that buffered state. The transport does not invent an initial decoder X value, clear arbitrary byte-1 values, or reconstruct a completed decoder buffer from a native snapshot.

For an indexed first block at writer ordinal `k`, the saved count `n` identifies the next count-transition block at `k+n`. Ordinary wanted blocks may arrive out of order; a fetched transition block is retained in the drive's second buffer until the other wanted blocks are delivered. After it is delivered, its saved `NBC` governs the following transfer group. A zero count makes further source-derived sequential packets unavailable. The provider raises `StopIteration`; a token decoder must treat premature exhaustion as a failure, not fill missing data.

The source's sharing of transition blocks matters: one packet can contain an earlier bundle's end and the next bundle's beginning. A transfer-group endpoint or a distance between directory slots is not a decoded resource boundary.

## Exported plans and consumer API

The pure provider returns immutable packet bytes and provenance:

```python
provider = DiskStream(original_d64_bytes, slot, side=1)
packet = provider.next_packet()
# packet['received']: bytes(256)
# packet['source']: original T/S, writer ordinal, count and patch provenance
```

The accepted data export uses schema `sparkle-received-packets-v1`. Each packet record has a filename relative to the plan, length 256, SHA-256 and source provenance. No native RAM or finished resource is an input.

| Plan | Original indexed first block | Raw pointer | First saved NBC | Export |
|---|---|---:|---:|---|
| [Slot 0](../../build/research/aloft-decode-20261109/block-analysis/accepted-01/side1-slot000-plan.json) | Ordinal 0, T1/S0 | `$FE` | 1 | Two packets through ordinal 1 |
| [Slot 5](../../build/research/aloft-decode-20261109/block-analysis/accepted-01/side1-slot005-plan.json) | Ordinal 63, T4/S1 | `$3F` | 70 | 71 packets through ordinal 133 |

These plans cover their first transfer group. The additional [sequential prefix](../../build/research/aloft-decode-20261109/block-analysis/sequential-prefix-accepted-01/side1-slot000-plan.json) exports the first **128** canonical packets from indexed slot 0 for a decoder that retains its own buffer and cursor between calls. Its first two packets are byte-identical to the original slot-0 export. Its fixed endpoint is inside a later transfer group, not a resource or effect boundary. This extra data job invokes the pinned pure provider and leaves the accepted transport producer unchanged.

The prefix plan is 114,004 bytes, SHA-256 `144709e90b2b5317f7a20d6340f9d315d8e8fc5c84fe325319bb68982461cbef`. Its [export proof](../../build/research/aloft-decode-20261109/block-analysis/sequential-prefix-accepted-01/prefix-export-proof.json) is 27,801 bytes, SHA-256 `ac3b5f1f0f2731a51d1a6bbbfaf658869b588d842088ce0c130256d501d63e61`. Match dependencies, unknown prior memory, file/bundle terminators and complete resource equality belong to the separate token-decoder proof.

## Replay and native-comparison boundary

The transport source is 16,436 bytes, SHA-256 `aac8825edab2375d100c0f8f41a5c3eb93c48cc3288e97eba58ef3c0778fe256`. Its [accepted proof](../../build/research/aloft-decode-20261109/block-analysis/accepted-01/block-proof.json) is 17,737 bytes, SHA-256 `768a37475c5e8e07c73fc8e0ab64c5ef80eea508212e462a3e8b58b8033e6ec3`.

```sh
rtk proxy python3 -B research/aloft-decode-20261109/disk_stream.py \
  --output build/research/aloft-decode-20261109/block-analysis/new-replay
```

A fresh replay reproduces all **78 files / 198,287 bytes** exactly; [self-replay-check.json](../../build/research/aloft-decode-20261109/block-analysis/self-replay-check.json) is retained. The separate bounded prefix export reproduces all **131 files / 177,838 bytes** exactly; see [sequential-prefix-self-replay-check.json](../../build/research/aloft-decode-20261109/block-analysis/sequential-prefix-self-replay-check.json). Earlier candidate output is retained.

The first predicted packet has SHA-256 `f0d37eb0b4cab29552efd727381fb64f5a31f0cd01d2eb000a6eb815b64de8a6`. A [separate diagnostic comparison](../../build/research/aloft-decode-20261109/block-analysis/native-probe-01/first-packet-concordance.json) compares it against the new natural `$021C` capture before depacking, with zero mismatches over `$0300..$03FF`. The native case was still live when that diagnostic was made; it is explicitly not a substitute for closed-case custody and source/request association. Neither that packet nor any completed native resource seeded this transport.

This source proof establishes successful byte transport and the declared canonical packet plans. Actual rotational order, all-order output equivalence, complete resource decoding, target-effect identity, display pixels and delivered frame rate remain separate questions.
