# The Lab / Elysium: patterned polygons and open panels

The correct release has been downloaded and hashed, and its complete 49-page
extras note has now been recovered through the original reader in PAL VICE.
Brush identifies span filling extended with stencils for the border-vector
part. The original green sprite-vector stage and later multicolor bitmap
vector engine have now been identified separately. The exact open-cube script
has also reached its “AND NOW?” speech in the native program. A restricted
palette-aliasing priority trick explains its opaque two-layer overlap; the
tools that produced those projected inputs have not been recovered. The native
captures identify the stages and techniques, without claiming a pixel-identical
match to a supplied video pose. No production renderer was changed.

## Release and primary author evidence

[The Lab on CSDb](https://csdb.dk/release/?id=262146) identifies Elysium's demo,
released 6 June 2026 at X'2026, first in the C64 demo competition. The credited
coders are Brush, Digger, Jetboy, MMS and YTM. Its linked official site is
[thelab.elysium.pl](https://thelab.elysium.pl/); it returned HTTP 403 during this
investigation.

The release page contains useful first-person comments from Brush:

- **10 June:** the disk-turn models and truecolor vectors are drawn, with
  different techniques; neither is color cycling.
- **11 June:** in response to a request for effect descriptions, he points to
  the note on the extras disk.
- **20 June:** he describes the vector part as timer-based and says he tested
  old, new, and mixed CIA revisions.

These statements do not identify the green patterned part's VIC mode or prove
that every vector scene uses the same engine. [Author comments on the release
page](https://csdb.dk/release/?id=262146)

No complete source release or scene-input producer for these payloads was
identified in the bounded search. The included author note credits a concrete
span-filling approach; the subsequent original-code and native checks establish
the mechanisms below. General viewer comments about z-order or full-screen
vectors remain leads rather than implementation evidence.

## Downloaded artifacts

The release-page download is
[the-lab.zip](https://csdb.dk/getinternalfile.php/280582/the-lab.zip), 627,051 bytes.
SHA-256:
`ea4ab6a4f3c8b10a412e80e3a4f46f240405cf2a820a526f222af2b5e0e48717`.

It contains four 196,608-byte, 40-track D64 images plus macOS metadata:

| Image | SHA-256 |
| --- | --- |
| `side1.d64` | `80f61811796da8e95b4b3b53c12409a8f9b879a88e863006c8533b8f81ce6198` |
| `side2.d64` | `d34101d9b5852020ed56b3574aae854c7b16befff893df77a6d6ec08198cdf3b` |
| `side3.d64` | `62021d2ebe067d6d81bda0616a829856ee0aaad2cd2b063946fac4a422fa9448` |
| `extras.d64` | `d43c4b56e131e6738972eec164e482bfa4d94861926fbf932b14371296a462ba` |

The ZIP, disk images, saved release HTML, disk-directory/file manifest, and
research receipt are ignored artifacts under `build/research/the-lab/`.

A host-only DOS sector-chain reader extracted the extras disk's demo-note
bootstrap from track 18 / sector 2: load address `$0801`, 2,506 bytes, SHA-256
`0814e21a1bee0f7925450af3b647d4e18f5b4b560e2b3e23f13a1aa37a77fb7b`.
A convenient copy is `build/research/the-lab/demo-note-bootstrap.prg`. The small
bootstrap is not a standalone copy of the complete note or demo; the extras
disk must remain attached.

The BASIC stub contains `SYS2061`; machine entry is `$080D`. The loaded data ends
at `$11C8`. The successful note run attached `release/extras.d64` as drive 8
and injected the normalized PRG into RAM. VICE documents `-autostartprgmode 1` as
RAM injection; mode 2 copies the PRG to another D64 and would substitute the
wrong attached medium. This startup arrangement was subsequently executed
successfully in the session described below.
[VICE autostart documentation](https://vice-emu.sourceforge.io/vice_6.html)

The same directory contains `side1-bootstrap.prg`, `side2-bootstrap.prg` and
`side3-bootstrap.prg`. The side-two bootstrap was subsequently executed and its
custom payload extracted. Keep the original D64s authoritative;
the demo's custom-loaded payload is not represented by those small DOS files.

## Complete extras note recovered in PAL VICE

The original bootstrap ran with the original extras disk attached, using the
owned session in `build/research/the-lab/note-live-01/`. Execution stopped at
`$080D`, then advanced through the original reader. The second native capture
shows the rendered title page. There were no PC changes, payload substitutions,
or mocked disk reads in this session.

Two complete RAM captures, separated by 2,097,152 executed CPU instructions,
contain identical note bytes at `$6800..$B05E`. The original reader's dispatch
at `$0884` distinguishes `$FF` page breaks, `$FE` end, and `$FC` commands; its
`$08E9` handler advances four bytes for the command form used here. This gives
49 pages and 46 styling commands. The mixed-case screen encoding and inverse
attribute explain why a plain ASCII string scan missed most of the text.

`research/the-lab/read_note.py` exports readable pages, keeps unknown font
symbols explicit, records styling parameters, checks the original dispatch
bytes, and verifies stability against the earlier capture. The 18,527-byte
raw note region has SHA-256
`1e4d904360a9de4db7a3b5463f005661c0e1cb5d126c70dcbe77e970a026dd2f`.
Outputs are in `note-live-01/decoded/`; the RAM, transcript, launch options,
and native screenshots remain adjacent. This is runtime text recovery, not
a standalone decoder for the original compressed disk.

The included note provides these **author statements**, rather than measured
renderer behavior:

- **MMS, pages 11–13:** identifies his ambition to make vectors with more than
  three colors. **Shogoon, page 40:** associates MMS's part with characters
  commenting on the objects. That speech-balloon lead is now connected to the
  native file-21 open-panel script described below.
- **Brush, pages 19–21:** describes a timer-driven sprite carpet covering the
  borders, an optimized line routine, a Vectrex presentation, and a filled
  variant based on Bitbreaker's Codebase64 span-filling approach, extended with
  stencils. He explicitly distinguishes those vectors from animation playback.
- **Brush, pages 17–18 and 23–26:** separately discusses a differential animation
  compressor derived from TSCrunch, and a variable-size dictionary quantizer
  with dynamically selected character subsets. Those animation techniques
  must not be silently attributed to every vector part.

The primary text is distributed on the [release's extras disk](https://csdb.dk/getinternalfile.php/280582/the-lab.zip).
The referenced [span-filling article](https://codebase64.net/doku.php?id=base:filling_the_vectors)
is separately inspected in [the vector-source note](lines-and-vector-fill.md).
The author's wording establishes the span/stencil attribution. Display mode,
pattern data, prepared input and overlap behavior are separate measured results
from the matched code paths below. In particular, an author statement about a
computed vector part must not be extended to every adjacent transition or
prepared sprite sequence in the demo.

## What the initial screenshots established

The green checker/dot polygon image initially supplied a lead for spatial
shading with a small number of actual colors. A scaled video image cannot
distinguish hires bitmap, dynamic hires characters, mixed character modes, sprite layers, or a
raster-switched combination. Patterned interiors also do not establish whether
the geometry is computed live or replayed.

The additional exploded-cube screenshot was inspected directly. It shows several
separated, solid-color quadrilateral panels with black gaps and overlapping
projections. It is consistent with an opened cube or independently displaced
panels. One frame cannot prove the original vertex connectivity, back-face
policy, panel thickness, or depth algorithm. In particular, it does not prove
that an apparent inward surface is the reverse of the same polygon rather than
a separate polygon. The original screenshot is preserved in ignored output as
`exploded-cube-user.png`, SHA-256
`43e2f693fa887084822f9179732d50b9d7ab5ea22bcae614fd1b2f2e910f5e1e`.

The subsequent investigation answered the display and shading questions through
register reads, code execution and byte comparisons. Recovering original mesh
connectivity, winding and general depth handling requires separate evidence
from matching the visible scene.

## Two matched rendering paths

Both paths were reached through the original side-two bootstrap and attached
disk. The native sessions used breakpoints and restorable snapshots; no PC or
payload substitution selected a part. The custom disk extraction also ran all
25 files through the original resident depacker. Detailed provenance is in
[the side-two binary audit](the-lab-binary.md).

| Matched path | Measured display and input | Rendering mechanism and strongest comparison |
| --- | --- | --- |
| Green patterned sprite stage, custom file 15 | Eight one-bit sprites, X/Y expanded, normal display disabled. Seven vertical bands display 192×147 logical samples as 384×294 physical pixels; the allocation has 168 logical rows. | Masked partial-byte span OR and full interior stores, sixteen density materials. All 7,056 displayed bytes of native front pose 72/back pose 73 match independent decoding. [Sprite audit](the-lab-sprite-vectors.md). |
| MMS speech-balloon stage, engine file 20 plus prepared scripts/assets 21–23 | Multicolor bitmap, switching bitmap/screen pairs `$E000/$DC00` and `$4000/$6000`. Prepared projected edges, slopes and attribute commands. | Generated vertical XOR-prefix fill plus per-cell color work. The exact “AND NOW?” open-panel script is native-matched; its pending pose has 4,608 exact marker bytes and 3,600 exact bitmap stores. [MMS audit](the-lab-mms.md). |

The green stage's native `$D015/$D017/$D01D=$FF` and `$D01C=$00` establish enabled,
doubly expanded one-bit sprites. Pointer-table and raster-handler checks prove
that its two 2 KB slices are consecutive vertical sections, not alternating
scanline fields. A captured large checker triangle confirms the dither style;
it is not claimed to be the same pose as the supplied video image. Material 8
contains the actual `$AA/$55` checker, alongside sparse and denser materials.

The inspected 164-pose sprite sequence consumes 118 prepared triangle packets
and 46 compressed scanline-run packets. The C64 rasterizes those primitives;
the observed consumer does not establish a live 3D transform for that exact
sequence. Original execution of all 46 run packets agrees with independent
span/mask/address calculations. This finding is scoped to the inspected input
and does not characterize every vector effect described in the author note.

The MMS bitmap mode is established by native I/O reads and the original bank
switch code. Its per-cell screen nibbles and Color RAM explain the screen-wide
color variety; it still has ordinary local multicolor-bitmap palette limits.
The file-21 script includes the open-sesame prompt and literal “AND NOW?”. Its
13,053 payload bytes match at the native entry. At the completed open-cube
checkpoint, displayed bitmap `$4000` is pose 8 while `$E000` contains completed
pending pose 9. Keeping those roles separate avoids treating the next input
pointer as the already-displayed image.

Commodore's [6567 VIC-II documentation](https://www.zimmers.net/anonftp/pub/cbm/documents/chipdata/6567_vicII_preliminary.pdf)
defines these display, expansion and memory-pointer rules. Raw `$D000–$DFFF`
bank RAM is not equivalent to I/O register or Color RAM readback.

The evidence and reproducible checks remain separate:

- `side2-targeted-02/` holds native sprite/open-cube PNGs, RAM, restorable VSFs,
  launch metadata, monitor log and full file-21 entry comparison.
- `span-plane-analysis/plane.json` records both sprite buffers' visible address
  mapping, prepared inputs, original run-code execution and native pose checks.
- `mms-open-cube-analysis/proof.json` records open-cube marker/prefix equality,
  original-code attribute replay, buffer ages and the palette-priority proof.

All paths above are beneath ignored `build/research/the-lab/`. The original
analysis scripts live under `research/the-lab/`; the detailed notes specify
their input hashes and reproduction commands.

## What the matched overlap actually does

The open-panel scene aliases bitmap codes `01` and `10` to the same color in
each touched character cell. Layer A contributes delta 1; B contributes delta 3:

| Coverage | Resulting code | Displayed choice |
| --- | --- | --- |
| Outside | `00` | Black. |
| A only | `01` | A color. |
| B only | `11` | B color. |
| Both | `10` | A color, aliased to `01`. |

This gives bounded **opaque A-over-B priority** even though XOR itself remains
commutative. The pending native pose contains 3,678 overlapping logical samples;
all 294 touched screen cells have equal high/low color nibbles. The proof names
priority classes A/B, not globally near/far surfaces: the supplied stream has
no 3D depth or panel identity from which to prove that stronger claim. Correct
opaque interpretation requires at most one accepted region per class at a
sample and a compatible local palette.

The marker and bitmap comparisons have an independent arithmetic oracle.
Attribute replay additionally agrees with all 576 pending Color RAM-shadow
bytes and 484 back-screen stores, but is not a complete independent per-panel
color/depth oracle or native post-swap Color RAM comparison. The screenshot
and these checks establish the matched mechanism within that scope.

## Implications for our renderer

Our existing convex-solid shortcut discards back-facing triangles and combines
the visible faces' edge-transition colors into one prefix fill. It works because
the retained faces partition the visible solid. An exploded or opened cube no
longer has that property: a panel's reverse may be visible, and panels can overlap
in projection while occupying different depths.

A two-sided material can render both windings, optionally choosing different
front/back colors or reversing the lighting normal. Merely disabling culling
does not solve occlusion. XOR is commutative; combining two overlapping opaque
panels produces an XOR of their selectors. With our current distinct-color
palette, that does not let a nearer panel hide a farther one. The matched MMS
scene uses a different contract: two selectors share one priority-layer color,
so an XOR overlap decodes to that layer's color. This works with at most one
covering region from each class and a compatible per-cell palette. See the
[native priority proof](the-lab-mms.md) and [panel design note](open-panels.md).

A candidate opaque path is far-to-near polygon drawing with byte coverage masks.
For each covered byte, replace both the lit and unlit pattern samples:

```text
destination = (destination AND NOT coverage) OR (pattern AND coverage)
```

An OR-only stipple fill would leave the farther polygon visible through a near
panel's zero pattern bits. That can be a deliberate transparency effect, but it
does not implement opaque shading.

The palette-priority alternative can also use character-mode outside code `11`,
Color RAM black, one global B tone and two aliased global A selectors. It keeps
one prefix pass, but does not supply the bitmap's varying per-panel palette.
Opaque black pattern samples in A need more than omitting a marker, which would
expose B. The [panel design](open-panels.md), [dither assessment](interlaced-dither.md)
and [cross-production technique map](technique-map.md) spell out those limits.

Sorting by a face's center depth remains a heuristic for general separated
panels. Interpenetration, cyclic overlap and near-plane crossings can require
splitting or explicit visibility resolution. No unrestricted runtime depth sort
or arbitrary transparent-polygon compositor is established by the matched scene.

## Remaining evidence gaps

The display modes, pattern tables, prepared-input formats and bounded palette
priority above are established. Further work concerns the tools that generated
the projected geometry and class assignments, their relation to original 3D
connectivity/winding, and whether the same constraints hold in other scenes.

The sprite checks cover all compressed-run packets and two complete native
display buffers, not every triangle case or every dirty-clear/stencil lifecycle.
The MMS checks distinguish independent bitmap arithmetic from original-code
attribute replay; a complete color/depth oracle and native post-swap attribute
comparison would be additional evidence. Neither investigation supplies a
whole-stage cycle benchmark or real-hardware coverage of every CIA revision.
Those measurements remain necessary before transferring a mechanism and
promising a cadence for our renderer.
