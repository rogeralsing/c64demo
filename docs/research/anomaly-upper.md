# We Are The Anomaly: one completed upper-wall update

The saved `native-04` continuation contains a complete **28-job upper-wall update** and its first buffer publication. All 13 bitmap-row copies, 13 screen-row copies and two new-column jobs match an independent RAM model. The completed hidden image also matches a separate, direct 39-cell-left-shift calculation: **4,160 bitmap bytes and 520 screen bytes**. Its data and job state remain unchanged until publication.

This closes the accepted-upper-job gap in the earlier [Arcade runtime checkpoint](anomaly-runtime.md). It establishes one completed update, **not the whole demo's 50 fps claim**, every later buffer swap, a complete image oracle or a VIC timing simulation. Root controlled the native session; this lane only reads original bytes and saved RAM/VSFs. It runs no CPU, emulator, hardware response or downloaded program.

## Original code and capture boundaries

The model uses original bundle 36 from the independently checked [Sparkle payload analysis](anomaly-binary.md). Its source receipt is `binary-analysis/side1-binary-proof.json`, SHA-256 `b8744b0184128330a069a7366c4f843193306074f4a55a03d10f092a6fa8800c`. Source/known-mask identities are checked before use. The matching production Link artifact, rather than the older Parts build, supplies these addresses.

| Job entry | Final RTS | Natural caller continuation | Payload stores per job |
| --- | --- | --- | ---: |
| `$36F3` pixel row | `$38BA` | `$3D89` | 320 |
| `$38BB` screen row | `$39B0` | `$3D89` | 40 |
| `$39B1` new screen column | `$39C9` | `$3D89` | 13 |
| `$39CA` new bitmap column | `$39E8` | `$3D89` | 104 |

The inspected [upper-scroll source](https://github.com/elder0010/WeAreTheAnomaly/blob/4361d011f56f27014c0b6cd542718ca0b23666d8/Parts/ArcadeScroller/upper_scroll_logic.asm), [buffer setup](https://github.com/elder0010/WeAreTheAnomaly/blob/4361d011f56f27014c0b6cd542718ca0b23666d8/Parts/ArcadeScroller/double_buffer_functions.asm) and [column generators](https://github.com/elder0010/WeAreTheAnomaly/blob/4361d011f56f27014c0b6cd542718ca0b23666d8/Parts/ArcadeScroller/ArcadeScroller.asm) are pinned to author revision `4361d011f56f27014c0b6cd542718ca0b23666d8`. Original opcode and table bytes are checked at each job, allowing only the documented mutable operands/counter.

The first accepted gate was captured at `$36E6`, immediately before `CMP #$24`, with **actual A `$14`** from the preceding `LDA $D012`. Bit 7 of `$14-$24=$F0` is set, and status `$07` is 1. Fourteen native clocks later it reaches `$36F3`, with all 65,536 RAM bytes unchanged. This uses the sampled register value; it does not substitute a later raster reading or treat the signed `BMI` predicate as unsigned comparison.

## Exact job semantics

At this update, bitmap `$4000` / screen `$6000` is the source; hidden bitmap `$E000` / screen `$CC00` is the destination. The viewport is 13 character rows, or 320×104 pixels. A bitmap row begins eight source bytes after its destination counterpart; a screen row begins one byte after it. Each copies a complete row, temporarily including a rightmost cell that the final two jobs replace.

The host oracle indexes character rows and cells directly. It does not interpret the 6502 instructions as its only reference. Native prestate supplies the current source artwork, pointers and counters. The model preserves these source-specific details:

- A bitmap job interleaves 256 reads and writes, increments pointer high bytes `$CD/$CF`, then interleaves the final 64 reads and writes. It does not snapshot a source slice before copying, so overlap semantics are retained.
- It increments row `$D4` before reading the four patched address tables. **Row index 13 is still read**, although each table declares only 13 entries. Those reads consume actual adjacent table bytes before dispatch changes to screen copying. This observed direction leaves pointers `$0040/$01E0`; it does not create or clamp a fourteenth row.
- A screen job adds 40 to each low pointer byte, but increments **both high bytes from the source-low carry only**. Destination-low carry is discarded. The color-row immediate at `$399C` resets after its thirteenth row.
- New-column jobs consume 13 consecutive screen bytes and 104 consecutive bitmap bytes. Destinations are the last screen cell and last eight bitmap bytes of each row. They advance incoming pointers by 13 and 104, respectively. The final job clears status and restores pixel-row dispatch.

The last bitmap-row copy may temporarily read eight source bytes beyond the upper viewport. The direct final-image check does not preserve that temporary column: it derives all 39 shifted cells and the incoming rightmost column independently. Final writes stop at `$503F/$F03F`, before the relocated floor helper at `$F040`.

## Observed sequence and differences

Capture `pixel-row-pre/post` is followed by `job-02-pre/post` through `job-28-pre/post`. The checker requires the exact sequence **pixel rows 0–12, screen rows 0–12, new screen column, new bitmap column**. It also requires all upper data and declared job state to remain unchanged between consecutive jobs. The source structure predicts **4,797 payload stores** across this chain; those individual stores were not independently bus-traced in this lane.

All four complete upper data domains are compared after every job: `$4000..$503F`, `$E000..$F03F`, `$6000..$6207` and `$CC00..$CE07`. Pointer/counter/dispatch comparisons cover `$07`, relevant bytes in `$CC..$DE`, `$36F1/$36F2` and `$399C`. Every other full-RAM difference remains in the receipt.

The first 26 pairs have **zero differences across all 65,536 RAM bytes** between native output and the host model. The two new-column pairs each retain exactly two extra stack-byte changes at `$0155/$0156`: the original nested JSR return words **`$39B3` and `$39CC`**. These are recorded explicitly, rather than silently masking stack memory or asserting whole-machine equality.

| Observed interval | Native elapsed clocks |
| --- | ---: |
| One bitmap-row job | 4,596–5,076 |
| One screen-row job | 562–597 |
| New screen column | 186 |
| New bitmap column | 1,552 |

These are actual entry-to-return clock intervals in their saved native context, including any elapsed hardware stalls. They are neither isolated nominal instruction counts nor complete-field rates.

## Publication

The final job returns at clock **165,939,375**, with status 0 and all hidden image bytes complete. `publication-pre` reaches `$B84B` at **166,934,611**. The checker requires that same completed image and job state to persist through this gap of **995,236 clocks**.

The original publication remains unconditional: it does not test that status is zero. This particular observed swap is complete. The independent publication model checks the two helper calls, pointer-table selection, mutable instruction operands and status update. It deliberately preserves dispatch and the screen-row counter, which publication does not reset.

`publication-post` is `$B864` at **166,934,839**, after 228 clocks. Buffer selection changes `$00→$FF`; actual saved registers are **`$D016=$C7`, `$D018=$38`, `$DD02=$3F`**. They select the completed bitmap `$E000` / screen `$CC00`. All compared upper data and state match. The receipt retains two additional stack changes at `$0157/$0158`, holding the internal publication return word `$B850`; it makes no blanket RAM-equality or whole-VIC claim for this interval.

## Floor-field handoff and remaining scope

The checker also exports the original **96 ordered `$D016` store sites**, their zero-page indices and expected values from each actual `field[-02/-03/-04]-pre` state. The first three have `$B400→$B828` pairs; the fourth is a following boundary. Each paired interval preserves `$08..$67`, so the exported values do not assume a table that silently changed during the field.

This schedule reuses the frozen original-source expansion from [the earlier checker](../../research/anomaly/inspect_arcade.py): 40 static sites execute as eight×3, eight×2, eight, eight and eight×5. **Native store-trace comparison, observer chronology, session closure and field-boundary cadence belong to the parent-owned native audit**, not this arithmetic model. Later upper updates, other gate samples, scene changes and a complete long-run deadline proof remain outside this bounded case.

## Reproduction

```sh
rtk proxy python3 research/anomaly/inspect_upper.py
```

[The passive checker](../../research/anomaly/inspect_upper.py) reads `build/research/anomaly/native-04/` and writes `build/research/anomaly/upper-analysis/upper-proof.json`, plus a byte-identical checked script. The receipt pins all consumed RAM/VSFs, original source receipts, the frozen snapshot reader, model outputs, every full-RAM difference and the field plans. `bounded_upper_chain_complete=true` describes this observed chain; `runtime_witness_complete=false` keeps the broader display/deadline question separate.

The final checker SHA-256 is **`f921136dc69e71500f76a733e04c48a581672ca1116ed422e83086547aafd33e`**. The owner-closed receipt SHA-256 is **`67ac3c820f62f2f8bdfa1342a8790459c4ce673145c1080393f471a896a4ff3f`**. One bounded read-only peer review found no material issue in the job, carry, final-image or publication contracts. Earlier source/runtime/native receipts were not changed by this lane.
