# Second Reality: original boot, unpacking and synthetic menu inputs

This lane passively checks captures from the original C64 **Second Reality**
side-1 disk in PAL VICE. It establishes loaded-file and unpacked-byte identity,
one explicitly separate native-RAM copy transition, and same-stop RAM/snapshot
equality. Later menu, DOS and note stops are observations unless a specific
contract is listed below. There is no independent full-image renderer oracle.

The closed capture batch passes **19 full-RAM/snapshot pairs**: 1,245,184
compared bytes without address exclusions. It retains four PNG observations,
61 synthetic `$CB` writes, and two explicitly rejected timeout stops.
Session metadata records closure at **2026-11-07 12:14:43 UTC**, exit `-15`.
This is the capture owner's cleanup result, not a claim that the demo exited
on its own.

The disk was started through normal autostart. No program counter, code byte
or geometry was patched, and no snapshot was restored in this capture lane.
The operator did supply **raw scan-result values through monitor writes to
`$CB`**. These synthetic inputs are part of the experiment; they are not a
test of the keyboard matrix, CIA scanning or physical key events.

## Original bytes and natural checkpoints

The [release acquisition](second-reality.md) pins the original disks. The
169-sector boot PRG is 42,890 bytes including its two-byte load address,
SHA-256 `c62598561f3bb6d74e9c399385df6e1dd21890c9fc0abbd952a2a61548a286f5`.
It loads at `$0801`; its BASIC line invokes `SYS 2304`, or `$0900`.

[inspect_boot.py](../../research/second-reality/inspect_boot.py) independently
reconstructs the known-file relocation and RAM-only decompressor. The
[binary receipt](../../build/research/second-reality/binary/boot-proof.json),
SHA-256 `92f272cd978c594467c72a9be0536b29685fbbe0e68e1b18a71d8b9c2718cdfd`,
is an input to this passive checker. Native RAM is a comparison target, not
a seed for those file-derived results.

The following stops were reached by executing the original program. Clocks
and beam coordinates are recorded VICE observations, not general timing
benchmarks; paths include original ROM, drive, I/O and interrupt activity.

| Capture | PC | Clock | Raster/cycle | Checked contract |
|---|---:|---:|---:|---|
| Boot entry | `$0900` | 110,364,473 | 249 / 2 | All 42,888 loaded file bytes at `$0801..$AF88`. |
| Wrapper entry | `$C000` | 110,368,830 | 6 / 12 | 256 file-derived wrapper bytes and 40 text bytes. |
| Loader call | `$C028` | 110,382,845 | 228 / 41 | Five-page copy compared with actual native pre-copy RAM, as qualified below. |
| Loader returned | `$C02B` | 110,807,915 | 111 / 50 | Observed natural return; no complete drive/loader behavioral oracle. |
| Packed SFX entry | `$080D` | 111,518,761 | 163 / 4 | All 41,216 file-derived relocation bytes. |
| Decompressor entry | `$040B` | 112,143,077 | 88 / 53 | All 120 established decompressor bytes and 40,877 established compressed-reader bytes. |
| Unpacked entry | `$9400` | 115,171,910 | 117 / 35 | All 60,152 independently reconstructed output bytes. |

The outer copies are `$0980..$0A7F → $C000..$C0FF` and
`$08C0..$08E7 → $05E0..$0607`. After the original loader returns, the
161-page move is `$0A00..$AAFF → $0801..$A900`. All 41,216 input bytes
for that move are defined by the original file.

The SFX pager's strict file-only execution stops when it would read unknown
RAM at `$0739`. Its unknown final page at `$5F00..$5FFF` is not a compressed
reader input: the established input begins at `$6053`. The separately
labelled RAM-only decompressor proof therefore supplies neither invented
padding nor mocked ROM/drive responses. It reconstructs exactly
`$07E8..$F2DF`, 60,152 bytes, SHA-256
`7599810d51826909c19a4ffd9d2a739b4b45ec1a52ef7a8d36f1ecbe5179f6cd`.
The original native execution matches that entire output at `$9400`.

## The loader copy includes non-file bytes

The earlier outer wrapper copies five pages from `$AB00..$AFFF` to
`$CA00..$CEFF`. The boot file ends at `$AF88`: the final **119 source bytes**
at `$AF89..$AFFF` are outside the file. Treating them as zero, `$FF` or any
other file-derived value would invent evidence.

For this copy only, the checker reads the **captured native pre-state** at
the `$C000` wrapper entry and compares its entire 1,280-byte source against
the destination at `$C028`. The 1,161 file-defined bytes and 119 native-only
padding bytes are separately recorded. This is a state-transition contract
for the captured run, not a claim that the PRG defines all 1,280 bytes or
that the padding is reproducible across boots.

## Synthetic menu and DOS input

The menu was observed at `$9767`, clock **124,281,759**, raster 262/cycle 21.
The monitor then wrote `$3B` to `$CB`, whose prior value was `$40`, without
executing an instruction between the before/after captures.

The checker requires both of these facts:

- Comparing **all 65,536 physical RAM bytes** finds exactly one difference:
  `$CB: $40 → $3B`.
- The recorded CPU registers and **complete `MAINCPU` snapshot payload**
  remain identical, including PC and clock.

The program then naturally reaches its DOS entry at `$C000`, clock
124,281,784. Later DOS commands likewise use explicitly recorded `$CB`
writes. The receipt retains each command, transcript line and most recent
observed stop; it accepts no unclassified direct RAM write, register edit,
`goto` or snapshot restore. It does not call a synthetic scan result a
physical key press or claim that the entire machine state is unchanged.

The recorded first `READ INFO1SDS` attempt is retained with its invalid-command
result. After navigating into the demo directory, the original parser reaches
the embedded note and later accepts `SECOND.EXE`. The earlier failure was a
directory-context attempt, not evidence of a parser defect. These command
observations do not enlarge the byte-check contracts above.

Menu before/after captures deliberately share PC and clock. They are paired
with snapshots by their **explicit capture names**, not by a PC/clock key
that could silently replace one of the two states.

The [disk-map note](second-reality-disk-map.md) independently recovers the
embedded author text. Its authorship and design statements are separate
from this native boot/input proof; reaching the note does not explain the
demo's renderer or establish that every visual effect is computed live.

## Rejected intended-loader observations

The names of two later files reflect intended breakpoints, not where execution
actually stopped. Both followed a timed-out monitor observation and remain
in the receipt as **rejected timeout observations**:

| Capture stem | Intended target | Actual PC / clock | Beam evidence |
|---|---:|---|---|
| `first-load-call` | `$CF00` | `$C404` / 440,589,240 | Monitor reports 0/0; snapshot VIC reports 311/0. |
| `first-load-ready` | `$CE0E` | `$C409` / 747,576,649 | Both report 0/1, but the intended target was not reached. |

Their full raw RAM still matches the same-stop snapshot RAM, and their CPU
snapshots match the recorded CPU observations. Neither is accepted as a
successful loader checkpoint or a timing witness. The first beam discrepancy
is retained without normalization or an invented explanation. All accepted
exec-stop captures continue to require exact monitor/snapshot beam agreement.
This batch therefore proves **no custom-loader handoff after `SECOND.EXE`**.

## Receipt, capture observations and limits

[native_capture.py](../../research/second-reality/native_capture.py) reads
the existing monitor transcript, raw RAM, snapshots and PNGs. It reuses the
existing pure capture-context and physical-RAM readers, pins their hashes,
and checks each recorded CPU/beam stop against its snapshot. Every complete
raw capture is compared with all 65,536 physical RAM bytes from its same-stop
VICE `C64MEM` module, without address exclusions.

The checker validates PNG integrity and records screenshot identity and
dimensions. Screenshots are original-program output observations; they are
not compared against an independent pixel model. A late VIC register read
is not treated as the mode of the whole preceding display.

The authoritative result is
[native-evidence.json](../../build/research/second-reality/native-analysis/native-evidence.json).
Its final `status: complete` and `pass: true` require a **closed session**,
all required byte checkpoints, no pending capture pairs, and exact checked
comparisons. While the operator is still capturing, `--allow-open-session`
can emit an explicit `provisional` result with `pass: null`; that is not a
completed native proof. The transcript, session, snapshot, RAM, PNG and
reference hashes are retained in the receipt.

This checker starts no emulator, process, interpreter or input action.
There is no claim here of physical VIC behavior, keyboard hardware,
complete SID sound, loader timing portability, effect frame rate or a
runtime/prepared-data split for the later demo parts.
