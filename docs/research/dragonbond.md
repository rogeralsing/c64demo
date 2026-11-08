# The Dragonbond: original-disk bootstrap and intermediate-sprite research

This case starts from the unchanged **The Dragonbond** disk by Abyss
Connection, released at X on **6 June 2026**. Background is credited for code
and graphics on the [release page](https://csdb.dk/release/?id=262185).
The author's [making-of PDF, printed page 7](https://englishclass.de/~wolf/ac/assets/downloads/demos/the-dragonbond-making_of.pdf)
describes an intermediate sprite whose first 30 pixel bytes come from the
successor and last 33 pixel bytes come from the current image. This is a
specific data-and-register handover claim; identifying a generic sprite
multiplexer would not verify it.

The original release now has checked native pointer/Y stores and VIC DMA
latches for two handovers, one in each VIC bank. The two checked eight-sprite
groups use **33 new head bytes and 30 old tail bytes**. That verifies the
prepared-intermediate mechanism while bounding the difference from the PDF's
simplified example. Pixel composition and the author's nine-line allowance
remain outside this result.

## Original identities

The [group disk](https://englishclass.de/~wolf/ac/assets/downloads/demos/the-dragonbond.d64)
and [CSDb disk](https://csdb.dk/getinternalfile.php/280588/the-dragonbond.d64)
are byte-identical, 174,848 bytes, SHA-256
`37854b4e3426349ee03bc759f5bed8ad9a6c7f0404a469f1ae5163918cf50300`.
The PDF is 2,286,989 bytes, SHA-256
`b6ad3ad2e96dae340f995ac7f8dbd1012c4c773272ccaed44c36ba9ee64fde2f`.

The actual DOS chain at **18/2 through 18/9** is a 2,022-byte PRG, SHA-256
`91e2aa52bcca8edda4dbf580709d294ff87deeb4a853aa2e14c2df9c92bb3fcc`.
It loads at `$0801`; its BASIC line says `SYS2078`, entering `$081e`.
The disk's many artwork directory aliases share this same chain. Neither
their names nor the author's separate statement about a story-part loader
establishes this bootstrap's family.

## Bootstrap reconstructed from the released bytes

The original `$081e` entry disables IRQ, increments processor port `$01`,
and copies `$0846..$0945` into `$0020..$011f`. It then copies seven pages,
`$08e5..$0fe4`, backward into `$f900..$ffff`, sets X to `$61` and jumps to
`$0020`. All **1,695 encoded bytes** at `$f961..$ffff` are read exactly once
in order. The first therefore refers to the original PRG byte at memory
address `$0946`. The source, destination and
page count follow the actual self-modifying copy operands, not a packer
signature.

The relocated depacker reads literals and reconstructs back-references into
one contiguous range, **`$1000..$2024`**, 4,133 bytes. Its final original
sequence is `DEC $01` at `$0100`, `CLI`, `STA $98`, and `JMP $2000` at
`$0105`. A bounded py65 execution of the original instructions takes
**62,508 instructions** to reach `$2000`. The model rejects every read
without byte provenance and every visible IO or ROM read; none occurred.
It does not execute the `$2000` entry, whose first instructions write VIC
registers.

The output's 4,133 bytes match the separately captured native RAM at the
natural `$2000` stop exactly, SHA-256
`cd0c20105dc3196aa0e0c87e2122ce40b8e00a75f2d1e6fb2b10857a863527ee`.
The full model RAM is not expected to match native RAM: native BASIC/KERNAL
state and its stack precede the observed bootstrap. Only the known output
range is compared.

## Released loader path and natural breakpoint anchors

At `$2000`, the original code sets border/background and clears color RAM,
then executes `CLD; JSR $1000; LDA #0; JSR $06bb; JMP $0400`. These are
useful natural execution checkpoints, with no PC redirection needed:

| Address | Meaning established from actual bytes |
| --- | --- |
| `$081e` | BASIC's original machine-code entry. |
| `$0020` | Relocated RAM-only depacker entry. |
| `$2000` | Depacked startup, before VIC/color-RAM initialization. |
| `$1000` | Loader installer entry. |
| `$06bb` | First load/depack request, with A=0 from `$201d`. |
| `$0400` | Original post-load jump target: common transition/loader code. |
| `$2800` | Next jump target after loading index `$3e` from `$041a`. |
| `$061f` | Resident receiver entry, dependent on CIA2/drive handshake. |
| `$06fd` / `$0775` | Resident literal / back-reference destination stores. |

The installer probes devices 8 through 11 using KERNAL entry points
`$ffb1/$ff93/$ffae`. At `$10bf` it sends `I`, then four 32-byte `M-W`
commands transferring `$1161..$11e0` to drive address `$0700`, followed by
`M-E $0700`. At `$1058..$1086`, it transmits the body `$11d6..$16b2`
through CIA2. This identifies concrete transport code and boundaries; it
does not establish successful drive execution in the host CPU model.

The loop at `$108f/$1095` installs the 423-byte host receiver/depacker from
`$16b3..$1859` into **`$0600..$07a6`**. Its adjacent source and destination
ranges overlap consistently: reproducing the actual X order and both stores
gives exactly the contiguous source image. The resident image's SHA-256 is
`e798d70f44a492c1f1d7c5dcdf74882d2e520f83b6b056af60c29dd1554b4612`.
`$06bb` sends the requested file index through `$0600`; `$0694` obtains
encoded bytes, refilling via `$06a0/$061f`; `$06fd` emits literals and
`$0775` copies matches. These receiver/drive boundaries must remain explicit
in any further host model. Flattening CIA2 into RAM would invent transport
results.

The native drive RAM captured at the first `$06bb` request binds both
transfers to the original disk bytes. `$0700..$077f` matches the 128-byte
first stage except `$0756`, its self-modified destination-page operand.
`$0000..$04dc` matches the 1,245-byte body except five bytes: the zone's sector
count at `$a5`, the JSR return address on stack `$0106/$0107`, and two branch
operands at `$01b5/$01ca` explicitly patched by `$0405/$0408`. These exact
differences are recorded and asserted; they are not ignored wholesale.
The 2,048-byte native drive dump has SHA-256
`675e68ea8023485b75bf619f742103a7515385cd6a419bf8018d2d6adac1d0ce`.

The first loaded `$0400` entry is a dispatcher. Its `$0412` route clears
VIC state, installs IRQ `$04b2` for raster `$34`, requests file index
`$3e` with `JSR $06bb` at `$041a`, then jumps to **`$2800`**. Therefore
the `$0400` capture alone does not yet contain or identify the artwork's
sprite schedule. Other dispatcher routes request `$3f/$40/$41/$42` before
the same `$2800` target, or request index 1 before `$2000`.

Native entry captures distinguish the first two scripted scenes. Index
`$3e` uses a text screen at `$4800`, sprite 0, wait `$28cc`, and exits at
`$28d1` through `$0403`, requesting `$3f`. Index `$3f` waits at `$2832`,
uses state-machine dispatch `$292d`, and exits through `$2835` to `$0406`,
requesting `$42`. Its visible sprite setup routines place groups at Y=29
or Y=250, with pointers `$10..$17` or `$17..$1e` in `$43f8..$43ff`.
Those groups do not yet establish the illustrated consecutive-sprite
handover. The producer retains both code listings and full captured-RAM
identities to avoid treating an early text/logo scene as the target artwork.

The following `$42` scene has ten sprite rows, Y=58+21r and pointer-table
values `$44+8r`, r=0..9. Its IRQ at `$2959` writes the next Y group and
pointer group together, then schedules the next interrupt. That is useful
consecutive-row code, but it does not contain the required separate
old/intermediate/new pointer publication. Its exit at `$28ea` goes through
`$040f` and requests `$40`.

One early file named `ram-scene-42-entry.bin` was saved while still at the
`$3f` wait `$2832`, after a rejected checkpoint deletion. It is retained as
rejected evidence. Only `ram-scene-42-entry-valid.bin`, saved at the actual
next `$2800` stop after the observed A=`$42` load request, enters the survey.
The producer reads original-PC/clock context from the saved monitor log and
asserts the expected PC for every native comparison; filenames alone cannot
establish the scene.

## Released sprite data: eleven new rows, ten old rows

Index `$40` exits through `$0409`, requesting **`$41`**. That next scene
contains the dense sprite and bank-switching kernel sought here. Its native
entry is bound to the original A=`$41` request at clock **136,444,385** and
the subsequent natural `$2800` stop at **139,667,377**, raster **182/31**.
The complete 65,536-byte entry RAM has SHA-256
`9166711ee41e411ee50191f123868db00f2e10f775af545343ccb4029fe55754`.

For hardware sprite 0 in VIC bank `$4000`, the executed code's static
publication sequence identifies old pointer `$2d`, intermediate `$35` and
successor `$3d`, with consecutive Y positions **124 and 145**. Their
pixel data are at `$4b40`, `$4d40` and `$4f40`. The 63-byte comparison gives:

```text
intermediate[0:33]  == successor[0:33]
intermediate[33:63] == old[33:63]
```

Both halves contain varied, nonzero image data. All eight pointer triples
`($2d+s, $35+s, $3d+s)`, s=0..7, satisfy this same relationship. The released
example therefore uses **11 new rows and 10 old rows**, whereas the PDF's
simplified illustration uses 10 and 11. For sprite 0, imposing the literal
PDF split at byte 30 produces three mismatches, exactly bytes **30, 31 and
32**. Seven of eight triples reject that split; sprite 4 also matches there
because its repeated bytes straddle the split. This is a concrete prepared
intermediate-image result, not confirmation that the printed simplified
30/33-byte layout is the release's universal layout.

| Sprite 0 image | Pointer | SHA-256 of its 63 pixel bytes |
| --- | --- | --- |
| Old | `$2d` | `ddb65175ef91ee40d1013ed92da644d2f7b306c12b27dbc9c2214f2008f3a68f` |
| Intermediate | `$35` | `9f3d87a91db2ecc30b4d06887e8f168520d2ed8b6e59cdaf425d9f44e48fec4b` |
| Successor | `$3d` | `d46e2c1341c7c975e61ad1d92d7758c69a7f91ac23cf97bc5f722bb32a7952c1` |

These exact original-code anchors make the remaining native observation
bounded. Shared `$3279` writes sprite Y; shared `$3239` publishes pointers
through `$43f8..$43ff`:

| Programmed IRQ line | Handler | Operation/call site |
| --- | --- | --- |
| 114 | `$2935` | Set Y=124 through `JSR $3279` at `$30fb`. |
| 122 | `$2944` | Publish pointers `$2d..$34` through `JSR $3239` at `$3150`. |
| 136 | `$2953` | Set next Y=145 at `$3156`, publish `$35..$3c` at `$315b`. |
| 144 | `$2962` | Publish `$3d..$44` through the call at `$319e`. |

These are **programmed IRQ lines and static call sites**. They are not
measured completed-store or DMA-fetch times. The earlier `$10/$1b/$20`
transition also has a byte-33 split, but its new head is entirely zero, so
it is retained only as an auxiliary lead rather than the main data proof.

## Native pointer/Y publication and DMA witnesses

The retained original `scene-41-entry.vsf`, SHA-256
`96f34d4beaec41de6f997aac42f8dcbc5e758fe3564c11c6c323c6a954bc1a3e`,
was restored once for `native-02`. Full MAINCPU, physical RAM and CIA payloads,
plus VIC registers and beam position, matched the parent before natural
execution continued. The completed observations use speed 100 with warp off;
no PC redirection or program/data injection was used.

Completed sprite 0 stores in bank `$4000` occurred at these observed
positions. **Cycle numbers here and below are zero-based monitor/VSF values**,
unlike one-based PAL cycle labels in hardware descriptions:

| Operation | Actual raster/cycle | CPU clock |
| --- | --- | --- |
| Prepare Y=124, `$3279` → `$d001` | 115/18 | 148,999,743 |
| Publish old pointer `$2d`, `$3239` → `$43f8` | 124/42 | 149,000,334 |
| Prepare next Y=145 | 137/15 | 149,001,126 |
| Publish intermediate `$35` | 138/15 | 149,001,189 |
| Publish complete successor `$3d` | 147/43 | 149,001,784 |

The second checked group occupies bank `$8000`, pointers
`($10+s, $18+s, $20+s)`, s=0..7, with Y registers **229 and 250**. All
eight also satisfy the exact 33/30-byte composite. Its observed original
publication sequence prepares `$10` in `$83f8` at 212/15, sets Y=229 at
228/21, switches CIA2 to bank `$8000` at 229/23, sets Y=250 at 230/45,
then publishes `$18` at 241/15 and `$20` at 254/39. These observations are
from the following field in the same uninterrupted original execution.

Saved same-stop VSF states expose the VIC's actual latched pointer, MC/MCBASE
counters, three-byte sprite data, DMA/display bits and register values. The
audited VICE 3.10 snapshot reader and
[official VICE source](https://sourceforge.net/projects/vice-emu/files/releases/vice-3.10.tar.gz/)
bind those fields and PAL fetch phases. Each listed completed-fetch sample
agrees with the original RAM bytes at `bank + pointer*64 + (MC-3)`:

| Bank | Observation | Raster/cycle | Latched pointer | Byte offset | Latched bytes |
| --- | --- | --- | --- | --- | --- |
| `$4000` | Old tail before intermediate publication | 138/11 | `$2d` | 39 | `04 a6 59` |
| `$4000` | Intermediate still fetching old tail | 139/13 | `$35` | 42 | `11 a6 d3` |
| `$4000` | Intermediate fetching successor head | 147/39 | `$35` | 3 | `00 03 4b` |
| `$4000` | Complete successor head | 148/40 | `$3d` | 6 | `00 12 a9` |
| `$4000` | Complete successor tail | 158/11 | `$3d` | 36 | `00 04 98` |
| `$8000` | Intermediate still fetching old tail | 242/13 | `$18` | 36 | `00 04 60` |
| `$8000` | Intermediate fetching successor head | 254/35 | `$18` | 9 | `aa aa aa` |
| `$8000` | Complete successor head | 255/37 | `$20` | 12 | `00 a2 aa` |

The old-tail and new-head samples each distinguish the relevant full image
from its neighbor; they are not accepted solely because a pointer value or
repeated/zero bytes match. DMA and display are active, Y expansion is off,
and each full 65,536-byte RAM capture equals its same-stop VSF physical RAM.
The handover kernels `$3000..$3404` and all 24 relevant 63-byte sprite slots
per bank remain identical to the original `$41` entry. In particular, the
first intermediate-tail witness already has next Y=145 while its old-row
counter continues, followed by an intermediate-head witness after retrigger.

The snapshot's VIC model is **MOS8565 PAL**, VICE model 1. In bank `$8000`,
sprite 0 is hires at the 242/13 sample and multicolor at 254/35 and 255/37:
the original lower-border routine changes `$d01c` to `$e7`. The claim here
is about fetched bytes and handover state; no independent pixel, border,
priority, or final-image reconstruction is claimed. The retained first-field
screenshot captures an initial transition and is not whole-picture proof.

An optional additional bank `$8000` successor-tail observation at raster 267
did not complete: the main-loop-only checkpoint returned no prompt, so no
such RAM/VSF files exist. The completed bank `$8000` successor witness stops
at **255/37, PC `$3278`, clock 149,028,238**. The wrapper ended before its
cleanup handler; `owner-cleanup.json` separately records verified termination
of the exact owned VICE process. `uncompleted-tail-observation.json` preserves
the unsuccessful observation without treating it as a final-state capture.
There was no restart to manufacture the missing observation.

## Boundary of the comparison with the author's example

In the author's simplified example, the current unexpanded sprite starts at
Y=100 and the successor at Y=121. During the current image, Y can be prepared
from its second line. From raster 110 a pointer can select a prepared image
whose bytes **0–29 equal the successor's head** and **30–62 equal the
current image's tail**. A subsequent pointer selects the complete successor.
There are three bytes per pixel row, so the split is ten new rows and eleven
old rows. The 64th slot byte is outside the 63 pixel bytes and must not be
included in the comparison.

The retained case now checks nontrivial image halves, bound banks and pointer
tables, ordered original pointer/Y writes, and native DMA latches spanning
the handovers. It does not establish that all artwork rows use the same split
or that the author has a nine-line worst-case scheduling window. That latter
allowance remains an author claim rather than a measured budget here.

## Reproduction and limits

The tracked producer is
[`research/dragonbond/inspect_original.py`](../../research/dragonbond/inspect_original.py).
It reads the saved originals under ignored
`build/research/frontier-20261108/` and emits ignored evidence under
`build/research/dragonbond/original-analysis/`. It uses Python and py65;
the already retained local environment can run it with:

```sh
rtk proxy build/research/tower-power/cpu-venv/bin/python research/dragonbond/inspect_original.py
```

To include the closed native handover observations in the same offline run:

```sh
rtk proxy build/research/tower-power/cpu-venv/bin/python research/dragonbond/inspect_original.py --handover build/research/dragonbond/native-02
```

The JSON receipt records source and producer hashes, exact depacker output
stores, all executed PC counts, known-byte ranges, native comparisons when
the corresponding saved captures exist, and extracted loader bodies.
`native-handover.json` additionally records all eight completed native DMA
witnesses, original-kernel/pixel checks, both ordered store traces, all 16
checked composite triples, exact source guards and the absent optional tail.
Disassembly listings are linear and can include embedded data; py65's
`???` rendering of an undocumented opcode is not evidence of a damaged
program. No external C64 program was converted into or executed as a host
tool. The producer starts no VICE/drive process. Its CPU model stops before
hardware initialization; the bounded native DMA results come only from the
retained snapshots and monitor events. No cycle-budget, scanout, physical-chip
or whole-demo-success claim is made.
