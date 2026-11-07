# Second Reality DB: two one-bit layers combined by OR

Research date: 7 November 2026. DB produces its rippling bitmap pattern by **independently shifting two prepared one-bit layers and combining them with OR**. They occupy opposite bits of each multicolor pair, so background, either individual layer and overlap select four palette entries. This is an original byte/instruction-derived mechanism, not a polygon or vector pipeline inferred from its appearance.

The check matches **32,768 prepared pattern bytes**, **1,024 lookup bytes**, and every one of **6,144 bitmap stores** in a complete native logical update. The [preceding transition note](second-reality-da.md) establishes the original DA/DB/EA/EB transfers and their non-file gaps.

![Original native DB output observation](../../build/research/second-reality/native-03/db-iteration-b.png)

This native PNG shows the original output. The proof below checks bitmap RAM and source addressing; it does not compose a VIC frame or establish analog output.

## Actual entry and display storage

The restored CB bridge enters original DB at **`$C000`**, after loading DA at `$4000`. DB's 3,072-byte payload occupies `$C000..$CBFF`; its PRG hash is `1c820bd4bc9d47a78f4c3c291be3a2ef7fd4f7a6754843632cfaf8410a48a8f2`. DA supplies 2,048 pattern bytes at `$4000..$47FF`, PRG hash `e3cb254ab2362ec54cca87386dd388658736953c163f89b607cb7781af65c137`.

DB initially fills `$E000..$FFFF` with `$FF`. It selects `$D011=$3B`; the prepared capture has `$D016=$18`, `$D018=$38`, CIA2 port A `$80` and direction `$3F`. These establish multicolor bitmap mode, bank **`$C000`**, screen matrix **`$CC00`**, and bitmap base **`$E000`**. Palette setup varies during the introduction; it is separate from the bitmap-value calculation.

The drawing window spans 32 character columns and 192 pixel lines. Each stored source byte supplies eight physical horizontal pixels; every calculated byte is written to **two adjacent bitmap row bytes**, vertically duplicating the sampled line. The matrix/Color RAM viewport is initialized in columns 4–35 of 24 rows. This is a 256×192 window within the bitmap, not evidence of a full-screen 320×200 redraw.

## Why OR gives the interference colors

All 2,048 DA bytes satisfy **`value & $AA == 0`**. Only eight byte values occur: `$00,$01,$05,$15,$40,$50,$54,$55`. The pattern therefore uses only the **low bit of each two-bit multicolor pixel**.

Preparation preserves that mask in all 16 KiB of the first-source planes. The later scatter loop shifts its values left once, so every byte of the 16 KiB second-source planes satisfies **`value & $55 == 0`**. These complementary bit masks are asserted for every byte in the maintained checker.

| First layer bit | Second layer bit | OR result | Ordinary multicolor bitmap selector |
|---:|---:|---|---|
| 0 | 0 | `00` | Background register `$D021`. |
| 1 | 0 | `01` | Screen high nibble. |
| 0 | 1 | `10` | Screen low nibble. |
| 1 | 1 | `11` | Color RAM nibble. |

Thus the overlap gets its own palette choice without adding colors or calculating geometry. Different source-row/horizontal offsets move the two versions of the same pattern relative to each other.

## File-derived preparation and its strict boundary

The original `$C400` routine first constructs a table that reverses the order of four **two-bit groups**, mirrors each DA source row into a wider row, and generates three shifted companion planes. Its literal page-carry behavior is retained. The result is **16,384 bytes at `$8000..$BFFF`**.

The independent CPU check begins at original **`JSR $C400`, `$C05A`**, using only known DA/DB file bytes. It executes **152,624 instructions / 452,062 nominal CPU cycles**, then stops at **`$C4D4` before the CPU-port sequence `LDA #$36; STA $01`**. No port write or response is supplied, and no later hardware execution is silently skipped into that CPU result.

The following `$C4D8..$C54A` data loop is checked with a separate host oracle. For each block, row and column, it transposes the prepared bytes into character-interleaved addressing and shifts them left once. All **16,384 bytes at `$4000..$7FFF`** match the native prepared capture. Together, the two layouts expand the original 2 KiB mask into **32 KiB of prepared data**, allowing differently addressed layers and pixel phases to be combined cheaply at runtime.

The lookup oracle separately checks **`$0400..$07FF`**, 1,024 bytes. These include mirrored row-address pairs for both layouts and the two stored 128-sample movement tables repeated into 256-byte pages. These are address/sample preparations, not projection or polygon-visibility tables.

All preparation comparisons use first **`$C620`**, clock **317,986,879**, raster 186/raw cycle 49. The full EA/EB staging copy at `$2000..$3FFF` is owned by the transition proof; its 399 non-file bytes remain explicitly separated and are not inputs fabricated for this DA-pattern preparation.

## The 96-row runtime kernel

At `$C200`, DB derives the first layer's byte/pixel phase and prepares **96 indirect source pointers** in `$28..$E7`. `$C560` computes the other layer's offsets and patches the **96 absolute OR source operands** in the unrolled kernel at `$C7C0`. The original eight phase bytes advance by **`+4,+3,+2,+4,-1,+3,-3,-5`**. The CPU replay retains actual 6502 carry behavior in the adds/shifts rather than substituting a real-number average.

Each unrolled row block is 11 bytes:

```text
LDA (row_pointer),Y
ORA prepared_source,X
STA bitmap_row,X
STA bitmap_row+1,X
```

The outer loop runs 32 times with **`X=0,8,...,248`**, advancing Y once per horizontal group. The 96 row blocks therefore issue **`96 × 32 × 2 = 6,144` bitmap stores**. No span-length or polygon-edge loop is involved.

An independent host oracle reads the prepared row pointers and patched operands at the original kernel entry, then calculates, for every row/column:

```text
value = RAM[first_source + Y] OR RAM[second_source + X]
RAM[destination + X]     = value
RAM[destination + X + 1] = value
```

All first-source addresses must lie in `$8000..$BFFF`; all second-source addresses in `$4000..$7FFF`. **Every ordered CPU store—PC, destination and value—equals this independently indexed oracle.** The oracle is conditional on the prepared source operands produced by the original setup. It is not an independent derivation of motion, VIC fetching or a complete displayed frame.

## Native-prestate iteration proof

The checker starts from native iteration A at `$C200`, runs original setup to its actual `$C7C0` call, then continues through the kernel and return to `$C200`. The original JSR-created stack and all CPU registers/flags/ports pass directly between those two RAM-only segments. No synthetic return address, IRQ, ROM read, VIC state or hardware response is supplied.

The complete update executes **16,071 instructions / 70,208 nominal CPU cycles**. Compared with native iteration B:

- All 3,072 DB code bytes, including the 96 patched OR operands, match.
- All 8,192 bitmap RAM bytes match both the CPU result and the independent indexed OR oracle.
- All 192 prepared source-pointer bytes, eight phase bytes and the iteration counter match.
- Final PC, A, X, Y, SP and flags match and are included in the final pass gate.
- The full RAM comparison retains **33 other differences**, including ten stack-page bytes and 23 bytes at `$0C10..$1383`. None is hidden or claimed to establish whole-machine equality.

The consecutive native intervals are **81,640**, **81,390** and **83,354 clocks**. They include the original machine's interrupt and VIC behavior; the nominal CPU total does not. These stops have different raster positions. Neither the source loop count nor these intervals is promoted to a display frame rate.

The source has eight introductory iterations at `$C620`, with palette/raster waiting in `$C700`, followed by a 64-iteration steady section at `$C200`. It then changes the row mapping at `$C257` before a later handoff toward `$2E00`. This proof covers the prepared data and the stated steady interval, not that later stage or a whole-demo algorithm.

## Reproduction and evidence

```sh
rtk proxy build/research/tower-power/cpu-venv/bin/python \
  research/second-reality/inspect_db.py
```

The [checker](../../research/second-reality/inspect_db.py) requires the closed native session, pins the [DA/DB transfer receipt](../../build/research/second-reality/da-analysis/da-transition-proof.json), and retains [all 6,144 ordered stores](../../build/research/second-reality/db-analysis/iteration-a-to-b-bitmap-stores.json), prepared planes, source rows, complete RAM differences and CPU comparisons. A bounded read-only peer review found no material issue; it did not rerun CPU or native execution.

Final script SHA-256: `0e3d596441b7b1439ef3703a8a377c3576a36b5bd564048ecfd5a8be6235124c`. [Final receipt](../../build/research/second-reality/db-analysis/db-proof.json) SHA-256: **`1db288eace0f8c241d9ee3578768bde2bca37fe34c50052fb7877a2a058642bf`**. The earlier receipt/script before the complementary-bit assertions remain preserved under `db-analysis/` with their exact `efcf1209…` / `9d596942…` identities.

This establishes an original bitmap-layer combination mechanism and its bounded preparation/runtime costs. It does not establish an author-assigned phase name, polygon renderer, independent VIC/analog pixel oracle, historical priority or complete-production behavior.
