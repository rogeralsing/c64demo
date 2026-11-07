# Second Reality C64: original bootstrap, conditional SFX, and loader

Research date: 7 November 2026. This examines the original C64 production acquired in [the release note](second-reality.md). It extracts the actual DOS boot, preserves two strict unknown-memory boundaries, and independently decompresses the first payload from file-established inputs. Native captures are comparison targets only; they are never used to supply missing file bytes.

## Original side 1 and actual DOS chain

The side 1 D64 is 174,848 bytes, SHA-256 `05aa03c00be26cab0618f8802477d0bc7226af029c003a253a34bd32c630acf2`. The author archive and current CSDb archive contain identical disk bytes under different filenames. This script defaults to the author-route member `2ndReality_S1.D64`; it does not substitute the PC production's source or executable. [Author download route](http://www.smash-designs.de/releases/c64/2nd_reality.zip), [CSDb original archive](https://csdb.dk/getinternalfile.php/71054/2ndreality.zip)

The title entry starts at **track 17, sector 0**. Its displayed block count is 1, but its real terminating DOS chain contains **169 sectors**. The extracted PRG is **42,890 bytes**, including its two-byte `$0801` load header. Its SHA-256 is `c62598561f3bb6d74e9c399385df6e1dd21890c9fc0abbd952a2a61548a286f5`. The loaded file establishes `$0801..$AF88` inclusive.

BASIC line 1 contains **`SYS2304`**, entering **`$0900`**. A following REM identifies the C64 version. The useful original entry signature is:

```text
0900  A2 00 BD 80 09 9D 00 C0 E8 D0 F7 A2 00 BD C0 08
0910  9D E0 05 E8 E0 28 D0 F5 4C 00 C0
```

The directory count is therefore not a reliable file-size or part-boundary oracle. The full chain, links and sector hashes are retained in [boot-proof.json](../../build/research/second-reality/binary/boot-proof.json).

## Outer wrapper: preserve the unknown-padding boundary

The `$0900` entry performs two literal copies:

| Original source | Destination | Bytes |
|---|---|---:|
| `$0980..$0A7F` | `$C000..$C0FF` | 256 |
| `$08C0..$08E7` | `$05E0..$0607` | 40 |

It then jumps to `$C000`. That copied wrapper sets `$01=$36` and copies five pages from `$AB00..$AFFF` into `$CA00..$CEFF`. The file only establishes source bytes through `$AF88`. **The last 119 source bytes are unknown startup RAM.**

The strict file-only CPU run stops at the first attempted read of **`$AF89`**, in the instruction at **`$C01E`**, after 2,882 completed original instructions. It does not fill the missing bytes with zeros or continue through a hardware installer. Its partial RAM is preserved as `file-only-prefix.ram`.

Statically, `$C028` calls `$CA00`. That installer reaches its first KERNAL boundary at **`$CA1F: JSR $FFBA`**, after 13 setup instructions. It configures data/command channels and uses `M-W`/`M-E` plus a custom IEC sender. Its later 768-byte transfer from `$CBBB..$CEBA` includes **50 bytes beyond file-established input**. Native startup RAM can establish an actual transition for that run, but cannot retroactively turn those padding bytes into original-file evidence.

The literal post-installer path at `$C02B` moves **161 pages**, source `$0A00..$AAFF` to destination **`$0801..$A900`**, then jumps to **`$080D`** at `$C04E`. Every source byte of this particular move is inside the original file. We reconstruct this move separately and explicitly conditionally; that is not an offline execution past the KERNAL/drive boundary.

## A second boundary in the SFX pager

The relocated `$080D` signature is:

```text
080D  78 A2 A1 A0 78 84 01 B9 31 08 99 FF 03 88 D0 F7
```

It disables interrupts, makes all RAM visible, copies the decoder to `$0400..$0477`, and moves the packed input upward in pages. This isolated file-derived pager executes **164,964 original instructions** before it attempts to read unknown source **`$0739`**, at instruction **`$081D`**. That strict stop is preserved in `conditional-SFX-copy-prefix.ram`.

The final pager destination page is `$5F00..$5FFF`. The actual decoder reads from **`$6053` upward**, so the unknown page is outside its input. At the stop, all decoder code and **all `$6053..$FFFF` reader bytes are already established** from the original file. Before starting the separate decoder, the checker explicitly invalidates the entire final page: its old file data at the strict stop cannot stand in for what a completed pager would overwrite. No missing page value is supplied.

This permits a narrower routine-only proof at `$040B`. X=Y=0 follows from the pager's fixed loop counters at completion, independently of the values copied. The initial accumulator is overwritten by the reader before it affects output. The analysis starts that routine with those explicit preconditions, retains unknown padding as unknown, and rejects every unknown or mapped-hardware read. It does not claim that the complete wrapper/pager ran without its recorded boundaries.

## Independently reconstructed output

The original `$040B` decoder uses **`$D7` as a run marker**. Ordinary bytes are emitted literally. Marker forms select a repeated byte with either a short counter or two nested counters; zero/wrap behavior belongs to the original loop, rather than an assumed ordinary little-endian length. The source-reader address is self-modified from `$6053`; decoding stops at the block boundary when its address high byte wraps to zero. It restores `$01=$37` and jumps to **`$9400`**.

The routine-only execution completes after **824,550 original instructions**, producing **60,152 bytes at `$07E8..$F2DF`**. Every output store is accounted for, consecutive and unique. Output SHA-256:

```text
7599810d51826909c19a4ffd9d2a739b4b45ec1a52ef7a8d36f1ecbe5179f6cd
```

Outputs under `build/research/second-reality/binary/` are:

- `unpacked-output.prg`: the 60,152 independently decoded bytes with a `$07E8` analysis load header.
- `file-derived-unpacked.ram`: a 64 KB analysis memory image, **not a claim that unowned startup bytes are zero**.
- `file-derived-known-mask.bin`: one byte per RAM address identifying established memory.
- `conditional-SFX-copy-prefix.ram`: the strict pre-decoder reference; its full 64 KB is not an oracle for unknown padding.

The native owner independently reached `$C000`, `$C02B`, `$080D`, `$040B` and `$9400` through the original boot. Comparison-only checks match:

| Range/contract | Bytes | Result |
|---|---:|---|
| Entire 161-page relocated SFX at native `$080D` | 41,216 | Exact |
| Established decoder code at native `$040B` | 120 | Exact |
| Entire established compressed-reader input at native `$040B` | 40,877 | Exact |
| Every decompressed output byte at native `$9400` | **60,152** | **Exact** |

These comparisons contain no padding exclusion inside their declared ranges. They are raw byte comparisons; the separate native checker owns RAM/VSF correspondence, capture clocks and session provenance. The binary proof does not execute the first display or establish its frame rate.

## The later custom loader is distinct from the installer

In the independently reconstructed image, a direct successor graph from `$9400` reaches the title/menu path and later program. The concrete loader caller at **`$CE0B`** supplies A=`$08`, X=`$5A`, and Y=`$40 + [$CFFF]` to **`$CF00`**. These are statically reached code paths, not a claim that every selection branch has run natively.

| Later routine | Address |
|---|---:|
| Custom C64 loader | `$CF00` |
| CIA2 bank-bit-preserving preparation | `$CF58` |
| Handshake and command transport | `$CF74` |
| Byte sender | `$CF94` |
| Byte receiver | `$CFC0` |
| Self-modified destination store | `$CF3A` |

The `$CF00` signature begins:

```text
24 EA 29 EF 8D 93 CF 20 58 CF 20 74 CF AD 93 CF C9 01 D0 01 60
```

The original installer's **44-byte** sender at `$CB2D..$CB58` matches the later sender at `$CF94..$CFBF` exactly after four JSR-address relocations, `$CB3C→$CFA3`. [Static checkpoint/sender receipt](../../build/research/second-reality/binary/loader-checkpoints.json)

The acquired release credits Dcp for the loader. That supports the attribution **“Dcp-credited custom loader in this release”**, not a known Bitfire/Sparkle library or exact version. [Release credits](https://csdb.dk/release/?id=908)

Addresses are reused: post-decompression `$C000/$CA00` contain different code from the original wrapper/installer. A native breakpoint needs the corresponding phase/signature, not the address alone.

## Reproduce this bounded batch

```sh
build/research/tower-power/cpu-venv/bin/python research/second-reality/inspect_boot.py
python3 research/second-reality/inspect_loader.py
```

[The reconstruction script](../../research/second-reality/inspect_boot.py) pins the original disk and PRG, records both strict stops, and exports the independently known output. Its [receipt](../../build/research/second-reality/binary/boot-proof.json) has SHA-256 `92f272cd978c594467c72a9be0536b29685fbbe0e68e1b18a71d8b9c2718cdfd`. The optional native files are read only after reconstruction, for comparison; they never seed its memory.

[The static loader helper](../../research/second-reality/inspect_loader.py) performs no CPU execution and verifies the exact relocated sender correspondence. Original disks, renderer files and native emulator state are not modified by either script. Per-effect graphics, live-versus-precomputed geometry, loader timing and display behavior remain subsequent research questions.
