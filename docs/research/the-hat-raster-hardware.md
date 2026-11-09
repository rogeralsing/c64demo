# The Hat: pinned x64sc register rules and retained draw pipeline

Research dates: 8–9 November 2026. This new, passive layer binds the register
rules needed by the B8/B9 upscroll to the official VICE 3.10 source. It also
decodes the complete draw-pipeline and retained framebuffer portion of the
closed native02 VIC-II snapshots. It does **not** advance a CPU, VIC cycle,
sprite renderer or pixel compositor. Register arithmetic is one input to
that later work; it is not a substitute for the internal state and actual
read/write chronology.

The [producer and reusable data helpers](../../research/the-hat/raster_hardware.py)
read the pinned VICE archive and frozen snapshot helper. All older source,
proofs, docs, native evidence and baseline files remain unchanged. The
[source-descriptor note](the-hat-raster-source.md) owns original B8/B9 macro
ordering. The [native02 note](the-hat-upscroll-native.md) owns the closed
machine case used here as declared snapshot context.

## Primary source and actual chip model

The only upstream implementation source is:

```text
vice-3.10.tar.gz
8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1
```

The acceptance records **25 source files**, their hashes, exact textual
guards and line-numbered excerpts. The x64sc source path matters:

```text
x64sc → c64sc library → c64/c64cpusc.c
       → mainc64cpu.c → 6510dtvcore.c
```

The shared core filename contains “dtv”, but `c64cpusc.c` defines
`SKIP_CYCLE=0`; this is the source path used by x64sc. The separate
`c64/c64cpu.c → maincpu.c → 6510core.c` path is not used as the instruction
source for this acceptance.

All **19 native02 snapshots actually store model 1**, the viciisc enum
`VICII_MODEL_8565`. The guarded model definition selects MOS8565, 63 clocks
per line, 312 lines, the PAL cycle table and **zero color latency**. PAL
does not by itself select the older 6569 model. The distinction matters to
the draw-color and sprite multicolor pipeline branches even when ordinary
register rules agree.

## CPU-visible values and register storage

The new helper `vic_register_read(regs, address, raster_line=None)` supports
only the source-used stable classes and explicitly supplied live raster
reads. The caller must establish that CPU I/O is mapped at the address.
Unsupported light-pen, collision or IRQ reads reject.

| Register class | CPU read rule |
| --- | --- |
| Sprite X-low/Y, `$D010`, enable/expansion/priority selectors | Stored byte |
| `$D011` | Stored bits 0–6 plus **actual raster bit 8** in bit 7 |
| `$D012`, including `$D112` | **Actual raster low byte** |
| `$D016` | `stored OR $C0` |
| `$D018`, including `$D118` | `stored OR 1` |

The stored `$D012` compare byte cannot substitute for a live raster read.
The helper requires a declared raster input for `$D011/$D012`. A trace
hook's later beam position is not silently substituted for the read-cycle
sample. The typed source consumer may instead accept a bound, actually
loaded LDY value as external input.

`vic_register_write(regs, address, raw_value)` returns a new logical
register array. Source-used X/Y, `$D010/$D011/$D012`, `$D015..$D018` and
sprite selector registers retain the written byte. In particular,
**`$D018` retains written bit 0**, even though reading it forces that bit
high. Colors `$D020..$D02E` retain only the low nibble. The raw CPU write
value remains separate for event comparison.

This logical write helper does not update cached sprite X, ysmooth, IRQ
comparison, DMA, border or color pipelines. The real device store may do
those additional things; their omission is an explicit layer boundary.

The device masks the address to six register bits. Thus `$D111`, `$D112`
and `$D118` select register `$11`, `$12` and `$18`. The CPU I/O dispatcher
registers the VIC mirror range through `$D3FF`. Address aliasing alone does
not establish the CPU-port/cartridge mapping that makes a particular
access reach this device.

## RMW arithmetic and stable SAX stores

For NMOS INC/DEC, the source core reads a byte, writes that **read byte** on
the dummy-write cycle, then writes the changed byte. For `$D016`, the
dummy byte can differ from the byte previously stored in the register:

| Stored `$D016` | Operation | Read/dummy write | Final write |
| --- | --- | --- | --- |
| `$88` | DEC | `$C8` | `$C7` |
| `$88` | INC | `$C8` | `$C9` |
| `$C7` | INC | `$C7` | `$C8` |

The producer enumerates all 256 starting bytes and both operations:
**512 complete read/dummy/final transformations**. Source `STX $D016`
with X `$88` stores `$88`; a following DEC reads `$C8`, not `$88`.

Sprite X arithmetic is different. INC/DEC on `$D000/$D002/.../$D00E`
changes the **low byte only**; it does not carry into or borrow from
`$D010`. The cached X is recomputed as the changed byte plus that sprite's
existing high bit. Therefore X 256 decremented through its low-byte
register becomes **511**, not 255. The finite certificate covers every
sprite, every high-mask byte, every low byte and both directions:
**1,048,576 cases**.

Opcode `$8F` is the stable NMOS absolute SAX store in the actual core:
`ST(A & X, SET_ABS, 3)`. It performs one ordinary store, with no RMW dummy
write. All 65,536 A/X pairs are checked as a finite bit transformation.
The source agent's B8/B9 descriptors independently bind the eleven
`SAX $D111` sites to literal A `$F0` and X `$88`, hence an actual written
byte `$80` to mirrored `$D011`. Keeping A's source origin is necessary;
the value is not inferred from a final screen image.

## Nominal pointer and image addresses

At the sprite-pointer fetch, the source computes:

```text
screen offset = (D018 AND $F0) << 6
pointer byte  = bank + screen offset + $3F8 + sprite
image byte    = bank + pointer*64 + internal MC
```

For bank `$4000`, `$D018=$00` selects screen `$4000` and pointers
`$43F8..$43FF`; `$D018=$10` selects screen `$4400` and pointers
`$47F8..$47FF`. The certificate checks all four nominal banks, all 256
`$D018` bytes and all eight sprites: **8,192 address cases**. Character
base is nominally `bank + ((D018 AND $0E) << 10)`.

The actual fetch first applies its phi-specific bank, address mask and
offset, then possible character-ROM/cartridge rules. The nominal helper
does not replace those mappings. The VIC snapshot writer explicitly says
that phi-bank and mapping fields are restored from elsewhere, so they
must be bound from the rest of the machine context when needed.

Writing a pointer-table byte does not retroactively change a pointer
already fetched into `sprite[i].pointer`. Likewise fetched image bytes
first enter `sprite[i].data`, then a separate draw-stage shift register.
Both pointer tables, their actual fetch order and the initially latched
pointer/data state matter to composition.

## Y writes, DMA and expansion

The Y-register store changes the compare byte. It does not directly reset
the sprite's row counter. At the source's named DMA-check events, a sprite
starts only when it is enabled, its Y equals `raster_line AND $FF`, and its
DMA bit was previously clear. Start sets the DMA bit, `mcbase=0` and
`exp_flop=1`. **638,976 finite predicate/state cases** cover both enable
and DMA values, all Y bytes, every PAL line and two prior counter/flop
patterns.

Other source events copy MC to MCBASE when the expansion flop permits it,
clear DMA at MCBASE 63, toggle the flop for enabled Y expansion, and set
display bits at the separate display check. `$D017` changes can also have
a special crunch effect at a particular cycle. The B8/B9 source contains
no `$D017` writes in its raster body, but a full model still needs the
initial DMA, MC, MCBASE, pointer, image data, display bits and expansion
flop. A register-only “21 rows from Y” description loses these states.

## DEN and border latches

A `$D011` store records the byte, ysmooth and raster-IRQ compare bits. It
does not directly reset all border state. The source's top comparison can
clear `vborder` and `set_vborder` only at line `$33` or `$37`, selected by
RSEL, with DEN set. Bottom comparison sets `set_vborder` at `$FB` or `$F7`.
Other events transfer that latch, while the horizontal comparisons use
CSEL from `$D016` to update `main_border`.

Consequently, clearing DEN is not an immediate “turn the whole display
black” command. Existing border latches and the timing of later comparisons
remain relevant. The pure `border_top_event` helper describes only that
one named source event; it never schedules subsequent cycles. The finite
domain confirms that DEN clear preserves its prior top-event latch pair.

The source also latches bad-line permission, uses delayed `$D011` bits for
some fetches, and pipelines border/color decisions. Changing a final
register byte cannot reconstruct an earlier scanline.

## Store hooks are not physical write timestamps

The x64sc core's RMW path contains two actual device stores separated by
`CLK_INC`, and `SKIP_CYCLE` is zero. The monitor's **dummy-access checkpoint
coverage defaults off**. With that setting, dummy stores still reach the
device but bypass the ordinary watcher. The read-only monitor command
`dummy` reports the coverage setting; `dummy on` changes observer coverage.

The monitor queues watched addresses and checks them later in the CPU
monitor path. Therefore attached register rows can show post-instruction
or IRQ-entry context. With dummy coverage enabled, two queued hits still
do not by themselves provide two physical write timestamps or values.
The future composition layer must expand source-defined dummy/final
chronology using explicitly declared timing inputs; it must not label a
post-store hook clock as every underlying bus-write clock.

## Complete retained snapshot-tail decoding

The frozen [core reader](../../research/quondam/snapshot_state.py) remains
unchanged. The new `read_extended_snapshot(path, border_mode=None)` first
runs it, preserves every returned core field exactly, then decodes this
guarded layout:

| VIC-II 1.3 payload range | Bytes | Meaning |
| --- | ---: | --- |
| `0..1880` | 1,881 | Existing frozen core schema |
| `1881..2054` | 174 | Draw pipeline |
| `2055..2070` | 16 | Raster current line, width, height, pitch |
| `2071..123414` | 121,344 | Padded framebuffer allocation |

The accepted bound is C64SC/VICE 3.10, **VIC-II version 1.3, model 1,
123,415 payload bytes, width 384, height 312, pitch 384**. Unknown variants
reject. The exact ordered C snapshot-writer fields are checked against
the declarative decoder list. Each 174-byte decoded pipeline is re-encoded
and compared with every original byte.

The added draw state includes the graphics buffer stages and mode pipes;
eight delayed sprite-X values; sprite priority, multicolor and X-expansion
bits; pending, active and halt masks; eight sprite shift registers and
current pixel bytes; X-expansion and multicolor flops; border state;
render/priority/pixel buffers; delayed color registers; and delayed cycle
flags. These values are necessary alongside the old core's DMA counters,
pointer/data latches and border state. They are decoded, not advanced.

The raster allocation is **384 × (312+4)** bytes. There are two padding
rows before and after the 384×312 unpadded byte image. Its unpadded start
is payload offset **2,839**, with **119,808 bytes**. Both padded and
unpadded hashes are retained. `framebuffer_bytes(path)` returns those
unchanged unpadded bytes without assigning them a frame generation.

For actual PAL normal-border resource 0, the guarded SC constants give
left/right widths 32, visible raster rows **16..287**, and a **384×272**
viewport. The cycle line-buffer copy starts at `17*8-leftwidth`, or 104.
Framebuffer `(0,0)` is the unpadded allocation origin; its row is the
raster line, not the viewport's cropped row. Graphics origin is `(32,51)`.
The optional `border_mode=0` argument is a declared external resource
value that the caller must bind to an actual query. Native02 never made
that query, so its acceptance leaves the viewport as a conditional source
contract. Model 1 itself is read directly from every snapshot.

The line buffer accumulates while the beam advances. At line end,
`vicii_raster_draw_handler → raster_line_emulate` commits displayed
viewport rows to the canvas, then advances/wraps `raster.current_line`.
Out-of-viewport rows may remain old or initial; a partially accumulating
line is not a freshly committed canvas row. A snapshot at beam wrap must
therefore retain the first/new-line boundary and viewport lifetime. It
cannot label all 312 stored rows as the just-finished field.

## Remaining inputs for composition

A full comparison needs an initial complete VSF with the old core and new
draw tail; actual model/border resources; CPU-port and phi-bank mappings;
complete source-bound stores to both pointer tables and the VIC mirrors;
actual loaded values for the live raster/Timer-A reads; and CIA1 latch,
start, pending and acknowledgement context. Source RMW expansions must
retain their read/dummy/final order. Binary ADC expressions additionally
need the actual decimal flag clear and their live carry inputs.

The observed field should continue through the cutoff handler and the
late visible rows, to a declared next-frame boundary. Only viewport rows
shown to have been fully committed in that interval become the relevant
retained-output comparison. These requirements describe the next bounded
pixel-composition step; this proof does not claim to have performed it.

## Separate monitor readback contract

The new [observer helper](../../research/the-hat/observer_schema.py) keeps
the frozen hardware producer unchanged. Its separate
[primary-source receipt](../../build/research/the-hat/raster-hardware-analysis/observer-accepted-01/observer-contract-proof.json)
binds the following conditional path in eight pinned source files:

```text
m D000 D03F → mon_memory_display → mon_get_mem_val
sidefx=0   → registered mem_bank_peek
bank io=3  → peek_bank_io → c64io_d000_peek → VIC device peek
```

The standard VIC device has a non-null `vicii_peek` callback. This path
does not use the ordinary VIC read side effects: peeking `$D01E/$D01F`
returns collision state without scheduling its clear, and peeking `$D019`
returns IRQ status without acknowledging it. The dump range does not
touch a CIA interrupt-control register. The guarded direct peek path
contains no CPU-cycle advance; actual unchanged CPU clock and stopped
command sequencing still belong to the separately closed native case.

This contract requires computer memoryspace, explicit `sidefx off`, the
standard device registration, `bank io` for the dump and restoration to
`bank ram`, with no resume between the composite commands. It does not
generalize side-effect freedom to an arbitrary I/O device's fallback read.
Any PETSCII glyph bytes in the printable column remain original raw bytes;
future custody parses the numeric columns and framing from a byte-safe
Latin1 view instead of assigning UTF-8 character offsets to that stream.

`model_readback(regs, address, raster_line=None)` returns an expected visible
byte and a comparison mask from **model state only**. Colors read as
`stored OR $F0`; `$D016` reads with `$C0`, and `$D018` with 1. If beam input
is unbound, `$D011` compares only bits 0–6 and `$D012` is omitted. Explicitly
bound raster context can supply their live bits. Unsupported IRQ, light-pen,
collision and other unmodeled context classes reject. Having a 64-byte
dump therefore does not imply prediction of all 64 register bytes.

Forced read bits also limit what a match proves: `$D018` readback cannot
reveal the written bit 0, and `$D016` readback cannot reveal the stored
top two bits. Raw source writes and logical storage remain separately
checked. Every visible dump is an **oracle for comparison**, never a new
logical-state seed or expected-store/model input.

Observer producer: 10,801 bytes, SHA-256
`0baff66ac8ebc6cda8b439aa6435c00891e9bd6e2d026a06d5625356d71dfe71`.
Its receipt is 9,634 bytes, SHA-256
`bc4387e8c5bf8909e9db6b3f174a691997ebbfaf8035d3553cad67aa5f7e9da9`.
Three output files total 37,868 bytes. This is a source/value contract;
acceptance of an actual per-hook readback window remains separate.
A fresh replay reproduces all three files exactly; its
[comparison report](../../build/research/the-hat/raster-hardware-analysis/observer-agent-replay-check.json)
is 595 bytes, SHA-256
`5add3a0f0405cc59fd1a8f8327c0a2b6d490422e9b76a38acbb4aa76cab218a1`.

## Acceptance and retained diagnostics

The [accepted receipt](../../build/research/the-hat/raster-hardware-analysis/accepted-02/raster-hardware-proof.json)
is 38,036 bytes, SHA-256
`1152358f2e24f596192758f5e2b9af5543556b35c63e6474ed8b08dac2de01fb`.
Producer: 29,460 bytes, SHA-256
`f9d15a6d26b877f63591b3c1ff7e31d3cf9430165783c89cb53b35ea6e32a12f`.
Five output files total **1,396,389 bytes**. All 19 closed native02
snapshots preserve every old core field and parse the entire remaining
payload without an opaque byte range.
A fresh replay reproduces all five files byte-for-byte. Its
[agent comparison report](../../build/research/the-hat/raster-hardware-analysis/agent-replay-check.json)
is 921 bytes, SHA-256
`8a635ebe7054e9ec1c46d75e9aa9b85465bccfac6d9fa51fb27922d83bc2a910`.

```sh
rtk proxy python3 -B research/the-hat/raster_hardware.py \
  --output build/research/the-hat/raster-hardware-analysis/replay-new
```

`candidate-01` retains its checked source and traceback: an incorrectly
assumed model-0 guard rejected the actual model-1 snapshots before tail
acceptance. `accepted-01` retains the earlier successful decoder before
the requested logical store/masking API was added. `accepted-02` is the
fresh acceptance of the final source. Source-probe copies remain primary
source data; none was compiled or executed.
