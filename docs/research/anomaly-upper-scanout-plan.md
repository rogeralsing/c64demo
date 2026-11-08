# Anomaly upper scanout: retained evidence and minimal next capture

The first useful upper interval is **raster 51–154, 104×384 pixels**, in
the four retained post-publication fields. No new native run is needed
to compare those pixels: the [new passive compositor](anomaly-upper-scanout.md)
now matches all four intervals. This plan preserves the source/state
investigation and separates the remaining fetch question from output that
is already observed.

## Concrete retained inputs

| Field | Upper state/input snapshot | Completed output snapshot |
| --- | --- | --- |
| 1 | `native-04/field-pre.vsf` | `native-04/field-post.vsf` |
| 2 | `native-04/field-02-pre.vsf` | `native-04/field-02-post.vsf` |
| 3 | `native-04/field-03-pre.vsf` | `native-04/field-03-post.vsf` |
| 4 | `native-05/restored-arcade.vsf` | `native-06/floor-line-drawn.vsf` |

Paths are under `build/research/anomaly/`. Field 4's input matches
`native-04/field-04-pre.vsf` in all five C64MEM/MAINCPU/VIC-II/CIA1/CIA2
payloads. Its final continuation is the already closed original `$B82A`
state, clock 167,013,188, beam 250/raw62, snapshot SHA-256
`2428affe32e414636d3444b1cfa72f41d25d7e466adf0ff0ad07dbabf28d32c8`.

Each prestate is at `$B400`, line 152/raw10 or13. Therefore its own raster
buffer cannot be assumed to contain completed current-field rows 152–154.
Using it that way fails at **70 pixels** in field 1. The matching poststate
at line 250 contains all 104 completed upper rows. Other fields' old tails
happen to agree because the wall image is unchanged; that coincidence does
not change the output-completion rule.

All four fields display the completed image published at original `$B864`,
clock 166,934,839, beam 255/raw22. The existing independent update receipt
already checks that image's 4,160 bitmap bytes and 520 attributes. Their
identities persist through every selected pre/post state:

| Data | Half-open physical RAM range | SHA-256 |
| --- | --- | --- |
| Upper bitmap | `[$E000,$F040)` | `429638efca0374578677edbfbe3bcb9b2b13bd09b4f5db382c075b0bee19f518` |
| Upper attributes | `[$CC00,$CE08)` | `d9e155dd84805e12d2fb9cc7c8e44457ae41130f37cd8684a508d2503a96af92` |
| Upper sprite pixels/slots | `[$CA00,$CB00)` | Equal to original known `[$7400,$7500)` |
| Sprite 4–7 pointers | `[$CFFC,$D000)` | `$28,$29,$2A,$2B` |

CIA2 PRA=`$F8`, DDR=`$3F` selects bank `$C000`; `$D018=$38` selects the
bitmap and screen above. `$D011=$3B` is hires bitmap with Y scroll 3;
`$D016=$C7` is hires, 38-column, X scroll 7. The source defines 25-row
display start `$33` (51). The active horizontal interval is buffer x=39–342,
and the source bitmap interval is x=0–303 for this fine-scroll phase.

Rows **51–85** are a particularly simple nonzero subcase: no upper sprite
has started, 6,583 of 13,440 pixels are nonzero, and all four copies share
SHA-256 `d979720969ff725af659d0a3dc57532af964d1951dcbb720a12736975eea5966`.
The full upper fields are distinct because their sprites move.

## Actual original setup and motion PCs

The original production Link bytes, rather than a source rebuild, bind:

| Original PC | Operation relevant to the upper interval |
| --- | --- |
| `$B857` | `STA $D016`, after loading the mutable upper fine-scroll immediate at `$B856`. |
| `$B85C` | `STA $D018`, using actual zero-page `$D1`. |
| `$B861` | `STA $DD02`, using actual `$D2`. |
| `$B864` | First instruction after all three upper-selection stores. |
| `$3BE8` | Music IRQ entry. |
| `$3BF8` | `STA $D011`, with original immediate `$3B`. |
| `$3C07` | `STA $D01D`, with original immediate `$FF`. |
| `$3C8A..$3D7E` | Sprite 4–7 movement blocks. |
| `$3D80` | `STY $D010`: the stored register is **Y**, not A. |
| `$3D83` | Original `JSR $2900`, after all sprite X/Y/high-bit preparation. |
| `$3D86` | `JSR $36E3`, the upper update gate. |
| `$3D89` | Actual `BIT $66C2`; the later fade/clear call is not enabled here. |
| `$B468` | Next floor's `STA $DD02=$3D`, observed at line154/raw55. |
| `$B46D/$B472` | Floor `$D016` and `$D018` stores on line155. |

Saved upper positions for sprites 4–7 are respectively
`(88,292,292,58)`, `(80,280,280,44)`, `(72,268,268,30)` and
`(64,256,256,16)`. Y positions remain `(113,85,96,120)`.
From the preceding publication/floor poststate, actual speeds `(8,12,12,14)`
and the original no-borrow/no-wrap branches reproduce each next prestate.
The saved top high-bit mask at `$CB` is `$60`; floor `$D010=$04` must not
be mistaken for the upper mask. All upper sprites are multicolor and
X-expanded, have own color14, shared colors1/3, and no Y expansion.

The retained native-04 `$D016` trace has exactly three intervening upper
stores at `$B857`, all `$C7` on line251/raw24. The first publication's
selected state is separately saved. Bank/D018/D011/sprite endpoints and
original code are checked, but a continuous upper register watch trace is
not present. Monitor observation clocks are not certified bus-write phases.

## Fetch evidence already available, and the precise residual gap

The four `$B400` prestates retain the actual final upper matrix row:
VCBASE=480, RC=5, all 40 VBUF bytes equal `$CDE0..$CE07`, and CBUF equals
Color RAM indices480–519. These are bank-$C000 matrix-latch observations.

Earlier native-04 job-return states also contain nonzero upper graphics
and laser DMA witnesses, in **bank `$4000`**, before the checked publication:

| Snapshot, original PC `$3D89` | Beam | Independent bitmap address | Actual GBUF and pipe0 |
| --- | --- | --- | --- |
| `pixel-row-post` | 94/raw37 | `$46F3` | `$19` |
| `job-09-post` | 113/raw31 | `$4946` | `$0D` |
| `job-13-post` | 88/raw53 | `$4635` | `$04` |
| `job-28-post` | 54/raw21 | `$4033` | `$5F` |

The same states supply nonzero sprite7 row1 at `$74C3..$74C5` (`55 7E E2`)
and sprite6 row0 at `$7480..$7482` (`BE A8 00`). These do not become active
bank-$C000 witnesses merely because the mirrored artwork is equal.

The residual question is an **active nonzero GBUF/laser-data latch in bank
`$C000` during one of these upper displays**, plus a continuous setup trace
if that stronger chronology is wanted. It is not missing pixel output.

## Optional smallest new native collection

The required new collection for the present four-field pixel proof is **zero**.
For the stronger bank-$C000 fetch claim, the sole native owner can later:

1. Restore the latest closed native-06 `$B82A` checkpoint once, with unchanged
   side-one disk SHA-256
   `d452497845598cca8936fdf57c60fdc9c70cd7e64110e049fa6fc7d735f940cd`.
   Verify complete RAM/CPU/ports/beam identity. Add a cancellable monitor
   reader before any potentially unbounded raster observation.
2. Retain upper setup at natural `$B864` and/or sprite preparation at
   natural `$3D83`. Store traces should cover `$D000..$D02E`,
   `$DD00..$DD03`, and `$CFF8..$CFFF`. Decode STA/STX/STY values from the
   actual opcode/register, not always A. These fixed PCs establish setup;
   they are not assumptions about an exact raster phase.
3. Use a bounded any-original-instruction condition for line86 after the
   early sprite5 fetch, ideally raw35–39. Require actual bank `$C000`,
   screen `$CC00`, RC=3, VBUF=`$CCA0..$CCC7`, and sprite5 pointer `$29`.
   Its row0 bytes are `$CA40..$CA42 = 28 00 00`; MC/MCBASE should be checked
   against the saved phase. Compute the latest graphics address from
   **saved VC−1 and RC**, not from a monitor store timestamp. Target
   fetch-VC180–184 addresses `$E5A3,$E5AB,$E5B3,$E5BB,$E5C3` contain
   `$20,$08,$7E,$92,$91`. Accept a nonzero witness only when actual RAM,
   GBUF and pipe0 agree. Retain a missed/zero candidate honestly.
4. Close the exact owned process and write the owner receipt before a
   passive checker consumes the new capture.

No new CPU state, output row or sprite restart should be synthesized to
make this optional observation succeed. Wider wall images, fine-scroll
phases, physical chips, full 312-line output and whole-run FPS remain
separate research.
