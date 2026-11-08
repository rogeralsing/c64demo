# Anomaly: four upper-wall fields and one coherent 200-row display

The [passive upper compositor](../../research/anomaly/upper_scanout.py)
matches **four complete 104×384 upper intervals, raster 51–154:
159,744 palette indices, with zero differences**. The fields reuse **one
prepared wall bitmap and attribute image**; four moving sprite placements
make the four output strips distinct. These are repeated comparisons of a
shared wall plus different sprite positions, not four independent wall images.

Field 4 joins the [already proved 96-row floor](anomaly-sprites.md) from
the same original continuation. All **200×384 pixels, raster 51–250:
76,800 indices**, match. The observed result is 199 completed raster rows
plus the completed current-line DBUF row at the native-06 endpoint.
Raster lines outside 51–250, physical-chip behavior and whole-run FPS are
not part of this result.

No new emulator or CPU execution was required. The [source/capture plan](anomaly-upper-scanout-plan.md)
records which evidence already exists and the optional remaining active
bank-$C000 fetch witness.

## Original image, source and native lineage

The checker pins seven existing receipts: original Sparkle bundle36,
native-04/05/06 ownership, the independent upper-image/update proof, the
complete-floor proof and the author-source receipt. It reads the frozen
snapshot/layout decoders and the official
[VICE 3.10 source archive](https://sourceforge.net/projects/vice-emu/files/releases/vice-3.10.tar.gz/),
SHA-256 `8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1`.
Source copies and literal rule guards are retained in its separate ignored
`build/research/anomaly/upper-scanout-analysis/` tree.

The first completed [upper update](anomaly-upper.md) published bitmap
`$E000..$F03F` and attributes `$CC00..$CE07`. That existing proof independently
derives all 4,160 bitmap bytes and 520 attributes from a 39-cell left shift
plus incoming column. The new checker requires those exact prepared-image
hashes at publication and in every compared field. It does not replace the
prepared-image oracle with a screenshot or replay it as its pixel model.

| Field | Actual upper prestate | Completed upper output | X of sprites 4,5,6,7 |
| --- | --- | --- | --- |
| 1 | `native-04/field-pre.vsf` | `native-04/field-post.vsf` | 88,292,292,58 |
| 2 | `native-04/field-02-pre.vsf` | `native-04/field-02-post.vsf` | 80,280,280,44 |
| 3 | `native-04/field-03-pre.vsf` | `native-04/field-03-post.vsf` | 72,268,268,30 |
| 4 | `native-05/restored-arcade.vsf` | `native-06/floor-line-drawn.vsf` | 64,256,256,16 |

Every RAM file equals the complete physical-RAM module of its paired
snapshot. CPU, clock and beam match the owner receipt. Each pre/post pair
has the same field label computed from saved CPU clock and PAL beam; the
four labels differ by 19,656 clocks. This checks retained-field coherence,
not register bus phases or a universal renderer deadline.

Field 4's restored prestate is byte-identical to the original
`native-04/field-04-pre.vsf` in C64MEM, MAINCPU, VIC-II, CIA1 and CIA2.
Its later native-06 endpoint and the floor proof refer to the exact same
snapshot. The earlier native audit already excludes injected inputs,
RAM/code/PC edits and records owner closure. No frozen producer, receipt
or previously indexed identity is changed by this extension.

## Direct upper pixel model

Actual CIA2 PRA=`$F8`, DDR=`$3F` selects bank `$C000`.
`$D018=$38` selects screen `$CC00` and bitmap `$E000`.
`$D011=$3B` selects hires bitmap and Y scroll3; `$D016=$C7` has multicolor
clear, 38-column selection and X scroll7. The pinned VIC definition opens
the 25-row display at line `$33`, 51.

For upper-relative line `n=line−51`:

```text
row       = floor(n/8)
fine_y    = n mod 8
bits      = RAM[$E000 + 320*row + 8*cell + fine_y]
attribute = RAM[$CC00 + 40*row + cell]
pixel     = bitmap_bit ? attribute>>4 : attribute&15
```

The source-defined 38-column active interval is full-buffer x=39–342.
With fine X=7 it contains bitmap x=0–303. Border color is actual `$D020=0`.
The oracle indexes cells and individual bits directly. It does not execute
the VIC pixel-shifter implementation or choose a fitted crop.

The wall image is stable through all selected boundaries. The bitmap hash is
`429638efca0374578677edbfbe3bcb9b2b13bd09b4f5db382c075b0bee19f518`;
the attribute hash is
`d9e155dd84805e12d2fb9cc7c8e44457ae41130f37cd8684a508d2503a96af92`.
The first 35 rows, 51–85, have no sprite contribution: 6,583 of their
13,440 pixels are nonzero. Their identical four copies are explicitly
reported as reused imagery.

## Upper sprites and their actual movement

Sprites 4–7 have pointers `$28..$2B` in `$CFFC..$CFFF`, selecting
`$CA00..$CAFF`. These 256 bytes equal both the actual mirror at `$7400`
and the fully known original bundle's `$7400..$74FF`. Slot byte63 is
excluded from pixel rows. No uninitialized original `$CA00` byte is invented.

Actual state supplies Y=`113,85,96,120`, multicolor and X expansion enabled,
Y expansion clear, priority in front of bitmap, own color14 and shared
colors1/3. Sprite source row is `line−Y−1`. Two-bit groups choose
transparent/shared0/own/shared1; each group occupies four pixels after
X expansion. Sprites 0–3 have no upper Y start.

Original `$3BF8` sets `$D011=$3B`; `$3C07` sets X expansion `$FF`.
The unchanged sprite preparation code ends with `STY $D010` at `$3D80`.
From the previous publication/floor poststate, actual speeds `(8,12,12,14)`
and the source's observed no-borrow/no-wrap branches reproduce all four
next upper positions. The checker preserves these limited branch conditions
rather than claiming unobserved wrapping cases. Saved `$CB=$60` is the upper
high-X mask; the floor later uses a different `$D010` value.

The three retained intervening upper `$D016` store observations are all
original `$B857`, value `$C7`, line251/raw24. Actual endpoints and unchanged
original `$B82A..$B863` code bind `$B85C/$B861` to the saved upper screen/bank
selection. The upper/floor phases remain separate. There is no continuous
watch trace of every upper bank/mode/sprite store, and no monitor timestamp
is promoted to a certified hardware bus phase.

## Comparisons and controls

Each strip contains 39,936 indices:

| Field | Nonzero output pixels | SHA-256 shared by independent and observed upper strip |
| --- | ---: | --- |
| 1 | 13,871 | `c3f2e5df9586e391803b8c0c1cb32e9d52862004e74d0c78dbdaf21cc2075f36` |
| 2 | 13,860 | `0dcec48fc4e4406582fb218a6fe4027f38f62ae44a2a2090d6264145d52fdc6c` |
| 3 | 13,840 | `fcd1679c662fe6663b750871e34e30127e3a502a4a785752dc35ed7f972305f5` |
| 4 | 13,825 | `ab70d33cb0b2656ab56210e3f64cc7b7bf1d140b799edf27a656a4daf9660fc8` |

Wrong-model controls retain every differing coordinate/value:

| Alternative | Different pixels in fields 1 / 2 / 3 / 4 |
| --- | --- |
| Omit sprites | 264 / 264 / 253 / 216 |
| Decode sprites as hires | 200 / 200 / 196 / 158 |
| Disable X expansion | 212 / 212 / 205 / 196 |
| Decode wall as multicolor bitmap | 12,951 / 12,937 / 12,924 / 12,952 |
| Put sprites behind bitmap foreground | 110 / 116 / 97 / 64 |
| Reverse sprite/sprite order | 0 / 0 / 0 / 0: **inconclusive** |

No two retained nontransparent upper sprite rows overlap at a pixel, so
reversing sprite numbers supplies no distinguishing output control here.
The source priority rule remains guarded, but the receipt does not count
that unsuccessful control as pixel evidence.

The line152 pre-snapshot output boundary also has a control. Treating all
104 pre-snapshot rows as completed current output fails in field1 at
70 pixels in lines152–154. The corresponding later fields happen to have
identical old tail pixels. The checker always takes completed rows from
the matching later snapshot instead.

## Actual retained fetch latches and remaining scope

At all four upper prestates, actual VCBASE=480 and RC=5. All 40 saved VBUF
bytes equal `$CDE0..$CE07`, and CBUF equals actual Color RAM indices480–519.
These bind the final upper matrix row to bank `$C000`.

Four earlier bank-$4000 upper states also retain nonzero graphics fetches:
`$46F3=$19`, `$4946=$0D`, `$4635=$04`, and `$4033=$5F`. Each equals actual
GBUF and draw pipe0, with address derived from saved VC−1/RC and the pinned
fetch-before-increment rule. Two states additionally bind actual laser DMA
data `$557EE2` at `$74C3` and `$BEA800` at `$7480`. Their snapshot identities
and original `$3D89` return PCs are in the new receipt.

Those active fetch samples precede publication in bank `$4000`; they are
not relabelled as active bank-$C000 samples. The [capture plan](anomaly-upper-scanout-plan.md)
offers a bounded optional line86 sample for that residual causal witness.
Its absence does not invalidate the exact saved-output comparison.

## Same-field join and reproduction

Field4's upper and floor proofs have the same raw-state lineage. Their
concatenation equals all native-06 retained raster rows51–249 plus completed
DBUF `[104:488]` for row250. Actual and independent 76,800-byte results share:

`8cbb1d7ea5696b9d624d8460d85a8b43294cf27164fee90096ce5e850af18bd7`.

This is a coherent **200-row bitmap-window result**, including borders and
both upper/lower sprites. The raster's other 112 lines are outside the join.
It is not a complete 312-line frame or whole-demo timing result.

```sh
rtk proxy python3 research/anomaly/upper_scanout.py
```

Output: `build/research/anomaly/upper-scanout-analysis/upper-scanout-proof.json`,
with byte-identical checked producer, eight raw upper-strip files, two joined
files, source copies, matrix/fetch witnesses, motion links and discriminating
or inconclusive controls. The producer reads saved evidence only and preserves
all earlier proofs.
