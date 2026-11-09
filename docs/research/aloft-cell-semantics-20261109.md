# Aloft generation31: cell dataflow and D011 values

The generated cells apply masks to two state bytes, reverse the resulting bits through `$0400`, and write the lookup results plus the updated state. Their state arithmetic uses OR/AND and has no multiplication, addition, or incoming-carry dependency. A normal cell then increments `$D011`; a row-end cell writes `$18`. This note proves that bounded source contract. It does **not** establish a rendered field or a native post-cell equality.

The [generator study](aloft-cells-20261109.md) independently predicts the final code before comparing generated native bytes. This lane consumes its accepted02 descriptors and the separately accepted [entry context](aloft-cell-context-20261109.md). The [primary-source study](aloft-cell-primary-20261109.md) supplies the official VIC/6510 value rules and distinguishes authored FLD/linecrunch examples from this effect's measured behavior.

## Inputs and provenance

The producer is [cell_semantics.py](../../research/aloft-cells-20261109/cell_semantics.py). It accepts only these pinned contracts:

| Input | Identity and role |
| --- | --- |
| Original decoded generation31 | `bundle031-memory.bin`, 65,536 B, SHA256 `95a344b261b1b28d229da9778df80bae06eff39470ff4515820ce4e1fa86869e`. Its source-byte/known/payload ancestry is bound by the generator proof. |
| Source-predicted cells | [generator accepted02 proof](../../build/research/aloft-cells-20261109/cell-analysis/accepted-02/cell-generator-proof.json), 14,421 B, SHA256 `480428221ed84aed404dde3dfd8fcf9c378aab39f4e00390bfbe9d77aa399e4c`. The layout contains 312 cells/11,232 bytes. |
| Genuine stopped inputs | [context accepted01 proof](../../build/research/aloft-cells-20261109/context-analysis/accepted-01/context-proof.json), 4,831 B, SHA256 `3610d8f46d722667f8d25f4f8976b363afc2c3c632c450f39d8d88d751d7e95e`. Declares physical ZP, separate CPU port reads, `$0400` lookup and `$0500` call targets; exposes no generated cell-body oracle bytes. |
| Hardware value rules | [primary accepted01 proof](../../build/research/aloft-cells-20261109/primary-analysis/accepted-01/primary-reading-proof.json), SHA256 `4fd7cedb1ce4325a6adc0c406406f4a2f6a2cc65ccb7c8ef735d21c02344ed04`; source helper SHA256 `4c8b3e1ae3968fff3bc90af9527fda0a6489c6853ba68f32bf17f4a1c4e74dda`. |

No completed cell state, native `$2000` code bytes, native post-call RAM or committed pixels seed this model. The native lookup is checked against an independently calculated bit-reversal table. The observed motion/call-target state remains an explicit input; its construction or future evolution is not inferred here.

## The exact cell formula

Each page has a 35-byte normal cell at offset `$00` and a 37-byte row-end cell at `$23`. The final 312 descriptors contain 160 variant-A and 152 variant-B cells, with 156 of each role. A strict recognizer admits only the guarded opcode skeleton, mask/operand patch sites and the two boundary NOP substitutions. It does not dispatch arbitrary 6502 instructions.

For the two source-selected state slots `zx` and `zy`:

```text
X = (CPU_ZP[zx] OR mask_or_x) AND mask_and_x
Y = (CPU_ZP[zy] OR mask_or_y) AND mask_and_y
Lx = lookup0400[X]
Ly = lookup0400[Y]
```

Variant A writes `Lx` to the absolute destination and `Ly` to the scratch ZP destination. Variant B writes `Ly` to the absolute destination and `Lx` to scratch. Both then execute `STX zx`, followed by `STY zy`. These are ordered effects: scratch, absolute destination and state can overlap in the full generated domain. The model keeps every admitted store rather than reducing them to a final-address map. The descriptor names `screen_address`/`write_screen` identify the template's absolute-result sink; this note does not derive a screen-fetch or pixel mapping from that name.

`$F676..$F685` initializes the lookup with eight `LSR A / ROL $0400,X` insertions per index. After eight insertions the old table byte is completely displaced. The independent check covers **65,536 index/old-byte combinations** and obtains `reverse8(index)` in every case. Another **159,744 cell/axis/input-byte checks** establishes each patched byte map and its idempotence. The admitted cell skeleton has no ADC/SBC or carry-reading branch.

At the declared pre-IRQ motion state, the first selected cell is `$4600`. Its inputs at ZP `$4F/$57` are both `$FF`; its masks produce `X=$F8`, `Y=$07`. The lookup results are `$1F/$E0`. This variant B conditionally predicts `$E0` at `$0797`, `$1F` at ZP `$DF`, then state `$4F=$F8`, `$57=$07`. These are calculated values, not a native post-cell observation.

## Eight patched cells suppress result stores

The original constant block `$F525..$F559` changes pages `$6C..$6F`:

| Cell-relative sites | Original | Final | Admitted effect |
| --- | --- | --- | --- |
| `$11` and `$34` | `$8D` STA absolute | `$0C` undocumented NOP absolute | No result store; retain target-read dependency. |
| `$17` and `$3A` | `$85` STA zero page | `$04` undocumented NOP zero page | No scratch store; retain operand/address slot without claiming a physical read from the VICE implementation. |

The masks are also specially patched. STX/STY state writes remain. All eight affected cells have absolute destination `$009F` and scratch `$A7`, coinciding with their state slots. The model separately evaluates these eight source cases against explicit pre-IRQ ZP parameters, verifying the two result stores are absent and both state stores remain. Those examples are **isolated source evaluations**, not evidence those cells executed in the recorded path.

Official VICE 3.10 `src/6510core.c` distinguishes the NOPs: `$0C` dispatch at lines 2549–2551 calls `NOOP_ABS`, whose lines 1451–1456 include `LOAD(p2)`. `$04` at 2507–2511 calls `NOOP(1,2)`; that macro at 1447 advances clock/PC without an explicit target LOAD. The model does not upgrade that omission into proof of a physical NMOS bus read, nor a proof that no such hardware read occurs. It establishes the suppressed stores and keeps the unresolved boundary explicit.

## D011 and the final CMP

The normal tail is `EE 11 D0 C1 00 60`: INC `$D011`, CMP `($00,X)`, RTS. The row-end tail is `A9 18 8D 11 D0 C1 00 60`: literal `$18` store, the same CMP and RTS.

For an actual supplied INC read byte `r`, the primary helper gives a dummy write of `r` and final write `(r+1)&255`. The VIC read supplies stored bits 0–6 plus the live raster high bit; it does not simply return the stored byte. This lane has no cell-by-cell raster samples. Consequently each normal call emits the two possible read/dummy/final triples for its known low seven bits. Row-end writes `$18` exactly. These are value alternatives, not an instruction-timing, DMA, border or scanout simulation.

The `CMP ($00,X)` is not discarded as padding. Official `LOAD_IND_X` at 6510core.c 583–588 performs a dummy ZP `$00` read, then reads pointer bytes at `X` and `(X+1)&255`, followed by the target read. CMP at 1067–1076 sets C/N/Z from A minus that target value. Each modeled cell records the post-store pointer bytes/address and leaves target value, physical-read side effects and final C/N/Z unbound. A normal cell's A is the second lookup result; a row-end cell's A is `$18`. The later cells' bitwise dataflow does not consume the unknown incoming carry.

Ports `$00/$01` use CPU-view values, not underlying RAM. Applying the source prefix's `DEC $00` changes the DDR read from `$2F` to `$2E`. This model deliberately leaves `$01` unknown after that DDR change because its new input-pin sample is unobserved; it never substitutes physical RAM at `$0001` into a CMP pointer.

## Conditional composition and its limit

The accepted context's `part08-frame01` is actually **before IRQ `$F080`**, clock 131,462,237, raster 46/cycle 11. It is neither a proven first frame nor a pre-`$0500` capture. Source `$F080..$F0B0` writes the DDR and delay/code operands, preserves the pushed A values, and writes `$D011=$18` at `$F0A5` before `JSR $0500` at `$F0AE`. The actual prefix differs from original source only at self-modified delay operand `$F08F`, recorded rather than normalized away.

The arithmetic composition is explicitly conditional on that prefix reaching `$F0AE`, and on no intervening mutation of the declared ZP/lookup/call-target state. It applies the DDR change and initial D011 `$18`, then walks the **200 supplied call targets at `$0500+3*i`**. There are **69 distinct selected PCs**, **175 normal calls and 25 row-end calls**. Each group of seven increments has low bits `$19..$1F`, followed by a row-end `$18` reset. The chosen targets contain no boundary-NOP cell. Complete 312-cell recognition and these 69 selected PCs are different coverage statements.

The model records 400 state-input reads, 400 lookup reads, 200 absolute-result writes, 200 scratch writes, 200 STX and 200 STY writes, plus 200 unresolved CMP target reads. **There is no genuine post-`$0500` witness in this case**, so the calculated ZP/store sequence has no native endpoint-equality claim. The pre-`$F02B` body context stays a distinct input; it is not silently substituted for a pre-cell state.

## Replay and follow-up

[Accepted semantic proof](../../build/research/aloft-cells-20261109/semantic-analysis/accepted-01/cell-semantics-proof.json): 7,669 B, SHA256 `88e8f06afaa9d066a0587d54b95d8f4a6e8c354eb14908dc09da0e924d5da3ed`. Producer: 16,924 B, SHA256 `cace07aa398eabc901cd29c5d1b3018504e3f9167e0b21e357a72114bf36676d`.

Fresh-directory [self replay](../../build/research/aloft-cells-20261109/semantic-analysis/self-replay-check.json) reproduces **all seven outputs / 641,765 B** exactly. Candidate01 and candidate02 are retained. Candidate01 used the earlier generator01 contract; candidate02 and acceptance use final generator02 and include the corrected primary NOP distinction. Neither candidate is silently replaced.

The parent independently reviewed the complete final producer and repeated it in a fresh directory. Its [root replay report](../../build/research/aloft-cells-20261109/semantic-analysis/root-replay-check.json), 4,778 B, SHA256 `5c1c1edbd3ec42a127efe8235b1ee994c1def5ba0b4bd992e251c64dd45f65bc`, records the same seven byte-identical outputs and no material review issue. This independently checks the passive model's reproducibility; it does not fill the missing actual pre-`$0500` and post-call native witness.

```sh
rtk proxy python3 -B research/aloft-cells-20261109/cell_semantics.py \
  --output build/research/aloft-cells-20261109/semantic-analysis/fresh-replay
```

A next native check should capture genuine pre-`$0500` inputs and a natural return at `$F0B1`, with cell entry/return or write hooks plus actual D011 raster-read values where required. It should retain CMP/NOP read behavior and CPU ports, separate logical writes from NMOS dummy writes, and prove the call-target/code generation stayed unchanged. Only then compare the predicted ordered data writes and endpoint state. Field timing, badline/linecrunch effects, committed pixels and the named layered-pattern scene remain separate follow-up work.
