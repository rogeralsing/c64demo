# Nonconvex vectors and runtime-generated spans

An original runnable counterpart to **Next Level**'s `parts/nonconvex` path.
A rotating square-frame prism has a genuine through-hole, inner walls and
opaque occlusion. The C64 transforms and projects its vertices, culls its
triangles, prepares edges and executes span writers that it generated during
startup. No Next Level code, mesh, artwork or prepared screen poses are included.

```sh
sh build.sh
sh run.sh
python3 verify.py
```

Build/run use the shared Java/KickAssembler and PAL VICE helpers. Verification
also needs Python3/Pillow, the root monitor helper and Colodore palette. Output
is ignored under `build/`. There is no network, sibling repository, downloaded
research input or generated asset dependency after checkout.

## The object and live geometry

The own model has **16 vertices, 32 edges and 16 quad faces**, triangulated into
32 triangles. It is an oriented closed manifold with Euler characteristic 0:
genus 1, rather than a convex cube with a black square painted on its front.
Outer half-size is 22, aperture half-size 10 and half-depth 7.

All 16 vertices undergo live Q6 yaw/pitch rotation and reciprocal-depth
perspective. Reusable sine, quarter-square and reciprocal tables contain
arithmetic, not animation poses. The 64-step motion supplies yaw/pitch scalars;
projected coordinates and all 32 signed determinant culls are calculated on the
C64. The bounded rocking motion avoids near-edge-on quantization folds.

The inner walls draw first, then the outer box's visible side/cap surfaces.
This order is specialized to a box with a rectangular through-hole: an outer
near surface hides any inner-wall portion behind it. It is not a general
painter's algorithm for arbitrary concave meshes. The independent per-pixel
depth oracle validates the complete bounded motion, including exact depth ties
resolved in later-face order.

The display is **64×128 logical multicolor pixels**, or 128×128 physical pixels,
in a 16×16-character window. Two 2KB charsets swap coherently at the top border
only after the next complete image is ready. A small original blue grid remains
visible through the aperture and outside the object.

## Exact edges and generated endpoint cases

The shared [`polygon-edges.asm`](../lib/polygon-edges.asm) is imported unchanged.
Its axes are transposed: its sampled X is this renderer's raster Y, and its
reported crossing Y is the horizontal pixel X. Each triangle prepares exact
`ceil(x(y))` crossings over half-open edge intervals. Left/right arrays collect
the extrema; spans cover `[left,right)`.

At startup, `span-generator.asm` emits **512 endpoint-byte cases** into RAM
`$9000..$B6FF`, plus their 1024 dispatch-pointer bytes. Both charset destinations
have a complete 16×16 table:

| Case | Generated work |
| --- | --- |
| Same byte | Intersect left/right masks and replace only the covered lanes. |
| Positive span | Direct `STA abs,Y` instructions write complete interior bytes; masked fragments preserve both ends. |
| Empty | Return without changing the destination. |

The foreground selects a case from the actual endpoint byte columns. It calls
the emitted code with the current row and face color. Whole span interiors
contain direct stores rather than a per-byte loop. Partial ends preserve
background pixels and earlier faces. The inclusive row loop consumes each
triangle's half-open bottom boundary through an empty writer; other collapsed
spans use the same safe empty case.

Only the mesh, scalar tables and original background are prepared on the host.
Code generation, transforms, culling, edge preparation and span drawing execute
on the C64. The span writers do not contain animation frames.

## Native proof and cadence

The retained verifier first checks the closed oriented topology. Its rational
edge intersections independently construct coverage. A separate per-pixel
perspective-depth calculation chooses the nearest covered triangle; this agrees
with the bounded draw order at every pixel in all 64 poses. It applies to the
actual quantized projected mesh, rather than an ideal unquantized surface.

Normal PAL VICE execution passes **66 publications**, including all 64 poses
and wraparound. It verifies all 9984 generated code bytes and 1024 pointer bytes,
plus 144 native triangle-preparation captures containing 36,864 crossing bytes.
All **40,626 actual endpoint dispatches** match their independent endpoint,
row and color schedules: 5234 empty, 16,423 same-byte and 18,969 positive-span calls.
There are no production test flags or monitor writes to the scene/code/state.

All **135,168 hidden charset bytes** and **6,893,568 full-screenshot pixels**
match. The depth oracle has zero mismatches. Depending on the pose, 6–418
inner-wall pixels are genuinely hidden by nearer surfaces. The transparent
aperture exposes 0–379 logical background pixels; it can close in projection
when the view is sufficiently oblique, while the mesh's through-hole remains.

Startup generation takes **455,308 native clocks**. Publications take **17–19
PAL fields**, averaging 17.7231 fields, about **2.82 updates/second**. Rendering
after geometry preparation takes 289,260–331,146 native clocks, including display
interrupts and VIC stalls. This straightforward exact-edge teaching renderer
makes no claim about the original production's speed. The owned VICE process
exits normally with code 0.

Evidence is in `build/verification/proof.json`, with generated machine code,
dispatch pointers, the complete monitor trace, PNGs and a sampled GIF.
`nonconvex-vectors.gif` uses uniform 160ms sample playback and does not represent
native cadence. A failed rerun invalidates the current success receipt. PAL VICE
8565 output is not a physical-hardware proof.

## Provenance and differences

The mechanism was selected after reading the pinned
[Next Level source survey](../../docs/research/lines-and-vector-fill.md),
[`complex.asm`](https://github.com/bboxy/next-level/blob/57643d53a97cdf38778958d8ebf99341315f834e/parts/nonconvex/complex.asm)
and
[`sierpinsky.asm`](https://github.com/bboxy/next-level/blob/57643d53a97cdf38778958d8ebf99341315f834e/parts/nonconvex/sierpinsky.asm)
from author revision `57643d53a97cdf38778958d8ebf99341315f834e`.
Those establish runtime rotation/culling/edge preparation and generated
same-byte, positive-span and empty fill cases. No third-party source was copied.

The square-frame model, background, exact edge contract, two-buffer generator,
occlusion order, bounded motion, resolution and cadence are our own choices.
This is not the original Sierpinsky/donut mesh or complete demo. The small Q6
product primitive follows our existing examples; the appropriate generic edge
module is reused by import. The root renderer, culling code and shared sampler
were not modified or forked into this experiment.
