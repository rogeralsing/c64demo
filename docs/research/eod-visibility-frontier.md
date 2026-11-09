# Edge of Disgrace: seven-bit visibility precision

Research date: 8 November 2026. The original visibility helper does not
always decide the exact sign of the projected integer triangle determinant.
When its first seven normalized quotient bits agree, it returns carry set,
which clears the face flag. Two nearly parallel edges can therefore produce
a nonzero positive determinant and still be rejected. This is a finite
precision property of the released algorithm; it is not evidence of a
visible hole, incorrect physical lighting or a faulty demo.

The new passive [producer](../../research/eod/visibility_frontier.py) retains
the frozen [geometry model](eod-geometry.md). It makes two separate checks:
an explicit coordinate-domain precision study, and a source-predicted
remaining trajectory with six existing native anchors. New original boundary
observations and their displayed pixels belong to a separate acceptance.

## What the source compares

Original `$5A25` first handles zero factors, product signs and normalized
order. For nonzero differences with the same product sign and order, it
compares seven successive binary quotient decisions. Each pair starts from
`min(abs(dx),abs(dy)) / max(abs(dx),abs(dy))`. If a bit differs, the helper
can determine orientation. If all seven agree, it returns carry set.

For positive coordinate differences from 1 through 127, the resulting
seven-bit code is:

```text
min(127, floor(128 * min(X,Y) / max(X,Y)))
```

The endpoint matters. A ratio of exactly one repeatedly leaves the
remainder equal to its denominator, so all seven bits are one: code 127,
not 128. The declared range also matters: a doubled remainder is at most
254 and does not overflow the original byte path. This formula is not
asserted for every arbitrary byte-valued coordinate difference.

The independent signed determinant used for comparison is:

```text
D = (x1-x0)*(y2-y0) - (y1-y0)*(x2-x0)
```

`D` is twice the signed triangle area. Its numeric value is not a count of
visible framebuffer pixels. Comparing `face_flag` with `D > 0` tests integer
orientation, not correct three-dimensional visibility before projection and
rounding.

## Bounded precision result

The study enumerates all **16,129 positive vectors** `(X,Y)` in `1..127` and
groups them by normalized order and seven-bit code. Every generated code
agrees with the formula above. There are **253 nonempty buckets**.

Two vectors from the same bucket make the source-model helper take its
seven-equal-bits fallback. The following totals count ordered vector pairs
with the common triangle origin `(0,0)`:

| Same-bucket class | Ordered pairs |
| --- | ---: |
| All pairs | 1,039,615 |
| Exactly zero determinant | 87,375 |
| Positive determinant, rejected by fallback | 476,120 |
| Negative determinant, rejected by fallback | 476,120 |

These counts use exact rational multiplicities. Within one bucket of size
`N`, the zero-determinant count is the sum of squared equal-ratio
multiplicities. Reversing each noncollinear pair exchanges positive and
negative determinant, so each orientation has half the remaining pairs.
This is an arithmetic counting proof, not a claim to have run every pair
through a CPU or through the scalar helper.

The producer separately executes the source-model helper on **15,876
adjacent rational-slope pairs**, covering every bucket's adjacent vector
entries. It also preserves these explicit controls:

```text
origin (0,0), vertices (1,126), (1,127): D=+1, face flag=0
origin (0,0), vertices (1,127), (1,126): D=-1, face flag=0
```

Both cases have the same seven quotient bits. Thus replacing this helper
with an exact cross-product sign can change face admission. It is not an
equivalent optimization merely because most ordinary poses agree.

## Remaining original motion as a source prediction

The accepted native04 baseline enters phase 1 with counter 120 and angles
`127,31,94`. The source uses velocity selector 8, with increments `1,3,4`.
The new study starts only from that baseline RAM, rebuilds the declared
integer tables and propagates the frozen ramp, coefficient, vertex and
visibility functions.

There are **120 countdown bodies plus 13 fade bodies** until the source
reaches phase 3: **133 bodies and 798 face decisions**. The propagation does
not execute contours, common IRQs, a CPU or display logic. It does not
predict elapsed cycles. Geometry's maximum absolute coordinate difference
in this predicted trajectory is 81, within the precision study's byte-safe
range; zero factors still take their separate source branches.

Six previously accepted native begin/body pairs are comparison oracles at
offsets `0,10,24,48,96,126`. Entry angles/counters and post-body ramp,
projected vertex records, face flags and edge flags agree at every anchor.
None of those later native bytes seed the propagated state. This supports
the stated upstream sequence at six anchors; it does not prove all 133
unobserved bodies or all downstream state updates.

Predicted branch counts are:

| Path | Face decisions |
| --- | ---: |
| Opposite product signs | 504 |
| Quotient-bit difference | 124 |
| Different normalized order | 114 |
| Second product zero | 26 |
| First product zero | 24 |
| Seven equal quotient bits | 4 |
| First product has both zero factors | 1 |
| Both products zero | 1 |

Four predicted entries use the seven-bit fallback:

| Offset after baseline | Phase / counter | Entry angles | Face | Determinant |
| --- | --- | --- | ---: | ---: |
| 35 | 1 / 85 | 162,136,234 | 1 | −8 |
| 38 | 1 / 82 | 165,145,246 | 5 | +6 |
| 47 | 1 / 73 | 174,172,26 | 3 | 0 |
| 92 | 1 / 28 | 219,51,206 | 3 | +13 |

Only the two positive entries differ from `D > 0`. Their projected points
are `(43,35),(36,8),(58,92)` and `(43,119),(50,51),(47,82)` respectively.
These specific phase/counter states provide natural observation targets.
A future checkpoint must select only original dispatcher/phase/counter
state, never predicted coordinates, face flags or determinant results.

## Reproduction and continuation

The accepted [proof](../../build/research/eod/visibility-frontier-analysis/accepted-01/visibility-frontier-proof.json)
is 457,861 bytes, SHA-256
`1890ec2731f4a2ba5cc9807bbb1741849041129add8ed9501a61a5603cf3c319`.
It pins original files 51/52, the existing geometry source and the accepted
native04 custody and six-pose receipts. The initial source trajectory
[diagnostic](../../build/research/eod/visibility-frontier-analysis/diagnostic-01/trajectory-diagnostic.json)
is retained separately; it was not a native test or a discarded failure.

```sh
rtk proxy python3 -B research/eod/visibility_frontier.py \
  --output build/research/eod/visibility-frontier-analysis/replay-new
```

Choose a fresh output directory. The producer performs no network access,
CPU interpretation, native process control, upstream build or product edit.
Independent source review found no material defect in the bounded ratio,
orientation, symmetry-count or oracle-separation claims.

A fresh independent root replay reproduced both accepted files, **469,405
bytes**, exactly. The [replay report](../../build/research/eod/visibility-frontier-analysis/root-replay-check.json)
is 540 bytes, SHA-256
`673b9d4412253de321de6e9cbdf5fd19d6c9583f71b691130f5f6cbf199bc4c5`.

The planned targets were subsequently captured in the owner-closed
[original native06 case](eod-boundary-case.md), using only dispatcher,
phase and counter predicates. The [separate boundary consumer](eod-boundary.md)
confirms both positive determinants, both original zero face flags, the
projected records and all marker/output/reset bytes. It derives its
prefix/clear descriptors from the [original static constructor](eod-crop.md),
so the incoming native crop plan is no longer its generation input.

That consumer also compares every one of the 16,384 committed indices in
the p082 rectangle `[212,340) x [91,219)`. Its mid-line sample is an actual
blank glyph fetch outside the effect's cached span. The two old
sample-specific inside-span/nonblank guards are explicitly adapted in a
new wrapper, with both failed attempts preserved. No inside-effect or
nonblank glyph latch is claimed for this second display observation.

Those two observations extend the six earlier native anchors. The
remaining 125 source-predicted trajectory entries have not received those
native anchor comparisons. Physical lighting, arbitrary clipping, full animation,
full-field display, delivered FPS and optimization savings remain separate.
The broader research now returns to original effect families, including
The Hat's ending and Aloft's author-linked side-2 interaction, while these
finite EOD results remain available as a transfer reference.
