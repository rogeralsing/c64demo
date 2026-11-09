# Edge of Disgrace: thirteen levels and thin tracing lines

Research date: 8 November 2026. Original side-1a candidates **51/52** contain
a shader-specific path, not merely another Gouraud-looking texture. The
code has a thirteen-level packed ramp, traces boundaries between adjacent
levels, and selects line routines that omit zero pattern sites. This
matches the specific mechanism described in HCL's
[original release note](eod-files.md).

The passive proof binds that source to the original loader's accepted
native captures, checks the horizontal occupancy of the selected paths,
and independently reproduces all 2,048 marker-buffer bytes after one thin
line. It does not establish a complete displayed image, independently
calculated lighting, or an exact speedup. The separate
[controller acceptance](eod-controller.md) owns the native wire and
RAM/VSF checks; file index alone does not identify an effect.

## Original-byte map and APIs

The pinned extraction inputs are:

| Candidate | Decoded data interval | PRG SHA-256 |
|---|---|---|
| 51 | `$0800..$30DC` | `e4899712681147b233a960d675aab369feebac4ba149073f1051d45f78b5312c` |
| 52 | `$30DD..$65FF` | `3adc5e1b6990cf41b3d93954de9d92bd3da62b4b562fc636cbd827cf94d67c04` |

These are contiguous program/data regions. Candidate 51 begins with tables,
not an entrypoint. Candidate 52's initial `$30DD JMP $310F` reaches a stub
RTS and belongs to an earlier scene. That first jump is not the later
Gouraud frame API.

The original mainline API `$0F0C` jumps to `$0F8B`, calls `$5467`, and then
increments scene state `$1767` from 9 to 10. `$5467 JMP $5485` is the shader
initializer. The IRQ-side dispatcher calls **`$546A`** for state 10, with
continuation `$17DB`. Mainline API `$0F0F` waits for state 11. Thus the
shader's frame calls originate in the original dispatcher, not a fabricated
standalone invocation.

The frame calls `$5515`, `$5586`, `$5759`, `$59A9`, `$5B56`, `$5D50`, and
`$5E65`. Source inspection ties these to ramp sequencing, word-valued
rotation arithmetic, transformed/projected vertex data, visibility tests,
edge preparation, tracing internal shade boundaries, and boundary work.
These are source roles, not an independently reproduced complete 3D model.

The earlier `$38B7` routine XORs two face/edge patterns and rejects a whole
line when the result is zero. That is a different optimization from
omitting zero sites *inside* a nonzero thin line. The shader-specific path
below establishes the latter.

## A thirteen-level ramp with one-site transitions

Original bytes **`$556E..$557A`** are:

```text
FF FB EB EA AA A6 96 95 55 51 41 40 00
```

Each byte contains four two-bit selector fields. The sums of their numeric
codes are exactly **12, 11, …, 0**. Every step changes one field by one code.
These are selector-code ranks; a perceptual luminance ramp or the actual
live VIC palette is a separate question.

Adjacent-level XORs are:

```text
04 10 01 40 0C 30 03 C0 04 10 01 40
```

Every mask occupies **exactly one two-bit field**. This is an independent
calculation from the original thirteen bytes, not a mask algebra invented
from the author's prose.

`$555F` copies a moving sixteen-byte window from the surrounding table into
`$60ED`. The ramp controller `$5515` changes that window during entry/exit.
The internal tracing loop at `$5E43` obtains the two edge intersections for
an intensity boundary. Its sequence at `$5E57` is:

```asm
LDA $60EC,Y
EOR $60ED,Y
STA $15
JSR $1856       ; call at $5E5F; continuation $5E62
```

It therefore passes the transition between adjacent ramp entries to the
line routine. Outer boundary work can instead tail-jump to `$1856` from
`$5EBD`; its return destination is different. Those call paths must remain
distinct in native observations.

## What the line routine skips

The line API at `$1856` consumes X endpoints `$10/$11`, Y endpoints
`$12/$13`, and packed XOR pattern `$15`. Descending-X endpoints are swapped.
A zero horizontal extent returns at `$1875`. Its generated plotting cells
consume ascending **half-open X intervals `[x0,x1)`**.

The pattern is handled in two passes:

| Pass | First selector field | Second selector field | Empty-pass branch |
|---|---|---|---|
| Upper nibble | `$C0` | `$30` | `$18EA → $199F` |
| Lower nibble | `$0C` | `$03` | `$19C0 → $1A72` |

If both fields in a pass are nonzero, the full-X path plots each X position.
Its generated-cell template at `$123C` advances by slope word `$1C/$1D`.
If only one field is nonzero, the half-X path visits only the corresponding
X parity; its template at `$124C` advances by **twice** that slope, prepared
at `$18C3` into `$06/$07`.

For ascending endpoints, the selected half-X column intervals are:

```text
first field only:  k in [ceil(x0/2), ceil(x1/2)), plot X=2*k
second field only: k in [floor(x0/2),floor(x1/2)), plot X=2*k+1
```

The initial interpolation position advances by one ordinary slope when
the first selected X follows x0: first-field mode if x0 is odd, or
second-field mode if x0 is even. The actual ADC chain must retain its
incoming carry: **1** in the first-field/odd-x0 path, **0** in the
second-field/even-x0 path. The former therefore includes an additional
fractional unit; replacing both with ideal `position += slope` loses a
source detail. Subsequent steps use the doubled slope.
This preserves the skipped coordinate spacing rather than compressing the
line toward its start. The general occupancy proof does not establish all
vertical rounding cases; the retained native line below supplies one
separate source-derived stepping and output witness.

For each of the twelve original adjacent-level masks, one pass is empty
and the other selects one X parity. The scalar checks these source-derived
floor/ceil formulas against direct per-site pattern tests for **all 2,080
ascending endpoint pairs in 0..63**, in both passes: **49,920 comparisons**.
All selected X lists agree, including zero-width and parity boundaries.

This establishes quarter occupancy in the four-site pattern. It does not
mean exactly 75% fewer elapsed machine cycles: setup, partial endpoints,
Y stepping, stores, interrupts and VIC stalls remain relevant.

## Original-generation and one-line witness

The independent controller proof observes the complete original file-51
payload at its load return (`$06FE`, 10,461 matching bytes) and file 52 at
`$0709` (13,603 matching bytes). This producer consumes that pinned proof
and rehashes the relevant RAM files. It also guards the real `$546A` frame
prefix and stable scene/ramp state. An earlier stop at the same numerical
PC belonged to another overlay and remains explicitly rejected.

The accepted thin-line entry at `$1856` has X=`32→40`, Y=`72→60`, mask `$04`,
scene state 10 and ramp flag `$5514=1`. Its actual caller is the internal
boundary call at `$5E5F`, returning to `$5E62`; it is not the outer-boundary
tail-call path. The scalar takes the complete **before** marker buffer,
prepared arithmetic-table bytes, original line templates and entry inputs.
Completed marker bytes are used only for the final comparison.

For this line the original reciprocal/product-table carry chain produces
unsigned slope `$00C0`. The negative path complements it to `$FF3F`, with
no added one; its doubled word is `$FE7E`. The lower-nibble first-field
path selects X=`32,34,36,38`. Its initial fractional/integer state is
`$40/$23`, with carry 1 from the nonempty interval test. Each intermediate
step retains the source ADC carry. A temporary RTS at the last generated
cell's offset 8 returns after the store and before another coordinate step.

| Selected X | Marker address | XOR mask | Before → predicted after |
|---:|---:|---:|---|
| 32 | `$7E23` | `$40` | `$00→$40` |
| 34 | `$7E21` | `$04` | `$00→$04` |
| 36 | `$7E60` | `$40` | `$00→$40` |
| 38 | `$7E5E` | `$04` | `$00→$04` |

All **2,048 bytes at `$7800..$7FFF`** agree with the native return capture:
four computed XOR-write bytes and 2,044 preserved incoming bytes. The
source also predicts **A=`$8A`, X=`$BD`, Y=`$08`, C=1**, matching the native
return. A/Y are derived from the epilogue `A9 8A A0 08 91 04 60` at `$1A6C`,
guarded in both the original file and the incoming native code generation.
The return PC and two-byte SP change come from the independently accepted
call witness. Other scratch RAM is outside this model.

This is one bounded line, not an arbitrary-line proof. Prepared arithmetic
tables and preceding markers remain inputs; their complete generation and
the full frame's geometry/shading are not reproduced here.

## Markers, common reconstruction and timing limits

`$1856` XORs **markers**, not completed shaded spans. The original common
IRQ path subsequently reconstructs output through a generated prefix pass
and clears the marker plane before another shader dispatch. The
[controller note](eod-controller.md#guarded-shader-and-one-line-boundaries)
binds `$174D JSR $1A73` and `$1750 JSR $1A78`, the `$125C`
`EOR $7800; STA $7000` template, and the generated `$D800/$C400` paths.
The shader's tracing method therefore coexists with a common filler.

The retained native clocks measure 515 elapsed machine cycles for this
line, 58,218 for one stable `$546A→$17DB` shader body, and 98,254 from that
begin to the next `$546A` begin. The remaining 40,036 cycles include work
outside the body; the available endpoints do not partition it further.
The scalar predicts no timing. Neither the body nor this single interval
establishes delivered scene FPS or a general speedup.

As separate context, HCL's [13 February 2008 forum reply](https://csdb.dk/forums/index.php?roomid=11&topicid=52629)
describes an invisible line buffer, separately buffered visible output,
and the RAM cost of an unrolled filler. The retained original HTML lines
187–190 are pinned. This is a general author explanation, not an explicit
specification of EOD; the EOD addresses above come from its own bytes.

## Passive reproduction and boundaries

```sh
rtk proxy python3 -B research/eod/shader.py --output build/research/eod/shader-analysis/fresh-replay
```

Choose a fresh directory. The producer pins the accepted-03 extraction
receipt and checked source, rehashes both original decoded PRGs, consumes
the accepted controller witness, guards entry/transition/line-template
bytes, and calculates the ramp, occupancy and retained thin line. It
executes no downloaded tool or CPU instructions and starts no native run.

The current receipt is
`shader-analysis/accepted-03/shader-proof.json`, **18,548 bytes**, SHA-256
`275cd3c59f5056b60ca7c63f66b931e504b6f44eb66772d0f02911d97ebd085f`.
The producer is **17,936 bytes**, SHA-256
`00206a1a027a56e7bf29f99c9714fb302dc58fb75c7b0fc59790b453877bcfd7`.
An independent root replay reproduces all five outputs byte for byte,
**38,557 bytes**. `shader-analysis/root-replay-check.json` records that
comparison (1,063 bytes, SHA-256
`b86f6551a20674dfe09b2d5944c3944a482ad167204f8b306e7ba30aca46f5c5`).
The earlier static-01/static-02 outputs remain retained; static-02 guards
the two distinct initial ADC carry paths. The accepted result adds the
native-bound one-line comparison, not whole-frame scanout.

Next, independently reconstruct the shader's contour/intensity inputs and
the common prefix output. Keep this thirteen-level path separate from
earlier flat scenes and HCL's earlier textured x-vector description. A full
image comparison must derive all its markers and account for the actual
publication/display path rather than treat this one line as a frame.
