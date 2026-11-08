# NUFLI spectral interference weave

This example generates original 320 × 200 mathematical artwork directly in
NUFLI's bitmap, attribute and sprite planes. It combines curved interference
contours with six expanded hires underlays, both left-edge repair layers and
raster color changes. The rightmost eight pixels deliberately use bitmap only.

## Build and run

```sh
sh build.sh
sh run.sh
```

The build needs Node.js and no packages. The runner needs PAL VICE. Set `NODE`
or `VICE` to override the executable paths. Output is `build/example.prg`, a
BASIC-autostart program, and `build/example.nuf`, a standard uncompressed NUFLI
file loading at `$2000` and entered with `SYS 12288`.

`build.cjs` is this example's source entry instead of `main.asm`: its job is
picture generation and native format serialization. No sibling checkout,
downloaded artwork or research cache is needed.

## What the C64 does

The image is static. Node prepares the mathematical picture's hardware planes
and register commands; it does not generate an animation. The unchanged Mufflon
player initializes the C64, expands picture-specific raster code and displays
the image with bitmap/sprite composition and carefully timed register changes.
There is no runtime texture synthesis, moving geometry or new player claim.

The generated plan explicitly exercises:

- 8,000 bitmap bytes and 4,000 two-scanline attribute bytes.
- Six expanded hires underlays across x=24..311.
- A hires and a multicolor sprite repairing x=0..23.
- Six register slots per two scanlines, including eight required sprite-Y
  updates in the legal split window and changes to every left-edge color.

The build independently decodes the serialized NUF using file addresses and
screen-page sprite pointers. It also removes each layer in turn and records
how many pixels change in `build/artwork.json`. Those counterfactuals demonstrate
actual visible layer contributions rather than counting nonzero input bytes.

## Reuse and attribution

`nufli-data.js` contains unchanged player bytes and address tables extracted
from **Mufflon v2.0, SVN revision 1440**. Original authors are
Bitbreaker/Metalvotze (Tobias Bindhammer), Crossbow/Crest (Roland Tögel), and
DeeKay/Crest (Daniel Kottmair), copyright 2008–2014 Crest & Metalvotze.

`nufli-export.js` is the C64 GFX Convert project's serializer port.
`decode-nufli.cjs` is its independent file-address decoder, following the
documented RECOIL layout; it does not use the serializer's packing tables.
These files are copied byte-for-byte with all original comments intact.
`SOURCE.json` pins their origins and SHA-256 hashes. The complete original
permission notice is preserved in `MUFFLON-LICENSE.txt`.

The artwork generator and integration are new project code. The viewer and
format are credited to their authors. The vendored files are unmodified;
the build rejects a hash mismatch rather than silently rewriting them.

## Native verification

```sh
sh build.sh
python3 verify.py
```

Verification needs Python 3 with Pillow, Node.js and the existing PAL VICE
installation. It verifies that the PRG embeds the exact NUF payload, re-decodes
that NUF independently, then compares three native 320 × 200 captures with the
decoded color indices using the external Colodore palette. The verifier adapts
this project's existing NUFLI capture implementation; its source identity and
changes are recorded in `SOURCE.json`.

`build/native/verification.json`, the monitor transcript, display RAM and three
screenshots retain the result. The verifier closes only its own emulator.
The normal `run.sh` leaves sound available; the verifier uses a dummy sound
device for silent capture. PAL timing is required; NTSC is not covered.

Verified in PAL VICE at normal speed with warp disabled on 8 November 2026.
All three captures matched all 64,000 pixels, for **192,000 comparisons with
zero mismatches**. Captures were byte-identical while native clocks advanced.
The owned emulator was confirmed closed after capture.

The generated image uses fifteen hardware palette colors. Independently decoded
counterfactual files changed 19,142 pixels when bitmap ink was removed, 17,781
without the six main underlays, 549 without the left hires layer, 2,053 without
the left multicolor layer, and 6,409 when raster color changes were held static.
These comparisons are layer-contribution evidence, not separate native runs.

The PRG is 29,185 bytes; the NUF is 23,042 bytes. This proves the generated
static picture in three sampled PAL fields. Physical hardware, NTSC, arbitrary
source fitting quality and animation are outside this example's verification.
