# Runtime UV-textured cube

This original standalone PAL C64 example rotates a cube with animated
plasma-like textures on its faces. It is our implementation of the visual
idea described for Second Reality’s texture-cube part. Its
[specialized original BA/BB renderer](../../docs/research/second-reality-cube.md)
uses prepared projected poses and a single-coordinate stripe shader. Our
example instead uses live projection and general two-coordinate UV sampling. No original demo code, texture artwork or
animation frames are included.

```sh
cd experiments/textured-cube
sh build.sh
python3 verify.py
sh run.sh
```

From the repository root, the shared build runner discovers it as
`experiment:textured-cube`.

## One textured face

A second build keeps the same live geometry, camera, motion and 4×4 display,
but textures only the fixed near-Z face (face 4, visible at the first pose).
The other five faces use solid colors: blue on X faces, cyan on Y faces,
and white on the remaining Z face. Flat triangles skip UV-gradient division
and texture sampling, and fill their packed screen spans directly.

```sh
sh build.sh one-face
python3 verify.py --variant one-face
sh run.sh one-face
```

The tiny `one-face/main.asm` entry imports the same renderer with `ONE_FACE`
defined. Its PRG and symbols live in `one-face/build/`; its native evidence
lives in `build/verification-one-face/`. The default all-textured build and
animation remain separate. Its PRG remains byte-identical to the retained
`aec5c439…` baseline.

| Variant | Mean updates/s | PAL fields/update |
| --- | ---: | --- |
| Six textured faces | 5.23 | 7–11 |
| One textured face, five solid faces | 8.67 | 4–8 |

This is **65.7% faster** over the measured cycle. The fixed textured face is
visible in 28 of the 64 authored poses; measured jobs average **6.99 updates/s
when visible** and **10.74 when hidden**. A hidden textured face leaves a
fully solid cube, so the average includes that cheaper half of the turn.
The texture itself is still rebuilt each pose; this isolates the gain from
cheaper face rendering.

The [one-face native proof](build/verification-one-face/proof.json) passes
66 presentations, all 64 poses and wraparound, all 264,000 decoded screen
samples and 65 complete native screenshots. Its full-cycle animation uses
measured per-pose display durations, including the different speeds when
the textured face turns away:

![One textured face at measured speed](build/verification-one-face/textured-cube.gif)

## Orthographic experiment

The [orthographic competition](ortho/README.md) compared exact spans, cached
tiles and row/column lookups. The selected lookup sampler reaches about
**8.31 updates/s**, with Q10 runtime yaw, pitch and Z roll that preserve the
cube's shape. Native length error stays below 0.01%; projected corners round
only at the final raster step. Z roll adds a complete turn to the existing
64-pose yaw/pitch loop; the yaw/pitch-only predecessor reached 9.64 updates/s.
The sampler's maximum one-texel approximation is
relative to its declared Q8 UV plane. The tile-cache candidate was slower
in the initial competition.

```sh
sh build.sh ortho
python3 verify-ortho.py
sh run.sh ortho
```

## Hybrid with the real XOR filler

The [XOR hybrid](xor-hybrid/README.md) uses the existing `src/xor-fill.asm`
to draw the opaque cube, then replaces the fixed textured face's pixels in
the same hidden charset. Its output uses the solid renderer's finer **2×1
physical-pixel samples** in a **128×128 physical window**. The source texture
remains 16×16, and yaw, pitch and roll still run on the C64.

The raw XOR-filled face supplies the texture mask, so both passes share the
filler's exact boundary ownership. Masked replacement also allows black
texels to overwrite the solid face color.

```sh
sh build.sh xor-hybrid
python3 xor-hybrid/verify.py
sh run.sh xor-hybrid
```

## Texture inside the XOR pass

The [texel-transition variant](xor-texels/README.md) builds texture start,
stop and color-change markers before the real prefix pass. One `xorFill`
therefore creates the complete textured cube; no pixel overlay follows it.
Three competing techniques preserve the preceding hybrid's exact image.
The selected shared row-event implementation reaches **8.01 updates/s**,
compared with **7.26** for pixel replacement after filling.

```sh
sh build.sh xor-texels
python3 xor-texels/verify.py
sh run.sh xor-texels
```

## Geometry and texture mapping

The default and `one-face` builds rotate all eight cube vertices and project
them with perspective on every update. The cube has six opaque faces. Backface culling uses signed
projected area; each accepted face is split into two UV-mapped triangles.

The C64 regenerates the two-dimensional 16×16 texture for every pose. With
`wave(t) = round(16 + 15 sin(2πt/256))` and coordinates/phase `u`, `v`, `p`,
the source selector is:

```text
(wave(16u + 4p) + wave(16v - 8p) + wave(8(u + v) + 4p)) >> 3 & 3
```

Wave indices wrap modulo 256. The fixed wave table contains scalar sine
values, not image frames. Each update caches 16 horizontal, 16 vertical and
32 diagonal wave values, then builds the 256 texels and three shifted
copies for the packed screen lanes. The runtime source image is 256 bytes; motion changes
both its source pattern and the cube’s orientation.

The mapper samples this texture at live interpolated UV coordinates. Texture coordinates are
affine within each projected triangle, with signed Q8 gradients and a
half-open top-left coverage rule. This is actual image sampling on the
surfaces, rather than additional colored polygons. The UV interpolation is
affine, so perspective distortion and the diagonal between a face’s two
triangles can become visible. Perspective-correct UV interpolation is not
claimed.

The model is a cube with coordinates ±24. A 64-update cycle drives yaw and
pitch from scalar sine coefficients. The C64 calculates the vertex products,
projection and UV gradients at runtime. The yaw is `4p + 1` in 256-angle
units; pitch is `round(24 sin(2πp/64 + 0.4))`. Projection uses a camera
distance of 160 and focal length of 80 logical samples, centered at `(40,25)`.
The Q6 products use quarter-square lookup arithmetic. No vertex-pose tables or rendered
animation frames are stored.

## Display

The logical canvas is 80×50 samples. Each sample occupies a 4×4 physical-pixel
square, filling the ordinary 320×200 character viewport. A fixed 256-glyph
multicolor charset encodes all combinations of four two-bit selectors in
one 8×8 character. The colors are black, blue, cyan and white.

Two screen matrices share the charset. Exact scanline spans write the
two-bit samples directly into the cleared hidden matrix. There is no
intermediate sample canvas or full-screen packing pass. Only a complete
image can become visible at the next top border. The VIC continues to display the current complete image while the
next one is calculated.

The charset is at `$2000`, the two screen matrices at `$0400/$0C00`, and
the live texture plus its shifted copies at `$5000–$53FF`. Code and scalar
lookup tables occupy `$6000–$7223`. The ordinary `$0801` BASIC entry
starts that renderer; neither screen matrix overlaps the entry or code.

## Validation

`verify.py` launches its own normal-speed PAL VICE instance. It checks the
runtime texture, projected geometry, visible faces and all 4,000 samples
decoded from the real packed screen against an independent mathematical reference, and compares
complete native screenshots. Its generated outputs remain beneath
`build/verification/` and are ignored by Git.

The [native proof](build/verification/proof.json) passes **66 presentations**:
all 64 moving poses and wraparound. It compares all **264,000 live UV
samples**, all 66 complete packed matrices, all runtime textures and
**65 complete 384×272 native screenshots**. All 256 texture addresses are
exercised, and all 64 source texture images differ. The eight rotated and
projected vertices and six visibility flags match for every pose.

Publication takes **7–11 PAL fields per update**, averaging **5.23 updates
per second**. VIC scanout continues at about 50 fields per second. Exact
scanline spans, direct packed writes, factored plasma construction, exact
quarter-square area products and shorter gradient division make this
**3.63× faster** than the first 1.44-update/s version. All three measured
versions pass the same pixel oracle. Archived programs, sources, profiles
and native proofs are beneath `build/profiling/`.

The remaining update rate is visibly choppy. This is still a reference
renderer. Its algorithm and timing differ from the original BA/BB effect;
see the [original cube analysis](../../docs/research/second-reality-cube.md).
Affine UV mapping and coarse geometry quantization also remain visible
limitations. Physical hardware and analog CRT output were
not checked.

The shared build runner also passes its focused
[`experiment:textured-cube` build](../../build/examples/20261108T115625.345417Z/receipt.json).
The rebuilt PRG is byte-identical to the native-verified program:

```text
SHA-256 aec5c439bd353d3eaca4c60a0ff4366d453c00ea1d9b23d17f417f34e6da5a38
```

The animation retains the measured hold time of each pose, rounded to GIF’s
10 ms time unit. Its full 64-pose loop takes about 12.30 seconds.

![Native textured cube at measured speed](build/verification/textured-cube.gif)
