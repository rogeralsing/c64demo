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
builds `build/example.prg` through `build-one.sh`; `run-one.sh` launches it.
The runner rejects assembler assertion failures and unchanged stale output.

## Effect inventory and implementation status

This inventory records the full documented scope. A research note, original
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
| Tower Power N2 | Rotating polygon sphere, product-table geometry, packed DDA, three face colors | Research reference; standalone example pending. [Mathematics](../docs/research/tower-power-n2-math.md), [palette](../docs/research/tower-power-n2-palette.md), [lines](../docs/research/tower-power-lines.md). |
| Tower Power F1 | Morphing/patterned cube with face subdivisions | Research reference; standalone example pending. [F1](../docs/research/tower-power-f1.md). The painted root target is related, not a matched reproduction. |
| You Know the Routine | Glenz/XOR polygon filling | Own [glenz example](glenz/README.md), sharing the existing runtime renderer. It demonstrates the technique rather than cloning the production. [Binary investigation](../docs/yktr-glenz.md). |
| Next Round | Fullscreen patterned vectors, two cubes and prepared visible fragments | Research reference; standalone example pending. [Renderer](../docs/research/next-round.md), [scene](../docs/research/next-round-scene.md). |
| Next Level `doublevec` | Host-prepared geometry with C64 span rendering | Source reference; standalone example pending. [Lines and vector filling](../docs/research/lines-and-vector-fill.md). |
| Next Level `nonconvex` | Runtime geometry and generated span cases | Source reference; standalone example pending. [Lines and vector filling](../docs/research/lines-and-vector-fill.md). |
| Next Level `transbox` / `bobvector` | Additional vector source entry points | Source leads only; detailed mechanisms and standalone examples pending. [Source boundaries](../docs/research/lines-and-vector-fill.md). |
| SMGF / Snapshot | Sprite-based filled vectors and Sprite Masking Gap Filling | Source references; standalone example pending. [Source survey](../docs/research/lines-and-vector-fill.md). |
| The Lab sprite vectors | Expanded sprite carpet, triangle/span packets and sixteen density materials | Research reference; standalone example pending. [Sprite vectors](../docs/research/the-lab-sprite-vectors.md). |
| The Lab MMS | Multicolor XOR-prefix vectors, open cube and bounded palette priority | Research reference; standalone example pending. [MMS engine](../docs/research/the-lab-mms.md). |
| Boo! | Sprite-filled cube, BRR line interpolation and drive-side slope preparation | Research reference; standalone example pending. [BRR](../docs/research/bit-reversal-lines.md), [binary](../docs/research/boo-binary.md). Complete native drive/display scheduling remains open. |
| Quondam Tunneling | Tunnel using retained screen codes and row-counter/raster changes | Research reference; standalone example pending. [Mechanism](../docs/research/quondam-raster.md). Full independent pixel composition remains open. |
| Lunatico MISC | Collision-register-assisted sprite crunch | Author/source reference; standalone example pending. [Frontier survey](../docs/research/frontier-demos.md). |
| Lunatico rain | WIZ/character ripple animation with slower bumpmapping | Author-note reference; standalone example pending. [Rain](../docs/research/lunatico-rain.md). Original rain code and scheduling remain open. |
| Freespin | Video and mechanical sound generated by a 1541 drive | Research reference; drive-target example pending. [Freespin](../docs/research/freespin.md). A C64 framebuffer demo would not reproduce this device contract. |
| A Mind Is Born | Coupled procedural image/music and overlapping state in a 256-byte intro | Own [audiovisual-feedback example](audiovisual-feedback/README.md); 256 native IRQ states, 6,375 SID writes and all 256 cyclic stack/font addresses checked, with real emulated SID audio output. Readable standalone code does not claim the original's 256-byte size. [Original](../docs/research/a-mind-is-born.md), [native checks](../docs/research/a-mind-is-born-native.md). |
| Nine character path | 3×3 character stamping and representation switching | Own [character-stamp example](character-stamp/README.md); sprite-to-character handoff, slot reuse and changed overlap priority checked over fifteen native fields. [Character path](../docs/research/nine-character-path.md). |
| Nine Device | Upper-border generated raster cells, ghostbytes and crunched sprites | Research reference; standalone example pending. [Device traces](../docs/research/nine-device.md). Complete composition and other hardware outcomes remain open. |
| Ghostbyte shine-through | Idle-pattern and sprite-mask composition, two teaching examples | Own [ghostbyte example](ghostbyte/README.md); three native views match 20,160 independently composed lower-border pixels. [Teaching examples](../docs/research/ghostbyte-shine-through.md). |
| The Ghost | Released ghostbyte-based first-scene display | Original files are recovered; standalone example pending. [The Ghost](../docs/research/the-ghost.md). Native scene matching remains open. |
| The Demo Coder | Rubicon FLD/stretch, with layered DYPP/MEGA leads | Research reference; standalone example pending. [Raster mechanism](../docs/research/demo-coder-raster.md), [artwork](../docs/research/demo-coder-assets.md), [further leads](../docs/research/frontier-followup.md). Complete stretching remains open. |
| Colors | Three-phase hires character/sprite display, moving coverage and reveal | Research reference; standalone example pending. [Display map](../docs/research/colors-first-display.md), [pixels](../docs/research/colors-first-display-pixels.md). Later effects and analog blending remain open. |
| Second Reality CA | Dot-field plotting with cached-address clearing | Own [dot-field example](dot-field/README.md); 32 native updates and five complete screenshot comparisons. Prepared profiles drive 256 live point requests, with whole-byte collision behavior retained. [CA](../docs/research/second-reality-ca.md), [coverage](../docs/research/second-reality-ca-coverage.md). |
| Second Reality DB | Two complementary bitmap layers and palette overlap | Own [bitmap-layers example](bitmap-layers/README.md); eight complete native bitmap/screenshot comparisons. Simple sampler takes about twelve PAL fields per update. [DB](../docs/research/second-reality-db.md). |
| Second Reality EC | Transformed texture planes sampled into character buffers | Research reference; standalone example pending. [EC](../docs/research/second-reality-ea.md). Full scanout and temporal composition remain open. |
| Second Reality presentation/later parts | Mock DOS/editor/SID menu; later polygons, texture cube and raytrace | Presentation is identified in original bytes; no standalone example. Later effect implementations remain open. [Production](../docs/research/second-reality.md). |
| The Impossible Thing | Glyph-reuse affine rotozoom | Own [character-rotozoom example](character-rotozoom/README.md); 32 moving phases and wraparound checked natively, with six complete screenshot comparisons. Own Q4 sampler runs at about 7.6 updates/s. [Intro](../docs/research/impossible-thing.md), [sampler](../docs/research/impossible-thing-affine.md). |
| No Bounds bobs | Masked bobs and mirrored background restoration | Own [masked-bobs example](masked-bobs/README.md); full 256-phase cycle plus wraparound and four complete screenshots checked natively. Bounded motion runs at 50 Hz. [Finite bobs](../docs/research/primary-2026-notes.md). |
| No Bounds loading | Streamed image strips and music-timed transition/loading handover | Source/model reference; standalone example pending. [Loading](../docs/research/no-bounds-loading.md). Native refill deadlines remain open. |
| The Dive / Memento Mori | Sprite interleave with rolled rows and overlapping pointer intervals | Own [sprite-interleave example](sprite-interleave/README.md); all 32 positions and wraparound, complete native screenshots and actual pointer/Y writes checked for 16-line intervals. The separate 20-line variant remains pending. [Interleave](../docs/research/sprite-interleave.md). |
| NUFLI / Crest Slide Story | Hires bitmap plus expanded sprite underlay and left-edge repairs | Own generated-art [NUFLI example](nufli/README.md), with unchanged attributed Mufflon viewer and self-contained serializer/decoder. All bitmap, underlay and repair layers contribute; three native 64,000-pixel captures match. [Viewer](../docs/research/nufli.md), [converter variants](../docs/research/nufli-converter-variants.md). MUIFLI remains separate. |
| MUIFLI | Interlaced high-color image display | Format/source lead; standalone example pending. Keep its blended-color subset separate from physical VIC palette entries. [Format boundaries](../docs/research/frontier-demos.md). |
| We Are The Anomaly | Arcade floor/wall scroller, staggered coarse updates and hidden-buffer publication | Research reference; standalone example pending. [Source](../docs/research/anomaly-arcade.md), [native fields](../docs/research/anomaly-native-upper.md). Complete scanout and worst-case timing remain open. |
| Codeboys & Endians | Prepared bar paths, sprites and angle-specific charsets | Own [prepared-bars example](prepared-bars/README.md); five angle fonts and separate sprite beacons, with 258 native observations and eighteen complete screenshot checks. Runs at about 16.7 updates/s. [2025–2026 sources](../docs/research/frontier-2026.md). |
| Censor Hires Bubbles | Blender-produced images expanded with LZO | Source/release reference; standalone example pending. [2025–2026 sources](../docs/research/frontier-2026.md). Native presentation remains unverified. |
| The Hat | Final all-border upscroller; separate prepared PETSCII artwork | Open mechanism lead; no standalone example. [Source boundaries](../docs/research/february-2026.md). Do not substitute ghostbyte teaching code for the ending. |
| Aloft | Three-layer moving pattern, bitmap/flipped Kefrens and interactive scene leads | Open mechanism leads; no standalone examples. [Source boundaries](../docs/research/february-2026.md). |
| Rodents in the Attic | Creator-explanation follow-up | Open source lead; no recovered mechanism or standalone example. [Primary notes](../docs/research/primary-2026-notes.md). |
| Scheduling examples | IRQ continuations, cooperative waits and separate nested-IRQ guard | Own [macro-scheduling example](macro-scheduling/README.md); 205 native frames and the 100-frame scene transitions checked. Separate per-call-site nested-IRQ guard remains pending. [Macro scheduling](../docs/research/macro-scheduling.md), [2026 guard](../docs/research/february-2026.md). |
| Drivecalc vectors | Educational C64/1541 calculation offload with generated drawing code | Source lead; standalone drive/C64 example pending. [Source survey](../docs/research/lines-and-vector-fill.md). |
| Speedcode plasma | Generated plasma code as a memory/speed trade | Own [speedcode-plasma example](speedcode-plasma/README.md), with two generated writers sampling live sine phases into 1,000 screen cells. [Speedcode references](../docs/research/lines-and-vector-fill.md). |

Supporting investigations cover exact field DDA, interlaced prefix dither,
packed marker collection, palette reassignment, open-panel composition,
loader/depacker reconstruction, Relax #24 article recovery, and VICE trace
semantics. These are implementation or evidence tools, not additional
completed demo effects. Their owning notes remain in the research reading map.
