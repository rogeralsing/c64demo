# Aloft: runtime motion-to-call-list generation

Two genuine invocations now match independently: **400 ordered target-byte stores and ADC/status results**, both complete **601-byte dispatchers**, and both natural program returns. The model is [motion.py](../../research/aloft-motion-20261109/motion.py), a finite table transform, not a CPU interpreter.

The [table/init study](aloft-motion-tables-20261109.md) proves five 512-byte periodic assets and four 1,801-byte programs built on the C64 from short templates. The assets are prepared; target lists are computed at runtime. No analytic sine formula is inferred.

## Source formula and genuine carry

Each program has 200 fixed terms and a final RTS:

```text
LDA table_A_operand_i, X
ADC table_B_operand_i, Y
STA $0502 + 3*i
```

Each store replaces one JSR high byte. The source initializer supplies the opcodes, low `$00`/row-end `$23` bytes and final RTS. **All 200 high bytes are overwritten; no old runtime target high byte is an input.** Generated low operands wrap modulo 256 without advancing their fixed high byte. The model performs exact 16-bit indexed reads into the original duplicated 512-byte assets.

With D clear, each result is `(A_i + B_i + C_i) & $FF`; carry flows to the next term, while A is freshly loaded. There is no CLC. Official SC `6510dtvcore.c` arithmetic/indexed-read anchors are retained in [primary-motion-source.json](../../build/research/aloft-motion-20261109/motion-analysis/accepted-01/primary-motion-source.json).

The source ranges bound every sum including C=1 to at most 107 for E600+E800, or 184 for EA00+EC00/EE00. Thus carry-out is always zero: incoming C affects exactly the first high byte, and the remaining 199 terms have C=0. The implementation still computes every actual ADC and flag; it does not insert an idealized carry reset.

The preceding `$0800` call reaches music before motion. Flags at the earlier display/wait boundary are therefore insufficient. The [new native custody](aloft-motion-native-20261109.md) captures true `$F133` inputs immediately before `JSR $C000`:

| Witness | Invocation index | X/Y | Genuine C/D | First target | Return A |
| --- | ---: | --- | --- | --- | --- |
| first | 0 | `$07/$5B` | 1 / 0 | `$3800` | `$41` |
| later | 64 | `$47/$DB` | 0 / 0 | `$4600` | `$2C` |

The later index follows the source-controlled checkpoint skip, not a phase-derived frame guess. Wrong C predicts `$3700` in the first case or `$4700` in the later case; only dispatcher offset 2 differs. Genuine flags select C independently, never the output oracle. Decimal mode is rejected; music is not interpreted.

## Pipeline and comparison

The current `$0500` list renders first. After glyph reset and music, motion builds the **next** list, then advances its phase immediates. Therefore the phase bytes beside a displayed list must not be paired with that same list as its output oracle. Natural `$F133 → $F136` pairs close the correct generation boundary.

The consumer checks the native receipt's raw identity, then reads only the directly pinned [independent input projection](../../build/research/aloft-motion-20261109/native-analysis/accepted-01/independent-inputs.json). It persists both complete predictions before parsing native post metadata or opening the separate store/target oracles.

Every reported program-interval hook is consumed. Checks cover source STA PC/opcode/address, fallthrough PC, actual A value, invariant X/Y, stack depth, per-term C/N/Z/V and preserved D/I. Both full dispatchers and return A/X/Y/PC/SP/status agree. The generated program leaves controller/counter/palette context unchanged.

At the optional `$F11D` wrapper return, phase X/Y match `$07/$5B → $04/$5D` and `$47/$DB → $44/$DD`; the dispatcher is unchanged and `$05/$06` have not yet advanced. Palette fades and complete wrapper CPU behavior are deliberately outside this model.

Finite source closure confines stores to the 200 dispatcher-high-byte addresses, disjoint from the program, lookup assets, controller and return stack. IRQ is disabled; D is clear; captured CPU mapping exposes the RAM program/assets. Unmodeled external NMI/control diversion, RAM-writing DMA and mapping changes remain excluded assumptions. Four source programs are recognized, but only the first `$C000` controller is exercised natively here.

## Bounded cost and replay

The independently calculated no-stall cost is `JSR6 + 200*12 + indexed page crossings + RTS6`:

| Witness | LDA / ADC crossings | Algebraic cost | Observed cycles |
| --- | --- | ---: | ---: |
| first | 6 / 66 | 2,484 | 2,484 |
| later | 70 / 162 | 2,644 | 2,644 |

Costs are persisted before reading endpoint clocks. Equality applies to these intervals, not whole-frame cost, general stall freedom or animation FPS. Hook clocks are completion contexts, not electrical bus timestamps.

[Accepted motion proof](../../build/research/aloft-motion-20261109/motion-analysis/accepted-01/motion-proof.json): 17,328 B, SHA256 `89786ccf204ac67fe7e7eb47139f02ea8d3f32eb9d76f91986a9bf27f22363ac`. Producer: 25,113 B, SHA256 `76a23ef2758578cef62c919e92258923af015ad1091a59c64e348ae2c7e7e02c`.

Self replay and independent root replay reproduce **all eight outputs / 259,276 B** exactly. The [root report](../../build/research/aloft-motion-20261109/motion-analysis/root-replay-check.json) is 1,601 B, SHA256 `756c032c26fe90d91a0df4e272be602708a3a7c6517b98a6102f3256e0e7b02f`. All source hypotheses and candidates remain retained; acceptance uses frozen closed custody.

```sh
rtk proxy python3 -B research/aloft-motion-20261109/motion.py \
  --output build/research/aloft-motion-20261109/motion-analysis/fresh-replay
```

Next, join a generated list to its **subsequent** natural display call and the established glyph/fetch/pixel pipeline. Other controllers and palette transitions need separate runtime witnesses. This proof makes no complete-field, future-pixel or delivered-FPS claim.
