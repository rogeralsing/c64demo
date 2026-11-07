# Tower Power: release provenance and written evidence

Research date: 7 November 2026. This note covers metadata, release files, and offline decoding of the included note. It does not claim the patterned sphere or cube has been reverse engineered. The binary/emulator investigation is separate; no emulator was launched in this research lane.

## Keep the two releases separate

| Release | Archive record | Date / party | Download |
| --- | --- | --- | --- |
| Tower Power 92% | [CSDb 11628](https://csdb.dk/release/?id=11628) | 29 December 1993; first in The Party 1993 C64 demo competition | [Original D64 in gzip](https://csdb.dk/getinternalfile.php/38681/Tower%20Power%2092%25.d64.gz) |
| Tower Power 100% | [CSDb 11791](https://csdb.dk/release/?id=11791), [Demozoo 6192](https://demozoo.org/productions/6192/) | 30 December 1994; released at The Party 1994 | [Two-side ZIP](https://csdb.dk/getinternalfile.php/38682/Tower%20Power%20100%25.zip), [scene.org archive entry](https://files.scene.org/view/parties/1994/theparty94/c64/demo/tower_power.zip) |

The combined [Pouët entry](https://www.pouet.net/prod.php?which=1586) displays December 1994 alongside the 1993 party win. That combines the final version's date with the earlier competition result; it is not a reason to assign the 100% release to 1993.

Both CSDb versions credit **Slammer** for code and **Glasnost** for the loader. The final release additionally lists Jeff, Duck LaRock, and MSK for music, and Kring, Neptune, Rob, and VIC for graphics. Demozoo separately credits Jeff's music-player code. These are production-level credits, not a verified allocation of each sphere/cube routine. [100% credits](https://csdb.dk/release/?id=11791), [92% credits](https://csdb.dk/release/?id=11628), [additional credit detail](https://demozoo.org/productions/6192/)

## Included crew note: recovered without execution

Disk 1 includes a FaceNoter program named `tower note!` with trailing spaces. The research copy is exactly the same 11,436 bytes extracted for the separate binary investigation:

```text
SHA-256 9c8a0bfcf934bea0710adc51ef36777afbe684bdb49c2784bee2bd9e04d4e640
```

The note is packed. Its small bootstrap copies a literal/RLE decoder to `$0100..$0143`; the original packed stream begins at `$087A`. Reading that decoder statically was sufficient to reconstruct its format and expand the stream using a host-side parser. No C64 instructions were executed. The output is 15,039 bytes starting at `$0840`, SHA-256 `2ff9d4ed44a805baaf4e786adaa7107b2fd4e5d0620f88c29f476d8edd81cfb5`. Text begins at decoded address `$2FFF`; pages occupy 1,024-byte slots with up to 1,000 screen characters, explaining the padding in a naive string dump.

Local receipts and reproducible parser are under `build/research/frontier/tower-power/`: `decode-note.py`, `note-decode.json`, `tower-note-unpacked.bin`, and `tower-note-pages.txt`. Ambiguous custom-font characters remain explicit rather than being silently invented. The public source is the [100% release archive](https://csdb.dk/getinternalfile.php/38682/Tower%20Power%20100%25.zip).

The five decoded pages establish the following:

- **Page 1:** the final version arrived a year later, adds a built-in load selector, new Jeff tunes, bug fixes, and extra graphics/parts, and removes the old credits part.
- **Page 2:** ordinary `RUN` starts the intro; numbered forms select a part. It also says the hidden part was absent at the 1993 party and is included in this version.
- **Page 3:** the crew criticizes inflated face counts obtained by subdividing a cube's planes. It argues that a cube still needs only six surface-visibility tests, distinguishing coplanar patches from distinct geometric surfaces.
- **Pages 4–5:** greetings explicitly place the writer at The Party 1994; the final signature is the Tower crew in 1994.

The note is signed collectively, so it should not be quoted as a specifically signed Slammer article. Its surface-count discussion is relevant to the patterned cube, but it does **not** explain that routine, claim texture-coordinate interpolation, or establish precomputed coordinates, visibility, or complete frames. No standalone rendering source was present in the downloaded release archives.

## Archive identity and mirror differences

The CSDb and SCS-TRC ZIP files differ, and their D64 hashes differ. Offline extraction resolves the important distinction: **all 44 common named files are byte-identical** (six on side 1 and 38 on side 2). The SCS-TRC side-1 image has an additional `win386.swp` file. Do not compare whole-disk hashes and conclude that the shared demo routines differ.

| Download | Bytes | SHA-256 |
| --- | ---: | --- |
| [100% CSDb ZIP](https://csdb.dk/getinternalfile.php/38682/Tower%20Power%20100%25.zip) | 187133 | `3d0dd901fa3090994a390f897004d42cad1a79920734b7d9fcb6f3598efb0ab6` |
| [100% SCS-TRC ZIP](ftp://ftp.scs-trc.net/pub/c64/Demos/pal/c/Camelot/Tower_Power.zip) | 187619 | `6f7ca47e740034313b8255a6c5aa392ee8d26c624a7331e9f9b6c41b0d51f3c4` |
| [92% CSDb D64 gzip](https://csdb.dk/getinternalfile.php/38681/Tower%20Power%2092%25.d64.gz) | 151161 | `f558e39dab261f5ba755e5f78ba7eb69949a07d937e3e1130bdf10db722b1097` |
| [92% SCS-TRC ZIP](ftp://ftp.scs-trc.net/pub/c64/Demos/pal/c/Camelot/Tower_Power_92%25.zip) | 150769 | `9d2b277779bbc6b4aafd16e3381c24f660122ebb313c2966d854d1e064a38f36` |

The CSDb final disks are SHA-256 `c727e87842b3adf924f05b1c2748c9d3e3d19560b38dfad271e7df6291cc536e` (side 1) and `51f3df67231908634674f3e7f83e450864bf560173a03636e81e61ef7f7261e9` (side 2). SCS-TRC disks are `4839031af8a47c9777de83bf815fd295b0f517adebd87d448dbe75518cb3a0c0` and `2e845a05c117e88ceca1df4d5ffeddd1729351286cd55869b13888ede064ce20`.

The two 92% disk images are also not byte-identical: CSDb's expands to `a54f779849e5e4c2ea5a0d21f2f24b95f99b67be27d720a66c5a8ba9b4b9665c`; SCS-TRC's is `738192583a1906106d08ea8b85241f2ea8b065c5ca425471a682216eef0d1516`. Both were directory-listed and extracted offline. This pass did not establish every reason for their differences. Detailed per-file hashes and extraction logs are preserved in `extracted-files.json` and adjacent directories; URL receipts are in `downloads.json`.

## Written leads and their limits

**Contemporary reception, not implementation documentation.** Commodore Format 49 (October 1994), printed page 15, describes translucent/stencil vector effects and reports 72 faces for the vector ball. The available search-index text of the [original magazine scan](https://electronicsandbooks.com/edt/manual/Magazine/C/Commodore%20Format%20UK/CommodoreFormat49-Oct94%20c20131204%20%5B36%5D.pdf) supports that as a **reviewer's reported count**. The PDF could not be fetched locally during this pass, so the printed layout and exact version reviewed have not been checked. The issue also predates the December 1994 final release: do not silently identify its reviewed binary with the final archive.

Commodore Format 51 (December 1994) later uses Tower Power as a comparison when discussing patterned stencil polygons in another demo. Again, that is effect terminology, not a description of Tower Power's code. [Original scan lead](https://electronicsandbooks.com/edt/manual/Magazine/C/Commodore%20Format%20UK/CommodoreFormat51-Dec94%20c20131204%20%5B24%5D.pdf)

**Later coder discussion.** In the 2007 [CSDb visibility thread](https://csdb.dk/forums/?roomid=11&showallposts=1&topicid=49250), Slammer supplies a geometric explanation for normal/depth-based visibility. Other participants discuss precomputed visibility and coordinates for fixed demo sequences. The thread does not identify Tower Power as an implementation of any of those methods; it cannot establish what the 1993/94 renderer did. A saved primary forum page is available locally as `vector-visibility-forum.html`.

**Reception only.** Nightlord's interview in [Commodore Free 20, May 2008, page 26](https://commodorefree.com/magazine/vol2/issue20.pdf#page=26) recalls the round-vector part's impact and warns generally that optimized mathematical effects can be hard to understand from table lookups alone. It is not a Tower Power technical breakdown.

No signed author explanation of the specific ball/stencil-cube implementation, or contemporary implementation article, was located in this bounded search. That remains an open source-research lead.

## Questions for the binary investigation

1. Locate the exact sphere and cube stages in this final release, recording their input part files and load/depack addresses. Use the built-in selector where it helps; do not assume its numbering equals an archive's file order.
2. Separate geometric planes, visibility tests, and patterned subregions. A screen full of apparent small faces does not by itself give the number of independent normals or transformed vertices.
3. Identify what changes per update: vertex transforms, perspective, edge positions, face masks, pattern source, character/sprite memory, and VIC registers. Determine whether pattern coordinates follow the surface or merely appear through its stencil.
4. Classify every large table by reads and generated output before calling it precomputed animation. Trig, reciprocal, multiplication, edge, pattern, visibility, and complete-frame tables imply different amounts of runtime work.
5. Measure frame intervals and raster occupancy directly. A patterned or translucent appearance does not establish affine/perspective texture mapping, full-resolution updates, or a particular refresh rate.
