# MUIFLI chromatic orbital lattice

This original mathematical picture is stored as two genuine MUIFLI fields.
An unchanged, attributed **Mufflon v1.0** player alternates their bitmap,
attribute and sprite domains on the C64. This is a static high-color picture;
there is no runtime image synthesis or animation-pose calculation.

MUIFLI is separate from the existing [NUFLI example](../nufli/README.md).
The owning [format notes](../../docs/research/frontier-demos.md) distinguish
its interlaced color choices from physical VIC palette entries. The
[NUFLI source notes](../../docs/research/nufli.md) identify the source package,
but their static one-field proof is not used as evidence for these two fields.

```sh
cd experiments/muifli
sh build.sh
sh run.sh
python3 verify.py
```

`build.py` is the source entry instead of `main.asm`, as in the existing
NUFLI example. It prepares our artwork and serializes the native MUI format.
Build needs only Python's standard library. Run needs PAL VICE. Verification
also uses the project's existing Pillow, palette, monitor and snapshot readers.
No sibling checkout, ignored research cache, downloaded picture, new package
or expansion hardware is required to build or run it.

Outputs are `build/example.prg`, a BASIC `RUN` launcher, and
`build/example.mui`, an ordinary uncompressed MUI file loading at `$2100`
and entered with `SYS 12288`. The archive runner should distribute the PRG;
the MUI file is picture data with its viewer, not a BASIC-autostart artifact.

## Native format and physical colors

Each field has an 8,000-byte hires bitmap, 4,000 two-line attribute bytes,
six expanded hires underlays and six 101-entry sprite-color tables. Bitmap
foreground wins over the underlays. The underlay color is shared over 48
physical pixels and staggered across odd/even line pairs; it is not a free
third color independently selectable for every pixel.

This picture uses six normal underlays over logical x=24–311. The first
24 pixels exercise MUIFLI's limited light-gray/one-color FLI-bug area: our
bitmap supplies light gray and the blanking sprite supplies black. These
are not NUFLI's two independently colored repair sprites. The final eight
pixels deliberately remain black.

The central mathematical contours and lattice are our artwork. The two
fields have separate palettes and data. A bottom checker panel reverses its
bitmap/paper representation between fields while preserving its physical
black/white pixels; it exercises distinct bitmap planes without adding
flicker to that panel. Underlay rows are prepared with the hardware's shared
row cadence. Seven sprite-Y handoffs occupy redundant first-slot color
updates in the legal split window.

Our 55 chosen field-color pairs are checked against the original Mufflon
pair table. The author's description of a selected **79 blended-color**
subset concerns conversion/display choices, not additional VIC colors.
In our actual picture, **each native field uses only the 16 physical C64
colors**. The fields differ at 32,449 logical pixel positions. Their digital
RGB mean contains 55 distinct values; that arithmetic preview does not prove
an analog display's perceived colors, flicker or effective palette.

## Two memory domains and legal loading

The normal PRG load occupies only `$0801–$CCFF`, below I/O. The MUI payload
itself is `$AC00` bytes. Its second picture tail is packed into the loadable
region and restored by the original player from `$7700–$A0FF` to
`$CD00–$F6FF`. CPU port `$34` makes this a **RAM copy beneath I/O and ROM**.
The program does not load picture bytes into active I/O registers.

The two picture domains are 32 KiB apart. Their upper and lower bitmap
pieces occupy `$6000/$3400` and `$E000/$B400`; their screen and sprite
regions are interleaved around those pieces. The viewer generates separate
raster programs at `$1000` and `$9000` and alternates its IRQ paths at
`$3200` and `$B200`.

In each field, the initial bank write at raster 42 selects `$4000` or
`$C000`. The generated midpoint write at raster 175 selects `$0000` or
`$8000`. Both complete picture fields therefore use two VIC banks. This
is not one NUFLI picture relabeled as two captures.

The unchanged player begins bitmap row 0 at raster 48 with horizontal
scroll 1. Only the first cold field waits for the normal top-border
comparison at raster 51, hiding its first three logical rows. The tail
leaves the vertical border open across subsequent wraps, so the steady
fields show all 200 rows. The side border hides the final logical column,
which is intentionally black here. The native oracle predicts these edges;
it does not exclude their pixels from comparison.

## Viewer attribution and license

The unchanged [vendor/mufflon.h](vendor/mufflon.h) is copied byte for byte
from the source package
[Mufflon1.0-source+GUI+Bonus.zip](https://csdb.dk/getinternalfile.php/180585/Mufflon1.0-source+GUI+Bonus.zip).
All its comments are preserved. The full original copyright and permission
notice is in [MUFFLON-LICENSE.txt](MUFFLON-LICENSE.txt).

Original credits: Bitbreaker/Metalvotze, Tobias Bindhammer, for the converter;
Crossbow/Crest, Roland Tögel, for NUFLI/MUIFLI formats and C64 players/editors;
and DeeKay/Crest, Daniel Kottmair, for concepts, conversion strategy and
documentation. Our Python serializer is a new narrow port of the MUI layout;
our artwork, independent decoder and integration are new project code.
We do not claim authorship of the original player or a new player implementation.

[SOURCE.json](SOURCE.json) pins the archive, header, notice and both player
arrays. The build rejects a changed vendored source identity. The loaded
PRG's complete two 768-byte player blocks are also checked before their
first instruction during native verification.

## Independent native proof

The default six-field run checks A/B/A/B/A/B in ordinary PAL VICE, with warp
disabled. [The receipt](build/verification/receipt.json) records:

- **626,688 exact native pixel comparisons:** every pixel of all six
  384×272 screenshots, including borders, all image rows, sprite seams,
  bitmap-bank seams, the limited left area and the cold-start transition.
- Both fields' **16,000 bitmap bytes** and **8,000 attribute bytes** on each
  capture, and all **10,752 relocated tail bytes**. These domains overlap;
  their counts are not a claim of that many distinct RAM bytes.
- An independent file-address decoder that derives screen pages and sprite
  addresses from physical pointers and counter wraps. It does not import
  the serializer's packing tables or use a rendered image as its expectation.
- Actual alternating IRQ endpoints and bank writes, VIC sprite/mode geometry,
  and the open vertical-border state from native snapshots.
- **Zero I/O-mapped SID writes.** All 1,024 observed stores to
  `$D400–$D7FF` occur during the RAM relocation with I/O banked out. CPU-port
  writes are traced to distinguish those from sound-register writes.
- Explicit ownership and closure of the verifier's VICE process.

Independently decoding a picture with its bitmap removed changes 20,778 /
20,847 pixels in fields A/B. Removing the six main underlays changes
15,062 / 14,857. These are decoder-layer controls, not separate native
disable-DMA runs or a claim that DMA timing would remain unchanged.

The field interval is exactly **19,656 PAL clocks**, about **50.12 fields/s**.
One complete A/B pair repeats at about **25.06 pairs/s**. These are static
image field/pair rates, not a geometry-rendering frame rate.

Verified program SHA-256:
`6469dbe7ae3a4a3d48ff1450d813a8e330c7a414fa7d6e313780096f87601d7a`.

One steady native field A:

![Native field A](build/verification/native-02-field-0.png)

The corresponding native field B:

![Native field B](build/verification/native-01-field-1.png)

An **offline RGB mean** of the two independently decoded physical fields:

![Digital mean preview](build/verification/digital-mean.png)

The [digital column weave](build/verification/digital-column-weave.png)
chooses alternating columns from A/B. The
[inspection GIF](build/verification/muifli-fields.gif) shows literal captured
fields at 200 ms each, deliberately slower than the running player. Neither
artifact is a new C64 field, extra hardware colors or a CRT simulation.

This proves our generated static image and the specified PAL viewer. General
source fitting, all possible MUI files, NTSC, analog appearance, physical C64
hardware, audio and an exhaustive blended-color palette remain outside it.
