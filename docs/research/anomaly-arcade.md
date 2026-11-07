# We Are The Anomaly: Arcade Scroller source mechanism

The Arcade Scroller spreads occasional bitmap copies across independent scanlines, and spends remaining time copying a hidden upper-wall buffer in small jobs. Its floor uses prepared skewed artwork plus per-line hardware fine scrolling; it does not calculate a perspective projection for every displayed pixel. [Elder0010's author article](https://www.elder0010.com/projects/we-are-the-anomaly/) describes a 936×96 floor and claims 50 fps and successful drive-stress testing. Those remain **author claims**, separate from the source arithmetic enumerated here. This case follows the [2025–2026 source survey](frontier-2026.md).

The source is pinned to [commit `4361d011f56f27014c0b6cd542718ca0b23666d8`](https://github.com/elder0010/WeAreTheAnomaly/tree/4361d011f56f27014c0b6cd542718ca0b23666d8), dated 14 December 2025, after the November release. The checker reads cached files and independently enumerates integer arithmetic; it runs no assembler, downloaded host script, 6510 CPU, emulator or Sparkle decompressor.

The published [scene settings](https://github.com/elder0010/WeAreTheAnomaly/blob/4361d011f56f27014c0b6cd542718ca0b23666d8/Parts/ArcadeScroller/scene_settings.asm) specify 96 floor lines, four buffered images and 13 upper-wall character rows. Floor lines occupy the lower 12 bitmap character rows. Their 96 `$D016` values live at zero page `$08..$67`; their fractional accumulators occupy `$68..$C7`.

For floor line `i`, the actual assembled rate is **`102+i`**, from 102 through 197. In [the main source](https://github.com/elder0010/WeAreTheAnomaly/blob/4361d011f56f27014c0b6cd542718ca0b23666d8/Parts/ArcadeScroller/ArcadeScroller.asm), `p=PERSPECTIVE_FACTOR` and the emitted byte is `p+x`. The imported `frame_line_offsets_list` contains different values, 113 through 246: each is assigned to local variable `f`, but **`f` is unused**. The imported list is not the runtime rate table for this revision.

The [unrolled line update](https://github.com/elder0010/WeAreTheAnomaly/blob/4361d011f56f27014c0b6cd542718ca0b23666d8/Parts/ArcadeScroller/scroll_logic.asm) has these exact integer semantics:

```text
sum = accumulator[i] + (102+i)
accumulator[i] = sum mod 256
if sum >= 256:
    d016[i] -= 1
    if d016[i] == $BF:
        d016[i] = $C7
        shift this bitmap scanline left by one byte
        insert the next prepared byte at its right edge
```

`DCP` performs the decrement and comparison with `A=$BF`. Values `$C7..$C0` preserve the configured upper register bits while counting down through fine-scroll phases 7..0. Only `$C0→$BF` triggers a coarse shift, followed by reset to `$C7`. Thus one coarse event follows eight fractional carries, not every carry. The exact average horizontal rate is `(102+i)/256` fine-scroll pixels per call, with one eight-pixel bitmap shift per wrap. Calls are source-update invocations here, not measured frames.

The twelve generated coarse-copy helpers each contain 39 `LDA abs,Y` / `STA abs,Y` pairs and an RTS: **235 bytes each, 2,820 bytes total**. With `Y=i mod 8`, a helper moves the selected physical scanline's 39 bytes between adjacent C64 bitmap cells, then the caller inserts one new byte. Each coarse event therefore reads and writes 40 bytes, representing a 320-pixel scanline shifted by eight pixels. Helpers load at `$E000` and relocate to `$F040`. The initialization copies 13 complete pages, 3,328 bytes, including **508 bytes beyond the 2,820-byte helper body**; that over-copy is not silently called generated code.

Each floor line's insertion instruction starts at `$7800+160*i`. The prepared stream interleaves 40 bytes from each of three incoming images and a fourth blank image, per scanline. Its self-modified absolute source address advances by one on each coarse event, with explicit low-byte carry into the high byte. It is a forward stream, not a modulo-160 circular buffer. The image parser and merged-line layout are preparation work; the live floor only changes registers, shifts bytes and advances these pointers.

The initial fine phases deliberately differ. Four 24-line quarters use `(j+6) mod 8`, `j mod 8`, `(j+2) mod 8`, and `j mod 8`, respectively, for `j=0..23`. Accumulators start at zero. The checker enumerates a complete **2,048-call accumulator/fine-state period**, and independently verifies every line against cumulative integer formulas. Over this period:

| Declared initial fine phases | Total coarse events | Mean lines copied per call | Maximum lines copied together |
| --- | ---: | ---: | ---: |
| Published staggered quarters | 14,352 | 7.0078125 | **24** |
| All lines initially phase 0 | 14,352 | 7.0078125 | 70 |
| All lines initially phase 7 | 14,352 | 7.0078125 | 96 |

These comparison baselines retain the same 96 different rates and zero accumulators. They are arithmetic experiments, not alternate assembled demos or measured timings. Staggering changes the peak distribution, not total bytes copied. The maximum published case implies 960 floor bitmap reads and 960 writes in that call; ordinary accumulator/fine bookkeeping, instructions, page crossings, IRQs and VIC stalls remain additional costs. The source scene counter reaches `$055E`, 1,374 calls; the same 24-line maximum also occurs within that initial range. No complete 50 Hz budget follows from this enumeration.

The upper wall uses bitmap `$4000` / screen `$6000` and bitmap `$E000` / screen `$CC00`, with a 13-row, 320×104-pixel viewport. [Double-buffer setup](https://github.com/elder0010/WeAreTheAnomaly/blob/4361d011f56f27014c0b6cd542718ca0b23666d8/Parts/ArcadeScroller/double_buffer_functions.asm) selects source/destination pointers and patches the write-column functions. Row sources begin eight bitmap bytes and one screen byte after their corresponding destination: a coarse eight-pixel shift. Copies include a temporary rightmost cell that is replaced by the new-column jobs.

The [upper scroll routine](https://github.com/elder0010/WeAreTheAnomaly/blob/4361d011f56f27014c0b6cd542718ca0b23666d8/Parts/ArcadeScroller/upper_scroll_logic.asm) first reads `$D012`, then executes `CMP #threshold / BMI`. This is a **signed-result test**, not an unsigned less-than branch. The high raster bit in `$D011` is not read. Exhaustive enumeration of all 256 possible low bytes gives:

| Threshold | Accepted `$D012` low bytes | Rejected low bytes |
| --- | --- | --- |
| Initial `$24` | `$00..$23`, **`$A4..$FF`** | `$24..$A3` |
| Later `$40` | `$00..$3F`, **`$C0..$FF`** | `$40..$BF` |
| Later `$60` | `$00..$5F`, **`$E0..$FF`** | `$60..$DF` |

`wait_nanocamera` changes the threshold when the scene counter high byte equals 2 and 4. An accepted gate still returns if `upper_scroll_status` is zero. The gate therefore needs its actual calling raster context to assess available time; this source note does not assume that every accepted low byte is an early line in the next PAL field.

When the gate accepts and status is nonzero, the self-modified `is_scrolling` jump advances through one job per call:

| Jobs | Calls | Bytes read and written |
| --- | ---: | ---: |
| Copy one 320-byte bitmap row | 13 | 4,160 |
| Copy one 40-byte screen/color row | 13 | 520 |
| Write the 13-byte new color column | 1 | 13 |
| Write 13×8 new bitmap bytes | 1 | 104 |
| **Complete hidden-buffer update** | **28 accepted calls** | **4,797 reads and 4,797 writes** |

The pixel-row loop explicitly copies 256+64 bytes. After row 13 it patches the next stage to color rows; after 13 color rows it switches to new-column colors, then pixels. The final pixel-column job advances its source by 104 bytes, clears status, and resets the jump to `copy_pixels`. The color-column source advances by 13 bytes. Rejected calls perform none of these copy jobs.

The raster routine decrements the upper fine-scroll phase only every **15** invocations. Every eighth decrement wraps `$C0→$BF`, resets to `$C7`, XORs the buffer-selection byte with `$FF`, resets row pointers and sets status to 1. Thus publication is scheduled every **120 raster-routine invocations**, irrespective of whether the hidden-buffer job chain finished. It does **not** test completion before swapping. Finishing 28 accepted calls within that interval is a runtime scheduling requirement, not a guarantee established by the state-machine count. The double-buffer mechanism avoids rewriting the visible upper bitmap during each normal copy, while the floor continues to use bitmap 0.

Static artifact identity narrows the production candidate but does not finish the source-to-disk proof. The pinned repository's `Release/WeAreTheAnomaly-Side1.d64` and Side2 file are **byte-identical** to the two original disks in the archived author ZIP: SHA-256 `d452497845598cca8936fdf57c60fdc9c70cd7e64110e049fa6fc7d735f940cd` and `3b537ade95fc1312d0c1b6ef2d042041e454ca3055c687fd8aaaf46a4a00a41e`. The production `WeAreTheAnomalyA.sls` names `Link/ArcadeScroller/ArcadeScroller.prg`, split into `$2800` section (file offset 2, length `$972F`) and `$E000` section (file offset `$B802`, remainder 2,820 bytes).

The 49,926-byte **Link PRG** has SHA-256 `8ee85d5dad9035e205bb68391ab5b4e033c5c596a7e62f840db270f63b1fc16c`; its rate bytes 102..197, initial fine phases and literal signed-gate bytes match the examined source. The same-size **Parts PRG**, SHA-256 `71bcf54c931b207fd2caae5a98d49cfc97b33544803dfa711d26fa0d3839e56e`, differs at **6,992 bytes** and has rate bytes 94..189. They must not be interchanged because their names and sizes look alike. The checker uses the published symbol file only to locate guarded bytes; this is not a rebuild. Whole-disk identity plus a manifest reference does not independently extract the original Sparkle payload. That decompression/native linkage remains unresolved for root's separate lane.

Run the original analysis checker with:

```sh
rtk proxy python3 research/anomaly/inspect_sources.py
```

[inspect_sources.py](../../research/anomaly/inspect_sources.py) SHA-256 is `94ac15892576cfa6eadc150122814b9513e6374ee09724ed3f466166fd75ceb1`. Ignored receipt `build/research/anomaly/arcade-source-proof.json` SHA-256 is `30e681b44b72f7a610bd8b151762813c591ad7339b153ca8ce8d18117e61e729`. It pins original acquisition receipts, Git blob identities for all examined files, 18 additional author-repository files, disk/binary comparisons, every gate input and the complete per-call floor workload. Original bytes remain under ignored `build/`; no downloaded program or script was executed. Native `$D016` writes, actual gate arrival times, upper-buffer publication completeness and the author's 50 fps claim still need separate original-disk evidence.
