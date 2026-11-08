# Second Reality: the original BA/BB texture cube

The original rotating texture cube is **BA/BB on side two**. It combines
prepared projected geometry with live edge interpolation and texture drawing.
This is a different rendering design from our general affine-triangle example.
The [original production and disk identity](second-reality.md) are unchanged.

## The actual original cube

The native continuation reaches the original `$4000` BA entry, prepares its
renderer and displays the cube. This full-size native capture identifies the
part independently of its filename:

![Original cube](../../build/research/second-reality/native-cube-20261108T123508Z/ba-visible-100.png)

The captured cube is 180×168 physical pixels in this pose. Its
geometry scale-table pointer is `$3B00`, the identity scale, so this is not
the small cube during the introductory zoom.

The original file identities are:

| File | Load address | Payload bytes | SHA-256 |
| --- | --- | ---: | --- |
| `side2-entry05-BA.prg` | `$4000` | 4,080 | `fdc325fc558f9fe9e40fd909b166b98f1acec19de20c7f6ceb7af1c790fcb846` |
| `side2-entry06-BB.prg` | `$7000` | 12,288 | `3b84919d607a072c1990f43be657017f1240be46a537a29b3046e05ecbe1d7ce` |

## Rotation, projection and visibility are stored

BB's first 4 KiB are copied from `$7000..$7FFF` to `$3000..$3FFF` before BA
runs. They include eight vertex tables. For vertex `i`, the 128 projected X
coordinates begin at `$3000 + 256*i`; the 128 Y coordinates immediately
follow at `+128`. These are screen-coordinate values in `0..48`, not 3D
object coordinates waiting for a rotation matrix.

Another 128 bytes at `$3800..$387F` contain face-visibility masks. The `$3880`
consumer selects faces from these stored bits. It does not calculate normals
or signed projected areas to decide which face is visible. Its five authored
face paths are:

| Mask bit | Vertex indices |
| --- | --- |
| `$01` | `0,1,2,3` |
| `$10` | `0,1,5,4` |
| `$08` | `1,2,6,5` |
| `$20` | `2,3,7,6` |
| `$04` | `0,3,7,4` |

The phase advances with `(phase - 1) & 127`. The sixth cube face has no draw
call in this restricted authored motion path.

The `$3A00` coordinate consumer applies a live zoom lookup through pointer
`$08/$09`, and adds a live vertical offset from `$04`. There are eleven
50-byte scale tables at `$3B00`; the base table is the identity `0..49`.
Those operations move and scale the stored poses. They do not perform a
runtime 3D rotation or perspective divide.

A diagnostic drawing of eight stored poses follows. These flat colors are
for inspection; this is not original native output or its texture renderer:

![Stored projected poses](../../build/research/second-reality/cube-source-inspection/bb-stored-projections.png)

The passive [geometry checker](../../research/second-reality/cube_geometry.py)
pins both original files and compares all 2,726 bytes of poses, visibility
and zoom tables against the captured native RAM. At BA entry it also compares
all 4,080 original BA bytes. The later code legitimately self-modifies.

```sh
rtk proxy python3 research/second-reality/cube_geometry.py
```

Its [receipt](../../build/research/second-reality/cube-geometry/proof.json)
contains the original hashes, decoded poses and all native-file comparisons.
This check executes no CPU and does not claim whole-machine equivalence.

## A 16-color 4×4 display

The cube uses multicolor bitmap mode with a fixed bitmap pattern `$5A`:
`01,01,10,10`. The high and low nibbles of a screen byte therefore provide
two independent colors, each four physical pixels wide. The bitmap is the
pixel-selector mask; screen bytes carry the changing colors.

The raster code forces another screen-matrix fetch halfway through each
8-line character row. That supplies a new pair of colors every four lines,
giving 4×4 physical-pixel samples with all 16 C64 colors. This differs from
our example's four-color, fixed 256-glyph character encoding.

Two pairs of matrices provide the rendering buffers. Descriptors `$08/$18`
display `$C000/$C400` while the renderer writes `$C800/$CC00`; `$28/$38`
reverse those roles. The IRQ applies the descriptor at its actual `$D018`
stores. The main loop does not wait for the top border before changing its
descriptor, so a logical render interval is not automatically an atomic
whole-frame presentation interval.

## Generated packed texture spans

During preparation, `$410D` builds unrolled sampling chains at `$5000/$5200`.
Their repeated operation is:

```text
LDA high-color-plane,X
ORA low-color-plane,X
STA (screen-pointer),Y
INY
```

One store emits two independent four-pixel-wide colors. Triangle setup
prepares the source offsets; the span can then use indexed lookup operands
instead of updating two full fixed-point UV coordinates for every texel.
The mapped colors are written directly, without a second glyph-packing pass.

## The apparent plasma is a specialized stripe shader

The original does not rebuild or sample a general 16×16 color image. Three
32-byte palettes at `$4400/$4420/$4440` define colored stripes. Preparation
expands them into high/low-nibble lookup families at `$6000/$6200`,
`$6400/$6600` and `$6800/$6A00`.

Triangle setup prepares the column contribution as source-offset operands.
For each row, the renderer combines an interpolated edge attribute with a
wave displacement. The generated sample is an indexed palette lookup:

```text
index = (prepared_column_offset + row_attribute + row_wave) mod 256
packed_pair = high_nibble_palette[index_left] OR low_nibble_palette[index_right]
```

This is one scalar stripe/shade coordinate over the face. It is not two
independent image coordinates U and V. `$4AC0` updates 50 row displacements
from the periodic table at `$4D00`, advancing its phase by two. The lookup
palettes remain prepared data; the row-wave update makes their stripes move.

## Bounded original drawing proof

The [sampler checker](../../research/second-reality/inspect_cube.py) compares
file-derived generated code and one complete original `$3880` draw against
the native captures. Its independent indexed span model checks 111 spans,
1,110 covered 4×4 samples and 609 ordered packed stores. The complete
4,096-byte `$C000..$CFFF` output matches native RAM. All four endpoint-parity
combinations are exercised.

The original CPU execution takes 47,342 nominal cycles for this draw. The
native interval takes 72,666 PAL machine clocks, including display DMA and
interrupts. CPU registers agree at the endpoint. The checker retains 36
other physical-RAM differences from IRQ/music activity, so this is an exact
output-domain proof, not a whole-machine equivalence claim. A separate
one-pixel span matches all physical RAM and CPU registers in 100 cycles.

```sh
rtk proxy build/research/tower-power/cpu-venv/bin/python research/second-reality/inspect_cube.py --capture build/research/second-reality/native-cube-20261108T123508Z --output build/research/second-reality/cube-analysis-20261108-ba-sampler
```

The [sampler receipt](../../build/research/second-reality/cube-analysis-20261108-ba-sampler/cube-proof.json)
pins the source and capture hashes, comparisons and limits.

## Measured update cadence

At the full-size identity zoom `$3B00`, the first 32 alternating descriptor
stores at `$4F87/$4FA4` provide 31 intervals of **52,449–108,385 PAL clocks**.
Their mean is **85,825.90 clocks**, or **11.48 update selections per second**
at the PAL CPU clock. This is a bounded, pose-dependent measurement, not a
constant rate for the whole production. A shorter segment has a higher mean.

These descriptors can change partway through the visible picture. They are
therefore not an atomic, top-border frame-publication contract like our
example's. The IRQ's actual `$D018` stores apply the selected matrix pair.
The distinction matters when interpreting this number as visual FPS.

The [cadence evidence](../../build/research/second-reality/native-cube-20261108T124731Z/steady-descriptor-evidence.json)
retains the exact PC, A and clock observations. The first trace session
missed its intended raster breakpoint; its requested 160-field capture is
explicitly unsuccessful. Its early descriptor observations remain usable:
the first 14 PC/A/clock triples match the subsequent successful field capture
exactly. No failed image capture is promoted to a successful one.

The [successful native capture](../../build/research/second-reality/native-cube-20261108T125156Z/native-cube-evidence.json)
contains **48 consecutive PAL fields**, each separated by exactly 19,656
clocks after accounting for its recorded beam position. The fields retain
normal 100% speed with warp disabled and the original SID code running.
The last-IRQ captures occur after the visible content, at raster 265–272.

![Original cube, 48 native PAL fields](../../build/research/second-reality/native-cube-20261108T125156Z/original-cube-fields.gif)

Across the four closed original capture sessions, the passive audit checks
98 full RAM/snapshot pairs, including CPU and beam agreement. C64 CPU, RAM,
CIA and VIC state restore exactly. Drive and extended SID-state differences
are retained explicitly; no whole-machine restore identity or independent
full-VIC pixel oracle is claimed. Every owned VICE process was reaped.

The [capture/audit helper](../../research/second-reality/native_cube.py)
starts no emulator in `audit` mode:

```sh
rtk proxy python3 research/second-reality/native_cube.py audit build/research/second-reality/native-cube-20261108T125156Z
```

## Difference from our example

| Work | Original BA/BB | Our example |
| --- | --- | --- |
| Geometry | 128 stored projected poses and visibility masks; live zoom/translation | Live rotation, perspective projection and area culling |
| Surface pattern | One interpolated stripe coordinate plus a live row wave; three palettes | Two UV coordinates sampling a rebuilt 16×16 image |
| Span samples | Prepared operands and unrolled indexed high/low palette loads; two colors per store | Per-texel fixed-point U/V stepping and packed-lane merging |
| Display | 16 colors, fixed bitmap selector mask and 4-line screen-matrix fetches | Four colors through a fixed 256-glyph character set |

In our latest measured renderer, drawing consumes 78.6% of the total time;
live geometry consumes 3.5%. The specialized packed sampler is the main
architectural saving; stored geometry provides another saving. The original
still interpolates edges and draws the textured faces live. Its stored poses
are geometry inputs, not completed movie frames.

This note separates the cube from other parts: EC's two-plane texture effect,
YB's picture warp, ZZ/ZY's reflective scene and WC/WD's prepared animation
are not evidence of the cube's rendering algorithm.
