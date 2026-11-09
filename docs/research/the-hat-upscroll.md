# The Hat: the B8/B9 upscroll source and timer cutoff

Research date: 8 November 2026. The correct source domain is **side-B files
8 and 9**, entered through file 7's controller. The original sprite-data
atlas contains the closing scroll's goodbye text, blue-background/border
discussion and production credits. The separately recovered B17 program is
the later horizontal logo effect. Passing its original-byte checks did not
identify the requested upscroll.

This note establishes original assets, scheduling instructions and bounded
independent source semantics. It does not yet reconstruct every coordinate,
pointer, color or committed pixel of the complete display.

## Original data and the controller chain

The frozen neighboring-source check binds these raw streams to the original
disk extraction and pinned Dali decoder:

| Original file | Decoded range, inclusive | Bytes | SHA-256 |
|---|---|---:|---|
| B8 | $4000–$CFFF | 36,864 | `5c8150c48068c62f8a77d8c97b18de33360dcb03046e0f5e9ffcb01ca6704ba6` |
| B9 | $E000–$F7FF | 6,144 | `9d0f80b7bc33c981a7befe2274ac98f30bf00c77916702016588b5e028e9a578` |

B7 calls the original compressed loader at **$203D and $2040**, waits for
its own completion flag, then jumps to **$8000 at $2048**. B8's distinguishing
entry bytes are:

```text
A9 F9 CD 12 D0 D0 FB A9 03 8D 11 D0 A9 00 8D F6 01 8D F7 01 78
```

The `$A9 $03 / STA $D011` at $8007 distinguishes this generation from B17's
later controller at the same numerical PC. B8 calls initialization at $804F,
then reaches the original loader call at **$8042**.

The [frozen source-classification receipt](../../build/research/the-hat/dali-analysis/neighbor-probe-02/accepted-01/source-classification.json)
also supplies the [static source atlas](../../build/research/the-hat/dali-analysis/neighbor-probe-02/accepted-01/b8-static-source-atlas.png).
That image interprets a stated eighteen-row subset of sprite data at
$4800–$6BFF; it is not a VICE screenshot or a complete asset-bank/display
oracle. Additional source data beyond that subset is not assumed blank.
The artist-linked font names remain separate catalog identities until an
exact font match is established.

## What is prepared and what changes at runtime

B9 supplies two **2,000-byte tables**:

- **$E1AE–$E97D:** initial sprite Y, ranging from 8 to 206.
- **$E97E–$F14D:** sprite-row pointer phase, taking multiples of eight from
  0 through 136.

The coroutine at **$E138** initializes the two source cursors; **$E152–$E159**
reads one pair into **$817D/$817E**. $E167 onwards increments the cursors.
These are prepared motion samples present in the original loaded data.
Their authoring tool/generator is not recovered. Two thousand samples do
not establish two thousand displayed fields or a frame rate.

The sprite glyph/image data is likewise supplied by the release. Runtime
work programs the sprite positions and pointers, executes carefully placed
register writes and chooses raster-program tails. It does not redraw the
whole text into a new software bitmap each sample in this inspected path.

At **$819D**, B8 copies $817D into all eight sprite Y registers. At **$81B8**,
it adds $20 to $817E and writes eight consecutive pointer values at
**$43F8–$43FF**. For a prepared phase `p` and sprite column `c`, the initial
source address, conditional on VIC bank $4000, is equivalently:

```text
pointer = $20 + p + c
address = $4000 + 64*pointer
        = $4800 + 512*(p/8) + 64*c
```

The scalar checks both forms for all 2,000 pairs and all eight columns.
It derives the initial program choice from pointer bit 3: **$8556** for
clear, **$A8DF** for set. This is an initial-pointer schedule, not a model
of every VIC fetch after subsequent raster writes.

There is an important temporal boundary: **$81F3 calls B9's updater after
the current Y and pointer registers have been copied**. A pair just written
at $E15C is therefore state for a later consumer, not automatically the
current field's hardware Y. The recorded sample-900 case demonstrates this:
RAM $817D is 13, while current VIC sprite Y is still 14.

## Raster selection, border writes and pointer reuse

At **$8516**, the program tests $43F8 bit 3. The two generated paths start
with horizontally offset coordinate presets and use different tails:

| Path | First regular program cell | Tail lookup tables |
|---|---:|---|
| Pointer bit 3 clear | $8556 | $F400/$F500 |
| Pointer bit 3 set | $A8DF | $F600/$F700 |

The path repeatedly changes sprite X coordinates, advances sprite Y by
$15 in source-specific groups, and builds the next pointer row by adding
eight. **$D018=$00/$10** switches between screen bases $4000/$4400 and
their pointer tables $43F8/$47F8. The graphics-display enable bit is clear
in the inspected $F200 control table, whose only values are **$88/$80**;
the border-size bits still change. The raster uses repeated **DEC $D016 /
STX $D016** sequences, with X=$88, alongside coordinate writes. Exact
border opening and emitted pixels still require native VIC timing/fetch
acceptance.

$D112 reads and $D118 writes are **VIC register mirrors when I/O is mapped**.
They must not be read as ordinary RAM state. Official x64sc source masks
the address to six register bits. It also returns `$D016 | $C0` on reads:
a DEC following a stored $88 produces raw final $C7, not $87. The effective
horizontal control fields pulse from $08 to $07 and back. The source proof
pins `vice-3.10/src/viciisc/vicii-mem.c`, SHA-256
`f8e2bdd30fbe8abf60a7e77647723f4615834e5b414f2695698ed28b31857edf`,
including its alias/read/store rules. The legacy `vicii/` implementation is
not substituted for x64sc's `viciisc/` source.

The scalar checks all **512** prepared tail-table entries. Every target
belongs to the expected original program set and starts at a guarded
`DEC $D016` cell. The actual target selected in a field still depends on
the live raster read; source data alone does not establish that chronology.

A second independent finite check covers the regular **$88EF–$892B**
coordinate/control stencil. It models the explicit vector decrements,
forced sprite-3 value $88, increments and final $D016 effects. Under its
declared steady-entry condition, all X values return to their start and
$D016 returns to $C7. **1,792 component cases** check closure across all
byte values of the other seven coordinates. A wrong sprite-3 entry condition
is rejected. This is twenty instruction-level final writes in a bounded
template, not a CPU interpreter, bus-cycle model or an assumption that the
native program entered the stencil with that state. Physical RMW dummy
writes, stalls and absolute write cycles are explicitly outside the model.

## The cutoff is CIA1 Timer B

The setup is a raster IRQ, but the long raster program is cut off by
**CIA1 Timer B**, not a later VIC raster-compare IRQ:

1. **$821C–$822F** reads the actual sprite-0 Y register, subtracts two, and
   uses that byte to read the low/high latch tables at $82CC/$83CC. The
   values are written to **$DC06/$DC07**.
2. **$8234** writes **$82 to $DC0D**, enabling the Timer-B interrupt bit.
   This set-mask operation alone does not prove that other IRQ sources
   are disabled; the native mask must be checked separately.
3. **$8269** writes **$19 to $DC0F**: start, one-shot and force-load.
   The force-load bit is a strobe; it must not be expected to remain set
   in the serialized CRB byte.
4. **$8279/$827A** saves the stack pointer at $828B. The code installs
   vector **$828C**, sets the VIC compare to unreachable PAL line **511**,
   enables interrupts and jumps to **$8516**.
5. At **$828C**, the cutoff handler changes mirrored $D018, reads **$DC0D**,
   restores the saved stack pointer with **TXS at $8297**, and disables
   sprites. The abandoned raster work never returns normally. **$8298**
   is the useful post-stack-restore observation point.

Timer A has a separate synchronization role. **$8249–$8253** calculates
`$13 - read($DC04)` and patches the following branch displacement into a
delay area. The snapshots retain Timer-A latch **62** and CRA **$01**,
consistent with a running 63-tick period. That phase read is distinct from
the Timer-B one-shot interrupt; no timer was inferred from a screen color.

All 256 original timer-table words satisfy:

```text
TimerB_latch[x] = $440F - 63*x
x = sprite0_Y_readback - 2
```

The inverse line term compensates for the launch position. It is a latch
formula, not an exact prediction of timer start, underflow, CPU recognition
or IRQ-entry clocks. CIA pipelines, phase, synchronization code and VIC
stalls remain relevant. The source model does not invent absolute raster
timestamps from this identity.

## Native context and its separate acceptance

The root-owned fresh original-B case is closed. The separate
[native audit](the-hat-upscroll-native.md) accepts all **19 RAM/VSF pairs**,
the original full B8/B9 load binding, wire chronology and snapshot schema.
Its [receipt](../../build/research/the-hat/upscroll-native-analysis/accepted-01/upscroll-native-proof.json)
is **615,890 bytes**, SHA-256
`54f255845253703f876a2cc7915ef008d9f9dd479feb991fb898c4f9f6d28071`.
The following source interpretation consumes that custody proof and its
separately retained snapshot context:

| Boundary | Even path | Odd path |
|---|---:|---:|
| Selector CIA1 interrupt mask | $02 | $02 |
| Selector pending flags | $01 | $01 |
| Timer-B latch | 16,667 | 16,541 |
| Selector Timer-B counter | 16,630 | 16,504 |
| Cutoff pending flags / asserted IRQ | $83 / 1 | $83 / 1 |
| Post-TXS pending flags / asserted IRQ | $00 / 0 | $00 / 0 |
| VIC pending IRQ / compare at selector and cutoff | 0 / 511 | 0 / 511 |

At both selectors and both cutoff captures, actual VIC registers are
`$D015=$FF`, `$D017=$00`, `$D01B=$00`, `$D01C=$00`, `$D01D=$FF`, and
`$D020=$D021=$06`: eight enabled **hires sprites with horizontal expansion**,
no vertical expansion, foreground sprite priority and blue border/background.
The coordinate decrements therefore shift those sprites one physical
horizontal coordinate at a time. This is a four-boundary mode contract,
not a claim that the entire effect keeps those values. Stored `$D016` is
**$C7** at the even selector/cutoff and **$88** at the odd selector/cutoff;
the finite $88EF stencil's $C7 precondition is not imposed on the odd path.

The recorded even selector-to-cutoff interval is **16,641 elapsed PAL
cycles**, clock `145415945→145432586`; the odd interval is **16,513**,
clock `146261279→146277792`. Both cutoff-to-post-TXS observations span
35 elapsed cycles. These are bounded observed intervals, including VIC/IRQ
phase effects, not complete-effect frame rates or nominal CPU instruction
costs. The corrected line-300 observation belongs to a later field after
the retained rejected raster request; it does not complete the earlier
even interval into one uninterrupted displayed-frame proof.

Timer A's pending bit is present but masked. The enabled pending source is
Timer B. CPU A=$83 after `LDA $DC0D` includes both timer flags and the master
flag; it must not be described as Timer A causing the cutoff. No $DC00–$DC0F
write trace was armed. These facts come from serialized CIA1 state and the
CPU continuation, not an invented I/O trace.

The trusted reader uses CIA module version **2.5**, payload length **77**.
Relevant payload offsets are counter B **6**, mask **13**, CRB **15**, latch B
**18**, pending flags **20**, timer-B state **43**, and IRQ-enabled **47**.
The word fields are little-endian. Serialized CRB remains $09 here, while
the timer-state word changes from **$196B to $1128**. Official
`ciatimer.h` defines running as state bit $0001; the timer is stopped after
its one-shot even though the saved raw control byte retains bit 0. This is
why the counter, latch, timer-state word and interrupt fields must remain
distinct.

The even selector's actual Y14 gives table index12 and latch16,667, despite
the newer RAM motion state Y13. The odd case's Y16 gives index14 and
latch16,541. Both CIA2 snapshots have PRA2/DDRA$3F, supporting effective low
pins2 and bank $4000. Timing-helper bytes $019F–$01AB match the original
shared delay chain, but the finite model does not use them to invent an
elapsed-cycle total.

Native instruction-store traces also retain an important endpoint detail:
one delayed watchpoint reports its store at the cutoff clock while the
attached register query already shows PC$828C. A blanket requirement that
each attached PC equal the reported instruction address plus its length
would reject legitimate interrupt-boundary evidence. The native audit owns
that chronology. Its rejected hexadecimal raster request is preserved;
the corrected line-300 observation is separate.

The [machine-context output](../../build/research/the-hat/upscroll-native-analysis/accepted-01/capture-machine-context.json)
is 1,004,114 bytes, SHA-256
`9e6e87aad43ba6bd40a489456fb5e0883d0f9b15188a235c3c3c8051a199b0ed`.
Independent root source review and native-custody replay reproduce all
four native-audit outputs / 4,346,135 bytes exactly; the
[report](../../build/research/the-hat/upscroll-native-analysis/root-replay-check.json)
is 2,463 bytes, SHA-256
`98b648668a72124dee1f61536323e92d2de92c989a7ce42d64d52dacec0e7a55`.

## Replay and the remaining boundary

```sh
rtk proxy python3 -B research/the-hat/upscroll.py \
  --output build/research/the-hat/upscroll-analysis/fresh-replay
```

Static source receipt: `accepted-01/upscroll-source-proof.json`, **7,832 bytes**,
SHA-256 `f8b1aefa687684c6c3bb9b67735a444d857e8c15d8d9e941eb050526a52228a7`.
Producer: **13,716 bytes**, SHA-256
`dcde1af559f66fe7890c4967bbabb3a18fdf8d72391a9342d3d0802edca18515`.
Independent root source review passed, and a fresh replay reproduces all
**six files / 1,152,914 bytes** exactly. The [root replay report](../../build/research/the-hat/upscroll-analysis/root-replay-check.json)
is **1,366 bytes**, SHA-256
`2bc1f8d33d30587718809468f5311fcb4e88c774c2921b7d48d2db74eb46f284`.
Its harmless initial wrong-output-folder setup is retained in the report.

The next useful step is a complete coordinate/pointer/color model for the
two recorded program paths, bound to actual register readback and dispatch
history. Full committed output pixels follow that boundary. This pass does
not claim a complete displayed upscroll, physical RMW bus trace, every
scroll sample or whole-effect FPS.
