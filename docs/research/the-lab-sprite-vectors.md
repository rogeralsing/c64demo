# The Lab: green patterned polygons on an expanded-sprite plane

The native green checker-polygon stage uses **eight one-bit sprites, expanded
in both directions and multiplexed vertically**, with the normal character
display disabled. Its two 2 KB drawing slices are contiguous vertical parts
of one canvas. They are not odd/even scanline fields.

The visible drawing plane is **192 × 147 logical one-bit samples**, expanded
to **384 × 294 physical pixels**, at PAL rasters 15–308. Each double-buffered
allocation has room for 192 × 168 logical samples; the last 21 rows are not
selected by this seven-band display schedule.

This identifies the actual display mechanism of the captured green polygon
stage. It is separate from the later speech-balloon [MMS multicolor-bitmap
engine](the-lab-mms.md), and from what can be inferred from a scaled screenshot.

## Original native route and device evidence

The original side-two program reached `$2A05 JSR $3420` with all 17,630 observed
file-15 output bytes matching. It then ran normally through `$3420 JMP $7C89`.
The correct repeated control boundary is `$7CA4`; the generic span entry `$59B0`
was not hit because the running path uses cached/specialized span dispatch.
No PC or payload substitution was used to reach this stage.

At 32 controller updates, the screenshot shows a small green checker triangle
partly beyond the left edge. Restoring the original initialized snapshot and
advancing 74 updates captures a large checker triangle, clipped at the top,
with front pose 72 and completed back pose 73. This proves the stage and dither
style without claiming the exact same pose as the supplied video image.
The captured device state at raster 263 is:

| Register | Native value and meaning |
| --- | --- |
| `$D011` | `$83`: normal display disabled at this raster. |
| `$D015` | `$FF`: all eight sprites enabled. |
| `$D016` | `$C8`; horizontal border-control writes occur elsewhere. |
| `$D017` | `$FF`: all eight sprites expanded vertically. |
| `$D01C` | `$00`: one-bit sprites, rather than multicolor sprites. |
| `$D01D` | `$FF`: all eight sprites expanded horizontally. |
| `$D027–$D02E` | Low nibbles all 13: light green. |
| `$DD00` | Low bits zero: VIC bank `$C000`. |

The standard VIC sprite pointer, expansion and display-control meanings are
defined in [Commodore's VIC-II documentation](https://www.zimmers.net/anonftp/pub/cbm/documents/chipdata/6567_vicII_preliminary.pdf).
The 32-update evidence is preserved under
`build/research/the-lab/side2-targeted-02/`, including
`span-after-032-fields.png`, `ram-span-032.bin` and restorable pre-initialization
and initialized VSFs. The raw RAM SHA-256 is
`8504f35ee08086d534ac2ef8644d0e31dcdc73e1b7ba35d77ed1a45c94ca4fa4`.
The larger pose is saved as `span-checker-pose072.png`,
`ram-span-update074.bin` and `span-checker-pose072.vsf`; its RAM SHA-256 is
`f63a4f22e68df183eb49648e21f8c8dc6d2a405f43c60338580149f281537757`.
The legacy screenshot filename says “fields”; the memory mapping below shows
that these controller updates are double-buffered poses, not interlaced rows.

## How the two slices reach the screen

The display-switch routines install seven complete sprite-pointer tables:
`$C3F8`, `$C7F8`, `$CBF8`, `$CFF8`, `$D3F8`, `$D7F8`, `$DBF8`.
The raster handlers select them through `$D018 = $06,$16,…,$66`.

For the `$F000` drawing buffer, the eight sprite pointers for band 0 are
`$C0,$C4,$C8,$CC,$D0,$D4,$D8,$DC`. Within each four-band slice, the pointer
increases by one for the next 21-row sprite block. Band 4 switches to the
second slice at `$F800`. The other drawing buffer uses `$E000/$E800` instead.

| Band | Physical rasters | Logical rows in complete plane | Slice and local rows |
| ---: | --- | --- | --- |
| 0 | 15–56 | 0–20 | First slice, 0–20. |
| 1 | 57–98 | 21–41 | First slice, 21–41. |
| 2 | 99–140 | 42–62 | First slice, 42–62. |
| 3 | 141–182 | 63–83 | First slice, 63–83. |
| 4 | 183–224 | 84–104 | Second slice, 0–20. |
| 5 | 225–266 | 105–125 | Second slice, 21–41. |
| 6 | 267–308 | 126–146 | Second slice, 42–62. |

The last band uses sprite Y register 11 at physical raster 267. The raster-248
handler arms that low-byte Y, and the raster-266 handler selects the seventh
pointer table. Treating Y=11 as a new band near the top would produce the wrong
layout. The raster-286 handler programs Y=15 for the next cycle, before a
low-byte Y=11 match could happen again near the next frame's top.
The next cycle returns to logical row zero at raster 15.

For logical byte column `c` and local slice row `y`, the span renderer writes:

```text
sliceBase + (c // 3) * 256 + (c % 3)
          + 64 * (y // 21) + 3 * (y % 21)
```

The pointer-selected sprite fetches produce exactly that same address for all
24 byte columns and every displayed row. Each 2 KB slice has 2,016 usable pixel
bytes plus 32 sprite-padding bytes. A complete displayed buffer uses 3,528
pixel bytes; the remaining allocated storage includes padding and the unused
last sprite band. No 320-pixel hires-bitmap assumption is involved.

## What the actual geometry consumer receives

The inspected controller cycles 164 pose indices. Its ordinary path selects
the first or second slice from `$6F/$70`, then consumes a triangle list for each
half. A header's low nibble counts first-slice triangles and its high nibble
counts second-slice triangles. A triangle has six already-projected X/Y bytes
and a material/edge-side byte; its coordinates are local to the selected slice.

Of those 164 indices, **118 use ordinary triangle packets**: 171 triangles in
the first slice and 167 in the second, summed across the sequence. Their maximum
local Y values are 83 and 51 respectively. The packet consumer starts at
`$9041` and advances sequentially only on these ordinary indices.

The remaining **46 indices** are looked up through the table at `$9EA0` and
redirected to compressed scanline runs. The original run consumer at `$7F8A`
receives, separately for each half:

- A run count.
- For each run, material, height, starting Y, and the first inclusive left/right
  span endpoints.
- For subsequent rows, a small endpoint-delta dictionary index, or `$FF`
  followed by a new absolute left/right pair.

All 46 packets parse to their exact next stored packet address; the last ends
at `$BFC2`. These runs also have maximum local Y 83/51, so the currently inspected
sequence does not draw into the undisplayed tail of the second slice.

This is concrete evidence of prepared screen-space triangles and prepared span
runs in this consumer. It still draws into sprite memory at runtime; it is not
a stream of complete sprite bitmap frames. It does not expose 3D vertices,
depths or normals, and it does not establish a live 3D transform for this exact
164-pose sequence. No claim is made about the unavailable producer or exporter.

Brush's separate statement about his computed vector part remains an author
statement about the part he describes. The [recovered note](the-lab.md) also
distinguishes differential animation, transitions and span/stencil vectors.
Those descriptions must not be extended to every adjacent stage solely because
it uses the same sprite plane or a similar green pattern.

## Patterns and span behavior

The material table has sixteen four-row density patterns. Material 8 is the
50% `$AA/$55` checker; other patterns provide sparse dots and intermediate
densities. The first slice uses material-row phase zero, the second phase four.
All 88 stored rows per material repeat every four rows, so both phases retain
the intended pattern in this table.

The renderer ORs masked pattern bits into partial endpoint bytes and directly
stores the pattern into complete interior bytes. In a one-byte span the two
endpoint masks are combined. That operation alone is not a general opaque
polygon overwrite at partial bytes; complete scene behavior also depends on
the controller's clearing and stencil data. The separate
[span primitive audit](the-lab-binary.md) checks 25,408 inclusive-span cases
against independent masks and sprite-shaped addresses.

## Reproduce the plane and run checks

```sh
rtk proxy build/research/tower-power/cpu-venv/bin/python research/the-lab/span_plane.py
```

`research/the-lab/span_plane.py` writes the ignored receipt
`build/research/the-lab/span-plane-analysis/plane.json`. It checks:

- The original pointer-table setup for both buffers, starting after its real
  raster handshake. All 112 pointer bytes and **7,056 displayed byte addresses**
  match the independently derived two-slice mapping.
- Original raster-handler constants for seven bands and the high-raster
  handoff of the last band. This is a source/layout check, not a timer emulator.
- All ordinary triangle records and all compressed runs, including packet
  bounds, materials and visible row ranges.
- The original compressed-run renderer, including its actual cached fast span
  paths, across **all 46 packets**. It executes **335,758 instructions** and every
  resulting 4 KB buffer matches independent decoded spans, pattern masks and
  address calculations.
- Independent decoded-run output for **native front pose 72 and back pose 73**.
  Every displayed byte matches: 3,528 per buffer, **7,056 total**, including zero
  bytes throughout the complete visible plane. The comparison omits only
  sprite padding and the undisplayed allocation tail, by the explicit pointer
  mapping above; no displayed pixel byte is excluded.

The isolated original-CPU run checks start with zeroed drawing buffers. The
two-pose comparison separately validates actual native frame contents. These
checks do not establish every frame's dirty-clear/stencil lifecycle, presentation
timing, or every triangle rasterization case. No VICE or hardware protocol is
run by this script.

The receipt also ranks packet draw area to choose useful native poses. Poses
72–74 have the largest material-8 checker area, about 2,460–2,510 logical samples
per packet. The largest total draw-area packets are around 104–106 and use other
densities. These are triangle-area/run-width sums, which can include overlap
and clearing material zero; they are not final opaque screen-area measurements.
At the initialized controller boundary, after `N` updates the completed back
pose is `N−1` and displayed front pose is `N−2`, because the buffer flip precedes
the next render. Restoring initialization and advancing 74 updates therefore
targets displayed pose 72 without changing the original program state.
