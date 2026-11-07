# The Impossible Thing: 256 glyphs instead of a full pixel canvas

Research date: 7 November 2026. **The Impossible Thing** is the April 2003 Smash Designs/Oxyron 4 KB intro, not the 1997 C64 Second Reality production. The original program's 6,433 decoded bytes and all 29,184 generated glyph-writing bytes match the offline reconstruction. One captured update also matches a literal CPU replay across the complete font/screen plane and renderer state. Its observed image-selection interval is about 58,600 PAL clocks; the bundled 25 fps statement is retained as an author claim.

The [independent affine model](impossible-thing-affine.md) now also derives
all newly written glyph and matrix bytes directly from the original texture,
profile, preset and input phases. **The captured initial preset is static:**
all three phase increments are zero. This establishes one fixed transform,
not moving-angle or other-preset native coverage.

## Original release and attributable claims

The [official Oxyron listing](https://www.oxyron.de/html/demosc.html) dates the release to 21 April 2003 and identifies its Breakpoint 4 KB third place. [Pouët](https://www.pouet.net/prod.php?which=10607) credits AEG with code and Axis with the idea; [CSDb](https://csdb.dk/release/?id=8615) lists both under code. That difference is retained rather than silently reconciled.

The Pouët download leads to the original [scene.org party pack](https://files.scene.org/view/parties/2003/breakpoint03/c64/in4k/c64-4k.zip). Its `c64-4k.d64` is byte-identical to the disk in the linked [CSDb package](https://csdb.dk/getinternalfile.php/57487/4Ks.zip):

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Scene.org party ZIP | 35,726 | `0bb5d307ab10461ea46e3f289c436cf0b59549340bfe3e384936e674b98fd7ca` |
| CSDb ZIP | 34,063 | `159339cb807c238de1bd74e33c02dca7c13550769873ad467a97e69b6f5334cf` |
| Identical original D64 | 174,848 | `8f40a954ef6bdbd28d8e5e9d81c920310169349242714a8611b0b8dabcaf5717` |
| `4K/AEG & AXIS`, extracted PRG | 3,592 | `a79f294f7a506bd489135dbf56515e939d8a14a6b16cafccea38673d09acca8d` |

The target is the first DOS file, starting at **track 19, sector 0**. The adjacent `READ ME` is a 439-byte BASIC program attributed to AEG and Axis. It claims a fullscreen 2×2-pixel rotate/zoom at **25 fps** and claims novelty. Those are original-release statements, not accepted measurements or independently established historical priority. The [acquisition receipt](../../build/research/impossible-thing/acquisition.json) retains both archives, all disk entries, the target's complete sector chain, and the note's decoded BASIC lines.

[AEG's post #81370](https://www.pouet.net/prod.php?which=10607#c81370) attributes the effect to runtime work, ordinary fullscreen character display and a 16×16 texture using the 256 available glyphs. [kb_'s #81849](https://www.pouet.net/prod.php?which=10607#c81849) explains one transformed 4×4-texel patch per texture origin, expanded into an 8×8 glyph at 2×2 sampling; the screen then selects those glyphs. [AEG's #81860](https://www.pouet.net/prod.php?which=10607#c81860) accepts that explanation while disputing the proposed Graham/Chaos lineage. Neither statement supplies a measured cycle count. An earlier three-frame report by Optimus is a viewer observation, not an author result.

These exact posts and account identities were already pinned in [the Second Reality source-boundary note](second-reality-sources.md). The explanation belongs to this 2003 intro and must not be transferred to Second Reality's 1997 effects.

## Bootstrap: three strict boundaries remain visible

The PRG loads at **`$0801`**, ending at `$1606` inclusive. BASIC contains **`SYS2049`**, also `$0801`. The overlapping entry begins:

```text
0801  0B 08 90 06 9E 32 30 34 39 00 A0 00 78 E6 01
0810  B9 93 15 99 40 03 C8 D0 F7 4C 40 03
```

`ANC #$08` always clears carry, so the branch reaches `$080B: LDY #0`. The strict original-instruction run stops at **`$080E: INC $01`**, because the CPU port is not supplied as ordinary file memory. This tiny ANC extension uses the semantics of VICE's 6510 core; every other unsupported opcode is rejected.

The subsequent literal copy would move 256 bytes from `$1593..$1692` to `$0340..$043F`. Only **116 bytes**, through source `$1606`, are established by the file; **140 bytes** are startup RAM. The copied wrapper restores the port, reads `$A2` and `$D012`, and may call KERNAL routines. This path is not executed with invented raster, timer or ROM responses.

The later decoder copy, `$14D9..$15D8 → $00FA..$01F9`, is entirely inside the file. Its original `$0100` code copies another helper block and begins decompression. An isolated run preserves two further stops:

1. After **1,176 completed instructions**, `$013F: INC $0400` reads unknown screen RAM.
2. With only that screen byte explicitly seeded, after **1,278 instructions**, `$07B9: CPY $12` reads unknown caller state.

The continued decode therefore has explicit preconditions: all RAM visible, no IRQ delivery, binary arithmetic, Y=0, SP=`$FF`, `$0400=0`, and **`$12=0`**. Initial A, X and carry are overwritten before affecting decoding. `$12` affects length control and is not claimed to be a harmless value or file-established state.

The screen seed has a narrower independence argument. Every access to `$0400` in the completed run is the same `INC` at `$013F`. Its value never becomes a decoded byte, pointer or length. INC leaves A/carry unchanged; LDX at `$0145` overwrites its N/Z before a condition can consume them. The 90 increments affect only this status byte. It remains an explicit synthetic seed, outside the declared output range.

The conditional decoder executes **184,223 original instructions**, ending at `$0763: STA $01` with A=`$37`. It stops before that port write; the following original code is `CLI / JMP $2000`. Its **6,433 output stores are unique and consecutive in reverse order**, filling `$0FFF..$291F`:

```text
8182a395e4c663a3bf8603e4b6538fd1d5108ba46281e84a580935243e5639f9
```

The [boot receipt](../../build/research/impossible-thing/binary/boot-proof.json) records the strict stops, assumptions, all output events and hashes. `conditional-unpacked.ram` is an analysis image, not an oracle for unowned RAM outside its known mask or a completed cold boot.

The original disk subsequently reached `$0100` and `$2000` naturally. Native `$12` was zero at both SYS and decoder entry, and all **6,433 decoded output bytes match** the hash above. This establishes the selected reconstruction's output identity for that native run. It does not retroactively turn the conditional inputs or unknown wrapper padding into file-established memory. Native `$0400` was `$FF` at decoder entry and `$59` at `$2000`, exactly 90 increments modulo 256; the offline seed remained zero.

## The recovered rendering mechanism

The entry at `$2000` initializes music through `$1000`, installs the music IRQ at `$2033`, then jumps to `$28D7`. `$28D7` calls the large initializer at `$2041`; **`$28DA` is immediately after it returns**, before the first image.

Two isolated RAM-only setup spans can be executed without Color RAM, IRQ, raster or ROM responses: `$205A→$2099` and `$20B2→$21EC`. They stop around the actual I/O-writing loop rather than emulate it. Their outputs support these finite contracts:

| Resource | Layout and role |
|---|---|
| Texture | 256 two-bit texels at `$2755..$2854`: the 16×16 source. |
| Packed sample tables | Four shifted versions of that texture, each duplicated across 512 bytes, at `$3800..$3FFF`. |
| Glyph writer A | `$4000..$78FF`, **256 × 57 = 14,592 bytes**, writing the 2 KB charset at `$E000`. |
| Glyph writer B | `$7900..$B1FF`, another **14,592 bytes**, writing the charset at `$E800`. |
| Screen writer | Forty consecutive copies of a six-byte cell template at `$2606..$26F5`; its outer loop writes 25 rows. |

All **29,184 generated glyph-writer bytes** match a separate reconstruction from the 57-byte template and every literal destination address. The final `INY` in each bank is replaced by `RTS`. This is a preparation check, not execution of every generated renderer path.

For each texture-origin index Y, one glyph routine uses sixteen indexed texture-table reads. Four groups of four samples form four packed multicolor bytes. Each packed byte is stored twice, to adjacent glyph rows: this produces the **2×2 physical sampling**. The generated code advances Y and handles the next of 256 origins. The frame-dependent zero-page pointers select the transformed sample positions; no new glyph code is generated per image.

The screen pass selects the prepared origin glyphs across 40×25 cells. The source at `$227C` writes `$D018`; `$28BD` alternates `$C8/$DA`, generating the hidden charset and its matching screen before the next selection. With the requested VIC bank at `$C000`, these correspond to:

| Selection | Screen | Charset | Hidden work before the next selection |
|---|---|---|---|
| `$D018=$C8` | `$F000` | `$E000` | Generate `$E800`, then write screen `$F400`. |
| `$D018=$DA` | `$F400` | `$E800` | Generate `$E000`, then write screen `$F000`. |

The register setup requests multicolor character mode, blue/light-blue global colors and a local white channel. Those source-level register/address relationships are not an independent VIC pixel oracle. The setup spans also skip the Color RAM loop's `$0600→$0700` sine-page duplication; the prepared analysis image's old `$0700` bytes must not be mistaken for its initialized contents.

The [renderer map](../../build/research/impossible-thing/renderer/renderer-map.json) retains exact generated-bank hashes, the setup instruction traces, the [first glyph's instructions](../../build/research/impossible-thing/renderer/one-generated-glyph.txt) and a direct-successor listing. That listing stops at external/generated code and does not turn stored texture bytes or unmodified placeholder instructions into an observed execution trace. A native `$28DA` capture matches all generated bytes, packed texture tables and initialized address/sine tables, including the separately checked `$0700` duplication. The separate [affine analysis](impossible-thing-affine.md) supplies the coordinate equations and its narrower captured-preset acceptance.

## A useful timing bound, not a measured frame rate

The generated instructions already impose a lower bound for one new charset-plus-screen image:

| Work | Minimum nominal CPU cycles |
|---|---:|
| 256 glyphs: four LDA indirect,Y, twelve ORA indirect,Y, eight absolute stores and INY per glyph; final INY becomes RTS | `256×114 + 4 = 29,188` |
| 1,000 screen cells: TXA, ADC immediate, STA indirect,Y, INY | `1,000×12 = 12,000` |
| Combined minimum | **41,188** |

Two standard PAL frames contain **39,312 cycles**. The minimum above already exceeds that by 1,876, before pointer/transform setup, row overhead, page crossings, VIC stalls or music IRQs. `$28BD` performs two such halves, so its corresponding lower bound is **82,376 cycles**, not 41,188.

This source-derived bound conflicts with a simple interpretation of the bundled 25 fps claim for a complete new charset-and-screen image. It does not turn Optimus's emulator observation into a measurement, specify a stable displayed cadence, or supply a native FPS value. `$227F`, immediately after each `$D018` write, is the relevant same-PC checkpoint for measuring selection intervals. Those writes are not surrounded by a source raster wait, so they are not automatically coherent-frame boundaries.

## Original native cadence and one complete update

The owner cold-autostarted the original D64 in PAL VICE, then captured the natural SYS, wrapper, decoder, main-entry, initialized and image-selection checkpoints. There were no payload/PC patches, snapshot restores or input writes. The owner later stopped the captured session; that closure is not an authored demo exit.

The [passive native checker](../../research/impossible-thing/native_capture.py) passes **13 full RAM/VSF pairs**, or **851,968 exact RAM bytes**, plus transcript/CPU-state correspondence and seven PNG observations. It compares the complete original file, the 116 file-established wrapper bytes, all 256 wrapper-copy bytes against actual native prestate, the full decoder copy and output, and the complete initialized generated-code/table ranges. There are no missing-byte exclusions inside those ranges. [Native receipt](../../build/research/impossible-thing/native-analysis/native-evidence.json)

A peer review found a missing provenance gate in the first checker: it read the prepared analysis image without requiring the independent renderer receipt to pass or checking that image's recorded size/hash. The corrected checker requires both before making native generation/table comparisons. One passive rerun passes with unchanged comparison results; its receipt SHA-256 is **`373c96d201b1e7294c3b2f281eb958750b7068226ef1bf17c9e6b2e096b6dd47`**. The [prior checker and receipt](../../build/research/impossible-thing/native-analysis/before-prepared-image-gate/archive.json) remain archived. The frozen half-image receipt below still pins that archived prior receipt by its original hash, `56d51b742363bbc0eba8c8e38045019c0641a0c156ae83cf4f8d5dbcff1d20d2`; it was not rerun or rewritten. The boot, renderer and half-image proof identities remain unchanged.

Seven consecutive `$227F` stops alternate `$D018=$C8/$DA`. The transcript contains one resume and one next breakpoint between each pair, with no ignored hits. `select-00` selects the initially cleared charset/screen and is not counted as a completed new image. The following five intervals are:

```text
58,601   58,561   58,614   58,603   58,601 PAL clocks
```

The mean is **58,596 clocks**, approximately **2.98 PAL raster periods per selection**. This sample therefore does not show a complete new image selected every two PAL frames. It is a measured selection cadence, not a claim that each screenshot is a coherent frame or that the entire intro has one fixed FPS. The [captured original image](../../build/research/impossible-thing/native-01/select-02.png) remains an observation, without an independent pixel-composition oracle.

For a stronger code contract, [steady_half.py](../../research/impossible-thing/steady_half.py) starts from the actual `select-01` RAM/CPU/port state at `$227F`. It executes the original setup, glyph writer and matrix writer until **the next `$227C`, before `STA $D018`**. The native `select-02` stop is immediately after that store at `$227F`. The skipped instruction is exactly three bytes/four nominal cycles and changes no CPU flags or registers.

This one update performs **14,032 original instructions / 53,188 nominal CPU cycles**, with no port, mapped ROM or I/O response and no IRQ delivery. All **2,048 glyph-byte stores and 1,000 matrix-byte stores** occur exactly once at their expected addresses. The native endpoint matches:

- Every byte of the **8 KB `$E000..$FFFF` font/screen/hidden plane**, including untouched buffers.
- Every byte of **29,184 generated glyph-writing instructions**, **2,336 renderer-code bytes including self-modification**, and **2,048 packed texture-table bytes**.
- All **98 zero-page addresses written by the literal renderer**, selected from its write trace rather than a favorable handpicked subset.
- A, X, Y, SP and flags, with the explicit `$227C/$227F` PC alignment above.

The unfiltered 64 KB comparison retains **22 other differences**: six stack-page bytes and sixteen addresses between `$108A` and `$1429`. They are not masked or promoted to whole-machine equality; this proof does not assign a cause to every byte. The native interval is **58,601 elapsed clocks**, including the final `STA` and the machine's VIC/IRQ effects. The difference from 53,188 is not independently decomposed into stall/music categories. [Half-image receipt and all differences](../../build/research/impossible-thing/steady-analysis/half-proof.json), [all 3,048 literal graphic stores](../../build/research/impossible-thing/steady-analysis/graphic-stores.json)

## The coordinate approximation is now explicit

The [affine follow-up](impossible-thing-affine.md) derives signed Q8 gradients,
the negative one's-complement shortcut, retained carries/borrows and packed
texture-index addition. Every character reuses one set of sixteen local
sample offsets; the matrix supplies only an integer texture origin. This
reduces rendering work but drops each character origin's fractional phase.
Packed-byte addition also permits U overflow to affect V. It is an exact
description of this source's sampler, rather than an ideal continuous affine
transform imposed on its output.

The independent model matches all **2,048 glyph bytes, 1,000 screen bytes,
32 pointer bytes, 40 column operands, 40 scratch bytes** and checked scalar
state without CPU replay. The captured Q8 gradients are `(145,-1,3,145)`,
with divisor 79 and fixed phases `(16,16,0)`. Other presets, moving phases
and negative horizontal-gradient paths remain outside native acceptance.

## Reproduction and limits

```sh
rtk proxy python3 research/impossible-thing/acquire.py --fetch
rtk proxy build/research/tower-power/cpu-venv/bin/python research/impossible-thing/inspect_boot.py
rtk proxy build/research/tower-power/cpu-venv/bin/python research/impossible-thing/map_renderer.py
rtk proxy python3 research/impossible-thing/native_capture.py
rtk proxy build/research/tower-power/cpu-venv/bin/python research/impossible-thing/steady_half.py
rtk proxy python3 research/impossible-thing/affine.py
```

Omit `--fetch` to recheck saved acquisition bytes offline. The native checker requires the retained owner-closed capture set; it never starts an emulator. The existing py65 1.2.0 environment is used only for bounded original CPU instructions; no downloaded host executable is run. No script starts or controls an emulator.

The result establishes an original artifact, precise decode boundaries, native byte identity, generated character-writing machinery, source-derived coordinate formulas, one literal update, an independent fixed-preset output model and a bounded native selection sample. It supports the author's 256-glyph explanation without assigning the mechanism to Second Reality or claiming an independently reconstructed VIC frame, analog behavior, historical priority or all-preset native coverage.
