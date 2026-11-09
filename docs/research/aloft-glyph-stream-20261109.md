# Aloft: forty live glyph bytes across 200 raster lines

This study independently derives the glyph byte supplied to every one of **8,000 logical graphics requests** in each of two retained original Aloft intervals. The source-predicted CPU stores update forty live RAM bytes, and their independently bounded timing fixes every store-before-fetch decision. Four phase-bound native GBUF and last-phi1 samples agree afterward.

The 8,000-byte output is a **temporal stream**, not an 8 KB bitmap stored by the demo. The VIC repeatedly requests row 7 of the same forty cached character codes. The CPU changes selected glyph bytes between successive scanlines. Physical RAM mapping, request scheduling, CPU data mathematics and final pixel decoding remain distinct proofs.

The [cell execution](aloft-cell-execution-20261109.md) already verifies the source-generated data stores for a two-target chain and a later 69-target chain. The [logical fetch binding](aloft-fetch-binding-20261109.md) supplies the active row-7 request schedule and cached-code lifetime. The [physical mapping](aloft-physical-fetch-20261109.md) resolves the admitted low-address requests to the same `mem_ram` object written by the CPU.

## Inputs and data separation

The new producer is [glyph_stream.py](../../research/aloft-pixels-20261109/glyph_stream.py). It consumes:

- Genuine pre-`$0500` values of the forty glyph slots from the frozen native input artifact.
- The frozen execution model's **predicted** 800 glyph-store events, including source PC, address, value and call index. Its endpoint predictions are not used to construct rows.
- Raw hook completion metadata: source PC, source instruction bytes, post-PC, clock and raw-record references. A/X/Y, monitored destination and observed store values are discarded before staging.
- The source-bound 40-request cycle schedule, logical cached-code addresses, continuous physical mapping and final-row tail guard.

For raw timing, the producer invokes only the frozen native module's raw wire/checkpoint/hook parsing functions with an empty capture list. It does not call that module's RAM/VSF pair decoder or machine-context stage. Full custody identities are checked, but no target GBUF, fetched-byte state or framebuffer is decoded during this projection.

Both complete row predictions and raw byte streams are written **before** opening the native machine-context artifact for the four byte comparisons. The actual hook values and target endpoints do not seed the data stream.

## The active CPU source route matters

The exact x64sc source route is `c64cpusc.c → mainc64cpu.c → 6510dtvcore.c`, with `c64memsc.c`. The generic `6510core.c` store-clock placement is not the compiled x64sc path. The separately pinned [store-route proof](../../build/research/aloft-pixels-20261109/display-analysis/source-route-01/store-route-proof.json), 4,932 B, SHA256 `2e7acf05f320399b27759d8811a0c0c074ba47511ac0466418740d65dfbf483a`, binds that distinction to official VICE 3.10 source.

In the SC `SET_ABS`/`SET_ZERO` path, the RAM STORE occurs before one trailing `CLK_INC`. That increment advances the clock and calls `vicii_cycle`. The direct-store helper therefore supplies the conservative macro visibility interval **`[completion−1, completion]`**, under its explicit no-diversion assumption. This is an implementation-level interval, not an invented electrical bus timestamp.

That correction is essential here: completion at cycle 56 alone would only provide an upper bound. The source-backed lower bound places the earliest next-row RAM update at cycle 55, safely after the current row's final graphics request at cycle 54.

The new source route also establishes that the active SC `$04/$0C` NOP paths have dummy target reads. Earlier frozen generic-core notes remain unchanged; their implementation-specific missing-read caveat must not be substituted for the SC path. Neither captured chain visits the eight suppressed-store boundary cells, and this producer does not simulate those read side effects.

## Deriving the row schedule

Each captured chain has 200 source cells and 800 source-derived glyph stores. The timing join consumes every corresponding reported data-watch store within the bounded request window. A source PC or source-byte mismatch, a missing/extra timing record, or a post-PC other than instruction fallthrough rejects the model. It does not choose events by an observed destination value.

The following completion pattern is **derived from both original raw traces**, not supplied as the staging input. Offsets are relative to the line whose forty requests consume the newly staged bytes:

| Source store | Completion offset | Conservative visibility interval |
| --- | ---: | --- |
| Absolute lookup-result store | −7, previous line cycle 56 | previous line cycles 55–56 |
| Scratch ZP result store | 0 | previous line cycle 62 through current cycle 0 |
| STX state store | 3 | current cycles 2–3 |
| STY state store | 6 | current cycles 5–6 |

For MOS8565 PAL, the source schedule requests the forty graphics bytes at zero-based cycles **15 through 54**, one per cached-code slot. All four current-cell stores are complete at least **nine cycles** before the first request. The next cell's first store cannot become visible until at least **one cycle** after the final request.

The staging algorithm starts from the genuine forty-byte prestate and applies only source-predicted byte assignments. For each requested byte, it applies a store only if the store's entire visibility interval precedes the fetch. Any overlapping interval rejects instead of guessing. The source order of all stores is retained; the physical mapper independently resolves each requested address.

All forty requests within a row consequently see one consistent staged state. Every output byte records either its genuine initial-byte provenance or the ordinal of its latest source-predicted store. All 800 stores are consumed, and both streams cover exactly raster lines **48–247**, forty bytes per line.

## Physical addresses and boundaries

The forty logical addresses are row 7 of glyphs `$00..$1F` and `$F0..$F7` in charset `$0000`. The admitted physical ABI binds them to ordinary `mem_ram` at the same addresses for both windows. VIC reads do not acquire the CPU port overlay at `$00/$01`; the actual row-7 addresses start at `$0007` anyway. Source closures and watched mapping registers retain bank 0 and ordinary non-cartridge RAM mapping for the request interval. The staging model rejects any unresolved address or a different RAM object.

Raster 47 is kept as a separate **partial initial boundary**. Genuine pre-`$0500` is already at cycle 24, with VIC idle state 1. This study does not manufacture the earlier requests or pixels in that line. It records that the first possible glyph update is after the prior scheduled cycle-54 window, but excludes line 47 from its 200-row glyph-stream claim.

At the other boundary, the natural kernel return `$F0B1` occurs at raster 247/cycle 30, before the final graphics request at cycle 54. The [tail guard](../../build/research/aloft-pixels-20261109/tail-analysis/accepted-01/tail-guard-proof.json) independently binds the original read-only `LDX #$F8 / CPX $D012 / BNE` wait through the natural `$F0B8` stop at raster 248/cycle 3. There is no intervening source write or reported hook. The final row therefore remains staged through its remaining requests; kernel return is not mistaken for display completion.

The tail's next D011 change, glyph reset, music and later field activity lie outside this byte-stream reconstruction. The original finite source closure still assumes no unmodeled external NMI/control diversion, RAM-writing DMA or CPU mapping change. VIC reads/stalls are not excluded. The store-clock contract additionally excludes a clock-changing diversion between a RAM callback and its observed completion context.

## Four byte observations after prediction

After both complete streams are persisted, the producer opens the frozen native machine contexts. Every sample requires matching CPU/VIC beam and clock phase, active FetchG flags, idle 0, RC 7 and the source-predicted VC/VCBASE/VMLI position.

The official `PHI1_TYPE_M=$E00`, `PHI1_FETCH_G=$400` source mask identifies a graphics cycle. `vicii_fetch_graphics` loads GBUF, and `vicii_cycle` assigns last-phi1 from that cycle's fetch before the snapshot is written. Thus zero-based cycle 24 selects slot 9, and cycle 30 selects slot 15.

| Chain / capture | Raster / cycle | Slot | Predicted byte | Native GBUF / last phi1 |
| --- | --- | ---: | ---: | --- |
| first / first cell return | 48 / 24 | 9 | `$FF` | `$FF / $FF` |
| first / full-chain return | 247 / 30 | 15 | `$FF` | `$FF / $FF` |
| later / first cell return | 48 / 24 | 9 | `$F8` | `$F8 / $F8` |
| later / full-chain return | 247 / 30 | 15 | `$04` | `$04 / $04` |

These are four independently phase-bound GBUF samples and four last-phi1 samples. They are **not 16,000 directly observed byte reads**. The complete streams are source/data/timing predictions; the comparison samples provide separate native checks. No target framebuffer is decoded by this producer, and no pixel or animation-FPS claim is made here.

The separate [display contract](aloft-display-contract-20261109.md) subsequently consumes these frozen streams and compares the two complete 384×200 bodies with native committed indices. Its later palette is injective, so its independent pixel inverse recovers all **8,000 later bytes**, matching this stream's `821665…` identity. The first all-black palette is degenerate and cannot provide that byte-level inverse check. This downstream result belongs to the [display proof](../../build/research/aloft-pixels-20261109/display-analysis/accepted-01/display-contract-proof.json), not to this producer's four GBUF observations.

## Frozen artifacts and consumer ABI

[Accepted glyph-stream proof](../../build/research/aloft-pixels-20261109/glyph-analysis/accepted-01/glyph-stream-proof.json): **6,598 B**, SHA256 `5628a150bac452423de3ccc2a4a2fc2ef67c5abb9372f0fe57f6c8bbb8be45a8`.

Producer: **24,288 B**, SHA256 `cd858bce2a9a0ac411aef8962c57a4fa78c2af200da1f127c5e61b1a9e454707`. Its receipt pins the native, execution, logical-fetch, physical-mapping, tail and exact SC store-route proofs.

| Temporal output | Bytes | SHA256 |
| --- | ---: | --- |
| `first-glyph-fetch-bytes.bin` | 8,000 | `2caae4b17736190a8dcc8ce45bdbd1c8c9478b9428bc31511c31bba6f6592870` |
| `later-glyph-fetch-bytes.bin` | 8,000 | `8216652dcfc04ad4e943e4395a3e54946e019269cd18512575ea3faa391e7efc` |

The binaries use row-major order: 200 rows × 40 cached-code slots. The receipt's `fields[]` entries, keyed by `first`/`later`, pin each `byte_stream` and `row_prediction`. `first-glyph-rows.json` and `later-glyph-rows.json` provide fetch clocks, logical/physical addresses, the forty predicted values, latest source-write ordinals, four current-cell store bounds and the next possible store deadline for every row. The raw timing projection contains no observed store data.

[Fresh self replay](../../build/research/aloft-pixels-20261109/glyph-analysis/self-replay-check.json) reproduces all **eight outputs / 3,847,058 B** exactly. The raw-timing candidate and both complete candidates remain retained. Candidate01 failed only a source-constant-name guard (`VICII_` prefix versus the actual `PHI1_` names), after both byte streams had been written; candidate02 fixes that guard without changing the staged bytes.

The parent independently reviewed the complete final producer and repeated it in a fresh directory. All eight outputs were byte-identical. Its [root replay report](../../build/research/aloft-pixels-20261109/glyph-analysis/root-replay-check.json), 1,618 B, SHA256 `914ef664d1280323cd0fe211d6ad84ad2d43e1bf05c50c490aed4f0be50bcfcf`, records that result. Source and accepted proof were unchanged by the review.

```sh
rtk proxy python3 -B research/aloft-pixels-20261109/glyph_stream.py \
  --output build/research/aloft-pixels-20261109/glyph-analysis/fresh-replay
```

The display consumer applies the MOS8565 multicolor-text shift/color/border geometry separately. Its full-body comparison preserves prediction-before-oracle order. The excluded initial boundary and later field tail remain separate work; neither proof should be enlarged into an independently reconstructed complete field or animation cadence.
