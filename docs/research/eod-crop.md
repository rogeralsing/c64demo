# Edge of Disgrace: the crop plan comes from fixed source bounds

Research date: 8 November 2026. The original initialization code and its
constant tables independently reproduce **every generated prefix and clear
byte**: 9,933 bytes at `$D800..$FECC` and 4,951 at `$C400..$D756`.
Both complete images and all 32 bound-table bytes match all **49 saved
post-initialization RAM states** in original `native-03` and `native-04`.
Captured generated code is a comparison oracle, never a generation input.

The bounds are **static source constants**, reused for both marker planes.
They are not a per-pose bounding box calculated from the current vertices.
This closes the generated-descriptor input gap in the earlier
[prefix proof](eod-frame.md) and [six-pose acceptance](eod-poses.md) for
these captured cases. Those older producers and receipts remain unchanged.
It does not prove that the fixed crop safely encloses arbitrary geometry.

The new passive producer is [crop.py](../../research/eod/crop.py); the
[accepted proof](../../build/research/eod/crop-analysis/accepted-01/crop-proof.json)
records source guards, constants, address formulas, complete expected code
images and all native comparisons.

## Where the original generator runs

The original [controller](eod-controller.md) calls `$0F00` at `$0701`,
before loading file 52. The public entry jumps to `$0F12`. At `$0F4C`
the source executes `DEC $01`, calls `$105E`, then restores the port with
`INC $01` at the return continuation `$0F51`.

`$105E` generates the full-X and half-X plot kernels first, then falls
through into the crop constructor at `$1181`. Thus the crop generator and
both bound tables are already in original file 51; file 52 is not their
source. They are generated during the shared part initialization, before
the later Gouraud frame dispatcher. The original common IRQ subsequently
calls the generated prefix and clear routines; it does not regenerate
these bounds for each pose.

The accepted `after52` snapshots at `$0709` already contain the complete
expected plan. Later shader, reconstruction, display and fade snapshots
retain exactly the same code. This is source-call-path and saved-byte
evidence. It is not an instruction trace or timing proof of every
transient initialization store. No extra native boundary is needed for
the present byte comparison. A separate constructor observation, if ever
required, would naturally bracket `$105E → $0F51`.

## The actual bounds and endpoint rule

At `$11B3`, A holds the candidate row X. `CMP $1262,Y; BCC skip` excludes
rows below the lower bound. `CMP $1272,Y; BCS skip` excludes the upper
bound itself. The selected interval is therefore **lower inclusive,
upper exclusive**. X runs from 0 through 63; Y selects one of sixteen
column entries.

| Column | Lower, `$1262+column` | Upper, `$1272+column` | Emitted rows |
| ---: | ---: | ---: | ---: |
| 0 | 16 | 46 | 30 |
| 1 | 11 | 51 | 40 |
| 2 | 7 | 55 | 48 |
| 3 | 4 | 58 | 54 |
| 4 | 2 | 60 | 58 |
| 5 | 1 | 62 | 61 |
| 6 | 0 | 63 | 63 |
| 7 | 0 | 63 | 63 |
| 8 | 0 | 63 | 63 |
| 9 | 0 | 62 | 62 |
| 10 | 1 | 62 | 61 |
| 11 | 3 | 60 | 57 |
| 12 | 5 | 59 | 54 |
| 13 | 8 | 56 | 48 |
| 14 | 13 | 52 | 39 |
| 15 | 20 | 44 | 24 |

These are the original literal values, not an ellipse fitted to captured
descriptors or pixels. Their geometric origin and a proof that they are
sufficient for every intended animation state remain separate questions.

## Pointer recurrence and the second plane

The original immediates initialize four pointers:

| Pointer | Initial address | Role |
| --- | ---: | --- |
| `$04/$05` | `$D800` | Emit prefix code |
| `$06/$07` | `$7800` | Current marker address |
| `$08/$09` | `$7000` | Current output address |
| `$0A/$0B` | `$C400` | Emit marker-clear code |

Every column begins by emitting `TXA`, which resets the later running XOR
because prefix entry `$1A73` sets X to zero. Each selected row copies the
six-byte template from `$125C`:

```asm
EOR marker
STA output
```

It also emits `STA marker` into the clear stream. Marker operands are
patched into both cells; output operands are patched into the prefix cell.
Emitted-code pointers advance by six and three bytes only for selected rows.
Crucially, the marker pointer advances by one and output by two for **all
64 candidate rows**, including skipped rows. Skipping a cell does not pack
the subsequent source or destination addresses together.

After sixteen columns, marker is `$7C00` and output is `$7800`. The
original SEC/SBC chain subtracts **`$07FF`**, leaving output `$7001`.
`LSR A` tests that low bit without modifying the stored pointer. Carry 1
returns to `$11A1`, resets the bounds index and emits the second plane with
the same sixteen bound pairs. The next wrap leaves marker `$8000` and
output `$7002`; the low bit is now zero, so both streams receive an RTS.

An independent closed-form enumeration checks that recurrence:

```text
marker = $7800 + 1024*plane + 64*column + row
output = $7000 + 128*column + 2*row + plane

plane = 0..1, column = 0..15, lower[column] <= row < upper[column]
```

Both calculations use original code/constants only and produce identical
complete byte images. All 1,650 marker addresses and all 1,650 output
addresses are unique. Of 2,048 considered cells, 398 are skipped.

## Complete emitted bytes and saved comparisons

There are 32 `TXA` groups, 1,650 six-byte prefix cells and a final RTS:
`32 + 1650*6 + 1 = 9933` bytes, terminating at `$FECC`.
The clear stream has `1650*3 + 1 = 4951` bytes, terminating at `$D756`.
Bytes after those terminators and the unused gap are not synthesized.

| Expected artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| [Prefix](../../build/research/eod/crop-analysis/accepted-01/expected-prefix-D800.bin) | 9,933 | `ad3d6190e3fb7f79a719a3ceda0bfe968bbbb76fe1ed55b7542417f88f9820d5` |
| [Clear](../../build/research/eod/crop-analysis/accepted-01/expected-clear-C400.bin) | 4,951 | `da858ac940dbac8d92f5ba452c8b2adeb5ba7c4bfe13d3ee285bd94987f06e1c` |

Comparison covers fourteen post-initialization `native-03` states and
thirty-five `native-04` states. The earlier SYS snapshots are deliberately
excluded because this initialization has not run yet. All six new pose
begins—baseline, `p110`, `p096`, `p072`, `p024`, `p206`—have the same plan,
as do their body/prefix/clear states. Native04's display snapshots also
retain it. The accepted case receipts supply the physical-RAM/snapshot
and original-boot custody; that audit is not duplicated here.

Two source interpretations are explicitly rejected:

| Wrong interpretation | Result |
| --- | --- |
| Include the upper endpoint | 1,682 cells; prefix 10,125 bytes, clear 5,047; both code images differ |
| Subtract `$0800` instead of `$07FF` | Output returns to even `$7000`; stops after one plane, only 825 cells |

These controls change source semantics. They are not claims about visible
artifacts or native runtime behavior of patched code.

## Replay and remaining limits

Choose a fresh output directory:

```sh
rtk proxy python3 research/eod/crop.py \
  --output build/research/eod/crop-analysis/replay-new
```

The producer is 14,235 bytes, SHA-256
`ba122ec09c19223cfbbe979cf3d67c33c0c02e5424825acd61ec83cecf956c17`.
The accepted receipt is 38,408 bytes, SHA-256
`c4096025b34405d20d488d793b1a3551110986aac1738dffe4608c508cecf1e8`.
A fresh self replay reproduces all four outputs and 67,527 bytes exactly;
its [report](../../build/research/eod/crop-analysis/self-replay-check.json)
is retained. Parent source review found no material issue, and an independent
root replay also reproduces all four files and 67,527 bytes exactly. Its
[report](../../build/research/eod/crop-analysis/root-replay-check.json)
is 806 bytes, SHA-256
`e5d073b760d4a9afb955bd2ea1255708522ba4639e640c0f2a1185c5c79bad55`.
The producer starts no emulator, CPU interpreter, downloaded host entrypoint,
build or native process.

This independently justifies the generated crop descriptors used by the
older accepted pipelines for these original cases. Their markers and
outputs still depend on declared incoming state. The skipped 398 cells
remain untouched by this prefix/clear pair; the earlier seventeen retained
nonzero marker bytes do not become zero merely because the constructor is
now understood. The [committed baseline display](eod-display.md) remains
its own bounded acceptance.

Next investigate an uncovered visibility/clipping boundary and another
committed pose or transition field. Fixed bounds are not general clipping:
this result proves neither an arbitrary object's enclosure nor safe
overflow, whole-animation crop safety, a complete displayed field,
delivered FPS or optimization savings.
