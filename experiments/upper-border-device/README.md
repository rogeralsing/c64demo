# Upper-border raster device

An original standalone counterpart of Nine's upper-border mechanisms:
generated raster cells, normal/invalid-mode ghostbyte graphics, one-time
sprite crunch and pointer-table changes on repeated pattern rows. The code,
rotating idle pattern and three-section sprite artwork are ours.

The owning [Device analysis](../../docs/research/nine-device.md),
[Nine overview](../../docs/research/nine.md) and Linus Åkesson's
[technical explanation](https://www.linusakesson.net/scene/nine/explanation.php)
describe the original. The author page is already archived at
`build/research/nine/author-explanation.html`; no released program or picture
bytes are incorporated here.

```sh
cd experiments/upper-border-device
sh build.sh
sh run.sh
python3 verify.py
```

The wrappers use the shared KickAssembler and VICE helpers. `run.sh` selects
**PAL 6569** explicitly with `-VICIImodel 6569`. The verifier uses the same
model, the existing native monitor/snapshot readers, Pillow and Colodore
palette. It starts and closes its own normal-speed emulator process.

## A real upper-border display

Startup opens the vertical border in an ordinary warmup field, then avoids
the bottom-border comparison so it stays open across frame wrap. The timed
device occupies rasters **26–46**, above the normal text display's raster-51
top edge. This is not the lower-border ghostbyte example moved in a picture.

The VIC bank is `$4000`. During idle graphics, ordinary mode fetches the
changing byte at `$7FFF`; ECM selects `$79FF`, which stays zero. The generated
cells switch `$D011` between normal `$1A` and invalid `$70`. The invalid mode
makes its pixels black while retaining the ECM-like idle-fetch addressing.
Timed `$D021` changes expose red, light-red and green background sections;
set ghost bits make black one-pixel details through the transparent sprite
symbols. The low nibbles of literal `$1A/$70` writes supply ordinary colors
10/0, not new palette entries.

After the upper pass, DEN is cleared before raster 48. The VIC remains in
idle state instead of starting normal character fetches. Border selection
is changed after raster 247 and before 251 each field, preserving the open
vertical border. The full-image capture point is raster 290, after every
visible row has been drawn; it does not include unpainted rows left over
from the warmup field.

## Runtime generated cells

C64 startup copies our 34-byte template into **21 cells plus RTS**, 715 bytes
at `$3000`. Every field rotates each applicable eight-bit pattern and patches
its generated immediate operand. This is runtime generation and patching of
the raster program, not a host-rendered animation.

Each full cell emits the following stores. Cycles are the native monitor's
zero-based checkpoint values, not a physical bus-phase calibration.

| Raw cycle | Target | Value |
| --- | --- | --- |
| 16 | `$D021` | `$02` |
| 23 | `$D011` | `$1A` |
| 30 | `$D021` | `$1A` |
| 34 | `$D021` | `$05` |
| 38 | `$D021` | `$70` |
| 42 | `$D011` | `$70` |
| 48 | `$7FFF`, or `$D018` on rows 2 and 17 | rotated pattern, or `$50/$60` |

All 21 first stores occur at the same cycle on rasters 26 through 46,
exactly **63 clocks apart**. Each pass has 147 stores: 84 background-color,
42 mode, 19 ghostbyte and two pointer-table selections. The deliberately
duplicated pattern rows 2/1 and 17/16 make those two skipped ghostbyte writes
redundant in every rotation.

Our fixed 21-full-cell pass differs from the release's 32-byte cells,
temporary closing-cell SAX/RTS patches and stop-row restoration. Those
original byte identities and restoration behaviors are outside this example.

## One-time crunch and three sprite sections

Four stationary sprites, members **0, 2, 4 and 5**, use Y=9. They are
multicolor, expanded horizontally, and in front of the idle graphics.
Their transparent symbols reveal the fine ghostbyte pattern; other symbols
draw black, blue or white. Their X coordinates are 96, 144, 208 and 256.

At raster 11/cycle 17, `$D017` becomes `$35`. The next write clears it at
raster 12/cycle 15. The actual Phi2 write lies at the VIC's crunch decision.
Native snapshots prove each selected sprite changes
`MC/MCBASE/expansion-flop` from **9/6/0 to 5/5/1**. This matches the hardware
counter equation:

```text
newMC = ($2A AND (MCBASE AND MC)) OR ($15 AND (MCBASE OR MC))
      = 5 for MCBASE=6, MC=9
```

The displayed byte starts are 0, 3 and 6 on rasters 10–12, then
`(5 + 3*(raster-13)) mod 64` on rasters 13–74. The counter wraps twice
before reaching 63 and ending DMA. This particular crunch produces **65 DMA
display rows**; it is not ordinary Y-position multiplexing or precisely
63 newly authored rows. No sprite Y register is rewritten during a field.
DMA is disabled after raster 80 to prevent another Y=9 match at raster 265,
then enabled before Y=9 in the next field.

Three prepared pointer tables at `$53F8/$57F8/$5BF8`, selected by
`$D018=$40/$50/$60`, refer to our three 64-byte sections per sprite at
`$6000–$62FF`. Pointer changes happen after current sprite fetches and before
the next row's fetches, so the new sections first appear on rasters 29 and
44. The pixel oracle wraps **each fetched byte** modulo 64; the unaligned
three-byte rows really use byte 63 and can cross back to byte 0.

Section artwork intentionally repeats where its 64-byte capacity requires
it. We do not implement the original moving vertical seams, copy-chunk
tables, wizard picture, orbiting digits or freely moving protected DMA
sprites.

## Native proof and rate

The [receipt](build/verification/receipt.json) records nine complete PAL
fields: all eight pattern rotations and wrap, **1,323 exact cell stores**,
all 715 generated bytes per field, prepared sprite bytes and pointers,
the before/after crunch snapshots, and final idle/border/DMA-end state.

Every pixel of each **384×272 native screenshot** matches an independent
coordinate-based compositor. It models normal versus ECM idle fetches,
the 6569's mode and color pipeline edges, sprite pair expansion, actual
pointer-table timing, both counter wraps and sprite priority. It neither
executes C64 instructions nor copies the emulator's rendered image into
its expected output. The receipt pins the inspected VICE 3.10 source files
that define these digital timing rules. No seam pixels are excluded.

Under the observed schedule, omitting each mechanism from the compositor
changes these many compared pixels over the nine fields:

| Omitted mechanism | Changed pixels |
| --- | ---: |
| Ghostbyte bits | 4,541 |
| Sprites | 31,888 |
| Crunch | 37,316 |
| Pointer-table changes | 19,368 |

These are isolated compositor controls, not claims that disabling sprite
DMA in a running machine would preserve its CPU timing.

Successive field origins are exactly **19,656 PAL clocks apart**, one
update per field, approximately **50.12 updates/s**. The inspection GIF
uses 100 ms per field and is deliberately slowed down.

Verified program SHA-256:
`faad225568b0f2bab34501100a6c536ef9830f4014d0b777cdd085d6513f37d5`.
The ordinary PRG loads `$0801–$62FF`; no load writes through I/O.

![Actual complete native field](build/verification/field-01.png)

The same native field's upper 64 lines, cropped and enlarged three times
with nearest-neighbor sampling for inspection:

![Native upper detail](build/verification/upper-detail.png)

[Nine-field inspection GIF](build/verification/upper-border-device.gif)

## Hardware scope

This program has one fixed alignment for the explicit PAL 6569 model.
Nine's author describes three generated families selected by detector result
and horizontal phase. Our example has no such detector and does not claim
those three original outcomes, 8565 grey-dot hiding or other VIC revisions.
The original research receipts separately distinguish the `$3000/$3400`
native families from the source-proved `$3800` family.

The proof concerns literal digital VICE output and observed checkpoint
clocks. Physical C64 hardware, analog/CRT appearance, NTSC, audio and the
original production's complete composition remain outside it.
