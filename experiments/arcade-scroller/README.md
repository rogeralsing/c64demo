# Arcade floor and hidden wall scroller

An original runnable counterpart to the Arcade Scroller in **We Are The
Anomaly**: neon arcade cabinets move over a prepared perspective floor. The
C64 performs the scrolling and copies. There are no prerecorded screen poses,
original demo bytes, external images or release artwork.

From this directory:

```sh
sh build.sh
sh run.sh
python3 verify.py
```

Build needs the repository's documented Java/KickAssembler installation. Run
uses PAL VICE with sound enabled and normal speed. Verification additionally
uses Python3/Pillow, the tracked root monitor helper and Colodore palette;
it owns and closes its own VICE process. Output is ignored under `build/`.
No sibling repository, downloaded research artifacts or network access is
needed after checkout.

## What the live C64 does

The lower **64 physical raster lines** each have their own accumulator and
fine-scroll value. On every floor update, line `i` adds `112+i` to its byte
accumulator. A carry decrements only that line's fine scroll. Wrapping phase
0 to 7 shifts that actual bitmap scanline by one byte and inserts its next
prepared byte. Eight generated helpers each handle one character row; Y
selects its physical scanline. The live work is fractional arithmetic,
register writes, byte copies and source-index advancement.

Initial phases are `(i + 2*floor(i/16)) mod8`. The prepared artwork compensates
for those phases, so the grid starts coherent. Staggering changes when byte
copies occur. An independent enumeration of the complete 2048-call period
compares this choice with all-zero/all-seven phases; all three perform 9184
scanline copies, while their peak counts are 18, 48 and 64. The comparison is
an arithmetic counterfactual, not an executed alternate binary.

A raster kernel writes 64 distinct `$D016` values on lines 187–250.
The floor is a real hires bitmap in bank 2, with a 38-column aperture hiding
the horizontal edge. The kernel selects that bank after the final horizon
fetch, then restores the wall bank in the lower border. Its aligned delay
routine avoids taken-branch page-crossing costs. Bad-line delays account for
the BA read hold; native register traces and the pixel oracle check the
result rather than assuming nominal instruction sums are enough.

The upper **13 character rows** use two bitmap/screen pairs. A hidden update
has exactly 28 jobs: 13 full 320-byte bitmap rows, 13 full 40-byte attribute
rows, one 13-byte attribute column and one 104-byte bitmap column. Row copies shift
one cell left and temporarily copy the following row's first cell into the
rightmost column. The final column jobs replace that temporary data.
Attribute movement is real, not a fixed palette behind moving pixels.

One foreground call per field samples `$D012` at raster 35, 163, 36, 164 in a
four-field cycle. The caller excludes raster 256–311, avoiding low-byte aliases.
It retains the actual polling sample across JSR: sampling again after a
bad-line hold could turn 163 into 164. `CMP #$24 / BMI` accepts 35 and 164,
and rejects 36 and 163.
The predicate uses the subtraction's sign bit: its complete accepted set is
00–23 and A4–FF, not unsigned “less than 36”. These deliberately chosen call
contexts make both signed boundaries visible. A late accepted bitmap job
can be interrupted by the floor raster; all its writes still target the
hidden wall.

The wall decrements its fine phase every 6 fields. A wrap request waits at
phase 0 until all 28 jobs finish. Only then does lower-border publication swap
the complete bitmap/attribute pair, reset phase 7 and start the next hidden
chain. This explicit completion guard is an own improvement over the
original's unconditional publication schedule. The additional 32-pixel
horizon strip is own static artwork and follows the upper fine scroll.

## Preparation, provenance and scope

`main.asm` generates the original cabinet pixels, small ARCADE glyphs,
per-cell wall colors and 512-pixel-wide skewed floor streams at assembly
time. It also emits copy helpers and address tables. The C64 does not
calculate perspective per pixel, rotate geometry or decode a video.

Mechanism references are the repository's
[source note](../../docs/research/anomaly-arcade.md),
[upper-job model](../../docs/research/anomaly-upper.md) and
[native audit](../../docs/research/anomaly-native-upper.md), based on
Elder0010's author repository revision
`4361d011f56f27014c0b6cd542718ca0b23666d8`. Those establish the original's
independent line rates, phase staggering, generated scanline copies, signed
gate and 28-job hidden chain. No original source or payload was copied here.

Own dimensions/rates, phase offsets, artwork, memory map, two-field floor
update cadence, gate call slots and completion guard differ from the
production. The original has 96 floor lines, rates 102–197, larger prepared
streams and a 15-invocation wall divider. Its 936×96 artwork and 50fps claim
are not claims about this example.

## Native verification

`verify.py` independently constructs the artwork, derives floor state from
cumulative integer formulas, models actual hidden jobs and derives the
complete screenshot directly from the artwork and each line's accumulated
motion. It checks visible buffers while an interrupted hidden copy is only
a prefix of its job, then checks both complete domains after the job.
Coherent wall images are also compared with a separate direct column-offset
construction before publication. The observer never writes CPU registers,
code, display data or the scene state.

The bounded result and actual timing measurements are recorded in
`build/verification/proof.json`, with full-field PNGs, monitor transcript,
VICE log and a sampled GIF. A failed rerun removes the current success
receipt. The GIF uses uniform 160ms sample playback; it is not a recording
of native cadence. VICE store timestamps are observer coordinates, not
certified physical bus-write phases. Physical C64 revisions, every future
field and the original demo's throughput remain outside this proof.

The retained native run passes **144 consecutive PAL fields**, 144 actual
gate calls, 71 completed hidden jobs and two complete publications after
fields 56 and 112. There are 21 captures of interrupted hidden-copy prefixes
and 17 fields where publication waits for readiness. Both bitmap and
attribute data match the independent models. Sixteen complete screenshots
cover moving phases and both publication transitions.

The floor updates every **2 PAL fields**. The first 72 updates take
989–4380 native clocks. A separate natural continuation reaches the first
maximum-copy update, number 291: its 18 coarse scanline copies take **8493
clocks**, from raster 253 to raster 76 of the next field, ahead of the next
gate and floor. Its following field 581 also passes a complete pixel oracle.
The skipped continuation fields are not added to the contiguous wall-job
audit. Across these 145 sampled floor fields, all **9280 actual `$D016`
stores** match their line/value schedules. Each field's stores are 63 clocks
apart; corresponding stores in the contiguous audit recur after
19655–19657 observer clocks, including a one-cycle phase variation.

All **1,775,616 screenshot pixels**, **1,160,000 visible bitmap bytes** and
**148,480 visible attribute bytes** match. Those counts include the peak
witness. VICE exits normally with code 0. This proves the stated bounded
example; the full-period peak count alone is not a worst-case timing proof
for every possible accumulator/job combination.
