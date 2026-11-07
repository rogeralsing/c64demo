# C64 vector cube

A standalone rotating cube with hidden edges removed, running at 50 frames per second on a stock PAL Commodore 64. The entry wrapper is `src/cube.asm`; the shared main loop and transforms live in `src/engine.asm`. The build produces a BASIC-autostarting `build/vector-cube.prg` for an emulator or real C64.

The renderer updates the geometry on the C64. Kick Assembler generates arithmetic tables at build time, not animation frames. A cube with half-size 24 rotates using `Rx(pitch) * Ry(yaw)`, with 256 angle steps per revolution and fixed-point coefficients where 64 represents 1.0. The eight corners are signed sums of three rotated axes. A signed quarter-square lookup routine handles scaled multiplication; a reciprocal-depth table supplies perspective factors without runtime division.

The cube has twelve edges, of which four to nine are drawn depending on its orientation. `src/cull.asm` tests the exact signed areas of the projected faces and retains zero-area faces at quantized silhouettes. An edge is drawn when either adjacent face is visible. This gives the cube an opaque appearance without filling its faces.

The display uses a 16×16 character matrix, positioned at screen row 4 and column 12 (zero-based). Screen codes increase down each column, so a pixel at `(x, y)` uses `charset + (x >> 3) * 128 + y`. Drawing changes charset bytes while the screen map stays fixed. Two 2 KB charsets at `$2000` and `$2800` provide a 128×128 canvas with double buffering.

`src/lines.asm` generates Bresenham kernels for each possible X coordinate, four top-to-bottom octants, and both buffers. Pixel masks and destination columns are baked into the code, removing pointer updates and mask shifts from the inner loop. The line module occupies 20,096 bytes at `$3000..$7e7f`, including 17,408 bytes of kernels, 2,048 bytes of dispatch tables, and 384 bytes of endpoint lookup tables. Culling follows at `$7e80..$82ff`, bringing the generated drawing and culling section to 21,248 bytes. This is a deliberate memory-for-speed tradeoff; the source still expresses each kernel once as an assembler macro.

Assembly-time loops also expand the eight projection steps and twelve edge-dispatch tests. Projection expands `MultiplyScaled` inline, avoiding repeated subroutine calls. Each edge uses constant vertex addresses and its adjacent-face mask, removing runtime indexing from dispatch.

`src/clear.asm` remembers the previous cube's bounding rectangle separately for each physical buffer. It clears only the covered columns and rows before that buffer is reused. Fixed-address store chains remove per-byte address calculations; temporary entry/end patches select the rectangle, and changed chain instructions are restored before returning.

`src/macros.asm` contains two helpers used by the renderer. `FillPages(address, pages)` unrolls stores across pages while X loops through byte offsets; it supplies the initial full-buffer clear. `StoreColumns(address, count)` emits one indexed store per canvas column for the bounded clear. This trades a small amount of generated code for fewer runtime branches, while avoiding a fully unrolled 2 KB clear for each buffer. Both macros document register effects and reject invalid bounds at assembly time.

One completed buffer is presented each PAL frame by switching `$D018` in the upper border. The line-0 IRQ supplies a software frame clock; rendering and presentation begin around raster line 1. Their start is not cycle-exact. Yaw advances one angle step per presentation, while pitch advances every second presentation, preserving the angular speed of the original 25 fps version. The combined animation repeats after 512 presentations, about 10.24 seconds.

The border is white during all rendering work and black while waiting for the next scheduled presentation. It measures the complete workload, including clearing, rotation, projection, culling, and drawing.

[Elite erases old ships by redrawing their stored edges with XOR](https://elite.bbcelite.com/deep_dives/the_ball_line_heap.html). That avoids a large screen clear, but still rasterizes the old edges again. It is not a universal win: this small double-buffered canvas already has a cheap bounded clear, and OR drawing retains shared pixels at corners. [Codebase64 discusses other line-drawing and dirty-block clearing tradeoffs](https://codebase64.net/doku.php?id=base%3Alines). This demo uses bounded clearing rather than an additional pass through the old line list.

The toolchain uses [Kick Assembler 5.25](https://theweb.dk/KickAssembler/), Java 11 or newer, and [VICE x64sc](https://vice-emu.sourceforge.io/). Kick Assembler combines 6510 assembly with high-level compile-time scripting for tables, loops, and assertions. The C64 runs the generated machine code; Java is only needed to build it. [RetroDebugger](https://github.com/slajerek/RetroDebugger) is an optional alternative for inspecting the running machine.

From this folder:

```sh
./build.sh
./run-vice.sh
./run-retro.sh
```

Both run scripts build first. VICE starts in PAL mode. The cube launcher selects 100% speed, disables warp and unused audio, and does not save these settings on exit. Trailing VICE options can override these defaults. Build output includes the PRG, Kick Assembler debug data (`vector-cube.dbg`), assembler labels (`cube.sym`), and VICE labels (`cube.vs`). Everything in `build/` is generated and ignored by Git.

After building, verify the assembled program in VICE with Python 3 and Pillow installed:

```sh
python3 verify.py --ticks 1 --raster-line 0
```

This checks 512 rendered frames, covering a full rotation period. It compares every canvas pixel with an independent line rasterizer, checks the projected geometry against floating-point calculations within three pixels, and verifies face visibility, both buffers, VIC-II screenshots, RAM write boundaries, and one-PAL-frame presentation cadence. Results are written to `build/verification/verification.json` and emulator captures to `build/verification/cube.gif`. Use `--vice /path/to/x64sc` if VICE is not on `PATH`; `--frames` and `--output` override the run length and destination.

Measure the complete period and check the white/black border meter with:

```sh
python3 profile.py --meter --frames 512
```

`build/profile/profile.json` records per-stage elapsed PAL cycles, including VIC-II bus stalls and raster IRQs. One PAL frame contains 19,656 cycles. Verification and profiling use separate VICE instances and deliberately stop them at breakpoints while sampling; `./run-vice.sh` supplies uninterrupted playback.

The original 25 fps renderer averaged 35,837.96 elapsed cycles and peaked at 37,049. The final 50 fps build averaged 16,774.82 cycles and peaked at 19,305 over its complete 512-presentation period, leaving 351 cycles below the PAL frame budget in the most expensive frame. This reduction includes the requested change from twelve transparent edges to four through nine visible edges. Local run receipts are [the 512-frame verification](build/optimized-final/verification/verification.json), [final cycle profile](build/optimized-final/profile/profile.json), and [original cycle profile](build/baseline/profile/profile.json).

Download and extract Kick Assembler into `~/.local/share/c64-tools/KickAssembler`, or set `KICKASS_JAR` to another location. Scripts find Java and VICE on `PATH`, with fallbacks for the installed Homebrew tools on macOS. Set these variables when needed:

```sh
export KICKASS_JAR=/path/to/KickAssembler/KickAss.jar
export JAVA=/path/to/bin/java
export VICE=/path/to/x64sc
export RETRO_DEBUGGER=/path/to/retrodebugger
```

`JAVA_HOME` and `XDG_DATA_HOME` are also respected. Additional emulator options follow the target, for example `./run-vice.sh cube -sounddev dummy`.

Open this repository folder in VS Code with the [VS64 extension](https://marketplace.visualstudio.com/items?itemName=rosc.vs64):

- **Cmd+Shift+B** builds the cube and debug symbols.
- **F5** builds and starts VICE with source debugging. Set a breakpoint in `src/engine.asm`, then continue or step.
- **Terminal → Run Task → Build + Run RetroDebugger** loads the cube and symbols into RetroDebugger. An existing instance receives the new program.

VS64 tool paths live in `.vscode/settings.json`; adjust them for another machine. The terminal scripts resolve their own tool paths independently.

The original raster-band starter remains in `src/main.asm`. Build or run it with `./build.sh raster`, `./run-vice.sh raster`, or `./run-retro.sh raster`.

## Filled XOR variant

The separate `filled` target renders solid multicolor faces at 25 fps using XOR boundary parity and a vertical prefix fill. It presents every two PAL frames, giving rendering a 39,312-cycle budget:

```sh
./build.sh filled
./run-vice.sh filled
./run-retro.sh filled
```

It builds the `src/filled.asm` wrapper into `build/filled-cube.prg`, with `filled-cube.dbg`, `filled.sym`, and `filled.vs` for debugging. Both wrappers select the shared runtime in `src/engine.asm`. The default target remains the verified wireframe cube. Filled playback uses the same PAL, 100% speed, sound-off launcher settings.

The filled cube keeps the same geometry size and angular speed. Yaw advances two steps and pitch one step per presentation, so its full period is 256 presentations, about 10.24 seconds.

Multicolor mode gives the canvas 64×128 logical pixels inside the same physical 128×128 display area. Each logical pixel has a two-bit code: `00` is black, `01` is blue, `10` is light blue, and `11` is cyan. These are pixel selectors; their C64 palette indices are 0, 6, 14, and 3 respectively.

Boundary drawing samples every covered horizontal coordinate and records the ceiling of the corresponding crossing row. Steep edges contribute crossings without plotting their vertical interiors. Vertical edges contribute no crossings to this column scan. Markers occupy immediate operands in generated fill code. A running XOR down each packed byte column turns those transitions into solid face colors, filling four logical pixels together.

Each active column starts with A = 0 and X = 0. The generated prefix kernel uses `EOR #marker`, `STA output`, and `STX markerOperand`, costing ten CPU cycles per byte before VIC-II stalls or interrupts. The store through X resets the consumed operand without changing the running color in A. A temporary `RTS` limits the kernel to the dirty row span; its original instruction byte is restored before returning.

Filled mode saves the old bounds of the physical back buffer before projecting the current cube. Filling covers the union of those bounds and the current bounds, so it also overwrites stale output with black. This removes the separate charset-clear pass. The persistent dirty arrays retain only the current image's bounds, preventing the union from growing across frames.

Each edge includes its left X coordinate and excludes its right X coordinate. Shared-vertex contributions join or cancel through XOR under this consistent half-open rule, including coincident markers at corners. Corner parity belongs to the rasterization contract and its dedicated fixtures. The filled variant has separate parity, corner, and playback verification. The 50 fps results above describe the wireframe target.

An edge one column wide writes its single marker without calculating a slope. Other edges try nine unrolled subtractions for common small quotients. Steeper edges with widths 2, 4, or 8 use exact shifts and masks for quotient and remainder; other widths continue subtraction. This preserves the same ceiling crossings in both directions.

Longer edges enter generated code at their starting X. Two chains cover the physical buffers, with four color-lane masks loaded once per edge. A temporary `RTS` at the excluded ending X stops the chain; its original `LDY` opcode is restored before returning. The 32-byte blocks remove pixel counters, mask shifts, and column-pointer stepping. The chains occupy 4,098 bytes, with 260 bytes of dispatch tables. Row lookup tables supply the low offset and page for each eight-byte filler cell. This addressing makes individual marker writes slower; removing the separate clear makes the complete renderer faster.

Both Y directions use the signed floor quotient and a nonnegative remainder. A biased remainder accumulator starts at -1; carry detects fractional row corrections without a separate comparison. This preserves the same exact ceiling crossings while sharing generated code between upward and downward edges. The filled drawing section occupies `$3000..$cc00`, using RAM beneath the disabled BASIC ROM and staying below `$d000` I/O. Its two 16 KB fill banks start at `$4c00` and `$8c00`; a native `RTS` at `$cc00` handles a full-height final column safely.

The filled build passed all 256 presentations with zero boundary-parity errors and exact multicolor polygon pixels. Its complete renderer averages 18,016.91 elapsed PAL cycles and peaks at 21,654, within the 39,312-cycle two-frame budget. Operand filling and inline reset reduced the preceding average of 19,070.14 cycles by 5.52%, and its 23,102-cycle peak by 6.27%. It remains a 25 fps renderer because the worst frame exceeds the 19,656-cycle single-frame budget. The white border includes frame setup, geometry, boundary generation, filling, and reset. Measurements are saved in `build/filled-profile/profile.json`.

We also inspected the original Glenz part from Cruzer/Camelot's *You Know The Routine*. Its six-cycle filler uses separate unrolled operand clearing, a smaller viewport, and quantized slope tables. [The research note](docs/yktr-glenz.md) records the binary evidence and why those slope tables cannot replace our exact crossings unchanged. The current renderer retains exact runtime DDA stepping.

After building, run the boundary/fill fixtures and full-period playback checks with:

```sh
python3 verify-filled.py --fixtures
python3 verify-filled.py
```

Fixture mode exercises 44 closed-polygon cases and 930 direct boundary cases across both buffers, then writes `build/filled-verification/fixtures.json`. Direct boundary checks compare exact mathematical crossings, decode all 4,096 marker operands from their literal output/reset stores, guard unrelated RAM, verify every reachable generated endpoint patch restores the original code, and enforce a 150-cycle budget for ordered one-column edges with display DMA and raster IRQs disabled. Actual prefix calls consume markers between cases. Playback verification checks old/current buffer bounds and complete operand reset, defaults to 256 presentations with two PAL frames per presentation, and writes `build/filled-verification/verification.json`, native VICE screenshots, and `filled-cube.gif` in the same directory. The GIF uses 40 ms per frame. Use `--frames 8` for a smoke run; the same `--vice`, `--labels`, and `--output` overrides are available.

### Glenz experiment

The `glenz` target rotates two interpenetrating tetrahedra built from the eight
corners of a cube with half-size 32:

```sh
./build.sh glenz
./run-vice.sh glenz
./run-retro.sh glenz
```

`src/glenz.asm` selects the shared engine and `src/glenz-renderer.asm` supplies
the topology and drawing calls. Both sides of all eight triangular faces
contribute to the XOR image. Their fixed material selectors are
`[0,1,2,3,0,2,3,1]`; selectors 0 through 3 display black, blue, cyan, and white
(C64 palette indices 0, 6, 3, and 1). Equal overlapping contributions cancel
to form deliberate dark windows. This is classic Glenz color logic rather
than physical alpha blending; it does not claim an exact reproduction of the
*You Know The Routine* part discussed above.

Geometry is transformed and projected on the C64 every presentation. The
renderer reuses the exact half-open boundary DDA and combined prefix
fill/output/operand reset, with complete double-buffered images. It presents
every two PAL frames at 25 fps, advances yaw by two and pitch by one, and
repeats after 256 presentations, about 10.24 seconds. Its border stays black.

The [258-presentation cycle profile](build/glenz/profile/profile.json) covers
the full period and wraparound on both buffers. Rendering averages 33,180.19
elapsed PAL cycles and peaks at 37,160, leaving 2,152 cycles inside the
39,312-cycle budget. These measurements include VIC-II stalls and raster IRQs;
waiting for presentation is separate. Average stage costs are 86.47 cycles
for frame setup, 896 for rotation, 1,374.83 for projection, 18 for accepting
both sides, and 30,804.89 for boundary drawing and filling.

Run the all-angle arithmetic audit, boundary fixtures, and native playback
verification with:

```sh
python3 verify-filled.py build/glenz.prg --labels build/glenz.sym --model glenz --rotation-audit --output build/glenz/rotation-audit
python3 verify-filled.py build/glenz.prg --labels build/glenz.sym --model glenz --fixtures --output build/glenz/fixtures
python3 verify-filled.py build/glenz.prg --labels build/glenz.sym --model glenz --ticks 2 --frames 258 --output build/glenz/verification
```

The [host all-angle audit](build/glenz/rotation-audit/rotation-audit.json) passes
all 65,536 yaw/pitch pairs, checking exact byte-valued rotated XYZ and
projected coordinates. Vertices stay within logical X = 5..58 and Y = 7..121;
the largest Q6 multiplication-table index is 121. The maximum error against
floating-point geometry, measured against each multicolor pixel's physical
footprint, is 4.331 pixels across all angles and 2.612 in the native animation.

The [native verification](build/glenz/verification/verification.json) passes
all 258 presentations and 32 VIC-II captures taken every eight presentations.
It checks independent XOR polygon coverage, coherent two-PAL-frame cadence,
and both buffers, observing 252 distinct canvases. The
[verified animation](build/glenz/verification/glenz-vector.gif) shows the full
period and wraparound. Six previous target binaries remain byte-identical in
the [regression comparison](build/glenz/legacy-regression.json). The separate
[fixture run](build/glenz/fixtures/fixtures.json) passes all 44 closed-polygon
and 930 direct boundary cases, including endpoint restoration and cleanup.

### Icosahedron

The separate `icosahedron` target renders 12 vertices, 20 triangular faces, and 30 edges through the same exact boundary drawer and single prefix-fill pass:

```sh
./build.sh icosahedron
./run-vice.sh icosahedron
./run-retro.sh icosahedron
```

The integer model uses permutations of `(0, ±21, ±34)`, approximating the golden ratio with 34/21. Its faces have outward windings and three colors chosen so adjacent faces differ. The assembler derives shared-edge adjacency. Culling stores one visibility byte per face.

The cube uses a specialized signed-axis shortcut. The icosahedron uses a compact indexed vertex loop with eight scaled multiplications per vertex, applying yaw followed by pitch. A signed lookup table enlarges projected offsets to 145% around the canvas center, reaching about 112 physical pixels across. This preserves the camera and multiplication-table ranges. Projected vertices stay within logical X = 4..59 and Y = 9..119, leaving at least eight physical pixels of margin.

The enlarged object presents every three PAL frames, about 16.7 fps, with a 58,968-cycle rendering budget. Yaw advances three steps per presentation; pitch alternates between one and two steps. This preserves the original angular speed. Its full sampled animation repeats after 512 presentations, about 30.72 seconds. Both existing cube binaries remain byte-identical.

Average elapsed PAL cycles per presentation over each target's complete period:

| Work | Filled cube | Icosahedron |
|---|---:|---:|
| Frame and bounds setup | 86 | 86 |
| Rotation | 896 | 6,723 |
| Projection and bounds | 1,374 | 2,382 |
| Face culling | 1,044 | 4,906 |
| Boundary markers | 7,406 | 18,962 |
| Fill, output, and operand reset | 7,210 | 15,531 |
| Complete renderer | 18,017 | 48,591 |

Filling depends on the old/current bounding-rectangle union, not the number of faces. Its inner loop still costs ten cycles per packed byte. The cube visits an average of 599.07 bytes; the enlarged icosahedron visits 1,359.14, peaking at 1,498. Before enlargement it averaged 678.12 bytes. More faces increase transformation, culling, and boundary work; the larger covered area increases the single fill pass.

The enlarged renderer averages 48,591.46 elapsed cycles and peaks at 51,739, leaving 7,229 cycles inside its three-PAL-frame budget. These measurements include VIC-II stalls and raster IRQs; presentation waiting is separate.

Verify the full period with:

```sh
python3 verify-filled.py build/icosahedron.prg --labels build/icosahedron.sym --model icosahedron --ticks 3 --frames 512 --output build/icosahedron-large-verification
```

The verifier independently derives the convex hull and adjacency from the specified vertex set, checks all 20 visibility flags and exact polygon pixels, and verifies code/model immutability, dirty unions, native captures, and cadence. All 512 presentations and 31 native captures pass. The geometry check measures maximum-axis error against each multicolor pixel's two-pixel physical footprint. Its model-specific tolerance is 4.8 physical pixels, with a maximum of 3.4561 measured in this animation. The cube's existing tolerance remains unchanged. Current artifacts are [the full verification](build/icosahedron-large-verification/verification.json), [the animation](build/icosahedron-large-verification/icosahedron.gif), [the cycle profile](build/icosahedron-large-profile/run/profile.json), and [the stage breakdown](build/icosahedron-large-after/profile/breakdown.md).

### Alternating-row experiment

The `interlaced` target updates alternate physical rows of the enlarged icosahedron:

```sh
./build.sh interlaced
./run-vice.sh interlaced
./run-retro.sh interlaced
```

Each physical charset buffer alternates its own row parity when reused. Updates run B-even, A-even, B-odd, A-odd, then repeat. After startup, the selected rows contain the current presentation; the untouched rows contain that buffer's image from two presentations earlier. The VIC-II displays the resulting mixed-age image with the same display settings as the full-row target.

Its faces use blue, purple, and green. Pixel selectors `01`, `10`, and `11` map to palette indices 6, 5, and 4; Color RAM selects purple as the character foreground.

The interlaced playback border stays black throughout rendering and waiting.

Rotation, projection, and culling still run for every presentation. Boundary drawing still calculates every horizontal crossing. For selected parity `p`, a crossing at physical row `c` becomes field row `ceil((c-p)/2)`. A generated fill cell writes only physical row `2*q+p`, then resets its marker. Dirty bounds belong to each buffer and parity separately, so erasing one field preserves the other field's pixels. The fill includes the closing marker even when it falls one selected row beyond the polygon's last vertex.

This halves the rows visited by filling, output, and operand reset. It also produces intentional comb-shaped edges because the two row parities show different object angles. The full-row `icosahedron` target remains available for comparison.

The generated fill banks retain their 32 KB footprint. Each packed byte column contains 64 even-row cells followed by 64 odd-row cells. Row-address tables map the unchanged exact edge crossings into the selected half. An even-field crossing at row 127 is beyond the last selected row, so it goes to a single discarded marker byte at `$ff01`. Startup initializes that byte, and every fill resets it. The program still loads below `$d000`; the discarded marker occupies RAM under the disabled KERNAL ROM.

Run the focused field fixtures and full-period verification with:

```sh
python3 verify-filled.py build/icosahedron-interlaced.prg --labels build/icosahedron-interlaced.sym --model icosahedron --interlaced --fixtures --output build/icosahedron-interlaced-fixtures
python3 verify-filled.py build/icosahedron-interlaced.prg --labels build/icosahedron-interlaced.sym --model icosahedron --interlaced --ticks 3 --frames 512 --output build/icosahedron-interlaced-verification
```

The field oracle selects alternate rows from the independent full-resolution polygon reference and retains the other rows from that physical buffer's previous presentation. Fixtures exercise all buffer/parity/color combinations, terminal crossings, collapsed spans, closing-marker cleanup, smaller images, and empty fields. Playback checks both field histories, exact mixed-age VIC-II captures, code restoration, marker reset, RAM ownership, and three-PAL-frame cadence.

Full-field filling also has a dirty-tracking break-even point. One selected field contains 1,024 packed bytes; dirty tracking costs about 785 nominal CPU cycles for this 12-vertex model. At ten cycles per fill cell, tracking alone breaks even around 946 bytes, or 92% field occupancy. The current animation visits roughly 702 bytes per field. Full-field processing would add more pixel work than it saves in bounds bookkeeping. [The instruction-count receipt](build/research/interlaced-dirty-breakeven.json) records the assumptions and separates column-dispatch costs from tracking costs.

Before the depth-culling shortcut below, interlacing alone reduced average rendering from 48,591.46 to 41,691.79 elapsed PAL cycles across 512 presentations, a 14.20% saving. Fill/output/reset fell from 15,531.30 to 8,515.98 cycles. Its peak was 44,244 cycles, leaving 14,724 cycles within the three-frame budget. Dirty-bound calculation alone averaged 663.90 elapsed cycles, including its call/return path and VIC-II stalls.

The [complete timing breakdown](build/interlaced-final/breakdown.md) and [comparison receipt](build/interlaced-final/timing-comparison.json) preserve the meter-enabled measurement. Disabling the meter changes one immediate border-color operand and preserves instruction lengths, cycles, geometry, and palette.

The alternating-row renderer passed 84 focused field fixtures. The current green/purple/blue, black-border build with guarded depth culling passed all 512 presentations and 31 native captures. Every face flag matches the independent projected-area oracle, and every mixed-age canvas pixel matches the field reference. Reports and animation are saved with the [full verification](build/z-culling-after/verification/verification.json). Earlier palette and border checks remain linked by the [validation chain](build/icosahedron-interlaced-verification/validation-chain.json).

### Guarded depth culling

The interlaced icosahedron uses its fixed convex shape to avoid most projected-area tests. For each face, it adds the three existing rotated vertex Z values. A sum at most -31 is visible; a sum at least -12 is hidden. Values from -30 through -13 use the original exact projected-area test, retaining zero-area faces at quantized silhouettes.

Negative Z points toward this camera. Perspective places the ideal face-center cutoff near a three-vertex sum of -21 rather than zero. A simple negative-Z test would mark 27% more faces visible in the current animation. The guarded shortcut produces the same visibility decisions as exact screen-space culling across all 65,536 byte-valued yaw/pitch pairs. Only 8.34% of face decisions require fallback, averaging 1.67 exact tests per presentation instead of 20.

The three-value sum stays within -97..97, and every two-value intermediate stays within -69..69. Two signed byte additions suffice; each clears carry independently. The [all-angle audit](build/research/icosahedron-z-culling.json) records the model, camera, rounding, projection, and cutoff assumptions. Changes to those inputs require a new audit. The runtime computes these tests each presentation; it does not read an animation table.

The 20 visibility bytes and 40-byte helper fit in existing alignment padding. Helper code remains outside mutable state, and the culling tables and 32 KB fill banks retain their addresses. The ordinary cube and full-row icosahedron targets remain unchanged.

Before the mesh-edge dispatch unroll below, guarded culling reduced its stage from 4,886.29 to 2,053.23 elapsed cycles over the complete 512-presentation period, a 57.98% reduction. Total rendering fell from 41,691.79 to 39,062.25 cycles on average, saving another 6.31%, and its peak fell from 44,244 to 41,749 cycles. The [culling-stage baseline breakdown](build/z-culling-after/profile/breakdown.md) and [timing comparison](build/z-culling-after/timing-comparison.json) include VIC-II stalls and interrupts.

Full-period native verification checks the new helper against its immutable PRG bytes. All 10,240 face flags, 512 mixed-age canvases and marker images, field histories, and geometry samples match the preceding renderer. The [regression comparison](build/z-culling-after/comparison.json) and [verified animation](build/z-culling-after/verification/icosahedron-interlaced.gif) preserve those results.

### Unrolled mesh-edge dispatch

The interlaced target emits all 30 mesh-edge dispatches at assembly time. Each 34-byte block reads its two fixed adjacent-face color addresses, skips a zero XOR transition, loads four fixed projected-coordinate addresses, and calls the existing boundary rasterizer. This removes runtime mesh indexing and edge-loop bookkeeping. The face-color preparation loop and descending edge order remain unchanged.

The 1,021-byte chain occupies `$cc01..$cffd`, leaving two bytes before mapped I/O. The prefix fill's native return at `$cc00` remains intact, including full-height endpoint patching and restoration. Assembly assertions check the chain's start, size, and I/O boundary. The line algorithm, exact crossings, palette, rotation, interlace cadence, and other renderer targets retain their behavior.

Across 512 presentations, boundary drawing falls from 19,040.58 to 17,965.19 elapsed cycles, a 5.65% reduction. Complete rendering falls from 39,062.25 to 38,071.07 cycles, saving 991.18 cycles or 2.54%. The peak falls from 41,749 to 40,748 cycles. It remains 1,436 cycles above the two-PAL-frame budget, so playback retains its steady 16.7 fps cadence.

All 512 marker images, canvases, visibility flags, and field histories match the preceding build; all 31 native canvas captures and the animation are identical. The new dispatch chain is checked against its immutable PRG bytes without expanding writable RAM ranges. The [current CPU breakdown](build/edge-unroll-after/profile/breakdown.md), [timing comparison](build/edge-unroll-after/timing-comparison.json), and [pixel regression comparison](build/edge-unroll-after/comparison.json) preserve the results.

### Fast full-frame solid icosahedron

The `fast` target keeps the enlarged 12-vertex, 20-face icosahedron and renders
complete images at **25 fps on PAL**. It uses solid flat face colors, with no
alternating-row interlace or per-pixel Gouraud work. The separate `gouraud`
experiment remains available.

```sh
./build.sh fast
./run-vice.sh fast
./run-retro.sh fast
```

This path combines the measured optimizations from the earlier experiments:

- The model's antipodal vertex pairs reduce rotation to eight dynamic Q6
  multiplications per image. Two 256-byte tables supply the exact original
  products for the constant model coordinates 21 and 34. This preserves the
  quarter-square routine's rounding rather than substituting another multiply.
- A reusable perspective table covers signed coordinates and depths -40..40.
  Each vertex selects a depth row, then looks up its X and Y offsets. Entries
  include the center bias, avoiding repeated additions. An unrolled bounds
  pass compares pixel extrema in zero page and converts X to byte columns once.
- Ten antipodal face pairs replace twenty independent depth sums. Only the
  negative-depth candidate can be visible. The audited -31/-12 guard retains
  the original exact projected-area fallback near the silhouette.
- Visible triangles retain the model's fixed blue, green and purple materials.
  Adjacent triangles have different colors, keeping every face identifiable.
  Material preparation is unrolled from the exact 0/1 visibility flags.
- All thirty edge dispatches remain unrolled. The exact half-open DDA and
  combined prefix fill/output/marker reset are retained. Filling covers the
  old/current rectangle union for each physical buffer and visits every row.
- Buffer-specific boundary addresses are cached once per frame. Returning
  immediately after an edge's last marker skips its unused final DDA step.
  For stop rows below 128, filling restores the known EOR opcode directly;
  full-height spans retain the original dynamic-opcode fallback.

The arithmetic tables are generated once during blanked startup in 7,680 bytes
at `$e000..$fdff`; they contain arithmetic functions, not animation poses.
Both 2 KB display buffers and the 32 KB generated fill banks remain. These
rotation, projection and culling shortcuts depend on the current model,
camera, zoom and rounding contract.

Across 512 presentations, covering two 256-pose periods and buffer reuse:

| Work | Mean elapsed PAL cycles |
|---|---:|
| Frame setup | 107 |
| Rotation | 986 |
| Projection and bounds | 1,238 |
| Face culling | 1,328 |
| Boundary drawing, fill, output and marker reset | 32,715 |
| Complete renderer | 36,374 |

The peak is **39,095 cycles**, leaving **217 cycles** within the two-PAL-frame
budget of 39,312. The border stays black. Yaw advances two steps and pitch one
step per presentation, preserving the original angular speed.

```sh
python3 verify-filled.py build/icosahedron-fast.prg --labels build/icosahedron-fast.sym --model icosahedron --fast-solid --rotation-audit --output build/fast-solid-verification/rotation-audit
python3 verify-filled.py build/icosahedron-fast.prg --labels build/icosahedron-fast.sym --model icosahedron --fast-solid --fixtures --output build/fast-solid-verification/fixtures
python3 verify-filled.py build/icosahedron-fast.prg --labels build/icosahedron-fast.sym --model icosahedron --fast-solid --ticks 2 --frames 512 --output build/fast-solid-verification/full
python3 profile.py build/icosahedron-fast.prg --labels build/icosahedron-fast.sym --frames 512 --output build/fast-solid/fixed-colors-final-profile
```

The host rotation audit compares all 65,536 yaw/pitch pairs with the original
eight-product-per-vertex formula. Native verification checks generated table
bytes, exact transformed/projected vertices, all twenty visibility flags and
depth sums, face colors, boundary parity, complete pixels, memory ownership,
code restoration and two-tick presentation cadence. The previous Gouraud,
interlaced, checker, screen-Y tonal and ordinary full-row icosahedron programs
rebuild byte-identically.

All 512 native presentations and 31 VIC-II captures pass. The separate CPU
fixtures pass 44 polygon cases and 930 direct boundary cases across both buffers.

Local receipts: [cycle profile](build/fast-solid/fixed-colors-final-profile/profile.json),
[native verification](build/fast-solid-verification/full/verification.json),
[fixtures](build/fast-solid-verification/fixtures/fixtures.json),
[animation](build/fast-solid-verification/full/icosahedron-fast-solid.gif), and
[previous-target comparison](build/fast-solid/legacy-regression.json).

### Vertex-lit Gouraud experiment

The `gouraud` target derives brightness from the rotating 3D object, then
interpolates it within each visible triangle. The fixed checker and screen-Y
tone variants below are comparison experiments; neither computes 3D lighting.

Every presented Gouraud image contains both row parities from one pose and
one set of vertex light values. Geometry is transformed once, triangle setup
is shared, and both back-buffer row groups are filled before the display
bank changes. There is no mixed-age interlace image in this target.

```sh
./build.sh gouraud
./run-vice.sh gouraud
./run-retro.sh gouraud
```

The twelve model vertices share squared radius 1,597. Their radial smooth
normals therefore reuse the existing rotated coordinates. A view-fixed
upper-front light points along `(0,1,-1)/sqrt(2)`. For signed
`s = rotatedY - rotatedZ`, the runtime vertex intensity is
`clamp(1+floor(7*max(0,s)/sqrt(3194)+0.5), 1, 8)`. The lookup holds this scalar
lighting function, rather than rendered animation frames.

Each face interpolates its three shared vertex intensities affinely over
the actual projected triangle. A 2×4 ordered-dither tile stays aligned to
the screen, while the interpolated light values change with the geometry.
A sample retains the face's blue, green or purple color when its intensity
is at least the Bayer rank plus one; otherwise it is black. This is
screen-space affine Gouraud interpolation, not perspective-correct shading.

For one selected row parity and logical X lane, the Bayer threshold is
constant down a column. Intersecting the triangle's vertical interval with
its affine lighting threshold produces one illuminated interval and two XOR
markers. The existing prefix filler reconstructs those intervals. This
avoids quantized clipping vertices and a per-pixel post-shading pass.

The coherent implementation passes 120 controlled triangle images (240
parity checks) and 64 complete presentations. At its current 16-tick cadence,
the angular pose period is 32 updates, so the native run covers two periods,
including initial and reused buffers. All 31 native captures match. Checks
also cover shared vertex lighting, exact barycentric thresholds, both
pending marker sets, virtual terminals, the intermediate fill and unchanged
display bank, complete final pixels, dirty histories and memory ownership.

```sh
python3 verify-filled.py build/icosahedron-gouraud.prg --labels build/icosahedron-gouraud.sym --model icosahedron --gouraud --fixtures --output build/gouraud-verification/coherent-fixtures
python3 verify-filled.py build/icosahedron-gouraud.prg --labels build/icosahedron-gouraud.sym --model icosahedron --gouraud --ticks 16 --frames 64 --output build/gouraud-verification/coherent-full
```

This first exact Gouraud prototype is substantially slower than solid faces.
Over the complete 32-pose period, rendering averages **263,491.25 elapsed
PAL cycles**, peaking at **290,251**. A 16-frame budget gives **about 3.1 fps**
and leaves 24,245 cycles at the measured peak. Rotation advances according
to elapsed PAL ticks, preserving angular speed. [The profile](build/gouraud-experiment/coherent-profile/profile.json),
[fixture receipt](build/gouraud-verification/coherent-fixtures/fixtures.json),
[native verification](build/gouraud-verification/coherent-full/verification.json)
and [animation](build/gouraud-verification/coherent-full/icosahedron-gouraud.gif)
preserve the exact program identity and scope. The earlier fast fixed-checker
and screen-Y-mask timings are not timings for this 3D lighting path.

### Fixed checker comparison

The `dither` target gives the interlaced icosahedron fixed checkerboard face
materials while retaining its geometry, rotation, culling, palette and black
border. The solid-color `interlaced` target remains available for comparison.

```sh
./build.sh dither
./run-vice.sh dither
./run-retro.sh dither
```

Each material has one packed byte for even physical rows and another for odd
rows. The three pairs are `$66/$99` (blue/green), `$BB/$EE` (green/purple),
and `$DD/$77` (purple/blue). The pattern repeats across four multicolor pixels
and two physical rows, aligned to the screen. Pattern selection uses the
actual field parity, preserving B-even/A-even/B-odd/A-odd buffer history.

Shared edges XOR the adjacent faces' full pattern bytes. Boundary setup
isolates the selected two-bit lane with `$C0/$30/$0C/$03`; the normal prefix
fill reconstructs the pattern. Its fill/output/reset cell stays at ten
nominal CPU cycles per packed byte. There is no extra interior shading pass.
This first experiment uses fixed materials, without orientation-based shade
selection or a palette reassignment.

Verify the boundary cases and the complete rotation period with:

```sh
python3 verify-filled.py build/icosahedron-dither.prg --labels build/icosahedron-dither.sym --model icosahedron --interlaced --dither --fixtures --output build/dither-verification/fixtures
python3 verify-filled.py build/icosahedron-dither.prg --labels build/icosahedron-dither.sym --model icosahedron --interlaced --dither --ticks 3 --frames 512 --output build/dither-verification/full
```

All 156 focused fields and 512 presentations pass, including 31 exact native
canvas captures. The independent reference paints exact polygon interiors,
then samples the material by physical row and X lane. It also checks marker
closure, the terminal sink, code/table immutability, dirty cleanup, retained
rows, black border and three-PAL-frame cadence. The [fixture receipt](build/dither-verification/fixtures/fixtures.json),
[full receipt](build/dither-verification/full/verification.json) and
[animation](build/dither-verification/full/icosahedron-dither.gif) retain the results.

Over the same 512-presentation period, average rendering rises from 38,071.07
to 38,275.89 elapsed PAL cycles: **204.82 cycles, or 0.54%**, including VIC-II
stalls and interrupts. Peak rendering is 40,986 cycles, leaving 17,982 of the
58,968-cycle budget. Playback stays at three PAL frames per presentation
(about 16.7 fps). The [timing comparison](build/dither-experiment/comparison.json)
pins both program/profile identities. Rebuilding the solid-color interlaced
target produces its preceding byte-identical PRG.

### Screen-Y tonal comparison

The `tonal` target adds a screen-aligned light-to-dark gradient across the
face interiors. It keeps each face's blue, green or purple hue and increases
the proportion of black samples toward the bottom. This is spatial tonal
shading, rather than the fixed two-color checker materials in `dither`.

```sh
./build.sh tonal
./run-vice.sh tonal
./run-retro.sh tonal
```

The normal prefix first writes raw face selectors. A separate pass applies
a 4×4 ordered-dither mask to the selected physical rows. For canvas-local
physical row `y`, its density is `clamp(16-floor((y-8)*17/112), 0, 16)`;
each logical pixel keeps its face color when its Bayer rank is below that
density, otherwise becoming black. The mask is anchored to the screen, not
derived from 3D lighting or normalized separately within each triangle.

The shader visits the prefix fill's old/current union of selected rows.
Opposite-parity pixels retain their previous shaded image. Fresh raw face
selectors are regenerated before each shade pass, preventing cumulative
darkening. One shared unrolled row kernel patches its 32 address high bytes
to the selected charset. Its code and 128-byte mask reuse the unused cube
sine-table page and alignment padding; the fill banks keep their addresses.

```sh
python3 verify-filled.py build/icosahedron-tonal.prg --labels build/icosahedron-tonal.sym --model icosahedron --interlaced --tonal --fixtures --output build/tonal-verification/fixtures
python3 verify-filled.py build/icosahedron-tonal.prg --labels build/icosahedron-tonal.sym --model icosahedron --interlaced --tonal --ticks 3 --frames 512 --output build/tonal-verification/full
```

All 156 focused fields and 512 presentations pass, including 31 native canvas
captures. The verifier checks raw material markers and the natural pre-shader
fill separately from the final Bayer-toned pixels. All 128 masks, 32 exact
address patches, retained fields, cleanup, black border and three-tick cadence
are checked. Results are in the [fixture receipt](build/tonal-verification/fixtures/fixtures.json),
[full receipt](build/tonal-verification/full/verification.json) and
[animation](build/tonal-verification/full/icosahedron-tonal.gif).

Average rendering is 49,788.78 elapsed PAL cycles, versus 38,071.07 for solid
faces: **11,717.71 extra cycles, or 30.78%**. The separate shading pass is the
main added work; the fixed-checker experiment's 0.54% figure does not apply
to this spatial gradient. Peak rendering is 52,923 cycles, leaving 6,045
within the three-frame budget. Playback remains about 16.7 fps. The
[timing comparison](build/tonal-experiment/comparison.json) pins both profiles.
The solid and fixed-checker PRGs remain byte-identical after this addition.

## Rendering research

[Research notes](docs/research/README.md) and the [technique map](docs/research/technique-map.md) document released C64 demos, primary sources, original-binary analysis, independent models, native checks, and unresolved questions. Supporting acquisition and analysis scripts live in `research/`. Original downloads and large generated receipts stay under the ignored `build/research/` directory.

For continuation, read the [research checkpoint](docs/research/CHECKPOINT.md)
and the [follow-up prompt](docs/research/FOLLOW_UP.md).
