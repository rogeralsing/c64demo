# Joystick-controlled bitmap Kefrens-style ribbons

Six shaded ribbons overlap and move through a **256×128 physical-pixel**
viewport inside a 320×200 multicolor bitmap. The default view bends vertical
ribbons across the scanlines. Fire flips to horizontal ribbons, sampled in
eight-pixel-wide columns. Later ribbons paint over earlier ribbons.

This is a new implementation and composition. It does not reconstruct
Aloft's unresolved bitmap renderer or establish that its flipped and bitmap
effects share an implementation.

## Build, run, controls

```sh
rtk proxy sh build.sh
rtk proxy sh run.sh
rtk proxy python3 verify.py
```

Output is `build/example.prg`. Use a joystick in **port 2**, or configure the
VICE port-2 keyboard joystick. `sh run.sh -joydev2 1` selects VICE's numpad
joystick mapping.

- **Up/down:** increase/decrease animation speed, clamped to 1–4 phase steps.
- **Left/right:** decrease/increase bend, clamped to 1–4 phase steps per sample.
- **Fire:** switch orientation once per press; holding fire does not retrigger.

The C64 samples CIA1 port A once per completed image. Held directions repeat
at that cadence. Neutral input leaves the automatic animation running.

## Rendering contract

Two 256-entry sine tables supply reusable start positions. Small AND/OR masks
contain four horizontal sub-byte phases of one 16-sample shaded bar; horizontal
mode uses an eight-row shade profile. These are reusable primitives, not
prepared animation frames or complete image strips.

The C64 clears a temporary line buffer, plots six bars in a fixed paint order,
then writes the composed line/column into the hidden bitmap. Vertical mode
uses one logical scanline per two physical rows. Horizontal mode assigns one
shade per eight-pixel column and also doubles its logical rows. Both modes
overwrite the entire viewport; the surrounding bitmap remains black.

Complete bitmap buffers alternate between `$2000` and `$A000` at the top
border. Screen attributes choose cyan, purple and white shading over black.
No sprites or raster color changes draw the ribbons. Phase advancement,
joystick handling, mask composition and all bitmap stores execute on the C64.

## Native verification

`verify.py` starts an owned PAL VICE instance with its official Joyport I/O
simulation device attached to port 2. It explicitly injects neutral, all four
directions, diagonal input, fire presses, held fire and releases through the
[binary monitor Joyport-set API](https://vice-emu.sourceforge.io/vice_13.html).
It does not write program RAM or CPU registers to fake interaction.

The verifier checks the actual CIA input pins and consumed input byte,
independently predicts speed/bend limits and fire edges, composes each bitmap
from sine-positioned shaded intervals, and compares all 8,000 displayed bitmap
bytes plus every pixel of a complete native 320×200 screenshot. It also checks
both bitmap banks, immutable attributes, Color RAM and all 512 sine bytes.
Actual clock intervals are reported separately for each orientation.

Each run retains input packets, state/cadence evidence, RAM dumps, native
screenshots, independent expected images, `animation.gif` and
`verification.json` under `build/verification/<UTC timestamp>/`.

The 8 November 2026 run passed **41 distinct native images**, including all
four speed and bend settings, both orientations, directional saturation,
diagonals, held fire and fire releases. All **328,000 bitmap bytes and
2,624,000 screenshot pixels** matched. Every image contained overlapping
bars and all three foreground shades.

Vertical mode took **196,555–196,565 PAL clocks**, ten video fields per update
(5 updates/s). Horizontal mode took **235,866–235,876 clocks**, twelve fields
per update (about 4.17 updates/s). This straightforward sampler favors complete
images over partial in-place updates; it does not claim the original effect's
frame rate.

The retained [receipt](build/verification/20261108T071351.349503Z/verification.json)
and [native animation](build/verification/20261108T071351.349503Z/animation.gif)
record that bounded run and its explicitly synthetic input sequence.

## Source boundary

The [owning local note](../../docs/research/february-2026.md) records Sparta's
creator statement that a joystick controls the movement of Aloft side 2's
flipped Kefrens bars. It explicitly leaves the original drawing algorithm
unresolved. The bitmap/every-second-line comment is a peer observation, not
an implementation-author explanation. This example's buffering, masks,
orientation mapping and control assignments are our own design choices.
