# Runnable effect examples

Each new standalone example belongs in `experiments/<effect>/`, with its own
`README.md`, `main.asm` (or a documented generator entry), `build.sh`, `run.sh`,
and ignored `build/` output.
Reuse shared code when its display and rendering contract fits the effect.
Keep original research inputs and receipts under `build/research/` intact.

## Build the examples

From the repository root:

```sh
rtk proxy python3 experiments/build-all.py --list
rtk proxy python3 experiments/build-all.py
rtk proxy python3 experiments/build-all.py root:painted sprite-ball:hexagon
```

The runner builds the twelve root targets, all three sprite-ball variants,
and every immediate `experiments/<name>/build.sh` folder. New folders appear
as `experiment:<name>` in `--list`; nested archived builds are excluded.
Builds run sequentially without launching an emulator. A failed build does
not skip later targets, and any failure gives a nonzero final exit status.

Each run retains per-target logs, copied runnable images with SHA-256 hashes,
and `receipt.json` under `build/examples/<UTC timestamp>/`. Existing receipts
and output trees are not cleaned. Standalone build scripts must write their
`.prg`, `.d64`, `.d81`, `.g64`, or `.crt` output beneath their own `build/`.
A successful assembly is build evidence; native playback needs a separate check.

The root targets are `cube`, `filled`, `icosahedron`, `interlaced`, `dither`,
`tonal`, `gouraud`, `fast`, `glenz`, `painted`, `pong`, and `raster`, selected
with the `root:` prefix. [Sprite-ball](sprite-ball/README.md) supplies
`hexagon`, `baseline`, and `golden`, selected with the `sprite-ball:` prefix.

The twelve root implementations also have standalone entry folders, including
[vector-cube](vector-cube/README.md), [filled-cube](filled-cube/README.md),
[glenz](glenz/README.md), [painted-cube](painted-cube/README.md),
[pong-cube](pong-cube/README.md), and the seven raster/icosahedron variants.
These entry files import shared source instead of forking it. Each folder
builds `build/example.prg` through its own `build.sh`. The common launcher calls
that complete build first, including generated inputs, then starts VICE.
The runner rejects assembler assertion failures and unchanged stale output.

## Effect inventory and implementation status

This inventory records the selected documented contracts for this example pass. A research note, original
binary, source fragment, or related renderer is not a completed standalone
example. New examples need runnable output and their own bounded validation.
Each new implementation explains its relation to the documented mechanism,
prepared inputs, actual runtime work, measured cadence, and remaining gaps.
An independent teaching implementation does not claim to clone a production.
The [research reading map](../docs/research/README.md) and
[checkpoint](../docs/research/CHECKPOINT.md) own the evidence and remaining limits.

| Production or technique | Documented effect | Local example status and source |
| --- | --- | --- |
| Our vector renderer | Wireframe cube, solid XOR cube, glenz, painted cube, Pong cube, solid/interlaced/dithered/tonal/Gouraud icosahedron, raster bands | Existing root targets; [renderer documentation](../README.md). They are separate from reproductions of other productions. |
| Our sprite-ball | Live projected hexagons or pentagons over an MCI background | Existing [sprite-ball](sprite-ball/README.md), with three build variants. |
| Our bitmap ribbons | Joystick-controlled vertical and horizontal Kefrens-style ribbons | Own [bitmap-kefrens example](bitmap-kefrens/README.md), with six overlapping ribbons, double-buffered bitmap output, and port-2 controls. Its documentation records native image and input checks. |
| Tower Power N2 | Rotating polygon sphere, product-table geometry, packed DDA, three face colors | Own existing [icosahedron-fast counterpart](icosahedron-fast/README.md) uses reusable model-specific products and live 3D geometry. Its current PRG matches the retained 512-presentation native proof. Original N2 orthographic geometry, packed DDA and palette differ explicitly. [Mathematics](../docs/research/tower-power-n2-math.md), [palette](../docs/research/tower-power-n2-palette.md), [lines](../docs/research/tower-power-lines.md). |
| Tower Power F1 | Morphing/patterned cube with face subdivisions | Own [morphing-cube example](morphing-cube/README.md); live 3D cut, rotation, perspective and face stencils checked over 66 native poses. Uses a new 24+18 mesh and runs at about 5.5 updates/s. [F1](../docs/research/tower-power-f1.md). |
| You Know the Routine | Glenz/XOR polygon filling | Own [glenz example](glenz/README.md), sharing the existing runtime renderer. It demonstrates the technique rather than cloning the production. [Binary investigation](../docs/yktr-glenz.md). |
| Next Round | Fullscreen patterned vectors, two cubes and prepared visible fragments | Own [prepared-fragments example](prepared-fragments/README.md); prepared visible fragments, shared interior glyphs, private boundary allocation and a natural capacity guard checked natively. Reference implementation runs at about 1.4 updates/s. [Renderer](../docs/research/next-round.md), [scene](../docs/research/next-round-scene.md). |
| Next Level `doublevec` | Host-prepared geometry with C64 span rendering | Own [double-vectors entry](double-vectors/README.md) shares the independently verified prepared-fragments engine: host geometry/visibility, live C64 edge/span rendering. Its allocator differs from the original Next Level filler. The two local entries intentionally build identical programs. [Lines and vector filling](../docs/research/lines-and-vector-fill.md). |
| Next Level `nonconvex` | Runtime geometry and generated span cases | Own [nonconvex-vectors example](nonconvex-vectors/README.md); live transformed genus-one frame, exact edges and 512 genuinely generated span cases. All 64 poses, independent depth/occlusion, 40,626 dispatches and 66 complete native images checked. About 2.82 poses/s. [Lines and vector filling](../docs/research/lines-and-vector-fill.md). |
| Next Level `TransBox` | Paired-sprite trajectories, character/Color RAM shifts and a 2D transition | Own [sprite-character-transition example](sprite-character-transition/README.md); paired sprites, live opposite character/Color RAM shifts and border expansion/quadrant wipe. Both complete 192-field screen cycles pass native pixel and state checks. Original charset art and released timing are not copied. [Source boundaries](../docs/research/lines-and-vector-fill.md). |
| Next Level `bobvector` | Prepared point cloud with depth-sized stamps, allocated glyphs and selective clears | Own [depth-bob-cloud example](depth-bob-cloud/README.md); prepared 56-point surface lattice and nine depth sizes, live allocated glyph stamping/OR merging and generated selective clears. All 64 poses plus wrap pass native pixel, overlap and ownership checks. Geometry is host work; about 7.56 poses/s. [Source boundaries](../docs/research/lines-and-vector-fill.md). |
| SMGF / Snapshot | Sprite-based filled vectors and Sprite Masking Gap Filling | Own [smgf-vectors example](smgf-vectors/README.md); four stretched edge sprites and four genuine gap underlays, with independent polygon/priority composition and native counterfactuals. All 65 fields match; prepared poses publish every four fields. [Source survey](../docs/research/lines-and-vector-fill.md). |
| The Lab sprite vectors | Expanded sprite carpet, triangle/span packets and sixteen density materials | Own [sprite-vectors example](sprite-vectors/README.md), with prepared triangles/spans rasterized on the C64 into a shared 144×63 logical sprite canvas. Both buffers, all density materials and 33 native screenshots checked. [Sprite vectors](../docs/research/the-lab-sprite-vectors.md). |
| The Lab MMS | Multicolor XOR-prefix vectors, open cube and bounded palette priority | Own [open-panels example](open-panels/README.md); six detached cube panels, multicolor XOR-prefix filling and bounded palette priority checked across all 64 poses plus wraparound. Runs at 6.25 updates/s. [MMS engine](../docs/research/the-lab-mms.md). |
| Boo! | Sprite-filled cube, BRR line interpolation and drive-side slope preparation | Own [brr-sprite-cube example](brr-sprite-cube/README.md); live cube geometry and generated BRR drawing cells use 594 real 1541 slope/rank requests over all 64 poses. Complete sprite pixels and 2,487 continuous PAL fields checked. Readable reference runs at about 1.33 poses/s. [BRR](../docs/research/bit-reversal-lines.md), [binary](../docs/research/boo-binary.md). |
| Quondam Tunneling | Tunnel using retained screen codes and row-counter/raster changes | Own [row-counter-tunnel example](row-counter-tunnel/README.md); 23 actual cache-retaining row-counter wraps and all four direction-selected VIC banks checked, with six complete native pixel comparisons. Uses four prepared texture phases. Original-production composition remains separate. [Mechanism](../docs/research/quondam-raster.md). |
| Lunatico MISC | Collision-register-assisted sprite crunch | Own [collision-sprite-crunch example](collision-sprite-crunch/README.md); actual collision reads drive sprite expansion writes, with four row-loop lengths and 64 native PAL phases checked. Runs at 50 Hz. [Frontier survey](../docs/research/frontier-demos.md). |
| Lunatico rain | WIZ/character ripple animation with slower bumpmapping | Own [wiz-rain example](wiz-rain/README.md); actual VSP/linecrunch and 10-bit matrix wrap checked over 129 PAL fields, with live C64 central-difference lighting into a hidden matrix. Viewpoint moves at 50 Hz; complete lighting publishes every eight fields. Original code and precise equations remain separate. [Rain](../docs/research/lunatico-rain.md). |
| Freespin | Video and mechanical sound generated by a 1541 drive | Own [drive-video example](drive-video/README.md); real DOS upload to an emulated 1541, VIA video output and Timer1-to-stepper coupling checked across 258 fields. Visible lines take 64 drive cycles; fields take 20,041 clocks. Analog video and physical sound remain separate. [Freespin](../docs/research/freespin.md). |
| A Mind Is Born | Coupled procedural image/music and overlapping state in a 256-byte intro | Own [audiovisual-feedback example](audiovisual-feedback/README.md); 256 native IRQ states, 6,375 SID writes and all 256 cyclic stack/font addresses checked, with real emulated SID audio output. Readable standalone code does not claim the original's 256-byte size. [Original](../docs/research/a-mind-is-born.md), [native checks](../docs/research/a-mind-is-born-native.md). |
| Nine character path | 3×3 character stamping and representation switching | Own [character-stamp example](character-stamp/README.md); sprite-to-character handoff, slot reuse and changed overlap priority checked over fifteen native fields. [Character path](../docs/research/nine-character-path.md). |
| Nine Device | Upper-border generated raster cells, ghostbytes and crunched sprites | Own [upper-border-device example](upper-border-device/README.md); generated upper-border cells, invalid-mode ghostbytes, real sprite crunch and pointer-table seams checked over nine complete PAL fields at one update per field. One explicit PAL 6569 alignment family; original detector outcomes remain separate. [Device traces](../docs/research/nine-device.md). |
| Ghostbyte shine-through | Idle-pattern and sprite-mask composition, two teaching examples | Own [ghostbyte example](ghostbyte/README.md); three native views match 20,160 independently composed lower-border pixels. [Teaching examples](../docs/research/ghostbyte-shine-through.md). |
| The Ghost | Released ghostbyte-based first-scene display | Own [banked-ghost-scene example](banked-ghost-scene/README.md); bitmap art and moving sprite cutouts exercise bank $4000, matrix $6000 and idle byte $7FFF. Seventeen full native fields and two actual bank/input controls match. Original scene identity and exact raster matching remain separate. [The Ghost](../docs/research/the-ghost.md). |
| The Demo Coder | Rubicon FLD/stretch, with layered DYPP/MEGA leads | Own [fld-stretch example](fld-stretch/README.md); actual idle FLD gaps followed by all-eight-row bitmap stretching through CIA2/D018. Checks all 16 live gap/height states across 33 native fields, 2,112,000 pixels and 12,288 stores at 50 Hz. Own [layered-dypp-reveal example](layered-dypp-reveal/README.md) additionally demonstrates counter-scrolling text/art planes, independent column sine displacement and a bytewise aperture over all 256 states. Both layer passes and 257 complete native images match; about 12.31 updates/s. Original scene identity remains separate. [Raster mechanism](../docs/research/demo-coder-raster.md), [artwork](../docs/research/demo-coder-assets.md), [further leads](../docs/research/frontier-followup.md). |
| Colors | Three-phase hires character/sprite display, moving coverage and reveal | Own [three-phase-colors example](three-phase-colors/README.md); three stored glyph phases, CIA2 direction-selected banks, retained paired sprite pointers, moving coverage and bytewise reveal checked over 99 complete native fields at 50 Hz. Analog blending remains separate. [Display map](../docs/research/colors-first-display.md), [pixels](../docs/research/colors-first-display-pixels.md). |
| Second Reality CA | Dot-field plotting with cached-address clearing | Own [dot-field example](dot-field/README.md); 32 native updates and five complete screenshot comparisons. Prepared profiles drive 256 live point requests, with whole-byte collision behavior retained. [CA](../docs/research/second-reality-ca.md), [coverage](../docs/research/second-reality-ca-coverage.md). |
| Second Reality DB | Two complementary bitmap layers and palette overlap | Own [bitmap-layers example](bitmap-layers/README.md); eight complete native bitmap/screenshot comparisons. Simple sampler takes about twelve PAL fields per update. [DB](../docs/research/second-reality-db.md). |
| Second Reality EC | Transformed texture planes sampled into character buffers | Own [texture-planes example](texture-planes/README.md); live C64 sampling of two complementary packed-bit planes, three charset bands and two-field scroll composition. Native proof covers 354 fields and all 16 transforms, with 34 full screenshots. Geometry updates every 22 fields, about 2.28/s; scanout continues at 50 Hz. [EC](../docs/research/second-reality-ea.md). |
| Second Reality presentation/later parts | Mock DOS/editor/SID menu; later polygons, texture cube and raytrace | Own [presentation-console example](presentation-console/README.md); normal keyboard commands, a 64-row read-only source viewer and three original SID patterns. Twenty complete viewport captures, command/viewer controls, 27 notes, 72 actual SID writes and real emulated audio pass. The original later polygon/texture-cube/raytrace descriptions remain review leads without established algorithms. [Production](../docs/research/second-reality.md). |
| The Impossible Thing | Glyph-reuse affine rotozoom | Own [character-rotozoom example](character-rotozoom/README.md); 32 moving phases and wraparound checked natively, with six complete screenshot comparisons. Own Q4 sampler runs at about 7.6 updates/s. [Intro](../docs/research/impossible-thing.md), [sampler](../docs/research/impossible-thing-affine.md). |
| No Bounds bobs | Masked bobs and mirrored background restoration | Own [masked-bobs example](masked-bobs/README.md); full 256-phase cycle plus wraparound and four complete screenshots checked natively. Bounded motion runs at 50 Hz. [Finite bobs](../docs/research/primary-2026-notes.md). |
| No Bounds loading | Streamed image strips and music-timed transition/loading handover | Own [streaming-strips example](streaming-strips/README.md); twenty real D64 loads through four resident slots, all ownership events and complete viewport pixels checked, including captures during LOAD. Final text publishes coherently. Uses slower KERNAL IEC loading; music cadence is affected, and original Sparkle deadlines remain separate. [Loading](../docs/research/no-bounds-loading.md). |
| The Dive / Memento Mori | Sprite interleave with rolled rows and overlapping pointer intervals | Own [sprite-interleave example](sprite-interleave/README.md); all 32 positions and wraparound, complete native screenshots and actual pointer/Y writes checked for 16-line intervals. The separate [20-line entry](sprite-interleave-20/README.md) shares the engine and checks the one-line overlap, rolled rows, all motion phases and 320 per-sprite pointer deadlines; minimum native margin is 22 PAL clocks. [Interleave](../docs/research/sprite-interleave.md). |
| NUFLI / Crest Slide Story | Hires bitmap plus expanded sprite underlay and left-edge repairs | Own generated-art [NUFLI example](nufli/README.md), with unchanged attributed Mufflon viewer and self-contained serializer/decoder. All bitmap, underlay and repair layers contribute; three native 64,000-pixel captures match. [Viewer](../docs/research/nufli.md), [converter variants](../docs/research/nufli-converter-variants.md). MUIFLI remains separate. |
| MUIFLI | Interlaced high-color image display | Own generated-art [MUIFLI example](muifli/README.md), with unchanged attributed Mufflon viewer and an independent format/address decoder. Six complete native fields match, including cold-field clipping and RAM relocation; actual scanout alternates every PAL field. Each field uses 16 physical colors; the digital mean has 55 RGB values. [Format boundaries](../docs/research/frontier-demos.md). |
| We Are The Anomaly | Arcade floor/wall scroller, staggered coarse updates and hidden-buffer publication | Own [arcade-scroller example](arcade-scroller/README.md); staggered floor copies, interrupted hidden-wall jobs and coherent publication checked over 144 fields plus the 18-line worst-case copy. Floor updates at 25 Hz. [Source](../docs/research/anomaly-arcade.md), [native fields](../docs/research/anomaly-native-upper.md). |
| Codeboys & Endians | Prepared bar paths, sprites and angle-specific charsets | Own [prepared-bars example](prepared-bars/README.md); five angle fonts and separate sprite beacons, with 258 native observations and eighteen complete screenshot checks. Runs at about 16.7 updates/s. [2025–2026 sources](../docs/research/frontier-2026.md). |
| Censor Hires Bubbles | Blender-produced images expanded with LZO | Own [prepared-bubbles example](prepared-bubbles/README.md); 25 original host-rendered 3D frames, Oscar64-format LZ expansion outside IRQs and coherent sprite publication. All 51 native presentations and 3,264,000 viewport pixels match at 50 Hz. [2025–2026 sources](../docs/research/frontier-2026.md). |
| The Hat | Final all-border upscroller; separate prepared PETSCII artwork | Own [all-border-upscroll example](all-border-upscroll/README.md); genuine sprite output spans all four borders, with 33 complete native fields, smooth one-pixel vertical motion and horizontal/vertical controls. Own [petscii-animation example](petscii-animation/README.md) separately plays sixteen original compressed PETSCII screen/color frames using the actual C64 character ROM; complete native loops and beam-following ColorRAM stores pass. Original Hat algorithms and artwork remain separate. [Source boundaries](../docs/research/february-2026.md). |
| Aloft | Three-layer moving pattern, bitmap/flipped Kefrens and interactive scene leads | Own [bitmap-kefrens example](bitmap-kefrens/README.md) demonstrates six overlapping ribbons and real joystick input in both orientations; 41 native images and interactions checked. Own [three-layer-pattern example](three-layer-pattern/README.md) checks all 64 motion states and eight overlap memberships using XOR selectors. Own [hangar-invaders example](hangar-invaders/README.md) adds a playable port-2 game with character enemies, sprite ship/projectile, hit/miss scoring and win/restart. Native real-input and pixel checks cover all twelve targets. Original Aloft algorithms/artwork remain separate. [Source boundaries](../docs/research/february-2026.md). |
| Rodents in the Attic | Creator-explanation follow-up | Open source lead; no recovered mechanism or standalone example. [Primary notes](../docs/research/primary-2026-notes.md). |
| Scheduling examples | IRQ continuations, cooperative waits and separate nested-IRQ guard | Own [macro-scheduling example](macro-scheduling/README.md); 205 native frames and the 100-frame scene transitions checked. Own [nested-irq-guards example](nested-irq-guards/README.md) checks per-call-site exclusion, two concurrent entries into one routine, 796 native events, 700 independent fast jobs and 100 complete counter images. [Macro scheduling](../docs/research/macro-scheduling.md), [2026 guard](../docs/research/february-2026.md). |
| Drivecalc vectors | Educational C64/1541 calculation offload with generated drawing code | Own [drivecalc-vectors example](drivecalc-vectors/README.md) now performs actual vertex rotation and perspective on a real emulated 1541, returning projected vertices through DOS. C64 generates/executes OR plot writers into a hidden bitmap. All 16 poses plus wrap, a drive-only vertex witness, complete writer streams and 1,152,000 native pixels pass. Measured cadence is 18–19 PAL fields per pose. This is a distinct drive-geometry implementation. [Source survey](../docs/research/lines-and-vector-fill.md). |
| Speedcode plasma | Generated plasma code as a memory/speed trade | Own [speedcode-plasma example](speedcode-plasma/README.md); all 256 phases plus wraparound and five complete native canvases checked. Two generated writers occupy 22,002 bytes; complete matrices publish at 50 Hz. [Speedcode references](../docs/research/lines-and-vector-fill.md). |

Supporting investigations cover exact field DDA, interlaced prefix dither,
packed marker collection, palette reassignment, open-panel composition,
loader/depacker reconstruction, Relax #24 article recovery, and VICE trace
semantics. These are implementation or evidence tools, not additional
completed demo effects. Their owning notes remain in the research reading map.

## Coverage and remaining research

Every identified example contract in this selected catalogue now has an own
runnable counterpart. Separate later StarWars, Dragonbond and Tusari research
notes are outside this build pass. The root variants share their existing engines; `double-vectors`
shares the prepared-fragments engine and is counted as a separate entry,
not another renderer implementation. Exact original-production scene,
arithmetic, timing or hardware equivalence is not implied.

The unidentified Rodents follow-up, original loader/depacker reconstruction
and unassigned later-production algorithms remain research leads. They have
no established additional runtime contract in this example inventory.
Individual READMEs preserve those boundaries and the measured cadence,
prepared inputs, runtime work, native proof and any format/viewer attribution.

## Recorded local validation: 8 November 2026

The completed batch has 72 build targets: twelve root targets, three
sprite-ball variants and 57 standalone entries. Forty-four own examples
have bounded native VICE proofs; twelve entries wrap existing root engines,
and `double-vectors` shares the prepared-fragments engine.

The [portable validation manifest](validation-2026-11-08.json) records the
72-target clean build and the 44 native-validated program hashes. Detailed
captures remain generated local artifacts.

The ignored local evidence includes the [72-target build proof](../build/examples/final-20261108T105400/build-proof.json),
[artifact/native-proof index](../build/examples/final-20261108T105400/native-index.json),
and [thirteen shared-entry identity checks](../build/examples/final-20261108T105400/standalone-entry-proof.json).
Each index binds the exact archived program bytes to its receipt. The common
launcher was also checked from a fresh source-only fixture: it generates
inputs through the entry's own build before launching VICE, and rebuilds
changed producer inputs. Failed-rerun receipt invalidation has isolated
regression checks without replacing the valid native histories.
