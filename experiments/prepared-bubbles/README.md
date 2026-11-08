# Prepared 3D bubbles with C64 decompression

An original counterpart to the prepared animation in Censor Hires Bubbles.
The [research note](../../docs/research/frontier-2026.md) distinguishes its
Blender-produced frames from runtime 3D rendering. Our host generator traces
an implicit three-body surface, calculates normals and lighting, dithers it,
and packs each 96×42 image into eight hires sprites. It creates 25 different
512-byte frames. All geometry, artwork, encoder and assembly are our own.

```sh
sh build.sh
sh run.sh
python3 verify.py
```

The build uses Python's standard library and the shared Kick Assembler
wrapper. The generator compresses 12,800 bytes into 3,640 bytes using the
small byte-command format called `lzo` by Oscar64. This is **not standard
LZO1X**. Literal runs and short backward matches, including overlapping
copies, follow the format visible in the official
[Oscar64 decoder](https://github.com/drmortalwombat/oscar64/blob/012e3128489fec3c2d2b1640c8d700cd05ae6cb2/include/oscar.c).
No Oscar64 compiler, downloaded code, original assets or research cache is
required to build or run this example.

The C64 expands the next frame in its main thread, outside raster IRQs,
into the inactive 512-byte sprite buffer. A raster-20 IRQ publishes all
eight pointers after expansion finishes. X/Y expansion presents the
96×42 image as 192×84 pixels over an original ECM character pattern.
There is no runtime metaball, lighting, rotation or projection calculation.

The [native verification receipt](build/verification/verification.json)
checks all 25 compressed streams independently, then 51 consecutive actual
C64 presentations, including two full cycles and wraparound. Both front
buffer observations match the prepared bytes through hidden-buffer work.
All 3,264,000 viewport pixels match an independent sprite/ECM composition.
Normal decompression takes 12,920–15,020 observed PAL clocks; complete
frames publish every PAL field, about 50/s. Observed breakpoint intervals
vary by a few clocks with instruction completion.

[Animation preview](build/verification/prepared-bubbles.gif) and full native
screenshots remain beside the receipt. The retained VICE session exits 0.
This example demonstrates prepared 3D, live expansion and coherent display;
it does not reproduce Censor's full intro, soundtrack or original artwork.
