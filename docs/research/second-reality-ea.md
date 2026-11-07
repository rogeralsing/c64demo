# Second Reality: EA/EB bridge and EC's two-plane character transform

The next effect after DB is a texture-coordinate transform drawn into multicolor character data. Two prepared bit planes supply the high and low bits of each multicolor pair; generated code samples them at moving coordinates and ORs the results. The original code establishes this mechanism without assigning a named part or a polygon renderer. The later native capture shows a purple/white diagonal tiled pattern with alternating horizontal lines.

This continues the [DA/DB preload map](second-reality-da.md) and [DB interference-pattern analysis](second-reality-db.md). Original PRGs come from the already pinned [disk inventory](second-reality-disk-map.md). No new acquisition or emulator run was made by this checker. Root's owner-closed `native-04` session restores `native-03/db-iteration-d.vsf` once, then follows the original program with no inputs or code/PC writes. Its independent lifecycle audit is documented in [the native continuation note](second-reality-native-ea.md).

| Original file | Load header | Payload | PRG SHA-256 |
| --- | --- | ---: | --- |
| EA | `$6000` | 3,817 bytes | `2444dd10effe58b3bc96decaf0199f75433aa74f03a5815bb4445512943ca8ce` |
| EB | `$7000` | 3,976 bytes | `9c0758f571f5ba71b3224a9d1ed1084d07b1adc7e50374e68f07fbcec548f887` |
| EC | `$C000` | 3,231 bytes | `4a39c4a07db39e513af8ad0af2641a649d40fbb8224642808e52996f42523a82` |

The staging addresses and execution addresses differ. DB previously copied full `$6000..$7FFF` pages into `$2000..$3FFF`. Its exit at `$C2D2` jumps to EA code at `$2E00`, which fades DB's colors and clears `$E000..$EDFF`. The following path is bound to original instructions and natural capture PCs:

| Reachable instruction or checkpoint | What it does |
| --- | --- |
| `$2EE4: JMP $3F50` | Enter EB's staged copy helper. |
| `$3F50..$3F71` | Restore all `$2000..$2FFF` to `$6000..$6FFF`; jump `$6C00`. |
| `$6C00` | Set up a character bridge, IRQ and a helper copied from `$6B00` to `$0900`. |
| `$6DD0` | Restore saved loader `$2F00..$2FFF` to `$CF00..$CFFF`. |
| `$6DE1: JSR $CF00` | Request EC with `A=$08`, `X='E'`, `Y='C'`; the capture is **before this JSR**, at `$6DE1`. |
| `$6DE4` | Loader return; all 3,231 EC bytes match the original file and loader end pointer is `$CC9F`. |
| `$6DE4: JSR $3A60` | Restore full `$3000..$3FFF` to `$7000..$7FFF`; return `$6DE7`. |
| `$6DCA: JMP $C000` | After the bridge's music-state waits/helper call, enter EC's actual renderer preparation. |
| `$C00E: JSR $7500` | Generate drawing programs and prepare source planes. |
| First `$CA80` | Preparation complete, before loop-control initialization. |
| `$CA88` | Begin a logical pair: motion/setup and `$9000` draw, then motion/setup and `$8000` draw. |
| `$CABC` | All 16 parameter stages completed; next instructions start the exit wipe. |

The page restores deliberately include bytes beyond the short files. EA's 4 KiB region contains its 3,817-byte body, **23 preserved stale bytes and 256 explicitly saved loader bytes**. EB's 4 KiB region contains its 3,976-byte body and **120 preserved stale bytes**. All page copies match native RAM exactly; these tails are neither file payload nor synthesized zero padding.

Preparation decodes a compact source texture. EB `$7D00` contains 111 `(value,count)` pairs, followed by value `$1C` at `$7DDE`. `$7E00` writes **count+1** bytes but advances the destination by **count**, so neighboring runs overwrite their shared endpoint. Together with the literal first row built at `$7A14`, this defines 4,096 bytes arranged as **16 rows of 256 bytes**. The only byte values are `$00,$02,$0A,$2A,$80,$A0,$A8,$AA`.

Each row is duplicated into two consecutive pages at `$2000..$3FFF`; a copy shifted right by one bit occupies `$4000..$5FFF`. The first 8 KiB uses only the high bit of each two-bit multicolor pair, and the second uses only the low bit. Their OR can produce all four pair values. Duplicating pages allows an indexed fetch to cross a 256-byte boundary without a branch or an unrelated next-row fetch. These are prepared packed bit patterns: a source byte is not an independently fetched texel for each of its four visible multicolor pixels.

EB `$7500` and EC `$C500` generate sibling programs at `$9000` and `$8000`, each spanning 3,078 bytes. The file-known proof stops at `$CA14`, before the later bank write. It executes 76,848 original instructions, taking 273,427 **nominal CPU cycles**, and the independently indexed run/duplicate/shift expansion agrees with every prepared source byte in both CPU output and native RAM. These are preparation counts, not elapsed native timing.

The generated programs contain 480 operand bytes defined by runtime setup rather than by their generator: 192 high source-address bytes, 192 low address bytes and 96 ORA immediates. At `$9000`, preparation defines **2,598 bytes and leaves 480 unknown**. At `$8000`, all 3,078 bytes happen to be file-defined because the preceding run expansion had already filled that RAM; those inherited operand values are still replaced before use. The receipt preserves an explicit known mask. It does not fill unknown operands with zero or claim that all prepared code bytes came from generator stores.

Runtime setup advances four phase bytes using one of 16 parameter sets at `$C480..$C4DF`, then `$C300` derives fixed-point coordinate increments and offsets. Signed tables at `$7000/$7100` have quarter-turn values `0,4096,0,-4096`; `$7400` controls scaling. The three shift/add helpers use the complement of the scale byte. The generated prefixes patch source-address operands and prepare coordinate-index tables at zero page `$40..$9F` and `$CE80..$CEDF`. Carry propagation is part of the original arithmetic; the proof runs these original instructions instead of replacing them with an idealized floating-point rotation.

The indexed drawing operation can be expressed from those prepared bases and tables as:

```text
for row = 0..31:
    for band = 0..2:
        indexA = lookupA[32*band + row]
        indexB = lookupB[32*band + row]
        for column = 0..30:
            n = 32*band + column
            value = planeA[baseA[n] + indexA] OR planeB[baseB[n] + indexB]
            chars[$E000 + $800*band + 64*column + 2*row] = value
```

There are **31 × 96 = 2,976 packed-byte output positions per draw**. Each byte encodes four double-width multicolor pixels, so the populated rows contain 124 multicolor pixels across. In character coordinates, `glyph = 8*column + floor(row/4)` and `glyph_row = 2*(row mod 4)`. Only glyph rows `0,2,4,6` receive samples; the alternating rows retain the initialization value zero.

The source screen maps 31 columns, starting at screen column 4, across 24 character rows: a **248 × 192 physical-pixel window**, containing **124 × 96 populated multicolor-pixel rows** with alternating blank lines. The screenshot's horizontal stripes follow directly from those even glyph-row stores. The IRQ alternates `$D011=$1B/$1C`, shifting vertical scroll by one scanline, but this note does not prove a combined interlaced image or temporal reconstruction.

The two character-buffer sets are `$A000/$A800/$B000` with screen `$B800`, and `$E000/$E800/$F000` with screen `$F800`. Generated draw endings write `$DD00=$81/$80` to select VIC bank `$8000/$C000`. The raster IRQ selects `$D018=$E8,$EA,$EC` for the successive eight-character-row bands, with scheduled raster values `$72` and `$B2` and a return to the top IRQ. Interior Color RAM is `$09`; shared multicolor registers and background are updated by IRQ tables indexed by the running music state. Thus the first solid-color captures do not establish a constant palette or a fixed texture pose. The native `$CABC` capture shows the completed tiled display.

There is a significant CPU-proof boundary at the suppressed last column. `CC00` changes the last store of each 32-column group into `LDA absolute` (`$AD`). In the `$9000` program these occur at `$99E2,$9AE9,$9BF0`, reading `$E7C0,$EFC0,$F7C0`. With the captured CPU port `$36`, these are **KERNAL-mapped reads**, whose A/N/Z results are overwritten before use. The strict checker stops **before `$99E2`**. It supplies no ROM bytes, skips no original instruction, and makes no continuous full-half-draw CPU/register claim.

From native `$CA88` prestate, the RAM-only prefix and first drawing segment execute 3,229 + 293 instructions, or 9,240 + 1,179 nominal CPU cycles, before that boundary. Their first 31 ordered stores agree exactly with the independent indexed model. The model's complete ordered list contains all 2,976 predicted stores; its final **6,144-byte character buffer and generated operands** agree exactly with the natural native `$9C02` endpoint. The model accepts the original prefix's prepared coordinate tables and bases; it is not an independent motion model. All **36 whole-RAM differences** outside its exact domains remain in the receipt, including final loop counters, stack and IRQ/music state.

The native first half takes 100,638 observed clocks. The first three paired-loop intervals are 186,544, 169,217 and 171,425 clocks. These include IRQ/VIC costs and preparation-stage differences; none is a coherent frame or a display-rate measurement. A single PNG also spans VIC work across time and is not an oracle for the indexed-store model.

Reproduce the bounded proof with the existing environment:

```sh
rtk proxy build/research/tower-power/cpu-venv/bin/python research/second-reality/inspect_ea.py
```

The final [checker](../../research/second-reality/inspect_ea.py) SHA-256 is `e85d768424d1bdd3bff5d6a22940cd02035047f979fce7286a868f1e248e2e83`. Ignored receipt `build/research/second-reality/ea-analysis/ea-proof.json` is `3d0b9fac1f2ceb6926b55b9dfea86bcf9caafe2050c717137449f57e0584301e`, with **24 exact domain checks**, exact restore CPU/RAM identity, source/file hashes, all 15 snapshot/RAM pairs, the known operand mask, texture planes and ordered sampled-store addresses. The hardware cycle schedule, whole-field pixels, analog/CRT output and author-specific effect label remain outside this proof.
