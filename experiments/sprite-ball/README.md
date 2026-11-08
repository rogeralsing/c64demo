# Expanded sprite ball proof of concept

A standalone PAL C64 demo using one expanded hires sprite per visible polygon.
The default model contains all twenty hexagons of a truncated icosahedron.
Each frame selects the eight largest visible hexagons. Pentagon-shaped gaps
and any smaller omitted hexagons reveal the supplied background artwork.

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

The active background is `assets/scene.mci`, an unchanged copy of the supplied
`Skarmavbild-.mci`. The 19434-byte uncompressed True Paint image contains two
bitmaps, two screen maps, a shared Color RAM map, and one background color.
The origin manifest records the existing sphere center (160,60) in 320x200
display coordinates and binds that calibration to the source image hash.
The earlier Koala and hires sources remain in `assets/` for reference.

`background.py` exports both fields without modifying their bitmap selectors
or color assignments. No black fill, mask, or additional dithering is applied.
It also accepts Koala input when the manifest selects that source asset.

Every raster IRQ switches VIC banks 0 and 1, their screen maps, and X scroll.
MCI field B is shifted one hires pixel right, matching the source format.
Color RAM is shared and remains unchanged after startup. Each completed sprite
pose is written into matching buffers in both banks, so either field shows the
same geometry. Both pointer tables select the completed pose together.

`$D01B=$00` keeps the hires sprites in front of the background. Sprite positions
remain fixed between geometry updates; their colors alternate normal/darker on
every video frame. Pentagon coloring remains removed: uncovered gaps reveal
the source artwork. Neither bitmap nor either screen's 1000 color cells is
modified while running. The pointer-table bytes change with each new pose.

## Rendering and arithmetic

Each sprite contains 24x21 one-bit pixels in 63 bytes. X/Y expansion displays
these as 48x42 physical pixels. Each face has an independent color.

The camera-facing light uses the rotated face normal, restored from commit
`9e10543`. Brightness uses its Z component, already computed for culling.
The lookup index is `-normalDepth-1`. The sprite ramp is blue (6), purple (4),
pink (10), light gray (15), and white (1), with transitions at indices 6, 12,
18, and 24. A face brightens as it turns toward the camera.

One 128-byte table stores these bands. Lighting reads that table without a
separate light transform or additional products. There are no screen-position
approximations or directional palette changes. Geometry, Z-culling, and vertex
projection retain their existing calculations.

The raster IRQ alternates sprite colors every PAL frame. A newly presented
pose uses its normal front-light colors; the next video frame uses one shade
darker: white becomes light gray, light gray becomes pink, pink becomes purple,
and purple becomes blue. Blue stays blue. The IRQ reads the displayed buffer's
original colors, so the shift never accumulates. Geometry still updates at
25.06 fps; color alternation runs on every 50.12 Hz PAL tick.

Every render clears eight crossing buffers, transforms the visible faces,
draws their XOR boundaries, and prefix-XOR fills the back sprite set. Clearing
and filling are fully unrolled. Each fill consumes 504 marker bytes and
writes two matching 504-byte sprite sets. Crossing buffers
use column-major layout; fill stores convert this to three bytes per sprite row.
Space between sprite rectangles has no clearing or filling cost. Hot scalar
temporaries, metadata, and the small vertex arrays use owned zero-page RAM
while ROM interrupts are disabled. This offsets the extra mirrored writes.

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
| $02..$FD | Owned zero-page metadata, vertex arrays, and render temporaries |
| $0400 | Field A screen colors and sprite pointers |
| $0801 | Initial BASIC loader |
| $0816 | Fill B seventh sprite |
| $0C00 / $0E00 | Two sprite sets in VIC bank zero |
| $1000 | Shared Color RAM source, copied to $D800 |
| $1400 | Front-facing color and darker-shade lookups |
| $1490 | Fill A final sprite |
| $16D0 | Edge-row pointer tables |
| $1800 | CPU-only crossing buffers |
| $1A00 | Unrolled marker clearing |
| $2000 | MCI field A bitmap |
| $4000 | MCI field B bitmap |
| $6000 | Shared-vertex projection |
| $6A00 | Fill B first six sprites |
| $7800 / $7A00 | Matching sprite sets in VIC bank one |
| $7C00 | Field B screen colors and sprite pointers |
| $8000 | Coordinate multiplication tables |
| $9400 | Field A screen-color source |
| $9800 / $9C00 | Edge-curve pointer tables |
| $A000 | Exact edge-crossing samples |
| $CC34 | Fill B final sprite |
| $E000 | Runtime beneath disabled KERNAL ROM |
| $F000 | Fill A first seven sprites, ending before hardware vectors |

In VIC bank zero, sprites in $1000..$1FFF would read character ROM. The display
bank-zero buffers deliberately stay below $1000. Bank one uses RAM at
$7800/$7A00. Assembly guards reject overlaps between code, tables, bitmaps,
sprite buffers, and the hardware vectors.

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
all 129528 sprite bytes against independent rational polygon spans and checks
their matching copies in the other VIC bank, all 11316 edge-table samples, and actual
VIC output against the expected composition. It also checks the ranked face
selection against all twenty hexagons. Eight nonempty sprite buffers
are reached. Both bitmaps, both screen-color maps, and shared Color RAM remain
unchanged for every presentation. Native sprite colors must match an independent
rotated-normal Z calculation and the brightness bands. All five
sprite shades must appear. Every presentation must arrive on the
two-PAL-frame cadence with zero missed deadlines.
Source verification checks the measured origin and exact preservation of both
MCI fields and their shared colors, including the sphere artwork. Intervening
PAL-frame checks verify field B selection, one-pixel X scroll, darker sprite
colors, unchanged geometry, and matching sprite copies. Native screenshots
check both VIC fields against independently decoded source pixels. Every presentation
checks foreground sprite priority; native output must match the expected
foreground composition. Sprites may cover artwork because their priority
places them above the bitmap.

Screenshots, animation, monitor logs, PRG hashes, source-image hashes, and CPU
measurements are saved under `build/<variant>/verification/`.

Hardware: [Christian Bauer's VIC-II reference](https://www.cebix.net/VIC-Article.txt).
Geometry: [Wolfram MathWorld's truncated icosahedron](https://mathworld.wolfram.com/TruncatedIcosahedron.html).
