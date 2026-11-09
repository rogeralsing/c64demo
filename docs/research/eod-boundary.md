# Edge of Disgrace: two visibility ties and another committed pose

Research date: 8 November 2026. Two further natural original poses now match
the independent geometry → contours → prefix/clear model, including **all
2,048 marker, output and reset bytes per pose**. Their crop descriptors are
generated from original code/constants, not captured descriptors. Both poses
also exercise the original visibility helper's previously unobserved
seven-equal-bit fallback, despite positive exact projected determinants.

For `p082`, the independently predicted output matches **all 16,384 committed
palette indices** in a new 128×128 rectangle. The saved midfetch is blank and
outside that effect rectangle; it supplies no inside/nonblank-glyph latch
witness. Two failed observer preconditions and the final narrowly scoped
two-guard adapter are preserved. This was not a renderer defect.

The new consumer is [boundary.py](../../research/eod/boundary.py), with
[final acceptance](../../build/research/eod/boundary-analysis/accepted-03/boundary-proof.json).
The existing [geometry](eod-geometry.md), [contours](eod-contours.md),
[crop](eod-crop.md) and [display](eod-display.md) producers remain unchanged.

## Original case and independent inputs

The pinned [native06 custody receipt](../../build/research/eod/boundary-case-analysis/accepted-01/boundary-case-proof.json)
accepts twenty full RAM/VSF pairs from a fresh original side-1a boot. The
source/checkpoint generation, natural phase/counter predicates, saved call
continuations, actual warp-off/Speed100 queries and complete display-store
history are separately checked there. The consumer does not repeat that
wire/snapshot audit or start a native process.

Its case listing SHA-256 is
`d328247aab0c1a8953189ea5acfe9aa1bd29a39d04cab5857814309b8f7cca37`.
The accepted manifest is `native-06-files-accepted.json`; the earlier raw
`native-06-files.json` remains an intermediate, not the acceptance authority.
The separate `native-05` observer startup rejection remains terminal/reaped,
with no monitor commands or captures; it is not a shader result. Native06's
one observation wait also remains in its journal and later completes on the
same process/connection.

| Pose | Begin phase/counter | Captured begin angles | Selected helper face |
| --- | --- | --- | ---: |
| `p082` | 1 / 82 | 165, 145, 246 | 5 |
| `p028` | 1 / 28 | 219, 51, 206 | 3 |

Each prediction starts **only from its own `$546A` begin RAM**. The frozen
models rebuild their declared integer tables, calculate ramp, coefficients,
vertex records, visibility, edge intersections and all marker writes.
Captures at `$5473` and `$5476` independently check the 56 declared vertex
bytes and 18 face/edge flags. The marker plane is checked at `$17DB`, before
the prefix, and after filling. Output and reset are checked at `$1750/$1753`.
No later-stage target seeds the model.

For the prefix and clear, this consumer calls the frozen crop producer's
`parameters(original_memory())` and `generate()`. The resulting 32 groups
and 1,650 cells come solely from original files 51/52. Both complete generated
code images are compared with the native begin/prefix states, but native
code is never parsed to choose expected cells. Incoming old output still
supplies the 398 skipped bytes; marker reset retains the same seventeen
nonzero outside-crop bytes. Independent descriptor generation does not turn
those preserved inputs into zeros or prove arbitrary crop safety.

## What the seven-bit helper actually decides

Original `$5B25` starts Y at 6. `$5B27..$5B44` compare up to seven binary
quotient bits, returning early on a difference. If all seven pairs agree,
`$5B46` executes `SEC; RTS`; the caller writes face flag `1−C`, hence zero.
This is the exact original decision tree, not an ideal signed-area test.

For the selected actual inputs:

| Pose / face | Projected points | Signed products | Exact determinant |
| --- | --- | --- | ---: |
| `p082` / 5 | (43,35), (36,8), (58,92) | −399 and −405 | +6 |
| `p028` / 3 | (43,119), (50,51), (47,82) | −259 and −272 | +13 |

The determinant is calculated independently as
`(x1−x0)*(y2−y0) − (y1−y0)*(x2−x0)` using signed integers.
The same helper path normalizes these pairs into fractions:

| Pose | First ratio | Second ratio | Exact difference | Both `floor(128*r/d)` |
| --- | --- | --- | --- | ---: |
| `p082` | 7/27 | 5/19 | −2/513 | 33 (`0100001`) |
| `p028` | 7/68 | 4/37 | −13/2516 | 13 (`0001101`) |

Their denominators keep every doubled remainder within a byte, so these
independent rational buckets equal the source's seven quotient-bit pairs.
The fractions differ, but the observed prefix of seven bits does not.
Both source predictions return C=1/flag=0, matching the captured native
flags. A substitute `flag = determinant > 0` would instead write 1 for
both selected faces and fails identical visibility-state acceptance.

This establishes a precision boundary of the original algorithm. It is
not a finding that a physically visible face is wrongly culled: independent
physical visibility, winding/light interpretation and visual impact of a
different policy remain separate questions.

Both full software results pass. `p082` has active face IDs 3/4, twelve
descending internal lines and 391 plot operations. `p028` has face IDs
1/4, twelve ascending internal lines and 362 plot operations, including a
zero-width outer edge. All 46 intersection bytes consumed by each pose are
freshly computed for that pose.

## The saved fetch is outside the effect span

Three p082 display packets bracket one field:

| Packet | PC | Raster / raw cycle | Machine clock |
| --- | ---: | --- | ---: |
| Setup | `$16BB` | 51 / 57 | 472,553,166 |
| Mid | `$5BA1` | 130 / 31 | 472,558,117 |
| Complete | `$5C9F` | 220 / 35 | 472,563,791 |

The cached matrix span is at vbuf indices **22..37**, character row 4,
VCBASE 378 and RC 7. Fine X is 4, giving physical left
`32 + 8*22 + 4 = 212`; logical row 39 at raster 130 gives top 91.
The observed VMli is 17, so the current fetched index is **16**, before
that span. It contains code 0 and fetches `$7007=$00`; GBUF and its draw
pipe agree on zero. There is no saved inside-effect or nonblank-glyph
latch witness in this case.

The first run's [accepted-01 receipt](../../build/research/eod/boundary-analysis/accepted-01/boundary-proof.json)
is deliberately **failed overall**, although both software poses pass.
I initially attributed the failure to the helper's nonblank assertion.
That attribution was wrong. Exact traceback diagnosis shows the original
function stopped earlier at its in-span assertion, line 121. The first
one-guard adapter's [accepted-02 receipt](../../build/research/eod/boundary-analysis/accepted-02/boundary-proof.json)
fails at that same unchanged span assertion before reaching its blank
assertion. Both receipts and checked producer versions remain byte-exact.

The final new wrapper adapts the pinned, archived original function with
exactly two literal replacements, each required to occur once:

1. The in-span fetch guard becomes the exact observed condition
   `first == 22`, `fetch_index == 16`, outside the span, and raw cycle <57.
2. The nonzero fetched-byte guard becomes `fetched == 0`.

Every other original mode, bank, matrix, Color RAM, cache, pipeline,
clock-phase, border-domain, write-history and complete-index comparison
remains intact. Reversing those two substitutions must reproduce the
original function text exactly. The [retained adapter](../../build/research/eod/boundary-analysis/accepted-03/blank-fetch-adapter.checked.py)
and proof store both source hashes and exact replacements. The returned
scope metadata is separately corrected to remove the old nonblank-witness
claim. The old `display.py` and its accepted receipts are unchanged.

The final producer also pins the **checked files** of both failed consumer
versions, not just their mutable repository producer paths:

| Retained version | Checked-source SHA-256 |
| --- | --- |
| First failed run | `bc29b8dbc13670eca4de2962db40d05a317183c2adea2b8578f867234796d5b7` |
| Failed one-guard adapter | `506f672ff992af2a50287619a696c65320a126e4bd8df52f927d1a6810050b39` |

A separate [passive diagnostic](../../build/research/eod/boundary-analysis/diagnostic-03/diagnostic.json)
first checked that the two-guard version reaches full rectangle equality.
No new capture was taken to obtain a more convenient fetch.

## The complete bounded image still agrees

The independently calculated p082 output matches all three display-packet
software buffers. Actual bank `$4000`, screen `$6C00`, charset `$7000`,
Color RAM 9 and palette `[2,10,7,1]` match the source display contract.
The complete watched history retains four store-instruction hits: two
raster schedules at `$D012` and two acknowledge RMW instructions at `$D019`,
all with CPU `$01=$35`. No watched matrix/charset/color/bank/mode/palette
store occurs in the window. Four instruction hits do not mean four
physical bus writes.

Direct multicolor-pair decoding of the predicted output agrees with every
committed index in **`[212,340) × [91,219)`**. All compared rows end before
the complete packet's current line 220. There are 6,990 indices differing
from the background palette index, so the compared image is not all blank.
The wrong Color RAM interpretation and swapped global-palette controls
differ at 1,672 and 5,318 pixels respectively.

The [predicted committed indices](../../build/research/eod/boundary-analysis/accepted-03/p082-committed-indices.bin)
are 16,384 bytes, SHA-256
`6edd2788b819d11baccf4b8f46bfb51953e488e6635f016a2459f1f70dbe5a33`.
Full image equality and the exact cache/history constraints support this
rectangle; they do not create an unobserved inside/nonblank latch witness.
Marker generation for the next pose can continue while this output is
displayed. This is not an assertion that the CPU or whole machine is idle.

The body intervals are 44,257 cycles for p082 and 42,157 for p028. The case
also retains one p082 begin→next-begin interval of 78,921 cycles. These are
elapsed machine cycles including IRQ/VIC effects, not delivered frame rates,
a whole-animation timing distribution or optimization savings.

## Replay, identities and continuation

Run the passive consumer into a fresh directory:

```sh
rtk proxy python3 research/eod/boundary.py \
  --output build/research/eod/boundary-analysis/replay-new
```

The final producer is 21,275 bytes, SHA-256
`a18737f3cc41ca9ec92015a01e3280da213dc71be618d22d661f77c04ff20b62`.
Accepted-03 is 106,718 bytes, SHA-256
`7c222f3116563b5ecce81b371c6cb7c36e99bd40e3978364b94a84c16dc4235b`.
The consumed case receipt SHA-256 is
`8acd59eb714d844855043cefe5526b872c3569a7af47779c7b7aabbda37c23b1`.

Fresh self and independent root replays reproduce **all fourteen files and
161,925 bytes exactly**. The [self report](../../build/research/eod/boundary-analysis/self-replay-check.json)
and [root report](../../build/research/eod/boundary-analysis/root-replay-check.json)
are retained. Root source review found no material issue. Its report is
2,429 bytes, SHA-256
`0fe95ee3e9e1030fc357bbdf901a7f77b61d514c02dfb025c1f1f434fd481bf1`.
No CPU interpreter, native process, upstream build, frozen producer edit
or product change occurs in the consumer/replays.

These are finite captured workloads. Arbitrary geometry/clipping,
geometric crop safety, every visibility branch, independent physical
lighting, all glyph fetches, full 312-line fields, animation-wide correctness,
delivered FPS and savings remain unproved. Continue with another primary
effect or a separately bounded transition/visibility case rather than
relabeling these finite checks as complete animation acceptance.
