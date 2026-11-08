# Pong cube

The rotating opaque cube carries a live Pong-style animation on its front
Z− face.

```sh
sh build.sh
sh run.sh
```

This folder supplies its own build/output directory while importing the
existing implementation from `src/pong.asm`. It does not fork that source.
The runnable program is `build/example.prg`. See the
[renderer documentation](../../README.md) for the exact display contract,
measured cadence, and verification results.

The bounded 64-pose motion uses an independently audited `$1a` visibility
mask for X+, Y+, and Z−. Unrolled surface mapping, projection and fixed body-edge
dispatch preserve the exact image. Exact narrow-edge division, cached material
masks and the fast fill-column loop reduce the cost further. The
[706-presentation profile](../../build/pong/optimizations/20261108-boundary/final-profile/profile.json)
measures 33,423.39 mean rendering cycles, 2.08% below the preceding mapping
build, while retaining 25 fps. The [native check](../../build/pong/optimizations/20261108-boundary/final-verification/verification.json)
passes all 706 presentations and 705 game updates against the independent
pixel and game reference. A [baseline comparison](../../build/pong/optimizations/20261108-boundary/final-comparison.json)
confirms identical images, game state, geometry, boundary markers, and buffer
history across all 706 presentations. The standalone PRG is byte-identical to
the verified root build. See the [optimization notes](../../docs/pong-boundary-optimization.md)
for the CPU breakdown and memory cost.

Run these checks from this folder after building:

```sh
python3 ../../verify-pong.py build/example.prg --labels build/main.sym --audit --output build/audit
python3 ../../verify-pong.py build/example.prg --labels build/main.sym --fixtures --output build/fixtures
python3 ../../verify-pong.py build/example.prg --labels build/main.sym --frames 706 --output build/verification
```
