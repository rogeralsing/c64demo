# No Bounds SpriteFPP: one complete visible component

The original release now has an independently reconstructed **133×320-pixel
visible SpriteFPP component**: raster rows78..210, columns32..351, **42,560
palette indices with zero differences**. All eight hardware sprites contribute
visible pixels. This extends the earlier [counter/fetch proof](no-bounds-native-spritefpp.md)
from first-fade black output to a naturally reached gray palette.

The expected image comes from original atlas bytes, the saved prepared row
table and direct multicolor-pair composition. It does not execute the C64
program or replay VICE's sprite shifters. The comparison covers this declared
component, not a complete 312-line frame, a full animation cycle or a frame-rate
measurement.

## Fresh original execution

`build/research/no-bounds/native-03/` is a fresh boot of the original side 1
disk, SHA-256
`f603e03f94ed4df416584419a696e1832b0710308de8faf2d0179b0a7725fe70`.
It deliberately does not restore native02: the [drive snapshot investigation](drive-snapshot-restore.md)
does not establish whole drive/IEC state equality after restoration.

The closed case contains 14 full RAM/VSF pairs and 125 completed serialized
commands on one owned process/socket. Two early navigation resumes used
declared warp; every resume after the production initializer entry used warp
off and Speed100. There were no RAM/PC injections, snapshot restores, retries
or process restarts. The owner explicitly closed and reaped the emulator
before the passive case pin was finalized.

Natural boot `$0810` matches all 832 loaded boot bytes, excluding its two-byte
PRG header. Production entry `$c300` again matches all 20,261 file-defined
bundle bytes. The actual `$08a4: JSR $c300` has stored return `$08a6`, and the
initializer naturally returns to `$08a7`. No supplied standalone startup is
substituted.

## The previously unresolved header case

The native values at unloaded `$4000..$4002` are again **`47 ec 98`**. At
cell 92's natural pre/post-clear PCs `$8c24/$8c27`, all eight cached pointers
are 0 and all fetched data words are zero. MCBASE remains 3,6,…,24; MC is
6,9,…,27. The corresponding source triplets at `$4003..$401a` are file-defined
zeros. A wrong zero-counter model would fetch the nonzero header instead and
fails all eight latches. This directly closes the pointer0/header distinction
left open by native02; it does not make the three header bytes file-defined.

The snapshots are at line 169/raw46 and50, four cycles apart. Native02 used
raw45/49 at its selected cells. Both cases clear D017 after PAL cycle16 and
preserve the held offsets; the proof does not force an exact reused phase.

## Reaching a visible eight-sprite layout

The machine-bound first mature breakpoint was:

```text
break 9237 if (@ram:$98a5 == $06) && (@ram:$44 >= $3c) && (@ram:$44 <= $44)
```

`$98a5` is the fade-stage LDX operand. At stage 6, the source has patched the
fade handler to `wait_to_start`. The hidden palette IRQ runs at raster 4,
before the prepared-table return at `$9237`; no color writes occur between
that return and the completed component capture. RAM conditions select code
state, rather than pretending `@ram:$d0xx` reads live VIC registers.

The actual prepared state is pose 4, X size 60, Y size 127 and palette index 1.
Importantly, `draw_frame` writes the hardware X layout **before** its pulse
helper updates X size. The used layout is therefore index 59, cached at
`$20/$21=$9d88`, with:

```text
sprite:        0   1   2    3    4    5    6    7
actual 9bitX: 51  75  99  147  195  217  265  289
D010:         $c0
D01D:         $3c
```

Sprites 2..5 are X-expanded; their overlap supplies intermediate widths.
An independent closed-form layout model matches all 72 used position tables:
576 X coordinates and 144 high-X/expansion bytes. The observed layout's
physical width is 262 pixels; neither those offline checks nor this one native
layout constitute scanout verification of every size.

The actual source pose pointer is `$ac6c`, pose 4's 91 original rows. The saved
destination `$0715` contains 92 rows: source row 0 twice, then rows1..90.
The pixel oracle uses this prepared table, whose original pose binding is
checked, rather than assuming a new polygon renderer calculates these rows.

The gray palette is background/border1, shared D025=11, shared D026=12 and
all individual sprite colors15. D01C=`$ff` selects multicolor. Actual CIA2
PRA=`$f8`, DDRA=`$3d` and input pull-ups select bank `$4000`; D018=0 places
the pointers at `$43f8`.

## Direct composition and exact native comparison

For raster row `y`, the row-table index is `y−E9−2`, using E9=76. This maps
the declared 133 rows to prepared indices 0..132. Each sprite reads three bytes
at `$4000 + pointer*64 + 3*(sprite+1)`. Every 24-bit slice supplies twelve
MSB-first two-bit selectors; selectors map to transparent, D025, individual
color and D026. A pair occupies two physical pixels, or four with X expansion.
Nine-bit X positions and lower-number sprite priority place the slices in the
declared C64SC raster coordinates. Coverage is tracked separately from color,
so an opaque pixel is not treated as transparent merely because of its color.

Three mature pre/post-clear pairs at cells 64..66 supply 24 nonzero original
data-latch matches and preserve MCBASE 3..24 across four cycles. All observed
slot payloads at offsets3..26 remain original. The earlier documented live
pointer-table writes occupy unused atlas padding, not those payloads.

The mature trace binds all 1,072 pointer stores: 133 ordinary cells plus one
extra final cell. Their observer positions begin at raw18, after the early
sprite-fetch window, confirming why the current RAM pointers are newer than
the cached pointers. Source rules come from the pinned official VICE3.10
archive, SHA-256
`8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1`;
the receipt records guarded fetch, palette, priority and raster-layout source
fragments. Store coordinates remain observer boundaries, not asserted physical
bus-write timestamps.

The end-of-effect table clear changes fifteen entries `$0741..$074f` only
**after** D015 disables sprites at raster 211. Those later RAM values are not
used to reconstruct already drawn pixels. The extra final kernel cell reads
prepared row 0, while the selected final raster row 210 still displays the
previous ordinary row 132, a blank margin here. Idle graphics, blank-slot,
border and stable register/bank/color guards are checked explicitly.

The completed snapshot is PC=`$0cfa`, clock 143,600,978, raster 220/raw38. Its
serialized raster's current line is 220, so every compared row through 210 is
committed; no partially drawn DBUF or stale raster tail is included.

The 17,028 visible opaque sprite pixels divide by sprite number as follows:

```text
672, 1752, 3504, 3504, 3504, 1606, 1752, 734
```

All eight counts are positive. There are 1,898 overlap events. Both expected
and actual 42,560-byte index images have SHA-256
`83f27386aa6570a6ef2e9477de2da44c726d340cb498ae4fc5641531352d656a`.

Wrong models give these differences:

| Model | Differing pixels |
| --- | ---: |
| No sprites | 17,028 |
| Decode multicolor data as hires | 12,069 |
| Ignore high-X bits | 3,841 |
| Ignore X expansion | 5,256 |
| Use the fresh row instead of the cached previous row | 13,976 |
| Give every sprite byte offset 3 | 10,084 |
| Reverse sprite priority | 0 — inconclusive here |

The last control remains explicitly inconclusive: overlapping slices can
select identical colors. Pixel equality in this scene does not uniquely
distinguish priority order.

## Replay, evidence and remaining scope

```sh
rtk proxy python3 research/no-bounds/spritefpp_visible.py
```

The producer writes
[`spritefpp-visible-proof.json`](../../build/research/no-bounds/spritefpp-visible-analysis/spritefpp-visible-proof.json),
expected/actual index images, the mature store trace and the 72-layout model
under ignored `build/research/no-bounds/spritefpp-visible-analysis/`.
The closed native case digest is
`8c5d4587365f905277b0b57af076f68b7a2d8db7c03bc855ce6763355cbb51bc`.
The [native PNG](../../build/research/no-bounds/native-03/mature-window.png)
is retained for visual review; its entire raster is not the comparison scope.
The frozen native02 proof and raw-wire auditor remain unchanged. Their narrow,
recorded autostart adaptation is reused for this new case.

This establishes one visible original pose, layout and palette. The earlier
[64-pose atlas investigation](frontier-geometry-20261108.md) explains the
prepared representation; it does not turn one native component into an
all-pose animation proof. A useful next case varies the pose, X expansion or
palette and repeats a committed component comparison. Later Y-pulse/tunnel
phases need fresh row-window and pointer-schedule guards. The supplied
standalone still needs its own genuine startup and separate comparison.
