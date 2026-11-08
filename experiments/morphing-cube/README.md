# Morphing patterned cube

This original PAL C64 example morphs and rotates a solid corner-cut cube with
colored triangle markings on its large faces. The C64 constructs its coordinates,
rotates and projects them, culls hidden faces and rasterizes the visible geometry.
It does not replay prepared screen poses or rendered images.

## Build and run

```sh
sh build.sh
sh run.sh
```

Requires the project's existing KickAssembler, Java and PAL VICE installation.
Output is `build/example.prg`. The scene runs automatically without controls.
No downloaded artwork or ignored research inputs are required.

## Live shape and colored face geometry

The body starts with eight cube corners at coordinates ±24. Each corner supplies
three points along its incident edges. A live corner-cut parameter varies from
4 through 14, producing **24 vertices, 36 edges and 14 faces**: six octagons and
eight corner triangles. The C64 recomputes these coordinates each update.

Eighteen additional points define a triangle on each of the six large face
planes. These are explicit 3D color stencils, rather than UV textures. Each
triangle rotates and projects with its parent face. A facing-normal guard
omits markings on shallow faces; the verified motion displays one to three
markings in every pose.

The 64-step scene makes a complete yaw revolution while pitching and changing
the corner cut. Stored motion values are scalar pitch/cut controls. Reusable
sine, quarter-square and depth-factor tables support live arithmetic; they are
not projected vertex or framebuffer poses. Camera distance is 144, with focal
factor 96 and Q6 rotation coefficients. Horizontal multicolor pixels are twice
as wide as physical rows, so the vertical projection doubles its scale.

## Visibility, boundaries and display

The renderer sums exact signed projected triangle areas across each polygon
fan to choose its visible faces. Convex supporting planes, disjoint visible
coverage and contained stencil coverage are checked independently for all
64 authored poses. No depth buffer or general intersecting-object visibility
algorithm is claimed.

Visible face perimeters feed the shared exact half-open boundary sampler.
Adjacent contributions combine by XOR in a 2 KB packed marker plane. Stencil
boundaries contribute the parent color XOR the marking color. A vertical
prefix pass reconstructs opaque colors in a complete hidden 2 KB charset.

The 64 × 128 logical canvas occupies a 128 × 128 physical region. Two RAM
charsets alternate through `$D018`, with publication in the top border after
rendering completes. The screen matrix remains fixed. Outside the canvas,
black hires text attributes keep the unused screen area black.

This readable callback-based renderer takes **8–10 PAL fields per update** in
the measured scene, averaging 9.12 fields, or about **5.5 updates/s**. It trades
speed for a small shared exact sampler, complete polygon culling and full
buffer output. It does not claim Tower Power's rendering performance.

## Native verification

```sh
sh build.sh
python3 verify.py
```

Verification needs Python 3 with Pillow and the existing PAL VICE executable.
Set `VICE` to override its path. The verifier starts and closes its own emulator;
fixed-output success is invalidated before a new attempt.

Verified on 8 November 2026 over **66 native presentations**, covering all
64 moving poses and buffer wraparound. An independent formula matches all
126 live model bytes, 126 rotated-coordinate bytes, 84 projected-coordinate
bytes, fourteen visibility flags and six stencil flags per presentation.
All 2,048 output charset bytes and all 2,048 boundary-marker bytes match in
both physical buffers. Expected coverage comes from rational intersections
and direct opaque color assignment, without replaying the line sampler.

Nine complete VICE screenshots match their independently composed images:
**940,032 native pixels, zero mismatches**. These include the maximum and minimum
corner cuts. The fixed-point geometry differs from ideal floating-point geometry
by at most 4.70 physical pixels over this motion. Both comparisons have distinct
roles: exact integer matching checks the declared renderer; floating point
provides a separate geometric sanity bound.

Complete RAM captures, images, measured presentation clocks, command and program
hash are retained under ignored `build/verification/` beside `proof.json`.
`morphing-cube.gif` contains sampled views rather than real-time playback.
The owned emulator exited normally. Arbitrary angles, camera changes, physical
VIC-II revisions and NTSC remain outside this bounded proof.

## Relationship to Tower Power F1

See [the F1 investigation](../../docs/research/tower-power-f1.md). The original
captured model has 24 body vertices, 26 faces and fifteen coplanar pattern points.
This example has a different topology and eighteen marking points. It retains
the useful combination of live morphing, rotation, perspective, culling and
face-local colored geometry without claiming to recover the original model
or reproduce its release bytes, assets, palette or loader.
