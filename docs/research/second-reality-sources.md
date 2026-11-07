# Second Reality: author explanations and source boundaries

This bounded search did **not locate a published C64 Second Reality renderer
source or a per-effect explanation by its credited coders**. It found direct
AEG recollections, a contemporary coding review, and a concrete AEG explanation
of a **different 2003 production**. These have different evidential value.
None establishes the split between runtime work and prepared data in the
1997 vector, texture, fire or rotozoom parts.

The [original-release acquisition](second-reality.md) identifies the C64 demo
and the matching two-disk author/CSDb packages. The public
[Smash Designs releases page](http://www.smash-designs.de/c64demo.html)
confirms the production and download, but supplies no renderer explanation.
The [CSDb release](https://csdb.dk/release/?id=908) and
[Pouët entry](https://www.pouet.net/prod.php?which=1216) credit AEG and DCP.
An author's credit is not itself an algorithm statement.

## What the primary material supports

| Source | What is attributable | Limit |
|---|---|---|
| [Recollection: Demo Map Germany](https://www.atlantis-prophecy.org/recollection/?country=germany&load=demo_map), editorial history by Jazzcat with Se7en | An explicitly attributed AEG recollection says the winning end credits were already in the first showing. He connects the joke to the PC original's competition win. | A design anecdote, not a description of geometry, filling or data preparation. Do not adopt the surrounding article's inconsistent party-year chronology. |
| [Deutschlandfunk, Christian Fischer, 15 October 2005](https://www.deutschlandfunk.de/der-brotkasten-lebt-100.html) | André Bürger is identified as a C64 Second Reality co-programmer and speaks about extracting more from fixed hardware. | The interview's concrete development story concerns Turrican 3. It does not explain Second Reality's effects. |
| [The Impossible Thing author comments](https://www.pouet.net/prod.php?which=10607#c81370), August 2003 | AEG gives a specific character-based rotate/zoom explanation and confirms another participant's elaboration. | This is a separate production, six years later. It cannot identify the 1997 rotozoom routine. |

The old author homepage advertises a **Turrican 3 source release**. That link
must not be relabelled as Second Reality source. The biography/interview
routes located in this pass likewise did not yield a C64 Second Reality
implementation account.

## Related concrete mechanism: The Impossible Thing, not Second Reality

The Pouët account `4909` is credited as AEG on both productions. On
[25 August 2003](https://www.pouet.net/prod.php?which=10607#c81370), he claims
runtime computation without precalculated animation or a badline trick,
using an ordinary fullscreen character display. His key resource is a
16×16 texture and the 256 available glyphs. These are author claims, not
timings measured in this research.

[kb_'s 27 August explanation](https://www.pouet.net/prod.php?which=10607#c81849)
describes generating a glyph for each texture origin: a rotated/zoomed
4×4-texel fragment becomes an 8×8 glyph at 2×2 pixel sampling. The 40×25
screen then selects those glyphs according to the transformed texture
coordinates. [AEG's reply](https://www.pouet.net/prod.php?which=10607#c81860)
accepts that mechanism while rejecting kb_'s proposed identification with
Graham's zoomer or Chaos's rotate/zoom.

This is a useful example of reducing per-pixel work through character reuse.
It supplies no source-code, cycle-count or frame-rate proof here. Applying
it to Second Reality would require evidence from that demo's own code.

## Contemporary review: useful inspection targets, not author proof

The Relax 24 transcription labels its coding review **Clarence**, rather
than AEG or DCP. The [indexed source page](https://c64mags.untergrund.net/wiki/index.php?action=edit&title=Relax_24)
was available through web-search cached text; direct HTTPS raw/edit and HTTP
requests failed with connection refusal. The preserved cache is explicitly
separate from successful HTTP acquisitions and has not been checked against
the original disk magazine.

The [original Relax #24 archive is now recovered](relax24-archive.md),
including the side-1 LYNX program and all 21 side-2 PRG chains. That later
acquisition resolves the artifact route; decoding the original coding
review and comparing it with the cached transcription remain open. The
earlier failed wiki requests and their frozen receipt remain unchanged.

Its Second Reality section describes these visible characteristics:

| Part | Reviewer's description to investigate |
|---|---|
| Opening vector sequence | Expanded-sprite glenz object followed by a larger object using alternate raster lines. |
| Face/lens and rotate/zoom | Coarse 4×4 sampling. |
| Plasma | Character display using extended color mode. |
| Texture cube | 4×4 sampling with moving plasma-like faces. |
| Raytrace section | A moving line and reflections in a rendered scene. |

Those are review observations, not verified memory layouts or algorithms.
The section does not establish prepared geometry, live texture mapping or
a fire algorithm. Its animation wording is insufficient to decide which
data is streamed or computed. Unrelated articles, competition rules and
other productions in the same issue are excluded.

## Rejected shortcuts and unresolved questions

Later CSDb/Pouët viewer comments are not automatically author evidence.
Secondhand recollections about who coded a part, its development time or
undocumented opcodes need original corroboration. The acquired Second
Reality Pouët page has no comment by the credited AEG account; that is a
statement about this saved page, not every possible author posting.

[Future Crew's published repository](https://github.com/mtuomi/SecondReality)
explicitly identifies itself as **1993 Future Crew** source and data. It is
the PC production. PC source, anniversary interviews with its authors, and
later PC renderer analyses do not establish the C64 implementation.

The external material leaves the most useful questions open: which C64
parts calculate transforms at runtime; whether they consume prepared poses,
spans or complete animation; how the texture cube addresses its samples;
and how each effect trades resolution for update rate. The independently
recovered original disk notes and any subsequent code/native analysis
should answer those questions with their own evidence, rather than inherit
an algorithm from a similarly named PC effect or a later C64 intro.

## Reproducible archive and scope

[sources.py](../../research/second-reality/sources.py) preserves ten bounded
text routes: six succeeded and four failed. It reuses the three existing
author/CSDb acquisition pages without refetching them. The ignored
[receipt](../../build/research/second-reality/sources/sources.json) contains
response metadata and hashes, source classifications, explicit Pouët post
IDs/dates/account links, and the separate cached-review provenance.

| Saved successful response | SHA-256 |
|---|---|
| Recollection | `3e82a4de4ceae5b67bbf293f03c57a500d0c7bbee461b4f82fdb9a0d5fce879c` |
| Second Reality Pouët | `4a96cece67686d9244e100f86291d634fa2178688762d75606225369e86fa848` |
| The Impossible Thing Pouët | `dabcffc090830f85f84ea883e303492e1c9a52fa8cff28cfab8048befb45fe9e` |
| Deutschlandfunk interview | `1b0fe1d0ed496f68e46f2acfd9315b7b029df8ffd09d4fe95d53812a9560ad38` |
| C64-Wiki AEG biography | `38a17f95fbac760d5cee9d725725cbc7eaafa136d03b5f70933ab34cfabd27fb` |
| Future Crew PC README | `3549330a25f75c690c045f64e64b1cd134a7f8a3992086ec5167081a768c90c2` |

The three magazine routes refused connection; the linked Tell The World
interview route failed its TLS handshake. Their failures remain in the
ledger. No TLS verification was disabled and no failed body was treated as
an acquired article.

Running the script without `--fetch` rechecks the saved bodies, classifications
and post signatures offline. `--fetch` performs the bounded public-text
acquisition. This pass ran no emulator or downloaded program and made no
native-display, speed, sound or hardware-compatibility claim.
