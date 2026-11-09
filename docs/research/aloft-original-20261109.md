# Aloft: original archive and authentic DOS bootstrap

The retained Aloft release contains three disks, and **all three contain the same authentic 832-byte DOS bootstrap**. Each disk's 48 decorative PRG entries points to that one four-sector chain. There are 144 directory rows across the disks, not 144 independent programs. BASIC loads the PRG at **$0801** and executes **`SYS 2064` → $0810**.

This is a passive archive/directory/sector-chain result. It establishes bytes and their original provenance; it does not execute the bootstrap or identify its loader/depacker algorithm, loaded effects, input consumers or display mechanism. Those belong to separate source/native lanes. In particular, identical bootstraps do not prove that side 2 or side 3 can start independently with their intended scene.

The accepted [disk-proof.json](../../build/research/aloft-20261109/disk-analysis/accepted-01/disk-proof.json) is **19,558 bytes**, SHA-256 `113eadc069fbf46bb1011d7c9373d175f4c3536950f7a7ee173f471b8f1eef84`. Its [producer](../../research/aloft-20261109/disk.py) is **11,134 bytes**, SHA-256 `a51191d3a91546f871a9de11910a50e1390e13b2a81deda57a9b801138a477a9`.

## Original bytes and earlier research

The existing [February source receipt](../../build/research/frontier-2026/february-analysis/source-findings.json) records acquisition directly from the [CSDb original download](https://csdb.dk/getinternalfile.php/276871/Aloft.zip): HTTP 200 on **7 November 2026 at 14:38:06 UTC**, with unchanged requested/final URL. That receipt is 38,114 bytes, SHA-256 `8d809ffeffcca90f1bcf7bfb65e99533ab705b6b7013b29b9d5112dbb3276f42`. This lane verifies its archive identity and every regular-member hash without making another network request.

The original [aloft-original.zip](../../build/research/frontier-2026/february-analysis/aloft-original.zip) is **419,712 bytes**, SHA-256 `275c0873b84dcea8ef03210506481f605e93f9f9b263bd5ce4c75dc39a7a1203`. Its eight ZIP entries are three D64 files, four SID files, and the empty `SID/` directory. There is no separate assembly/text-note member. That statement does not rule out code or notes embedded in a disk's custom resources.

| Original disk, copied unchanged | Bytes | SHA-256 |
|---|---:|---|
| [Aloft-Side1.d64](../../build/research/aloft-20261109/disk-analysis/accepted-01/Aloft-Side1.d64) | 174,848 | `d13eae8daeada64bc61772a2dad2d3e62d1a0d30a34b29103119535610e4cfce` |
| [Aloft-Side2.d64](../../build/research/aloft-20261109/disk-analysis/accepted-01/Aloft-Side2.d64) | 174,848 | `a40374bc8b59ab13c06d577331dde5d3ccaef23ef5b434762d8ed9700b944d31` |
| [Aloft-Side3.d64](../../build/research/aloft-20261109/disk-analysis/accepted-01/Aloft-Side3.d64) | 174,848 | `3b2844016e697111fa8ccd1e419bb281e4ffa04ae3f542f01b0ef39f91719a1e` |

The four preserved SID members are `Psych858o-Cloudracer.sid`, `Psych858o-VectorFlight.sid`, `Psych858o-VelvetFrequencies.sid` and `Steel-Butterflies.sid`. Their hashes and ZIP CRC/compression metadata are in the receipt; their contents are not executed or interpreted in this lane.

The earlier [author/source note](february-2026.md) and [primary follow-up](frontier-effects-followup.md) supply the historical research boundary: original archive/notes were retained, while disk internals and target code were then undecoded. No earlier Aloft native capture or decoded effect resource was located in those notes/producers. The three-layer moving pattern, Sparta's author-linked **side-2 joystick/flipped-Kefrens interaction**, and the separate bitmap-Kefrens peer observation must remain distinct until their actual instruction/data domains are identified. The artist's airplane sprite count is a different asset statement, not a representation claim about those effects.

## Directory art and real file chain

Every disk is an exact 35-track D64: **683 × 256-byte sectors**, with no appended error map. The parser uses the standard 21/19/18/17-sector track zones, bounds-checks every sector and rejects cyclic directory or file links.

The BAM points to directory track 18/sector 1. Directory sectors **18/1 through 18/6** contain 48 nonempty closed-PRG entries each. The first filename is the side's title; later filenames form PETSCII directory art. All raw 32-byte entries and PETSCII name bytes are preserved in [directory-inventory.json](../../build/research/aloft-20261109/disk-analysis/accepted-01/directory-inventory.json), **109,653 bytes**, SHA-256 `caa974cc879ef92ffcf974d1c5d9fc435189db0ac08aa6021ee449f60f44b6af`.

For every one of the 144 rows, file type is **$82**, first track/sector is **18/7**, and its recovered content hash is the bootstrap hash below. The first entry declares four blocks; the other 47 entries on that disk declare zero blocks. Those zero counts do not denote empty or additional files: following their actual links recovers the same bootstrap.

| File sector | Next link | Data bytes appended |
|---|---|---:|
| 18/7 | 18/8 | 254 |
| 18/8 | 18/9 | 254 |
| 18/9 | 18/10 | 254 |
| 18/10 | track 0, final count byte 71 | 70 |

The final-sector count is interpreted as the last used byte index plus one, so 71 contributes 70 data bytes after the two link/count bytes. Total PRG length is **832 bytes**, including its two-byte load address. Each source-sector offset, full-sector hash, data hash and link is retained. The three source disks independently recover byte-identical content.

## Bootstrap entry and natural source guards

The authentic recovered PRGs are [bootstrap-side1.prg](../../build/research/aloft-20261109/disk-analysis/accepted-01/bootstrap-side1.prg), [bootstrap-side2.prg](../../build/research/aloft-20261109/disk-analysis/accepted-01/bootstrap-side2.prg), and [bootstrap-side3.prg](../../build/research/aloft-20261109/disk-analysis/accepted-01/bootstrap-side3.prg). Each is **832 bytes**, SHA-256 `7e283e390a10c2b7784ac1885081234c21a754d161e938babd504a13da2ee2e5`.

The PRG load word is `$0801`; its 830-byte payload occupies **$0801–$0B3E**, end exclusive $0B3F. The BASIC line is line 10 with next-line pointer $080B and tokenized `SYS 2064`. Three padding zeros precede the machine entry $0810. The entry prefix is:

```text
$0810: A9 FF 85 FC A2 04 A9 08 85 BA A5 BA 20 0C ED
       A9 6F 20 B9 ED 30 3A A5 BA 85 FB 20 FE
```

This gives a precise original-byte guard for a future **natural** startup observation. It is not permission to assign the program counter or inject the decoded payload, and it is not a claim that a custom-file entry equals $0810. The loader/code-localization lane owns subsequent setup, relocation, decoding, resource selection and any proposed later PCs.

The initial quick [source-01 extraction](../../build/research/aloft-20261109/disk-analysis/source-01/source-extraction.json) remains retained. Its disk and bootstrap bytes are identical to accepted outputs. It was supplied promptly for original source inspection and is superseded by the repeatable complete directory/chain receipt above.

## Replay and continuation

Fresh passive self replay reproduced **all 13 output files / 688,392 bytes exactly**. [self-replay-check.json](../../build/research/aloft-20261109/disk-analysis/self-replay-check.json) is 2,139 bytes, SHA-256 `c8fd36bf8b16073359004c3c6515e612d31bf3c97bc6a74e53ea99df811c98ce`.

Two failed producer attempts remain intact: candidate-01 used a wrong dictionary field name for directory-page sectors; candidate-02 had an overlong literal for the 15-byte BASIC/padding guard. Their checked sources, partially extracted original bytes and failure receipts are preserved in fresh directories. Neither accepted a source/loader interpretation or changed prior artifacts.

For another offline replay, choose a new directory:

```sh
rtk proxy python3 -B research/aloft-20261109/disk.py \
  --output build/research/aloft-20261109/disk-analysis/replay-NEW
```

The next source step can consume the original D64s and authentic PRG directly. Bind the actual bootstrap/resident bytes to primary loader source before choosing a decoder or part entry. Keep directory aliases separate from the custom resource inventory, and distinguish a published version/family resemblance from a complete source-byte match. Native/emulator control remains a separate owner responsibility. This lane provides no bootstrap runtime result, target identification, image, cycle budget, FPS or product change.
