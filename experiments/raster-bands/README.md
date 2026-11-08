# Raster bands

A small PAL starter prints a title and draws six color bands with raster polling.

```sh
sh build.sh
sh run.sh
```

This folder supplies its own build/output directory while importing the
existing implementation from `src/main.asm`. It does not fork that source.
The runnable program is `build/example.prg`. See the
[renderer documentation](../../README.md) for the exact display contract,
measured cadence, and existing verification commands.
