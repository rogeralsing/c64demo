# SMGF hardware polygon panels

An original folding triptych made from **four moving stretched edge sprites
and four gap sprites**. The VIC fills the visible polygon areas through
sprite coverage and priority. There is no bitmap filler or software-rendered
sprite canvas.

The representation follows the full archived
[Sprite vectors article](https://codebase64.net/doku.php?id=base%3Aspritevectors),
read alongside [the owning research section](../../docs/research/lines-and-vector-fill.md).
The article describes SMGF and its later expansion; its Snapshot 50 Hz claim,
exporter, topology restrictions and music-inclusive budget belong to that
production. This example contains our geometry and raster program, with no
original production bytes. It does not recover Snapshot's exporter.

```sh
./experiments/smgf-vectors/build.sh
./experiments/smgf-vectors/run.sh
python3 experiments/smgf-vectors/verify.py
```

Run from the repository root, using the shared Kick Assembler/VICE helpers
and installed Python/Pillow tools. Output: `build/example.prg`.
PAL is required; physical hardware has not been tested.

## What actually fills the polygons

The scene has three adjacent six-vertex panels, bounded by four piecewise
linear edges. Each edge has top, middle and bottom knots. The complete
envelope is at most 192×120 physical pixels. It is a folding ribbon rather
than a 3D cube or an unrestricted mesh renderer.

Every sprite is X-expanded, so a solid source row covers 48 pixels. Sprites
0–3 have descending roles:

| Sprite | Role |
|---|---|
| 0, highest priority | Black final right-edge mask |
| 1 | Light-blue start of the right panel |
| 2 | Purple start of the middle panel |
| 3 | Cyan start of the left panel |
| 4 | Cyan gap underlay at X=88 |
| 5, 6 | Purple gap underlays at X=128 and 152 |
| 7 | Light-blue gap underlay at X=192 |

The lower-priority underlays fill holes left by the finite 48-pixel edge
strips. Higher-priority edge strips cover their overshoot at the next
boundary. The black rightmost strip removes the final overshoot. These
are real VIC sprite overlaps, not painter stores into a framebuffer.

All eight DMA streams start at Y=60. A timed expansion crunch changes
MCBASE from 45 to 53 on line 76. Subsequent cycle-15 expansion writes hold
that counter at 53. The only solid pixel data is **three constant white
bytes** in source row 53; a second constant sprite is blank. Switching
between two pointer matrices gates the panel's top and bottom while keeping
DMA timing constant.

Four X positions change each raster line. Their writes are deliberately
ordered around the beam: the middle-right edge is written before it is
displayed, while the other three edges are written after their current
48-pixel strips have passed. Their prepared values therefore use explicitly
different current/next-line indices. The bounded coordinate ranges and
fixed gap anchors are part of this engine's contract.

DEN stays off through raster line 48 to suppress badlines. It is enabled
at line 50 to open the normal vertical window, then disabled again after
line 51. The background uses an invalid bitmap/ECM mode and stays black.
The example does not open the borders.

## Prepared work and publication rate

`prepare.py` generates 16 poses from our sine-driven knot equations.
It computes exact ceiling intersections and exports only edge coordinates
and solid/blank pointer selections: 720 bytes per pose, 11,520 bytes total.
It prepares no polygon pixels.

The C64 executes a 36-byte raster slot per line across lines 80–223.
Two raster-code buffers hold five immediate control operands per slot.
After each displayed field, the CPU patches 36 rows in the inactive buffer.
After four fields, the complete new schedule is published in the bottom
border by changing the next entry address.

Thus a field is displayed every 19,656 PAL clocks, but **geometry changes
every four fields**, nominally **12.5 poses per second**. Geometry and edge
preparation are host work. No runtime geometry or original 50 Hz performance
is claimed. There is no SID player.

The sprite patterns and two pointer matrices live in VIC bank 1. Raster
buffers occupy `$1000` and `$2600`; prepared commands begin at `$8000`.
The patch worker owns zero-page `$02–$03` for its destination pointer.

## Independent native result

Passing receipt:
`build/verification/20261108T094458.823009Z/verification.json`.

The verifier reconstructs the knot equations and uses exact rational
point-in-polygon tests, separately from its eight-rectangle sprite priority
model. The three panel interiors never overlap. Over all 16 poses, the
sprite model exercises 245,188 overlap samples and the right mask hides
14,892 colored samples. All four gap sprites contribute visible pixels:
115, 44,277, 1,778 and 30,306 respectively.

Native PAL VICE then proved:

- **65 consecutive fields and 4,160,000 exact full-screen pixels**, covering
  all 16 poses, four-field publication and the complete pose wrap.
- **93,600 live operands** matched across active and partially updated
  inactive raster buffers. The constant sprite pixels remained unchanged.
- **42 native timing observations** matched eight active DMA streams,
  MCBASE=53, expansion falling writes ending on cycle 15, edge writes,
  current X positions and solid/blank pointer selection.
- Sampled 36-row patch jobs took **3,940–3,959 clocks**, including VIC
  stalls. They finished by raster 288, before the next field's setup.
- Blackening only the gap sprites removed **4,893 polygon pixels**.
  Coloring the final mask red exposed **5,760 mask pixels**. Both native
  counterfactual images exactly matched the separate sprite-priority model
  and failed the normal polygon image, while geometry and DMA were unchanged.

PRG SHA-256:
`1f4c7886dd7d855cfa587eb66f15b8916fbc3136faa810d78cbddb8d1d8dcabc`.
Verification creates a new dated receipt initialized with `passed: false`,
preserves failure evidence and closes its VICE process.
