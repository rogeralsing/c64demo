# Wireframe cube

A live rotating perspective cube uses visible-edge culling, generated Bresenham kernels, and a double-buffered hires character canvas.

```sh
sh build.sh
sh run.sh
```

This folder supplies its own build/output directory while importing the
existing implementation from `src/cube.asm`. It does not fork that source.
The runnable program is `build/example.prg`. See the
[renderer documentation](../../README.md) for the exact display contract,
measured cadence, and existing verification commands.
