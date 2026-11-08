# Two complementary bitmap layers

This original PAL C64 example independently moves two copies of a concentric
ring mask. The layers occupy opposite bits of each multicolor pixel. Runtime
OR composition chooses black background, cyan layer A, purple layer B, or
white overlap. The overlap color is an explicit palette choice.

The displayed window contains **128×96 logical samples**, doubled horizontally
by multicolor bitmap mode and doubled vertically by two bitmap stores. It
occupies **256×192 physical pixels**, centered horizontally in a black
320×200 bitmap. Complete bitmap buffers alternate between `$2000` and `$A000`.

## Build, run, verify

```sh
rtk proxy sh build.sh
rtk proxy sh run.sh
rtk proxy python3 verify.py --frames 8
```

The build uses the shared KickAssembler wrapper and produces
`build/example.prg`. Playback uses PAL VICE. Verification uses the existing
Python/Pillow and VICE tools; it starts and closes its own emulator.

## Prepared data and runtime work

Assembly creates an original **64×64 one-bit ring mask** and four horizontal
sampling phases for each layer. Each phase stores four mask samples in one
multicolor byte: A uses only `$55` bit positions, B only `$AA`. The eight
prepared planes occupy 8,192 bytes. Row/column address tables are arithmetic
data; no animation frames are stored.

For every new image, the C64 selects source rows and horizontal phases from
four live offsets, samples both masks, combines each pair with OR, and writes
all 3,072 resulting bytes twice vertically. A advances by `(1,2)` source pixels;
B advances by `(-1,1)`, wrapping at 64. Thus both layers move independently.
All rendering runs into the hidden bitmap before a top-border bank switch.
The program makes no 50 fps claim.

The verifier derives ring membership using integer distances, independently
of the assembler's floating-point expression. It checks all 8,192 prepared
bytes, every byte of each complete 8,000-byte displayed bitmap, both screen
matrices, Color RAM, offset progression, buffer switching, and native VIC
screenshots after complete scanout. Each run retains RAM dumps, screenshots,
an animation and `verification.json` under `build/verification/<UTC timestamp>/`.

The 8 November 2026 native run checked eight distinct images across both
buffers: **64,000 bitmap bytes and 512,000 screenshot pixels**, with no
differences. All screenshots matched at display origin `(32,35)`. Consecutive
completed images were 235,868–235,875 PAL clocks apart, about twelve video
fields per update. This deliberately simple sampler keeps the last complete
image visible while the next bitmap is rendered.

The retained [receipt](build/verification/20261108T064920.507950Z/verification.json)
and [native animation](build/verification/20261108T064920.507950Z/animation.gif)
record that bounded run.

## Relation to the documented effect

[Second Reality DB](../../docs/research/second-reality-db.md) uses two prepared
one-bit layers in complementary multicolor positions, shifted independently
and combined by OR into vertically doubled bitmap rows. This example teaches
that representation and composition contract with new code and a new mask.
It does not reuse the release's code, artwork, motion tables, expanded layouts,
loader, or palette introduction, and it is not a clone of the complete part.
