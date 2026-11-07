# Frontier follow-up: Quondam, Lunatico rain, and full-row stretching

Research date: 7 November 2026. This follows the unresolved leads in [the first frontier pass](frontier-demos.md). No VICE session or production implementation was added. Downloaded C64 code was only interpreted offline for a bounded SFX depack and one finite preparation helper; the effect and its raster handlers were not executed.

That scope describes this initial follow-up. Later work adds a
[native Quondam inspection ledger](quondam.md) and
[measured VIC row reuse](quondam-raster.md). The rain and full-row-stretching
leads below still have their stated evidence limits.

## Quondam Tunneling — a concrete mechanism recovered from the original code

**Identity.** Quondam Tunneling is lft/Linus Åkesson's full-screen C64 tunnel entry for Fjälldata, released **31 January 2026**. Code, graphics, and music are credited to lft. His release-page reply says it requires PAL timing and no other special hardware. The separate explanation video was posted 6 February 2026. [Author release/download page](https://www.linusakesson.net/scene/quondam-tunneling/index.php), [release and credits](https://csdb.dk/release/?id=259052), [author explanation page](https://www.linusakesson.net/scene/quondam-tunneling/explained.php)

The explanation page supplies an embedded video, not an article or source listing. Its video ID is `4Db-tmL8Tno`. The first research pass found an advertised English auto-caption track, but the caption request returned an empty body. That receipt is retained; this follow-up does not pretend to have read a transcript or watched and verified its diagrams. Nor is the anonymous comment about repeated rows and sprite masking treated as author confirmation.

### Original SFX and bounded inspection

The official PRG is 33,675 bytes, SHA-256 `e86e4bcf40e859f4ec3fcc83a86f8f0c172b6efa0a38d8dc199a85717fddc17c`. Its BASIC line enters at `$080D`. We interpreted its original depacker, including its original self-modification, until it returned to the newly unpacked `$080D` entry after **1,776,184 instructions**. Execution stopped there, before the demo ran.

The diagnostic RAM handler separates mapped I/O writes from underlying RAM: the original SFX writes `$D020` 33,365 times while changing `$01`. Treating those writes as ordinary RAM would risk corrupting unpacked data under I/O. This is still a minimal host analysis, not a C64 hardware model. The original effect's initialization, interrupts, CIA timers, and VIC display were not run.

The unpacked RAM hash is `8d1b7ea523dc2fbcb7c9ddc9b335cd451f87e0659b4e380b52334c350998e3db`. The receipt, script, RAM image, and listings are under `build/research/frontier-followup/` as `quondam-depack.json`, `inspect_quondam.py`, `quondam-unpacked-ram.bin`, `quondam-init.txt`, and `quondam-renderer.txt`.

### One timed store window has two different jobs

The concrete mechanism is **register-role switching through self-modifying code**. The preparation helper at `$939B..$93E8` rewrites the same short window so that it performs one of two operations:

```text
bank/charset step:  LDX #memorySelection
                   ...
                   LDA #bankDirection
                   STA $DD02
                   STX $D018

palette step:      LDX #multicolor1
                   ...
                   LDA #multicolor2
                   STA $D023
                   STX $D022
```

The two absolute stores at `$9327` and `$932A` retain the same instruction lengths and nominal execution times. Their operands become either `$DD02/$D018` or `$D023/$D022`. The preparation helper also patches the immediate A and X values. Thus one raster-controlled slot can switch memory selection or change how the same packed multicolor data is interpreted, without branching between differently sized store paths inside that slot.

This specifically uses **CIA2's direction register `$DD02`** in its bank-selection path; it is not a listing typo for the ordinary `$DD00` port latch. Initialization sets `$DD00` to zero, and the bank table varies `$DD02` over `$3C..$3F`. The paired VIC `$D018` and direction tables each contain 18 entries at `$966E` and `$9680`.

On alternating preparation phases, the palette path swaps multicolor registers 1 and 2 between palette indices **0 and 12**. That changes which two-bit selector receives gray versus black. It establishes two interpretations of the packed data; it does not by itself establish unrestricted independent bitplanes, arbitrary colors, or the whole tunnel-generation algorithm. In particular, it would be inaccurate to call this a general RGB blend.

The helper's phase counter selects a bank/charset step on even phases and a palette step on odd phases. We separately interpreted **36 finite helper cases**, covering all 18 memory-selection entries and both palette orientations. Every case returned with the independently expected immediate values, store opcodes, and destination addresses. `quondam-window-proof.json` records those cases. This executes no raster loop and supplies no native timing claim.

### Raster scheduling and asset reuse: bounded conclusions

Static control-flow inspection links this window to the IRQ path at `$9300`. Handlers at `$9300` and `$935C` schedule their next raster IRQ by adding four to a line counter; the first path writes `$D011`, reaches the patched window, and prepares a later window through `$939B`. The second path changes the low scroll bits of `$D011` and hands control back. This is a real register-scheduled raster mechanism in the original binary. A static four-line *requested schedule* is not a measured four-line deadline, complete VIC counter proof, or independently measured frame rate.

The initialization also copies 2 KB from `$7800` to `$2800` and replicates a 1 KB block from `$3800` into `$7800/$B800/$F800`. These are further concrete data-reuse operations. We have not reconstructed the asset generator, proven which frame each selected data bank represents, or measured its compression ratio or visual precision.

**Why this is interesting.** The display can change through memory selection and color interpretation, rather than a full software redraw. This is a storage/encoding/raster trade, distinct from making each arbitrary 3D edge cheaper. It is not yet a replacement for our rotating geometry renderer. A useful next investigation would independently decode the bank assets and the `$D011` schedule, then relate both to a native capture; no native lane was opened here.

## Lunatico rain — identity confirmed, algorithm still unresolved here

The author's **Rain Effect Explained**, posted **6 November 2026**, concerns the bumpmapped rain part of **Lunatico from X 2016**. It is a new explanation of an old production, not a rain demo released in 2026. The page describes a mixture of older and newer techniques but supplies the video rather than textual details. Its video ID is `F2TkzDaa8A4`. [Author rain page](https://www.linusakesson.net/scene/lunatico/rain.php), [original Lunatico release/download](https://www.linusakesson.net/scene/lunatico/index.php)

The official Lunatico ZIP is preserved, 272,533 bytes, SHA-256 `1e22a02eeef77d98a8c348b03cbb808b489b3cf842d14db25dbf72f79eb9e6c0`. The earlier advertised English-caption request returned zero bytes; this pass retains that result rather than claiming no public transcript exists. No rain-part code was identified or executed, so there is no support here for a particular height-map equation, normal calculation, lookup organization, update rate, or amount of precalculation. The already-covered MISC sprite-crunch article concerns a different Lunatico part and cannot fill that evidence gap.

The next concrete route is an available transcript/source or identification of the rain part in the original disks. Until then this remains an attributed bumpmapping lead, not an inspected mechanism.

The later [rain investigation](lunatico-rain.md) resolves part of that gap
through the original disk's technical note. Its own text decoder recovers
the author's WIZ/character-graphics explanation and the distinction between
fast ripple animation and slower bumpmap recalculation. The new video's
transcript, exact bumpmapper and native scheduling remain open.

## Another recent primary lead: The Demo Coder / Fairlight (2024)

The Demo Coder was released **23 November 2024**, winning the Mysdata C64 demo competition; Trident is the credited coder. His **25 November author comment** distinguishes its full-row stretching from forcing extra badlines that only repeat the first raster row of an eight-row character block. He says this production stretches all eight rows. He also identifies counter-scrolling in the layered DYPP part and horizontal movement that exposes the source pixels in its MEGA picture mode. [Release, credits, and Trident's technical comment](https://csdb.dk/release/index.php?id=247776)

Those are useful, phase-specific author statements. His suggested firsts/records remain qualified author claims; they were not independently established. The comment does not provide the full register schedule. The later FairLight TV discussion is a future source to examine, not a substitute for a transcript read in this pass. The downloaded disk was directory-listed only: 196,608 bytes, recognized by c1541 as 40 tracks, SHA-256 `b8c54fc1ca41c00cd81773ecff780649d892bc6497a84b7c67c79a9235d95e9b`. No effect was unpacked or run.

## Provenance and remaining work

All fetched pages, originals, text extractions, scripts, and receipts are in `build/research/frontier-followup/`. `downloads.json` distinguishes new HTTP fetches from reused original artifacts and records URL, size, and SHA-256. The prior caption receipt is explicitly named `prior-transcript-status.json`. The CSDb disk URL is [the original release artifact](https://csdb.dk/getinternalfile.php/263070/fairlight-the-demo-coder-fbc7cb83.d64); c1541's directory output is preserved separately.

The substantive new inspected mechanism is Quondam's dual-role store window and packed-data color reinterpretation. The rain algorithm remains open; the full-row stretcher is a separate recent primary-author lead. None of these findings implies runtime general 3D, a guaranteed 50 Hz rate, or a drop-in optimization for our current filler. The broad research goal remains open.

The later [Demo Coder binary investigation](demo-coder.md) now reconstructs all
68 complete in-place images, including raw tails that its decompressor leaves
in their original loaded positions. It identifies reachable raster candidates
and checks a 50-case bank/bitmap-selector family. Native stage identity and
the full-row-stretching mechanism remain separate questions.
