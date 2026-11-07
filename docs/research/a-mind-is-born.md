# A Mind Is Born: 254 payload bytes, shared state and checked arithmetic

The pinned 256-byte PRG contains a two-byte load address and **254 payload
bytes**. lft's inline assembly reproduces all 194 unique instruction bytes in
its interrupt, startup and main-loop groups. The remaining header, initial
state, script and table bytes are individually annotated too. Original-CPU
checks confirm the LFSR, the complete finite music-control sequence and bounded
visual arithmetic. They do not emulate the SID/VIC/CIA, KERNAL or displayed
timing.

The later [native validation](a-mind-is-born-native.md) adds the original
startup/relocation, a complete captured IRQ transition, timer cadence and
native output observations. Its scope is distinct from these flat-CPU checks;
neither supplies an independent complete visual or audio oracle.

The primary source is [Linus Åkesson's complete walkthrough](https://www.linusakesson.net/scene/a-mind-is-born/index.php),
including its assembly fragments and [original PRG](https://hd0.linusakesson.net/files/a_mind_is_born.prg).
The author identifies the work as the winner of Revision 2017's Oldskool 4K
competition; the compo category does not change its 256-byte file size. His
page labels the work [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
Raw author copies and the complete derived listing remain ignored artifacts.

## Source-to-byte comparison

Input: `build/research/frontier/a_mind_is_born.prg`, SHA-256
`7da29c8eed5acc39c5a1d3f0d40f5057c516cb6d2a04a18b15d71e6f8903f1f5`.
It loads at `$0801` and occupies `$0801–$08FE`. The BASIC text invokes decimal
2225 (`$08B1`). At that address, the high operand byte `$EA` of the preceding
IRQ-tail jump is also an executed `NOP`; startup proper follows at `$08B2`.

`research/a-mind-is-born/source_bytes.py` parses all eighteen preformatted blocks
from the archived author page. A restricted assembler handles their literal
instructions and expressions, resolves the declared labels and verifies each
locally declared label address. The comparisons are:

| Source group | Bytes compared | Detail |
| --- | ---: | --- |
| Interrupt body | 129 | Relocated `$0031–$00B1`. |
| Startup | 27 | Loaded `$08B1–$08CB`, including the shared `NOP`. |
| Main visual code | 39 | Relocated `$00CC–$00F2`. |
| Unique instruction bytes | **194** | Startup/IRQ share one byte. |

This checks the author's assembly against the released bytes, rather than
transcribing a disassembly and comparing it with itself. Data and absolute
symbol locations are supplied explicitly; it is not a recovered standalone
author build system. `payload-annotated.txt` and `source-byte-proof.json` map
**every payload byte** to file offset, loaded address, nominal relocated address
and overlapping roles. The HTML snapshot SHA-256 is
`8c39d10fd5329369dec5ee2cde1db6cad49d616d7d7f20e3cdc67490bca00668`.

One literal discrepancy remains visible: the pinned PRG's BASIC next-line word
is `$080D`, while the prose calls it `$080B`. The null end marker is at
`$080B/$080C`. The machine-code groups all match; no byte is silently corrected.
This investigation does not execute the BASIC interpreter or infer which
revision explains the prose/header discrepancy.

## Relocation and lifetime reuse

The original copy loop executes 1,015 instructions from `$08BC` through its
jump to `$00CC`. It copies 252 loaded payload bytes from `$0803–$08FE` into
`$03–$FE`, then also reads `$08FF` into `$FF`. That final source byte lies just
beyond the loaded file and is unconstrained here. `$00–$02` are preserved.
The `$FF` destination becomes the script's dummy-write slot, overwritten during
the first music tick. This is more precise than saying every payload byte is
copied into zero page.

The important reuse is semantic, not just nearby storage:

| Relocated bytes | Simultaneous or successive roles |
| --- | --- |
| `$03/$04 = $D3FF` | BASIC line number becomes the indirect SID-copy base. |
| `$0A–$22` | Twenty-five SID shadow bytes; partly overlaps BASIC termination and the script. |
| `$0F/$10 = $D01C` | Two voice-1 envelope values also form the indirect VIC-copy base. |
| `$11–$15` | Palette shadow, overlapping melody pitch, pulse width, LFSR and waveform. |
| `$13/$20` | Split clock low/high bytes also control melody pulse width, palette and filter cutoff. |
| `$14` | LFSR state, melody pulse-width high byte and a palette entry. |
| `$21–$30` | Eight poke pairs; first pair also configures SID filter routing/resonance and volume. |
| `$CB/$CC` | Visual pointer low/high reuse the initialization jump's zero operand and the already-executed first main opcode. |
| `$D5` | Script-selected `LDY`, `BIT` or `AND` opcode also supplies the final screen-code OR mask. |
| `$D7` | Envelope operation changes from `ORA` to `ADC` in the final bar. |
| `$0100–$01FF` | Cyclic `PHA` output supplies font bytes while IRQ entry/exit also uses the stack. |

The normal bass path executes `AND $00AB`. A branch instead enters its operand
at `$72`, interpreting `$AB,$00` as immediate `LAX #0`. Meanwhile `$AB` holds
the constant 3 because it is an indirect-store operand elsewhere. The zero
operand matters: the checker does not pretend generic immediate LAX has one
portable deterministic result.

## LFSR and finite music control

The melody update uses the NMOS `SRE` combination, which shifts the memory byte
and XORs it into A. With `s` the old state, the independently checked recurrence
is:

```text
s' = (s >> 1) XOR ($B8 if s & 1 else 0)
noteIndex = s' & 7
```

The accumulator is initially `$B8`, even when the shifted-out bit is zero;
the conditional store keeps only the shift in that case. Its low three bits
still equal `s' & 7`, because `$B8` has zero low bits. All 256 states and both
incoming carries match original CPU execution. Every nonzero seed has period
255 and visits every nonzero byte; zero is absorbing. Across one complete
nonzero cycle, index zero occurs 31 times and each other index 32 times.
This period does not describe the whole song, whose script repeatedly reseeds
the register with `$41` during bars 8–15.

The complete control run starts with the released shadow state and increments
the split clock by two per handler call. An independent host model agrees with
all 8,192 calls: 8,191 reach the KERNAL tail, while the last reaches the reset
branch at bar `$40`. It checks **204,775 literal SID writes** and **73,719 literal
VIC writes**, plus all zero-page mutations. There are **1,023 melody updates**
before exit; the initial partial bar does not include an extra update at clock
zero. The model covers the mute bar, script writes, final filter/opcode change,
drum ramp, bass words and LFSR reseeding.

The bass table packs each frequency's high two bits into its low byte. Its
four reconstructed words are `$032B,$02AA,$0202,$0262`; the drum replaces the
high byte while retaining the chosen low byte. The melody table supplies only
frequency high bytes, with a zero first entry. These are register arithmetic
facts, not an audio-spectrum or tuning measurement.

The author describes a 60 Hz timer, 112.5 bpm and a 64-bar song. The program
inherits its interrupt service from the existing system; it does not install a
new timer period. The handler-call count is verified here. Its conversion to
wall-clock duration, SID envelope behavior, hard-sync and combined-waveform
sound remains dependent on the actual machine and startup environment.

## Visual arithmetic and font addressing

The main loop reads CIA timer low byte `$DC04` and SID voice-3 envelope `$D41C`.
Those are live chip inputs in the demo and controlled byte fixtures in this
analysis. The generated font byte is either timer OR envelope, masked-timer OR
envelope, or the corresponding addition with inherited carry after the final
opcode change. Original execution agrees for **786,432 cases**: all timer and
envelope bytes, both incoming carries, all three first opcodes and both envelope
opcodes. `PHA` writes the result into the wrapping stack.

The following `ALR/ASR #$04` is **AND followed by logical shift right**, not a
signed arithmetic shift. It leaves a small random seed, 0 or 2, and clears
carry. Two indexed reads, a low-pointer increment, two ADCs and a ROR then
combine neighboring screen values. Independent arithmetic models both ADC
carries and the ROR carry-in, rather than substituting an ordinary average.
All **131,072 neighbor-pair cases** pass, varying pointer pages/low bytes,
clock-bar values and opcode masks, including 512 low-pointer-wrap cases.

The byte ORed into each stored screen code always has bit 5 set. Thus the
lower six ECM character-index bits select only glyphs 32–63: exactly font
addresses `$0100–$01FF`, the stack page. The stored byte is always nonzero,
proving why the final `BNE` returns to the main loop in these arithmetic paths.
`$D018=$30` selects screen `$0C00` and font `$0000` in the assumed default VIC
bank zero; `$D011=$50` selects ECM with zero vertical scroll. Color RAM is prepared black by startup, so one bits in
the generated font are dark and zero bits expose the chosen ECM background.

Only the pointer low byte advances in the main loop. At its wrap, the two read
addresses are not consecutive linear addresses; IRQ changes to the high byte
can also interleave with them. Initially the pointer is `$A900`, producing dummy
high-memory accesses before the interrupt selects pages `$08–$0F`; those initial
accesses are outside the neighbor fixture's stated page domain. The original payload at `$0801` is part of the
initial pattern seed, but higher workspace RAM, timer phase and SID envelopes
also influence the developing image. A single uninterrupted-update proof is
not a deterministic full-screen replay or a visual frame-rate result.

## Startup and hardware boundaries

Execution assumes the BASIC/SYS environment supplies X=0 for the first color
writes, normal I/O/ROM banking, default VIC bank zero, a usable KERNAL screen-clear
routine at `$E544`, the existing CIA interrupt service, and the usual IRQ vector
low byte `$31`. Startup clears only the vector's high byte. The main loop enables IRQs;
the handler eventually jumps to `$EA7E` to acknowledge/restore/return through
the KERNAL. The checker supplies that vector-low precondition for the isolated
copy loop and stops before executing ROM tails.

At the end, the program shifts `$D011` and jumps through `$FFFC`. This is a
software jump to the reset vector, not a processor RESET-pin event. The familiar
shutdown and eventual BASIC screen described by the author require the ROM;
they are not bytes stored in the 256-byte file. No ROM, asynchronous interrupt,
SID/VIC/CIA, undocumented bus side effect or native display is emulated here.
The initial file size is therefore not the runtime memory or hardware budget.

## Reproduction and receipts

```sh
rtk proxy python3 research/a-mind-is-born/source_bytes.py
rtk proxy build/research/tower-power/cpu-venv/bin/python research/a-mind-is-born/validate_arithmetic.py
```

The [research README](../../research/a-mind-is-born/README.md) identifies inputs
and dependencies. `build/research/a-mind-is-born/` holds the author snapshot,
`payload-annotated.txt`, `source-byte-proof.json` and `arithmetic-proof.json`.
The CPU model adds explicit stable NMOS `LAX`, `ALR`, `SRE` and `AXS` behavior,
with immediate LAX restricted to operand zero. These are local arithmetic
checks, not a native playback or sound/cadence proof. No VICE process, production
renderer or commit was created by this investigation.

The instruction additions were also checked against the [official VICE CPU core](https://github.com/VICE-Team/svn-mirror/blob/main/vice/src/6510core.c),
using the already archived reference SHA-256
`efa76d449fe628983b6a52b90ce4ba8b4dbc6973346f658388a1ac20a20fc6b0`.
The arithmetic definitions agree; RMW dummy writes and chip-bus behavior remain
outside the flat model.
