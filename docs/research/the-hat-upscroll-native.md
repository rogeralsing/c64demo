# The Hat: original B8/B9 upscroll native custody

Research date: 8 November 2026. The original side-B disk now has a closed,
replayable native case that reaches the B8/B9 text-upscroll resource without
a RAM or PC patch. Both complete decoded resources match loaded RAM before
initialization. Two prepared motion writes and the two pointer-selected
raster variants have bounded source/snapshot bindings. Their cutoff uses
**CIA1 Timer B**, with an explicit saved-stack restore.

This result is separate from the B17 horizontal THE HAT closing-logo
carpet in [the B17 note](the-hat-ending.md). The [B8/B9 source study](the-hat-upscroll.md)
explains the prepared text, motion tables and write stencils. This note
accepts the retained native evidence and its limited comparisons; a full
scanout/pixel or absolute timer-deadline model remains open.

## Closed original-disk case

The passive [producer](../../research/the-hat/upscroll_native.py) reads
`build/research/the-hat/native-02/`. The owner started original side B with
PAL VICE, true drive emulation and a 1541 drive, then closed and reaped that
one process. The ZIP member is compared byte-for-byte with the startup D64:

```text
the-hat-7a825b1-b.d64
1527038ebebca1a3d3d3379b91dd1a77dffb6d6d89a4dbfc32bf3f6908eb5b21
```

The [owner's closed manifest](../../build/research/the-hat/native-02-files.json)
pins **46 files / 61,778,341 bytes**, canonical listing SHA-256
`6c1d2df597cbf1751a2f5e8bbffb5afb020f06eac27991841ed3a73bdf987454`.
The manifest itself is 7,189 bytes, SHA-256
`dd06be2ba97ed9255cd922938b41bd0aec84daa21448454361128c2b49692d2d`.

There are 151 ordinary commands: 150 complete and one explicitly
interrupted. The frozen wire auditor checks every input, sent and received
byte range, event, command queue, original pending handle, timeout and
closure. It confirms no ordinary resend or restart. The exact command-list
digest is
`0f34b0cbd778182801bd4f688b1de1266c6be3f56cf132e52432c6b61be5f8d5`.
The observation/export/checkpoint grammar excludes RAM, register and PC
patches, snapshot restoration and extra keyboard/media input. Warp controls
remain explicit. Actual `warp` and `Speed` queries are retained; navigation
includes a declared warp-on interval, and the B8 controller, later field
and final queries show warp off and Speed 100.

All **19 RAM/VSF pairs** compare the full 65,536 physical RAM bytes, CPU
registers/flags/clock, CPU-port latch/DDR/readback, and raster line/cycle at
the same stopped interval. The frozen pair helper's production-specific
DDR `$2F` constant is removed while its equality and readback checks remain.
Thus the actual original transition to DDR `$37` is accepted from matching
wire and snapshot state.

## Original source is bound before initialization

The original bootstrap has 2,708 payload bytes at `$0801..$1294` and its
BASIC line invokes `$080D`. The first side-B loaded resource contributes
all 263 independently decoded bytes at `$0F00`. Both compare exactly with
their natural captured RAM generations.

At both `b7-loaded` (`$2043`) and `b8-controller` (`$8000`), the producer
compares **every byte** of these two independent source outputs:

| Resource | Destination | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| B8 | `$4000..$CFFF` | 36,864 | `5c8150c48068c62f8a77d8c97b18de33360dcb03046e0f5e9ffcb01ca6704ba6` |
| B9 | `$E000..$F7FF` | 6,144 | `9d0f80b7bc33c981a7befe2274ac98f30bf00c77916702016588b5e028e9a578` |

That is **43,008 source bytes at each of two capture boundaries**. The
strict [source-classification receipt](../../build/research/the-hat/dali-analysis/neighbor-probe-02/accepted-01/source-classification.json)
is the source authority; native RAM is the comparison oracle. No unknown
source bytes are supplied from native captures. B7's original two-load,
wait and `JMP $8000` controller bytes are checked separately. The original
initializer call is `JSR $804F`, returning naturally to `$8042`.

## Two actual prepared-motion writes

Original `$E152..$E15B` reads paired tables through zero-page cursors and
writes `$817D/$817E`. The before/after snapshots show exactly these results:

| Table index | Before PC | After PC | Elapsed clocks | Source pair = actual RAM pair |
| ---: | --- | --- | ---: | --- |
| 0 | `$E152` | `$E15C` | 18 | `[206, 0]` |
| 900 | `$E152` | `$E15C` | 18 | `[13, 16]` |

The two cursors agree on the table index, Y is zero, the cursor bytes do
not change in this interval, and any changed RAM byte belongs to the two
declared destinations. This binds two original table reads and writes; it
does not turn all 2,000 prepared entries into measured frames.

The temporal order matters: `$819D` copies the current Y to all sprites,
`$81B8` copies the current pointer phase, and **then** `$81F3` calls the B9
motion controller. Consequently, a newly written pair can describe the
next consumer state. At the even selector, RAM is `[13,16]` while every
actual VIC sprite Y is **14**. The proof reads both independently.

## Both source-selected raster variants

Original `$8516` tests bit 3 of sprite pointer `$43F8`. The even observation
has pointers `$30..$37`; the odd observation has `$38..$3F`. The latter
naturally reaches `$A8DF` 75 clocks after its selector. Original B8 code
guards remain equal at the initialized observations.

| Observation | Even | Odd |
| --- | --- | --- |
| Selector clock at `$8516` | 145,415,945 | 146,261,279 |
| Current Y of all eight VIC sprites | 14 | 16 |
| Source timer-table index, current Y minus 2 | 12 | 14 |
| CIA1 Timer-B latch | 16,667 | 16,541 |
| Timer-B counter at selector | 16,630 | 16,504 |
| Cutoff clock at `$828C` | 145,432,586 | 146,277,792 |
| Hardware-stacked interrupted PC | `$97FF` | `$B6E5` |
| Restored clock at `$8298` | 145,432,621 | 146,277,827 |

The source latch tables satisfy `0x440F - 63*index` at these actual
hardware-Y indices. CIA2 PRA 2 and DDRA `$3F` give effective bank pins 2,
selecting VIC bank `$4000` at both selectors.

The two selector and two cutoff snapshots also have all eight sprites
enabled (`$D015=$FF`), no Y expansion (`$D017=0`), foreground priority
(`$D01B=0`), hires sprites (`$D01C=0`) and X expansion (`$D01D=$FF`).
Background and border are both 6. These are hires sprite rows doubled
horizontally; they are separate from VIC character/bitmap mode. The
recorded `$D016` bytes differ between variants: `$C7` even and `$88` odd.
The root replay report binds these observations to the accepted context
JSON; register values alone do not prove border scanout pixels.

At each selector, CIA1's interrupt mask is 2, pending flags are 1, and
Timer B's internal state is `$196B`. At each cutoff, pending is `$83`, the
CIA IRQ is enabled, and Timer B has reloaded its latch with internal state
`$1128`. VIC IRQ status is zero and its raster compare is 511. The masked
Timer-A pending bit therefore does not identify the active source. The
original source starts a one-shot Timer B and points the IRQ at `$828C`.
Together these source/snapshot checks bind the cutoff to **CIA1 Timer B**.

The cutoff handler writes the `$D018` mirror at `$D118`, reads `$DC0D`,
loads saved SP `$59` and executes TXS. Before that restore, SP is `$56`;
the hardware IRQ's three stack bytes recover the interrupted PCs above.
At `$8298`, SP is `$59` and A is `$83`, matching the CIA acknowledgement.
Each interval takes 35 observed clocks and preserves all physical RAM
bytes. The internal Timer-B running bit changes from set to clear; raw
serialized CRB remains `$09` and alone would give the wrong running-state
conclusion. The frozen reader's field layout and pinned VICE timer source
are retained in the proof.

**The absolute timer deadline is not hardware-validated here.** The store
watch ranges did not cover `$DCxx`, so there is no timed trace of the
Timer-B latch/start writes. The proof distinguishes that open scheduling
question from the observed pending source and stack transition.

## Complete trace custody, including the observer failure

The configured store hooks cover `$D000..$D3FF`, `$DD00..$DD03` and
`$43F8..$43FF`. The producer checks all **75,370 observed trace hooks**:

| Response sequence | Hooks | Retention |
| ---: | ---: | --- |
| 82 | 11 | Every hit |
| 88 | 1,742 | Every hit |
| 94 | 2 | Every hit |
| 100 | 71,890 | Complete raw response plus all-hit aggregates/digests |
| 130 | 8 | Every hit |
| 136 | 1,716 | Every hit |
| 142 | 1 | Every hit |

Every header is paired with its instruction line and attached `r`; clock,
beam, A/X/Y/SP, checkpoint generation, code-byte provenance and raw byte
framing are checked. Hook totals do not claim NMOS dummy/final bus-write
counts. The long response is compacted only in the derived JSON; its full
**17,253,726 bytes** remain in the pinned original wire.

One important store-hook boundary is retained: response 94 reports a
`STA $D000` from `$97FC` with the observed PC already at `$828C`, at the same
clock as the preceding cutoff stop. The validator does not impose
`postPC = storePC + 3`; deferred store reporting can include IRQ-entry
context.

The first intended line-300 breakpoint was an observer error. The command
`RL == 300` was normalized by VICE to **`RL == $300`**, decimal 768, outside
the PAL line domain. Its pending response 100 was interrupted once. The
full `rejected-raster-request` RAM/VSF pair is retained at actual `$8048`,
line 0, cycle 3, clock 146,240,643, and is **excluded from requested
line-300/full-field acceptance**.

The interrupt request was not the end of the trace stream: its retained
suffix contains **7,364 further trace headers and 7,366 register rows**.
The shared, pinned 1,298-byte framing helper binds only the final explicit
interrupt-`r` frame using the same PC prompt, exact ADDR header, one strict
register row and final prompt. The ordinary register reader remains
strict. All intervening trace hooks remain checked. The final frame starts
at response offset 17,253,600 and is 126 bytes; the complete 1,767,662-byte
interrupt suffix retains its own digest.

After deleting the unreachable condition, command 108 explicitly requests
`RL == $012C`. VICE reuses checkpoint number **1**, a new generation.
Command 109 naturally stops at `$81B2`, line 300, cycle 0, clock
146,259,540. Conditions are parsed using an exact predicate grammar;
unknown terms reject, and actual RAM/raster predicates are evaluated.
The saved PNG is cosmetic evidence only. No independent framebuffer or
full-field pixel comparison is claimed from this single beam observation.

## Reproduction and remaining boundary

The accepted [native receipt](../../build/research/the-hat/upscroll-native-analysis/accepted-01/upscroll-native-proof.json)
is **615,890 bytes**, SHA-256
`54f255845253703f876a2cc7915ef008d9f9dd479feb991fb898c4f9f6d28071`.
Producer: **47,151 bytes**, SHA-256
`3edd29533e90036c596949d030928ac36da76c7ac4dacb7af62b95420defdfbf`.
Its four output files total **4,346,135 bytes**. A fresh agent replay is
byte-identical; its [comparison report](../../build/research/the-hat/upscroll-native-analysis/agent-replay-check.json)
is 751 bytes, SHA-256
`922f183b7321682bff08ff56eca407d24a8dee4fd47d16ae8a073dd38992a84d`.
The parent independently reviewed the complete producer and reproduced
all four files exactly. Its [root replay report](../../build/research/the-hat/upscroll-native-analysis/root-replay-check.json)
is 2,463 bytes, SHA-256
`98b648668a72124dee1f61536323e92d2de92c989a7ce42d64d52dacec0e7a55`.
That report also records the four sprite-mode observations above.

```sh
rtk proxy python3 -B research/the-hat/upscroll_native.py \
  --output build/research/the-hat/upscroll-native-analysis/replay-new
```

`candidate-01` preserves its exact checked source and failure traceback.
That run passed the native/source/trace checks, then rejected a mistaken
primary-source anchor name, `ciacore_readCRB`. The actual VICE source uses
the `CIA_CRB` switch arm. The corrected acceptance uses a fresh directory;
the failure is not presented as a native effect counterexample.

The accepted producer is passive: no emulator, process controller,
downloaded program, CPU interpreter, live socket or build is started.
What remains open is complete pixel composition across the borders,
absolute hardware timer timing, animation coverage and any useful
performance/transfer result. Observation clocks and prepared table
entries do not establish FPS or portability to physical hardware.
