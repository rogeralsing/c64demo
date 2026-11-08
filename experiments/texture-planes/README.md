# Live complementary texture planes

This original standalone example implements the two-source packed-plane
mechanism documented for Second Reality's EC file in
[the owning research note](../../docs/research/second-reality-ea.md).
The source texture, scalar motion coefficients and program are ours.
No original release artwork, generated drawing program or file bytes are
included.

```sh
cd experiments/texture-planes
sh build.sh
sh run.sh
python3 verify.py
```

These commands use the shared KickAssembler/VICE helpers. Verification uses
the repository's existing Pillow installation, native monitor helper and
Colodore palette. It starts and closes its own normal-speed PAL VICE process.

## What runs on the C64

Two 8 KiB source planes contain complementary bits of multicolor pairs.
Plane A occupies only `$AA` bits and plane B is the same pattern shifted
right one bit, occupying `$55` bits. Their OR supplies all four pair values.
The own 16×256-byte source texture is prepared during assembly, with each
256-byte row duplicated into a second consecutive page. Runtime indexed
loads really cross into those duplicate pages; they retain the same source
row rather than accidentally sampling the next row.

Each output byte is sampled from **two independent coordinate transforms**:

```text
uA,vA = originA + column*horizontalA + row*verticalA
uB,vB = originB + column*horizontalB + row*verticalB
byte  = planeA[uA,vA] OR planeB[uB,vB]
```

Coordinates and signed increments use wrapping 16-bit Q8 arithmetic. The
integer U coordinate wraps over 256 source bytes, and V over 16 source rows.
The C64 builds column offsets, advances row coordinates, propagates the
fractional carries, patches its source operands and executes both indexed
loads and the OR. Source coordinates are not host-prepared animation poses.
Only sixteen small scalar coefficient records and one fixed source texture
are stored in the PRG.

A sampled byte already contains four multicolor pixels. Those four pairs
retain their internal arrangement; this is not four independently sampled
texels or a continuous per-pixel rotation. The two planes have separate
counter-rotating coefficient sets and translations. Their combination is
the feature of this case, rather than a single transformed glyph library.

The C64 writes 31 columns × 96 sampled rows = **2,976 bytes per render** into
three 2 KiB character sets. For band `row/32`, the destination is
`band*$800 + column*64 + 2*(row mod 32)`. Thus glyph rows 0, 2, 4 and 6
receive the live samples. Odd glyph rows and unused glyphs remain zero.
There is no per-image font clear: every populated byte is overwritten.

## Scanout and complete publication

| Item | Buffer A | Buffer B |
| --- | --- | --- |
| Three character sets | `$A000/$A800/$B000` | `$E000/$E800/$F000` |
| Screen matrix | `$B800` | `$F800` |
| `$DD00` bank selection | `$81` | `$80` |

The matrix uses columns 4 through 34 and rows 0 through 23. Its code is
`8*columnWithinWindow + (row mod 8)`, so the visible window is **248×192
physical pixels**, or 124 multicolor pixels × 96 populated rows per field.
Other cells select blank glyph 255. Color RAM `$09` enables multicolor and
selects white for pair 3; background/pair 1/pair 2 are black/purple/blue.
Sprites are disabled.

The IRQ selects `$D018=$E8/$EA/$EC` for three successive eight-character-row
bands. The middle selections occur in the blank final scanline of each
band: raster 114/178 for scroll 3, or 115/179 for scroll 4. The full proof
observed those exact lines, at raw monitor cycles 9–15. The top selection
and bank write occur on raster 1, before the image.

`$D011` alternates low-seven-bit values `$1B/$1C` every PAL field. One field
places populated rows at physical Y=0,2,…,190 inside the window; the next
places them at Y=1,3,…,191. The high raster-compare bit also changes for the
bottom IRQ without changing those scroll bits. Both literal field images
are verified; the raster schedule continues while the renderer works.

The main loop renders only the hidden 6 KiB font buffer. A ready flag is set
after the final byte. Publication can occur only at the top of a scroll-3
field, so both fields of a pair show the same complete transform. The
subsequent scroll-4 field retains that bank. This supplies a concrete
two-field digital composition contract. An offline **digital weave** takes
the populated rows from each native field; it is an inspection artifact,
not a claim about analog blending or what a single captured field contains.

All ordinary PRG loading remains below I/O: `$0801–$7BE6`. Source planes are
at `$2000–$5FFF`, runtime coordinate tables and coefficient records at
`$6000–$6297`, and the sampler at `$7000–$7BE6`. C64 startup clears the two
font buffers and initializes both matrices after normal loading.

## Native evidence and actual cadence

The default verifier passed **354 consecutive PAL fields** and sixteen
complete publications, covering all sixteen transforms and the return to
transform 0. Its [receipt](build/verification/receipt.json) records the
command, states, clocks and program SHA-256
`0329fce733a70904446aba59165b78aa8a54d4c56d3f5f4bb1a8f125caeeac54`.

- Before startup, the ordinary loaded payload and all 16,384 prepared
  source-plane bytes match independent mathematical expectations.
- The initial live draw's **5,952 ordered physical source reads** match
  independently derived addresses, including 218 duplicate-page accesses.
  The initial transform exercises 2,218 fractional carries, and 2,154
  output bytes would change if the second plane were omitted.
- Every field's complete 6,144-byte visible font and both 1,024-byte
  matrices match an independent direct-coordinate model. Hidden buffers
  are also checked whenever their ready flag is observed; this happened
  on 26 fields. Actual ready stores precede publication stores.
- All **34 complete 384×272 native screenshots** match pixel for pixel,
  including both scroll fields, window edges and both charset seams.
  All seventeen digital two-field weaves also match independently expected
  pair pixels. There are no excluded seam pixels.
- Actual bank, charset and scroll writes establish the raster schedule;
  the front buffer stays complete while the other buffer is being drawn.

New texture geometry is published every **22 PAL fields**, approximately
**2.28 updates per second**. The scroll alternation and three-band scanout
continue every field, approximately **50.12 fields per second**. Completion
breakpoints have a few clocks of polling/IRQ-entry jitter; these are not
extra displayed fields. The initial draw with the display disabled took
373,305 native clocks. The runtime publication interval includes VIC/IRQ
costs and waiting for a complete two-field publication boundary.

This is a readable full-Q8 teaching implementation. It does not claim the
original runtime code generator, original motion arithmetic, music-driven
palette, half-draw timing or original EC temporal reconstruction. There are
no stored animation bitmaps. Physical hardware, analog/CRT reconstruction
and audio are outside the proof.

One actual native scroll-3 field:

![Native field](build/verification/publication-08-field-0.png)

The corresponding offline digital weave of its two verified fields:

![Digital weave](build/verification/publication-08-digital-weave.png)

The [inspection GIF](build/verification/texture-planes.gif) contains just
the first field pair of each publication, at 100 ms per captured field.
It omits repeated holding fields and does not represent runtime cadence.
