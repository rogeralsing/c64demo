# Layered column DYPP and horizontal reveal

An original standalone C64 technique counterpart to the counter-scrolling
layered DYPP and horizontal picture reveal mentioned by Trident for **The Demo
Coder**. A blue text strip and cyan night-city/planet strip scroll in opposite
directions and follow independent column waves. Their overlap becomes white.
The picture opens from left to right, holds, closes from right to left, and
holds dark while the text continues moving.

Build and run from the repository root:

```sh
rtk sh experiments/layered-dypp-reveal/build.sh
rtk sh experiments/layered-dypp-reveal/run.sh
```

Build requires the repository's installed Java/KickAssembler setup and Python
3. Running requires PAL VICE (`x64sc`, or the `VICE` environment variable).
The run wrapper uses normal speed and sound. No downloads, sibling repository,
released demo bytes or prepared animation frames are inputs.

## Source evidence and scope

The [owning survey](../../docs/research/frontier-followup.md#another-recent-primary-lead-the-demo-coder--fairlight-2024)
records Trident's 25 November 2024 description of counter-scrolling in the
layered DYPP part and horizontal movement exposing source pixels in MEGA.
[His release comment](https://csdb.dk/release/index.php?id=247776) is the primary
attribution. That establishes a concrete visual lead, not its exact implementation.

The [asset investigation](../../docs/research/demo-coder-assets.md) identifies
stream 46's stored picture as The Sarge's **Rubicon** loading art, associated
with the author's separate FLD-with-stretch description. It is not evidence that
this stream is the MEGA/Eyes picture. The [raster investigation](../../docs/research/demo-coder-raster.md)
maps stream 46's bank/mode/row-counter behavior; it does not recover the layered
DYPP/MEGA scene's full mechanism. This example therefore demonstrates our own
software column displacement and selector-plane reveal, with original art and
explicitly chosen dimensions. It does not reproduce the original register
schedule, artwork, scene identity or full-row stretcher, or claim a historical
first or original frame rate.

## Prepared source, live C64 work

`prepare.py` produces two ordinary one-bit source strips: 256×24 text pixels
from the repository's original [shared 5×7 font](../lib/font5x7.py), and a
256×48 mathematical skyline with windows, stars, a ringed planet and floor.
The original city equations are in this folder. Preparation also encodes 64
overlapping eight-pixel windows per source row, four fine-scroll byte-expansion
tables per selector plane, and two reusable signed sine profiles. These are
source data and reusable lookup functions. There are no per-pose images,
displacement lists or precomposed frames.

Each native update performs these operations:

1. Choose the hidden 2 KiB font and clear it. The front font stays visible.
2. Render all 16 text byte columns. Each column addresses its own sine Y offset,
   reads the current source window and expands its selected four pixels into
   multicolor selector 1.
3. Render the enabled picture columns with a separate source position and wave,
   OR-ing selector 2 into the same hidden font. Text bits survive; pixels from
   both layers become selector 3.
4. Publish the completed font through `$D018` at the next top border, then allow
   a full scanout before advancing the scroll, wave and reveal state.

The two scroll positions advance by −2 and +1 source pixels per update, while
the wave phases advance by +5 and +3. Adjacent output columns use phase steps
13 and 11. These independent column displacements are the actual DYPP here;
there is no global affine image transform. A column is four logical pixels
wide. The text Y origin is `34 + round(18 sin(phase))`; the picture uses
`42 + round(12 sin(phase))`. Both fit wholly inside the canvas.

The live reveal consists of 16 mask bytes and a four-state controller. Opening
sets one new byte to `$FF` per update, the first hold lasts 16 updates, closing
clears one byte per update, and the dark hold lasts 16 updates. A disabled
picture column is skipped by the renderer; the underlying text continues.
Each complete reveal choreography lasts 64 updates. Source scroll, waves and
reveal state all return together after 256 updates.

The display uses a 64×128 logical multicolor canvas, **128×128 physical pixels**,
at character column 12, row 4. One immutable matrix at `$0400` maps 256 character
codes in column-major order. Two fonts at `$2000/$2800` alternate; Color RAM is
static. Character 0's first eight rows remain blank under the bounded Y ranges,
so it also supplies the surrounding black area. Selectors map to black, light
blue, cyan and white. This deliberately bounded scene redraws a hidden font;
it does not claim the original display resolution or raster technique.

The example imports [the existing publication/IRQ module](../prepared-fragments/display.asm)
unchanged and applies its own palette, immutable matrix and initial fonts.
Build uses [the shared assembler helper](../build-one.sh). All generated inputs,
programs and receipts are beneath ignored `build/`; their producers are tracked.

## Native proof and measured cadence

After building, run:

```sh
rtk python3 experiments/layered-dypp-reveal/verify.py
```

Verification additionally requires Pillow and the repository's tracked Colodore
palette and root monitor helper. It launches and closes its own PAL 8565 VICE
instance, invalidates its previous primary success receipt before fallible
setup, and does not write emulated memory or alter the PC.

The completed bounded run verifies **257 consecutive publications**, all 256
states plus the complete wrap. Its oracle uses ordinary source bitmap pixels,
independent coordinate math and trigonometry, without using the producer's
window encoding, expansion tables or native compositor to generate expectations.
It checks both full fonts and the screen matrix at five natural boundaries per
update: before rendering, hidden clear, text pass, picture pass and completed
scanout. Intermediate native text bytes must equal the text-only reference;
the picture contribution must equal the composite XOR text, and the text plane
must remain intact. It checks every live source/wave/reveal state and all 16
offsets for both layers, including hidden picture columns.

All **26,843,136 pixels** of 257 complete 384×272 VICE captures match exactly.
The run observes all four reveal states, 128 changed mask bytes across four
complete choreographies, 162–360 text pixels, 0–1,388 picture pixels and up to
93 overlap pixels per update. The final native screenshot equals the first.
Both fonts alternate coherently. All 257 publication stores occur on raster 0
at observer cycles 12–18. `$D018` readback ignores its unused bit 0.

Actual cadence is **3–5 PAL fields per publication**, with counts 68, 104 and 84
over the 256 intervals: mean **4.0625 fields**, approximately **12.31 updates/s**
at nominal 50 Hz. Rendering takes **41,244–66,691 clocks**, including the hidden
clear and both layer passes; the measured clear takes 23,730–23,901 clocks.
The visible picture width changes the amount of work. No 50 Hz deadline or
original production cadence is claimed. Monitor raster/cycle values are
observer coordinates, not calibrated physical bus phases; this proof covers
the stated PAL VICE model rather than physical hardware.

Results are [the receipt](build/verification/proof.json), individual native PNGs
such as [fully revealed phase 16](build/verification/publication-017-phase-016.png),
and [the animation](build/verification/layered-dypp-reveal.gif). GIF durations
follow the measured PAL-field intervals, although viewer timing is approximate.
The program is 22,529 bytes; SHA-256:
`3052c1b96280a17172b60fdcc2cafccdcb1f5892b23df975f0632416465aae9b`.
