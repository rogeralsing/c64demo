# Follow-up prompt

Continue the active C64 demo research in
`/Users/rogerjohansson/git/asynkron/c64demo`.

The complete objective remains: scan primary blogs/articles, find demos
that push the machine, reverse-engineer released code, understand the
mechanisms, and document verified findings and open questions. Do not
redefine completion around the existing cases or the last passing checker.

**Current next task:** explain the stock raster coverage of the negative-side
groups in new camera poses 9 and 10 before proposing a conservative replacement.
The strict camera-plane predicate changes 96/144 display pixels despite valid
source units and all full scalar/native buffers matching. Preserve those
counterexamples; do not fit a threshold to these samples or hard-code face IDs.
No policy patch or measured native speedup is accepted. Pong is outside this work.

## Read first

1. `CHECKPOINT.md`, `HANDOFF-ARTIFACTS.md` and `README.md` in this directory.
2. `3dvibe64-camera.md`, `3dvibe64-camera-units.md` and
   `backface-source-conventions.md` for the new native-pose classifier failure,
   source-proven coordinate contract and separate ideal-projection reference.
   `3dvibe64-overdraw.md`, `3dvibe64-cull-policy.md` and
   `normal-plane-culling.md` retain independent omission, SDK-policy and
   primary mathematical evidence. They are separate scopes.
   `3dvibe64-profile.md`, `3dvibe64-profile-plan.md` and
   `3dvibe64-profile-pixels.md` retain measured costs and scalar acceptance.
3. `3dvibe64-native-pixels.md`, `3dvibe64-build.md`, `3dvibe64-toolchain.md`
   and `3dvibe64-native-scene.md` for the accepted Gouraud case; `3dvibe64.md`
   retains the earlier source arithmetic. `spires-native.md` owns the corrected
   original FPP binding; the other source notes retain their bounded scope.
4. `no-bounds-spritefpp-visible.md`, `no-bounds-original.md`, `no-bounds-native-spritefpp.md`,
   `spritefpp-native-plan.md` and `no-bounds-plasma-vector.md`.
5. `anomaly-native-priority.md`, `anomaly-native-upper-fetch.md`, `anomaly-upper-scanout.md`,
   `anomaly-sprites.md`, `anomaly-native-tail.md`, then the host-only
   `research/anomaly/overlap_plan.py` receipt under `build/research/anomaly/overlap-plan/`.
6. `dragonbond-native-tail.md`, `dragonbond-scanout.md` and
   `vice-live-observer.md`; the older `dragonbond-native.md` preserves its
   original boot, handover and failed optional-observation scope.
7. `relax24-loader.md`, older resource/article notes, the November frontier
   reading/follow-up/geometry notes and the technique map.

Research resumed on 8 November 2026. The initial 7 November evidence remains
frozen; the new receipts extend it. Recheck actual Git/filesystem state:
other chats are developing standalone experiments and the Pong renderer.
Preserve their edits and preview processes. Do not commit without a fresh
commit instruction. No converter feature or NUFLI viewer replacement is
requested; `/Users/rogerjohansson/git/asynkron/c64` is a separate repository.

Every shell command must start with `rtk`; read
`/Users/rogerjohansson/.codex/RTK.md`. Use parallel agents for independent
source/model work, with a single owner for VICE/process control. Do not
execute downloaded host tools merely because they appear in demo archives.
Preserve old producers/receipts and failed observations before corrections.

For **potentially unbounded native observations**, use the new
`research/vice_session_live.py` cancellable observer. Its actual JSON/wire
checks retain the rejected UTC-collision run, then validate same-connection
interrupts, ordinary-command ordering, partial output, waiting notices and
owned closure. Read `vice-live-observer.md` before using it. A timeout keeps
the original command pending; `{"interrupt":true}` sends read-only `r` on
that same connection, while `{"close":true}` closes the owned session.
Do not infer completion from a stale prompt or restart after a waiting notice.
The old `research/vice_session.py`, failed main-loop-only raster observation
and separate cleanup evidence remain frozen. Keep one process owner and
verify cleanup of only that owner's process; do not reuse closed handles.

## No Bounds: one original visible SpriteFPP component is exact

Read `no-bounds-spritefpp-visible.md` and its frozen native03 receipt before
continuing. The fresh original boot (no restore) has 14 exact RAM/VSF pairs,
125 completed commands and a PNG. All 20,261 file-known production-entry
bytes again match. Navigation warp was declared; all proof resumes after
production entry used warp off/Speed=100. The supplied Parts standalone init
remains a different variant.

The former pointer 0/header case is now observed: cached pointers 0 fetch
file-defined zeros at held MCBASE 3..24, ignoring native header `47 EC 98`.
Pre/post-clear observations are raw cycles 46/50, distinct from native02's raw cycles 45/49.
The three header bytes remain outside the original file-known mask.

The mature pose 4/layout 59/gray-palette component independently matches all
**42,560 palette indices**, rows 78..210 and columns 32..351; every compared
row is committed. All eight sprites contribute nonzero visible pixels. The
source row table, actual cached pointers, all 1,072 traced pointer stores
and the 72-layout offline model are bound. Eight live pointer-table padding
bytes do not make the original atlas payload mutable. Reverse priority is
inconclusive here because overlaps can select equal colors. This is one
pose/layout/palette, not a whole 312-line frame, animation/FPS or standalone proof.

Latest owner-closed/reaped continuation:

```text
build/research/no-bounds/native-03/mature-window-complete.vsf
SHA256 967f604ebde48b649edee3715ece4b08836710ce091e62de246eb6908e5f6a02
PC 0CFA, clock 143600978, raster 220, raw cycle 38
```

Continue with another pose, X layout or palette, or later Y-pulse/tunnel
phases with fresh row-window/pointer-schedule guards. Do not repeat the first
pointer 0/header or mature-component checks as unresolved work. Use the exact
original side1 D64 path/hash in `no-bounds-original.md`. Before any restore,
save/compare its first full restored state, including C64 RAM/CPU/CIA/VIC,
real ports/beam and relevant DRIVE8, DRIVECPU0, 1541VIA1D0, VIA2D0 and FSDRIVE
state. [Drive restore analysis](drive-snapshot-restore.md) explains observed
resync/rescale deltas without proving whole-machine equality. If exact
drive/IEC continuity cannot be established, use fresh original boot and
natural navigation; never edit snapshot bytes or PC to force equivalence.
Native01 remains cancelled navigation, native02's palette-zero DMA receipt
remains frozen, and native03 is the completed fresh-boot extension.

Passive replays (no VICE):

```sh
rtk proxy python3 research/no-bounds/inspect_original.py
rtk proxy python3 research/no-bounds/native_spritefpp.py
rtk proxy python3 research/no-bounds/spritefpp_visible.py
```

PlasmaVector is a separate static result: 256 prepared projected poses,
generated color-LUT sampling and 971 literal supplied-PRG bytes. Runtime
XOR/fill selects LUT high address bytes, rather than filling bitmap pixels.
Bind its original loaded part and resident Mem dependencies before native
generated-code/LUT/pixel work; `research/frontier-2026/plasma_vector.py` owns
that passive proof. None of these results completes the broader research.

## Anomaly: priority is distinguished; changed-wall upper strip has 101 rows

`anomaly-native-priority.md` and `native-priority-proof.json` own the latest
result. Native08 is fresh original side1 autostart, no restore, three exact
RAM/VSF pairs, 43 ordinary commands and a PNG. The earlier native07 state is a
host prediction input, not an execution parent. Navigation retains two
waiting notices, one interruption on the same process/socket and one rejected
read-only WarpMode resource query. Both proof resumes inherit explicit warp
off/Speed=100; none of that navigation is a timing measurement.

The observed counter 020F, wave indices, phases, positions and mask agree
with the old 403-further-update upper-sprite prediction. Actual all eight
states close its old occlusion condition: at line 110/X 318..319, sprites 6/7
both contribute nontransparent original-art pixels while the other six do
not obscure them. Saved committed output and direct all-eight composition
give 14/14; reversed priority gives 1/1. The active snapshot's uncommitted row
still contains 3/3 and is retained as a rejected stale-row control.

The native VIC bank is $4000, D018=$80 and actual pointer table $63F8.
Independent 101-row composition uses an explicitly separate input-address
renaming view for the frozen compositor, not a native $C000 display, CPU
execution or injected state. All **38,784 indices** across committed rows
**51–151** match. This is not a complete sixth 104-row upper strip: current
line 152 and later rows are excluded. The wall is new, with 3,317/4,160 bitmap
bytes and 333/520 attribute bytes different from native07. Substituting only
the stale wall makes 15,162 pixel errors.

The armed pointer trace covers $4FF8/$CFF8, not actual $63F8. Actual endpoint
pointer bytes and active nonzero original-art latches are bound, but do not
claim continuous actual-table pointer-write history. All prior complete
four/fifth upper-strip and coherent-window receipts remain frozen, with
their one-wall scope; this partial changed-wall strip extends them separately.

Latest owner-closed/reaped continuation:

```text
build/research/anomaly/native-08/priority-row-committed.vsf
SHA256 09df702e9fcac59d9c81a3ced230a58a7fcc8bbe7296a6b249ed42131f0db992
PC B400, clock 175046267, raster 152, raw cycle 11
```

Keep original side1 D64 SHA-256
`d452497845598cca8936fdf57c60fdc9c70cd7e64110e049fa6fc7d735f940cd`.
Any continuation uses a NEW case and states fresh-boot versus restore
explicitly. If restoring, save/verify full initial C64 and relevant drive/IEC
state; [the restore note](drive-snapshot-restore.md) does not prove whole-machine
equality. Prefer fresh original boot if exact continuity cannot be established.
Never edit snapshots or PC to force equality.

Next trace actual $63F8..$63FF, then capture after rows 152–154 commit to complete
the 104-row window. Broader changing-wall/workload coverage, deadlines, full 312
raster frames and physical hardware remain open. Do not repeat the already
closed priority/all-eight or different-wall checks as unresolved work.

```sh
rtk proxy python3 research/anomaly/native_priority.py
```

The host-only `overlap_plan.py` is preserved as the prediction, not reclassified
as native evidence. Prior corrections remain: physical RAM bytes 0/1 are not
CPU ports; historical floor-strip-complete is 178/53 and floor-strip-drawn is
178/59. Distinguish current-line DBUF from committed rows and do not revive
uniform 63-clock observer timestamp assumptions.

## Relax #24: promote the functional contract to real transfer evidence

The original resource parser already recovered all 9,216 bytes from 3,569
compressed bytes. Its strict CPU prefix still stops at unknown `$0223`;
that boundary has not been bypassed by invented RAM or hardware inputs.
Do not rerun the multi-million-instruction packing proofs unnecessarily.

The new `research/relax24/loader-contract.py` binds the original 496-byte
uploaded drive image (`$25A8..$2797` to drive `$0500..$06EF`), first request
`02 30 30`, actual directory lookup, all 21 original file streams and the
recovered `$AC00` receiver. The first byte 02 is overwritten by this drive
code, not dispatched as a separately identified command.

For original `00`, the conditional byte protocol has 13,980 wire bytes and
13,820 output stores at `$2000..$55FB`, cursor`$55FC`, carry clear. The final
`0C 08` bytes patch the later jump to `$080C`; the relocated entry begins
`A0 00 78`. This is a source-byte-gated functional result, not an observed
IEC transfer, initialized reader or executed jump. Preheader failure and
failure after data transfer have different cursor/store effects; the new
note preserves that distinction and the full-address-wrap carry clear edge.

Next native acceptance:

1. Bind actual uploaded drive RAM `$0500..$06EF` to SHA256
   `d0225bd8f23d19858bddf5ff2dd1cbfa7a95c12bd9ec556522c9e49606d29748`.
2. Observe resident job `$04` service establishing real directory and file
   sectors at drive `$0700`, returning successfully at `$062D`. Do not supply the
   service or firmware state in a CPU model.
3. At actual C64 `$C15D` after`JSR $AC00`, check carry clear, cursor `$55FC` and
   `$2000..$55FB` SHA256
   `dd8dff99a0f316d5d2a17a98949b738f31fbba6497151d763724a7f386d8fecf`.

Then follow the actual copy/reader path and establish article identity.
Other resources, continuous bootstrap, serial timing and the cached
Clarence review remain unverified.

## Dragonbond: extend the bounded original handover evidence

The November note pins Background's 18-page making-of PDF and original
2026 disk, plus independent source/asset cases for Viva Las Vegas and
Tusari 2. Reproduce with:

```sh
rtk proxy python3 research/frontier-2026/november.py
```

The original Dragonbond disk is
`build/research/frontier-20261108/dragonbond.d64`, SHA256
`37854b4e3426349ee03bc759f5bed8ad9a6c7f0404a469f1ae5163918cf50300`.
Original bootstrap/installation and the requested intermediate handover are
now bound to released bytes. All sixteen sprite triples use **33 new head
bytes plus 30 old tail bytes**, excluding slot byte63. This differs from the
PDF's simplified new30/old33 illustration. Eight saved sprite-0 witnesses
match actual old/intermediate/successor DMA bytes in VIC banks `$4000` and
`$8000`; the latter changes from hires to multicolor between samples.

Reproduce the passive source/data and owner audits:

```sh
rtk proxy build/research/tower-power/cpu-venv/bin/python research/dragonbond/inspect_original.py --handover build/research/dragonbond/native-02
rtk proxy python3 research/dragonbond/native_capture.py
```

The earlier native audit covers **27 RAM/VSF pairs, 1,769,472 physical RAM bytes,
26 completed resumes and one incomplete optional observation**. It retains
the rejected scene42 filename/context and the late raster 267 attempt.
The latter returned no prompt or save pair; queued commands do not establish
a new checkpoint. The helper ended before cleanup, so the owner separately
verified the exact orphaned VICE PID's absence after SIGTERM. Its child exit
code was not observed. These facts are owner cleanup, not natural demo exit.
Keep the `--handover` argument: the default source-only run writes a receipt
with a different scope and must not overwrite this frozen handover report.

The new native-03 continuation restores that exact parent and stops at an
**any-original-instruction** raster-267 checkpoint inside the music IRQ.
It follows original control flow for 730 clocks to `$12A9`, with all eight
bank-$8000 successor-tail data latches checked against the actual data.
The new session is owner-closed and reaped with recorded VICE exit −15.
This is separate evidence; the old failed attempt remains absent in its
frozen receipt. Reproduce the new passive audit with:

```sh
rtk proxy python3 research/dragonbond/native_tail.py
rtk proxy python3 research/dragonbond/scanout.py
```

Latest completed checkpoint:

```text
build/research/dragonbond/native-03/bank80-new-tail.vsf
SHA256 a 8b8558f366e94512c1d6682987e57d5dca63a60a4d79edb1566f457138df7c3
PC 12A9, clock 149028968, raster 267, raw cycle 11
```

The artifact index and `dragonbond-native-tail.md` pin the exact SHA-256.
All native01/native02/native03 handles are closed. A main-loop-only condition
can miss a raster line occupied by the music IRQ; keep the new observer and
any-original-instruction checkpoint when extending this case. Restore the
last completed snapshot once and verify identity before following natural
control flow. The separate `scanout.py` now matches **10,368 exact indices**
in 27 second-field rows (126–143 and 148–156), with original multicolor
bitmap and eight hires overlays. Its first-field DMA snapshots have DEN
clear and all-black output, so they remain fetch evidence rather than a
visible-picture proof. Preserve the rejected bounding-box color guard and
inconclusive priority control. Extend the excluded position/color-changing
rows 144–147 and complete-picture composition next; the maximum nine-line
allowance and wider effect/whole-demo timing remain open. Do not identify
the loader from an archive filename or a story-part comment.

## Spires: original first-band code/data/counters are bound

Read `spires-native.md` and its frozen `native-analysis/native-proof.json`.
Original boot payloads, the service table, all 130 macro rows (4,550 bytes)
and 4,032 meaningful stripe bytes match. Native snapshots bind seven actual
first-band offsets `0,3,6,9,12,15,18`, row data and holds over a later raster
line. All 2,640 finite-window trace stores match. Two successful fresh boots
have 17 RAM/VSF pairs; neither restores or injects state. Native01 is a
separate closed/reaped failed startup with no snapshots or execution witness.

Native02's black low nibbles were accepted by a wrong unmasked D028 guard:
unused read bits are `$F0`. Native03 uses `(@io:$d028 & $0f) != 0` and observes
all seven colors as blue 6, with a retained screenshot. The screenshot is
visual observation, not an independent committed-pixel or FPS proof. Initial
first-field high-X leftovers are not seven fully visible rectangles.

The old frozen source note's pointer addresses are wrong. Screen `$AC00`
uses table **`$AFF8`**, used sprites `$AFF9..$AFFF`, not `$ACF8/$ACF9..$ACFF`.
The correct macro expansion matches native code; wrong addresses fail 910
bytes. Record this correction without changing the earlier frozen note/receipt.

Latest owner-closed/reaped checkpoint:

```text
build/research/spires/native-03/colored-window-complete.vsf
SHA256 96691e36ee0e6aa645cd8be6e116a60297b554894ae8d8cfe9a8678839302855
PC A2B1, clock 77633652, raster 192, raw cycle 12
```

Future Spires work can separately observe the other Y bands, build a
character-mask-aware committed-pixel oracle, or bind TechTech's runtime fonts,
screens/bank split and palette. Its five coarse×eight fine positions, ten
charsets as five phases×two vertical banks, 817-byte tool-LUT mismatch and
missing imports remain frozen source/asset facts. No further Spires capture
is planned in this extension; next focus is the Gouraud task below.

```sh
rtk proxy python3 research/spires/native.py
```

## Prepared Dragon pictures: source/data proof, no native playback yet

Read `host-3d-2026.md` and `build/research/host3d/analysis/host3d-proof.json`.
The pinned FlyingFathead toolkit revision contains a metallic Dragon CRT
whose 128 prepared pictures match 1,105,920 bitmap/screen bytes against an
independent decode of the supplied host oracle. Actual frame directories and
67 copy-loop/address-mask bytes are bound; the 88-page bootstrap input is
`$0800..$5FFF`, excluding uncopied zero padding. No upstream code was executed.

The 5,205-vertex source model is not a per-frame 6510 transformation claim.
All changing screen-color cells fall inside the 437-cell absolute-update
set; bitmap recycling still needs the previous picture's clear metadata.
The conditional 24,622-core-cycle lower bound for the largest literal copy
excludes overhead/stalls and is not a measured frame time or FPS result.

A future native case would start the exact CRT naturally and bind completed
buffer publication to presented bitmap/screen data, separating render work
from intentional holds. That case has not run. Host geometry/lighting and
source-to-oracle reproduction are separate open work. The passive replay is:

```sh
rtk proxy python3 research/host3d/inspect.py
```

## VIC-II-spector: bounded planner checks, not a hardware replacement

Read `vicspector.md`; passive replay is `rtk proxy python3 research/vicspector/inspect.py`.
The final source audit checks 32,256 settled PAL BA classifications, 32 fetch
half-cycle entries, 63 X values and 29 MISC instruction-start annotations.
AEC was not independently compared; continuous BA-low stalls must not be
called fetch occupancy. Seven existing frozen FPP pairs are passive reanalysis,
not new native observations. They demonstrate held offsets after cycle 16,
not the graph's cycle-15 crunch transformation.

The 15/16-line graph paths exist mathematically; the +2/+1 explanatory labels
do not prove internal operations, arbitrary artwork or executable MISC timing.
Use official VICE/Bauer as authority and validate any new scheduled routine
against native state and committed pixels. No new native session ran here.

## Camera-plane result: strict removal fails image preservation

Read `3dvibe64-camera.md` and `3dvibe64-camera-units.md`. The unchanged PRG
was observed in a fresh closed 81-file case with 37 RAM/VSF pairs: start
`$080D`, then `$1153` / `$1441` / `$08D4` for 12 consecutive rendered poses.
These are not consecutive PAL fields. The full scalar replay matches every
completed native bitmap and both palette arrays before filtering.

Use actual `(signed8(rx), signed8(ry), signed16(sz|szhi<<8))`, eye zero and
outward `N=(P1−P0)×(P2−P0)`, retaining `N·(E−P0)>0`. Depth already includes
object Z=128; +190 is a compensated physical table index, not an eye offset.
All 81 source coordinate products, 18 old captured vertices and 1,536 linked
table bytes match. Read the prepared matrix at `$1153` or fresh geometry at
`$1441`; drawing clobbers some completed matrix scratch bytes.

Strict selection preserves all three old windows and ten of 12 new windows,
but rejects face 3 in pose 9 (48 bitmap bytes / 96 physical pixels changed)
and face 5 in pose 10 (66 bytes / 144 pixels). Both palette arrays stay equal.
The classifier remains a failed image-preserving candidate; do not turn the
successful full-buffer integrity flag into a classifier success claim.

Next follow those two groups' actual projected/rasterized coverage and retain
full bitmap, both palettes and 64,000 decoded indices as regression conditions.
Coarse tables, projected smoothing and edge rules are context, not a proved
unique cause. Do not fit a threshold only to these poses or hard-code face skips.
No new build, product patch or speed measurement occurred. Root accepts the
negative experiment: all 106 classifier outputs replay exactly, including the
false classifier flags. All 12 full replays cover 1,958 spans, 96,000 bitmap
bytes and 24,576 palette bytes with zero native differences.

The separate `backface-source-conventions.md` checks an exact ideal-projection
identity on 120 triangles in 15 windows / 13 distinct point clouds. Old
first/third repeat new poses 1/3. Both primary HTML/text bodies and retrieval
records are retained. Ideal plane-facing or a projected-area sign alone does
not establish compatibility with stock integer raster coverage.

Latest closed experimental checkpoint is
`build/research/3dvibe64-camera/native-01/pose-12-complete.vsf`: PC `$08D4`,
clock 10183653, raster 29 / raw cycle 18. The new case is fresh generated-PRG
autostart mode 1, not a restored continuation or original-disk loading proof.
Speed reads are 100; InitialWarpMode reads 0 do not prove current warp state.
No committed-VIC image, full rotation or delivered FPS is added.

For a passive replay, use an unused output directory below the owned analysis
root. The classifier succeeds as an integrity experiment while intentionally
reporting image-preservation false:

```sh
rtk proxy python3 research/3dvibe64-camera/classify.py --output build/research/3dvibe64-camera/analysis/replay-NEW
rtk proxy python3 research/3dvibe64-camera/source_units.py --output build/research/3dvibe64-camera/source-analysis/replay-NEW
rtk proxy python3 research/3dvibe64-camera/source_geometry.py --output build/research/3dvibe64-camera/source-geometry-replay-NEW
```

Replace `NEW` with unused suffixes. No path normalization is needed. Intermediate
`old-three-*`, `combined-*` and earlier accepted copies remain historical;
`analysis/accepted-02/camera-proof.json` is the final combined receipt.

The user separately requested a visible Gouraud preview. Leave it running.
`build/research/3dvibe64-camera/preview-owner.json` is a dated ownership record,
not current liveness authority. It records observer handle 92528 / PID 96769;
verify the exact owner before any future control. Mutable `preview-01/` stays
outside the immutable inventory while active. Static preview PNG/JSON and
wrapper source are cosmetic provenance, not research timing or pixel proof.

## Accepted omission and conservative SDK policy

Read `3dvibe64-cull-policy.md`. The third pose's face 7 is intentionally retained
by the active rotated-XY cross ≥ −32 test: its cross is −17. The −96 clipped-quad
alternative is compiled out, and the captured depth/sliver checks also pass.
Actual source latch `$0C`, not counter `$0D`, binds each draw's work and spans.
Third face 1/face 7 subtrees total 172,828 elapsed cycles; do not report that as
saved cycles without a new candidate benchmark.

The independent exhaustive omission is accepted: all 64 group subsets were
tested. First/second require all four groups; third uniquely keeps minimum
`[2,0,3]`, omitting either/both 1/7 with all 8,000 bitmap bytes, both 1,024-byte
palettes and 64,000 decoded physical pixels identical. These are completed
buffer images, not new VIC output. Third loses 80 spans/339 input writes
only in offline replay. Face 1 remains necessary in earlier poses; its second
omission changes 640 pixels. Finite fit is not a general hard-coded-ID policy.

That earlier continuation is now tested in the camera study above: units are
bound, but strict removal changes pixels in two new poses. The observed 172,828
cycles remain work, not a native saving. This preceding omission/policy study
itself changed no product, configuration, build or native process.

`normal-plane-culling.md` is separate primary reading/math. Its retained PDF
really prints a +1 offset for normal Y and endpoints `±X+Y`; those endpoints
instead satisfy `Y·p−1=0`. Sixteen exact endpoint checks, six of eight threshold
counterexamples and a tangent case support the correction. With outward normal,
use `n·(E−P)>0`, reducing to `n_z<−d/C` only for its stated eye/plane convention.
Do not infer a SDK sign error, a measured speedup or verified 1991 code from it.
The source/retrieval/text/page renders and both rational proofs remain retained.

## Stock Gouraud profile: measured costs, no product fix

The accepted profile reports three renders of 590,499 / 543,692 / 676,134 PAL
machine cycles and full begin periods of 612,884 / 549,791 / 688,964. Third-render
exclusive shares are 38.41% spans, 17.76% XYQ2 bounds, 16.18% shade edges,
9.20% row setup/dirty tracking, 7.06% material, 6.29% dirty clearing, 2.12%
rotation/lazy projection, 1.34% collection/culling, 1.03% lighting, 0.60% residual.
These are elapsed clocks with IRQ/VIC work, not retired core cycles, wall-time
FPS or observed VIC publication. Never add inclusive fill and its children to
this exclusive partition.

All 530 span calls have actual general/uniform markers and correctly paired
stack/continuation observations. Uniform/general counts are 28/140, 15/144,
11/192; a short constant-looking span can still use the general route. The
third pose's fifth face draw is a geometry/culling question, not a missing
return. `$0D` is always 8 here and cannot identify the active face. Three poses
are not a full rotation, best/worst workload or whole animation.

The closed case has 11 RAM/VSF pairs and 153 completed commands, including
read-only query rejections. Current runtime warp was not successfully queried;
valid Speed and InitialWarpMode reads do not substitute for it. The separate
three-buffer pixel comparison is accepted: 24,000 bitmap and 6,144 palette
bytes match. It adds no new committed-VIC or delivered-FPS claim.

The captured active ID is `mode4_current_face_id=$0C`; `$0D` is only the
collector counter 8. Third groups 1/7/2/0/3 include face 7's 45 nonempty spans,
203 writes and widths 1–8. The accepted omission proof above now establishes
finite redundant overdraw for groups 1/7, without proving geometric visibility,
a culling defect or a global policy. The third clear still matters: replaying
over stale B makes 896 wrong bytes. The measured profile is an unchanged
baseline, not a candidate benchmark.

Latest closed profiling checkpoint:

```text
build/research/3dvibe64-profile/native-01/fourth-begin.vsf
SHA256 f31c7ce5b0ef00f8f93727447ea0857640c8d5e184a912fe9b76b3dec968b97f
PC 08CB, clock 5131747, raster 24, raw 19
```

Keep the earlier stock pixel baseline and all other research gaps. Geometry,
clipping/culling, edge-shade construction, complete lighting and new committed
VIC scanout remain separate claims.

Replay the accepted omission producer with a fresh directory under its owned
`omission-analysis/` tree. Root and agent replays match all 23 files exactly;
no path normalization is needed. `root-replay-check.json` also pins cull and
normal-plane replay equality and the rejected outside-root path argument.
That rejection occurred before directory creation; no source/input changed.
The normal-plane 1991 attribution remains an author account, not a recovered
executable or measured speed result.

## Earlier accepted Gouraud scalar/pixel baseline


The unchanged pinned SDK and authored octahedron produced PRG
`69b0d86f79106b2bf9654d85bd631bc68c12f4efd708454a0048560b3c1bfdeb`.
Toolchain/build audits bind actual executions, byte-identical symbol assembly
and 57 tables / 1,011 bytes. The runtime cache/member catalog covers 1,148 regular
files without individually duplicating runtime DLLs, unpacked source and staged
SDK files in the handoff inventory. Actual executables and archives remain pinned.

Seven RAM/VSF pairs bind 458,752 RAM bytes and 49,709 startup payload bytes.
This is generated-PRG autostart mode 1 with declared loader injection. Stock PAL,
Speed=100 and warp-off flags are requested at launch; no runtime speed/warp query
was recorded. Both 8,000-byte target bitmaps and full Screen/physical Color RAM
arrays match scalar sampling from actual span inputs. Only sample 2 adds a
publication witness and 64,000 committed visible-body indices (51–250/X 32–351).
The rejected first-publication condition and same-socket interruption remain
failures, not a recovered first display. No complete geometry/clipping/culling,
painter-order/edge-shade, clearing or full lighting-transform proof is claimed.
The authored octahedron's sample 2 quadrilateral silhouette remains explicit.

Observed `$1153→$08D4` intervals are 577,195 and 509,905 cycles, about 0.5858 and
0.5175 PAL-model seconds. They include projection/collection/drawing plus IRQs
and VIC stalls, while excluding earlier lighting/clearing and later presentation.
They are not delivered FPS. Preserve this slow correctness baseline; do not
adopt it into Pong or present it as a 50 FPS performance improvement.

Latest closed/reaped checkpoint:

```text
build/research/3dvibe64-native/native-01/sample2-visible.vsf
SHA256 87fc47b7b737644658ac7d548417837054adaff2827612b69bc5d076dd810637
PC 0FB1, clock 10276311, raster 252, raw cycle 3
```

Use the retained PRG and `symbols-01/3Dvibe64.labels` for a NEW owned profiling
case; do not rebuild merely to recover symbols. Pair natural routine entry
and return observations with actual stack/return state. Separate geometry and
projection, setup/collection, span processing and material costs, with nested
calls handled explicitly. Count actual uniform-bulk versus gradient branches;
the 28/7 input intervals eligible for uniform fill are not observed branch hits.
Keep captured-input raster correctness separate from unproved front-end math.
Only then choose a bounded optimization experiment, retaining this exact baseline.
All other research cases and missing proofs below remain active.

## Fresh passive replay without overwriting accepted evidence

The build/pixel scripts default to their accepted output directories. A future
passive replay must use a NEW output directory. From the repository root:

```sh
rtk proxy python3 - <<'PYREPLAY'
from pathlib import Path
import runpy
import sys
sys.dont_write_bytecode = True
root = Path.cwd()
for script_name, leaf in [
    ('inspect_build.py', 'build-analysis-followup-01'),
    ('pixels.py', 'pixel-analysis-followup-01'),
]:
    fresh = root / 'build/research/3dvibe64-native' / leaf
    assert not fresh.exists(), fresh
    namespace = runpy.run_path(
        str(root / 'research/3dvibe64-native' / script_name),
        run_name='passive_replay',
    )
    main = namespace['main']
    main.__globals__['OUT'] = fresh
    main()
PYREPLAY
```

For the tool auditor, use its `--output` option with another nonexistent new
directory as documented in `3dvibe64-toolchain.md`. Retain the new outputs;
never overwrite accepted or failed directories. The root build/tool replays
are byte-identical. For pixel replay, all 12 nonproof outputs must match exactly;
compare its JSON only after normalizing the known output-artifact path prefix.
No input pin/state/source field may change. `root-pixel-replay.json` records
that exact qualification; raw proof JSON bytes need not be identical across
output directories. The failed first tool catalog is manual/nonreceipt history,
and its pre-fix producer was not frozen.

For the new profile pixel checker, use the same fresh-OUT `runpy` approach
with `research/3dvibe64-profile/check_pixels.py`. Its 16 other outputs must be
byte-identical. Normalize only output-artifact prefixes **and the exact declared
`reference_reuse.output_root_only_redirected` bare string** before comparing
JSON. Inputs, source and results must remain identical. The root's first
comparison rejected because it omitted that bare-field normalization; the
producer had already succeeded and was not rerun. `root-pixel-replay.json`
retains the qualified comparison. Source-plan/native-profile CLI replays need
fresh directories; the accepted source/profile receipts are `accepted-02`.
Earlier source-plan output/path-formatting failures remain history, not accepted
success receipts.

## Separate 1985 hires reading lead

`hires-dither-1985.md` links the original article. FACET is flat triangle
shading; curved primitives are front-view/no-rotation examples, not fast
rotating Gouraud evidence. Only retrieval metadata/digest is retained, not
the HTML body. Recover SHADE/RSHADE before adopting its threshold convention;
this lead adds no native or performance proof.

## Primary reading: preserve new models and pursue their actual gaps

The [repeated-bob lattice](frontier-reading-20261108.md) establishes a shared
144-character image, ten supplied maps, all 10,240 map bytes and all 9,000
visible cells synthesized from the one loaded map. Boundary repair removes
unknown input dependencies; omitting it fails the negative control. Bind the
published source/PRG to the original loaded 2023 part before measuring
publication or runtime savings.

The [Star Wars table model](frontier-followups-20261108.md) binds 295 row
functions to the supplied 7,544-byte PRG block and checks 428,813 truth cases.
It retains two source-selected lazy-copy exceptions at `(79,19)` and `(92,2)`.
Recover the actual cyclic-buffer/text trajectory before treating those
function counterexamples as visible demo defects. No original rendering
code was changed to hide them.

```sh
rtk proxy python3 research/frontier-2026/reading_next.py
rtk proxy python3 research/frontier-2026/followups.py
rtk proxy python3 research/frontier-2026/geometry_next.py
```

The [SpriteFPP strip model](frontier-geometry-20261108.md) binds 14,793
nonoverlapping code/data bytes in its supplied PRG and checks 559,104
prepared logical samples. Its four constant texture rows and 64 prepared
frame lists are not live C64 3D transformation or arbitrary texture mapping.
The later [original-release binding](no-bounds-original.md) and [native DMA
proof](no-bounds-native-spritefpp.md) supersede this lane's earlier binding
and fetch gaps. [The later visible proof](no-bounds-spritefpp-visible.md)
now checks one mature component; additional poses/layouts, animation and
timing remain open. The separate
[PlasmaVector static model](no-bounds-plasma-vector.md) supersedes the older
acquired-leads-only status with prepared-pose, generated-sampler and literal
PRG checks. Original loaded-part and native-pixel binding remain open.

Continue afterward with later Second Reality effects, moving presets in
The Impossible Thing, original Hat/Aloft algorithms and the broader reading
map. Keep author claims, source-byte models, native observations and
independent pixel oracles distinct. Failed acquisitions and wrong release
IDs are evidence to preserve, not invitations to invent the missing path.

If an observation times out, poll the same verified live handle; never
restart solely because observation expired. When a bounded pass closes,
update notes, checkpoint and artifact index. Report the verified result,
remaining limits and exact next step. Keep the broad research goal active.
