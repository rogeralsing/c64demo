# Second Reality: snapshot continuation through configuration and part loading

This is an explicit **continuation of the original native-01 demo-entry
snapshot**, not another cold-boot proof. The earlier
[boot/SFX proof](second-reality-native.md) remains frozen. A new PAL VICE
session restored that saved state at `$8000`, then executed the original
configuration handler and custom loader without code or PC patches.

The closed batch passes **20 full-RAM/snapshot pairs**: 1,310,720 compared
bytes, without address exclusions. It retains ten PNG observations, seven
synthetic inputs and three explicit restore branches. All seven original-file
payload comparisons and the separately qualified AA helper-copy transition
are exact. Session metadata records closure at **2026-11-07 12:39:46 UTC**,
VICE cleanup exit `-15`; this is owner cleanup, not a natural demo exit.

[native_parts.py](../../research/second-reality/native_parts.py) is a passive
checker: it starts no emulator, process, interpreter or input action. Its
[receipt](../../build/research/second-reality/native-parts-analysis/native-parts-evidence.json)
is authoritative only after the session closes and its independent payload
evidence has been attached. A provisional receipt is not a completed proof.
The saved receipt is now `status: complete`, `pass: true`; native-01 was
reused without rerunning or rewriting its proof.

## Restore lineage and input scope

The checker pins native-01's immutable receipt, SHA-256
`33c3b6c18acdc407d2f56337ecc4a279d78932cab05b8950bdbabea555821be9`.
That receipt identifies the original `demo-entry.vsf` and its hash. Native-02
must begin with an `undump` naming that file. The first observed CPU
state after the restore must equal the source snapshot's CPU state:
`PC=$8000`, clock **125,924,831**. The reused capture/snapshot helpers are
also checked against the frozen parent receipt's hashes.

Two additional branches are explicitly allowed from the earlier native-02
`ca-return.vsf` and then `ca-entry.vsf`, in that order. Each source must
already have been captured in this session; its hash, restore command and
first subsequent CPU observation are retained and checked. These are visible
snapshot continuations, not uninterrupted execution, and clocks are not
treated as monotonic across a restore. The final branch captures prepared
code before drawing changes cached operands; the earlier iteration captures
are retained as their own branch.

The operator supplied seven synthetic raw scan-result writes at the original
`$8207` handler: `$02,$40`, repeated three times, then `$01`. The monitor
transcript and every input's most recent observed stop are retained. No
hardware keyboard or CIA-keyboard scan proof is inferred from these writes.

The original handler changes options `$50..$52` from **`0,0,0`** to
**`3,0,0`**, selecting SID while retaining the other two settings. These
options were changed by executing the handler, not by monitor writes to the
option bytes. All physical RAM differences between the two configuration
captures are retained; the checker does not pretend that only `$50` changed
while instructions, interrupts and display updates ran.

| Configuration capture | PC | Clock | Raster/cycle | `$50..$52` |
|---|---:|---:|---:|---|
| Default | `$8207` | 126,286,961 | 266 / 59 | `00 00 00` |
| SID selected | `$8207` | 126,444,212 | 266 / 62 | `03 00 00` |

## Actual loader entry witnesses

Unlike native-01's two rejected timeout observations, these are real
`$CF00` execution stops. The original loader is entered with the following
literal register values. The filename is formed here only from the observed
ASCII `X,Y`; the meaning of `A` is not generalized across calls.

| Capture | `X,Y` filename | `A` | Clock | Raster/cycle |
|---|---|---:|---:|---:|
| First call | AA | `$00` | 232,604,717 | 242 / 23 |
| Second call | BC | `$00` | 234,353,540 | 233 / 29 |
| Third call | BA | `$00` | 241,170,324 | 172 / 24 |
| Fourth call | BB | `$08` | 244,029,502 | 4 / 10 |

The AA loader returns naturally at `$CE33`, clock 233,556,167, before the
first `$9000` part entry at clock 234,345,374. A subsequent `$9000` entry
after BC is a different loaded state, captured at clock 240,239,206. Capture
files are paired by their explicit names, never merely by a recurring PC.

These clocks are observations along the original drive/ROM/IRQ execution
path. They are not graphics cycle budgets, frame rates or portable drive
timings. BB's different `A` value is preserved rather than silently treated
as equivalent to the first three calls.

A requested `$6000` stop later timed out. The next observation was `$CFC3`,
clock 562,574,379; no attempted-entry RAM or snapshot was created. The
attempt is rejected and retained in the transcript, with no inferred `$6000`
entry. The subsequent `ca-return.vsf` branch separates replayed execution
from the unobserved interval. A load destination alone does not establish
an effect's execution address.

The additional restore is observed at the original `$97E3`, clock
253,778,972. That branch subsequently reaches `$6D00` at 296,552,675,
`$6D12` at 296,552,747 and **`$C000` at 296,647,151**. These capture names
identify the gate, relocator and relocated entry. The independent
relocation/loop analysis belongs to the separate CA lane; this checker
asserts their native RAM/snapshot/CPU/beam identity without inventing a
`$6000` execution witness.

Four later same-PC stops are **logical draw/update boundaries**, not
full-frame checkpoints:

| Capture | PC | Clock | Raster/cycle |
|---|---:|---:|---:|
| `ca-iteration-a` | `$C85F` | 300,080,406 | 189 / 3 |
| `ca-iteration-b` | `$C85F` | 300,152,636 | 87 / 35 |
| `ca-iteration-c` | `$C85F` | 300,224,335 | 289 / 40 |
| `ca-iteration-d` | `$C85F` | 300,297,278 | 199 / 29 |

Their original PNGs show the waving dot-grid effect as an output observation.
The differing raster positions and clock intervals are retained; this lane
does not infer a fixed presentation cadence or a complete-frame pixel match
from a recurring code address.

The final branch restores `ca-entry.vsf` at `$C000`, clock 296,647,151,
then captures the first `$C840` at **297,765,535**, raster 261/cycle 4,
before the drawing path changes cached operands. Independent CA code
generation and effect models belong to the CA analysis lane; this receipt
checks that preparation stop's RAM, snapshot, CPU and beam identity.

## Byte checks and display limits

For every complete capture, the checker compares all **65,536 physical RAM
bytes** with the same-stop VICE snapshot, without excluded addresses. The
recorded CPU state and beam position must agree with the snapshot as well.
No asynchronous timeout exception is allowed in this continuation checker.
The receipt retains exact file/snapshot hashes and all comparison results.

Original-file payload identity is supplied by
[parts.py](../../research/second-reality/parts.py). Its
[receipt](../../build/research/second-reality/parts/parts.json), SHA-256
`98a0b452a175de22fac8a3fedc51cdf1f2d6685d3d196e882e347434e4da528c`,
is pinned and joined by exact captured-RAM hashes. This checker does not
recreate file references from native memory. Each source PRG/payload hash,
load range and native comparison is checked, as is the configured original
D64 hash.
See the separate [part-map explanation](second-reality-parts.md) for file
and loader protocol interpretation.

| Original file | Header load range, inclusive | Payload bytes | Captured payload comparisons |
|---|---|---:|---|
| AA | `$9000..$913F` | 320 | First loader return and first part entry. |
| BC | `$8600..$BF3F` | 14,656 | BC entry. |
| BA | `$0C00..$1FFF` | 5,120 | Fourth loader call, before BB. |
| BB | `$3000..$5FFF` | 12,288 | BB loader return. |
| BD | `$C000..$C8FF` | 2,304 | BD loader return. |
| CA | `$6000..$77FF` | 6,144 | CA loader return; this is staging, not an asserted execution entry. |

All **seven payload comparisons, 41,152 compared bytes**, are exact. The
file headers state where bytes load, not necessarily where they execute.
AA's later 256-byte helper copy has only 64 source bytes defined by the AA
file. A separate **native-prestate transition** compares all 256 destination
bytes at the second loader call with AA's 64 file-defined bytes plus the 192
source bytes captured before AA executes at the first part entry. Those 192
source bytes must also remain unchanged across this interval. The entire
copy is exact, but its padding is not promoted to AA-file data or assumed
boot-independent. The earlier first-loader-return capture is before this
particular copy and is not used as its post-state.

PNGs are checked for image integrity and recorded with their native capture
context. They are original-program output observations, not independently
reconstructed images. A register state at a later stop does not describe
every raster of the preceding frame. This lane makes no physical-VIC,
whole-demo renderer, SID-audio or general runtime/precalculation claim.
