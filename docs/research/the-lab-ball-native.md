# The Lab: original side-two ball, native custody

The fresh original-disk run now contains the missing publication evidence: the ball's pending bitmap/screen, the IRQ bank selection **before** ColorRAM copying, the completed ColorRAM copy, the cleared request, and two following field endpoints. This is the multicolor bitmap scene framed by the cyberpunk portraits. It is separate from The Lab's earlier all-border sprite-vector part.

The accepted receipt is [ball-native-proof.json](../../build/research/lab-polygons-20261109/native-analysis/accepted-01/ball-native-proof.json), **238,618 bytes**, SHA-256 `123732a8293916ffc9648b51686eeff314f1d0a9b371756efaab975976d968e5`. The passive producer is [ball_native.py](../../research/the-lab/ball_native.py), **38,652 bytes**, SHA-256 `5457848099a3c2bc5b596d5f60eb0eb541e894b59eaec4cdc0865ce1e97ae163`.

This receipt proves retained observations and their original-byte bindings. Independent edge, attribute, publication and pixel predictions belong to their own producers. Replaying captured writes below is an observation-consistency check, not an independent attribute algorithm.

## Closed case and failure custody

Root alone owned the native process. `native-02` used original `side2.d64` as **both** `-autostart` and drive 8, with a true 1541, PAL, and default resources. It started on 2026-11-09 at 06:03:26 UTC and was terminated/reaped at 06:18:53 UTC, PID 99881, port 51287, exit −15. There were no program-counter or payload writes, snapshot restores, disk changes, restart/retry, or injected decoded assets.

[native-02-files.json](../../build/research/lab-polygons-20261109/native-02-files.json) is 10,928 bytes, SHA-256 `9c0db5a102cdf10682e52a139708572ef5b210714094b6362a58607a29687465`. Its exact 48-file inventory is **4,782,035 bytes**, canonical listing SHA-256 `47bffc8f059b0b88437c1638430808845bcf40578a1da9cabde659bae474bc2e`. All raw input, sent bytes, received bytes, JSON events, session metadata, snapshots and exports are retained.

The earlier [native-01](../../build/research/lab-polygons-20261109/native-01/session.json) is a separate **host startup failure**, not C64 evidence: `OSError(22, 'Invalid argument')`, zero commands and zero captures, seven files / 3,935 bytes. The retained [diagnostic](../../build/research/lab-polygons-20261109/native-launch-diagnostic.json) attributes it to Kqueue registration of redirected `/dev/null` stdin; root's fresh tty-backed launch corrected that observer problem. Its manifest is [native-01-files.json](../../build/research/lab-polygons-20261109/native-01-files.json), SHA-256 `e92365e77f85ac2ea6f1d39178a57cbf24fd4135f4ccaa6589a0807b48745403`.

The successful case contains **177 response records**: 175 public ordinary commands plus two internal initialization commands; 176 completed responses and one interrupted response. Every raw byte interval and command/event relationship is checked by the frozen wire auditor. Command-list SHA-256 is `325d6ed22d9b64d5a8868ce4056668d7a6e644f648b2cdb63b276157f2e1a020`.

One late optional request failed and is explicitly excluded:

- Sequence 152's oversized full-color breakpoint expression was rejected by the monitor with two syntax errors. It created **no breakpoint**. Only this exact command/response hash is allowed; other monitor errors fail acceptance.
- After all watches/checkpoints were deleted, sequence 161 resumed execution without a remaining stop. The observer waited 30.08 seconds once, then root sent a read-only `r` interrupt on that same pending command. Actual stop: **$7234, clock 599,016,604, raster 0/cycle 4**.
- The queued `fullcolor52-body-entry` RAM/VSF/ColorRAM exports are retained as the fourteenth pair, with `accepted_natural_phase=false`. They are not a body-entry, palette precondition, scalar input, or publication target. The receipt records the absent active breakpoint rather than pretending that an intended condition failed at that point.

## Original boot and source bindings

The original [release ZIP](../../build/research/the-lab/the-lab.zip) has SHA-256 `ea4ab6a4f3c8b10a412e80e3a4f46f240405cf2a820a526f222af2b5e0e48717`. Its `side2.d64` member is byte-identical to the booted [retained disk](../../build/research/the-lab/release/side2.d64), SHA-256 `d34101d9b5852020ed56b3574aae854c7b16befff893df77a6d6ec08198cdf3b`.

The DOS directory labels its first closed PRG as one block, but its **actual linked chain is track 18, sectors 2 through 11**, yielding 2,510 bytes. The passive sector walk recovers exactly [side2-bootstrap.prg](../../build/research/the-lab/side2-bootstrap.prg), SHA-256 `a1d61674083c1c8f5b7e7532a0b6709ebdd897375ba26d23e0892042ebe25d78`. It loads at $0801 and contains BASIC `SYS 2061`, entering $080D. Thus direct original-disk autostart is the authentic DOS boot path; this PRG is not custom file 0 or an invented emergency loader.

The natural $080D stop matches **all 2,508 bootstrap payload bytes**. Natural custom-file-zero entry $0480 matches **all 7,162 original decoded output bytes at $0400–$1FF9** against the frozen original-release extraction. The two following bytes $1FFA/$1FFB are separately bound to the packed file's untouched `DD 00` tail; they are not described as depacker output.

The natural $2118 stop is the common engine's `JSR $8C00`, under the original `DEC $01` / `INC $01` wrapper. It matches **all 14,156 original file-22 payload bytes at $8C00–$C34B**. Later accepted ball captures keep the original code prefix and $9026–$C34B stream intact; the 16-byte palette at $9016 is treated as mutable runtime data. The current stream pointer remains $BFE8 through rendering and publication. It advances to $C0B5 before the later field endpoints, so those endpoints are not relabelled from their current pointer as a newly displayed generation.

Every source guard in the frozen [display-source contract](../../build/research/lab-polygons-20261109/display-source-analysis/accepted-01/display-source-proof.json) is checked against the original file-20 written-mask/code or file-22 PRG and against **all ten accepted ball-stage snapshots**. This covers mode setup, the script call, IRQ/port wrapper, both bank branches, copy/request order, and render entry. It does not assert that the entire old file-20 RAM image remains unchanged after later assets and generated code.

No depacker, 6502 interpreter or downloaded host code is executed by the custody producer. Frozen earlier decoded original bytes are compared to the untouched natural run. Trace instruction bytes that come from runtime-generated or modified code are labelled as earlier natural native context instead of being passed off as static original bytes.

## Same-stop captures

Each of the 14 pairs retains strict equality for every physical RAM byte between the 65,536-byte export and VSF `C64MEM`, plus CPU clock, PC, A/X/Y/SP, flags, port latch/DDR/readback, and PAL raster/cycle consistency. Thirteen are natural checkpoint phases; the rejected interrupted pair is separately labelled.

| Natural phase | PC | Absolute clock | Raster / cycle |
|---|---:|---:|---:|
| DOS SYS | $080D | 10,780,741 | 146 / 55 |
| Custom file 0 entry | $0480 | 13,368,416 | 37 / 5 |
| File 22 script call | $2118 | 231,623,664 | 270 / 6 |
| Ball full body entry | $21BD | 237,344,345 | 282 / 35 |
| Edge entry | $2209 | 237,344,381 | 283 / 8 |
| Events ready, before wait/fill | $224E | 237,370,833 | 79 / 0 |
| Render complete, before request | $2265 | 237,431,554 | 106 / 52 |
| Request queued | $2267 | 237,431,559 | 106 / 57 |
| Banks selected, before ColorRAM copy | $21A9 | 237,441,570 | 265 / 51 |
| ColorRAM copied, before decrement | $21AC | 237,447,041 | 40 / 41 |
| Request cleared | $21AE | 237,447,046 | 40 / 46 |
| Following field endpoint A | $23D0 | 237,464,137 | 0 / 1 |
| Following field endpoint B | $7BF8 | 237,483,796 | 0 / 4 |

Breakpoint predicates are parsed and evaluated against each actual stopped RAM/register state. Unknown predicates are rejected. The exact sequence-152 syntax rejection is skipped without assigning an ID or generation. All successful checkpoint generations were removed before closure.

The true attribute prestate is **`ball52-edge-entry`**; `ball52-body-entry` provides the preceding entry guards. The captured palette is `00 01 0E 01 04 01 01 01 01 01 0A 0B 01 0D 01 01`, not an assumed identity palette. This partial palette is meaningful original runtime input; the rejected late full-color export supplies no replacement values.

## Actual modes, ColorRAM and publication

[capture-machine-context.json](../../build/research/lab-polygons-20261109/native-analysis/accepted-01/capture-machine-context.json), 1,151,399 bytes, SHA-256 `a9cb01ba1dbf89bde00215ab5c0fad5de46f373ff252075b2c98cb98f74f5c60`, preserves every frozen core snapshot field and the source-guarded VIC draw/raster tail. The actual resource queries bind **VICIIModel=1 (MOS8565), normal border mode 0, Speed=100, warp off**, and checkpoint dummy accesses disabled. No constant DDR is inherited from another demo: actual ball DDR is $37. Render code uses port $34; the IRQ maps I/O with $35. Actual EXROM/GAME are both zero.

Every accepted ball-stage snapshot has **D011=$3B, D016=$D8, D015=$00**. This is ordinary multicolor bitmap mode with no enabled sprites in this observed window. It does not support a polygon-per-sprite explanation of this ball.

| Phase | $43 / $44 | CIA2 PRA / DDRA | D018 stored | Derived VIC bank | Screen / bitmap |
|---|---|---|---|---|---|
| Through render done | 00 / 00 | 00 / 3F | 78 | C000 | DC00 / E000 |
| Request queued | 00 / 01 | 00 / 3F | 78 | C000 | DC00 / E000 |
| $21A9, before copy | 01 / 01 | 02 / 3F | 80 | 4000 | 6000 / 4000 |
| $21AC, after copy | 01 / 01 | 02 / 3F | 80 | 4000 | 6000 / 4000 |
| $21AE and both endpoints | 01 / 00 | 02 / 3F | 80 | 4000 | 6000 / 4000 |

CIA2 drives both bank-select pins; this is not a guess from PRA alone. Raw GLUE state is also preserved (`01 03 00` before and `01 01 00` after). The source contract records that DD00 changes before D018, and that $21A9 precedes ColorRAM copying; the bank switch and ColorRAM update are not described as atomic.

At every available ColorRAM export, the command explicitly selects monitor **bank I/O**. All **1,024 low nibbles** equal the actual VIC-II snapshot ColorRAM array at the same stop. Hardware ColorRAM is kept distinct from physical $D800 RAM: renderer port $34 can write that physical address range while I/O is absent. Export high nibbles vary with the emulated bus ($40 or $90 in these captures) and are never used as palette data.

The $21A9 device ColorRAM is still identical to render-done ColorRAM. Sequence 113 then contains **484 unique ColorRAM stores**, CPU port $35, and **26 device nibbles change**. Replaying those observed low-nibble stores exactly reconstructs all 1,024 post-copy device cells. This proves capture/publication consistency, while the independent publication producer must predict the copied values from original source and true prestate.

## Watch and viewport oracles

[trace-hits.json](../../build/research/lab-polygons-20261109/native-analysis/accepted-01/trace-hits.json), 818,319 bytes, SHA-256 `ed2f24ff2315f5978fe76a6099fbf460162ae2031024a9e1866aa09fc3ae4f30`, contains all **1,015 ordered store hooks** from six resumes. Their declared ranges are $0000–$0001, $D000–$D3FF, $D800–$DBFF, $DD00–$DD03, $9016–$9025, and $C380–$C7FF. Each record preserves source instruction bytes/PC, attached `r` registers/ports, absolute clock/beam, checkpoint generation, exact received-byte offsets, and raw block digest. Parsing uses Latin1 solely to retain byte offsets; original event UTF-8 replacement decoding is independently checked unchanged.

The source-byte references distinguish original file-20 written code from earlier natural generated/modified code. Attached-register PC is recorded as observed; it is not forced to equal the store instruction's PC plus length. Watch counts are monitor hooks with dummy accesses disabled, not all physical NMOS bus transfers. These ranges do not establish a complete bitmap/screen RAM-write history.

The extended VIC-II 1.3 reader decodes the pinned 123,415-byte model-1 payload and keeps its old core fields unchanged. It supplies the padded drawbuffer geometry and the update-at-beam lifetime contract. At both natural raster-zero endpoints, the normal **384×272 viewport, raster rows 16–287**, was committed during the preceding field. The current accumulating raster-zero line is outside that declared viewport.

The two extracted viewport-index oracles are byte-identical, each 104,448 bytes, SHA-256 `191104b69c5494fa23b23ffd88847313a3091007cb611554fc4e83b8a55cd66d`:

- [Endpoint A viewport](../../build/research/lab-polygons-20261109/native-analysis/accepted-01/ball52-wrap-a-retained-viewport-384x272.bin), actual raster 0/cycle 1.
- [Endpoint B viewport](../../build/research/lab-polygons-20261109/native-analysis/accepted-01/ball52-wrap-b-retained-viewport-384x272.bin), actual raster 0/cycle 4.

Their stops are one PAL frame plus three cycles apart. This gives stable, completed native viewport data for a later compositor oracle. It does **not** independently explain those pixels, validate all 312 allocation rows, measure FPS, or prove cycle-accurate real-hardware timing. The stopped, trace-instrumented run must not be used as a normal-speed benchmark.

## Replay and continuation

Fresh self replay reproduced **all seven accepted files / 2,490,776 bytes exactly**; see [self-replay-check.json](../../build/research/lab-polygons-20261109/native-analysis/self-replay-check.json), 1,326 bytes, SHA-256 `c445d220cf4f5d4bb75186dd0648ef26023051549c8f4f5669e1802ab0ae9459`.

Root independently reviewed the complete producer and reproduced those same seven files / 2,490,776 bytes exactly. [root-replay-check.json](../../build/research/lab-polygons-20261109/native-analysis/root-replay-check.json), 2,004 bytes, SHA-256 `28d23a183b081ae58d68ada6a9645e99b2c1fff664b33c8cf14f20301ff2af18`, also independently asserts that all six watch setups and attached `r` commands preceded the edge-entry resume and that deletion followed the wrap-B snapshot **and** ColorRAM export. No producer or accepted-output change was required.

The producer's adaptations are deliberately narrow: original-D64 startup assertion; pair DDR equality without a foreign fixed constant plus the one exact interrupted export; and the one rejected breakpoint setup. The ordinary and interrupted register parsers remain strict. Candidate-01 and candidate-02 retain checked source/failure receipts for observer spelling assumptions (`screenshot ... 2` and prompt-only `sidefx off`), while candidate-03 is the preceding successful run. None is overwritten.

To repeat only the passive custody check, choose a fresh output directory:

```sh
rtk proxy python3 -B research/the-lab/ball_native.py \
  --output build/research/lab-polygons-20261109/native-analysis/replay-NEW
```

Consumers should pin the accepted receipt, then resolve `captures[]` by `stem` and require `accepted_natural_phase=true`. Context fields live under `capture-machine-context.json → captures[stem] → summary` and `frozen_core_and_extended_state`. Use the original edge-entry palette/state as input, render-done and post-copy states as oracles, and the ordered watch history only for comparison. Keep the rejected late pair excluded. No further native launch is necessary for these retained inputs.
