# November 2026 frontier follow-up: sprite data, mirroring and independent interrupts

This pass adds three primary-source cases absent from the existing research map:
The Dragonbond (June 2026), Viva Las Vegas (September 2026), and Tusari 2:
The River (May/June 2025). The last is a game developed from a technical demo;
its released assembly and sprite assets provide the strongest source-level
check here. A separate October 2026 release is preserved as an unresolved lead.
The cutoff is **8 November 2026**. None of these findings establishes a
historical first, a measured frame rate or a runtime 3D renderer.

## The Dragonbond: author-described intermediate sprites

[The Dragonbond](https://csdb.dk/release/?id=262185), by Abyss Connection,
was released **6 June 2026** at X. **Background** is credited for code and
graphics. His group's [demo page](https://englishclass.de/~wolf/ac/demos)
publishes both the original disk and an 18-page bilingual
[making-of PDF](https://englishclass.de/~wolf/ac/assets/downloads/demos/the-dragonbond-making_of.pdf).
The PDF's creation metadata says 26 May 2026; this is document metadata,
not an independently established publication date.

On printed page 7, the author gives a concrete sprite handover example:
an unexpanded sprite starts at Y=100 and its successor at Y=121. Y can be
prepared from the current sprite's second line. From line 110 the pointer
selects an intermediate 63-byte image: **bytes 0–29 are the next sprite's
head; bytes 30–62 are the current sprite's tail**. A later pointer switch
selects the complete successor. This moves pointer/Y work away from the
boundary, leaving time for X/color changes. The stated nine-line windows
are author claims, not measurements here.

The explanation is part of an artwork-specific construction: almost all
eight sprites overlap the elf/moon area, with 64 logical sprites overall.
It also describes point-specific X/color changes and hires sprite overlays
on multicolor bitmap pixels. This is a disclosed prepared-data scheduling
technique, not evidence of extra simultaneous hardware sprites.

The rendered page was inspected and agrees with the extracted text. The
30/33-byte split corresponds exactly to ten new rows plus eleven old rows
at three bytes per sprite row. That arithmetic is internally consistent;
it does not prove the pointer-fetch window, Y retrigger behavior, or the
released demo's actual schedule. No assembly listing was recovered from
this PDF, and no pixel, register or timing comparison was performed.

Both the group disk and the release-page
[CSDb disk](https://csdb.dk/getinternalfile.php/280588/the-dragonbond.d64)
are **174,848 byte-identical bytes**, SHA-256
`37854b4e3426349ee03bc759f5bed8ad9a6c7f0404a469f1ae5163918cf50300`.
The group PDF and
[CSDb PDF](https://csdb.dk/getinternalfile.php/280589/Making%20of%20The%20Dragonbond.pdf)
are also identical: 2,286,989 bytes, SHA-256
`b6ad3ad2e96dae340f995ac7f8dbd1012c4c773272ccaed44c36ba9ee64fde2f`.

The DOS directory contains many artwork aliases pointing to track 18,
sector 2, plus `MAKING-OF-DRAGON` at 24/16 and `SHADOWS-PROLOGUE` at 24/3.
All three distinct ordinary sector chains are extracted unchanged under
the receipt directory. Their names do not establish their executable
purpose, depacker or loader. In particular, the author's Bitfire statement
about the story part does not identify the acquired bootstrap by itself.

**Next native case:** boot this exact original disk normally, bind the
intro's loaded image and sprite data, then observe the relevant pointer/Y
writes and DMA fetches around one consecutive pair. Match the actual
intermediate data to both adjacent images before generalizing the PDF's
simplified example. This gives a more precise acceptance question than a
generic claim that the picture uses a sprite multiplexer.

## Viva Las Vegas: an authored quarter and checked web-image symmetry

Censor Design's [Viva Las Vegas](https://csdb.dk/release/?id=264488) was
released **19 September 2026**. In his
[21 September article](https://c64portal.pl/2026/09/21/en-viva-las-vegas-by-censor-design-my-graphics/),
credited artist **Carrion** says he drew one **160×512-pixel quarter** and
**Bob** supplied programmatic/hardware mirroring. This is artwork-author
evidence about the intended representation. Quiss's
[20 September production credits](https://csdb.dk/release/?id=264488&show=notes)
name this part **Four ways mirror**, with Bob for code and Carrion for
graphics, so the article can be attached to a specific part.

The three original article PNGs support a bounded independent result:

| Published image | Stored dimensions | Exact relationship checked |
| --- | --- | --- |
| [mirror_final.png](https://c64portal.pl/wp-content/uploads/2026/09/mirror_final.png) | 320×512 | Every neighboring horizontal pixel pair is equal: 81,920 pairs. |
| [m1.png](https://c64portal.pl/wp-content/uploads/2026/09/m1.png) | 640×512 | Left half equals the quarter; right half equals its horizontal reflection. |
| [m2.png](https://c64portal.pl/wp-content/uploads/2026/09/m2.png) | 640×1024 | Top equals m1; bottom equals its vertical reflection. |

The comparison checks all RGBA components of **983,040 stored pixels**
across m1/m2, with zero differences. Consequently, the apparent discrepancy
between the author's 160-pixel width and the file's 320-pixel width is
explained by exact horizontal duplication in this published asset. The
logical source is 160×512; its displayed quarter is 320×512. This geometry
does not establish the C64's visible viewport, loaded bitmap layout,
scrolling trajectory or raster mirroring instructions. These are web
illustrations, not independently reconstructed native output.

The original
[two-disk ZIP](https://csdb.dk/getinternalfile.php/283333/Viva_Las_Vegas-CD.zip)
is 316,043 bytes, SHA-256
`81ca3067002c53c3eaf313f4b10b86f8c506bb6c6015bbf52a82cbb234aee1ad`.
Its only members are the two 174,848-byte disks:

| Original member | SHA-256 |
| --- | --- |
| `Viva_Las_Vegas-CD_s1.d64` | `98c0999f093d18cb152a081185c19e4d6908ad71787add1be56748dce28c3bf5` |
| `Viva_Las_Vegas-CD_s2.d64` | `e194670ab00def063f88db6c65c09d3cea63b5b281a695174bdee0d35f69859e` |

The currently listed separate
[fixed side 2](https://csdb.dk/getinternalfile.php/284246/Viva_Las_Vegas-CD_s2_fixed.d64)
is preserved separately, SHA-256
`b41f1a41963b100614a3e749f21726968306fe4ebc75168bb9199912356219b5`.
It differs from the ZIP's side 2 at **136,131 byte offsets**. It must not
silently replace that original during later runtime/source comparisons;
this count does not diagnose the fix or imply that many code bytes changed.

Bob's **20 October** release-page comment additionally links Martin Piper's
[general teardown](https://www.youtube.com/watch?v=n6R9ZqJudKM),
[FLI disk analysis](https://www.youtube.com/watch?v=KjuSMGK8TJU), and
[AGSP scroller analysis](https://www.youtube.com/watch?v=mRNjCUO2mZs).
These are creator-endorsed analysis leads, not acquired transcripts or
effect source. No mechanism claim in this note is taken from their videos.

## Tusari 2: one sprite carries three independent bullet positions

**Martin Piper's** [own release page](https://martin-piper.itch.io/tusari-2-the-river)
links the [public source subtree](https://github.com/martinpiper/C64Public/tree/7cea879b93f66231c1cc3c5bd782c14b71e24d7a/Tusari2/FLDParalax)
and calls the bullet method **Sprite Shift-Plexing**. His explanation says
one sprite holds up to three bullets, changing X during its display, then
reuses the sprite vertically. He also claims simultaneous raster-aligned
NMI/IRQ scrolling and sprites. The historical-priority wording remains his
claim. V4's source/release commit is
[`7cea879b93f66231c1cc3c5bd782c14b71e24d7a`](https://github.com/martinpiper/C64Public/commit/7cea879b93f66231c1cc3c5bd782c14b71e24d7a),
dated **4 June 2025, 09:59:45 UTC**; the earlier IRQ source was committed
1 May 2025. This is a separate source family from the 2026 demos above.

The checked mechanism is more specific than ordinary eight-sprite
multiplexing:

- [Data.a](https://github.com/martinpiper/C64Public/blob/7cea879b93f66231c1cc3c5bd782c14b71e24d7a/Tusari2/FLDParalax/Data.a)
  imports SpritePad bytes at `$5000`, skipping `$1009` source bytes.
  [FLDParalax.a](https://github.com/martinpiper/C64Public/blob/7cea879b93f66231c1cc3c5bd782c14b71e24d7a/Tusari2/FLDParalax/FLDParalax.a)
  selects **frame 144 for hardware sprite 2**, with multicolor and X
  expansion enabled. Combining that layout with the imported asset places
  this exact 64-byte slot at file offset **`$2409`**.
- The original
  [game.spd](https://github.com/martinpiper/C64Public/blob/7cea879b93f66231c1cc3c5bd782c14b71e24d7a/Tusari2/FLDParalax/data/game.spd)
  slot has nonzero pixel rows **2–4, 10–12 and 18–20**, all three groups
  byte-identical: `015014 aaabaa 0ffc14`. All other pixel rows are zero.
  Thus the artwork itself reserves three eight-line bands for independent
  X values. Its 64th byte `$8C` is outside the 63 sprite pixel bytes.
- [IRQSparse2.a](https://github.com/martinpiper/C64Public/blob/7cea879b93f66231c1cc3c5bd782c14b71e24d7a/Tusari2/FLDParalax/IRQSparse2.a)
  contains **23** chained bullet IRQ expansions, at the source-programmed
  lines `67+8r`, `r=0..22` (67 through 243). Each loads that band's X from
  `BulletSprite_XPos[r]`. Only rows 2, 5, 8, 11, 14, 17 and 20 update sprite
  Y, preparing 91, 115, 139, 163, 187, 211 and 235 respectively. The final
  expansion returns to the bottom-border handler. This is a checked
  macro/asset schedule, not a trace of where instructions complete.

The X update performs `ASL`, stores the low byte, and uses carry to set or
clear only bit 2 of `$D010`. An exhaustive arithmetic check of **65,536**
input/shared-register pairs confirms that the encoded coordinate is always
`2*BulletSprite_XPos[r]` and the other seven sprite-X bits survive. The
five ordinary player-bullet slots reject duplicate Y-band indices; the
smartbomb instead writes every band's X array. This explains the useful
representation: prepared repeated vertical artwork, separately controlled
horizontal positions, and sparse vertical retrigger updates. It is not
three freely positioned images on the same scanline.

[IRQSparse.a](https://github.com/martinpiper/C64Public/blob/7cea879b93f66231c1cc3c5bd782c14b71e24d7a/Tusari2/FLDParalax/IRQSparse.a)
shows how the second interrupt source supports this division. CIA2 Timer A
is configured with `CyclesPerRasterPALC64-1`; Timer B counts Timer A
underflows and raises NMI. Its handlers update scroll/color/`$D011` state
and program later intervals, while VIC raster IRQ handles the sprites.
The bottom-border IRQ disables CIA2 interrupt sources. These instructions
support the architecture claim; they do not prove raster alignment,
interrupt interaction under every load or safe worst-case timing.

Eleven selected source/assets/PRGs have their Git blob identities checked
against both the immutable V4 tree and the current repository tree at
`ef95e2e3b96d401918d6bbeec0836269d6dadb9c`; every selected file is unchanged.
The bundled **V4 PRG** is 20,640 bytes, SHA-256
`25eda8652880dc37615db82c2cd8c055b613e33fc6ec1cdf30dfc3f4c957ad4a`.
As an independent release binding, the
[published CSDb V3](https://csdb.dk/getinternalfile.php/269113/Tusari2TheRiver_V3.prg)
matches the repository's V3 exactly: 20,452 bytes, SHA-256
`2c8c09e07fe6d683d035b1273ab2031540249a6cf753ea5c00323f240d5e31a9`.
That V3 identity does not prove that V4 was rebuilt. The build file embeds
time/date/machine/user fingerprint text before assembly and uses a separate
packer, so a reproducible build must account for those inputs explicitly.
No compiler, packer or original routine was run here.

## October lead and evidence retained

[The Mode Coder](https://csdb.dk/release/?id=264779), by Dual Crew, is a
**4 October 2026** one-file demo with **Metal Maniac** credited for code.
His [5 October note](https://csdb.dk/release/?id=264779&show=notes) identifies
a large beer in the side border. The
[original disk](https://csdb.dk/getinternalfile.php/283720/the_mode_coder-dc.d64)
was acquired: 174,848 bytes, SHA-256
`20b54552c0c5f7bd2edd14c5f0ab9ca3278f8992c875d10e3c5aebc079bf9dd9`.
The real PRG directory entry starts at 17/0. No algorithm article or
released effect source was recovered in the bounded routes checked, so no
sprite/border/raster mechanism is inferred from its appearance or title.

All original bodies, selected source files, extracted disk inputs and
checks live under ignored `build/research/frontier-20261108/`.
`acquisitions.json` pins 40 successful HTTP bodies and headers;
`findings.json` records 22 immutable Git blob checks, sprite layout/schedule,
PNG equality results, ZIP member identities, disk directory entries and
the separately preserved fixed-side differences. One unrelated CSDb ID
initially guessed for Dragonbond is explicitly excluded; the event-linked
release 262185 and both identical original disks supply its authority.

The tracked producer resolves the repository root from its own path and
reads the saved inputs under `build/research/frontier-20261108/`. It can
be repeated without network or downloaded code (Python and Pillow are
required):

```sh
rtk proxy python3 research/frontier-2026/november.py
```

The producer is 10,520 bytes, SHA-256
`ddc7466fc0496b299540b090680a60955892a632d6efa565fb10fe802d996bc0`.
The fresh `findings.json` is 1,882,362 bytes, SHA-256
`0d36903c9cfcd055e980343f0668946d66d6765cdcf393e3527aa4de1f868974`,
and pins this tracked producer's path, byte count and hash. Before this
change, the original ignored producer and receipt were preserved unchanged
under `pre-tracked-producer/`: `analyze.py` is 9,579 bytes, SHA-256
`0ca754b23182c67679a4975db5060370fa24b8f0ce411e2b11f648b662842b0a`;
`findings.json` is 1,881,752 bytes, SHA-256
`b788f534b6020f305cb03ccf03e55e82abb2d14c321287fbfd5118bba6718886`.
The tracked producer verifies both archive identities and requires every
research result to equal that preserved receipt before adding producer
metadata. The fresh offline run reproduced all original check counts.

Passing means the listed saved bytes, source identities and bounded
arithmetic/asset relationships agree. There was **no native execution,
VICE/process control, assembled source-to-release proof, C64 scanout
reconstruction or measured cycle budget** in this lane. The strongest
transferable idea is to spend storage on intermediate/repeated sprite
rows so register publication can happen in wider windows; its actual
benefit must be measured in the intended renderer or original case.
