# The Lab: native multicolor vectors with prepared edge streams

The speech-balloon polygon stage has now been reached through the original
side-two program. Its active engine redraws **prepared projected edges and
color commands**, then runs a vertical XOR-prefix fill into a multicolor bitmap.
Native captures now match both the many-panel “TEN!” stage and the user's
specific open-panel “AND NOW?” scene. The latter uses a bounded palette trick:
two bitmap selectors share one color, so XOR of two coverage layers can give
one layer opaque priority. This is distinct from a general runtime depth sort.

This is a different code path from the [patterned span candidate](the-lab-binary.md).
It must also remain separate from Brush's author statement about his border
vectors being computed rather than animation playback. MMS's own note describes
his separate ambition to exceed three vector colors; the recovered note and
release attribution are documented in [The Lab overview](the-lab.md).
[Original release and extras note](https://csdb.dk/release/?id=262146)

## Native identification and actual VIC mode

The owned PAL VICE run used the released side-two bootstrap and disk with no
PC changes, payload substitution, or mocked loader. Warp advanced preceding
parts and was disabled at the original `$2A05 JSR $3420`. All 17,630 bytes
written by custom file 15 matched at that pre-initialization stop. The run then
continued into the later speech-balloon part; file 15 was no longer active.

At the later stop inside `$800C`, native RAM matched the file-20 engine and
file-22 script/edge assets. The released file-22 payload has only 14 changed
bytes in its mutable palette at `$9017–$9025`; its complete edge stream is
unchanged. The frame-complete capture stops **before `$2265 INC $44`**, at raster
153, native stopwatch 237,631,023. Its RAM SHA-256 is
`d8aac0f083581c4c616d9c85fd2f3d4b12107e9ec2942dd1b7ffc19136150bbc`.

Native I/O reads at multiple raster positions, including this completed pass,
give `$D011=$3B`, `$D016=$D8`, `$D018=$79` and `$DD00=$C0`, with background color
zero. These establish multicolor bitmap mode in VIC bank `$C000`, bitmap
`$E000`, screen `$DC00`. `$D018` bit 0 is unused; code writes `$78`, readback is
`$79`. The source IRQ alternates this with bank `$4000`, bitmap `$4000`, screen
`$6000`. At the completed capture `$43=0`, the prepared backbuffer is `$4000`
while the displayed front buffer remains `$E000`.

This mode uses the ordinary bitmap selection rules and per-character screen
nibbles/color RAM; it is not a mode with sixteen independent colors in every
pixel cell. The screen-wide set can use the C64 palette while each 8×8 physical
cell selects the background and three local colors.
[Commodore VIC-II documentation](https://www.zimmers.net/anonftp/pub/cbm/documents/chipdata/6567_vicII_preliminary.pdf)

The native evidence is saved under `build/research/the-lab/side2-live-01/`:
`native-observations.json`, the original monitor transcript and launch metadata,
`mms-frame-complete.png`, the RAM capture, a restorable VSF, and a separate
1,024-byte I/O color-RAM readback. The low-nibble color-RAM hash is
`5904a05d421abc44cf4ca00e5f5595acd7cad37c3cf4d59a6034a8488902e8b0`.
Underlying `$D000–$DFFF` RAM contains working data; it must not be mistaken for
VIC registers or actual color RAM.

## Prepared vector input, rather than bitmap frames

File 22 supplies **56 edge frames**, with 33–47 commands per frame and **2,173
commands** in total. The 13,094 bytes at `$9026–$C34B` match native RAM exactly;
SHA-256 `8b4c67a6300951f8fd15ead592b16021892da8f9bdd19e1a60437616d54fdda5`.
An `$FF` separates frames, and an empty `$FF` frame terminates the stream.
The native consumer resets to the stream's saved start when it reaches that
final marker; a scripted render count can therefore cycle the same poses.

Each six-byte command contains:

| Byte | Meaning established by the consumer |
| --- | --- |
| 0 | Start X in low seven bits; one bit of the bitmap transition code. |
| 1 | End X in low seven bits; the other transition-code bit. |
| 2–3 | Fractional/integer slope bytes used by the ADC stepping kernel. |
| 4 | Starting Y. |
| 5 | Attribute operation in the upper bits, palette index in the low nibble. |

X is sampled over a half-open interval, from the mapped start through one
before the mapped end. Vertical edges with equal mapped X are skipped. Raw X
indices are 0–95 and raw Y is 0–191. Runtime scale tables and translation offsets
map them to the drawing coordinates. The line kernel preserves carry from the
row addition into the next fractional addition; treating a negative slope as
an ordinary independent signed 16-bit add changes its pixel placement.

These records already contain projected endpoints, slopes, transition codes
and attribute instructions. They contain no 3D vertex, normal, face-depth or
visibility fields. The inspected frame consumer performs scale/translation,
edge sampling, attribute construction and filling. This establishes prepared
vector-command playback for these assets, while still doing the rasterization
on the C64. It does not show playback of complete bitmap frames, and it does
not demonstrate a live 3D transform or generic depth sort.

The data inventory includes these additional streams:

| File | Stream, inclusive | Frames | Edge commands | Commands per frame |
| --- | --- | ---: | ---: | ---: |
| 21 | `$8D32–$98B2` | 64 | 480 | 4–9 |
| 21 | `$98B3–$9AF7` | 4 | 96 | 24 |
| 21 | `$9AF8–$BEFC` | 64 | 1,526 | 23–24 |
| 22 | `$9026–$C34B` | 56 | 2,173 | 33–47 |
| 23 | `$8D02–$C326` | 48 | 2,302 | 38–54 |

The depacker can finish with an unchanged in-place tail already at its output
address. For example, file 23's logical end is `$C327`, while its last observed
depacker store ends at `$C320`; the final seven loaded tail bytes are still part
of the stream. File 20's generator likewise uses its eleven-byte in-place tail
at `$9030–$903A`. Store-range receipts deliberately describe observed writes,
not the full logical contents including these unchanged loaded tails.

## XOR markers, generated filler, and expanded colors

The transition code is formed from the two high X bits:

```text
code = 2 * bit7(startX) + bit7(endX)
marker[(X // 4) * 192 + Y] ^= code << (6 - 2 * (X % 4))
```

The marker buffer starts at `$C800` and contains 24 columns × 192 rows, or
4,608 bytes. Each byte contains four multicolor lanes. The corresponding bitmap
window is 192 physical pixels wide by 192 rows, with 96 horizontal multicolor
samples, inside the ordinary 320-pixel bitmap. Bitmap destinations begin at
offset `$40`, equivalent to an eight-character horizontal offset.

The original initializer `$8FE8` generates 2,304 bytes at `$7A46–$8345`: 192
six-byte cells for each bitmap bank. Each cell performs `EOR ($45),Y`, an
absolute-X store, and `INY`. The destination follows:

```text
bank + $40 + (row // 8) * 320 + (row % 8) + X
```

The running program patches an endpoint to `RTS` and restores it after each
bounded column pass. During the earlier mid-fill capture only `$8345` differs
from the generated bytes; at the complete capture every generated byte matches.
The nominal cell is 12 cycles, plus an indirect-indexed read page-crossing cycle
where applicable. This excludes column dispatch, patching and restoration,
attribute work, line setup, interrupts and VIC bus contention.

The low-nibble material index also drives per-character color information.
The consumer has separate operations for screen-color nibbles and a color-RAM
shadow; the IRQ copies color data while switching the display bank. It does
more than reinterpret one globally fixed set of three non-background colors.
The captured palette table contains all sixteen C64 color indices. Detailed
proof of every attribute propagation case is outside the marker/bitmap tests
below, so the bitmap proof alone must not be described as a complete sixteen-
color screen oracle.

## Independent original-CPU and native byte checks

`research/the-lab/mms_inventory.py` reproduces these checks with py65 1.2.0:

```sh
rtk proxy build/research/tower-power/cpu-venv/bin/python research/the-lab/mms_inventory.py
```

- The original generator executes **14,182 instructions**. Its complete output
  matches an independent address/template formula and all 2,304 native code
  bytes at the completed capture.
- The original edge consumer executes **505,902 instructions** across all 56
  released file-22 frames at the captured scale and zero translation. Every
  marker byte matches an independent integer carry-chain/bit-lane reference.
- The completed native frame is stream index **52**, starting at `$BFE8` with
  **34 commands**. All **4,608 native marker bytes** match that independent
  reference.
- Re-executing its original bitmap-fill entry `$2662` takes **9,802 instructions**
  and emits **3,040 bitmap stores**. Every store equals both the mathematical
  vertical prefix and the completed native backbuffer byte. No actual bitmap
  store is excluded. Unwritten image/background outside the original dirty
  ranges is preserved rather than incorrectly expected to be black.

The output receipt is `build/research/the-lab/mms-analysis/inventory.json`.
Focused original-code listings remain ignored beside it. The isolated CPU
checks use flat all-RAM API contexts without disk, VIC or IRQ emulation; native
execution and captured device state provide the separate hardware evidence.
The all-frame check covers bitmap markers at one captured scale, not every
scale/translation, color-attribute case, scene pose or presentation deadline.

## The specific open-cube image and occlusion

The literal speech **“AND NOW ?”** is present in file 21 at `$8CB9`, immediately
after its `$8CB6 JSR $3D84` speech call. The script has switched to the third
stream at `$9AF8` and made nine frame calls before printing it. Earlier text
includes the open-sesame prompt. This is a substantially stronger match to the
user's image than identifying a later many-panel object by visual style alone.
Its 23–24 boundaries per pose are consistent with six quadrilateral panels
with occasional vertical edges omitted, but that count alone is not a proof of
the original mesh connectivity or winding policy.

The original first call at `$2109` has now been replayed. All 13,053 file-21
output bytes match the native entry RAM. Execution stopped at the original
speech call, resumed through the speech routine, then reached the next original
`$2265` completed-render checkpoint. The resulting
`side2-targeted-02/mms-open-cube-native.png` shows the separated colored panels
with “AND NOW?”. The RAM is `ram-open-cube-frame.bin`, SHA-256
`800c5a0157d11b8a013cf8dd387f5b58d48a2ff38246a9bd623f46216a763cc7`.
No PC, input or payload patch was used to select the scene.

At this checkpoint `$3E/$3F=$9FFF` means **third-stream pose 9 is the completed
backbuffer**, not the displayed pose. `$43=1,$44=0` selects displayed bitmap
`$4000` and completed pending bitmap `$E000`, before its display request. The
same input pointer was present immediately after speech because it already
identified the *next* input. Independently rendering candidate poses 7, 8 and 9
identifies the displayed pose as **8**: all 8,069 covered samples agree there;
the other candidates differ at 3,547 and 3,605 covered samples. That comparison
checks covered bitmap samples, not a complete front-buffer color oracle.

`research/the-lab/mms_open_cube.py` parses the unchanged third stream and
reproduces the pending pose 9 from its **24 commands and 538 X samples**. All
**4,608 native marker bytes** agree with independent carry-chain stepping.
Executing original `$260B` takes 11,579 instructions and emits **3,600 bitmap
stores**; every store agrees with both independent vertical-prefix math and
the native completed backbuffer. Replaying the original edge and attribute
code additionally matches all 576 pending Color RAM-shadow bytes and 484
back-screen stores. These attribute checks are original-code replay, not a
separate per-panel color/depth oracle. The later Color RAM copy is inspected
and executed offline, but is not claimed as a native post-swap Color RAM check.

## Aliased selectors give bounded opaque priority

The open-panel script sets `$47=1`. In the attribute consumer this duplicates
each screen color into both nibbles: bitmap codes `01` and `10` consequently
select the **same** color in that character cell. Code `11` takes the other
color from Color RAM; `00` remains the black background.

The captured pose has eight edges with delta 1 and sixteen with delta 3. Split
their prefixes into binary coverage masks A and B. Their aggregate bitmap code
is `A XOR (3*B)`:

| A | B | Bitmap code | Displayed choice |
| ---: | ---: | --- | --- |
| 0 | 0 | `00` | Black outside. |
| 1 | 0 | `01` | A color. |
| 0 | 1 | `11` | B color. |
| 1 | 1 | `10` | A color, because `10` aliases `01`. |

Thus A has opaque priority over B even though the marker arithmetic remains
commutative. The capture contains 1,850 A-only, 1,915 B-only and **3,678 overlap
samples**. All 294 native screen cells touched by these masks have equal color
nibbles; A samples select yellow 7 or blue 6. B-side attribute commands select
light green 13, light gray 15, light red 10 and purple 4. Those commands and palette aliasing
explain how several colored panels can coexist with opaque-looking overlap.

This proof establishes **priority A/B**, not that A is globally nearer in 3D.
The input has no depths or panel IDs from which to prove that stronger claim.
The producer must choose suitable layer membership, visible boundaries and
per-cell color assignments. Multiple same-layer coverings would XOR-cancel,
so the useful opaque interpretation requires at most one covering region per
layer at a sample, and enough local palette capacity for the chosen colors.
Arbitrary independently intersecting panels are not covered by this argument.

There is a compatible two-tone character-mode variant: seed outside code `11`,
keep delta A=1 and B=3, put black in Color RAM, put B in `$D021`, and alias
`$D022/$D023` to A. The four output codes become `11,10,00,01`, again giving A
priority with one prefix pass. It combines with [N2's outside-code choice](tower-power-n2-palette.md).
It supplies two global layer tones; reproducing the native bitmap's varying
panel colors needs additional attribute/palette handling.

Opaque black stipple samples in A need further care: omitting A's delta exposes
B, rather than covering it with black. B can stipple against empty black when
there is no rear layer; arbitrary opaque pattern colors in A need resolved
coverage or another compositing mechanism. This is a bounded palette technique,
not unrestricted transparency or texturing. The [panel compatibility note](open-panels.md)
and [interlaced dither note](interlaced-dither.md) distinguish these cases.

The reproducible receipt is
`build/research/the-lab/mms-open-cube-analysis/proof.json`. It also checks both
outside-code truth tables and the opaque-black counterexample. Run:

```sh
rtk proxy build/research/tower-power/cpu-venv/bin/python research/the-lab/mms_open_cube.py
```

The transferable pieces are generated bounded prefix code, half-open edge
sampling, separate attributes, and this restricted palette-priority algebra.
General 3D visibility is not solved by reordering XOR edge calls.

To replay the exact candidate through original code, stop at `$2109 JSR $8C00`,
the first script call in the file-20 engine. File 21's first 24 entry bytes are:

```text
A9 32 85 3E 85 40 A9 8D 85 3F 85 41 A9 00 85 4A A9 00 85 47 A9 23 85 5A
```

File 22 uses the later `$2118` call; file 23 uses `$2127`. The common engine's
`$2265` stop is render completion/request for display, while `$21A9` is in the
IRQ after the bitmap-bank update. These distinct points avoid treating a
completed backbuffer as though it had already appeared on screen.
