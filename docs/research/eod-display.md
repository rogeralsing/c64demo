# Edge of Disgrace: actual text display and publication boundary

Research date: 8 November 2026. The original shader's `$7000..$77FF`
software output is selected as a VIC character set, not a bitmap. One
original native-04 baseline now matches **all 16,384 palette indices** in
a committed **128×128 physical-pixel rectangle**. An actual nonzero glyph
fetch, cached matrix/color state and the complete watched store history
bind the independent software prediction to that displayed field.

The [frame proof](eod-frame.md) independently reproduces the complete
software buffer with declared crop/previous-state inputs. It does not
prove that an arbitrary later screenshot samples that plane coherently.
This note owns the separate display mapping and bounded committed field.
The [new case proof](eod-output-case.md) owns native custody, while the
[six-pose software proof](eod-poses.md) supplies the independently calculated
new baseline. Its other poses do not gain displayed-pixel acceptance from
this one field.

## Source-bound layout

Original files 51/52 are reused without modification. `$0F23..$0F2D`
copies the 47-byte register template at `$102F` to `$D000..$D02E`.
Its `$D018=$BC` selects a screen at bank offset `$2C00` and character set
at offset `$3000`. `$0F35` sets CIA2 DDRA to `$3D`.

Retained snapshots have CIA2 PRA=`$C0`, DDRA=`$3D`. The effective output
used by the official VICE bank callback is `PRA OR NOT DDRA`, hence `$C2`:
bank **`$4000`**, screen **`$6C00`**, charset **`$7000`**. Reading the PRA
latch's low bits without the DDR would select the wrong bank. Official
VICE 3.10 `ciacore.c:802–809` supplies the combined output; `c64cia2.c:150–154`
inverts its low bits for the bank. The pinned archive is read as data.

`$0FCB` clears all 1,024 screen bytes. The loop `$0FDE..$1004` then writes:

```text
screen address = $6CF0 + 40*row + column
screen code    = 16*column + row
row, column    = 0..15
```

Normal text addressing for that code gives:

```text
glyph byte = $7000 + 8*(16*column+row) + RC
           = $7000 + 128*column + logical_Y
logical_Y  = 8*row + RC
```

Thus the nominal canvas is sixteen by sixteen characters: **64×128
multicolor selectors / 128×128 physical pixels**. All 2,048 software offsets
are unique. Its actual raster position must still follow the live fetch
counters, timed top IRQ and fine scroll; screen-memory row 6 is not enough
to infer the final raster coordinates.

`$0F3B..$0F4A` fills physical Color RAM with 9. All 1,024 serialized Color
RAM bytes in the selected retained states are 9. This is the snapshot's
physical Color RAM, not the RAM hidden beneath `$D800` when I/O is banked
out for generated code. With ECM/BMM off, MCM on and color bit 3 set, each
glyph byte supplies four two-bit selectors, each displayed twice:

| Selector | Display color source |
|---:|---|
| 0 | `$D021` |
| 1 | `$D022` |
| 2 | `$D023` |
| 3 | Color RAM AND 7, here palette index 1 |

The official `vicii-draw-cycle.c` mode table and multicolor bit-pair code
define this mapping. A nibble is two selectors/four physical pixels; it is
not a single native C64 pixel.

## IRQ movement, palette and direct publication

The top IRQ at `$1606` obtains a waveform byte through `$0800,X`, advances
the self-modified waveform index at `$1637`, and writes `$D016` at `$1643`.
The lower three waveform bits set fine X through `XOR $17`. Its remaining
bits change a branch delay before the timed `$D011=$7A` then `$1B` pulse at
`$166B/$166E`. The static lattice must therefore be bound to actual cached
codes/counters in each observed field; a fixed raster-column assumption is
not sufficient.

Top IRQ color work writes border/background and, on its ramp cadence,
updates `$D022/$D023`. Separate bottom IRQ `$16D4` briefly writes zero to
background/border and then the self-modified color at `$1700`. Those
current-register values need not describe an earlier line. For example the
retained stable interior palette is `[2,10,7,1]`, while snapshots at other
raster phases have a different current background. No palette is inferred
from the software selector bytes alone.

Every selected retained state uses the same `$D018=$BC` and bank `$4000`.
The inspected common IRQ calls prefix construction at `$174D` and marker
clear at `$1750`, then dispatches more geometry. Prefix stores directly to
the **active `$7000` charset**; no front/back selector flip is identified
in that path. The prefix window itself spans a display field, so its
completion is not automatically a coherent displayed-frame boundary.
This is a bounded source/observation claim, not proof that no other scene
or animation phase ever changes banks.

Retained VIC states show `$D015=0`, sprite DMA/display bits zero. The accepted
display window also guards those facts and their write history before
omitting sprites from its independent compositor.

## Current and cached evidence

The passive producer checks all 1,024 screen bytes and
1,024 Color RAM entries in each of six native-03 states. Two retained
cached matrix rows contain the original sixteen-code progression, with
Color RAM cache entries 9. Their active sequence begins at vbuf index 9;
the sampled character rows are 12 and 3. These are cache observations,
not a claim that all corresponding glyph pixels were already fetched or
committed at the stop.

The VIC RC update occurs at PAL cycle 58 (snapshot raw cycle 57). A late
snapshot can already hold the next row's RC while its current line was
drawn with the preceding RC. VIC graphics fetches use `vbuf[VMli]`, current
RC and the charset bits, then increment VMli and leave the byte in `gbuf`.
That latch is the actual-fetch witness in the new field below.

## Accepted bounded display field

The scalar consumes the newly captured original stable pose's independently
predicted output from the multi-pose proof. The prior native-03 output SHA-256
`f49b358d502aee74860db36ce54986e310ff4e8ec96e7d154adc402a35428378`
also happens to match, but it is not used as the new boot's prediction.
The new baseline is recalculated from its own incoming angles/state; its
current-frame native stage results enter comparisons only.

After natural prefix-filled `$1750` and next `$546A`, the next top-IRQ
continuation **`$16BB`** supplies the actual palette, scroll and bank after
setup. Two any-original-instruction breakpoints give the later witnesses:

| Capture | PC | Clock | Raster / raw cycle |
|---|---:|---:|---:|
| `display-setup` | `$16BB` | 469329631 | 52 / 43 |
| `display-mid` | `$5CDB` | 469334533 | 130 / 31 |
| `display-complete` | `$5DDC` | 469340208 | 220 / 36 |

Clock differences equal the corresponding 63-cycle line/raw-phase
differences exactly: all three observations belong to one field. Their
RAM/VSF pairs and original source generation are accepted by the frozen
36-pair/270-command case proof. The complete case retains its two waiting
notices and actual command/breakpoint responses;
this display producer does not replace that wire audit.

The instruction-boundary conditions were:

```text
line 130, raw cycle 31..35: display-mid
line 220, raw cycle 35..45: display-complete
```

The monitor commands use explicit hexadecimal constants:

```text
break exec 0000 ffff if (RL == $82) && (CY >= $1f) && (CY <= $23)
break exec 0000 ffff if (RL == $dc) && (CY >= $23) && (CY <= $2d)
```

The actual creation/ID responses and observed phases remain retained.
These are instruction-boundary windows, not forced exact cycles. The
official monitor lexer maps RL/CY to raster line/cycle.

At midrow the unique cached sequence is at vbuf 9..24, with character row
4, RC=7 and VCBASE=391. All forty cached codes agree with the unchanged
source matrix at `screen+(VCBASE+index) mod 1024`; all cached colors are 9.
The logical Y is therefore `8*4+7=39`, giving first canvas line
`130−39=91`. Fine X is 2, giving physical left X `32+8*9+2=106`.
The first 32 is the normal PAL left border in the pinned official source,
consistent with the actual 384-pixel-wide serialized buffer.

`VMli=17` identifies the last completed fetch at vbuf index 16. Its code
is `$74`, so the actual source address is **`$7000+8*$74+7=$73A7`**.
The new independent software prediction supplies **`$BB`**, matching both
VIC `gbuf` and draw-pipe 0; the latched code/color also agree. This byte's
selectors are `[2,3,2,3]`, displayed as yellow/white/yellow/white pairs under
the actual palette `[2,10,7,1]`. Not every glyph byte is individually
latched: this nonblank actual fetch supports the source/counter contract,
while the complete rectangle is checked against committed output.

All **16,384 indices in X `[106,234)`, Y `[91,219)`** match a direct
bit-pair compositor. The serialized raster's current line is 220; the
last compared line is 218. The compositor uses the independently predicted
software file, actual stable palette and anchored lattice. Late native
charset RAM and the finished raster are comparison targets only.
Predicted and committed rectangle SHA-256 is
`fe5a5701c8d0aab20d8762a96efe04fa2d888db753500c9bc33d6c46cd62ac49`.
Color counts are 1→1,564, 2→8,696, 7→4,916 and 10→1,208.

Two discriminating controls reject alternate interpretations: using full
Color RAM 9 for selector 3 gives **1,564 wrong pixels**; swapping `$D022`
and `$D023` gives **6,124**. The correct selector mapping is not merely a
matching color histogram.

## Watched stores and publication scope

The five store trace ranges are `$D000..$D02E`, `$DD00..$DD03`,
`$6C00..$6FFF`, `$7000..$77FF` and `$D800..$DBFF`. They are armed after
setup and remain active through the committed endpoint. The exact four
instruction hits are:

| PC | Instruction | Role |
|---:|---|---|
| `$16BD` | `STA $D012`, A=`$C0` | Schedule the later IRQ |
| `$16C5` | `INC $D019` | IRQ acknowledge RMW |
| `$1732` | `STA $D012`, A=`$FA` | Schedule the bottom IRQ |
| `$173A` | `INC $D019` | IRQ acknowledge RMW |

All attached register reads have CPU `$01=$35`, establishing VIC I/O for
these addresses. The RMW observations are instruction hits, not a claim
that one hit equals one physical bus write. No charset, matrix, Color RAM,
mode, palette or bank write occurs in the watched window. Palette-write,
unchanged-value palette-write and effective-palette-change counts are all
zero; same-value stores would still count as observed writes.

The first hit in each resume has monitor prompts on its line. An anchored
`^#` parser would miss the two `$D012` stores. This producer retains and
rehashes complete response ranges and all four raw hit blocks, matches
without that line-start assumption, checks original instruction bytes and
classifies their addressed device using the accepted CPU-port context.

The active charset equals the independent software prediction in setup,
midrow and endpoint RAM, and the complete trace excludes reuse within this
field. This establishes one coherent displayed component after prefix
completion, with direct publication into the active charset. It does not
establish tear-free publication during every prefix pass, a universal
display latency, complete surrounding borders or all 312 raster lines.

## Passive replay

```sh
rtk proxy python3 -B research/eod/display.py --output build/research/eod/display-analysis/fresh-replay
```

Choose a fresh directory. Current acceptance is
`display-analysis/accepted-02/display-proof.json`, **33,595 bytes**, SHA-256
`c10a8291e174609d250c0149d500aa49f4c584752b3a6e7cf592ce3a090f982f`.
The producer is **25,133 bytes**, SHA-256
`4566af3d510f8b7108697456b8decc48c427c2cc0b033e369e42315eaa0f050d`.
Source-01/source-02 retain the earlier pending source/cache scope;
accepted-01 retains the first native result, and accepted-02 adds explicit
output-file metadata. No earlier output is overwritten.

Independent source review passes. A fresh root replay reproduces all four
output files byte for byte, **76,136 bytes**.
`display-analysis/root-replay-check.json` records that comparison
(970 bytes, SHA-256
`618f44898118fcf6ae7ffac68c015b4ea593aa4637cc91db68cb0c85ecdd8b30`).

The new case proof is `output-case-analysis/accepted-01/output-case-proof.json`,
SHA-256 `0fe2af337eb6a2674e6cb60b7f861b744457fa7ee8b65e05eed2d10bd9c6a0dd`.
The new software baseline comes from
`multi-pose-analysis/accepted-01/multi-pose-proof.json`, SHA-256
`ca3baca1dd889b3b0e9ef9fe81d5f1f3c89f27c15d7a420f105a19d670f19a11`.
Both dependencies and their checked sources are pinned. No emulator, CPU
interpreter, build, downloaded host entrypoint or process control is used by
passive replay. Earlier EOD producers, documents and outputs remain frozen.

Next extend actual fetch/output acceptance to another pose or crop boundary,
and inspect prefix-transition fields or crop-plan generation if needed.
The five additional poses' software results remain separate from this
single displayed field. Preserve the existing independent oracle rather
than treating every new screenshot as proof or repeatedly checking only
the same software buffer.
