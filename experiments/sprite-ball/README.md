# Expanded sprite ball proof of concept

A standalone PAL C64 demo using one expanded, single-color hires sprite per
visible polygon. Twelve independent pentagons define the colored patches of a
truncated icosahedron. Its twenty black hexagons are supplied by the background.
There are no shared vertex indices, edge lists, or face adjacency records.

Each face owns five 3D vertices and a normal. All faces share one rotation matrix.
Projection is orthographic. Opposite normal pairs limit visibility to six faces;
all eight hardware sprite slots remain available.

## Build and run

Requires Python 3, Kick Assembler (`kickass`), Java, and VICE (`x64sc`).

```sh
cd /Users/rogerjohansson/git/asynkron/c64demo/experiments/sprite-ball
sh run.sh
```

`sh build.sh` builds without launching VICE. `KICKASS` and `VICE` can select
alternative executable paths. The runnable program is
`build/baseline/sprite-ball.prg` (`SYS2062`).

The main demo and its build/run scripts are untouched. This experiment uses its
own generated files, PRGs, and verification output under this directory's ignored
`build/` folder.

## Rendering

Each sprite stores 24×21 one-bit pixels in 63 bytes. X/Y expansion displays these
as 48×42 physical C64 pixels. Each face has an independent color; its projected
normal selects dark green, light green, or white.

Every render performs these steps:

1. Clear the six 63-byte crossing buffers using generated absolute stores.
2. Rotate and cull the faces, then project the visible vertices on the C64.
3. Subtract each face's bounding-box origin to get local sprite coordinates.
4. XOR one crossing per integer X in each edge's half-open `[left,right)` interval.
5. Prefix-XOR the three byte columns and store the completed hardware sprites.
6. Present the back sprite set in the upper border, every two PAL ticks.

Both clearing and filling are fully unrolled. Crossing buffers use column-major
layout, so vertical addressing is consecutive. The fill stores convert that
layout into the VIC's three-bytes-per-row sprite layout at no extra pass cost.
The six used sprite images are completely overwritten; old pixels cannot survive.
Transparent areas inside the sprite rectangles are processed. Black space between
rectangles has no corresponding memory operations.

Only static geometry and arithmetic tables are generated on the host. Rotation,
culling, projection, boundary drawing, and filling execute on the C64. There are
no prepared animation frames or prepared projected-coordinate streams.

DEN stays low across raster line 48, suppressing badlines, then a line-49 IRQ
sets DEN before the vertical border opens. Screen and Color RAM remain black.
Sprite pointers, positions, colors, and enable bits change in the line-zero IRQ.
The visible border stays black.

## Mathematical shortcuts

The baseline uses signed Q6 quarter-square multiplication and a shared matrix.
Short edges permit an additional exact optimization: a generated table supplies
an 8.8 step and initial fractional bias for every `dx=1..23`, `dy=-20..20`.
These reproduce `ceil(n*dy/dx)` for every sample of the edge. The pixel loop
advances Y with carry, without an error-correction branch or slope artifacts.

An experimental variant projects only pentagon corners 0, 2, and 4. With
`k=(sqrt(5)-1)/2`, it reconstructs:

```text
P1 = P0 + k*(P2-P4)
P3 = P4 + k*(P2-P0)
```

Four constant-multiply lookups replace ten general multiplies per visible face.
Pixel rounding changes the reconstructed corners, so the baseline is the default.

```sh
sh run.sh golden
```

## Verified results

Both variants passed a full 256-presentation rotation cycle in PAL VICE.

| Measurement | Baseline | Golden-ratio reconstruction |
| --- | ---: | ---: |
| Presentation rate | 25.06 fps | 25.06 fps |
| Mean elapsed clocks/render | 34,819 | 32,200 |
| Maximum elapsed clocks/render | 37,024 | 34,307 |
| Maximum corner-coordinate difference from baseline | 0 | 4 logical pixels |

The shortcut saves about 7.5% total render time in this version. Its worst-case
corner difference is eight physical screen pixels, so it remains optional.
The clock measurement includes IRQ service and VIC sprite DMA stalls. One
presentation budget is 39,312 PAL clocks.

Verification checks all 65,536 yaw/pitch combinations for face size and sprite
count. Baseline vertex spans are at most 17×18 logical steps; the reconstruction
variant reaches 17×20. Both fit the sprite's 24×21 coordinate grid. Each run also
checks 129,024 native sprite bytes against independent rational polygon spans,
all 11,316 permitted edge samples, and an actual VIC screenshot with zero pixel
differences from the verified output.

```sh
# Verification additionally needs NumPy and Pillow.
python3 verify.py
python3 verify.py --variant golden
```

Evidence, actual VICE screenshots, and animations are stored under
`build/<variant>/verification/`. The JSON receipts contain the PRG hash and each
render's timing.

## Using all eight sprites

The same truncated-icosahedron geometry has twenty congruent hexagonal faces.
Select sixteen as eight opposite pairs, and leave the remaining faces black.
With orthographic projection, this gives at most eight colored faces, and eight
at generic orientations. This hexagon version is not implemented here.

Regular hexagons also allow cheaper corner reconstruction. With center C and
two adjacent radius vectors U and V, their vertices are:

```text
C+U, C+V, C+V-U, C-U, C-V, C+U-V
```

After projecting C, U, and V, all six corners need only additions and
subtractions. Hexagon bounds would need their own scale check.

Hardware background: [Christian Bauer's VIC-II reference](https://www.cebix.net/VIC-Article.txt).
Geometry: [Wolfram MathWorld's truncated icosahedron](https://mathworld.wolfram.com/TruncatedIcosahedron.html).
