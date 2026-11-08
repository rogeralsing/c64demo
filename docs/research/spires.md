# Spires: seven-sprite FPP and character-mode TechTech

The published source explains the seven-sprite checkerboard's three 21-byte
bands and its 7/14-line Y changes. The supplied TechTech assets independently
verify five exact coarse translations of 0, 8, 16, 24 and 32 physical pixels.
The source combines those five charset phases with eight VIC fine-scroll
values to obtain all 40 horizontal positions. Its ten charsets are arranged
as five phases in each of two vertical display banks, rather than ten coarse
horizontal phases.

This is source and prepared-asset evidence. No source is assembled, no supplied
host tool is run, no original 6502 instructions are executed and no native
display is observed. The passive producer is
[`research/spires/inspect.py`](../../research/spires/inspect.py); its receipt is
`build/research/spires/analysis/spires-proof.json`.

## Primary provenance and source availability

The [author's Spires page](https://www.elder0010.com/projects/spires/) describes
the 2012 Onslaught demo and attributes its checkerboard and lower scroller to
Freshness. It describes staggered sprites, the vertical offsets and shifted
charsets. Its [CSDb release link](https://csdb.dk/release/?id=108322) supplies both
the original release and the source ZIP. These are the positive source trail;
the author's current ten-repository GitHub inventory is not used to infer
that source is absent.

| Download | Bytes | SHA-256 |
|---|---:|---|
| [Original release ZIP](https://csdb.dk/getinternalfile.php/105505/Spires_-_Onslaught.zip) | 25,729 | `7a895ee1723a550002f70d57c386c807d74ab2e059dddc3b29658cc707832894` |
| [Published source ZIP](https://csdb.dk/getinternalfile.php/106229/spires_source.zip) | 449,528 | `ae83489bef116bcfe5b018e6446dfdac0e91c39893c3c08946c4421fa0189d82` |
| Original D64, also present in the source ZIP | 174,848 | `2e7299b1cd0bfc8dac4aa7886a472255be4f1ca9429964d526ba9c84e8d2175d` |

The source ZIP's `spires-onslaught.d64` equals the release ZIP's
`Spires_-_Onslaught.d64` byte for byte. This establishes shared release data,
not equality between a newly assembled source build and the released program.

`build/research/spires/acquisitions.json` retains original and final URLs,
retrieval timestamps, HTTP status, headers, body identities and paths. The
author and CSDb HTML bodies are pinned along with both ZIPs. A direct Demozoo
request returned HTTP 403; that response body is retained as a retrieval
failure, not treated as release evidence. The independently accessible web
view supplied the same release link during discovery.

ZIP paths, sizes, CRCs and symlink types are checked before extraction.
Metadata entries remain inventoried in their archives. The source archive
contains 46 extracted nonmetadata files. No executable file from it is run.

The original D64 contains decorative closed-DEL directory entries plus two
nonempty PRGs:

| DOS file | Bytes | SHA-256 |
|---|---:|---|
| `SPIRES       [O]` | 12,427 | `bf41f4736d09408b30671e0c622fd6922032f9b14820d355403040c45adef791` |
| `NOTE         [O]` | 6,682 | `16f19c641a7dce716ee96f47be17351a9fe1b6a51d5d1a6497cd28cf7da0d37d` |

Both literal load headers are `$0801`, with BASIC `SYS2061` (`$080D`). DOS
sector chains are extracted and checked; the runnable payloads are not
depacked or executed. Their paths are `dos-files/11.prg` and `dos-files/12.prg`.

## Seven sprites and three data bands

`fppinc.asm` identifies itself as Freshness's FPP zoomer. Its declared base is
`$8000`: sprite tables occupy `$8000..$8FFF`, code starts at `$9000`, charset
space starts at `$A800`, and the screen is `$AC00`. `setgraph` selects the
corresponding VIC bank and `$D018=$BA`. The source's `$D011` values keep bitmap
mode clear; the text characters provide masking around the sprite effect.

The source sets `$D015=$FE`, using sprites **1 through 7**. The first sprite's
Y is selected from 61, 54 or 47. The remaining six Y values descend by one:

| Band | Sprite 1 through 7 Y registers | Data bytes within each definition |
|---|---|---|
| 0 | 61, 60, 59, 58, 57, 56, 55 | 0..20 |
| 1 | 54, 53, 52, 51, 50, 49, 48 | 21..41 |
| 2 | 47, 46, 45, 44, 43, 42, 41 | 42..62 |

The Y registers are direct source facts. The data-column interpretation
requires the source-intended held counter phase: seven consecutive three-byte
triplets, then another 21 bytes when all starts move seven lines earlier.
Native MCBASE and expansion-flop captures must verify that actual phase before
calling these table entries observed hardware offsets.

The preparation routine makes the packing unambiguous independently of that
timing question. Each of two complementary banks has 32 definitions of 64
bytes. Three passes write 21 bytes into each slot, starting at offsets 0, 21
and 42. Thus one slot holds three stripe widths. Across both banks:

```text
32 definitions × 3 bands × 21 bytes × 2 complements = 4,032 written bytes
32 definitions × 64 bytes × 2 complements          = 4,096 allocated bytes
```

Byte 63 in every definition is not written by this preparation routine. The
producer marks all 64 such bytes unknown. Zero placeholders in its generated
file are not claims about those unwritten runtime bytes.

For generated stripe width `w=1..96`:

```text
slot = (w−1) mod 32
band = floor((w−1)/32)
first byte = slot×64 + band×21
pixel bit at horizontal position p = floor(p/w) mod 2
```

The second bank complements the first. The audit compares that closed form
against a separate source-derived run-counter/sentinel-ROL description for
all 96 widths and all **4,032 meaningful output bytes**. Both descriptions
agree. This validates source arithmetic, not an independently captured runtime
table.

The runtime source chooses slot `z & 31`, band `z >> 5`, and complement through
pointer bit `$20`. Its two 256-byte Z tables contain values 5 through 95. The
generated horizontal stripe width selected by this indexing is `z+1`. The
source's selector instructions are separately checked over all 256 possible
input bytes, including the fact that they leave carry clear. This detail is
preserved rather than replacing the indexing with an approximate zoom model.

## Pointer changes and expansion timing

There are 130 literal `wait46bg` macro invocations, numbered 1 through 130,
plus the initial pointer entry: 131 pointer rows. Each macro writes one
selected pointer to `$ACF9..$ACFF`, covering the seven used sprites.

The source order matters: it writes zero to `$D017`, updates six sprite
pointers, writes `$FF` to `$D017`, then updates the seventh pointer. X is
prepared as `$FF` and Y as zero. The same macro also writes a changing fine-Y
value to `$D011`. This is an expansion/counter trick with pointer-fed rows;
it is not software filling a conventional framebuffer.

One expanded macro is 35 bytes and has 46 nominal CPU instruction cycles.
Those are static opcode costs. They exclude VIC bus stalls, interrupt entry
and scheduling. The source alone does not certify the write phases, held
counters, a 63-cycle row schedule or a measured frame rate.

## TechTech: five phases per vertical bank

The main source imports ten 2,048-byte charsets at these physical addresses:

| Coarse phase | First bank | Second bank | Horizontal translation |
|---|---|---|---:|
| 0 | `chs00.raw` at `$4000` | `chs10.raw` at `$C000` | 0 pixels |
| 1 | `chs01.raw` at `$4800` | `chs11.raw` at `$C800` | 8 pixels |
| 2 | `chs02.raw` at `$6000` | `chs12.raw` at `$E000` | 16 pixels |
| 3 | `chs03.raw` at `$6800` | `chs13.raw` at `$E800` | 24 pixels |
| 4 | `chs04.raw` at `$7000` | `chs14.raw` at `$F000` | 32 pixels |

Both screen matrices import the same 1,024-byte `tech_chars/lut.raw`, at
`$7800` and `$F800`. The code splits after 19 character rows: 152 pixel rows
use the first charset bank, and the remaining six character rows use the
second. The same screen-code arrangement can therefore address different
glyph definitions above and below the split.

For each coarse phase the producer reconstructs all 40×25 character cells,
using the appropriate top/bottom font. Every reconstructed 8,000-byte glyph-row
image equals phase 0 translated by exactly 0, 1, 2, 3 or 4 complete character
columns, with zero-filled left edges. All **40,000 compared glyph-row bytes**
agree. One character column corresponds to eight physical display pixels.
This byte relationship also holds independently of the eventual palette.

Reusing the upper charset bank for the lower rows gives 622, 632, 642, 579
and 579 wrong glyph-row bytes across the five phases. The two banks cannot be
collapsed into five charsets without changing these assets.

The literal `$D018` table selects phases as follows:

```text
$E0 → phase 0   $E2 → phase 1   $E8 → phase 2
$EA → phase 3   $EC → phase 4
```

The paired `$D016` table uses `$D8..$DF`. Its low three bits add hardware fine
scroll from 0 through 7. Combining each literal pair gives:

```text
horizontal position = 8×coarse_phase + (D016 & 7)
```

Both tables have 256 entries. Their combined positions cover every integer
from 0 through 39, and adjacent entries change by at most one pixel. At a
charset boundary, a one-column coarse change accompanies the fine-scroll
wrap, keeping the displacement continuous. `fill_line` writes the two table
values as raster work proceeds; the effect moves rows by selecting prepared
glyphs and fine scroll while retaining the screen layout.

The `$D016` literals have the multicolor-character bit set. The source also
uses character mode in `$D011`. Runtime color RAM, palette fades and the exact
bank-switch scanline are not observed by this audit. These prepared glyph
checks are not presented as native VIC palette pixels.

## Generator and build limits

All ten `tech_chars/chs*.raw` files equal their counterparts in the tool
folder: 20,480 equal bytes. However, `techer tool/lut` differs from the demo's
`tech_chars/lut.raw` in **817 bytes**, all within the visible 1,000-cell region.
The audit retains this rejected identical-LUT assumption and uses the demo
matrix consistently. It does not claim a successful generator round trip.

The supplied `techer tool/techer` is a 27,056-byte x86-64 Mach-O executable.
Only its header and embedded usage strings are read. No C/C++ generator source
is in the archive, and the executable is never run. The author's custom-tool
description therefore remains attribution; the exact prepared-asset relations
are independently established from the supplied bytes.

The reachable main-source imports are missing:

- `tech_chars/logo_liscio/s.prg`
- `tech_chars/freshzoom.prg`
- `sc3800.prg`
- `tech_chars/logo_liscio/f.prg`

The archive supplies `fppinc.asm` and `scroll3.asm`, but this audit does not
assemble them into substitutes for missing binaries or silently repair the
listing. The separate FPP source also has bare address lines in its pointer
initialization block that need review before a build attempt. Original-disk
identity, source mathematics and asset relationships are separate results;
a complete source rebuild or original-executable comparison remains open.

## Replay and next native questions

Replay all passive checks from the repository root:

```sh
rtk proxy python3 research/spires/inspect.py
```

The output folder contains the receipt, a checked producer copy, generated
FPP bytes plus their known mask, five reconstructed glyph-row images, and the
literal register tables. Acquisition bodies, source members, original disks
and DOS files remain separately retained with exact identities.

The next useful native work is bounded and does not require a source rebuild:

1. Boot the original D64 and retain the original runnable entry path. Do not
   jump directly into `$9000` before its actual FPP code and initialization
   are loaded.
2. Bind the actual `$9000` service table, seven-pointer row sequence and sprite
   generator to the published source. Record mismatches as build variants;
   do not assume the missing `freshzoom.prg` equals an unassembled listing.
3. Observe all three Y groups, `$D017` write phases, MC/MCBASE and actual
   three-byte row fetches. Test the intended offsets `0,3,..18`, `21,24,..39`
   and `42,45,..60` before claiming all three data bands are observed.
4. At mature TechTech, compare all ten actual charset images and both screen
   copies with the retained assets. Trace `$D016`, `$D018` and the actual VIC
   bank changes through the 19/6-row split. Only then compare committed VIC
   pixels with an independent character-mode oracle.

Any native capture belongs in a fresh directory owned by the native lane.
This source/asset receipt supplies inputs and testable expectations, not a
native timing, counter-phase, framebuffer or FPS witness.
