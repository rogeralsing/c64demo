# CA point-field coverage: whole-byte stores and clipping sinks

CA's **992 plot requests do not accumulate 992 independent points**. In the
pinned iteration A→B, 465 requests reach the colored character atlas, covering
459 distinct two-bit pixel lanes. Native B retains 397 of those samples:
**62 requested lanes are absent**, with no extra samples or incorrect colors
relative to the last requested color per lane. This describes the authored
store behavior in one interval, not a claim that the demo is defective.

The [CA architecture proof](second-reality-ca.md) already establishes the
generated plotting routines. This follow-up consumes its existing ordered
1,984 stores and the original native A/B captures. It executes **no CPU or
emulator** and supplies no hardware response.

## What counts as eligible glyph memory

The native lookup tables independently match the finite address arithmetic:

```text
X byte contribution = 8 * floor((x-64)/4), for 64 <= x < 192; otherwise 0
Y page              = $E8 + floor((y-32)/8), for 32 <= y < 224; otherwise $E4
byte address         = 256 * Y_page + X_contribution + (y & 7)
pixel lane           = x & 3
```

The three 2 KB character sets at `$E800/$F000/$F800` represent successive
64-row atlas regions. Their matrix entries encode the column and local
character row. Color RAM enables multicolor cells only in columns **5–35**
of rows **0–23**. This gives 5,952 eligible glyph bytes / 23,808 two-bit
samples. The matrix and Color RAM checks are made against native A and B.

`$E400..$E4FF` is a vertical clipping sink outside the selected charsets.
The first byte-column of each charset row is another sink: its screen cells
remain black. **That address alone cannot distinguish out-of-range X from
valid inputs `$40..$43`**, which also map to the first column. The following
numbers count destination traffic, not a guessed original-coordinate count.

| Destination category | New plot stores | Unique plot byte addresses | Cached clear stores | Unique clear byte addresses |
|---|---:|---:|---:|---:|
| Colored atlas | 465 | 435 | 472 | 436 |
| Black left-column sink | 355 | 157 | 352 | 141 |
| Hidden `$E4xx` sink | 172 | 72 | 168 | 75 |
| Total | 992 | 664 | 992 | 652 |

Across all destinations, 328 plot stores repeat a previously requested byte
address; 160 addresses receive multiple plots, up to ten each. The colored
atlas has 21 byte addresses requested through more than one pixel lane.
Its six same-lane duplicate requests explain why 465 stores represent only
459 distinct samples.

## `STA` replaces the entire four-pixel byte

Each plot value contains exactly one nonzero two-bit selector. Writing it
with `STA` zeros the other three lanes. Drawing also proceeds **one instance
at a time**: 32 cached clears, then 32 plots, for each of 31 instances.
Consequently, a later instance's clear may erase a point just drawn by an
earlier instance; clearing is not a single global phase before all plots.

In the eligible atlas, 45 later cached clears erase a live current-iteration
plot byte, and 23 later point stores replace one. These are 68 plot-write
identity replacements, including duplicate requests; they must not be
confused with the 62 distinct missing endpoint samples. Of those 62 missing
samples, 43 have a clear as the address's final writer and 19 have another
point as its final writer.

Two literal witnesses use `$F508` (zero-based indices in the full store log):

- Store 48 plots `$80`; cached clear 80 writes `$00` to that same byte.
- Store 240 plots `$10`; point store 432 writes `$01`. The earlier lane is
  erased. OR or XOR of those two values would instead be `$11`, retaining
  both lanes at that moment.

Independent ordered assignments reconstruct **all 8,192 graphic RAM bytes
at `$E000..$FFFF`** in native B. They do not reconstruct the rest of the
program's RAM changes. The original CPU proof separately retains its 36
whole-RAM differences outside the exact semantic domains.

## Alternative combining rules produce different results

These are arithmetic comparisons over the same recorded requests, not
simulated hardware. Starting from native A and retaining the original clear
order, changing only point assignment changes the endpoint:

| Point operation | Different eligible bytes versus native B | Different two-bit samples |
|---|---:|---:|
| Original whole-byte assignment | 0 | 0 |
| OR into the old byte | 15 | 16 |
| XOR into the old byte | 17 | 18 |

A fresh, per-pixel last-color-wins reference for the current point requests
differs in 56 bytes / 62 samples. This reference preserves other lanes when
one point is written; CA's whole-byte assignment does not.

![Derived glyph-memory ownership, not a native frame](../../build/research/second-reality/ca-coverage/stored-atlas-ownership.png)

The left panel is the last requested color per eligible lane. The right is
native B's stored atlas, with missing requested samples marked red. The gray
strip is the black left-column sink. This is a visualization of **stored
glyph memory**, not a C64 screenshot or an independently reconstructed beam
frame. IRQ-driven charset selection and concurrent drawing affect what the
VIC fetches over time; endpoint memory alone cannot prove that output.

## Why it cannot replace polygon boundary marking directly

The generated addressing and cached clear operands are useful implementation
ideas, but the combining rule is specialized. A general point compositor
must define same-pixel color priority while preserving unrelated lanes.
CA instead gives the complete byte to its latest writer, including clears.

An XOR-prefix polygon filler has a stronger requirement: all crossing
contributions to the same marker byte must combine by XOR, including shared
edge color deltas and crossings in different lanes. `STA` loses earlier
contributions; OR also fails parity cancellation. Redirecting clipped
crossings into a hidden point sink does not establish polygon closure or
the half-open endpoint rules needed by a filler. CA supplies points from
prepared profiles and live offsets, not an edge rasterizer, visibility
pipeline or prefix-fill pass. A transfer would need to change those
contracts rather than reuse this plot store unchanged.

The [passive analyzer](../../research/second-reality/ca_coverage.py) pins the
source proof, store log and closed native lifecycle receipt. Its
[coverage receipt](../../build/research/second-reality/ca-coverage/coverage.json)
retains collision histories, overwrite witnesses, all missing sample
coordinates, counterfactual results and visualization hash. The result is
limited to this existing A→B interval; it promises no new renderer speed or
whole-demo coverage.
