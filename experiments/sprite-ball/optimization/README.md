# Sprite-ball delta-rendering experiments

Measured on 8 November 2026. Three independent prototypes were tested against
the same 513-presentation animation, including hexagons, pentagons, zoom,
changing rotation speeds, empty slots, and both destination-buffer histories.
None improved the measured average. The production renderer is unchanged.

| Strategy | Measured work | Original mean | Prototype mean | Result |
| --- | --- | ---: | ---: | --- |
| Cache identical local vertices and topology | Clear, edge drawing, fill, and cache bookkeeping; 511 presentations after two warmup presentations | 19,632.77 CPU cycles | 20,430.24 CPU cycles | 4.06% more cycles |
| Compare each filled byte before writing both mirrors | Fill kernel; 513 presentations | 5,526 CPU cycles | 5,877.36 CPU cycles | 6.36% more cycles |
| Retain column spans and XOR changed endpoint intervals | Span construction and delta update; 513 presentations | 19,641.77 CPU cycles | 47,993.58 CPU cycles | At least 144.34% more cycles |

These rows measure different scopes. They are not whole-frame percentage
changes. CPU measurements execute assembled NMOS 6502 code in py65 and exclude
VIC DMA and raster/music interrupts. The span comparison favors the prototype:
the original includes position/color metadata work which the prototype omits.
The span prototype also omits external JSR dispatch counted for the original.
The conditional-store kernel omits the production fill's segmented tail calls
from both sides of its comparison.

## Native acceptance and exact pixels

The freshly built original program passed the existing VICE verifier for all
513 presentations, including exact rational polygon coverage, both VIC-bank
copies, screenshots, colors, face selection, and two-PAL-frame cadence. Its
elapsed render time averaged 31,882.55 clocks and peaked at 35,887 clocks.
Its SHA-256 is
`bda91e6fc54d1fc1adfc7eeaccaa0495de350c40977202bf074c103ec9367421`.

The trace capture patch only adds observations to an isolated copy of the
verifier. It records actual sprite contents before and after each destination
buffer update, local vertices, and crossing markers. Initial contents come
from native RAM after the intro, rather than assuming empty buffers. The
canonical trace SHA-256 is
`0cb3694b9ddefdded3e92bc6e26ccae10370afe07b5606e9eca69787f67b9843`.

All three prototypes reproduced every traced sprite byte in both mirrors.
The original assembled clear/draw/fill path was also replayed against every
crossing marker and output byte. This establishes raster correctness for the
recorded trajectory, not arbitrary poses or complete prototype lifecycles.

The integrated cache fits the C64 address map, but the unchanged native
verifier rejected it at RUN pose 5 for a missed presentation deadline. Its
elapsed render time there was 38,251 clocks. The first five presentations had
passed the pixel checks. It was not adopted. Only 136 of 3,864 active shapes
were cache hits after warmup (3.52%). Slow-motion phases also lost on average.
Its additional mapped code occupies 687 bytes including alignment, and its
runtime state occupies 274 bytes.

Conditional stores found only 74.94% unchanged bytes. The instruction kernel
needs more than 85.71% unchanged bytes before page-cross penalties to win.
It lost on 449 of 513 presentations. The integrated version also failed the
`Fill A overlaps hardware vectors` assembly guard: generated code grows by
4,560 bytes across both destination banks.

Span delta reduced average mirrored output stores from 912 to 691.48
(24.18%), but comparisons, retained-state updates, and per-bit interval
operations outweighed that saving. Every presentation took more CPU cycles.
The prototype requires 768 bytes of history and 48 bytes of span scratch;
replacing the original 512-byte crossing workspace adds 304 data bytes before
code/table placement. This rejects the tested column-span implementation,
not every possible delta algorithm.

## Reproduce

Requirements: Python with NumPy, Pillow and py65, Kick Assembler (`kickass`),
VICE (`x64sc`), and `rtk`. Run from the repository root. `prepare.py` refuses
to overwrite an existing experiment directory and never changes product code.

```sh
rtk proxy python3 experiments/sprite-ball/optimization/prepare.py /tmp/discoball-delta-replay
rtk proxy sh /tmp/discoball-delta-replay/baseline/experiments/sprite-ball/build.sh
rtk proxy sh /tmp/discoball-delta-replay/shape-cache/experiments/sprite-ball/build.sh
rtk proxy python3 /tmp/discoball-delta-replay/baseline/experiments/sprite-ball/verify.py --frames 513
rtk proxy python3 /tmp/discoball-delta-replay/baseline/profile_reference.py /tmp/discoball-delta-replay/baseline/experiments/sprite-ball
rtk proxy python3 /tmp/discoball-delta-replay/shape-cache/benchmark_shape_cache.py --baseline /tmp/discoball-delta-replay/baseline/experiments/sprite-ball --candidate /tmp/discoball-delta-replay/shape-cache/experiments/sprite-ball --trace /tmp/discoball-delta-replay/baseline/experiments/sprite-ball/build/hexagon/verification/delta-trace.json --output /tmp/discoball-delta-replay/shape-cache/report.json
rtk proxy python3 /tmp/discoball-delta-replay/changed-bytes/benchmark_changed_bytes.py /tmp/discoball-delta-replay/baseline/experiments/sprite-ball/build/hexagon/verification/delta-trace.json
rtk proxy python3 /tmp/discoball-delta-replay/boundary-delta/boundary_delta.py --trace /tmp/discoball-delta-replay/baseline/experiments/sprite-ball/build/hexagon/verification/delta-trace.json --profile /tmp/discoball-delta-replay/baseline/experiments/sprite-ball/build/hexagon/verification/reference-cpu-cycles.json
```

To repeat the integrated cache rejection, run its existing verifier. This
command is expected to fail the presentation-deadline assertion:

```sh
rtk proxy python3 /tmp/discoball-delta-replay/shape-cache/experiments/sprite-ball/verify.py --frames 513
```

The initial cache run encountered a host-side monitor startup timeout. The
retry increased only the host socket timeout after reusing the completed
geometry proof; native pixel and cadence assertions were unchanged. The
saved failure log identifies the subsequent program-level rejection.

The standalone benchmarks generate their assembly, tables, and PRGs next to
their copied scripts. Detailed measurements and the source hash manifest are
in [results](results/). The measured run's larger trace, RAM dumps, screenshots,
and isolated source snapshots remain under `../build/delta-strategies/`.
