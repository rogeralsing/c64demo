# Demo Coder stream 46: a source-derived raster contract

This note maps the original stream 46 register program and tests a bounded native segment against that map. It is **not a complete pixel reconstruction or proof that this stream is the author's MEGA picture**. The separate [release and extraction note](demo-coder.md) establishes the original disk and complete stream images. General native byte matching belongs to the [passive capture checker](../../research/demo-coder/native_capture.py); the raster evidence below uses actual trace clocks and parsed VIC state rather than inferring timing from a byte match.

Trident's distinction between stretching all eight source rows and repeating one row makes the VIC's row counter and graphics-fetch addresses the useful questions. A count of `$D011` writes cannot resolve them. [Author's release comment](https://csdb.dk/release/index.php?id=247776)

## Exact input and reproducible scope

The input is the complete original `046-2000-unpacked.prg`, loading **`$2000..$C000` inclusive**. Its 40,961-byte payload has SHA-256 `3be2386eeb9c9f0d3bb274eab04fd7aa48f7df3b3a10199df3d49cecaabec31c`. This is the current full image, including its in-place raw tail, rather than the rejected prefix-only export. The input index has SHA-256 `307b6de0dd9a5ca8fa81d095260768088bb29d49937a7b0a5772a068e4d3f709`.

[The contract script](../../research/demo-coder/raster_contract.py) pins both inputs, checks the newly mapped instruction sequences, and records the relevant official VICE source excerpts. It **reuses** the [existing selector receipt](../../build/research/demo-coder/selector-analysis/selector-proof.json), which owns the 50 routines and 1,275 cells; it does not repeat that matrix or execute a CPU.

```sh
rtk proxy python3 research/demo-coder/raster_contract.py
```

The [result](../../build/research/demo-coder/raster-analysis/raster-contract.json) includes original signatures, continuation-store PCs, mutation ranges, source hashes, and proposed checkpoints. Its passing status means those finite static contracts hold. It does not mean that the hardware predictions below have been observed.

The hardware reference is the official [VICE 3.10 source archive](https://downloads.sourceforge.net/project/vice-emu/releases/vice-3.10.tar.gz), SHA-256 `8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1`. The script copies only the cited source members into its ignored output directory and records each hash. PAL cycle numbers in the source use hardware numbering; the monitor and snapshot cycle are **one less** (`viciitypes.h:44–57`).

## A frame has an interrupt escape, not a normal loop return

`$6000` installs IRQ `$6238`. A reused `$6000` address alone is not enough to identify this part: the initial vector operands at `$6011/$6016` must be `$38/$62`. Initialization ends at `$6237`. Before its ready flag is set, the top and bottom handlers alternate; afterwards `$62A6` becomes the frame-start handler.

At `$62A6`, the program selects `$FB` in both `$D018` and `$DD00`. It sets horizontal multicolor mode with `$D016 = $18 | ($6700 & 7)`. For `p = 7 XOR ($6704 & 7)`, it writes **`$D011 = $70 | p`** and schedules IRQ `$62EA` on **raster `46+p`**. Thus the initial mode has DEN, bitmap mode, and ECM set together; it is not ordinary valid multicolor bitmap display yet.

`$62EA` performs timer-dependent timing correction, calls `$6706`, schedules raster **251**, saves its stack pointer, installs IRQ `$6336`, acknowledges the current IRQ, and executes `CLI`. The foreground of this outer IRQ then enters the display program at `$68AA`.

The raster-251 interrupt deliberately abandons that program. At `$6336`, `LDX savedSP; TXS` discards the nested interrupt frame and any display-loop subroutine frames. The handler calls the resident service and writes `$1B` to `$D011` at `$633F`, prepares later frame state, then restores the outer register frame and returns. Consequently **`$68BC` is a recurring segment boundary, not a frame boundary**. A complete-frame trace must include this nested-interrupt escape.

## The selected family and its seven-cell continuation

`$68B6` samples the current low raster byte into X **once**. The patched `JMP` at `$68B9` chooses one of 50 prebuilt routines; its pristine target is a self-loop and should not be mistaken for a selected routine. Case `i` executes `i+1` of the following cells, then jumps to `$68BC`:

```text
LDA $B800,X
STA $D011
LDA #selector
STA $DD00
STA $D018
INX
```

The cells are 15 bytes and 20 nominal CPU cycles each, with an aligned indexed load. For cell `j`, the three store instruction PCs are `target + 15*j + {3,8,11}`. This instruction count excludes VIC stalls and does **not** establish one cell per raster line. The preliminary map miscounted the immediate load as three bytes; the actual native trace exposed that error, and these offsets are corrected.

The continuation contains seven additional `$D011/$DD00/$D018` groups. Their `$D011` source is now `$B900,X`; selectors come from prepared variables `$B50D..$B513`:

| Group | `$D011` store PC | `$DD00` store PC | `$D018` store PC |
|---:|---:|---:|---:|
| 0 | `$68BF` | `$68C5` | `$68C8` |
| 1 | `$68EB` | `$68F1` | `$68F4` |
| 2 | `$691F` | `$6925` | `$6928` |
| 3 | `$6945` | `$694B` | `$694E` |
| 4 | `$695B` | `$6961` | `$6964` |
| 5 | `$6971` | `$6977` | `$697A` |
| 6 | `$699B` | `$69A1` | `$69A4` |

Arithmetic between the groups updates motion accumulators, obtains the next index, patches `$68BA/$68BB`, and prepares later selectors. `$69BE` jumps back to `$68B9` without resampling `$D012`. X therefore continues as a software counter; comparing its value with the actual raster at each store is a necessary native check.

## Bank selection and mode gating both affect the fetched image

Each selector byte is written first to CIA2's port and then to `$D018`. Under the ordinary bank decode, with CIA2 low two port bits configured as outputs, the choices are:

| Stored selector | VIC bank | Screen matrix | Bitmap base when BMM=1 |
|---:|---:|---:|---:|
| `$FB` | `$0000` | `$3C00` | `$2000` |
| `$72` | `$4000` | `$5C00` | `$4000` |
| `$70` | `$C000` | `$DC00` | `$C000` |
| `$F8` | `$C000` | `$FC00` | `$E000` |

Initialization copies 28 pages from source offsets `$2001` and `$2002` into `$4000` and `$C000`, and clears `$E000..$FBFF`. This gives the bank selectors distinct shifted data, not merely copies with different colors. Actual CIA2 direction/pins and the VIC's resolved bank should still be captured: the instruction operand is not a substitute for device state. `$D018` bit 0 is unused, so a readback comparison must not interpret it as an address bit.

The original `$B800` page is `$70 | ((X+1)&7)`; `$B900` is `$70 | ((X+2)&7)`. The coroutine at `$64D9/$64EF` gradually applies `AND #$3F` to these entries. Its descending eight-entry blocks and final ascending block cover **172 unique indices, `$50..$FB`, in each page**. Its continuation yields for two polling calls between blocks; that is not a demonstrated PAL-frame rate. The later `$656C` coroutine applies `ORA #$70` in four-entry blocks after six polling calls and covers **164 indices, `$58..$FB`**. The ranges differ: `$50..$57` are not restored by that second sweep.

The authored sequence at `$63E0` waits 150 polling calls after reveal completes, then waits for music/service byte `$103F` to equal `$12`. It changes motion parameters, waits another 400 calls, invokes rehide, and publishes the exit flag. Continuations `$6414`, `$6432`, `$648D`, and `$64C2` distinguish those stages. These are source polling counts; only the measured intervals below are labelled PAL periods.

In the pinned VICE draw implementation, ECM+BMM combinations select black (`vicii-draw-cycle.c:133–142,200–210`). Clearing ECM makes this program's multicolor bitmap mode valid. However, ECM also changes the **graphics-fetch address**, masking it with `$39FF` (`vicii-fetch.c:163–181`). Treating this as only a visibility flag would miss part of the mechanism.

## What would distinguish full-row scaling from first-row repetition?

The relevant hardware rules in the pinned cycle engine are:

- With badlines enabled, YSCROLL matching the current raster's low three bits asserts the badline condition and enters display state (`vicii-cycle.c:51–60,523–531`).
- At **PAL cycle 14**, VC is loaded from VCBASE and VMLI becomes zero. RC is reset to zero only if the badline condition is true at that point (`541–549`).
- At **PAL cycle 58**, RC=7 makes the sequencer idle and copies VC into VCBASE. If display remains active or a badline is asserted, RC then advances modulo eight and display continues (`551–563`).
- Matrix accesses depend on badline state and BA/AEC timing. The fetch mode uses delayed/current `$D011` state according to the configured VIC model (`594–608`, `vicii-fetch.c:236–270`).

These rules create different predictions. Repeated badlines already true at cycle 14 can keep resetting RC to zero. A condition asserted later can obtain matrix fetches while preserving RC's progression. A condition created near the end of RC=7 can allow a row sequence to wrap and continue. Christian Bauer describes these distinctions in the FLI, linecrunch, and doubled-text-line sections of his [VIC-II article](https://www.cebix.net/VIC-Article.txt); the program's exact phases still have to be measured.

There are two additional traps here. First, `$6763/$6766` are **`DEC $D011; INC $D011`**, both NMOS read-modify-write instructions. A faithful trace must retain dummy and final stores rather than reducing the pair to two abstract values. A `$D011` read also exposes the current raster high bit, whereas a write uses bit 7 for the IRQ comparator. Second, bitmap graphics addressing uses **`(VC << 3) | RC`**, plus the selected bitmap base, ECM mask, and VIC bank. It does not use the cached character code as its bitmap offset. The shifted bank data means RC alone cannot prove which original source row supplied a displayed pixel.

## A bounded native observation plan

Trace **stores to `$D011`, `$DD00`, and `$D018`**, without automatic monitor actions. `$D012/$D016` are optional setup ports. Record instruction PC, clock, actual raster/cycle, stored byte, and X. Use a separate control restored from the same pre-trace VSF if tracing is being claimed not to perturb the result; preserve all module differences rather than hiding unrelated drive/CIA phases.

Useful natural stops are:

| PC | Scope |
|---:|---|
| `$6237` | Completed initializer, before its RTS. |
| `$62EA` | Phase-specific raster IRQ entry. |
| `$6763` / `$6769` | Before / after both `$D011` RMWs. |
| `$68B9` | Selected dispatch; record and reject an unselected self-loop as a display case. |
| `$68BC` | Selected routine completed; seven continuation cells still ahead. |
| `$69BE` | Continuation completed, before redispatch. |
| `$6336` / `$633F` | Raster-251 escape / teardown mode store. |

At the relevant write boundaries, retain RC, VCBASE, VC, VMLI, badline/idle/enabled state, register and delayed-register values, cached matrix/color buffers, graphics buffer, resolved bank, and border state. Match RAM tables and source bank bytes to the original image, reporting later mutations individually. Native post-instruction stops can have DMA-dependent latency: they must not be labelled the store's bus phase without calibrating that distinction.

## Bounded native segment and continuation

The original release booted through its own loader, without transplanting this payload or changing its PC. The finite raster witness starts at **`$68B9`, clock 259,896,720, raster 80/cycle 48**. Its natural target is **`$7012`, table case 14**. It ends at `$68BC`, clock **259,897,628**, raster 95/cycle 11.

All **45 observed stores** match their independently expected instruction PCs, port addresses, source values, X, Y, and SP. The 15 `$D011` events occur on rasters 80–94 at zero-based cycle **59**, exactly **63 clocks apart**. Each corresponding `$DD00` event is at cycle **2** of the following raster, and `$D018` at cycle **6**. The measured span is **908 clocks**, compared with **306 uncontended instruction cycles**, including both dispatch/endpoint jumps. The difference is 602 clocks, numerically `14 × 43`; it is retained separately from the nominal instruction count, without converting it to a demo frame-rate claim or labelling a monitor event a calibrated physical bus phase.

Every one of the **65,536 physical RAM bytes is unchanged** through this selected routine. The endpoint A/X/flags/Y/SP state also matches the finite load/INX contract. The original 19,275-byte family and 100-byte target table remain exact.

Four replayed snapshot pairs sample the selected `$FB/$72/$70/$F8` bank cases on rasters **81, 84, 87, and 89**. Each pair is at raw cycles **6 and 55**, 49 observed clocks apart. All have badline enabled and asserted, VCBASE **520**, no sprite DMA, and RC **0** after the fetch interval. Before the interval, RC is 7 for the first pair and 1 for the others. Each resulting 40-byte matrix cache and 40-byte color cache matches the independently addressed screen and Color RAM row. The first pair's old cache differs from the newly fetched row, so it is not a self-comparison of a cache that never changed.

These probes confirm the predicted RC reset within the selected kernel. They are deliberately narrow: all four still have **ECM+BMM set**, so these early-phase witnesses are black-gated rather than proof of the final visible image.

The following continuation, **`$68BC → $69BE`**, takes **475 observed clocks** and produces **21 exact stores**. Its `$D011` event cycles are `[62,61,61,61,61,61,56]` on rasters 95–101. All 65,536 endpoint RAM bytes match an independent calculation of its two phase additions, signed/clamped table index **17**, next dispatch **`$72EB`**, seven prepared selectors, and literal JSR stack effects. Only four RAM bytes have a net change in this pose.

Additional sampled states show RC **1, 4, and 7** on rasters **96, 99, and 102**, with VCBASE still 520 and no badline at those points. The next selected routine reaches raster **103/cycle 6** with **VCBASE 560**, RC 7, and a newly asserted badline. This establishes a repeated-RC0 segment followed by an RC progression and matrix-row advance. It does **not** by itself establish that every original source row is stretched equally or identify the complete eight-row image transform.

### The RMW pair creates a late badline pulse

A later original `$6763` call was captured before DEC, between DEC and INC, and after INC. This is a different frame from the selected case above:

| Natural stop | Clock | Raster / raw cycle | `$D011` | RC | VCBASE / VC | Badline / idle |
|---|---:|---:|---:|---:|---:|---:|
| `$6763`, before DEC | 265,812,191 | 65 / 8 | `$72` | 7 | 400 / 400 | 0 / 1 |
| `$6766`, after DEC | 265,812,197 | 65 / 14 | `$71` | 7 | 400 / 400 | 1 / 0 |
| `$6769`, after INC | 265,812,243 | 65 / 60 | `$72` | 0 | 440 / 440 | 0 / 0 |
| `$631B`, original caller return | 265,812,249 | 66 / 3 | `$72` | 0 | 440 / 440 | 1 / 0 |

The middle snapshot has a true badline **after** the cycle-14 RC-reset opportunity, while RC remains 7. It fits the code-derived late-pulse mechanism: change YSCROLL to match raster 65, enter display/fetch state without resetting RC, then advance VCBASE by 40 and wrap RC at the end of the line. INC restores the initial `$D011` byte. The pair consumes **52 observed clocks**, and its original RTS makes **58** to the caller. All physical RAM is unchanged; A/X/Y/flags and the original stack return are exact. The return address is established from the existing stack, not a patched PC.

With dummy-access tracing enabled, the clean run produces four queued records: two DEC records timestamped 265,812,197 and two INC records timestamped 265,812,243. This is **not four independently measured write phases**. The trace prints A=`$13`, which is not the RMW store value. The old/new write values `$72,$71,$71,$72` come from the original NMOS instructions and captured device states.

The [pinned monitor-source analysis](vice-trace-timing.md) explains why the debugger queues memory-access addresses and later prints them with shared clocks/PC context. Pending monitor state is outside the machine VSF. An early stop at `$6769` leaves the final INC records undrained; another trial contains six records, including two emitted at the restored pre-execution clock. Both are retained with explicit limits. A file named `selector-rmw-clean-return-after-control` also still had trace 3 active after an incorrect checkpoint deletion. It is retained as a contaminated observation, **not accepted as the untraced control**. The canonical `selector-rmw-clean-return-after-untraced` trial contains no trace records.

The clean four-record run and that actual untraced control finish at the same clock with **every snapshot module identical**. The separate `$6769` endpoint comparison is also identical across all modules; its incomplete trace is not promoted to a four-write timing proof.

### Trace controls retain the rest of the machine

Each traced interval has a control replay restored from the same original pre-interval VSF, with no automatic trace actions. For the selected routine, the endpoint **MAINCPU, all C64 RAM, and the complete VIC-II snapshot module are byte-identical**. The snapshot as a whole is **not identical**: the receipt retains every drive VIA timer/packed-pin difference, drive CPU clock/status/opcode field, and one `SIDEXTENDED` byte. The official writers name all changed bytes; none is removed from the comparison.

The SID difference is payload offset 27, the ReSID register `$1B`/OSC3 readback, `$00` versus `$FF`. `sid-snapshot.c:663` writes the 32 register bytes first; `resid/sid.cc:380–383` obtains the read-only registers through `read()`, and `$1B` calls voice 3's oscillator readback. Restore writes only registers `$00..$18` (`430–431`). This mapping does not establish the cause of the readback difference or audio equivalence. The VIA writer/reader also has a combined-CB1 packing asymmetry; the actual differing bytes remain recorded rather than being dismissed as irrelevant.

For the **continuation** interval, traced and untraced endpoint snapshots are identical across **every module**, including their full VIC draw buffers. This stronger result belongs to that one interval; it is not generalized to the entire effect.

### Output observations and remaining identity limit

Three original screenshots are retained at the raster-251 escape. From the first observation, the later two are **100 and 300 PAL periods** away, after accounting for the measured two-cycle stop-latency change. The monitor's `ignore` operand is hexadecimal: the earlier `63` command skipped 99 hits, producing the measured 100-period interval, not 64. The middle and last snapshots match **all 512 bytes** of the independently expected fully revealed `$B800/$B900` pages. Their choreography continuations are `$6414` and `$648D`, consistent with the post-reveal wait and later motion phase.

The viewed outputs are black initially and later show thin colored bands. They do not establish a recognizable photograph or the author's named MEGA phase. **Stream 46's visual identity remains unassigned**, even though its original bytes, counter transitions, and finite store sequences are proved. No contemporaneous full-image oracle is claimed for these PNGs.

The [structured native receipt](../../build/research/demo-coder/raster-analysis/native-raster-evidence.json) pins the script, reader helpers, original data, capture hashes, trace records, source schemas, all-module comparisons, and finite contracts. Reproduce it only after the owning native session has closed:

```sh
rtk proxy python3 research/demo-coder/raster_contract.py \
  --capture build/research/demo-coder/native-01
```

The tool's optional `--allow-live` mode writes a separately named **provisional** receipt. It does not silently promote an open session to final evidence.

This pass establishes the original control flow and the bounded counter/fetch observations above. It does not establish a complete visible-frame oracle, all-eight-row scaling, historical priority, a display-rate claim, or a transferable software polygon-fill optimization.
