# We Are The Anomaly: original Sparkle boot and Arcade payload identity

The original side 1 disk contains **Sparkle 2.3.23.105's loader image**, with its configured return address changed to `$FF40`. Its drive sectors independently match the same version after documented configuration patches. An offline decoder now recovers all **39 real payload bundles**, each using only bytes established inside that bundle. **Bundle 36 matches every one of the 41,523 bytes in the production Arcade Scroller Link binary's two loaded sections.** This closes the original-disk/artifact gap identified in the [Arcade source note](anomaly-arcade.md); it does not rebuild the published source or prove Arcade's live timing.

Input is `WeAreTheAnomaly-Side1.d64`, 174,848 bytes, SHA-256 `d452497845598cca8936fdf57c60fdc9c70cd7e64110e049fa6fc7d735f940cd`, extracted from the already archived [author download](https://www.elder0010.com/uploads/we_are_the_anomaly/we_are_the_anomaly_gp_ext.zip). The pinned author repository's Release disk is identical. No Colors disk, loader image or assumed format is used in this analysis.

There are 48 decorative DOS directory entries, all pointing to the same four-sector chain starting at **18:7**. The distinct DOS file is an **834-byte PRG**, SHA-256 `40cd90f462434ea395d1c03e09d5cb6336186ab2229e4889c4d3abb48a2816ea`, loading `$0801..$0B40`. BASIC `SYS2064` enters `$0810`.

Only six original instructions precede the first external call:

```text
0810  LDA #$FF
0812  STA $FC
0814  LDX #$04
0816  LDA #$08
0818  STA $BA
081A  LDA $BA
081C  JSR $ED0C       ; KERNAL IEC LISTEN — strict CPU check stops here
```

They take **15 nominal CPU cycles**. The file-known checker provides no ROM, I/O, drive or unknown-memory response. Its declared initial SP/flags do not affect these instructions; it invents no initial CPU-port or RAM value. The remaining boot sequence is read from original bytes and corroborated by native captures, rather than executed through a fabricated IEC environment.

The original boot's resident copy loop is `$08A6..$08B3`. For each `X=0..255`, it copies `$09A5+X→$0160+X` and `$0A45+X→$0200+X`. The 96-byte overlap is consistent because both source and destination bases differ by `$A0`. The clean natural checkpoint is **`$08B5`**.

This writes 416 destination bytes, but only **412** originate inside the PRG: source `$09A5..$0B40` maps to `$0160..$02FB`, SHA-256 `17b7d0dca6f00c68772031097288f7f8160c36570686b6f2804a42d06562d4d4`. The remaining source `$0B41..$0B44` is beyond the file and maps to `$02FC..$02FF`. The native join checks all four against the actual source bytes at the same post-copy stop; it does **not** supply zero padding. Later loader calls modify resident state, so the initial installed image is not assumed pristine throughout the demo.

Version identification rests on original bytes. At author repository commit [`4361d011f56f27014c0b6cd542718ca0b23666d8`](https://github.com/elder0010/WeAreTheAnomaly/tree/4361d011f56f27014c0b6cd542718ca0b23666d8), `Extras/Sparkle/Sparkle2.exe` embeds the 834-byte canonical boot at host-file offset `$11B520`. Its PE FileVersion/ProductVersion is **`2.3.23.105`**. The executable was read only as data, never launched.

The official loader source was then pinned independently to [Sparta's commit `427e8be5743e70e9ea206eeef49cb4c971b1cba3`](https://github.com/spartaomg/SparkleCPP/tree/427e8be5743e70e9ea206eeef49cb4c971b1cba3), committed 5 January 2023. Its [`Resources/Loader.prg`](https://github.com/spartaomg/SparkleCPP/blob/427e8be5743e70e9ea206eeef49cb4c971b1cba3/Resources/Loader.prg) is identical to the embedded array. The original disk differs at only PRG offsets **261 and 264**: the immediate bytes pushed as an RTS destination change from `$10/$AD` to `$FF/$3F`, configuring return to `$FF40`. This binds the loader image and version family, without asserting that no other host build retained those bytes.

The six original drive sectors **18:11..18:16** provide a second binding. The pinned [`SD.prg` and builder](https://github.com/spartaomg/SparkleCPP/blob/427e8be5743e70e9ea206eeef49cb4c971b1cba3/Sparkle.cpp) specify the six-page zero-initialized image, block permutation, reversed-byte third block and EOR transformation. After these operations, only eight raw bytes differ: three Product ID bytes, four version bytes and Next Side ID. Applying their documented configurations yields an exact **1,536-byte** match, SHA-256 `d973ac105cce8d94bfbf637e3bd8f9113cd4dd13881346b3058f7433bbd33b28`. The original drive contains version BCD `$23,$01,$05` and major/minor `$23`, Product ID `$001FA5`, and next-side ID 1. The repository's separate 2.2 manual and old 1.5 assembly are not substituted for this matching image.

The byte-bound [resident symbol file](https://github.com/spartaomg/SparkleCPP/blob/427e8be5743e70e9ea206eeef49cb4c971b1cba3/Resources/SL.sym) gives:

| Function/state | Address |
| --- | --- |
| Send bundle/side command | `$0160` |
| Load indexed bundle | `$0182` |
| Load prefetched block | `$0185` |
| Load next sequential bundle | `$0200` |
| Fallback IRQ / player call / RTI | `$02E2` / `$02F0` / `$02FB` |
| Sector buffer | `$0300..$03FF` |
| Destination pointer / bit state | `$02..$03` / `$04` |

The internal directory occupies raw sectors **18:17 and 18:18**, separate from decorative DOS entries. Each entry stores transformed track, track-start sector, remaining-sector count and an untransformed bit pointer. Bytes within each directory sector are ordered `0,255,254,…,1`. The original BAM supplies zone interleaves **4,3,3,3**. The checker reconstructs their exact sector permutation, including the skipped directory track and wrap behavior. A stored track-start sector is not automatically the payload's actual sector.

The [original resident depacker](https://github.com/spartaomg/SparkleCPP/blob/427e8be5743e70e9ea206eeef49cb4c971b1cba3/Resources/SL.asm) reads destination addresses and byte data backward, with interleaved sentinel bit streams and paired literal-length nibbles. It supports short, near/far mid and near/far long backward LZ matches, file boundaries, block boundaries and bundle endings. The host implementation translates those data rules; it does not execute the serial receiver or emulate the drive.

One necessary drive operation explains an initially preserved failure. A transitional sector can end one bundle and begin the next. Its byte 1 carries the next block count for the drive. The byte-bound `SD.asm` routine `ChkLastBlock` saves that metadata and replaces it with transformed `$7F`, which arrives as **zero** in the C64 buffer. The first raw-sector attempt retained this metadata as compressed payload and correctly stopped on an unknown match source in bundle 2. After implementing the **source-defined transitional-field removal**, all real bundles decode. The earlier script and failed receipt remain archived under `binary-analysis/*before-transition-count-*`; no unknown backreference was filled to make decoding succeed.

Every bundle now starts with an empty known-byte mask. Literals establish bytes; matches must read bytes already established **inside that same bundle**. All 39 succeed without prior effect RAM, earlier bundles or native prestate. The output `.ram` files accompany `.known` masks: zeros outside each mask are storage placeholders, never decoded inputs or asserted payload. Directory entries 39..127 repeat the final dummy entry. At track 35, sector 12, bit pointer 11, it writes a zero to its own buffer address `$0308` then requests another block/side. It is recorded as a terminal reset/continuation dummy, not forced into a fortieth complete payload.

Selected identities and native boundaries are:

| Bundle | Independently decoded bytes | Natural checkpoint and checked identity |
| --- | ---: | --- |
| 0 | 336 | First `$FF40`: CIA detection at `$FE00..$FF4F`, exact published Link PRG. Entry begins `JSR $FE00`. |
| 1 | 122 | Second `$FF40`: EntryWithBASICFade at `$FF40..$FFB9`, exact Link PRG. Entry begins `JSR $FF80`. |
| 2 | 2,043 | `$FF54`: 143 base-code bytes `$0800..$088E` plus 1,900 Exordium bytes `$0900..$106B`. Both match published artifacts. |
| 3 | 24,622 | `$FF63`: all BASICFade asset ranges plus the 24-byte incoming driver, before its `$8500` initialization call. |
| 4 | 25,088 | `$2D00`: all original HumanMade preload bytes `$2D00..$8EFF`. |
| 35 | 61 | Incoming NanoCamera/Arcade driver at `$088F..$08CB`, source of the later natural Arcade call. |
| 36 | **41,523** | Arcade Scroller's two sections; exact production Link artifact identity, **not yet a native Arcade-entry capture**. |

Original Arcade bundle 36 begins at **track 28, sector 5**, bit pointer `$3C`, and consumes 76 compressed sector blocks including its shared boundary blocks. Both sections match [`Link/ArcadeScroller/ArcadeScroller.prg`](https://github.com/elder0010/WeAreTheAnomaly/blob/4361d011f56f27014c0b6cd542718ca0b23666d8/Link/ArcadeScroller/ArcadeScroller.prg), SHA-256 `8ee85d5dad9035e205bb68391ab5b4e033c5c596a7e62f840db270f63b1fc16c`:

| Destination | Link PRG file offset | Bytes | Result |
| --- | --- | ---: | --- |
| `$2800..$BF2E` | `$0002` | 38,703 | All original disk bytes known and identical |
| `$E000..$EB03` | `$B802` | 2,820 | All original disk bytes known and identical |

The intervening `$BF2F..$DFFF` gap is not loaded by that bundle and is not made known by the decoder. The differently built `Parts/ArcadeScroller/ArcadeScroller.prg` remains a separate artifact. Exact Link section identity does not establish a fresh assembly of the post-release source.

The actual late entry follows original driver instructions. Bundle 35 copies `$A800..$AFFF→$C000..$C7FF`, calls `$C000`, then **`$08AE: JSR $0809`** loads Arcade bundle 36. At return `$08B1` it waits for `$088F` (PartDone), clears it, and **`$08BB: JSR $3B00`** enters Arcade. The decoded entry guard is `A200A90195E8BD873B95F0BDE93A95E0E8E006D0EDA90F85`. `$2800` is a transfer/table address, not the execution entry. This gives a safe natural checkpoint for a future late native continuation without jumping directly into a part.

Root's closed `native-02` boot batch contains eight matching RAM/VSF pairs and five PNGs, ending at HumanMade `$2D00`, clock 37,568,580. The passive source join passes **15 exact domains**, including all stated early payload bytes and the initial resident's 412 file bytes plus four actual native source-tail bytes. `$FF66` is neutrally labelled `fade-call-return`, after the `$8500` call; no RAM-only initialization proof or stable-frame claim is assigned to it. The separate [native audit](anomaly-native.md) owns lifecycle, CPU/beam pairing and absence of intervening input/patch/restore. The earlier `native-01` setup-only failed attempt remains distinct.

Reproduce source/data decoding, then perform the passive closed-session join:

```sh
rtk proxy build/research/tower-power/cpu-venv/bin/python research/anomaly/inspect_boot.py
rtk proxy build/research/tower-power/cpu-venv/bin/python research/anomaly/inspect_boot.py --native-only
```

[inspect_boot.py](../../research/anomaly/inspect_boot.py) SHA-256 is `1ce2fc8725d7f6f693931ae527de34f1abd175451ef6a66c43d14ce6cfbe87bb`. Ignored `binary-analysis/side1-binary-proof.json` is `b8744b0184128330a069a7366c4f843193306074f4a55a03d10f092a6fa8800c`; `native-payload-comparisons.json` is `a6d48ec5123ca1ee9f621dfc52de8317a75e362feb0d8019384e6da21ec504e5`. Source receipts pin Git blobs and all raw artifacts. No downloaded host executable was run, no source was assembled, and no loader I/O, CIA/NMI response or unestablished RAM was synthesized. Arcade's per-line register timing, upper-copy gate arrivals, publication completeness, coherent fields and author 50 fps claim remain open native questions.

Peer review caught a provenance-field error in the first frozen receipt: the embedded boot-array offset was asserted as `$11B520`, but a reused loop variable later caused the receipt to record `$B802`, an Arcade section's file offset. A dedicated variable and final output assertion now preserve the correct `$11B520` value. Before correction, the complete old script (`2a6d74c0a520…`), source receipt (`6c887675d86c…`) and native join (`a45fa0dacfdb…`) were archived byte-for-byte under `binary-analysis/*before-array-offset-fix-*`. Refreshing the source check and passive join changed only that metadata and their script/dependency identities; all decoded data and 15 native comparisons remain identical. No new native execution was performed.
