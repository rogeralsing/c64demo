# Trident's assembler macros: anonymous IRQs and protothreads

Trident's Fjälldata 2025 talk and accompanying Kick Assembler example show how
macros can express a demo's timeline as sequential source while generating
ordinary 6502 code. This complements loop unrolling: the scheduling macros
organize when effects run, while generated/unrolled kernels determine their
inner-loop cost. Neither technique makes the expanded instructions free.

The inspected sources are pinned to Trident's repository commit
`80d1027742815e55cda13a80cb4826744dd75c83`:

- [Original standalone example](https://github.com/trident64/c64/blob/80d1027742815e55cda13a80cb4826744dd75c83/anonymous-irq-handlers-example.s).
- [Original 36-slide talk](https://github.com/trident64/c64/blob/80d1027742815e55cda13a80cb4826744dd75c83/trident%20-%20fj%C3%A4lldata%202025%20slides.pptx).

The talk's general-purpose illustrations and the standalone executable are
separate artifacts. The proof below assembles the standalone source unchanged;
it does not assemble every slide excerpt, identify those bytes in a released
demo, or establish a native raster result. Ordered slide XML text is retained
as a reading aid, not a spoken-video transcript or rendered-slide inspection.

## An IRQ wait installs the continuation

The example's `irq_set` emits stores of a continuation address to `$fffe/$ffff`,
the next raster's low byte to `$d012`, and its high selection bit to `$d011`.
`irq_wait` selects a macro-local `next` label, acknowledges the IRQ with
`INC $d019`, and executes `RTI`. The next interrupt starts at that label,
immediately after the wait in the source.

There is no runtime search through handler names or high-level interpreter.
The expanded instructions perform the same vector and register updates that
handwritten handlers need. The talk's overhead claim concerns this organization;
the hardware IRQ entry, acknowledgement, register work and return still cost
cycles. Exact raster effects still need their own synchronization and DMA
analysis.

The standalone source cycles through four border colors. Its handler entry
points are `$083f`, `$0861`, `$0883` and `$08a5`; the requested raster sequence
is `$00`, `$40`, `$80`, `$f8`, then `$00` again. The final handler calls the
separate scene sequence once per completed chain.

This is an inline continuation technique. Expanding an `RTI`-based wait inside
an ordinary `JSR` helper would leave that helper's return address above the IRQ
frame. Registers and an ordinary call stack are not persistent local variables
across a wait. Keep persistent effect state in RAM and define the register and
stack contract at each continuation.

The standalone program interrupts an idle `JMP` loop and does not save A/X/Y.
That is compatible with this example's caller; it is not a register-preserving
IRQ wrapper for an arbitrary foreground renderer. The talk separately presents
save/restore macros, including `$01`, which are absent from this small source.

## A frame sequence stores its own resume address

The sequence enters through `JMP ($090c)`. Each `pt_wait_ticks` expansion:

1. Clears its own counter, stored in an immediate operand.
2. Stores the address of its local polling label in the two-byte continuation
   pointer.
3. Compares that counter with the requested tick count.
4. Increments and returns while waiting; otherwise falls through to the next
   scene operation.

The next `JSR sequence` jumps straight to the waiting label, skipping its
initialization. This is cooperative scheduling with code and RAM state, not a
second CPU thread. The small implementation has one-byte counters and writes
its code operands. It needs writable code and independent state for independent
instances; recursive or concurrent calls would share those operands.

Here both waits request 100 ticks. The first color change occurs on invocation
101: the first invocation initializes and advances the counter, and invocation
101 observes the completed count. Subsequent color changes occur exactly 100
invocations apart. The repeatable source resets each counter when its wait is
entered again. Describe the invocation convention explicitly before treating
the first event as an off-by-one bug.

`ticks` means calls of this sequence. It becomes PAL seconds only when the
caller supplies the intended cadence. This standalone proof does not establish
that hardware cadence, an NTSC conversion or the timing of the talk's larger
demo examples. Child-sequence and condition-wait macros mentioned in the talk
are also not present in the executable inspected here.

## Bounded original-code checks

The [acquisition script](../../research/macro-scheduling/acquire.py) saves the
unchanged source, original PPTX, Git tree, HTTP provenance and SHA-256 hashes
under ignored `build/research/macro-scheduling/`. Git blob identities are
checked against the pinned tree. The source is 1,144 bytes, SHA-256
`caa3e48260562636ae1d47c6c3ba18b079b42948666253f41a8ff00dc49b0cee`.
The original PPTX is 11,811,341 bytes, SHA-256
`3ad6014bfdb1116d80b2eed5923f8d20902731fcb33b9559bc34bc3aef9369c4`.

The [validator](../../research/macro-scheduling/validate.py) uses the existing
research environment's py65 1.2.0 and Kick Assembler 5.25. The unchanged source
assembles into a 271-byte PRG with SHA-256
`cdf44a52986ba87ff9849fd727426321485db7943a558c6c12a5dce91a955c16`.

```sh
rtk proxy python3 research/macro-scheduling/acquire.py
rtk proxy build/research/tower-power/cpu-venv/bin/python research/macro-scheduling/validate.py
```

For **1,001 sequence calls**, an independent host counter model matches all
65,536 physical RAM bytes after every return, plus every literal I/O write.
The comparison includes the self-modified counters, continuation pointer and
caller's stack return bytes; no RAM addresses are excluded. Ten background
writes alternate colors 5 and 6 at invocations 101, 201, through 1001.

| Path | Calls observed | Nominal CPU cycles including caller's JSR |
| --- | ---: | ---: |
| Already waiting | 990 | 29 |
| Initial entry | 1 | 47 |
| First color transition and next wait | 5 | 60 |
| Second color transition, loop and next wait | 5 | 63 |

These counts include the indirect jump, counter polling, code writes and RTS.
They exclude VIC DMA, IRQ entry, surrounding raster handlers and hardware
timing. They are not whole-frame measurements.

A separate check runs original startup and injects **16 synthetic IRQ entries**,
covering four complete handler chains. All scheduled vectors, literal border
and raster-register values, IRQ acknowledgements and stack returns match the
source-derived expectations. Explicit fixed register fixtures supply reads.
The CPU model does not reproduce VIC raster progression, pending-IRQ timing,
RMW dummy writes or the acknowledgement bus sequence. No VICE session is
started by either script.

## Transfer to this project

The useful transfer is a readable scene controller around measured assembly
kernels. A macro can instantiate clear/fill bodies or timed register sequences
at assembly time; a continuation pointer can sequence effects between frame
updates. These solve different costs and combine without requiring a runtime
language interpreter.

Our renderer's buffer/field history, frame publication and IRQ ownership still
need explicit state. A yield cannot conceal a missed raster deadline, make a
long computation fit inside one frame, or preserve registers that the expanded
code overwrites. The [Nine investigation](nine.md) and
[technique map](technique-map.md) provide concrete examples of generated kernels
whose timing and memory contracts remain separate from their source-level
organization. No production renderer changes accompany this research.
