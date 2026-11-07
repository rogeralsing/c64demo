# Next Round: the original fullscreen scene inputs

Research date: 7 November 2026. This extends [the renderer/source note](next-round.md) with the original *Next Round* round-3 disk data. The original production now has a native match to the user's two-cube image; the published source archive's single-polygon example is a separate dataset. No production renderer code was changed for this investigation.

## Original release, bootstrap, and part handoff

The input is the [original 2026 release ZIP](https://csdb.dk/getinternalfile.php/280568/next_round_performers_2026.zip), not a recreation. Its `round3.d64` has SHA-256 `e1991a76fa7968743e81efd7fd46bd1c4f81cc831512f02b33fb8eef563a4179`. All 24 ordinary DOS directory aliases on that disk contain the same 2,487-byte bootstrap, also shared with the first two disks: SHA-256 `a5441eea42eab6f7bbe9566403cf5eae9b86e2e17dbdadeca7813ad6ae6682ec`. Choosing another decorative DOS filename does not select another part.

The canonical extracted bootstrap is `build/research/next-round/boot-analysis/round3-bootstrap.prg`. Its BASIC line executes `SYS2061` (`$080D`). The original SFX hands off to `$0900`, installs the resident loader at `$0200`, loads custom file 0 to `$0100`, and jumps there. Round 3's loader stub initializes its music and first stage, then enters that stage at `$0800`. This is a normal release bootstrap route; setting the PC to a later part is not required.

The actual fullscreen-vector wrapper is in the later asset loaded to `$E800`. At `$F4E2/$F4E5/$F4E8`, three `JSR $02E4` calls load and depack the renderer, scene, and initialization files. The original wrapper eventually executes `JMP $E000` at `$F4F8`. `$E000` is the useful native breakpoint. Entry `$0600` is the subsequent relocated three-buffer main loop. A direct jump to the wrapper without the original loader/music state was not validated.

The disk uses Bitfire's custom raw-file directory, distinct from its DOS directory. We checked its layout against the loader bytes and the primary [Bitfire source](https://github.com/bboxy/bitfire/tree/5a3964b533656332c12cc0904f2ce92f44499c6f). The custom directory is track 18/sector 18, with a second block at sector 17 only when the first 63 entries are full. Files occupy complete 256-byte data sectors in the loader's implicit sector order, without DOS link bytes. `research/next-round/extract_bitfire.py` reproduces all 168 extracted raw files across rounds 1–3 byte-for-byte.

## Depacking evidence and its native cross-check

`research/next-round/analyze_boot.py` executes only the original SFX in bounded flat-RAM py65, stopping before `$0900`. `unpack_files.py` installs the original resident code using its literal copy instructions, then calls its plain-depack entry `$02DE` on the extracted files. It extends the necessary NMOS opcodes explicitly; it does not replace the original decompression algorithm or execute archive binaries on the host CPU. This offline step alone is not drive, VIC, IRQ, or timing proof.

The separately owned native session then booted the original round-3 release and reached `$E000` naturally, without PC or payload changes. Its RAM matched **all 44,525 bytes** of these three offline-depacked payloads, without exclusions:

| Custom file | Packed disk load | Depacked interval | Bytes | Role |
| ---: | --- | --- | ---: | --- |
| 6 | `$4E0E` | `$2000..$6CBC` | 19,645 | Renderer and tables |
| 7 | `$81C5` | `$6CBD..$C5FF` | 22,851 | Scene commands and trailing padding |
| 8 | `$E474` | `$E000..$E7EC` | 2,029 | Initialization/integration |

The comparison receipt is `build/research/next-round/production-round3-live-01/payload-comparison.json`. Its PRG hashes include their two-byte load headers; the offline depack receipts separately hash the raw output payloads. This distinction matters when reproducing hashes.

The renderer's contiguous `$2000..$5D3C` block, **15,677 bytes**, is also identical to the initialized published standalone renderer captured at its `$E000` entry. Over the full 19,645-byte renderer interval, 159 bytes differ, mainly near the integration/initialization code. Thus this is stronger than a visual resemblance, but it is not a claim that the whole linked program is identical to the standalone example. In particular, the original scene-end path jumps back to production integration at `$0418`; the standalone example rewinds its example data.

The original's 24 pattern-table bytes at `$E400..$E417` exactly match the published twelve even/odd pairs. Their SHA-256 is `959103631699d1310caf6e1fcc02e1dea6499c2affafed2d5d79eac696882311`.

## What the original scene supplies

Initialization patches the renderer's scene-end comparisons to `$C571`. Therefore the actual command stream is **`$6CBD..$C570`, 22,708 bytes**, rather than the whole padded file. Its SHA-256 is `e04c1ed8790c7b860c14c354d6e6c608611d55c22d0547a6c5c21880b493edcb`.

`research/next-round/analyze_scene.py` decodes the original descriptor and edge-update format from the published renderer. The low nibble selects the pattern; the high nibble counts updates after the initial three coordinate pairs. Coordinates are supplied Y then X in a two-chain traversal order. They are not simply an unordered list of mesh vertices.

The original stream contains:

- 536 frame records and 2,402 polygon records;
- polygons with 3–16 supplied vertices; 578 reconstructed outlines are nonconvex;
- logical X coordinates 0–160 and Y coordinates 0–238;
- pattern IDs 1 and 3–12; no ID 2;
- zero backwards-Y steps in the two supplied chains.

No runtime 3D transform or visibility calculation is required to derive these final 2D polygons: those coordinates and pattern choices are already in the input. The archive inspected here does not include their 3D exporter, so this does not establish how the original model, clipping, visibility, or dithering regions were generated offline.

## Prepared fragments, spatial ordering, and overlap

We reconstructed polygon contours and audited them with exact rational arithmetic. For each pair within a frame, all vertex-Y values and segment-intersection Y values divide the common range into open slabs. On each slab, even-odd interior intervals have a fixed ordering; their intersection width is affine. Midpoint interval tests detect positive-area overlaps, and integrating those widths gives exact intersection areas.

Across all **7,960 unordered within-frame pairs**, only two have positive-area overlap:

| Zero-based frame | Polygons | Patterns | Intersection area in logical-pixel² |
| ---: | --- | --- | ---: |
| 322 | 0 and 3 | 8 and 8 | `615/199924` ≈ 0.00307617 |
| 368 | 1 and 3 | 5 and 7 | `2192/1365` ≈ 1.60586081 |

All other pairs are disjoint in area, though touching boundaries are allowed. A separate audit found **zero proper self-crossings** and no open Y slab with multiple separate intervals inside one polygon. Vertex touches and pinched outlines are allowed. It also checked drawing order: at common Y, an earlier polygon lies wholly to the right of a later polygon, apart from the same two small overlaps. There were no wholly reversed, non-overlapping pairs. This independently supports the author's stated right-to-left spatial preparation rule.

These are properties of the supplied continuous polygon geometry. They do **not** assert exact C64 edge rounding, absence of single-pixel raster seams, or pixel equivalence to a host polygon renderer. The exceptions are reported rather than silently erased. Receipts are `boot-analysis/scene-overlap.json` and `boot-analysis/fragment-order.json`.

## The two-cube picture and its apparent transparency

Zero-based input frame **376**, at `$9525`, reconstructs the same two-cube arrangement and stippled-region layout as the user's picture. Its ten polygon patterns are, in order, **4, 8, 12, 5, 7, 4, 3, 5, 8, 7**. The adjacent native pose, `production-round3-live-01/scene-frame-377.png`, independently shows that arrangement in the original running production. Its data pointer at `$0018/$0019` is `$95EB`, the start of input frame 378, confirming that the native capture follows zero-based frame 377. This frame-index check is recorded separately in `frame-index.json`.

The decisive input fact is that the apparently transparent object is already partitioned into regions with different fixed pattern pairs. For example:

- the central slotted quad uses pattern 3, `$CC/$FF`, combining green with the background selector;
- other adjoining slotted regions use patterns 5 and 7, `$FF/$EE` and `$BB/$AA`, combining green with light green;
- the solid-looking cube uses its own separate supplied regions, including the white pattern 12;
- those ten supplied contours have no positive-area overlap.

This rules out the explanation that this frame simply submits complete rear faces, then draws a complete perforated front face with a general transparent-pixel compositor. The runtime receives already-separated visible/color-pattern regions. Its fixed two-bit pattern choices can make a region look like one material seen through another, without preserving arbitrary rear-face pixels under a front polygon. The source's right-edge OR merge remains an edge/glyph assembly operation, not an alpha blend or a general depth-ordering algorithm.

It is fair to call the result a convincing transparency effect. It is not evidence of unrestricted transparent polygon overlap, RGB alpha, runtime 3D visibility, or the exact offline clipping algorithm. Those stronger claims would require the missing exporter or additional production code.

## Reproduction and image limits

`research/next-round/render_scene.py` produces `boot-analysis/scene-contact-sheet.png` and `host-scene-376.png` from the decoded contours and literal source pattern bytes. These are explicitly **host geometry previews**, using rational pixel-center coverage and an illustrative palette. They are not native captures and intentionally do not claim the renderer's integer edge rules.

The actual native image and original RAM are separate: `production-round3-live-01/scene-frame-377.png` and `ram-scene-377.bin`. The primary native session, palette/pattern checks, monitor history, and their limits belong to [the main note](next-round.md).

Offline artifacts live under `build/research/next-round/boot-analysis/`: `bitfire-files.json`, `extraction-check.json`, `depacked-round3/receipts.json`, `original-scene.json`, `scene-overlap.json`, `fragment-order.json`, and `host-preview.json`. Each analysis receipt records its script or input hash. No production timing claim comes from these host calculations.
