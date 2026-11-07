# Tower Power N2: black is multicolor code 11

The orange/brown sphere uses an effective trick: **black comes from character Color RAM, while all three global registers hold face colors**. Its prefix fill starts with `$FF`, so the empty image uses bit pair `11`. It does not reserve `$D021` for the empty image.

This note concerns the mode-1 sphere in the native capture `build/research/tower-power/n2-live-01/sphere-native-01.png`. The loaded payload and [math](tower-power-n2-math.md) have separate proofs; live-session chronology and register observations belong to [the binary ledger](tower-power-binary.md).

## Hardware mapping and the chosen palette

In multicolor character mode, Color RAM bit 3 enables paired pixels for that character. Codes `00`, `01`, and `10` select `$D021`, `$D022`, and `$D023`; code `11` selects the lower three Color RAM bits. Thus the first three choices can use any of the 16 colors, while the character-specific choice has eight. This is the original hardware definition in the [Commodore Programmer's Reference Guide, page 116](https://www.devili.iki.fi/Computers/Commodore/C64/Programmers_Reference/Chapter_3/page_116.html) and [page 117](https://www.devili.iki.fi/Computers/Commodore/C64/Programmers_Reference/Chapter_3/page_117.html).

N2's setup at `$2862` selects the triplet at `$381E..$3820`, enables multicolor with `$D016 = $D8`, then executes `LDA #$88; JSR $2C85`. The latter routine writes that value to all 1,024 Color RAM locations. Its effective nibble is `$8`: multicolor enabled, individual color black (`0`). The sphere's palette table and the native register observation agree:

| Pixel bits | Selected source | Sphere color |
|---|---|---|
| `00` | `$D021 = $0A` | Light red |
| `01` | `$D022 = $08` | Orange |
| `10` | `$D023 = $09` | Brown |
| `11` | Color RAM low three bits = `0` | Black |

The names “background color” for `$D021..$D023` do not dictate which code represents the outside of this particular image. N2 deliberately assigns that role to `11`. The border is separately set black at `$2034..$2036`.

## Output starts FF; edge markers start 00

These are two different buffers with different neutral values:

| Operation | Original code | Result |
|---|---|---|
| Initialize charset image | `$2C6B..$2C84` | `$0800..$0FFF` receives `$FF` |
| Clear edge markers | Generated at `$29C9`, called at `$218E..$2190` with A = 0 | Selected marker bytes around `$F700..$FEFF` receive `$00` |
| Begin each column's prefix | Generated at `$28B7` | `LDA #$FF`, then EOR marker / STA image |
| Continue lower half | Same generator | Load the already-filled row 63, then continue EOR / STA |

With no markers, `$FF XOR $00` stays `$FF`: four black `11` pixels per byte. Clearing markers to `$FF` would therefore be wrong. N2 clears marker memory to zero and seeds the accumulated output with `$FF`.

The generated fill uses fixed per-column start/end rows, omitting the disc's unused corners. It emits 1,719 byte cells rather than all 2,048 charset bytes. The first column begins at row 35, so glyph 0's first eight rows remain `$FF` throughout this fill.

That explains the screen outside the 16×16 canvas too. `$3791` clears the matrix to character 0; `$37A3` replaces only rows 4..19, columns 12..27 with the column-major character IDs. The outside therefore displays glyph 0, whose all-one bits select black through Color RAM. A nonblack `$D021` does not paint the outside light red. The native `ram-sphere-01.bin` confirms all 744 matrix cells outside the canvas are zero and glyph 0 is eight `$FF` bytes.

## Face contributions are relative to 11

The 70 strip-face entries at `$24FC` contain `$55`, `$AA`, or `$FF`. These repeat two-bit contributions `1`, `2`, or `3` across a byte. They are **XOR deltas from the outside code**, not the final face pixels:

| Face contribution | Filled byte from `$FF XOR contribution` | Final pixel code / color |
|---|---|---|
| `$55` | `$AA` | `10`, brown |
| `$AA` | `$55` | `01`, orange |
| `$FF` | `$00` | `00`, light red |

Visible faces XOR their contribution into each incident edge at `$2232..$225F`. Caps contribute `$55` through the separate `$2268..$2291` path. The edge renderer then uses the accumulated mask; `$3605` restricts it to the relevant packed pixel lanes. After drawing, `$229D..$229F` returns that edge accumulator to zero.

For adjacent final face codes `a` and `b`, their contributions are `3 XOR a` and `3 XOR b`. The shared edge receives:

```text
(3 XOR a) XOR (3 XOR b) = a XOR b
```

Thus the usual shared-edge XOR rule remains intact. The outside complement cancels at interior edges. Entering a silhouette uses one face contribution, changing the prefix from outside `3` to that face's code; exiting changes it back. Coincident contributions still cancel through XOR.

The palette gain comes from choosing the code assignment, not increasing the hardware's color count: it is still four colors in each character. Black uses the restricted per-character slot; the three visible face colors can all use unrestricted global slots. Later mode-2 code can alter canvas Color RAM through `$2C97`, so this note does not claim the same palette setup for every phase of N2.

## Reproducible checks

The [palette harness](../../research/tower-power/n2_palette.py) runs original initialization and code generators in flat py65 RAM. It checks generated instructions against their marker/output addresses, then executes the unchanged pixel-cell spans for 28 empty, face, and shared-edge cases, including each packed two-bit lane and transitions across row 63/64. All outputs match an independent `$FF`-seeded prefix reference. The original marker-clear code is separately executed with A = 0, checking its exact write region and untouched canaries.

```sh
build/research/tower-power/cpu-venv/bin/python research/tower-power/n2_palette.py
```

The receipt `build/research/tower-power/static/n2-palette/palette-validation.json` records 211,097 original instructions and the input/script hashes. It also confirms both generated prefix banks match the native capture byte for byte: `$CB00..$DF35` and `$6800..$7C6A`. The captured RAM SHA-256 is `4d2d2d026daa909595446570e3e8a44cf25dc8856f688cba604ed0152bd7d2c6`.

This isolated check omits the unrelated sprite helper between the two fill halves. Flat RAM execution establishes the literal Color RAM writes; a raw bank-RAM capture is not hardware Color RAM readback. It is not a full line/culling test or a native timing measurement. No VICE process or production renderer was changed by this analysis.
