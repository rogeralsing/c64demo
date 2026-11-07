# C64 rendering research checkpoint

Recorded 7 November 2026. This is the consolidated handoff for the research
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

Research is paused at this handoff. The [artifact index](HANDOFF-ARTIFACTS.md)
pins the final producers, receipts and continuation inputs. Resume research
only when requested; the follow-up prompt is ready for that request.

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
alter any frozen research producer or the paused research objective.

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
| [Anomaly upper update](anomaly-upper.md) | All 28 first jobs, first publication and a direct 4,680-byte prepared-image oracle pass. Three 96-write field traces repeat at PAL cadence. | Complete VIC scanout, later workload coverage and worst-case timing remain open. |
| [No Bounds finite bobs](primary-2026-notes.md) | Opaque masked drawing and a mirrored 14 KB-to-28 KB background restore match independent asset models. | Restore scheduling is motion-dependent; source-to-release and native timing remain open. |
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

1. **Dither in edge transitions.** The interlaced prefix proof reconstructs
   screen-aligned face patterns without an interior shading pass. It is a
   host proof, not an integrated assembly result.
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

## Latest Anomaly runtime checkpoint

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
phases. Full VIC scanout/pixel reconstruction, wider update coverage and a
maximum complete renderer budget remain open.

Current saved continuation:

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

Next, bind the uploaded drive receiver's command/name handling to that
request, then follow the actual original `00` file and trailer contract.
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

1. Extend Anomaly's verified first update/publication and three floor traces
   to coherent scanout and wider timing coverage, from native-04's saved
   `$B400` boundary. Preserve observer and physical-bus timing distinctions.
2. Bind Relax24's recovered loader request `02 30 30` to the uploaded drive
   receiver, then follow the original `00` file and its trailing JMP target.
   Identify the actual reader/article format before comparing cached prose.
3. Deepen Second Reality's later effects and the 2003 intro's moving presets.
   Preserve the exact production, setup and evidence boundaries.
4. Follow the newly acquired Hat/Aloft artifacts and nested-IRQ source;
   then continue the broader queue in the reading map. These priorities do
   not replace the overall research objective.

Final bounded checks pass within the scopes stated above; rejected
observations and hypotheses remain archived. The whole research goal is
paused and incomplete.
The continuation prompt names the authoritative files and exact next
observer steps so another chat can proceed without reconstructing this one.
