# Second Reality: the native EA/EB bridge and EC continuation

The owner-closed `native-04` session continues the original C64 program from the saved DB iteration D. All **15 raw RAM/snapshot pairs, totaling 983,040 RAM bytes**, agree exactly. Every snapshot's CPU state and VIC beam position agrees with its recorded monitor stop. The one restored state also matches its parent in all 65,536 RAM bytes, the complete `MAINCPU` snapshot payload, recorded registers, CPU-port bytes and beam position.

This is a snapshot continuation of [native-03](second-reality-native-next.md), not another cold boot. The [original boot and DOS inputs](second-reality-native.md) and earlier continuations remain separate, frozen evidence. This session introduces no further synthetic inputs or code/PC edits. Its source mechanisms and bounded drawing oracle are documented separately in [the EA/EB and EC analysis](second-reality-ea.md).

The capture owner restored `native-03/db-iteration-d.vsf` once. Immediately after `undump`, the original program was still at `$C200`, clock **319,023,529**, raster **105**, cycle **34**. The parent snapshot SHA-256 is `fd7bb2839aafaa31b719480e4f5d9db765a967e84dbbea93ae541c14f05d6089`; its RAM SHA-256 is `0d64ab7ed0af10fe863ab8bba136dae88100a1798f3c811ca3a5c31a3a6a488c`. The checker pins the complete native-03 receipt, SHA-256 `89b12a2aa1c506653e3924b0e8ac24970cc575005ec321d6690f709b247bd825`, before using either reference.

The mounted original side-one disk remains SHA-256 `05aa03c00be26cab0618f8802477d0bc7226af029c003a253a34bd32c630acf2`. No disk was acquired, reparsed or executed by this checker. The native session started at **2026-11-07 13:28:29 UTC** and was closed by its owner at **13:40:38 UTC**. The VICE cleanup exit code was `-15`; the controlling helper exited normally. This is an explicit capture-session closure, not a claim that the demo naturally terminated.

All accepted checkpoints appear below. Cycle values are the monitor's raw cycle numbers. The repeated `$CA88` stops are logical paired-draw boundaries, not whole-frame boundaries.

| Capture stem | PC | Clock | Raster / cycle |
| --- | --- | ---: | ---: |
| `restored-db` | `$C200` | 319,023,529 | 105 / 34 |
| `ea-entry` | `$2E00` | 329,109,653 | 146 / 47 |
| `eb-bridge` | `$3F50` | 329,475,962 | 33 / 11 |
| `ea-restored` | `$6C00` | 329,552,794 | 4 / 46 |
| `ec-load-call` | `$6DE1` | 329,591,715 | 310 / 33 |
| `ec-load-return` | `$6DE4` | 331,937,955 | 112 / 27 |
| `eb-restored` | `$6DE7` | 332,014,673 | 82 / 11 |
| `ec-entry` | `$C000` | 334,902,833 | 61 / 62 |
| `ec-prepared` | `$CA80` | 335,386,812 | 256 / 12 |
| `ec-iteration-a` | `$CA88` | 335,386,822 | 256 / 22 |
| `ec-half-a` | `$9C02` | 335,487,460 | 293 / 49 |
| `ec-iteration-b` | `$CA88` | 335,573,366 | 97 / 23 |
| `ec-iteration-c` | `$CA88` | 335,742,583 | 287 / 22 |
| `ec-iteration-d` | `$CA88` | 335,914,008 | 200 / 24 |
| `ec-visible-end` | `$CABC` | 356,241,532 | 251 / 31 |

`ec-load-call` is **before** the original `JSR $CF00` at `$6DE1`; it is not a stop inside the loader. Its actual registers are `A=$08`, `X=$45`, `Y=$43`, requesting EC. `$CABC` is the source-derived exit of the visible parameter sequence, before the wipe; no ordinal part name was guessed from that address.

The transcript audit admits only the one pinned `undump`, register reads, `sidefx off`, `bank ram`, execution breakpoints and their deletion, resume, full-RAM saves, snapshots and PNG captures. It retains all **108 commands** and their line numbers in the receipt. There are **zero recorded synthetic inputs, direct RAM writes, code writes, register/PC writes, rejected timeout observations or missing capture paths** in this session. These statements concern the archived monitor transcript, not an external audit of every host activity.

The checker pairs each `ram-<stem>.bin` with `<stem>.vsf` by its explicit filename and requires the same recorded stop for both. It compares every physical RAM byte, without exclusions, using the pinned `C64MEM` reader. It separately reads `MAINCPU` registers/clock and VIC raster state from the snapshot; these must equal the monitor register query. It also requires exactly the 15 known RAM files, 15 snapshots and five PNGs, so a stray or unclassified capture cannot disappear from the result. No emulator, CPU interpreter or process is started by the passive check.

The independent source receipt `ea-analysis/ea-proof.json`, SHA-256 `3d0b9fac1f2ceb6926b55b9dfea86bcf9caafe2050c717137449f57e0584301e`, supplies **24 exact domain checks**. This passive receipt pins that result, its source/helper/dependency hashes and all exposed artifact hashes, then joins every one of its 15 capture identities to the independently parsed native records. The source contracts distinguish original file payloads from full-page restores containing preserved stale and loader bytes. They establish EC's prepared complementary bit planes, generated drawing programs and indexed OR stores without inventing the 480 initially undefined operand bytes.

There is an important limit to the drawing proof: strict RAM-only CPU execution stops before the mapped KERNAL read at `$99E2`. The complete **2,976-store indexed oracle** is conditional on original prepared bases and lookup tables; it agrees with the native half-draw's 6,144-byte character buffer. It does **not** supply a continuous CPU/register proof through the full `$CA88` to `$9C02` half. The source receipt retains all **36 whole-RAM differences** outside its exact comparison domains. Neither this lifecycle receipt nor the source receipt masks those differences to assert whole-machine equivalence.

Five PNGs are archived at `ec-prepared`, `ec-half-a`, `ec-iteration-b`, `ec-iteration-d` and `ec-visible-end`. Each file is decoded and hashed, and its capture stop is bound to the matching snapshot. The final image shows the diagonal tiled display; the earlier preparation and drawing images are observations at their recorded beam phases. No independent full-field pixel reconstruction, stable global palette, analog blending, sound, drive timing or display-rate proof is asserted. The 100,638-clock half and varying paired-draw intervals remain logical work intervals, not coherent-frame FPS.

Reproduce only the passive checks with:

```sh
rtk proxy python3 research/second-reality/native_ea.py
```

The [checker](../../research/second-reality/native_ea.py) writes `build/research/second-reality/native-ea-analysis/native-ea-evidence.json`. That receipt contains the final checker hash, parent/source proof pins, session and transcript hashes, complete command audit, every RAM/snapshot/PNG identity and the full comparison results. A byte-identical checked script is archived beside the receipt. No original capture or earlier receipt is overwritten.
