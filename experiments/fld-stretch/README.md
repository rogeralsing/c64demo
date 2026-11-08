# Flexible line distance and eight-row bitmap stretching

This original example demonstrates two different operations documented in
the [Demo Coder raster investigation](../../docs/research/demo-coder-raster.md):
delay the next character/bitmap row with FLD, then stretch all eight source
rows through bank selection. It uses our own eight-row `ALL 8 ROWS` picture,
code and timing schedule. It does not identify an unassigned original scene
or claim to reproduce Rubicon's complete implementation.

```sh
sh build.sh
sh run.sh
python3 verify.py
```

Seven normal bitmap rows establish `VCBASE=280`. The live C64 phase chooses
a gap of zero to seven raster lines. During this gap, YSCROLL avoids the
next badline and the VIC remains idle with RC=7 and VCBASE unchanged. This
is actual flexible line distance, rather than a black rectangle covering
an otherwise advancing image.

The following 128 raster cells repeatedly create early badlines and reset
RC to zero. Each cell changes CIA2 and D018 before graphics fetches. Eight
bitmap bases contain the eight different source rows at sparse RC0 byte
positions. The C64 calculates the current row duration, patches each cell's
bank selector, and prepares the YSCROLL/mode page every field. Each source
row lasts eight to sixteen lines. The visible picture therefore contains
all eight rows stretched to 64–128 physical lines, with an independent
FLD gap above it. Unused cells select invalid ECM+BMM mode and draw black.

Matrices at bank offset `$3C00` avoid the VIC's character-ROM windows.
The program loads below `$3140`; initialization installs the sparse row
bytes and four matrices in their actual banks. No full animation frames,
downloaded production assets or research cache are required at runtime.

The [native verification receipt](build/verification/verification.json)
checks 33 consecutive PAL fields, all 16 gap/height states and wraparound.
All 2,112,000 viewport pixels match an independent eight-row scale model.
It also checks 12,288 actual register stores, every patched selector, all
source bytes and matrices. Eight VIC snapshots show RC=0, VCBASE=280 and
the expected matrix cache during the eight source rows. A separate FLD
snapshot shows RC=7, idle state and no badline in the delayed gap.

Cells run exactly 63 PAL clocks apart. Observed D011 store checkpoints are
at zero-based cycles 58 or 59, with CIA2/D018 at cycles 1/5 or 2/6 of the
next raster. These are debugger checkpoint clocks, not physical bus-phase
claims. Complete presentations occur every PAL field, about 50/s; the
breakpoint interval has a few clocks of instruction-completion variation.

[Preview](build/verification/fld-stretch.gif), full native screenshots,
port traces and VIC snapshots are retained beside the receipt. The preview
slows each field to 80 ms. VICE exits 0 after verification. No different VIC,
NTSC, analog monitor or physical-hardware result is implied.
