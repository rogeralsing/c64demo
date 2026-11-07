# C64 lines, vector filling, and generated code

Research snapshot: 7 November 2026. This note covers primary author articles and static inspection of their published sources. No third-party program was executed, assembled, or profiled in this research pass. The existing [YKTR Glenz investigation](../yktr-glenz.md) contains our earlier live binary analysis and is not repeated here.

Evidence labels matter: **author claim** means the author reports it; **source inspection** means the downloaded instructions/data support it; **local measurement** means one of this repository's recorded runs. Instruction-path counts are not complete-frame timings.

## Start with the representation

| Method | What the C64 updates | Main saving | Constraint when comparing with this project |
|---|---|---|---|
| Packed-byte lines | A pixel mask and an existing bitmap/charset byte | Several neighboring pixels share one read/write | A complete outline contains vertical interiors that our boundary markers deliberately omit |
| Run-length slices | Consecutive pixels between minor-axis steps | Amortizes error updates and mask/pointer changes | Setup and endpoint conventions still count |
| Polygon span speedcode | Masked left/right ends and whole bytes between them | Full interior bytes need stores rather than per-pixel plotting | Per-face work, clearing, and shared-edge merging differ from prefix XOR |
| Dynamic character allocation | Screen codes, allocated boundary glyphs, reusable solid glyphs | Solid interiors become character-map writes | Changes the screen-map/allocator architecture; glyph capacity is finite |
| Immediate-operand XOR fill | Transition operands, followed by prefix evaluation/reset | Cheap prefix instructions and a simple coverage model | Operand reset and scaled marker addressing are part of the cost |
| SMGF / sprite vectors | Sprite positions, stretching, priority, and raster code | VIC sprite hardware supplies visible edges/areas | Sprite availability, raster scheduling, topology, and background are restricted |
| Drive calculations | 1541 code plus C64/drive transfers | Geometry can run on another CPU | Transport and synchronization remain; it does not remove pixel rendering |

## Bitbreaker: line drawing beyond slope tables

Primary article: [Lines](https://codebase64.net/doku.php?id=base:lines). [Author source archive](https://codebase64.net/lib/exe/fetch.php?media=base:bresenham.tar.gz).

**Author description.** Flat lines accumulate pixels until the row or byte column changes, then write one combined mask. Unrolling a byte's pixel positions makes masks constant. Steep lines can instead emit runs between X changes; run-length slicing also combines error operations when a minimum run is already known. These are separate improvements from replacing Bresenham with precalculated slopes.

The article labels one unrolled path **23 cycles/pixel** and a larger absolute-address/SAX path **18 cycles/pixel**. These are shown inner paths, not whole lines: correction paths, column transitions, dispatch, endpoint handling, and clearing remain. Its overhead section explicitly recommends benchmarking specialized cases rather than assuming their inner-loop gain survives setup. It also describes first-touch character/block allocation and screen-based clearing.

**Source inspection.** `bresenham/lines.asm` contains the implementations; `cube.c` generates 256 frames of transformed/projected line data on the host. This example therefore must not be presented as a complete runtime-geometry benchmark. The archive's Makefile generates `data.asm`, but `lines.asm:4` also imports `oldschool7.prg`, which is absent from the archive. We did not attempt a build.

**Transfer to our exact boundary drawer.** Packing is valid only when samples land in the same packed byte and mapped crossing row. Different multicolor lanes may share a combined mask; coincident contributions to the same lane must still XOR. Keep the existing ceiling, half-open X endpoint, and corner cancellation rules. A faster OR-outline implementation does not establish those properties.

## Bitbreaker: span filling and its version trap

Primary article: [Filling the vectors](https://codebase64.net/doku.php?id=base:filling_the_vectors). [Historical source archive](https://codebase64.net/lib/exe/fetch.php?media=base:vector.tar.gz).

**Author description.** Prepare left/right crossings, split each horizontal span into masked ends and complete interior bytes, and enter generated fill code at the required span. The page discusses zero-page placement, indirect jump tables, patterns, and sharing edge calculations between adjacent faces. That last optimization is a proposal in the article, with extra storage/addressing costs, rather than an established free gain.

**Author claim, version-specific.** The page says its inline filler was rewritten for a 25% improvement and explicitly calls the attached archive outdated. Preserve that distinction: the downloaded `vector/fill.asm` is 20,577 bytes, while the current inline source block is 33,522 bytes. The archive is not evidence that the revised version achieves a measured result on our object.

The page reports `$57` raster lines for its example's clear. Its recommendation for plain clear speedcode belongs to that implementation and workload. It is not a general proof that a full-buffer clear beats every dirty or fused-clear scheme.

**Source inspection.** The archive includes `vector.asm`, `maths.asm`, `fill.asm`, `clear.asm`, mesh data, and a sine table. The inline revision is separately saved as `filling-the-vectors-block-2.asm`, derived from the archived HTML. We did not compile or time either version.

## Fullscreen character allocation: the Next Round source

Primary article and download: [Fullscreen vectors](https://codebase64.net/doku.php?id=base:fullscreen), [full.zip](https://codebase64.net/lib/exe/fetch.php?media=base:full.zip). Bitbreaker's [1 July 2026 author announcement](https://csdb.dk/forums/index.php?firstpost=72&roomid=11&topicid=162980) identifies this as the fullscreen renderer used in *Next Round*.

**Author description.** The character screen doubles as an allocation map. Boundary fragments allocate or modify glyphs; solid interior blocks reuse pattern characters. The stated single-buffer footprint is `$0be8` bytes, or 3,048 bytes: 2,048 bytes of charset plus 1,000 screen cells. This excludes renderer code and auxiliary state. Glyph exhaustion, clipping, overlapping boundary fragments, and completing partially covered glyphs are explicit complications.

**Static trace of `full/full/full.asm`:**

| Entry or routine | What the inspected source does |
|---|---|
| `fullvec_start` (line 66) | Initializes display state and relocates zero-page/secondary code |
| `start` (line 1821) | Cycles `render_buffer1/2/3`, sprite copies, buffer switches, and cleanup setup |
| `do_frame` (line 2983) | Consumes polygon records, calls `render`, advances edges, and finishes with `merge_buffer` |
| `render` / `next_edge` (lines 3556 / 3739) | Set up the polygon and advance its supplied outline segments |
| `alloc_char` macro (line 488) | Allocates the glyph backing a newly used screen cell |
| `clear_log`, `setup_char_del`, `clear1/2/3` | Bound screen cleanup and clear allocated glyph content |
| `data_start` (line 3979) | Begins embedded, frame-labelled polygon commands |

**Source inspection.** This archive configures multicolor text mode and three screens/charsets, plus border sprites. The embedded command stream supplies polygon coordinates; the archive does not supply its geometry exporter. Do not equate its runtime polygon rendering with our runtime rotation/projection. It also does not eliminate all clearing: allocated-glyph clear code is present. The solid-interior shortcut is an alternative renderer architecture, not a replacement instruction for our current prefix loop.

## Next Level: pinned author repository, two different pipelines

Repository: [bboxy/next-level](https://github.com/bboxy/next-level), inspected commit [`57643d53a97cdf38778958d8ebf99341315f834e`](https://github.com/bboxy/next-level/tree/57643d53a97cdf38778958d8ebf99341315f834e), committed 22 November 2023. The author's README identifies the production as *Next Level*, winner at X 2023. We archived 17 selected source/build files, not the whole toolchain, and did not execute them.

### `parts/doublevec`: host geometry, C64 span rendering

- [`exporter.c:224`](https://github.com/bboxy/next-level/blob/57643d53a97cdf38778958d8ebf99341315f834e/parts/doublevec/exporter.c#L224) rotates/project vertices; subsequent code culls and orders faces, then emits their coordinates. [`main:465`](https://github.com/bboxy/next-level/blob/57643d53a97cdf38778958d8ebf99341315f834e/parts/doublevec/exporter.c#L465) emits the two objects' frame streams.
- [`player.asm:3221`](https://github.com/bboxy/next-level/blob/57643d53a97cdf38778958d8ebf99341315f834e/parts/doublevec/player.asm#L3221) initializes the runtime. `render_frame1` and `render_frame2` configure sprite/character destinations; `next_face_s/c` read the supplied face data.
- [`fill_start:1890`](https://github.com/bboxy/next-level/blob/57643d53a97cdf38778958d8ebf99341315f834e/parts/doublevec/player.asm#L1890) relocates the inner filler into zero page. `fill` advances a slope and dispatches to span fragments with preconfigured destinations. `setup_fill` and `gen_clear` prepare generated code during initialization.

**Inference from this call/data flow:** the drawing is performed by the C64, but the inspected path's 3D transforms and face preparation are host work. Comparing only the runtime player to our complete renderer would omit substantial work.

### `parts/nonconvex`: runtime geometry and generated span cases

- [`complex.asm:284`](https://github.com/bboxy/next-level/blob/57643d53a97cdf38778958d8ebf99341315f834e/parts/nonconvex/complex.asm#L284): `main` calls `update`, then page/display handling.
- [`update:460`](https://github.com/bboxy/next-level/blob/57643d53a97cdf38778958d8ebf99341315f834e/parts/nonconvex/complex.asm#L460) clears and calls `makemat`, then enters mesh-specific generated code. [`sierpinsky.asm`](https://github.com/bboxy/next-level/blob/57643d53a97cdf38778958d8ebf99341315f834e/parts/nonconvex/sierpinsky.asm) expands `ROTPOINT`, `CULLFACE`, `CALCEDGESTEP`, and `DOTRI` calls.
- [`ROTPOINT:524`](https://github.com/bboxy/next-level/blob/57643d53a97cdf38778958d8ebf99341315f834e/parts/nonconvex/complex.asm#L524) sums matrix contributions and performs perspective lookup. `CULLFACE` uses projected determinants with a product-sign shortcut.
- [`genfill:1959`](https://github.com/bboxy/next-level/blob/57643d53a97cdf38778958d8ebf99341315f834e/parts/nonconvex/complex.asm#L1959) builds dispatch cases for pairs of endpoint byte columns. `genfillzero`, `genfillpos`, and `genfillempty` specialize same-byte, positive-span, and empty cases. Whole interior bytes use direct stores; edge fragments preserve unrelated bits through masks.

This is actual runtime geometry in the inspected path. It is still not our exact raster contract: no cross-implementation pixel proof or timing was performed. The source is useful for studying compile-time mesh expansion, shared edge-step preparation, and runtime-generated span code. Other downloaded parts (`bobvector`, `transbox`) were surveyed for entry points only; no detailed renderer conclusions are claimed for them.

## Sprite Masking Gap Filling: a different display engine

Primary explanation: [Sprite vectors](https://codebase64.net/doku.php?id=base:spritevectors), maintained by Bitbreaker. Original production/download route: [Snapshot by Glance](https://csdb.dk/release/?id=90336), including the with-note archive linked there. The production's author comments direct readers to Norvax's SMGF note.

**Author claims and mechanism.** The article credits *Snapshot* (2010) with 50 fps SMGF vectors. Its expanded version stretches sprites, changes X positions per raster line, and fills gaps with additional sprites. Sprite priority/background interaction can hide the final edge. Badlines are suppressed while display code runs. It reports a 160×160 maximum case with only three raster lines spare including SID playback; the same text explains sprite exhaustion and limits on edge count/background/movement.

Flat slopes are precomputed and share table subsequences; steep slopes use fixed-point updates. The author says the exporter orders edges and gap sprites, but does not publish that exporter on this page. This is not evidence of a general, unrestricted 50 fps filled-mesh renderer, or of its geometry being calculated at runtime. No SMGF binary was run in this lane.

## Speedcode and addressing references

- Cruzer/Camelot's [Speedcode](https://codebase64.net/doku.php?id=base:speedcode) distinguishes hand unrolling, assembler scripting, and runtime generation. Its 10-store example reports 103 cycles looped versus 42 unrolled. This is a small instruction example, not a demo frame rate. Its generated plasma examples illustrate the memory/code-generation tradeoff.
- Bitbreaker's [Advanced optimizing](https://codebase64.net/doku.php?id=base:advanced_optimizing) covers zero-page self modification, jumpcode, indirect dispatch tables, register/carry reuse, undocumented opcodes, and alignment penalties. Those mechanisms explain how the line/span examples avoid bookkeeping; they do not establish a speedup for an arbitrary port. Page crossings and the full correction/dispatch path must be counted.
- Wegi's [Drivecalc vectors](https://codebase64.net/doku.php?id=base:drivecalc_vectors) explicitly presents a nonoptimized educational C64/1541 example. The page includes source; its [ZIP](https://codebase64.net/lib/exe/fetch.php?media=base:3ddrivecalc.zip) contains a PRG. C64 `PREPLINE` builds drawing speedcode while a drive program performs calculations. Real drive emulation is part of the author's run instructions. We did not run it.

## Cost and exactness rules for future experiments

1. Count **geometry, culling, edge preparation, marker/outline work, fill, reset/clear, and display scheduling** separately. Include VIC-II stalls and IRQs in elapsed measurements. A music-inclusive author claim and a bare instruction loop are different evidence.
2. Record resolution, multicolor/hires mode, field updates, object/face count, buffer count, and host-precalculated data. A displayed 50 fps effect need not calculate every stage each frame.
3. Preserve exact crossing and endpoint rules independently of the chosen storage representation. Ordinary outline Bresenham, span masks, and our half-open ceiling markers have different contracts.
4. Quantized slopes are an explicit approximation unless their exact required rational directions are demonstrated. Our [YKTR note](../yktr-glenz.md) reconstructs its table and shows why viewport/operand scaling and reset cost cannot be omitted.
5. For our source, the long-edge marker path is 27 nominal cycles for address/mask/XOR storage plus 21 or 25 for exact DDA stepping: 48/52 per covered horizontal X, excluding setup, fill/reset, and bus stalls. Those are instruction counts, not a comparison claiming the scene examples are slower.

## Reproduction receipts and download inventory

Third-party content remains under ignored `build/research/vector-sources/`; this note contains links and findings rather than vendored source. `pages.json` records source URLs, retrieval time, size, and SHA-256 for seven Codebase64 pages. `downloads.json` and `extracted-files.json` record each archive and extracted file. `inline-code-extractions.json` identifies source blocks extracted from the saved HTML. GitHub metadata/tree and each selected raw file have separate URL/hash receipts in `github-receipts.json` and `next-level-source-files.json`.

| Download | SHA-256 | Inspected material |
|---|---|---|
| [bresenham.tar.gz](https://codebase64.net/lib/exe/fetch.php?media=base:bresenham.tar.gz) | `92ac364cb5c607cbdd08d1f56a30abf82e8f7813a290510da80716043b57478e` | Line routines, host exporter, Makefile |
| [vector.tar.gz](https://codebase64.net/lib/exe/fetch.php?media=base:vector.tar.gz) | `72a8517cd23f5ba28c95534144700354c2a9840c8b93a8fa6aa12533c5c39721` | Historical span filler/math/clear sources |
| [full.zip](https://codebase64.net/lib/exe/fetch.php?media=base:full.zip) | `ccbbfea67386da589e53864a7a62ba0c1180ab58c0d200af648c38a10aeadbdb` | Fullscreen renderer source and supplied PRG |
| [3ddrivecalc.zip](https://codebase64.net/lib/exe/fetch.php?media=base:3ddrivecalc.zip) | `23bcb6500d4ff4a392bfa912ca3509112fa1fa186793224a7a8354b18ad5bc49` | Archive inventory; source listing read on author page |

Open follow-ups are narrow: measure complete paths before adopting byte collection, establish exact corner/tie behavior for a candidate span filler, and inspect SMGF's original note/binary before attributing more than the author article establishes.
