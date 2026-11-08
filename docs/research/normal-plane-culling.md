# Normal-based culling: useful primary account, check the printed sign

Andreas Larsson's PDF, signed **JackAsser**,
[Rotation and backface culling for simple demo-like objects](https://codebase.c64.org/lib/exe/fetch.php?media=base%3Arotation_and_backface_culling_for_simple_demo.pdf),
describes forming simple objects and normals by adding rotated basis vectors.
For a fixed camera, it reduces face visibility to a normal-component threshold.
The author says an object bytecode generated unrolled vertex/normal routines in
an unnamed 1991 Booze Design hidden-line part. That historical attribution is
an author account; this study has not recovered that production's executable.

The acquired PDF is 211,856 bytes, SHA-256
`4c6eabf015843c9edd5c9ae002278fac6acc5dd50951d2a1a390bf2a64157465`.
Its creation metadata says 22 May 2013 at 22:05:14 UTC. That is file metadata,
not an independently established publication date. The
[retrieval receipt](../../build/research/3dvibe64-overdraw/primary-culling/retrieval.json)
records the actual download. All three pages were extracted and visually
inspected; the equations below reflect the rendered pages rather than a
potential text-extraction sign error.

## An exact counterexample to the printed example

Pages 2-3 identify the rotated Y basis as a normal to the segment joining
`-X+Y` and `X+Y`, then print the plane equation `Y·p + 1 = 0` and the camera
threshold `Yx < 1/cx`. With the normal and vertices as stated, the sign of
that offset is inconsistent.

The identity orientation suffices to check this without a renderer:

```text
X = (1,0), Y = (0,1)
p0 = -X+Y = (-1,1)
p1 =  X+Y = ( 1,1)

Y·p0 = Y·p1 = 1
Y·p + 1 = 2 at both points, rather than 0.
Y·p - 1 = 0 at both points.
```

For orthonormal rotated axes, the same result follows directly from
`Y·X=0` and `Y·Y=1`. Thus it is not a special rounding or rasterization case.
The statement can also be made consistent with the opposite normal, but then
the visibility inequality must reverse too. A positive distance alone does
not supply the signed plane coefficient.

Our own [rational checker](../../research/3dvibe64-overdraw/normal_plane.py)
tests eight exact unit rotations and both stated endpoints: all 16 printed
plane-incidence checks have residual 2, while the corrected outward convention
has residual 0. With the specified test camera, six of eight printed threshold
decisions disagree with direct outward-normal half-space evaluation. An exact
tangent case checks the strict boundary separately. The
[proof](../../build/research/3dvibe64-overdraw/normal-plane-analysis/normal-plane-proof.json)
contains the rational inputs and results. These are counterexamples to the
printed mathematical example, not findings about the original 1991 code.

## A convention that can be carried into 3D

Define an outward normal `n`, a point `P` on the face, and plane
`n·P=d`. For eye `E`, front-facing means:

```text
n·(E-P) > 0
```

With `E=(0,0,-C)`, `C>0`, this becomes:

```text
-C*n_z - d > 0
n_z < -d/C
```

Rigid rotation about the object's origin preserves its plane distance, so a
fixed object/camera arrangement can precompute that threshold. Transformed
normal Z and an object-specific constant can therefore be enough; testing a
vertex's Z sign is a different operation. Arbitrary object translation,
camera movement, normal reversal and fixed-point scaling require the matching
plane/camera relation. Do not copy a sign or threshold between conventions.

This supplies a principled future alternative to the SDK's observed
rotated-XY tolerance test. It is not yet a culling implementation for the
captured SDK coordinates, proof of all their transforms, or a measured speedup.
The [actual SDK policy](3dvibe64-cull-policy.md) and
[offline omission experiment](3dvibe64-overdraw.md) remain separate evidence.

Passive reproduction uses a new directory:

```sh
rtk proxy python3 research/3dvibe64-overdraw/normal_plane.py \
  --output build/research/3dvibe64-overdraw/normal-plane-replay-NEW
```

Replace `NEW` with an unused suffix. No demo code, CPU model, compiler or
emulator runs in this checker.
