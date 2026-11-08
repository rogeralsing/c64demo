# Spires: original native FPP binding

The original disk now binds to the published FPP mechanism: a natural original
boot payload, eight-entry service table, all 130 unrolled pointer rows and all
4,032 generated meaningful stripe bytes agree. Native snapshots also show the
seven staggered sprites fetching offsets `0,3,6,9,12,15,18`, the expansion-flop
reset, and those counter offsets staying fixed over a subsequent raster line.
A separate fresh boot reaches actual blue sprite colors and a visible blue
checkerboard. This is a bounded code, data, fetch and counter result; there is
no independent committed-pixel compositor or whole-frame/FPS proof.

The passive acceptance producer is [`research/spires/native.py`](../../research/spires/native.py).
The receipt is `build/research/spires/native-analysis/native-proof.json`.
The [earlier source/asset note](spires.md) supplies primary author/download
provenance and the separate TechTech asset proof.

## Correction to the frozen source note

The earlier note and source receipt incorrectly named the seven pointer
addresses `$ACF9..$ACFF`. The arithmetic is:

```text
base + scnpage + $03F9 = $8000 + $2C00 + $03F9 = $AFF9
screen = $AC00; pointer table = screen + $03F8 = $AFF8
used sprite pointers = $AFF9..$AFFF
```

This was an error in our literal-address description. The published assembly
already uses the correct expression, and the original executable writes the
correct addresses. All prior frozen files remain unchanged; this extension
records the correction explicitly. Expanding all 130 macros with the corrected
addresses matches 4,550 actual native code bytes. Substituting the old wrong
addresses changes 910 bytes and fails that comparison.

## Three retained cases

| Case | Result | Directory SHA-256 |
|---|---|---|
| `native-01` | Observer startup failed; no monitor traffic or captures | `9eaa979ea65241ae1bd3913d7738185a545cda2490efc2316e229bc9cfb89d59` |
| `native-02` | Original entry, generation and two black-color FPP windows | `e65433c6938a120d8a62f6d0571dd938f6e2d460dd1edf9ce7356db2ac0eb9af` |
| `native-03` | Separate original boot, correctly masked blue-color FPP window | `b72fb9b7a73e3bbfda3b62def4fdb42d8f6784f636db28b2fa88d64c4cbd586b` |

`native-01` retains seven files and the exact error
`OSError(22, 'Invalid argument')`. The owner observed failure while starting
the observer with non-PTY input, then used selectable PTY input for the new
case. The retained failed case independently establishes the error, empty
wire files, termination of owned PID 91443 and its reaping with exit `-15`.
It supplies no native execution witness and is not called a recovered timeout.

Both successful cases boot the same original D64 afresh through autostart and
a true 1541 drive. Neither restores a prior snapshot or injects RAM, PC or
register values. `native-02` has 150 completed serialized commands and 13 full
RAM/VSF pairs; `native-03` has 52 commands and four pairs. Every pair checks all
65,536 RAM bytes, CPU registers/clock/ports and VIC beam state: **17 pairs and
1,114,112 compared RAM bytes**. There are no observation waits, interrupted
resumes or rejected monitor commands in these successful cases.

The frozen wire auditor is reused with one declared adaptation: its manual
load metadata assertion becomes an exact original-disk autostart assertion.
Raw input/sent/received custody, serialization, response and process closure
checks remain in force. Native02's initial navigation and native03's search
for blue are declared warped navigation. Accepted proof resumes explicitly
confirm warp off and `Speed=100`; no later warp change may intervene after the
cited query. No observer or original-code helper is modified.

## Original boot and code fingerprints

Both natural `$080D` stops match all **12,425 loaded payload bytes** from DOS
file `SPIRES       [O]`, loaded at `$0801..$3889`. The original PRG itself is
12,427 bytes including its load header. This binds each capture lineage to the
original disk before depacking, independently of source similarity.

Native02 reaches `$9000` naturally after the intro. Its eight-JMP table is:

```text
4c58a4 4cf3a3 4c55a6 4c5ca6 4c38a6 4c3da6 4c11a6 4c75a6
```

The first target `$A458` matches the source-derived screen-initialization
prefix, including its backward jump. The driver contains the exact expected
call sequence through `$9000`, `$900C`, `$900F` and `$9003`. Additional color,
end-check and VIC-bank service bytes agree. The source's screen remains
`$AC00`, charset `$A800` and `$D018=$BA` in VIC bank `$8000`.

The 130 consecutive 35-byte macros begin at `$90E9`, read pointer rows from
`$A87D+i`, and match the published instruction order and fine-Y immediate:

```text
load pointer[i]
STY $D017                 ; Y=0
STA $AFF9 .. $AFFE        ; first six used sprites
STX $D017                 ; X=$FF
STA $AFFF                 ; seventh used sprite
LDA #($18 | ((i+61)&7))
STA $D011
```

The exact 4,550-byte expansion has SHA-256
`de73b5c38e7fc2cd242da55ab4c3350cb48f6467f5450e1b268019685c2dd782`.
The same block remains present in every later accepted native checkpoint.
This binds the missing `freshzoom.prg` import's mechanism to original runtime
code, without claiming a full rebuilt-source or binary identity.

## Generated stripes and actual first-band fetches

Between native02's `$9000` entry and natural `$9003` entry, 2,444 meaningful
stripe bytes change. After generation, all **4,032 known bytes** agree with
the independent source arithmetic retained by the earlier proof. The 64
ungenerated byte-63 locations happen to be zero at the prepared endpoint.
Those values are observations, not proof that the generator wrote them or
that no transient/redundant stores occurred.

At the first clear, sprites 1–7 have MCBASE `0,3,6,9,12,15,18`, MC `3..21`,
pointer zero and cached data `$555555`. The producer independently reads the
corresponding three RAM bytes for each actual pointer and MCBASE and compares
them with the cached 24-bit latch. It repeats that check at all accepted active
checkpoints. The first clear changes `$D017` from `$FF` to zero and the seven
expansion flops from zero to one; the counter offsets remain unchanged.

The first field also exposes initialization state that the source does not
repair until later `calcfx`: sprite 4/7 cached X values are 412/484 because old
X-high bits remain set. They are not seven adjacent visible sprites in that
first field. A later natural checkpoint has `$D010=0`, regular X spacing and
pointer `$1B`, selecting generated stripe width **28**, not 27. At two
consecutive preclear stops one raster line apart, all seven MCBASE offsets
stay `0,3,..18` while the actual cached data still agrees with RAM. The native
delta is 63 PAL CPU clock positions. Only this first data band is observed;
the other two source bands are not promoted to native evidence.

## The color guard failure and fresh blue observation

Native02's condition `@io:$d028 != $00` was wrong: unused color-register read
bits are high. A black low nibble therefore reads `$F0` and passes. The pinned
official VICE 3.10 `src/viciisc/vicii-mem.c` supplies both the `$F0` unused-bit
mask and the peek/read behavior; the producer verifies that source rule. All
seven saved sprite color low nibbles in native02 are zero. Its `mature*`
filenames remain retained labels and do not establish visible fill.

Native03 uses `(@io:$d028 & $0f) != $00` on a **fresh original boot**. Its three
active endpoints have color low nibble **6, blue**, for all seven used sprites,
`$D010=0`, `$D01B=$FF`, `$D018=$BA` and the expected staggered Y values
`61,60,59,58,57,56,55`. All 4,032 meaningful pattern bytes still match, and
the actual row latches and MCBASE hold are checked independently. This case
does not capture the generator entry or claim its stores were individually
observed again.

The retained `native-03/colored-window.png` visibly shows a blue checkerboard
within the gray frame, above the SPIRES text. The character mask clips its
left side. Seven fetched sprite rows do not imply seven fully visible sprite
rectangles. The screenshot is a visual observation; it is not a palette-index
oracle or a full-frame pixel comparison.

## Complete bounded traces and delayed delivery

The producer checks every traced macro store's PC, target, row, raw cycle,
embedded clock and actual A/X/Y-derived store value:

- Native02: **1,970 records**, covering rows 1–130 and later rows 64–130.
- Native03: **670 records**, covering blue rows 64–130.

Within these windows the clear is reported at raw cycle 18, six pointer writes
at 22..42, expansion set at 46, seventh pointer at 50, and `$D011` at 56.
These are observed VICE checkpoint clocks, not certified physical bus-write
phases. The trace ranges are `$D000..$D02E`, `$DD00..$DD03` and `$AFF8..$AFFF`.
Other RAM is not continuously traced.

Several native02 stop-boundary stores print only on a later resume. For
example, the first clear at clock 75,247,092 is delivered in response 60,
and the seventh pointer store at 75,247,124 is delivered in response 93.
The producer preserves delivery sequence separately from the embedded clock;
it does not attribute the delay to monitor-bank switching. Both traces include
their final `$D011` store before their terminal capture, so terminal-buffer
flush is checked for these finite windows.

## Replay and continuation

```sh
rtk proxy python3 research/spires/native.py
```

The only generated outputs are under `build/research/spires/native-analysis/`:
the receipt, its checked producer copy, and the two decoded store traces. All
raw cases and prior source evidence remain unchanged.

The latest retained endpoint is native03's `colored-window-complete.vsf`,
PC `$A2B1`, clock 77,633,652, raster line 192/raw cycle 12. Snapshot SHA-256:
`96691e36ee0e6aa645cd8be6e116a60297b554894ae8d8cfe9a8678839302855`.
It is the current continuation input, not permission to claim a complete
312-line field from the current draw buffer.

Remaining research can separately capture the other two natural Y groups and
their offsets `21,24,..39` and `42,45,..60`, or build a character-mask-aware
committed-pixel oracle. TechTech's runtime bank/screen/font/timing binding also
remains open. None of those extensions, a full source rebuild, broad animation
coverage or FPS measurement is required or claimed by this receipt.
