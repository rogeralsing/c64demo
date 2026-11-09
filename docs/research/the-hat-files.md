# The Hat: original disks, shared bootstrap and raw stream directory

Research date: 8 November 2026. The original release contains two ordinary
35-track D64 images. Both DOS directories have **48 artwork aliases**, all
pointing to the same eleven-sector bootstrap chain at track 18, sector 2.
The bootstrap PRG is byte-identical on both sides. The custom stream
directory describes **43 side-A resources and 19 side-B resources** in a
layout documented by the retained Bitfire writer source.

The new passive [extractor](../../research/the-hat/disk.py) recovers all 62
raw payloads and their exact physical byte segments. It does not decompress
them, execute the loader or identify the final upscroller by file number.
That source-to-effect binding remains a separate original-machine and
decompression task.

## Original release identity

The ZIP was previously obtained through the production's own download
route. Its archived acquisition is owned by the [February source study](february-2026.md).
The current extractor opens that retained ZIP, checks its literal hash,
reads every member with ZIP CRC checking and compares the two released
disk copies with their original member bytes.

| Original member | Bytes | SHA-256 |
| --- | ---: | --- |
| Release ZIP | 522,048 | `ab15a74ba10a71264ccad74cd1d3a394b8f442a2acd33fd363b671bf293b081f` |
| `the-hat-7a825b1-a.d64` | 174,848 | `ce09a1819a5dcec16342ebdc6515d20c377304db68e326ca2d86a499f0c9399d` |
| `the-hat-7a825b1-b.d64` | 174,848 | `1527038ebebca1a3d3d3379b91dd1a77dffb6d6d89a4dbfc32bf3f6908eb5b21` |
| Cover JPEG | 755,253 | `caa7b28fcaff0e498a5bc4ee7aab7517537a9f0ba1381af3d462fc2680d1fe5c` |

The archive also contains one directory entry. It has no separate source
or text-note member. This archive inventory does not rule out notes or
additional data embedded inside disk resources. The short `7a825b1`
filename suffix remains an unbound release string, not a recovered source
revision.

Original D64 copies are retained under
`build/research/the-hat/release/`. No source ZIP, original disk member or
previous research producer is modified.

## DOS directory and exact bootstrap

Both DOS directory chains use track 18 sectors `1,13,14,15,16,17`. Each
contains 48 closed PRG-type entries with a declared size of zero blocks.
Those block counts are artwork metadata: following the actual `18/2`
sector chain recovers a nonempty program. Its terminal sector is `18/12`,
with 170 data bytes in the final sector.

All aliases on both disks produce the same **2,710-byte PRG**, SHA-256:

```text
32189d1101a947c3ecc02ae3e9493756dbc063008582d09c62f939068f1049cd
```

The two-byte header is `$0801`. The remaining **2,708 loaded bytes** cover
`$0801..$1294`, with SHA-256:

```text
927f80fe8515f40aac6180bc62149123dbc54664c08b136b1a5f9755f3b02b7f
```

The literal BASIC header contains `SYS2061`, so the original machine-code
entry is `$080D`. The header includes fourteen bytes, including its PRG
load word and BASIC terminators.

Source inspection of that original bootstrap establishes a small
self-relocation boundary. Y starts at `$EC`; the copy loop visits offsets
`$EC` down through 1 and stops when Y reaches zero. Thus source
`$0821..$090C` is copied to `$0001..$00EC`. **It does not copy offset zero
to the CPU DDR at `$0000`.** The bootstrap jumps from `$081E` to `$0003`.
Its literal final source instruction at `$090A` is `JMP $0A00`; after
relocation that instruction resides at `$00EA`.

These byte/source facts identify `$0A00` as the unpacked handoff target.
They do not independently reproduce the unpacked bytes or prove that an
unrelated later `$0A00` overlay is the same code generation. The extracted
bootstrap is an exact original-input oracle for a natural `$080D` capture;
an original execution and its resulting code need separate custody.

The identical bootstrap on side B also does **not** establish an
independent emergency entry into the ending. Installed drive state, disk
identity and the first requested resource still need to be observed. No
side-B shortcut or final-scroller entry is inferred here.

## Source-described raw directory

Track 18, sector 18 contains a separate 256-byte table. Its first four
bytes are `01 00 00 F0` on side A and `01 00 00 F1` on side B. The first
three bytes seed a track / ordered-sector slot / byte cursor; the fourth
is the side tag. Four arrays of 63 bytes follow:

```text
field byte address = 4 + file_index + 63*field_index
load address       = low | (((stored_high + 1) & 255) << 8)
payload length     = (length_low | (length_high << 8)) + 1
```

The interpretation is bound to the retained primary
[`bboxy/bitfire` writer source](https://github.com/bboxy/bitfire/blob/5a3964b533656332c12cc0904f2ce92f44499c6f/d64write/d64write.c)
at commit `5a3964b533656332c12cc0904f2ce92f44499c6f`. Its exact source
hash and line fragments are guarded by the producer. The relevant source
sections are:

- `d64_bitfire_set_side`, lines 669–681: side tags and directory sector;
- `d64_create_bitfire_direntry`, lines 724–760: the four arrays and initial
  cursor bytes;
- `d64_allocate_next_block`, lines 386–448: four-sector stride on tracks
  1–17, three-sector stride afterward, and skipping directory track 18.

This is a format/source relationship, **not** an assembled binary match of
The Hat's complete installed loader to that public revision. The retained
resident and drive source files are versioned context for that later
comparison. They are not assembled, imported or executed by this producer.

For each data track, sector order is enumerated by residue classes. Track
1 starts `0,4,8,12,16,20,1,5,...`; tracks above 17 use stride 3. File
boundaries can occur inside a sector: the cursor carries forward rather
than discarding the remaining bytes. All directory-described payloads
are extracted from this continuous stream, skipping track 18.

An independent second construction concatenates the entire physical sector
order first and slices it using cumulative declared file lengths. Every
cursor-based extraction equals its corresponding global slice. This checks
cursor advancement and file boundaries; both constructions use the stated
source-described sector ordering. It is not independent native transfer
acceptance.

## Extracted resources and limits

| Side | Directory resources | Raw payload bytes | Final track / ordered slot / byte |
| --- | ---: | ---: | --- |
| A | 43 | 164,388 | 34 / 12 / 36 |
| B | 19 | 71,781 | 14 / 7 / 101 |

After each side's final active entry, all remaining field arrays are zero:
20 unused entries on A, 44 on B. Both directories fit entirely in sector
18; the DOS artwork sector 17 is therefore not misread as a second raw
resource table. This does not assert that every unused disk byte is empty
or that no other original consumer can address it.

Output filenames have the form `raw-a/000-1673.prg`. Their first word is
the loader address reconstructed from the original table, followed by the
exact raw payload. It is a useful loader-address wrapper, not a promise
that the resource is a runnable standalone program. Each record retains
its original field bytes and every disk-offset/file-offset segment.

For example, side-A resource 0 has loader address `$1673` and **2,443
payload bytes**, ending at `$1FFE` exclusive when loaded linearly. Its
payload hash is
`1e5fbf8137b400d0f3d56a65f5acd4edb7a37ae728151020ea59e4868b59a0de`.
The resulting 2,445-byte wrapper has hash
`d73b98335b746369be7a76582b4d6b866806957a70ff78943a381cb9a1872bce`.
Its first payload word is `$0F00`, recorded as a **prospective destination**;
only decompression can establish the actual output range and code.

Likewise, the last two side-B resources have prospective destination words
`$2000` and `$F000`. Their position at the end of the table does not identify
either resource as the final upscroller, font or music. Those names require
an actual controller/request-to-consumer relationship and decoded data.

## Reproduction and retained diagnostics

Run from the research repository with a fresh output directory:

```sh
rtk proxy python3 -B research/the-hat/disk.py \
  --output build/research/the-hat/disk-analysis/replay-new
```

Current [accepted receipt](../../build/research/the-hat/disk-analysis/accepted-02/disk-proof.json)
is **313,138 bytes**, SHA-256
`a23fa100137fe60f929af25b6596584089cd93cacd891fe02e7ebc85d47635a3`.
The producer is **11,735 bytes**, SHA-256
`0871d6f75a4e2959a3ddc3be1064b521d871b666eb40f286e5f2044840d1c1af`.
A fresh agent replay reproduced all **65 files / 563,876 bytes** exactly;
its [report](../../build/research/the-hat/disk-analysis/agent-replay-check.json)
is 10,044 bytes, SHA-256
`9092621c12202f513c3e2c700d4de386d36624cee0ac2d5edf11d3c8b84e05f3`.
Independent root source review found no material issue. A fresh root replay
also reproduced all 65 files and 563,876 bytes exactly. Its
[10,175-byte report](../../build/research/the-hat/disk-analysis/root-replay-check.json)
has SHA-256
`619549af5660cd20cd5aaaa63d71d150e60f2ab4df8970e2e791d73def9d4edf`.

The earlier `early-01/` output preserves the first bootstrap/chain result.
The first main extraction's `accepted-01/` failure is retained with its
checked source: a fourteen-byte literal header was initially compared with
a thirteen-byte slice. It stopped before stream extraction or any native
comparison. The source slice was corrected in a fresh output; original
bytes were unchanged. An optional static disassembler import also failed
because `py65` was absent. Its note states that it is not a complete
execution receipt; no dependency, CPU model or game program was run.

This lane performs no network access, CPU interpretation, emulation,
native process control, assembler/build, downloaded host execution or
product change. The next useful result is a natural original bootstrap and
load/depack binding, followed by the real ending's controller, font and
display domains. Whole-demo timing, visible pixels and the final
all-border mechanism are not established by this extraction.
