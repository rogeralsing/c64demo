# Expanded sprite ball proof of concept

A standalone PAL C64 demo using one expanded hires sprite per visible polygon.
The default model contains all twenty hexagons of a truncated icosahedron.
Each frame selects the eight largest visible hexagons. Visible pentagons use
moving bitmap color cells; any smaller omitted hexagons use the sphere background.

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

## Sphere image and sprite priority

The working Koala image is `assets/scene.koa`; the supplied version is preserved
as `assets/scene-unretouched.koa`. The rim has been corrected to a symmetric
92-pixel circle, with nearby color streaks repaired within multicolor limits.
Its white circle has center (160,60) in 320x200 display coordinates.
Graphics placement constants
align the existing sphere there; its geometry and sprite rendering are unchanged.
The earlier hires image sources remain in `assets/` for reference.

At build time, `background.py` decodes the scene and opens a solid black circle
interior, without dithering. Every pixel outside the circle retains
its original color. Within the circle, selector `01` reveals behind-graphics
sprites and takes its color from the screen byte's high nibble. Selector `00`
provides fixed black outside the moving gap-color region.

`assets/scene-rim.pbm` adds an eight-pixel inward opaque rim: outer radius 46,
inner radius 38. `assets/scene-rim-light.koa` extends surrounding light streaks
into 688 of its 1048 multicolor pixels. A constant two-pixel black outline
occupies radii 38 to 40; short colored streaks continue across nearby tiles.
Selectors `10` and `11` provide two fixed opaque colors per cell through the
low screen nibble and color RAM. Both cover sprites and pentagon color spill
without per-frame work. `assets/scene-rim.json` records the mask geometry and
lighting counts.

`$D01B=$FF` selects behind-graphics priority for all sprites. In multicolor
bitmap mode, selectors `00` and `01` reveal sprites; `10` and `11` hide them.
The sprites themselves remain hires. The 8000 bitmap bytes stay unchanged.
Two copies of the color cells alternate with the sprite buffers, so moving
pentagon colors and sprite positions appear together.

## Pentagon gap colors

The mesh contains twelve pentagons. Every lit, front-facing pentagon can change
color, even when one of its neighboring hexagons has no hardware sprite. Its
facing estimate comes from the sum of those five original face depths, divided
by the length of their summed normal. Sprite selection keeps a separate depth
copy, so dropping a hexagon cannot darken or disable a neighboring pentagon.
That normalization gives the same facing cosine used for hexagons. Both face
types use the same fixed material and brightness thresholds; pentagons no longer
have a separate dark ramp. Dark rim gaps keep the static black color.

The mapper projects no extra vertices. It takes the bounds of the pentagon's
five shared vertices and paints the full rectangle of 8x8 color cells. Farther
pentagons paint first, allowing nearer faces to win overlapping cell rectangles.
Neighboring sprites and the fixed rim hide most excess coverage. Color clashes
at omitted hexagons and shared cell boundaries are accepted;
there is no clipping to a conservative envelope or partial pentagon fill.
Only a 10x9 region of the back color screen needs resetting each presentation.
Color writes stay inside that reserved region; the surrounding bitmap uses
fixed selectors and cannot display animated gap colors.
Resetting restores original scene attributes, preserving nearby artwork.
Gap shading preserves the low color nibble in boundary cells shared with artwork.

## Rendering and arithmetic

Each sprite contains 24x21 one-bit pixels in 63 bytes. X/Y expansion displays
these as 48x42 physical pixels. Each face has an independent color. Its normal
selects this fade from the silhouette toward the camera:

```text
black, brown, dark gray, green, mid gray, cyan, light green, white
0,     9,     11,        5,     12,       3,    13,          1
```

For either polygon family, divide its camera-facing depth by its normal length.
The shade advances at facing cosines 0.15, 0.30, 0.45, 0.60, 0.75, 0.88, and 0.94.
White is reserved for nearly front-facing polygons, approximately within 20 degrees
of the camera axis. The fixed-point normals quantize these boundaries slightly.
All 65536 rotation pairs allow at most two white faces across the complete mesh.
Two neighboring faces can briefly share the highlight during rotation.
The build generates two small lookup tables from this one formula, accounting
for the different normal scales and the bitmap color nibble. No extra runtime
division, palette switching, or color cycling is needed.

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
| $0400 / $0800 | Two bitmap color screens and sprite pointer tables |
| $0801 | Initial BASIC loader; reused by the second color screen after startup |
| $0C00 / $0E00 | Two sets of eight sprite images |
| $1000 | Initial Koala color RAM data, copied to $D800 |
| $1400 / $1500 | Mixed sine/cosine yaw and pitch paths |
| $1600 | Shared material, normalized for sprite and gap depths |
| $1800 | CPU-only crossing buffers |
| $2000 | Static 8000-byte multicolor bitmap |
| $4000 | Generated clear/fill code |
| $6000 | Shared-vertex hexagon projection |
| $7000 | Pentagon color mapping, paint ordering, and static topology |
| $8000 | Coordinate multiplication tables |
| $9400 | Initial bitmap color cells |
| $9800 / $9C00 | Edge-curve pointer tables |
| $A000 | Exact edge-crossing samples |
| $E000 | Runtime beneath disabled KERNAL ROM |

In VIC bank zero, sprites in $1000..$1FFF would read character ROM. The display
buffers deliberately stay below $1000. CPU crossing buffers can use that range.

The normal multicolor bitmap display is enabled, including its badline fetches.
Sprite pointers, positions, colors, and enable bits change in the line-zero IRQ.
The gap-mapping experiment presents every three PAL frames: 16.71 fps, with
58968 clocks per render budget. A phase counter selects mixed sine/cosine yaw
and pitch angles, with changing speeds and reversals on both axes. For phase
`p` and `t=2*pi*p/256`, the paths in 256-unit angles are:

```text
yaw   = 2*p + 64*sin(t)   + 32*(cos(3*t)-1)
pitch =   p + 48*sin(2*t) + 24*(cos(5*t)-1)
```

Two 256-byte tables hold only the angles; geometry still runs live. The path
repeats after 256 presentations, about 15.3 seconds. The visible border stays black.

## Verification

```sh
# Requires NumPy and Pillow.
python3 verify.py
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
are reached. Bitmap bytes and both displayed color-screen phases are checked
for every presentation. An independent geometric reconstruction of the twelve
pentagons checks their complete color-cell rectangles, including accepted spill.
Native sprite and gap colors must match the same normalized facing-angle formula.
The exhaustive rotation check also ensures no three faces reach white together.
Koala verification also checks color RAM, sprite-transparent interior selectors,
the measured origin, and exact preservation of artwork outside the circle.
Every presentation checks that the complete opaque rim retains its authored
lighting colors, without sprite or pentagon color bleed.

Screenshots, animation, monitor logs, PRG hashes, source-image hashes, and CPU
measurements are saved under `build/<variant>/verification/`.

Hardware: [Christian Bauer's VIC-II reference](https://www.cebix.net/VIC-Article.txt).
Geometry: [Wolfram MathWorld's truncated icosahedron](https://mathworld.wolfram.com/TruncatedIcosahedron.html).
