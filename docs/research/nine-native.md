# Nine: original-boot native byte comparison

This analysis compares saved native RAM and full VICE snapshots with the byte
contracts established in [the binary analysis](nine-binary.md). The original
PRG must follow its own SFX, hardware-dependent wrapper and initializer. The
analysis script starts no emulator, interprets no CPU instructions and supplies
no raster, CIA or ROM values to make the program proceed.

The released PRG is 14,356 bytes, SHA-256
`a257fa0436bc0d97fbeaa906c55489786a26ee6a9213aa3fd0d8e21f9612d839`.
The earlier [binary proof](../../build/research/nine/binary/binary-proof.json)
is pinned as SHA-256
`2a68b45ae9a6c4e0de061a7233b46a131420070f5d6fe586157bd945f10558cc`.
The source assets and independently constructed reference outputs are inputs
to the native check, not replacements loaded into the running demo.

## Capture before the wrapper changes the unpacked payload

The BASIC start `SYS 2061` reaches `$080d` twice, for different bodies:

| Phase | First bytes at `$080d` |
|---|---|
| Original packed SFX | `a0 1d ba bd 3a 3f 9d fc 00 ca d0 f7` |
| Untouched unpacked wrapper | `a9 7f 8d 0d dc a2 02 b5 00 9d 00 fe` |

The final SFX handoff is the original **`JMP $080d` at `$01b3`**, bytes
`4c 0d 08`. A natural stop there is before the wrapper saves zero page,
reconfigures hardware or relocates anything. Another route is to install
an execution breakpoint at `$080d` before normal boot and ignore its first hit;
the verified SFX path's next `$080d` is the unpacked body. In either case,
check the unpacked signature before interpreting the capture.

The entire **29,884-byte `$0801..$7cbc` payload** is compared, without any
excluded addresses, against the independently unpacked reference. Its expected
SHA-256 is
`ef45ab609f139bb03befcf20ab3253e2bb30debbc4cbd789350607c1c9d54004`.
A later full-RAM dump cannot substitute for this checkpoint: the wrapper's
relocation destinations overlap parts of the original unpacked storage.

## Natural effect entry and generator boundary

The wrapper eventually executes its own `JSR $8000`. The guarded entry bytes
are **`20 17 80 20 77 82 a9 bf`**. At that stop, all nine relocation blocks
are compared directly with the source-derived destinations: 29,528 bytes total.
There is no need to assume the rest of RAM resembles the offline startup
fixture.

The clean post-generator checkpoint is **`$8146`**, beginning
`a2 00 8a 9d 00 5c`. It is immediately after the final generated-cell patch,
before the following display-buffer clears. Maskable IRQs remain disabled;
the generated raster body has not been entered. The analysis compares:

- All three 673-byte families at `$3000/$3400/$3800`: 2,019 bytes in total,
  including every cell and trailing `RTS`.
- All nine relocation blocks against the generated reference, including the
  three template immediates changed by the generator.
- The literal 256-byte `$ae52..$af51` table copied to `$4700..$47ff`.
- Explicit initializer zero-page state `$02..$ff`, including the final
  generator pointer `$40/$41=$3aa0` and the table at `$77..$7f`.

The normal caller later finishes initialization and returns to `$8003`, before
music initialization and enabling IRQs. That is a separate useful
checkpoint for the pointer tables and image-copy setup. At that stop, the
analyzer also checks all nine blocks with exactly six source-derived updates:

| Address | Expected update | Original cause |
|---|---|---|
| `$823b` | `$e8→$f0` | Eight-page clear advances its destination operand |
| `$824a/b` | `$7800→$7a40` | Nine source-image strides of 64 bytes |
| `$824d/e` | `$e883→$ef43` | Nine destination strides of 192 bytes |
| `$79ff` | `$00→$ff` | Literal idle-byte initialization at `$8273` |

These are expected values, not excluded addresses. The checks additionally
cover all 16 prepared pointer slots and the complete `$e800..$efff` result:
eight cleared pages containing the nine 63-byte image copies. This checkpoint
must not be mistaken for the earlier generator boundary or an already
displayed frame.

## Character ROM and physical RAM are separate inputs

Before generation, the original initializer changes `$01` to `$33`, copies
character ROM `$d800..$daff` into `$4400..$46ff`, then restores `$01=$35`.
Reading a raw RAM dump at `$d800` would read the underlying RAM, not those ROM
bytes. A zero-filled placeholder is also not an authentic reference.

The native capture also saves the actual 768-byte source through the monitor's
explicit `rom` bank at `$d800..$daff`. That short ROM dump is classified separately
from 64 KB RAM dumps, with its bank, range, context and hash retained. It can
validate the destination even when the VSF omits ROM modules.
The pinned C64SC implementation `c64memsc.c:1296..1301` maps that monitor bank's
`$d000..$dfff` reads directly to `mem_chargen_rom[address & $0fff]`; the
[`rom`-bank source receipt](../../build/research/nine/native-analysis/rom-bank-source.json)
preserves its exact archive/member hashes. This is a character-ROM source,
not CPU-visible Color RAM or underlying RAM.

When a captured VSF includes ROMs, VICE 3.10's `C64ROM` module v0.0 stores
KERNAL 8 KB, BASIC 8 KB, then CHARGEN 4 KB. The copied source is therefore payload
slice `[0x4800:0x4b00]`. Those 768 bytes are compared directly with the native
destination, with the module and CHARGEN hashes retained. If the snapshot
omits ROMs, the receipt explicitly marks that extra copy check unverified;
it does not replace it with RAM or silently count it as a pass.

For every 64 KB native RAM capture, the complete data is also compared with the
same-stop VSF's physical RAM. The pinned `C64MEM` v0.1 schema is four prefix
bytes, 65,536 RAM bytes and fifteen suffix bytes, so RAM is payload
`[4:65540]` of 65,555 bytes. This cross-check has **no excluded addresses**.
It establishes agreement between the two native capture formats, separately
from agreement with any offline byte oracle.

## Reproduction and interpretation

The [native analyzer](../../research/nine/native_capture.py) classifies captures
by the recorded natural PC and signature, and requires RAM/VSF files at the
same PC and CPU clock. Run only after the separately owned native session
has been closed:

```sh
rtk proxy python3 research/nine/native_capture.py \
  --capture build/research/nine/native-01 \
  --output build/research/nine/native-analysis
```

It pins the original PRG, prior proof, reference RAM, parser, transcript and
each captured artifact. Every mismatch is retained with its address and
expected/actual byte; unexplained differences are not masked. Later display
captures may legitimately contain self-modified code and changing assets.
Those are separately labelled observations, with full differences against
the original destinations, rather than being passed as initializer matches.

The [character-consumer note](nine-character-path.md) covers a separate analysis.
Its natural `$92c0/$9439/$949f/$9a46/$9cf4` checkpoints concern dispatch, screen writes and
IRQ consumption, not the untouched SFX payload. Native screenshots are output
observations unless an independent full-image oracle is also supplied. A
matching initializer or a screenshot alone does not prove the ghostbyte
raster timing, every scene's chronology, or a physical VIC result.

The nine 63-byte copies into `$e883+192n` are not that character font. The
character path consumes the separately relocated 9×72-byte font at
`$4178..$43ff`, including its blank bottom rows. The two representations
are not interchangeable image oracles.

## Completed original-program result

The `native-01` session booted the unchanged original PRG in VICE's
PAL 8565 model and reached every checkpoint naturally. No payload or PC patch
was used. The session was closed after the final captures.

**All four established initialization checkpoints pass exactly.**

| Natural checkpoint | CPU clock | Raster / zero-based cycle | Established comparison |
|---|---:|---|---|
| Second `$080d` | 5,748,441 | 141 / 6 | All 29,884 unpacked payload bytes exact |
| `$8000` | 6,313,261 | 58 / 31 | All 29,528 bytes of nine relocation blocks exact |
| `$8146` | 6,362,882 | 222 / 8 | All 2,019 generated bytes, nine blocks, explicit ZP/table state and ROM copy exact |
| `$8003` | 6,435,835 | 132 / 7 | Nine blocks with the six literal updates above, 16 pointer slots, and the full 2 KB clear/image-copy result exact |

The authentic 768-byte ROM source has SHA-256
`6f9fbed3390dcec2ac055cef262f10518101df20e9596347e5f2705ad8b8f406`.
It matches `$4400..$46ff` at both the generator and completed-initializer
checkpoints. The full reference-fixture state is not being inferred from
that copy; only the explicitly checked regions have an offline byte oracle.

The final general receipt contains **21 full native RAM/VSF pairs**. Every
one matches all 65,536 physical RAM bytes: **1,376,256 byte comparisons**,
without excluded addresses. Its four initialization records are byte-contract
acceptance checks. Its seventeen later records remain separately labelled observations of changing
state, including detector/music return, the character switch/stamp,
two visible character states and the Device call/restore/visible states.
Their changing code/data bytes are retained against the original relocation
baseline, not silently passed as initializer equality.

The [general native receipt](../../build/research/nine/native-analysis/native-evidence.json)
has SHA-256
`1c10770128e14e0ea5fa8bf29dda9a00da4825a1234b58298da719fabdc41034`.
The separate character and Device checks give narrower causal
interpretations of selected later captures:

- [Character path and natural stamp proof](nine-character-path.md), with
  [its native receipt](../../build/research/nine/character-analysis/character-native-proof.json).
- [Device execution and alignment-family tracing](nine-device.md), with
  [its first-family receipt](../../build/research/nine/device-analysis/device-proof.json);
  its causal oracle is not duplicated by the general byte checker.

Three saved output observations are available:
[character state A](../../build/research/nine/native-01/character-visible-a.png),
[character state B](../../build/research/nine/native-01/character-visible-b.png)
and [Device state](../../build/research/nine/native-01/device-visible.png).
Each is a 384×272 original-program screenshot with its same-stop full snapshot
and RAM capture, not a host recreation. The display buffer can retain pixels
from a scan preceding that live state. These bind the captures to visible
output; the general analyzer does not supply a whole-image pixel oracle.

This upgrades the earlier isolated CPU/byte findings to a normal original
boot through the real wrapper and initialization in the captured VIC model.
The general receipt does not prove every scene's timing or a physical VIC
result; those limits remain separate from its exact-byte successes.
