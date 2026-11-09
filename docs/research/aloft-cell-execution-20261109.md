# Aloft: two original cell chains independently predicted

The typed model matches two genuine executions of the original `$0500` dispatcher: a first captured two-target state and a later state selecting 69 distinct cells. In each 200-call chain it predicts all **800 direct glyph-store values**, all **1,350 reported watched-access records**, and the first-cell/full-chain endpoint data. The first chain changes four glyph bytes; the later chain changes 38. This closes the earlier native execution gap for these two captured states, while leaving actual VIC fetches and pixels to a separate study.

The [cell semantics](aloft-cell-semantics-20261109.md), [glyph mapping](aloft-cell-glyphs-20261109.md) and [new native custody](aloft-execution-native-20261109.md) remain separate evidence. The arithmetic model is [cell_execution.py](../../research/aloft-execution-20261109/cell_execution.py); it imports the frozen, strictly recognized cell algebra rather than executing 6502 instructions.

## Exact inputs and prediction order

The new original native case contains 18 paired RAM/VSF captures. This consumer pins [native accepted02](../../build/research/aloft-execution-20261109/native-analysis/accepted-02/native-proof.json), 131,527 B, SHA256 `5db9694db276541a5fd2b5cb386e92639e6da2c0d6cd644caf758eb113cc2326`.

Its distinct [independent-inputs.json](../../build/research/aloft-execution-20261109/native-analysis/accepted-02/independent-inputs.json), 902,791 B, SHA256 `bf50bdafeb7b18b737397bbf24f78f67390e2b883e32ed02a7011013d6b16f81`, supplies only genuine pre-`$0500` state and read-time bounds:

- CPU-view ZP, with `$00/$01` device readbacks separated from physical RAM aliases.
- The complete `$0400` lookup and initial values of all 40 source-defined glyph slots.
- All 601 dispatcher bytes: exactly 200 JSRs followed by RTS, including the actual motion-selected targets.
- Stored `$D011`, CPU flags, and captured code-generation identities.
- For each of 175 INC instructions, a clock interval from the preceding STY completion through INC completion, with raw source/trace references.

The model re-recognizes the 312 frozen source-predicted cells. It checks the genuine dispatcher bytes, applies the bitwise/lookup formula in source order, overlays its own stores on the initial glyph values and writes **four prediction files before opening the separate hook/endpoint oracle artifact**. The custody receipt's raw identity is checked first; its endpoint metadata is parsed only after predictions exist. No completed glyph/ZP state, post-INC flags, expected store values or expected access counts seed the prediction.

The call targets are declared actual motion state, not a prediction of the motion generator. Both observed chains use the same source-generated cell library; neither observation exercises every possible cell or every pose.

## Independently bounded D011 reads

Monitor watch records are delivered at instruction completion. Enabling dummy accesses preserved both INC store records, but did not turn their shared completion timestamp into two bus timestamps. The native custody proof pins the official monitor/core source and preserves this distinction.

Each normal cell ends its data stores with STY ZP immediately followed by INC `$D011`. The operand read therefore lies between the preceding STY's completion and the INC's completion. This model recomputes all possible raster lines in each inclusive clock interval using 63 cycles/line and 312 lines/field, then rejects a domain spanning different raster high bits. All **175 domains in each captured chain** have a unique high bit of zero. No post-store value or post-INC flag is used to choose that bit.

The predicted read byte is the model's preceding stored low seven bits combined with that independent raster high bit. The frozen hardware helper then derives read/dummy/final INC values. The seven normal calls in each group produce `$19..$1F`; the eighth cell writes literal `$18`.

These RMW values are **source-derived values, not directly observed bus data**. The comparison keeps the following observations separate:

| Observation per full chain | Matched result |
| --- | --- |
| Direct glyph STA/STX/STY values from the actual source opcode and post-instruction A/X/Y | 800 stores |
| Ordered reported operation/source-PC/address records | 1,350 records: 800 glyph stores, 175 D011 loads and 375 D011 stores |
| Literal D011 STA value from post-instruction A | 25 stores |
| INC completion N/Z and preserved A/X/Y, guarded by the actual fallthrough PC | 175 distinct completion states |
| Raw stored D011 at the first-cell and full-chain endpoint snapshots | `$19` and `$18` |

Of the 375 D011 store records, 350 are the two source-defined RMW writes per INC. Their raw data are absent from the hook records. Source semantics identify dummy/final order; the native records preserve the two stores and their ordering, not separate bus-data measurements. Explicit D011 I/O peeks bracket the first INC only in the custody case. They must not be generalized into peeks for every INC.

The comparator consumes **every reported hook within each captured interval**, including the armed VIC/CIA2/ZP/glyph watch ranges. It does not filter the oracle to the model's predicted destination set; an additional reported write would fail the comparison. The source and oracle address/value projections remain distinct.

## Endpoint and coverage results

All four endpoint comparisons match:

| Chain | First selected cell | Distinct full-chain targets | Changed glyph slots after first cell / after 200 calls |
| --- | --- | --- | --- |
| `first` | `$2000` | 2 | 4 / 4 |
| `later` | `$4600` | 69 | 4 / 38 |

At the first return `$0503` and complete return `$F0B1`, the model matches **all 40 glyph values**, **all 256 CPU-view ZP values**, **all 256 physical ZP aliases**, A/X/Y, PC, SP, preserved I/D/V flags and raw stored D011. The physical `$00/$01` aliases are retained from genuine prestate; they are not substituted for device reads.

For example, source-selected `$2000` maps the initialized inputs to `X=$80`, `Y=$7F`, then writes `$01` to `$07BF`, `$FE` to ZP `$FF`, `$80` to `$07` and `$7F` to `$0F`. Repeating the same two selected cells does not change the four-byte endpoint further. In the later chain, the first `$4600` cell instead produces `X=$F8`, `Y=$07`, `$E0` at `$0797` and `$1F` at `$DF`. All values are calculated from genuine entry inputs; these examples are not tuning constants in the producer.

CMP `($00,X)` remains a real indirect read. The model records its pointer/address dependencies but does not obtain its target data, simulate read side effects or claim final C/N/Z. Those unknown flags do not feed the admitted bitwise cell arithmetic. Likewise, the earlier boundary-NOP distinctions remain unchanged. Neither of these captured paths visits the eight suppressed-store boundary cells; their strict source recognition is broader than this execution coverage.

## Executable lifetime and machine assumptions

Matching executable bytes at the endpoints alone would be insufficient. The finite source closure checks the complete genuine dispatcher, every admitted target and all source stores. The dispatcher contains only JSRs and a final RTS; recognized cells contain the fixed bitwise/lookup/store/tail skeleton. Their RAM stores are confined to the 40 glyph slots, disjoint from the lookup, dispatcher, all cell bodies and return stack. The remaining store is D011 I/O. IRQs are disabled at genuine pre-`$0500` entry.

This closure explicitly assumes no intervening external NMI handler, other CPU control diversion or RAM-writing DMA actor, and the captured CPU memory mapping. It does **not** claim NMI is disabled merely because I is set. VIC reads and CPU bus stalls are allowed; the read-domain inputs handle their phase. The native case separately binds actual generated-code equality at all declared captures. No generic CPU interpreter or complete instruction trace is hidden in this argument.

There is also a useful source alias fact, separate from the execution comparison. Original `$F00A..$F01B` copies the old `$FE/$FF` clock bytes to `$FA/$FB`, then patches increment operands `$0801/$0805` to `$FA/$FB`. `$FF` is one of the active glyph-row-7 slots; `$FA/$FB` have byte offsets 2/3 within their glyph and lie outside the selected row-7 union. That is a functional address relation visible in the original generation31 bytes, not a claim about the author's intent.

## Measured elapsed clocks and limits

Both original captured chains have the same elapsed clocks:

| Captured boundaries | Elapsed PAL cycles |
| --- | ---: |
| Before outer JSR `$F0AE` → natural continuation `$F0B1` | 12,612 |
| Dispatcher entry `$0500` → `$F0B1` | 12,606 |
| First dynamic cell entry → `$0503` | 57 |
| `$0500` → `$0503` | 63 |

These are bounded emulated-clock measurements, not wall time or an animation-FPS claim. They are consistent with the source's equal normal/row-end cell budgets, but this consumer does not implement a cycle scheduler or use nominal instruction timing to manufacture native observations.

This study proves the two captured entry-to-data-write comparisons. It does not prove every motion state, continuous fetch/cache lifetime, a complete displayed field, committed pixels or the named layered-pattern scene. VIC address/RC/cache/badline timing requires its [separate fetch binding](aloft-fetch-binding-20261109.md); calculated glyph bytes alone are insufficient for that claim.

## Frozen proof and replay

[Accepted execution proof](../../build/research/aloft-execution-20261109/cell-analysis/accepted-01/cell-execution-proof.json): **23,651 B**, SHA256 `b3bf0ae5e74059bc17b29717174587bb679bfe3701a388dad0f9a3d88b8ebdf5`.

Producer: **29,921 B**, SHA256 `e4d603a41c344268b1a350c93878d6c0bf83ce370071d31020f07297c597e687`. The receipt pins the native custody/input/oracle artifacts and frozen semantic/hardware helpers. `first-full-chain-prediction.json` and `later-full-chain-prediction.json` retain the complete source-derived event sequences, independent read domains and closure assumptions; separate first-cell predictions and comparison records are preserved alongside them.

The [self replay report](../../build/research/aloft-execution-20261109/cell-analysis/self-replay-check.json) records all **seven outputs / 2,836,846 B** byte-identical. The parent independently reviewed the full producer and final all-hooks comparison change, then reproduced the same seven files exactly. Its [root replay report](../../build/research/aloft-execution-20261109/cell-analysis/root-replay-check.json) is 1,584 B, SHA256 `3a2b844eb6c6016b00f458103b277b9bca1956e94d0aa522864e80d2c9761082`.

Candidate01 contains prediction-only results emitted before any oracle artifact was opened. Candidate02 contains the first passing comparison. Candidate03 strengthens it to consume all interval hooks; prediction mathematics is unchanged. Every candidate, checked source and replay remains retained.

```sh
rtk proxy python3 -B research/aloft-execution-20261109/cell_execution.py \
  --output build/research/aloft-execution-20261109/cell-analysis/fresh-replay
```

Continue by combining the independently predicted event sequences with the source-bound VIC fetch contract. Treat hook completion clocks as completion bounds, retain the pending mode pipeline and cached matrix data, and prove actual fetch addresses/phase before claiming pixels. Additional natural motion states can extend execution coverage later; they should preserve the same separation between genuine prestate, independently derived timing inputs and endpoint oracles.
