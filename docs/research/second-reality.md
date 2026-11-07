# Second Reality / Smash Designs (1997): original disks, bootstrap and notes

Added at the user's request on 7 November 2026. The supplied capture title is:

> Smash Designs - Second Reality - C64 Demo - C64 Ultimate64 EliteII + SIDKick2350 + PDsid [8580]

The title is retained as capture context. Its hardware setup is not evidence
of the original demo's minimum requirements or the timing of its algorithms.
No exact capture URL was supplied, so this entry does not assign one from a
similar video title.

## Original production identity

[The original release entry](https://csdb.dk/release/?id=908) identifies
**Second Reality**, also called **2nd Reality**, released **29 December 1997**
by **Smash Designs**, first in **The Party 1997 C64 demo competition**. Credits
name AEG and Dcp for code, Dcp for the loader, kb for music, and AEG/Idefix for
graphics. The [production catalogue](https://demozoo.org/productions/19822/)
additionally credits The Obsessed Maniacs alongside Smash Designs.

The [Smash Designs C64 releases page](http://www.smash-designs.de/c64demo.html)
also lists Second Reality as the first-place C64 demo at The Party 97 and
links `releases/c64/2nd_reality.zip`. Its archived page has SHA-256
`c7a4204fe44eefa36b3759842249b5b2d3cc79947857916e10377860735ab4f3`.

## Archived packages and exact disk identity

The existing acquisition on 7 November 2026 preserved two valid ZIP packages:

| Route | ZIP bytes | SHA-256 |
|---|---:|---|
| [CSDb internal file 71054](https://csdb.dk/getinternalfile.php/71054/2ndreality.zip) | 224,787 | `a48083c1bb24ff5d4b7ce5d9b3c57c7178274ab1a627ed17ec90c4b684d273d0` |
| [Author-site HTTP download](http://www.smash-designs.de/releases/c64/2nd_reality.zip), redirected to [fzool.org's Smash archive](https://www.fzool.org/smash/c64/2nd_reality.zip) | 224,823 | `6acc4b1570e3534d17ed263602d6ccfd113b7f3615f5a964384dbd64dd8ebd77` |

The outer ZIPs differ by 36 bytes and use different member names, but contain
**the same two D64 payloads, byte for byte**. Both disks are 174,848 bytes:
35 tracks, 683 sectors, without an error-byte trailer.

| Side | CSDb member | Author-site member | D64 SHA-256 |
|---|---|---|---|
| 1 | `2ND1.D64` | `2ndReality_S1.D64` | `05aa03c00be26cab0618f8802477d0bc7226af029c003a253a34bd32c630acf2` |
| 2 | `2ND2.D64` | `2neReality_S2.D64` | `0f61c5fd673d2c0cd63d43feeca4bf9e49686c8f06df0dd69a2ff2415f5c9c17` |

The author package's `2neReality_S2.D64` spelling is retained exactly. These
comparisons establish package equivalence for the two archived routes; they
do not establish a separate party/final/fixed version history.

The direct author **HTTPS** request failed hostname certificate validation.
The author **HTTP** route succeeded through the recorded HTTPS redirect;
certificate verification was not disabled. The raw Demozoo request returned
HTTP 403 and its body is preserved as a failed acquisition. The receipt
separately records the successful web-tool observation used for catalogue
identity and author-link discovery, rather than parsing the 403 body as the
production page. The author release page independently confirms the download
link.

## Notes, directory date and present limits

Each ZIP contains only the two disks. There is **no outer README, NFO, text
note or source file** in either package. This says nothing yet about notes or
source embedded within disk contents. At the initial acquisition stage only
standard DOS directories had been read; the follow-ups below now recover
the original boot image and its embedded note.

Side 1's directory artwork contains **`28.12.97`**, while the catalogues list
**29 December 1997**. Both observations are retained. The directory date does
not silently replace the catalogued release date or prove a distinct release
revision.

The [acquisition script](../../research/second-reality/acquire.py) and
[existing receipt](../../build/research/second-reality/acquisition.json) pin
the routes, request outcomes, archive/member hashes, ZIP integrity and raw
directory-name bytes. Receipt SHA-256:
`df052184703650f3622fb977992cf28d457c42f0171a50a11fa4cf2492f06a8f`.
The archived ZIP and D64 hashes were rechecked against that receipt for this
documentation update; no new acquisition, CPU, depacker or emulator run was
performed.

## Original files and independently recovered boot image

The [complete disk map](second-reality-disk-map.md) follows **71 valid PRG
chains**, 27 on side 1 and 44 on side 2. They share no PRG sectors or starting
points. Every displayed block count disagrees with the actual chain length.
The first boot is **42,890 bytes across 169 sectors**, despite a one-block
directory label. Two separate tiny chains have identical contents; the
remaining files are distinct.

The [bootstrap investigation](second-reality-binary.md) identifies
`SYS2304`, the copied wrapper, the drive-uploader boundary, a 161-page
relocation, and the original `$D7` run-length decoder. File-only execution
stops when wrapper/pager copies reach unknown padding. A separately bounded
decoder proof consumes only established code and packed input, executing
**824,550 original instructions**. All **60,152 output bytes at
`$07E8..$F2DF` match the native `$9400` handoff**, without invented padding
or excluded output bytes.

The [closed native boot check](second-reality-native.md) validates 19 full
physical-RAM/snapshot pairs, or **1,245,184 byte comparisons**, including
the original loaded boot and independent decompression output. Later menu
operation uses 61 explicitly recorded scan-result inputs; that is not a
physical-keyboard validation. Two asynchronous timeout captures remain
rejected observations, rather than successful loader handoffs.

## The DOS interface and editor run on the C64

The original production contains a mock DOS environment, a PC-style sound
configuration menu, and a small editor/viewer. These screens are part of
the C64 presentation. The setup screen explicitly describes its 6510
target; selecting SID through the original menu reaches the custom disk
loader. The later capture continues from a saved original C64 snapshot,
with that restore and subsequent input interventions recorded separately
from the cold-boot proof.

The included note is opened from the mock DOS prompt with:

```text
cd demos
cd 2ndreal
read info1sds
```

`read info1sds` at the initial root prompt fails because the file belongs
to the simulated `C:\DEMOS\2NDREAL` directory. That failed trial is preserved;
it is not evidence of a parser bug. The original viewer was subsequently
reached at `$9100` and its first page captured. [Original C64 note viewer](../../build/research/second-reality/native-01/note-page-0.png)

The [recovered INFO1SDS note](second-reality-disk-map.md) occupies
`$B000..$B7FF`, 64 stored rows of 32 characters. All 2,048 note bytes and
the actual alphabet glyphs match between independent reconstruction and
native RAM. AEG describes the high-resolution conversion aim, gives design
credit to Future Crew/PC, and calls the DOS emulation imperfect. Those
statements do not establish per-effect geometry, preparation or update rates.

The [external source survey](second-reality-sources.md) found no 1997
per-effect author algorithm account in its inspected routes. It preserves
author recollections, a contemporary review lead, failed acquisitions and
AEG's concrete explanation of the separate 2003 **The Impossible Thing**.
That later glyph-based rotate/zoom mechanism is a useful new lead, without
being assigned to Second Reality's renderer.

## First loaded parts and the CA dot field

The [part map](second-reality-parts.md) now binds six original DOS files to
seven exact native payload comparisons, **41,152 compared bytes**. `AA`
provides a small launcher; `BC` initializes the title display and preloads
`BA`, `BB`, `BD` and `CA`. Their original load headers are storage contracts,
not execution addresses. In particular, CA is staged at `$6000`, then its
code and tables are relocated before the guarded `$C000` entry is reached.
The rejected attempt to execute-break at `$6000` remains in the record.

The [closed continuation check](second-reality-native-parts.md) validates
20 additional full-RAM/snapshot pairs and the file placements. It records
three explicit snapshot branches and seven scan-result inputs for SID
selection. Its ten PNGs include the actual title and a waving dot grid;
they are machine-output observations rather than complete-frame pixel
oracles.

The [CA effect analysis](second-reality-ca.md) identifies a substantial
code/memory trade. This stage uses **multicolor character mode**, with a
screen at `$E000` and raster-selected charsets at `$E800/$F000/$F800`.
During preparation, the C64 generates **32 plotting
routines of 1,108 bytes**, totaling **35,456 bytes at `$2000..$AA7F`**.
All generated bytes match the independent construction at the first
pre-draw checkpoint. The runtime draws 31 instances with 32 points each:
**992 cached-address clear stores and 992 point plots per iteration**.
Old plot addresses are retained in self-modified clear operands. This
kernel draws individual dots; it does not draw or fill polygon spans.
Plots use whole-byte stores, so shared byte positions and draw order matter;
the kernel is not a general OR/XOR point compositor.

Stored coordinate profiles and expanded motion data feed live position
updates and plotting. One original draw/update interval takes **62,094
nominal CPU cycles** in the RAM-only model, versus **72,230 observed native
clocks**. The latter includes display/interrupt effects. Generated code,
cached addresses, the full 8,192-byte `$E000..$FFFF` plane and the selected
position/style/counter outputs match exactly. The full-RAM comparison
retains 36 other differences rather than masking them or claiming a full
machine transition match.

This establishes how this particular dot field combines prepared data,
generated code and runtime work. It does not yet identify the later
polygon-vector, texture or raytrace implementations, nor establish an
arbitrary live 3D engine or a coherent-frame presentation rate.

The [coverage follow-up](second-reality-ca-coverage.md) makes its destructive
store rule concrete. Of the 992 plot requests in the checked interval,
465 reach the colored atlas and request 459 distinct pixel lanes. Only
397 remain in the endpoint atlas: later cached clears and whole-byte point
stores remove 62 requested samples. The ordered stores reproduce the
original display-memory endpoint exactly; replacing point assignment with
OR or XOR changes it. This is recorded behavior, not a claim of a demo bug
or a general-purpose plotter.

## The following bitmap effect combines two one-bit layers

The [next transition map](second-reality-da.md) binds original files
`DA`, `DB`, `EA` and `EB` to their loader returns and identifies **DB's
`$C000` entry**. It separates all 399 bytes not defined by the EA/EB file
bodies, including the later loader-page backup, from actual payload data.
[The native continuation proof](second-reality-native-next.md) checks all
11 full-RAM/snapshot pairs, one explicit restore and zero synthetic inputs.

The [DB renderer](second-reality-db.md) produces the rippling bitmap pattern
by shifting **two one-bit versions of a prepared pattern**. DA's 2 KiB
source expands into two 16 KiB layouts. One uses only the low bit of each
multicolor pair; the other uses only the high bit. Runtime OR combines them
into selectors `00/01/10/11`, giving separate palette choices for background,
either layer and overlap. No polygon geometry is needed for this effect.

Its unrolled kernel calculates 96 rows by 32 byte positions and writes each
result to two adjacent bitmap rows: **6,144 stores into a 256×192 window**.
The independent indexed oracle reproduces every ordered store. The prepared
32,768 bytes and 1,024 lookup bytes also match the original native state.

One original logical update takes **70,208 nominal CPU cycles**, compared
with **81,640 elapsed native clocks** for the corresponding interval. Code,
the entire 8 KiB bitmap region, source pointers, phase state and CPU registers
match; 33 other RAM differences remain explicitly recorded. These are
logical-update and stored-memory checks, not coherent-frame timing or an
independent VIC pixel oracle.

## EC transforms prepared texture planes into character buffers

The [EA/EB bridge and EC analysis](second-reality-ea.md) follows DB's natural
exit through restored staging pages, a real EC loader request, and EC's
guarded `$C000` entry. Full-page restores retain the short files' original
non-file tails and saved loader bytes. Preparation uses 111 overlapping
runs and a literal row to build two complementary source-bit layouts totaling
**16 KiB**, and generates sibling character-drawing programs at `$8000/$9000`.

Runtime phase/scale setup patches their source bases and coordinate tables.
Each draw samples and ORs two packed bytes into **2,976 output positions**:
31 columns by 96 populated rows. A column-ordered, three-charset display
maps this to a **248×192 physical-pixel window**, with alternating blank
glyph rows. Two VIC banks hold the display sets; IRQ work changes charset,
palette and vertical-scroll state. This is texture-coordinate sampling,
not a polygon boundary/fill stage.

An independent indexed-store model matches the complete **6,144-byte
character-buffer endpoint** and final generated operands. Strict original
CPU replay stops before a suppressed-column instruction reads mapped
KERNAL ROM at `$99E2`; no ROM result is invented and no continuous full-half
CPU proof is claimed. The model consumes the original prefix's prepared
coordinates, so independent motion mathematics and complete VIC/interlace
composition remain open. The paired-loop observations are code-boundary
intervals, not coherent frames or FPS measurements.

The [closed native-04 lifecycle check](second-reality-native-ea.md) verifies
all **15 RAM/snapshot pairs**, totaling 983,040 RAM bytes, complete restore
identity and five PNG contexts. Its transcript records one snapshot restore
and no new synthetic inputs or data/code/PC writes.

## Questions to investigate

- Identify individual C64 effects, their original part boundaries and any
  included author explanations.
- Recover the split between live geometry, lookup tables, prepared poses and
  animation data, especially in the vector/3D sections.
- Map pixel storage, line and span kernels, filling, visibility, buffer history
  and cleanup. Measure complete costs where native execution supports it.
- Inspect loader/drive scheduling and music synchronization separately from
  graphics timing.
- Check original PAL/NTSC and SID handling from release instructions and code.
  Record the user's modern capture configuration separately.

Keep the C64 implementation distinct from its PC inspiration. Source or
technical explanations for Future Crew's PC production cannot establish how
Smash Designs implemented a corresponding effect on the C64.

Disk identity, the original boot/decompression route, embedded note, first
file sequences, dot-field kernel, two-layer bitmap mechanism and EC's
character texture-sampling path are established within their declared checks.
Later rendering paths, complete timing and hardware requirements
remain open. A static directory label or an author credit alone cannot
resolve those questions.
See [the research map](README.md) and [technique comparison](technique-map.md)
for already inspected productions.
