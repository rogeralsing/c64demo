# Edge of Disgrace: original output-case custody

Research date: 8 November 2026. This note records the original native
`native-04` case used by the separate [display](eod-display.md) and
[additional-pose](eod-poses.md) calculations. The original disk boot is now
owner-closed and pinned: all **36 complete RAM/VSF pairs** and **270 serialized
commands** pass the new [passive producer](../../research/eod/output_case.py).

This producer owns wire/lifecycle and complete machine-state custody, source
and natural checkpoint binding. The display and multi-pose producers own
the independent pixel and arithmetic comparisons. Existing cases, source
readers and accepted proofs remain unchanged.

## Original execution and retained events

The closed case contains **80 files / 9,764,629 bytes**, canonical listing
SHA-256 `c52bb838d493b5d6261b1b55f931df74b358136748ceb9f9de201b8ea499540c`.
Its 12,480-byte manifest has SHA-256
`68e8bd5cc27781048f9e80655e3cfa9b3c946ac78ea0b58bae3ab4170ecdfb0e`;
the ordered 270-command list has SHA-256
`485b5a0d26109169bfb294552d56daf507aba714fdbbc059d7d5291531cbdf71`.
The single owned PID 91179 was explicitly terminated and reaped, exit −15,
at `2026-11-08T19:11:40.579580+00:00`. The full wire auditor verifies byte
ranges and event ordering, one process/endpoint, natural completion and
absence of resends, restarts, cancelled commands or discarded events.

The owned VICE instance starts the original `EdgeOfDisgrace_1a.d64` as both
`-autostart` and drive 8, with the original true-drive 1541 path. It does not
load a candidate PRG into RAM, restore a snapshot, set PC/registers or patch
runtime RAM. Monitor breakpoints, tracepoints and conditional predicates
observe the running original. Navigation warp is explicit; actual warp and
Speed resource responses bound the accepted observations.

The frozen `verify_vice_live.py:audit_session` receives exactly one in-memory
startup-assertion replacement: require original-D64 autostart and the same
disk at `-8`, in place of its original manual-load assertion. The function's
remaining source and all journal events are retained. The producer records
both function hashes and the literal replacement.

Two observation waits belong to this original same-process journal:
sequence 1 is the observer's internal startup `r` (30.051 seconds), and
sequence 13 is the original `natural-load52` `x` (30.003 seconds). Both later
complete on their original handle. They are neither filtered out nor
rewritten as retries, interruptions or failures.

## Saved-state contract

Every capture has an immediately preceding explicit register query, a full
physical-RAM `bsave ... 0000 ffff`, and an adjacent VSF `dump`, without a
resume in between. The unchanged frozen `controller.capture_pairs` compares
all 65,536 RAM bytes, CPU registers/flags and clock, CPU port latch/readback
fields and driven bits, and VIC beam state under the already pinned official
VICE 3.10 snapshot schema. Full-range raster breakpoints report the actual
single instruction PC in their natural-stop line, so no capture-parser
adaptation is needed.

The accepted capture set is `sys`, `after52`, six five-stage pose groups,
`baseline-next-frame`, and three display states. Pose stages are `$546A`
(begin), `$17DB` (body return), `$1A73` (prefix entry), `$1750` (prefix return),
and `$1753` (marker-clear continuation). Source guards bind the real shader,
scene dispatcher and common prefix entries, and the saved stack binds the
natural body/prefix continuations. Numeric PCs alone are insufficient: an
earlier original overlay used `$546A` for unrelated bytes.

Pose entry predicates select dispatcher state 10 and the actual phase/counter
at `$5514/$5513`: baseline 1/120, p110 1/110, p096 1/96, p072 1/72,
p024 1/24 and p206 2/6. Predicted angles, visibility or output bytes do not
select native stops. The later captures are comparison oracles for the
separate multi-pose scalar.

The loaded original bootstrap matches all 874 bytes at `sys`, and the
original file-52 payload matches all 13,603 bytes at its real `$0709` load
return. These comparisons reuse the pinned original file-extraction proof.
Every later capture matches exact original source guards, with no excluded
bytes in these ranges:

```text
1643..1646  1667..1671  16AA..16AD  16B8..16D0
174B..1758  1768..17E1  1A73..1A7D  5467..5513  5515..556D
```

Ends are exclusive. They bind timed IRQ writes, common reconstruction,
scene dispatch, the shader entry/generation and ramp phase logic. Broader
geometry/contour source and generated descriptor guards remain the separate
multi-pose proof's responsibility.

| Pose | Native begin clock | Native body clock | Body interval |
| --- | ---: | ---: | ---: |
| baseline | 469,223,429 | 469,281,647 | 58,218 |
| p110 | 470,049,369 | 470,090,682 | 41,313 |
| p096 | 471,306,999 | 471,368,861 | 61,862 |
| p072 | 473,508,691 | 473,551,084 | 42,393 |
| p024 | 477,341,379 | 477,358,183 | 16,804 |
| p206 | 479,896,685 | 479,954,975 | 58,290 |

Intervals are elapsed PAL machine cycles, including VIC stalls and IRQ work
in their scopes. They are observations, not scalar timing predictions,
exclusive operation costs, delivered FPS or a measured speedup.

## Display interval and trace scope

The display interval begins at the first following original top-IRQ
continuation `$16BB`, after fine-scroll/palette setup. Natural instruction
stops request raster line 130/raw cycle 31..35 and line 220/raw cycle 35..45.
The actual register and snapshot beam values, actual instruction PCs and
clock lineage satisfy these predicates in one PAL field:

| Capture | Actual PC | Raster / raw cycle | Clock |
| --- | ---: | ---: | ---: |
| display-setup | `$16BB` | 52 / 43 | 469,329,631 |
| display-mid | `$5CDB` | 130 / 31 | 469,334,533 |
| display-complete | `$5DDC` | 220 / 36 | 469,340,208 |

The full-range break response reports each actual single instruction PC, so
the frozen capture parser requires no edit. Raw setup/condition acknowledgments
and every capture's active checkpoint binding are exposed in the proof.

Store tracepoints cover `$D000..$D02E`, `$DD00..$DD03`, `$6C00..$6FFF`,
`$7000..$77FF` and `$D800..$DBFF`, each with attached `r` for CPU `$01`
context. Trace setup, attached commands and their raw response byte ranges
are retained. Each observed monitor trace hit and attached register context
must be reported in original order. In particular, an RMW instruction's
monitor hit is not assumed to be one physical bus write. A CPU `$01=$34`
write in the last range can address RAM under Color RAM; address alone does
not establish the destination device. The downstream display proof owns
that classification and every committed-pixel claim.

The two complete natural-resume responses, sequences 77 and 83, contain
exactly four configured monitor instruction hits in original order:

| Response | Address / instruction | Source PC | Attached `r` PC | Clock |
| --- | --- | ---: | ---: | ---: |
| 77 | `$D012` / `STA` | `$16BD` | `$16C0` | 469,329,637 |
| 77 | `$D019` / `INC` | `$16C5` | `$16C8` | 469,329,649 |
| 83 | `$D012` / `STA` | `$1732` | `$1735` | 469,338,451 |
| 83 | `$D019` / `INC` | `$173A` | `$173D` | 469,338,463 |

All attached CPU-port readbacks are `$01=$35`. The receipt preserves each
complete hit/register block and the whole original response's byte ranges
and hashes in `received.bin`, plus all five arming/attachment acknowledgments.
These are monitor instruction hits, not a four-bus-write count. The watched
matrix, charset, Color RAM and CIA2 ranges emit no additional monitor hit
inside these bounded responses. This does not establish their behavior
before arming, after trace deletion or elsewhere in the demo.

## Replay and limits

Choose a fresh directory:

```sh
rtk proxy python3 -B research/eod/output_case.py --output build/research/eod/output-case-analysis/fresh-replay
```

The passive producer starts no emulator, socket, process, CPU interpreter or
build and executes no downloaded host code. It consumes only retained files,
Python's standard library and pinned existing repository readers. Its
`captures` records use the established frame-proof schema so independent
producers can verify the same RAM/VSF inputs.

A closed-case custody result does not itself prove shader arithmetic,
correct output pixels, coherent display publication, an entire 312-line
field, delivered FPS, every pose or a performance improvement. The finite case does not justify those broader claims.


Acceptance is `build/research/eod/output-case-analysis/accepted-01/output-case-proof.json`,
237,514 bytes, SHA-256
`0fe2af337eb6a2674e6cb60b7f861b744457fa7ee8b65e05eed2d10bd9c6a0dd`.
Its producer is 27,239 bytes, SHA-256
`1b5d654fd75c02c3c54abb28d40f8e58f9fe59afb1a6bf01cc74d56ec1213c1d`.
The deterministic fresh-directory replay reproduces both accepted outputs
byte-for-byte, 264,753 bytes. Its 614-byte
`agent-replay-01/agent-replay-check.json` has SHA-256
`3ee57569dd3d6f3f59bbf6406772035861fcc8d84a3657fe855638302f136580`.

Root source review found no material issue. Its separate `root-replay-01/`
reproduces the same two outputs, 264,753 bytes, without path normalization.
The 673-byte `root-replay-check.json` has SHA-256
`3a0943f65b8e3db18ce9d374ccd12445659e95b3fbc25f9c34127a22930d9d5e`.
