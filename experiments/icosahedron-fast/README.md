# Fast solid icosahedron

The full-frame solid renderer combines specialized projection, rotation, bounds, and culling paths.

```sh
sh build.sh
sh run.sh
```

This folder supplies its own build/output directory while importing the
existing implementation from `src/icosahedron-fast.asm`. It does not fork that source.
The runnable program is `build/example.prg`. See the
[renderer documentation](../../README.md) for the exact display contract,
measured cadence, and existing verification commands.

## Product-table sphere counterpart

This is also our existing counterpart to Tower Power's reusable-product
geometry idea. Its twelve-vertex spherical mesh has twenty solid faces.
The C64 performs live rotation and perspective; two 256-byte tables supply
products for fixed model coordinates, while the remaining products execute
at runtime. These tables contain arithmetic, not prepared animation poses.

Tower Power's N2 engine uses a larger 16 KB product table, orthographic
projection and a different outside-color convention. This example retains
our model-specific Q6 arithmetic, perspective and palette instead of claiming
to reconstruct that production. See the
[Tower sphere analysis](../../docs/research/tower-power-n2-math.md).

The current built PRG is byte-identical to the independently checked
[512-presentation native run](../../build/fast-solid-verification/full/verification.json),
SHA-256 `ffe0e19041b5fd11ca8060326cb11206b336adc71ea1b8b2d688e8e99428fd0b`.
That proof covers both output buffers, all runtime arithmetic tables, 256
distinct canvases, and 31 VIC screenshots at two PAL fields per presentation.
