# Relax #24: reader wrapper and the first strict boundary

Research date: 7 November 2026. This is a bounded, file-derived inspection of the original reader recovered in [the archive note](relax24-archive.md). **The reader has not yet been decompressed, and no original article has been decoded or identified as the coding review.** This checkpoint preserves the useful decoder structure without substituting hardware values to force completion.

## Original input and entry

The 31,211-byte PRG has load address **`$0760`** and establishes bytes through `$8148` inclusive. Its SHA-256 is `ea9040469d211c87cdfd1aaa2a5eca04685be741d679bc1537cb7cc280810180`. The owning archive proof remains unchanged at `0c68892c3a73cdeda0854eaa28db205672a9b02ed3f04ce185dbda72ad656fac`.

At `$0801`, BASIC line 1993 contains the tokens for **`SYS pi*656`**. Conventional integer truncation gives **`$080C`**, where the original bytes begin `LDY #0 / SEI / INC $D030`. This is a static entry interpretation, not execution of BASIC ROM or a native entry observation.

The strict CPU check executes exactly **two original instructions**, four nominal cycles, then stops at **`$080F: INC $D030`** on its attempted hardware-address read. It supplies no I/O value and performs no later CPU instruction. The following code also touches `$D011/$01`, so a file-only bootstrap cannot simply continue as flat RAM.

## The literal copies are completely file-established

The original copy operands define:

| Source, inclusive | Destination, inclusive | Bytes |
|---|---|---:|
| `$7F52..$8051` | `$0340..$043F` | 256 |
| `$8048..$8147` | `$0723..$0822` | 256 |

Every source byte is present in the file. Unlike an unknown-padding case, no bytes need to be invented to inspect these relocated instructions and tables. The inspector constructs these copies separately, **conditionally**, rather than executing past the startup hardware stop. It does not call that constructed state an initialized or decompressed reader.

The [file-derived instruction listing](../../build/research/relax24/reader-analysis/file-derived-wrapper.txt) ends at the last wrapper instruction, `$0435: RTS`. The following table bytes are not disassembled as code.

## Instruction-derived bit/LZ format

These are static format findings from the copied original instructions. No complete decompression run is claimed.

| Role | Original address/state |
|---|---|
| Literal/match loop | `$0352` |
| Read X bits | `$03CA` |
| Buffered byte | `$078A`, initially `$1E` |
| Remaining-bit immediate | `$03D4`, initially 6 |
| Source-pointer operand | `$03E8/$03E9`, initially `$7F51` |
| Output-byte helper | `$040D` |
| Destination operand | `$040E/$040F`, initially `$A0DF` |
| Table-coded length helper | `$041C` |

Bits are read **MSB first**, while input bytes are fetched backward. A refill decrements the source before reading it, so the first refill is `$7F50`. The initial buffer supplies six bits before that refill. Reading zero bits returns zero. The result is accumulated in `$FD:$FC`, with A and X receiving the low byte.

The length helper counts zero bits until a one. Literal selection starts with Y=`$FF`; match selection starts with Y=`$1F`. It then uses separate stored bit-width/base tables, returning the **8-bit** sum. A set selector bit 4 selects the exit path. This is not a generic unbounded gamma decoder.

Literal count zero skips the literal run. For a match, `fb=(length-1)&255`; offsets use four direct bits for length one, two class bits for length two, or three class bits plus four otherwise. Distance classes index the stored width/base tables. Class four or above with decoded offset zero escapes to class twelve.

For ordinary nonzero lengths, the copy behaves as backward LZ with distance `offset+1`. The exact source recurrence is:

```text
fb   = (returned_length - 1) & 255
base = (destination + offset - fb) & 65535
y    = (fb + 1) & 255

read RAM[base+y], write RAM[destination], decrement destination
y = (y-1) & 255
repeat until y==0
```

**Returned match length zero is a special wrap case:** it performs 256 stores, but its first Y is zero, so its first source address differs from the simple `destination+offset+1` rule. A future decoder must preserve that behavior or prove the case absent in the actual stream. It must also retain overlapping mutable-RAM semantics and reject every unestablished compressed or back-reference read.

## Hardware wrappers remain outside any pure format model

The loop returns through **`$0349..$0351`**, which decrements `$01`, masks A for a border-color store at `$D020`, then increments `$01`. The next DEY at `$0352` is part of the decoder's length setup and must not be dropped with those side effects.

The exit at **`$03FE..$040C`** restores `$01`, decrements `$D030`, writes `$D011` and jumps to `$0801`. That handoff is source-derived; it has not been reached by this CPU check.

A pure format transcription could explicitly exclude those wrappers, with its own declared entry/state and known-memory checks. It would establish decoded bytes only, not the original port, raster, border or complete bootstrap behavior. This checkpoint does not silently skip the instructions and label the result original CPU execution.

## Side-2 observations and open article question

All 21 extracted side-2 files are rechecked against the archive proof. **Twenty** have a first big-endian word equal to their file length minus five; the exception is `00`, whose body begins with a BASIC-style wrapper. This is a raw container relation, not proof of a five-byte article header, load address or shared compression format. The owning reader consumer still needs to be identified.

No file is assigned to Clarence's coding review by its two-letter name or an incidental byte-string match. The cached web transcription remains unvalidated against original magazine text. No wholesale article text is copied into this note.

## Reproduce the checkpoint

```sh
rtk proxy build/research/tower-power/cpu-venv/bin/python research/relax24/inspect_reader.py
```

[inspect_reader.py](../../research/relax24/inspect_reader.py) pins the archive/source, records the strict startup stop, constructs only file-established copy references, exports all decoder tables and records every side-2 header observation. Its [receipt](../../build/research/relax24/reader-analysis/reader-proof.json) is deliberately scoped to those findings. The original archive proof, containers and acquisition script are not changed. No native process, emulator, hardware mock or downloaded host program is run.
