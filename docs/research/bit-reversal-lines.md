# Bit-reversal-rendered lines: Boo! and our XOR filler

BRR is a promising approximate boundary interpolator. It preserves each edge's endpoint displacement while moving the fractional steps to different columns. It does **not** reproduce our current `ceil(y(x))` pixels. The five-cycle inner operation also assumes a register arrangement that our marker plotter does not currently have.

This is host research only. No renderer, assembler target, drive program, or VICE session was changed or run for this investigation.

## Primary evidence

Matthias Kramm / Quiss describes BRR in [his Boo! article](https://www.quiss.org/boo/) and links [two Python rank selectors](https://www.quiss.org/boo/bitreverse.html). [Boo!'s release record](https://csdb.dk/release/?id=232949) identifies the X'2023 4K intro, released 3 June 2023.

The author's claims, paraphrased: comparing a remainder-derived threshold with a bit-reversal pattern replaces fractional stepping with `CPX #immediate; ADC zeropage`, five cycles. The comparison covers interpolation, not pixel plotting. Division and threshold selection still cost time, and short lines can favor Bresenham. Boo! prepares up to nine slopes per frame in its disk drive. The article reports a 172×172 sprite-filled cube, versus 140×140 for Protogeo 100%, and discusses temporal stability as well as changed line shapes. These are author statements, not measurements of this repository. [Source](https://www.quiss.org/boo/)

The linked Python contains a fixed eight-stage selector and a selector that stops when one candidate remains. The second promises the required strict rank, even if its separator differs from an actual list member. Our exhaustive byte-domain run found both returned the exact order statistic in every checked case. [Author code](https://www.quiss.org/boo/bitreverse.html)

No explicit redistribution license was found on those two downloaded pages. Raw HTML and extracted author code remain in ignored `build/research/boo-math/`; the tracked analysis script is our own implementation and comparison harness.

| Download | SHA-256 |
| --- | --- |
| `https://www.quiss.org/boo/` | `21c8010b0058bc6e3337288cab1c1efc3c8d6a54e3a9fc1a2455ba6158fa4da6` |
| `https://www.quiss.org/boo/bitreverse.html` | `6a7cf15d26afe2fd2686494051200c7d7165f83a85c239384cbab5c88995c458` |

The Python text extracted from the second HTML page has SHA-256
`364ec3837a594ba1894d301ab5284cb9d12cc8a57c5ebd7ea508faffa059140f`.

## Explicit host interpolation contract

The following is our endpoint-anchored adaptation to horizontal sampling, rather than a claim about Boo!'s complete machine-code convention. Sort endpoints by X, skip vertical edges, and let `a=leftX`, `b=rightX`, `n=b-a`. Use signed floor division:

```text
dy = q*n + r,  0 <= r < n
R[x] = reverse_bits_in_byte(x)
T = sorted(R[a:b])[r]
y[a] = leftY
y[x+1] = y[x] + q + (R[x] < T)
```

There are exactly `r` selected positions, so `y[b]=leftY+n*q+r=rightY`. Mark only `x in [a,b)`. For positive slopes, each step is `q` or `q+1`; negative slopes use the same floor-quotient form. The sequence stays between its endpoint rows.

For `(0,0)→(8,3)`, including the endpoint:

| X | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Current ceiling DDA | 0 | 1 | 1 | 2 | 2 | 2 | 3 | 3 | 3 |
| Nearest/Bresenham baseline | 0 | 0 | 1 | 1 | 2 | 2 | 2 | 3 | 3 |
| BRR | 0 | 1 | 1 | 2 | 2 | 3 | 3 | 3 | 3 |

The nearest baseline uses halves toward positive Y. Bresenham has several valid tie conventions; that row is one explicitly defined comparison, not a universal Bresenham pixel pattern.

6502 compare carry is inclusive, so the comparison constant matters. The
[released Boo! generator](boo-binary.md) uses `CPX #(reverse8(row)+1)` while X
holds T. Carry is therefore `T >= reverse8(row)+1`, exactly the strict test
`reverse8(row) < T`. A zero remainder can use threshold zero and the ordinary
integer quotient. The host script also checks an equivalent threshold-minus-one
form, with a separate integer-slope convention; that alternative is not the
released machine-code path. Both produce the BRR sequence defined above.

## Reproduced results

The selector check covers **2,829,056 interval/rank triples per implementation**: every `0<=start<end<=256`, and every rank below the interval length. Both selectors passed. No approximate-separator difference occurred in that finite domain.

Scene inputs are the restored single-object icosahedron's 512 poses: yaw `3*k mod 256`, pitch `floor(3*k/2) mod 256`, fields `B-even,A-even,B-odd,A-odd`. The script independently regenerates the rounded quarter-square transform, perspective, and 29/20 zoom. Every generated vertex set and visible-face set matched the archived `d5baf50b…` verification report. This is the same geometry used after the constant-edge-dispatch optimization.

| Quantity over 512 presentations | Result |
| --- | ---: |
| Visible edges, including vertical | 7,690 |
| Nonvertical edges | 7,555 |
| Crossing markers | 118,427 |
| Markers handled by existing `dx=1` fast path | 241 |
| BRR crossings differing from ceiling DDA | 52,312 |
| Nearest-baseline crossings differing from ceiling DDA | 46,589 |
| Mean / maximum changed full-canvas MC pixels, BRR vs ceiling | 102.96 / 185 |
| Mean / maximum changed selected-field MC pixels, BRR vs ceiling | 51.50 / 94 |
| Maximum vertical error from the input continuous edge, BRR | 57/32 = 1.78125 rows |
| Same error, current ceiling DDA | 35/36 ≈ 0.97222 rows |
| Same error, nearest baseline | 1/2 row |

These error figures concern interpolation of already projected vertices. They do not measure or replace the renderer's 3D projection error bound.

There were zero failures in 4,608 full/field prefix-closure checks and 3,072 checks that a field equals selecting its rows from the full canvas. BRR produced no black samples between the first and last colored sample of any canvas column in these 512 poses. Rectangle, diamond, steep triangle, one-column and row-127 fixtures also passed reversal and duplicate-edge XOR cancellation. This is bounded host evidence, not a general proof that approximate mesh edges cannot overlap or cross.

## Cycle and memory fit

The current generated marker plot costs 27 nominal cycles, followed by a ceiling-DDA advance costing 21 cycles, or 25 when its fractional correction wraps. The existing one-column fast path performs no advance and is excluded below.

The literal five-cycle BRR core keeps the running position in A and its threshold in X. Our plotter keeps the row in X and clobbers A/Y, so it cannot simply replace the DDA instructions. A compatible candidate is:

```asm
ldy threshold       // 3
cpy #reverseOfThisX // 2: constant in the fixed-X block
txa                 // 2: current row; preserves compare carry
adc rowStep         // 3
tax                 // 2
```

That is **12 cycles per advance**, before plotting. It saves 9 cycles normally and 13 on a correction. Across the recorded poses, gross savings would average **2,508 cycles per presentation**, before extra threshold setup, code dispatch, branch-page effects, IRQs or VIC stalls. The ideal five-cycle arrangement would gross 4,124 cycles, but needs a plotting/register redesign. Neither figure is a measured renderer improvement.

The compatible candidate reduces each fixed-X block from 32 to 24 bytes, saving 1,024 bytes across two 64-column kernels. The existing 256-entry row-to-operand maps and large prefix-code banks remain necessary. The reversal values can be immediate operands in those blocks; a separate 256-byte reversal table is not required at draw time.

The extra setup allowance is small: about 170 cycles per nonvertical edge, or
196 cycles per nonzero-fraction edge if zero remainders bypass selection. There
are 990 zero-fraction edges, including the 241 one-column cases. Our scene needs
about 14.76 nonvertical edges per presentation, about 12.82 with nonzero
fractions. The Python selectors establish correctness; the separate
[binary study](boo-binary.md) executes the actual released drive selector and
costs it against these same pose inputs.

Precomputing every absolute-phase threshold for endpoints `0<=a<b<=63` needs `sum(b-a)=43,680` one-byte entries. That defeats the memory advantage. A phase-reset-at-left scheme needs only `sum(n), n=1..63 = 2,016` entries, but its compare pattern depends on `x-leftX`; it no longer drops into our fixed-absolute-X immediate comparisons. Quick selection avoids the large table. Drive offload can move setup off the C64, but requires a new drive/protocol path and its transfer/latency budget. Those costs are outside this host study.

## XOR and interlace requirements

Canonicalize a shared edge identically regardless of face winding. Keep half-open X coverage and XOR transition colors; never OR colliding markers. The parity of crossings per column then remains correct because BRR changes rows, not which X columns an edge visits. Exact endpoint totals also keep interpolated rows inside the vertex Y bounds, preserving the existing dirty-rectangle envelope.

For a field of parity `p`, map each BRR crossing with the same rule as an exact crossing: `q=ceil((crossingY-p)/2)`. Keep the even-field row-127 terminal sink and consume through the ceiling-mapped maximum closing row. Field selection must happen after full-resolution interpolation.

Shared edges with identical endpoints can cancel exactly. Subdividing one edge into separate segments generally changes its rank thresholds and trace; a T-junction or inconsistent segmentation therefore needs a common boundary representation. BRR also changes the geometric raster oracle: passing a parity check alone would not establish agreement with the current exact polygon interiors.

The released selector at drive `$0401` has now been checked independently against
the rank rule. Transposed to these same 512 poses, with zero-remainder and
`dx<=1` bypasses, it costs about **3,021 cycles per presentation** before call and
parameter overhead. That exceeds the compatible advance's **2,508-cycle gross
saving** by about 513 cycles. The [binary study](boo-binary.md) records the exact
inputs, original-byte execution and exclusions. This particular same-CPU
combination is therefore not an optimization established by the research.
Boo!'s direct position stores and drive preparation are material parts of its
design; its five-cycle interpolation claim alone does not select an architecture
for our current exact marker plotter.

## Reproduce

From the repository root, run the host script. It downloads pinned primary HTML if absent, extracts the author's examples into ignored build output, checks both selectors exhaustively, then performs the scene/fixture comparisons:

```sh
rtk proxy python3 research/bit-reversal/analyze.py
```

If the archived baseline report is available, also verify every regenerated input pose:

```sh
rtk proxy python3 research/bit-reversal/analyze.py \
  --report build/z-culling-after/verification/verification.json
```

Results and raw downloads are under `build/research/boo-math/`. `--sample-author` is a quicker smoke run; it is explicitly marked non-exhaustive in the receipt. `--fetch` refreshes downloads but rejects changed SHA-256 values until someone reviews and updates the source pins.
