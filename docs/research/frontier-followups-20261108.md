# Star Wars scrollers: compressed row functions and safe reuse boundaries

Research date: **8 November 2026**. This adds a distinct representation to the
research map: font-row dictionaries plus precomputed bit-picking functions,
checked against a supplied production-part PRG. It is separate from the
previous No Bounds loading, finite-bob restoration and repeated-bob screen-map
checks. The examples are older effects, not new November 2026 releases.

Fresh creator-site and targeted search routes did not recover the requested
The Hat ending or Aloft pattern/Kefrens implementation. The retained Trident,
Quiss and Raistlin index bodies support that bounded search result; they do
not establish that the source is unavailable elsewhere. The attribution and
original-release limits in [the February note](february-2026.md) remain.

## Author explanation and the source snapshot

Raistlin's [22 March 2022 article](https://c64demo.com/star-wars-scrollers/)
explains his Rivalry/The Dive scrollers: reduce a font to reusable horizontal
rows, precompute the bit selections needed by a fixed perspective plane, and
draw output bytes with indexed loads and OR. Separate page-sized column rings
provide vertical movement without moving the whole text buffer. Adjacent-row
reuse can avoid recalculating some bytes. These are creator explanations of
those productions, not an account of The Hat or Aloft.

The checked later implementation is
[`NoBounds/Parts/StarWars`](https://github.com/RobertTroughton/C64Demo-PublicReleases/tree/965807c511e2025b5c5e1ffb2a6235a4efd6ae5b/NoBounds/Parts/StarWars),
with matching supplied assets in
[`NoBounds/Link/StarWars`](https://github.com/RobertTroughton/C64Demo-PublicReleases/tree/965807c511e2025b5c5e1ffb2a6235a4efd6ae5b/NoBounds/Link/StarWars).
The repository commit is **`965807c511e2025b5c5e1ffb2a6235a4efd6ae5b`**,
dated **25 December 2025**, rather than a claimed byte-identical rebuild of
an original demo disk.

This variant draws a **256×120** waisted plane centered within the bitmap.
Its width varies sinusoidally between approximately half and full width.
It uses **inverted** font tables and **AND**, unlike the earlier article's
ordinary bit tables and OR. Each source text character occupies 16 columns;
the output samples never require more than two character columns per byte.
The geometry is fixed in generated code; the text and its vertical phase
change. It is not a general runtime 3D projection renderer.

## Complete font and supplied-table binding

The original 512×16 font BMP and its 1,024-byte CharPad map agree in every
byte under independent image-pixel packing. The text's actual alphabet uses
**15 glyphs**. Their 240 horizontal rows contain only **20 distinct 16-bit
patterns**. Replacing each row with its dictionary index reproduces the
published **240-byte `SW-RemappedFont.bin`** exactly. Parsing only the active
C++ text literals, applying blank-line markers and alphabet remapping also
reproduces all **497 bytes of `SW-ScrollText.bin`**.

For each output byte, the source generator separates contributions by text
column. A contribution table answers: given one of the 20 row patterns,
which target bits should this column clear? Duplicate tables are stored once.
The independent producer enumerates output pixels and forms those inverse
tables from the original font image. It derives:

| Property | Checked result |
| --- | ---: |
| Distinct contribution tables | 295 |
| Stored slots per table | 24 |
| Live dictionary indices | 0–19 |
| Four unused slots | `$FF` |
| Complete packed table block, including padding | 7,544 bytes |
| Supplied PRG block location | file offset 105; loaded `$2067` |
| Matching row-pointer prefix | 32 bytes |

The **entire 7,544-byte block** occurs exactly once in the supplied
`StarWars.prg` and matches byte for byte. This binds the generated representation
to concrete C64 bytes; it does not establish equivalence of every generated
instruction or of the supplied PRG to the original release's loaded image.
The Sparkle script loads the remapped font at `$FD00` and text at `$E000`;
the assembly defines the visible column rings from `$CE00`.

Across all 3,840 output-byte positions, **593** have no contributor, **2,291**
have one, and **956** have two. The checker independently selects every
possible dictionary row for each contributor, reads the corresponding tables
from the actual PRG, and compares AND composition against direct pixel
sampling. **428,813 byte truth cases match**, with zero differences.
Replacing AND with OR produces **366,470 wrong cases** among the two-column
positions. The composition polarity is therefore part of the representation.

The generator pads table offsets relative to the start of its data block.
That block actually begins at `$2067`; **29 table bases permit a live index
to cross a physical page**. These are address-range facts, not observed
page-crossing counts or timings. A claim that every indexed load has a fixed
four-cycle cost would require additional execution evidence.

## Cyclic text indices and two limits of lazy row copying

The source's virtual vertical samples span offsets **0–131**. For a byte-valued
phase `p`, a displayed row selects `(p + offset) & 255` within its column page.
The next tail slot is `(p + 132) & 255`; it is absent from the current sample
set and is the next phase's farthest sample. All **256 phases** and **30,720
row-index relations** satisfy that bounded indexing contract. This does not
prove original buffer initialization, update ordering or hardware deadlines.

The generator can replace a new row's computed byte with the old next row's
bitmap byte when the vertical sampling difference is one and the horizontal
functions agree. **744 selected copy cells** pass an independent comparison
of both contribution functions and source-column identities.

Two additional source-selected cells fail universal function equivalence:

| Generated `(Y, byte X)` | What the source comparison misses | Literal supplied instructions |
| --- | --- | --- |
| `(79,19)` | Current cell uses column 9; next cell additionally uses column 10. | `$805F`: `LDA $F23F / STA $F23E` |
| `(92,2)` | Current table index 0 matches the zero-initialized unused slot of an empty next cell. | `$8CAE`: `LDA $F434 / STA $F433` |

Both six-byte instruction sequences occur uniquely at their listed supplied
PRG locations. For the first cell, **260 of 400** independently selected row
combinations disagree. One counterexample gives direct `$FF`, copied `$FE`.
For the second, **15 of 20** row choices disagree; one gives direct `$FE`,
copied blank `$FF`. These establish limits of the general reuse rule, not
observed visual defects in the demo. The actual text trajectory, skipped rows,
bitmap history, colors and sprite composition have not been reconstructed.
No original file or rendering code was changed to hide the exceptions.

The failed initial strict-copy check and its producer are retained under
`pre-lazy-refinement/`. A second archived producer/receipt under
`pre-default-slot-refinement/` records why the candidate comparison was
refined to include the original generator's zero-initialized unused slots.
The final receipt retains both exceptions explicitly.

The same source declares a 32-entry repeated-row array but initializes twelve
nonzero values. C++ zero initialization also marks **row 0** skipped. The
checker retains that concrete source behavior; it does not silently shorten
the array to twelve entries.

## Reproduction, identities and limits

The offline producer uses Python and Pillow:

```sh
rtk proxy python3 research/frontier-2026/followups.py
```

[`followups.py`](../../research/frontier-2026/followups.py) validates **19
acquired HTTP bodies**, saved response headers, a pinned acquisition index,
the immutable commit/tree link and **13 Git blob identities**. No downloaded
C++, assembly, packer or host script is imported or executed. The separate
The Dive BMP/MAP pair also agrees in all 1,024 bytes; its full 32-glyph input
contains 29 distinct rows. That full-input count is not substituted for the
article's reduced 28-row runtime alphabet.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Supplied `StarWars.prg` | 33,865 | `38dd86241bb0f53cb4749f548bbfd19015947bbf2f61121a045161ca66217b84` |
| `SW-RemappedFont.bin` | 240 | `ff77c38a8ed95e1695cef59fafbb0cfa2220e2a995d7f099155a09ef3b7bd16e` |
| `SW-ScrollText.bin` | 497 | `1b7654cd2f82806d53003ef6509d4cd93f696fa55ce5bb4ceaed0d52b914467b` |
| Predicted/matched font-table block | 7,544 | `496c309398d504c2140e576731bd9ac4163b4072fa2186a915657bd7abeefaf9` |
| Tracked producer | 17,295 | `5c84bcbb2fbb216f4504cb590355d6e1792085f4c48e03c880b540d56a39bbc2` |
| `followup-findings.json` | 8,765 | `6d3c9d4198281016c308ddf59fb6021d95e312e9fff74e8646edcb9bcf982e67` |

All original bodies, headers, failed-producer archives and the receipt remain
under ignored `build/research/frontier-followups-20261108/`. A fresh checkout
needs that retained archive for offline reproduction.

There was **no native/VICE execution, original C64 instruction execution,
source build, original-disk extraction, full displayed-frame reconstruction
or timing measurement**. The next concrete case is to bind the supplied
plotter to its original loaded part, recover the actual cyclic-buffer update
trajectory, and inspect the two reuse exceptions under those exact inputs.
The transferable optimization is broader: when a deformation is fixed,
precompute byte functions over a small source-pattern dictionary, then update
indices and reuse proven output. A moving arbitrary polygon needs a different
mapping or its own bounded source domain.
