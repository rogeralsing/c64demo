# One-Der: original runtime shading and a 13-cycle packed plot

Research date: 8 November 2026. **One-Der / Oxyron**, coded by Graham,
released 29 December 1997 at The Party, is now an original-byte native
Gouraud study rather than a screenshot-only recommendation.
[Release](https://csdb.dk/release/?id=11692),
[Graham's own rendering statement](https://csdb.dk/forums/index.php?roomid=10&showallposts=1&topicid=53226).

The original program reaches its shading stage naturally. Native execution
binds varying vertex attributes, four triangle-gradient calls, the packed
lookup tables and one exact `LDA / ORA / STA` plot. It does not establish
full-image correctness, physical output geometry or whole-scene FPS.

## What is computed and what is prepared

The inspected code rotates object data during execution. Its per-vertex
third rotated component supplies the intensity attribute; this is not yet
an independently verified light-source/normal calculation. The collector
loads vertex X/Y/third values, complements the third byte and submits
triangle triples. Runtime edge and gradient routines then use those
different intensities across each triangle.

| Original code | Role established by inspection and bounded execution |
|---|---|
| `$2000` | Shading-stage initialization, reached naturally |
| `$090C / $091B` | Five object configurations and initialization calls |
| `$09CD` | Rotation-coefficient call, then buffer clear/toggle and object draw |
| `$09D6` | Actual object-draw return, before angle increments/presentation wait |
| `$1D74 / $1D93` | First object's initialization/rendering pair |
| `$0056 / $0064 / $0072` | Per-vertex X/Y/third arrays |
| `$0CE0` | Triangle-index collector and complemented third attributes |
| `$0D7E / $1514` | Triangle drawing and edge construction |
| `$0E53 → $1770 → $0E56` | Runtime gradient call and actual continuation |
| `$17EA / $1853` | Multiply/divide helpers used in gradient construction |

The later captured object uses initializer `$1B02` and renderer `$1B1D`.
It must not be silently labelled the first tetrahedron. Native trace 111
contains **four complete gradient calls**, each with differing third
attributes among its three supplied vertices. The producer checks caller
bytes, actual PCs/SP and unchanged vertex triples across each call. The
gradient arithmetic itself has not yet been independently reproduced.

## A small ramp, four unrolled kernels, patched span endpoints

Initializer `$1D74` supplies fraction `$D8`, signed integer `$FB` (−5), and
increment `$0D` to `$0A24`. That routine generates eight 256-byte pages at
`$3000..$37FF`. It preincrements a wrapping 16-bit accumulator, clamps its
signed high byte to 0..6 and selects one packed code:

```text
FF EE AA 99 55 44 00
```

Each code becomes high/low nibbles and their two-bit-shifted variants;
pairs of pages duplicate the values for index/address range. These are
**seven packed ramp codes**, not seven independent RGB colors. The actual
VIC palette and raster display contract need separate interpretation.

The independent scalar reconstruction matches **all 2,048 bytes** in
five captures, **10,240 compared bytes total**. Tables are prepared by
the C64 initializer and reused. They are not complete animation frames.

Four static kernels start at `$12CF / $1360 / $13F1 / $1482`. Each contains
16 repeated nine-byte `LDA abs,X; ORA abs,X; STA abs,Y` groups plus RTS:
**145 bytes per kernel, 580 bytes total**. Their software destinations
cover `$2000..$27FF` and `$2800..$2FFF` in `$80` column strides. Two table
pairs provide the alternative packed phases. Operand offsets are patched
for the work being drawn.

At `$0F1A` the original code places a temporary RTS at the span endpoint;
the patched JSR at `$0F20` enters the chosen start. `$0F25` restores the
LDA opcode afterwards. This selects part of the unrolled body without
a per-group loop branch. Exact edge inclusion and full-frame coverage
remain to be modelled before reusing this convention elsewhere.

## An actual native byte plot

The owned PAL run stopped naturally at this patched kernel entry:

```asm
$133B  LDA $304E,X
$133E  ORA $3246,X
$1341  STA $2600,Y
$1344  RTS
```

With **X=$41, Y=$20**, the two reads are `$308F=$90` and `$3287=$0A`.
Three original instructions produce `$9A` and store it at `$2620`.

The before/after full RAM files differ at **exactly that one address**,
`$FF → $9A`. CPU A/N/Z, preserved registers/ports/SP and continuation PC
agree. The interval is **13 actual elapsed PAL cycles**. The RTS is not
included. This proves one byte plot combining two nibble contributions;
the exact number and dimensions of displayed samples are separate work.

One later `$09CD → $09D6` interval takes **132,724 cycles**, about **6.75
PAL field budgets**. It includes original rotation, clearing, drawing,
IRQ execution and VIC delays, and excludes the following wait/presentation.
It is one pose of one later object, not a same-workload comparison with
3Dvibe64 and not a delivered-frame-rate measurement. The fast byte kernel
does not establish a 50 Hz complete renderer.

## Original boot, retained corrections and CPU-port semantics

The CSDb download is a gzip-compressed T64. Its one active entry contains
**51,199 payload bytes**, loading at `$0801` and ending before `$D000`.
The extracted PRG is 51,201 bytes, SHA-256
`a4d719d1ef0d65b287225f466ca068f742d7d7d98e6f667045065da2ce056053`.
All 51,199 loaded bytes match native RAM before the original BASIC SYS
entry `$CF9D` executes.

Natural milestones are `$CF9D → $3175 → $080E → $0142 → $013F → $14BE →
$1000 → $F040 → $2432 → $2000 → $09CD`. The original program performs
its relocations and depacking; there is no later PC/RAM/register patch or
snapshot restore. Navigation warp is declared and disabled at `$2000`
before the shading observations. Speed reads are 100; emulated cycle
evidence is not a host wall-time speed measurement.

Two observation details remain explicit:

- The monitor received `keybuf "D"`; native A was `$22`, the first literal
  quote character. The original menu accepts any non-N key for its demo
  branch. This is not evidence that `$44` selected it.
- Sequence 81 attempted to delete nonexistent checkpoint 1. Consequently
  `shade-start-ram.bin` records the second `$09CD` boundary, not `$0A24`.
  Its filename is preserved; the producer classifies it by actual PC.
  The later `$0A24` observation attempt was interrupted with read-only `r`
  on the same socket. No table-builder entry is fabricated from that wait.

All **14 full RAM/VSF pairs** agree on 65,536 RAM bytes, CPU registers,
clock and beam. CPU ports require the correct schema: C64MEM saves both
the output latch and externally affected readback. With DDR `$2F`, latch
`$00` can read `$10`, and latch `$B5` can read `$35`. The final proof
compares monitor `$00/$01` with serialized `dir_read/data_read` at payload
offsets **65542/65541**, separately checking driven output bits. It guards
C64MEM version 0.1, length 65,555 and zero unused-bit/decay state.
It does not equate the output latch with input readback or infer tape state.

The schema comes from pinned VICE 3.10 sources: `c64memsnapshot.c:217–230`,
`c64pla.c:53–75` and `c64mem.c:267–338`, retained in the existing official
source archive. Intermediate `accepted-01` preserves the narrower initial
port check; final `accepted-02` additionally checks serialized readbacks
and the gradient callsite bytes.

The case is closed and its owned process reaped: **36 files / 3,944,034
bytes**, canonical listing SHA-256
`3264e764ff72ae0744de5c0a3b55beabd7641ac370c79744a8fb3ba0f4b361a9`.
All 124 ordinary commands received complete responses; one is the
explicit read-only interruption. The one invalid-checkpoint response is
retained and checked rather than treated as a successful deletion.

## Reproduce and continue

```sh
rtk proxy python3 research/one-der/analyze.py --output build/research/one-der/analysis/fresh-replay
```

Use a fresh directory. This command only reads retained evidence; it
starts no emulator or CPU model. Its frozen wire-auditor adaptation permits
only the exact original extracted PRG autostart metadata. Final acceptance:

- `analysis/accepted-02/one-der-proof.json`: **36,184 bytes**, SHA-256
  `e5eaaa1c454462e84de564b0984b8d587a37993b2b42457cc504bff0925f1532`.
- Checked producer: **17,180 bytes**, SHA-256
  `8b46d13c021f2d691bacfd87c2194e77450459b8d5c1b3ea24da0e71ed6338f4`.
- `analysis/root-replay-01/` reproduces all three final outputs exactly;
  `analysis/root-replay-check.json` records their identities.

The native image is a cosmetic observation, not a decoded pixel proof:

![Original One-Der shading stage in PAL VICE](../../build/research/one-der/native-01/gouraud.png)

Next, reproduce the signed gradient/division and edge conventions from the
captured triangle inputs, then compare complete software-buffer pixels.
Establish the actual raster display geometry before translating a packed
byte into displayed sample dimensions. Investigate the independent
[HCL tracing-line technique](stock-gouraud-sources.md) from its original
code; its 13 dither levels must not be assigned to One-Der's seven codes.
No SDK, Pong, viewer, exporter or production renderer changed in this study.
