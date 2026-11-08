# Three stored character phases with paired sprite underlays

This original standalone example implements the first-display mechanisms
documented for **Colors** in
[the architecture notes](../../docs/research/colors-first-display.md) and
[the pixel reconstruction](../../docs/research/colors-first-display-pixels.md).
The mathematical picture, sprite masks, reveal permutation and controller are
ours. No released Colors artwork or program bytes are included.

```sh
cd experiments/three-phase-colors
sh build.sh
sh run.sh
python3 verify.py
```

The shared builder uses the existing KickAssembler installation. The native
verifier uses the repository's VICE monitor helpers, Pillow and Colodore
palette. It starts and closes its own PAL VICE instance. `run.sh` selects
`-gluelogictype 1`, the 252535-01 digital bank-transition model used by the
verification. Additional VICE options may be passed to `run.sh`.

## Stored picture and ordinary loading

There are three stored hires character phases in each of four VIC banks.
Each bank supplies six character rows, giving a 320×192 canvas. A character's
code is `6*column + localRow`; its eight bytes follow vertically within the
bank's 48-line part. All 24 screen rows are initialized in every bank, so
cached matrix codes remain defined across the bank transitions.

| Item | Address relative to each VIC bank |
| --- | --- |
| Three sprite masks, 64 bytes each | `$2300`, `$2340`, `$2380` |
| Screen matrix and sprite pointers | `$2400`, `$27F8` |
| Phase 0 font, `$D018=$9A` | `$2800` |
| Phase 1 font, `$D018=$9C` | `$3000` |
| Phase 2 font, `$D018=$9E` | `$3800` |

Each font uses 240 characters, or 1,920 bytes. The twelve used font regions
total 23,040 bytes. The final bank's last used character byte is `$FF7F`, so
the top vector area is outside the picture data.

The PRG loads only `$0801–$79FF`, including packed fonts at `$2000–$79FF`.
It does not load through I/O. After banking out ROM, C64 code relocates the
twelve regions from highest asset and highest byte downward. This preserves
unread packed input while placing fonts into their final bank addresses.
The local relocation include uses the fitting technique demonstrated by
`row-counter-tunnel`; the raster include uses the independent ready-job
polling pattern demonstrated by `sprite-interleave`.

The stored picture uses integer coordinates and the following predicate;
set glyph bits are black foreground:

```text
ring = floor(((x-160)^2 + (2*y-191)^2) / 192)
ink  = (ring + floor(x/7) + floor(y/5) + 5*phase) mod 16 < 8
```

Picture calculation happens during assembly. Runtime work selects a stored
phase, changes banks, reveals sprite bytes and moves the sprite coverage.
This example does not compute the mathematical image on the C64 each field.

## Bank schedule and sprite history

The CIA2 data latch `$DD00` keeps both bank bits low. Bank selection uses
the **direction register** `$DD02`: output bits drive low and input bits
use their pull-ups. Values `$3C`, `$3D`, `$3E`, `$3F` select banks `$0000`,
`$4000`, `$8000`, `$C000`. The controller writes these on raster lines
4, 102, 150 and 198. The active 192 lines are raster 55 through 246.

The three active-display changes occur during character fetches. Their
recorded cycles vary with sprite DMA; this is not an atomic switch between
whole six-row rectangles. In the 99-field run the monitor reported cycles
37–47 on line 102, 37–46 on line 150 and 38–46 on line 198. The pixel oracle
uses every actual write's clock
and the individual column's glyph-fetch clock. It also includes GLUE type
1's temporary bank-3 glyph fetch during the `$3D→$3E` transition. No pixels
at those boundaries are excluded from comparison.

Sprites are hires, unexpanded and behind black character foreground. Four
pairs `(0,4)`, `(1,5)`, `(2,6)`, `(3,7)` share X positions 24 pixels apart.
The lower-numbered sprite has priority within each pair. Blue is the
background where neither selected mask draws. The 96-pixel coverage window
moves three pixels per field through 32 positions, including the X-MSB
boundary. All eight Y registers restart at 54, 75, …, 243; the next restart
is scheduled eight lines early, while the previous sprite DMA finishes.

| Phase | Sprites 0–3 pointer / color | Sprites 4–7 pointer / color |
| --- | --- | --- |
| 0 | `$8C` / red | `$8D` / green |
| 1 | retain pointer / green | `$8E` / red |
| 2 | `$8D` / red | retain pointer / green |

The initial field is phase 1 with deliberately non-warmed pointers
`$8D/$8C`. Consequently its retained lower pointer is `$8D`; the next
phase-1 field retains `$8C` from phase 0. The verifier proves this difference
instead of treating a phase number alone as the complete sprite state.
Current pointer tables and mask bytes are replicated into all four banks.

Our three disjoint sprite masks partition the 24×21 pixels using
`(x + 2*y + floor(x/6)) mod 3`. Each has 168 set pixels. Initially all slots
are blank. Every field copies one chosen byte from **each** mask into all
four banks. The own permutation `(17*i+5) mod 63` reveals every byte once;
the masks are complete after field 63. This reveal and the moving coverage
are independent of the stored character phases.

## Native verification and cadence

The default 99-field run passed in normal-speed PAL VICE. Its
[receipt](build/verification/receipt.json) records the exact command and
program SHA-256
`7ec7a4479cd55d0dbe29c5e548e08dcb126120cb6f8f6fc9a78614914c1f7292`.
The checks include:

- Ordinary-load payload bytes before the first instruction, all 23,040
  relocated font bytes, all four 960-byte matrices, pointer tables and
  partially revealed sprite slots on every field.
- Independent coordinate-based picture and mask expectations for all
  61,440 canvas pixels, plus the complete 384×272 native screenshots.
  Bank boundaries, sprite-pair seams and all ten Y restarts are included.
- Three-phase ordering, retained-pointer history, red/green swaps, all
  396 direction-register stores and 7,920 sprite-Y stores. No data-latch
  bank writes occur during these fields.
- All 63 reveal steps, wrap of the 32-position motion, and 96 consecutive
  warmed phase/motion states. The reveal is still in progress during some
  of those states; the run does not claim all 96 combinations with fully
  revealed masks.

The independent model would change 706 compared pixels if it ignored the
temporary GLUE bank and 27,326 if it assumed whole six-row bank rectangles.
These checks demonstrate why final register snapshots alone are insufficient.

There is one state update per PAL field. Completion samples averaged
19,656.071 clocks, with intervals 19,649 / 19,656 / 19,663 caused by the
polling completion point; the raster schedule remains one field apart.
That is about 50 updates per second, with a three-field character-phase
cycle. The [inspection GIF](build/verification/three-phase-colors.gif) uses
100 ms per captured field and is deliberately slower than the running demo.

![Native field 99](build/verification/field-099.png)

This verifies literal digital field pixels in the stated VICE model. It
does not establish a static RGB mixture, an effective palette, analog
display behavior or physical C64 hardware behavior. The original artwork,
its reveal ordering, later demo sections and original machine code are
outside this counterpart.
