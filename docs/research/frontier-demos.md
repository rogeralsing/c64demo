# C64 frontier demos: first research pass

Research date: 7 November 2026. This is a set of inspection candidates, not a ranking or a claim that their techniques have been reproduced here. The broad research remains open. Production code was not changed and no emulator was launched for this pass.

Author explanations are distinguished below from archive metadata and our own offline inspection. A video showing an effect establishes its appearance, not its algorithm, update rate, or amount of precomputation. Download receipts, original pages, extracted archives, and disk-directory listings are preserved under `build/research/frontier/`; `downloads.json` records URLs, sizes, SHA-256 hashes, and failed requests.

This first-pass ledger is historical. Later investigations now cover the
[released Freespin loader and video fragment](freespin.md),
[Mufflon's embedded NUFLI viewer](nufli.md),
[A Mind Is Born's byte/state map](a-mind-is-born.md),
[Quondam's native row-reuse mechanism](quondam-raster.md), and the
[Tower Power sphere and patterned cube](tower-power-binary.md).
Their detailed notes supersede the initial inspection limits below; remaining
work is tracked in the [current research queue](README.md#current-investigation-queue).

## 1. Lunatico — lft, X 2016

[Author release page](https://www.linusakesson.net/scene/lunatico/index.php), [MISC technical article](https://www.linusakesson.net/scene/lunatico/misc.php), [production record](https://csdb.dk/release/?id=151273). The author identifies it as his X 2016 entry, placed second; the official ZIP contains two disk sides, a sleeve, and soundtrack files.

**Documented technique.** Massively Interleaved Sprite Crunch uses sprite offset `$35` as the origin for crunch schedules of several lengths. Crucially, pixels encode the schedules: background collisions pack the eight sprites' control decisions into `$D01F`, which supplies the Y-expansion control at `$D017`. Thus the VIC supplies information already combined into the byte the raster routine needs. The article includes timed assembly and the constraints around cycle 15, sprite DMA, and avoiding badlines. Its sprite-carpet example reduces row-update work from at least 34 to 12 cycles, with timing restrictions. [Author's explanation](https://www.linusakesson.net/scene/lunatico/misc.php)

**Rate caveat.** The author explicitly updates only two or three columns each video frame, choosing the third after measuring time left following the music player. This is not evidence that all eight columns' animation states change at 50 Hz. [MISC implementation details](https://www.linusakesson.net/scene/lunatico/misc.php)

**Inspection / next step.** Official archive unpacked; offline directory confirms `note & vsp tool` on side 1. No unpacked code or raster traces inspected. Next: extract that note, identify the greetings part's actual register schedule, and compare sprite-pointer updates with the article. This is especially interesting as hardware-assisted bit assembly, beyond accelerating a software filler.

## 2. Freespin — Reflex, Gubbdata 2021

[Author site](https://www.quiss.org/freespin/), [release and credits](https://csdb.dk/release/?id=205500). Released 3 July 2021; code by Quiss/Matthias Kramm, music by kb and PVCF, graphics by Felidae. This is a **1541-only production**, not a C64 effect accelerated by its drive. The author describes 16 effects over 3 minutes 40 seconds, video through the serial outputs, and sound through the head-stepper mechanism. [Author overview](https://www.quiss.org/freespin/)

**Documented technique.** DATA/CLK plus a resistor generate sync, black, and white levels. The drive CPU handles the signal itself; a four-cycle port write limits adjacent transitions to at least 32 nominal video pixels. The raster article combines video timing and two VIA timer waveforms, including an `RRA` sequence that shares work between audio and sync. The reported 412×256 signal is not 412 independently addressable pixels of arbitrary graphics. [Video-generation article and assembly](https://www.quiss.org/freespin/raster.html)

**A second frontier: encoding for the decoder.** The loader article explains a standard-D64-compatible custom payload encoding, synthesized with finite-domain constraint solving so that a very small add/XOR decoder recovers the desired bytes. The final resident loader is reported as 254 bytes at `$0702`, with exactly seven blank video frames per part load. This is a storage/CPU trade: expensive offline encoding simplifies the runtime decoder. [Loader article](https://www.quiss.org/freespin/loading.html), [published loader assembly](https://www.quiss.org/freespin/loader.html)

**Inspection / next step.** Author D64 downloaded and its directory listed offline. Loader assembly read, not assembled or executed. Next: map its encoded sectors to the published decoder and independently decode one part before considering unusual video hardware or emulator work.

## 3. Crest Slide Story 90% / NUFLI — Crest, LCP 2009

[Production record and author comments](https://csdb.dk/release/?id=81153), [archive cross-check](https://demozoo.org/productions/100044/), [Mufflon 1.0 source-package release](https://csdb.dk/release/?id=93314). The slideshow is dated **18 July 2009**, not 2010; the separate Mufflon 1.0 converter release is 14 August 2010. Credits include Crossbow and Bitbreaker for code and DeeKay for the concept, text, and graphics work.

**Documented technique and restrictions.** The original Mufflon README credits Crossbow with the NUFLI/MUIFLI formats and editors. It describes static NUFLI at 320×200, FLI every second line, at most three colors per ordinary character region with the sprite color shared across six characters, and specialized graphics in the left FLI-bug area. Those exceptions matter: “three arbitrary colors independently in every 8×2 block” is too loose a description. MUIFLI is a separate interlaced choice; the converter's 79 blended colors are a selected low-flicker subset, not additional physical VIC palette entries. [Original source/README/editor package](https://csdb.dk/getinternalfile.php/180585/Mufflon1.0-source+GUI+Bonus.zip)

**Inspection / next step.** The four-image slideshow ZIP and source package were unpacked. The tooldisk contains NUFLI/MUIFLI editors and example pictures. Source inspection found `convert_nufli` and embedded 6502 display-code arrays in `mufflon.c`/`mufflon.h`; this is host converter source with display bytes, not a fully commented display assembly listing. Next: recover that displayer's register schedule and decode one example's sprite/bitmap ownership. It offers a much richer color/display direction than the current three-color mesh, with a substantial raster and asset-preparation cost.

## 4. A Mind Is Born — lft, Revision 2017

[Author's complete technical walkthrough and download](https://www.linusakesson.net/scene/a-mind-is-born/index.php), [production record](https://csdb.dk/release/?id=155560). A 256-byte C64 executable submitted to, and winning, the Oldskool 4K competition in April 2017. “4K compo entry” does not mean the executable occupies 4 KB; the downloaded file is exactly 256 bytes including its load address.

**Documented technique.** Code, clock state, SID shadow registers, color state, and a tiny script deliberately overlap. A linear-feedback shift register generates melody material; a main loop writes changing font data through the cyclic stack and combines neighboring screen entries into a cellular-automaton-like pattern. SID envelope state also influences the visuals. The final transition reuses the machine's reset sequence. The article includes the assembly and explains why otherwise accidental stack/interrupt interference is aesthetically acceptable here. Its 60 Hz music timer is not evidence of a 60-frame independent visual renderer. [Author walkthrough](https://www.linusakesson.net/scene/a-mind-is-born/index.php)

**Inspection / next step.** Official PRG size and `$0801` load header checked; author walkthrough read, no execution or instruction trace. Next: annotate the 254 payload bytes and their overlapping roles. The lesson is composing a strong audiovisual result from coupled processes and intentional reuse, rather than scaling up geometry or framebuffers.

## 5. Boo! — Reflex / Quiss, X 2023

[Author's BRR-lines explanation](https://www.quiss.org/boo/), [published threshold-selection Python](https://www.quiss.org/boo/bitreverse.html), [release/credits/downloads](https://csdb.dk/release/?id=232949). Released 3 June 2023, first in the X 2023 C64 4K competition. The article's bottom-of-page “2021” copyright/footer is not the release date.

**What the author claims.** A 172×172 sprite-filled cube at 50 Hz, with line interpolation costing five cycles per step. The two-instruction BRR inner step compares against bit-reversed position order and incorporates the carry into an integer increment. This is a different distribution of fractional notches; it is not an exact replacement for rational/Bresenham rasterization. Threshold setup needs division and selection, so short lines can favor other methods. The author says Boo computes up to nine slopes per frame in the 1541. Those are author-reported figures, not whole-renderer timing measured in this research pass. [BRR article](https://www.quiss.org/boo/)

**Inspection / next step.** PRG and D64 downloaded; PRG is exactly 4096 bytes. Explanation and published selector source read; binary execution/reverse engineering belongs to the separate emulator lane. Next: isolate the drive's threshold calculation, actual C64 line loop, transfer cost, and sprite fill layout. Compare total frame cost and visual differences, rather than treating a five-cycle arithmetic step as a five-cycle plotted pixel.

## Downloaded artifacts

The links are public release URLs; hashes identify the bytes fetched for this pass. Archives were opened and source text was read, but downloaded host programs were not run.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| [Lunatico official ZIP](https://hd0.linusakesson.net/files/lft-lunatico.zip) | 272533 | `1e22a02eeef77d98a8c348b03cbb808b489b3cf842d14db25dbf72f79eb9e6c0` |
| [Freespin author D64](https://www.quiss.org/freespin/freespin.d64) | 174848 | `7798f74046ee767a2e05e4e05c12e7b7453640c579ebc3d5daed20ce019f890c` |
| [Crest Slide Story 0.9 ZIP](https://csdb.dk/getinternalfile.php/77572/CrestSlideStory0.9.zip) | 637415 | `7a0b6d72c7b7aa67d78280e7fb66201447a0b9910a6d6a2c2a54ed3a8c9ac13a` |
| [Mufflon 1.0 source/GUI/bonus ZIP](https://csdb.dk/getinternalfile.php/180585/Mufflon1.0-source+GUI+Bonus.zip) | 2589912 | `c610bc91ec7f60bd7c19c19fe0ecc4e97288a26b12e65febad3827da1f4d4adf` |
| [A Mind Is Born author PRG](https://hd0.linusakesson.net/files/a_mind_is_born.prg) | 256 | `7da29c8eed5acc39c5a1d3f0d40f5057c516cb6d2a04a18b15d71e6f8903f1f5` |
| [Boo PRG](https://csdb.dk/getinternalfile.php/246018/boo.prg) | 4096 | `4105eecdb5ee4e5927b22cc5afe029a1d14a0919d633cdf291460b94ec9b4920` |
| [Boo D64](https://csdb.dk/getinternalfile.php/246019/boo.d64) | 174848 | `758833094ec3d003c497ff968638512323b3b83ac155f962df447da43729fd50` |
| [Quondam Tunneling author PRG](https://hd0.linusakesson.net/files/lft-quondam-tunneling.prg) | 33675 | `e86e4bcf40e859f4ec3fcc83a86f8f0c172b6efa0a38d8dc199a85717fddc17c` |

## Backlog and unresolved evidence

- **Tower Power / Camelot.** User-selected next investigation: obtain the original 1994 full release separately from the 1993 92% preview, establish credits and any disk/author notes, then identify the patterned sphere and cube in the actual binary. Their appearance alone does not establish texture mapping or precomputed geometry.
- **Quondam Tunneling / lft, Fjälldata 2026.** [Author production page](https://www.linusakesson.net/scene/quondam-tunneling/index.php) calls it a full-screen 3D tunnel and supplies the PRG; [author explanation page](https://www.linusakesson.net/scene/quondam-tunneling/explained.php) is video-only. The PRG is downloaded. English auto-captions are advertised by YouTube, but caption requests returned empty bodies. No implementation claim is taken from the anonymous comment proposing repeated character rows and sprite masking. Obtain a transcript or inspect the binary before promoting a mechanism to a finding.
- **Lunatico rain / bumpmapping.** [Author explanation](https://www.linusakesson.net/scene/lunatico/rain.php), published 6 November 2026, identifies bumpmapped rain and a mix of old/new techniques, but supplies only video. Same transcript limitation as above; saved status is `transcript-status.json`. This is a timely follow-up, not yet an inspected implementation.
- **High-color animation versus static images.** Follow the NUFLI source trail into REU-backed productions only after explicitly recording required expansion hardware, frame data volume, and whether motion is replayed assets. A rich display format alone does not establish realtime image synthesis.

For a next implementation choice, first reproduce a small isolated mechanism and measure its entire budget: preparation, display/raster occupancy, memory, loader/drive communication, and actual update cadence. No production in this note is assumed to be a drop-in upgrade to the current mesh engine.
