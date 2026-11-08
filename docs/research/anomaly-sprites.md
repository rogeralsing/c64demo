# Anomaly: independent lower-floor sprite composition

The passive [sprite checker](../../research/anomaly/sprite_scanout.py) now
independently reconstructs **one complete 96×384 floor field, rows
155–250: 36,864 palette indices, with zero differences**. This includes
the original bitmap, sprite composition, per-line scroll and both borders.
It extends the frozen [24-line bitmap proof](anomaly-scanout.md) through
the lower floor in the same closed [native-05 field](anomaly-native-scanout.md),
then consumes the native owner's closed five-clock native-06 continuation
to complete the last row. The comparison uses no screenshot palette,
host scaling or fitted crop.

The native-05 endpoint remains frozen at original PC `$B828`, line 250 /
raw cycle 57, clock 167,013,183, snapshot SHA-256
`2185b4f932c49c900223c9e5c3598fc66c6fd8b1e04704158699659aa574b28a`.
It had 95 completed raster rows and 352 completed pixels of the last row.
Native-06 resumes that exact state through original `INC $D9`, stopping at
`$B82A`, line 250 / raw cycle 62, clock 167,013,188. The completed final
row comes from its separate current-line `DBUF`; that row is not yet
committed to the raster allocation. The output boundary is explicit.

## Pinned inputs and direct pixel rules

The checker pins the frozen snapshot/layout decoder, native-05 and
native-06 owner receipts, original Sparkle bundle-36 proof, author-source receipt and
official [VICE 3.10 source archive](https://sourceforge.net/projects/vice-emu/files/releases/vice-3.10.tar.gz/).
It writes source copies and all results into its own ignored directory,
`build/research/anomaly/sprite-scanout-analysis/`. It starts no emulator,
build, downloaded program or hardware-response model.

Before the extension, the complete native-05-only producer, documentation
and output tree were preserved under `frozen-native05/`. Its manifest
pins 20 files, SHA-256
`9cb1ba973b5cb94b69e6b6e2735bcc524b25593fb8d96e5d9959beb352cae1ff`.
Every run verifies all preserved files. That earlier proof remains at
27,616 new pixels and `full_96_row_floor=false`; the new complete-field
contract does not overwrite those facts or rerun the frozen four-strip
checker.

The actual saved CIA2 latch `$F8` and DDR `$3D` select VIC bank `$4000`.
Actual `$D018=$80`, `$D011=$3B` and all scoped `$D016=$C0..$C7` select a
hires bitmap, screen `$6000` and 38-column border. For each floor line,
bitmap bits directly select the screen byte's high or low color nibble.
The source-derived active interval remains full-buffer x=39–342; all
other pixels are actual border color zero. The 96-byte scroll table,
bitmap `$5040..$5F3F`, screen `$6208..$63E7` and sprite artwork are
identical at the retained entry, line-178 and final boundaries.

This stability has a code check in addition to endpoint equality. The
checker statically decodes the original `$B400..$B827` control block,
admitting its actual instruction set and enumerating every possible write.
There are no indirect/indexed stores or subroutine calls in that block;
all write targets are literal, and none targets the artwork or scroll
table. All observed register/pointer stores belong to this inventory.
The original bytes permit six labelled live immediate operands; during
this field only foreground/shadow color operands `$B559` and `$B55E`
change. This is static control-block inspection, not 6502 execution.

Sprite bytes `$6400..$66BF` and `$7600..$763F` are fully known and equal
the original released bundle bytes. A 24-bit sprite row is indexed
directly from that RAM:

- Hires: each bit chooses transparency or that sprite's own color.
- Multicolor: each two-bit pair chooses transparency, `$D025`, the
  sprite's own color, or `$D026`; each pair occupies two pixels.
- X expansion repeats each output pixel twice.
- Lower sprite number wins overlapping nontransparent sprite pixels.
  Actual `$D01B=0` puts these sprites in front of bitmap foreground.
- The border is applied after composition, including sprite pixels.

The pixel oracle is direct byte/bit/pair indexing. It does not translate
or replay VICE's pixel shifter implementation.

## What the sprites actually contribute

| Sprite | Saved setup and direct model | Visible selected pixels in rows 179–250 |
| --- | --- | ---: |
| 0 | Y=179, X=64, pointer `$96`, hires, no X/Y expansion; rows display at 180–200 | 182 |
| 1 | Y=179, X=64, pointer `$90`, multicolor, no X/Y expansion; fills sprite-0 transparent holes | 71 |
| 2 | Y=208, X=336, pointer `$D8`, hires, X and Y expansion | 0: starts at full-buffer x=344, behind the right border |
| 3 | Y=208, X=64, pointer `$99`, hires; later Y/pointer/expansion updates | 31 |

Sprites 4–7 cannot start in the checked lower interval: their actual saved
Y values are 113, 85, 96 and 120, and the scoped trace has no later Y
assignment for them. Actual line-178 DMA/display/pending/active sprite
bits are all zero.

Sprite 0 and sprite 1 share X=64, or full-buffer x=72. The lower number
therefore supplies its nonzero hires pixels first, and the multicolor
sprite supplies visible pixels through its transparent holes. The
`$D027` writes on lines 180 and 188 occur after these 24 pixels have
finished. Line 180 uses the preceding color 1; lines 181–200 use color
13. This conclusion needs only the observed instruction boundaries and
their large separation from the source-defined X interval, not an
invented exact bus-write clock.

Sprite 3's pointer `$99` contains nonzero data only in its first five
rows. Those rows display at 209–213. Rows 5–20 are already zero. Its
later change to blank pointer `$9A` therefore does **not** supply a
distinguishing visible-pixel witness, although the register history,
source pointer-fetch order and final actual pointer establish that change.

The lower extension now covers **72 complete rows, 179–250: 27,648
indices**. Its sprite contributions remain unchanged by the final 32
border pixels. The entire 96-row independent field is compared again as
one result, rather than declaring full-floor completion from the earlier
partial result alone.

## Vertical expansion, pointer order and actual fetch latches

The source-derived vertical model advances only the four relevant sprite
DMA counters. It starts from the actual line-178 MC/MCBASE/expansion
state, rather than inventing a sprite origin from output pixels.

The pinned PAL source table places sprite 3's pointer/data fetch at
cycles 1–2, and sprite 0–2's fetches at cycles 58–63. Sprite 3 therefore
uses an early current-line fetch; sprites 0–2 use data fetched late in
the preceding line. The counter model follows the source's MCBASE
update, DMA start checks, Y-expansion toggle and display check. It records
each three-byte address and row counter in `sprite-row-fetches.json`.

The line-218 `$D017=$0C` store sets expansion bit 3 while preserving bit
2. Its reported raw cycle 17 is after the MCBASE update and well before
the expansion check. The subsequent equal-value `$0C` stores on lines
226, 234, 242 and 250 do not reset the expansion flip-flop. The associated
Y=240 and pointer `$9A` assignments occur after sprite 3's early fetch,
so that pointer first applies to its line-219 fetch. The original Y=208
DMA finishes, then Y=240 starts another expanded run using the blank
sprite. These repeated pointer stores do not restart that run.

The model matches the final actual MC, MCBASE, expansion flip-flop, DMA
and display state for all four sprites:

| Sprite | MC | MCBASE | Expansion flip-flop | DMA / display at 250/57 |
| --- | ---: | ---: | ---: | --- |
| 0 | 63 | 63 | 1 | off / off |
| 1 | 63 | 63 | 1 | off / off |
| 2 | 63 | 63 | 1 | off / off |
| 3 | 15 | 15 | 0 | on / on |

Two saved native-05 endpoint sprite data latches also match their independently
addressed original bytes:

| Sprite | Pointer | Byte counter | Original RAM address and bytes | Actual saved data |
| --- | --- | ---: | --- | --- |
| 2 | `$D8` | 60, sprite row 20 | `$763C..$763E`: `$2E $C4 $D6` | `$2EC4D6` |
| 3 | `$9A` | 12, sprite row 4 | `$668C..$668E`: `$00 $00 $00` | `$000000` |

The nonzero sprite-2 latch is a real fetch witness even though the border
masks its output. The Y-expansion sequence has endpoint counter evidence;
this field does not visually distinguish expanded from unexpanded pixels
for the masked/blank sprites. Likewise, actual priority is in front of
the bitmap: a behind-bitmap priority setting is implemented by the oracle
but is not claimed as observed behavior.

There is **no row crunch in this interval**. After a changed `$D017`
value, the guarded VICE handler visits each sprite whose **new** expansion
bit is zero and whose flip-flop is low. It applies the crunch formula at
the special check cycle and resets that flip-flop; a falling bit edge is
not required. Here the changed `$04→$0C` write occurs after that special
cycle, and the sprites with new zero bits have flip-flop 1. The other
four sprites also enter with flip-flop 1 and never start lower-field DMA.
Repeated equal-value writes return before this handling. These checks,
rather than the absence of falling bit edges alone, exclude a crunch.

## The closed five-clock completion

The [native owner audit](../../research/anomaly/native_tail.py) supplies
`build/research/anomaly/native-tail-analysis/native-tail-evidence.json`,
SHA-256 `6a059c275606b55e1fc6bfa14a6ac2093112548981fb78182209883d2274ba9e`.
The sprite checker checks that closed receipt and independently verifies:

- The native-06 restored snapshot has byte-identical `C64MEM`, `MAINCPU`,
  `VIC-II`, `CIA1` and `CIA2` payloads to the frozen native-05 endpoint.
- CPU advances from `$B828` to `$B82A` in exactly five clocks. Original
  bytes are `$E6 $D9`, `INC $D9`. The sole physical RAM delta is `$D9`,
  3→4; CPU ports, A/X/Y/SP and all flags except the correct INC N/Z result
  remain unchanged.
- VIC registers and CIA ports/configuration remain fixed. Running CIA
  timers and relative TOD scheduling naturally advance; whole-CIA
  equality is not required across elapsed clocks.
- The saved current line remains 250, and DBUF's written endpoint advances
  456→496. All **384 displayed bytes**, DBUF `[104:488]`, are now written.
  The previously checked 352-byte prefix is unchanged.
- Completed raster rows 155–249 remain byte-identical. Those 95 rows plus
  the completed current-line DBUF row form the observed 96×384 field.
  Every byte matches direct independent bitmap/sprite composition.

The final snapshot is `native-06/floor-line-drawn.vsf`, SHA-256
`2428affe32e414636d3444b1cfa72f41d25d7e466adf0ff0ad07dbabf28d32c8`.
No CPU data/PC patch or synthesized replacement final row is involved.

## Retained rejections and reproduction

Three independently compared alternatives fail against the actual output:

| Rejected model | Different palette indices |
| --- | ---: |
| Omit the sprites | 284 |
| Decode multicolor sprite 1 as hires | 48 |
| Reverse sprite/sprite priority | 93 |

Each JSON preserves every differing coordinate and value. A proposed
same-line pointer-change negative control proved inconclusive because
sprite `$99`'s row 9 is already zero. That failed control and producer
are retained separately; the checker does not count it as pixel proof.
A misaligned initial original-code byte guard is also retained with its
actual bytes and producer.

```sh
rtk proxy python3 research/anomaly/sprite_scanout.py
```

The result is
`build/research/anomaly/sprite-scanout-analysis/sprite-scanout-proof.json`,
with byte-identical checked producer, raw actual/independent indices,
source copies, counter/fetch schedule and rejection records. The frozen
earlier scanout checker and receipt are unchanged.

The result sets `full_96_row_floor=true`, with 36,864 exact palette-index
pixels. Actual and independent full-field files share SHA-256
`898b51a523f9a67460c364086b5f704731f90621772d7e0b3120723e98454577`.
This proves one coherent floor field in the retained original
continuation. Upper-wall scanout, physical-chip timing and whole-run
performance remain separate open work.
