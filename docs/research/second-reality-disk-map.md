# Second Reality: disk chains and embedded note

Research date: 7 November 2026. The pinned original disks contain **71 valid, separate DOS PRG chains**, rather than a directory full of aliases to one bootstrap. Every displayed PRG block count is inaccurate. An **AEG-signed embedded note** is now recovered from the independently unpacked boot image and corroborated against the existing native first-entry RAM. No C64 program, CPU or emulator was executed in this inventory lane.

The original package identities and the user's exact capture title remain in [the main production note](second-reality.md). This pass reads the two CSDb D64s already pinned by [the acquisition receipt](../../build/research/second-reality/acquisition.json); it makes no new web requests.

## Directory labels versus actual file contents

| Property | Side 1 | Side 2 |
|---|---:|---:|
| Directory entries | 33 | 49 |
| Closed, locked PRG entries | 27 | 44 |
| Decorative DEL entries | 6 | 5 |
| Valid terminating PRG chains | 27 | 44 |
| Distinct PRG start sectors | 27 | 44 |
| Distinct PRG contents | 26 | 44 |
| Sectors occupied by those chains | 658 | 660 |
| Sectors shared by PRG chains | 0 | 0 |
| Declared block counts differing from chain length | 27 | 44 |

The reader follows each sector link, applies the final-sector byte count and records every sector's hash. All 71 chains terminate normally, without cycles or invalid pointers. There are **70 distinct file contents overall**, with no identical contents across the two sides. A repeated two-character filename prefix on another side is not the same file. The complete [file table](../../build/research/second-reality/disk-map/files.tsv) provides every start track/sector, actual length, nominal PRG load header and full SHA-256. The [structured inventory](../../build/research/second-reality/disk-map/disk-inventory.json) additionally retains every raw directory entry, full chain and file-byte-to-disk-offset mapping.

The 11 DEL entries are decorative directory artwork. Their pointers are preserved but are not followed as live PRG files. Most point to the BAM at track 18/sector 0; interpreting that metadata sector as a program or note would be misleading.

Selected boundaries illustrate why directory labels and block counts need checking:

| Side / first two filename bytes | Start T/S | Actual sectors | File bytes, including two-byte PRG header | Content |
|---|---|---:|---:|---|
| 1 / `SE` (title entry) | 17/0 | 169 | 42,890 | Literal BASIC header has `SYS2304` and the C64-version title REM. The directory claims one block. |
| 1 / `ZD` | 19/3 | 1 | 14 | Separate chain with the same contents as `ZE`. |
| 1 / `ZE` | 19/4 | 1 | 14 | Separate chain; not a same-start alias. |
| 1 / `II` | 2/0 | 1 | 34 | Nominal `$CE00` header followed by a short screen-code message, not an author technical note. |
| 1 / `SY` (`SYMMEK98 INVI.`) | 19/14 | 60 | 15,153 | A separately labelled invitation payload, not the Second Reality technical note. |
| 2 / `II` | 17/0 | 1 | 4 | Exact bytes `00 CE 01 00`; a marker candidate, without a runtime role proved here. |
| 2 / `VA` | 7/15 | 12 | 2,818 | Contains the literal credit table described below. |
| 2 / `WB` | 26/15 | 27 | 6,679 | Contains a literal 1997 KB/T.O.M music-player credit. |

The full boot PRG hash is `c62598561f3bb6d74e9c399385df6e1dd21890c9fc0abbd952a2a61548a286f5`. The identical `ZD`/`ZE` contents hash to `2433b7eef7fb87e2837878e94112232a69437a5edb58670229e56391c09e9302`. `VA` hashes to `831a75966bd9d60bcbf4c54544dd9a967d3e7b945a45f9180f59908b24af4c9e`.

The directory artwork itself includes the side-one `28.12.97` date and side-two DOS starting-point prompts naming `SECOND 2`, `SECOND 3` and `SECOND 4`. Those are literal labels, not demonstrated playback commands or renderer assignments. The nominal load addresses in the table are the first two file bytes under the directory PRG type; this inventory does not assume a packed payload remains at that address after execution.

## The embedded INFO1SDS note

The absence of an outer README did not mean the release lacked a note. The boot's recovered DOS command table contains `read info1sds` at **`$9940`** and `read info1sds.txt` at **`$9960`**. The coherent note occupies **`$B000..$B7FF`**, 2,048 bytes arranged as **64 stored rows of 32 characters**, ending with AEG/Smash-Designs' signature.

The separate boot investigation owns execution of the original decompressor and its limits. This inventory reads its existing `file-derived-unpacked.ram`, verifies the owning [boot proof](../../build/research/second-reality/binary/boot-proof.json), checks the original boot-file identity, and requires every note and alphabet byte to be established in `file-derived-known-mask.bin`. It then compares the note and all 52 alphabet glyphs with the existing native `ram-first-entry.bin`: **every compared byte is exact**. Native RAM supplies corroboration only; it does not supply the independently recovered note bytes.

The character mapping is checked against the stored font at `$B800`: `$01..$1A` are lowercase letters and `$81..$9A` uppercase letters. Punctuation/digits use `$20..$3F`, with `$A0` as space. The generated [alphabet glyph sheet](../../build/research/second-reality/disk-map/note-alphabet-font.png) renders those actual bytes directly. It is a font diagnostic, not a VIC screenshot.

The note describes the project in the authors' own terms:

- It credits The AEG and the literal spelling **Dasheele** for coding, The AEG for graphics, and KB/The Obsessed Maniacs for music.
- AEG acknowledges that many effects had appeared before, while emphasizing their use of high resolution.
- It describes an ambition to reproduce the PC original's appearance closely and assigns the overall **design credit to Future Crew/PC**.
- It calls the DOS emulation imperfect and explains it as part of the presentation before the demo.

These are recovered author statements about aims and presentation. They do not establish a measured display mode for every part, a rendering algorithm, a live-versus-prepared ratio, or reuse of Future Crew's PC source. No per-effect vector, texture, fire or rotozoom implementation explanation was recovered from this note.

The [raw note](../../build/research/second-reality/disk-map/info1sds-note.raw) has SHA-256 `7d9c320a3d721df3951b2615c713ecf7eda827a32c0608d16d221929a74e975b`; the [decoded stored rows](../../build/research/second-reality/disk-map/info1sds-note-rows.txt) have SHA-256 `0d756ee150eb95c44838323e8d1b4e9089eb2ae79cd74393ca820208b9513926`.

The passive binding was refreshed once against final boot-proof SHA-256 `92f272cd978c594467c72a9be0536b29685fbbe0e68e1b18a71d8b9c2718cdfd`, after its owner invalidated the pager's unknown final page. Every note/alphabet byte remains known and unchanged. The [earlier inventory receipt](../../build/research/second-reality/disk-map/disk-inventory.before-boot-proof-rebind-4da8712dea9c.json) is retained with its original `4da8712dea9c…` identity; no CPU was rerun for this refresh.

Initial printable-string scans of the **packed** boot file are retained in the receipt as candidates. Their run boundaries, omissions and apparent fragments are not treated as the final note. The complete note above is bound to the independent decompressor output and native comparison instead.

## Literal credit blocks, with phase identity still open

Side-two `VA` contains a **590-byte** table at file offsets **`$03BC..$0609`**, with 20 `$FE` separators and a final `$FF`. The [credit-block inventory](../../build/research/second-reality/disk-map/credit-blocks.json) preserves all 21 blocks, raw bytes, offsets, physical-sector locations and readable strings.

Most blocks name coding, graphics, objects or samples. Zero-based table block **2** includes an animation credit to Idefix; block **15** contains the literal **`RAYTRACE - AEG`**, alongside KB samples and DCP code credits; block **18** credits a world to Idefix/Yoda and code to AEG/DCP. These are useful original attribution leads. The ordinals describe stored table order, not established runtime part numbers. In particular, a raytrace credit does not prove live ray tracing, the contents of an adjacent packed file, or a frame-rate claim.

No separate source file or source-like technical note has been recovered in this pass. Packed/custom-encoded material remains unclassified; the inventory does not prove that further embedded notes or source are absent. File headers, directory-art phrases and chance printable sequences are not promoted to renderer descriptions.

## Reproduce the passive inventory

```sh
rtk proxy python3 research/second-reality/disk_inventory.py \
  --boot-ram build/research/second-reality/binary/file-derived-unpacked.ram \
  --native-ram build/research/second-reality/native-01/ram-first-entry.bin
```

Without the optional RAM arguments, the [script](../../research/second-reality/disk_inventory.py) performs only the disk-chain, literal-string and credit-table inventory. It never invokes the acquisition or boot-execution scripts. All extracted original bytes and generated outputs remain under ignored `build/research/second-reality/disk-map/`.

Final script SHA-256: `6a76b581b2f52745b5606fb15e256968c264bbf38d1eb9bac331278886325288`. Final inventory receipt SHA-256: **`8f363708bc9fa4cf8ab867f93cd6b74d57510af8f8d882849b97108d6017054c`**. This pass establishes exact DOS chains, recovered note bytes and literal credit data; renderer and per-effect runtime analysis remain separate work.
