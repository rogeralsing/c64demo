# Anomaly: active upper fetch, borrow/wrap motion and a fifth strip

The closed `native-07` capture adds three separate results to the existing
ArcadeScroller proof. It observes an active graphics fetch from VIC bank `$C000`,
checks previously unobserved sprite motion branches, and matches another
104-row upper strip against independent palette-index composition. It does not
change the earlier four-field receipt.

The passive producer is
[`research/anomaly/native_upper_fetch.py`](../../research/anomaly/native_upper_fetch.py).
It reads retained RAM, VICE snapshots and raw monitor streams. It starts no
emulator, process, CPU interpreter or downloaded host program.

## Capture ownership and lineage

`build/research/anomaly/native-07/` is closed. One owned VICE process, PID
33714, used one monitor endpoint and was reaped with exit code `-15`.
The directory identity is:

```text
e2a86a8cbbb9136388e4dbed04ce0294151fee01840b016e09a1c84dcf0fd428
```

The identity hashes the sorted list of each retained file's name, byte length
and SHA-256. Do not add, replace or rename files inside this closed directory.
The new audit imports the frozen `research/verify_vice_live.py` wire auditor
with only its case-directory and identity map overridden. All 460 events cover
the complete input, sent and received streams. All 55 ordinary commands have
one completed response. There are no retries, restarts, interrupts, partial
responses, cancelled commands or observation timeouts.

One restore starts from
`native-06/floor-line-drawn.vsf`, SHA-256
`2428affe32e414636d3444b1cfa72f41d25d7e466adf0ff0ad07dbabf28d32c8`.
All five complete modules—`C64MEM`, `MAINCPU`, `CIA1`, `CIA2`, `VIC-II`—match
the restored snapshot before execution. Every RAM dump also matches all 65,536
physical RAM bytes in its paired snapshot. CPU registers, processor ports,
clock and beam coordinates agree with the same monitor stop.

The original side-one disk remains SHA-256
`d452497845598cca8936fdf57c60fdc9c70cd7e64110e049fa6fc7d735f940cd`.
The session attaches it without autostart. Five observation resumes each have
an explicit warp-off response and `Speed=100` check. Apart from the declared
restore, the command inventory contains no RAM, code, PC, register or hardware
state writes and no input to the original program.

| Checkpoint | PC | Clock | Raster line / raw cycle |
|---|---:|---:|---:|
| `restored-floor` | `$B82A` | 167013188 | 250 / 62 |
| `upper-selected` | `$B864` | 167013227 | 251 / 38 |
| `sprites-prepared` | `$3D83` | 167014848 | 277 / 21 |
| `upper-fetch` | `$08C1` | 167022487 | 86 / 37 |
| `fifth-field-pre` | `$B400` | 167026619 | 152 / 11 |
| `upper-complete` | `$B47B` | 167026856 | 155 / 59 |

Each row has a full RAM/snapshot pair: 393,216 compared RAM bytes in total.
Raw cycles are zero-based; PAL hardware-cycle comments add one.

## The upper bank is actively fetched

The transition back to the upper display is continuously observed through
the registered MMIO trace ranges:

| Instruction | Write | Observer line / raw cycle |
|---|---|---:|
| `$B857` | `$D016 = $C7` | 251 / 24 |
| `$B85C` | `$D018 = $38` | 251 / 31 |
| `$B861` | `$DD02 = $3F` | 251 / 38 |

The `$DD02` trace line appears in the response to the following resume. The
paired `upper-selected` snapshot already contains the completed write. This
is observer delivery order, not an additional later bank switch.

At `upper-fetch`, CIA2 PRA is `$F8` and DDRA is `$3F`. The resulting VIC bank
is `$C000`. `$D011/$D016/$D018 = $3B/$C7/$38` selects the upper hires bitmap
at `$E000`, with screen attributes at `$CC00` and horizontal fine scroll 7.
The saved display is active rather than idle or vertically bordered.

Actual saved state is `VC=183`, `RC=3`, `VMLI=23`. The pinned VICE 3.10 source
stores the graphics byte before incrementing VC and VMLI. Therefore the
most recent graphics address is:

```text
$E000 + 8 × (183 − 1) + 3 = $E5B3
RAM[$E5B3] = $7E = saved GBUF = draw-pipe GBUF0
```

All 40 saved matrix bytes also equal RAM at `$CCA0..$CCC7`. Their saved color
buffer equals the corresponding color RAM entries. This closes the earlier
gap where active nonzero graphics latches came from bank `$4000`, while the
four composed upper strips used bank `$C000`.

Sprite 5 supplies a nonzero active sprite witness in the same snapshot:

```text
pointer = $29, X = 244, Y = 85
visible source row = 86 − 85 − 1 = 0
address = $C000 + $29 × 64 = $CA40
RAM[$CA40..$CA42] = 28 00 00 = saved data latch
MC = MCBASE = 3
```

Sprite 7 is also active: pointer `$2B`, `X=352`, `Y=77`, row 8,
`MC=MCBASE=27`. Its saved data is zero and its X position lies beyond the right
display border. Retain this state, but do not count it as another nonzero or
visible sprite witness.

The fetch interpretation uses the retained official VICE archive, SHA-256
`8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1`.
The relevant fetch, counter and snapshot source files are copied into the new
analysis output with their identities. These establish emulator-state meaning;
they do not establish physical-chip behavior or individual bus-write phases.

## The fifth motion transition borrows and wraps

The old upper X-high mask is RAM `$CB=$60`. The floor has already multiplexed
VIC `$D010` to `$04`, so using that live floor register as the previous upper
mask would be wrong. The independently evaluated source branch uses the saved
upper mask and the actual previous low-X registers.

| Sprite | Old upper X | Speed | Observed low-X writes | New upper X | Result |
|---|---:|---:|---|---:|---|
| 4 | 64 | 8 | `$38` | 56 | Normal subtraction |
| 5 | 256 | 12 | `$F4, $00, $F4` | 244 | Borrow clears high bit |
| 6 | 256 | 12 | `$F4, $00, $F4` | 244 | Borrow clears high bit |
| 7 | 16 | 14 | `$02, $60` | 352 | Low-phase wrap sets high bit |

The intermediate writes matter. For sprites 5 and 6, the high-phase
subtraction borrows. The original source writes the low result, adds 12 and
writes the temporary correction, clears the high phase, then falls through to
the low-phase subtraction using the old X again. Replacing this history with
a single unsigned subtraction would lose real observed stores.

Sprite 7 crosses the low-phase cutoff: `16−14=2 < 6`. It restarts at low X
`$60` with high bit 7 set. Its Y changes from 120 to 77. The wave index changes
from 54 to 55, and actual RAM at `$39E9+54` supplies 77. The final saved upper
mask and `STY $D010` value are `$80`. The source bytes `$3BE8..$3D92`,
`$B82A..$B863` and the 256-byte Y-wave table match the original file-known
payload in both compared states.

These are new branch witnesses. The previous four-field motion proof covered
actual transitions without these borrows or wraps. Its restrictive checker is
left unchanged; the new producer uses its own arithmetic and the complete
temporary-store history.

## Independent fifth-strip comparison

The producer calls only the frozen upper compositor's `compose()` function for
the new field. It does not call the older `field()` or `code_and_motion()`
functions, whose guards intentionally describe the earlier four transitions.
The oracle directly indexes bitmap bits, attribute nibbles and multicolor
sprite pairs. It does not execute the VICE renderer, sprite shifter or original
6502 instructions.

The oracle uses `fifth-field-pre` RAM and display state. The observed output
comes from `upper-complete`'s serialized palette-index raster, which has
committed every row below current line 155. Thus lines 51 through 154 contain
the entire current upper strip, including rows that were not yet complete at
the line-152 pre-snapshot.

Result: **39,936 indices, zero differences**, SHA-256:

```text
5d6e4137a4f411372db1ca5d657a9f74300a765425d50a87eac032133fd3b984
```

Selected sprite pixels are `{4:12, 5:36, 6:84, 7:0}`. No nontransparent
sprite pixels overlap. The wall bitmap, its attributes and both copies of the
sprite art remain identical at the compared endpoints and to the previously
proved inputs.

Alternative models produce these mismatch counts:

| Control | Different indices |
|---|---:|
| Omit sprites | 132 |
| Interpret sprites as hires | 94 |
| Disable horizontal sprite expansion | 114 |
| Interpret bitmap as multicolor | 12,978 |
| Put sprites behind foreground bitmap bits | 36 |
| Reuse previous upper sprite X/Y and saved X-high mask | 272 |
| Reverse sprite priority | 0; inconclusive because pixels do not overlap |

The earlier four-field receipt remains SHA-256
`7a6f5a32c52adb85cde0b851ecff47f5154ca301240e48e52d1a810b5ccdc4d3`
and still contains 159,744 compared upper indices. This separate result makes
five strips and 199,680 separately compared indices. It does not create a
312-line whole-frame proof, a workload deadline, or a demo FPS measurement.
Endpoint RAM equality also does not prove that no transient RAM write occurred
between checkpoints.

## Reproduce and continue

Run the passive audit from the repository root:

```sh
rtk proxy python3 research/anomaly/native_upper_fetch.py
```

Outputs live under `build/research/anomaly/native-upper-fetch-analysis/`:
`native-upper-fetch-proof.json`, actual and independent 39,936-byte strips,
seven control reports, pinned source copies and a checked copy of the producer.
The receipt lists all input identities, all six pairs, wire coverage and every
observed register store. The capture directory and all older receipts remain
unchanged.

The exact continuation snapshot is `native-07/upper-complete.vsf`, SHA-256
`2560606a79af78009553dfcfef19d678e5d8eeddc46215aa81c2d4c56eda2474`,
at `$B47B`, clock 167026856, line 155/raw cycle 59. Any new native observation
must use a fresh directory and retain this snapshot as its explicit parent.
Useful remaining work is a naturally overlapping nontransparent upper-sprite
case to distinguish priority, or a new bounded complete-field capture. Keep
physical bus phases, continuous RAM-write absence and whole-demo performance
as separate claims requiring separate evidence.
