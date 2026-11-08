# Interlaced icosahedron

The shared icosahedron renderer alternates physical row parities and retains the matching buffer history.

```sh
sh build.sh
sh run.sh
```

This folder supplies its own build/output directory while importing the
existing implementation from `src/icosahedron-interlaced.asm`. It does not fork that source.
The runnable program is `build/example.prg`. See the
[renderer documentation](../../README.md) for the exact display contract,
measured cadence, and existing verification commands.
