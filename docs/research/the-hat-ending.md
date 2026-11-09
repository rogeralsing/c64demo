# The Hat B17: prepared logo, sprite carpet and raster cutoff

Research date: 8 November 2026. Original side-B resource 17 contains a
26,402-byte image at `$2000..$8721`. Its prepared sprite atlas reads
**THE HAT**, and its source has a horizontal strip-window controller, a
large unrolled raster body, a sprite initialization path and a timed IRQ
that restores an earlier stack pointer. These are concrete source/data
findings. This is a separate horizontal closing-logo carpet. The specific
all-border text upscroller discussed in the peer comments and teardown has
since been located in **side-B resources 8 and 9**, whose source atlas has
the goodbye, blue-background and ghostbyte-limitation credits. The guarded
[source classification](../../build/research/the-hat/dali-analysis/neighbor-probe-02/accepted-01/source-classification.json)
keeps that target distinct from B17; its native display proof is a separate
case.

The new passive [producer](../../research/the-hat/ending.py) consumes the
strict [Dali decode](the-hat-dali.md), not a screenshot or a guessed source
repository. It separates code, prepared data, finite arithmetic checks and
the remaining native display boundary. There is no CPU interpreter or
new native process in this lane.

## Original input and controller boundaries

The [disk extraction](the-hat-files.md) supplies raw side-B resource 17 at
loader address `$71F3`, with 5,423 compressed payload bytes. The separate
Dali acceptance recovers all **26,402 bytes**, without prior-RAM references:

```text
fb41ff61943ba509b4cae952b50f48643006550633a0a181603565834aecaa72
```

The decoded payload has several different roles. `$2000` is the unrolled
raster body, **not** the one-time initialization entry. Original `$8000`
waits for raster 249, clears a frame counter and installs the initial IRQ.
It calls setup at `$804B`, then loads the next resource through `$02D2`,
waits on `$804A` and eventually jumps to `$0800`. Setup returns at `$8135`,
so `$803D` is the original post-initialization continuation.

The raster body is `$2000..$322F`; it ends with a self-loop at `$322D`.
The following `$3230` is an RTS. The scroll/strip helper is
`$3231..$3367`. Data begins at `$3368`, so the early diagnostic's linear
listing through `$3513` is not an accepted executable-code inventory.
The producer's accepted listing stops at `$3368` and keeps its source
instruction counts separate from reachability and execution counts.

## What the prepared data contains

There are **13 bands × 128 strip slots** of sprite pointers at
`$3600..$3C7F`. They reference exactly **155 consecutive sprite IDs**,
`$30..$CA`, in VIC bank `$4000`. Their stored 64-byte slots occupy
`$4C00..$72BF`; each sprite has 63 significant image bytes. All 155
significant sprite images are distinct. Sprite `$30` is blank.

The independent asset decoder reads three bytes for each of 21 sprite
rows, extracts four two-bit selectors per byte, and repeats each logical
sample four times horizontally for multicolor plus X expansion. Its
prepared atlas therefore has 1,536 logical selector columns and 273 rows,
or **6,144 × 273** expanded sample geometry.

![Prepared nonzero-selector atlas, not native output](../../build/research/the-hat/ending-analysis/accepted-02/prepared-nonzero-mask.png)

White in this diagnostic means a nonzero selector; black means selector
zero. This is a binary opacity view of prepared sprite data, **not** a
native screenshot, current palette render or proof that all 273 rows are
displayed. It is sufficient to identify the literal THE HAT logo in the
prepared asset.

The 128 bytes at `$336C..$33EB` are blank-strip flags. Each byte is checked
against independent pixel emptiness across all thirteen selected sprites:
**80 strip slots are blank and 48 are nonblank**, with every flag matching.
Thus the strip-selection routine can skip empty columns using prepared
metadata rather than examining sprite pixels every frame.

## Underlying character field and palette

The first 1,000 screen bytes at `$4400` and `$4800` are identical. Decoding
their ordinary screen-code subset yields the familiar BASIC startup lines:

```text
**** COMMODORE 64 BASIC V2 ****
64K RAM SYSTEM 38911 BASIC BYTES FREE
READY.
```

The stored space glyph at `$4100` is eight `$FF` bytes; glyph `$7F` at
`$43F8` is eight zero bytes. The screen rows use `$7F` in their two final
columns. These are properties of this supplied character field; no ROM
font identity or displayed BASIC execution is inferred from the text.

Initialization selects character Color RAM value 6, background/border
`$0E`, multicolor on all sprites and X expansion on all sprites. It also
initially assigns `$0E` to all sprite palette sources. At that palette,
nonzero sprite selectors can cover the underlying field with its
background color. This is not permanent mask-only rendering: `$85C1`
subsequently obtains three independent multicolor selector colors from
tables at `$85E9`, `$8609` and `$8629`, writing `$D025`, `$D026` and all
eight local sprite-color registers.

Literal source writes select `$D011=$1A`, `$D016=$07`, `$D018=$10/$20`
and CIA2 PRA 2. With the appropriate effective bank pins, those two screen
choices are `$4400/$4800`, with the same character-set base. The effective
bank still requires the actual CIA2 DDR context; PRA alone is insufficient.
Final register values also cannot describe earlier scanlines that have
already passed through the timed raster body.

## Horizontal strip-window arithmetic

The helper reads speed `$34FD` (initially 4), direction `$34FE`, pixel
phase `$3501` and starting strip index `$3502`. It moves the phase by four,
wraps within 48 and advances the strip index accordingly. Direction
reverses at indices 0 and 117. This is a horizontal window into prepared
48-pixel strips; it does not generate new glyphs or prove a vertical
upscrolling text producer.

For each candidate strip, source arithmetic starts at coordinate
`-72 + phase` and advances by 48. A nonblank strip consumes one sprite
slot; blank strips still advance the coordinate and strip index. At most
eight slots are selected, and the coordinate scan stops after 384.
Unfilled strip-index slots preserve their prior values while their X-low
bytes are set to 127 and the corresponding X-high bits remain set.

The selected indices are copied into `$3514..$351B` for the raster body.
Two explicit source corrections subtract 8 from the first two wrapped
negative-X slots. This note records those exact source corrections; it
does not replace VIC counter/wrap behavior with an ideal screen-coordinate
model.

The producer compares a byte-recurrence translation of the original helper
with a separate signed-coordinate enumeration. The declared domain is all
48 phases, 118 strip indices, both directions and two prior-index arrays:
**22,656 comparisons, all equal**. Edge examples preserve the clamped
direction changes and old unfilled indices. This is finite arithmetic
acceptance, not an actual native helper-return or sprite-positioning proof.

A separate [endpoint-context wrapper](../../research/the-hat/ending_context.py)
now consumes the frozen functions and the final original-A-to-B
[native acceptance](../../build/research/the-hat/native-analysis/accepted-02/native-proof.json)
(358,877 bytes, SHA-256
`726b76be1f9560ff22697129c1de788da82e95beac7a3993fdc4ba498082e141`).
From the cutoff capture's phase 24, index 51, direction 0, prior selections
and speed 4, both source recurrence and signed-coordinate enumeration
predict all **28 recorded selection-state bytes** at the later controller
observation: phase 20; selected strips `[51,52,53,54,55,58,59,60]`;
X-low `$C4,$F4,$2C,$5C,$8C,$1C,$4C,$7C`; X-high mask `$E3`.
Blank flags come from the original decoded B17 payload; completed RAM is
only the equality oracle. The separate cutoff `$831B` to post-TXS `$831F`
pair restores SP `$56→$59` in six elapsed cycles with all 65,536 RAM bytes
unchanged. The [new receipt](../../build/research/the-hat/ending-context-analysis/accepted-01/ending-context-proof.json)
is 13,851 bytes, SHA-256
`86df60315514a157c9ddeddf8df1d29450adbab6986fad67d463903b6ad8c37f`.
Fresh self and root replays reproduce all three files / 23,399 bytes
exactly; independent root source review also passed. The
[root report](../../build/research/the-hat/ending-context-analysis/root-replay-check.json)
is 789 bytes, SHA-256
`7e53b2fb7215bed1b3a3490ffd54fc0a6bd3585a71aa2d827aad5a6310b22c58`.
These endpoints are **compatible with one helper update**. They do not
establish its exact call count, helper entry/return clocks, full raster-body
execution or displayed pixels. The 1,808 elapsed cutoff-to-controller cycles
include other work and are not the selection helper's measured cost.

## Raster body and ending IRQ

The raster body contains 229 absolute stores to `$D016`, 126 `LSR $D016`
sites and 126 `ROL $D013` sites. These are static instruction-site counts,
not observed execution counts or physical bus-write counts. RMW
instructions require their real NMOS dummy/final write behavior and actual
I/O mapping before a display-timing claim can be made.

Source writes sprite Y values:

```text
40, 61, 82, 103, 124, 145, 166, 187, 208, 229, 250, 15, 36
```

Each differs by 21 modulo 256. The source repeatedly changes sprite
pointers between the two screen-pointer arrays, `$47F8..$47FF` and
`$4BF8..$4BFF`, using the selected strip indices and successive band
tables. This is a prepared sprite-carpet structure. Actual DMA starts,
row counters, clipping and border coverage remain native observations.

The relevant IRQ structure is source-bound:

1. The active frame path at `$8211` enables all sprites, installs the first
   band pointers and positions, then arms IRQ `$82CA` for raster 17.
2. `$82CA` stabilizes timing using the CIA timer and self-modified padding.
   It programs the later IRQ from `$81CC/$81CD` (initially raster 271).
3. `$8305` saves the current SP into `$831A`; after acknowledging the IRQ
   and executing CLI, `$8317` jumps directly into `$2000`.
4. The later IRQ enters `$831B`, loads that saved SP and executes TXS. It
   thereby discards the interrupted raster body's current stack before
   disabling sprites and returning through the outer saved-register path.

Consequently, waiting only for the terminal `$322D` loop is not a safe
way to locate completion: the later IRQ may intentionally interrupt the
body before that loop. Capturing `$831B` before TXS preserves the hardware
IRQ's interrupted PC; its stack offsets differ from an ordinary JSR/RTS
continuation. A post-TXS capture at `$831F` can check the saved-SP restore.

The code also uses per-call-site running flags around `$3231` and the
scripted control routine, acknowledges the current IRQ, executes CLI and
allows nested interrupts. That source organization is visible in the
original payload. It does not create more CPU time or establish safety of
arbitrary shared routines and state.

## Current proof and remaining target boundary

The [static receipt](../../build/research/the-hat/ending-analysis/accepted-02/ending-proof.json)
is 14,603 bytes, SHA-256
`94fb63d5c8fc9ccecf7b595b3cd75973ee3c2ce36b222acb4d49d5f8f2ea030e`.
Producer: 18,675 bytes, SHA-256
`4cc8e89f7f324c64bff103bd1821e2d901857aba12ba4a4416fb7d911ddf6f4c`.
An independent agent replay reproduces all **six files / 912,586 bytes**
exactly; its [report](../../build/research/the-hat/ending-analysis/agent-replay-check.json)
is 1,043 bytes, SHA-256
`537a0006771cac9aa87143aca29de70aa07444ea4cb01cf216b3204c3a44ca15`.
The parent's independent source review and fresh replay also reproduce all
six files / 912,586 bytes; the [root replay report](../../build/research/the-hat/ending-analysis/root-replay-check.json)
is 1,007 bytes, SHA-256
`470cb8dcb890fcf5c3cd9bbcd31edabcf234193e7e42c7e2f7bf82e09220b099`.

```sh
rtk proxy python3 -B research/the-hat/ending.py \
  --output build/research/the-hat/ending-analysis/replay-new
```

Retained diagnostics include the initial overlong code/data listing, two
manual screen/asset-inspection syntax failures, a wrong preflight receipt
key and a replay-directory comparison issued before its same asynchronous
replay handle had finished. The actual completed replay was not restarted
or replaced. These are host diagnostic/setup mistakes, not native effect
counterexamples, and their notes do not pretend to be complete execution
receipts.

Original controller/load binding, timed store history, native DMA and
committed display pixels belong to the separately owned machine case.
The literal logo and resource order do not identify B17 as the named
upscroller. The B8/B9 target instead has independently recovered vertical
sprite-Y and pointer consumers. B17's full raster-composition mechanism,
exact physical border coverage, complete animation and useful
transfer/performance results remain open.
