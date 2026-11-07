# Sprite interleave: rolled data buys a pointer-update window

Raistlin's [Sprite Interleave](https://c64demo.com/sprite-interleave/) article is dated **12 October 2026**. Its examples are older productions: **The Dive**, released by Genesis Project on [30 June 2019](https://csdb.dk/release/?id=179128), and **Memento Mori**, released by the group on [19 September 2020](https://csdb.dk/release/?id=195841). The article rewrites his earlier [Codebase64 explanation](https://codebase64.net/doku.php?id=base:sprite_interleave), whose archived page records a last modification by Raistlin on 26 October 2020. These dates describe the publications and releases separately.

The concrete trick is to separate two schedules. Normal-height sprites restart every **21 image lines**, while their pointers advance through blocks every **20** or **16** lines. The new block is rolled so its internal row number matches the sprite's already-running row counter. Adjacent blocks contain identical data for their overlapping rows. Consequently, different sprites can accept their new pointers on different sides of a shared row without displaying different image data. Raistlin credits Christopher Jam for the original idea and help.

This is a sprite-memory layout and pointer-multiplexing technique. It is distinct from our renderer's alternating even/odd field updates. It neither reconstructs 3D geometry nor provides a general polygon filler.

## The overlap contract

An independent way to define the layout is: for pointer step `s`, block `b` contains image rows in the closed interval `[s*b, s*b+20]`. A row `y` goes into internal sprite row `y mod 21` in **every** block whose interval contains it. For eight sprites across, source byte `xByte` has offset:

```text
64 * (8 * block + floor(xByte / 3))
  + 3 * (y mod 21) + (xByte mod 3)
```

Each sprite reserves 64 bytes, of which 63 contain its 21 three-byte rows. With step 20, rows `20,40,60,…` appear in both neighboring blocks. With step 16, the first **five** rows of each new interval also belong to the previous block. Merely copying multiples of 16 would be insufficient; the article's complete table and its five-line-overlap explanation agree with the interval definition.

For a 200-line image, step 20 needs 10 rows of eight blocks: **5,120 allocated bytes**. Step 16 needs 13 rows: **6,656 bytes**, or 1,536 more. The article describes the former's one-line pointer window as tight and the latter's five-line window as more forgiving. Its badline reasoning concerns a correctly scheduled carpet; it is not a guarantee that arbitrary pointer writes or IRQ entry phases are safe. No hardware timing was measured in this lane.

## Published production code, not just diagrams

Raistlin's [20 November 2023 source announcement](https://csdb.dk/forums/index.php?roomid=11&showallposts=1&topicid=162980) links his [public release repository](https://github.com/RobertTroughton/C64Demo-PublicReleases). The source snapshot here is pinned to commit **`965807c511e2025b5c5e1ffb2a6235a4efd6ae5b`**, dated 25 December 2025, and Git tree **`2a9bc04218fb7c60d744e8eb1b86ca4cda044eca`**. The nine selected files are validated against both their recorded SHA-256 and the tree's Git blob identities. The unchanged cached tree remains available to other research lanes.

The Dive's matching part is **`VertBitmap`**, not the separate `GPLogo` outro. Its [host converter](https://github.com/RobertTroughton/C64Demo-PublicReleases/blob/965807c511e2025b5c5e1ffb2a6235a4efd6ae5b/TheDive/VisualStudioProject/C64-RaistllinCodeGenerator/Source/DemoParts/VertBitmap.cpp#L18) weaves three sets of seven rows of eight sprites. For block `b` and row `k`, it reads source image row `20*b+k` and stores it at internal row `(k+21-b) mod 21`. Because `20*b ≡ -b (mod 21)`, that destination is exactly the global row modulo 21. The original `InitialSpriteLogos.map` supplies all 10,752 input bytes.

The [6502 source](https://github.com/RobertTroughton/C64Demo-PublicReleases/blob/965807c511e2025b5c5e1ffb2a6235a4efd6ae5b/TheDive/Build/Parts/VertBitmap/ASM/VertBitmap.asm#L135) independently shows the two schedules: `SetSpriteY` advances by 21, while `SetD012` schedules successive pointer work 20 lines apart. Its SAX/STX macro updates the pointer table for the currently displayed bitmap bank, at `$4FF8` or `$CFF8`. This supports the article's description of sprites over the bitmap scroller. It does not establish a captured screen or a cycle-accurate bank transition.

Memento Mori's matching part is **`RotatingGP`**. Its [converter](https://github.com/RobertTroughton/C64Demo-PublicReleases/blob/965807c511e2025b5c5e1ffb2a6235a4efd6ae5b/MementoMori/PC/Parts/RotatingGP.cpp#L39) creates a rolled base image and a lookup containing both destination rows for each overlap. Later it detects byte sites that vary across the **16 prepared animation frames**, deduplicates their 16-byte value vectors, and emits blitter stores for every destination in that lookup. A shared row therefore receives both writes when animated. This is prepared artwork with runtime byte blitting, not a live geometric rotation of the logo.

Its [IRQ source](https://github.com/RobertTroughton/C64Demo-PublicReleases/blob/965807c511e2025b5c5e1ffb2a6235a4efd6ae5b/MementoMori/6502/Parts/RotatingGP/RotatingGP.asm#L195) requests IRQ lines `0,77,96,116,…,236`, programs Y values `58,79,100,…,247`, and selects pointer groups beginning `$80,$88,…,$C8`. The sprite allocation is `$E000..$F3FF`; the pointer table is `$FBF8..$FBFF`. These are source-derived addresses and requested raster values, not observed IRQ arrival cycles or proof that every stored artwork row is visible.

The related [Big Animating Sprite Logo article](https://c64demo.com/big-animating-sprite-logo/), dated **13 April 2022**, says the two logo halves update on alternate frames at 25 fps, while the carpet's horizontal movement updates at 50 fps. Those are **the author's rates**, not measurements here. Its description of frame selection is also not treated as byte-identical to this repository snapshot: the public assembly uses an up/down `AnimTable` for artwork selection and separate tables for horizontal movement. Neither the articles nor a source snapshot alone proves that a particular released disk contains an identical build.

## Faster pointer writes

The article's SAX trick loads `X=base+4` and `A=$FB`. Alternating `SAX` and `STX` writes the low and high groups of four pointers, with three `INX` instructions between the pairs. For a base divisible by eight, clearing bit 2 in `base+4+i` yields `base+i`, for `i=0..3`. The same increment thus advances two pointers. The source uses this actual sequence in both productions.

Counting from the first completed store to the last, the plain sequence has seven four-cycle stores and seven two-cycle increments: **42 nominal cycles**. SAX reduces the increments to three: **34**. These counts exclude setup, the first store, IRQ overhead and VIC stalls; they are not captured bus phases. The host check covers all **32 aligned bases and 256 pointer values**. Base 4 is a counterexample to dropping the alignment requirement.

The alternative `$D018` method in the 2026 article is an explanatory option: prepare pointer sets in two screen matrices and switch the selected matrix with one register write. Both matrices must also provide suitable background screen data. This lane found direct SAX use in the selected production sources; it does not attribute the two-screen alternative to these particular parts.

## What the finite check proves

[The acquisition/check script](../../research/sprite-interleave/acquire.py) runs only our Python, image decoding and arithmetic. Its interval-based ownership oracle is separate from the translations of the published C++ row-roll arithmetic. It checks:

- **483 cells** in the article's 16- and 20-line layout tables against independent row ownership.
- All **5,120 base-layout bytes** and **81,920 packed bytes across 16 Memento Mori frames**. All 1,721 varying logical byte sites have the necessary destinations. They produce **894 and 911 store sites** in the two halves; static LDA/STA/RTS counting gives 7,158 and 7,294 nominal cycles and 5,365 and 5,467 code bytes, matching the article's totals. The 16-byte-aligned vectors and frame indices `0..15` avoid indexed-load page crossings in this calculation.
- All **10,752 bytes** of The Dive's three woven sets, including zero sprite padding, against the independent interval mapping.
- Negative controls: omitting animated duplicate destinations changes **946 packed bytes across the 16 frames**; reversing The Dive's roll direction changes **4,125 bytes**.

The Memento Mori source's reverse bottom-half loop omits image row 94. That row is constant in the published assets, and the complete frame comparison still passes. This is an asset-specific result, not a general proof for arbitrary odd-height replacement artwork. The checks do not run the original C++ converter, generate or assemble its machine code, emulate sprite DMA, or compare a native display. Their packed-memory results are not PNG or beam-output predictions.

## Original release provenance and reproduction

The linked release routes were also acquired without executing their contents:

| Linked original artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| [The Dive](https://csdb.dk/release/download.php?id=222527), raw 35-track D64 | 174,848 | `3a21fb0a297bfb91d8c5c55ef38490305ffbcd92a133bbb36a16a406786778aa` |
| [Memento Mori](https://csdb.dk/release/download.php?id=241934), ZIP | 413,608 | `6743becfe76e731a9c3e048ba13d0335cd07cb7ea9c7f0e8722e962ae7e6634e` |

The latter contains three 174,848-byte disks, the original NFO, file ID and three SIDs; every member hash is retained. The NFO credits the rotating GP logo's code to Raistlin and graphics to JonEgg. This corroborates part/author identity, not source-to-binary equivalence. The Dive response was initially saved with a `.zip` filename; its actual response is a raw D64. The initial metadata and misnamed copy are retained, and the corrected filename contains identical bytes. This format correction is not an HTTP acquisition failure.

All **20 direct HTTP acquisitions succeeded**. The browser tool separately refused Codebase64 and both CSDb release pages; the successful direct responses are archived, so those browser failures are not reported as unavailable primary evidence. The receipt pins each route, response identity, selected source and original artifact, together with the reused 2026 article SHA-256 `13341d774dda1a23ae78aec3a21765e0fcf41fd4017d01c6a4d84777a59eafe8`.

After acquisition, the bounded check is offline:

```sh
rtk proxy python3 research/sprite-interleave/acquire.py
```

`--fetch` acquires missing routes while preserving and validating successful cached responses. The result is `build/research/sprite-interleave/source-proof.json`. A useful next native case would be the original rotating-logo part: first bind its loaded bytes to the source build, then observe actual pointer writes and overlapping sprite rows under the relevant VIC timing. That remains a follow-up; no native, runtime-performance or universal glitch-free result is claimed here.
