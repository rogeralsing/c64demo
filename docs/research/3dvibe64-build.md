# 3Dvibe64: the completed Mode 6 build is byte-bound

The root-owned build completed with exit code 0 using the unmodified pinned SDK, official PowerShell 7.6.9 and locally compiled 64tass 1.60.3243. A second assembly with VICE symbols produced an identical PRG. Our independent passive audit binds **57 selected tables / 1,011 bytes** in both emitted assembly and linked PRG, including the **132 Bayer bytes**, **704 lighting bytes**, six shade normals and their center terms. This establishes the build/data boundary; native execution and pixels belong to the separate native audit.

No PowerShell, assembler or emulator is invoked by this producer:

```sh
rtk proxy python3 research/3dvibe64-native/inspect_build.py
```

It reads retained inputs and writes only `build/research/3dvibe64-native/build-analysis/build-proof.json`. It does not rerun the upstream generator or the older frozen source-analysis producer.

## Exact products and invocation

All paths below are under `build/research/3dvibe64-native/` unless specified otherwise.

| Product | Bytes | SHA-256 |
|---|---:|---|
| `build-01/products/3Dvibe64.asm` | 527,362 | `22008b3a92b7896c699543b12f9036704797262aa3558cd9116d8a09c85b796f` |
| `build-01/products/3Dvibe64.prg` | 49,711 | `69b0d86f79106b2bf9654d85bd631bc68c12f4efd708454a0048560b3c1bfdeb` |
| `symbols-01/3Dvibe64.prg` | 49,711 | same PRG hash |
| `symbols-01/3Dvibe64.labels` | 24,267 | `265a1770fe7a605139f0cdfd9d2983f6ddb314a1cf234a6f3a14d6f3b344e847` |
| Authored `research/3dvibe64-native/scene.json` | 1,104 | `2dc0c5d4a8bab84ae522a31da6b7e998e346cce1dd0ffe6693ab01990ca6f72a` |

The retained `build-01/command.json` records the actual configuration: legacy precision, Mode 6, `high-basic-v2`, PAL, fixed camera, normal viewport, **fast quality and extended-table projection**, `NoFpsOverlay`, `SkipCmdUpdate`. These last quality/projection selections are actual build flags, not inferred defaults. `TASS64_EXE` names the task-local reviewed assembler; PowerShell ran with no profile and without a shell wrapper. Complete stdout/stderr hashes and successful terminal results are checked for both build and reassembly.

The producer independently compares all **387 pre-build SDK files** with the pinned upstream archive at commit `b19df459b7efe50d514b59fe876c0bc7c326c5b4`. The recorded SDK delta contains no modified or removed original files, only `work/3Dvibe64.asm`, `work/3Dvibe64.prg` and its `work/build/` copy. The builder remains SHA `b03d5d7ce6e9e5af85d47c04950841da96f1f3e6dc7b50f5c26a1f97c5bb7e70`. No undocumented source patch explains the result.

The normal reassembly uses `-a -B --vice-labels --labels=… -o …` and the frozen generated assembly. Its 968 exported symbols omit many expression aliases and zero-page equates; those are derived from the emitted source and corroborated by selected machine operands below. This audit is not an independent implementation of 64tass.

## Tables and scene binding

The emitted program contains the exact packed Bayer and intensity data reconstructed by the [earlier source/math audit](3dvibe64.md):

| Data | C64 addresses | Checked size |
|---|---|---:|
| Four packed Bayer rows | `$B526–$B5A9` | 132 |
| Eleven 64-byte light-level tables | `$B60B–$B8CA` | 704 |
| Shade-to-geometric-vertex mapping | `$B4FC–$B501` | 6 |
| Normal X/Y/Z arrays | `$B502–$B513` | 18 |
| Center-dot low/high arrays | `$B514–$B51F` | 12 |
| Initial dynamic shade state | `$B520–$B525` | 6 |

Both lookup-pointer tables are checked against the linked symbol addresses. The normals occur in geometric-vertex order **0,5,2,1,3,4**:

```text
(63,0,0), (0,0,-63), (0,63,0), (-63,0,0), (0,-63,0), (0,0,63)
```

All six center terms are **882 / `$0372`**. The source calculation uses the half-scale local vertex coordinate, so `63×14=882`; using `63×28` would be wrong. Initial shade bytes are `$ff` sentinels, not measured lighting. The producer also checks coordinate tables, coordinate indices, triangle indices/arities, four shade-corner maps, object position/scale/angular velocities, fixed light position and intensity against the authored scene.

The scene's gray material and reflectivity 1 give per-face material index 0 / reflectivity offset 10. Linked palette tables at that offset yield **Screen RAM `$bf`, Color RAM `$01`**: pixel codes 01/10/11 map to colors 11/15/1. Bootstrap constants instead use Screen RAM `$bf`, Color RAM `$0f`; runtime material application must establish the intended cell palette. A build table does not prove that every displayed cell received it.

Selected byte guards bind the actual startup, end-of-render calls, logical buffer toggle, IRQ bank writes, four Bayer loads/masks, and normal/center loads to their symbol names. Bayer load operands are deliberately self-modified when selecting a logical scanline's table row; a later native capture must account for those writes rather than require all code bytes to remain unchanged.

## Memory layout

The PRG loads at **`$0801`** through **`$CA2D`**, exclusive end `$CA2E`. Its BASIC SYS target is **`$080D`**. The assembler reports these initialized ranges:

| Region | Inclusive addresses | Bytes |
|---|---|---:|
| Low code/data | `$0801–$14FD` | 3,325 |
| Middle code | `$4000–$43D1` | 978 |
| Relocated raster code | `$9000–$9C20` | 3,105 |
| High code/data | `$A000–$CA2D` | 10,798 |

The remaining 31,503 payload bytes are assembler-reported gaps, verified zero in the file. File gaps are still physically loaded and may later hold video/runtime state; they are not independent free-memory claims. The build's post-assembly checks report runtime exclusive end **`$849C`**, with 2,916 bytes before relocated code at `$9000`. Video buffers are A bitmap `$6000`, screen `$5C00`; B bitmap `$2000`, screen `$0400`. Startup selects RAM under BASIC via `$01=$36`; high tables/code are below the reserved I/O boundary `$D000`.

## Natural capture anchors and lifecycle

These are linked PCs in this exact product, not suggested CPU-state injections:

| Anchor | PC | Meaning |
|---|---|---|
| `start` | `$080D` | Natural BASIC SYS target, before initialization |
| `main_loop` | `$08C5` | Tick consumption precedes the render |
| `render_frame_begin` | `$08CB` | Rendering work begins |
| `gous_done` | `$1153` | Current object's shade update complete, before RTS |
| `render_frame_end` | `$08D4` | Drawing complete; presentation wait has not run |
| `show_buffer` | `$0D06` | Toggles RAM `drawbuf`; does not write VIC bank registers |
| `raster_irq` | `$09A9` | Acknowledge raster IRQ, then apply bitmap mode/bank |
| IRQ after bitmap-body JSR | `$09B1` | Selected `$DD00/$D018` writes completed |
| `sbb_show_a` / `sbb_show_b` | `$0A27` / `$0A37` | IRQ branches selecting the actual front buffer |
| `gouraud_fill_bounds` / `gfb_row` | `$9455` / `$947E` | Per-face fill / per-row processing |
| `gouraud_draw_scan_span_bytes` | `$A000` | Current scanline endpoints and shade state are prepared |

`drawbuf=0` draws A while the IRQ shows B; `drawbuf=1` draws B while the IRQ shows A. Startup sets 1, so the first completed drawing is in B. At `$08D4`, `wait_raster` waits through line 252 until line 253, then `show_buffer` toggles the logical index. The following line-0 IRQ applies it: A uses bank bits 2 / `$D018=$78`; B uses bank bits 3 / `$D018=$18`.

A source-derived first-B capture plan is: observe first render completion, then `$09B1` with `drawbuf=0`, then stop naturally at line 252 in that displayed field. The bitmap rows displayed at raster lines 51–250 should then be committed while the next render targets A; even an early next completion waits until 253 before its logical toggle. **This is a plan, not a record of a native capture.** Actual CIA pins, VIC registers, raster commitment and absence of later buffer reuse must be checked in the native audit. Publication alone proves no displayed pixels.

Tick consumption can advance the object's angles before the first render. The input's zero initial rotation therefore does not establish an identity pose at `$1153`; read actual matrix/light/angle state before predicting live shades.

## Bounded per-scanline state

At `$A000`, read zero page `$0B–$2F` plus **`$B43B–$B441`**. The seven contiguous scan bytes mean **x, end, delta, direction, error, extent, shade**. Direction is `$01` or `$ff`; the caller initializes error to zero. `yrow=$2F`, `drawbuf=$0B`, `faceidx=$0D`, `objidx=$7B`; light-cache components are `$6F–$71`.

The normal fixed-camera flags disable raw/near/screen polygon clipping and retain standard projection. The emitted alias chain gives:

| Arrays | Start addresses | Length each |
|---|---|---:|
| `sx`, `sy`, `syq2_lo`, `syq2_hi` | `$8000,$8006,$800C,$8012` | 6 |
| `sx_prev`, `sy_prev`, `smooth_ready` | `$8018,$801E,$8024` | 6 |
| `sz`, `szhi`, `rxbuf`, `rybuf`, `projdone` | `$802A,$8030,$8036,$803C,$8042` | 6 |
| `leftb`, `rightb`, `leftshade`, `rightshade` | `$8063,$80C7,$812B,$818F` | 100 |

The last four arrays form **400 contiguous bytes `$8063–$81F2`**. Actual indexed load operands at `$947E` corroborate `leftb=$8063`, `rightb=$80C7`. These buffers are reused for the next face: capture each face's span inputs while that face is being consumed, rather than treating the final arrays as a whole frame's history. `projx/projy` lookup tables are not per-vertex projected outputs; use `sx/sy` after the projection routine returns.

The passive receipt contains all input pins, table addresses/hashes, machine-byte guards, source flags and capture anchors. It makes no dynamic geometry, shading, framebuffer, FPS or physical-hardware claim. Native evidence should consume this build identity and add its own guarded observations without modifying these products.
