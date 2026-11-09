# The Lab: the colored polygon ball is a bitmap effect

Research date: 9 November 2026. This resolves the new reference from
[the supplied recording](https://www.youtube.com/watch?v=7fmAprTVE9Y): the
colored ball between two cyberpunk portraits. It is the already captured
side-two file-20/file-22 speech-balloon vector stage. The retained original
native screenshot shows the same ball and framing at another pose, with
“TEN!”. This is a scene match, not an exact frame-index match to the supplied
image. The [earlier detailed analysis](the-lab-mms.md) contains the source,
native capture and arithmetic results for this engine and the separate
open-panel cube.

![Original native ball capture](../../build/research/the-lab/side2-live-01/mms-frame-complete.png)

## Why the object can exceed sprite dimensions

The polygon object is drawn into a **multicolor bitmap**, rather than assigning
one ordinary hardware sprite to each polygon. Retained native I/O observations
at original render-completion PC `$2265` read `$D011=$3B`, `$D016=$D8`,
`$D018=$79` and `$DD00=$C0`, with background zero. Those mode bits establish
bitmap plus multicolor operation. The displayed bitmap is `$E000` in bank
`$C000`, with screen attributes at `$DC00`; the other buffer is switched by
the original IRQ. The `$D018` readback includes its forced bit 0.

The drawing window is **192 physical pixels wide by 192 rows**, containing
96 horizontal multicolor samples. An expanded ordinary sprite's 48-pixel
width therefore does not constrain this object. Neither the number of visible
polygons nor the number of visible colors establishes a sprite allocation.
This conclusion concerns the polygon renderer; it does not claim the entire
scene or every overlay is sprite-free.

## What the C64 computes, and what is prepared

The released file-22 stream contains **56 prepared poses and 2,173 six-byte
edge commands**, occupying 13,094 bytes. A command carries projected X
endpoints, slope bytes, starting Y, a two-bit transition code and an attribute
operation/palette index. These are prepared 2D boundaries and slopes. This
consumer does not perform a demonstrated live 3D rotation, projection or
generic visibility sort. It also does not play back complete bitmap frames.

At runtime the engine scales/translates the edge coordinates, samples the
edges, XORs transition markers into a column-oriented buffer, constructs
color attributes, and fills a backbuffer. The column buffer is 24 byte-columns
by 192 rows, **4,608 bytes**. Each byte carries four two-bit multicolor lanes.
The filler accumulates XOR down each column, using the same toggle-on /
toggle-off principle discussed for our own vector renderer.

An initializer generates **2,304 bytes of fill code**, covering both bitmap
banks. Each row cell is `EOR ($45),Y; STA absolute,X; INY`. Runtime endpoint
patching bounds the work to the relevant column ranges. The earlier native
frame 52 at `$BFE8` has 34 commands; its 4,608 marker bytes and all 3,040 observed
bitmap stores agree with the recorded independent arithmetic checks.

## How it displays more than three polygon colors

Ordinary multicolor bitmap uses background `$D021` plus **three colors per
8×8 physical-pixel cell**. Two local colors come from the screen byte's
nibbles, and the third comes from Color RAM. Different cells may select
different triples. Therefore the whole ball can use many C64 palette colors,
even though each cell has the usual local restriction.

The engine performs attribute work alongside the XOR boundaries; it does not
use one fixed global three-color palette for the entire object. Consequently,
our small character-mode renderer cannot reproduce the color freedom merely
by choosing more two-bit XOR codes. It needs per-cell attribute management
or a different display arrangement. The palette-priority trick proved for
the open-panel cube is bounded; it is not a general depth buffer.

Brush's [author comment on CSDb](https://csdb.dk/release/?id=262146&show=review)
says the turn-disk floppies and truecolor vectors are drawn using different
techniques, with no color cycling. That statement alone does not establish
live 3D geometry. The actual edge stream supplies the more specific result
above. Other vector and dithered-sprite parts in The Lab remain distinct.

## Fresh verification and remaining limits

The new [passive recheck](../../build/research/lab-polygons-20261109/verify.py)
pins the previous inventory and source, original decoded file 20/file 22,
native RAM, screenshot, mode observations, supplied reference and current
CSDb retrieval. It reparses the 56-pose stream and independently recomputes
the captured pose's 4,608 marker bytes and 2,304 generated filler bytes. All
match. It executes no emulator, CPU interpreter or original demo code.

The [receipt](../../build/research/lab-polygons-20261109/accepted-01/ball-recheck.json)
and [fresh replay](../../build/research/lab-polygons-20261109/root-replay-01/ball-recheck.json)
are byte-identical. The prior 3,040-store original-code/native comparison is
retained evidence, not rerun by this passive check. This adds no complete
color/committed-scanout oracle, measured FPS or arbitrary-pose 3D proof.
The official site returned 403 during this refresh; that result is retained
beside the fetched CSDb page.

Legacy custody remains explicit: the ball's `side2-live-01` monitor log has
no snapshot restore. The separate open-cube `side2-targeted-02` run restored
its own original entry snapshot after a wrong speech breakpoint, then used
the corrected original call. Its result must not be described as an
uninterrupted run without restores.

Reproduce in a fresh output directory:

```sh
rtk proxy python3 -B build/research/lab-polygons-20261109/verify.py --output build/research/lab-polygons-20261109/<fresh-directory>
```
