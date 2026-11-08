# Ghostbyte shine-through

This original PAL C64 teaching example combines idle graphics in the opened
lower border with eight horizontally expanded multicolor sprites. Transparent
sprite symbols expose one-pixel black details from the repeated idle byte.
Other symbols paint solid black or the same light gray as the background.
The sprite symbols themselves remain four physical pixels wide.

The program automatically cycles through three views every 128 PAL frames:

- **A: combined.** The sprite masks selectively expose the moving idle pattern.
- **B: idle only.** Sprites are disabled, revealing the repeated eight-bit pattern.
- **C: mask only.** The idle byte is zero, revealing the coarse sprite artwork.

The repeated byte moves two narrow black lines within each eight-pixel period.
All sprites remain stationary. This isolates composition from sprite motion.
The upper border also shows idle graphics when the vertical border remains open;
the sprite composition is confined to the lower border.

## Build and run

```sh
sh build.sh
sh run.sh
```

Requires the project's existing KickAssembler and PAL VICE installation. Output
is `build/example.prg`; no downloaded source, research cache or image is needed.
The program initializes the VIC bank, screen, text attributes, sprite data,
priority, multicolor palette, expansion and interrupt state on startup.

## Source and scope

The mechanism follows Trident / Fairlight's January 2023 article,
[Multicolor Ghostbyte Shine-through](https://github.com/trident64/c64/blob/80d1027742815e55cda13a80cb4826744dd75c83/unexpanded-border-scroll/README.md).
The project's research notes distinguish that article from its two small
teaching programs and the complete released scroller. This example contains
new code and new geometric sprite masks; it includes no third-party font,
artwork or source code.

This is a mechanism demonstration, not a clone of *Orbit Untold*, *The Ghost*
or *Nine*. It does not implement a scrolling font, arbitrary hires border
graphics, side-border opening or raster-line-specific ghostbyte font data.
The shared eight-pixel idle pattern constrains the detail in all transparent
windows on a raster line.

## Native verification

```sh
sh build.sh
python3 verify.py
```

The verifier needs Python 3 with Pillow and the existing `x64sc` executable.
Set `VICE` to select another VICE path. It starts and closes its own emulator;
no research cache or previous native receipts are needed.

Verified in PAL VICE on 8 November 2026. The program reached all three views
naturally at frame counters 64, 192 and 320. At those stops, combined and idle
views contained `$81` at `$3FFF`; the mask-only view contained zero.

An independent compositor matched every pixel in the visible 320 × 21 sprite
area in all three screenshots: **20,160 comparisons, zero mismatches**.
The combined view contained **906 black pixels exposed through transparent
symbols** that were absent from the mask-only view. This directly checks the
idle-graphics contribution rather than inferring it from register settings.

Screenshots, complete RAM dumps, monitor transcript, capture metadata and the
pixel comparison are retained under ignored `build/native/`. The owned VICE
process exited after capture. These three sampled fields do not establish
exhaustive DMA timing or compatibility with physical VIC-II revisions.
