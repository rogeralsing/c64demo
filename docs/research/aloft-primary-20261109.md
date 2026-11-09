# Aloft: targeted creator-content follow-up

Research date: 9 November 2026. **The moving three-layer pattern and the
bitmap/flipped Kefrens drawing mechanisms remain open.** This pass reads
specific creator pages, documentation and assembly content beyond the earlier
[path-inventory follow-up](frontier-effects-followup.md). It recovers a useful
Scrap-credited code route, but no source-to-Aloft association. A passing receipt
means the retained acquisition/content checks pass, not that an effect is solved.

## Keep the scenes separate

The [creator-submitted CSDb interaction note](https://csdb.dk/release/?id=259056&show=hidden)
still attributes joystick-controlled movement of flipped Kefrens on side 2 to
Sparta's 1 February submission. That is an input/interaction statement. It does
not identify a buffer, drawing routine, inversion formula or entry address.
It does not establish that the moving three-layer pattern or the separately
described bitmap-Kefrens scene uses the same code.

The release discussion's report that Quiss explained the pattern at Fjälldata
is a route to a possible explanation, not the explanation's technical content.
This lane supplies no layer-composition, sprite/bitmap or prepared-data theory
for that scene. The [February note](february-2026.md) and the original-release
orientation retain their own attribution limits.

## What the creator content actually supplies

[Quiss's own writings page](https://www.quiss.org/writings.html) leads to a
[blog listing](https://www.quiss.org/writings_blog_posts.html) containing five
2010–2012 typography/mobile articles. The acquired listing contains no Aloft
entry. His [C64 legacy listing](https://www.quiss.org/legacy.html) covers older
Reflex work; it likewise contains no Aloft entry. These are content checks of
the listed pages, not a crawl of every old project or proof that no unpublished
explanation exists.

The resolved [Scrap profile](https://csdb.dk/scener/?id=1929) and
[Sparta profile](https://csdb.dk/scener/?id=29482) both link the group website.
Its [resources page](https://gp-64.com/resources) describes tools including
Sparkle, SPOT, DART and Scrap Writer 64. Its [news page](https://gp-64.com/news)
contains the group-site launch item, rather than an Aloft technical article.
Scrap Writer 64 is presented as a note-writing tool; its presence is not an
effect-source association.

The acquired public gist lists for the two identified creator accounts are
empty, with no pagination link. Exact public commit-message searches for
`Aloft` under those author accounts return zero items with
`incomplete_results=false`. The `Aloft+C64` repository query and `Scrap+C64`
user query also return zero. These results are limited to the exact API query
domains; repository metadata and commit-message searches do not inspect all
code, private projects or deleted history.

Two actual documentation blobs further separate projects from target effects:

| Content read | Verified scope |
| --- | --- |
| [Soul on Fire README at the earlier pinned revision](https://github.com/matthiaskramm/soul_on_fire/blob/d094947170cbe18eee0e553bfa2dc59a7d474fd2/README.md) | Describes the separate X2024 4K intro, including its sprite-vector and distortion modules. No Aloft reference. |
| [Sparta's Sparkle README](https://github.com/spartaomg/SparkleCPP) | Describes a general multifile IRQ loading/linking solution. No Aloft effect explanation or source association. The acquired blob, rather than a moving branch name, is pinned by the receipt. |

No instruction from either project is relabelled as an Aloft mechanism.

## A new Scrap code route, with an explicit identity boundary

[Raistlin's SIDquake source](https://github.com/RobertTroughton/SIDquake)
credits Scrap for an adapted column visualizer. Following the actual source
directory reaches
[SIDPlayers/ScrapColumns/ScrapColumns.asm](https://github.com/RobertTroughton/SIDquake/blob/1d7dbb4b56547f2fcf816f528cb5cf46c9bcceba/SIDPlayers/ScrapColumns/ScrapColumns.asm)
at immutable revision
`1d7dbb4b56547f2fcf816f528cb5cf46c9bcceba`.

The 46,568-byte source has Git blob SHA-1
`f8664351a4870755c74116d486b25023d7bbe38a` and content SHA-256
`b637cac2df842ea4a4436b1cb3d666c848183404418798d1c0bc1c13b4fe8778`.
Its header explicitly credits Scrap and identifies the SIDquake adaptation.
The comments and constants describe twenty columns, three eight-row sections
driven by separate SID voices, a multicolor charset and two screen buffers.
Neither `Aloft` nor `Kefrens` occurs in the acquired source.

This is an actual code-content finding, beyond the previous tree-name search.
It supplies a future source/author route. It is **not** a match to Aloft's
moving three-layer pattern: three SID display sections alone do not establish
three composited moving pattern layers. No original Aloft bytes, data or scene
have been matched to this file, and the source was neither assembled nor run.

## Access failures are retained results

Official GitHub code-content searches for `Aloft` under `matthiaskramm` and
`spartaomg` both return HTTP 401 with an authentication-required error. The
complete bodies, requests and headers remain. No content-search result or
absence conclusion is inferred from those failures; no login or alternate
authenticated route was attempted.

The attempted WordPress search-API route on Raistlin's site returns HTTP 404.
The ordinary `?s=Aloft` URL returns the static landing page without an Aloft
match, which does not establish that a full-text search occurred. Neither is
treated as a successful whole-site technical-content audit. Web-tool opens
that failed while ordinary public GETs succeeded, and two initial local
read-path mistakes, are separately recorded in `discovery-notes.json`.

## Retention and offline replay

The new [accepted receipt](../../build/research/aloft-20261109/primary-source-analysis/accepted-01/primary-source-proof.json)
pins **30 HTTP response bodies / 437,544 bytes**: 27 HTTP 200, two HTTP 401 and
one HTTP 404. Seven request plans and every individual request, response
metadata record and raw body form a closed 97-file acquisition listing.
URLs, discovery/purpose, method, request headers, UTC start/end, redirects,
status, response headers, byte lengths and SHA-256 values remain unfiltered.
The listing is 17,395 bytes, SHA-256
`f6a92c878040b59c4da2e29860a3903809f2c67a49e1315aca041ea23a11ffd5`.

The [stdlib producer](../../research/aloft-20261109/primary_sources.py) checks
every listed identity, request/body binding, exact error boundary, returned
search/gist shape, selected HTML content and the four decoded Git blobs.
For each decoded blob it verifies the Git object SHA-1 as well as SHA-256.
The Scrap source route is bound through the pinned branch and successive
immutable directory/file API requests. The original source bodies are data;
the producer never imports or executes them and performs no HTTP requests.

The producer is 12,139 bytes, SHA-256
`afc993dee9eaea061f5a93ea7c8502fadc37781b376d32c19bb57ae0d7980e5c`.
The accepted proof is 242,217 bytes, SHA-256
`393e7311e20e8b82d623f388dcbbce96b46aaba91b28a64062b0cfaaee222346`.
The [fresh self-replay](../../build/research/aloft-20261109/primary-source-analysis/self-replay-check.json)
matches all three outputs / 427,955 bytes exactly. Its 695-byte report SHA-256
is `5d649852702446b29c259518aadd55a434fe79f26a557ff1196c8fc1a313990d`.

```sh
rtk proxy python3 -B research/aloft-20261109/primary_sources.py --output build/research/aloft-20261109/primary-source-analysis/<fresh-directory>
```

The earlier source-gap note and all 6,049 previously inventoried artifact
identities remain untouched. This lane sends no messages to creators,
downloads no video/audio, starts no emulator, runs no target CPU model and
executes no downloaded host code. The practical next boundary remains a
specific creator explanation or original instruction/data association for
each distinct scene. The broad research goal remains active.
