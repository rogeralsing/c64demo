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

Boundary drawing samples every covered horizontal coordinate and records the ceiling of the corresponding crossing row. Steep edges contribute crossings without plotting their vertical interiors. Vertical edges contribute no crossings to this column scan. A running XOR down each packed byte column then turns the boundary transitions into solid face colors, filling four logical pixels together.

Each active column starts with A = 0. The generated prefix kernel uses `EOR` followed by `STA` for each byte, costing eight CPU cycles before VIC-II stalls or interrupts. A temporary `RTS` limits the kernel to the dirty row span; its original instruction byte is restored before returning.

Each edge includes its left X coordinate and excludes its right X coordinate. Shared-vertex contributions join or cancel through XOR under this consistent half-open rule, including coincident markers at corners. Corner parity belongs to the rasterization contract and its dedicated fixtures. The filled variant has separate parity, corner, and playback verification. The 50 fps results above describe the wireframe target.

The filled build passed all 256 presentations with zero boundary-parity errors and exact multicolor polygon pixels. Its complete renderer averages 21,505.32 elapsed PAL cycles and peaks at 26,090, within the 39,312-cycle two-frame budget. The white border includes clearing, geometry, boundary generation, and prefix filling. Measurements are saved in `build/filled-profile/profile.json`.

After building, run the boundary/fill fixtures and full-period playback checks with:

```sh
python3 verify-filled.py --fixtures
python3 verify-filled.py
```

Fixture mode exercises ten cases in both buffers and writes `build/filled-verification/fixtures.json`. Playback verification defaults to 256 presentations with two PAL frames per presentation and writes `build/filled-verification/verification.json`, native VICE screenshots, and `filled-cube.gif` in the same directory. The GIF uses 40 ms per frame. Use `--frames 8` for a smoke run; the same `--vice`, `--labels`, and `--output` overrides are available.
