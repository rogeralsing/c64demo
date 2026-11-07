# Colors: original disks and identified Sparkle bootstrap

Research date: 7 November 2026. This inspects the current original Colors / Lethargy pack acquired for [the Colors investigation](colors.md). It establishes the DOS bootstrap and loader family. It does not identify the color-combination renderer, execute a packed demo part, or supply a drive/KERNAL model.

## Current pack and DOS contents

The current [original ZIP](https://csdb.dk/getinternalfile.php/280610/Colors%20%5BLethargy%5D.zip) is 422,380 bytes, SHA-256 `085301efa3282fddf8bfb64390ba90f50a7f3831e53f100f009f1cf4e2ee6383`. Its three disk members each contain 174,848 bytes: ordinary 35-track D64 sector data, without appended error bytes. This is the acquired reuploaded pack; equality with the earlier party archive is not assumed.

| Current filename | BAM side label | D64 SHA-256 |
|---|---|---|
| `Colors [Lethargy] 1.d64` | `SIDEA` | `94bde11ed515f6312fbd77efff9f1fe5c2cdbf25587f0eabada566e0430b1ad6` |
| `Colors [Lethargy] 2.d64` | `SIDEB` | `f1b2e7ace21a9492f05860666397790a5b42aa9f22d2083100de8af592783d04` |
| `Colors [Lethargy] 3.d64` | `SIDEC` | `1c1532eb273e01a81c590557f92b7d9305d961d23615e3f43f4c4de325775585` |

Each DOS directory has 13 entries: one closed PRG and 12 directory-art entries with the closed DEL type. All entries point to the **same chain at track 18, sectors 7–10**. There is one distinct DOS payload per side, not a named-file list of the demo's parts.

Each extracted boot PRG is **849 bytes including its two-byte load header**, loading 847 bytes at `$0801..$0B4F`. BASIC line 10 contains **`SYS2064`**, entering **`$0810`**. No separate DOS technical note is present. This says nothing about hidden raw sectors or external author explanations. The ZIP also has no separate source or document member, as recorded by the acquisition lane.

The [boot receipt](../../build/research/colors/binary/boot-proof.json) records every directory entry, raw filename, sector-chain hash, extracted boot hash, and differences among the three boot files. The side 1 **boot PRG** SHA is `6c83458c3ab427c4d3a11abe50ffbfcb6d8922f99da864b4a54cac412f967f3b`; that is distinct from the D64 hash above.

## No initial SFX depack before hardware

The entry begins:

```text
0810  A9 FF       LDA #$FF
0812  85 FC       STA $FC
0814  A2 04       LDX #$04
0816  A9 08       LDA #$08
0818  85 BA       STA $BA
081A  A5 BA       LDA $BA
081C  20 0C ED    JSR $ED0C
```

Only these **six official 6502 instructions** are interpreted offline, separately for each boot. Execution stops before the KERNAL bus call at `$081C`. All value-bearing reads are established by the loaded PRG or those stores. No ROM routine, drive response, VIC read, packed part, or hardware effect is invented. There is therefore no boot-SFX output image to claim from this prefix.

The static listing follows direct calls and branches within the original PRG, retaining external calls as boundaries. It is a control-flow overapproximation, not evidence that every branch occurred. It shows the later command-channel setup, resident installation, PAL/NTSC receiver adjustment, and loader jump; those hardware-dependent paths are not run offline.

## Loader identification: exact Sparkle 3.4 array match

All three original boots match **847 of 849 bytes** of the primary author's loader array in **Sparkle 3.4, tag `v3.4.260405`**, commit `41d6963b8334dd5f0046ff0dfccb29ef7d9ad0fb`. The only differing bytes are configured return-address immediates, not unexplained code changes. [Author loader array](https://github.com/spartaomg/SparkleCPP/blob/41d6963b8334dd5f0046ff0dfccb29ef7d9ad0fb/loader.cpp)

The canonical array SHA-256 is `c3af3c519034fb5fe8dfa4cc7749b8e55922f599de5caf6d6ef3158568ff87d0`. Both that C++ text and the matching assembly source are preserved with URL, commit, size, and hashes under `binary/source/`. They are read as text; no downloaded host program is compiled or run. Matching bytes can persist in later builds, so this identifies the loader implementation rather than the exact host-tool build date.

The differing PRG offsets are **269 and 272**, corresponding to immediates at **`$090C/$090F`**. They push a return address before jumping to the resident loader:

| Side | Pushed return address | Eventual RTS destination |
|---:|---:|---:|
| 1 | `$7FFF` | **`$8000`** |
| 2 | `$0004` | `$0005` |
| 3 | `$BFFF` | `$C000` |

The side-specific values are observed in the originals. They do not establish that starting an arbitrary later side reproduces the normal whole-demo route. The native lane starts the original side 1.

## Resident installation and native checkpoints

The boot prepares an `M-E` command and opens drive command channel 15. Its C64-side copy loop at `$08B8` then installs:

```text
$09B0+X → $0160+X
$0A50+X → $0200+X
X = 0..255
```

The two destination ranges overlap by 96 bytes, and all overlapping source values agree. Their union is exactly **416 bytes, `$0160..$02FF`**, equal to original source `$09B0..$0B4F`. This is host copy arithmetic over original bytes, not execution of the installer. All three side boots contain the same resident bytes, SHA-256 `b09c13f9f60a28aa87cf1b157b4035df325eb60bf6d79fe8f176cf7aa606db48`.

The matching [author assembly](https://github.com/spartaomg/SparkleCPP/blob/41d6963b8334dd5f0046ff0dfccb29ef7d9ad0fb/resources/sl.asm) supplies the resident roles:

| Role | Address |
|---|---:|
| Fallback IRQ | `$0160` |
| Send command | `$017A` |
| Load selected bundle | `$019C` |
| Load fetched bundle; boot enters here | **`$019F`** |
| Set memory configuration | `$0205` |
| Done/music hook | `$0209` |
| Load next | `$021C` |
| Block buffer | `$0300` |
| Destination / bit state | `$02/$03` / `$04` |

The useful clean installation breakpoint is **`$08C7`**, immediately after the copy and before the raster-based PAL/NTSC adjustment. A native capture there can compare all 416 bytes without masking receiver patches. The next natural boot jump is `$0911: JMP $019F`. On side 1, the first configured return is `$8000`; the first-image signature still needs the actual loader/native capture. No Bitfire/Dali directory or decompressor addresses are assumed.

## Reproduce the bounded batch

From the repository root:

```sh
build/research/tower-power/cpu-venv/bin/python research/colors/inspect_boot.py
python3 research/colors/identify_loader.py
```

The first command uses the existing py65 1.2.0 interpreter for only 18 instructions in total. The second performs no CPU execution. To fetch the two pinned primary source files in a fresh artifact directory, use `identify_loader.py --fetch-source`.

Outputs are ignored under `build/research/colors/binary/`: the three boot PRGs and direct-reachable listings, `boot-proof.json`, the 416-byte `resident-reference.bin`, and [loader-identification.json](../../build/research/colors/binary/loader-identification.json). [Extraction/boundary script](../../research/colors/inspect_boot.py), [exact source comparison](../../research/colors/identify_loader.py)

This batch establishes the original boot route and the actual loader. It leaves packed-bundle extraction, first-image byte identity, RGB/field scheduling, analog color interpretation, geometry work, and renderer performance to subsequent evidence. No production renderer or original disk is changed.
