# Ghostbyte shine-through: the useful constraint behind apparent hires borders

Trident's [January 2023 article](https://github.com/trident64/c64/blob/80d1027742815e55cda13a80cb4826744dd75c83/unexpanded-border-scroll/README.md)
explains the lower-border scroller in **Orbit Untold**, Fairlight, 2023. Its
expanded multicolor sprites select which parts of a repeating idle-graphics
pattern become visible. The resulting detail can be one pixel wide even though
an expanded multicolor sprite symbol spans four pixels. It remains a constrained
composition, rather than arbitrary hires sprite data.

This pass, 7 November 2026, pins the article and teaching sources, assembles both
unchanged, and executes their original initialization and border-polling code in
a bounded CPU model. **The published teaching programs do not implement the
shine-through scroller.** This is not a reproduction or identification of The
Ghost (2024) or Nine (2025).

## What the source actually contains

The inspected tree is `trident64/c64` commit
`80d1027742815e55cda13a80cb4826744dd75c83` (repository commit dated 11 February
2025). Its `unexpanded-border-scroll/` directory contains the article, PNG
illustrations and two small KickAssembler sources. It contains no `.prg` or
complete scroller implementation. The article credits Trident for Orbit
Untold's code and scroll font, Danko for music and tNG for logo/font.

| Pinned input | Raw bytes | SHA-256 |
|---|---:|---|
| `README.md` | 10,658 | `e431b957e7dad60a37242291d5a0d6635f9f1026d57d8e3f210f799dca313dbc` |
| `ghostbyte.s` | 293 | `db28c561af70b1c83b42b9eabb5ecf8aef561dded5dbc418fe684ea6e57b1c62` |
| `sprite.s` | 853 | `64b26f7b2b9a284bda6d9b233817460cb39eb4b1a03476b042c06d4cfbf3d801` |

The acquisition receipt also checks each Git blob SHA-1 against the pinned tree,
retaining the original CRLF bytes. Selected author PNGs are archived and hashed;
their pixels are not used as a release-binary oracle. Third-party bytes stay in
ignored `build/research/ghostbyte/`.

## Masking and shine-through use opposite layer arrangements

In the article's masking example, the black ghostbyte is in front of the sprite.
It removes selected pixels from an expanded letter. A suitable font and a
periodic mask can disguise expansion, but the same mask also crosses the rest
of the image.

Shine-through instead places the sprite above idle graphics and makes selected
multicolor symbols transparent (`00`). Black idle pixels and the background
color become visible through those holes. Other symbols draw solid black or
the same color as the background, joining the exposed pattern into a coherent
letter. The ghostbyte normally changes between raster lines; its horizontal
eight-pixel repetition remains shared across the row. The article describes
seven expanded sprites carrying the moving scroller.

The hardware palette routes `01` through `$D025`, `10` through the individual
sprite-color register and `11` through `$D026`; `$D01C` enables sprite multicolor
and `$D01D` horizontal expansion. The mapping is documented on
[Commodore's Programmer's Reference Guide, page 136](https://www.devili.iki.fi/Computers/Commodore/C64/Programmers_Reference/Chapter_3/page_136.html).
The teaching sources do not configure this palette, multicolor or foreground
priority. Those are requirements derived from the article's construction, not
register values recovered from its released scroller.

## An independent, exhaustive constraint check

`research/ghostbyte/validate_examples.py` also evaluates an ideal two-color
compositor. Fix sprite/ghost alignment, represent black as `1`, and let each
four-pixel sprite symbol choose transparency, solid black or solid background.
For a ghostbyte split into high/low nibbles `h,l`, the available eight-pixel
results are exactly:

```text
high quartet in {0000, 1111, h}
low  quartet in {0000, 1111, l}
```

For example, a fixed `$81` ghostbyte can produce only
`00 01 0F 80 81 8F F0 F1 FF` under that palette. It cannot produce `$42` at the
same alignment. The program checks all 256 ghostbytes and all 16 pairs of
hardware symbols: four ghostbytes have four distinct outcomes, 56 have six,
and 196 have nine. A fourth color could add a color choice but does not provide
independent fine-pixel control inside a solid symbol.

These are our exhaustive ideal-model results. They demonstrate why tailored
glyphs and alignment are necessary; they do not decode Trident's font or
measure VIC output. Ghostbytes from the ordinary upper/lower-border idle fetch
also do not provide this pattern throughout the side borders. Extending the
method to other display regions requires additional mechanisms.

## Original teaching-program CPU check

Both unmodified sources assemble with the already installed KickAssembler
5.25. The generated BASIC stubs name entry `$080E`.

| Derived artifact | Bytes including load word | SHA-256 |
|---|---:|---|
| `ghostbyte.prg` | 55 | `06f6fae999418aeb1b7f79b7d6acb6ffa7e173ee150bb6893551db12d50b96a0` |
| `sprite.prg` | 321 | `c84f340c8077706e0c282fb36156945b1725bf42eda4be962fac88064467ca1f` |

These are newly assembled teaching programs, not acquired release binaries.

Both execute the following control flow:

| Trigger/action | Original register or memory operation |
|---|---|
| Initialization | Write `$7F` to `$DC0D` and `$DD0D` |
| `ghostbyte.s` initialization | Write `$01` to `$3FFF` |
| `sprite.s` initialization | Write `$00` to `$3FFF`; enable and horizontally expand all eight sprites through `$D015/$D01D` |
| Poll `$D012` until its low byte is `$F8` | Write `$13` to `$D011`, clearing the 25-row selection bit |
| Poll `$D012` until its low byte is `$02` | Write `$1B` to `$D011`, restoring that bit; repeat |

The second poll does not test raster bit 8: following line 248, low byte `$02`
can occur at **line 258** before the next frame's line 2. Calling this a
frame-wrap wait would be wrong. The code also does not set `$DD00`, `$D018`,
`$D016` or `$D01C`; meaningful screen output relies on the surrounding machine
state, including the VIC bank and conventional screen/pointer setup.

The sprite example installs eight `$24` pointers at `$07F8..$07FF`, referring to
its 64-byte block at `$0900` in bank 0. All Y registers become 255. Combining its
low X bytes with `$D010=$C1` gives nine-bit X values
`496,40,88,136,184,232,280,328`; sprite 0 is explicitly moved eight pixels left
after the generated initialization. Only sprite 5's color is explicitly changed
to 8. These are register facts, not a claim about captured visible coverage.

The CPU check uses the existing **py65 1.2.0** environment. Its synthetic
`$D012` sequence is `F7,F8,01,02` twice, forcing one failed comparison before
each successful comparison. The unchanged programs complete two polling loops
in 35 and 92 CPU instructions respectively; both write `$D011` as
`13,1B,13,1B`. There is no VIC, CIA, DMA, interrupt delivery, CPU-port banking or
pixel pipeline in this fixture. The numbers are instruction counts in that
explicit fixture, with no frame-rate, border-visibility or cycle-safety claim.

## Invalid modes and the connection to Nine

Neither teaching program selects an invalid mode: their `$D011` values are
`$13/$1B`, with ECM and bitmap mode clear. Importing Nine's `$70` schedule into
these programs would conflate different implementations.

Åkesson's [Nine explanation](https://www.linusakesson.net/scene/nine/explanation.php)
explicitly links Trident's article and identifies ghostbyte shine-through as
related work. For Nine, he explains that mode `$70` has the needed ECM-like
ghostbyte behavior and hides a left-edge gap. His raster variants account for
horizontal-scroll alignment and VIC revision differences. This is author
context; the Trident examples are not byte-matched to Nine. Existing local
Nine binary work is documented separately in [nine-binary.md](nine-binary.md).

The same author article links [The Ghost release 239394](https://csdb.dk/release/?id=239394),
attributing it to Fairlight and Genesis Project in 2024. The CSDb page could not
be fetched by the web reader during this pass. No release bytes, internal
part identity or native output were established for it. It remains a concrete
next release to acquire and inspect, not evidence that these sources belong
to it.

## Reproduction and receipts

From the repository root, with the existing assembler and CPU environment:

```sh
rtk proxy python3 research/ghostbyte/acquire.py
rtk proxy build/research/tower-power/cpu-venv/bin/python research/ghostbyte/validate_examples.py
```

Acquisition uses only the Python standard library. Validation records the
assembler command, JAR hash, input/output hashes, original write/read traces,
model conditions and compositor counts in `build/research/ghostbyte/proof.json`.
The proof receipt for this run is SHA-256
`710f3b8de6c471310fcaafce46f3f7756c7766650686efbb404a84efd9d72a2e`.
No native emulator, application renderer or release loader was launched.
