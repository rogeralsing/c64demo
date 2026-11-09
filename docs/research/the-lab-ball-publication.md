# The Lab ball: independent Color RAM publication

Research date: 9 November 2026. The new pure publication model takes the
attribute producer's independently predicted 576-byte shadow, the genuine
pre-body 1,024-byte Color RAM device state, and the original 484-cell source map.
It predicts all 1,024 stored low nibbles and all 576 post-copy shadow slots.
Every value matches the fresh natural `$21AC` copy-complete capture. All 484
source-order STA PCs, addresses, register-A values and completion clocks match.
Only 26 device cells change, although the source executes 484 stores.

The [producer](../../research/the-lab/ball_publication.py) uses typed source
semantics rather than a CPU interpreter. It starts no CPU/native process,
emulator, socket or build. The [source contract](the-lab-ball-display-source.md),
[attribute prediction](the-lab-ball-attributes.md) and
[fresh native custody](the-lab-ball-native.md) remain separate authorities.
The custody proof retains its rejected later full-palette export; that export
is not used here. This model does not synthesize pixels or prove a complete
renderer/scanout timing model.

## Prediction inputs and comparison oracles

Prediction receives exactly three numeric inputs:

- The original source map with 24 column resets and 484 ordered cells.
- `predicted-color-shadow-c5c0.bin` from the independent attribute proof,
  derived from original 34 commands and genuine pre-edge state. Native pending
  or copied attribute bytes never seed this input.
- Genuine pre-body Color RAM low nibbles from `ball52-body-entry` at `$21BD`.
  The custody reader checks the 1,024-byte I/O export against the separate
  serialized Color RAM device. Underlying `$D800` RAM is a different object.

The pure `predict_color_copy(color_map,predicted_shadow,initial_color_ram)`
returns byte arrays `color_ram`, `cleared_shadow` and ordered `stores`.
Late native RAM/device values are accessed only in the comparison phase.
Actual `$2265` pending and `$21A9` pre-copy shadows must equal the independently
predicted events. Pre-edge and pre-copy device Color RAM must equal the genuine
initial input. The `$21AC` target, `$21AE` request-clear stage and later wraps
are oracles, never prediction seeds. Oracle values do not repair predictions.

The source body and caller are guarded in pending, selected and copied RAM:
all 5,835 bytes at `$26B9..$3D83` equal the independent original file20 bytes,
and `$21A9` remains `JSR $26B9`. The observed normal handshake is:

| Phase | PC | `$43,$44` |
| --- | ---: | --- |
| body / completed backbuffer | `$21BD` / `$2265` |0,0 |
| request queued | `$2267` |0,1 |
| bank selected, copy not yet begun | `$21A9` |1,1 |
| copy complete, request not yet decremented | `$21AC` |1,1 |
| request consumed | `$21AE` |1,0 |

The new front is bitmap `$4000`, screen `$6000`, with CIA2 bank `$4000`.
Those selectors and normal multicolor-bitmap mode are checked from real
CIA2 DDR/effective pins and VIC state; software `$43` alone is insufficient.
Color RAM and selectors stay equal through both retained wrap endpoints.
This supports the separate stable-viewport compositor rather than asserting
that register writes retroactively change already-fetched VIC caches.

## Per-column propagation and ordered stores

The source resets A=0 once per column. Each cell loads its shadow byte into X.
If nonzero, it copies X to A and clears that shadow slot. A zero event leaves
the previous A unchanged. Every cell then stores A to its Color RAM address;
the device keeps A&15. This is ordered last-nonzero propagation, not independent
per-cell palette lookup and not bitmap XOR-prefix filling.

The 484 visited slots lie in the 576-byte `$C5C0..$C7FF` shadow window. All 484
visited slots become zero; the 92 unvisited slots retain the upstream prediction.
Color RAM outside the 484 destinations retains the genuine initial device
state. The whole1,024-byte result and 576-byte post-state match their oracles,
including preserved regions. Sixteen nonzero events are consumed.

The Color RAM watch is armed with attached `r` before the first edge/event
continuation and deleted after the wrap-b RAM/VSF and Color RAM exports.
All device-visible `$D800..$DBFF` stores in that bounded watched interval occur
inside the source copy. CPU `$00` drives the mapping bits, and all484 copy
hooks have I/O-visible port `$35`. This distinction prevents an all-RAM `$34`
write from being misclassified as a device transaction. Actual hook bytecode
must be the expected `STA absolute`; raw register A equals each predicted byte.

`ordered-logical-color-stores.json` keeps original source order, expected
source-clear/event state, raw logical store byte, stored low nibble, predicted
completion offset and actual raw-wire references. It does not claim a complete
physical bus analyzer or interpret floating/unused I/O bits as stored state.

## Bounded instruction-cost result

The copy's source-derived cost includes caller JSR and callee RTS:

```text
JSR6 + LDY2 + 24*TYA2
+ 484*(LDXabs4 + STAabs4)
+ zeroEvents*BEQtaken3
+ nonzeroEvents*(BEQnot2 + TXA2 + STYabs4)
+ takenBranchPageCrosses + RTS6
```

The predicted shadow selects 16 nonzero events and 5 taken-branch page crossings.
The independent sum is **5,471 machine cycles**, equal to the observed
`$21A9` clock 237,441,570 through `$21AC` clock 237,447,041. All 484 individual
STA completion offsets also match, including the first store 21 cycles after
caller entry. The timing computation sees source PCs and predicted events,
not observed target timestamps.

This equality is scoped to verified preconditions: actual VIC model enum 1,
no enabled/active sprite DMA, CPU interrupt-disable set, CIA2 NMI mask/enable
zero, unchanged fixed copy/caller code, and the entire interval outside PAL's
potential badline raster range 48..247. The interval runs from raster 265/raw
cycle 51 through next-frame raster 40/raw cycle 41. The copy writes no VIC sprite
or CIA2 control register, so it does not enable those causes mid-routine.
This does not infer a complete renderer cost, generic IRQ deadline, physical
machine portability, animation cadence or FPS. It is the measured/modelled
fixed source-copy interval under the declared device state.

## Frozen inputs, outputs and replay

Accepted dependencies are the native proof SHA-256
`123732a8293916ffc9648b51686eeff314f1d0a9b371756efaab975976d968e5`,
source proof `30431ebfbef385a2b05a9983b2ef0094005053563ae3d60da95ef9ef980712ed`,
and attribute proof
`f0f4fa7941b24e9d9a3d4fbea1d39cf7e59bc387f87f4fb3a49fe17791cacbb6`.

The [publication receipt](../../build/research/lab-polygons-20261109/publication-analysis/accepted-01/publication-proof.json)
is 7,874 bytes, SHA-256
`5eedbbdaf09863861c34edface3d2be117d5205603806c2e902b37aaa10f9238`.
The producer is 17,677 bytes, SHA-256
`0a38471fe55e1d16b65a837c1b5edeb1e6f355e5f5812def714ae72597b310b6`.
Its five directory-independent outputs are:

| Output | Bytes | SHA-256 |
| --- | ---: | --- |
| `predicted-color-ram-1024.bin` |1,024 | `b7ba67664d39ce4c21a0e571a535d7b19526c004de30c051f5ae40b02ebc48eb` |
| `predicted-cleared-shadow-c5c0.bin` |576 | `1a0295f4bf5986c5f74eca9153a6a4cb10b073a01a76ba4a457fd862c78966a4` |
| `ordered-logical-color-stores.json` |216,418 | `5aaf116251530d734e2094c94a83c27328299978ea23942237af95155c4b9dbd` |
| `ball_publication.checked.py` |17,677 | producer hash above |
| `publication-proof.json` |7,874 | receipt hash above |

The [fresh self-replay check](../../build/research/lab-polygons-20261109/publication-analysis/self-replay-check.json)
matches all five outputs / 243,569 bytes exactly. Its 1,101-byte report SHA-256
is `a14d4250611d7649a33511a29351244c4b6eb773819cdf6a84ed7c8e85396b27`.
The earlier successful candidate remains retained; the final source additionally
guards complete original copy/caller bytes in actual phase RAM.

The [independent root replay](../../build/research/lab-polygons-20261109/publication-analysis/root-replay-check.json)
also matches all five files / 243,569 bytes exactly. Full source and bounded
timing review found no defect. Its 1,521-byte report SHA-256 is
`50a99a4306601bfef2b8e4aeec6f6915d457e346424add265be752d419c988ed`.

```sh
rtk proxy python3 -B research/the-lab/ball_publication.py --output build/research/lab-polygons-20261109/publication-analysis/<fresh-directory>
```

The source/API partition remains finite: one genuine prepared-edge pose with
its observed FD/EC translations and partial palette, one normal publication,
and bounded stable endpoints. It establishes source-derived Color RAM state
and copy order/cost, not arbitrary attribute geometry or independent complete
scanout. The root scalar bitmap/attribute/pixel consumer owns that next join.
