# Host-prepared double vectors

This standalone entry demonstrates the broad pipeline documented for
Next Level's `doublevec`: the host transforms and resolves two objects,
then the C64 renders supplied visible fragments with edge/span work.
See the [source survey](../../docs/research/lines-and-vector-fill.md).

```sh
sh build.sh
sh run.sh
```

It deliberately shares our own
[prepared-fragments renderer](../prepared-fragments/README.md). The two
entries produce the same program; this is a separate runnable entry for
the documented pipeline, not another renderer implementation or an original
Next Level playback. The build compiles the shared generator/source and
checks byte identity with the shared entry.

Our host prepares sixteen poses of two overlapping cubes and visible
convex fragments. The C64 performs exact edge walks and span filling, reuses
interior glyphs, and allocates private boundary glyphs. This character
allocation policy differs explicitly from Next Level's original filler.
Geometry and visible-fragment resolution are host work, not runtime 3D.

The shared [native proof](../prepared-fragments/build/verification/receipt.json)
covers all sixteen poses and wraparound, complete font/matrix/screenshot
output, copy-on-modify and a real allocator-capacity input. The readable
implementation publishes every 34–40 PAL fields, about 1.4 poses/s.
See the shared README for the independent oracle and precise limitations.
