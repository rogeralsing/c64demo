# Mode 6: scalar rasterizer and committed visible pixels

Both captured rasterizer windows match an independent scalar reconstruction
of the complete 8,000-byte target bitmap, its Screen RAM and physical Color
RAM. The second sample also matches **all 64,000 palette-index pixels** in the
committed native 320×200 visible bitmap body. The gradients are real, including
descending shades and both Bayer bands. The observed render intervals are
slow: approximately **0.586 and 0.518 seconds** on the PAL clock model, before
earlier lighting/clearing and later presentation work. This is a correctness
experiment, not a fast stock-C64 vector replacement or a 50 FPS result.

The producer is [`research/3dvibe64-native/pixels.py`](../../research/3dvibe64-native/pixels.py).
Receipt: `build/research/3dvibe64-native/pixel-analysis/pixel-proof.json`.
The [input scene note](3dvibe64-native-scene.md) and
[emitted-byte note](3dvibe64-build.md) describe separate input/build
contracts. This acceptance uses actual span endpoints as input; it does not
independently prove projection, culling, clipping, painter order or edge-shade
construction.

## What the two images establish

**Sample 1: decoded completed bitmap. Its first publication was missed.**

![Sample 1 decoded completed bitmap; no first-publication witness](/Users/rogerjohansson/git/asynkron/c64demo/build/research/3dvibe64-native/pixel-analysis/sample1-preview.png)

**Sample 2: scalar reference, also equal to the committed native visible body.**

![Sample 2 scalar reference verified against committed native visible pixels](/Users/rogerjohansson/git/asynkron/c64demo/build/research/3dvibe64-native/pixel-analysis/sample2-preview.png)

The source object is the authored smooth six-vertex/eight-triangle
octahedron. Sample 1 reads as a shaded diamond; sample 2's projection reads
more like a tilted quadrilateral. The pixel equality does not make that
silhouette more legible. The fixed gray ramp is dark gray 11, light gray 15
and white 1, with black background; it does not supply 33 simultaneous VIC
colors. Preview RGB uses the pinned Colodore palette. Acceptance compares
palette indices, independently of PNG compression or RGB palette appearance.

## Closed capture and honest failure history

`build/research/3dvibe64-native/native-01` contains 21 files, 2,744,142 bytes.
Its directory pin is
`ec17844d8b748e0914f6ffdba3b336c63247229bb62ada335172b4da30fe9281`.
The authored generated PRG is 49,711 bytes, SHA-256
`69b0d86f79106b2bf9654d85bd631bc68c12f4efd708454a0048560b3c1bfdeb`.
All 49,709 loaded payload bytes match at the natural `$080D` entry.

Startup uses VICE **PRG autostart mode 1**, a declared loader-injection path
for our newly generated program. It is not an original disk/1541 loading
witness. After startup there are no manual CPU/register/RAM patches and no
snapshot restores. The single owned process, PID 59361, remains the same
through both samples and the interruption; it closes and is reaped with VICE
exit `-15`. The helper exits normally. Seven full RAM/VSF pairs independently
check 458,752 RAM bytes, CPU registers/clock/ports and beam positions.

The wire audit checks all 63 ordinary commands and the exact raw sent/received
custody. A narrowly declared adapter changes only the frozen auditor's manual
startup assertion to exact generated-PRG autostart metadata. Native launch
flags request PAL, `Speed=100`, warp disabled and autostart warp disabled. No
explicit runtime speed/warp resource query was made. The proof does not use
host elapsed time as a performance measurement.

After sample 1 completed, command 29 attempted:

```text
break 09b1 if @ram:$000b == 0
```

VICE rejected it with `Conditional operation missing an operand`. The
following resume, command 30, had no intended publication breakpoint and was
later interrupted read-only on the same socket/PID. Its actual stop was
`$A0FB`, clock 9,257,978. These events remain in the receipt; the first
publication is not invented from later state. A `$00` constant is accepted
subsequently. Sample 2 starts from its own later natural baseline and uses
`$01` for its observed publication condition. No timeout retry, state rollback
or process restart is represented as a successful first publication.

## Capturing the actual rasterizer inputs

The emitted `gouraud_draw_scan_span_bytes` entry is `$A000`, before either its
packed-byte work or Bayer-constant bulk classifier runs. The read-only trace
command attached to that entry is exactly:

```text
m 000b 002f; m b43b b441
```

The first range contains `drawbuf=$0B`, the two physical row pointers at
`$25..$28`, left/right values at `$29/$2A`, and `yrow=$2F`. The second gives
seven contiguous bytes: X start, X end, absolute shade delta, signed direction,
initial error, span extent and initial shade. Each trace entry is bound to its
actual clock and both memory displays. Parsing requires the complete exact
address set, zero initial error, consistent inclusive X/extent, valid shade
range and matching row pointers. Captured call order is retained.

The official VICE source confirms that a trace checkpoint can execute its
attached monitor command and continue without an attached `x`; semicolons
separate the two memory displays. `bank ram` and `sidefx off` are retained.
No checkpoint command writes C64 memory or registers.

The three natural stages are:

- `$1153`, `gous_done`: clearing and vertex-shade update have finished; our
  single object has not drawn any spans yet. This supplies the actual bitmap
  baseline, angles, cached light and raw shades.
- `$08D4`, `render_frame_end`: all spans in this accepted window have returned.
- `$09B1`: the raster IRQ has returned from `set_bitmap_body_mode`, so actual
  `$DD00/$D018` selection can be checked after `show_buffer` toggles `drawbuf`.

`show_buffer` itself only toggles a byte; it is not the VIC publication write.
Sample 2 additionally stops at line 252/raw cycle 3, in the same PAL field as
the observed publication, after the complete visible bitmap body is committed.

## Independent scalar calculation

For an inclusive span `x0..x1`, let `L=x1−x0`, `d=abs(s1−s0)` and `dir=±1`.
For sample `k=x−x0`:

```text
s(k) = s0 + dir × floor(k×d/L)       when L>0
s(0) = s0                           when L=0
```

The signed increment truncates toward zero. Flooring the entire interpolated
shade, or flooring a negative increment, gives different descending samples.
The reference performs integer rational sampling rather than copying the
renderer’s repeated-subtraction, register-carried or bulk-fill paths.

The 4×4 Bayer rank is constructed from two binary 2×2 ranks using screen
coordinates `x&3,y&3`. At shades 0..16, it selects bitmap code `10` when rank
is below the shade and `01` otherwise. Above 16 it selects `11` below
`shade−16`, otherwise `10`.

For each logical pixel the standard C64 bitmap byte offset is:

```text
(y//4)×320 + (x//4)×8 + 2×(y%4)
```

Its two-bit field is replaced, then the same field is written at offset+1 for
the duplicated physical row. Starting from captured baseline memory preserves
uncovered pixels and neighboring partial-byte fields. Calls replay in their
captured order. The single object’s verified `$BF/$01` material is applied to
each touched cell `(y//4)×40 + x//4`; this independently predicts Screen RAM
and physical Color RAM changes as well as bitmap writes.

| Accepted result | Sample 1 | Sample 2 |
|---|---:|---:|
| Captured spans | 168 | 161 |
| Logical pixel writes, including overlap | 3,780 | 2,429 |
| Unique logical pixels | 3,611 | 2,330 |
| Actual sample shade range | 2..32 | 2..32 |
| Descending nonconstant spans | 83 | 138 |
| Singleton spans | 0 | 8 |
| Full bitmap bytes compared | 8,000 | 8,000 |
| Screen / physical Color RAM bytes compared | 1,024 / 1,024 | 1,024 / 1,024 |
| Differences in all three arrays | **0** | **0** |

Both actual baseline bitmaps happen to be zero. The reference still uses
those captured baselines and does not claim an independent dirty-clear proof.
There are 28 and 7 input intervals eligible for the uniform-byte classifier;
the internal branch is not individually traced. The same scalar result covers
whichever optimized path actually produced the accepted bytes.

Meaningful wrong models fail on each captured sample:

| Wrong reference | Sample 1 differing bytes | Sample 2 differing bytes |
|---|---:|---:|
| Constant start shade over each span | 1,044 | 766 |
| Floor the negative signed increment | 180 | 254 |
| Shift Bayer Y phase by one | 1,786 | 1,062 |
| Omit the duplicated physical row | 966 | 630 |

## Palette, lighting boundary and committed VIC body

For sample 2, the target is bitmap `$6000` and screen `$5C00`. Publication has
`drawbuf=1`, VIC bank `$4000`, `$D018=$78`, `$D011=$3B`, `$D016=$18`, and sprites
disabled. Bitmap, attributes and physical Color RAM agree at completed,
published and visible endpoints. Endpoint equality is not a claim of no
transient writes.

The frozen VIC snapshot decoder supplies the native palette-index raster. In
the standard 40-column bitmap mode, the accepted visible body is raster
lines **51..250**, X **32..351**. All **64,000 bytes** match the expanded scalar
reference, SHA-256
`64188fa22c47c41d9bdd7b200c3b71f6cc028e41f2057bb8d79c5038a0cfaa1c`.
Borders, other raster lines and a complete 312-line field are not included.

The first raw vertex-shade sample also matches target arithmetic from the
**observed light-cache inputs**: cache `(-95,79,-114)`, intensity 10, raw shades
`[0,32,20,25,0,0]`. Whole angle bytes are zero, but the observed cache differs
from the conditional identity case; this acceptance uses the captured cache
without attributing the difference. The scene note’s
conditional identity targets are not forced onto native state. The later raw
shades are retained with their instantaneous targets; their earlier temporal
slew history is unobserved. No independent full illumination transform or
geometry proof is added here.

## Cost and replay

| `$1153 → $08D4` interval | Cycles | PAL refresh equivalents | PAL model seconds |
|---|---:|---:|---:|
| Sample 1 | 577,195 | 29.365 | 0.5858 |
| Sample 2 | 509,905 | 25.941 | 0.5175 |

The official PAL model uses 19,656 cycles per refresh and 985,248 cycles per
second. These intervals include projection, collection, drawing, IRQs and VIC
stalls, but exclude earlier vertex lighting/clearing, waiting/presentation and
the rest of the loop. Their inverse costs are only upper bounds of about
1.71/1.93 such intervals per second. They are **not measured delivered FPS**.
The slow SDK prototype does not establish a practical speed improvement over
our existing fast vectors, or physical-hardware/Turbo6510 performance.

Replay with our passive code only:

```sh
rtk proxy python3 research/3dvibe64-native/pixels.py
```

It reads the closed case, pinned build proof, emitted products and frozen
parsers. It writes only `pixel-analysis/`: the receipt and checked producer,
decoded span records, scalar bitmap/palette-index artifacts, two previews and
the native committed-index crop. No SDK, assembler, emulator or downloaded
program is executed.

Latest continuation: `sample2-visible.vsf`, PC `$0FB1`, clock **10,276,311**,
line **252/raw 3**. The rejected first-publication attempt remains a retained
failure. Broader geometry/lighting correctness, additional workloads and useful
stock-C64 speed remain separate work.
