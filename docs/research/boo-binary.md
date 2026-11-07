# Boo!: released BRR generator and drive selector

The released 4K PRG contains the five-cycle BRR interpolation template described
by Quiss, plus the drive-side rank selector at his published `$0401` address.
This investigation executed the original bootstrap and small RAM-only routines
with py65. It did not run the display, IEC protocol, drive ROM, music or raster
scheduling, and makes no native frame-time claim.

The primary references are [Quiss's article](https://www.quiss.org/boo/),
[his Python selectors](https://www.quiss.org/boo/bitreverse.html), and
[Boo!'s release entry](https://csdb.dk/release/?id=232949). The downloaded file is
[the linked PRG](https://csdb.dk/getinternalfile.php/246018/boo.prg), exactly
4,096 bytes including its load prefix, SHA-256
`4105eecdb5ee4e5927b22cc5afe029a1d14a0919d633cdf291460b94ec9b4920`.
Raw author bytes and generated disassemblies remain ignored build artifacts.

## CPU unpacking boundary

The BASIC stub enters at `$080B`. Original instructions save zero page to
`$CF00`, copy 256 bytes from `$1708` to zero page, construct a table at `$CE00`,
and jump to `$005E`. The copied processor-port values are DDR `$2F`, latch `$38`;
the decompression phase therefore selects RAM rather than mapped I/O/ROM.

The first stage finishes after **2,764,294 original instructions**, calling a
newly decoded RAM postprocessor at `$4D19`. That routine reconstructs code at
`$2000` using several source streams and an opcode-class table. Its return is
followed by the original `JMP $2A78`. The script stops there after **2,829,809
instructions**, before demo initialization.

No original PRG byte was patched and no I/O routine was mocked for unpacking.
The flat-RAM CPU model starts with zero RAM except the PRG, processor-port
defaults and a diagnostic SYS return address; A/X/Y are zero and arithmetic is
binary with carry clear. It does not reproduce BASIC or the whole C64 startup
environment. Hardware-visible I/O would stop the run. None was accessed.

py65 1.2.0 lacks two stable NMOS instructions used by this bootstrap, so the
harness adds `$89` immediate NOP and `$BF` absolute,Y LAX semantics. Selector
checks also add `$27` zero-page RLA. These definitions agree with the
[VICE CPU core's implementation](https://github.com/VICE-Team/svn-mirror/blob/main/vice/src/6510core.c).
The downloaded reference copy has SHA-256
`efa76d449fe628983b6a52b90ce4ba8b4dbc6973346f658388a1ac20a20fc6b0`.
The additions change the CPU model, not the program, and do not model every
undocumented instruction or hardware bus side effect.

The resulting full diagnostic RAM image has SHA-256
`5a2026b773fc66b41a1665a8b375aea929eec3f9b6ca9e0eb9fc3891e4925779`.
It is CPU-produced RAM, not a native emulator snapshot.

## The actual comparison convention

At C64 `$27A5`, the original seven-byte template is:

```asm
sta $fffe       // placeholders for the generated target address
cpx #$fd        // placeholder for the row's comparison constant
adc $16
```

The constructor at `$26CD..$26E8` reverses the bits of its row counter and adds
one. The copy loop at `$275D..$2784` substitutes that value and the destination
into generated cells. Thus the concrete cell is:

```text
STA target
CPX #(reverse8(row)+1)
ADC integerStep
```

X holds the rank separator, A the current interpolated position. Compare carry
is `X >= reverse8(row)+1`, which is exactly `reverse8(row) < X` without changing
the rank separator. This resolves the strict-vs-inclusive comparison question
left by the article's two-instruction sketch. A zero remainder can use separator
zero and the ordinary integer quotient.

The isolated original constructor and generated cells passed **255 row cases**
and **42,840 position/threshold/step/carry combinations**. Rows 0..254 were
checked; row 255 would wrap the incremented comparison byte and is deliberately
outside this assertion. No claim about the live renderer's full row-domain
selection is based on this isolated check.

The compare plus addition costs **five nominal CPU cycles**. Including the
absolute position store gives **nine**. This is a position-output cell, not a
measurement of the complete physical-pixel, polygon-fill or display work.
Threshold setup, entry/exit, generated-code construction, IRQs and VIC bus
contention are excluded.

## Reconstructed 1541 payload

The original C64 upload code opens an `M-E $0205` command containing a small
command-buffer receive stub. Its send loops supply 2,032 bytes. Their static
mapping is:

| C64 source, inclusive | Bytes | Drive destination, inclusive |
| --- | ---: | --- |
| `$3837..$3926` | 240 | `$0010..$00FF` |
| `$3927..$39AD` | 135 | `$0100..$0186` |
| `$2BDD..$3255` | 1,657 | `$0187..$07FF` |

The receiver starts partway through page zero, then fills the remaining pages.
The third C64 loop increments the **high byte** of its absolute,Y source operand
until it reaches `$32`. Treating that operand update as a low-byte increment
would reconstruct the wrong stream. The resulting payload starts with a jump
to drive `$0187` and places the selector at drive `$0401`, independently matching
the address stated by Quiss.

SHA-256 of reconstructed drive `$0010..$07FF`:
`b97be62ac0e610fbdd3686001bb22d211e71cd91c4f21a8a4e006e3cfe905a60`.
This is a static reconstruction from the sender/receiver addressing, not a
capture from a running 1541. The full drive program and transfer protocol were
not executed.

## Original selector checked against a mathematical oracle

The isolated drive routine takes start in `$34`, exclusive end in `$35`, and
rank in `$38`. It computes its separator in `$31`. CPU execution stops at `$047F`
before the surrounding routine consumes the result. The oracle is a plain sort
of independently generated bit-reversal values; it does not call the author's
Python selectors.

Results:

- **43,680 cases:** every rank for every endpoint interval
  `0 <= start < end <= 63`, the complete horizontal-coordinate domain of our
  current 64-pixel logical canvas.
- **12,259 additional cases:** byte-coordinate intervals, boundary lengths up to
  255, and deterministic random ranks, including lengths 171..173.
- **55,939 total cases:** every computed separator matched the order statistic.

An exclusive end of 256 is not representable by this byte-argument API and is
not included. Across these selected cases, the isolated routine used 32..143
instructions, 100..410 nominal CPU cycles. Those counts exclude the caller,
input setup and result consumption; their average over this test distribution
is not a live scene average.

## What this means for our renderer

The [host interpolation study](bit-reversal-lines.md) identifies a 12-cycle BRR
advance compatible with our current register allocation, grossing about 2,508
cycles per presentation before threshold setup. The actual released selector
can now be costed against those same 512 single-object poses.

Transposing its interval/rank inputs to our horizontal sampling, and bypassing
the existing `dx<=1` cases and zero remainders, gives 6,565 selector calls across
the period. Executing the original selector bytes for those inputs costs:

| CPU-cycle model | Mean per presentation |
| --- | ---: |
| Gross saving from our 12-cycle compatible advance | 2,508.12 |
| Original Boo selector alone | 3,021.04 |
| Gross saving minus selector alone | **−512.92** |

The selector averages 235.61 nominal cycles per call for this scene, and its
per-presentation total peaks at 3,761. Call/parameter/result overhead is still
unpaid. This model therefore gives no reason to replace our exact DDA with that
particular same-CPU combination.

It also explains why the two systems should not be compared using five cycles
alone: Boo! has the direct-store register arrangement and delegates preparation
to the drive. The ideal five-cycle advance from the host study grosses 4,123.95
cycles before setup, but fitting that arrangement requires different plotting
work. No drive-transfer cost, scheduling result, visual output or frame rate
has been established here.

## Reproduce and inspect

Use the same isolated py65 1.2.0 environment as the Tower research:

```sh
rtk proxy build/research/tower-power/cpu-venv/bin/python research/boo/unpack_6502.py
rtk proxy build/research/tower-power/cpu-venv/bin/python research/boo/inspect_binary.py
```

The scripts are tracked under `research/boo/`. Input remains the exact downloaded
`build/research/boo/boo.prg`. Outputs are ignored under
`build/research/boo/static/`, including:

- `bootstrap-execution.json` and the first-stage/postprocessed RAM images;
- `binary-analysis.json`, generated-cell and selector results;
- `drive-0010-07ff.bin` and explicitly reconstructed full-size drive RAM;
- focused generator, selector and upload disassemblies;
- the downloaded reference CPU-core source.

The inspection script reuses the repository's NMOS disassembly utility in
`research/tower-power/static_loader.py` and scene inputs in
`research/bit-reversal/analyze.py`; it does not edit or execute the renderer.
