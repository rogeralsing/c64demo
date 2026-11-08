# All-border sprite upscroll

An original visual counterpart of The Hat's documented final all-border
upscroller. Four short text rows move upward by one physical pixel per PAL
field, through the top, bottom, left and right borders.

The Hat's actual implementation is still unresolved in
[the owning research note](../../docs/research/february-2026.md).
Its archived author/peer statements, public source routes and teardown lead
were read before choosing this mechanism. They do not establish that The Hat
uses the technique below. No original demo executable, font or artwork was
run or repackaged.

```sh
./experiments/all-border-upscroll/build.sh
./experiments/all-border-upscroll/run.sh
python3 experiments/all-border-upscroll/verify.py
```

Run from the repository root. These use the shared Kick Assembler/VICE helpers
and existing Python/Pillow tools. The output is `build/example.prg`.
The target is PAL; physical hardware has not been tested.

## Genuine sprite pixels and border latches

All eight monochrome sprites are X-expanded and placed at VIC X positions
0, 48, …, 336. Their visible coverage in the normal 384×272 VICE viewport
starts at x=8 and extends through its right edge. The first eight pixels stay
black. Text is visible in all four border regions.

The sprites first advance normally from Y=60. A timed expansion crunch on
line 76 changes MCBASE from `$2d` to `$35`. Every following line clears
`$D017` on human-numbered PAL cycle 15 and enables expansion again before
cycle 56. Since the crunch transformation maps `$35` to itself, all eight
DMA streams stay active on that single source row indefinitely.
This uses the documented
[Lunatico sprite-counter equation](https://www.linusakesson.net/scene/lunatico/misc.php),
also exercised separately in
[collision-sprite-crunch](../collision-sprite-crunch/README.md).
This example does not use collision bits as its controller.

Different sprite-pointer matrices select a new three-byte text slice for
each column on each raster line. The same register value selects both
`$D018` and the VIC bank through CIA2. The main background mode is invalid
bitmap/ECM and remains black. No idle graphics or ghostbyte supplies text.

The horizontal opening uses an actual `DEC $D016`, starting on cycle 51:
its two writes occur on cycles 55 and 56, changing CSEL from 40 to 38 columns
between the two right-border comparisons. The writes finish despite sprite
DMA taking the bus. CSEL is restored earlier on the following line.

Initialization opens the vertical latch with one screen-on field. The steady
program then keeps DEN off, preventing badline stalls, and changes RSEL on
lines 249 and 252 so the vertical bottom comparison is missed. These are
general sprite/border principles, also described in Raistlin's
[all-border DYPP article](https://c64demo.com/memento-mori-all-border-double-dypp/);
this is not a recreation of that DYPP.

## Prepared data and runtime work

`artwork.json` owns the small 5×7 font and four 32-character text lines.
`prepare.py` packs their 32 scanlines into sparse sprite banks. Only 768
foreground bitmap bytes and 256 pointer bytes are needed, distributed over
two 16 KB address spaces. No framebuffer animation frames are stored.

VIC bank 1 at `$4000` is used directly. The other bank is staged at
`$8000`, then copied to `$c000–$ffff` while CPU I/O is disabled. This
avoids VIC character-ROM interception in bank 2. Sprite-pointer matrix 15
of bank 3 overlaps interrupt vectors; its blank row therefore aliases
bank 1's blank row 7. The two IRQ vector bytes change during stabilization
and are never consumed as sprite pointers.

The runtime kernel changes the pointer matrix/bank each raster line,
maintains all border/crunch timings, and advances the font-row phase once
per field. It runs through all 312 PAL lines. After the initial partial
bootstrap field, the visible 32-row pattern wraps smoothly every 32 fields.
Interrupts remain disabled during the steady raster loop.

## Native result

The tracked verifier uses authored glyph coordinates as its input and
independently predicts expanded sprite pixels over the entire native
384×272 viewport. It also checks VIC DMA counters, selected source matrices,
the RAM-under-I/O bank copy and instruction timing.

Passing receipt:
`build/verification/20261108T092747.333663Z/verification.json`.

- **33 consecutive complete fields**, including every phase and the wrap:
  **3,446,784 exact pixels**.
- **1,081,344 source-bank bytes** matched, with only the specified IRQ-vector
  initialization accounted for.
- **66 native timing points** across six phases: all eight MCBASE values
  stayed at 53, DMA stayed active, crunch writes ended on cycle 15 and
  side-border RMW writes ended on cycle 56.
- One pixel upward per field, exactly **19,656 clocks** per field.
  Every captured phase had foreground in all four borders.
- A same-duration `INC` replacing one border `DEC` removed exactly
  **16 side-border pixels**, leaving the interior unaffected.
- Making all sprite colors black, while preserving DMA and raster timing,
  produced **104,448 exact black pixels**. This excludes a visible ghostbyte
  contribution.
- A paired vertical-latch probe briefly closes the horizontal gate.
  Correct RSEL reopens it at the next left edge, affecting only eight
  side-border pixels. Omitting the RSEL change instead blocks the bottom
  interior and rejects **3,106 pixels**.

PRG SHA-256:
`c15f94938bc04b99c2314ddd6ac603689fa3bc99021a8984277542755d80561d`.
Each verification run creates a new dated receipt initialized with
`passed: false`, preserves failure evidence and closes its VICE process.
