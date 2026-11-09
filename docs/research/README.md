# C64 demo rendering research

This archive investigates how released C64 effects work and which techniques fit this project's vector renderer. The scope remains open: finding an impressive effect is the beginning of an investigation, not evidence that its implementation is understood.

For a handoff, start with the [consolidated checkpoint](CHECKPOINT.md) and
the [copy-ready follow-up prompt](FOLLOW_UP.md). They preserve the current
findings, exact saved state, remaining limits and continuation order. The
[artifact index](HANDOFF-ARTIFACTS.md) pins the latest receipts and original
inputs. Research resumed on 8 November 2026; the broad objective remains active.

Start with [the technique map](technique-map.md) for the cross-production
comparison and compatible transfers. The detailed notes below preserve each
claim's source, original bytes, independent checks, and remaining limits.

## Current study: The Hat's all-border upscroll

The original vertical closing text is now identified in **side-B B8/B9**.
The [source scheduling study](the-hat-upscroll.md) explains prepared sprites,
2,000 Y/pointer pairs, two raster programs and CIA1 Timer B's deliberate
stack cutoff. [Disk extraction](the-hat-files.md) and [strict decoding](the-hat-dali.md)
preserve the original-byte chain. [B17](the-hat-ending.md) is a separate
horizontal logo carpet and must not substitute for the named effect.

The [closed original-B native02 custody](the-hat-upscroll-native.md)
binds all 43,008 B8/B9 bytes at two natural boundaries and captures both
raster program variants. [Original side-A/side-B native01 custody](the-hat-native.md)
separately binds B17. Both cases retain 19 complete RAM/VSF pairs and pass
independent root replay: native01 three files/986,426 bytes; native02 four
files/4,346,135 bytes. Every late trace record after an interrupt request
remains checked, and each interrupted phase stays explicitly rejected.

Next independently reconstruct the executed pointer, X/Y, color and border
writes for both B8/B9 program paths, then compare with the native contexts.
Full displayed-pixel reconstruction, whole-animation cadence and physical
hardware remain open. Read the current checkpoint/follow-up first; the older
"latest" sections below are historical. Aloft and every earlier backlog remain
active; this does not authorize SDK/Pong/product optimization or FPS claims.

## Latest EOD committed baseline and six software poses: 8 November 2026

[Native custody](eod-output-case.md) accepts fresh original side-1a `native-04`:
80 files / 9,764,629 bytes, 36 exact full RAM/VSF pairs and 270 completed
serialized commands. Both observation waits remain and later complete on the
same process/connection. Actual warp-off/Speed100 queries, source generation,
phase/counter predicates, saved continuations and all checkpoint/trace bindings
pass. The owned process is explicitly closed/reaped; no restore, RAM/register/PC
patch, retry, restart or event filtering occurs.

[Six independent software poses](eod-poses.md) start separately from each
natural begin RAM: a fresh baseline, four further stable poses and one fade.
All 2,048 marker, 2,048 output and 2,048 reset bytes agree per pose. Flat,
ascending/descending, uniform and zero-width paths are exercised. Prepared
source tables, generated crop/plot descriptors, preserved output and old-state
bytes remain declared inputs; the frozen models required no correction.

[Committed display](eod-display.md) binds the new baseline prediction to
**all 16,384 indices in one 128×128 physical rectangle**, `[106,234)×[91,219)`.
Actual nonblank fetch `$73A7=$BB`, live bank `$4000`, screen `$6C00`, charset
`$7000`, Color RAM 9 and palette `[2,10,7,1]` agree. Complete watched history
retains four IRQ register instruction hits with CPU `$01=$35`; RMW hits are
not equated to physical bus-write counts. The wrong Color RAM interpretation
and swapped palette controls differ at 1,564 / 6,124 pixels.

Independent root replays reproduce output-case 2 files / 264,753 bytes,
multi-pose 20 / 283,518 and display 4 / 76,136 exactly. Root source review
finds no material issue. Latest closed endpoint is
`build/research/eod/native-04/p206-cleared.vsf`, SHA-256
`5b8f10721b8318fcf57c4dd0a6f13696d6428d8977ad77f28f7f0367cf534cf7`,
PC `$1753`, clock 479995079, raster 241 / raw cycle 32. A new observation
needs a new owned case and verified startup/continuation; use a fresh original
boot when drive/IEC equivalence is unknown.

Next reconstruct source crop-plan/bounds generation and an uncovered
visibility/clipping boundary, then another committed pose/crop or transition
field. Only the baseline has a displayed rectangle; five extra poses remain
software-only. Physical lighting, arbitrary geometry, every fallback, complete
312-line fields, whole-animation cadence/FPS and optimization savings remain
open. Broad research and all earlier backlogs remain active. The old sections
below retain their original narrower claims and continuation context.

## Latest crop, visibility-boundary and source-gap results: 8 November 2026

[Original crop generation](eod-crop.md) now independently emits all 9,933
prefix and 4,951 clear bytes from fixed original bounds. Complete code and
32 bound bytes agree in 49 earlier post-initialization states. The bounds
are static source constants, not a per-pose box; arbitrary crop safety and
their geometric derivation remain open. Preserved outside-crop state stays input.

[Visibility precision](eod-visibility-frontier.md) distinguishes the released
seven-bit quotient test from exact projected determinant sign. Its declared
positive-vector 1..127 domain contains 476,120 positive-determinant ordered
pairs rejected by equal-code fallback; this is a symmetry count, not arbitrary
native testing or a visible-defect finding. The source predicts 133 remaining
upstream bodies. [New natural boundary custody](eod-boundary-case.md) and
[two complete software poses](eod-boundary.md) now observe phase-1 counters
82/28: native face flags are zero despite exact determinants +6/+13. All
2 KB marker, output and reset bytes per pose agree. Crop descriptors come
from original-only generation, not captured generated code.

The p082 prediction also matches **16,384 committed indices** in
`[212,340)×[91,219)`, a second 128×128 physical rectangle. Its actual saved
fetch is `$7007=$00`, outside the effect span; there is **no inside/nonblank
latch witness**. Both failed in-span observer preconditions, checked sources,
diagnostic and exact two-guard adapter remain retained with corrected failure
attribution. Complete cache/mode/bank/palette/write-history and pixel checks
pass; neither a renderer defect nor four physical bus writes is inferred.

Fresh original `native-06` is closed/reaped: 47 files / 5,423,132 bytes,
20 full RAM/VSF pairs, 148 completed commands and one retained wait that later
completes naturally. `native-05` remains a terminal observer startup rejection
with zero commands/captures. Both native06 manifest formats and their setup
diagnostic remain; only `native-06-files-accepted.json` is acceptance authority.
Root reviews and fresh replays pass: crop 4 files/67,527 bytes, visibility
2/469,405, custody 2/171,029, boundary 14/161,925 and source follow-up 2/117,073.

[The Hat/Aloft primary follow-up](frontier-effects-followup.md) retains 41
HTTP bodies, immutable creator/uploader tree inventories and exact empty/error
caption responses. The named upscroller, three-layer pattern and Kefrens
mechanisms remain unrecovered. HTTP 200 with zero bytes and transcript HTTP
400 do not provide technical contents; no spoken algorithm is inferred.

Next broaden into **The Hat's original side-B ending/loader or a separately
identified Aloft side-2 input-linked effect**, using the retained originals
and refreshed creator/uploader routes. Do not spend the next pass repeating
another EOD software buffer. Keep EOD arbitrary geometry/crop safety,
unobserved trajectory entries, physical lighting, all glyph fetches, full
312-line fields, animation/FPS and savings as backlog. No SDK/Pong/product
work is authorized by these research results; the broad objective stays active.
The older sections below retain their historical narrower scopes.

## Reading map

The [Relax #24 loader contract](relax24-loader.md) now binds original uploaded drive bytes, directory selection, sector streams, escapes and the C64 cursor/trailer. It is a functional contract; resident sector service and physical IEC transfer remain unobserved.

| Note | Evidence and practical question |
| --- | --- |
| [The Hat B8/B9 upscroll](the-hat-upscroll.md) | Prepared sprite data and 2,000 Y/pointer pairs, two source raster programs and CIA1 TimerB stack cutoff. Both original loaded resources are naturally bound; complete executed writes and committed scanout remain next. |
| [The Hat original native02 upscroll custody](the-hat-upscroll-native.md) | Original side-B boot, 19 full pairs, both complete B8/B9 source matches and both timer-cutoff paths; all 75,370 hooks and rejected raster request retained. |
| [The Hat original native01 custody](the-hat-native.md) | Original side-A boot, authentic F1 side-B attach, 19 full pairs, both retained interrupts and all 442,634 trace hooks. Full A00/B17 source equality identifies the separate logo-carpet case. |
| [The Hat original stream directory](the-hat-files.md) | Both original DOS bootstraps and all 62 source-described raw resources; compressed PRGs are inputs, not standalone effects. |
| [The Hat strict Dali decode](the-hat-dali.md) | Eight independently checked stream outputs, exact word-length extension and explicit original-tail/unknown-memory boundaries. |
| [The Hat target-source boundary](the-hat-target.md) | Retained creator-linked code/font routes; catalog names alone supply no ending algorithm or skip key. |
| [The Hat B17 logo carpet](the-hat-ending.md) | Independent prepared atlas, horizontal window and raster cutoff; distinct from the actual B8/B9 vertical upscroll. |
| [EOD fixed crop generation](eod-crop.md) | Original constants independently emit all 14,884 prefix/clear bytes and match 49 saved states. Fixed source bounds close the descriptor-generation gap; arbitrary crop safety remains open. |
| [EOD seven-bit visibility precision](eod-visibility-frontier.md) | Bounded rational-code analysis and 133 source-predicted upstream bodies distinguish source culling from exact projected determinant sign; no visible-defect or full-animation claim. |
| [EOD natural boundary case](eod-boundary-case.md) | Original native06: 20 exact RAM/VSF pairs, 148 completed commands and one retained natural wait. Separate rejected native05 startup and raw/accepted manifest identities are preserved. |
| [EOD two visibility ties and second display](eod-boundary.md) | Two full software poses match original-source crop descriptors; positive determinants +6/+13 still yield native zero face flags. All 16,384 p082 committed indices agree, with an outside/blank saved fetch and no inside/nonblank latch witness. Failed observer preconditions remain explicit. |
| [The Hat/Aloft source follow-up](frontier-effects-followup.md) | 41 retained HTTP bodies refresh creator/uploader tree routes and bound empty/error caption access. Target algorithms remain open; continue into original ending/loader or side-2 instruction/data domains. |
| [EOD original output-case custody](eod-output-case.md) | Fresh original native04: 36 exact full RAM/VSF pairs, 270 completed commands, both retained waits, actual mode queries and natural source/checkpoint/trace bindings. No RAM/PC patch or restore. |
| [EOD six independent software poses](eod-poses.md) | A fresh baseline, four additional stable poses and one fade all match complete 2 KB marker/output/reset buffers from each begin state. Generated crop/plot descriptors and preserved state remain inputs; other geometry/fallbacks remain open. |
| [EOD committed multicolor-text display](eod-display.md) | New independent baseline matches all 16,384 indices of one 128×128 physical rectangle, with actual nonblank fetch, palette and complete watched history. Other five poses are software-only; full fields, animation/FPS and savings remain open. |
| [Lines and vector filling](lines-and-vector-fill.md) | Author articles, downloadable code, and pinned Next Level sources; packed plotting, run slices, generated spans, sprite vectors, and the distinction between host-generated commands and C64 geometry. |
| [Bit-reversal lines](bit-reversal-lines.md) | Boo author's interpolation algorithm, exhaustive selector checks, and a comparison against our exact DDA. Quantifies speed opportunities and changed pixels without modifying the renderer. |
| [Boo binary analysis](boo-binary.md) | Original bootstrap, generated line-cell template, reconstructed drive payload, and measured selector setup cost under a bounded CPU model. |
| [Frontier demos](frontier-demos.md) | Research cases and further leads, including VIC collision-register computation, drive-only effects, NUFLI, and size coding. Each case separates author explanations from locally reproduced evidence. |
| [Frontier follow-up](frontier-followup.md) | Quondam's bank/palette switch window from original code, the unresolved rain explanation, and a 2024 stretching/counter-scroll lead. |
| [November 2026 frontier follow-up](frontier-2026-november.md) | Original Dragonbond author PDF/disk, checked Viva Las Vegas mirrored artwork, and Tusari 2 shift-plexing source/assets; native mechanisms remain separately bounded. |
| [Dragonbond original bootstrap and sprite data](dragonbond.md) | Original 4,133-byte depacker output, installed receiver/drive bytes, and released intermediate sprites with 33 new head bytes plus 30 old tail bytes. The PDF's simplified 30/33 split remains distinct. |
| [Dragonbond earlier native lineage](dragonbond-native.md) | Original-disk boot, exact parent restore and eight sprite-0 data/DMA witnesses across both VIC banks. Its failed optional raster-267 attempt and explicit cleanup remain frozen; the new continuation below extends that boundary. |
| [Dragonbond successor-tail continuation](dragonbond-native-tail.md) | New owned native-03 restores the exact bank-$8000 endpoint and stops naturally at raster 267 inside the music IRQ. All eight successor-tail data latches match; the old absent observation is not rewritten as success. |
| [Dragonbond visible bitmap/sprite bands](dragonbond-scanout.md) | Two disjoint second-field bands match 10,368 palette indices from a multicolor bitmap and eight hires sprite overlays. The first DMA field is black with DEN clear; four timing-sensitive rows and complete artwork remain excluded. |
| [New 2025–2026 primary sources](frontier-2026.md) | Anomaly's budgeted per-line scrolling, Mahoney's prepared bar paths, Carrion's Blender/LZO animation and a new sprite-interleave article. Pinned code/artifacts; runtime and source/build checks remain separate. |
| [Camera-plane classifier and 12 native poses](3dvibe64-camera.md) | Full scalar/native buffers match all 12 poses, but strict geometric removal changes 96/144 display pixels in poses 9/10. The three older windows and ten other new windows preserve images. The negative result rules out this unmodified strict predicate as an image-preserving replacement. |
| [Camera-space units and projection origin](3dvibe64-camera-units.md) | Stored signed X/Y and geometric depth share units; eye E=(0,0,0), object depth already includes Z=128. The +190 table bias is compensated in its divisor. 81 coordinate products, 18 vertices and 1,536 linked table bytes match; drawing-clobbered late matrix bytes are excluded. |
| [Backface-source conventions](backface-source-conventions.md) | Retained Codebase64/CSDb primary bodies and exact ideal-projection identity for 120 triangles in 15 windows / 13 distinct point clouds. Printed signs are checked separately; ideal geometry does not repair the two native-buffer counterexamples. |
| [Offline Gouraud group omission](3dvibe64-overdraw.md) | All 64 subsets tested: the first two frames need all four groups; the third uniquely keeps minimum [2,0,3], omitting [1,7] with bitmap, both palettes and 64,000 decoded pixels identical. No modified code or native speedup; fixed IDs do not define a general culling rule. |
| [Gouraud's active conservative culling](3dvibe64-cull-policy.md) | Third face 7's rotated-XY cross −17 passes the active ≥−32 tolerance; the −96 path is compiled out. Actual depth/sliver checks also pass. Observed subtree costs are work, not savings or a geometric-visibility theorem. |
| [Normal-plane culling reading and sign check](normal-plane-culling.md) | Retained primary PDF/pages, plus exact-rational counterexamples to its printed +1 offset for the stated normal/vertices. A consistent outward convention is supplied separately; the 1991 implementation remains author evidence, not SDK behavior or a speed result. |
| [Three profiled Gouraud buffers](3dvibe64-profile-pixels.md) | All 24,000 bitmap and 6,144 palette bytes match the frozen scalar reference. First B reuse clears 1,932 nonzero bytes; omitting clear gives 896 wrong bytes. Actual face latch is $0C; third face 7 emits 45 nonempty spans. No geometric-visibility/culling-defect or new VIC-scanout claim follows. |
| [Stock Gouraud native cost partition](3dvibe64-profile.md) and [linked boundary plan](3dvibe64-profile-plan.md) | Three complete renders take 590,499 / 543,692 / 676,134 PAL machine cycles. Third-render exclusive shares: spans 38.41%, XY bounds 17.76%, shade edges 16.18%; actual uniform/general paths 28/140,15/144,11/192. Elapsed costs include IRQ/VIC work; the separate three-buffer pixel audit matches, while no speed fix or VIC-publication result is proved. |
| [3Dvibe64 native scalar/pixel acceptance](3dvibe64-native-pixels.md) | Two complete 8,000-byte bitmaps and their palette arrays match a scalar reference from captured spans; sample 2 also matches all 64,000 committed visible-body indices. The 0.586/0.518-second PAL raster intervals are slow partial-loop costs, not delivered FPS. First publication was missed; full geometry/lighting and useful speed remain open. |
| [3Dvibe64 retained toolchain](3dvibe64-toolchain.md) and [emitted build](3dvibe64-build.md) | Official local PowerShell/64tass produced a 49,711-byte PRG and byte-identical symbol build. Independent assembly/PRG checks bind 57 tables / 1,011 bytes, including Bayer/light data and the authored octahedron. Native-pixel acceptance is a separate audit. |
| [3Dvibe64 Gouraud source and arithmetic](3dvibe64.md) | Dynamic source-level vertex lighting, a 132-byte packed 33-shade Bayer LUT and exact equal-endpoint bulk fill. Independent checks cover 14,025,231 DDA samples, 704 light entries and 65,536 UV pairs. The later build/native notes extend this source-only scope; full transform proof and delivered FPS remain open. |
| [Spires original native FPP](spires-native.md) | Original boot, 4,550 macro bytes, 4,032 generated stripe bytes and seven held first-band offsets bind to actual code/data. Distinct black/blue fresh boots retain the failed color guard; corrected pointers are $AFF8. No independent committed-pixel or FPS proof. |
| [Spires source and prepared assets](spires.md) | Original/source ZIP disks match. Independent source mathematics checks 4,032 FPP bytes; prepared assets check 40,000 glyph-row bytes and 5 coarse×8 fine positions. Ten charsets are five phases in two vertical banks. Missing imports, an 817-byte tool-LUT mismatch and native timing remain explicit. |
| [VIC-II-spector source audit](vicspector.md) | Settled PAL BA/fetch/X tables and 29 MISC annotations match independent official-source models. AEC was not independently compared; the crunch graph omits the held-offset path. Seven old FPP pairs are passive reanalysis, not new native captures. |
| [Prepared Dragon cartridge pictures](host-3d-2026.md) | Pinned 2026 c64-3d-toolkit asset: all 128×8,640 bitmap/screen bytes match an independent host-oracle decode, with actual directory and 67-byte copy-kernel binding. The 5,205-vertex input is host-prepared; native playback, geometry correctness and performance remain unmeasured. |
| [The Hat and Aloft source boundaries](february-2026.md) | Original 2026 artifacts and attributed creator notes, with peer guesses kept separate. Recovers Trident's full nested-IRQ example while leaving the targeted border/pattern algorithms open. |
| [Anomaly Arcade Scroller](anomaly-arcade.md) | Complete 2,048-call floor-work enumeration, signed raster gates, upper-wall jobs and original-disk identities. Distinguishes the production Link binary from a different Parts build; native scheduling remains open. |
| [Anomaly original Sparkle payloads](anomaly-binary.md) | Original boot/drive binding to Sparkle 2.3.23.105, 39 independently known bundles and all 41,523 Arcade Link section bytes. Early native payload comparisons preserve bootstrap boundaries. |
| [Anomaly native bootstrap](anomaly-native.md) | Eight exact RAM/snapshot pairs, five PNGs and fifteen early payload domains through HumanMade. The setup-only attempt and corrected source-receipt metadata remain explicit. |
| [Anomaly earlier partial runtime](anomaly-runtime.md) | Native-03 records real load/entry, initialized state, two floor-update models and a rejected gate. Native-04 extends its bounded scope in the later upper/field notes. |
| [Anomaly runtime capture audit](anomaly-native-arcade.md) | Closed eleven-pair continuation, exact restore identity, explicit warp transit and observer audit. Lifecycle integrity does not complete the pending runtime witness. |
| [Anomaly initial coherent floor strips](anomaly-scanout.md) | Four fields of 24 rows and 36,864 independent palette-index comparisons, with real matrix/color/bitmap fetch latches. This frozen strip proof precedes the complete field below. |
| [Anomaly complete floor and sprite composition](anomaly-sprites.md) | One complete 96×384 floor field: all 36,864 palette indices match independent bitmap/sprite composition, including borders, multicolor and overlap priority. The upper-window proof below joins this frozen result. |
| [Anomaly upper-window scanout](anomaly-upper-scanout.md) | Four 104×384 upper strips match all 159,744 palette indices. Field 4 joins the proven floor into one coherent 200×384 bitmap window; the later priority note checks a different wall over 101 rows; complete raster frames and timing remain open. |
| [Anomaly upper-window investigation plan](anomaly-upper-scanout-plan.md) | Preserves the source, mode, buffer and latch questions that led to the upper-window proof. The result note owns the final checked scope and remaining active-fetch limitations. |
| [Anomaly scanout capture lineage](anomaly-native-scanout.md) | Closed native-05 original-state continuation, five RAM/VSF pairs, full register/pointer trace and exact restart state. |
| [Anomaly observed upper-sprite priority](anomaly-native-priority.md) | Fresh original autostart checks all eight sprites and distinguishes color 14/14 from reversed 1/1 at the overlap; 101 committed rows (38,784 indices) match a different wall. Actual pointer-table tracing remains incomplete; the native bank stays $4000. |
| [Anomaly active upper fetch and fifth strip](anomaly-native-upper-fetch.md) | Closed native-07 binds a nonzero bank-$C000 fetch, borrow/wrap motion branches and a fifth 104×384 strip with 39,936 exact indices. The later priority note observes the predicted overlap; this frozen receipt itself has no priority witness. |
| [Anomaly final-row continuation](anomaly-native-tail.md) | Closed original five-clock native-06 continuation completes the last 32 DBUF pixels. Full restore identity, sole RAM delta and current-line output boundary are explicit. |
| [Anomaly upper update](anomaly-upper.md) | All 28 first-update jobs and publication match independent RAM models; a separate image oracle checks the complete prepared bitmap and attributes. |
| [Anomaly earlier upper/field capture audit](anomaly-native-upper.md) | Closed 67-pair continuation, first publication and three 96-write floor traces. The later upper-window proof extends this audit's old scanout boundary; worst-case timing remains open. |
| [Sprite interleave](sprite-interleave.md) | Rolled/duplicated sprite rows, SAX pointer updates, all sixteen Memento Mori artwork frames and The Dive's three woven sets. Packed layout and static costs are checked; native DMA timing remains separate. |
| [No Bounds original release](no-bounds-original.md) | Genuine two-disk release, exact Sparkle 2.3 binding and bundle 31: all 20,261 file-known production driver/part bytes match. The supplied Parts PRG has a separate standalone wrapper. |
| [No Bounds visible SpriteFPP component](no-bounds-spritefpp-visible.md) | Fresh original boot closes pointer 0/header selection and independently matches all 42,560 palette indices in one committed 133×320 component, with all eight sprites visible. Other poses/layouts, complete animation, timing and standalone execution remain open. |
| [No Bounds original SpriteFPP execution](no-bounds-native-spritefpp.md) | Eleven original-boot RAM/VSF pairs bind production entry/return, live bank selection and 24 nonzero sprite data latches across three held-counter cells. Palette-zero captures prove DMA; the later visible-component note adds one independently matched displayed pose. |
| [SpriteFPP native capture plan](spritefpp-native-plan.md) | Preserves source/build distinctions and acceptance conditions. Its earlier binding and first-fetch gaps are closed by the later original-release, DMA and visible-component notes; the static plan remains historical context. |
| [No Bounds PlasmaVector](no-bounds-plasma-vector.md) | 256 prepared projected poses, generated color-LUT sampling and 971 literal supplied-PRG bytes. The runtime XOR/fill selects LUT high bytes; original loaded-code and native-pixel binding remain open. |
| [No Bounds loading](no-bounds-loading.md) | Twenty 2,000-byte strips in four resident buffers, exact File/Mem plan, bytewise music synchronization and the specific fade/loader/RTS handover. Original-disk timing remains open. |
| [No Bounds repeated-bob screen lattice](frontier-reading-20261108.md) | A 144-character shared image and ten screen views: all 10,240 supplied map bytes and 9,000 synthesized visible cells match independent constructions. Original-disk equivalence and native publication remain open. |
| [Star Wars scroller row functions](frontier-followups-20261108.md) | A 7,544-byte dictionary/table block in the supplied PRG and 428,813 AND-composition cases match. Two lazy-copy exceptions remain explicit; actual cyclic-buffer trajectory and displayed pixels are unproved. |
| [SpriteFPP prepared strip geometry](frontier-geometry-20261108.md) | All 68 sprite slots, 64×91 prepared row indices, metadata and 133 pointer cells match 14,793 supplied PRG bytes. An independent interval oracle checks 559,104 prepared samples. [The later original native proof](no-bounds-native-spritefpp.md) binds captured FPP DMA, and the visible-component note adds one pose/layout/palette; live geometry, wider animation and timing remain separate. |
| [Drive snapshot restore limits](drive-snapshot-restore.md) | Source-decoded DRIVE8 head-offset and DRIVECPU0 stop-clock deltas explain the observed restore path without proving whole-machine equality. Preserve exact snapshots; if drive/IEC continuity cannot be established, use a fresh original boot. |
| [Cancellable VICE observations](vice-live-observer.md) | A new observer retains incremental wire bytes, accepts interruption/close while a command waits and reaps only its own process. Real captured JSON/wire cases preserve the rejected UTC-collision run; the frozen sequential helper remains unchanged. |
| [The Demo Coder](demo-coder.md) | Original 40-track disk, all 68 complete in-place images, preserved raw tails, reachable raster candidates and a checked 50-case bank/bitmap selector family. Stream 46's artwork is Rubicon; complete stretching and whole-effect timing remain open. |
| [The Demo Coder native bytes](demo-coder-native.md) | Original disk boot, complete stream-46 image, finite initialization and selector checks; all 36 raw RAM/full-snapshot pairs match exactly. Later observations remain separate from causal oracles. |
| [The Demo Coder raster mechanism](demo-coder-raster.md) | Native selector/continuation traces, before/after DMA witnesses, RC progression, a late badline pulse and explicit control limits. Complete all-row stretching remains unproved. |
| [The Demo Coder stored artwork](demo-coder-assets.md) | Stream 46's Rubicon picture matches all 57,344 represented pixels under a palette mapping; byte-row copies and screen overlap explain why ordinary full-bitmap decoding is insufficient. |
| [VICE trace timestamps](vice-trace-timing.md) | Pinned emulator source explains deferred watchpoint clocks, RMW dummy writes, endpoint truncation and debugger queues that survive snapshot restore. |
| [Quondam Tunneling](quondam.md) | Original multicolor-text assets, CIA2 direction-register bank selection, alternating palette/memory store windows, and native register witnesses. |
| [Quondam raster mechanism](quondam-raster.md) | Native late row-counter wraps, forty cached screen codes across twenty-four bands, exact VICE snapshot schemas, and controls that retain the measured TOD-phase differences. |
| [Freespin](freespin.md) | Pinned author material, reconstructed drive-only payloads, original GCR decoder checks, and a released 64-cycle video fragment. |
| [Lunatico rain](lunatico-rain.md) | Original technical note recovered through its own decoder: WIZ/character graphics animate ripples while bumpmapping runs slower. The new video's transcript and original rain code remain separate gaps. |
| [NUFLI's embedded viewer](nufli.md) | Mufflon 1.0 source matched to four packaged pictures; generated raster code, bitmap/sprite ownership and independently decoded logical samples. Native timing remains separate. |
| [NUFLI native validation](nufli-native.md) | Original Smoking Fish viewer and the converter's current fitting/export pipeline: exact bytes, two original-player captures and three current-export captures. Corrects the research checker's ordinary-bitmap crop assumption. |
| [NUFLI converter variants](nufli-converter-variants.md) | Four exports and twelve native captures, every pixel checked; fixes the actual application's screenshot-verifier socket race with four regression tests. Keeps fitting quality separate from export consistency. |
| [A Mind Is Born](a-mind-is-born.md) | Released 256-byte intro, exact payload/state overlap map, original IRQ arithmetic and independently checked visual operations. |
| [A Mind Is Born native validation](a-mind-is-born-native.md) | Normal original startup, complete relocation, a captured IRQ's all-RAM transition, native visual observations, inherited timer cadence and terminal reset-vector path. |
| [Nine](nine.md) | Author explanation and investigation map: character replacement, idle graphics, crunched sprites, pointer banking and DMA constraints. |
| [Nine binary analysis](nine-binary.md) | Original unpacker, nine relocation blocks, three generated raster families and matched timing templates, with bounded CPU checks. |
| [Nine native initialization](nine-native.md) | Normal original startup, physical RAM/snapshot pairs, all relocation blocks, actual character ROM and generated raster code. Later runtime captures remain observations unless independently checked. |
| [Nine character replacement](nine-character-path.md) | Original 3×3 character stamping, font transposition, scripted representation switch, IRQ publication and exact native screen/Color RAM transitions. |
| [Nine Device raster trace](nine-device.md) | Natural clipped and complete generated-cell calls, timed register/ghostbyte stores, temporary SAX/RTS patches and restoration, with an untraced snapshot control. |
| [Ghostbyte shine-through](ghostbyte-shine-through.md) | Trident's pinned article and two original teaching examples; bounded CPU checks and an exhaustive ideal shared-mask compositor. These examples are not the full released scroller. |
| [The Ghost](the-ghost.md) | Original two-disk release, author notes, older Bitfire directory, all 62 files depacked through the original API, and bank-aware first-scene ghostbyte anchors. Native matching remains open. |
| [Assembler macro scheduling](macro-scheduling.md) | Trident's original IRQ-continuation and protothread example, unchanged assembly, 1,001 all-RAM sequence checks and 16 synthetic IRQ entries. Distinguishes source organization from unrolling and hardware timing. |
| [Tower Power sources](tower-power-sources.md) | Separates the 1993 92% and 1994 100% releases; decodes the included note and checks shared files across mirrors. The following binary notes identify the sphere and patterned cube. |
| [Second Reality / Smash Designs](second-reality.md) | Original C64 remake, matching author/CSDb disks, independently recovered boot image and AEG's embedded note. The mock DOS/editor is part of the C64 production; per-effect rendering remains under investigation. |
| [Second Reality source survey](second-reality-sources.md) | Primary recollections and separate 2003 glyph-rotozoom explanation, with contemporary review leads and failed acquisitions kept distinct from 1997 algorithm evidence. |
| [Relax #24 original archive](relax24-archive.md) | Original contemporary magazine ZIP, exact single-entry LYNX extraction and 21 valid side-2 file chains. Article decoding and cached-transcription comparison remain open. |
| [Relax #24 reader boundary](relax24-reader.md) | Literal wrapper/table copies, strict startup hardware stop and backward bit/LZ format. No original article or coding-review file has yet been decoded. |
| [Relax #24 packing stages](relax24-decoder.md) | Exact outer 39,135-byte and inner 63,486-byte recovery against original pure decoder instructions. Hardware startup and original article identification remain separate. |
| [Relax #24 resource consumers](relax24-articles.md) | Original drive installer and five embedded-resource descriptors, followed to a strict unknown-RAM boundary. No article filename or side-2 header meaning is inferred. |
| [Relax #24 resource recovery](relax24-resources.md) | Two functional models recover 9,216 bytes at AC00..CFFF from all 3,569 compressed bytes. The actual C000 loader issues request 02 30 30; drive-side filename binding and articles remain open. |
| [Primary notes and finite bobs](primary-2026-notes.md) | No Bounds' original masked bob plotters and mirrored background restoration match independent asset oracles. Hat/Aloft mechanisms and Rodents' explanation transcript remain unresolved. |
| [Second Reality disk map](second-reality-disk-map.md) | All 71 PRG chains, inaccurate displayed block counts, exact INFO1SDS note/font corroboration and 21 literal credit blocks. |
| [Second Reality bootstrap](second-reality-binary.md) | Strict unknown-padding stops, file-derived relocation and 60,152 independently reconstructed bytes matching the original native handoff. |
| [Second Reality native boot](second-reality-native.md) | Nineteen exact RAM/snapshot pairs, original note viewer, recorded synthetic scan inputs and two explicitly rejected timeout observations. |
| [Second Reality first parts](second-reality-parts.md) | Six original files and seven exact payload comparisons, phase-specific loader calls, source-padding limits and CA staging distinguished from execution. |
| [Second Reality native continuation](second-reality-native-parts.md) | Twenty exact RAM/snapshot pairs, recorded SID selection and restore branches, real loader witnesses and four logical dot-field iterations. |
| [Second Reality CA dot field](second-reality-ca.md) | Exact 35,456-byte generated plotting bank, cached-address clearing, stored profiles, live position updates and a scoped draw/update comparison. |
| [Second Reality CA coverage](second-reality-ca-coverage.md) | Clipping sinks, byte collisions and interleaved clear/plot overwrites explain why 459 requested eligible samples become 397 stored samples. OR/XOR alternatives change the endpoint. |
| [Second Reality next preload chain](second-reality-da.md) | DA/DB/EA/EB payloads, actual DB entry, preserved non-file gaps and loader-backup copy, all bound to original bytes and native captures. |
| [Second Reality native next stage](second-reality-native-next.md) | Eleven exact RAM/snapshot pairs, one restore, zero synthetic inputs and four logical DB update observations. |
| [Second Reality DB bitmap layers](second-reality-db.md) | Two complementary one-bit source layouts, 32 KiB of prepared data and 6,144 independently indexed OR/store operations per checked update. |
| [Second Reality EA/EB bridge and EC transform](second-reality-ea.md) | Natural relocations, 16 KiB source-plane preparation, sibling generated character samplers and 2,976 predicted packed stores. The CPU proof preserves its mapped-ROM boundary. |
| [Second Reality native EC continuation](second-reality-native-ea.md) | Fifteen exact RAM/snapshot pairs, complete restore identity, five PNGs and an audited continuation with zero new inputs or code/PC edits. Joins all source checks without broadening them to full-frame proof. |
| [The Impossible Thing](impossible-thing.md) | Separate 2003 4 KB intro: native-matched decode, 29,184 generated writer bytes and one exact stored-image update. Sampled selections take about 58,600 PAL clocks; the 25 fps note claim remains distinct. |
| [The Impossible Thing affine sampler](impossible-thing-affine.md) | Independent texture/coordinate model matches all new glyph/matrix bytes. Q8 signed shortcuts and packed carry rules are explicit; native acceptance covers one static initial preset. |
| [Tower Power binary investigation](tower-power-binary.md) | Boot, loader, and depacker evidence from the original final release, with reproducible local artifacts and explicit gaps. |
| [Tower Power depacker](tower-power-depacker.md) | All 42 custom streams checked against execution of the original depacker; reconstructed payloads and entry vectors. |
| [Tower Power sphere mathematics](tower-power-n2-math.md) | Exact 16 KB product-table formula, self-modifying rotation, orthographic scaling, and mirrored mesh coordinates, checked against original CPU code. |
| [Tower Power sphere palette](tower-power-n2-palette.md) | `FF` outside pixels, separate zeroed markers, and black in Color RAM free all three global registers for face colors; generated code checked against native RAM. |
| [Tower Power patterned cube](tower-power-f1.md) | Native F1 model selection, perspective tables, 24 body vertices plus 15 coplanar stencil points, and the large cyan face triangles. |
| [Tower Power line kernels](tower-power-lines.md) | Packed-byte collection, biased integer DDA, generated entry/exit patches, and original-CPU cycle comparisons with our current sampler. |
| [The Lab](the-lab.md) | The 2026 Elysium release, recovered author note, native green sprite-vector stage, and matched multicolor open-cube script. |
| [The Lab binary candidate](the-lab-binary.md) | Original side-2 decompression, span-mask routines, 16 dither densities, and sprite-shaped output storage; native stage matching remains separate. |
| [The Lab sprite vectors](the-lab-sprite-vectors.md) | Matched one-bit expanded-sprite canvas, seven bands, density materials, prepared triangle/span inputs, and complete native display-buffer checks. |
| [The Lab multicolor vector engine](the-lab-mms.md) | Prepared edge/slopes commands, generated XOR-prefix bitmap fill, native open-cube frame comparisons, and restricted opaque overlap through aliased palette selectors. |
| [Next Round](next-round.md) | Performers' 2026 fullscreen vector effect, published renderer source, patterned shading, and transparency questions. Keep the standalone renderer dataset distinct from the production scene. |
| [Next Round scene preparation](next-round-scene.md) | Original 536-frame command stream, nonconvex prepared fragments, interval/overlap audit, and the matched transparent-looking cube pose. |
| [Next Round original-renderer timing](next-round-timing.md) | Original disk-3 capture: 536 draw bodies and 535 complete periods. Accepted analysis partitions 31,951,837 cycles; selection cadence spans 1–9 PAL fields (535 initial-inclusive / 534 changed-only intervals). Root replay matches all four outputs. This is a prepared 2D fragment stream, distinct from the SDK's runtime Gouraud geometry/lighting. |
| [One-Der complete captured scalar raster](one-der-raster.md) | Independent gradient→edge→span pipeline matches all 2,048 target bytes, 384 workspace bytes (273 computed / 111 seeded untouched) and 32 offset bytes. Every consumed row is freshly generated. One captured four-triangle buffer, not committed VIC scanout or other-pose acceptance. |
| [One-Der signed gradient arithmetic](one-der-gradient.md) | Pure byte/word scalar matches 32 native output bytes and four carry bits, preserving the original divider's nonideal guards/overflow. Domain probes are scalar findings, not additional native calls. |
| [One-Der column-major display map](one-der-display-map.md) | Bijective 2 KB mapping, 1,792 screen and 1,792 color checks, plus two cached multicolor-text rows. Source canvas is 64×128 selectors / nominal 128×128 physical pixels; the raster-178 text-to-bitmap transition prevents a full-scanout claim. |
| [One-Der original runtime Gouraud](one-der-gouraud.md) | Original boot and 14 RAM/VSF pairs bind runtime triangle gradients, 10,240 compared shade-LUT bytes and one exact 13-cycle packed byte plot. Rotated third attributes are not independently proved N·L lighting. Later scalar notes close one captured gradient/edge/buffer path; committed display and wider poses remain open. |
| [Edge of Disgrace original frame and common prefix](eod-frame.md) | Fresh original boot supplies fifteen exact RAM/VSF pairs. The independent whole-frame marker prediction feeds common reconstruction: all 2,048 output bytes match, with 1,650 computed and 398 preserved incoming bytes. The incoming crop plan remains an input; actual VIC fetch/palette/publication and other poses remain open. |
| [Edge of Disgrace complete contour/marker prediction](eod-contours.md) | Chains original frame-entry angles through independent geometry, 78 freshly computed intersection cells, 26 internal lines and six outer edges. All 2,048 marker bytes match, including 17 incoming nonzero bytes. Endpoint, slope and zero-seed controls fail; this is one in-range pose, not arbitrary clipping or displayed pixels. |
| [Edge of Disgrace coefficients, vertices and visibility](eod-geometry.md) | From one original frame-entry state, source-exact scalar stages match 128 declared bytes and regenerate 3,328 table bytes. Runtime angle/coefficient/projection arithmetic uses prepared word/scale and generated quarter-square tables; depth supplies shade bins. No separate normal-light law or all-pose/whole-RAM claim. |
| [Edge of Disgrace original controller and content boot](eod-controller.md) | Fresh side-1a bootstrap installs its own drive service and zero-based load API. All 14 RAM/VSF pairs, complete payloads 51/52 at original load returns and guarded shader/line boundaries match. The wrong earlier $546A overlay remains rejected. Body 58,218 cycles differs from one 98,254-cycle begin-to-begin interval; no delivered FPS. |
| [Edge of Disgrace thirteen-level tracing shader](eod-shader.md) | Original ramp's adjacent XORs occupy one selector field; original tracing code calls specialized zero-site-skipping line paths. Its bounded one-line scalar precedes the geometry/contour/common-prefix extensions above and does not itself prove a frame or speedup. |
| [Edge of Disgrace original files and note](eod-files.md) | Bounded extraction of three original disks, 90 headerless indexed slots: 89 nonempty decoder candidates and one explicitly rejected empty hypothesis. Original 1,968-byte shader-note section matches all 1,440 normalized mirror bytes. Later controller/shader notes bind candidates 51/52; other candidates remain separate. |
| [Edge of Disgrace original native boot](eod-native-boot.md) | Three RAM/VSF pairs bind all 32,862 loaded main-file bytes, 192 original decoder bytes and 63,231 unpacked payload bytes through natural $0900. One completed-wait/inactive-interrupt rejection is retained. Main bootstrap only; no shader, image or FPS result. |
| [Classic Gouraud primary author sources](stock-gouraud-sources.md) | HCL's EOD tracing-line/13-level description and claimed three-of-four zero skips, Mekanix lineage and Browar's Applause statement. The later original EOD scalar pipeline extends the author evidence through one software buffer; actual display, other poses and measured savings remain separate. |
| [Colors / Lethargy](colors.md) | User-requested X'2026 case, released 6 June 2026. Corrected original pack, source survey, Sparkle boot and first three-phase character/sprite display; later effects and analog interpretation remain open. |
| [Colors source survey](colors-sources.md) | Preserved author/group routes, official upload and release comments, with request failures and viewer hypotheses distinguished from credited-member evidence. |
| [Colors original bootstrap](colors-binary.md) | Direct Sparkle 3.4 boot, configured returns and exact resident-copy contract. No substituted Bitfire or Dali interpretation. |
| [Colors native bootstrap](colors-native.md) | Normal original-disk startup, byte-matched boot/resident installation, first payload handoff and same-stop physical RAM/snapshot comparisons. |
| [Colors first-display map](colors-first-display.md) | Four-bank column-ordered hires canvas, three character phases, paired sprite masks, retained pointers, reveal permutation and separate intro/multiplex schedules. |
| [Colors first-display pixels](colors-first-display-pixels.md) | Three native fields match all 184,320 canvas pixels, including measured midline bank changes and custom-GLUE transient fetches; analog blending and other hardware remain separate. |
| [Open panels and our renderer](open-panels.md) | Explains why an exploded cube needs different visibility and overlap handling from our convex, single-fill renderer. |
| [Dither with the interlaced prefix fill](interlaced-dither.md) | Physical row parity allows per-face pattern bytes to enter through edge masks while keeping fill cells unchanged; 512-field host proof and setup-cost limits. |
| [Exact field DDA](exact-field-dda.md) | Carry-based stepping preserves the existing nested-ceil samples; exhaustive endpoint/parity proof, workload estimates, and direction/LUT/RAM integration limits. |
| [You Know the Routine glenz](../yktr-glenz.md) | Earlier binary investigation: immediate EOR fill cells, separate reset, quantized slopes, and display layout. |

The [1985 hires-shading article](hires-dither-1985.md) is a separate pending
reading lead: FACET supplies flat triangle shading; curved primitives are
front-view/no-rotation examples, not fast rotating Gouraud evidence. Its
retrieval metadata is retained, but the HTML body is not.

The earlier 3Dvibe64 reading lead is now a bounded [source/arithmetic
case](3dvibe64.md). Its runtime/native acceptance remains open; it is separate
from the FlyingFathead prepared Dragon cartridge.

## Evidence rules

- **Visible in a screenshot:** describes the output only. It does not establish bitmap versus character mode, frame rate, hidden-surface algorithm, or runtime geometry.
- **Author statement:** evidence of the author's claim, cited to the specific article, comment, or included note. Do not silently upgrade it to a measurement.
- **Source inspection:** identifies a mechanism in a pinned source revision. Check whether that source is the released build and whether its input is generated on a host.
- **Static binary analysis:** follows identified instructions or a reconstructed stream format. Do not disassemble packed data and call it a renderer.
- **Emulator trace:** records the exact release, entry, memory, and intervention. A PAL VICE result does not prove every real-hardware configuration.
- **Reproduced measurement:** includes the inputs and output receipt, and states which setup or overhead the number excludes.

Downloaded third-party binaries, raw source copies, screenshots, and large receipts live under ignored `build/research/`. Original analysis scripts and notes live under `research/` and `docs/research/`. Each production's note identifies the relevant hashes and source URLs. Third-party downloads are not automatically licensed for redistribution.

## Current investigation queue

**Current next task:** bind EOD's independently reconstructed software
output to actual committed VIC fetches, palette selection and publication,
then extend to other poses. One complete original frame's runtime geometry,
depth-derived shade contours, markers, cropped prefix output and marker
reset now match. The crop plan, 398 unwritten output bytes and prior marker
state remain declared inputs. Preserve the rejected earlier $546A overlay
and side-1b T1/S16 empty decode. Do not repeat only that software-buffer
check or promote it to displayed pixels, delivered FPS or savings.
One-Der's gradient→edge→span software-buffer proof is
complete for one captured pose; committed VIC fetches, the raster-178 mode
transition, independent rotation/culling and other poses stay backlog. No
complete scanout, SDK or Pong optimization is claimed.

1. **Tower Power:** measure complete-stage timing and derive safe transfers from the now-identified sphere, patterned model, and checked line kernels. Keep the earlier simple cube and later stenciled beveled model separate.
2. **The Lab:** extend the matched sprite-vector and open-cube stages to complete timing and additional poses. Keep prepared screen-space commands, palette priority, and any unproved original 3D exporter separate.
3. **Next Round:** bounded original-renderer timing is complete; extend committed scanout and other scene coverage if useful. Its missing exporter remains distinct from the verified C64 rasterizer and prepared input stream.
4. **Boo:** extend the now-confirmed released line kernel and drive selector to native scheduling, transfer, and complete drawing cost. The original selector's same-CPU setup already exceeds the estimated saving of our compatible kernel; offload and register allocation matter.
5. **Transfer to this renderer:** evaluate a compatible line-step kernel with real setup cost and image comparison before changing the production code. The current renderer remains unchanged by this research.
6. **Colors / Lethargy:** extend the first three-phase character/sprite display's exact captured pixel model to other poses, hardware and later effects. Keep analog/display interpretation separate from C64 palette values and measured CPU work. [Investigation](colors.md).
7. **Second Reality / Smash Designs:** extend the matched boot, file sequences, CA dot field, DB bitmap layers and EC character texture sampler to later effects, especially live-versus-prepared polygon/3D work. Full scanout, complete timing and wider hardware remain open. The mock DOS/configuration screens are original C64 presentation. Keep the supplied Ultimate64/SID capture setup separate from original requirements and timing. [Investigation](second-reality.md).
8. **The Impossible Thing:** the complete source-coordinate formulas and one static initial preset are now checked. Extend native acceptance to moving presets, phase transitions, other divisors and negative horizontal gradients. Keep the original 25 fps claim distinct from measured selections and coherent-frame timing. [Investigation](impossible-thing.md).
9. **Further frontier cases:** expand NUFLI's one original-player reference and four exact converter exports to additional data, NTSC and physical hardware; deepen A Mind Is Born's asynchronous display/audio analysis beyond its checked IRQ and lifecycle. Extend Freespin's fragments toward loader/video scheduling. Quondam's asset producer and complete independent pixel composition remain open. Extend Nine's matched initialization, character path and two natural Device families toward complete pixel composition, the other detector outcome and physical VIC revisions. Bind The Ghost's 62 original unpacked files to native sections. Extend The Demo Coder's now-identified Rubicon artwork and native raster witnesses to the complete FLD-with-stretch transform; all-eight-row stretching remains unproved. Use Lunatico's recovered WIZ/rain note to identify the original rain code and actual update scheduling; its new explanation video's captions remain unresolved. Continue finding other frontier effects.
10. **Anomaly:** extend native08's 101 committed rows to the full 104-row upper window with the actual `$63F8` pointer-table trace, then broaden wall/workload coverage and timing. The 403-update prediction is now observed from fresh original autostart, with all-eight occlusion checked, priority distinguished and a genuinely changed wall matched. The address-renamed oracle does not change the native `$4000` bank. [Priority result](anomaly-native-priority.md).
11. **Relax #24:** bind the recovered loader's 02 30 30 request to the uploaded drive receiver, then follow the actual 00 file and trailing entry. Original article text and the cached review remain unchecked. [Resource recovery](relax24-resources.md).
12. **No Bounds / SpriteFPP:** extend the now-matched original visible component to other poses, X layouts or palettes, then later Y-pulse/tunnel phases with fresh row-window guards. Pointer 0/header selection and the first mature 42,560-index comparison are complete; complete animation, timing and supplied standalone execution remain open. PlasmaVector separately needs original-part and generated-code/native-pixel binding. [Visible proof](no-bounds-spritefpp-visible.md).
13. **The Hat / Aloft and source scheduling:** analyze the acquired original upscroller/pattern effects and preserve creator-versus-viewer attribution. The newly recovered 2026 nested-IRQ example is a separate general technique, not an identified implementation of either demo. [Source boundaries](february-2026.md).

14. **Spires / planner / prepared Dragon:** first-band original Spires code/data/counter binding is now checked; continue other Y bands, character-mask-aware pixels or TechTech runtime binding. Test VIC-II-spector plans against complete native routines, and bind actual Dragon cartridge publication/display before performance claims. [Spires native](spires-native.md), [planner audit](vicspector.md), [prepared Dragon](host-3d-2026.md).

These are priorities, not a replacement for the broader research scope. No claim that every relevant demo, blog, article, or implementation has been exhausted is intended.
