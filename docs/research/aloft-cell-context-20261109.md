# Aloft cells: original source and three distinct machine-state boundaries

Research date: 9 November 2026. The retained part08 captures provide three
different inputs: before the original wrapper calls initialization, before
IRQ setup, and before an observed IRQ entry. **Neither the pre-setup nor the
pre-IRQ state is automatically the state at `$0500` or an individual cell.**
This distinction matters when checking generated raster code and its lookup,
zero-page state, motion-selected call targets and device reads.

The new [passive context producer](../../research/aloft-cells-20261109/context.py)
rechecks three full RAM/VSF pairs and their CPU/port/clock/beam identities.
It reads no CPU instruction, emulator, native process or downloaded host
program. It consumes the previously closed original run; this is not a new
native case. Full boot/wire/checkpoint/process custody remains with the
[original native proof](aloft-native-20261109.md).

![Retained original part08 orientation capture](../../build/research/aloft-20261109/native-01/part08-frame01.png)

This is the retained native orientation image of the vertical ribbons. It
helps locate the program visually; it is not an independently predicted
viewport or proof of the separately named three-layer scene.

## Original source comes first

The source is completed logical generation31 from the separate
[strict stream and Color RAM study](aloft-color-stream-20261109.md).
Its original code is independently associated with the retained entry state
by the [23-window comparison](aloft-decoded-parts-20261109.md). This producer
pins the original memory, known mask and physical-payload mask before opening
any retained native RAM. All 2,112 bytes at `$F000..$F83F` are known original
payload and equal the initial entry window. No runtime patch is normalized
away to obtain that equality.

Later observations differ from that original source window: 47 byte positions
at pre-setup and 53 at pre-IRQ. These are measured differences, not a dynamic
write count or a reconstructed execution history. They remain explicit
runtime-generation observations; final RAM does not replace original templates.
The separate [generator study](aloft-cells-20261109.md) owns predictions of
generated cells and template updates.
The later [glyph-address and cache study](aloft-cell-glyphs-20261109.md)
interprets their forty-byte working set without upgrading a stopped cache
match to a physical-fetch or pixel claim.

## Exact stopped phases

| Capture alias | CPU PC | PAL machine clock | Raster/cycle | Role |
| --- | --- | ---: | --- | --- |
| `part08-entry` | `$0890` | 129,591,314 | 300/62 | Before wrapper `JSR $F000`. |
| `part08-body` | `$F02B` | 130,163,026 | 15/49 | Initialization returned; IRQ setup has not run. |
| `part08-frame01` | `$F080` | 131,462,237 | 46/11 | Before this observed IRQ's first instruction. |

All three are natural checkpoints in the original closed case. All 196,608
physical RAM bytes equal the corresponding VSF `C64MEM` arrays. The strict
`MAINCPU` 1.4 and `C64MEM` 0.1 layouts, CPU registers/flags/SP/clock, actual
port latch/DDR/readback and PAL beam arithmetic agree. Each VIC core is
schema1.3, model1; both CIA payloads use the pinned reader's exact2.5 layout.
No interrupted state or later snapshot is substituted for an earlier phase.

`frame01` is only a capture alias. It does not prove this was the first
rendered frame, and its clock is substantially later than pre-setup. The
wrapper counter changes from `$1F` to `$20`; that bookkeeping is not a
directory-slot or visual-scene identity.

## Device context is not physical RAM

The CPU port is DDR `$2F`, readback `$35` in all three captures. Physical RAM
bytes at `$0000/$0001` do not stand in for those device reads. The exported
input declarations retain both raw physical zero page and a separate
same-stop CPU-read view with those two positions corrected from the actual
snapshot port fields. Future source-prefix evaluation must apply its own
changes, including the IRQ's `DEC $00`.

| Capture | Stored `$D011` | Same-stop `$D011` peek | Stored `$D018` | CIA2 PRA/DDRA |
| --- | ---: | ---: | ---: | --- |
| Entry | `$00` | `$80` | `$00` | `$F8/$3C` |
| Pre-setup | `$00` | `$00` | `$00` | `$F8/$3C` |
| Pre-IRQ | `$10` | `$10` | `$10` | `$08/$3C` |

The entry example demonstrates the readback trap. `$D011`'s high read bit
comes from the live raster line, not the stored raster-IRQ comparison bit.
The pinned official VICE source gives
`(stored & $7F) | ((rasterLine & $100) >> 1)`. The independent reading lane
explains why this also matters to `INC $D011` and its NMOS dummy write.
These same-stop peeks do not predict a later CPU bus read after the beam moves.
Unused read bits likewise make `$D016` and `$D018` readback differ from their
stored bytes; the source-backed rules are preserved explicitly.

CIA2 DDRA `$3C` leaves both bank-select bits as inputs. Looking only at PRA's
low bits would incorrectly request bank3. Official CIA code uses
`PRA | ~DDRA` for effective logical pins, then inverts the low two for the bank
request. All three stopped logical requests are bank0. Their GLUE1.0 payloads
are exactly `01 00 00`: type1, previous logical bank0, no active delayed alarm.
This is stopped logical state, not a trace of physical VIC fetch addresses.
The complete frozen VIC core, CIA state, opaque draw-tail hash and register
arrays remain available for a later, separate pipeline model.

The sprite-enable latch is zero at all three boundaries. That statement does
not by itself prove the absence of DMA at every point in an unobserved field.
Nor do these three mode snapshots prove a single mode throughout the display.

## Inputs for a later cell model

[declared-entry-inputs.json](../../build/research/aloft-cells-20261109/context-analysis/accepted-01/declared-entry-inputs.json)
provides, separately for each exact phase:

- Physical zero page and the same-stop CPU-read view of `$0000/$0001`.
- The observed 256-byte `$0400` lookup domain.
- The observed 200 call targets in `$0500..$0758`, where that kernel exists.
- The actual redirected clock operands at `$0801/$0805`.

The pre-setup kernel has two unique targets; the observed pre-IRQ kernel has
69. These are declared motion/dispatch inputs, not an independently predicted
motion trajectory. No `$2000/$2023` cell-body output bytes are exposed as
prediction inputs. Lookup and zero-page inputs are measured at the named
entry; a separate source model must establish their initialization or evolution
before claiming those inputs were independently predicted.

Original `$F080` starts with `DEC $00`, saves A, and uses the live CIA1 timer
low byte `$DC06` to patch its branch delay. It saves X/Y and writes
`$D011=$18` at `$F0A5`, then calls `$0500` at `$F0AE`. Afterward it waits for
`$D012=$F8` and writes `$D011=$10`. Thus copying the raw pre-IRQ `$D011=$10`
into a model of the first cell would miss an intervening original store.
Timing and that timer-derived delay require actual read/bus evidence; they
are not inferred from the static instruction listing.

## Receipt, failures and replay

The [accepted context proof](../../build/research/aloft-cells-20261109/context-analysis/accepted-01/context-proof.json)
is 4,831 bytes, SHA-256
`3610d8f46d722667f8d25f4f8976b363afc2c3c632c450f39d8d88d751d7e95e`.
Its primary-source output retains exact official archive-member identities
and line fragments for register readback, effective CIA pins and GLUE fields.
The core snapshot schema remains delegated to the unchanged pinned reader.

Candidate01 stopped before opening native capture data: its selected `$D018`
source excerpt ended at line639, three lines before the required return
expression. Its checked producer and failure remain. Candidate02 corrects
only that excerpt to627..643; no machine state or observed byte changed.

A fresh [self replay](../../build/research/aloft-cells-20261109/context-analysis/self-replay-check.json)
reproduces all five accepted files / 304,141 bytes exactly, without path
normalization. Independent full-source peer review and another fresh replay
reproduce the same five files. The [peer report](../../build/research/aloft-cells-20261109/context-analysis/peer-replay-check.json)
is 4,736 bytes, SHA-256
`40afc6e90bcac04d83ffb62932ca052c7ed48770a41aa4cfdbd80cde06bad084`.
It additionally checks official `MAINCPU`/`C64MEM` source layouts and the
stored-versus-read register, logical-bank and declared-input boundaries.
No producer or accepted-output change was required after review.

```sh
rtk proxy python3 -B research/aloft-cells-20261109/context.py \
  --output build/research/aloft-cells-20261109/context-analysis/replay-NEW
```

This note establishes exact reusable stopped-state inputs. It adds no native
launch, CPU execution, physical fetch composition, pixel image, runtime trace,
animation/FPS, optimization or named three-layer-scene result. The broad
research goal and all previous backlogs remain active.
