# Aloft: from forty changing bytes to the captured image

Research date: 9 November 2026. The previous goal turn made concrete progress:
two original call windows and logical fetch schedules passed. This pass closes
physical mapping, byte visibility and the complete 200-row display-body join.
The broad demo-research objective remains active.

![Independently reconstructed later body, enlarged 2×](../../build/research/aloft-pixels-20261109/preview-01/aloft-later-640x400.png)

This image comes from the independently predicted palette indices, not a
native screenshot. Its physical graphics geometry is 320×200; the multicolor
sample grid is 160×200. The preview uses the retained Colodore palette and
nearest-neighbor enlargement. RGB values illustrate the indices, not an
analog-output measurement.

## What now passes

The [physical mapping study](aloft-physical-fetch-20261109.md) resolves all
forty requested glyph addresses to ordinary main RAM. It binds the original
C64SC machine, no cartridge or memory hack, initial CIA2/GLUE bank state,
official-source mapping setters and continuous port/bank-control history.
The VIC reads RAM directly; the CPU's `$00/$01` device overlay is a separate
route. The forty actual glyph stores use the same RAM object.

The [glyph-stream join](aloft-glyph-stream-20261109.md) starts from genuine
initial bytes and the previously independent typed store values. Raw native
hooks supply timing only; register values and monitored addresses are removed
from that input projection. Each line's four store completions occur at
offsets −7, 0, 3, 6 relative to its graphics line. Conservative source visibility
bounds keep current stores at least nine cycles before the first request,
and the next absolute store at least one cycle after the last request.
Each of two 200-line streams therefore supplies 8,000 fully ordered bytes.
Four late GBUF/last-phi1 samples match; they were not stream inputs.

The [tail guard](aloft-tail-guard-20261109.md) closes a subtle endpoint gap.
The dispatcher returns at line 247/cycle 30, before the last request at cycle 54.
Original `$F0B1..$F0B7` is a read-only raster wait. Natural `$F0B8` falls
through at line 248/cycle 3, after the last request; glyph clearing cannot begin
early under the stated source closure.

The [display study](aloft-display-contract-20261109.md) derives the fixed
MOS8565 multicolor-text pipeline and pixel placement. Both 384×200 bodies,
raster rows 48–247 including horizontal borders, match all **153,600 indices**.
The graphics portions match all **128,000 physical pixels**. Both predictions
were written before either target framebuffer was opened.

The initial window's colors are all black: its pixel match cannot distinguish
glyph bits. The later palette is `[14,10,4,0]`, with four distinct colors.
Inverting the later native image recovers all **8,000 bytes**, exactly equal
to the independently predicted stream. This is the meaningful complete byte
comparison; it is not presented as sixteen thousand directly logged reads.

## The source-route correction matters

Official x64SC source links `c64cpusc.c`, `mainc64cpu.c` and `6510dtvcore.c`,
with `c64memsc.c`. Generic `6510core.c` has different STORE clock placement.
The new source contract supersedes that generic timing attribution, while
confirming actual SC execution-break-before-watch flushing. Earlier raw
deferred-hook observations remain valid and unchanged.

SC direct stores run before their trailing clock increment. The consumer
keeps a conservative `[completion−1, completion]` visibility interval, rather
than inventing electrical bus timestamps. Actual SC `$04/$0C` NOP paths also
perform dummy target reads. That refines the old conditional source reading;
it does not change the already compared ordinary cells' store values.

The [current installation record](../../build/research/aloft-pixels-20261109/environment-analysis/current-install-01/observer-environment.json)
retains Homebrew recipe/receipt support and a current executable fingerprint.
It was acquired after capture and is explicitly not a backdated binary hash
or a reproducible-build equivalence proof. The captured log itself records
VICE 3.10 and the same Cellar system path. No binary or build was launched.

## Reproduction and next work

The detailed studies own the exact producers, receipts, source members,
independent replays and failed-candidate custody. All old artifacts remain
immutable. The five previous indexes were archived under
`build/research/handoff-20261109/prior-10925/` before this publication.
All new work is confined to the new `aloft-pixels-20261109` source/build
directories, new detailed notes and the five mutable handoff indexes.

No new native case was required. Reuse the closed original case at
`build/research/aloft-execution-20261109/native-01/`; do not overwrite it or
restart merely to replay these passive models.

The first partial line 47, earlier viewport prefix and later field tail remain
outside the independent body model. The result does not establish complete
animation cadence, every pose, physical silicon timing or a human scene name.
If extending the full viewport, bind those missing intervals explicitly;
copying already committed prestate pixels is a declared input, not another
independent prediction.

The supplied source generation and actual per-line call targets are admitted
inputs. Reconstructing the motion-to-target generator is a separate useful
next step: explain which parameters choose the OR/AND edge masks, without
silently supplying the captured JSR list as its output.

Continue the wider backlog too: the separately referenced moving layered
scene, side-two joystick/flipped Kefrens, Hat composition and unfinished
Lab/EOD cases. [The rendering comparison](rendering-models-20261109.md)
separates The Lab's prepared edges, this raster staging engine and the new
[primary WIZ reading](row-cache-and-wiz-20261109.md). The latter includes the
author-linked PRG and finite arithmetic only; its released behavior is not
yet reverse-engineered or natively compared.
