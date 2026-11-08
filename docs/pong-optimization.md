# Pong cube optimization, 8 November 2026

This records the mapping pass. The subsequent
[boundary and fill optimization](pong-boundary-optimization.md) contains the
current measurements and continuation point.

The current Pong cube renders the same images and game states with 4.34% fewer
mean elapsed PAL cycles than the preceding visibility-only build. Presentation
remains 25 fps, with two complete PAL frames per image.

## Changes

Only `src/pong-renderer.asm` changes the executable behavior in this pass:

- Assembly-time loops emit direct XYZ scratch stores for all rectangle corners.
  The signed quarter-square products and each independent subtraction retain
  their original rounding and carry behavior.
- A runtime zero-factor check lets world-X corners share duplicate results.
  The general four-corner path remains available when that factor is nonzero.
- Four projected scratch vertices use direct addresses instead of an index loop.
- Body edges use fixed endpoints and color transitions derived from the existing
  guarded visibility mask `$1a`. Zero transitions emit no call. Descending edge
  order, all model tables and the six material-state writes remain intact.

The game rules, motion, exact boundary DDA and combined fill/output/marker reset
are unchanged. No new arithmetic tables are needed.

## Measured CPU cost

Both builds were profiled over 706 consecutive presentations. Measurements
include VIC-II bus stalls and raster interrupts. The two extra stage boundaries
separate `drawCube..boundariesReady` from `boundariesReady..frameReady`.

| Work | Previous mean cycles | Current mean cycles |
|---|---:|---:|
| Frame setup | 107.49 | 107.49 |
| Body rotation | 896.00 | 896.00 |
| Body projection and bounds | 1,372.30 | 1,372.30 |
| Face culling | 18.00 | 18.00 |
| Pong mapping, projection and boundary drawing | 22,450.77 | 20,824.00 |
| Fill, output and marker reset | 10,835.81 | 10,914.57 |
| Complete renderer | 35,680.36 | 34,132.36 |
| Peak complete renderer | 37,099 | 35,615 |
| Shortest presentation wait | 1,860 | 3,342 |

The mean saving is 1,548 cycles; the peak falls by 1,484. The fill instructions
remain unchanged, but their earlier raster position changes VIC-II stalls and
interrupt overlap. Therefore their elapsed cost can increase slightly.

The renderer total excludes the game/motion update after presentation. Native
verification includes that update when checking the complete presentation
cadence: 39,300–39,325 cycles around the two-frame schedule. A PAL frame contains
19,656 cycles. The current renderer still exceeds a single-frame budget.

An intermediate mapping-only build averaged 34,763.52 cycles. Its source, PRG,
symbols and profile are preserved in `build/pong/optimizations/20261108-mapping/mapping-only/`.

## Memory and validation

The PRG grows by 325 bytes, from 50,781 to 51,106. Body drawing also uses 191
bytes of existing prelude padding. The generated fill banks remain at `$4c00`
and `$8c00`; both 2 KB display buffers and projection-cache ownership remain
unchanged. Code/state end at `$cfa0`, leaving 95 bytes before mapped I/O.

The final native run passes 706 presentations and 705 game updates against the
independent opaque pixel and game reference. All fourteen recorded image,
geometry, state, marker and dirty-buffer fields match the previous build for
every presentation. There are zero boundary parity errors. Both paddles and
both walls are exercised; 32 VIC-II captures pass. Eleven rebuilt non-Pong PRGs
are byte-identical to their saved hashes. The standalone Pong PRG matches the
verified root PRG byte for byte.

Final PRG SHA-256:
`e627f76b582e8e020405e21eaccec14f04f3b3da053878a2215f85878c1d3e6e`.

Local receipts:

- [Previous detailed profile](../build/pong/optimizations/20261108-mapping/baseline/detailed-profile/profile.json)
- [Final detailed profile](../build/pong/optimizations/20261108-mapping/final-profile/profile.json)
- [Native verification](../build/pong/optimizations/20261108-mapping/final-verification/verification.json)
- [Frame-by-frame comparison](../build/pong/optimizations/20261108-mapping/final-comparison.json)
- [Other-target binary comparison](../build/pong/optimizations/20261108-mapping/final-legacy-regression.json)
- [Final input hashes](../build/pong/optimizations/20261108-mapping/final-inputs.json)

## Continue here

Build with `sh build.sh pong`, or `sh experiments/pong-cube/build.sh` for the
standalone example. Run `python3 verify-pong.py --frames 706 --output DIR` for
native verification. Ordinary profiling uses:

```sh
python3 profile.py build/pong-cube.prg --labels build/pong.sym --frames 706 --output DIR
```

To reproduce the detailed profile, load `profile.py` as a Python module, insert
`boundariesReady` immediately before `frameReady` in `STAGES`, and insert
`fill_and_reset` immediately before `presentation_wait` in `COSTS`, then call
its existing `profile(...)` function. The output records all stage boundaries.

The next useful investigation is the exact boundary sampler: mapping and
drawing still account for about 61% of renderer time. Profile individual edge
calls before changing the DDA. Preserve its half-open parity contract, test
one-column and steep crossings, and compare the full 706-presentation cycle.
High runtime space is nearly full; use the remaining prelude space or reduce
existing code before adding more unrolled high routines. The quantized-slope
tradeoff remains outside this change.
