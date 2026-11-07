# Colors / Lethargy (2026): original release and first display

Added to the research list at the user's request on 7 November 2026.
[The original release entry](https://csdb.dk/release/?id=262141) identifies
**Colors by Lethargy**, released **6 June 2026**, third in the **X'2026 C64 demo
competition**. Coding credits name dev0, EGO, Schedar and Strepto; music is by
Vincenzo. Those are release metadata, not an inspected rendering algorithm.

## Original artifacts and version identity

The release links
[Colors [Lethargy].zip](https://csdb.dk/getinternalfile.php/280610/Colors%20%5BLethargy%5D.zip).
Vincenzo's 7 June release comment says the disk images were corrected and the
ZIP uploaded again. The acquired current pack therefore needs its own hash
and disk-order record; an older party pack or video must not silently substitute
for it. Acquisition artifacts belong under ignored `build/research/colors/`.

The current original pack is now archived by
[the acquisition script](../../research/colors/acquire.py). The ZIP is
422,380 bytes, SHA-256
`085301efa3282fddf8bfb64390ba90f50a7f3831e53f100f009f1cf4e2ee6383`.
It contains exactly three 174,848-byte, 35-track D64s, without error trailers:

| Member name | SHA-256 |
| --- | --- |
| `Colors [Lethargy] 1.d64` | `94bde11ed515f6312fbd77efff9f1fe5c2cdbf25587f0eabada566e0430b1ad6` |
| `Colors [Lethargy] 2.d64` | `f1b2e7ace21a9492f05860666397790a5b42aa9f22d2083100de8af592783d04` |
| `Colors [Lethargy] 3.d64` | `1c1532eb273e01a81c590557f92b7d9305d961d23615e3f43f4c4de325775585` |

There are no README, NFO or source files in the ZIP. The separately fetched
production-notes route has no note body; that does not establish whether a
technical note is stored inside a disk or another author source exists.
[The acquisition receipt](../../build/research/colors/acquisition.json)
retains the original pages, current ZIP/member hashes and version limits.

## Author evidence and original loader

The [source survey](colors-sources.md) preserves release comments, group and
author routes, the official upload, and failed requests separately. The
inspected routes contain no coder explanation of Colors' rendering method.
Vincenzo's correction notice is credited-member evidence about the pack;
other viewers' RGB-line and CRT comments remain hypotheses or observations.
This is a bounded search result, not proof that no author explanation exists.

The [boot analysis](colors-binary.md) identifies the original side 1 PRG as
an 849-byte `SYS2064` bootstrap for **Sparkle 3.4**, rather than Bitfire or
Dali. Its 416-byte resident copy and configured return to `$8000` are
separate byte contracts. The [native investigation](colors-native.md)
follows the acquired D64's ordinary autostart through that return without
changing the program counter or renderer. An independent first-bundle
decompression oracle remains open.

That native session is now owner-closed. All **17 physical-RAM/snapshot
pairs match across 1,114,112 byte comparisons**, without excluded addresses.
The loaded boot and pristine resident also pass their original-byte
contracts. The 11 saved PNGs remain output observations until their pixels
are checked by a separate consumer; RAM equality alone is not that check.

## First-display architecture

The [first-display map](colors-first-display.md) identifies three stored
character phases and a **320×192 hires text canvas**. Four VIC banks each
supply six character rows; code `6*column + local_row` arranges those rows
in column order. Three counter cases and four matrix-builder cases execute
5,050 original instructions against independent all-RAM contracts.

Bank changes use **CIA2's direction register `$DD02`**, with the captured
`$DD00` latch as a required input. The character foreground is black.
Paired hires sprites behind the characters supply red/green patterns over
a blue background. Sprite pointer retention, gradual mask reveal and
raster multiplexing are part of the display history; a late snapshot's
registers cannot stand in for the whole preceding field.

Three stored sprite masks partition a 24×21-pixel grid into disjoint
diagonal classes, with **168 set bits per mask**. The phase-dependent
palette maps those local classes to red, green and blue in different
orders. Character bits select black versus the underlying color; moving
sprite coverage determines where the red/green carriers are available.
This describes literal pixel selection, without assuming an analog blend.

The first intro captures were black during the FLD/reveal transition.
Later captures at `$8E4E`, after 64 reveal-stage invocations, contain the
visible picture. Four consecutive unwarped captures show phase sequence
**0, 1, 2, 0**, with one PAL field between advances after accounting for
the recorded stop-cycle jitter. This establishes the sampled three-field
phase cadence, not the whole demo's frame rate or a static pixel's final
perceived color.

The [independent pixel decoder](colors-first-display-pixels.md) now matches
**all 184,320 canvas pixels across three traced fields**, with zero
mismatches and no excluded pixels. It uses each field's measured bank-store
history and a source-derived fetch schedule. The captured custom GLUE model
briefly selects bank 3 during the bank 1→2 transition, affecting the first
changed character fetch. That intermediate fetch is included explicitly.
The earlier whole-bank-per-six-rows assumption is preserved as a failed
model, with its 14–23 mismatching boundary pixels per sampled field.

These are literal, unfiltered machine-color checks for the captured setup.
They do not establish an effective perceived palette, every physical GLUE/
VIC revision, or compatibility with our vector renderer's two-parity history.

## Questions to investigate

- How does its color-combination cycle divide pixels between raster rows and
  successive fields or frames? Recover the actual register/data sequence.
- Which visual parts calculate geometry or rasterize on the C64, and which
  consume prepared commands, bitmaps or animation phases?
- What are the display storage, buffer history, fill, cleanup and CPU costs?
  Compare like-for-like work with the vector investigations.
- How does the intended analog display interact with the stored palette
  sequence? Keep machine output, PAL decoding, display persistence and any
  emulator/video filtering separate in measurements.
- Can the color method combine with patterned vector filling or our existing
  field histories without introducing incompatible timing or storage demands?

Release comments discuss alternating RGB lines, flicker and CRT presentation.
Those are useful leads and viewer observations; they do not establish the
authors' exact encoding, achievable palette or hardware timing. A screenshot
cannot answer the temporal questions above.

The broader comparison is in [the technique map](technique-map.md). Original
bytes and three exact native pixel comparisons now establish a concrete
first-display architecture. Later effects, other poses and hardware models,
analog presentation and transfers to our renderer remain separate
investigations.
