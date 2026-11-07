# Colors: the first native display's phase, character and sprite program

Research date: 7 November 2026. This maps the first payload reached naturally at `$8000` from the original side 1 Sparkle loader. Its input is the observed full RAM capture, SHA-256 `d03eee9b41f9142ac459609966b2396d77ec134fb1e055d2bf521aff0679e34f`. An independent packed-bundle oracle does not yet exist. [Boot/source identification](colors-binary.md), [native bootstrap checks](colors-native.md)

This lane interprets only two small RAM-only helpers. IRQs, VIC writes, drive code, complete frames and analog blending are not simulated. Native call cadence and literal pixel ownership require their separate capture/decoder evidence.

## Three phases, with two known callers

`$8045` increments the immediate X value stored at `$8046`, wrapping 2 to 0. All three input cases were executed from the observed original bytes and compared with an independent modulo-three formula over all 65,536 RAM bytes. Inputs 0 and 1 take 19 nominal CPU cycles; input 2 takes 20. These helper costs do not establish how often the caller runs.

Two source call sites are **`$8C71`** and **`$8E53`**. They belong to different display stages. Measuring successive `$8045` hits must retain their caller/stack context; treating every hit as a complete displayed frame without that evidence would be premature.

The later [closed native capture](colors-native.md) now supplies one bounded cadence witness: four consecutive `$8E4E` stops carry phases **0, 1, 2, 0**. Their clock gaps, corrected for the recorded one-cycle stop jitter, are each **19,656 clocks**, one PAL frame. This confirms those stable-field controller intervals, not the cadence of every call site or a static-image period.

`$8052` sets CIA2's direction register `$DD02=$3C` and selects `$D018` from the current phase:

| Phase | `$D018` | Relative character base |
|---:|---:|---:|
| 0 | `$9A` | `$2800` |
| 1 | `$9C` | `$3000` |
| 2 | `$9E` | `$3800` |

The screen offset is `$2400` in every phase. These are source-derived register values, not a palette-size or equal-exposure claim.

## Four six-row character bands

The native first-entry snapshot has CIA2 port latch `$F8`, with its two VIC-bank latch bits zero. Direction register values therefore select banks through output-low versus input-pull-up pins:

| `$DD02` | VIC bank | Screen | Three character bases |
|---:|---:|---:|---|
| `$3C` | `$0000` | `$2400` | `$2800/$3000/$3800` |
| `$3D` | `$4000` | `$6400` | `$6800/$7000/$7800` |
| `$3E` | `$8000` | `$A400` | `$A800/$B000/$B800` |
| `$3F` | `$C000` | `$E400` | `$E800/$F000/$F800` |

This uses **`$DD02`**, not ordinary writes of bank numbers to `$DD00`. The captured latch value is an explicit precondition of the decode.

Initialization calls `$8423` with four table pointers at `$9500`: **`$2400`, `$64F0`, `$A5E0`, `$E6D0`**. Each call writes six rows by 40 columns, with character code:

```text
code = 6 * column + local_row
```

Four original-helper cases validate all **960 matrix bytes** and every other RAM byte against that formula. Each bank owns its relevant six-row portion of the full screen; the offsets are global rows 0, 6, 12 and 18. This is an intended **40×24-character, 320×192 hires canvas**, using only codes 0–239 per bank. The first-entry `$D016=$08` has multicolor disabled and 40 columns selected. The active setup writes `$D011=$17`; exact beam origin and border state still belong to native display evidence.

Each used character region is 1,920 bytes, with 128 bytes of padding in its 2 KB allocation. Initialization writes `$3FFF=$FF` in such padding. In the final bank, used `$F800..$FF7F` does not consume the IRQ-vector bytes at the end of RAM. Later glyph equality should compare the actual used regions explicitly, rather than assuming every padding byte remains immutable.

## Initialization is a transition, not immediately the final picture

`$817C` first constructs the matrices, captures the startup text's Color RAM into a temporary screen representation, and copies startup character-ROM glyphs into bitmap storage. It then uses a bitmap transition and a palette fade before switching to the character canvas. These paths contain real register reads and raster waits; they are mapped statically here, not executed through a host hardware substitute.

`$83F6` clears 192 bytes in each sprite area **`$2300/$6300/$A300/$E300`**. The routine at `$836C` clears all **1,024 Color RAM cells** to zero. Thus the eventual character foreground is black under hires interpretation; the first-entry Color RAM and sprite slots are not yet the active initialized assets.

At `$8C67`, the program writes black to `$D021` above the picture and advances the phase. The picture path at **`$8CBA` writes `$D021=6`**, blue. A source model that keeps the above-canvas black value throughout the picture would be wrong.

The initial `$8C8F` path uses a table-driven FLD transition. It schedules bank changes with 48-raster increments, clipping later steps to raster 252. The first complete beam can therefore still contain an intentionally partial reveal; it is not evidence that the final canvas is missing rows.

## Paired sprites and retained pointer state

`$8072` enables all eight sprites and sets `$D01B=$FF`, putting them behind character foreground. Sprites form four overlapping pairs: **0/4, 1/5, 2/6, 3/7**, at X offsets **0, 24, 48, 72** from a moving table value. The first-entry snapshot has sprite multicolor and both expansion registers zero; later native state should confirm those properties before decoding active output.

The palette/pointer paths are:

| Phase | Sprites 0–3 | Sprites 4–7 |
|---:|---|---|
| 0 | Write pointer `$8C`, color 2 | Write pointer `$8D`, color 5 |
| 1 | Retain incoming pointer, color 5 | Write pointer `$8E`, color 2 |
| 2 | Write pointer `$8D`, color 2 | Retain incoming pointer, color 5 |

The eight pointer bytes at `$27F8` are replicated to `$67F8/$A7F8/$E7F8`, matching the four screen banks. In a warmed cycle, those pointers select the three sprite slots at relative `$2300/$2340/$2380`. **Retention is part of the algorithm:** a phase number alone does not define a freshly initialized pointer state. Early transition fields require their actual history; at least a complete palette cycle is needed before assuming the steady sequence.

`$8442` gradually copies the three source masks from `$96C0/$9700/$9740`. Its 63-entry index table at `$9652` is exactly a permutation of 0–62. Each invocation copies one selected byte into each sprite slot in all four banks, then advances its own index. After 63 invocations the visible 63 bytes of each mask have been copied; padding remains from the clear. This is an asset reveal, not runtime generation of new mask geometry.

## Later multiplex schedule and useful capture points

The later stage begins at `$8E4E`, which advances the phase, selects the charset, updates sprite positions/palette, and performs one mask-reveal invocation. The source schedules bank 1 at raster **102**, bank 2 at **150**, and bank 3 at **198**, using `$DD02=$3D/$3E/$3F`. Sprite Y targets are **54, 75, 96, 117, 138, 159, 180, 201, 222, 243**; the eight sprites are repeatedly repositioned down the picture. These are requested raster values and source operations, not measured store-bus phases or proof of their DMA effects.

The best whole-previous-frame checkpoint is **`$8E4E` at the next requested raster 4, before its call to `$8045`**. The preceding PAL beam has finished, and the new phase/pointer updates have not begun. The raster-252 handler `$8FD6` is useful for end-service inspection, but sprite DMA can extend below that point. **`$8E5C`** is useful after phase/palette setup and before the next mask byte is revealed. The earlier suggested `$8E59` is the call to the sprite setup itself and would expose a mixed old/new state; the corrected checkpoint follows that call.

For fully populated sprite masks, capture after at least 63 reveal invocations and retain each field's actual X positions, pointers, colors, phase and bank history. The moving X table means consecutive fields need not cover identical pixels. Do not infer a static analog mixture from three phase numbers alone.

## Reproduce the finite checks

```sh
build/research/tower-power/cpu-venv/bin/python research/colors/first_display.py
```

[The script](../../research/colors/first_display.py) executes **5,050 original instructions total** across three counter cases and four matrix-builder cases. It rejects I/O access, constrains the executed PC ranges, and checks the complete RAM result. No IRQ or palette-writing helper is executed. [The structured receipt](../../build/research/colors/first-display-analysis/first-display-contract.json) records the input hash, exact helper cases, phase semantics, banking, reveal permutation and checkpoints.

This establishes a concrete first-display architecture: stored character phases, a four-bank canvas, paired sprite underlays, and raster scheduling. Complete pixel/color ownership, actual field cadence, and analog color interpretation remain separate evidence requirements.
