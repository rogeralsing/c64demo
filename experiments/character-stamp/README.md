# Sprite-to-character digit handoff

This original PAL C64 example changes one digit from a hardware sprite to a
3 × 3 character stamp. The same image survives the switch while its hardware
sprite slot becomes available for an additional green star.

All eight hardware sprites occupy the same raster band. In view A, sprite 0
draws the white digit and wins fixed sprite priority over the moving red ball
in slot 1. In view B, the digit uses characters; sprite 0 draws the green star,
and the red ball passes in front of the character digit. The second view thus
shows nine objects while retaining only eight simultaneous hardware sprites.

## Build and run

```sh
sh build.sh
sh run.sh
```

Requires the project's existing KickAssembler and PAL VICE installation.
Output is `build/example.prg`. Views change every 128 PAL fields. No keyboard
input, downloaded artwork or research cache is required.

## Transposition and publication

The digit is original 5 × 7 artwork expanded into a 24 × 21 sprite. At startup,
the C64 transposes its three byte lanes into nine row-major eight-row glyphs.
Three zero rows pad the image to a 24 × 24 character block. Character zero is
explicitly blank; other ordinary text glyphs come from the machine's ROM.

The main loop prepares the next mode, sprite pointer, positions, colors and
frame number, then publishes a single ready flag. The top-border raster IRQ
clears the previous nine screen cells, writes the new nine codes and Color RAM
when needed, updates the hardware sprites, and releases the flag. Preparing a
future packet cannot erase the currently displayed character digit early.

The digit remains aligned to the character grid. The red ball animates through
it, making the priority difference observable. Its transparent pixels reveal
the same digit image in either representation. This example does not implement
fine-scroll positioning, a rotating nine-digit ring or a sprite multiplexer.

## Provenance and differences

The mechanism is informed by [the Nine character-path investigation](../../docs/research/nine-character-path.md)
and Linus Åkesson's author explanation linked there. This contains new code
and new artwork, not Nine's released bytes or digit font.

Nine's authored script chooses the representation and its IRQ consumes packets
for eight sprites plus one digit. This example uses a fixed timed switch and
one ready flag. It makes both slot reuse and fixed-priority consequences
explicit without claiming an automatic overlap detector or an exact clone.

## Native verification

```sh
sh build.sh
python3 verify.py
```

The verifier needs Python 3 with Pillow and the existing `x64sc` executable.
Set `VICE` to select another VICE path. It starts and closes its own emulator
and writes new evidence under ignored `build/native/` without a research cache.

Verified in PAL VICE on 8 November 2026. Fifteen captured fields include both
switch directions, the matching digit before/after frame 127→128, and red-ball
overlap at frames 64 and 192. An independent geometry/priority model matched
the complete 320 × 24 scene strip in every capture: **115,200 pixel comparisons,
zero mismatches**.

The 24 × 24 digit region retained all **576 pixels** across the representation
switch. At equal overlapping red-ball positions, **101 pixels** changed exactly
as predicted by sprite priority versus sprite-over-character priority.

Each capture also matched all 72 transposed font bytes, nine screen codes,
nine Color RAM entries, sprite pointers, mode, positions, eight enabled slots
and the queued next-frame packet. At the two transition boundaries, the queued
new mode left the current stamp unchanged until IRQ publication. Complete RAM,
I/O and Color RAM dumps, screenshots and the monitor transcript remain beside
`build/native/proof.json`. The owned VICE process exited after capture.

This verifies one grid-aligned stamp and the authored timing sequence. It does
not verify Nine's ring geometry, fine-scroll placement, complete multiplexer
or physical VIC-II revisions.
