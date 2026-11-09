# Aloft part08: primary VIC reading and the D011 boundary

Research date: 9 November 2026. This is a bounded reading aid for the original
part08 cell study. **It does not identify the effect as FLD, linecrunch, ECM,
bitmap or the separately named moving three-layer pattern.** Its accepted
result is source retention, attribution, exact passage/code anchors and a small
register-value transformation. No emulator, downloaded program, CPU interpreter
or new native capture was run.

The existing [original-to-native association](aloft-decoded-parts-20261109.md)
matches the complete selected `$F000..$F83F` window from source generation 31.
The [part note](aloft-parts-20261109.md) separately describes the call generator
and observed cells. This reading checks original template bytes at `$F7EC`
(`INC $D011`) and `$F80F` (`LDA #$18 / STA $D011`) against that independently
decoded generation. It does not substitute a snapshot's generated code for
the generator's source, or prove which template executes at a given time.

## Primary material actually read

[Christian Bauer's author-hosted VIC article](https://www.cebix.net/VIC-Article.txt)
is retained at its current **2024-09-29** revision, rather than labelled with
an older revision date found in search summaries. It is an original research
reference informed by hardware tests, with an explicitly descriptive internal
model; it is not a Commodore silicon specification.

The relevant distinction in its §§3.5, 3.7.2 and 3.14.2–3.14.4 is precise:
FLD delays allowed badlines; its early-linecrunch example cancels a begun
badline condition before cycle 14, leaving RC at 7 and allowing VCBASE to
advance. Their common use of `$D011` does not make them interchangeable.
Its mode tables also separate ECM text from bitmap modes; ECM with BMM set
belongs to the listed invalid modes. Those rules require the actual mode
and sequencer state, not an image-based guess.

Three signed, contemporary articles supply practical examples:

| Retained original authored text | Specific useful content |
| --- | --- |
| [Pasi Ojala, “Opening the borders”, C=Hacking 6](https://csbruce.com/cbm/hacking/hacking06.txt), written 20 July 1992, issue dated 5 September 1993 | The “Scrolling the screen” section explains delaying the first badline and spacing later character rows. It also distinguishes border opening from ordinary character display. |
| [Marek Klampar, “FLD - Scrolling the screen”, C=Hacking 7](https://csbruce.com/cbm/hacking/hacking07.txt), February 1994 | Credits Ojala's earlier section, then provides a demonstration. Its IRQ explicitly derives a three-bit scroll value from `$D012`, combines control bits, and writes `$D011`. This is a concrete comparison for a delay mechanism, not a match to Aloft. |
| [Pasi Ojala, “BFLI - New graphics modes 2”, C=Hacking 10](https://csbruce.com/cbm/hacking/hacking10.txt), 30 June 1995 | Describes and implements scrolling a tall FLI image by combining linecrunch with badline delay. It is a real example of composing techniques instead of copying the whole image. Its historical explanatory shorthand is not adopted as a complete modern VIC model. |

These magazine bytes come from original contributor Craig Bruce's archive.
They remain **mirrored signed primary content**: this pass does not establish
an original-distribution hash or byte identity with every other mirror.
[Ojala's own project page](https://a1bert.kapsi.fi/Dev/) links the official
Fridge archive, and Bruce's index identifies the same official site. The
official endpoint failed certificate validation with and without `www`.
Those failures are retained; verification was not disabled. Codebase64 copies
were retained during discovery but do not supply additional technical authority.

[Linus Åkesson's Raster paper](https://www.linusakesson.net/programming/rasterpaper/index.php)
is an author-hosted scheduling aid. The detailed late-badline/repeat-last
explanation below it is by **anonymous commenters**, not the page author.
It is retained as an excluded lead and is not used to identify Aloft. Secondary
technique summaries and AI-like knowledge-base search hits supply no claims
in this note. The earlier broad Aloft creator searches were not repeated.

## What the small value check proves

The pinned official [VICE 3.10 release source](https://sourceforge.net/projects/vice-emu/files/releases/vice-3.10.tar.gz/)
provides a narrow implementation contract. In `viciisc/vicii-mem.c` lines
501–512, reading `$D011` combines stored bits 0–6 with the **current raster
MSB** in bit 7. In `6510core.c` lines 1175–1188, the INC macro reads a byte,
performs the old-value dummy write, increments modulo 256, then writes the
result; absolute opcode `$EE` selects that macro at lines 3408–3410.
The `$D011` store function retains the byte and updates raster comparison.
These are implementation-source observations, not a newly measured chip trace.

The new [pure reader](../../research/aloft-cells-20261109/primary_reading.py)
exports `d011_read(stored_register, raster_line)` and
`d011_inc_read(actual_read_byte)`. The latter's input is the **actual software
read value**, never an assumed old register byte. The accepted table exhausts
all 256 read bytes and checks 512 stored-byte/raster-MSB combinations:

```text
read  = (stored & $7F) | ((raster & $100) >> 1)
dummy = read
final = (read + 1) & $FF
```

For example, read values `$18..$1E` increment through `$19..$1F`; `$1F`
increments to `$20`. Carry therefore crosses from the scroll bits into other
control bits. This is why “increment YSCROLL” is an incomplete description
unless the caller establishes its range and reset path. The literal `$18`
row-end store is a separate value operation. The API does not predict when
either write occurs, whether the VIC performs a badline, or what pixels result.
It does not consume or settle the cell's separate indirect comparison reads.

## What still binds a mechanism to this program

The cell/generator lane must first establish the actual generated variants,
patches, paths and read values. A timing/scanout lane then needs ordered CPU
read/dummy/final accesses, raster phase and stalls, DEN/badline and
RC/VC/VCBASE/display state, and the relevant mode/bank/memory selection at each
fetch. Matrix/color-line contents, glyph or bitmap data and border/fetch
latches must lead to an independently captured, fully committed viewport.
A source-level resemblance to one of the examples does not replace these
dependencies. This pass supplies reference conditions and byte semantics only.

## Retained result and continuation

The [accepted receipt](../../build/research/aloft-cells-20261109/primary-analysis/accepted-01/primary-reading-proof.json)
pins **14 retrieval attempts: 11 HTTP-200 bodies / 1,658,685 bytes and three
certificate failures without HTTP responses**. Each successful response keeps
its exact body, URL, final URL, timestamp, status and headers. The passage
atlas records line ranges and digests rather than copying articles into the
derived output. Two official VICE members are checked against the already
pinned release archive. Historical source bytes and their known/write masks
remain dependencies of the separate original decoder proof.

The first candidate rejected a wrongly spelled literal section boundary;
its source and failure diagnostic remain in `candidate-01`. An initial local
HTML inspection also rejected an undeclared UTF-8 assumption; the retained
legacy bodies are subsequently decoded as Latin-1 where declared. Neither
failure was turned into a technical finding. Candidate 02 and fresh accepted
outputs remain alongside those records.

Offline reproduction from the repository root:

```sh
rtk proxy python3 -B research/aloft-cells-20261109/primary_reading.py \
  --output build/research/aloft-cells-20261109/primary-analysis/new-replay
```

The [self replay](../../build/research/aloft-cells-20261109/primary-analysis/self-replay-check.json)
matches all **four outputs / 50,975 bytes** exactly without network access.
The independent [root review and replay](../../build/research/aloft-cells-20261109/primary-analysis/root-replay-check.json)
also matches those four outputs exactly after reading the full producer and
note. It additionally compares both retained VICE source files byte for byte
with their original members in the pinned release archive; both match.
Root report: 3,464 bytes,
`38e6b3705f003a198f37a4799b351308b8afc7ec0614e31e3941e02ab3142bcd`.
Current producer: 14,200 bytes,
`4c8b3e1ae3968fff3bc90af9527fda0a6489c6853ba68f32bf17f4a1c4e74dda`.
Accepted receipt: 4,758 bytes,
`4fd7cedb1ce4325a6adc0c406406f4a2f6a2cc65ccb7c8ef735d21c02344ed04`.
The concrete next comparison is the original-generated cell path and its
actual `$D011` accesses against these conditions; no screenshot-derived
mechanism label is part of this result.
