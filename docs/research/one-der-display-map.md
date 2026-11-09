# One-Der: the column-major charset and its visible sample geometry

Research date: 8 November 2026. This extends the
[original shading study](one-der-gouraud.md). The software planes at
`$2000/$2800` are ordinary multicolor character data in the sampled
interior text region. A shared screen matrix arranges the characters
column by column. No new native execution or product changes were needed.

## The address trick

The source initializer at `$206B..$20C3` constructs a 16×16-character
matrix beginning at screen column 12 in screen `$0400`. For canvas column
`c` and character row `r`, its character code is:

```text
code = 16*c + r

screen row  0:   0  16  32  48 ... 240
screen row  1:   1  17  33  49 ... 241
...
screen row 15:  15  31  47  63 ... 255
```

The loop retains A across columns: the branch at `$20C2` targets `$206E`,
after the initial `TXA`. Each column's sixteen additions advance A by
16. Replacing that control flow mentally with `A=X` on every iteration
would predict the wrong matrix.

A glyph occupies eight consecutive bytes. Therefore, with glyph row
counter `rc` and logical Y coordinate `y=8*r+rc`:

```text
address = charset + 8*(16*c+r) + rc
        = charset + 128*c + y
```

All **2,048 byte offsets** are unique and cover the plane exactly.
Moving one line vertically increments the address; moving one byte
column horizontally adds 128. This is the character-column arrangement
the user originally described. It does not require a new address lookup
for every vertical pixel.

The exact generator bytes are guarded. All **256 matrix entries** and
their **256 Color RAM cells** agree in seven retained captures:
**1,792 matrix-byte checks and 1,792 color-byte checks**.

## What the actual VIC state proves

Two interior captures independently bind the screen layout:

| Capture | Raster/cycle | Cached matrix row | Glyph RC | Selected charset |
|---|---|---:|---:|---|
| `shade-start` | 71 / 22 | 2 | 4 | `$2800` |
| `kernel-start` | 81 / 45 | 3 | 6 | `$2800` |

Their captured VIC state has BMM/ECM off, multicolor text enabled and
Color RAM `$08` for all sixteen canvas columns. CIA2's two bank-selection
bits are outputs selecting bank 0; D018 selects screen `$0400` and
charset `$2800`. All sixteen cached screen codes and colors agree with
the expected row. The reader also checks the corresponding glyph-address
formula against the cached RC.

These are **ordinary multicolor text rows**. They do not establish a
special 4×4 display mode for this renderer merely because another Graham
demo used such a technique. The source-defined canvas is nominally
**64×128 multicolor samples**, or **128×128 physical display pixels**.
It occupies sixteen characters horizontally and vertically.

This is not complete scanout acceptance. At raster 178 the original IRQ
switches to the portrait bitmap below the object. The exact boundary
pixels and all 128 nominal rows still need an execution/scanout model.
The stopped-state addresses are potential row fetches, not evidence that
every such byte had already reached the display when the monitor stopped.

## Why one packed byte is two shading samples

Each byte contains four two-bit VIC selectors. In multicolor text each
selector spans two physical horizontal pixels. The renderer combines a
high nibble and a low nibble, so each nibble covers two VIC selectors,
or four nominal physical horizontal pixels. Dither coverage and the
number of independently interpolated intensities are different counts.

For the already verified output byte `$9A`:

```text
nibbles:             9       A
VIC selectors:       2   1   2   2
physical replication:2 2 1 1 2 2 2 2
```

The sampled palette at `kernel-start` is indices `[3,14,6,0]` for
selectors 0..3. If displayed with that palette, the four selector pairs
would use `[6,14,6,6]`. This is a conditional interpretation: the verified
byte plot writes the draw buffer `$2000` while the VIC displays `$2800`.
It is not a comparison with already committed pixels.

The seven packed ramp codes from the earlier study remain separate from
HCL's thirteen-level tracing technique. This companion establishes the
ordinary multicolor footprint; it does not add simultaneous VIC colors.

## Clearing to `$FF` is intentional

Source `$0D28` toggles the draw-buffer selector and clears all eight pages
of the selected 2 KB plane to `$FF`. There is no dirty-region tracking in
that routine. Every two-bit pair in `$FF` selects color 3. The canvas's
Color RAM `$08` enables multicolor while selecting black as color 3.
Thus the cleared outside is black even when the three global colors fade
or form the bright object palette. Clearing this layout to zero would
select its global background color instead.

## Reproduction and limits

```sh
rtk proxy python3 research/one-der/display_map.py --output build/research/one-der/display-analysis/fresh-replay
```

Choose an unused directory. The passive producer pins and reuses the
earlier original-file/native acceptance, then rehashes each retained
RAM/snapshot input. Its final receipt is
`build/research/one-der/display-analysis/accepted-01/display-proof.json`,
6,277 bytes, SHA-256
`5c39d0d9f172220e0235012d1cb0b8f453add416ff1518502a78f9483e9a0d53`.
It also emits the exact 256-cell matrix as CSV and a checked producer.

The remaining image task is to compare the complete software rasterizer
with the captured output, then bind that output to the actual raster
fetches and lower display transition. The current cached-row observations
do not stand in for either of those stronger results.
