# Painted cube

An opaque rotating cube carries inset triangular marks on its faces. The C64 constructs and projects each visible marking, then fills body and marks in one XOR-prefix pass.

```sh
sh build.sh
sh run.sh
```

This folder supplies an independent build/output directory while reusing
the existing renderer in `src/painted.asm`. It does not copy that renderer.
The native output is `build/example.prg`. See the
[renderer documentation](../../README.md) for the full mechanism, update
cadence, arithmetic contracts, and existing verification commands.

This is our own implementation. It is not a byte-for-byte reconstruction
of a released production discussed in the research archive.
