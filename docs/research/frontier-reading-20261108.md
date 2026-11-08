# Repeated bob scrolling: one charset, ten views, one loaded map

Research date: **8 November 2026**. This adds a source-and-asset check of a
previously uncovered mechanism: **No Bounds' Scrolling Bob Scroller**. It is
separate from the demo's already checked finite-bob background restoration
and loading protocol. It is an older mechanism recovered during the current
frontier search, not a newly released 2026 effect.

Fresh, bounded checks of [Trident's article index](https://trident64.github.io/),
[Quiss's homepage](https://www.quiss.org/) and
[Raistlin's index](https://c64demo.com/) did not recover an original Hat
upscroller or Aloft pattern/Kefrens implementation. The already documented
creator/peer distinction remains in [the February note](february-2026.md).
The new October 2026 loading article also proved to be covered by the
[existing loading analysis](no-bounds-loading.md), so it is not counted again.
The three freshly acquired index bodies are retained with the new evidence.
No video summary or neighboring viewer comment fills the unresolved source
gaps.

## The author's representation and the actual source

Raistlin's [8 June 2023 article](https://c64demo.com/scrolling-bob-scroller/)
explains repeating a bob path at diagonal offsets of **80 pixels**, plotting
the changing shape into a shared charset, and selecting among **ten** screen
maps for coarse movement. Fine X/Y scrolling supplies the remaining pixel
phase. The article calls the shape's character requirement **144**. These
statements concern *No Bounds (2023)*, not Aloft.

The matching implementation is
[`NoBounds/Parts/TinyCircleScroll`](https://github.com/RobertTroughton/C64Demo-PublicReleases/tree/965807c511e2025b5c5e1ffb2a6235a4efd6ae5b/NoBounds/Parts/TinyCircleScroll),
pinned to commit **`965807c511e2025b5c5e1ffb2a6235a4efd6ae5b`**, committed
**25 December 2025, 01:20:37 UTC**. This post-release source snapshot is not
silently equated with bytes on an original 2023 production disk.

The C++ generator uses **104 text positions**, three motion phases and a
five-pixel-wide, five-pixel-high font. Its rounded-star path has radius
`85 + 15 sin(5a)` and centers displaced by `(80,80)`. After clipping, it retains
the diagonal character band `15 <= X+Y < 35`. Character indices are assigned
in row order to cells touched in any of the three phases. The assembly plots
the changing text into that shared character data; screen maps refer to it
repeatedly. These are repeated references to one glyph image, rather than
separate bitmap copies updated for every visible repetition.

An independent coverage oracle enumerates every pixel of each clipped 5×5
rectangle. The original generator instead records per-row byte contributions
and handles right-byte spill. The oracle finds **143 nonblank character
cells**, assigned indices 1–143; index 0 is blank. Thus **144 including blank**
agrees with the article and the supplied map's actual index range.

## All ten published maps match a separate quotient construction

The published
[`Screen.bin`](https://github.com/RobertTroughton/C64Demo-PublicReleases/blob/965807c511e2025b5c5e1ffb2a6235a4efd6ae5b/NoBounds/Link/TinyCircleScroll/Screen.bin)
contains ten **1,024-byte** maps. Each has 1,000 visible screen cells and 24
zero padding bytes. The source splats each occupied base cell into up to eight
diagonal copies. Our checker instead visits each destination cell once and
resolves its representative in the retained diagonal band.

For screen phase `s`, visible destination `(x,y)` and repeat index `r`:

```text
r = floor((x + y + 38 + 2s) / 20)
X = x + 23 + s - 10r
Y = y + 30 + s - 10r
```

The cell contains the coverage oracle's character index at `(X,Y)`, or zero
if no such occupied cell exists. This follows the diagonal translation
period and gives a unique representative because the retained band has
width 20 in `X+Y`.

The result matches **all 10,240 published bytes**, including padding, with
zero differences. Changing the assumed period from ten characters to eight
produces **3,506 differences**. This negative control shows that arbitrary
repetition is insufficient; the specific path spacing and screen maps matter.

## The executable setup needs only the first screen map

The source's
[`TinyCircleScroll.sls`](https://github.com/RobertTroughton/C64Demo-PublicReleases/blob/965807c511e2025b5c5e1ffb2a6235a4efd6ae5b/NoBounds/Parts/TinyCircleScroll/TinyCircleScroll.sls)
loads only file offset `$0000`, length **`$0400`**, of `Screen.bin` at `$C000`.
The assembly's `SetupScreens` constructs the other nine maps. The screen
addresses are `$C000,$C400,$C800,$CC00,$E000,$E400,$E800,$EC00,$F000,$F400`.
They share the charset at `$F800`; the sprite areas account for the gap.

Each construction first copies 1,024 bytes from the previous screen plus
**41 bytes**: a one-row, one-column diagonal displacement. It then repairs
the right and bottom edges using either blank cells or the same diagonal
period. Simply copying the shifted window would pull unrelated bytes into
the new edge and would not preserve the tiled shape.

The checker follows the source's interleaved four-page copy order, including
aliasing when a read reaches a destination already written. Every byte
outside the one loaded 1 KB map starts **unknown**, not fabricated as zero.
For the `$CC00`→`$E000` construction, the initial window can read beyond the
old screen into `$D000`; some later padding also remains unknown. The edge
repairs remove every such dependency from the visible cells. Across the
nine synthesized screens, **all 9,000 visible character cells** equal their
corresponding published maps, and **none remains unknown**.

Omitting the repairs immediately creates **18 wrong visible cells** in the
first derived screen. By screen 4 it also leaves **17 visible unknowns**.
That control distinguishes actual boundary handling from a successful
comparison obtained by preloading all ten expected maps.

This establishes a source-defined setup transformation, not its executed
instruction bytes or runtime duration. In particular, the 24 padding bytes
of each synthesized map are not required to equal `Screen.bin`'s padding;
sprite pointer publication has separate consumers.

## Cheap coarse selection is present in the supplied PRG

The source-generated 256-byte movement table also matches its published
`SinTable.bin` in every byte. Values are **0–79**. `DoMainScreenUpdate`
uses the low three bits for the fine-scroll tables and three right shifts
for the coarse screen index 0–9.

The supplied `TinyCircleScroll.prg` loads at `$2000`. A **36-byte** sequence
containing the ten `$D018` choices, both eight-byte fine-scroll tables and
the ten sprite-pointer-page choices occurs once at PRG file offset **51**,
corresponding to loaded address **`$2031`**. The `$D018` values are:

```text
0E 1E 2E 3E 8E 9E AE BE CE DE
```

All choices retain charset selection 7 and change the screen selection.
This joins concrete published bytes to the source's representation. It does
not identify the whole supplied PRG with an independently rebuilt source
or extract that PRG from a released disk.

## Reproduction, identities and limits

The offline producer uses only the Python standard library:

```sh
rtk proxy python3 research/frontier-2026/reading_next.py
```

[`reading_next.py`](../../research/frontier-2026/reading_next.py) validates
**27 acquired HTTP bodies**, their pinned acquisition index, commit/tree
metadata and **20 immutable Git blob identities** before checking the
geometry, maps, setup recurrence, negative controls and selection tables.
The archive includes the initial commit-addressed tree response as well as
the tree fetched by its actual tree-object SHA. No downloaded C++, assembly,
packer, loader or host tool is imported or executed.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `Screen.bin` | 10,240 | `c125722e795caf7d173e8ed81b2f2bf94d9409b9b44168fa05409e695293431a` |
| `SinTable.bin` | 256 | `ae5399186e178bd5b4346d74ae525ca54bb76a9ee8f61ed3d68f18ce2785dfe1` |
| `TinyCircleScroll.prg` | 17,358 | `3a2f84689904ae23e033c5456e1a29bb5d9026f7ce216682072df214555c0212` |
| Tracked producer | 9,946 | `886171f81020a489a1890892fd9e2b0f5e81d37f1afa4390d6b8b86a1fdff2cc` |
| `reading-findings.json` | 11,687 | `9b4705999561d154a9688d294411ab4cf788155482a3749eb146a51a3b447963` |

Original bodies, response headers and the final receipt are retained under
ignored `build/research/frontier-reading-20261108/`. A fresh checkout needs
that retained input archive to repeat the offline producer.

There was **no native execution, VICE/process control, C64 CPU execution,
scanout reconstruction, source build, original-disk payload equivalence or
measured frame/cycle budget**. The transferable representation is bounded:
when copies can share character data and a periodic path, stored screen
references can supply visible repetition and coarse motion. Arbitrary
independently moving objects or differently colored overlaps would need
their own representation and checks. A useful next case would extract the
original 2023 part and bind its setup/plotter bytes before measuring display
publication or discussing rendering savings.
