# Next Round: original fullscreen renderer timing

Research date: 8 November 2026. The original round-3 renderer consumed all
**536 prepared frame records** in an unchanged PAL VICE run. There are
**535 complete main-loop periods and 535 queued, changed screen/charset
publications**. The final record reaches the production's scene handoff
without its normal return, border copy, request or publication. It remains
explicitly censored rather than counted as another displayed frame.

This measures the original prepared-2D renderer described in
[the scene analysis](next-round-scene.md), not runtime Gouraud shading.
The [author's article](https://codebase64.net/doku.php?id=base:fullscreen)
explains the dynamic charset approach: partial boundary glyphs are drawn,
while complete interior tiles use shared pattern characters. The C64 still
performs edge stepping, allocation, filling, cleanup and presentation work.
The supplied scene has already selected its 2D fragments and pattern IDs.
The missing exporter and its original 3D algorithms remain unknown.

## Exact elapsed-cycle partition

These intervals partition all **31,951,837 cycles** in the 535 complete
main-to-next-main periods. They include VIC bus stalls and IRQ execution
where those occur. They are not exclusive retired-6510 instruction costs.

| Phase | Total cycles | Share | Median per complete period |
|---|---:|---:|---:|
| Buffer setup and old screen/glyph clearing | 3,577,688 | 11.1971% | 7,194 |
| Polygon body: patterns, edges, allocation and filling | 26,752,377 | 83.7272% | 38,563 |
| Frame terminator bookkeeping and normal return | 13,355 | 0.0418% | 22 |
| Top/bottom border sprite-copy path | 79,794 | 0.2497% | 30 |
| Wait for prior selection and request next buffer | 1,488,094 | 4.6573% | 13 |
| Metadata for future clearing and next-loop setup | 40,529 | 0.1268% | 71 |
| **Complete main-to-next-main period** | **31,951,837** | **100%** | **47,636** |

The full 536 polygon-body intervals total **26,787,596 cycles**, with
minimum **3,574**, median **38,380.5**, maximum **170,247**. The bodies are
not constant-cost: geometry, boundary work and allocation differ between
records. The complete-period minimum/maximum are **8,617 / 180,843** cycles.

Request-to-publication latency totals 6,928,305 cycles over 535 requests
(median 14,053; range 128–19,569). This overlaps subsequent rendering work;
do not add it to the partition above.

## Screen/charset selection cadence

The IRQ executes the original `STA $D018` at `$FF3D`. The `$FF40` marker
observes its completion, before the next instruction acknowledges it in
zero-page `$22`. This changes screen/charset selection inside the selected
VIC bank; it is not a CIA bank switch.

The trace contains **1,628** such IRQ observations: one initial selection,
**1,092 repeats** and **535 changed selections**, each joined to one unique
pending render request. The initial selection is not another queued frame.

| PAL fields between selections | Initial-to-first plus changed-to-changed | Changed-to-changed only |
|---:|---:|---:|
| 1 | 168 | 167 |
| 2 | 102 | 102 |
| 3 | 68 | 68 |
| 4 | 56 | 56 |
| 5 | 63 | 63 |
| 6 | 49 | 49 |
| 7 | 17 | 17 |
| 8 | 10 | 10 |
| 9 | 2 | 2 |
| **Intervals** | **535** | **534** |

Field gaps use actual clock/beam pairs and **19,656 cycles per PAL field**.
The initial-inclusive interval range is 19,651–176,904 cycles; sub-line
variation comes from the observed IRQ execution phase. This proves buffer
selection cadence. It does not prove complete committed pixel scanout,
delivered-image FPS, wall-clock emulator speed or physical-hardware timing.

## Original lifecycle and final record

| Boundary | Original production PCs |
|---|---|
| Before each render call | `$0600 / $06A5 / $074A` |
| Common polygon-body entry | `$5D02` |
| Body complete, before advancing terminator | `$5D32` |
| Actual normal return continuations | `$0603 / $06A8 / $074D` |
| Border copy complete, wait starts | `$065E / $0703 / $07A8` |
| Request store complete | `$0669 / $070E / $07B3` |
| D018 store complete | `$FF40` |
| Final production handoff | `$5D44`, `JMP $0418` |

All 536 body entries have actual stack continuation words matching the
expected caller and SP `$FD`; complete caller boundaries have SP `$FF`.
Each input pointer is checked against the parsed original stream. Frame 0
uses the explicit `$0600` register/RAM capture because tracing was armed
while already stopped there.

Final record 535 starts at clock **110,488,808**, enters its body at
**110,501,184**, reaches the terminator at **110,536,403**, then handoff at
**110,536,425**. Those final 22 cycles do not imply a normal return or a
publication. The final prepared data pointer is `$C571`.

The original startup integration initially calls `$0432` from IRQ `$FF6A`.
Its code at `$0496` later replaces that call with `DEC $D019` and sets the
three logo-clear immediates to `$EC`; they reset to `$00` when consumed.
Only those three observed `LDX #$00 / #$EC` operand changes are allowed.
This startup work remains in the measured intervals, not silently removed.

## Custody and reproduction

The original extracted DOS bootstrap autostarts with the unchanged
`round3.d64`, then reaches `$E000` and `$0600` naturally. There is no later
PC, register, payload or disk patch. Navigation warp is declared before
the part; `warp off` executes at `$E000` before every timed interval.
Speed reads are 100. These declarations do not turn cycle evidence into
a host wall-time performance claim.

The closed `build/research/next-round-timing/native-01/` case contains
**14 files / 8,037,504 bytes**, canonical listing SHA-256
`766e62fa105c35fc722de5e540343265a2a825bec8970a677b57ed06cf2ff507`.
The observer reaped its owned process. All 64 ordinary commands completed.
One waiting notice for sequence 59 precedes natural completion of that
same command and socket; there are no retries, interrupts or restarts.

Three full RAM/VSF pairs agree on every 65,536 RAM bytes, CPU ports,
registers, clock and beam. At production entry all **44,525** renderer,
scene and initialization payload bytes match the independently unpacked
original files. The original disk SHA remains
`e1991a76fa7968743e81efd7fd46bd1c4f81cc831512f02b33fb8eef563a4179`.

Passive producers:

```sh
rtk proxy python3 research/next-round-timing/validate_capture.py --output /tmp/next-round-capture-check.json
rtk proxy python3 research/next-round-timing/analyze.py --output build/research/next-round-timing/analysis/fresh-replay
```

Choose unused output paths. Neither command starts an emulator or a CPU
model. The analyzer preserves the frozen wire auditor's checks, changing
only its startup metadata assertion to the exact original bootstrap/disk.
It pins the case, source, input scene, capture validator and capture plan.

Final acceptance is `analysis/accepted-02/timing-proof.json`, **17,586 bytes**,
SHA-256 `43b6ac925b6bff0095635614eb217676af24b775bcdde5222da2bc583b97f6c2`.
The checked producer SHA is
`a1e4883c39dc89c12803345956fda80a4d23a2f717c1d06bf613bd2eaa55774f`.
It emits the compact receipt, 536-row `frames.csv`, 1,628-row
`publications.csv` and its checked source. `analysis/root-replay-01/`
matches every accepted output byte; `analysis/root-replay-check.json`
records that independent root replay. `accepted-01/` is the preserved
intermediate before the additional original-logo guards and separate
changed-to-changed cadence summary.

## What this says about the slow Gouraud preview

The [3Dvibe64 profile](3dvibe64-profile.md) is a different workload: it
performs runtime rotation, vertex lighting and shade interpolation.
Its three renders take 543,692–676,134 elapsed PAL cycles; rotation and
projection account for only 2.12% of the third. Its rasterizer dominates.
The [SDK author's article](https://www.retromind.it/blog/3dvibe64-gouraud-textures-and-raycasting-in-commodores-8-bit-world/)
also motivates its more expensive modes with accelerated C64 machines.

Next Round's supplied coordinates and fixed pattern choice per fragment
remove different work, and its interior-character representation avoids
writing every interior pixel. The two workloads do not establish a
same-scene speedup or a general impossibility result for stock Gouraud.
The next useful research is primary-source genuine stock-C64 Gouraud,
with original code and a clear host/runtime boundary. No SDK, Pong,
production renderer or viewer was changed here.
