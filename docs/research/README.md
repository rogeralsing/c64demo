# C64 demo rendering research

This archive investigates how released C64 effects work and which techniques fit this project's vector renderer. The scope remains open: finding an impressive effect is the beginning of an investigation, not evidence that its implementation is understood.

Start with [the technique map](technique-map.md) for the cross-production
comparison and compatible transfers. The detailed notes below preserve each
claim's source, original bytes, independent checks, and remaining limits.

## Reading map

| Note | Evidence and practical question |
| --- | --- |
| [Lines and vector filling](lines-and-vector-fill.md) | Author articles, downloadable code, and pinned Next Level sources; packed plotting, run slices, generated spans, sprite vectors, and the distinction between host-generated commands and C64 geometry. |
| [Bit-reversal lines](bit-reversal-lines.md) | Boo author's interpolation algorithm, exhaustive selector checks, and a comparison against our exact DDA. Quantifies speed opportunities and changed pixels without modifying the renderer. |
| [Boo binary analysis](boo-binary.md) | Original bootstrap, generated line-cell template, reconstructed drive payload, and measured selector setup cost under a bounded CPU model. |
| [Frontier demos](frontier-demos.md) | Research cases and further leads, including VIC collision-register computation, drive-only effects, NUFLI, and size coding. Each case separates author explanations from locally reproduced evidence. |
| [Frontier follow-up](frontier-followup.md) | Quondam's bank/palette switch window from original code, the unresolved rain explanation, and a 2024 stretching/counter-scroll lead. |
| [New 2025–2026 primary sources](frontier-2026.md) | Anomaly's budgeted per-line scrolling, Mahoney's prepared bar paths, Carrion's Blender/LZO animation and a new sprite-interleave article. Pinned code/artifacts; runtime and source/build checks remain separate. |
| [Anomaly Arcade Scroller](anomaly-arcade.md) | Complete 2,048-call floor-work enumeration, signed raster gates, upper-wall jobs and original-disk identities. Distinguishes the production Link binary from a different Parts build; native scheduling remains open. |
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

## Evidence rules

- **Visible in a screenshot:** describes the output only. It does not establish bitmap versus character mode, frame rate, hidden-surface algorithm, or runtime geometry.
- **Author statement:** evidence of the author's claim, cited to the specific article, comment, or included note. Do not silently upgrade it to a measurement.
- **Source inspection:** identifies a mechanism in a pinned source revision. Check whether that source is the released build and whether its input is generated on a host.
- **Static binary analysis:** follows identified instructions or a reconstructed stream format. Do not disassemble packed data and call it a renderer.
- **Emulator trace:** records the exact release, entry, memory, and intervention. A PAL VICE result does not prove every real-hardware configuration.
- **Reproduced measurement:** includes the inputs and output receipt, and states which setup or overhead the number excludes.

Downloaded third-party binaries, raw source copies, screenshots, and large receipts live under ignored `build/research/`. Original analysis scripts and notes live under `research/` and `docs/research/`. Each production's note identifies the relevant hashes and source URLs. Third-party downloads are not automatically licensed for redistribution.

## Current investigation queue

1. **Tower Power:** measure complete-stage timing and derive safe transfers from the now-identified sphere, patterned model, and checked line kernels. Keep the earlier simple cube and later stenciled beveled model separate.
2. **The Lab:** extend the matched sprite-vector and open-cube stages to complete timing and additional poses. Keep prepared screen-space commands, palette priority, and any unproved original 3D exporter separate.
3. **Next Round:** extend the now-matched original scene and transparency preparation to full timing and other poses. Its missing exporter remains distinct from the verified runtime rasterizer and input stream.
4. **Boo:** extend the now-confirmed released line kernel and drive selector to native scheduling, transfer, and complete drawing cost. The original selector's same-CPU setup already exceeds the estimated saving of our compatible kernel; offload and register allocation matter.
5. **Transfer to this renderer:** evaluate a compatible line-step kernel with real setup cost and image comparison before changing the production code. The current renderer remains unchanged by this research.
6. **Colors / Lethargy:** extend the first three-phase character/sprite display's exact captured pixel model to other poses, hardware and later effects. Keep analog/display interpretation separate from C64 palette values and measured CPU work. [Investigation](colors.md).
7. **Second Reality / Smash Designs:** extend the matched boot, file sequences, CA dot field and DB two-layer bitmap effect to later effects, especially live-versus-prepared polygon/3D work. CA byte-overwrite behavior is now quantified; full scanout, complete timing and wider hardware remain open. The mock DOS/configuration screens are original C64 presentation. Keep the supplied Ultimate64/SID capture setup separate from original requirements and timing. [Investigation](second-reality.md).
8. **The Impossible Thing:** extend the original 2003 intro's generated glyph writers to its complete affine-coordinate arithmetic and stored-image comparisons. Compare original note claims with measured native buffer selections, keeping scanout/coherent-frame timing separate. [Investigation](impossible-thing.md).
9. **Further frontier cases:** expand NUFLI's one original-player reference and four exact converter exports to additional data, NTSC and physical hardware; deepen A Mind Is Born's asynchronous display/audio analysis beyond its checked IRQ and lifecycle. Extend Freespin's fragments toward loader/video scheduling. Quondam's asset producer and complete independent pixel composition remain open. Extend Nine's matched initialization, character path and two natural Device families toward complete pixel composition, the other detector outcome and physical VIC revisions. Bind The Ghost's 62 original unpacked files to native sections. Extend The Demo Coder's now-identified Rubicon artwork and native raster witnesses to the complete FLD-with-stretch transform; all-eight-row stretching remains unproved. Use Lunatico's recovered WIZ/rain note to identify the original rain code and actual update scheduling; its new explanation video's captions remain unresolved. Continue finding other frontier effects.

These are priorities, not a replacement for the broader research scope. No claim that every relevant demo, blog, article, or implementation has been exhausted is intended.
