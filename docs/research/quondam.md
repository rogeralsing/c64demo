# Quondam Tunneling: original-program map for native inspection

Research date: 7 November 2026. This deepens [the frontier follow-up](frontier-followup.md) using the same original PRG and previously depacked bytes, then checks them against a separately owned original-program PAL VICE session. The analysis tools control no emulator or process and perform no new CPU interpretation or download. The previous 36 finite helper cases are reused rather than rerun. Native code/assets, register effects, sampled IRQ timing, and two output images are now confirmed; a complete display reconstruction remains open.

The author identifies this as his PAL C64 tunnel contribution to Fjälldata, released 31 January 2026. [Original release/download page](https://www.linusakesson.net/scene/quondam-tunneling/index.php), [author's separate explanation video page](https://www.linusakesson.net/scene/quondam-tunneling/explained.php). The latter supplies no textual algorithm here; its inaccessible-caption status is not retried in this pass.

## Exact original and normal control flow

The copied original is `build/research/quondam/quondam-tunneling.prg`: **33,675 bytes**, SHA-256 **`e86e4bcf40e859f4ec3fcc83a86f8f0c172b6efa0a38d8dc199a85717fddc17c`**. It is byte-identical to the author download preserved in the earlier pass. The diagnostic unpacked RAM has SHA-256 `8d1b7ea523dc2fbcb7c9ddc9b335cd451f87e0659b4e380b52334c350998e3db`; this is a host snapshot hash, not an expectation that a native machine's entire RAM has the same startup/stack contents.

| Address | Role | Native inspection use |
| --- | --- | --- |
| `$080D` | BASIC `SYS2061`; also the unpacked program's entry | Ambiguous as a first breakpoint: it is reached before and after unpacking. |
| `$01BD` | Relocated original SFX final `JMP $080D` | Optional precise depack handoff. The same instruction's **stored template** is at `$8B65` in the packed file; `$8B65` is not its final runtime PC. |
| `$09FF` | Intro's natural `JMP $9000` | Confirms leaving the earlier sprite presentation. |
| **`$9000`** | Tunnel initialization, before its asset preparation | Recommended first tunnel breakpoint. Reach naturally; do not set the PC here. |
| `$902C` | Asset/state preparation | Copies and initializes data; contains expected self-modification. |
| `$90C9` | Sprite/palette/Color RAM setup | Writes `$08` to all 1,024 Color RAM entries. |
| `$9029` | Final jump after tunnel IRQ installation | Initialization complete, before foreground wait at `$9595`; display may not yet have scanned a tunnel frame. |
| `$9129` | Main video-frame IRQ | Advances motion states, selects initial memory/palette state, schedules later IRQs. |
| `$93E9` | Foreground wait for viewport-preparation flag | Part of the overlay/scroller path, not a polygon renderer. |
| `$9595` | Foreground wait for raster 228 | Followed by setup of the bottom sprite band. |

The unpacked `$080D` entry starts `A9 7F 8D 0D DC 78`, and `$9000` starts `A9 0B 8D 11 D0 20 2C 90`. These are useful phase signatures. Once initialized, some code and screen data are intentionally modified; comparing the whole later image with the pre-initialization dump would incorrectly flag normal behavior.

## Actual graphics mode and memory selection

The tunnel IRQ writes `$D011` values formed as `$18 | yscroll`: DEN and the 25-row control bit are set, while bitmap and extended-color mode bits are clear. It writes `$D016` as `$10` plus an even fine-X value: multicolor enabled, 38-column selection. This is **multicolor text**, with sprites layered over it, rather than a conventional multicolor bitmap.

All 18 entries of the `$D018` table have high nibble `$C`, so the selected screen lies at offset `$3000` within the current 16 KB VIC bank. The table's low bits choose the charset. The corresponding `$DD02` table values are `$3C..$3F`. Initialization writes the CIA2 `$DD00` output latch to zero, and the code changes bank selection through the **direction register**, using output-zero versus input/pull-up behavior on its low pins. Native inspection should record both CIA2 registers/pins; a raw RAM byte at `$DD00` is not the port state.

Expected bank mapping under that original latch/pin arrangement:

| `$DD02` | Expected VIC bank | Screen | Sprite pointer table |
| --- | --- | --- | --- |
| `$3C` | `$0000` | `$3000` | `$33F8` |
| `$3D` | `$4000` | `$7000` | `$73F8` |
| `$3E` | `$8000` | `$B000` | `$B3F8` |
| `$3F` | `$C000` | `$F000` | `$F3F8` |

`build/research/quondam/release-map.json` expands all 18 actual table pairs into bank, screen, pointer, and charset addresses. For example, `$D018=$C2/$DD02=$3E` selects expected charset `$8800`; `$CA/$3C` selects `$2800`. No listed combination selects a VIC character-ROM window in banks 0 or 2.

The only initialization copy affecting these listed charset assets is the literal 2 KB `$7800→$2800` copy. The map applies that copy to derive **per-charset expected hashes** for a later native comparison. It does not pretend to simulate initialization, SID state, I/O, or all self-modification. Other copies of `$3800` into `$7800/$B800/$F800` are asset mirroring; these destinations should not be mislabeled the `$D018=$C*` screen bases.

## Two uses of the same raster-controlled store window

The original helper `$939B..$93E8` increments zero-page counter `$11` and prepares the following window. Its previously executed 36 finite cases are preserved in `quondam-window-proof.json`.

| Prepared `$11` phase | Immediate/data source | Store window at `$9325..$932C` |
| --- | --- | --- |
| Even | `$966E` memory-selection table and `$9680` direction table | `LDA #bankDirection; STA $DD02; STX $D018` |
| Odd, bit 1 clear | A=12, X=0 | `LDA #12; STA $D023; STX $D022` |
| Odd, bit 1 set | A=0, X=12 | `LDA #0; STA $D023; STX $D022` |

X is loaded by the patched `LDX #...` at `$931E`. Both variants retain the same LDA-immediate, STA-absolute, and STX-absolute instruction sizes and nominal cycles. The helper patches values and destination operands, not a generic alpha or texture shader.

The main IRQ initializes this phase from the vertical-motion table: `$11 = table[$9796 + frameIndex] >> 3`. Subsequent calls advance it for successive raster bands. **It is a vertical band/preparation phase, not simply an animation-frame parity.** Calling the palette swap “two animation frames” from these addresses alone would conflate different state variables.

Separate code increments `$12` by `$20` each video-frame IRQ; its high two bits participate in choosing one of four 64-character code groups. Horizontal and vertical positions come from stored tables at `$9896` and `$9796`, with fine/coarse components feeding scroll bits and screen entries. These are observable consumers of prepared glyph data and motion tables. They do not establish live general 3D projection or the original asset-generation algorithm.

## Exact pixel interpretation, including the limitation on bitplane claims

The viewport-preparation IRQ writes `$D021=14`. With the initialized Color RAM value `$08`, selector `11` takes foreground color 0, black. The two palette orientations from the original helper therefore mean:

| Packed selector | Phase 1: `$D022=0,$D023=12` | Phase 3: `$D022=12,$D023=0` |
| --- | --- | --- |
| `00` | 14, viewport background | 14, viewport background |
| `01` | 0, black | 12, gray |
| `10` | 12, gray | 0, black |
| `11` | 0, black | 0, black |

The interpretation changes which exclusive selector gets gray. A single global XOR bit or two arbitrary independent one-bit pictures is **not** the full truth table: code `11` stays black in both views. Sprite overlay, border/background changes, and screen fetch selection are separate consumers.

`research/quondam/map_release.py` enumerates all 256 byte values under both actual palette states and inventories the bytes in all 18 selected charset assets after the required copy. Its `pixel-interpretation.json` records 147,456 logical asset samples: code counts are `00=60,098`, `01=25,493`, `10=25,600`, `11=36,265`. Those counts cover all glyphs in the assets, **not just glyphs proven fetched in a native frame**. Actual asset bytes containing all four selectors are identified in the map as concrete witnesses. These results describe character-pixel interpretation; they do not reconstruct the raster image.

## Raster and overlay breakpoints

| Address | Role | What to record |
| --- | --- | --- |
| `$9247` | Early sprite-band IRQ | Top/background changes and sprite-pointer work. |
| `$92B0` | Viewport preparation | Background 14; viewport flag and initial line scheduling. |
| `$9300` | First raster-band IRQ | Timing adjustment from CIA1 timer, `$D011` write, patched window, next-window preparation. |
| **`$932D`** | Immediately after both patched stores | Best causal witness of which register pair was just changed. Record `$11`, `$931E..$932C`, raster/cycle, I/O `$D011/$D016/$D018/$D021..23/$DD00/$DD02`. |
| `$935C` | Alternate raster-band IRQ | Changes `$D011` low scroll bits and schedules the next first handler. |
| `$93ED` | First foreground read after the viewport flag | Candidate completed-viewport capture before its next scan; see caveat below. |
| `$961C` | Finite sprite shift worker | Foreground text/overlay updates; not tunnel 3D geometry. |

The two band handlers add four to their next-raster counter. That is a code-derived **requested IRQ schedule**, not a measured cycle deadline or a complete VIC internal row-counter explanation. The first handler uses CIA1 timer-derived self-modified timing code; a host CPU without those timer/VIC interactions cannot validate this display mechanism.

The foreground path multiplexes sprites, updates pointers in the four screen pointer tables, and shifts sprite data. It can affect apparent holes, masks, text, and the bottom band. A single text-mode decoder that ignores sprites is not a whole-screen reference. Likewise, the fact that the code updates 40 sequential screen entries in one selected bank does not alone prove how the VIC repeats/fetches rows; that requires the raster schedule's hardware consequences.

## Native sequence and capture interpretation

1. Boot the **unchanged original PRG** in PAL VICE and stop naturally at `$9000`. Save raw RAM and source signature bytes. This separates the intro from the tunnel and avoids guessing later entry state.
2. Stop at `$9029` to confirm preparation and the selected asset hashes. Read charset memory using an explicit RAM view, including `$D000/$D800` assets, and inspect Color RAM using I/O view. Initialization's source state is `$01=$35`, which leaves I/O visible to CPU-space reads.
3. Resume through at least one `$9129` IRQ and capture successive `$932D` witnesses of both window kinds. Use the counter and patched destinations to classify them. Mask unused readback bits (`$D018` bit 0, palette high nibbles) rather than demanding raw read bytes equal immediate constants.
4. Take a normal screenshot after the tunnel has scanned. Pausing at `$932D` captures an in-progress frame and is suitable for register evidence, not a complete-frame comparison. The **first** `$93ED` reached after its flag wait is expected just after the raster-47 preparation and before its raster-56 foreground wait; it is a candidate point where the prior viewport is complete. Record actual raster/cycle before relying on that expectation. A persistent breakpoint there will also hit its tight wait repeatedly and must not be counted as one hit per frame.

At that early-next-frame capture, the viewport pixels can belong to the preceding scan while RAM/phase state already describes the next scan. Comparing them to one contemporaneous RAM/IO snapshot would be unsound. Preserve the causal register witnesses and the previous/current distinction. A full native reconstruction would additionally need VIC row/fetch state and sprite scheduling; that is not supplied by the static asset map.

## Reproducible outputs and current limits

Run `rtk proxy python3 research/quondam/map_release.py` from the repository root. It reads the existing exact artifacts, copies them under `build/research/quondam/` with hash checks, and produces `release-map.json`, `pixel-interpretation.json`, and bounded pre-initialization code excerpts. It runs no CPU, effect, emulator, or network request.

The SFX and finite-helper receipts remain explicitly offline. The completed native session below used `$9595` as its post-initialization stop, rather than the earlier candidate `$9029`. The source-derived map remains useful for interpreting that evidence; a breakpoint suggestion is not itself a capture.

## Native confirmation from the original PRG

The root-owned `native-01` session autostarted the unchanged original PRG in PAL VICE and reached `$9000` naturally, after the intro. Its monitor transcript records warp disabled at that entry before the captures. No payload or PC replacement was used. The owned session was closed after recording the evidence.

`research/quondam/native_capture.py` reads only those existing files and produces **`build/research/quondam/native-01/native-evidence.json`**. It controls no process. The receipt hashes the original PRG, reference map, helper receipt, monitor log, raw RAM, screenshots, and script.

### Original code and prepared assets match

At `$9000`, native RAM matches all declared pre-initialization regions, without exclusions: the 499-byte intro interval and the 1,686-byte tunnel-code/table interval, which includes the separately listed 78-byte preparation helper. The overlapping helper comparison is not another distinct code region.

After initialization at `$9595`, **all 18 expected 2 KB charset hashes match exactly**: 36,864 bytes, including the assets in underlying RAM at `$D000/$D800`. The only required charset preparation in the reference is the identified `$7800→$2800` copy. All 18 also match in the later elapsed-32 and elapsed-96 RAM captures. This confirms the predicted asset preparation and their unchanged sampled contents; it is not a write-watch proof that no byte ever changes between samples.

### Three causal store-window witnesses

The monitor stopped immediately after both stores at `$932D`, with explicit I/O reads and separate raw-RAM captures:

| Band counter `$11` | Raster / cycle | Window kind | Native memory selection | Native globals `$D021,$D022,$D023` |
| ---: | --- | --- | --- | --- |
| 7 | 62 / 1 | Palette swap | `$D018=$C5` readback → `$C4`; `$DD02=$3D`; charset `$5000` | `(14,12,0)` |
| 8 | 70 / 1 | Bank/charset selection | `$D018=$C7` readback → `$C6`; `$DD02=$3D`; charset `$5800` | `(14,12,0)` |
| 9 | 78 / 1 | Palette swap | `$D018=$C7` readback → `$C6`; `$DD02=$3D`; charset `$5800` | `(14,0,12)` |

Each captured window's instruction bytes, patched immediate values, and post-store A/X registers agree with the previously interpreted original helper. Native `$DD00=$C2` gives physical low pins `10`, selecting VIC bank `$4000`; that agrees with the original direction-register scheme. `$D018` bit 0 is normalized away, and only the low nibbles of palette-register readbacks are compared.

All three have `$D011=$1D` and `$D016=$D4` readback: bitmap/extended-color bits clear, multicolor enabled, and the 38-column control bit clear. This confirms the mode **at the sampled viewport windows**, rather than applying a later lower-band register snapshot to the entire frame.

The motion state bytes `$12..$14` remain **`$20,$01,$01` in all three captures**, while `$11` advances 7, 8, 9. This directly separates vertical-band palette/memory interpretation from animation-frame parity. The stops are each **504 cycles apart at the same PC and raster cycle**, exactly eight PAL raster lines. It does not follow that the underlying row/fetch behavior or every other interrupt deadline has been fully reconstructed.

The global colors are directly sampled. Selector `11`'s black foreground remains based on the identified Color RAM `$08` initialization path; these I/O reads did not directly sample Color RAM. The parser records that distinction instead of treating the RAM charset bytes at `$D800` as Color RAM.

### Alternate handler and sampled frame-clock cadence

The separate `$935C` capture occurs at raster 81, cycle 14, with stopwatch 13,489,133. It is 202 cycles after the preceding `$932D` stop at raster 78, cycle 1. Because the PCs are different, **202 cycles is not a four-line handler period**. Its `$D011=$1D` read is before that handler executes its later scroll-bit store; it does not measure the store's resulting value.

Five sampled `$9129` entries occur at raster 251, with entry cycles 18, 18, 21, 18, and 20. Successive raw clock deltas are:

| Raw cycles | Observed entry-position difference | PAL-frame intervals |
| ---: | ---: | ---: |
| 19,656 | 0 | 1 |
| 19,659 | +3 | 1 |
| 589,677 | −3 | 30 |
| 1,257,986 | +2 | 64 |

Removing the separately measured entry-position differences leaves exact multiples of 19,656 cycles. These sampled IRQ events align with the PAL frame clock. This is not evidence that all glyph data changes every frame, that every pixel is freshly synthesized at 50 Hz, or that live 3D geometry is being computed.

### Native output observations

[`tunnel-native-032.png`](../../build/research/quondam/native-01/tunnel-native-032.png) shows a right-biased checker tunnel with a green sprite craft and upper text. [`tunnel-native-096.png`](../../build/research/quondam/native-01/tunnel-native-096.png) shows a more centered tunnel, the craft, and different text coverage. These are distinct original-program output images, not host previews.

Their filename numbers mean **elapsed PAL intervals from the first sampled main IRQ**: 32 and 96, respectively the 33rd and 97th IRQ hits if that reference is counted as hit 1. They are not absolute demo-frame numbers. The capture-time I/O at raster 251 describes the lower-band state; it cannot serve as the contemporaneous viewport state for every pixel already present in the PNG.

Run `rtk proxy python3 research/quondam/native_capture.py` to reproduce the structured checks from the closed session. All checks pass. A complete image-to-bank reconstruction, exact VIC row/fetch schedule, asset-generator projection, and full display timing proof remain outside this bounded capture analysis.
