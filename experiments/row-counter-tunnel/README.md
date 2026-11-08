# Cached-row tunnel

This original PAL C64 example displays an animated 320 × 192 checker tunnel
using **one fetched row of forty character/color entries**. Twenty-three late
`$D011` conditions wrap the VIC-II row counter, retaining those cached entries
across twenty-four eight-row bands. Charset changes and CIA2 direction-register
bank selection reinterpret the same codes through different prepared glyphs.

It uses the actual cached-row mechanism documented for *Quondam Tunneling*,
not a bitmap redraw that merely resembles it. No release bytes, original
artwork, soundtrack or sprite overlay is included.

## Build and run

```sh
sh build.sh
sh run.sh
```

Requires the project's existing KickAssembler and PAL VICE installation.
Output is `build/example.prg`. No downloaded asset or research cache is needed.

The picture has four prepared texture phases, selected by changing forty screen
codes every four PAL fields. The C64 performs raster timing and bank selection;
it does not calculate arbitrary live 3D geometry. The final eight rows of the
ordinary 320 × 200 screen are black.

## Cached-row mechanism

The first ordinary bad line fetches codes 64..103, 104..143, 144..183 or
184..223, depending on the animation phase. Later screen rows deliberately
contain different data. Simply reading successive matrix rows cannot produce
the displayed repetition.

On the final line of each glyph row, the kernel asserts a matching YSCROLL
condition after the character-matrix fetch window. RC wraps from seven to zero
and VCBASE advances, while the cached forty codes and colors remain unchanged.
A mid-band `$D011` change prevents the next ordinary bad line from replacing
that cache. A double raster IRQ stabilizes the first window; fixed 504-cycle
sections carry the subsequent eight-line bands without sprite DMA.

Each six-band group uses a different 16 KB VIC bank. The CIA2 output latch's
low bits remain zero; `$DD02=$3C..$3F` changes those pins between inputs and
zero-driving outputs. This selects all four banks through the direction
register. `$D018` retains screen offset `$3000` and chooses one of six charset
offsets within that bank. Color RAM remains nine, enabling multicolor text
with white as selector three; the other selectors use black, blue and cyan.

## Prepared data and loading

The source generates its own inverse-distance/checker texture as 24 glyph sets,
each containing four phases of forty eight-byte characters: 30,720 bytes.
These are prepared glyph data, not a runtime raycaster or a recovered asset
generator from Quondam.

The PRG loads only through `$97FF`, avoiding writes to the I/O range during a
normal LOAD. Startup relocates the packed glyphs into all four VIC banks,
including RAM under KERNAL ROM. Backward copies handle destinations above their
packed source; the remaining lower destinations copy forward. The raster
display starts after this preparation is complete.

## Native verification

```sh
sh build.sh
python3 verify.py
```

The verifier needs Python 3 with Pillow and VICE 3.10 C64SC. It reuses the
repository's tracked monitor helper and audited snapshot-schema decoder.
Original Quondam files and ignored research artifacts are not inputs.
Set `VICE` to override the emulator executable.

Verified on 8 November 2026 using PAL 8565 model 1. Six completed captures cover
all four texture phases and two comparable phase-zero fields. An independent
spatial formula matched **384,000 pixels with zero mismatches**, including
the eight black bottom rows. Every capture also matched all 30,720 relocated
glyph bytes, without obtaining expected glyphs from the assembled data.

The first mechanism witness records these zero-based instruction boundaries:

| Stop | Raster / cycle | RC | VCBASE | Bad-line condition |
| --- | --- | --- | --- | --- |
| Before late instruction | 58 / 49 | 7 | 0 | Clear |
| After its `$D011` store | 58 / 55 | 7 | 0 | Asserted |
| After selecting next band | 59 / 4 | 0 | 40 | Clear |

All 23 successive next-band snapshots retain the same cached forty codes and
colors, with RC zero and display active. VCBASE advances through 40..920 while
native CIA2 state confirms the expected bank changes. The before snapshot's
complete 64 KB physical RAM agrees with the separately saved RAM dump.

Sixteen later first-window observations remain at raster 58/cycle 49, exactly
19,656 clocks apart. Screenshots with and without the full sequence of band
snapshots match at the same texture phase. Complete snapshots, RAM, screenshots,
the command and transcript are retained under ignored `build/native/` alongside
`proof.json`. The owned VICE process exited normally.

Instruction-boundary timestamps are not independently recorded bus-write
timestamps. The serialized VIC state proves the sampled row-counter/cache
behavior; the pixel oracle proves the six completed sampled images. Matching
screenshots do not assert complete CIA or whole-machine snapshot identity.
There are no PC changes, RAM patches, snapshot restores or payload replacements.
Physical VIC-II variants and NTSC are not covered.

## Relationship to Quondam

See [the original-program map](../../docs/research/quondam.md) and
[the cached-row investigation](../../docs/research/quondam-raster.md).
Quondam combines its own glyph assets, motion, palette switching, horizontal
scrolling and sprite overlays. This example retains the late row-counter wrap,
cached-code reuse and direction-register bank selection, using a smaller
four-phase original texture and a fixed palette to expose those mechanisms.
