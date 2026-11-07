# Rendering technique map

The strongest transfers to our exact interlaced renderer are independent pieces:
packed pattern transitions, a different outside-color code, cheaper exact field
stepping, and fewer packed marker writes. Display allocation, geometry
preparation and visibility impose separate contracts. An impressive polygon
image does not establish which of those jobs runs on the C64.

This map summarizes the owning investigations; no renderer changes or new
performance results accompany it.

## What each production actually supplies

| Renderer | Runtime computation and prepared input | Storage, boundaries, fill and cleanup | Palette, pattern and visibility |
| --- | --- | --- | --- |
| **Tower Power N2** | Runtime three-plane rotation and orthographic projection; reusable 16 KB product tables, stored mesh coordinates, mirrored partners. | Column-major multicolor charset; generated integer-error boundary kernels, shallow packed collection, separate zeroed marker buffer and generated prefix fill. | Outside is code `11`; three global face colors. Convex sphere mesh. [Math](tower-power-n2-math.md), [lines](tower-power-lines.md), [palette](tower-power-n2-palette.md). |
| **Tower Power F1** | Runtime morphing, rotation, perspective and culling; stored shape targets and reciprocal/product selectors. | Related charset/XOR machinery. Captured body has 24 vertices plus 15 coplanar stencil points. | Earlier packed-X patterns and later explicit colored face subdivisions are different phases. Native captured faces use ordinary orientation culling. [F1](tower-power-f1.md). |
| **Next Round** | Prepared 2D polygon fragments; C64 edge stepping, glyph allocation, partial-glyph assembly and scheduling. | Dynamic multicolor characters; shared interior pattern glyphs, allocated boundary glyphs, screen spans and cleanup; border sprites. | Twelve two-row patterns. Matched two-cube pose already contains ten disjoint visible fragments. [Renderer](next-round.md), [scene](next-round-scene.md). |
| **The Lab sprite stage** | Inspected 164-pose sequence supplies 118 triangle packets and 46 compressed span-run packets. Runtime triangle/span rasterization. | Double-buffered expanded one-bit sprite carpet; contiguous vertical slices, 192×147 logical displayed samples. Partial-byte OR, interior pattern stores; controller clearing/stencils matter. | Sixteen density materials. Prepared screen-space input; no live 3D transform established for this sequence. [Sprite audit](the-lab-sprite-vectors.md). |
| **The Lab MMS stage** | Prepared projected edges, slopes and attribute commands, with runtime scale/translation and rasterization. | Multicolor bitmap; generated vertical XOR prefix, bounded passes, screen/Color RAM work and buffer switching. | Aliased selectors prove bounded A-over-B opaque priority; local attributes vary panel colors. Geometric depth is not inferred from the layer labels. [MMS audit](the-lab-mms.md). |
| **Boo!** | BRR interpolation; original generator and reconstructed drive rank selector checked offline. Author describes drive-assisted slope preparation. | Generated position-output cells. Complete native display/drive scheduling remains unproved in this investigation. | Approximate fractional-step placement; author describes a sprite-filled cube. [Binary](boo-binary.md), [BRR comparison](bit-reversal-lines.md). |
| **Our interlaced icosahedron** | Runtime Q6 rotation, perspective, audited model-specific guarded culling, exact rational crossings. | Fixed column-major multicolor charset; generated immediate markers; ten-cycle fill/output/reset cells; old/current dirty unions per buffer/parity. | Three face selectors; opaque convex visible faces partition the image. B-even/A-even/B-odd/A-odd histories are intentional. [Current renderer](../../README.md), [composition](open-panels.md). |

The inspected Tower binaries are the [100% final release](https://files.scene.org/view/parties/1994/theparty94/c64/demo/tower_power.zip).
Next Round's [author article](https://codebase64.net/doku.php?id=base:fullscreen)
and The Lab's [included author note](https://csdb.dk/release/?id=262146) describe
different engines and preparation choices. Keep those statements attached to
the matched code paths.

## Other ways to change the workload

These cases exploit a display contract or a different output device. They do
not establish a faster general polygon filler:

- **Quondam:** late `$D011` writes wrap the VIC row counter while retaining
  the same forty cached screen codes. In the sampled frame, twenty-four
  eight-row bands change charset selection or packed-color interpretation.
  All selected native snapshots retain the cached codes even as VCBASE
  advances. The complete VIC endpoint agrees with the uninstrumented control;
  a small CIA TOD alarm-phase difference is retained explicitly. This trades
  prepared image data and raster control for software redraw.
  [Native mechanism and controls](quondam-raster.md).
- **NUFLI:** Mufflon's embedded viewer generates 3,906 bytes of raster code
  from picture-specific switch tables. Hires bitmap ink/paper, six expanded
  sprite underlays and two left-edge repair sprites supply the picture's
  colors. Original-code generation and logical layer ownership are checked;
  [one original picture also matches two complete native captures](nufli-native.md).
  The actual converter's [four fitted exports match twelve native captures](nufli-converter-variants.md);
  a screenshot-verifier socket race was repaired separately from its color math.
  That direction adds color through
  substantial raster/display ownership, not additional arbitrary free pixels.
  [Format and viewer](nufli.md).
- **Freespin:** a 1541 directly generates video and mechanical sound. Its disk
  representation is chosen for a tiny runtime decoder, and port-write timing
  creates the image. The checked decoder and 64-cycle fragment are a different
  output-machine contract, not a C64 framebuffer optimization.
  [Released-byte checks](freespin.md).
- **A Mind Is Born:** code, clock, SID shadow state, palette and stack/font
  storage deliberately overlap. The checked arithmetic demonstrates useful
  audiovisual coupling within 254 payload bytes. [Native checks](a-mind-is-born-native.md)
  additionally cover startup, a complete IRQ transition and inherited timer
  cadence; those checks do not promise
  independent animation controls or a measured visual update rate.
  [Byte and state map](a-mind-is-born.md).
- **Nine:** the original script switches representations: one digit becomes
  a 3×3 character stamp when sprite priority becomes restrictive. Native checks
  match all screen/Color RAM changes for the captured stamp. Its upper-border
  Device instead uses generated timed cells, ghostbytes, crunched sprites and
  prepared pointer tables. Native traces cover two natural fine-scroll paths;
  representation and scheduling remove different constraints from a general
  polygon filler. [Character switch](nine-character-path.md),
  [Device timing](nine-device.md).
- **Ghostbyte shine-through:** a shared eight-pixel idle pattern combines with
  wider sprite masks. Trident's separate teaching examples and an ideal
  compositor are checked; with one fixed `$81` byte the aligned model has only
  nine distinct outputs, rather than arbitrary eight-pixel graphics. The
  complete scroller and later released implementations remain separate
  investigations. [Source and model](ghostbyte-shine-through.md).
  The original [The Ghost disks](the-ghost.md) now yield all 62 packed files
  through their original depacker. Its first-scene byte anchors use bank
  `$4000` and idle byte `$7FFF`; native output and pixel composition remain open.
- **Macro scheduling:** Trident's original example expands IRQ waits into
  vector changes and RTI, and frame waits into a stored continuation plus
  self-modified counters. Original CPU checks give 29 nominal cycles for an
  already-waiting sequence call, including JSR. This makes scene organization
  manageable; it does not remove emitted instructions, supply a raster clock
  or accelerate the rasterizer. [Source and bounded checks](macro-scheduling.md).
- **The Demo Coder:** all 68 in-place images are reconstructed, including
  377 untouched raw-tail bytes. One reachable candidate uses 50 prebuilt
  bank/bitmap-selector routines with 1,275 checked cells in 19,275 bytes.
  A cell takes 20 nominal CPU cycles before DMA. Native traces now match
  one 15-cell kernel and its seven-group continuation. The selected kernel
  resets RC through badlines; the continuation allows ordinary RC progression.
  A separate DEC/INC `$D011` pulse restores the register yet advances the
  40-cell matrix-row base. The stored artwork now matches the unreleased
  Rubicon loading picture, which the author assigns to FLD-with-stretch.
  Complete row stretching remains unproved. This is a concrete code/memory/
  display trade, not measured general polygon speed. [Original images](demo-coder.md),
  [native counter and trace checks](demo-coder-raster.md),
  [artwork and shifted storage](demo-coder-assets.md).
- **Lunatico rain:** the original technical note describes a WIZ surface and
  character graphics, combining fast apparent ripple animation with slower
  actual bumpmapping. The WIZ description arranges animation phases into
  seamless tiles and uses AGSP viewpoint movement to sample them. Its 50 fps
  claim concerns ripple animation, not a measured 50 Hz bumpmapper. The original
  rain code and precise scheduling remain open. [Recovered author evidence](lunatico-rain.md).
- **Colors:** the first original display combines three stored character
  phases, a four-bank 320×192 hires canvas and paired sprite underlays.
  The matrix formula arranges six rows per bank in column order; bank changes
  use CIA2's direction register. Native captures show one phase advance per
  PAL field in the sampled stage. An independent decoder matches all 184,320
  pixels of three traced fields, including midline bank changes and the
  captured custom-GLUE transient. Retained sprite pointers, moving coverage
  and reveal history matter, so three phases alone establish neither a static
  RGB mixture nor an effective palette size. This is a display/storage trade,
  not yet a general polygon-renderer optimization. [First-display map](colors-first-display.md),
  [exact captured pixels](colors-first-display-pixels.md),
  [original-release investigation](colors.md).
- **Second Reality:** the original C64 disks now have a complete DOS-chain
  inventory, a recovered author note and an independently checked first
  unpacked image. Its CA dot field generates 35,456 bytes of plotting code,
  with cached old addresses for 992 clears and 992 point plots per iteration.
  One scoped original draw/update run matches code, caches and the full
  glyph plane; 36 other RAM differences remain explicit. This is runtime
  plotting driven by prepared profiles/motion data, not evidence of arbitrary
  live 3D transforms. Its mock DOS, editor and PC-style sound menu are C64 code.
  AEG's high-resolution conversion aim remains an author statement; later
  polygon, texture and raytrace paths still need their own byte/runtime evidence.
  Neither the PC source nor his separate 2003 glyph-rotozoom explanation is
  assigned to these 1997 effects. [Disk and note evidence](second-reality-disk-map.md),
  [native boot](second-reality-native.md), [source boundaries](second-reality-sources.md),
  [dot-field kernel](second-reality-ca.md).
  Its [coverage analysis](second-reality-ca-coverage.md) records 62 requested
  eligible samples missing from the checked endpoint because of later clears
  and whole-byte assignments. The subsequent [DB bitmap effect](second-reality-db.md)
  expands a 2 KiB mask into two complementary 16 KiB layouts and ORs samples
  into 6,144 vertically doubled bitmap stores. Low/high bit-pair ownership
  gives separate palette choices for the two layers and their overlap; it
  does not imply a polygon or depth pipeline.
- **The Impossible Thing:** AEG's separate 2003 rotate/zoom intro reduces
  the texture domain to 16×16 origins. It generates 256 transformed glyphs,
  then selects them over a 40×25 character matrix. Two 14,592-byte writer
  banks support alternating screen/charset pairs. This is a concrete
  representation trade: glyph reuse replaces a complete pixel canvas, while
  glyph generation and screen mapping still cost runtime CPU. All 29,184
  generated bytes match native preparation, and one stored-image update
  matches with 53,188 nominal CPU cycles. Five post-empty native selection
  intervals average 58,596 clocks; those writes are not synchronized frame
  boundaries. The bundled 25 fps claim remains distinct from those measured
  selections and the source lower bound. [Original release, code and measurements](impossible-thing.md).
  The [independent coordinate model](impossible-thing-affine.md) now derives
  every new glyph/matrix byte from original texture/profile/preset data and
  input phases. Its native acceptance covers the static initial preset;
  moving-angle coverage remains open. Shared glyph-local fractions, signed
  Q8 shortcuts and packed U/V carries explain the sampling approximation.

Native timing claims also depend on the observer. VICE's text store traces
report a later instruction boundary, not a saved per-write bus timestamp.
RMW dummy-write visibility and pending debugger queues require explicit
handling, especially around execution breakpoints and snapshot restores.
[Pinned source and observed limitations](vice-trace-timing.md).

The [new 2025–2026 source survey](frontier-2026.md) adds three concrete
workload choices. Elder0010's **We Are The Anomaly** staggers fine-scroll
wrap phases and gates sections of hidden wall-buffer copying on remaining
raster time; published assembly and the original disks are archived, but
source/build matching and native scheduling remain open. Mahoney's own
**Codeboys & Endians** account explicitly trades prepared line coordinates
for more simultaneous bars, with sprites and angle-specific charsets doing
different jobs. Carrion's **Censor Hires Bubbles** stores 25 Blender-produced
images and expands them with LZO outside its IRQs; the repository's bundled
release matches CSDb exactly, while a source rebuild and native presentation
remain unverified. These are distinct examples of amortization, prepared
paths and prepared imagery. They do not establish faster boundary drawing
for our current vector renderer.

The [Anomaly source follow-up](anomaly-arcade.md) makes the workload trade
explicit: its published fine-scroll phases have the same 14,352 coarse
events over 2,048 calls as the declared aligned baselines, but reduce the
peak from 70/96 lines to 24. This is arithmetic enumeration, not native
timing. The signed raster gate and unconditional upper-buffer publication
still require actual call-time/completion evidence before accepting a
complete deadline guarantee.

[Second Reality's EC stage](second-reality-ea.md) supplies a separate
column-ordered character transform: two prepared bit planes feed patched
source operands, and 2,976 packed-byte stores populate alternate glyph rows
in a 248×192 window. The full buffer/store endpoint is checked, while
independent motion equations, complete temporal interlace and VIC pixels
remain open. Its deliberate replacement of final-column stores by reads
also illustrates why a physical-RAM model cannot assume every read observes
RAM: the captured CPU port maps those addresses to KERNAL ROM.

## Transfers, in practical order

**1. Add screen-aligned dither through edge bytes.** For face pattern byte
`P[f,p]` on physical parity `p`, an edge contributes the adjacent visible faces'
byte XOR, masked to its X lane. A field has one constant row parity, so the
existing prefix cells reconstruct the pattern without an interior shading pass.
The [host proof](interlaced-dither.md) compares 524,288 selected packed bytes
against independent opaque polygon interiors. General and one-column setup must
replace their two-bit shift/index assumptions with lane AND masks. Four-logical-
pixel by two-physical-row patterns fit; arbitrary textures or larger vertical
periods require more machinery.

**2. Put black outside at code `11`.** Tower N2 seeds output with `$FF`, keeps
markers zero, and takes black from character Color RAM. This frees `$D021–$D023`
for three face colors chosen from all sixteen palette entries; the hardware
still supplies four selectors per character. The transfer combines algebraically
with dither: for outside byte `B`, visible face contribution is `B XOR P`;
hidden faces contribute zero. Interior shared-edge complements cancel. Prefix
seed, stale-image cleanup and the surrounding blank glyph must consistently use
`B`; marker reset remains zero. This is a palette reassignment, independent of
line stepping or geometry. [Verified arrangement](tower-power-n2-palette.md).

**3. Evaluate direct exact field stepping.** The [negative-error DDA proof](exact-field-dda.md)
reproduces `ceil((ceil(y(x))−p)/2)` without slope quantization. It uses denominator
`2*dx` and direction/parity-specific initial bias. A hybrid retains direct
quotient stepping for very steep edges, avoiding long correction loops. Its
1,371-cycle mean hot-kernel saving is a workload estimate before setup, dispatch,
page penalties and VIC effects. Direct field rows require new q-indexed operand
maps; current full-Y maps cannot be reused unchanged. Extra direction families,
entry tables, the q64 terminal sink and interrupt vectors need a concrete RAM
layout. Arithmetic enumeration is already strong; assembly fit and whole-frame
benefit remain open.

**4. Collect adjacent lanes before a marker write.** Tower demonstrates this
in executed generated code. Our own samples can merge only when they address
the same packed byte and exact field row; their masks combine by XOR. About
30.1% fewer writes are possible in the audited workload, before bookkeeping.
Flush on row change, byte boundary and the final partial byte. Preserve
half-open X, duplicate-marker cancellation and terminal routing. Tower's
`dx+1/dy+1` coverage bias changes pixels and must not accompany this transfer.
The collector and direct-field DDA compete for registers and replace shared
hot-loop work, so their estimates cannot simply be added. [Original kernels](tower-power-lines.md).

**5. Trade RAM for products while retaining live geometry.** Tower's 16 KB
table contains reusable products, not rendered frames; F1 reuses product pages
for perspective. That preserves runtime pose selection. Our 32 KB generated
fill banks already dominate memory, so another full table needs a layout trade.
Model-specific products can cover fixed source coordinates more compactly, but
later rotation inputs vary: a first-stage table does not remove every multiply.
Precision, signed domains and projection bounds need their own audit.
Prepared projected poses can preserve a fixed sampled animation if generated
from the same rules, while constraining free angle/model changes. Next Round
and The Lab show that prepared geometry still leaves substantial rasterization
on the C64.

**6. Exploit bounded palette priority for open panels.** XOR remains
commutative, but the native Lab stage aliases selectors `01/10` to one color:
delta A=1 and B=3 give A's color for both A-only and overlap. With N2-style
outside code 3, the outputs are `{outside3,A2,B0,both1}`. Color RAM black,
`$D021=B`, and `$D022=$D023=A` therefore give two-tone opaque A priority through
one unchanged prefix pass. Each layer must have at most one covering region
per sample; palette capacity must fit, and layer membership must be justified
geometrically. The bitmap's varying panel colors need local attributes.
This does not establish general depth sorting. B can stipple against empty
black; omitting an opaque black A sample instead exposes B. Richer A patterns
or arbitrary overlaps require resolved coverage or composition.
[Panel constraints](open-panels.md), [dither limits](interlaced-dither.md).

DB's complementary bitplanes also demonstrate a simpler two-layer palette
composition. Because their bit positions are disjoint, `A OR B = A XOR B`.
For two resolved binary masks and N2's outside selector 3, layer deltas 1
and 2 produce `{outside=3, A=2, B=1, overlap=0}`. All three foreground/overlap
colors can then come from the global registers while Color RAM supplies
outside black. This algebra fits the existing two-bit prefix representation;
each layer must still supply one resolved coverage mask. It gives a chosen
overlap color, not alpha blending or general depth ordering, and no assembly
or performance benefit has been measured for our renderer. [Original two-plane example](second-reality-db.md).

## Limits that decide the next experiment

[Quiss's BRR article](https://www.quiss.org/boo/) explains a real five-cycle
comparison/addition core. It changes our exact crossing pixels and excludes
plotting and threshold setup. With our compatible register arrangement, the
released selector alone averages about 3,021 cycles against roughly 2,508 gross
advance cycles saved. Drive offload or a new plotter could change that balance;
the isolated core does not establish a whole-renderer win.

The evidence levels remain separate: author explanation, identified source,
original-CPU reproduction, and matched native output. Native captures validate
specific stages and poses; host exhaustive DDA arithmetic does not validate
assembly timing. Missing preparation tools leave the exact offline visibility
algorithm unresolved. A concrete transfer should preserve the current pixel,
corner, field-history and reset contracts, then measure the complete renderer
once its setup and RAM costs are included.
