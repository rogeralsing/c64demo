# Collision-controlled sprite crunch

An original PAL example of the mechanism described by Linus Åkesson for
[Lunatico's MISC part](https://www.linusakesson.net/scene/lunatico/misc.php).
Eight colored sprite columns contain outlined, diagonally hatched tiles with
14, 17, 19 and 21 raster rows. Their initial vertical offsets follow separate
phases of a sine wave. The artwork and raster program are ours; this does not
package the original production or reproduce its complete choreography.

Run from the repository root:

```sh
./experiments/collision-sprite-crunch/build.sh
./experiments/collision-sprite-crunch/run.sh
python3 experiments/collision-sprite-crunch/verify.py
```

The output is `build/example.prg`. The shared build helper requires the same
Kick Assembler installation as the other examples. Verification uses the
installed PAL VICE `x64sc` and existing Python/Pillow setup.

## Actual hardware path

The eight sprites use VIC bank 1, pointers 0–7 and 512 bytes at
`$4000–$41ff`. They share Y=60 and have adjacent X positions 88+24×column.
They remain eight active DMA streams through the visible body; they are not
restarted every 21 rows.

The hires bitmap at `$6000` has a foreground stripe under the final pixel of
each sprite. Foreground and background both select black, and `$D01B=$ff`
puts sprites behind foreground. Those eight hidden sprite pixels therefore
set the eight independent bits in the **real** background/sprite collision
register `$D01F`. The CPU reads that register once per raster row, clearing
the hardware latches. The returned byte is written directly to `$D017` in
the steady-state body, raster lines 83–236.

With all eight DMA streams active, the raster program executes a five-cycle
NMOS `SHY $D017,X`, X=Y=0, whose zero write falls on human-numbered PAL
cycle 15. The collision read occupies cycles 16–19 and the direct expansion
write cycles 20–23. Clearing expansion at that specific cycle changes the
next sprite row counter according to the author's documented equation:

```text
n = (base + 3) mod 64
next = ((base OR n) AND $15) OR ((base AND n) AND $2a)
```

Without a selected crunch, the counter advances by three normally. Tile rows
are packed at offsets belonging to closed loops under those two operations.
The control pixel encodes the decision two positions ahead in the loop:
fetch, display, collision sampling and crunch are separated in the VIC
pipeline. Late `$D011` writes on even rows, ending at cycle 55, keep bitmap
fetches running while avoiding early badline DMA stalls. A double raster IRQ
aligns the prelude.

The bounded bootstrap is explicit. Sprites first advance normally from base
0. The program enables expansion on line 75 and crunches `$2d → $35` on
line 76. Seven C64-computed initial masks hold individual columns at the
blank `$35` row for 0–7 extra rows. Lines 76–77 use those masks, and lines
78–82 OR the remaining holds with actual collisions. From line 83 onward,
there is no CPU-packed substitute for the collision decisions. The CPU
still reads and resets `$D01F` during every bootstrap row. Full foreground
bitmap bands hide bootstrap and trailing DMA output.

## Prepared work and runtime work

`prepare.py` produces the original 512-byte sprite patterns and an
8,000-byte static bitmap of invisible control stripes and masking bands.
It validates the four row-counter loops. No animation frames are prepared.
The C64 computes the seven bootstrap masks each field from its 64-entry
offset curve, then runs the timed hardware collision/crunch program.

This example animates the initial phases of eight reusable tile patterns.
It does not implement Lunatico's changing artwork, column-update budget,
music or complete part sequencing. It requires a PAL NMOS 6510/VIC-II
timing model; physical C64 hardware has not been tested.

## Native result

The verifier checks the unmodified assembled PRG, reconstructs sprite bytes
from a separate geometric tile specification, and predicts row counters,
hardware collision bytes and full pixels independently of the CPU log.
It uses the monitor's VIC DMA counters as well as screenshots.

The passing native run is
`build/verification/20261108T084411.317039Z/verification.json`:

- All 64 consecutive movement phases: 9,856 direct body collision bytes
  matched. Native source patterns and sprite pointers also matched.
- 36 timed row observations across six phases: eight active DMA streams,
  expected MCBASE before and after the crunch, falling write ending at
  cycle 15, collision read at 16–19, cleared hardware collision latches,
  and direct body writes at 20–23.
- Eight complete 320×200 screenshots: **512,000 exact pixels**.
- One phase per PAL field, exactly **19,656 clocks** between field starts
  throughout the 64-phase run. This is nominally 50 updates per second.
- A separate synthetic negative control redirected one live crunch write
  on line 90 to the black border register, preserving instruction duration.
  Two actual VIC row bases became wrong and the independent full-image
  oracle rejected **2,166 pixels**. Only that final test changes live RAM;
  it does not change the PRG.

PRG SHA-256:
`cdb8e27d87cf7f17e95973d8a91ace5a586c6867d4b38f12e41f9ae264f2a2b0`.
The verifier always creates a new dated receipt, starts with
`passed: false`, records failures and closes its VICE process.
