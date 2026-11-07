# Nine: the character digit and the sprite handoff

The released code has a concrete **eight sprites plus one character digit** path. It does not decide that switch by testing every pair of projected digits for overlap. The authored main script changes a control bit; the drawing routine then publishes a different packet for the IRQ. This complements the [earlier binary map](nine-binary.md), which identified several preparations without connecting the complete character consumer.

The [author's explanation](https://www.linusakesson.net/scene/nine/explanation.php) attributes the early switch to fixed sprite priority as the rotating ring becomes flatter: even before nine digits occupy the same raster band, assigning sprites with the required front/back order becomes awkward. The released code supports that representation change. The exact geometry threshold below is **not** claimed to be an automatic overlap solution.

## Pinned inputs and reproducible CPU checks

The original PRG SHA-256 is `a257fa0436bc0d97fbeaa906c55489786a26ee6a9213aa3fd0d8e21f9612d839`. This pass reuses the already proved nine-block relocation, without repeating unpacking or inventing the initializer's raster and character-ROM inputs. The 64 KB relocated fixture is SHA-256 `82b6eb9f4b175512ce3f8073d187b7e29f3140a673631bca0658b1b4bfde0a7e`.

```sh
rtk proxy build/research/tower-power/cpu-venv/bin/python \
  research/nine/character_path.py
```

The [checker](../../research/nine/character_path.py) produces `build/research/nine/character-analysis/character-proof.json`. It runs original official-opcode CPU slices only. Its existing memory mapper records mapped I/O writes separately from underlying RAM; any attempted hardware/ROM read stops execution instead of supplying a fake raster value.

The focused checks pass:

- Nine independent conversions from each original 63-byte sprite image to its prepared 72-byte character image.
- Seventy-two original-code character placements: all nine digit images and eight scroll phases, all 16 literal colors, old/new stamp overlap and separated positions, and screen-edge rows/columns. Every physical RAM byte and every literal mapped-I/O write equals an independent placement reference.
- Three sprite handoffs: ascending, reversed and tied Y positions with nontrivial input permutations. The result matches a stable host sort, and all physical RAM matches the independently predicted handoff state.
- Four post-music IRQ selector cases establish priority and idle behavior without executing any raster wait or hardware-dependent section.

These tests address consumers and packet ownership not covered by the previous font-copy and generator checks. They introduce no production seams. Their explicit input fixtures are not asserted to be naturally occurring complete demo frames. A separate natural native case, described below, now validates the authored switch and the first character stamp against actual captured RAM and Color RAM.

## The font actually consumed by the character path

The earlier `$8245` copy to `$E883+192n` is not the font selected by this path. The character font is already a separate relocated block at **`$4178..$43FF`**, 648 bytes: nine digits × nine glyphs × eight bytes.

For digit index `n`, the code's `$A6E9+n` table gives the first character code:

```text
2f 38 41 4a 53 5c 65 6e 77
```

Thus `font_address = $4000 + 8*first_code = $4178 + 72*n`. The subsequent eight codes form a row-major 3×3 character block. Independently taking the 21×3 bytes at `$7800+64n`, appending three blank pixel rows, and transposing the byte lanes into nine eight-row glyphs reproduces **all 648 prepared font bytes exactly**. This establishes image correspondence, rather than inferring it from an address ending in a likely font range.

The normal initializer clears glyph zero at `$4000..$4007`; erasing a screen stamp with character code zero therefore restores a blank background. Its separate character-ROM copy to `$4400..$46FF` supplies other characters and must remain distinct from both custom digit representations.

## Main-side character stamp

`$9051` prepares nine digit colors, image pointers and computed positions. At `$92C0`, `($22 & $20) != 0` chooses the sorted nine-sprite path; zero jumps to `$931A`, the character path.

The current digit arrays are indexed by digit slot, not hardware sprite number:

| Zero-page range | Packet data |
| --- | --- |
| `$07..$0F` | Nine colors |
| `$10..$18` | Nine sprite-image pointers, `$E0..$E8` in the ordinary set |
| `$27..$2F` | Nine X low bytes |
| `$47..$4F` | Nine Y values |
| `$50..$58` | Nine X high bits |

The character path waits at `$931A` until all three publication flags `$CD/$CE/$CF` are zero. It then writes the **first eight** positions, colors and image pointers directly to hardware sprite registers and `$4BF8..$4BFF`. The ninth slot becomes the character digit; it is not always the same digit image as the ring turns.

Its placement arithmetic is concrete:

```text
vertical_offset = (Y[8] - 47) & 255       ; $61
fine_x          = Xlow[8] & 7            ; $62
column          = ((Xlow[8] - 24) & 255) >> 3   ; $46
screen          = $4800 + 40*(vertical_offset >> 3) + column
digit_index     = image_pointer[8] - $E0
first_code      = RAM[$A6E9 + digit_index]
```

The exact CPU arithmetic is bytewise; the placement tests use valid screen coordinates so those intended integer expressions have no ambiguous wrap interpretation. The code clears the previous stamp's nine screen cells using the retained `$24/$25` address. It writes `first_code..first_code+8` at offsets `0,1,2,40,41,42,80,81,82` from the new screen address, then remembers that address for next time.

It converts the screen high byte with XOR `$90`, mapping `$48xx..$4Bxx` to `$D8xx..$DBxx`, and writes the ninth digit's color to the same nine Color RAM cells. Old color cells need not be cleared because their character codes were erased. Overlapping old/new stamps are cleared first and stamped second; the oracle checks that order through final RAM contents. Finally **`INC $CE` at `$949F`** publishes the packet and `$94A1` returns.

The CPU-only fixtures measure 635–906 nominal cycles from the selector through publication, depending mainly on the row-address loop. This is not native raster timing, a whole update cost, or evidence of any total frame-rate improvement.

## IRQ consumers and flag lifecycle

`$CD/$CE/$CF` are frame-data handshakes, not themselves the authored scene clock. The top-level `$99BF` IRQ calls music and then tests them in this priority order:

| Flag | Main producer | IRQ consumer | Release of handoff |
| --- | --- | --- | --- |
| `$CD` | Crunched/ghostbyte path, publishes at `$904E` | `$9A09`, installs `$9B00` | `LSR $CD` at `$9C7C` |
| `$CE` | Eight sprites + character stamp, publishes at `$949F` | `$9A4A`, installs `$9CBA` | `LSR $CE` at `$9CF4` |
| `$CF` | Sorted nine-sprite packet, publishes at `$9317` | `$9A96`, installs `$9D00` | `LSR $CF` at `$9DB0` |

The producer waits for the needed previous packet to be consumed. The usual flag value is one, and the matching `LSR` clears it; treating these as independent queued scene counters would miss that ownership contract.

For the character packet, `$9A4A` disables multicolor and X expansion, sets `$D018=$20`, and uses `$61&7` for Y fine scroll and `$62|8` for X fine scroll. With the original bank-$4000 display contract, this selects **screen `$4800` and font `$4000`**, exactly the main-side stamp and prepared font identified above. It installs `$9CBA` at a raster derived from that same Y phase. The later IRQ changes display/scroll state for the lower region and releases `$CE`. These are actual code consumers; this offline pass does not claim their precise bus-write phases or a native image match.

For the sprite packet, `$92C9` stably sorts the index list `$77..$7F` by current Y, copies five nine-element arrays into `$80..$AC`, records a special digit index in `$68`, and publishes `$CF`. `$9D00` consumes that sorted list while recycling hardware sprites. `$9D89` can replace the remembered special digit's hardware pointer with blank sprite `$E9` if the currently installed pointer still matches it. The source's pointer comparison is established; assigning a particular visible seam to it still requires a native trace.

## Authored switch versus geometry condition

The main script starts control byte `$22` at `$3D`. Its relevant representation changes are:

| Original instruction group | Resulting `$22` | Resulting producer |
| --- | --- | --- |
| `$8569`: XOR `$10` | `$2D` | Continues nine-sprite path; reverses `$3F` control towards zero |
| `$8574`: XOR `$01` | `$2C` | Continues nine-sprite path |
| **`$857F`: XOR `$20`, stored at `$8583`** | **`$0C`** | **Character path** on subsequent updates |
| `$85FD`: XOR `$04` | `$03` | Crunched/ghostbyte producer |
| `$86E7`: XOR `$0C` | `$0F` | Character producer again |
| **`$8707`: XOR `$20`, stored at `$870B`** | **`$2D`** | **Nine-sprite producer** again |
| `$8712`: XOR `$10` | `$3D` | Reverses `$3F` towards 127 |

Other control-bit changes occur between these rows; the receipt preserves the complete decoded main-script XOR sequence, rather than pretending the table is every assignment. The `$8569` change is followed by `$57` calls of the frame-update helper, then the `$8574` change and `$1C` more update calls before the first character switch. These are authored update counts, **not measured native PAL frames or wall-clock durations**.

This yields a testable numerical prediction: `$3F` has been held at 127, then decreases through 87+28 update calls to 12 at the switch. The first subsequent updater should make it 11. The native capture confirms both values; the representation choice still comes from the authored control bit, not a new overlap test on those positions.

There is a separate geometry-dependent threshold in the sprite IRQ: `$9D05` compares `$1D` against `$14`. Below 20 it uses the ordinary multiplexer; at or above 20 it jumps to `$9E00`, which selects the other bank and the specialized side-border register schedule. That comparison does **not** activate the character digit. Likewise, the coordinate special case at `$91A3/$91A9` concerns exact prepared-position evaluation; it is not a general overlap-based choice of sprite versus characters.

## Natural native checkpoints

The root-owned native lane can reach these without PC, code or geometry edits:

| PC | Capture meaning |
| --- | --- |
| `$8585` | First instruction after the script clears control bit `$20` |
| `$931A` | First character-path entry; may still be waiting on an older published packet |
| `$9322` | Previous `$CD/$CE/$CF` packets have all been consumed |
| **`$93F8`** | **Before erasing the old 3×3 screen stamp**; sprite-register packet has already been written |
| `$9439` | Computed new screen address is in `$40/$41`, before selecting/writing the font codes |
| `$9473` | New nine character codes have been written, before retaining the address and writing Color RAM |
| **`$949F`** | **After all stamp/Color RAM writes, before publishing `$CE`** |
| `$94A1` | After publication, before the original return |
| `$9A4A` / `$9CBA` | Character-packet IRQ setup and the later display split |

The narrowest natural stamp comparison is `$93F8→$949F`: capture physical RAM plus the VIC snapshot's Color RAM at both ends, and derive the new placement from the before state's `$61/$46/$18/$0F`. Retain the first `$931A` snapshot for complete packet context. The separately owned [native lane](nine-native.md) records original boot/initialization evidence; the following receipt owns this specific stamp comparison.

## Natural native switch and first stamp: passed

The root-owned PAL VICE run reached these original checkpoints without changing the PC, geometry or code. Warp was disabled at the first `$931A`; the stamp measurements occur afterwards.

| PC | Physical raster / zero-based cycle | Native clock | Relevant state |
| --- | --- | ---: | --- |
| `$857F`, before authored flag change | 173 / 5 | 97,150,856 | `$22=$2C`, `$3F=12` |
| `$8585`, after flag change | 173 / 13 | 97,150,864 | `$22=$0C`, `$3F=12` |
| `$931A`, first character-path entry | 207 / 14 | 97,153,007 | `$22=$0C`, `$3F=11` |
| `$93F8`, before stamp erase | 167 / 1 | 97,170,130 | Previous stamp `$4800`; A=`$E5`, X=`$44`, Y=`$FF`, SP=`$F0` |
| `$949F`, after glyph/color stores | 172 / 59 | 97,170,503 | New stamp `$4866`; A=`$0E`, X=`$06`, Y=`$52`, SP=`$F0` |

The eight-cycle `$857F→$8585` interval changes only physical RAM `$22`, exactly as the original `LDA/EOR/STA` sequence requires. The first packet confirms the independently predicted `$3F=11`. The later `$931A→$93F8` interval includes waiting for an older sprite packet and IRQ activity, so it is **not** treated as an isolated CPU/RAM transition.

For the actual stamp, the before state has `$61=22`, `$46=22`, image pointer `$18=$E6`, and color `$0F=$0E`. The host formula predicts row 2, column 22, screen address **`$4866`**, and image index 6. Its nine screen stores contain **`$65..$6D`** at `$4866..$4868`, `$488E..$4890`, `$48B6..$48B8`. The corresponding Color RAM cells at `$D866..$D868`, `$D88E..$D890`, `$D8B6..$D8B8` contain color 14.

The predicted final state matches **every one of 65,536 physical RAM bytes and all 1,024 Color RAM entries**, with no masked ranges. Only nine screen bytes and scratch `$24,$40,$41` change in physical RAM; the high-byte partner `$25` already has the correct `$48`. The previous stamp's nine cells are already blank in this first natural case, so their continued blank state alone is not evidence of an erase write; the nonblank and overlapping CPU fixtures above independently exercise erasure. Character font `$4178..$43FF` still matches the original prepared font, and glyph zero is actually blank.

The capture interval is **373 observed emulated cycles**, with unchanged SP and `$CE` still zero at the after boundary. This is one real stamp interval, not an average, an instruction-only count, or a whole-frame timing claim. Publication follows at the next original `INC $CE`.

Each of the five raw RAM captures matches its same-stop VSF's version-checked physical RAM extraction over all 64 KB. Contexts also agree on PC, memory bank, raster and cycle. The checker reuses the native lane's read-only transcript/snapshot helpers, hashes those inputs, and freezes the consumed transcript prefix so later captures can append to the main monitor log without altering this proof's input.

```sh
rtk proxy python3 research/nine/character_path.py \
  --capture build/research/nine/native-01
```

This mode performs **no CPU model execution and no emulator/process operation**. Its passing receipt is `build/research/nine/character-analysis/character-native-proof.json`. It establishes an original native authored switch and correct first character stamp. It does not establish a full pixel reconstruction, every later digit assignment, section bus timing or physical-machine behavior.
