# Patterned vectors on an expanded-sprite canvas

An original counterpart of The Lab's sprite-vector stage. Six hardware sprites
across and three reused bands form one **144×63 logical-sample canvas**, expanded
to **288×126 physical pixels**. Prepared projected triangles and span runs are
rasterized into that canvas by the C64. Polygons cross sprite columns and band
seams; the sprites are storage/display tiles of the shared plane.

```sh
sh build.sh
sh run.sh
python3 verify.py
```

The shared builder writes `build/example.prg`. The launcher uses PAL at normal
speed. The example uses the installed Kick Assembler, VICE, Python and Pillow;
it installs no dependencies.

## Geometry and density materials

Each of sixteen prepared poses contains two screen-space triangle records:

```text
apexX, topY, bottomLeftX, bottomY, bottomRightX, material
```

These are bounded flat-bottom triangles with the apex between the two bottom
X coordinates. Runtime integer-error stepping computes exact rational edge
crossings. A row includes integer samples satisfying:

```text
topY <= y < bottomY
leftIntersection(y) <= x < rightIntersection(y)
```

The left endpoint rounds up; the right endpoint is exclusive. Partial endpoint
bytes receive combined masks, and complete interior bytes receive the material
pattern. Rendering ORs covered pattern bits into a cleared back buffer, giving
a union of the one-bit patterned shapes. It does not provide opaque polygon
overwriting or geometric depth sorting.

Separate five-byte span-run packets provide sixteen small density swatches:
inclusive left, exclusive right, starting Y, height and material. Their rows
use the same runtime span writer as the triangles. A 4×4 Bayer rank pattern,
repeated horizontally, supplies sixteen thresholds: material 0 is empty,
material 8 is 50% checker and material 15 is 15/16 coverage.

Only vertices, scalar material indices, span commands and small address/mask
tables are prepared. There are no stored animation bitmaps. Rotation/projection
and arbitrary triangle clipping are not runtime features of this counterpart;
the sixteen poses are already projected and remain inside the canvas.

## Canvas, display and publication

Each buffer contains eighteen 64-byte sprite records: **1,152 bytes**, including
eighteen unused padding bytes. Logical pixel `(x,y)` selects its byte at:

```text
buffer + floor(y/21)*384 + floor(x/24)*64
       + (y mod 21)*3 + floor((x mod 24)/8)
```

Buffer A occupies `$2000..$247F`; buffer B occupies `$2800..$2C7F`. Both X and Y
expansion are enabled for all six hires sprites. Their programmed Y positions
are 64, 106 and 148, giving three consecutive 42-line physical bands.

Each buffer has three immutable pointer matrices. A uses screens `$0400`,
`$0800`, `$0C00`; B uses `$3000`, `$3400`, `$3C00`. These addresses keep pointer
fetches outside the VIC's `$1000..$1FFF` character-ROM window. Blank character
data and black background colors leave the visible image to the sprites.

The raster IRQ selects the appropriate matrix atomically through `$D018`, with
band transitions at raster lines 106 and 148. Y positions are set earlier while
the preceding band is still drawing. Main-thread rendering continues between
these display jobs. A ready flag publishes a complete back buffer and its pose
only in the top-border IRQ; all three bands of a field use the same front buffer.

## Native verification

The checked run passed **224 PAL fields**, including **32 publications** after
the initial pose. It covers all sixteen poses twice. An independent oracle
uses integer half-plane inequalities and Bayer thresholds; it does not replay
the runtime DDA or read captured pixels to produce expectations.

- All 1,152 front-buffer bytes match on every field, including clear regions and
  sprite padding. Thirty-one ready hidden buffers also match before publication.
- Thirty-three complete native screenshots match the expected expanded canvas,
  including both band seams and surrounding black pixels.
- Actual traces match 669 `$D018` selections and 4,014 sprite-Y stores, with the
  selected pointer matrix consistent with the published buffer for every band.

The first update takes six PAL fields; subsequent updates take **seven fields**,
about **7.2 scene updates per second**. The sprite display itself refreshes each
PAL field. These figures describe this readable loop-based implementation,
without assigning them to the investigated production.

Generated [receipt](build/verification/receipt.json),
[monitor transcript](build/verification/monitor.log) and
[animation](build/verification/sprite-vectors.gif) remain under ignored `build/`.
Verification closes only its owned emulator. Physical-hardware timing,
arbitrary prepared meshes, the original 164-pose controller and its border-open
192×147 logical canvas remain outside this smaller example's scope.

See [The Lab sprite-vector investigation](../../docs/research/the-lab-sprite-vectors.md)
for the separately established original stage. This folder contains original
code, geometry packets and pattern artwork.
