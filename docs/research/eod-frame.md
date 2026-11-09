# Edge of Disgrace: one complete software image from independent markers

Research date: 8 November 2026. One original stable Gouraud frame now has an
independent scalar chain from its incoming angles/state through coefficients,
projected corners, visibility, intensity intersections and XOR markers to the
complete **2,048-byte software output buffer**. All bytes agree with original
execution. This is one captured pose, with declared previous state and generated
crop descriptors as inputs. Actual VIC fetches, palette selection, publication
and other poses remain separate questions.

Read [geometry](eod-geometry.md), [contours](eod-contours.md), the earlier
[line mechanism](eod-shader.md), and [original loader binding](eod-controller.md)
for the individual source contracts. No product renderer changed.

## Fresh original execution and stage boundaries

The root-owned `native-03` case starts the original side-1a D64 through its
ordinary DOS bootstrap. It does not restore an older snapshot or write runtime
RAM/registers/PC. Navigation warp is explicit; actual warp-off and Speed=100
queries precede the measured stages and are repeated at the endpoint.

The closed case has **37 files / 4,048,269 bytes**, listing SHA-256
`b5218a5a088bb0343970327b8ddfc03ea3c177f6bf471db5a739f4bd00817af9`.
All 99 serialized commands complete. One 30.037-second observation notice
on command 12 remains in the journal; that same command subsequently stops
naturally. No interrupt, retry or replacement process occurs. The owned
process is explicitly closed/reaped, exit -15.

All **15 full RAM/VSF pairs** agree on physical RAM, CPU registers/flags,
clock, ports and VIC beam under the existing pinned official VICE schema.
The frozen wire auditor receives only an exact in-memory replacement of its
manual-load startup assertion with the original-disk autostart contract.
The original bootstrap's 874 loaded bytes and file 52's 13,603 decoded bytes
again match completely. Earlier native-02 separately establishes the entire
original file-51/file-52 pair and its actual loader/controller path.

| Capture | Natural PC | Machine clock |
|---|---:|---:|
| `begin` | `$546A` | 469,164,461 |
| `ramp` | `$546D` | 469,164,493 |
| `coefficients` | `$5470` | 469,166,308 |
| `vertices` | `$5473` | 469,168,060 |
| `visibility` | `$5476` | 469,169,677 |
| `edges` | `$5479` | 469,182,577 |
| `internal` | `$547C` | 469,200,758 |
| `outer` | `$547F` | 469,222,667 |
| `body-complete` | `$17DB` | 469,222,679 |
| `prefix-before` | `$1A73` | 469,240,212 |
| `prefix-filled` | `$1750` | 469,255,307 |
| `prefix-cleared` | `$1753` | 469,262,659 |
| `next-frame` | `$546A` | 469,262,715 |

Stage continuations retain the actual call/stack contract. The prefix
entry's saved return word points to `$1750`, and its natural return increases
SP by two. Source guards identify the real shader generation, rather than
accepting a reused numeric PC. Compared with native-02's same-pose entry,
the new incoming RAM differs at exactly one old stack byte: `$0146` is now
`$00`, previously `$80`. The difference is retained, not normalized into a
whole-machine equality claim.

## The common prefix is a separate stage

The original common IRQ path invokes `$1A73`, whose `LDX #0; JMP $D800`
enters generated prefix code. Each column group begins with `TXA`, so its
running XOR starts at zero. Cells use the original `$125C` template
`EOR marker; STA output`. `$1A78` then loads zero and enters the generated
marker-clear code at `$C400`.

The scalar treats these fixed code cells as descriptors, not as arbitrary
CPU instructions to execute. It validates every opcode/address against the
template and an independent two-plane/column formula:

```text
marker = $7800 + 1024*plane + 64*column + row
output = $7000 + 128*column + 2*row + plane

plane = 0..1, column = 0..15, row = 0..63
```

Before cropping, both formulas enumerate exactly 2,048 unique offsets.
The marker planes become alternating rows in a column-major output buffer.
This establishes software addressing; it is not yet a committed VIC display
or physical-pixel geometry proof.

The incoming generated plan contains 32 groups and **1,650 unique prefix
cells**, from `$D800` through the RTS at `$FECC`. The corresponding clear
cells name exactly the same marker addresses. Each plane's sixteen group
lengths are:

```text
30 40 48 54 58 61 63 63 63 62 61 57 54 48 39 24
```

The scalar computes cumulative XOR within each group from the independently
predicted contour marker file. The completed native marker/output buffers
are comparison oracles only. All **2,048 output bytes** agree: 1,650 computed
stores and 398 preserved previous-output bytes. Output SHA-256:
`f49b358d502aee74860db36ce54986e310ff4e8ec96e7d154adc402a35428378`.

The subsequent clear also matches all 2,048 marker bytes, with 1,650 zero
stores and 398 preserved outside-crop bytes. **Seventeen nonzero bytes remain
outside the crop.** A whole-plane-zero assumption would be false. The contour
model preserves that incoming state; its rejected zero-seed control differs
at those seventeen marker bytes. No visible-artifact claim follows from that
control, since these cells are outside the current prefix plan.

The crop plan is still an input captured before execution. Its complete
generation and bounds policy are not independently reproduced here. Neither
the old output's 398 preserved bytes nor the unused marker bytes are invented
as zeros.

## Observed costs for this one frame

The consecutive natural stops partition the observed interval without
double-counting an inclusive parent. Costs include VIC stalls and any IRQ
work inside the corresponding interval; they are not retired-instruction
counts or a general worst case.

| Work / observed boundary | Elapsed PAL machine cycles |
|---|---:|
| Ramp sequencing `$546A..$546D` | 32 |
| Coefficients `$546D..$5470` | 1,815 |
| Corner projection `$5470..$5473` | 1,752 |
| Visibility `$5473..$5476` | 1,617 |
| Intensity-edge preparation `$5476..$5479` | 12,900 |
| Internal contours `$5479..$547C` | 18,181 |
| Outer boundaries `$547C..$547F` | 21,909 |
| Shader epilogue `$547F..$17DB` | 12 |
| Return to next prefix entry | 17,533 |
| Prefix entry through natural caller return | 15,095 |
| Clear call through natural continuation | 7,352 |
| Clear continuation to next shader entry | 56 |
| **Shader begin to next begin** | **98,254** |

The shader body sums to **58,218** cycles. Common prefix and clear now have
separate observed windows. The remaining caller/IRQ/wait intervals are
reported as boundaries, not guessed as exclusive arithmetic costs. The
prefix window excludes its caller's JSR; the clear window starts at that
caller's JSR. These scopes are deliberately explicit.

One begin interval is approximately five PAL refresh budgets of 19,656
cycles. It is not a delivered-FPS distribution, a whole-animation timing
claim or a measured speedup over our own renderer.

## Passive replay and limits

Choose fresh output directories:

```sh
rtk proxy python3 research/eod/frame_case.py --output build/research/eod/frame-analysis/fresh-replay
rtk proxy python3 research/eod/prefix.py --output build/research/eod/prefix-analysis/fresh-replay
```

Frame acceptance is `frame-analysis/accepted-01/frame-proof.json`, 33,339
bytes, SHA-256
`ef77c7a2d93d110ce5caa8c60c313d8d7313325ba51e9d355cff9e855535bb50`.
Prefix acceptance is `prefix-analysis/accepted-01/prefix-proof.json`, 7,150
bytes, SHA-256
`3bc7c07dc281850885dc1671cbca55a2c9a42a1340d99bd8fe19afb919ec057b`.
The tracked producers and receipts identify every pinned input. Passive
replay starts no emulator, process, CPU interpreter or build. Source review
and independent deterministic replays are retained alongside each result.

Frame replay reproduces both outputs exactly, 43,361 bytes; its 919-byte
`root-replay-check.json` has SHA-256
`b64e473c2894f7ac1d4b7b513069ef2c5812dcfcc68d969515d66aeb719e0ae3`.
Prefix replay reproduces all four outputs exactly, 19,021 bytes; its
936-byte check has SHA-256
`326aa1b078941e6b6dda0b1e8f271676a2eecb82cd7bcc7f6ee48ce968767f83`.
Independent source review found no material issue in the wire/pair custody,
descriptor formulas, prediction/oracle separation or preserved-byte scopes.

The complete software-image result combines the separately accepted
geometry and contour calculations with this prefix pass. Previous state,
static source tables, generated crop descriptors and some preserved slots
remain declared inputs. It does not establish arbitrary clipping/overflow,
all visibility fallbacks, other rotations, perception of the palette,
actual VIC fetch/publication timing or a complete 312-line displayed frame.

Continue with committed VIC data/color/charset fetches for the independently
calculated output, then another pose or crop/line boundary. Preserve the
whole-chain scalar rather than repeatedly treating one thin line as a frame.
