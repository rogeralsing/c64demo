# Tower Power: binary investigation ledger

This is an investigation of the **100% final release**, not the 1993 competition build. Release provenance and the crew's included note are covered in [the source note](tower-power-sources.md). The original N2 stage now runs natively and identifies itself as the 72-face sphere. Its runtime rotation and generated product tables are confirmed. The patterned beveled cube is located in F1; active native coordinates, topology, culling, and coplanar stencils explain its large cyan triangles.

## Exact input

The root investigation downloaded the [scene.org final-release archive](https://files.scene.org/view/parties/1994/theparty94/c64/demo/tower_power.zip). Its mirror-resolved ZIP is 189,586 bytes, SHA-256 `338ad76a594e39530c96f89c64b2085d83df87985183b381ad4492e2da71b444`. Download and per-file receipts are under ignored `build/research/tower-power/`.

The two 174,848-byte D64 files are:

| Side | SHA-256 |
| --- | --- |
| 1 | `4839031af8a47c9777de83bf815fd295b0f517adebd87d448dbe75518cb3a0c0` |
| 2 | `2e845a05c117e88ceca1df4d5ffeddd1729351286cd55869b13888ede064ce20` |

The extracted boot PRG is 10,241 bytes, SHA-256 `467a27f7055bf96de9cd8431bdcefd1d1febeacd01e6e22f1822ca2e19cc0b04`. Its load address is `$0801`; the ordinary BASIC entry calls `$2600`. The DOS directory includes a Sharks label and an extra `win386.swp`. Comparison with the CSDb distribution establishes that the shared named demo files are byte-identical; a directory label is not evidence of a different renderer.

## Boot and loader, confirmed in PAL VICE

`research/vice_session.py` launches an owned PAL `x64sc` process and preserves monitor commands, output, launch options, and process cleanup in a session directory. The existing interactive renderer preview is not part of these sessions.

In `build/research/tower-power/live-01/`:

- A breakpoint at `$2600` stopped at the original entry, stopwatch 3,134,523 cycles.
- The original boot copy moved `$2100..$25FF` to `$C000..$C4FF`.
- A breakpoint at `$C300` stopped before loader initialization, stopwatch 3,148,144 cycles. A raw 65,536-byte RAM capture is saved as `ram-loader-init.bin`.
- The copied 1,280-byte loader matches the offline reconstructed loader byte for byte.
- The original loader interface at `$C010` was reached, stopwatch 4,141,637 cycles. The first observed request was the disk-marker name `>>>>CAMELOT!<<<<`.

These observations establish boot and loader control flow. They are not a measurement of a vector effect's speed.

The original code subsequently displayed “INSERT DISKSIDE 2” and waited at `$2688` for the keyboard matrix. The session started with side 1 attached. For investigation, side 2 was attached and PC was moved to `$268D`, bypassing only that space-key wait. This attempt later entered the loader's explicit disk-error loop at `$C1FF`. The attempt was closed and is **not** evidence of a functioning renderer. Both the disk prompt and error path are preserved in native captures and the monitor transcript.

A second session, `live-02/`, started with side 2 already attached, as recommended by the included prompt. It passed the marker check, reached the next `$C010` request with sixteen `$77` filename bytes, and reached the original bootstrap entry `$0810` at stopwatch 9,009,853 cycles. Unlike the first attempt, this session changed neither PC nor attached medium after launch. Full raw RAM captures before the request and at that entry are saved as `ram-before-intro.bin` and `ram-intro-entry.bin`.

Comparison shows only eleven changed RAM bytes between those captures. `$0810` belongs to the boot-resident page copied from `$2000`, not a newly unpacked demo part. The one-byte side-2 marker at `$C2F8` matches the offline decode, but `$C2F0..$C2F3` remain zero and no vector payload has been established. This confirms successful original boot/disk identification, not a successful vector-part load. Detailed comparison is saved as `static/live-intro-comparison.json`.

## Packed part files

Most side-2 files contain custom loader streams. Their first two bytes are not sufficient evidence of their final load destination. Treating those bytes as ordinary PRG load addresses can lead directly to disassembling packed data at an invented address.

The copied loader contains an identifiable depacker. Its raw-byte reader, bit reader, variable-length command decoder, literal output, destination changes, and forward back-reference copy have been reconstructed offline. See [the depacker investigation](tower-power-depacker.md) and `research/tower-power/` for the decoder and command receipts.

The offline parser is now independently checked against execution of the original 6502 depacker: all 42 streams pass, with all 340,371 chronological output address/value writes matching. Only the original disk-block receive boundary is mocked; the original raw-byte and bit readers execute unchanged. The [depacker note](tower-power-depacker.md) records the precise scope, counts, and reproducible receipts. This validates decompression, not the native drive transport or a vector scene's executed path. Missing memory in a flat output image remains explicitly unknown.

The validated `n2` payload generates a 16 KB product table, consumes three angle bytes and 3D coordinate rings, emits projected/depth coordinates, and generates line/fill routines for a 16×16 column-major character grid. The native run below now confirms these computations in the displayed sphere stage. See the address-by-address analysis in the depacker note and [the exact mathematics](tower-power-n2-math.md).

## Original sphere stage reached and verified

The owned `n2-live-01/` session started the original boot with side 2 attached.
At the ordinary `$2600` entry, PC was set to `$2609`: the exact `SYS9737` entry
in the original BASIC line 3, documented by the included note as `RUN 3`.
This deliberately selects an existing entry rather than modifying the renderer.
All subsequent disk transport, unpacking, initialization, interrupts, and
drawing ran in the original program without input mocks or payload injection.

The observed load chain is disk marker, `N1.*`, `M5.*` music, `N7.*`, then
`N2.*`. The original N2 entry `$2034` was reached at stopwatch 36,263,026.
Captures at the relevant boundaries match **all known output bytes**, with no
I/O, stack, or other address exclusions:

| Payload | Native bytes matching decoded output | Receipt |
| --- | ---: | --- |
| N1 | 214 / 214 | `n2-live-01/n1-comparison.json` |
| N7 | 12,301 / 12,301 | `n2-live-01/n7-comparison.json` |
| N2 | 9,793 / 9,793 | `n2-live-01/n2-comparison.json` |

The native title displays **72 FACES**, followed by the rotating faceted sphere.
`after-1m-instructions.png` records that title; `sphere-native-01.png` and later
captures show the sphere. The initial captured sphere palette is orange/brown
rather than the user's green phase, so this is a stage identification, not a
claim of pixel identity with that particular video frame.

The native sphere capture contains the generated table at `$8000..$BFFF`.
All 16,384 bytes match the independently checked product formula, SHA-256
`5e7ed80eace62cc50cc0a965ca76ee8c987c2a38e17b7636290aff0195c48c31`.
This is recorded in `native-product-table.json`. A later stop at the original
transform's `$32F1` return records angles `(199,134,195)`; all **246 coordinate
and depth bytes** for 41 processed source/mirror pairs match the independent
host formula. The mesh uses 40 pairs; the extra pair is an unused sentinel-like
record, as explained in the math note. Receipt: `native-transform-check.json`.

Together, the original load chain, native image, executed transform, and byte
comparisons establish actual runtime rotation and orthographic scaling for
this sphere. The 16 KB tables are arithmetic aids, not complete stored frames.
This does not exclude precomputed topology, trigonometric seeds, motion scripts,
or other lookup data. It also does not establish a production frame rate.

Instrumentation detail: an initial breakpoint at `$32F2` was one byte beyond
the routine's real RTS and timed out. The final transform capture was replaced
after a confirmed stop at `$32F1`; the transcript retains both attempts. The
session was closed cleanly after the final capture.

## F1 patterned cube: native stage and split display

The original `RUN 1` entry is `SYS9731`, `$2603`. In `f1-live-01/`, PC selected
that existing entry at the ordinary boot breakpoint; no renderer byte or disk
payload was changed. Original code then loaded through C1, C7, C2, D1, and E1
to F1. A conditional breakpoint reached F1's actual `$2194` entry at stopwatch
140,640,229, with entry/IRQ vector bytes `94 21 29 3C`.

Execution resumed before an untouched entry RAM dump was saved. The subsequent
running capture therefore is **not** claimed to match every original payload
byte: 11,759 of 12,241 established bytes match, with all 482 differences retained
in `running-comparison.json`. Many changed locations are runtime data or
self-modifying operands, but this ledger does not silently exclude any of
them to manufacture a complete match.

The native `f1-running.png` image shows the patterned blue/purple/cyan beveled
cube beneath the Camelot logo, matching the supplied effect's appearance.
Its generated 16 KB product table again matches the independent N2 formula
byte for byte (`native-product-table.json`). The [F1 investigation](tower-power-f1.md)
identifies 24 body vertices plus 15 coplanar pattern points and derives one
cyan triangle directly from its changing face-edge masks. This is distinct
from the N2 sphere and from F1's earlier eight-corner cube phase.

This stage demonstrates why a single VIC snapshot can misidentify an effect.
At raster 0, the upper logo has `$D011=$3B`, `$D018=$29`, `$DD00=$14`: bitmap
mode in the high VIC bank. A conditional execution breakpoint at **raster 128**
then records `$D011=$13`, `$D016=$D0`, `$D018=$13`, `$DD00=$17`: multicolor
character mode using screen `$0400` and charset `$0800` for the cube area.
The latter region's palette nibbles are `$03/$0E/$06` at `$D021..$D023`.
Both observations use explicit `bank io`; the raw captures use `bank ram`.

The session transcript, `ram-f1-running.bin`, `ram-cube-raster128.bin`, and
`native-session-observations.json` preserve these distinctions. The session
was closed after the cube-region capture. The active model changes during
F1: treating an earlier phase's tables as the pictured cube would give the
wrong vertex and face counts.

## Next binary questions

1. Connect the now-checked original line kernels to full-stage timing and presentation cadence, including VIC contention and setup overhead.
2. Extend the sphere's edge/fill, visibility, and palette traces across its distinct presentation modes.
3. Measure the patterned model's per-frame transform, culling, boundary, and fill work before comparing cost with our renderer.
4. Classify tables from their consumers. A multiplication or slope table is not a complete-frame animation; a frame-command stream is not proof of runtime geometry.
5. Read VIC mode, memory bank, screen/charset/bitmap pointers, and relevant raster changes during the actual stage. Do not infer those from a scaled video screenshot.

No production renderer source or build output was changed by this investigation.
