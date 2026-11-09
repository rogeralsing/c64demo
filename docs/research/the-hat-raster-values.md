# The Hat upscroll: four complete raster-value paths

Research completed 9 November 2026. An independent typed-macro consumer
predicts all **7,011 watched final-instruction store hooks** across four
closed original-B raster windows, with matching source PC/address/order,
CPU A/X/Y/carry contexts and tracked endpoints. The two readback windows
also pass **96,348 software-visible VIC register-byte checks**. Actual
raster-read values and the IRQ's stacked cutoff PC are declared control
inputs; CPU timing, DMA and emitted pixels are separate boundaries.

The [consumer](../../research/the-hat/raster_values.py) uses the complete
[source descriptors](the-hat-raster-source.md) and the independently frozen
[hardware rules](the-hat-raster-hardware.md). It does not execute 6502
opcodes. The closed native03 custody supplies initial state, the separate
live-read stream, store-hook oracles and snapshots. Expected stores and
ending values are supplied only to the comparator, after prediction.

## What the four paths establish

| Window | Live raster reads | Watched store hooks | Selected regular kernel | Cutoff source PC | Visible register-byte checks |
|---|---:|---:|---:|---:|---:|
| Even | 30 | 1,794 | $96D6 | $97FF | — |
| Odd | 28 | 1,776 | $B5E9 | $B6E5 | — |
| Even with readback | 29 | 1,729 | $9B4B | $9B82 | 48,412 |
| Odd with readback | 26 | 1,712 | $BA5D | $BEAF | 47,936 |

Each path takes its own prefix and **five initial-loop iterations**, then
the regular kernel selected by the actual D112 sample and original dispatch
tables. The first three windows include a complete regular iteration and
a final partial iteration; the last stops inside its first regular
iteration. Those paths follow the source graph and live-read inputs, not
an observed write-count target.

Complete static coverage and native coverage differ. The source note
decomposes all **15 generated kernels**, of which **14 are reachable**
through the original tables: two initial kernels and twelve regular ones.
This native acceptance checks four selected regular targets. It does not
execute every generated kernel or verify every one of the 512 dispatch
entries at runtime. `$BED1` remains a complete source block absent from
the original dispatch tables.

The observed selector-to-cutoff durations are respectively **16,641,
16,513, 16,072 and 15,885 PAL cycles**. These are native observation
intervals. The value model neither predicts their clocks nor derives an
animation frame rate from them.

## Inputs and semantic stages

The prediction API receives:

- Selector-time physical RAM, logical VIC registers and CPU A/X/Y/carry.
  Decimal mode is clear, the effective CPU-port low bits are `$05`, and
  the recorded saved-stack generation has SP `$59`.
- The current F200–F7FF table generation. HIRAM must be clear so Fxxx
  table loads and Axxx/Bxxx code read RAM, while VIC I/O remains mapped.
- Ordered actual loaded-Y values at the independent D012/D112 source
  anchors: **113 reads** across the four windows.
- The stacked source PC where the external Timer-B interrupt stops the
  final partial iteration. The cutoff clock bounds oracle selection; it
  is not synthesized by the value model.

Source bytes are checked against the original B8 image. Only four declared
JMP-operand bytes may differ initially; each active prologue resets its
own operand before dispatch. The model does not adopt a prior patched
target as predicted control flow. Original F400–F7FF dispatch pages are
guarded, while current F200/F300 bytes remain declared data inputs.

Each guarded macro is lowered to its individual semantic stages at the
original PCs. A load, binary addition, optional CLC and each store remain
separate. A cutoff between arithmetic and a later store therefore emits
only completed operations. Carry follows the source chain, including CLC
after an addition; sampled lookup indices retain their INY-derived offsets.

The normal-flow graph chooses the prefix through pointer bit 3, repeats
the initial dispatcher and then self-loops the selected regular kernel.
Since source PCs recur, the consumer accepts the cutoff only **after all
provided live reads have been consumed**. It does not stop at an earlier
visit to the same PC or use store counts to decide how long to run.

The exact shared helper bytes `$019F..$01AB` are:

```text
60 20 9F 01 60 20 A0 01 60 20 A4 01 60
```

The used entries are an RTS, JSR-to-that-RTS followed by RTS, and the next
such nested chain. They preserve A/X/Y/carry; stack evolution and elapsed
cycles are not modeled. The actual helper-generation binding comes from
native custody. Equality to an earlier loaded generation is execution
provenance, not an independent original-SFX decode.

## Independent oracle classes

The source predicts **7,059 writes**, including **48 unwatched SMC
instructions**. The comparator uses the separately accepted checkpoint
ranges to select the 7,011 watched writes. It never builds that selection
from observed addresses or counts. Unwatched source writes remain in the
prediction and their four operand endpoints are checked.

All watched hooks match PC, address and operation. Post CPU contexts pass
**28,044 A/X/Y/carry component checks**. Independent post A/X/Y values
also bind **2,723 ordinary STA/STX/STY/SAX store bytes**. The **4,288
INC/DEC hooks** pass N/Z checks against the predicted final byte.

The first two windows have only register hooks, so they do not separately
record every intermediate RMW data byte. The two composite windows add
**3,441 complete 64-byte visible-I/O dumps**, including the **2,106 RMW
hooks** in those windows. The comparator checks 28 source-used/preserved
registers after each watched write, for 96,348 byte checks. The remaining
dump bytes remain retained evidence rather than silently becoming model
inputs.

The separate observer contract supplies read masks. D016 forces its high
bits, palette reads force their unused high nibble, and D018 reads force
bit 0. D011's live raster bit is formatted from the independently observed
query beam; that context does not schedule the source or choose a branch.
Consequently a visible dump is not a direct observation of all stored
unused bits, and none of these hooks is a physical dummy/final bus trace.

At each cutoff, complete bytes match for **28 tracked logical VIC
registers** and **20 pointer/operand RAM locations**. Eighteen RAM
locations are written by the model; the two inactive-branch operands
preserve their entry values. Final A/X/Y/carry also match. The 64-byte
logical-register output includes other unchanged input registers; their
presence is not a claim to reconstruct the entire serialized VIC state.
CPU stack RAM, caches, DMA counters, shifters and pixels are outside this
endpoint comparison.

## Frozen evidence and replay

The [native03 custody receipt](../../build/research/the-hat/raster-case-analysis/accepted-01/raster-case-proof.json)
is 3,222,719 bytes, SHA-256
`44f64e23252ed23db79c7ac5a56ffa326ba0d9e863a85f6902aa628e84c92f24`.
Its live-read input output is separately hashed and excludes store values
and visible-I/O dumps. The value producer imports only pinned checked pure
hardware/observer modules; the observer's lazy hardware slot is explicitly
bound to that same frozen module, without editing its source.

The [value receipt](../../build/research/the-hat/raster-value-analysis/accepted-01/raster-value-proof.json)
is **42,158 bytes**, SHA-256
`e33d5f8868ea0af205c390f57884362a42caf04523f1387212d40771cee525a5`.
Producer: **28,349 bytes**, SHA-256
`851dd310b56cd3574161d66b2020ec0e5d098ea7d1c96a883caf20c19b33b870`.

```sh
rtk proxy python3 -B research/the-hat/raster_values.py \
  --output build/research/the-hat/raster-value-analysis/fresh-replay
```

Self and independent root replays reproduce all **fourteen files /
2,738,434 bytes** exactly, without normalization. Full root source review
also passed. The [root report](../../build/research/the-hat/raster-value-analysis/root-replay-check.json)
is 3,172 bytes, SHA-256
`7100f5b656aae0390faaa3597552f0e94c4678c1fefaafc613b9162da60668a3`.
The [self report](../../build/research/the-hat/raster-value-analysis/self-replay-check.json)
is 2,482 bytes, SHA-256
`600efb203237bdec799ec08ed67b12c6be42be3c62c4ee55d28e2c41f8c629ec`.

The retained first value candidate failed on a custody field-name typo,
`visible_bytes64` versus the actual `visible_bytes`; the source arithmetic
was unchanged. Its partial results and failure remain. The passing second
candidate, earlier static-only source plan and source-recognizer failures
are also retained.

## Deliberate independence controls

A separate [negative-control report](../../build/research/the-hat/raster-value-analysis/negative-controls-01/negative-controls.json)
leaves the frozen value producer and receipt unchanged. All seven
counterfactuals reject: wrong decimal mode, wrong HIRAM mapping, one
changed current F300 byte, one changed observed raster value, one corrupted
oracle PC, one corrupted direct-store CPU byte and one corrupted visible
VIC byte. The table/raster changes alter the prediction before comparison.
An unchanged rerun first reproduces the accepted baseline source writes.

The report is 3,777 bytes, SHA-256
`067f1238e6d9f89855aeb240ccb35545dd3bd99aee5b0e2d373be3af39c3746a`.
A self replay in a fresh directory repeats all seven controls and
reproduces that report byte-for-byte; its
[check](../../build/research/the-hat/raster-value-analysis/negative-controls-self-replay-check.json)
is 485 bytes, SHA-256
`5495cc74d93a07b91331efbf6bb7814e60ffc68f9e0ea7cd421450cb63718b09`.
These are intentionally corrupted passive diagnostics, not native demo
failures, new native cases or fixes to the original release.

The next useful boundary is sprite-fetch, latch, border and shifter history
for these accepted register paths. This value acceptance establishes
neither complete displayed upscroll pixels nor whole-animation timing.
