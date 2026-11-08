# Camera-plane classification of the captured Gouraud object

The strict camera-plane test is **not image-preserving for this renderer**.
It preserves all three older accepted frames and 10 of 12 newly captured
consecutive render poses, but removes visible pixels in new poses 9 and 10.
Those counterexamples remain failures: the classifier or acceptance rule has
not been adjusted to make them pass.

The test comes from actual captured 3D vertices, then replays only spans
belonging to its selected faces. It does not choose face IDs from previously
successful omissions. All full, unfiltered scalar replays match their native
completed bitmap and palette arrays before any omission is assessed.

The producer is [`classify.py`](../../research/3dvibe64-camera/classify.py).
No SDK, generated CPU code, assembler, emulator or product change runs in
this passive analysis. The separate
[camera-units investigation](3dvibe64-camera-units.md) establishes source and
coordinate provenance. The final receipt is
`build/research/3dvibe64-camera/analysis/accepted-02/camera-proof.json`.

## The predicate and its sign

For the original source triangle order, let the captured camera-space
vertices be `P0, P1, P2`. Define the outward normal and the eye-side scalar:

```text
N = (P1 − P0) × (P2 − P0)
S = N · (E − P0)
E = (0,0,0)

retain the face when S > 0
```

The PRG's linked coordinate and triangle tables establish outward winding
without using rendered images. With the untransformed radius-28 octahedron,
the object origin lies strictly behind every outward triangle plane. For
example, after translating the object by `(0,0,128)`, source face 0 has
normal `(784,784,−784)` and `S=78,400`; face 4 has normal
`(784,784,784)` and `S=−122,304`. The first faces point toward the eye; the
second points away.

With the eye at zero, the same scalar is `−det(P0,P1,P2)`. It includes the
plane's position relative to the eye, which a test of the normal's Z
component alone omits. No normalization, projection division, empirical
area tolerance or dot-product threshold fitted to the samples is needed.

The implementation uses unbounded signed Python integers. It verifies the
determinant identity, cyclic and reversed winding, common translation of
both vertices and eye, and the eightfold scalar change under uniform
positive scaling by two. For each captured point cloud it also records
whether every face remains a strict outward supporting plane: its centroid
and all nonface vertices must lie on the interior side. That check confirms
the interpretation of winding for the captured quantized geometry.

`S=0` is recorded separately as tangent; a zero normal is degenerate. The
strict candidate excludes those cases. This is a continuous plane-facing
rule, not a conservative integer-raster coverage guarantee. A zero or
near-zero raster counterexample must stay a counterexample; it is not
silently repaired by adding an empirically chosen acceptance band.

## Coordinate and projection conventions

The exact fixed-camera build uses signed eight-bit `rxbuf=$8036` and
`rybuf=$803C`, with Y up, plus signed 16-bit geometric depth from
`sz=$802A` and `szhi=$8030`. Each contains six entries. Depth already
includes the object center Z of 128. Adding 128 again or dropping the
translation would change the camera-relative planes incorrectly.

The projection table's index bias of 190 does not move the geometric eye to
Z=−190. The retained table builder subtracts that bias from its geometric
divisor; the far table uses 32-unit bucket midpoints. Thus it approximates
perspective with a coarse per-vertex scale, and the plane classifier uses
the geometric eye at zero. The separate units proof binds these source
and table facts. Completed matrix scratch bytes are not used as a transform
oracle: rendering can clobber them, while the captured vertex arrays remain
the inputs to this calculation.

The classifier describes the actual quantized vertex cloud. It does not
reconstruct an ideal unquantized rigid rotation. Coarse perspective tables,
projected smoothing, edge rounding and conservative raster rules can differ
from the exact central-projection plane model near a silhouette.

## The older three frames

The original profile-pixel acceptance supplies actual span ABIs, post-clear
baselines and completed RAM/snapshot pairs. Its
[image checks](3dvibe64-profile-pixels.md) remain unchanged. The camera
classifier reproduces the earlier exhaustive
[omission result](3dvibe64-overdraw.md) through an independent geometric
predicate:

| Frame | Observed face order | Camera-plane retained order | Bitmap / Screen / Color RAM / display differences |
|---|---|---|---|
| First | `[3,2,1,0]` | `[3,2,1,0]` | `0 / 0 / 0 / 0` |
| Second | `[1,2,0,3]` | `[1,2,0,3]` | `0 / 0 / 0 / 0` |
| Third | `[1,7,2,0,3]` | **`[2,0,3]`** | **`0 / 0 / 0 / 0`** |

All eight captured triangle planes remain strict outward convex supporting
planes in these three samples. The wrong reversed-side control changes
14,444, 10,276 and 7,968 physical display pixels respectively. The third
frame's orthographic `N.z<0` set still includes face 1, while its true
camera-plane `S` is negative. This is why a normal-component sign alone is
not the general finite-camera test.

## Twelve consecutive unchanged-renderer poses

A fresh generated-PRG autostart supplied 12 consecutive render poses. These
are rendered poses, not 12 consecutive PAL display fields. The case has
three natural stops for each pose:

| PC | Actual capture |
|---|---|
| `$1153` | After clear and shade update, before rotation |
| `$1441` | All six new camera-space vertices available, before face collection/lazy projection |
| `$08D4` | Completed rasterization, before presentation wait |

At every `$1441` capture, all six `projdone` bytes are zero. Its six 3D
vertices equal the corresponding completed capture exactly. The 12 new
clouds and the three old clouds all have strict outward convex supporting
planes for all eight source triangles. No tangent or degenerate plane is
observed, and no mathematically front face lacks an observed span group in
these finite samples.

The new full scalar replay accepts **1,958 spans**, **31,683 logical pixel
writes**, **96,000 bitmap bytes**, **12,288 Screen bytes** and **12,288 physical
Color RAM bytes**, all with zero native differences. It starts from each
actual post-clear `$1153` baseline and preserves captured span order. The
camera test then filters that same stream, keeping all original endpoints,
shades, Bayer phase, material and remaining order.

| Pose | Observed order | Retained order | Spans: full → selected | Bitmap bytes changed | Display pixels changed |
|---|---|---|---:|---:|---:|
| 1 | `[3,2,1,0]` | `[3,2,1,0]` | 168 → 168 | 0 | 0 |
| 2 | `[1,2,0,3]` | `[1,2,0,3]` | 157 → 157 | 0 | 0 |
| 3 | `[1,7,2,0,3]` | `[2,0,3]` | 203 → 123 | 0 | 0 |
| 4 | `[2,7,0,3]` | `[7,0,3]` | 171 → 119 | 0 | 0 |
| 5 | `[7,4,0,3]` | `[7,4,0,3]` | 154 → 154 | 0 | 0 |
| 6 | `[7,0,4,3]` | `[7,0,4,3]` | 160 → 160 | 0 | 0 |
| 7 | `[7,4,3,0]` | `[7,4,3,0]` | 165 → 165 | 0 | 0 |
| 8 | `[7,3,4,0]` | `[7,3,4,0]` | 155 → 155 | 0 | 0 |
| **9** | `[7,3,4,0]` | `[7,4,0]` | **156 → 109** | **48** | **96** |
| **10** | `[1,4,5,0]` | `[1,4,0]` | **154 → 108** | **66** | **144** |
| 11 | `[4,1,5,0]` | `[4,1,5,0]` | 154 → 154 | 0 | 0 |
| 12 | `[4,5,1,0]` | `[4,5,1,0]` | 161 → 161 | 0 | 0 |

Both palette arrays remain byte-identical in all 12 selected replays. The
display decoder checks both physical bitmap rows separately across all
**320×200** palette indices. In these duplicated-row images, 96 and 144
display pixels correspond to 24 and 36 logical 160×100 pixels respectively.

## The two counterexamples

Pose 9 rejects source face 3, triangle `[3,5,0]`. Its captured normal is
`(−1240,−235,−135)`, with `S=−1680`. Its 47 nonempty spans have widths 1..2
and contribute 71 logical pixel writes. Removing them changes 48 bitmap
bytes and 96 display pixels within inclusive bounds `(108,62)..(127,133)`.

Pose 10 rejects face 5, triangle `[2,1,4]`. Its normal is
`(1212,206,−59)`, with `S=−11503`. Its 46 nonempty spans have widths 1..5
and contribute 122 logical writes. Removing them changes 66 bitmap bytes and
144 display pixels within `(194,66)..(217,153)`.

These are not zero-side degeneracies. The negative-side groups leave real
pixels in the stock completed images. Their captured projected `sx/syQ2`
triangle areas are respectively **+192** and **−600**, with all three
vertices projected. Thus the actual projected/rasterized coverage is not
interchangeable with the strict geometric plane predicate. Coarse scale
tables, projected smoothing, edge conventions and conservative submission
are relevant context; this experiment does not establish one unique cause
for either discrepancy.

The following decoded images retain the evidence. Difference images mark
changed display pixels in red:

- Pose 9: [full](/Users/rogerjohansson/git/asynkron/c64demo/build/research/3dvibe64-camera/analysis/accepted-02/new-pose-09-full.png), [selected](/Users/rogerjohansson/git/asynkron/c64demo/build/research/3dvibe64-camera/analysis/accepted-02/new-pose-09-selected.png), [difference](/Users/rogerjohansson/git/asynkron/c64demo/build/research/3dvibe64-camera/analysis/accepted-02/new-pose-09-difference.png).
- Pose 10: [full](/Users/rogerjohansson/git/asynkron/c64demo/build/research/3dvibe64-camera/analysis/accepted-02/new-pose-10-full.png), [selected](/Users/rogerjohansson/git/asynkron/c64demo/build/research/3dvibe64-camera/analysis/accepted-02/new-pose-10-selected.png), [difference](/Users/rogerjohansson/git/asynkron/c64demo/build/research/3dvibe64-camera/analysis/accepted-02/new-pose-10-difference.png).

The reversed-side control changes bitmap and display pixels in every one of
the 15 old/new windows. The receipt reports
`input_and_full_scalar_integrity_pass=true`, while both
`classifier_all_full_memory_preserved` and
`classifier_all_decoded_images_preserved` are **false**. Successful data
acceptance must not be mistaken for successful classifier acceptance.

## Closed native evidence and scope

The new case is `build/research/3dvibe64-camera/native-01`: **81 files,
30,912,553 bytes**, directory SHA-256
`4b320fcca0330ff3f11338a810340ec8cde71fd80ec082080be0325118c69463`.
The frozen raw-wire auditor checks all serialized input/sent/received
ranges, one original process/socket, completion and closure. Only its exact
generated-PRG autostart metadata assertion is adapted. The unchanged PRG
has SHA-256
`69b0d86f79106b2bf9654d85bd631bc68c12f4efd708454a0048560b3c1bfdeb`;
all 49,709 loaded payload bytes equal the natural `$080D` start RAM.

All **268 ordinary commands** complete without errors, interrupted resumes,
waits or retries. The whitelist permits debugger checkpoints, read-only
observations and capture commands; it contains no later CPU/RAM/register
patch or restore. All 37 RAM/snapshot pairs compare **2,424,832 RAM bytes**,
CPU registers/clock, CPU ports and raster line/cycle. The original process
is closed with VICE exit −15 and reaped; the observer exits successfully.

The root-authored plan and capture guide are pinned metadata, not substitute
evidence. Their 36 stage records must match the actual checkpoint setup,
break ID, natural stop PC, stop clock/registers and subsequent paired file
commands. The 12 span responses are sequences
`30,51,72,93,114,135,156,177,198,219,240,261`. No span trace occurs outside
those responses.

The attached command at `$A000` is exactly:

```text
m 0100 01ff; m 000b 002f; m b43b b441
```

The unchanged frozen profile parser requires all 300 unique byte addresses,
valid draw-buffer row pointers and span/shade ranges. Each saved stack
return is `$957C`, returning to `$957D` after the pinned `JSR $A000`. All
span clocks lie after the corresponding fresh geometry stop and before its
completion. The observed buffers alternate B/A over the 12 poses. No new
preclear-begin capture or full dirty-clear algorithm proof is claimed.

Speed resource reads at sequences 3 and 266 report 100. InitialWarpMode
reads at 4 and 267 report 0, and startup arguments include warp disabled.
There is no runtime warp query, so the startup resource is not promoted to
proof of current warp state. No host-time FPS, optimization cost or speedup
is inferred from these captures. The declared PRG autostart mode 1 loader
injection is not an original disk-loading witness.

## Replay and continuation

The output uses local filenames and no output-directory prefix or timestamp
in the receipt. Use a fresh directory beneath the owned analysis root:

```sh
rtk proxy python3 research/3dvibe64-camera/classify.py \
  --output build/research/3dvibe64-camera/analysis/replay-next
```

The command completes when the analysis and data integrity checks finish;
it intentionally writes a receipt with classifier acceptance **false** for
the retained counterexamples. Nonempty outputs are refused. The earlier
`old-three-*` and `combined-*` folders are intermediate analyses; the final
combined receipt is `accepted-02`.

A fresh `replay-01` reproduces all **106 output files, 3,780,076 bytes**,
byte-for-byte, including the receipt and checked producer. No path
normalization is needed. Independent read-only review found no producer
defect. Every nested artifact reference and all 1,611 previously frozen
artifact hashes were checked; no earlier source or capture was changed.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Independent units receipt | 22,508 | `665e9233aafe5cc3e25e82b497549117a04f64f2a14fa5f0c335290970284551` |
| Previous profile-pixel receipt | 50,301 | `a564dc770db6b02afc66607b259cd71971b9ef2810200c642fd5c4cae1cb2710` |
| New classifier producer | 28,335 | `6b4c517045827d8c71b136c5e2f6672f1b6ac3016d11502f72e6d4366d444449` |
| New combined receipt | 353,239 | `6023d45cbf7a47ff4f74d61211df512d077cbd046d01537d2a83f05c3a7fa536` |

The useful continuation is to explain the coverage of these exact two
negative-side groups before proposing a conservative replacement rule.
Keep their full bitmap, both palette arrays and decoded-pixel comparisons
as regression conditions. Do not tune a threshold against only these poses
and call it a general culling solution. No product patch is made, no
measured saving is claimed, and projection, clipping, edge construction and
vertex illumination are not independently proved by the scalar span
reference. The three old windows plus 12 new windows are not claimed to be
15 distinct poses or a full rotation.
