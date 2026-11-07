# Exact field-row DDA: arithmetic proof and transfer estimate

The negative-error accumulator can reproduce our **exact rational ceiling crossings**, including alternating physical rows, without a slope table. It must use the true edge width; Tower Power's `dx+1/dy+1` coverage rule is not required. The arithmetic is proven exhaustively here. No proposed assembly implementation or native performance result is claimed.

This follows the [original Tower line analysis](tower-power-lines.md). The reproducible [host checker](../../research/tower-power/lines_exact_field_dda.py) models binary eight-bit ADC/SBC carry and compares it with independent integer ceilings.

## Full-resolution rule

Sort the edge into increasing X. Let `d = x1−x0`, signed `dy = y1−y0`, `h = abs(dy)`, and `s = +1` for nonnegative dy or `−1` otherwise. Vertical edges remain skipped. Begin with row `y0` and error:

```text
dy >= 0: error = −1
dy <  0: error = −d
```

After plotting each X's marker, add h to the negative error. If the sum is nonnegative, change the row by s and subtract d until the error is negative again. The resulting rows are exactly `ceil(y0 + dy*j/d)`, not rounded slope samples.

Operationally, an encoded negative error plus h produces ADC carry precisely when a row correction is needed. INX/DEX does not affect carry; each subsequent SBC runs with carry set, and the final borrow clears it. The ending error is always in `[-d,−1]`. The next add therefore starts with carry clear. This avoids the existing generic quotient/remainder advance, at the cost of a loop when the row changes several times.

## Direct field rule

For selected physical-row parity p, each exact crossing c maps to `q = ceil((c−p)/2)`. Set:

```text
D  = 2*d
q0 = ceil((y0−p)/2)
r  = (y0−p) & 1
```

The correct initial errors are:

| Direction | r = 0 | r = 1 |
|---|---:|---:|
| dy >= 0 | `−1` | `−d−1` |
| dy < 0 | `−2*d` | `−d` |

Use the same add/correct recurrence, now subtracting D and changing q by s. It produces:

```text
q(j) = ceil(((y0−p)*d + dy*j) / (2*d))
     = ceil((ceil(y0 + dy*j/d) − p) / 2)
```

To see the initialization, write `y0−p = 2*q0−r`. For positive dy, the number of upward corrections is `ceil((h*j−r*d)/D)`; for negative dy, the number of downward corrections is `floor((h*j+r*d)/D)`. The four initial errors encode those two integer identities.

In our 64×128 input domain, `1 <= d <= 63`, `D <= 126`, and `h <= 127`. The error stays in `[-D,−1]`; error+h lies between −126 and 126. Encoded eight-bit carry and borrow therefore suffice, without signed overflow tests or a wider accumulator.

The direct field row can equal **64** only for even parity when the full-resolution ceiling crossing is 127. It is the existing terminal marker and must go to the dummy sink rather than the odd field or next column. Odd parity never produces q = 64. The current sink's initialization/reset and the prefix's closing-row consumption remain necessary.

Direct q needs a **q-indexed operand-address lookup**, including that sentinel. The current lookup is indexed by full-resolution crossing Y plus parity; feeding q into it unchanged would address the wrong cells. Dirty-history and opposite-parity preservation do not change just because the boundary stepper changes.

## Exhaustive coverage

The checker enumerates all 63 legal widths and all 16,384 `(y0,y1)` pairs, for full Y and both parities. It includes the right endpoint's state even though that marker is excluded from drawing. Absolute x0 does not enter the recurrence, so horizontal translation adds no untested arithmetic state.

All **102,187,008 sample comparisons** pass: 34,062,336 for each of full Y, even q, and odd q. It also checks 99,090,432 transitions, the negative-error interval after every correction loop, carry clearing, row range, and the exact q64 condition. The counts include 33,183 even-field terminal samples.

```sh
python3 research/tower-power/lines_exact_field_dda.py
```

The host script requires NumPy, already available in the research environment. Its receipt is `build/research/tower-power/static/lines/exact-field-dda.json`. This is arithmetic enumeration, not execution of a new assembly routine.

## Practical cycle model

Keeping our current 27-cycle marker-address/write path and storing the error in zero page gives the following **nominal** costs when h and D are also zero-page operands. Carry can remain clear across the marker's loads, ORA, EOR and stores, so only entry needs an initial CLC.

| Field-row corrections | Advance alone | Including current marker write |
|---|---:|---:|
| 0 | 12 | 39 |
| 1 | 18 | 45 |
| 2 | 26 | 53 |
| 3 | 34 | 61 |

The current fixed-point kernel costs 48/52 cycles per logical X. A useful hybrid retains that kernel when `h > 2*d`, and uses the negative-error version only when `h <= 2*d`. The latter can need at most one correction per step. The current one-column fast path should remain separate.

These figures assume an increment/decrement direction is available without adding a per-X branch. Immediate h/D operands can save cycles, but patching two operands in each of 64 generated blocks on every edge is not free. The estimate does not make that assumption. Separate direction families also consume code: four additional 64×29-byte families plus RTS would be about 7.4 KB before entry tables and control. A concrete layout must account for the `$FF01` sink and interrupt vectors; this note does not promise that layout fits unchanged.

For a realistic input distribution, the checker uses the saved 512-field proof at `build/z-culling-after/verification/verification.json`, program SHA-256 `d5baf50b922f23ace12c829e28ef8a6796dd3431b334aff660409334a173c792`. It derives drawn edges from that verified model's adjacent visible face colors and preserves vertical/one-column fast paths.

The hybrid covers a mean **161.79 of 230.83 kernel X samples**, across 7.27 edges per presentation. Its modeled hot-kernel saving is **1,371 cycles per presentation on average**, ranging from 875 to 1,846. This excludes new setup, dispatch, code-page branch penalties, lookup changes and VIC stalls. It is a budget for an implementation, not a measured whole-frame improvement.

## Packed collection remains a separate opportunity

The same verified workload contains a mean 161.24 runs sharing one packed byte and one exact field row, versus 230.83 individual X samples: about 30.1% fewer potential marker writes. Adjacent lanes in one row can be XOR-combined without changing any marker. Mapping directly to q also permits collection when consecutive full-resolution rows map to the same selected row.

That is a capacity count, not a cycle saving: collection needs masks, register allocation and endpoint flushing. A final partial packed byte must flush even without a row change. Tower's old branch-displacement patch cannot be copied by byte offset into a different recurrence. Exact marker equality, half-open endpoints and q64 routing are the acceptance boundary if a concrete implementation is built.

No assembly, renderer binary, emulator process or display state was changed for this proof.
