# Anomaly Arcade: a complete first upper update and three floor traces

The closed `native-04` continuation records the first **28 upper-wall jobs**,
their first publication, and **three consecutive 96-write floor fields**.
All **67 full RAM/snapshot pairs, 4,390,912 RAM bytes**, same-stop CPU/beam
contexts and three PNG identities pass the passive audit. The separate
[upper-copy model](anomaly-upper.md) checks the actual job writes and the
prepared image. This advances the earlier [partial runtime batch](anomaly-runtime.md);
its frozen receipts remain valid for their older, smaller scope.

This is still not an independent full-screen VIC reconstruction, a maximum
renderer budget or a whole-demo frame-rate proof. Root controlled one owned
VICE process; the checkers only read the retained observations afterward.

## Exact continuation, without a substituted entry

The sole restore is `native-03/upper-rejected-post.vsf`, SHA-256
`db7c7cae5e97a0f0c90229fde26767d162ff3f2dd28f5d2d44e18147644a7449`.
Every restored RAM byte, the complete `MAINCPU` module, recorded CPU ports,
registers, clock and beam equal that parent. The original side-one disk is
unchanged. The restored PC is `$3D89`, clock **164,602,120**, raster 44/cycle 4.

The monitor confirms **warp off and Speed=100 before every resume** in this
batch. There is no warp change, data/code write, register/PC write, keyboard
input, additional restore or replacement part. The parent batch's earlier
warp transit remains separately documented. The recorded-command audit
does not claim an external audit of every host action.

At `$36E6`, the actual raster sample is `A=$14`, with threshold `$24`.
The signed difference has bit 7 set, and the pending job reaches `$36F3`
**14 clocks** later. All RAM stays unchanged across that gate-to-entry
interval. This is an observed acceptance, complementing the parent's
observed rejection at `A=$2B`.

Four entry traces and corresponding complete entry/return captures record:

| Job | Count before first publication | Entry |
|---|---:|---|
| Pixel row | 13 | `$36F3` |
| Screen-attribute row | 13 | `$38BB` |
| New attribute column | 1 | `$39B1` |
| New pixel column | 1 | `$39CA` |

Every job returns naturally to `$3D89`. Trace clocks match their actual
entry snapshots. A further pixel-row trace after publication belongs to the
next update; it is retained separately, not added to the first 28 jobs.

The first publication is captured at `$B84B`, clock **166,934,611**, and
afterward at `$B864`, clock **166,934,839**. Status is already zero before
the swap. The independent model checks both that completion and the
subsequent selection/pointer/register setup; an unconditional source swap
is no longer being mistaken for evidence that its preceding work finished.

## Ninety-six stores, not forty source sites

For each captured `$B400→$B828` interval, all **96 `$D016` store events**
match the original expanded PC/index schedule. Each event's A value equals
the corresponding actual field-prestate table byte at `$08..$67`. The
forty static store sites execute through their original loops. The field
events occupy consecutive raster lines **155..250**.

The following `$B857` store is the upper area's scroll setup. Three such
events are retained separately from the **288 floor stores**. This prevents
an apparent 97th floor write from entering the field model.

All 96 observer timestamps in the second and third fields are exactly
**19,656 clocks** later than the corresponding prior field. Their complete
line/cycle vectors repeat too. Entry into `$B400` has slightly different
timing:

| Boundary | Clock | Raster / raw cycle |
|---|---:|---|
| Field 1 | 166,947,994 | 152 / 10 |
| Field 2 | 166,967,650 | 152 / 10 |
| Field 3 | 166,987,309 | 152 / 13 |
| Field 4, entry only | 167,006,965 | 152 / 13 |

The entry deltas are **19,656, 19,659 and 19,656 clocks**. Thus the short
entry jitter does not propagate to the sampled floor-store sequence.
This establishes the observed three-field recurrence; it does not measure
all rendering paths or every frame in the production.

An initial checker assumption that every adjacent store timestamp would
differ by exactly 63 clocks **failed**. In each field the actual histogram
is 90×63, 2×65, 1×64, 1×70 and 1×62. The failed producer and hypothesis are
archived under `native-upper-analysis/rejected-all63-assumption.*`. The
passing checker verifies the repeated full vectors and source/value
schedule instead. As established in the [observer analysis](vice-trace-timing.md),
these monitor coordinates are not certified physical bus-write phases.

## Reproduction and next boundary

```sh
rtk proxy python3 research/anomaly/native_upper.py
rtk proxy python3 research/anomaly/inspect_upper.py
```

The [passive audit](../../research/anomaly/native_upper.py) writes
`build/research/anomaly/native-upper-analysis/native-upper-evidence.json`.
It pins the parent receipt, exact disk, helpers, session, transcript,
captures, trace sequence and failed assumption. Its closed-inventory result
is distinct from the [independent RAM oracle](../../research/anomaly/inspect_upper.py).
The PNGs are output observations, not full-field pixel oracles.

The owned session was closed on 7 November 2026 at **15:16:42 UTC**; helper
exit was 0 and VICE cleanup was −15. This is owner cleanup, not a natural
demo-exit claim. The final saved continuation is:

```text
build/research/anomaly/native-04/field-04-pre.vsf
SHA256 70fbfcde49a6c1b9a1b18ad538d7e0684cc1c7fdaf2ec6a42b40ad734bbf1b5b
PC B400, clock 167006965, raster 152 / raw cycle 13
```

The next useful native step is a coherent scanout/image reconstruction
using the real bank, bitmap, attributes and register history, followed by
wider update/cadence coverage. Do not recapture the first job merely because
the older provisional batch lacked it. Preserve both batches and their
separate evidence boundaries.
