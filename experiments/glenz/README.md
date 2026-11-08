# Glenz

Two interpenetrating tetrahedra contribute colored XOR polygons. Equal overlap contributions cancel, producing dark windows. Runtime geometry and perspective run on the C64.

```sh
sh build.sh
sh run.sh
```

This folder supplies an independent build/output directory while reusing
the existing renderer in `src/glenz.asm`. It does not copy that renderer.
The native output is `build/example.prg`. See the
[renderer documentation](../../README.md) for the full mechanism, update
cadence, arithmetic contracts, and existing verification commands.

This is our own implementation. It is not a byte-for-byte reconstruction
of a released production discussed in the research archive.
