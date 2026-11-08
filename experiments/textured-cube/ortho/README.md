# Orthographic cube: competing samplers

The selected sampler is the row/column lookup implementation. Its current
three-axis Q10 geometry reaches **8.31 complete updates/s** in normal-speed
PAL VICE. The preceding yaw/pitch-only Q10 version reached **9.64**; adding
Z roll costs about 13.8% of that update rate. When the textured face is
visible, the current version averages **7.53 updates/s**. The initial
11.01-update/s orthographic result used visibly deformed whole-sample basis
vectors and is retained as historical evidence.

```sh
# From experiments/textured-cube:
sh build.sh ortho
python3 verify-ortho.py
sh run.sh ortho
```

All candidates keep one fixed textured face and five solid faces, an 80×50
sample canvas, 4×4 physical pixels, four colors and the same 64-pose cycle.
The C64 calculates three rotated 3D basis vectors for each update and builds
all eight vertices by signed sums. Basis vectors and vertices retain ten
fractional bits; scalar sine coefficients retain fourteen. Only the final
screen corners round to whole logical samples. No projected poses or complete image frames
are stored. The half-size is 14 logical units, chosen to keep this projection
inside the existing viewport; this is not a same-pixels comparison against
the perspective camera.

## Three-axis motion

The orthographic runtime applies Y-axis yaw, then X-axis pitch, then Z-axis
roll to each high-precision basis vector. The 64-pose animation uses these
angles, in units of 1/256 turn:

```text
yaw   = 4*phase + 1
pitch = round(24*sin(2*pi*phase/64 + 0.4))
roll  = 4*phase
```

Yaw and roll each complete a full turn per loop; pitch oscillates through
approximately ±33.75°. Z roll rotates the already tilted cube in the screen
plane. The C64 calculates the new basis, corners and coverage on every update;
scalar sine lookup tables contain no prepared geometry or image frames.
The texture remains attached to the same model face throughout the rotation.

## Geometry precision

The initial competition rounded each rotated basis vector to whole samples.
That preserved integer parallelograms but changed the cube's physical shape:
native axis lengths ranged from 12.884 to 15.297 instead of 14, and angles
ranged from 83.281° to 93.659° instead of 90°. The old pixel reference matched
that deformed model, so its successful pixel checks did not establish rigidity.

The corrected runtime retains Q10 basis vectors and vertices. Its signed
products use Q14 sine coefficients and round to nearest, with ties toward
positive infinity. The verifier reads the actual native high-precision arrays
and compares their lengths, angles and corners with an independent floating
point rigid rotation. It also checks the final projected corners, every
screen sample and complete native images. The same physical checks fail all
64 archived pre-fix poses; the receipt is
`../build/wobble-before-9749/rigidity-regression.json`.

The three-axis native run measures basis lengths **13.998885–14.001260**,
with at most **0.00901%** length error and **0.00683°** angle error.
Final projected corners differ from the ideal rigid orthographic projection
by at most **0.4995 logical sample per axis**. All 66 presentations, 264,000
screen samples and 65 complete native images pass. The
[native proof](build/verification/20261108T185939.135752Z/proof.json)
retains the exact program, source hashes and measured intervals.
The preceding yaw/pitch-only Q10 binary, inputs and animation are archived
under `../build/before-z-roll-aac1/`. Its native captures fail the new Z-roll
rotation oracle at every nonzero-roll phase; phase zero still passes.

Whole-sample screen corners need not form exact parallelograms after the final
rounding. The general four-edge walker renders each convex quad, and culling
uses both projected triangles. At every pose, visible faces cover the rounded
cube's convex hull without sample gaps or overlaps. Ordinary 4×4-pixel raster
aliasing remains visible; the internal cube no longer changes its dimensions.

## Sampler comparison

All three implementations were independently developed by subagents. Each
passed 66 native presentations, all 64 poses and wraparound, all 264,000
screen samples and 65 complete native screenshots against a separate
mathematical reference. After the precision fix, all three passed that same
native coverage plus the independent rigidity checks with the corrected
geometry. Cache construction and coordinate-table construction
happen inside the measured runtime; their cost is included.

| Sampler | Mean updates/s | Textured face visible | UV precision |
| --- | ---: | ---: | --- |
| Exact whole-face spans | 7.89 | 6.85 | Exact canonical Q8 |
| Lazy packed 2×2 tile cache | 7.76 | 6.66 | At most one texel per axis |
| **Selected row/column lookup** | **8.31** | **7.53** | At most one texel per axis |

The initial whole-sample geometry reached 10.15, 9.90 and 11.01 updates/s
respectively. Those historical timings and their binaries remain in the
original competition receipts; they do not describe the corrected builds.

The initial control, with ordinary triangle-filled solid faces, reached only
8.33/8.19/8.88 updates/s respectively. Using whole parallelograms for the
solid faces raised all three results. Removing perspective alone did not
produce the gain; eliminating redundant setup and per-texel arithmetic did.

The tile cache did not win. Each visible pose invalidates its 256 tags,
generates missing four-sample codes and masks boundary cells. That extra
work outweighed its saved UV stepping in this scene. The exact span
implementation remains available when preserving every texture sample is
more important than the selected sampler's additional speed.

## What the winner changes

The original whole-face Q8 target is:

```text
u = floor((duDx*(x-x0) + duDy*(y-y0))/256)
v = floor((dvDx*(x-x0) + dvDy*(y-y0))/256)
```

The selected implementation separates each sum before rounding:

```text
u = floor(duDx*(x-x0)/256) + floor(duDy*(y-y0)/256)
v = floor(dvDx*(x-x0)/256) + floor(dvDy*(y-y0)/256)
```

A sum of two floors differs from the floor of their sum by zero or minus
one. Thus each texture coordinate differs by at most one texel, with the
16×16 texture wrapping periodically. The declared mapping is checked
independently for every native pixel. This bound is relative to the Q8 affine
UV plane derived from the first three rounded face corners. Final corner
rounding means that plane is an approximation to the physical face's UVs;
the one-texel bound does not apply against an ideal continuous UV plane.
Geometry, culling and face coverage are checked separately.

In the three-axis complete 64-pose scene, **38.23% of textured samples change color**
relative to the exact sampler. This is a deliberate texture-coordinate
approximation, not an exact visual replacement. The geometry-dependent row
and column tables are rebuilt at runtime. A generic 4 KiB modulo-U lookup
table is assembled once; it contains arithmetic translations, not geometry
or artwork. The animated source texture remains generated on the C64.

The fixed textured face is visible in 31 of the three-axis cycle's 64
poses. Hidden-face jobs reach about **9.24 updates/s**, so the full-cycle mean
includes the cheaper fully solid half of the turn. Every preview uses the
actual per-pose hold time, rounded to GIF's 10 ms units. The animation advances
one phase per completed update; variable rendering cost causes variable
angular speed. Z roll uses the existing presentation scheduling.

## Reproduce the alternatives

```sh
# From the repository root:
sh experiments/build-one.sh "$PWD/experiments/textured-cube/ortho/alternatives/spans"
python3 experiments/textured-cube/verify-ortho.py --folder experiments/textured-cube/ortho/alternatives/spans --mapping exact
sh experiments/build-one.sh "$PWD/experiments/textured-cube/ortho/alternatives/tiles"
python3 experiments/textured-cube/verify-ortho.py --folder experiments/textured-cube/ortho/alternatives/tiles --mapping tiles
```

The retained experiment, archived input sources, original perspective
baselines, all native receipts and the selection rationale are beneath
`build/experiments/orthographic-competition/20261108T172619Z/`.
The [selection receipt](../../../build/experiments/orthographic-competition/20261108T172619Z/selection.json)
links all three successful runs. The selected build has its own latest
verification pointer at `ortho/build/latest-verification.json` and a stable
preview below.

![Selected lookup sampler at measured speed](build/orthographic-cube.gif)
