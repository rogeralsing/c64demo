# Nine: released bytes, relocation and generated raster cells

The released PRG contains a self-extractor, a hardware-dependent relocation wrapper, and a RAM-resident effect with generated raster code. The original CPU routines independently reproduce the unpacked payload, nine relocated blocks and three generated timing variants. This note records **CPU and byte-layout evidence**. Later [native initialization](nine-native.md), [character-path](nine-character-path.md) and [Device-trace](nine-device.md) notes add separate hardware-model observations; the initial CPU checks below do not acquire those broader scopes retroactively.

The author’s [explanation](https://www.linusakesson.net/scene/nine/explanation.php) describes ghostbyte graphics, sprite-DMA stabilization, crunched sprites with pointer-table changes, and switching moving digits to character graphics when sprite priorities become troublesome. The binary findings below support particular mechanisms in that account; they do not independently establish every visible section or timing claim. See also the short [release overview](nine.md).

## Pin and reproduce

The [author release](https://www.linusakesson.net/scene/nine/) links the [original PRG](https://hd0.linusakesson.net/files/lft-nine.prg). The acquisition receipt is `build/research/nine/acquisition.json`.

| Item | Exact result |
| --- | --- |
| Released PRG | 14,356 bytes including its two-byte load address |
| PRG SHA-256 | `a257fa0436bc0d97fbeaa906c55489786a26ee6a9213aa3fd0d8e21f9612d839` |
| Load range | `$0801..$4012`, inclusive |
| BASIC entry | Line 30, `SYS2061`, or `$080d` |
| Unpacked payload | 29,884 bytes, `$0801..$7cbc`, inclusive |
| Payload SHA-256 | `ef45ab609f139bb03befcf20ab3253e2bb30debbc4cbd789350607c1c9d54004` |

Run the pinned acquisition and [binary analysis](../../research/nine/inspect_binary.py) from the repository root:

```sh
rtk proxy python3 research/nine/acquire.py
rtk proxy build/research/tower-power/cpu-venv/bin/python research/nine/inspect_binary.py
```

The second command uses the existing research environment with **py65 1.2.0**. It creates ignored RAM images, selected disassemblies and `build/research/nine/binary/binary-proof.json`. The script checks the original PRG hash before executing anything. Its final proof receipt is SHA-256 `2a68b45ae9a6c4e0de061a7233b46a131420070f5d6fe586157bd945f10558cc`.

## First unpacker and second wrapper

The first `$080d` entry copies its small depacker into zero page and the stack area, then jumps through `$3eea`. Execution of the **original official opcodes**, with binary arithmetic and IRQs disabled, returns to a different `$080d` body after **743,360 instructions**. The two output-store sites write exactly 29,884 distinct addresses, once each. No ROM read or mapped I/O access occurs during that run.

Four explicit startup fixtures—uninitialized RAM filled with `$00` or `$a5`, and stack pointer `$fd` or `$f6`—produce the same payload hash and output range. The lower-stack fixtures take 743,332 instructions. The depacker reads `$008a` and a few padding bytes beyond the loaded file; these fixtures establish that changing those initial values in the tested ways does not change its output. This is not a proof for arbitrary CPU flags or every possible startup environment.

At the second `$080d`, the program saves zero page, disables interrupts, changes memory banking, and synchronizes using VIC/CIA state. Unmocked execution stops at its first I/O read, `BIT $d011` at `$082b`, after 1,026 completed instructions. The preceding CIA writes remain I/O observations rather than writes into underlying RAM. The initializer later copies character ROM data from `$d800..$daff`; a zero-filled substitute would not be an authentic display initialization.

To inspect the next stage without fabricating raster or ROM behavior, the analysis executes only the identified RAM-copy loop `$0888..$0907`. An independent host parser reads its backward length/target records. All **29,528 copied bytes** match, and every RAM address outside the loop’s scratch `$02..$09` matches the host result. The original loop takes **119,459 instructions**, stopping before the original `JSR $8000`.

| Destination | Bytes | Source before relocation |
| --- | ---: | --- |
| `$f000` | `$0340` | `$797b` |
| `$e000` | `$0800` | `$7177` |
| `$8000` | `$4b80` | `$25f3` |
| `$7800` | `$0240` | `$23af` |
| `$6800` | `$0480` | `$1f2b` |
| `$4178` | `$0288` | `$1c9f` |
| `$4020` | `$0150` | `$1b4b` |
| `$2f00` | `$0100` | `$1a47` |
| `$1000` | `$1100` | `$0943` |

The actual effect entry is `$8000`: `JSR $8017`, `JSR $8277`, install IRQ `$99bf`, acknowledge VIC IRQ, enable interrupts, and jump to `$8304`. The first five original entry bytes are `20 17 80 20 77`. This identifies a useful native breakpoint; it does not make skipping the wrapper equivalent to an original boot.

## Three timing families, reproduced byte for byte

The RAM-only generator `$807b..$8145` builds three families at `$3000`, `$3400` and `$3800`. Each family contains **21 cells of 32 bytes**, then an `RTS`: 673 bytes per family, **2,019 total**. Original CPU execution takes 8,809 instructions. A separate builder reproduces every output byte, including the changed template immediates; all other RAM matches except pointer scratch `$40/$41`.

The templates at `$a22a`, `$a24a` and `$a26a` differ in instruction placement and addressing modes. With `X=$70`, indexed stores through `$cfa1,X` and `$cfb1,X` reach `$d011` and `$d021`. With incoming carry clear, their relevant **instruction-start** cycles are:

| Template / family | First split `$d011` | Following `$d021` | `STY $d021` | `STX $d021` | `STX $d011` |
| --- | ---: | ---: | ---: | ---: | ---: |
| `$a22a` / `$3000` | 15 | 21 | 26 | 30 | 34 |
| `$a24a` / `$3400` | 16 | 22 | 26 | 30 | 34 |
| `$a26a` / `$3800` | 16 | 21 | 26 | 30 | 34 |

These agree with the author’s three displayed code variants. Six original-CPU cases exercise all three templates with both carry values. Each unpatched cell takes **44 nominal CPU cycles** with carry clear, or 45 with carry set because its initial `BCS +0` is then taken. Mapped register writes leave underlying `$d011/$d021` RAM untouched in the harness.

Those are instruction starts, not VIC bus-write phases. They exclude DMA stalls, IRQ entry, raster synchronization and surrounding setup. The real caller contains `CLC`; no claim follows that a whole rasterline or frame is 44 cycles.

## Pattern rows and pointer-table switches

Each cell normally loads one byte from a 21-row pattern, then stores it at `$7fff`. The pattern is:

```text
c3 81 81 7e ff ff 7e 81 c3 ff c3 81 7e ff ff 7e 81 81 c3 ff ff
```

The generator replaces the final pattern store in cells **2 and 17** (zero based) with `LDA #$50/#$60; STA $d018`. Both affected pattern rows repeat the previous row, so omitting that row’s ghostbyte update preserves the pattern. This is a direct byte-level match to the author’s explanation of hiding pointer switches on duplicate pattern lines.

The separately executed pointer setup `$81ab..$81fa` prepares four tables at `$53f8`, `$57f8`, `$5bf8` and `$5ff8`. The four sprite members here are **0, 2, 4 and 5**, with pointer rows `$90..$93`, `$94..$97`, `$98..$9b` and `$9c..$9f`. These are stage-specific assignments, not the article’s illustrative generic sprite numbering.

Static code provides further connecting evidence: `$9b5a` writes `$35` to `$d017` and later clears it; those four bits select the same sprite members. `$9b8a` loads a raster-indexed `$cb00` table and writes `$d018`. The chunk interpreter `$8d0f` reads a run length plus source/destination offsets and uses four patched copy pairs in one loop. These are convincing candidate mechanisms for the described crunched-sprite preparation; a native trace is still needed to bind their changing state to displayed seams.

## Section candidates and limits

| Original code | Observable role in the bytes | Evidence limit |
| --- | --- | --- |
| `$9900..$99be` | Sets up two sprites, changes `$3fff/$39ff`, reads `$d01f`, returns collision bit in carry | Hardware result not supplied or executed here |
| `$82e2..$82eb` | Calls that detector; carry-clear result changes a timing-family selector from `$34` to `$38` | Does not identify which real VIC revision will select which path |
| `$99bf` IRQ | Dispatches from flags `$cd/$ce/$cf`, calls music `$1003`, installs section IRQs | Static dispatch, not a section chronology |
| `$9b00` path | `$d017` crunch writes, pointer-table updates and jump into generated cells | Strong Device/upper-border candidate; no native raster proof |
| `$9cba` path | Modifies `$d011` scroll/mode state against raster `$d012`, writes `$79ff` | Candidate display-split path |
| `$9d00` path | Additional timed sprite/register handler | Section appearance remains unbound |
| `$8245..$8270` | Nine 63-byte images copied from `$7800+64n` to `$e883+192n` | All CPU writes match independently; the copy alone does not prove character replacement |

The author explicitly attributes the character switch partly to sprite-priority constraints. This pass has not independently mapped that complete switch or reconstructed the digit multiplexer. A store to an address ending in `$3fff` or `$39ff` is not alone proof of a displayed ghostbyte: VIC bank, mode, register timing and screen state must also match. Writes to `$ffff` in these paths commonly update the IRQ vector, rather than the idle byte.

The useful transfer is **layout and scheduling**, rather than a replacement line algorithm: choose representation per scene, prepare alternative pointer tables, place a needed register update on a visually redundant row, and generate several explicitly timed variants. Their hardware benefits depend on the surrounding display contract. Nothing in this analysis measures a renderer speedup, a whole Nine frame rate, or correctness on a physical VIC revision.

The native follow-ups now resolve the initialization and character-switch gaps
for their captured paths, and trace complete `$3000` and `$3400` Device calls.
The remaining native questions above describe what this initial binary pass
alone could not prove; see the owning follow-ups before treating them as the
current investigation status.
