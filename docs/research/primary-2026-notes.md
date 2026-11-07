# Primary sources: an exact finite-bob mechanism and unresolved 2026 effects

Research date: 7 November 2026. The substantive result is a code-and-asset
check of **Raistlin's No Bounds finite bobs**, not a newly discovered
implementation of The Hat or Aloft. The older effect gives a concrete
example of masked drawing and background restoration. This pass also
identifies lft's separate 2026 *Rodents in the Attic* explanation, but
recovers no transcript and makes no mechanism claim from its video.

## Finite bobs: preserve the background instead of XORing it

Raistlin's [Finite Bobs article](https://c64demo.com/finite-bobs-nobounds/)
is dated **5 June 2023** and explicitly concerns *No Bounds*. It describes
AGSP movement, character-set splits, bob plotting and restoration outside
the visible area. This is effect-author evidence. The discussion of a
full-screen successor in Aloft remains the **peer attribution** preserved
in the [February note](february-2026.md), not proof that this source is its
2026 implementation.

The matching [published source subtree](https://github.com/RobertTroughton/C64Demo-PublicReleases/tree/965807c511e2025b5c5e1ffb2a6235a4efd6ae5b/NoBounds/Parts/InfiniteBobs)
is pinned to commit `965807c511e2025b5c5e1ffb2a6235a4efd6ae5b`.
Its C++ function `InfiniteBobs_ConvertBobToASM` matches the article's full
generator excerpt after whitespace normalization. Eight selected files
match their immutable Git blob identifiers. No downloaded C++, assembly
or C64 program was executed.

The [generator](https://github.com/RobertTroughton/C64Demo-PublicReleases/blob/965807c511e2025b5c5e1ffb2a6235a4efd6ae5b/NoBounds/Parts/InfiniteBobs/InfiniteBobs.cpp#L57)
embeds the artwork into four unrolled plotters for horizontal phases
0, 2, 4 and 6 physical pixels. The actual bob image is **18×15**, with
two identical physical pixels per multicolor sample. Magenta marks
transparency; white, gray and black map to selectors 2, 1 and 3.
For each packed destination byte, it constructs a preserve-mask and
replacement data. Mixed bytes use the equivalent of
`new = (old & preserveMask) | data`; fully opaque bytes can store an
immediate value, and wholly transparent bytes need no store.

This is masked overwrite, not ordinary OR drawing and not XOR
transparency. A covered black pixel is still an opaque replacement.
Four phases × three byte-columns × fifteen rows give **180 byte sites**:
90 partially masked, 62 opaque and 28 transparent. Our independent
pixel-ownership oracle checks each site against **all 256 old bytes**:
**46,080 comparisons pass**. Dropping the coverage mask and using only OR
fails **4,544** of those cases. That negative control demonstrates the
specific information the mask preserves.

## A clean half-image restores a full mirrored image

The source's [runtime map and restore routine](https://github.com/RobertTroughton/C64Demo-PublicReleases/blob/965807c511e2025b5c5e1ffb2a6235a4efd6ae5b/NoBounds/Parts/InfiniteBobs/InfiniteBobs.asm#L1266)
give the important storage trade: fourteen 2 KB character sets hold a
512×448 image across `$4000..$77FF` and `$C000..$F7FF`; a clean 14 KB
half-image occupies `$8000..$B7FF`. The two VIC banks contain different
vertical portions of the image, not two complete alternating framebuffers.

Restoration reads one 256-byte half-row and writes a complete **512-byte
character row**, eight physical raster lines high. For the right half,
the destination offset is `offset XOR $F8`: reverse character-column
order while retaining the three within-character Y bits. Each byte's
four **two-bit samples** are reversed too. Reversing all eight individual
bits would change selectors and is the wrong operation.

The independent check starts from the actual RGB background PNG. Its
left/right symmetry and paired multicolor pixels are verified. Direct
packing of its left half matches the supplied `ImageData.bin` in
**all 14,336 bytes**. Applying the source-derived restore mapping then
matches a separately packed full image in **all 28,672 bytes**. The wrong
individual-bit reversal differs in **4,523 bytes**. This establishes the
asset format and restore transformation, not an arbitrary scene renderer.

The author's important limitation is retained: his clear schedule and
motion were deliberately coordinated, and he warns that extending the
effect too long exposes sliced trails. The assembly's
`RestoreHorizontalLine` uses a prepared clear-row table and runs after
the bob plots; this is not generic damage tracking or a proof that any
motion may erase any old row safely. The article's approximate per-bob
cycle figure is author-reported; this pass measures no CPU or raster cost.

## The 2026 searches: what was and was not recovered

Fresh checks of [Trident's site](https://trident64.github.io/),
[Quiss's homepage](https://www.quiss.org/) and
[Raistlin's article index](https://c64demo.com/) did not expose an original
Hat end-scroller or Aloft pattern/Kefrens implementation. This is a bounded
route result, not a claim that no public explanation exists. The earlier
[creator-note/source inventory](february-2026.md) remains authoritative;
viewer comments and matching-looking older techniques do not fill that gap.

A new primary lead is [lft's Rodents in the Attic page](https://www.linusakesson.net/scene/rodents-in-the-attic/index.php).
The [release record](https://csdb.dk/release/?id=262145) dates the production
**6 June 2026**, at X'2026; the author's page and
[technical explanation video](https://www.youtube.com/watch?v=uZ1atMUOUMU)
are dated **30 July 2026**. Keep release and explanation dates separate.
The official player metadata identifies `lftkryo` and advertises an English
auto-caption track. Two simple caption requests and three requests derived
from that signed track each returned **HTTP 200 with zero bytes**. Those
responses are preserved. No transcript was recovered, no source listing was
found on the acquired author page, and third-party video summaries are
excluded from the technical conclusions.

The other retained failure is a guessed `/finite-bobs/` URL returning 404;
the author's index resolves the actual `/finite-bobs-nobounds/` article.
That was a wrong route, not a missing primary explanation.

## Reproduction and evidence

[primary_notes.py](../../research/frontier-2026/primary_notes.py) validates
the archived HTTP bodies, exact acquisition-index hashes, reused immutable
repository tree/commit, eight source/asset blobs, article/source excerpt
identity and the two independent image/mask contracts. Original downloaded
host code is never imported or executed. The proof's negative controls
exercise actual source assets rather than invented hardware fixtures.

```sh
rtk proxy python3 research/frontier-2026/primary_notes.py
```

The ignored evidence folder is
`build/research/frontier-2026/primary-notes/`; its final receipt is
`primary-notes-proof.json`. `--fetch-missing` can reacquire missing bodies
using the retained pinned acquisition indexes; changed remote content
fails the original hash. A fresh checkout needs those retained evidence
indexes, as with the other research proofs.

There is **no native, CPU, source-build/release equivalence, complete bob
trail visibility, full-frame timing or physical-hardware claim** here.
The next useful check is to bind this source and its generated plotters to
the original No Bounds part before investigating any alleged Aloft reuse.
For Rodents, the next input should be an original transcript or its actual
released code, not an inferred algorithm from a screenshot.
