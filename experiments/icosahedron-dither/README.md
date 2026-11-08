# Dithered icosahedron

The interlaced renderer compares fixed screen-aligned checker materials with the vertex-lit shading experiment.

```sh
sh build.sh
sh run.sh
```

This folder supplies its own build/output directory while importing the
existing implementation from `src/icosahedron-dither.asm`. It does not fork that source.
The runnable program is `build/example.prg`. See the
[renderer documentation](../../README.md) for the exact display contract,
measured cadence, and existing verification commands.
