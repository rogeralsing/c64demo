# Colors: literal pixels of the first revealed display

**All 184,320 canvas pixels in three consecutive captured fields match an independent digital pixel model: 61,440 per field, zero mismatches, no excluded pixels.** This proves the selected, warmed first-display poses. It does not establish every Colors part, the original image converter, or perceived PAL/CRT colors.

The [checker](../../research/colors/first_display_pixels.py) reads existing original-release captures only. It starts no CPU, emulator, process, or monitor. Its [final receipt](../../build/research/colors/first-display-pixels/pixel-evidence.json) pins the native RAM/VSF/PNG inputs, source files, palette, trace history, and output indices. The first payload is an observed native image, not an independently depacked-image oracle.

## Character masks over colored sprite underlays

The display is hires text with black character foreground, blue background, and unexpanded monochrome sprites behind character data. Thus a glyph bit of **1 masks the underlying color with black**; a zero reveals a sprite pixel or background. The decoder chooses the lowest numbered opaque sprite before applying graphics priority, matching the VIC rules.

Four banks supply six character rows each, for a **320×192** canvas. Each bank has three 1,920-byte used charset regions, at local `$2800/$3000/$3800`. Cell codes are `6*column+local_row`. All 23,040 used glyph bytes match the first observed payload; all 1,024 Color RAM cells are zero in these captures.

The three revealed sprite masks are exact diagonal residue classes:

```text
mask 0: (local_x + local_y) mod 3 = 0
mask 1: (local_x + local_y) mod 3 = 1
mask 2: (local_x + local_y) mod 3 = 2
```

Each contains 168 lit pixels in a 24×21 sprite. They are disjoint and together cover all 504 positions. The checker verifies their literal source bytes and all twelve native sprite slots after the 63-byte reveal completes.

| Phase | Charset | Red/green sprite masks | Blue background class |
|---:|---:|---|---:|
| 0 | `$2800` | mask 0 red; mask 1 green | 2 |
| 1 | `$3000` | mask 2 red; mask 0 green | 1 |
| 2 | `$3800` | mask 1 red; mask 2 green | 0 |

Red, green, and blue here mean literal C64 indices **2, 5, and 6**. This is spatial diagonal sampling combined with three temporal phases, not three complete monochrome RGB scanlines.

## Exact bank boundaries came from source and native history

The initial model assumed each bank owned six complete rows. It failed on **18/15/14/23 pixels** in four earlier untraced fields, all on rasters 102/150/198. That [rejected model and its comparisons](../../build/research/colors/first-display-pixels/rejected-whole-bank-row-assumption/pixel-evidence-provisional.json) remain preserved. Their unknown timings were not invented afterwards.

For the three traced fields, the corrected model uses the actual `$DD02` writes and pinned official VICE 3.10 timing. Glyph column N fetches at raw cycle `15+N`. A reported store boundary T means the STA's final Phi2 write occurred at `T−1`, after that cycle's Phi1 fetch. The next fetch sees the bank change.

The snapshots also identify **custom GLUE type 1**. Its bank **1→2** transition exposes temporary bank 3 for exactly the first changed glyph fetch, then the alarm restores bank 2. This behavior was derived from `c64gluelogic.c`, the CPU cycle ordering, and the PAL fetch table before the corrected comparison. No boundary parameter was fitted to a PNG. Cached character codes remain from the earlier matrix fetch; only subsequent glyph fetches use the changed bank.

| Captured field | Phase | First changed glyph columns at rasters 102 / 150 / 198 | Pixel mismatches |
|---|---:|---|---:|
| a | 1 | 32 / 33 / 32 | 0 |
| b | 2 | 34 / 33 / 32 | 0 |
| c | 0 | 33 / 33 / 32 | 0 |

The receipt preserves all register events. It checks mode, palette and sprite-X stability during the canvas and uses the source-mapped repeated sprite Y sequence. Late register values alone are not treated as the whole field. [Monitor timestamp interpretation](vice-trace-timing.md)

## Digital samples are not an analog color measurement

The sprite window moves three pixels per captured field. The receipt therefore limits its cross-field statistics to these exact poses and records the common 90×192 window separately. For example, canvas pixel `(220,32)` emits `[5,6,2]` across the captured phase order 1/2/0, while `(168,0)` emits `[0,0,2]`. These are digital component-presence observations, not calibrated intensities or claims of a particular perceived mixed color.

No PAL delay-line, CRT phosphor, camera, subjective blend, or full-demo color-count model is supplied. The exact result is the literal palette-index match to the three native PNG canvases.

```sh
python3 research/colors/first_display_pixels.py
```
