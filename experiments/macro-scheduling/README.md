# Raster continuations and cooperative frame waits

A standalone PAL C64 example with four raster-colored border bands and a
two-phase scene sequence. The background alternates green and blue every 100
PAL frames, about two seconds. The screen shows the current scene number.

```sh
sh build.sh
sh run.sh
python3 verify.py
```

The shared builder uses the installed Kick Assembler and writes
`build/example.prg` plus symbols. The launcher selects PAL at normal speed.

Each raster IRQ saves the registers, then jumps through a continuation pointer.
`WaitRaster` saves the next segment's address, schedules the next raster line,
and returns from the IRQ. The sequence reaches lines 0, 64, 128 and 248 once
per frame. This is line scheduling, without cycle stabilization or nested IRQs.

At line 248, one scene call runs. `WaitSceneFrames` stores a continuation and
a countdown, then returns to its caller. Later calls decrement the countdown
without blocking the IRQ chain. When the count expires, execution resumes
after the wait. Both waits in the example use the same mechanism.

The public technique comes from [Trident's anonymous IRQ/protothread
example](https://github.com/trident64/c64/blob/80d1027742815e55cda13a80cb4826744dd75c83/anonymous-irq-handlers-example.s).
This folder contains an independent implementation with explicit machine
initialization and visible scene state. No original source is copied. See the
[research note](../../docs/research/macro-scheduling.md) for the original
example's separately checked behavior and attribution boundaries.

This example demonstrates scheduling. It does not reproduce a released demo
effect, make waits cost no CPU time, or establish safe publication for arbitrary
shared scene state.

## Native verification

A bounded VICE PAL run checked all 205 consecutive completed frames. The scene
counter and phase matched on every frame; the green-to-blue transition occurred
at frame 101 and blue-to-green at frame 201. Sampled screen digits and VIC colors
matched each phase. Three unfiltered screenshots showed the text, four border
bands and changing background. The owned emulator process exited after capture.

The generated [receipt](build/verification/receipt.json),
[monitor transcript](build/verification/monitor.log) and
[phase animation](build/verification/scenes.gif) remain under ignored `build/`.
This run checks the visible sequence and frame countdown, without claiming
per-cycle raster timing or physical-hardware validation.
