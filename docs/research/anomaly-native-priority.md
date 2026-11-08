# Anomaly: observed upper-sprite priority and a different wall

A fresh original-disk run reaches the planned overlap naturally. At raster
line 110, X 318 and 319, sprites 6 and 7 both supply nontransparent pixels.
The saved output selects sprite 6's color 14. Reversing hardware-number
priority in the independent calculation selects sprite 7's color 1 instead.
All eight actual sprite states are checked; sprites 0 through 3 do not obscure
the overlap.

The same capture also matches 101 committed upper rows, 38,784 palette
indices, against independent composition. Its wall bitmap and attributes are
different from those in the preceding five upper-strip observations. Neither
result is a whole-frame or FPS measurement.

Producer:
[`research/anomaly/native_priority.py`](../../research/anomaly/native_priority.py).
Receipt:
`build/research/anomaly/native-priority-analysis/native-priority-proof.json`.
The producer reads closed files only. It starts no emulator, original CPU,
assembler, subprocess or live connection.

## Fresh original lineage and retained navigation

`native-08` starts by autostarting the original side-one disk, SHA-256:

```text
d452497845598cca8936fdf57c60fdc9c70cd7e64110e049fa6fc7d735f940cd
```

It restores no snapshot and receives no RAM, code, PC or register writes.
`native-07` contributes a host prediction only; it is not this capture's
execution parent. The original disk's retained DOS boot-sector chain is
rechecked against the 834-byte boot PRG, SHA-256
`40cd90f462434ea395d1c03e09d5cb6336186ab2229e4889c4d3abb48a2816ea`.
The run does not retain a direct `$0810` boot-entry snapshot. Its fresh-disk
autostart lineage and its later source-bound scene observation are the claims.

One owned VICE process, PID 30321, uses one monitor endpoint, port 60880. It
closes on explicit input and is reaped with exit code `-15`. The closed capture
directory identity is:

```text
9cc937c7275a2697bb8c7aaec8cc6f203fd2582d96f68e690c7d3baad771f1a7
```

Do not modify, add or rename files inside `build/research/anomaly/native-08/`.
This identity covers every retained file's name, byte count and SHA-256.

The frozen raw-wire auditor is reused with one documented adaptation: its
manual-start metadata assertion becomes an original-disk autostart assertion.
The original auditor file is unchanged. All byte-range, serialization,
interruption, timeout, ownership and closure checks remain in force. The
receipt records both function-source hashes and the exact replaced assertion.

The audit covers 361 events and 43 ordinary commands: 42 completed responses,
one explicitly interrupted navigation response, two waiting notices, zero
resends, zero restarts and no unfinished or cancelled commands. A bare `warp`
query observes warp off during early navigation. The first pending resume is interrupted
on the same socket and PID at `$8086`, clock 111646081, line 0/raw cycle 1.
This is an earlier demo state, not the requested scene. Navigation then resumes
with warp explicitly confirmed on.

One rejected read-only query is retained exactly:

```text
resourceget "WarpMode"
Unknown resource "WarpMode".
```

It changes no state and supplies no evidence about warp. The ordinary `warp`
query supplies that evidence. After the natural target stop, warp is explicitly
off and speed is 100. Both proof resumes, command sequences 26 and 35, inherit
an explicit warp-off observation and `Speed=100` observation with no intervening
warp change. Warped navigation is excluded from the proof interval and from
timing claims.

The retained official VICE 3.10 source explains a possible transition: autostart
saves the original runtime warp state and restores it when autostart completes.
A manual warp-on command during autostart can therefore later revert to the
saved value. This capture has no decisive completion/off event proving that
mechanism caused its observed OFF state. The specific cause remains unproved.
The source also distinguishes runtime `warp_enabled` from the startup resource
`InitialWarpMode`. The latter must not be used to infer current warp. The bare
monitor command queries runtime state; the resource table has `Speed` and
`InitialWarpMode`, and rejects `WarpMode`. The relevant autostart, vsync, parser
and resource-query source files are retained with guarded fragments in the
same analysis output.

## Actual checkpoints and the prediction

| Checkpoint | PC | Clock | Raster line / raw cycle |
|---|---:|---:|---:|
| `candidate-prepared` | `$3D83` | 175034118 | 271 / 21 |
| `priority-active` | `$08C1` | 175043648 | 110 / 38 |
| `priority-row-committed` | `$B400` | 175046267 | 152 / 11 |

Every checkpoint has a full 65,536-byte physical RAM dump and snapshot. All
196,608 RAM bytes match their paired snapshot modules. CPU registers, clock,
processor ports and beam coordinates match the corresponding monitor stops.
Raw cycles are zero-based. The active and committed stops belong to the same
field; their field-base clock is exactly one PAL field after the prepared stop.

The natural `$3D83` breakpoint checks scene counter `$020F` and original code
prefix bytes. It does not require the predicted wave indices, so an incorrect
prediction would remain observable rather than being forced by the guard.
The actual wave indices, phases, upper mask and positions agree with the
earlier conditional model:

| Sprite | Actual 9-bit X | Y | Phase | Wave index |
|---|---:|---:|---:|---:|
| 4 | 352 | 75 | `$60` | 72 |
| 5 | 280 | 65 | `$60` | 38 |
| 6 | 280 | 108 | `$60` | 48 |
| 7 | 310 | 108 | `$60` | 71 |

The saved upper high-X mask is `$F0`. The prior model predicts 403 further
upper-motion updates from its `native-07` starting state. Agreement here checks
that conditional trajectory; it does not turn the older state into this run's
parent or predict native elapsed cycles. The producer always retains a
trajectory-comparison report and would preserve a mismatch as a rejected
prediction.

## All eight actual sprites, then the two output pixels

At the active stop, CIA2 selects native VIC bank `$4000`. Registers
`$D011/$D016/$D018 = $3B/$C4/$80` select bitmap `$4000`, attributes `$6000`,
fine scroll 4 and actual sprite-pointer table `$63F8`.

The independent point calculation uses actual 24-bit row data latches, actual
pending/display flags, actual 9-bit X positions, cached multicolor and
horizontal-expansion modes, and actual cached color registers. It does not
simulate future motion or VICE's sprite shifter. Cached X, mode and palette
values agree with the saved VIC registers at this stable phase.

| Sprites | Actual X | Y | Pending/display at line 110 | Role |
|---|---|---|---|---|
| 0, 1 | 64, 64 | 179, 179 | Clear | No upper-pixel contribution |
| 2, 3 | 125, 62 | 208, 240 | Clear | No upper-pixel contribution |
| 4, 5 | 352, 280 | 75, 65 | Clear | No contribution at this row |
| 6, 7 | 280, 310 | 108, 108 | Set | Both overlap at the target pixels |

DMA and display masks are both `$C0`. The upper sprites are multicolor,
horizontally expanded, enabled, not vertically expanded and in front of
bitmap foreground. Source pixels therefore occupy four physical pixels per
multicolor pair. Sprite 6's raster origin is `280+8=288`; sprite 7's is
`310+8=318`.

The actual active row fetches are:

| Sprite | Pointer | Physical bytes | Saved data | MC / MCBASE |
|---|---:|---|---|---|
| 6 | `$D2` | `$7483..$7485` | `$5FE200` | 6 / 6 |
| 7 | `$D3` | `$74C3..$74C5` | `$557EE2` | 6 / 6 |

Both are source row 1. Their saved nonzero data equals actual RAM and the
corresponding original sprite-art bytes. At X 318 and 319, sprite 6 contributes
pair 7, selector `10`, using its individual color 14. Sprite 7 contributes
pair 0, selector `01`, using shared color 1. Lower hardware sprite number wins.

The later `$B400` snapshot has committed all rows below 152. Its serialized
palette-index raster contains `[14,14]` at the two target pixels. The direct
all-eight calculation also gives `[14,14]`; reversed priority gives `[1,1]`.
The active line-110 snapshot still holds `[3,3]` in its uncommitted raster row.
That stale-row control is retained and is not mistaken for current output.

The original file-known motion code, Y-wave table, sprite art and stable raster
IRQ prefix ranges match all three target states. The proof interval traces
`$D000..$D02E` and `$DD00..$DD03`; it contains zero MMIO stores, and the relevant
registers agree at all three endpoints.

There is a retained pointer-trace gap: the armed ranges are `$4FF8..$4FFF` and
`$CFF8..$CFFF`, while this actual display uses `$63F8..$63FF`. The actual table
bytes agree at the captured endpoints and the active row latches already
contain the required fetched bytes before the target pixels are displayed.
No continuous pointer-write history is claimed. This gap is not hidden or
reinterpreted as coverage of `$63F8`.

## An additional 101-row match, with explicit address transport

The frozen upper compositor uses fixed oracle addresses `$E000`, `$CC00`,
`$CA00` and `$CFF8`. It is not modified. To reuse it for this native bank `$4000`
case, the new producer constructs a separate oracle RAM view with these
declared byte mappings:

| Actual physical input | Oracle address | Bytes |
|---|---|---:|
| Bitmap `$4000..$503F` | `$E000..$F03F` | 4,160 |
| Attributes `$6000..$6207` | `$CC00..$CE07` | 520 |
| Sprite art `$7400..$74FF` | `$CA00..$CAFF` | 256 |
| Actual pointer slots `$63FC..$63FF`, values `$D0..$D3` | `$CFFC..$CFFF`, translated values `$28..$2B` | 4 |

Every actual pointer is translated through its physical art address. All
bitmap, attribute and art input bytes agree at the prepared, active and
committed endpoints. Actual native CIA state and VIC registers remain
unchanged. The oracle view is an input-address renaming, not an observation
of a native `$C000` display and not an emulator state injection.

Sprites 0 through 3 have Y values 179, 179, 208 and 240. Their unexpanded or
expanded display bands start after row 151 and finish before the preceding
field reaches line 312. They cannot contribute to the compared current upper
interval. The four-sprite upper oracle is therefore appropriate for this
bounded interval.

Rows **51 through 151**, 101×384 = **38,784 indices**, match exactly. Both actual
and independent bytes have SHA-256:

```text
360136647a60d5eff589ae306e74ac8dd150cc7963ffec2ea959eef334e9823c
```

Current line 152 and later rows are excluded. This does not complete a sixth
104-row upper strip or a 312-line frame. Omitting sprites changes 179 compared
indices. Reversing sprite priority changes precisely the two independently
examined pixels.

## The wall input is demonstrably different

The comparison uses the preceding `native-07/upper-complete` wall as the old
input, not the partly prepared back buffer in the new run.

| Input | Old SHA-256 | New SHA-256 | Changed bytes |
|---|---|---|---:|
| 4,160 bitmap bytes | `429638efca0374578677edbfbe3bcb9b2b13bd09b4f5db382c075b0bee19f518` | `b601e4dfe4da7f4aae8b90f71539f362e6661375fac881b8469158595c030c8f` | 3,317 |
| 520 attribute bytes | `d9e155dd84805e12d2fb9cc7c8e44457ae41130f37cd8684a508d2503a96af92` | `ac6273304d091923e08d1d46f7a64b011d3bf4680a6bbedf1fa1ef9151921a08` | 333 |

A stale-wall control keeps current sprite art, positions, palettes, priority
and fine scroll, replacing only the bitmap and attributes with those old
inputs. It differs from the new observed strip in **15,162 indices**. The new
wall is established by changed bytes and changed output, not inferred from a
later scene counter.

## Replay and continuation

Run from the repository root:

```sh
rtk proxy python3 research/anomaly/native_priority.py
```

Outputs are the receipt, actual and independent 38,784-byte strips, the
stale-wall control bytes, trajectory comparison, source copies and a checked
copy of the producer. The receipt also identifies the retained screenshot as
an output observation, not the palette-index oracle.

The exact continuation is
`native-08/priority-row-committed.vsf`, SHA-256:

```text
09df702e9fcac59d9c81a3ced230a58a7fcc8bbe7296a6b249ed42131f0db992
```

It stops at `$B400`, clock 175046267, line 152/raw cycle 11. Any further native
work must use a new capture directory and explicitly state whether it starts
fresh or continues a retained state. For continuous pointer history in this
configuration, trace the actual `$63F8..$63FF` table. To extend the current
output strip, capture after rows 152 through 154 are committed; do not relabel
the present 101-row result as 104 rows. Endpoint RAM identity, physical bus
phases, physical-chip behavior and whole-demo performance remain separate
questions requiring their own evidence.
