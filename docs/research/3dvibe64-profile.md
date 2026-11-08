# Stock Gouraud: most elapsed work is in spans and the two edge passes

Three natural renders of the unchanged stock PAL Mode 6 octahedron took **590,499 / 543,692 / 676,134 emulated machine cycles**. In the third render, which first reuses buffer B, span drawing accounts for **38.4%**, XYQ2 geometry bounds **17.8%**, and shade edges **16.2%**. Lighting is **1.0%** and rotation plus lazy projection **2.1%**. For this observed workload, the rasterizer dominates the arithmetic that establishes the 3D pose and lighting.

These are **elapsed PAL machine-clock costs including VIC stalls and IRQ work**, partitioned exclusively within the selected traced call hierarchy. They are not retired-6510 instruction counts or a general worst-case result. The case covers three poses of this one scene. The [linked plan](3dvibe64-profile-plan.md) explains every anchor and tail jump; native pixel acceptance is a separate check.

## Measured partition

| Exclusive bucket | First B render | Second A render | Third B render | Third share |
|---|---:|---:|---:|---:|
| Span drawing | 282,624 | 237,085 | 259,720 | 38.41% |
| XYQ2 geometry bounds | 89,536 | 92,145 | 120,112 | 17.76% |
| Shade-edge interpolation | 77,630 | 87,120 | 109,402 | 16.18% |
| Row setup and dirty tracking | 51,314 | 50,588 | 62,189 | 9.20% |
| Material load and Screen/Color RAM spans | 59,806 | 45,204 | 47,745 | 7.06% |
| Dirty bitmap clear | 21 | 19 | 42,544 | 6.29% |
| Angles/matrix, rotation/depth, lazy projection | 11,783 | 13,075 | 14,360 | 2.12% |
| Face collection/culling/bucketing, excluding projection | 7,741 | 8,091 | 9,047 | 1.34% |
| Light setup, vertex shades and face reflectivity | 6,881 | 7,111 | 6,954 | 1.03% |
| Other setup, traversal and caller overhead | 3,163 | 3,254 | 4,061 | 0.60% |
| **Sum / exact render interval** | **590,499** | **543,692** | **676,134** | **100%** |

The first two clearing intervals target buffers initialized clean. The third render is the first B reuse and therefore provides the dirty-clear measurement. This does not establish clearing cost for every subsequent rotation or a full-clear crossover threshold.

A theoretical Amdahl calculation puts the scale in perspective. The third render consumes **34.40 PAL refresh budgets**; eliminating its rotation/projection bucket alone removes only **2.12%**. Even assigning **zero cost** to both spans (259,720) and both edge passes together (229,514) leaves **186,900 cycles, or 9.51 refresh budgets**. Under the simplified assumption that every other measured cost stays fixed, those two local optimizations alone cannot reach a 19,656-cycle, 50 Hz render budget. This is a hypothetical accounting limit, not promised performance or a cycle-accurate prediction: shortening a render can also change VIC phase and interrupt incidence.

`gouraud_fill_bounds` is an inclusive parent of row setup, material spans and bitmap spans. For example, its third-render inclusive total is **369,261**, consisting of row setup/dirty tracking **62,189**, material spans **47,352**, and shade spans **259,720**. Material *loading* adds another 393 elsewhere, producing the table's total 47,745. Adding inclusive fill and span totals would count the same work twice.

Geometry bounds and shade edges are separate actual passes. Geometry follows the linked `$95DD→$95E0→$AC96` XYQ2 path; shade endpoints then interpolate through `$9232`. The nominally named `rotate_project_vertices` only rotates/stores depth here. Projection is lazy inside face visibility collection and was measured separately at `$9051`, then subtracted from the collection bucket.

## Executed span paths

| Observed work | First | Second | Third |
|---|---:|---:|---:|
| Drawn face calls | 4 | 4 | 5 |
| Completed logical spans | 168 | 159 | 203 |
| Inclusive logical pixel visits | 3,780 | 2,656 | 2,666 |
| General-route spans | 140 | 144 | 192 |
| Uniform bulk-route spans | 28 | 15 | 11 |
| General full-byte groups | 740 | 505 | 502 |
| General partial-byte groups | 162 | 218 | 282 |

These pixel visits include painter overdraw; they are not a unique visible-pixel count. The byte-group columns cover only the general path. The uniform route has its own full-byte loop and is represented by its span count, rather than those two group markers.

The 4/4/5 figures count instrumented pipeline draw calls, not independently correct visible faces. Why this convex octahedron submits five calls in the third pose remains a bounded geometry/culling question; this cost audit does not resolve quantization, edge-on or degenerate-face behavior. It does not affect the attribution of work the actual pipeline performed.

All **530 spans** have exactly one observed general/uniform marker. An independent packed Bayer calculation from the captured endpoints, shades and row phase agrees with every classifier choice. The general full/partial group counts also match the independent partition of each span by four logical pixels per byte. All traced full-byte LUT operands select the actual span's `yrow mod 4` table. A short constant-looking span can legitimately use the general route because the classifier is skipped below eight inclusive pixels; the general path is not synonymous with visible shade variation.

## Exact intervals and capture lineage

| Render | Begin `$08CB` clock | Complete `$08D4` clock | Render cycles | Next begin period |
|---|---:|---:|---:|---:|
| First | 3,280,108 | 3,870,607 | 590,499 | 612,884 |
| Second | 3,892,992 | 4,436,684 | 543,692 | 549,791 |
| Third | 4,442,783 | 5,118,917 | 676,134 | 688,964 |

Fourth begin is **5,131,747**. The three render intervals equal **30.04 / 27.66 / 34.40 PAL frames** of 19,656 machine cycles; these are clock equivalents, not a wall-time or physical-hardware FPS measurement. The next-begin periods additionally include presentation/tick work. The elapsed gaps after rendering are 22,385 / 6,099 / 12,830 cycles.

Root alone launched and controlled native case `build/research/3dvibe64-profile/native-01`, now closed: **29 files / 14,444,407 bytes**, case digest **`13bfd23f30bf0b7a2db7a9e8dc4ceb8dc69e77d81c76862fe9b372a1f23ef714`**. The immutable case includes raw input/sent/received wire, events, logs, closure metadata and 11 full RAM/snapshot pairs: start; three begins, shade baselines and completions; fourth begin. Every RAM file equals snapshot C64MEM; monitor registers, MAINCPU clock/PC/SP/flags/ports and VIC beam agree. At `$080D`, all **49,709 loaded PRG payload bytes** equal the original linked product.

The passive producer checks all **153 serialized completed monitor commands**, their raw wire boundaries and explicit owned-process closure/reaping. It allows only retained read operations, read-only trace attachments, debugger checkpoints and host RAM/snapshot saves after the declared PRG autostart loader injection. There are no manual runtime RAM/register/PC writes or snapshot restores. All 46 planned trace IDs, addresses and attached commands match their actual arming receipts.

Three rejected read-only resource queries remain visible: unquoted `Speed`, unquoted `WarpMode`, then quoted unknown `WarpMode`. Valid quoted `Speed` reads at command 9 and 148 return 100; `InitialWarpMode` at 18 and 149 returns 0. Launch arguments contain `+warp/+autostart-warp`, disabling warp at startup. **Current runtime warp was not successfully queried.** Official VICE's `InitialWarpMode` resource is separate from the current `warp_enabled` variable; the report does not convert these resource reads into a current-warp or wall-time claim.

## How pairing avoids false attribution

First/second/third trace streams concatenate response pairs **85+98 / 112+119 / 133+140**. The natural `$1153` shade-baseline stop splits a still-open shade-update call; the parser keeps that call open across the two responses. It derives each entry's return address from the full actual page-one stack dump, checks the linked JSR continuation and parent stack depth, then closes it only when the **observed continuation PC and SP both match**. The interval therefore contains the actual RTS and any VIC/IRQ delay, rather than a guessed nominal six-cycle return.

Tail fill `$9455` inherits the face call's return `$4030` and SP. One actual return closes fill and its outer face at the same clock; the inclusive parent-child subtraction counts it once. XYQ2 starts after two wrapper JMPs, so those JMPs remain in the face residual. Uniform `$A143` is a path marker under `$A000`, never another pushed call. The result has no open entries and the sum of exclusive nodes equals every full render interval exactly.

Matching only the continuation PC would be wrong. `$4317` also executes as the triangle branch's convergence even though its fourth, quad-only projection JSR did not run; there are 4/4/5 such flow hits. In the A-buffer render, `$94D8` is also the A/B convergence and has 159 hits without B-material calls. These are retained as unmatched *flow hits*, not fabricated returns. Actual lazy-projection calls are 12/12/15.

Official source provenance is pinned to `build/research/quondam/hardware-source/vice-3.10.tar.gz`, SHA **`8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1`**. The receipt records member hashes and exact line guards: `src/6510dtvcore.c:437–442,1763,1792,1804` establishes the exec-checkpoint boundary before instruction fetch; `src/monitor/mon_breakpoint.c:573,596,602` binds raster sampling, current-instruction disassembly and attached dump execution; `src/monitor/mon_disassemble.c:1633` binds the register/clock formatting path. `src/vsync.c:153,156,191` distinguishes runtime warp state from its initial resource. No source is copied or executed by this check.

## Passive reproduction and continuation

```sh
rtk proxy python3 -B research/3dvibe64-profile/native_profile.py --output build/research/3dvibe64-profile/profile-analysis/root-replay-01
```

Use a fresh output directory. The producer reads pinned closed evidence and writes only the named output directory; it starts no emulator, subprocess, CPU model, build tool or live connection. Output-directory names do not affect receipt bytes. Accepted outputs are under `profile-analysis/accepted-02/`:

| Output | Bytes | SHA-256 |
|---|---:|---|
| `profile-proof.json` | 33,880 | `ebf994a2f7ed0a211cf98a2a112ea2d2b055de04a493484d238717736c42942a` |
| `span-records.json` | 364,215 | `9dc2145badd95d98401b68938c437448160ff3ed8a80a20bce40b4c5cd79c18b` |
| `intervals.json` | 490,677 | `a85f51572e824a88fade3fb20a0289dbc349772a6f97e6bd2b94083d935c6119` |
| `trace-events.json` | 2,169,152 | `8b0235ca910be7b907c264b7b0b754f2d4dba48a7a986a42cb2f6231c82214ba` |

The initial passive output has identical bytes. The accepted replay also checks each traced parent stack-depth relationship and the full-byte Bayer operand against the current span row. No additional native actions occurred in this audit.

A next optimization experiment should preserve these unmodified products and compare one candidate against the same span inputs and independent scalar pixels. These measurements prioritize byte-span work and the two edge passes. They do not yet identify a safe product change, prove a candidate's speedup, or establish correct displayed pixels; those require their own bounded evidence. Interrupt costs remain where they occurred because this case has no separate IRQ-only timeline.
