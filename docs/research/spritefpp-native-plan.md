# SpriteFPP: exact entries and the shared-strip DMA acceptance plan

This is a static source/machine-byte plan for the next owned native run.
No assembler, Unity project, C64 CPU or emulator was executed here. The
[prepared atlas/list proof](frontier-geometry-20261108.md) remains unchanged;
its sample counts are not counted again as new work.

## Two real binaries with different startup contracts

The supplied **Parts** PRG is a standalone executable, although the retained
`variables.asm` currently says `STANDALONE_BUILD=false`. Its machine bytes
take precedence over that source setting. A separately acquired **Link**
PRG is the common-demo variant. Both are immutable Git blobs in author
repository commit `965807c511e2025b5c5e1ffb2a6235a4efd6ae5b`:

| Artifact | Bytes / loaded range | SHA-256 |
| --- | --- | --- |
| Existing `Parts/SpriteFPP/SpriteFpp.prg` | 48,386; `[$0801,$C501)` | `7aba9b129119ec31aa31d06e663ebaca0bf221247c71af532f3b529c4a359e1a` |
| New `Link/SpriteFPP/SpriteFPP.prg` | 33,970; `[$4003,$C4B3)` | `397ab215391c900d39fcc1d5b8da93e9f7bd8b251fde78f5f0a190fb253388aa` |
| New `Link/SpriteFPP/DISK-SpriteFPP.prg` | 52; `[$088F,$08C1)` | `d1ebebacac5053f0d7b89d3d1941efc8fc0df8514ad8cdbf98ef81942b8edef9` |

The new bodies, response headers and Git-blob checks are under ignored
`build/research/spritefpp-native-plan/`; `acquisitions.json` pins them.
The Link PRG blob is `6e9ec7b034d597209b338f6d2b7fd4816150370a`;
the driver blob is `a791a54b38231f9fcb40f63b486d11cadbd05203`.
These repository artifacts are not yet identified with the original
release's loaded bundle; the native owner must establish that binding.

The standalone BASIC line is `SYS49920`, entering **`$C300`**. Its own
startup disables interrupts, writes processor port `$01=$35`, initializes
the embedded SID at `$0900`, configures CIA/raster interrupts and eventually
spins at **`$C3CD`**. Bytes `$AB $00` at `$C305` are the source's two-byte
`LAX #0`; a generic disassembler's separate `???/BRK` output is not an
executed BRK. Music play is `$0906`. Its init IRQ begins `$C3D1` and uses a
different count-down schedule from the current common-demo source.

The common PRG's **`$C300`** begins directly with a frame wait. It provides
no BASIC/SID/base-code startup and ends with **`RTS $C36B`**. Its init IRQ
is **`$C36C`**, calls common music **`$0800`**, and follows the source's
`$20−$18` raster-countdown path. The standalone instead has its counter
at `$C3D0` and subtracts `$08`. Do not transfer those startup PCs/literals
between variants.

The [original driver source](https://raw.githubusercontent.com/RobertTroughton/C64Demo-PublicReleases/965807c511e2025b5c5e1ffb2a6235a4efd6ae5b/NoBounds/Parts/SpriteFPP/DISK-SpriteFpp.asm)
and its actual 52-byte binary agree: entry **`$0890`** checks full-demo
marker `$08FF`; if negative, it waits for music counter `$FE/$FF` to reach
`$19FB`. **`$08A4` calls `$C300`** and the natural return is **`$08A7`**,
which preloads through `$0809`. It then waits on PartDone `$088F`.
This path requires the production's installed loader/music, mapped RAM IRQ
vectors, raster IRQ service and return stack. It is not a naked SYS entry.

The retained `NoBoundsA.sls` loads the Link PRG in three File domains:

| Physical destination | PRG file offset | Length |
| --- | --- | --- |
| `$4003` | `$0002` | `$1100` |
| `$8000` | `$3FFF` | `$2440` |
| `$AB00` | `$6AFF` | through file end |

Thus original-bundle matching should check those actual File domains and
the driver, rather than assume all PRG gap bytes were loaded. In particular,
`$4000..$4002` are outside the first domain; the strip format intentionally
starts at slot byte3.

## Actual initialization and natural anchors

Both binaries have the same initial sprite routine at **`$9900`**.
It programs these eight Y registers, in hardware-sprite order:

```text
sprite:   0   1   2   3   4   5   6   7
Y:       75  74  73  72  71  70  69  68
```

It clears X/Y expansion and priority, enables multicolor for all sprites,
initializes adjacent X coordinates starting110 in steps24, and sets shared
pointer `$FF` in `$43F8..$43FF`. `$D010=$80` supplies sprite7's high X bit.
The X loop temporarily also writes `$D010` as its ninth indexed store;
the explicit `$80` assignment follows it. Runtime `draw_frame` subsequently
replaces X positions and X-expansion masks from its size tables.

The common initializer additionally clears `$7F00..$7FFF`, making pointer
`$FF` a defined blank. Its RTS is **`$997A`**. The standalone's RTS is
**`$9977`**; that variant's full PRG already contains zero-filled `$7F00`.
The common setup finishes at `$08A7`; the standalone finishes at `$C3CD`.
Capture actual initialized RAM/ports/registers there instead of inventing
zero-page, stack or CIA state.

Common init IRQ writes `$DD02=$3D` at **`$C39F`**, `$D016=$C8` at `$C3A4`
and `$D018=0` at `$C3A9`. `$DD02` alone is not a bank proof: record actual
CIA2 PRA and DDR and evaluate output pins plus input pull-ups. For the
intended bank `$4000`, those low pins are `%10`; screen/pointers are then
`$4000/$43F8`. The standalone instead writes DDR `$03` at `$C356` and
selects PRA's low bits `%10` at `$C3FD`.

| Shared machine PC | Useful natural boundary |
| --- | --- |
| `$920D` | Bottom IRQ entry; schedules hidden palette IRQ and next FPP. |
| `$9234` | `JSR draw_frame`: target `$9A92` common, `$9A8F` standalone. |
| `$9237` | Natural return after pointer-row/X-table preparation. |
| `$8000` | FPP IRQ entry. It enables all sprites at `$8008`. |
| `$800D/$8010` | Compare/wait for actual `$E9`, initially `$4C` (76). |
| `$8026/$8028` | Load Y=`$FF`, X=`$00`. |
| `$802A` | First `STY $D017`; `$802D` follows it. |
| `$8048` | First `STX $D017`; `$804B` follows it and starts cell1. |
| `$914F` | Extra final pointer cell, after 133 ordinary cells. |
| `$916D/$9170` | Extra cell's clear and its continuation. |
| `$9172` | Disable sprites for the remainder of the field. |

For zero-based cell `n`, use **`S(n)=$802A+33*n`**:
`STY` at `S`, row load at `S+3`, pointer stores at `S+6+3*s`,
`STX` at `S+30`, and its next original PC at `S+33`.
An interior example is cell64: **`$886A / $886D / $8888 / $888B`**.
These are exact code addresses shared by the two supplied variants, not
certified raster phases. The `$0700` row table is initially `$FF`; choose
an actual nonblank later row from saved table state after `$9237`.

## Why the expected offsets are 3,6,...,24

The pinned [official VICE PAL source](https://sourceforge.net/projects/vice-emu/files/releases/vice-3.10.tar.gz/)
defines DMA starts at the Y match, display/MC reset at PAL cycle58, and
MCBASE update at cycle16. These PAL labels are **one-based**; snapshot raw
cycles14/15/55/57 correspond to PAL15/16/56/58. Sprite0–2 fetch late in the preceding line;
sprite3–7 fetch early in the displayed line. With the actual staggered Ys,
no Y expansion before the first FPP cell, and all sprites enabled in time,
the state after **line76/cycle16** is:

| Sprite | First complete triplet's fetch line | MCBASE after line76/cycle16 | Held offset's subsequent triplet |
| --- | ---: | ---: | --- |
| 0 | 75, late | 3 | 3–5 |
| 1 | 74, late | 6 | 6–8 |
| 2 | 73, late | 9 | 9–11 |
| 3 | 73, early | 12 | 12–14 |
| 4 | 72, early | 15 | 15–17 |
| 5 | 71, early | 18 | 18–20 |
| 6 | 70, early | 21 | 21–23 |
| 7 | 69, early | 24 | 24–26 |

This explains the stored 24-byte strip at slot+3: one common pointer can
route eight different triplets, in horizontal sprite order. It is a
source-derived expected state, not a claim that native counters have already
been observed. The table gives bases for **subsequent** reset/fetch cycles;
the line76 data registers need not already contain those following triplets.

The likely steady mechanism is **holding MCBASE**, not assuming a crunch:
set `$D017=$FF` before the expansion check at PAL56, making the expansion
flip-flops0; keep them0 through the following cycle16 so MCBASE does not
advance; then clear `$D017` after that update to set the flip-flops1 again.
Setting `$FF` later in that line allows the next expansion check to toggle
them back0. Record the actual phases to establish this sequence.

The official `$D017` handler has a separate special **PAL15** crunch case.
After any changed register value it handles sprites whose *new* bit is0
and flip-flop is0; a falling edge is not separately required. At that
special cycle it computes:

```text
MC' = ($2A & (MCBASE & MC)) | ($15 & (MCBASE | MC))
```

That formula would change many proposed 3,6,... offsets. Therefore do not
label the clear as cycle15 or apply the formula merely because the source
contains `$D017` stores. The native before/after pair must distinguish
post-cycle16 holding from a real crunch.

## Minimal owned native acceptance

1. Keep two runs distinct: a fresh declared standalone BASIC launch, and
   the original disk/common part after its bundle bytes and driver are bound.
   Do not substitute the standalone's startup/music for common-demo services.
2. Save entry and completed-init RAM/VSF pairs at the variant-specific PCs
   above. At the common run, preserve the actual `$08A4→$C300→$08A7` call.
   Then retain `$9237` state: `$0700..$0784`, frame/size values, actual
   pointer/X tables, colors, VIC mode and CIA bank pins. A nonzero stored
   triplet can prove DMA even while fade-in colors still make output black.
3. Observe a settled FPP prefix at `$8026` and one interior cell whose
   saved pointer row selects nonblank atlas data. Retain **before clear**
   `S+30` and **after clear** `S+33`; also retain the next cell's `S+30`
   to prove the offset vector persists over a line. Record all eight
   MC/MCBASE/expansion-flop, pointer/data, DMA/display and draw-pipeline fields.
4. Expected steady MCBASE is **`3,6,9,12,15,18,21,24`**. After all eight
   fetches have completed and before the cycle58 MC reset, expected MC is
   **`6,9,12,15,18,21,24,27`**. Before a post-cycle16 clear expect D017=`$FF`
   and flip-flops0; afterward D017=0 and flip-flops1, without changing
   MCBASE. Apply the saved phase's partial-fetch/reset rules if the snapshot
   straddles those boundaries; do not force this convenient MC vector there.
5. For a completed fetch, require actual `sprite.data` to equal the three
   original bytes at **`bank + pointer*64 + MCBASE`**, or equivalently
   `MC−3` only in the completed-fetch phase above. Record actual cached
   pointers: do not assume that eight just-written table entries have all
   reached the shifters, or invent the table-index-to-raster lag. One sample
   with all eight latched to the same nonblank pointer and the expected
   triplets directly tests the shared-strip representation.
6. Trace `$D017`, `$43F8..$43FF`, `$D015/$D01C/$D01D`, CIA2 bank selection
   and relevant frame-table writes. Decode STY values from Y and STX from X.
   Monitor store timestamps are later observer boundaries, not bus phases.
   Close the exact owned process and owner receipt before passive analysis.

The existing cancellable reader should bound all raster waits; these original
PCs avoid a main-loop-only raster condition. Retain failed conditions,
unexpected offsets and blank/undiscriminating strips. This plan establishes
what to check next; it does not claim displayed pixels, original-release
equivalence, all-frame continuity or a complete renderer budget.
