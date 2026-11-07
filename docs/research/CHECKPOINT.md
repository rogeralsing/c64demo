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
Re-read Git state before acting; this is not a request to amend those commits.

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

The [runtime note](anomaly-runtime.md) and
[capture audit](anomaly-native-arcade.md) own this partial batch. It has
**eleven full RAM/snapshot pairs and two PNG observations**, with one explicit
restore from the earlier HumanMade snapshot. The original program ran to
the guarded NanoCamera/Arcade driver naturally. No code/PC jump, synthetic
input or replacement payload was used.

Host warp was used only for transit to the guarded `$08AE` load call.
`SoundEmulateOnWarp=1` and `Speed=100` were observed. Warp was confirmed off
before the Arcade load-call capture and remained off for the runtime samples.
Two failed read-only `WarpMode` resource queries remain in the transcript;
the working control is VICE's `warp` command. These failures are not missing
captures or successful resource changes.

Already observed and checked:

- Original Arcade payload identity at load return and its real `$3B00` entry.
- Initialized `$3B88` state and the 2,820-byte relocated helper body.
- First floor call: zero carries/coarse lines; **1,589 elapsed clocks**.
- Second floor call: seventy carries, eight coarse lines and 320 bitmap
  stores; **5,207 elapsed clocks**. Fine values, accumulators, insertion
  operands and floor memory match the host model. Other RAM differences
  remain recorded; these are not isolated CPU-cycle measurements.
- A rejected upper gate: sampled `A=$2B`, threshold `$24`. Its return changes
  no RAM byte and takes ten observed clocks.
- Four upper-job execution tracepoints were installed before the first
  floor call. **Zero job hits** occurred in this bounded interval.

**Still not observed:** an accepted upper-copy job, all 28 jobs completing
before publication, the actual 96-store `$D016` field sequence, coherent
display output or a complete measured 50 Hz budget. The runtime source
receipt explicitly says `runtime_witness_complete=false`; closed capture
integrity does not turn that into a completed runtime witness.

The last saved state is:

```text
build/research/anomaly/native-03/upper-rejected-post.vsf
PC=$3D89  clock=164602120  raster=44  raw cycle=4
A=$2B X=$C7 Y=$00 SP=$58  CPU port=$35
```

Snapshot SHA-256:
`db7c7cae5e97a0f0c90229fde26767d162ff3f2dd28f5d2d44e18147644a7449`.
The associated full RAM file is `ram-upper-rejected-post.bin`.
At this point the upper update is still pending: status 1, row 0, first
dispatch `$36F3`, select 0, fine scroll `$C7`; copy sources/destinations are
`$4008→$E000` for pixels and `$6001→$CC00` for attributes.

The owned research session was **closed**, helper exit 0 / VICE cleanup −15.
That is owner cleanup, not a demo exit. Do not wait on its old tool handle
or assume its PID is live. No further execution is needed to preserve this
checkpoint. Future work should restore the saved state in a new owned
session against the same original disk, then revalidate RAM/CPU/beam identity.

## Latest Relax #24 checkpoint

The [original magazine archive](relax24-archive.md) is recovered. Its
side-1 program passes two separate format/CPU contracts: 39,135 outer bytes
and 63,486 inner bytes. Hardware bootstrap instructions remain excluded
rather than mocked. See [the packing analysis](relax24-decoder.md).

The [consumer trace](relax24-articles.md) identifies a 496-byte drive upload,
five actual resource descriptors and a post-resource `$C000` handoff. Its
strict original prefix stops after 235 instructions at `$99F2`, reading
unknown ordinary RAM `$0223`; no output byte is manufactured.

The [resource-format checkpoint](relax24-resources.md) now specifies the
LSB/sentinel stream, length/carry edges, gap tables and the literal path's
dead-value dependency. **Zero embedded resources and zero articles have
been decoded by that new resource lane.** The five-byte-looking side-2
headers and a filename such as `DR` still have no established article meaning.

The next concrete input is `$8000..$8DF0`, followed by descriptor
`$8DF1..$8DF5 = 27 F1 0D 00 D0`. Implement its functional parser with known
memory and mutable overlap. A pure format model may explicitly exclude a
provably unused literal read, but must not feed the CPU an invented byte or
claim continuous original execution through that boundary. Every genuinely
used match input must be known. Only a justified expansion can establish
the later `$C000` reader consumer and enable original article identification.

The cached Clarence review remains secondary analysis and unvalidated
against original magazine text. Recovering it would not make it an AEG/DCP
author explanation of Second Reality.

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

1. Resume Anomaly from the saved `$3D89` state. Capture an accepted upper
   gate/job; follow the 13+13+1+1 jobs to the first publication. Then trace
   and independently explain the 96 floor `$D016` writes and actual cadence.
2. Implement the original magazine's resource parser and obtain a justified
   post-expansion reader. Identify the real article consumer and coding-review
   file before comparing any original article with the cached transcription.
3. Deepen Second Reality's later effects and the 2003 intro's moving presets.
   Preserve the exact production, setup and evidence boundaries.
4. Follow the newly acquired Hat/Aloft artifacts and nested-IRQ source;
   then continue the broader queue in the reading map. These priorities do
   not replace the overall research objective.

All newly performed bounded checks have passed within the scopes stated
above. The whole research goal is not complete and is not declared blocked.
The continuation prompt names the authoritative files and exact next
observer steps so another chat can proceed without reconstructing this one.
