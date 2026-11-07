# Three new primary-source leads from 2025–2026

Survey date: 7 November 2026. These cases extend the existing reading map;
they are source/author evidence, **not new native or performance proofs**.
The strongest next case is **We Are The Anomaly's Arcade Scroller**: it has
an unusually specific author explanation, published assembly and an original
two-disk download ready to compare.

## 1. We Are The Anomaly: distribute work across raster lines and frames

[Elder0010's article](https://www.elder0010.com/projects/we-are-the-anomaly/)
is dated **30 November 2025** and credits him with code, Psych858o with music
and Sulevi with graphics. It describes the Genesis Project/Extend production
that won Transmission64 2025. [CSDb](https://csdb.dk/release/?id=257561)
dates the release **29 November**; retain that one-day difference rather
than replace either source's date.

The author's Arcade Scroller explanation combines a 936×96 floor, 96
independent horizontal scroll values, pre-skewed artwork and byte shifts
when fine scrolling wraps. He deliberately disperses wrap phases to reduce
simultaneous expensive lines. Remaining raster time updates sections of a
hidden upper-wall buffer. **50 fps and drive-stress results are his claims**,
not measurements reproduced here. The separate Stretcher discussion also
explains sprite priority over bitmap selector `%01` and linewise `$D017`
stretch control; it is a different routine.

The [published source](https://github.com/elder0010/WeAreTheAnomaly/tree/4361d011f56f27014c0b6cd542718ca0b23666d8)
is pinned to **`4361d011f56f27014c0b6cd542718ca0b23666d8`**, committed
14 December 2025. Its README explicitly connects the repository to this demo
and states that it contains Kick Assembler source and binaries. Static
inspection confirms a 96-line setting, per-line carry accumulators, `DCP`
fine-scroll updates and a raster-threshold gate before upper-buffer work:

- [scroll_logic.asm](https://github.com/elder0010/WeAreTheAnomaly/blob/4361d011f56f27014c0b6cd542718ca0b23666d8/Parts/ArcadeScroller/scroll_logic.asm)
  expands one line-update body per configured floor line.
- [upper_scroll_logic.asm](https://github.com/elder0010/WeAreTheAnomaly/blob/4361d011f56f27014c0b6cd542718ca0b23666d8/Parts/ArcadeScroller/upper_scroll_logic.asm)
  reads `$D012`, applies a `CMP #$24`/`BMI` gate, and advances pixel/color
  copying in sections. This is a signed wrapped-range test, so its actual
  raster-call context must be established before calling it a deadline.
  Its comments' cycle estimates are not adopted as measured costs.

The [author ZIP](https://www.elder0010.com/uploads/we_are_the_anomaly/we_are_the_anomaly_gp_ext.zip)
is archived at 1,265,847 bytes, SHA-256
`cc33d92f4b3ac732c340ecd65ce7389e6cd4d1e5a360d3cfc69e92210d882eb3`.
Its two 174,848-byte disks are:

| Member | SHA-256 |
|---|---|
| `WeAreTheAnomaly-Side1.d64` | `d452497845598cca8936fdf57c60fdc9c70cd7e64110e049fa6fc7d735f940cd` |
| `WeAreTheAnomaly-Side2.d64` | `3b537ade95fc1312d0c1b6ef2d042041e454ca3055c687fd8aaaf46a4a00a41e` |

The source snapshot is post-release. It was not assembled or matched to the
production disks in this survey. **Concrete next case:** bind the original
Arcade Scroller payload to this source, then observe the per-line `$D016`
sequence and the gate-controlled upper-buffer stores. Measure actual wrap
work and publication timing before making a complete 50 Hz or transferable
budget claim. This is particularly relevant to amortizing occasional work
in our renderer; it is not an automatic reduction of rendering cost.

The [bounded Arcade Scroller follow-up](anomaly-arcade.md) now enumerates
the complete accumulator/fine-scroll period and the upper-wall jobs. It
also matches the repository's release disks to the author download and
distinguishes its production `Link` binary from a different `Parts` build.
The [original Sparkle payload](anomaly-binary.md) now independently matches
both loaded Arcade Link sections, all 41,523 bytes. Source rebuild and native
Arcade scheduling remain open checks.

## 2. Codeboys & Endians: authored line imagery with explicit prepared paths

[Codeboys & Endians](https://csdb.dk/release/?id=249805) is Booze Design's
**3 February 2025** Fjälldata winner. The full release forum contains
[Pex Mahoney Tufvesson's 5 February, 08:50 explanation](https://csdb.dk/forums/?roomid=12&showallposts=1&topicid=170065#170074).
Account **3701** is both that poster and the credited coder **Mahoney**.
This is direct effect-author evidence, rather than a viewer guessing from
the image.

He describes at most four vertical lines built from alternating multicolor
sprites with roughly 80 prepared slopes, randomized starting Y, and
priority-based white intersections. Up to seven non-overlapping horizontal
lines traverse five angle-specific charsets. Their coordinates are prepared:
he says calculating them live cost three horizontal lines. Drawing top to
bottom avoids screen double buffering in his design. These are author
claims, not locally checked limits. The later viewer's 50 fps wording is
not silently attributed to him.

A useful secondary lead in the same thread is HCL's explanation of
Pernod's separate character-explosion effect: masks make seven glyph states
per four-pixel chunk sufficient in his reasoning. HCL expressly says he did
not code that effect. Keep his contributor explanation distinct from
Pernod's own code or an independently reproduced glyph packing proof.

The original download route is
[CodeboysAndEndians.zip](https://csdb.dk/getinternalfile.php/265674/CodeboysAndEndians.zip),
identified in the archived release page; it was **not downloaded or executed**
in this survey. The full forum HTML is pinned at SHA-256
`4e11cc357bfa9e6dc3fcc3d0ae5b86c817fe56ab1bde4bd701e992bdd1ffc127`,
with the isolated primary post preserved separately. Next useful questions
are actual slope storage, sprite reuse and charset traversal—not whether a
matching-looking bar can be implemented with a generic polygon filler.

## 3. Censor Hires Bubbles: source-confirmed offline 3D, live presentation

Carrion's [23 May 2026 article](https://c64portal.pl/2026/05/23/kod-w-c-grafika-w-blenderze-jak-napisalem-intro-na-c64/)
describes **Censor Hires Bubbles Intro**, released
[28 February 2026](https://csdb.dk/release/?id=259782) for ICC 2026. Code and
graphics are credited to Carrion, music to Magnar. The author explains a
64-character ECM logo, sprite/character parallax, and 25 Blender-rendered
metaball images converted to binary sprite data. LZO expansion happens
outside raster interrupts. The apparent 3D forms are prepared animation,
not evidence of a runtime metaball or perspective renderer.

The article's GitHub link initially appears misleading because the
repository description still names a **2022 invitation**. The correct
2026 project is its **`censor_intro/`** subtree. At commit
**`84207a9fcd4c1268e4f5515699403ae9cc1fb8b3`**:

- [main.c](https://github.com/c64portal/c64_code/blob/84207a9fcd4c1268e4f5515699403ae9cc1fb8b3/censor_intro/main.c)
  explicitly names the intro and Jan/Feb 2026. Its main loop waits for a
  frame, expands the selected image to `ANIM`, and reverses through 25 frame
  indices. IRQ functions are separate from these expansion calls.
- [mem.h](https://github.com/c64portal/c64_code/blob/84207a9fcd4c1268e4f5515699403ae9cc1fb8b3/censor_intro/mem.h)
  embeds the animation with LZO. The pinned tree contains 25 raw 512-byte
  `.bin` frames; the [converter](https://github.com/c64portal/c64_code/blob/84207a9fcd4c1268e4f5515699403ae9cc1fb8b3/censor_intro/data/anim/png2spr.py)
  is archived but was not run.

The repository's release PRG is **byte-identical** to the
[published CSDb PRG](https://csdb.dk/getinternalfile.php/277735/censor_intro_icc26.prg):
13,497 bytes, SHA-256
`46f203bb81a108b3474dad41c08e82134cd3227534e284dc0130eaeff5bc7b9a`.
That establishes the bundled artifact link, not that the current source was
rebuilt reproducibly. No compiler or C64 program was run. Scheduling and
partially updated sprite-data behavior still need native inspection before
making a frame-rate or tear-free-presentation claim.

## Supplement, provenance and bounded failures

Raistlin's [Sprite Interleave](https://c64demo.com/sprite-interleave/), dated
**12 October 2026**, is a substantive new rewrite explaining overlapping
sprite data and pointer-update windows. Its examples are **The Dive (2019)**
and **Memento Mori (2020)**; it is not a new 2026 production. It is retained
as a teaching-source follow-up rather than substituted for the three cases
above.

[sources.py](../../research/frontier-2026/sources.py) archives 33 bounded
routes plus selected source files. All direct HTTP acquisitions succeeded.
The web tool had refused the full forum/API routes and a ZIP content type;
direct requests to the same public URLs succeeded. Those channel failures
are recorded separately, not described as missing author material. The
stale Carrion repository description was resolved by subtree and exact
release-PRG identity, not by assuming its root README described this intro.

The [receipt](../../build/research/frontier-2026/sources.json) pins response
metadata, original bodies, ZIP members, exact Git commits/trees, selected
Git blob identities and SHA-256 hashes, release correspondence and primary
post attribution. Default execution rechecks saved bytes; `--fetch` refreshes
all routes and `--fetch-new` fetches only newly added ones. No downloaded
script, compiler, CPU routine, emulator or host executable was run; no
messages were sent to authors. None of these three mechanisms is claimed
to be historically first or an already proven optimization for our code.
