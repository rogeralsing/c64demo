# Keep camera planes, projected areas and raster coverage separate

Two recovered primary readings describe different culling formulations:

- Bitbreaker's [Codebase64 article](https://codebase64.c64.org/doku.php?id=base%3Abackface_culling)
  computes a signed area from vertices already in 2D. Its particular expression
  is the negative of the usual `(P1-P0)×(P2-P0)` scalar cross. Winding and the
  screen-Y convention therefore matter when copying its comparison. The same
  page links JackAsser's separate normal-based PDF; those are not one kernel.
- The acquired page of
  [Vector visibility - Z axis solution](https://csdb.dk/forums/?firstpost=21&roomid=11&topicid=49250)
  develops a fixed-eye plane test. Its plane coefficient `D=-1` and intermediate
  expression `C*(-3)-1>0` are consistent, but the later `C>e`, `e=-1/3`, is not
  equivalent: division by a negative number reverses the inequality. At `C=0`,
  the plane expression is `-1`, whereas that final comparison accepts. This
  concerns the printed shorthand on the acquired page, not an executable or
  every reply in the thread.

Both HTML bodies and HTTP/hash receipts are retained under
`build/research/3dvibe64-camera/primary-reading/`. Neither was executed. The
earlier [PDF example check](normal-plane-culling.md) is a separate acquisition
and mathematical counterexample.

## Exact projection reference

For camera-space points with positive depth, outward triangle normal
`N=(P1-P0)×(P2-P0)` and eye at the origin, define `S=N·(-P0)`.
An ideal perspective projection, with screen Y directed downward, obeys:

```text
Q_i = (x_i/z_i, -y_i/z_i)
area(Q0,Q1,Q2) = S / (z0*z1*z2)
```

This follows by expanding the determinant. Positive focal scaling and screen
translation do not change the sign. It is an exact mathematical identity,
not an assumption that integer lookup-table projection must preserve it.

Our [reference checker](../../research/3dvibe64-camera/source_geometry.py)
uses exact rational coordinates for all **120 triangles** in the 15 captured
windows. Every depth is positive and every identity holds. Those windows
contain **13 distinct 3D point clouds**: the old first/third clouds repeat in
new poses 01/03. A separate 729-case integer grid confirms the Codebase64
expression's sign convention. Three simple normal-Z cases expose the forum's
printed final-inequality mismatch. The
[proof](../../build/research/3dvibe64-camera/source-geometry-analysis/source-geometry-proof.json)
pins both primary bodies and the accepted camera-study inputs.

## What the two native-buffer counterexamples actually establish

The [camera experiment](3dvibe64-camera.md) keeps the correct signed-plane
convention but fails to preserve two native buffers. For pose 09, face 3 has
negative geometric `S` while its valid captured `(sx,syQ2)` area is **+192**.
The exact-projection identity and that integer projected triangle have opposite
winding. Projection approximation and coordinate quantization are therefore
material; this observation does not isolate one rounding instruction or only
the 32-depth bucket table as the unique cause.

Pose 10 is different. Face 5 has negative `S` and captured projected area
**-600**, yet removing its existing thin spans changes 144 decoded pixels.
Thus replacing the camera test with a projected-area sign test alone would
not establish exact compatibility with the current raster coverage either.

The full scalar reference still matches all native buffers. The strict
camera-plane classifier remains **rejected for image preservation**. This
reference pass neither repairs that classifier nor establishes a speedup.
Next isolate the actual integer coverage/occlusion near the two failing faces
before selecting another culling or overdraw rule; do not fit a tolerance to
these two examples and call it general.

Passive reproduction, using a new directory:

```sh
rtk proxy python3 research/3dvibe64-camera/source_geometry.py \
  --output build/research/3dvibe64-camera/source-geometry-replay-NEW
```

Replace `NEW` with an unused suffix. No CPU model, SDK, renderer, compiler or
emulator runs in this reference checker.
