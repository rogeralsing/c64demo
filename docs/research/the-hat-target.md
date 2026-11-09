# The Hat ending: concrete identifiers and a bounded source check

Research date: 8 November 2026. The useful new identifiers are **two distinct
font assets in the artist-linked collection**, not a recovered ending routine.
The original ending PC, its input/skip condition and production timestamps
remain unestablished by these web sources. The parallel original-disk
investigation owns the instruction/data binding.

## Keep the two fonts separate

In his retained [production note](https://csdb.dk/release/?id=259070&show=notes),
redcrab links [The Hat's artwork collection](https://c64gfx.com/release/259070).
That collection contains these separately named records:

| Record | Published name | Credited artists | Useful scope |
|---|---|---|---|
| [9985253](https://c64gfx.com/image/9985253) | The Hat – Shifted Font | Trident, redcrab | Candidate font identity for comparison with original loaded data. |
| [9985254](https://c64gfx.com/image/9985254) | The Hat – Shifted Ghost Font | redcrab | A different candidate; its name must not turn every Hat scene into a ghostbyte effect. |

Both acquired pages explicitly identify CSDb release 259070. Their structured
metadata and visible attribution agree on the names and artists. They offer
384×272 rendered PNG artwork and a link to the site's GFXquake converter.
That image framing is **not an established native display resolution**.
There is no direct `.prg`, `.bin`, `.64c`, `.chr` or `.d64` link among either
page's acquired anchors. This does not establish that original font bytes
are unavailable elsewhere, and converting the PNG would not recover the
original packed representation automatically.

These records are concrete discriminating search terms for the disk lane.
Neither page says which routine consumes its font. Their collection order
is not evidence of the demo's execution order. A match still needs original
font bytes or independently checked glyph shapes and a source-bound consumer.

## The ending itself is identifiable; navigation is not supplied

Martin Piper's retained official [teardown upload](https://www.youtube.com/watch?v=Vfnyczaf1Ao)
identifies the target as the **end upscroller showing a “hires” scroll in all
borders**, and links the correct [production](https://www.pouet.net/prod.php?which=105678).
This is uploader-authored target identification by a reverse engineer, not
an implementation explanation by either credited coder. Its 674-second
length is the teardown's length, not the production's ending timestamp.

The retained Hat hidden-information page has no submitted hidden entry.
The one production note is redcrab's artwork/500-frame PETSCII note. They
provide no supported skip key, controller address or ending-entry PC.
The credited coders remain Alfatech and Trident; that credit alone does not
assign the ending to one of them. Peer comments about the final upscroll,
balloons and earlier sprite tricks remain distinct observations, as explained
in the [February note](february-2026.md).

The [earlier transcript boundary](frontier-effects-followup.md) remains
frozen. This pass made **no caption, transcript, video or media request**.
No algorithm was inferred from empty responses or machine-generated chapter
titles.

## A content-level check closes one plausible uploader route

The previous follow-up checked repository paths. This pass reads **all twelve
Git blobs, 578,454 bytes**, at the already pinned uploader repository
[`martinpiper/C64FindCode`](https://github.com/martinpiper/C64FindCode/tree/f5f36e1fb0b68bd8337a4b3cb44849b19d8ea17d),
including files with generic names. Every acquired body matches its complete
immutable-tree length and Git blob SHA-1, in addition to a retained SHA-256.

The largest file,
[`features/FindCode.feature`](https://github.com/martinpiper/C64FindCode/blob/f5f36e1fb0b68bd8337a4b3cb44849b19d8ea17d/features/FindCode.feature#L1),
is **520,858 bytes**. Lines 1–5 explain its actual purpose: boot disk images,
detect loads and scan C64/1541 disassembly for drive-code signatures. Lines
29–50 specify CIA2/drive receive-code patterns; later rows enumerate historical
disk images. This is useful source context for excluding a false lead, not
Hat raster code. Its process-launch, cleanup and emulator commands were read
as text and **never executed**.

Across all twelve bodies, the recorded case-insensitive identifier checks
find no `The Hat`, upscroll, all-border, `7a825b1`, release 259070/105678,
Trident/Alfatech or Fjälldata match. This is a bounded content result for that
specific repository, not a claim that generic code cannot be reused or that
the uploader's other repositories contain nothing relevant. `C64Docs` remains
at the earlier tree-inventory scope; its mostly mirrored hardware documentation
was not relabelled as an ending writeup.

## Reproduction and limits

The new [passive producer](../../research/the-hat/target_sources.py) consumes
the frozen prior release/watch/tree inputs, twelve new immutable raw Git
bodies and the two new font pages. It parses JSON and HTML as data. It
executes no downloaded host code, CPU interpreter, native emulator or build.

Fresh offline replay:

```sh
rtk proxy python3 -B research/the-hat/target_sources.py \
  --acquisition build/research/the-hat/target-analysis/acquisition-02 \
  --artwork build/research/the-hat/target-analysis/artwork-01 \
  --output build/research/the-hat/target-analysis/fresh-replay
```

Current receipt: `accepted-02/target-proof.json`, **12,118 bytes**, SHA-256
`f5cd77924eaea60457c8107703157a915a9fdc09249528385bbad7fe5bfc4dcb`.
Producer: **11,256 bytes**, SHA-256
`c52bfcc71efbf6ceaf12056aeeb047f68be7912bb3ae8b5dbc6f8f201197395f`.
Fresh `replay-01` reproduces both output files byte for byte, **23,374 bytes**.
Independent root source review found no material issue within this bounded
identifier/content scope. Its fresh passive replay also reproduces both
files exactly, without path normalization. The [552-byte root replay report](../../build/research/the-hat/target-analysis/root-replay-check.json)
has SHA-256
`0b799da45c158dc0168406df9d0bccf761246f12ff2bb9f43cc9e0ca6e347f13`.

Fourteen complete new HTTP responses are retained with request URLs,
timestamps, status, headers, bytes and hashes. The first acquisition attempt
retains one additional body but failed before writing its HTTP metadata;
it is not counted among the fourteen complete retrievals. Its manual failure
note and source copy remain, as does an offline failed literal-quote HTML
guard corrected to parse anchor attributes. These are preserved failure
artifacts, not full native execution receipts.

This source lane supplies two font candidates and a precise rejected source
route. Actual ending instruction/data recovery must come from the original
disk/loader and later native custody, not another broad title search.
