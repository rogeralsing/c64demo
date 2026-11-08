# Anomaly: coherent floor strips and actual VIC fetch latches

The retained `native-04` observations and the same-continuation `native-05`
extension check **24 consecutive full-width floor lines in four fields**.
A direct bitmap/screen-cell oracle matches all **36,864 palette-index
pixels**, with zero differences. This includes the two borders and the
actual per-line horizontal scroll. The four resulting strips differ.
The new continuation also retains actual matrix/color latches and a
nonzero graphics fetch byte in both the VIC's graphics latch and its draw
pipeline.

This advances the [upper-update witness](anomaly-upper.md) and
[three floor-store traces](anomaly-native-upper.md) from correct prepared
data/register values to bounded coherent output. It does not establish the
remaining 72 floor lines, sprite composition, upper-wall scanout, a full
screen, physical-chip timing or the demo's whole-run frame rate.

## An output observation already present in the snapshots

The frozen snapshot reader previously retained the VIC module's remaining
121,534 bytes as an opaque hash. The official
[VICE 3.10 source archive](https://sourceforge.net/projects/vice-emu/files/releases/vice-3.10.tar.gz/),
SHA-256 `8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1`,
defines that remaining structure:

| VIC module payload offset | Retained state |
| --- | --- |
| 1,881 | 174 bytes of graphics, sprite, border and color-resolution pipeline state |
| 2,055 | Four little-endian 32-bit values: current raster-buffer line, width, height and pitch |
| 2,071 | Padded palette-index draw allocation: width × (height + 4) bytes |

The observed geometry is **384 × 312**, pitch 384. The allocation begins
with two padding lines; the unpadded image begins 768 bytes later. These
are VIC color indices before host RGB scaling/filtering, so the comparison
does not need an inferred screenshot palette or a fitted crop.

The exact source archive is checked before seven files are read. The new
checker copies those files into its ignored evidence tree and records their
identities. `vicii-snapshot.c`, `vicii-draw-cycle.c`,
`raster/raster-snapshot.c` and `raster/raster.c` supply the layout. The
existing audited `snapshot_state.py` stays unchanged.

At each `field[-02/-03]-post` observation, the current line is 250. Rows
155–178 have therefore completed the raster draw into that field's retained
output. The checker consumes only those completed rows; it does not treat
the still-current line 250 or the unscanned remainder as newly completed
output. This is why the original screenshots alone were unnecessary.

## Independent address and pixel model

The active floor setup writes `$DD02=$3D`, with actual CIA2 port-A latch
`$F8`. The two bank pins select **bank `$4000`**. `$D018=$80` then selects
screen `$6000` and bitmap `$4000`. `$D011=$3B` enables bitmap display;
every scoped `$D016` value is `$C0..$C7`, with multicolor and 40-column
selection clear. This is a **hires bitmap** strip: one bitmap bit chooses
the screen byte's upper or lower color nibble. Color RAM is not used for
that mode's displayed bitmap colors.

For floor-relative line `n=0..23`, the direct model uses:

```text
cell_row = 13 + floor(n / 8)
fine_y = n mod 8
bitmap_byte = RAM[$4000 + 320*cell_row + 8*cell + fine_y]
attribute = RAM[$6000 + 40*cell_row + cell]
fine_x = RAM[$08+n] & 7
color = bitmap_bit ? attribute>>4 : attribute&15
```

The source input is each actual `field-pre` RAM image, rather than a newly
invented image or a replay of the 28 upper jobs. Bitmap `$5040..$53FF`,
screen `$6208..$627F` and the relevant `$D016` table bytes are identical at
the paired pre/post boundaries. The original first-24-line code contains
no writes to these artwork ranges.

The source-exact floor control code `$B400..$B549` is bound to original
Sparkle bundle 36. Only four source-labelled live immediate operands may
differ: `$B40C`, `$B442`, `$B44F` and `$B47F`. This binds the actual setup
and loop path to the original released bytes. The checked native pre/post
code bytes are unchanged throughout each observed field.

The 38-column border needs a pixel-level rule. The official cycle renderer's
left transition masks seven pixels, while its right transition masks the
last pixel of that group. Its active interval is graphics **x=7..310**,
which is full-buffer **x=39..342** with the observed 32-pixel left border.
The model places `bitmap_pixels[7-fine_x : 311-fine_x]` there and uses
actual stable `$D020=0` for the rest of the 384-pixel row. This border rule
comes from `draw_border8`; the comparison does not select a crop to hide
differences.

Sprites do not overlap these 24 lines. Actual prestate has DMA, display,
pending and active sprite bits clear. None of the eight saved Y positions
starts a sprite at 155–178. The only Y assignments in this bounded code
set sprites 2 and 3 to line 208. The first new floor sprite starts at line
179. This is an explicit composition boundary, not an assumption that the
entire floor has no sprites.

## Results and retained failed assumptions

| Field | Compared rows | Pixels including borders | SHA-256 of both independent and observed strips |
| --- | --- | ---: | --- |
| 1 | 155–178 | 9,216 | `ac41fe64e5f78ebe4db17df701fab0a26318e6dbf3d18cec3209e98ffa6babce` |
| 2 | 155–178 | 9,216 | `dde3b8a2a35b83a1ad95d9c8af034d6169cadd608f6545fd12079a4d270a9da5` |
| 3 | 155–178 | 9,216 | `f0bc8a76336730a585fdfa60f72b5ff353f85c15dc4c460b27d8fc6da1994b66` |
| 4, native-05 | 155–178 | 9,216 | `5b130b9a2af21c87804be21a11432642fc7e11b344577fa76d4689be21a9ac36` |

An initial `x=8..311` active-area assumption failed at the right edge:
12, 11 and 12 nonzero bitmap pixels respectively were actually border
pixels in the original three fields. Those failed coordinates/values
remain in each field's receipt.
The corrected source-derived `x=7..310` model matches every pixel in the
complete 384-wide strip. An early checker source-guard error and its
producer are also retained; the writer's casted `SMW_DW` expression is
now guarded literally.

The original 96-store traces remain observer records. This pixel comparison
does not convert their reporting times into bus-write timestamps, nor claim
the moment each VIC latch samples a CPU register. The distinction in
[VICE trace timing](vice-trace-timing.md) still applies. Source fetch and
draw rules explain the model; the new native fetch/latch state below is
separate evidence of the actual fetched data.

## The fourth field's real fetch and draw state

The [root-owned native-05 session](anomaly-native-scanout.md) restores exactly the saved
`native-04/field-04-pre.vsf`, with all RAM, CPU state, CPU ports and beam
checked before resuming. Its wider retained store trace covers VIC
registers `$D000..$D02E`, CIA2 `$DD00..$DD03`, and sprite pointers
`$63F8..$63FF`. During the scoped field, its only stores to mode/bank/border
selection are one `$DD02=$3D` at original `$B468` and three `$D018=$80`
stores at `$B472`, on lines 155, 163 and 171. The latter instruction lies
inside the repeated first eight-line block. An initial one-store assumption
failed; its producer and the actual repeated observations are retained in
`scanout-analysis/rejected-single-D018*`.
It retains the complete 96-value floor-scroll sequence separately. The
owner audit supplies the execution/session boundary; the pixel checker
only reads the closed artifacts.

At `first-row-fetched`, PC `$B47B`, raster **155 / raw cycle 59**, clock
**167,007,200**, actual saved state is:

- `VCBASE=520`, `VC=560`, `VMLI=40`, `RC=1`, badline=1.
- All 40 `VBUF` bytes equal actual RAM `$6208..$622F`, screen row 13.
- All 40 `CBUF` bytes equal actual saved Color RAM indices 520–559.
- The draw pipeline has `xscroll=5`, bitmap-mode value 8, multicolor value
  0, and no pending/active sprites.
- The 304 active pixels of the first floor line match the direct oracle
  in the current-line `DBUF`. The checked interval is already written;
  no stale right-border tail is used.

The saved RC is 1 because the line's cycle-58 RC update has occurred. It
does not imply that the first bitmap row was fetched with RC=1. The real
matrix latches and counter values establish the row that was fetched;
the independent pixel output establishes the corresponding displayed
bitmap result.

The capture called `floor-strip-complete`, at PC `$B54A`, is actually
raster **178 / raw cycle 53**, clock **167,008,643**. It has not completed
the last row's rightmost graphics. This retained observation is useful
as a fetch witness instead: `VC=639`, `VMLI=39`, `RC=7`, `VCBASE=600`.
The pinned `vicii_fetch_graphics` source stores `GBUF` and then increments
VC/VMLI, so the latest graphics fetch used **VC 638**. The real selected
address is therefore:

```text
$4000 + ((638 << 3) | 7) = $53F7
RAM[$53F7] = $07
saved VIC GBUF = $07
saved draw-pipeline GBUF pipe 0 = $07
```

All 40 `VBUF` bytes at this stop also match screen row 15,
`$6258..$627F`; `CBUF` matches actual Color RAM indices 600–639. This is a
nonzero graphics byte in real saved latch/pipeline state, with its address
derived from the saved post-fetch counter and source-defined increment
order. It does not assign a bus-write phase from a monitor record.

Six natural clocks later, `floor-strip-drawn` is PC `$B54D`, raster
**178 / raw cycle 59**, clock **167,008,649**. The previous 23 lines are
committed in the full raster buffer; all 304 active pixels of line 178
are now written in `DBUF`, and actual sprite DMA/display/pending/active
bits remain zero. Both portions match the independent 24-line image.
The later `$B828` field endpoint supplies the complete 24×384 strip,
including the final row's borders. The checker keeps these different
output completion boundaries explicit.

## Reproduction and next boundary

```sh
rtk proxy python3 research/anomaly/scanout.py
```

The [passive checker](../../research/anomaly/scanout.py) reads the retained
original bundle, closed native receipts, six original `native-04` RAM/VSF
pairs and five new `native-05` pairs.
It writes `build/research/anomaly/scanout-analysis/scanout-proof.json`,
byte-identical checked producer, eight raw palette-index strip files and
pinned source copies. `full_floor_or_upper_scanout=false`,
`bus_write_phase_certified=false` and `runtime_witness_complete=false`
preserve the actual scope.

The older native-04-only producer and receipt remain under
`scanout-analysis/native04-only-*`; the source-guard rejection and
right-edge failures remain separate from successful output checks.

The checked producer SHA-256 is
`c5e63a07f3060614710518aaf9b9e6c9365c297619af4e19719a4b5f8b62198f`;
the final receipt SHA-256 is
`ed4a71298f786f7dddaa205c0d217c615fa451bf90ce0a99597f378b91a2236e`.

The useful extension is to extend the compositor through the original
sprites and remaining floor, then reconstruct the upper-wall scanout.
Do not restart the upper-update work merely to obtain another screenshot.
