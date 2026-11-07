# Next Round (2026): fullscreen patterned-vector source

Research date: 7 November 2026. This covers the user's green patterned-polyhedron screenshot at 9:24 of the 16:01 capture, and the additional two-cube image. Original screenshots are preserved unchanged under `build/research/next-round/`, with hashes in `screenshots.json`. Both the published example and original disk-3 renderer now run in PAL VICE. The native two-cube pose matches the supplied effect, and its prepared polygon fragments explain the transparency. No production renderer source was changed.

## Release identity and source attribution

This is **Next Round by Performers, released 6 June 2026 at X 2026**, second in the demo competition. It is not *Next Level*, the group's X 2023 production. [Release record](https://csdb.dk/release/?id=262169), [independent archive metadata](https://demozoo.org/productions/392459/), [the matching 16:01 YouTube capture](https://www.youtube.com/watch?v=GqEI0T_WoAw&t=564s)

Bitbreaker's 1 July 2026 post on the release page links the [Fullscreen vectors article](https://codebase64.net/doku.php?id=base:fullscreen). His [same-day author announcement](https://csdb.dk/forums/index.php?firstpost=72&roomid=11&topicid=162980) explicitly identifies its explanation and source as the fullscreen vector renderer used in *Next Round*. The published archive contains a standalone example dataset. Separate extraction and native execution of the original disk-3 payload now connect that renderer to the two-cube production scene; the two input datasets remain distinct below.

The source is [full.zip](https://codebase64.net/lib/exe/fetch.php?media=base:full.zip), containing `full.asm`, `full.prg`, and a Makefile. The full 2026 [release ZIP](https://csdb.dk/getinternalfile.php/280568/next_round_performers_2026.zip) contains `round1.d64`, `round2.d64`, `round3.d64`, `bonusround.d64`, and an alternate `round2_digimax.d64`. These were downloaded and directory-listed offline; the alternate disk and bonus disk are kept distinct.

## Display and allocation: not a conventional full bitmap

The author explains a character screen used as both image and allocation map. A boundary cell receives a newly allocated or existing glyph; a fully covered interior cell can point at a shared pattern glyph. The stated single-buffer image footprint is `$0BE8` bytes: 2 KB of glyphs plus 1,000 screen entries, excluding code and auxiliary state. The tradeoffs include glyph exhaustion, clipping, and the many partial-character boundary cases. [Author article](https://codebase64.net/doku.php?id=base:fullscreen)

The inspected source configures multicolor text (`$D016=$18`, Color RAM bit 3 set), three screen/charset buffers, and sprites for top/bottom-border continuation. A glyph row is four two-bit logical pixels, displayed eight physical pixels wide. In this standalone build, charset addresses are `$D800/$E000/$E800` in underlying RAM; screens are `$F000/$F400/$F800`. CPU mapping changes allow access to RAM under I/O. These addresses are source-specific, not recommendations for moving our renderer.

## Exact pattern bytes and how they are selected

`patterns_odd` and `patterns_even` at source lines 1792 and 1806 define **twelve fixed two-row patterns**. `gen_solid` at line 3083 expands each pair into an eight-row glyph, alternating the even and odd bytes. These occupy reserved character codes 1–12. Dynamic boundary glyph allocation starts beyond that reserved set (`FIRST_CHAR=$0C`).

| Pattern ID | Even row | Odd row | Source-defined effect |
| ---: | --- | --- | --- |
| 1 | `$00` | `$33` | Background / selector-3 stipple, 25% selector 3 |
| 2 | `$CC` | `$33` | Background / selector-3 checker, 50% each |
| 3 | `$CC` | `$FF` | 75% selector 3 |
| 4 | `$FF` | `$FF` | Solid selector 3 |
| 5 | `$FF` | `$EE` | Selectors 3/2, 75%/25% |
| 6 | `$BB` | `$EE` | Selectors 3/2 checker, 50% each |
| 7 | `$BB` | `$AA` | Selectors 3/2, 25%/75% |
| 8 | `$AA` | `$AA` | Solid selector 2 |
| 9 | `$AA` | `$99` | Selectors 2/1, 75%/25% |
| 10 | `$66` | `$99` | Selectors 2/1 checker, 50% each |
| 11 | `$66` | `$55` | Selectors 2/1, 25%/75% |
| 12 | `$55` | `$55` | Solid selector 1 |

The standalone constants map selectors `(0,1,2,3)` to C64 palette indices `(6,1,13,5)`: blue, white, light green, green. The code exposes patchable `fullvec_bg`, `fullvec_mc1`, `fullvec_mc2`, and `fullvec_cr` operands, so this does not prove the linked production uses identical register values throughout.

`do_frame` (line 2983) takes the low nibble of each polygon descriptor as its pattern ID and calculates the reserved interior character code. `render` (line 3556) loads that ID's even/odd bytes and constructs left/right edge-mask tables using masks such as `$FC/$F0/$C0` and `$3F/$0F/$03`. Thus the edge fragments use the same screen-aligned pattern phase as the interior tiles. `full`/`ffull` (lines 2849/2862) and `scr_fill` (line 3899) fill solid interior regions by **storing character codes into the screen**, not by writing every interior pixel.

This is a finite palette of spatial dither patterns with a pattern selected per polygon. The inspected path does not interpolate texture coordinates or a per-pixel lighting value. Checker appearance and changing face pattern IDs should not be called perspective-correct texturing or Gouraud shading without additional production code proving that.

## The exact combining operation, and transparency limits

The source is **not an XOR-prefix filler**:

- In the separate-edge loop, the left fragment writes directly with `STA (cset_l),Y` (lines 1332–1334). The right fragment merges with `ORA (cset_r),Y; STA (cset_r),Y` (lines 1338–1339), skipping a zero fragment.
- When both edges fall in the same glyph, the combined path first `AND`s their masks, then `ORA`s the resulting fragment into existing glyph data (lines 1460–1464 and the even-row counterpart).
- Complete interior tiles replace the screen's character reference with the selected pattern character. They do not perform a general read/modify/write color blend with an older polygon underneath.

This asymmetry is intentional. The author discusses preparing/sorting faces **right to left in screen space** so the left side can write through while the right side may need to merge with a neighbor's existing glyph. This is a spatial edge/allocation invariant, not a generic far-to-near painter sort. The article also places sorting and clipping/tessellation among work that precalculated inputs can perform beforehand. [Author's preparation discussion](https://codebase64.net/doku.php?id=base:fullscreen)

The table's zero selectors genuinely produce the background color in a pattern tile. A zero fragment in the right-edge OR path also leaves existing bits untouched. Neither fact proves arbitrary rear walls survive beneath a whole stippled front face: the left path can overwrite, and a full interior tile replaces its screen reference. OR is also not alpha blending—overlapping selectors 1 and 2 can become selector 3 rather than a weighted mixture of their RGB colors.

The original production scene resolves the user's two-cube case through prepared visible fragments. Its matching pose has ten already-partitioned polygons. The central slotted region selects pattern 3 (green/background), while adjoining slotted regions select patterns 5 and 7 (green/light green). The rear-wall-looking colors are consequently already present in the chosen region patterns. These ten polygons have no positive-area overlap in continuous geometry. The C64 does not need to retain and blend two whole overlapping cube faces to produce that pose. The source exporter is absent, so the exact host-side 3D clipping/visibility algorithm remains unknown.

## What is precomputed, and what still runs on the C64

The archived `full.asm` contains an embedded, frame-labelled **2D polygon command stream** at `data_start` (line 3979). `do_frame`, `render`, and `next_edge` consume those supplied coordinates and rasterize them at runtime. This is not evidence that the inspected program rotates/projects a 3D model at runtime.

Offline parsing of the supplied stream found:

- 512 labelled frame slots, numbered 0–511;
- 502 slots containing one four-vertex polygon and ten empty slots;
- all twelve pattern IDs used;
- 5,020 command bytes, SHA-256 `ba94fa0a219bd8e28cdb605c59508dce401b76cc175c0f1032cf9a2edf33e1a7`;
- supplied coordinate-byte ranges Y 12–236, X 21–142.

The descriptor's high nibble gives the number of edge updates beyond the initial three vertices; its low nibble selects the pattern. Coordinate pairs are supplied Y then X in the renderer's two-edge traversal order, not a universal 3D mesh format. The example begins with a four-corner rectangle and later changes its coordinates and pattern. It contains no two-cube scene. The archive supplies neither its geometry exporter nor the 2026 production's full scene stream, so the original model, transform generation, visibility decisions, and scene ordering cannot be reconstructed from this package alone.

The C64 still performs slope/edge stepping, character allocation, partial-glyph completion, screen span filling, cleanup, buffer scheduling, and border-sprite copying. Precomputed coordinates are distinct from complete precomputed framebuffer images. No cycle/frame benchmark was taken in this lane.

## Reproduction receipts and useful entry points

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| [2026 release ZIP](https://csdb.dk/getinternalfile.php/280568/next_round_performers_2026.zip) | 749980 | `ccbcff8ed6edc43af090674f7bd5ae727042a453a03546040cc6a4abba681017` |
| [Published full.zip](https://codebase64.net/lib/exe/fetch.php?media=base:full.zip) | 36111 | `ccbbfea67386da589e53864a7a62ba0c1180ab58c0d200af648c38a10aeadbdb` |
| `full.asm` in that archive | 116131 | `980757e07b9c2447f77ad83fb87696fe5fd4589e1a1a671b21e46222bf1ef5dd` |
| `full.prg` in that archive | 13106 | `94c427ab6950fd420e02fa20c56b78b765d6cba8cabace1c014e676c663576c4` |

The source Makefile uses ACME and Dali, with packed execution entry `$E000`; `fullvec_start` is explicitly assembled there. The relocated helper/pattern block starts at `$0400`, and its `start` loop aligns to `$0600`, cycling render/copy/switch/cleanup for buffers 1, 2, and 3. No ACME binary was installed in this environment, so optional symbol/report output was not generated.

All reused-source hashes are in `build/research/next-round/reused-source.json`; `downloads.json` identifies the new release/announcement fetches. `embedded-data.json` contains the parsed example records; `patterns.json` contains the exact two-bit selector expansions. `pattern-atlas.png` visualizes those source bytes with an illustrative palette and is **not** a native VICE capture. Disk hashes and offline directory listings are separate files.

## Native standalone confirmation

The exact published `full.prg` ran unmodified in the owned PAL VICE session
`build/research/next-round/standalone-live-01/`. The original SFX reached `$E000`
at stopwatch 5,089,734; initialization then reached the three-buffer loop at
`$0600`. Native captures show the initial white quad and its later green/white
stippled appearance. The latter was captured after 54 calls through the supplied
frame records. The session was closed cleanly after recording RAM and I/O.

At the sampled loop boundary, physical I/O reads gave `$D011=$1B`, `$D016=$D8`,
`$D018=$D9`, and `$DD00=$C0`. These establish multicolor text and the selected
screen/charset bank for that moment. Unused register bits account for the high
readback bits; palette registers read `$F6/$F1/$FD` for background, MC1, and MC2,
consistent with the source's low-nibble palette. This is a sampled state, not a
complete raster-split trace.

The CPU had `$01=$34`, mapping RAM over I/O. Therefore a default CPU-space read
of `$D011` misleadingly returns RAM zero, not VIC state. The transcript records
the subsequent explicit `bank io` reads; raw charset captures use `bank ram`.
That distinction also allows the RAM charset at `$D800` to be examined without
confusing it with Color RAM.

`research/next-round/verify_pattern_capture.py` compares the source definitions
with the native capture. Both relocated pattern tables at `$0400..$0417` match,
as do all twelve eight-byte pattern glyphs in each of the three charsets:
**36 of 36 glyph checks pass**. The exact capture, definition, and source hashes
are in `standalone-live-01/pattern-verification.json`.

This confirms the published example executes the documented pattern machinery.
The separate original-production investigation below establishes the pictured
two-cube preparation. No production frame rate is inferred from the small test.

## Original disk-3 scene and native two-cube match

The original normal-DOS bootstrap, SHA-256
`a5441eea42eab6f7bbe9566403cf5eae9b86e2e17dbdadeca7813ad6ae6682ec`,
ran with the original `round3.d64` attached. It reached the first stage at
`$0800`, then the fullscreen renderer at `$E000` through the original loader
and wrapper. Warp was enabled only to advance through the preceding stage and
disabled at `$E000`. PC, payloads, disk sectors, and renderer code were not
changed. The session and transcript are in
`build/research/next-round/production-round3-live-01/`.

At the original renderer entry, raw native RAM matches all bytes of three
independently unpacked production files, with no exclusions:

| Original custom file | Destination | Matching bytes |
| --- | --- | ---: |
| 6: renderer | `$2000..$6CBC` | 19,645 / 19,645 |
| 7: scene data | `$6CBD..$C5FF` | 22,851 / 22,851 |
| 8: initialization | `$E000..$E7EC` | 2,029 / 2,029 |

The renderer's `$2000..$5D3C` block is byte-identical to the corresponding
standalone block before initialization patches. The production's used command
stream ends at `$C571` and contains **536 frames and 2,402 polygons**, including
578 nonconvex fragments. It is a prepared 2D stream, not the example's single
quad and not complete framebuffer images.

Input pose 376 contains the ten regions described above. The adjacent original
native pose is captured in `scene-frame-377.png`, visibly reproducing the same
two-cube geometry and slotted surfaces as the supplied image. The full native
RAM is `ram-scene-377.bin`. Explicit physical I/O reads confirm multicolor text:
`$D011=$1B`, `$D016=$D8`, `$D018=$D9`, `$DD00=$C0`; the low palette nibbles are
background 6, MC1 1, and MC2 13. Both pattern tables and all 36 reserved glyphs
again match the source definitions. Receipts are `payload-comparison.json` and
`pattern-verification.json`.

An exact-rational audit of continuous polygon coverage finds positive-area
overlap in only two of 7,960 within-frame pairs. Those tiny exceptions are
documented separately; this is not a claim of zero raster-pixel collisions or
a reconstruction of the unavailable exporter. The overwhelmingly partitioned
input and the concrete two-cube region patterns establish a much narrower
contract than a general transparent overdraw engine.

The complete extraction, input ordering, and geometric audit are documented
in [the original-scene investigation](next-round-scene.md).

Further work concerns the unavailable exporter, exact preparation of other
poses, and complete renderer timing. Preserve the distinction between runtime
polygon rasterization, precomputed geometry/visibility, and stored image
playback when comparing this with our runtime geometry plus XOR-prefix engine.
