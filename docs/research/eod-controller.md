# Edge of Disgrace: original content boot and controller

Research date: 8 November 2026. This note maps the original side-1a/1b
emergency boot and its custom-load/controller API. A fresh original side-1a
boot reaches that controller and two later payloads through its real loader.
All 14 saved RAM/VSF pairs agree; complete payloads 51/52 match at their
natural load returns. This is code/input custody and bounded call evidence,
not complete shader-pixel or animation acceptance.

The [file extractor](eod-files.md) owns the original disk/candidate identities.
The earlier [disk-0 boot](eod-native-boot.md) is a different entry path. The
[Gouraud shader's arithmetic and line behavior](eod-shader.md) remain a
separate analysis consuming this witness.

## A content side can bootstrap itself

Each content side's DOS program decodes to 800 bytes at `$0900..$0C1F`.
The side-1a/1b versions differ in only one byte: `$094B` is `$B1/$B2`.
The entry blanks the display and SID, then calls `$0957` while KERNAL and
the normal drive command interface remain available.

That routine addresses drive 8, command channel 15, sends `I`, and sends a
41-byte command from `$0983..$09AB`. It starts with `M-E`, execute address
`$020D`, eight track/sector bytes, and a short program that executes from
the drive's command buffer. It does not first require disk 0.

The drive program copies the four read-job track/sector pairs into zero
page `$06..$0D`. It issues job codes `$80` in descending job order and waits
for successful status `$01` before advancing:

| Job | Original disk sector | Drive buffer |
|---:|---:|---:|
| 0 | T18/S18 | `$0300..$03FF` |
| 1 | T18/S15 | `$0400..$04FF` |
| 2 | T18/S12 | `$0500..$05FF` |
| 3 | T18/S9 | `$0600..$06FF` |

It then jumps to **drive** `$04E9`. These are declared placements of original
sectors, not a drive CPU simulation or a claim that all four pages remain
unchanged. The loader later replaces its completed initialization region
with the index and also self-modifies transfer code.

On the C64, the original copy loop installs 536 file-known loader bytes from
`$0A00..$0C17` into `$0200..$0417`. Other copy-loop reads extend beyond the
800-byte decoded file; they are not invented as zeros or accepted as loaded
controller content. The controller is transferred later by index 0.

## `$0200`: select a side or load a zero-based index

The original C64 API begins `PHA; JSR $03FF; PLA; BPL ...`. Thus the command
A is restored after transmission before the branch tests its sign. The
sender establishes its own carry/sentinel; incoming carry is not an API
precondition.

- **Negative A:** the drive masks off bit 7 and saves the remaining value.
  It reads BAM sector T18/S0 into `$0700`, then repeats until byte `$07FF`
  matches. Original `$B1/$B2` requests expect markers `$31/$32` respectively.
  It acknowledges the side, reads T18/S6 into the same `$0700` buffer, and
  copies the 256-byte index into **drive `$05AE..$06AD`**.
- **A=0..127:** the drive doubles A and reads a track/sector pair at
  `$05AE+2*A` / `$05AF+2*A`. This is a zero-based index, with valid bounds
  supplied by that disk's original index. The C64 path receives the stream
  and decompresses it; A is not an arbitrary load address or scene number.

The negative-command return at C64 `$094F` witnesses the handshake, **not
completion of the drive's index copy**: the latter read/copy can still be
pending. The subsequent index-0 transaction waits for the real service.
Natural `$0440` with the exact original controller is a stronger complete
transfer witness.

The compressed data header supplies `$D1` initial bit state and `$D2/$D3`
destination through `$0227..$023A`; the loader's end path returns at `$0323`.
A/X/Y and flags are scratch. Successful positive loads return A=0/C=1 under
the original binary-mode condition; the API does not execute CLD locally.
The bootstrap establishes `$01=$35` and disables interrupts, while later
controller IRQs save A/X/Y and `$01`. Do not invent these initial conditions
for arbitrary later callers or equate C64 carry with drive-service timing.

Earlier preliminary drive addresses `$048C/$04AE` were incorrect: relocating
the sector placement does not relocate its encoded absolute operands. The
byte-guarded receiver is **drive `$058C`**, index base **`$05AE`**. The final
producer uses those original literal addresses.

## Controller entries and the late payload pair

Side-1a index 0 supplies 872 bytes at `$0440..$07A7`. Its entry table is:

```asm
$0440: JMP $04B3   ; initial content-side setup
$0443: JMP $04CA   ; later continuation entry
```

The initial path installs the IRQ and loads indexes 1, 2, 3 and 4. It later
patches the music call into the IRQ. Scene operations are explicit JSRs
interleaved with loads and waits; index order alone is not semantic scene
identification.

The source-bound sequence relevant to candidates 51/52 is:

| Original PC | Operation |
|---:|---|
| `$06F1/$06F3` | A=`$32` / JSR `$0200`: load index 50 |
| `$06F6` | JSR `$8800` |
| `$06F9/$06FB` | A=`$33` / JSR `$0200`: load index 51 |
| `$06FE` | JSR `$8803` |
| `$0701` | JSR `$0F00` |
| `$0704/$0706` | A=`$34` / JSR `$0200`: load index 52 |
| `$0709/$070B` | A=`$35` / JSR `$0200`: load index 53 |
| `$070E` onward | JSR `$0F03`, `$0F06`, `$0F09`, `$0F0C`, `$0F0F` |

Index 51 occupies `$0800..$30DC`; index 52 occupies `$30DD..$65FF`. The
first `$0F00` call happens **before** index 52 is requested. A runtime
binding must therefore observe these real load returns and subsequent
dispatch, rather than assume the concatenated files are an initialized
standalone program.

## Native acceptance and continuation

The frozen case is `build/research/eod/native-02`, **36 files / 3,820,648
bytes**, canonical listing SHA-256
`03b3a0faabf52736b3bb2cc176f4f98a12d4443f5a3d5395d636a91caae9b24c`.
It contains 14 full RAM/VSF pairs and one cosmetic PNG. The owned process
was explicitly closed/reaped, exit −15. The original side-1a D64 is both
`-autostart` and drive 8; no manual RAM/PC/register patch or restore occurs.

The unchanged frozen wire auditor receives only an exact in-memory
replacement of its manual-load startup assertion with the original-D64
autostart contract. All original events remain. The 101 ordinary commands
complete in order. A 30.058-second wait notice on sequence 26 later completes
on the same process/connection; no interrupt, resend or restart occurs.
The ordered command list is pinned in addition to the wire/manifest hashes.

For all 14 pairs, the producer compares 65,536 physical RAM bytes, CPU
registers/flags, clock and VIC beam. CPU-port reads use serialized
`dir_read/data_read`, distinct from output latch; driven bits and zero unused
state are guarded. The earlier official VICE schema proof is reused with
its original source/archive pins.

| Capture | PC | Clock | Complete original payload match |
|---|---:|---:|---:|
| `sys` | `$080D` | 6,976,276 | 874 loaded bytes |
| `unpacked` | `$0900` | 7,091,534 | 800 decoded boot bytes |
| `controller` | `$0440` | 10,194,824 | 872 index-0 bytes |
| `rejected-candidate` | `$546A` | 215,921,314 | Earlier overlay; rejected |
| `before51` | `$06FB` | 398,251,001 | Observed A=`$33` before original JSR |
| `after51` | `$06FE` | 401,192,343 | **10,461 bytes `$0800..$30DC`** |
| `after52` | `$0709` | 418,848,691 | **13,603 bytes `$30DD..$65FF`** |

All **26,610 original bytes** across those five payload comparisons match,
without exclusion masks. The installed 536-byte C64 loader matches apart
from only its documented self-modified transfer operands at `$0364`,
`$03EB`, `$03F8`, `$03FA/$03FB` (actual differences are listed in the receipt).
These operands are not claimed to remain at their initial values.

The rejected earlier `$546A` begins `71 10` (`ADC ($10),Y`), while the real
loaded shader entry begins `20 15 55` (`JSR $5515`). Reusing the numeric PC
was insufficient. Its complete RAM/VSF pair and wait notice remain retained.

## Guarded shader and one-line boundaries

With the original late payloads bound, the real dispatcher has state 10 at
`$1767`. Its `$17D8: JSR $546A` continues at `$17DB`. Natural entry is
captured at clock 468122687, and its return at 468169304. A later stable
entry also guards ramp flag `$5514=1`. Saved stack words independently
confirm the frame continuation and the one observed line's `$5E62` return.

| Window | Begin → end clock | Elapsed machine cycles |
|---|---:|---:|
| First accepted `$546A→$17DB` | 468122687 → 468169304 | 46,617 |
| Stable `$546A→$17DB` | 469164461 → 469222679 | 58,218 |
| Thin `$1856→$5E62` | 469182934 → 469183449 | 515 |
| Stable begin → next `$546A` begin | 469164461 → 469262715 | 98,254 |

The thin-line input is X=`32→40`, Y=`72→60`, packed XOR mask `$04`, state 10
and ramp flag 1. The entry/return stack changes by two bytes as expected.
The separate shader scalar must calculate its writes from source and the
entry state; this producer does not infer them from completed pixels.

Navigation warp was explicitly enabled. Before the accepted body/line
windows, warp was disabled, queried as off, and Speed queried as 100; both
queries were repeated at the final endpoint. The producer checks actual
responses, not only launch options.

**The 98,254-cycle begin-to-begin sample is not the 58,218-cycle shader
body.** Its remaining 40,036 cycles are not individually attributed. The
original common IRQ path performs reconstruction and marker clearing before
the next dispatcher call:

```asm
$174B: DEC $01
$174D: JSR $1A73   ; LDX #0 / JMP generated $D800
$1750: JSR $1A78   ; LDA #0 / JMP generated $C400
$1753: INC $01
$1755: JSR $1768   ; state 10 reaches $17D8 / shader
```

The `$11A1` generator uses the `$125C` template `EOR $7800; STA $7000`,
carrying the accumulator between marker bytes, and emits corresponding
zero stores for the marker plane. Source bounds crop the emitted cells.
Thus common XOR-prefix reconstruction exists outside the tracing-line
shader. The residual also includes caller/IRQ work, waits and VIC effects;
the four timestamps do not supply an exclusive cost partition.

HCL's no-filler prose must not be promoted to absence of any common
reconstruction pass. The actual code distinguishes shade-boundary tracing
from the shared prefix reconstruction. No delivered FPS, full cadence
distribution or steady-state speedup is inferred from one begin-to-begin
interval.

## Replay and restart

```sh
rtk proxy python3 research/eod/controller.py --output build/research/eod/controller-analysis/fresh-replay
```

Choose a fresh directory. Final acceptance is
`controller-analysis/accepted-01/controller-proof.json`, **39,172 bytes**,
SHA-256 `256828263de51e95cb374db0c177e146e948752f61cc6651ff5371fe956532f6`.
The producer is **22,076 bytes**, SHA-256
`033bafb6ac6e97283175ac6713af0eef60cb7991b653ee1c98c47a1a4afa83c9`.
A fresh self-replay and independent root replay reproduce all three outputs
exactly, 61,784 bytes. `controller-analysis/root-replay-check.json` records
the latter (950 bytes, SHA-256
`ad3911fec3bdf5d89291272383b904cf6fd74ca50b4136e4cec1131a951c22bc`).
Static peer review found no material issue in the source map, case custody
or bounded frame/line interpretation.

The latest closed endpoint is `native-02/next-frame.vsf`, PC `$546A`,
clock 469262715. It is an observed next entry, not an after-publication
checkpoint. The previous process/monitor handle is closed; further native
work requires a new owner/case and an explicit continuation contract.

No product renderer, alternate boot injection, CPU interpreter, downloaded
host entrypoint, build or new native execution is part of passive replay.
No complete image, whole-demo state, FPS or physical-hardware claim follows
from a code/payload match.
