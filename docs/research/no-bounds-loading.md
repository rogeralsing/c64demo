# No Bounds: loading, streaming buffers and part handovers

Raistlin's [11 October 2026 article](https://c64demo.com/seamless-loading-nobounds/)
explains the loading design of Genesis Project's **No Bounds (2023)**. Small
transition IRQs keep the image and music running while the main thread loads;
preloading and stream buffers avoid holding every scene's data at once.
Its descriptions of seamless presentation, hardware testing and spare CPU
time are author reports, not measurements reproduced here.

The [published source](https://github.com/RobertTroughton/C64Demo-PublicReleases/tree/965807c511e2025b5c5e1ffb2a6235a4efd6ae5b/NoBounds)
lets us check a narrower set of concrete contracts: the stream manifest,
its geometry, the bytewise music-counter comparison and the return-address
handover. No assembler, Sparkle decoder, downloaded tool or C64 program is
run by these checks. Source/build and original-disk equality remain open.

## Twenty strips fit in four resident buffers

The source image is 1,600×200 physical pixels. Its initial 320-pixel viewport
is prepared separately; the remaining 1,280 pixels become **twenty 64-pixel
strips**. Each strip contains eight character columns across all 25 rows.
The C++ `CHUNK` layout is precise:

| Component | Stored layout | Bytes per strip |
|---|---|---:|
| Bitmap | 25 rows × 8 columns × 8 bytes | 1,600 |
| Screen attributes | 25 × 8 | 200 |
| Color attributes | 25 × 8 | 200 |
| Total | Bitmap plus both attribute planes | **2,000** |

Thus the 40,000-byte stream includes **32,000 bitmap bytes and 8,000
attribute bytes**. Calling it 40,000 bitmap bytes would overstate its pixel
payload. This follows the literal arrays and the assembly's separate bitmap,
screen and Color RAM fetch offsets; it does not require guessing from a video.

The ring uses `$7C00`, `$7400`, `$9800` and `$9000`, in that order. Each
2,048-byte slot holds 2,000 payload bytes, so four slots retain **8,000 payload
bytes**. The published `StreamData.sls` starts with four `File` entries in
group 0. Groups 1 through 16 each declare the other three resident strips
with `Mem` and supply one new `File`, replacing the oldest slot.

The independent plan derives strip count/size from the source geometry and
computes ring addresses and file offsets with integer indexing. It matches
all **68 manifest rows**: twenty new-file definitions and 48 resident-memory
definitions. Every `Mem` declaration agrees with the preceding modeled slot
occupancy. These are source/manifest consistency checks, not observations of
actual transfers or Sparkle's compression references.

## Loading is requested by the display controller

The No Bounds IRQ increments `$0400` at the selected scroll boundary. The
DISK script's main loop waits for that signal, calls `IRQLoader_LoadNext`,
then decrements it. A separate counter stops requesting additional image
bundles, and the later ease-out raises a signal to preload the outgoing fade.
The production script places that fade after the streaming script.

The runtime copies bitmap bytes and attributes at different phases. Four
buffer indices select alternate display-bank update functions. This source
structure explains why a strip must remain available until its consumer
finishes; the manifest alone cannot prove refill deadlines, producer/consumer
ordering under IRQs or tear-free presentation. Those require original-disk
execution and a matching raster/memory trace.

The article's broader strategy is supported by the surrounding scripts:
RotatingGP preloads the next artwork while its own IRQ runs, and the outgoing
fade loads Trailblazer while its raster transition and music continue. This
overlaps jobs in time; it does not make loading or rendering consume zero CPU.

The author also describes separating repetitive generated opcodes from their
varying operands to improve compression. That is a packaging/preparation
choice, not a reduction of the expanded code's live RAM footprint. This
batch does not reproduce the reported compression improvement.

## The music sync is a 16-bit unsigned comparison

The original `MusicSync` macro reads `$D011` and waits until its high raster
bit is set, then compares the music counter to its configured target:

```text
carry = (counter_low >= target_low)
high_result = counter_high - target_high - (1-carry)
continue when high_result >= 0
```

The host oracle compares this byte/borrow calculation with ordinary unsigned
16-bit `counter >= target` for **all 65,536 counter values at each of the
17 published sync targets**: **1,114,112 comparisons**, all equal.
For example, the source's twist-scroller target is `$06D9` (1,753) and its
vertical-scroller target is `$3301` (13,057).

On PAL, a set `$D011` raster high bit represents lines **256..311**. The
source comment's informal reference to 255+ is not the exact register test.
This range selection is intended to avoid the music update's IRQ window;
the arithmetic check assumes coherent low/high reads and does not establish
that exclusion for every scene's actual interrupt schedule. It is also an
ordinary unsigned comparison, not a general modular deadline across counter
wrap. A music-call counter is not automatically a visual-frame counter.

## Reusing a tiny DISK entry

Common definitions put `DISK_BASE` at `$088F`. Its first byte is the part-done
flag, followed by `Entry` at **`$0890`**. Before leaving, a DISK script pushes
the high then low byte of `Entry−1`, allowing a later RTS to reach the new
entry at the same address. A host stack-byte model checks all 256 initial
stack-pointer values, including wrap, and restores both the expected PC and
stack pointer. This is RTS-address arithmetic, not original CPU execution or
an interrupt/stack-safety proof.

The specific No Bounds path adds a useful distinction to the article's
generic example: its DISK script pushes that return address and jumps to
the preloaded fade at **`$C000`**. The fade installs its own IRQ, calls the
loader for Trailblazer, waits for its transition-complete state, then returns.
The pushed address therefore leads into the replacement DISK entry after
the outgoing scene's code has been overwritten. IRQ ownership and safe
overwriting depend on the actual memory layout and execution order; the
stack calculation alone does not prove them.

## Sources, reproduction and open checks

[loading_sources.py](../../research/no-bounds/loading_sources.py) preserves
the article and thirteen source files at commit
`965807c511e2025b5c5e1ffb2a6235a4efd6ae5b`. Each file's size and Git blob hash
must match the immutable, non-truncated repository tree already acquired by
the [sprite-interleave investigation](sprite-interleave.md). Default mode
uses saved bytes; `--fetch` refreshes all routes and `--fetch-new` acquires
only newly listed ones. Acquisition does not run the downloaded C++ code.

```sh
rtk proxy python3 research/no-bounds/loading_sources.py
rtk proxy python3 research/no-bounds/inspect_loading.py
```

The [source receipt](../../build/research/no-bounds/loading-source-proof.json)
is SHA-256 `7156b089cbd263b2f57e8fe0dfd4191d33d0657d2adbfacd6a3d835be6f6f191`.
The [plan/arithmetic receipt](../../build/research/no-bounds/loading-plan-proof.json)
is `2c2b6b9d1a70c60e50bbe7b917184b1799ea7e3d10f82f53d410f437aff10d37`.
Both pass and retain source/script identities and complete modeled rows.

Remaining work includes source/build and original-disk matching, actual
loader/memory ordering, music-call spacing, IRQ publication and refill timing.
No full-demo frame rate, absence of loading gaps, real-drive margin or
historical priority is established by this bounded source analysis.
