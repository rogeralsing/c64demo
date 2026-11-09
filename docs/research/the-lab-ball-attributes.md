# The Lab ball: independently reconstructed color attributes

Research date: 9 November 2026. A passive mathematical reference now
reproduces the ball's **entire pending 1,000-byte back-screen**, both
**576-byte attribute event planes**, and **1,422 bytes of attribute-code
state** from genuine pre-edge state. All **93 watched event stores**
also match source PC, address and independently observed CPU-A byte.
No original CPU instructions or emulator are executed by this producer.

This supplies the missing independent color stage alongside the
[prepared-edge/bitmap findings](the-lab-ball.md). The producer is
[ball_attributes.py](../../research/the-lab/ball_attributes.py).
The input geometry is prepared 2D edge data; this adds no live 3D projector
or general visibility algorithm.

## The actual accepted case

The fresh [native custody](the-lab-ball-native.md) has natural stops at
`$21BD` before the frame body, `$2209` before the first edge record and
`$2265` before `INC $44`. The accepted input is file-22 pose **52**, stream
pointer **$BFE8**, with **34 commands**, scale mode 20 and selector `$43=0`.
Both pre-edge 576-byte event planes are observed zero.

Its translations are **$FD/$EC**, meaning −3 multicolor X samples
(−6 physical pixels) and −20 scanlines. Its actual mutable palette is:

```text
0,1,14,1,4,1,1,1,1,1,10,11,1,13,1,1
```

The old `side2-live-01` pose-52 observation instead has zero translation and
the identity palette. It remains a separate **conditional** arithmetic
study because a true pre-edge state was not retained there. The new
acceptance uses the fresh partial palette and translated coordinates.
The rejected `fullcolor52-body-entry` export is excluded from every
prediction input and accepted phase predicate.

The frame selects the pending bitmap at $4000 and screen at **$6000**.
Consequently its screen-attribute wrapper is **$6F27**; `$6EE8` is the
sibling wrapper for the $DC00 screen. At $2265 the new color events remain
pending. Physical Color RAM publication is checked by the separate
[publication consumer](the-lab-ball-publication.md).

## What is original source and what is runtime input

Retained file-20 and file-22 decode images are padded 64-KiB host images.
Their original written ranges are only:

| File | Inclusive release-written range | Payload bytes |
|---|---|---:|
| 20 | $2000–$902F | 28,720 |
| 22 | $8C00–$C34B | 14,156 |

The producer pins each RAM image, PRG and 65,536-byte written mask, checks
their exact correspondence, and uses only source bytes inside those ranges.
Padding zeros at $C380 or $C5C0 are **not** treated as release-owned buffer
initialization. The new event-buffer zeros come from the accepted native
pre-edge state.

The whole stream is parsed as **56 prepared poses / 2,173 six-byte
commands**, but only pose 52's attributes receive this native acceptance.
The current runtime X/Y scale tables, mutable palette, prior back-screen
and event planes are declared pre-edge inputs. Rendered attributes and
observed store values enter only the comparator after prediction.

The record's sixth byte selects a palette index and an attribute operation:

| Operation bits | Resulting event |
|---|---|
| $10 | Replace the screen event's high nibble. |
| $20, or nonzero $00 form | Replace its low nibble. |
| $30 | Write a Color RAM-shadow event byte. |
| Entire byte zero | Skip attribute work for this boundary. |

The source's `$47` flag can duplicate a color into both screen nibbles.
It is zero in this accepted ball case. The separate open-cube aliasing
result is not silently promoted into this proof.

## Character-cell boundary sampling

The source maps each projected endpoint through the declared scale table
and performs an eight-bit translation addition. Four multicolor samples
span one 8-physical-pixel character column; eight scanlines span one
character row. The attribute span begins at `floor(left/4)` and ends at
`ceil(right/4)`, exclusive.

The mathematical reference follows **$2367–$2479/$250F** as a record-level
fixed-point construction:

- Negative slopes align using the left cell's remaining samples and carry
  1. Positive slopes seed alignment carry from bit 2 of the translated Y.
- Three logical shifts of the row/fraction pair convert scanlines to
  character rows. A signed slope half converts one-sample vertical change
  into one-character-column stepping in those units.
- Interior traversal receives the source CPX carry of zero. Negative
  last-column correction halves the slope twice more and begins subtraction
  with the final shift's carry, without an inserted SEC.

The first cell, interior cells and final partial cell retain their exact
source endpoint rules. The producer uses integer addition, subtraction
and arithmetic shifts over typed record fields; it contains no opcode
dispatcher, CPU stepper, stack execution or timing model.

For this translated pose, the 20 nonzero attribute commands produce
**40 screen-event stores and 17 shadow-event stores**. The latter touch
16 distinct slots. Those positions and bytes are calculated before any
native target or store hook is examined.

## Two event planes and a selective prefix

Both event planes are column-oriented, with 24 character columns and
24 rows:

```text
screen event = $C380 + 24*column + row
shadow event = $C5C0 + 24*column + row
```

Screen events merge high/low nibbles using `(old & keep_mask) | color_bits`.
Thus different commands can supply the two screen colors for one cell.
Shadow commands overwrite their event byte in source record order.

The screen propagator maintains one running screen byte per column. For a
nonzero event `e`, it computes:

```text
mask[e] = (low_nibble(e) != 0 ? $F0 : $FF)
        & (high_nibble(e) != 0 ? $0F : $FF)
state   = (state & mask[e]) | e
```

All **256 independently calculated masks** equal the original $3F00 table.
The consumed event is cleared, and the current state is written to the
back-screen. This attribute prefix holds/selectively replaces colors;
the separate bitmap prefix uses XOR.

**Zero is a hold sentinel.** A zero screen event retains the current
screen byte. In the later Color RAM copy, a zero shadow event likewise
retains the prior column accumulator; it is not an unconditional request
to switch an already colored column to black. The accepted stream and
bitmap background obey this constraint. No arbitrary palette-transition
or black-material guarantee follows from the event format.

The fixed original crop tables select **484 screen cells**. They are not
the current polygon's dirty bounds. The source writes:

```text
$6000 + 8 + 40*row + column
```

for columns 0–23 and their original shaped row intervals. The screen X
range is 8–31. Every column begins with state zero. The two 27-byte-per-row
unrolled propagators at $69D8 and $6C60, their row-entry tables and temporary
RTS endpoints are guarded against original file 20.
These attribute propagators are supplied code in file 20. The separate
2,304-byte bitmap filler is the runtime-generated code.

The reference also predicts persistent self-modification: eleven distinct
AND-table operand bytes are updated by the nonzero events, and the active
wrapper's final JSR target is derived from column zero's crop entry.
Applying those effects to the genuine prior code generation reproduces
all **1,422 bytes at $69D8–$6F65**. Temporary endpoint patches are restored
at completion. CPU scratch/stack writes and a full transient code-write
history are outside that endpoint claim.

## Independent native comparisons

The accepted result matches:

| Region | Calculated/preserved work | Full-byte comparison |
|---|---|---:|
| Pending back-screen | 484 calculated cells, 516 preserved prior cells | 1,000 bytes |
| Color RAM-shadow events | 17 writes to 16 slots, 560 preserved prior slots | 576 bytes |
| Screen events after propagation | 40 boundary writes to 36 slots, then 36 clears | 576 bytes |
| Attribute-code state | Predicted persistent operands; other prior bytes preserved | 1,422 bytes |

The event-buffer watch covers the 40 screen-boundary stores, 17 shadow
stores and 36 consumed-event clears. All **93 ordered source PCs,
addresses and raw CPU-A store values** match. The watched sequence is an
oracle: its values, addresses and count do not select the predicted cells
or control the mathematical traversal. No palette store occurs within
the accepted body window; the entry palette also equals the render-done
palette.

The [`$44` wait](the-lab-ball-display-source.md) occurs after edge/event
construction. Source `$44=0` alone is therefore not used as a universal
zero-input or race-freedom theorem. The genuine pre-edge snapshots verify
the initial event planes directly. This avoids both current-output seeding
and assumptions about every earlier scripted frame.

## Evidence and replay

The [native custody receipt](../../build/research/lab-polygons-20261109/native-analysis/accepted-01/ball-native-proof.json)
is 238,618 bytes, SHA-256
`123732a8293916ffc9648b51686eeff314f1d0a9b371756efaab975976d968e5`.
The [attribute receipt](../../build/research/lab-polygons-20261109/attribute-analysis/accepted-01/ball-attribute-proof.json)
is **25,177 bytes**, SHA-256
`f0f4fa7941b24e9d9a3d4fbea1d39cf7e59bc387f87f4fb3a49fe17791cacbb6`.
Producer: **24,133 bytes**, SHA-256
`dc22dd6ada807deaa44c8b7ff71cb90cb6835f8fc5969de097e7aa00d95df077`.

The accepted predicted [back-screen](../../build/research/lab-polygons-20261109/attribute-analysis/accepted-01/predicted-back-screen-6000.bin)
has SHA-256 `52ba4f16233a5275121dd5030cdb8d0cda59e5f066ac0ba3473a781a25abb11d`;
the predicted [shadow events](../../build/research/lab-polygons-20261109/attribute-analysis/accepted-01/predicted-color-shadow-c5c0.bin)
have SHA-256 `ed534f183fde711e92925800dab2f0f731f57e941d4fce9656c11a35b1e1a38c`.
These independently computed outputs are the inputs to the publication
and complete-color consumers.

```sh
rtk proxy python3 -B research/the-lab/ball_attributes.py \
  --output build/research/lab-polygons-20261109/attribute-analysis/fresh-replay
```

Self and independent root replays reproduce all **eight files / 128,203
bytes** exactly, without normalization. Root source review also passed.
The [root report](../../build/research/lab-polygons-20261109/attribute-analysis/root-replay-check.json)
is 2,042 bytes, SHA-256
`fbc40e2a84ad495f7f57b2e307f2b876ed1235767c6500d761d7db7555756b25`.
The [self report](../../build/research/lab-polygons-20261109/attribute-analysis/self-replay-check.json)
is 1,453 bytes, SHA-256
`250a12065008dd798743cdd6426112a6a85b81bffc3896479f13d2d41058482c`.

Retained diagnostics include the conditional old identity/zero-translation
study and the first fresh candidate's rejected zero-translation assumption.
The actual pre-edge bytes FD/EC were then passed through the existing
typed coordinate construction. No native retry, PC patch or change to
the original renderer repaired that host-side input assumption.

This acceptance covers one prepared pose at the captured scale and actual
translation/palette, plus the separate conditional legacy comparison.
It does not prove all 56 attribute results, arbitrary transforms, generic
3D visibility, a post-publication physical Color RAM state or complete
committed pixels by itself. Those later consumers retain separate proof
boundaries.
