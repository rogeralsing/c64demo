# Dragonbond: visible multicolor bitmap and hires sprite composition

The independent [band compositor](../../research/dragonbond/scanout.py) predicts
**27 complete 384-pixel rows**, in two disjoint bands, from the original bitmap
and sprite data. All **10,368 palette indices match** the retained second-field
output, with zero differences. **7,984 indices are nonzero**.

This extends the earlier [intermediate-byte/DMA investigation](dragonbond.md)
into visible pixel composition. It remains a bounded comparison, not a complete
reconstruction of the artwork or all raster tricks.

## Why the first DMA captures were not visible-picture proof

The first captured picture IRQ runs while `$D011=$2B`, DEN clear, and the
vertical border remains closed. Its saved DMA counters and sprite data still
provide valid fetch witnesses. The selected output rows in that field are
entirely black, so they would give a trivial visible-image comparison.

The checker instead starts at `native-02/picture-field-01-end.vsf`, clock
149,017,061, raster 78/11 in the next field. Actual `$D011=$3B`, open vertical
border, VCBASE=120 and RC=3 identify the active bitmap phase. The later
`native-02/bank80-after-intermediate.vsf`, at 242/13, contains all selected
rows as committed output from that same field. The reader uses VICE's saved
palette-index raster allocation, rather than decoding a screenshot.

Original `scene-41-entry.vsf`, both capture contexts, the complete native
owner audit, original handover proof, monitor log and official VICE source
archive are pinned by SHA-256. The old first-field and handover receipts remain
unchanged; this note does not relabel their scopes.

## Direct bitmap and sprite rules

The recorded second-field setup selects VIC bank `$4000`, screen `$4000`,
bitmap `$6000`, and Color RAM. `$D011=$3B`, `$D016=$D8`, `$D018=$09` select
multicolor bitmap, 40 columns and zero fine X scroll. Each bitmap pair selects:

| Two-bit selector | Actual color source |
|---|---|
| `00` | `$D021` |
| `01` | Screen byte's high nibble |
| `10` | Screen byte's low nibble |
| `11` | Color RAM nibble |

Each pair occupies two physical pixels. The source-defined 320-pixel active
interval is full-buffer x=32–351; the remaining pixels use border color zero.
For line `y`, the oracle samples bitmap row/fine position from `y−51`, then
indexes actual bytes and pairs directly.

All eight relevant sprites are hires, unexpanded and in front of the bitmap
in these bands. A nonzero sprite bit replaces the background with that sprite's
own recorded color. Full-buffer sprite X is VIC X+8. The source's register
history supplies positions, colors and modes; the expected pixels are not
copied from VICE's render or sprite-shifter routines.

The logical old image uses pointers `$2D..$34`, with first displayed row125.
The logical successor uses `$3D..$44`, first displayed row146. The oracle samples
those two full original images, independently of the intermediate's pixel
operands. The separate byte proof checks that intermediate `$35..$3C` contains
the appropriate new head and old tail; native DMA witnesses bind its actual
use. Thus a prepared Y register does not become a fabricated immediate restart
of the still-running old image.

The selected bands are:

- **126–143:** eighteen rows of the old image, spanning intermediate publication.
- **148–156:** nine rows of the successor, spanning the full-pointer handover.

Rows144–147, which contain timing-sensitive X/color changes, are excluded.
The complete bitmap matrix, bitmap image and 24 relevant 63-byte sprite images
match the original scene entry and both compared endpoints. Color RAM agrees
between endpoints. These equality checks do not assert a continuous absence
of transient writes.

## The retained color-write refinement

One selected color store occurs inside a sprite's bounding box: `$D02D` on
line148 at observer cycle32. Sprite6's original source bytes at `$50C6` are
`00 00 10`; its only opaque bit is index19. The leading nineteen pixels are
transparent and do not consume that sprite color.

The checker therefore requires the completed store plus two complete draw
cycles to precede the first nontransparent bit, rather than the start of the
24-pixel rectangle. This conservative margin is tied to the pinned color-pipe
rules. The first, overbroad bounding-box guard and its producer are preserved
under `rejected-bounding-box-color-guard/`. No output row or fitted crop was
changed to make the comparison pass.

## Controls and limits

| Alternative | Different indices |
|---|---:|
| Omit sprites | 832 |
| Decode background as hires bitmap | 6,120 |
| Use the complete successor prematurely in old-tail rows139–143 | 149 |
| Reverse sprite/sprite priority | 0: inconclusive |

The failed reverse-priority control and its producer are retained. These
selected pixels do not distinguish the two priority orders; that outcome is
not counted as evidence of priority behavior.

Actual and independent concatenated bands share SHA-256:
`2c20b9881de3d475e7a46b1f247091b2986f3b6f6b0853d3740a7c3c5dd5ebc0`.

```sh
rtk proxy python3 research/dragonbond/scanout.py
```

Output: `build/research/dragonbond/scanout-analysis/scanout-proof.json`, with raw
actual/independent indices, every control difference, row/store history,
original identities and source copies. No new native execution is performed
by this producer.

The claim covers two disjoint visible bands from one field. Complete artwork,
the excluded position-changing rows, all later states, exact bus phases,
physical VIC variants and whole-demo timing remain open. The fixed color
augmentation in this captured image does not establish arbitrary 3D geometry
or general alpha blending.
