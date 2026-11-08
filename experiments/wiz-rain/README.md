# WIZ rain with slower C64 bump lighting

An original, coarse character-cell counterpart of the representation described
in Lunatico's original note: spatial animation phases form a WIZ surface, and
AGSP viewpoint motion animates the ripples while bump/light calculations run
more slowly. The recovered evidence is summarized in
[the local research note](../../docs/research/lunatico-rain.md). The original
rain height equation, lighting implementation and update rate remain unknown.
No Lunatico executable, code or artwork is included here.

```sh
./experiments/wiz-rain/build.sh
./experiments/wiz-rain/run.sh
python3 experiments/wiz-rain/verify.py
```

Run these from the repository root. The output is `build/example.prg`, using
the shared Kick Assembler and VICE helpers and existing Python/Pillow tools.
This program targets PAL; physical hardware has not been tested.

## One spatial atlas, actual AGSP

WIZ means **Wraparound Isometric Zoetropes**. The author's
[Perpetual Fragility explanation](https://www.linusakesson.net/scene/perpetual-fragility/index.php)
also explains the underlying ten-bit VIC address space and the diagonal
arrangement of small animation phases. Our example uses a two-dimensional
ripple surface, without an isometric object scene.

The atlas has 1,024 character cells. Each new viewpoint is
`(120 + 64*phase) mod 1024`, for 16 phases. The VIC adds 40 cells for each
displayed character row. Crossing cell 1023 therefore wraps to cell 0,
rather than wrapping an ordinary 40×25 rectangle. No matrix rows are copied
to perform this viewpoint change.

The display program performs real **VSP plus linecrunch**:

- A double raster IRQ reaches line 47, zero-based cycle 3. A selected delay
  positions the `DEC/INC $D011` VSP sequence on line 48.
- VSP produces a baseline `VCBASE=120-x` before line 67.
- On lines 67–95, active slots enter display state with RC=7, then cancel
  the early badline before its RC reset. Each active slot advances the
  actual VIC counter by 40. Idle slots keep RC=7 and hold the counter.
- After 0–24 active slots, the line-96 badline resets RC to zero. Normal
  character display begins at exactly the requested ten-bit viewpoint.

The early and later writes in each 63-clock slot finish on human-numbered
cycles 8 and 43. The selected VSP delay x is 0, 8, 16, 24 or 32. Native
counter observations prove the resulting addresses, including the
`1016 → 56` wrap between the last two high-offset phases.
The general PAL reference is
[Codebase64's AGSP example](https://codebase.c64.org/doku.php?id=base%3Aagsp_any_given_screen_position);
this program uses its own bounded delay blocks and active/idle line slots.

The top 45 screen rows cover the positioning work. The main image contains
40×19 cells, or 320×152 physical pixels. The final three screen rows show
the idle background after the VIC's badline cutoff at raster 248.
`$3fff` is explicitly zero, so idle fetches remain empty.

## Own ripple and lighting equations

`prepare.py` accumulates 16 small ring phases into one periodic height
atlas. Phase t has center `64*t mod 1024`, age `t/16`, radius
`.4 + 5.2*age`, and elliptical distance `r=sqrt(dx²+(1.5*dy)²)`.
Its contribution is:

```text
10*(1-age) * sin(pi*(r-radius)) * exp(-((r-radius)/1.1)^2)
```

The combined height is rounded and clamped to 0–31 around a base height of
15. Contributions use the same modulo-1024 cell topology as the VIC.
Neighboring rings overlap. Moving the viewpoint advances all their spatially
arranged phases together; the underlying height atlas remains unchanged.

The C64 computes central differences for every atlas cell:
`dx=H[i+1]-H[i-1]`, `dy=H[i+40]-H[i-40]`, with wraparound.
It then evaluates `128 + Lx*dx + Ly*dy` using signed multiplication tables,
quantizes the result to 16 luminance codes and writes an inactive matrix.
Sixteen successive light directions turn around the surface.

This is character-cell bump lighting: one normal/light result per 8×8
physical cell, represented by a multicolor dither glyph. It does not claim
per-pixel bump normals or Lunatico's original resolution.

## Prepared and runtime work

Prepared data consists of a 1,024-byte height atlas with 40-byte wrap halos,
a 2,048-byte reusable font, five signed multiplication pages, a shade lookup
and one initially lit matrix. No sequence of complete framebuffer images
is stored. The font uses blue, light blue, cyan and white.

At runtime, the C64 recalculates 128 cells each field. Two matrices at
`$0400` and `$0800` alternate; a completed 1,024-cell result is published
only in the bottom border. The font is at `$3000` and the height atlas at
`$6000`. The CPU owns zero-page `$02–$10` for neighbor/output pointers and
its weighted-gradient temporary.

The viewpoint advances every PAL field. A complete bump/light update takes
**eight fields**: nominally 50 apparent animation steps per second and
6.25 fresh lighting surfaces per second. Those are separate rates.

## Native proof

The passing receipt is
`build/verification/20261108T090616.285266Z/verification.json`.
The tracked verifier independently reconstructs the height equation, glyph
coverage, finite differences, signed light dot products and VIC addresses.
It checks the assembled PRG in native PAL VICE, without a verification-only
program build.

- **129 consecutive fields**, covering all viewpoint routes and all 16 light
  directions, with exactly **19,656 clocks per field**.
- **264,192 matrix bytes** matched, including every intermediate inactive
  chunk, completed publication and unchanged active matrix.
- **18 full screenshots: 1,152,000 exact pixels.**
- Eleven VSP timing observations and all 29 linecrunch/idle slots at the
  high-offset phase matched actual VIC counters. The viewport starts at
  line 96, zero-based cycle 4.
- Sampled 128-cell computation bodies took **9,389 or 9,562 clocks**,
  including VIC stalls, and finished by raster 251. Complete matrices changed
  every eight fields.
- Two explicit synthetic negative controls changed only live routing-table
  inputs after the normal run. Incorrect VSP and linecrunch routes produced
  wrong actual viewpoints and **10,692 / 10,360** wrong pixels respectively;
  both were rejected by the independent image oracle.

PRG SHA-256:
`5a075ebceddf5666bc67ea3e925f815d0a6bd92d32a1f11246a26b29f80d6da4`.
Each run creates a new dated receipt initialized with `passed: false`,
preserves failure evidence and closes its own VICE process.
