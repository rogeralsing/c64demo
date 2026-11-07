# Tower Power N2/F1: generated XOR boundary kernels

N2 and F1 use the same normal XOR line-kernel design. They generate code for every horizontal position, collect adjacent packed pixels into one write on shallow edges, and use an integer error accumulator. **They do not use a quantized-slope table for this path.** Their large cosine/product tables belong to 3D math, not line stepping.

The source of these findings is the original unpacked generator code, execution of that code in flat py65 RAM, and the generated code preserved in the native [N2](tower-power-n2-math.md) and [F1](tower-power-f1.md) captures. The routines make **vertical-prefix fill markers**, not a continuous visible pixel line: vertical interiors are deliberately omitted.

## Generated layout and register use

| Role | N2 entry | F1 entry |
|---|---|---|
| Generate normal kernels and entry tables | `$341F` | `$3643` |
| Prepare packed color masks | `$3605` | `$3877` |
| Draw one boundary edge | `$3661` | `$38D5` |
| Marker canvas | `$F700..$FEFF` | `$3F00..$46FF` |

Four normal generated families occupy **5,376 bytes**:

| Family | Generated range | Bytes per logical X |
|---|---|---|
| Shallow, increasing Y | `$5000..$563F` | Three 22-byte lane blocks plus one 34-byte block per packed byte |
| Shallow, decreasing Y | `$5700..$5D3F` | Same, with DEY |
| Steep, increasing Y | `$5E00..$623F` | 17 |
| Steep, decreasing Y | `$6300..$673F` | 17 |

Each canvas column is 128 bytes, holding four multicolor X lanes. Absolute,Y addressing combines a fixed generated column address with Y = row. Since Y is 0..127 and column low bytes are `$00/$80`, the marker EOR reads do not cross pages. The indexed store always has its normal five-cycle cost.

In the shallow family, A holds the error accumulator, X counts a pending run of packed lanes, and Y is the row. Ten masks in zero page cover the possible contiguous packed runs. In the steep family, X briefly preserves the error while A loads and XORs the single-lane mask. The accumulator is not loaded from and stored to RAM on every horizontal step.

F1 also contains a separate constant-store route. The native captured mode has `$3924 = 0`, selecting the normal XOR families above. The measurements here do not silently include that other route or its later memory reuse.

## Exact stepping rule, including its coverage bias

The wrapper sorts endpoints into increasing X and ignores vertical edges. It forms:

```text
DX = x1 − x0 + 1
DY = abs(y1 − y0) + 1
```

It chooses the steep family when `DY >= DX`, otherwise the shallow family. There is no division, slope lookup, or fixed-point slope coefficient per edge. The carry-based subtract/add recurrence determines the rows at runtime.

For local horizontal index `j = 0..(x1−x0−1)` and direction `s = +1` or `−1`, executing the original routines establishes these marker rows:

```text
steep:  y(j) = y0 + s * ceil(j*DY/DX)
shallow:y(j) = y0 + s * max(0, floor((j*DY−1)/DX))
```

One lane marker is produced for every X in `[x0,x1)`. The final X endpoint is excluded. Packed shallow writes may contain several of those lane markers at once.

These rules are exact descriptions of the original recurrence, **not the exact rational ceiling rule used by our renderer**. For example, `(0,0)→(10,2)` yields Tower rows `0,0,0,0,1,1,1,1,2,2`; mathematical `ceil(2*j/10)` yields `0,1,1,1,1,1,2,2,2,2`. Increasing both deltas by one changes the effective slope; the shallow accumulator also has a distinct initial bias. This is a coverage convention to preserve when reproducing Tower Power, rather than an approximation to quietly substitute into our pixel oracle.

## Shallow edges merge packed writes

The first three lane blocks of each packed byte have this shape, with their mask base and absolute column addresses generated into the code:

```asm
inx
sbc DY
bcs nextLane
sta savedError
lda runMasks,x
eor markerColumn,y
sta markerColumn,y
ldx #0
iny                    // DEY in the other family
lda savedError
adc DX
nextLane:
```

When the next lane remains on the same row, it takes only the first three instructions. A row change flushes the pending packed run, moves Y, and resets the run count. The fourth lane has a larger template that flushes at the byte boundary even without a row change. Consequently a horizontal 60-lane edge needs just **15 marker-byte writes**, not 60 read/modify/writes.

Nominal instruction cycles, excluding VIC/IRQ effects, are:

| Shallow path | CPU cycles |
|---|---:|
| First three lanes, retain run on same row | 8 |
| First three lanes, flush and change row | 33 |
| Fourth lane, flush without row change | 29 |
| Fourth lane, flush and change row | 36 |

A taken branch crossing a code page adds one cycle. A forced final partial-byte flush has its own branch condition. These are path costs, not a fixed average for an arbitrary edge.

## Steep edges skip vertical interiors

The steep block is:

```asm
tax
lda laneMask
eor markerColumn,y
sta markerColumn,y
txa
nextY:
iny                    // DEY in the other family
sbc DX
bcs nextY
adc DY                 // then fall through to the next X's block
```

Only the first four instructions write a marker. The loop advances to the next crossing row without plotting its intervening vertical pixels. Its ordinary block costs **18 + 8*n cycles**, where `n` is the number of vertical increments before advancing to the next X, before any taken-branch code-page penalty. At slope 1:1 this is 26 cycles; at slope 2:1 it is 34. Very steep edges can require many increments per X.

The final X block returns immediately after its marker write, taking 20 cycles including RTS. It does not walk Y afterward. This is why a one-column edge with a huge vertical span is cheap, while a two-column edge may still have a long first crossing search.

## RTS endpoints and partial-byte repair

Both wrappers use generated entry tables and temporarily modify the kernels:

- **Shallow:** replace the first opcode at X = `x1` (`INX`, `$E8`) with `RTS`, `$60`. If the endpoint is inside a packed byte, also change the preceding lane's BCS displacement to zero, forcing its pending run to flush. After return, restore `$E8` and the normal displacement `$11`.
- **Steep:** replace the TXA at offset 9 of block `x1−1` with RTS. This allows that last marker write, then returns before unnecessary Y stepping. Restore TXA, `$8A`, afterward.

The exhaustive fixtures check restoration after every call. The saved native N2 and F1 captures also match the regenerated normal families **byte for byte**, with no outstanding endpoint or branch patches in these captures. This avoids interpreting a temporary RTS as a permanent code boundary.

## Measured isolated CPU costs

These figures come from the original instructions in py65 1.2.0. They exclude VIC DMA, interrupts, disk/music work, caller JSRs, and prefix filling. Kernel cycles include their endpoint RTS and actual code-page branch penalties. “Wrapper” includes entry setup, its JSR into the kernel, patch restoration, and the boundary routine's final RTS. Color-mask setup is separate: **121 cycles for N2**, **123 for F1**, plus six cycles if counting the caller's JSR.

| Endpoints | X samples | Marker writes | Kernel cycles | N2 wrapper | F1 wrapper |
|---|---:|---:|---:|---:|---:|
| `(0,20)→(60,20)` | 60 | 15 | 804 | 170 | 188 |
| `(0,20)→(60,35)` | 60 | 25 | 1,089 | 170 | 188 |
| `(0,20)→(60,79)` | 60 | 59 | 2,006 | 170 | 188 |
| `(0,0)→(60,60)` | 60 | 60 | 1,554 | 144 | 156 |
| `(0,0)→(60,120)` | 60 | 60 | 2,026 | 144 | 156 |
| `(0,0)→(2,127)` | 2 | 2 | 382 | 143 | 155 |
| `(0,0)→(1,127)` | 1 | 1 | 20 | 143 | 155 |

For our current [exact boundary kernel](../../src/xor-fill.asm), an ordinary logical-X block costs **48 or 52 cycles**: 27 for operand addressing and the marker XOR, then 21 or 25 for its quotient/remainder step. Our signed quotient jumps over vertical interiors directly, so that cost does not grow with the slope's integer part. It also targets self-resetting immediate operands in the fused fill program, rather than Tower's ordinary contiguous marker RAM.

The useful comparison is therefore conditional. Tower's packed shallow collection can save many stores, and its simple absolute,Y marker addressing is cheaper. Its steep loop can lose on large Y advances. Its mask setup, different coverage convention, and separate marker clear/fill passes also matter. The isolated kernel figures are not a native frame-rate comparison or proof that replacing our exact stepper would improve the full renderer.

Packed-run collection is a separate idea from the biased DDA: an implementation could retain exact ceiling crossings and merge only adjacent lane markers with the same row. That would need its own endpoint/parity and whole-frame measurements; this research changes no renderer code.

## Reproduction and coverage

```sh
build/research/tower-power/cpu-venv/bin/python research/tower-power/lines_kernels.py
```

The [harness](../../research/tower-power/lines_kernels.py) runs the original generators and normal line routines. For **each** program it checks 16,451 cases: all widths 1..63 and heights 0..127, both Y directions, additional packed-X start phases, reversed endpoints, and vertical-edge skipping. Final marker bytes are compared with an independent closed-form row oracle; all temporary kernel patches must restore. Representative traces record original opcode counts and CPU cycles.

Receipts are under `build/research/tower-power/static/lines/`: `kernels-validation.json` and each regenerated canonical RAM image. Only the stated generated ranges are interpreted as kernels; unknown bytes elsewhere in flat reconstructed images remain placeholders. The result establishes the original bounded line behavior and CPU instruction costs, not a complete native image oracle or a PAL-frame budget.
