# Minimal Mode 6 Gouraud scene

[`research/3dvibe64-native/scene.json`](../../research/3dvibe64-native/scene.json)
defines one smooth octahedron: six vertices, eight outward triangles, a fixed
camera and a fixed point light. The object rotates slowly, so its lighting
field should change with its orientation while the Bayer phase stays anchored
to the screen. This file is newly authored input for the pinned SDK, not a
scene recovered from the author's unavailable examples.

Scene identity: **1,104 bytes**, SHA-256
`2dc0c5d4a8bab84ae522a31da6b7e998e346cce1dd0ffe6693ab01990ca6f72a`.
The independent input derivation is retained as
`build/research/3dvibe64-native/scene-review/input-proof.json`. No SDK script,
validator, assembler, generated program or emulator was run by this scene
authoring lane. Actual build and runtime outcomes require separate evidence.

## Pinned SDK and supported input shape

Use [SDK revision b19df459b7efe50d514b59fe876c0bc7c326c5b4](https://github.com/Librologica/3Dvibe64/tree/b19df459b7efe50d514b59fe876c0bc7c326c5b4),
the retained 1.15.1 source SDK. Its source tar SHA-256 is
`fbccc522110b1fe4beb85ba1378183f70b5d8fc76227c2482306cd5354b4c998`;
the retained `work/build-3Dvibe64.ps1` SHA-256 is
`b03d5d7ce6e9e5af85d47c04950841da96f1f3e6dc7b50f5c26a1f97c5bb7e70`.
The [earlier source audit](3dvibe64.md) records acquisition and arithmetic
evidence. Preserve that frozen SDK and build in a fresh complete copy.

This is schema **1**, with an `objects` array and an inline object of
`type: "mesh"`, `geometry: "solid"`. The supported importer consumes its
`vertices`, `faces` and `gouraud.creaseAngle`; there is no octahedron builtin
or special octahedron constructor. Explicit `axisConvention: "engine-y-up"`
keeps scene vectors and raw local mesh axes in the same order: X right, Y up,
Z depth. It avoids the documented distinction between public world-Z-up
scene-vector conversion and unconverted raw mesh vertices.

Relevant pinned builder locations:

| Concern | Lines |
|---|---:|
| Scene schema, camera/light import and object list | 3531–3557 |
| Inline solid source dispatch | 3494–3496 |
| Vertex/triangle importer | 3027–3108 |
| Crease validation | 919–935 |
| Area-weighted shade normals and deduplication | 2704–2788 |
| Scene object pose/velocity/scale import | 3658–3667 |
| Static-light input and ranges | 1124–1215 |
| Fixed-camera choice and validation | 3897–3934 |
| Source-dependent center-dot generation | 7915–7926, 7956–7967 |
| Runtime object-space light and Gouraud target | 13184–13354 |

## Exact geometry and smooth-normal expectations

The local vertices are:

| Index | Position | Expected Q6 smooth normal |
|---:|---|---|
| 0 | `(28,0,0)` | `(63,0,0)` |
| 1 | `(-28,0,0)` | `(-63,0,0)` |
| 2 | `(0,28,0)` | `(0,63,0)` |
| 3 | `(0,-28,0)` | `(0,-63,0)` |
| 4 | `(0,0,28)` | `(0,0,63)` |
| 5 | `(0,0,-28)` | `(0,0,-63)` |

Every face has one signed X, Y and Z endpoint. Its ordinary cross product and
the source's Newell normal both give components `±784`, with positive dot
product against its local centroid. Thus every face winds outward. All 12
edges have exactly two uses in opposite directions; `V−E+F=2`, and the signed
volume is `87808/3`. These checks are independent integer geometry, not a
runtime culling test.

Four equal-area faces meet at every vertex. With crease angle 180° all four
normals participate; their sum points along the vertex's axis. The builder
therefore needs **six shade vertices**, without hard-edge splits. Source
first-use order predicts `gouraud_geom_vertex = [0,5,2,1,3,4]`. Expected normal
byte arrays in that order are:

```text
X: 3f 00 00 c1 00 00
Y: 00 00 3f 00 c1 00
Z: 00 c1 00 00 00 3f
```

The eight face-to-shade rows, including the triangle's duplicated final slot,
should be:

```text
0 1 2 2    2 1 3 3    3 1 4 4    4 1 0 0
0 2 5 5    2 3 5 5    3 4 5 5    4 0 5 5
```

These are emitted-data expectations to compare with the actual generated ASM
and PRG. They do not claim that a particular build has already emitted them.

## Pose, point light and genuine shade variation

Camera position/rotation are zero and camera mode is fixed. The object starts
at `(0,0,128)`, identity rotation and scale 1 (`scale64=64`). Its initial
camera-space geometric depth range is 100..156, comfortably in front of the near plane.
Angular velocity is `(0.25,0.375,0.125)` turn units per simulation tick, encoded
as Q8 increments `(64,96,32)`. Position remains fixed. Simulation ticks must
not be confused with completed rendered frames or measured FPS.

The scene light is `type: "static", mode: "static"`, position `(-96,80,16)`,
intensity 10 and no pulse. This selects the supported fixed runtime sample;
it keeps the world-space point stationary rather than freezing object-derived
shading. Its initial light relative to the object center is `(-96,80,-112)`,
all representable signed-byte components without subtraction overflow.

The SDK's Gouraud center term uses **half the local vertex coordinates**. For
this radius and unit scale it is `63×14=882=$0372` for all six shade vertices.
Thus expected center-dot arrays are six `$72` lows and six `$03` highs.
Using 1,764 here would miss that explicit half-coordinate preparation.

At an exact identity Q6 matrix, the independently derived source arithmetic is:

| Geometry vertex | `normal·light − 882` | Nonnegative dot high byte | Target shade |
|---:|---:|---:|---:|
| 0 | −6,930 | dark | 0 |
| 1 | 5,166 | 20 | 27 |
| 2 | 4,158 | 16 | 21 |
| 3 | −5,922 | dark | 0 |
| 4 | −7,938 | dark | 0 |
| 5 | 6,174 | 24 | 32 |

The target uses `min(32, round(2×dotHi×10/15))`, matching the pinned intensity
table arithmetic. In shade-emission order the targets are `[0,32,21,27,0,0]`.
The four initially camera-facing triangles therefore contain differing corner
shades, including values on both sides of Bayer level 16. A uniform flat-face
pattern would not satisfy these expectations.

This is conditional input/source arithmetic. Simulation can advance before the
first displayed frame; actual fractional angles, transformed light and the
`$FF` first-sample/slew state must be captured before asserting native values.
The native renderer's quantized point-light approximation is not claimed to
be physically accurate photometry.

## Palette choice matters

The object uses gray **reflectivity 1**, whose pinned material table specifies
dark 11, high 15 and highlight 1: three distinct gray/white pigments. Expected
screen byte is `$BF`, and Color RAM is 1. With black background, bitmap codes
`00/01/10/11` correspond to `0/11/15/1` when that ramp is actually installed.

An earlier authoring draft used reflectivity 0. The source table makes its
high and highlight both 15, which would hide visible changes in the upper
Bayer band. That draft was replaced before the final input pin. Geometry and
light expectations are unchanged. Compare the actual emitted palette state;
do not infer it solely from the selected scene material.

## Build command, outputs and dependencies

The ordinary legacy builder rejects `-OutputDirectory`; it writes inside its
own `work/`. Copy the complete pinned SDK to a new disposable directory first.
PowerShell 7 and 64tass 1.60 or newer are external tools; `TASS64_EXE` can point
to the assembler. No scene textures, PNGs, music, mesh files, camera files or
graphic includes are required. This ordinary path reads the scene and SDK
`work/tools/c64_material_scales.generated.json`; it does not select Mode7,
Q8, Normalized16, legacy-plus, gameplay or their Python generators.

Replace `/absolute/fresh-sdk` with that complete copy, retaining the absolute
scene path:

```sh
rtk proxy pwsh -NoProfile -File /absolute/fresh-sdk/work/build-3Dvibe64.ps1 \
  -SceneFile /Users/rogerjohansson/git/asynkron/c64demo/research/3dvibe64-native/scene.json \
  -GraphicsMode 6 -Precision legacy -LegacyStability historical \
  -Quality fast -Projection extended-table -MemoryLayout high-basic-v2 \
  -CameraMode fixed -CameraViewport normal -VideoStandard pal \
  -FramePresentation safe -NoFpsOverlay -SkipCmdUpdate
```

`NoFpsOverlay` gives the normal 160×100 logical viewport, expanded to 320×200
physical bitmap pixels, with no header split. It is still multicolor output.
The default clear policy remains dirty, and no experimental optimization or
acceleration is requested. The object supplies its own pose/rotation/material;
the default builtin mesh is not used when `SceneFile` is present.

Expected output locations are `work/3Dvibe64.asm`, `work/3Dvibe64.prg`, and
the copied `work/build/3Dvibe64.prg`. The ordinary builder invokes 64tass with
`-a -B -o <PRG> <ASM>`. For a separate debug PRG, the SDK assembly guide
documents these extra inspection outputs:

```sh
rtk proxy 64tass -a -B --vice-labels \
  --labels=/absolute/fresh-sdk/work/build/3Dvibe64.vice.labels \
  --map=/absolute/fresh-sdk/work/build/3Dvibe64.map \
  --list=/absolute/fresh-sdk/work/build/3Dvibe64.lst \
  -o /absolute/fresh-sdk/work/build/3Dvibe64-debug.prg \
  /absolute/fresh-sdk/work/3Dvibe64.asm
```

Compare the debug and builder PRGs before using debug labels as native
authority. Preserve exact commands, tool identities, logs, generated ASM and
every emitted table. Then verify the six normals, six center terms, face-shade
indices, 132-byte packed Bayer table, intensity tables, material ramp and
actual initial/native shade state. A successful build is not a rendered-pixel
or speed result. Root owns all such build/tool/native actions; this scene lane
only authored and independently inspected the input.
