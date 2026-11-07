# The Demo Coder: original loader, complete images, and raster candidates

Research date: 7 November 2026. The original disk has been extracted, its boot depacker interpreted, and all 68 raw streams decompressed through its own resident routine. No effect, raster handler, drive, or VICE session was run in this lane. The visible identity and physical raster behavior of the candidates below remain native follow-up questions.

## Original release and author claims

**The Demo Coder / Fairlight** was released on 23 November 2024 and won the Mysdata C64 demo competition. In his 25 November comment, coder Trident distinguishes stretching all eight rows from techniques that repeat only the first row of a character block. He also describes horizontal movement that exposes source pixels in the MEGA picture, and counter-scrolling in the layered DYPP. His historical first/record suggestions are qualified author claims, not independently established results here. [Release, credits, and Trident's comment](https://csdb.dk/release/index.php?id=247776)

The primary download is the [original D64](https://csdb.dk/getinternalfile.php/263070/fairlight-the-demo-coder-fbc7cb83.d64). The preserved file is **196,608 bytes**, with SHA-256 `b8c54fc1ca41c00cd81773ecff780649d892bc6497a84b7c67c79a9235d95e9b`. Its 40-track geometry matters: the earlier Next Round extractor explicitly accepted only 35-track disks and was not reused unchanged. The archived page, download receipt, and c1541 listing remain in `build/research/frontier-followup/`.

## The DOS directory is artwork, not a part list

All ten live DOS entries point to the same linked file, starting at track 18, sector 2. Its chain runs through sectors 2–12. The extracted PRG is **2,675 bytes**, loads at `$0801`, and contains BASIC `SYS2061`, entering `$080D`. Its SHA-256 is `b184ba219fa92d8ca46da54a423ba6f19b1a40352765ac96b8f1481dbe1aa532`.

The actual bootstrap uses the original NMOS `LAX` and `DCP` instructions. We interpreted it twice, with otherwise artificial startup RAM filled with `$00` and `$A5`. Both runs executed **178,719 instructions** and produced identical output at **`$3FFF..$BFFF`**, 32,769 bytes. The two complete RAM dumps differ in unowned startup memory, as expected; the output-byte comparison does not exclude addresses within that output range.

Execution stops before the first unpacked instruction at **`$8A00`**. Its signature is:

```text
8A00  A9 18        LDA #$18
8A02  2C 11 D0     BIT $D011
8A05  10 FB        BPL $8A02
```

Mapped ROM and I/O reads are rejected during the current boot proof. The first wrapper instruction that would read the VIC is therefore outside the executed scope. The earlier exploratory attempt that wrongly expected Next Round's `$0900` handoff is retained as `attempt-flatram-no-handoff.*`; its flat-RAM polling result is not promoted as evidence.

The exact write sites, startup reads, port changes, two RAM hashes, original DOS sectors, and output hash are recorded in [the boot receipt](../../build/research/demo-coder/boot-proof.json). [Reproduction script](../../research/demo-coder/inspect_boot.py)

## The release's own Bitfire/Dali configuration

Static inspection of the reached wrapper establishes `JSR $8000` at `$8A1B`. Its installer copies `$82B1..$84AC` to **`$0200..$03FB`**, using two overlapping indexed copies. The four overlapping bytes agree. This configuration differs from Next Round's addresses; copying that production's resident locations would have been incorrect.

| Role | Demo Coder address |
|---|---:|
| Plain decompression | `$02CC` |
| Load next stream and decompress | `$02D2` |
| Load next raw stream | `$0224` |
| Hardware block poll, forbidden in the offline run | `$022E` |
| Packed source pointer | `$F0/$F1` |
| Bit buffer | `$F2` |
| Destination pointer | `$F3/$F4` |
| Length high byte | `$F5` |

The plain entry starts with `LDA #$96; LDX #$60`. Its original code patches the completion branch and replaces the block-fetch entry at `$03E3` with `RTS`. The load-and-decompress entry instead sends a loader command. These are different original entry paths; no hardware call is mocked or patched by the host.

The wrapper pushes `$DFFF` and jumps to `$02D2` at `$8AD8`, so the loader's eventual return enters **`$E000`**. The first raw stream independently decompresses to that address. Its first part copies music data to `$1000`, calls that music initializer, loads the next stream, then jumps to `$2000`. This is a concrete initial handoff chain, not a reconstructed complete timeline.

## All 68 streams, including in-place tails

The raw directory is at track 18, sector 18, continuing in sector 17. Each page stores an initial track/logical-slot/byte position, followed by four 63-byte columns. These encode load low byte, load high byte minus one, and length minus one. The stream consumes all 256 bytes of each sector; DOS link bytes do not apply. The extraction follows the writer's residue-major interleave, advances tracks, and skips track 18. The second page's start must match the first page's exact final stream position. [Pinned Bitfire writer source](https://github.com/bboxy/bitfire/blob/5a3964b533656332c12cc0904f2ce92f44499c6f/d64write/d64write.c)

All **68 original plain-depack calls returned**. The offline host makes all RAM visible with `$00=$2F`, `$01=$34`, loads the original packed addresses, and installs a pristine copy of the original resident before each call. Earlier established RAM is retained for dictionary reads. The proof rejects hardware/IRQ entries and unestablished value-bearing reads; the original NMOS NOP's unused memory reads are separately recorded. This supplies neither the drive nor native loader scheduling.

The final totals are:

| Quantity | Bytes |
|---|---:|
| Original raw packed streams | 185,932 |
| Original CPU output stores | 824,252 |
| Preserved raw tails | 377 |
| Complete in-place images | **824,629** |

The CPU interpretation executed **7,368,312 original instructions** and accounted for **733,770 back-reference reads** from established RAM. These instruction totals are analysis work, not demo frame timing.

The tail distinction is essential. Every stream executes the source/destination convergence path at `$03DD` exactly once. In-place Dali stops decoding when the two pointers meet and leaves the remaining data as raw bytes already in their final addresses. Its source-high completion marker is not a consumed-byte counter. The original Bitfire documentation describes this format behavior. [Bitfire's in-place explanation](https://github.com/bboxy/bitfire/blob/5a3964b533656332c12cc0904f2ce92f44499c6f/README.md#salvador--zx0)

For example, stream 1 has 37,254 written bytes plus a 58-byte tail; stream 7 has a 30-byte tail. The short stream 11 wrapper has 145 written bytes plus its 12-byte IRQ epilogue. Stream 37 has a 118-byte tail. All 24 nonempty tails are checked against the original packed payload and against the exact output-store address set. The preliminary prefix-only PRGs and receipt are retained under `streams/prefix-only-attempt/` with an explicit rejection note.

The current [stream index](../../build/research/demo-coder/streams/unpacked-index.json) records every original sector segment, packed address/hash, CPU-written prefix, untouched tail, complete output image, instruction count, and output-store event hash. [Reproduction script](../../research/demo-coder/unpack_streams.py)

## Scoped raster candidates, not visual identifications

The static mapper starts from the actual first `$E000` handoff and a complete repeated wrapper prologue, then follows direct control flow within each complete image. Literal IRQ-vector installations supply additional roots. It retains unresolved or self-modifying transfers rather than assuming a raw-data signature is executing code. It is a branch overapproximation, not an execution trace. [Map and listings](../../build/research/demo-coder/static-map/part-map.json)

The following are useful native checkpoints. Stream numbers are zero-based raw-directory indices, not author part names.

| Stream | Entry candidate | Initial IRQ | Concrete static lead |
|---:|---:|---:|---|
| 1 | `$2000` | `$2299` | First part reached through stream 0; large prebuilt `$D011/$D018` sequences accompany its code. |
| 40 | `$2000` | `$2383` | CIA2 timer/NMI setup, a raster path at `$24AB`, and table-directed code beginning near `$41AA`. |
| 46 | `$6000` | `$6238` | Bank/bitmap-selector family described below; raster path at `$62EA`. |
| 50 | `$2000` | `$22CD` | Distinct raster/control body and color-RAM update code. |
| 62 | `$2000` | `$239D` | Related CIA2/NMI and table-directed raster structure; separate final transitions to `$0A00` or `$0500`. |

The addresses recur across different parts, so a native breakpoint needs a phase-specific byte signature or original load observation. A breakpoint on `$2000` alone would not identify stream 40 or 62. No named stretcher or MEGA phase is assigned solely from the number of register stores.

### A checked 50-case bank/bitmap-selector engine

Stream **46** contains a particularly concrete candidate. Its code at `$6867` and `$692C` reads low/high tables at **`$BB64/$BB96`** and patches the target of `JMP` at **`$68B9`**. The index is clamped to 49. The IRQ path at `$6332` reaches this dispatch area. We checked all 50 table targets and every cell of the selected routines:

```text
LDA $B800,X
STA $D011
LDA #selector
STA $DD00
STA $D018
INX
```

Case `i` has `i+1` cells, followed by `JMP $68BC`. The family occupies **`$69C1..$B50B`**, **19,275 bytes**, with **1,275 cells** in total. Each cell is **20 nominal CPU cycles**: the indexed source page is aligned, so the source load cannot cross a page. The final jump adds three cycles per selected routine. These counts exclude VIC DMA, interrupt entry, and bus-write phase; they do not establish a scanline deadline or display rate.

The four literal selectors are `$FB`, `$72`, `$70`, and `$F8`. The same byte is written to both CIA2's port and VIC memory selection. Under the ordinary bank/address decode, these select bitmap bases `$2000`, `$4000`, `$C000`, and `$E000`, with screens `$3C00`, `$5C00`, `$DC00`, and `$FC00`. Initialization also copies 28 pages from byte-offset source positions `$2001` and `$2002` into `$4000` and `$C000`, clears `$E000..$FBFF`, and replicates screen data. These are inspected memory-reuse operations, not a claim about their final pixel interpretation.

The two initial `$D011` pages are exactly `$70 | ((x+1)&7)` and `$70 | ((x+2)&7)`. Thus their original values have both ECM and bitmap bits set. A reachable coroutine at `$64EF` masks bit 6 out of eight entries in each page. That is more specific than calling the part a generic bitmap zoom, but its interaction with VIC row counters, badlines, and visible pixels has not been measured here. In particular, this static check does **not** prove that the candidate is the author's MEGA picture or that all eight source rows stretch as claimed.

The [finite selector receipt](../../build/research/demo-coder/selector-analysis/selector-proof.json) records all targets, selectors, table bytes, source consumers, and nominal costs. [Reproduction script](../../research/demo-coder/inspect_selectors.py)

## Native follow-up and practical relevance

The unmodified DOS boot is a safe normal route: all directory-art aliases load the same `SYS2061` bootstrap. The first independently established unpacked wrapper signature is at `$8A00`, and its eventual first-part target is `$E000`. To identify later phases, observe the original loader's output and match a complete image or phase-specific signature before treating a reused entry address as a particular stream. Stream 46's `$6000/$6238/$62EA` chain and dispatch `$68B9` provide a narrow candidate for that work.

The initial open questions were the visible identity of each candidate, actual generated/modified table state, VIC counter and fetch behavior, timed register writes, and native frame cadence. The follow-ups below resolve selected parts of those questions. No claim about unrestricted real-time 3D or a drop-in line-renderer optimization follows from this raster mechanism. What is established is a concrete trade: substantial prebuilt code and memory selection can move display work away from per-pixel software drawing.

Reproduction instructions and the exact rejected-attempt status are in [the research README](../../research/demo-coder/README.md). This batch changes research artifacts only; it does not change the renderer or the original demo.

The later [native byte comparison](demo-coder-native.md) now follows the
original disk through stream 46, and [the raster investigation](demo-coder-raster.md)
checks a selected kernel, its continuation, DMA/counter states and a late
badline pulse. The [stored-artwork decoder](demo-coder-assets.md) identifies
stream 46's unreleased Rubicon loading picture: all 57,344 pixels represented
by its 7,168-byte bitmap prefix match the gallery image under a one-to-one
palette mapping. Trident assigns that artwork to his FLD-with-stretch effect,
separately from MEGA. These results identify the asset and author-described
effect family; the complete timed pixel transform and all-eight-row stretch
remain unproved.
