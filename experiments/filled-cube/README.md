# Solid XOR cube

A live opaque cube uses exact edge markers and a vertical XOR-prefix fill in a multicolor character canvas.

```sh
sh build.sh
sh run.sh
```

This folder supplies its own build/output directory while importing the
existing implementation from `src/filled.asm`. It does not fork that source.
The runnable program is `build/example.prg`. See the
[renderer documentation](../../README.md) for the exact display contract,
measured cadence, and existing verification commands.
