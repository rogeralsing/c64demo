# Sprite-to-character 2D transition

This original standalone example follows the three concrete mechanisms in
Next Level's **TransBox**: paired sprites on adjacent prepared path samples,
opposite character/Color RAM row shifts, and an expanding raster-border band
followed by a bounded quadrant wipe. It is a **2D transition**, not a
transparent 3D renderer.

The inspected source is
[TransBox.asm at the pinned author commit](https://github.com/bboxy/next-level/blob/57643d53a97cdf38778958d8ebf99341315f834e/parts/transbox/TransBox.asm),
with [includes.asm](https://github.com/bboxy/next-level/blob/57643d53a97cdf38778958d8ebf99341315f834e/parts/transbox/includes.asm).
Relevant source areas are initialization 25–90, paired Jumper 691–737,
opposite shifts 339–454, and expansion/wipes 231–333 and 585–663. The
archived selection references an unavailable `assets/charset_box.prg`;
there is no released-picture pixel-match claim.

Our code, path, text, geometric glyphs and solid sprite artwork are new.
The existing project [5×7 font helper](../lib/font5x7.py) supplies letters
and digits by import; its source is not copied into this example.

```sh
cd experiments/sprite-character-transition
sh build.sh
sh run.sh
python3 verify.py
```

Build uses Python's standard library and the shared KickAssembler helper.
Run and native verification select normal-speed **PAL 6569** explicitly.
Verification uses the existing Pillow, native monitor helper and Colodore
palette. There is no research-cache or released-asset dependency.

## One coherent sequence

The normal program repeats a 192-field sequence. At approximately 50.12 PAL
fields per second, one complete sequence lasts about **3.83 seconds**.

| Fields within sequence | Visible operation |
| --- | --- |
| 0–47 | Four colored sprite pairs follow adjacent prepared 2D samples |
| 48–95 | Character row 10 rotates left; row 14 rotates right, with their colors |
| 96–143 | The border band expands two raster lines per edge per field |
| 144–191 | Four bounded quadrants clear, then the initial scene returns |

The second stage begins with the unshifted rows and performs 47 cyclic
shifts. Each shift moves all 40 character bytes **and** their corresponding
Color RAM bytes in the same direction. The upper and lower rows move in
opposite directions. This work happens on the C64, not in stored animation
screens.

The third stage expands the band from its initial 146–162 region to
50–250. The upper-right, lower-left, upper-left and lower-right quadrants
then clear in that order. Each quadrant has ten two-column clearing steps
and two holding fields. Upper quadrants cover rows 0–11; lower quadrants
cover rows 12–24. All columns stay in 0–39.

## Actual sprites, raster stores and wrap

Eight unexpanded hires hardware sprites form four pairs. Each member draws
a solid 16×16 half; the second member is offset 16 pixels horizontally.
Four pairs use path samples `phase`, `phase+1`, `phase+2`, `phase+3`, with
white, light gray, light blue and blue. Lower hardware numbers have priority
where the moving blocks overlap. All eight members visibly contribute
during the verified sequence.

The 51 prepared scalar samples are our own trajectory:

```text
hardwareX(sample) = 40 + 5*sample
hardwareY(sample) = 132 + round(52*sin(sample*2*pi/48))
```

The C64 reads these samples and programs all eight X/Y registers plus their
X-MSB bits. It does not calculate 3D geometry. The original pairs share
coordinates; our adjacent solid halves make both members visible and are
an explicit own choice.

The raster IRQ writes the border color at the current top and bottom band
lines. The native run observed top-edge stores at raw cycles 35–39 and
bottom-edge stores at 33–37. Therefore a boundary line can have different
left/right border colors. The pixel oracle uses every actual store clock
and the 6569 color pipeline; it does not approximate these as atomic
whole-row changes. Background color stays black.

Font `$2000` and sprite `$2800` are shared. Screens `$0400/$0C00` alternate
at wrap through `$D018=$18/$38`. The hidden screen is restored from the one
initial design in sixteen-byte chunks during positions 0–63. Each wiped
cell becomes a space and gets its initial color restored while that color
is invisible. Consequently the single physical Color RAM is already ready
when the complete hidden screen is selected at the next top IRQ.
This is a two-screen publication scheme, not double-buffered Color RAM.

The ordinary PRG load ends at `$4958`, below I/O. It stores one initial
design, one font, one sprite, scalar path tables and 48 small wipe commands.
There are no complete stored animation frames.

## Independent native evidence

The default verifier runs **385 consecutive fields**: both complete
192-field screen-buffer cycles and a return to the first buffer. Testing
both buffers exercises the shifted-row operands and wipe destinations
after publication, not only the first wrap image.

[The receipt](build/verification/receipt.json) records:

- **40,212,480 exact native pixel comparisons**, every pixel of every
  384×272 screenshot. No sprite, glyph, quadrant or raster-edge pixels are
  excluded.
- Both 1,024-byte screen matrices, all 1,024 Color RAM entries and the
  complete 2,048-byte font on every field.
- An independent reference using list rotations and rectangular regions,
  rather than the C64's in-place loops or prepared wipe-command table.
  Sprite coordinates are independently derived from the scalar path.
- **1,632 actual sprite X/Y/MSB stores**, **9,520 runtime Color RAM stores**
  and **961 border-color stores**. The last Color RAM update precedes the
  following field origin by at least 1,131 clocks. Color updates occur on
  rasters 263–294, entirely outside the visible text interval.
- All three stages, quadrant ends/holding states, both screen selections,
  complete Color RAM restoration and two coherent wraps.
- Explicit ownership and closure of the verifier's VICE process.

Every field origin is exactly **19,656 PAL clocks** after the preceding
one: one sequence update per field, approximately **50.12 updates/s**.
The [inspection GIF](build/verification/sprite-character-transition.gif)
uses 40 ms per native field and is about twice as slow as the running demo.

Verified program SHA-256:
`cd0427c323fd67dc4876e56240f9f3d381bed2fdc17dea5968894b9ea5b82cd7`.

Paired sprites:

![Sprite stage](build/verification/field-001.png)

Opposite character/color shifts:

![Character stage](build/verification/field-073.png)

Bounded quadrant wipe:

![Quadrant stage](build/verification/field-181.png)

The counterpart simplifies the original transition's art, timing, coincident
sprite pairs, fades, middle-row details and demo-loader integration. It does
not claim the released charset, original pixels, transparency, 3D, music,
NTSC, other VIC revisions, analog output or physical-machine verification.
