# Second Reality CA: generated point plotting in character memory

Research date: 7 November 2026. Original file **CA** implements a moving field of points using generated, self-modifying plotting routines and three multicolor character sets. The recovered kernel has **31 instances × 32 points**, with cached addresses for clearing the previous positions. It does not contain an edge/span polygon filler. The observed native output resembles a waving dot grid; an author-specific effect name remains unassigned.

The independent preparation check matches **all 35,456 generated code bytes** before the first draw. A separate literal CPU replay of one steady draw/update interval matches the native generated code/cache, screen/character RAM, position arrays, styles, phase counters and final CPU registers. These are RAM contracts, not a complete-frame or physical-VIC pixel oracle.

![Original native CA output observation](../../build/research/second-reality/native-02/ca-iteration-b.png)

This is the original program's captured output. Its image is not independently reconstructed here, and a logical iteration need not align with a displayed frame.

## Original bytes and the actual handoff

The inputs come from [the pinned original disk chains](second-reality-disk-map.md):

| File | Header / payload | Complete PRG SHA-256 |
|---|---|---|
| CA | `$6000`, 6,144 bytes | `b795d4bd191a6dd6a153fa827a3c3e0175fb720c3266a38ae09e441df13b7554` |
| BD | `$C000`, 2,304 bytes | `99fae6d7d0b108be8f14a0ce067d96bc3aa661620d34b6493f7a1a76a4e7a49a` |
| BC, narrow transition context | `$8600`, 14,656 bytes | `25f2ec9af774fc49eba9ce0d1048722c73640ed23043fb23f45ce6d2aad581dc` |

**`$6000` is CA's staging address, not its observed execution entry.** Its absolute internal targets are in `$C000` space. The earlier attempt to wait for execution at `$6000` timed out; no `$6000`-labelled capture was made and no PC was forced there.

The transition matters because BD occupies `$C000` first. BC's reachable `$9400 → $9700` path later loads CB, then `$9A00..$9AC4` copies its `$8000..$8FFF` bytes to RAM underneath `$D000..$DFFF` in raster-paced chunks and enters BD at `$C000`. BD eventually executes **`JMP $6D00` at `$C8AB`**. CA's gate installs a temporary IRQ and enters its relocator at `$6D12`, which copies:

- `$6000..$6BFF → $C000..$CBFF`: 3,072 code/table bytes.
- `$6C00..$6CFF → $CF00..$CFFF`: one loader page.
- `$7000..$77FF → $9000..$97FF`: 2,048 stored motion-table bytes.

It then executes **`JMP $C000` at `$6D5F`**. The native gate, relocator and entry captures follow this route, and every byte in all three destination ranges matches the original CA source. The CA-entry guard is `A9 00 8D 20 D0 8D 21 D0 8D 11 D0 8D 15 D0 20 90 C3`; it distinguishes CA from the earlier BD entry.

## Display storage and address lookup

CA sets `$D011=$1B` and `$D016=$18`: multicolor **character** display, with bitmap mode clear. It selects CIA2 port A `$80`; the prepared/steady captures have direction `$3F`, so both low bank pins are outputs selecting VIC bank **`$C000`**. The screen matrix is **`$E000`**.

The IRQ at `$C0B9` changes `$D018` between **`$8A/$8C/$8E`**, selecting character sets **`$E800/$F000/$F800`** while retaining the same screen. Its raster targets divide the 192-line drawing area into three character-set regions. The matrix reuses a 256-character atlas across three groups of eight rows, making the character memory act as a writable point canvas. This source-level layout does not establish every midline fetch or compose an independent frame.

Initialization clears `$E000..$FFFF`, constructs character codes in columns 4–35, copies the matrix to `$E000`, and sets Color RAM `$09` in columns 5–35 of 24 rows. With `$D022=$0F`, `$D023=$0B`, and the local color's low bits selecting white, the active multicolor points use gray/light-gray/white on black. Column 4 remains black and hides the left clipping destination; the final screen row is outside the colored viewport.

The prepared 512-byte address lookup gives the plotting code its clipping and storage mapping:

- `$0400..$04FF` supplies the byte-column contribution. Inputs `$40..$BF` select the 128 logical horizontal positions; other inputs select the hidden left character.
- `$0500..$05FF` supplies the page. Inputs `$20..$DF` select the 192 drawing rows at `$E800..$FFFF`; other inputs select hidden page `$E400`.
- The row's low three bits complete the address, and the low two horizontal bits choose one of four prepared two-bit pixel masks.

The plotting instructions use **whole-byte `STA`**, rather than OR-ing a pixel into an existing byte. Shared byte positions and drawing order therefore matter. This is not a general point renderer with an independently established blending rule.

## What is prepared, and what runs each iteration

CA stores 32 sixteen-byte coordinate profiles, 32 sixty-four-byte motion-table quarters, address/pointer tables, pixel masks and short instruction templates. The exact finite preparation performs two substantial expansions:

| Preparation | Result | Independent contract |
|---|---|---|
| `$C500 → $C900 → RTS` | 512 address-lookup bytes, style initialization, and 32 mirrored 128-byte motion tables at `$B000..$BFFF`. | All 4,096 expanded table bytes, 512 lookup bytes and 256 style bytes match the native prepared capture. |
| `$C200..$C38A` | 32 routines at `$2000..$AA7F`, each 1,108 bytes. | Every one of the 35,456 generated bytes matches first `$C840`, before runtime cache modification. |

Each generated routine comprises a **99-byte clear prefix**, **16 copies of a 63-byte two-point template**, and one `RTS`. The stored `$C800/$C820` pointer tables equal `$2000 + 1108*i` for all 32 entries. Instance zero is not drawn by `$C440`; the runtime uses indices **1–31**.

The unused routine zero has an unusual seed: the generator initially points at `$C800`, its pointer-table bytes. Subsequent routines use the coordinate-profile pointers. The checker preserves this literal behavior and still compares all 32 routines; it does not repair the unused seed into an assumed profile.

The 32 clear stores remember the previous target addresses. Each new two-point calculation patches the corresponding clear operands for the next iteration. The template combines current positions, prepared profile offsets, lookup bytes and mask values, carrying the original 6502 arithmetic flags through the calculation. Its output is **32 point stores per instance**, not an edge list or filled span. The first unused clear targets point to hidden `$E400`.

At `$C440`, the program selects each instance's generated routine, loads its style and current position from `$0B00`, `$0A00` and `$0A20`, and calls it. Thus a complete draw performs **992 cached clears and 992 point stores**.

The following update rotates/shifts style state and calculates the next positions. It averages pairs of prepared 128-entry table samples, adds the literal per-instance base offsets, and advances phase indices. The global phase increments are **`+5,+4,+6,+3`**; the local sample phases progress across instances by **`+4,+3,+4,+5`**, masked to seven bits. This is live position calculation using prepared samples and generated plotting code. It is not evidence of a perspective matrix, projected edges, polygon visibility or filling.

The authored sequence has 32 introduction iterations at `$C840`, a 64-iteration steady section at `$C85F`, and 32 exit iterations at `$C885`. Those are source loop counts, not frame counts. The temporary gates and later exit/loader work are outside the steady RAM-only proof.

## Independent CPU and native contracts

The [checker](../../research/second-reality/inspect_ca.py) uses the existing py65 1.2.0 environment. Its memory wrapper rejects unknown reads, CPU-port accesses, mapped ROM reads and hardware writes. No IRQ, raster, SID, drive or KERNAL response is fabricated.

For preparation, it starts at original call/jump sites **`$C085`** and **`$C0B3`**, using only file-derived relocated bytes. Original `JSR/RTS` instructions create their own stack contents; a synthetic return target is not supplied. The table preparation executes 30,608 instructions / 100,484 nominal CPU cycles, and code generation 218,293 instructions / 734,541 cycles. These are bounded routines, not a complete initialization cost.

The clean native preparation capture is **`$C840`, clock 297,765,535**, raster 261/raw cycle 4. It supplies the exact comparison before the first clear-address self-modification. The separate native continuation checker owns restore/input/capture lineage; this lane requires the owner-closed session and independently checks each selected full RAM file against its matching VSF.

The steady proof starts from captured **iteration A**, executes the original `$C85F` draw/update code without interrupts, and stops on its next visit to `$C85F`. It is explicitly conditional on that known native RAM/CPU/port prestate:

- **20,492 instructions / 62,094 nominal CPU cycles**, with zero hardware, ROM or unknown accesses.
- All 35,456 generated code/cache bytes and all 8,192 bytes of `$E000..$FFFF` match native iteration B.
- All 65 next-position bytes, 35 style/state bytes and five phase/instance counters match.
- Final PC, A, X, Y, SP and flags all match.
- The full 65,536-byte comparison retains **36 differences** elsewhere: 11 in the stack page and 25 at `$0C12..$1387`. They are not masked or promoted to whole-machine equality, and this pass does not assign a cause to each byte.

Native consecutive iteration clocks are **72,230**, **71,699**, and **72,943**. They include the original machine's interrupts and VIC behavior. The 62,094-cycle RAM-only total excludes those effects; subtracting the values does not independently classify each source of elapsed time. The stops occur at different raster positions, so no coherent-frame duration, refresh rate or physical-hardware timing claim follows.

## Reproduction and retained limits

```sh
rtk proxy build/research/tower-power/cpu-venv/bin/python \
  research/second-reality/inspect_ca.py
```

The [receipt](../../build/research/second-reality/ca-analysis/ca-proof.json) pins original files, the closed session, eight RAM/VSF pairs, all comparisons, instruction counts and every complete-RAM mismatch. It also retains [all 1,984 graphic stores](../../build/research/second-reality/ca-analysis/iteration-a-to-b-plot-stores.json), the RAM-only expected endpoint and file-derived generated image. The [curated instruction listing](../../build/research/second-reality/ca-analysis/ca-reachable-instructions.txt) represents the file-derived prepared state, so template operands reflect generation; adjacent data is not disassembled as a renderer.

Peer review found that the checker printed CPU equality but did not include it in its final pass gate. All recorded CPU comparisons were already exact. The gate now includes them and fails after retaining a mismatching receipt. One rerun preserved all byte/cycle/difference results. The [original receipt](../../build/research/second-reality/ca-analysis/ca-proof.before-cpu-gate-094ef718514d.json) (`094ef718…`) and [original script](../../build/research/second-reality/ca-analysis/inspect_ca.before-cpu-gate-fc314ea6.py) (`fc314ea6…`) remain readable for frozen downstream dependencies.

Script SHA-256: `933b2ee896cebbb47a7d34aa67b826469d5ed4c7fe8664c8be380490d7d0b42c`. Receipt SHA-256: **`36af2e866fc3421b0fe9652a0503866a4bc08b715e6f4c46a4587453f6c4f57c`**.

The result establishes this original point-field architecture, preparation and one draw/update interval. It does not establish analog output, an independent pixel oracle, whole-demo behavior, an author-assigned phase name, historical priority or a transferable polygon-fill optimization.
