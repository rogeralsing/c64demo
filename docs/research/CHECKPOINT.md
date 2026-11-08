# C64 rendering research checkpoint

Updated 8 November 2026; retains the 7 November checkpoint. This is the consolidated handoff for the research
objective: **find boundary-pushing C64 demos and primary explanations,
reverse-engineer their released code, reproduce what can be checked, and
document both mechanisms and remaining questions**. The broader research is
unfinished. Passing a bounded checker does not complete a production or the
overall objective.

Start with this file, the [complete reading map](README.md), the
[technique comparison](technique-map.md), and the
[copy-ready continuation prompt](FOLLOW_UP.md). Detailed notes own the exact
inputs, source URLs, hashes, comparisons and limitations. This checkpoint
summarizes those results; it does not replace their evidence.

Research resumed at the user's request on 8 November. The [artifact index](HANDOFF-ARTIFACTS.md)
pins the retained producers, receipts and exact continuation inputs. The
broad research goal remains active; the new bounded results do not finish it.

## Workspace and preservation

- Research repository: `/Users/rogerjohansson/git/asynkron/c64demo`.
- Graphics-converter repository: `/Users/rogerjohansson/git/asynkron/c64`.
- Original analysis code: `research/`; documentation: `docs/research/`.
- Downloads, original source copies, unpacked images, snapshots, screenshots
  and large receipts: **ignored `build/research/`**. Preserve this directory.
  A fresh checkout does not contain the retained native evidence.
- Prefix every shell command with `rtk`, as required by
  `/Users/rogerjohansson/.codex/RTK.md`.
- Preserve concurrent renderer and `experiments/sprite-ball/` edits. Other
  work is active in this shared repository. Do not reset or stage unrelated
  files, replace its assets, or stop its preview processes.
- For potentially unbounded native observations, use the new
  `research/vice_session_live.py` [cancellable observer](vice-live-observer.md).
  It retains partial wire output and accepts interrupt/close on the same
  pending connection. The old `research/vice_session.py` and its failed
  main-loop/raster attempt remain frozen. Prefer bounded any-original-instruction
  checkpoints; keep one process owner and exact cleanup.

The research baseline was committed as
`d50d173e0b465c23353899b7fb28f1fb0873a762` (190 files).
The NUFLI verifier repair was committed separately in `c64` as
`b730ceb1a099376ccec8924a1fd63328c0fe40ec`; its four regression tests passed.
Subsequent research additions described below are not included in that
baseline commit. At the handoff inspection, unrelated sprite-ball work had
advanced `c64demo` HEAD to `425bf0e35f6fea615e64956d14c11ea3b6a11121`.
The subsequent authorized all-change checkpoint is `44f8dcb`; the newer
native-04/resource findings below were produced afterward. Re-read Git
state before acting; this is not a request to amend those commits.

The concurrent sprite-ball shading checkpoint is `3da9ae1`; its current
default hexagon receipt is summarized in the artifact index. It does not
alter any frozen research producer or the research objective.

The interlaced icosahedron PRG remained SHA-256
`41bde9eff7f4ccccb3ce2d8da9c3b896d07356f9777f20842d9d77f46587a17a`.
Research has not silently replaced that renderer or changed its display
to implement effects seen in other demos.

## Findings across the investigations

| Case | Established result | Important remaining limit |
|---|---|---|
| [Tower Power final](tower-power-sources.md) | Original final release and all 42 custom streams recovered. The sphere and patterned cube are identified in their own original code. | Keep the 1993 preview and 1994 final, and different model stages, separate. Complete stage timing is still open. |
| [Tower sphere mathematics](tower-power-n2-math.md) | Live rotation/projection uses reusable 16 KB product tables; these are products, not rendered animation frames. | Not every later effect necessarily uses this engine. |
| [Tower palette](tower-power-n2-palette.md) | Outside selector `11`, black character Color RAM and three global face colors are verified. | All state, marker and surrounding-blank conventions must change consistently if transferred. |
| [Tower patterned cube](tower-power-f1.md) | The captured body has 24 vertices and 15 coplanar stencil points; the cyan subdivisions are geometry in the original pipeline. | Do not identify every visible polygon as a hardware sprite. |
| [Tower line kernels](tower-power-lines.md) | Packed-byte collection and generated biased integer-DDA kernels are reconstructed and checked. | Their coverage bias differs from our exact crossings; an isolated cycle saving is not an integrated win. |
| [The Lab sprite vectors](the-lab-sprite-vectors.md) | A 164-pose prepared input sequence feeds triangle/span rasterization into an expanded sprite carpet, with sixteen density materials. | The sprites form the canvas; the result does not establish live arbitrary 3D transformation or one sprite per polygon. |
| [The Lab multicolor stage](the-lab-mms.md) | Prepared projected-edge/slopes commands feed generated XOR-prefix bitmap filling. The exploded-cube scene is matched. | Palette aliasing gives bounded layer priority, not general depth sorting or alpha blending. |
| [Next Round](next-round.md) and [scene preparation](next-round-scene.md) | The original 536-frame stream supplies resolved visible fragments; the transparent-looking two-cube pose contains ten disjoint fragments before rasterization. | The missing exporter/visibility preparation algorithm remains separate from the verified C64 rasterizer. |
| [Colors](colors.md) | Original Sparkle 3.4 bootstrap and first three-phase character/sprite display are mapped; all 184,320 sampled first-display pixels match the native model. | Analog blending, physical hardware variants and later effects remain open. |
| [Second Reality](second-reality.md) | The original C64 production, boot, loader, mock DOS/editor, file chains and early effects are identified. CA uses cached-address dot clearing; DB ORs complementary one-bit patterns; EC samples transformed texture planes into character buffers. | These paths do not establish the later polygon, texture-cube or raytrace implementations. Full scanout and full-demo timing remain open. |
| [The Impossible Thing](impossible-thing.md) | The separate 2003 intro generates 256 reusable glyphs from a 16×16 texture. Generated code, one stored-image update and an independent affine sampler match. | Native acceptance covers the static initial preset only. The bundled 25 fps statement is not verified; sampled selections average about 58,596 PAL clocks. |
| [Impossible Thing affine details](impossible-thing-affine.md) | Signed Q8 shortcuts, retained carry/borrow, integer glyph origins and packed U/V index addition are explicit. All new glyph/matrix bytes match the independent model. | An ideal continuous affine transform gives different samples. Other moving presets and negative horizontal-gradient paths lack native acceptance. |
| [Anomaly source mechanism](anomaly-arcade.md) | Ninety-six rates, staggered fine-scroll phases, byte shifts, signed raster gates and 28-job hidden-wall updates are reconstructed. Staggering reduces modeled peak coarse lines to 24, versus 70/96 in the declared aligned baselines. | Equal total work is redistributed; no complete 50 Hz budget follows from that enumeration. |
| [Anomaly original binaries](anomaly-binary.md) | Exact boot/drive binding to Sparkle 2.3.23.105; all 39 real bundles independently decoded. Both Arcade Link sections match all 41,523 bytes. | A source rebuild is still distinct from matching the supplied Link binary. |
| [Anomaly upper update](anomaly-upper.md) | All 28 first jobs, first publication and a direct 4,680-byte prepared-image oracle pass. Three 96-write field traces repeat at PAL cadence. | The later upper-window proof extends its old scanout boundary; later workload coverage and worst-case timing remain open. |
| [Anomaly complete floor](anomaly-sprites.md) and [upper window](anomaly-upper-scanout.md) | Four upper strips match 159,744 palette indices. Field 4 joins the frozen 96-row floor into one coherent 200×384 bitmap window with 76,800 exact indices. | Four upper outputs share one prepared wall image. No complete 312-line frame, universal deadline, physical-chip timing or whole-demo FPS proof. |
| [Dragonbond](dragonbond.md), [successor tail](dragonbond-native-tail.md) and [visible bands](dragonbond-scanout.md) | Sixteen released triples use 33 new head bytes plus 30 old tail bytes. Native-03 adds all eight bank-$8000 successor-tail latches. A direct bitmap/sprite oracle matches 10,368 indices in 27 second-field rows. | The earlier failed optional observation remains frozen. Four position-changing rows, complete-picture composition, maximum nine-line timing allowance and whole-demo success remain open. |
| [No Bounds finite bobs](primary-2026-notes.md) | Opaque masked drawing and a mirrored 14 KB-to-28 KB background restore match independent asset models. | Restore scheduling is motion-dependent; source-to-release and native timing remain open. |
| [No Bounds repeated-bob lattice](frontier-reading-20261108.md) | All 10,240 supplied screen-map bytes and 9,000 synthesized visible cells match independent coverage/quotient models, with 144 characters including blank. | Pinned post-release source and supplied PRG anchors are not original-disk extraction, native publication or timing. |
| [Star Wars row functions](frontier-followups-20261108.md) | The complete 7,544-byte table block matches the supplied PRG; 428,813 composition truth cases and 744 selected copy cells pass. | Two source-selected lazy copies fail universal function equivalence. Their actual text trajectory and visible consequences remain unobserved. |
| [SpriteFPP prepared strip geometry](frontier-geometry-20261108.md) | All 68 sprite slots, 64×91 row indices, metadata and 133 pointer cells match 14,793 supplied PRG bytes. The independent interval model checks 559,104 prepared samples. | Prepared host geometry is not live C64 3D. [Original binding and captured FPP DMA](no-bounds-native-spritefpp.md) now extend this static result; [one mature component](no-bounds-spritefpp-visible.md) is now exact; other poses/layouts, complete animation and timing remain open. |
| [Cancellable native observer](vice-live-observer.md) | Actual JSON/wire captures check interruption, queued commands, partial output, timeout notices and owned closure; the rejected UTC-collision run is retained. | Monitor contract checks do not prove artwork, full-machine equality, physical hardware, forced send failure or crash durability. |
| [Anomaly native bootstrap](anomaly-native.md) | Eight RAM/snapshot pairs, five PNG contexts and fifteen early payload domains pass through HumanMade. | That first batch ends before Arcade. The later partial runtime batch is summarized below. |
| [No Bounds loading](no-bounds-loading.md) | Twenty 2,000-byte strips contain bitmap plus both attribute planes. Four slots retain 8,000 payload bytes. The manifest, seventeen music comparisons and specific fade/loader/RTS handover are checked. | Refill deadlines, coherent counter reads, native publication and load times are not established by a source plan. |
| [Sprite interleave](sprite-interleave.md) | Rolled sprite rows and duplicated overlaps reconcile 21-line sprite restarts with 16/20-line pointer schedules. All sixteen Memento Mori artwork frames and The Dive's three woven sets match independent packed layouts. | Source-layout and static-cost checks are not native DMA timing or source-to-release equivalence. |
| [The Hat / Aloft](february-2026.md) | Original releases and attributed creator notes are archived. Trident's separate March 2026 nested-IRQ example is recovered. | The requested Hat upscroller and Aloft pattern/Kefrens algorithms remain unsolved; viewer reactions are not coder explanations. |
| [Boo / bit-reversal lines](bit-reversal-lines.md) and [binary analysis](boo-binary.md) | The original approximate selector and generated kernel are reconstructed. Its comparison/addition core is cheap, but compatible same-CPU selector setup exceeds the estimated advance saving in our workload. | No integrated speedup or complete native drive/display schedule is proven. |
| [The Demo Coder](demo-coder.md) | All 68 images are reconstructed. Stream 46 is Rubicon artwork; bank selection and native raster/row-counter witnesses are checked. | Complete all-eight-row FLD/stretch transformation remains unproved. |
| [Quondam](quondam-raster.md) | Native late row-counter wrapping and twenty-four bands of retained screen codes are identified. | The complete asset producer and independent full-field composition remain open. |
| [Nine](nine.md) | Initialization, character stamping and two natural Device raster families are checked against original execution. | Wider detector/alignment outcomes, complete pixel composition and physical VIC revisions remain open. |
| [Ghostbyte teaching examples](ghostbyte-shine-through.md) and [The Ghost](the-ghost.md) | Two teaching examples are bounded and modeled; all 62 original Ghost files are recovered through their own depacker. | The teaching compositor is not the full released scroller. Original Ghost native matching remains open. |
| [Freespin](freespin.md) | The 1541 drive's own video/output contract, original payloads and a released 64-cycle fragment are reconstructed. | This is a different output device, not a faster C64 framebuffer routine. Full scheduling remains open. |
| [A Mind Is Born](a-mind-is-born.md) | Original size-coded state overlap, IRQ arithmetic and bounded native state/lifecycle checks are reproduced. | Asynchronous service cadence is not automatically a visual update rate. |
| [Lunatico rain](lunatico-rain.md) | The original note is recovered and attributes rain ripples to WIZ/character graphics with slower bumpmapping. | Actual rain code, complete scheduling and the newer explanation video's captions remain unresolved. |
| [NUFLI](nufli.md) and [converter variants](nufli-converter-variants.md) | Original Mufflon/player ownership is mapped. Four exports match twelve native captures; fitting changes are distinguished from export inconsistency. The actual application's monitor-response race is fixed. | No new exporter color-math or player-color defect was established. This does not prove optimal fitting for every image or every VIC/hardware variant. |
| [Macro scheduling](macro-scheduling.md) | The 2025 example's IRQ continuations and cooperative waits are independently checked. | Source organization is not free CPU time. Keep the separate 2026 per-call-site nesting guard distinct. |

The [complete reading map](README.md) also links supporting boot, native,
line, palette, coverage and source-survey notes omitted from this condensed
table. Those are part of the findings, not superseded drafts.

## Practical conclusions for our vector renderer

The [technique map](technique-map.md) owns the transfer ranking and compatibility
details. The strongest independently useful pieces are:

1. **Dither in edge transitions.** The earlier host-only status is superseded
   by the implemented dither, tonal and Gouraud experiments documented in
   [interlaced-dither.md](interlaced-dither.md). Preserve their distinct
   geometry, performance and interlace limitations; do not repeat the
   original fixed-pattern experiment as an unimplemented research step.
2. **Reassign the outside selector.** Tower's `11` outside convention frees
   all three global multicolor registers for foreground colors, provided
   clearing, blank cells and prefix seeds use the same representation.
3. **Step exact field crossings directly.** The [exact-field DDA](exact-field-dda.md)
   preserves the current sampling rule. Setup, dispatch, RAM layout and
   terminal routing still need assembly integration and measurement.
4. **Collect adjacent packed markers.** Combining samples that address the
   same byte/field row can reduce stores. Preserve half-open coverage and
   XOR cancellation; do not import Tower's biased coverage by accident.
5. **Treat products, projected poses and rendered images separately.** A
   product LUT retains live geometry. Prepared poses/fragments reduce the
   runtime geometry problem. Generated fill code consumes RAM even if its
   on-disk representation compresses well.
6. **Use bounded palette composition honestly.** A chosen overlap selector
   or aliased color can emulate a restricted layer order; neither is generic
   alpha blending or a depth buffer.

Applying prefix XOR again to a filled image does not generally clear it.
Reapplying identical XOR markers cancels those markers; that is a different
operation. The current renderer's fused fill/output/marker-reset contract
and per-buffer/per-parity dirty history must remain consistent.

## Latest accepted camera-plane negative experiment: 8 November 2026

[Source/units](3dvibe64-camera-units.md) binds signed-byte X/Y and signed-word
geometric depth in the same units, with eye `E=(0,0,0)`. Object Z=128 is already
included; +190 is a compensated projection-table address origin. All 81
coordinate products, 18 captured vertices and 1,536 linked table bytes match.
Use the prepared `$1153` or fresh `$1441` matrix; completed drawing clobbers
some matrix scratch bytes.

[The classifier study](3dvibe64-camera.md) uses a new closed generated-PRG
case: 81 files / 30,912,553 bytes, 37 RAM/VSF pairs and 12 consecutive rendered
poses, each captured at `$1153`, `$1441` and `$08D4`, plus the `$080D` start.
These are rendered poses, not consecutive PAL display fields. The unchanged
renderer's full scalar/native buffers pass for every pose. Strict outward
`N·(E−P)>0` removal preserves the three older windows and ten new windows, but
changes **96 display pixels / 48 bitmap bytes in pose 9**, and **144 pixels /
66 bitmap bytes in pose 10**. Both palettes remain unchanged. Classifier
acceptance is false; these failures remain regression evidence.

Next explain those exact negative-side groups' stock projected/raster coverage
before proposing a conservative rule. Do not fit a threshold to these poses or
hard-code face IDs. No SDK patch, new build or measured saving was made; the
new native case observes the unchanged PRG. Root replay matches all 106 outputs
exactly. The broad goal stays active and Pong is untouched.

[The separate source-convention reference](backface-source-conventions.md)
retains both primary HTML/text bodies and receipts. Exact ideal projection
checks all 120 triangles in 15 windows, containing 13 distinct point clouds;
old first/third repeat new poses 1/3. Pose 9 has negative geometric eye-side
but positive captured projected area; pose 10 has negative values for both
yet leaves visible raster coverage. No unique rounding cause is established.
The ideal identity is a reference, not a substitute classifier pass.

Latest closed experimental checkpoint:
`build/research/3dvibe64-camera/native-01/pose-12-complete.vsf`,
**PC `$08D4`, clock 10183653, raster 29 / raw cycle 18**. This fresh generated-PRG
case has no restore or product patch. The separate user-requested visible
preview is intentionally running: its mutable `preview-01/` is excluded from
the immutable inventory. The dated ownership record and static screenshot
are cosmetic provenance, not experimental timing or pixel evidence; verify
actual ownership before control and leave the viewing process running.

## Preceding accepted offline omission and culling-policy study: 8 November 2026

[The accepted SDK policy audit](3dvibe64-cull-policy.md) reproduces all three
submitted ID sets from captured rotated coordinates and linked integer code.
Third face 7 has cross −17 and passes the active conservative threshold −32,
plus actual depth/sliver checks. The −96 alternative is compiled out. This
explains actual submission, not ideal visibility or a culling bug. The measured
face 1/face 7 draw subtrees total 172,828 cycles (25.56% of the third render),
which is observed work, not a native saving. No new product or native case ran.

[The exhaustive omission proof](3dvibe64-overdraw.md) tests all 64 subsets.
First and second frames require all four observed groups. Third uniquely has
minimum `[2,0,3]`; omitting either or both 1/7 preserves all 8,000 bitmap bytes,
both 1,024-byte palette arrays and 64,000 decoded display indices. Those are
completed-buffer images, not new VIC scanout. Removing 1/7 skips 80 captured
spans and 339 input writes offline, with no modified program or measured saving.
Face 1 is required elsewhere (640 changed pixels in second-frame omission),
so finite equivalence is not a global hard-coded-ID visibility rule.

That checkpoint proposed the camera/plane study now reported above. Its offline
omission and policy results remain unchanged; the newer strict classifier
fails two new image comparisons and is not a replacement policy.

[Normal-plane reading](normal-plane-culling.md) retains the author's PDF and
all three rendered pages. The printed `Y·p+1=0` is inconsistent with its stated
normal Y and vertices `−X+Y`/`X+Y`; exact-rational checks give residual 2 at all 16
endpoints and six threshold disagreements over eight rotations. For the stated
outward convention, `n·(E−P)>0` and eye `E=(0,0,−C)` give `n_z<−d/C`. This is a
printed-example correction and a separate mathematical alternative, not an SDK
sign-bug diagnosis, measured speedup or independently bound 1991 executable.

## Preceding accepted Gouraud cost and three-buffer study: 8 November 2026

[The native profile](3dvibe64-profile.md), using the unchanged linked product
and [accepted stack/continuation anchors](3dvibe64-profile-plan.md), measures
three full render intervals: **590,499 / 543,692 / 676,134 elapsed PAL machine
cycles**. The third is the first B-buffer reuse and costs 34.40 refresh budgets.
Its exact exclusive partition is spans 38.41%, XYQ2 bounds 17.76%, shade edges
16.18%, row setup/dirty tracking 9.20%, material 7.06%, dirty clear 6.29%,
rotation/lazy projection 2.12%, collection/culling 1.34%, lighting 1.03%, other 0.60%.
These include RTS, VIC stalls and IRQ work where it occurred; initiating JSRs
stay in parent residuals. Inclusive fill/helper totals cannot be added again.

All 530 spans pair by actual entry/continuation PC and SP, with actual uniform/
general path counts **28/140,15/144,11/192**. The third pose submits five
pipeline face calls rather than four; why remains a geometry/culling question,
not an open trace interval or proof of five correctly visible faces. Captured
`faceidx=$0D` remains 8 and is not the active face identifier. Keep the call
order and actual span inputs as evidence.

Render-begin periods are 612,884 / 549,791 / 688,964 cycles, including additional
presentation/tick work. No VIC publication or whole-animation/FPS claim follows.
The closed 29-file case has 11 full RAM/VSF pairs, three completed renders and
four begins. Valid Speed=100/InitialWarpMode=0 reads and rejected read-only
queries are retained; current runtime warp was not successfully queried.
The [separate three-buffer pixel audit](3dvibe64-profile-pixels.md) matches
24,000 bitmap bytes and 3,072 bytes each of Screen and physical Color RAM.
Third B begins as the first B image (1,932 nonzero bytes), then is zero before
drawing; a no-clear control differs in 896 bytes. This checks that finite clear
outcome, not the entire dirty algorithm or a new committed VIC field.

The source-latched current face is `$0C`, not loop counter `$0D`. Third-render
groups are `1/7/2/0/3`; group 7 contains 45 nonempty spans and 203 pixel writes,
widths 1–8. These are actual work IDs, not five geometrically visible faces or
a proved culling bug. Next omit selected groups in a NEW offline experiment
and compare final bitmap/palette before changing policy, then choose an exact
edge/span reduction if useful. The source-based cost model uses the older two
samples and remains hypothetical. Even eliminating spans and both edge passes
in a fixed-other-cost model leaves 186,900 cycles (9.51 refresh budgets).

The closed latest endpoint is
`build/research/3dvibe64-profile/native-01/fourth-begin.vsf`, SHA-256
`f31c7ce5b0ef00f8f93727447ea0857640c8d5e184a912fe9b76b3dec968b97f`,
PC `$08CB`, clock 5131747, raster 24/raw 19. Only three completed renders are
accepted; a fourth begin is not a fourth completed image or interval.
Source-plan/native/hypothesis replays are exact. Pixel replay's 16 nonproof
outputs match; JSON additionally normalizes the known output prefix and exact
`reference_reuse.output_root_only_redirected` string. The first comparison
rejection omitted that latter field; production had already succeeded and
was not rerun. The root report retains that qualification.

The [1985 hires article](hires-dither-1985.md) remains a reading lead with no
retained HTML body or fast rotating-Gouraud evidence. Broader research stays
active, with no product speed fix or Pong change in this extension.

## Preceding authored Gouraud build/native baseline: 8 November 2026

The [task-local toolchain](3dvibe64-toolchain.md) built the authored smooth
six-vertex/eight-triangle octahedron with the unchanged pinned SDK, official
PowerShell 7.6.9 and locally compiled 64tass 1.60 r3243. The 49,711-byte PRG,
SHA-256 `69b0d86f79106b2bf9654d85bd631bc68c12f4efd708454a0048560b3c1bfdeb`,
is identical to the symbol reassembly. The [build proof](3dvibe64-build.md)
binds 57 tables / 1,011 bytes in ASM and PRG, including 132 Bayer and 704 light
bytes plus scene normals/center terms. All 387 original SDK files are unchanged.

[Native scalar/pixel acceptance](3dvibe64-native-pixels.md) has seven exact
RAM/VSF pairs (458,752 bytes) and all 49,709 loaded payload bytes exact. Startup
is declared generated-PRG autostart mode 1 loader injection, not an original
1541 disk-load witness. Launch flags request stock PAL/Speed=100/warp off;
there is no explicit runtime resource query. No manual state patches or
snapshot restores follow startup. The owned session is closed and reaped.

Both samples match complete 8,000-byte target bitmaps plus 1,024-byte Screen
and physical Color RAM arrays, using captured baseline/span inputs. Only
sample 2 has publication and all 64,000 committed visible-body indices exact
(rows 51–250, X 32–351). Sample1's rejected breakpoint and same-socket interrupted
resume remain a missing first-publication witness. This accepts rasterization
from captured spans, not independent geometry, clipping, culling, painter/edge
shade construction, clearing or complete lighting transforms. The source is
an octahedron; sample 2's quadrilateral-looking silhouette remains a limit.

Intervals `$1153→$08D4` are 577,195/509,905 PAL-model cycles, about 0.5858/0.5175 seconds.
They include projection, collection/drawing, IRQs and VIC stalls, excluding
earlier lighting/clearing and later wait/publication work. They are partial-loop
costs, not measured delivered FPS. No 50 FPS or acceleration claim is made.

Latest continuation: `build/research/3dvibe64-native/native-01/sample2-visible.vsf`,
SHA-256 `87fc47b7b737644658ac7d548417837054adaff2827612b69bc5d076dd810637`,
**PC `$0FB1`, clock 10276311, raster 252/raw 3**. The existing four case endpoints
remain unchanged. Next use a NEW natural entry/return profile to separate
geometry/setup/span/material costs and classify actual uniform-bulk versus
gradient paths. Existing 28/7 eligible uniform intervals are not branch-hit
measurements. Preserve this slow stock baseline before a bounded optimization;
Pong remains untouched and the broader research backlog is active.

Archives/catalogs cover1,148 extracted regular files; unchanged runtime/SDK
caches are reconstructible and not individually repeated in the manifest.
Actual executed binaries, all command streams/products, the failed partial
catalog/manual failure note, accepted/replay proofs and the closed native case
are retained. Tool/build replay bytes match exactly. Pixel replay matches all
12 other output files exactly and its JSON after only the documented output
artifact-prefix normalization in `root-pixel-replay.json`.

## Preceding Gouraud source and Spires native extension: 8 November 2026

[3Dvibe64](3dvibe64.md), pinned at `b19df459b7efe50d514b59fe876c0bc7c326c5b4`,
has a source-only SDK release with no bundled PRG or example/validation tree.
The source computes runtime normal/light-derived vertex shades and transports
them into a screen-fixed Bayer fill. Independent arithmetic checks cover the
132-byte packed 33-shade LUT, its exact equal-endpoint uniform-span rule,
14,025,231 scalar DDA samples, 704 light entries and 65,536 default affine UV
pairs. No complete normal/light transform, emitted program, native pixels,
stock/accelerated timing or FPS result is established. The optional projective
Mode7 path is outside this default-unlit sampler proof.

[Spires original native FPP](spires-native.md) now binds both original
12,425-byte boot payloads, all 4,550 bytes of 130 macro rows and 4,032
meaningful generated pattern bytes. The first-band MCBASE offsets
`0,3,6,9,12,15,18` and actual source-backed data latches hold over the next
raster line. All 2,640 stores in the selected finite trace windows match.
Seventeen RAM/VSF pairs cover the two closed/reaped fresh original boots.
The failed non-PTY startup has no snapshots or native witness.

Native02's sprite colors are black: its `@io:$D028 != 0` guard accepted
unused `$F0` read bits. Native03 uses the low-nibble guard and observes color
6 (blue) in all seven used sprites, plus a visible screenshot. This is not
an independent committed-pixel compositor. Only the first data band is
observed; the other two bands and TechTech runtime remain open. The frozen
source note's `$ACF8` pointer arithmetic is explicitly corrected to **`$AFF8`**,
with used sprites at `$AFF9..$AFFF`; no frozen file is rewritten.

Spires' latest continuation is
`build/research/spires/native-03/colored-window-complete.vsf`, SHA-256
`96691e36ee0e6aa645cd8be6e116a60297b554894ae8d8cfe9a8678839302855`,
**PC `$A2B1`, clock 77633652, raster 192/raw cycle 12**. Existing No Bounds,
Anomaly and Dragonbond endpoints remain unchanged.

At that checkpoint the next task was tool setup and the Gouraud build/pixel
test. The later accepted baseline above now completes those steps; the current
next task is cost profiling. The archived missing-tool observation and old
source-only limits do not describe the current task-local toolchain.

## Preceding passive source/data extensions: 8 November 2026

[Spires](spires.md) now has positive original/source-ZIP provenance and exact
shared release-D64 identity. Independent source descriptions agree on 4,032
meaningful FPP preparation bytes; slot byte 63 remains unknown. All 40,000
prepared glyph-row bytes verify five coarse translations. The ten charsets
are five horizontal phases in two vertical banks, combined with eight fine
scroll values for 40 positions. The tool/demo LUT differs in 817 bytes; four
main imports are missing and the supplied Mach-O tool was not executed.
That receipt is source mathematics/prepared-asset evidence, not source-build
identity or native timing. The later native proof above separately binds the
first-band mechanism/counters; other bands and committed pixels remain open.


[The published metallic Dragon cartridge](host-3d-2026.md) from pinned
c64-3d-toolkit revision `079b6d8a907bea6242d94296701ad7aa9a11dc73`
contains 128 independently encoded pictures. Independent cartridge and
supplied-oracle paths match **128×8,640 = 1,105,920 bitmap/screen bytes**.
Actual ROMH `LDX #$58` binds the 88-page `$0800..$5FFF` bootstrap input;
uncopied zero padding is excluded. All directory entries and 67 copy-loop/
address-mask bytes bind to the cartridge. No original CPU or upstream tool ran.

Its 5,205-vertex/11,102-triangle model is host input. The selected C64 path
copies literal bitmap spans and absolute screen colors. Twenty-three shared
color runs cover 437 cells, including every changing oracle cell; bitmap
recycling still needs the old picture's clear metadata. Omitting clearing
between the first two pictures leaves 37 wrong bitmap bytes. The maximum
1,894 literal bytes imply a **conditional minimum of 24,622 core cycles**
for the bound copy instructions alone, excluding setup, clear/color work,
IRQs, page crossings and VIC stalls. This is not measured timing or FPS.

[VIC-II-spector's bounded source audit](vicspector.md) matches 32,256 settled
PAL BA-cycle classifications, 32 sprite fetch half-cycle entries, 63 X values
and 29 published MISC instruction annotations against independent official
VICE/Bauer-based models. BA-low CPU stalls are not AEC fetch occupancy; AEC
was not independently compared. The graph's 15/16-line return paths exist
mathematically, while arbitrary artwork and timed MISC encoding remain
unproved. Its explanatory +2/+1 labels are not proof of internal operations.
Seven frozen FPP clear pairs are passively re-decoded as held offsets after
cycle 16, not new native evidence or cycle-15 crunch observations.

That preceding extension added passive source/data analysis only. Existing SpriteFPP,
Anomaly and Dragonbond native endpoints below remain the latest observed
states. Host geometry correctness, native publication/banking and playback
performance remain open; it is a separate toolkit example, not an identified
part of an investigated demo or a change to Pong.

## Latest Anomaly priority and changed-wall extension: 8 November 2026

[Anomaly native08](anomaly-native-priority.md) is fresh original-disk
autostart with no restore. Its three exact RAM/VSF pairs and 43 serialized
commands retain two waiting notices, one same-process/socket navigation
interruption and a rejected read-only WarpMode query. The two proof resumes
are explicitly unwarped at Speed=100. The prior native07 state is a host
prediction input, not this run's execution parent.

At line 110/raw cycle 38, all eight actual sprite states are checked: sprites 0..5
do not obscure sprites 6/7 at X 318..319. Original nonzero row latches and
committed output give **14/14**, while reversed priority gives **1/1**. The
conditional 403-update prediction is thus observed within its stated scope.
The actual VIC bank remains **$4000**, D018=$80, pointers **$63F8**. A separate
oracle address-renaming view transports bytes to the frozen compositor's
fixed addresses; it neither patches native state nor observes a $C000 bank.

Rows **51–151**, **101×384 = 38,784 indices**, match exactly. Current line 152
and later rows remain excluded; this is not a sixth complete 104-row strip.
The new wall differs from native07 in 3,317/4,160 bitmap and 333/520 attribute
bytes; the stale-wall control fails 15,162 pixels. Armed pointer ranges were
$4FF8/$CFF8, not actual $63F8: endpoint table and active original-art latches
are checked, but continuous pointer-write history remains unproved.

Latest closed/reaped continuation:
`build/research/anomaly/native-08/priority-row-committed.vsf`, SHA-256
`09df702e9fcac59d9c81a3ced230a58a7fcc8bbe7296a6b249ed42131f0db992`,
**PC `$B400`, clock 175046267, raster 152/raw cycle 11**. A next new case should trace
actual $63F8..$63FF and capture after rows 152–154 commit, then broaden coverage
and timing. Whole 312-line/FPS or physical-bus proof remains open. The old
five upper outputs over one wall remain frozen; this changed-wall partial
strip is a separate scope.

## Latest visible SpriteFPP extension: 8 November 2026

[Fresh original SpriteFPP native-03](no-bounds-spritefpp-visible.md) closes the
pointer-zero/header distinction and matches **42,560 palette indices** in
one committed **133×320 component**, rows 78–210, columns 32–351. All eight
sprites contribute visible pixels. Native03 has fourteen RAM/VSF pairs,
125 completed commands and a PNG, from a fresh original boot with no restore;
all proof resumes after production entry were unwarped at Speed=100. All
20,261 known production-entry bytes match. The new pointer-zero pairs use
raw cycles 46/50, while native02 used raw cycles 45/49; no reused phase is assumed. Nonzero
header `47 EC 98` is ignored by held offsets 3–24, closing that former gap.

The mature pose is 4, used X layout 59 and gray palette 1. All 72 prepared
X layouts are checked offline; one layout has native scanout proof. Reverse
priority is inconclusive in this component. Whole 312-line frames, all-pose
animation, FPS/timing and supplied standalone execution remain open.

The latest closed/reaped continuation is
`build/research/no-bounds/native-03/mature-window-complete.vsf`, SHA-256
`967f604ebde48b649edee3715ece4b08836710ce091e62de246eb6908e5f6a02`,
**PC `$0CFA`, clock 143600978, raster 220/raw cycle 38**. Its first-fade and mature
rows are separate observations. Continue another pose/layout/palette or a
later phase with fresh component guards. If exact drive/IEC restore continuity
cannot be established, use a fresh original boot; never edit saved state.

## Preceding original-release and native extensions: 8 November 2026

- [No Bounds original release](no-bounds-original.md) identifies CSDb 232957,
  download 246029, and both original ZIP disk images. Repository production
  disks match; the separate SpriteFPP test disk and supplied standalone PRG
  remain distinct. Exact Sparkle 2.3.23.105 byte binding permits the existing
  offline extractor: side-1 bundle 31 matches **20,261 file-known production
  bytes**, including the 50-byte driver. Of the earlier 14,793 geometry-domain
  bytes, 14,790 are file-defined and three header bytes are excluded offline.
- [Original SpriteFPP native-02](no-bounds-native-spritefpp.md) has eleven exact
  64 KiB RAM/VSF pairs from original boot `$0810`, production `$C300`, natural
  return `$08A7`, generated-code entry and cells 62–64. All 20,261 known bytes
  match at production entry; the three previously unknown RAM bytes are
  `47 EC 98`, an observation rather than file-derived padding. The observed
  bank is `$4000` from actual CIA2 PRA/DDR/pins. Twenty-four nonzero sprite
  data triplets match original cached pointers and held MCBASE offsets 3–24.
  `$D017` transitions `FF→00` while expansion flops change `0→1`; the captured
  counters/data hold across the transition and following lines. These are
  PAL-cycle-16 hold witnesses, not a special PAL-cycle-15 crunch proof.
  All 68×24 atlas payload bytes remain original. Of the 4,352 loaded atlas
  bytes, 4,344 are unchanged; eight slot-15 padding bytes at `$43F8..$43FF`
  are the live pointer table. The initial all-zero palette makes this DMA proof, not visible pixels.
- The new SpriteFPP continuation is
  `build/research/no-bounds/native-02/cell64-postclear.vsf`, SHA-256
  `6968c0684eebb7e1a4cd4656e081088b6a762cbe890ad6f15d1eb24b7f9a140f`,
  **PC `$888B`, clock 141197980, raster 141/raw cycle 49**. The owner closed
  and reaped native-02 with exit -15. This is the preceding checkpoint;
  [fresh-boot native-03](no-bounds-spritefpp-visible.md) above supersedes its
  candidate cell-92/header and mature-pixel plan. Native03 deliberately did
  not restore it because [drive restore limits](drive-snapshot-restore.md)
  leave whole-machine equality unproved. Relevant future restore checks still
  include DRIVE8, DRIVECPU0, 1541VIA1D0, VIA2D0 and FSDRIVE alongside the five
  C64 modules. Preserve differences; use a fresh original boot if needed.
  Native-01 remains cancelled navigation with no RAM/VSF pairs or FPP proof.
- [Anomaly native-07](anomaly-native-upper-fetch.md) restores the exact prior
  native-06 endpoint and closes a nonzero active **bank-$C000** bitmap fetch:
  `$E5B3=7E` agrees with saved GBUF and drawpipe state. Its six RAM/VSF pairs
  also bind the observed sprite borrow/wrap branches and a separately checked
  fifth **104×384 = 39,936** upper strip. Together with the frozen four-strip
  receipt this is 199,680 upper indices across five outputs over one prepared
  wall image. The fifth strip has no overlapping upper sprites, so reversed
  priority remains inconclusive. Current continuation is
  `build/research/anomaly/native-07/upper-complete.vsf`, SHA-256
  `2560606a79af78009553dfcfef19d678e5d8eeddc46215aa81c2d4c56eda2474`,
  **PC `$B47B`, clock 167026856, raster 155/raw cycle 59**, owner-closed/reaped.
- Anomaly native-07 restore equality covers the five C64 modules. `DRIVE8`
  and `DRIVECPU0` payloads differ from the parent; full drive/IEC continuity
  is unproved and requires inspection before future continuation. The
  [source-decoded deltas](drive-snapshot-restore.md) identify head-offset
  rescaling and stop-clock resynchronization; the old track-size denominator
  is not serialized, so these explanations do not prove whole-machine equality.
- The host-only `research/anomaly/overlap_plan.py` predicts the earliest
  distinguishing overlap **among upper sprites 4–7 only** after 403 further
  upper updates (predicted counter 527 / `$020F`). At line 110, X 318–319,
  sprites 6/7 predict color 14 versus 1 under reversed priority. This is a
  historical conditional plan; [fresh native08](anomaly-native-priority.md)
  now observes the target with all-eight occlusion and fresh bank/wall/palette
  checks. The planner itself remains a host-only, sprites 4–7 prediction.
- [PlasmaVector](no-bounds-plasma-vector.md) uses 256 prepared projected poses
  and generated character/color sampling. Runtime XOR edge/fill work selects
  high address bytes of color-LUT loads. Its 691 sampler cells, 426 fill/reset
  cells and three color channels are distinguished from bitmap filling;
  971 literal supplied-PRG bytes match. Original-part binding and native
  generated-code/pixel evidence remain open. Historical paused wording in
  frozen notes records the earlier Pong switch; research is active again.
- The five new producer receipts were independently reviewed and replayed
  byte-identical. The current inventory retains all **773** previous artifact
  identities unchanged, including their frozen receipts and rejected cases.
  Earlier extension statements below retain their original proof scope;
  the new original-release and bank-$C000 results supersede their old gaps.

## Preceding extensions: 8 November 2026

- [Anomaly upper scanout](anomaly-upper-scanout.md) matches **four complete
  104×384 upper strips, 159,744 palette indices**, including original sprite
  composition. The moving sprites make four distinct outputs over one shared
  prepared wall bitmap/attribute image. Field 4 joins the frozen same-field
  floor into **200×384 = 76,800** exact indices across raster lines 51–250:
  199 committed rows plus the completed current DBUF row. This closes the
  earlier upper-window composition gap without turning the result into a
  full 312-line frame, new-wall-image, physical-chip or FPS/deadline proof.
  Active nonzero auxiliary fetch latches are earlier bank-$4000 witnesses;
  they are not substituted for unobserved active bank-$C000 fetches.
- [Dragonbond native-03](dragonbond-native-tail.md) restores the exact
  bank-$8000 native-02 endpoint, then follows original control flow for 730
  clocks to **PC `$12A9`, clock 149028968, raster 267/raw cycle 11**, inside
  the music IRQ. All eight successor-tail sprite data latches match. The
  earlier failed main-loop-only observation remains an absent observation
  in its old receipt; this is a new owned continuation with its own lineage.
- [Dragonbond visible bands](dragonbond-scanout.md) independently composes
  the original multicolor bitmap and eight hires overlays across **27 rows,
  10,368 exact palette indices**, including 7,984 nonzero indices. Bands
  126–143 and 148–156 span intermediate/full-pointer handover; rows 144–147
  remain excluded. The first captured DMA field has DEN clear and a closed
  vertical border, so its all-black output is not used as visible-picture
  proof. No-sprite, hires-background and premature-successor controls differ;
  reversed sprite priority is inconclusive. Failed bounding-box color and
  priority guards remain archived.
- The [new live observer](vice-live-observer.md) addresses the old pending
  reader/cleanup limitation. Actual wire captures preserve the UTC-collision
  failure, then check the corrected interrupt, natural any-PC stop, queued
  register read, pending close and incremental trace output. The frozen
  sequential helper and all earlier evidence remain unchanged.
- [SpriteFPP](frontier-geometry-20261108.md) binds prepared strip geometry
  to 14,793 supplied PRG bytes and checks 559,104 prepared logical samples.
  Its four constant input rows, 68 strip keys, 57 distinct packed strips
  and 64 prepared poses explain a bounded appearance; that static receipt
  does not establish arbitrary runtime texture mapping. [The later native
  proof](no-bounds-native-spritefpp.md) separately binds original FPP DMA.

## Earlier verified progress: 8 November 2026

The following frozen results retain their original scope. The latest
extensions above supersede the named upper-scanout, successor-tail and
monitor limitations; the original receipts are not rewritten.

- [Anomaly full floor](anomaly-sprites.md): **one complete 96×384 field**
  matches all **36,864 independent palette indices**, including bitmap,
  sprites, fine scroll and borders. This extends the frozen four-strip
  result; the equal pixel totals describe different scopes. Native-05
  supplies completed rows 155–249, actual sprite counter/data latches and
  the first 352 pixels of line 250. The [closed native-06 continuation](anomaly-native-tail.md)
  executes original `INC $D9` in five clocks and completes the last 32
  pixels in current-line DBUF. The former producer and 20-file evidence
  tree remain frozen. Upper-wall scanout and wider timing remain open.
- [Relax24 loader](relax24-loader.md): the uploaded 496-byte drive image
  selects original `00` from request `02 30 30`. Its 13,980 expected wire
  bytes produce 13,820 stores at `$2000..$55FB`, cursor `$55FC` and trailer
  `$080C`. All 21 original file streams agree with independent extraction.
  Sector service, real IEC transfer and reader execution remain unproved.
- [Dragonbond original code/data](dragonbond.md) and [native evidence](dragonbond-native.md):
  the original bootstrap's 4,133 bytes and resident receiver/drive
  installation match. All sixteen released sprite triples use **33 new
  head bytes and 30 old tail bytes**, distinct from the PDF's simplified
  30/33 illustration. Eight saved sprite-0 DMA/data witnesses bind old,
  intermediate and successor bytes in VIC banks `$4000` and `$8000`.
  Bank-$8000 switches hires to multicolor between retained samples.
  The optional raster-267 complete-new-tail observation did not return;
  its queued saves are not evidence. Exact owner cleanup is recorded,
  with no observed child exit code. The owner audit retains 27 RAM/VSF
  pairs, 1,769,472 RAM bytes and 26 completed resumes, separately from
  the one incomplete optional attempt. No full framebuffer or maximum
  nine-line handover window follows from these bounded witnesses.
- [Further primary reading](frontier-reading-20261108.md): No Bounds'
  repeated-bob lattice matches all 10,240 map bytes and reconstructs all
  9,000 visible cells from only the loaded first map. Boundary-repair
  negative controls fail as expected. [Star Wars row functions](frontier-followups-20261108.md)
  bind 295 dictionary tables to a 7,544-byte supplied-PRG block and check
  428,813 truth cases. Two selected lazy-copy exceptions remain visible
  in the receipt; actual text/buffer trajectory and native pixels are open.
- [November primary-source survey](frontier-2026-november.md) retains the
  Dragonbond author illustration, Viva Las Vegas quarter/mirror artwork
  and Tusari 2 shift-plexing mechanism. The new reading did not resolve
  the original Hat or Aloft algorithms. These successes leave the broad
  research objective active.

Current Anomaly continuation is `build/research/anomaly/native-06/floor-line-drawn.vsf`,
SHA-256 `2428affe32e414636d3444b1cfa72f41d25d7e466adf0ff0ad07dbabf28d32c8`,
PC `$B82A`, clock 167013188, raster 250/raw cycle62. The owned session is
closed. Native-05 `$B828` and native-04 `$B400` remain frozen historical parents.

The current completed Dragonbond continuation is
`build/research/dragonbond/native-03/bank80-new-tail.vsf`, PC `$12A9`, clock
149028968, raster 267/raw cycle11. Its new owned session is closed; the
snapshot SHA-256 is `a 8b8558f366e94512c1d6682987e57d5dca63a60a4d79edb1566f457138df7c3`.
The artifact index and [tail audit](dragonbond-native-tail.md) pin its lineage.
The older native-02 endpoint at `$3278`, clock 149028238,
raster 255/raw cycle37 remains the frozen restore parent. Its failed optional
attempt still produced no checkpoint, and its separate owner cleanup remains
explicit. Do not revive either closed handle or call owned cleanup a demo exit.

## Earlier Anomaly native-04 runtime checkpoint

The earlier [native-03 checkpoint](anomaly-native-arcade.md) remains frozen:
natural entry, two floor updates and a rejected upper gate. The newer
[native-04 audit](anomaly-native-upper.md) now records **67 complete
RAM/snapshot pairs, 4,390,912 RAM bytes and three PNG observations**. The
single restore matches every parent RAM byte, the complete MAINCPU payload,
recorded ports/registers, clock and beam. Warp is off and Speed=100 before
all resumes; there is no code/PC patch, replacement payload or synthetic input.

The [independent upper model](anomaly-upper.md) establishes:

- Actual accepted gate: sampled `A=$14`, threshold `$24`, then 14 clocks to
  `$36F3`, with every RAM byte unchanged across that gate interval.
- **13 pixel rows + 13 attribute rows + two new-column jobs**, all captured
  at entry and natural `$3D89` return. All modeled data/state bytes agree;
  the two internal JSR stack pairs remain explicit.
- A separate direct image oracle matches the complete prepared **4,160-byte
  bitmap and 520-byte screen**, independently of replaying the 28 jobs.
- Status is zero before first publication at `$B84B`, clock 166,934,611.
  The `$B864` poststate, clock 166,934,839, matches the swap/pointer/register
  setup. This is a completed first chain, not a universal deadline guarantee.
- Three consecutive floor fields each contain **96 PC/index/value-matched
  `$D016` stores** on raster lines 155..250. Three later `$B857` upper stores
  are separate. The complete floor trace vectors repeat every **19,656
  observer clocks**. B400 entry deltas are 19,656 / 19,659 / 19,656.

The rejected assumption that adjacent trace timestamps must all differ by
63 clocks is archived. Actual per-field observer deltas are 90×63, 2×65,
1×64, 1×70 and 1×62. These coordinates do not certify physical bus-write
phases. The later complete-floor and upper-window proofs above extend this
batch; wider changing-image coverage and a maximum complete renderer budget remain open.

Previous saved continuation (superseded by native-06 above):

```text
build/research/anomaly/native-04/field-04-pre.vsf
SHA256 70fbfcde49a6c1b9a1b18ad538d7e0684cc1c7fdaf2ec6a42b40ad734bbf1b5b
PC=$B400  clock=167006965  raster=152  raw cycle=13
```

The owned session is closed, helper exit 0 / VICE cleanup −15. This is owner
cleanup, not a demo exit. Restore this later state with the same original
disk for further execution, and revalidate full RAM/CPU/beam lineage. Do not
repeat the old accepted-job capture merely because native-03 lacked it.

## Latest Relax #24 checkpoint

The [original archive](relax24-archive.md) and [two packing stages](relax24-decoder.md)
remain frozen: 39,135 outer bytes and 63,486 inner bytes, with hardware
bootstrap instructions excluded. The strict [consumer CPU prefix](relax24-articles.md)
still stops after 235 instructions at the unused-value `$99F2` load of
unknown ordinary RAM `$0223`; that boundary has not been bypassed in a CPU.

The [resource recovery](relax24-resources.md) now consumes all **3,569 input
bytes** at `$8000..$8DF0`, descriptor `27 F1 0D 00 D0`, and writes **9,216
bytes at `$AC00..$CFFF`**. Two functional models agree on every input event,
output store and final format state. All 7,501 match reads reference prior
output. Only the proved dead literal-value dependency is abstracted; no
meaningful unknown byte or hardware input is invented.

Output SHA-256:
`63843ddc392267cc18ac133cefa0f3109332d65cdbfa98d85bcbee00b326b069`.
The actual recovered `$C000` consumer sets up display/interrupt state and
calls a loader at `$AC00`. Its first source request is **`02 30 30`**, whose
name bytes spell `00`. It later derives a JMP target from the transferred
file's final two bytes. Source sites are checked; initialization, transfer
and that trailing entry have not been executed.

The new [loader contract](relax24-loader.md) now closes that command/name,
file-chain and trailer binding at the functional byte interface. Next capture
the real uploaded drive image and successful sector service, then actual
C64 return at `$C15D` with cursor `$55FC`, carry clear and stored-byte SHA-256
`dd8dff99a0f316d5d2a17a98949b738f31fbba6497151d763724a7f386d8fecf`.
The other four embedded resources, initialized reader state, original
article format and coding-review identity remain open. The cached Clarence
review is still unvalidated against original magazine text.

For exact pickup, the uploaded drive program is the inner image's
`$25A8..$2797` copied to drive `$0500..$06EF` (496 bytes), pinned in the
consumer proof. Compare it with the recovered `$AC00..$ACF7` routines.
The retained `side2-files/00.prg` is 13,822 bytes, loads at `$2000`, and ends
in `$0C $08` (word `$080C`). This matches the shape of the trailer contract;
the actual transfer and executed entry remain unproved.

The final resource proof is
`f56b8b0b650d104433c46cea100dd3d08a82e43175a76b43cd7eb10b87a8ca7b`;
its producer is
`3912abac6e607150f87b304f0817d96098feb0fb2faf93faaa664e69823994d4`.

## Latest primary-source and restoration findings

The [primary-source note](primary-2026-notes.md) joins Raistlin's original
No Bounds finite-bob article to immutable source. All eight selected Git
blobs match. Independent asset oracles check all 14,336 clean half-image
bytes, all 28,672 mirrored restore bytes and 46,080 masked-overwrite cases.
Reversing individual bits instead of two-bit multicolor samples fails in
4,523 bytes; replacing masked overwrite with OR-only fails 4,544 cases.
Restoration is scheduled around chosen motion and hidden rows; general
damage clearing, native timing and source-to-release equivalence are open.

lft's Rodents in the Attic is a new primary lead: release 6 June 2026,
author explanation 30 July 2026. Five original caption requests returned
HTTP 200 with empty bodies. No transcript or mechanism was recovered.
The 21-route acquisition inventory keeps its one wrong-slug 404 separate
from those empty responses. Hat/Aloft mechanisms remain unresolved.

The [artifact index](HANDOFF-ARTIFACTS.md) records final receipt and producer
identities, exact restart inputs and the verified current sprite-ball
checkpoint. Research and experiment limitations remain separate.

## Corrections and preferences that must survive handoff

- The target is **Smash Designs' C64 Second Reality**, not Future Crew's PC
  implementation. Its DOS/editor/configuration screens are original C64 code.
  Acquired Windows packer executables were inspected as bytes, not run.
- Three-dimensional research is not a reason to replace the NUFLI viewer.
  Fix actual demonstrated converter/viewer bugs; distinguish them from
  fitting-quality differences and hypotheses about other demos.
- The Swedish save-multicolor-bitmap request was explicitly withdrawn as
  a wrong-chat message. It is not an outstanding feature request.
- The production Anomaly `Link` PRG and same-sized `Parts` PRG differ; use
  the matched Link sections and its symbols. The actual entry is `$3B00`.
- Its late driver is legitimately self-modified: two operand bytes change
  after its eight-page copy. Do not demand a pristine 61-byte driver or
  hide that difference under a broad mutable mask.
- A recorded canonical-tool offset was corrected from `$B802` to `$11B520`.
  The prior source/receipts were archived before repair; payload results
  did not change. Current binary/native notes identify the new pins.
- Earlier rejected decoder gates and unknown-read failures remain archived.
  A fixed checker is not a reason to erase the failed observation.
- A screenshot, a source comment, a code-loop boundary and a coherent
  displayed field are different evidence. Never substitute one for another.

## Continuation order

The current next task is explaining the two strict camera-plane coverage failures.
All other research priorities remain the backlog.

1. Explain why the stock projected/rasterized negative-side groups leave pixels
   in camera poses 9 and 10. Preserve the complete bitmap/palette/display
   regressions, then test a source-derived conservative rule across more poses.
   Units and strict classification have been checked; strict removal fails.
   Do not tune a sample-only threshold or hard-code IDs, change SDK policy, or
   call observed subtree work measured savings.
2. Extend original No Bounds SpriteFPP beyond its checked mature component:
   vary pose, X layout or palette, then guard later Y-pulse/tunnel phases.
   Pointer-zero/header selection and the first visible component are complete.
   Use the latest native-03 endpoint only with verified drive/IEC continuity,
   otherwise use fresh original boot. Preserve the separate standalone scope.
3. Continue Anomaly from closed fresh-boot native08 in a new case. Trace actual
   $63F8..$63FF and capture after rows 152–154 commit to extend the current 101-row
   result to 104 rows. Priority and the changed-wall partial strip are complete;
   wider workload/field coverage and measured deadlines remain open.
4. Bind PlasmaVector to its original loaded part, including resident Mem
   dependencies, then check naturally generated code/LUT updates and pixels.
5. Bind Relax24's recovered loader request `02 30 30` to the uploaded drive
   receiver, follow original `00` and identify its reader/article format.
6. Deepen Second Reality's later effects, the 2003 intro's moving presets,
   and Hat/Aloft/source-scheduling leads, then the broader reading-map queue.
   These priorities do not replace the overall research objective.

Final bounded checks pass within the scopes stated above; rejected
observations and hypotheses remain archived. The whole research goal is
active and incomplete. The continuation prompt names the authoritative files
and exact next observer steps so another chat can proceed without rebuilding
this investigation's history.
