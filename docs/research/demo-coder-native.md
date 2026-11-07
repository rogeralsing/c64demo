# Demo Coder: original cold-boot native comparisons

Research date: 7 November 2026. This follows [the offline loader and selector analysis](demo-coder.md). The owner runs the unmodified original disk in VICE C64SC; the checker in this lane only reads the resulting files. It does not start an emulator, interpret a CPU, alter a program counter, or supply loader responses.

The final closed-session check **passes all 36 RAM/VSF pairs and every established byte contract**. The native raster mechanism belongs to the [separate raster contract](demo-coder-raster.md); byte equality below is not a physical-VIC or independent pixel proof. The former provisional receipt remains preserved separately.

## Original route and input

The input is the original 40-track D64, SHA-256 `b8c54fc1ca41c00cd81773ecff780649d892bc6497a84b7c67c79a9235d95e9b`. VICE cold-autostarts the disk with a true 1541 drive. All directory aliases enter the original `SYS2061` bootstrap. The owner reports that the established entry and initialization captures follow the original playback, without PRG injection, skipped entry, manual program-counter changes, or algorithm patches. Later trace/control observations restore an already captured VSF; those interventions belong to the separate causal trace ledger, not a claim that the entire session is uninterrupted. The preserved command, monitor transcript, captures, and close state are in `build/research/demo-coder/native-01/`. The owner closed the session normally at **11:02:55 UTC**.

Warp is used for the long original playback and is disabled when the selected part is reached. The capture clocks below are emulated machine clocks, not wall-clock measurements.

## Established stops

| Stop | Native clock | Register-observed raster | Exact byte contract |
|---|---:|---:|---|
| `$8A00` | 11,838,470 | 88, cycle 14 | All 32,769 original boot output bytes at `$3FFF..$BFFF`. |
| `$8087` | 12,861,027 | 95, cycle 18 | All 508 resident bytes at `$0200..$03FB`, plus their original copy source. |
| First `$E000` | 13,899,256 | 39, cycle 7 | The complete first in-place image, 7,902 bytes at `$E000..$FEDD`. |
| Stream 46 `$6000` | 259,550,128 | 195, cycle 19 | Its complete 40,961-byte image at `$2000..$C000`, before its initializer. |
| Stream 46 `$6237` | 259,848,293 | 248, cycle 5 | The finite initialization copies, clears, Color RAM, and explicit operand/state updates described below. |
| First stream 46 `$62EA` | 259,855,669 | 53, cycle 10 | Original selector-family, target table, and both complete `$D011` pages. |
| Prepared dispatch `$68B9` | 259,875,552 | 56, cycle 48 | Exact family/table, derived table-index-zero target, and the first preparation's 16 data-page changes. |

Every raw capture contains all 65,536 physical RAM bytes and is checked against its same-stop VSF RAM, with no excluded addresses. A register observation must precede the capture, and both its PC and clock must equal the snapshot's CPU state. The final 36 pairs provide **2,359,296 exact raw-RAM/VSF byte comparisons**, separately from the original-image comparisons.

The checker reuses the frozen Nine monitor-context/RAM readers and the pinned VICE 3.10 snapshot schema. For `C64MEM` version 0.1, the 65,536 RAM bytes occupy payload `[4:65540]`; the surrounding bytes are not silently treated as RAM. The owning `mainc64cpu.c` writer establishes `MAINCPU` version 1.4, with clock at `[0:8]` and PC at `[12:14]`. Reader and input hashes are recorded in the receipt, and the CPU writer is preserved under `native-analysis/source/`.

## Why the resident checkpoint is early

`$8087` is immediately after the original indexed copy loop. The resident must still equal `$82B1..$84AC` exactly. Later initialization and loading intentionally modify it: for example, SID detection updates `$020B`, and the resident decompressor changes its own operands. Those later resident differences are retained as observations, not accepted by excluding a broad mutable range or calling the whole resident pristine.

The first wrapper signature is:

```text
8A00  A9 18        LDA #$18
8A02  2C 11 D0     BIT $D011
8A05  10 FB        BPL $8A02
```

The pristine resident breakpoint can be guarded with the original copy-loop bytes:

```text
8076  A2 00 BD B1 82 9D 00 02 BD AD 83 9D FC 02 CA D0 F1
8087  78
```

## Identifying stream 46 without skipping the demo

The address `$6000` occurs in earlier parts. Its selected-part guard uses `$6011=$38` and `$6016=$62`, the immediate low/high bytes of the initial IRQ `$6238`. The full checked entry signature is:

```text
6000  A9 F9 CD 12 D0 D0 FB A9 00 8D F6 01 8D F7 01 78
6010  A9 38 8D FE FF A9 62 8D FF FF A9 00 8D 12 D0 A9
6020  01 8D 1A D0
```

The owner reached this guard through the original whole-disk playback. The full image comparison includes original data, code, tables, and the final byte at `$C000`; it does not compare only an attractive code subset or omit in-place tails.

## Finite initialization, with interrupts acknowledged

`$6237` is the initializer's return instruction. It is **not before all interrupts**: the part executes `CLI` at `$6027`, before calling `$606F`. The early `$6238/$6256` handlers can already run music and schedule interrupts while `$606C=0`. The last main-initializer store publishes `$606C=1` at `$6234`, allowing the later active path. Thus the checker models the initializer's finite RAM effects rather than inventing a pristine whole-machine state.

The oracle starts from the actual, already byte-verified `$6000` capture and implements the literal fixed copy operations:

- 1,000 original bytes from `$4000` go to Color RAM, using their low four bits. The last 24 Color RAM cells retain their entry values.
- 28 pages from `$2001` go to `$4000`, and 28 pages from `$2002` go to `$C000`.
- `$E000..$FBFF` is cleared.
- The 1,000-byte screen source at `$3C00` is copied to `$5C00`, `$DC00`, and `$FC00`.
- The exact source/destination operand advances, final screen-loop tail length, six literal parameters, and publication flag are applied individually.

The full `$2000..$C000` image then matches the derived result. The contiguous RAM range `$C000..$FFE7` also matches, including its untouched gaps. Physical Color RAM comes from the VIC snapshot module and matches all 1,024 cells; RAM under `$D800` is not substituted for it.

The initial version of this **host oracle** incorrectly advanced four unused tail-copy operands. Both 28-page copies have zero tail length, so their `BEQ` skips those tail-parameter patches. Native execution correctly retains the original bytes at `$6133/$6136/$617E/$6181`. The failed receipt is retained as `native-analysis/initializer-oracle-attempt.json`, with an explicit correction note. Only the checker was corrected; this was not an original-demo bug.

## Selector-family and self-modification contract

At initialization completion, all **19,275 bytes** of `$69C1..$B50B` and all **100 target-table bytes** at `$BB64..$BBC7` remain exactly equal to the original stream. The checker also applies these exact comparisons at later identified raster/dispatch captures.

The original code at `$6867` and `$692C` patches only the two target bytes of `JMP` at `$68B9`, selecting from the 50 checked table entries. The initial self-loop target `$68B9` is also valid before preparation. The checker retains the original/actual operand and derives its matching table index; it does not broadly mask a code page.

At the first captured `$62EA`, both complete `$B800/$B900` pages are still original. At the prepared dispatch, the only page changes are `$B8F4..$B8FB` and `$B9F4..$B9FB`, each original byte AND `$3F`. This is derived from the first literal preparation loop: `X=$FB`, `Y=7`, mask both entries, then `DEX/DEY/BPL`. The saved coroutine continuations also equal `$6401` and `$6521`. All 512 page bytes match that exact oracle; no arbitrary bit-mask acceptance is used for other bytes or phases.

All **6,280** differences between the prepared-dispatch full image and the original stream remain recorded, including the initialization copies and these table changes. They are not broadly excluded or all automatically declared harmless. Later phase claims require their actual captured consumer state.

## Later observations and trace provenance

An additional `$68B9` capture at clock **259,896,720**, raster 80/cycle 48, selects **`$7012`, table index 14**. It passes the same exact family/table and derived dispatch-target checks. The remaining **28 captures** cover segment endpoints, beam-point probes, RMW variants, continuation, and visible output. Their complete RAM/VSF comparisons pass, while every later full-image difference remains observational in this checker. The separate raster tool owns the causal store/counter/trace comparisons.

Restored comparisons can have identical PC and clock. The checker therefore pairs each RAM file with its explicitly matching VSF basename, preserving distinct traced and control device states rather than overwriting one in a `(PC, clock)` map. Ambiguous RAM pairings fail.

One original filename needs an explicit provenance correction: **`selector-rmw-clean-return-after-control` is a dummy-off capture with tracepoint 3 still active**. The operator had deleted breakpoint 2 instead of the active tracepoint. The actual untraced replay is **`selector-rmw-clean-return-after-untraced`**, captured after deleting tracepoint 3 and listing only breakpoint 1. Both originals and the complete transcript remain preserved. This note does not assign semantics merely from the word “control” in a filename.

Three same-stop PNGs, [visible A](../../build/research/demo-coder/native-01/selector-visible-a.png), [visible B](../../build/research/demo-coder/native-01/selector-visible-b.png), and [visible C](../../build/research/demo-coder/native-01/selector-visible-c.png), are retained as original-program output observations. No independent full-image pixel oracle is asserted for them.

## Reproduce the passive comparison

During capture, this reads only completed, existing pairs and writes a clearly provisional receipt:

```sh
python3 research/demo-coder/native_capture.py --allow-live
```

The final command requires the closed session and all established stages, and writes `native-evidence.json`:

```sh
python3 research/demo-coder/native_capture.py
```

The [checker](../../research/demo-coder/native_capture.py) records complete mismatch lists, reference hashes, source hashes, transcript hash, session metadata, and capture state. The [final receipt](../../build/research/demo-coder/native-analysis/native-evidence.json), SHA-256 `1e529dea1f97bcf03dd431c279e0bf06d9ca3a8db7386eebfc6dce0109b55609`, distinguishes exact assertions from later observational differences. Its passing status covers the byte contracts above; it does not promote observations into an all-module, frame-timing, or pixel proof.
