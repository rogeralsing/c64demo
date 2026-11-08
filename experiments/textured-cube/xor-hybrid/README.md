# XOR-filled cube with a textured face

This variant combines the existing `src/xor-fill.asm` polygon filler with
the live 16×16 plasma texture. The XOR pass draws the complete opaque cube;
a second pass replaces the pixels belonging to the fixed Z-minus face.
Both passes write the same hidden charset before one complete-image flip.

```sh
# From experiments/textured-cube:
sh build.sh xor-hybrid
python3 xor-hybrid/verify.py
sh run.sh xor-hybrid
```

## Display and geometry

The real XOR renderer uses a **64×128 logical canvas** in a **128×128
physical-pixel window**, with **2×1 physical pixels per sample**. This gives
finer edges than the orthographic example's 4×4 samples. Its physical window
is smaller than that example's full 320×200 viewport.

The geometry retains the same Q10 cube basis and Q14 scalar trigonometry.
Yaw, pitch and Z roll are calculated on the C64 for each of the 64 poses.
The cube's half-size remains 14 world units. Projection changes to
`(32 + round(X), 64 - round(2Y))` so both physical axes use the same scale.
Y rounds directly from its high-precision coordinate; it does not double an
already rounded screen coordinate. No geometry poses or image frames are
stored.

## Shared coverage

The ordinary XOR pass assigns selectors 1, 2 and 3 to the X, Y and Z face
pairs. When the textured Z-minus face is strictly visible, its opposite
Z-plus face is hidden. Selector 3 in the raw filled image therefore provides
the exact texture mask for this cube's audited motion.

The overlay replaces each selected two-bit lane, including black texels,
while preserving every other lane in the byte. It does not OR a texture over
an existing solid color. This also preserves the actual XOR filler's edge
ownership: its vertical ceil-crossing convention differs from the earlier
horizontal span renderer's boundary ties.

The texture still uses a single affine Q8 plane from the first three rounded
face corners. Separate row and column contributions round independently,
so each coordinate differs by zero or minus one texel from that declared
plane. The bound is relative to the rounded Q8 plane, not an ideal continuous
physical UV plane. The source texture remains 16×16; the finer output raster
does not increase the number of source texels.

The prefix fill writes the old/current dirty-rectangle union before the next
overlay. Reusing either physical charset therefore removes texture pixels
left by an earlier pose. Presentation waits for the next upper border after
both passes finish.

## RAM layout

The real XOR fill banks occupy `$4C00–$CC00`. Texture pages move to
`$E000–$E3FF` to avoid those banks, with rotation and shader helpers above
`$E400`. Runtime coordinate caches use free RAM at `$CD00–$CFFF`.
The two dynamic charsets stay at `$2000/$2800` and the screen matrix at
`$0400`, as in the original solid renderer.

The PRG itself stops at `$CFE3`; it does not load through mapped I/O.
While the display is blank, startup copies 4,416 staged bytes to
`$E400–$F53F`, then clears both charsets. One staging range temporarily uses
the charset memory; the other uses `$CC01–$CFE3`, which later becomes shader
cache workspace. The prefix fill's native return at `$CC00` remains intact.

The four-color palette is black, blue, cyan and white. Only complete hidden
charset images become visible; the VIC continues scanning at PAL field rate
while the next image is rendered.

## Native verification and timing

The [native proof](build/verification/20261108T195309.741582Z/proof.json)
passes 66 presentations: all 64 poses and wraparound. It checks the actual
4,096 immediate XOR marker operands, their reset after the prefix pass,
both staged runtime copies, both charset histories, every solid-base sample,
every final textured sample, and 65 complete 384×272 VICE screenshots.
The solid-base and final-image comparisons each cover **540,672 samples**.

The 32 textured-face poses exercise **29,988 texture samples**, including
**6,876 black samples** that must erase the base color. Every source texel is
sampled somewhere in the loop. The raw selector-3 mask matches the independent
rational polygon interior, with no silhouette gaps, overlapping faces or
stale pixels outside the current cube.

Normal-speed PAL VICE measures **7.26 complete updates/s** over 65 intervals,
or **7.32 updates/s** for the first complete 64-pose loop. Updates take
3–12 PAL fields. Textured-face jobs average **5.14 updates/s**; hidden-face
jobs average **12.63**. Texture sampling remains the expensive part.
The smaller physical window and finer raster differ from the 4×4 example,
so this is not a comparison at equal on-screen size.

The model retains less than **0.01%** native axis-length error and less than
**0.00683°** axis-angle error. Projected X/Y coordinates stay within 0.51
logical sample per axis of a direct floating-point rigid rotation.
The animation below retains the measured hold time of each pose.

Eight existing solid/textured programs remain byte-identical after the
shared-engine hooks and gradient extraction. The actual `src/xor-fill.asm`
source remains unchanged. Generated receipts, source snapshots and failed
pre-fix border captures remain under `build/`; the final program is:

```text
SHA-256 ac87364d44d2c483ffa3197c2515f8e8a4ff3cb75b3b278f928c03bd76000368
```

![Verified XOR hybrid at measured speed](build/xor-hybrid-cube.gif)
