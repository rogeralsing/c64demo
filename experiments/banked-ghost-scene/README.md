# A bank-aware ghostbyte scene

Our own bitmap scene and moving sprite cutouts exercise the concrete
first-scene address anchors documented for
[The Ghost](../../docs/research/the-ghost.md): VIC bank `$4000`, D018 `$80`,
screen `$6000`, ordinary idle byte `$7FFF`, and bitmap/character mode changes.
The original first scene has not been pixel-matched or assigned a complete
raster contract. This is an original counterpart, with our own ghost,
landscape, font, masks and timing schedule.

```sh
sh build.sh
sh run.sh
python3 verify.py
```

The top image is a prepared 320×200 hires bitmap. Every field, the C64 copies
one of sixteen reusable 512-byte mask arrangements into the sprite buffer.
Eight X-expanded multicolor sprites cover the lower border. Their opaque
symbols hide the idle pattern; transparent letter cutouts reveal its finer
one-pixel detail. The C64 rotates the live idle byte while the cutout title
moves horizontally. No full animation frames are stored.

The raster program keeps bitmap mode through all 200 source rows. It opens
the lower border using RSEL, changes to character idle output after the last
bitmap pixels, and restores normal character mode at raster258. The idle
pattern is cleared after the captured display ends. The warm vertical latch
also leaves a plain upper idle band and an eleven-line black divider before
the bitmap. Mode handovers finish before the next graphics fetches.

The [native receipt](build/verification/verification.json) checks seventeen
complete 384×272 PAL images, all sixteen motion states plus wraparound:
1,775,616 pixels match the independent bitmap/idle/sprite compositor.
Each field's bitmap bytes, current masks, matrix and sprite pointers also
match. A VIC snapshot establishes idle state, RC=7, VCBASE=1000, zero cached
foreground colors and all eight active sprite DMA streams.

Two real RAM-input controls distinguish the bank addresses. Changing only
`$3FFF` leaves all 104,448 pixels of the next full image unchanged. Setting
the selected normal idle-pattern input to zero removes exactly 1,428 pixels
of fine detail even while `$3FFF` remains nonzero. Code and execution PCs
are never patched by the verifier.

Complete presentations occur every PAL field, about 50/s. The
[preview](build/verification/banked-ghost-scene.gif) slows fields to 80 ms;
full screenshots and the closed VICE transcript remain beside the receipt.
This proves our native PAL composition, not the original release's exact
appearance, timing, other scenes or physical-hardware behavior.
