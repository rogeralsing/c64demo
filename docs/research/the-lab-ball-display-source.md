# The Lab ball: source order from rendered backbuffer to display selection

Research date: 9 November 2026. The original file20 source queues a completed
backbuffer, switches the VIC bank and `$D018`, then copies a shared Color RAM
shadow. **`$21A9` is post-bank-selection but before the Color RAM copy.** It is
not a complete color-publication or committed-scanout boundary. `$21AC`, after
the copy returns and before request decrement, is the stronger color endpoint.

The new [passive source reader](../../research/the-lab/ball_display_source.py)
recognizes original instructions, pointer tables and all 484 copy cells. It
imports the pinned existing static decoder; it executes no C64 instructions,
CPU interpreter, native process, renderer, socket or build. Its inputs are
original decoded file20/file22, file20's written mask and retained official
VICE source. Native marker/bitmap/attribute/color outputs are not inputs.
The [ball identification](the-lab-ball.md) and [earlier MMS note](the-lab-mms.md)
retain the separate source, native and legacy CPU evidence.

## The normal queued-publication protocol

The full render body starts at **`$21BD`**, before scale/translation updates,
edge sampling and attribute construction. File22's original first call is
**`$8C44 JSR $21BD`**, returning to `$8C47`; its script begins at `$8C00` and
selects stream `$9026` and palette `$9016`. File20 calls that script at
`$2118 JSR $8C00`, after `$2116 DEC $01`, then restores with `$211B INC $01`.
The usual inherited port `$35` therefore becomes all-RAM `$34` for the script;
actual CPU DDR/mapping must be bound separately.

The render body calls the edge/attribute consumer at `$221C`. Only afterward
it waits on `$44` at `$224E`. With the previous request consumed, it chooses
the backbuffer from current `$43`, calls the bitmap filler and screen-attribute
propagator, then reaches `$2265 INC $44`. The normal request goes 0→1, after
the completed backbuffer. The following `$2267` starts marker erasure/input
advance. Consequently a later `$3E/$3F` pointer is not, by itself, the identity
of the just-published picture. Capture the completed generation before INC44.

The IRQ entry is `$216D`. It saves A/X/Y and CPU `$01`, writes `$01=$35` to
make I/O visible, and calls external `$0432`. At `$2185` it tests `$44`:

1. Zero branches directly to `$21AE`; there is no selector toggle or color
   copy on that path.
2. Nonzero loads `$43`, XORs 1, stores the new selector, and transfers it to X.
3. It writes **CIA2 `$DD00` first**, then **VIC `$D018`**.
4. Both paths meet at `$21A9 JSR $26B9` for the Color RAM copy.
5. `$21AC DEC $44` consumes the request after normal copy return.
6. `$21AE JSR $83E8` runs the speech/font tail, then `$21B1 INC $D019`
   acknowledges VIC IRQ; the wrapper restores CPU `$01` and registers.

Initialization requests raster250 using `$D012=$FA` and compare bit8 zero.
Later init writes `$D011=$3B` and sets `$D016` multicolor bit4. This is the
source's intended schedule/mode, not a measurement of the actual entry beam
or the current cached display state. External `$0432`, later overlays, NMI,
VIC contention and hardware pipeline timing are not evaluated by this reader.

## Which bitmap and screen become front

The following logical addresses require ordinary multicolor-bitmap mode and
CIA2 effective low bank pins matching the writes. The original file20 path
does not establish CIA2 DDR here; capture PRA, DDRA and effective readback.
CPU `$00` must likewise drive the `$01` mapping bits. Hardware readbacks such
as `$D018=$79` include unused bits; decode selector bits rather than treating
the whole readback as a written value.

| `$43` during rendering | Existing front | Rendered backbuffer | Original bitmap/screen calls | New `$43` | Selection at `$21A9` |
| ---: | --- | --- | --- | ---: | --- |
|0 | bitmap `$E000`, screen `$DC00` in bank `$C000` | bitmap `$4000`, screen `$6000` | `$2662` / `$6F27` |1 | `$DD00=2`, `$D018=$80`: bitmap `$4000`, screen `$6000` |
|1 | bitmap `$4000`, screen `$6000` in bank `$4000` | bitmap `$E000`, screen `$DC00` | `$260B` / `$6EE8` |0 | `$DD00=0`, `$D018=$78`: bitmap `$E000`, screen `$DC00` |

This binding uses original generator template `EOR ($45),Y; STA absolute,X;
INY`, its first `$E040` destination, and the source patch selecting `$4040`
for the second 192-row pass. Original start tables select generated entries
`$7A46` for `$E000` and `$7EC6` for `$4000`. Neither generated native filler
bytes nor an expected rendered buffer supplies this source contract.

Both screen wrappers' original pointer/end tables select 484 indexed screen
store sites over the same cropped cell set. Their source column loop runs
X=23 down to 0. Their destinations are `$DC00 + 40*row + column` or
`$6000 + 40*row + column`, where physical screen columns are 8..31. This reader
checks address footprints, not the separate nibble/event arithmetic.

Because the bank write comes first, the two register updates are not atomic:

| Transition | After `$DD00`, with old `$D018` still active | After new `$D018` |
| --- | --- | --- |
| `$C000`→`$4000`, old `$78` | logical bitmap `$6000`, screen `$5C00` | bitmap `$4000`, screen `$6000` |
| `$4000`→`$C000`, old `$80` | logical bitmap `$C000`, screen `$E000` | bitmap `$E000`, screen `$DC00` |

These are selector-address consequences, not a claim that those transient
addresses are fetched into visible pixels. The pinned official source keeps
bank/GLUE state and VIC phi1/phi2/cache behavior separate. Matrix fetches cache
screen and Color RAM bytes; changing registers or Color RAM does not prove
that every already-fetched row immediately adopts them.

## The exact shared Color RAM copy

`$26B9..$3D83` is 5,835 source bytes, ending with RTS. The recognizer consumes
24 explicit TYA column resets and 484 exact 12-byte cells. Every cell has:

```text
LDX shadow
BEQ store
TXA
STY shadow       ; Y was forced 0, so consume a nonzero event
store: STA ColorRAM
```

A starts 0 in every column. Zero shadow entries retain the previous A;
nonzero entries replace A and are cleared. Every visited cell executes its
Color RAM STA. The stored device value is A&15. It is a vertical last-nonzero
color propagation, distinct from the bitmap's XOR-prefix arithmetic.

The independent source map is:

```text
shadow source = $C500 + 24*screenColumn + screenRow
Color RAM     = $D800 + 40*screenRow + screenColumn
```

The logical 24×24 shadow window is `$C5C0..$C7FF`. Only484 shaped cells are
visited; 92 shadow slots and all Color RAM locations outside that crop are
untouched by this function. There are not 576 Color RAM stores.

| Screen columns | Rows, inclusive | Cells per column |
| --- | --- | ---: |
|8 and31 |7..16 |10 |
|9 and30 |5..18 |14 |
|10 and29 |4..19 |16 |
|11 and28 |3..20 |18 |
|12 and27 |2..21 |20 |
|13,14,25,26 |1..22 |22 |
|15..24 |0..23 |24 |

Copy order is columns 8→31, top→bottom within each listed interval. The exact
484 addresses and instruction PCs are in `color-copy-map.json`. There are
2,446 linear instruction sites, while the normal executed count is
`1478 + 2*nonzeroEvents`, depending on data. This is a static count, not a CPU
run or fixed cycle budget; callback time, badlines, DMA and bus effects remain.

Normal completion leaves all 484 visited shadow cells zero: an initial zero
remains zero; any nonzero value executes STY0. This is an **immediate local
postcondition**, not a universal later-frame initial-state theorem. In
particular, `$221C` edge/attribute construction precedes the `$224E` request
wait. Source alone does not rule out an arbitrary previous-request/event race.
Using the zero postcondition at a later render entry requires no intervening
writer, or an independently captured genuine pre-body state. Current event
outputs must not be used as that initial state.

The font tail `$83E8..$8418` does not write palette `$9016`: it updates
`$5C/$5D/$5E`, reads through `$5A/$5B`, and copies 16 glyph bytes from `$6700+X`
to `$E890+Y` and `$4890+Y`. It runs after the request clears, and may therefore
change bitmap pixels in both banks after the postcopy checkpoint. This claim
is limited to that guarded tail; the external `$0432` callback is separate.

## Bitmap writes use dynamic bounds inside the fixed crop

The 484-cell screen/ColorRAM crop is **not** the actual bitmap-store domain.
The bitmap wrappers use runtime columns `[53,54)` and, per column, rows
`[8*max(fixedTop[column],55),fixedBottomPixel[column])`. The static pointer
tables agree in both generated banks. The stop patch replaces the last row's
INY **after** its EOR/STA, so that last pixel row is written.

Source reduction sets 53=floor(minMappedStartX/4), 54=ceil(maxMappedExclusiveEndX/4)
and 55=max(floor(minimumSourceY/8)−1,0). The source Y minimum is updated from
each processed nonzero-width edge's mapped startY and post-kernel finalY.
It must not be inferred only from nonzero XOR markers, which can cancel.
Every byte outside those runtime spans keeps its genuine pre-body bitmap value.

The separate [fill coverage descriptor](../../build/research/lab-polygons-20261109/display-source-analysis/fill-coverage-01/fill-coverage.json)
and [guarded source proof](../../build/research/lab-polygons-20261109/display-source-analysis/fill-coverage-01/fill-coverage-proof.json)
expose both table families and a pure `bounds_from_extrema` / `coverage` API.
The full fixed-crop maximum is 3,872 bitmap bytes, not a claim of 3,872 executed
stores. A scalar full-crop prefix replacement might happen to give the same
image in a particular case, but must independently verify that every replaced
outside-dirty byte already equals the prefix; source does not imply it.
This follow-up reads only original file20 and never a native bitmap or the
legacy 3,040-store count as an input. Its three outputs replay exactly.

## Practical anchors for a fresh natural run

The [capture plan](../../build/research/lab-polygons-20261109/display-source-analysis/accepted-01/capture-plan.json)
includes exact roles. Guard both file20 and file22 generations, then use:

- `$2118` and `$8C00`: original first file22 call/script entry.
- `$8C44` or `$21BD`: full render start before scale, edges and events.
- `$224E`: isolate previous-request wait/fill from the full render interval.
- `$2265` then `$2267`: completed backbuffer and queued request generation.
- `$2185`, conditional on pending `$44=1`: publication IRQ after callback.
- `$2190`: new selector stored/X loaded, before the hardware selects.
- `$21A9`: both selects written, Color RAM copy not started.
- `$26B9` / `$3D83`: full copy entry and completion before RTS.
- `$21AC` / `$21AE`: copy returned, then request consumed, before font tail.

Native evidence should retain CPU `$00/$01`, CIA2 PRA/DDRA/effective pins,
actual VIC mode/bank/mirrors, all 484 Color RAM writes and the postcopy low
nibbles. Underlying `$D800..$DBFF` RAM is not the Color RAM device. Preserve
full CPU/RAM/VSF/beam observations and actual wire ordering; do not equate a
monitor-dot address with CPU PC. Do not use a later input pointer or one
post-bank screenshot to name the completed/displayed pose. For a full render
cost use the true body entry, and label IRQ/wait/contention contributions;
`$224E→$2265` is only a subset.

## Replay and scope

The [accepted source proof](../../build/research/lab-polygons-20261109/display-source-analysis/accepted-01/display-source-proof.json)
is 9,947 bytes, SHA-256
`30431ebfbef385a2b05a9983b2ef0094005053563ae3d60da95ef9ef980712ed`.
The producer is 18,417 bytes, SHA-256
`f5e99a56a9d27787e4fae8e369470aede881373d704527e4b3a10c2cab50bbcd`.
A [fresh self replay](../../build/research/lab-polygons-20261109/display-source-analysis/self-replay-check.json)
matches all seven outputs / 913,443 bytes exactly. The report is 1,399 bytes,
SHA-256 `56a21ce1cea80393dc664abcf74d8413c9a6d490b3dfc1eed3da5b139bf35cf3`.
Root reviewed both complete producers and independently replayed all seven
main files / 913,443 bytes and all three fill-descriptor files / 15,031 bytes
exactly. The [main root report](../../build/research/lab-polygons-20261109/display-source-analysis/root-replay-check.json)
is 1,814 bytes, SHA-256
`824083bc43e3f51dc5bbef47a6c0e8215a74f3b75f5ce19fc906ac12d7e3c8b7`.
The [fill root report](../../build/research/lab-polygons-20261109/display-source-analysis/fill-root-replay-check.json)
is 1,187 bytes, SHA-256
`ee9034e030ee33906c16e256887e16d0a77453af4da307b091ee61ab3953e5cb`.
Candidate01 remains retained; the final source adds mode/continuation guards.

```sh
rtk proxy python3 -B research/the-lab/ball_display_source.py --output build/research/lab-polygons-20261109/display-source-analysis/<fresh-directory>
```

Original decoder output and its written mask are declared source artifacts;
this lane does not rerun the depacker or legacy CPU proofs. The original
initial generator also uses its retained in-place template tail. No native
post-swap equality, attribute-value proof, complete scanout, deadline,
whole-animation/FPS, physical-hardware or optimization result is added here.
