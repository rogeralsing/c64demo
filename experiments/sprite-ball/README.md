# Expanded sprite ball proof of concept

A standalone PAL C64 demo using one expanded hires sprite per visible polygon.
The default model contains all twenty hexagons of a truncated icosahedron.
Each frame selects the eight largest visible hexagons. Pentagon-shaped gaps
and any smaller omitted hexagons show the static black sphere background.

All hexagons reference sixty shared vertices. Thirty opposite vertex pairs
are projected once, so adjoining faces always use identical edge endpoints.
Rotation, selection, culling, projection, boundary drawing, and filling run
live on the C64.

## Build and run

Requires Python 3, Kick Assembler (`kickass`), Java, and VICE (`x64sc`).

```sh
cd /Users/rogerjohansson/git/asynkron/c64demo/experiments/sprite-ball
sh run.sh
```

`sh build.sh` builds without launching VICE. The default runnable program is
`build/hexagon/sprite-ball.prg` (`SYS2062`). `KICKASS` and `VICE` can select other
executable paths. This experiment has its own generated files and PRGs under
its ignored `build/` directory; the main demo is unchanged.

The earlier twelve-pentagon comparisons remain available:

```sh
sh run.sh baseline
sh run.sh golden
```

The golden variant reconstructs two corners from three projected corners using
the inverse golden ratio. It can differ by four logical pixels from direct
projection. The hexagon variant uses direct shared-vertex projection.
Both older comparison models can extend beyond this supplied image's circle.
Foreground sprites are not clipped to that circle.

## Sphere image and sprite priority

The working Koala image is `assets/scene.koa`; the supplied version is preserved
as `assets/scene-unretouched.koa`. Both files match the supplied
`Skarmavbild- (2).koa` exactly. The earlier border repainting has been removed.
Its white circle has center (160,60) in 320x200 display coordinates.
Graphics placement constants
align the existing sphere there; its geometry and sprite rendering are unchanged.
The earlier hires image sources remain in `assets/` for reference.

At build time, `background.py` measures the supplied image's white circle and
paints a smaller circle at the same center, using global black
(selector `00`). Its radius is 43 display pixels, with one pixel trimmed from
the top and bottom of each column to prevent edge leaks. The surrounding source
image remains intact, without an added mask or dithering. All bitmap selectors
outside the painted circle, all screen attributes,
and all color RAM entries retain their source values. The historical rim
mask and lighting assets are no longer used.

`$D01B=$00` puts all sprites in front of the bitmap. The sprites remain hires
and are not clipped by the artwork. The 8000 bitmap bytes stay unchanged
while running. The two sprite buffers alternate through the pointer table
in one fixed color screen. Pentagon coloring remains removed: there is no
pentagon culling, shading, color fill, sorting, reset, or color-screen swap.

## Rendering and arithmetic

Each sprite contains 24x21 one-bit pixels in 63 bytes. X/Y expansion displays
these as 48x42 physical pixels. Each face has an independent color. Two lights
remain fixed in camera space as the model rotates:

```text
Upper left:  white, light green, cyan, mid gray, green, dark gray, brown, black
             1,     13,          3,    12,       5,     11,        9,     0
Lower right: white, yellow, light gray, pink, orange, purple, red, blue, black
             1,     7,      15,         10,   8,      4,      2,   6,    0
```

Lighting approximates the two side directions from the screen-space midpoint
of each polygon's bounds. In the internal coordinate system the sphere center is
(64,64). The signed doubled diagonal is:

```text
q = minX + maxX + minY + maxY - 256
```

Negative values select the upper left gradient; positive values select the lower
right gradient. Zero selects white. Larger magnitudes produce darker shades.
The byte sum discards the 256 offset without any extra instruction.

A lookup converts the diagonal into the approximate normal alignment
`abs(q)*45/(128*radius)`. The build computes the hexagons' mean center radius
from their static vertices: about 19.209.
The upper left gradient advances at alignments 0.15, 0.30, 0.45, 0.60, 0.75, 0.88,
and 0.94; the lower right uses 0.12, 0.25, 0.38, 0.50, 0.63, 0.75, 0.87, and 0.94.

One 256-byte table includes both gradients, their thresholds and the radius
normalization. Runtime shading only adds the four bounds and reads one byte.
There are no light-vector transforms or normal-light products. Bounding-box
midpoints approximate the true face centers; shade
transitions can move slightly. Geometry, Z-culling and vertex projection remain
exactly the same. The tables contain no animation frames.

Every render clears eight crossing buffers, transforms the visible faces,
draws their XOR boundaries, and prefix-XOR fills the back sprite set. Clearing
and filling are fully unrolled: each pass covers 504 bytes. Crossing buffers
use column-major layout; fill stores convert this to three bytes per sprite row.
Space between sprite rectangles has no clearing or filling cost.

For equal-size faces under orthographic projection, facing depth estimates
projected area. At most ten hexagons face the camera. The selector drops the
weakest one or two when necessary, keeping the largest faces on all eight
hardware sprites. Equal depths favor the lower face index. Opposite face
normals share one depth calculation. Each selected face gathers its six
projected corners and derives its sprite bounds.

The static coordinate values have specialized multiplication tables for every
rotation coefficient. Face tests and edge dispatch are unrolled. A shared
11316-byte table stores exact short-edge crossings for `dx=1..23, dy=-20..20`.
The half-open `[left,right)` endpoint rule and `ceil(Y)` crossings preserve XOR
parity at corners. These are arithmetic tables, not prepared animation frames.

## Memory and display

| Address | Use |
| --- | --- |
| $0400 | Static bitmap color screen and changing sprite pointer table |
| $0801 | Initial BASIC loader |
| $0C00 / $0E00 | Two sets of eight sprite images |
| $1000 | Initial Koala color RAM data, copied to $D800 |
| $1400 | Midpoint-diagonal color lookup for sprite faces |
| $1800 | CPU-only crossing buffers |
| $1A00 | Projected midpoint shading helpers |
| $2000 | Static 8000-byte multicolor bitmap |
| $4000 | Generated clear/fill code |
| $6000 | Shared-vertex hexagon projection |
| $8000 | Coordinate multiplication tables |
| $9400 | Initial bitmap color cells |
| $9800 / $9C00 | Edge-curve pointer tables |
| $A000 | Exact edge-crossing samples |
| $E000 | Runtime beneath disabled KERNAL ROM |

In VIC bank zero, sprites in $1000..$1FFF would read character ROM. The display
buffers deliberately stay below $1000. CPU crossing buffers can use that range.

The normal multicolor bitmap display is enabled, including its badline fetches.
Sprite pointers, positions, colors, and enable bits change in the line-zero IRQ.
The sprite-only renderer presents every two PAL frames: 25.06 fps, with
39312 clocks per nominal render budget. Rotation advances steadily by six yaw units and
three pitch units per presentation, using 256 units per full turn. There are no
speed changes or reversals. Geometry still runs live, and the combined path
repeats after 256 presentations, about 10.2 seconds. The visible border stays black.
Startup allows one extra PAL frame before the first presentation so an arbitrary
initial raster position cannot shorten the first render's deadline.

## Verification

```sh
# Requires NumPy and Pillow.
python3 verify.py
# Two complete rotations:
python3 verify.py --frames 513
python3 verify.py --variant baseline
python3 verify.py --variant golden
```

Geometry checks cover all 65536 yaw/pitch pairs. Hexagon vertex spans stay
within 17x19 logical steps, fitting the 24x21 sprite grid. Native verification
checks 257 presentations, covering the full rotation path and its wrap,
all 129528 sprite bytes against
independent rational polygon spans, all 11316 edge-table samples, and actual
VIC output against the expected composition. It also checks the ranked face
selection against all twenty hexagons. Eight nonempty sprite buffers
are reached. Bitmap bytes, the fixed color screen, and color RAM must remain
unchanged for every presentation. Native sprite colors must match an independent
projected-midpoint calculation, including gradient selection and brightness bands.
Both gradient families must appear. Every presentation must arrive on the
two-PAL-frame cadence with zero missed deadlines.
Koala verification checks the solid black circle, measured origin, and exact
preservation of bitmap selectors and colors outside it. Every presentation
checks foreground sprite priority; native output must match the expected
foreground composition. Sprites may cover artwork because their priority
places them above the bitmap.

Screenshots, animation, monitor logs, PRG hashes, source-image hashes, and CPU
measurements are saved under `build/<variant>/verification/`.

Hardware: [Christian Bauer's VIC-II reference](https://www.cebix.net/VIC-Article.txt).
Geometry: [Wolfram MathWorld's truncated icosahedron](https://mathworld.wolfram.com/TruncatedIcosahedron.html).
