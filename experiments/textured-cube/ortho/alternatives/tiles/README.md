# Packed midpoint-origin tile candidate

This candidate renders the common live orthographic cube, with one textured
face and five flat faces. It uses the common quad geometry, exact half-open
coverage spans, animated 16×16 texture and four-color 4×4 physical samples.
No projected poses or completed frame images are prepared on the host.

## Tile rule

Each 8×8 physical character contains a 2×2 block of logical samples. For its
even logical anchor `(ax, ay)`, the sampler calculates the Q8 affine UV origin
once. Its integer U/V parts select a packed tile. The four relative sample
positions `(j,k)` use:

```text
U = floor(anchor_u / 256) + floor((j*duDx + k*duDy + 128) / 256)
V = floor(anchor_v / 256) + floor((j*dvDx + k*dvDy + 128) / 256)
```

Both coordinates wrap modulo16. This represents the anchor fractions by the
midpoint128/256 instead of retaining their exact values. The top-left sample
remains its exact integer origin. Each coordinate differs from direct Q8
sampling by at most one wrapped texel: the exact and quantized carries each
belong to `{0,1}`, so their difference belongs to `{-1,0,+1}`.

The declarative `reference.py` implements only that formula; it does not replay
the assembly's row stepping or tile cache. Parent verification independently
checks geometry and the coordinate error bound against its exact Q8 target.
This is a quality tradeoff: arbitrary fractional-origin accuracy is reduced.
The geometry, sample resolution and animated source texture remain unchanged.

## Actual tile reuse

A 256-entry cache stores packed four-sample character codes by integer UV
origin. A matching 256-byte tag table is cleared at every visible-face call.
A code is generated lazily on the C64 when first used; later cells with that
origin reuse its single byte. No cache generation is moved outside measured
frame work. No cache survives logically across geometry/texture updates.

Coverage is separate from sampling. Exact top/bottom span intervals build a
four-sample mask for each edge cell; interior cells use mask255. The masked
cached code is ORed into the hidden screen, preserving every sample belonging
to another face. The complete model still uses the common full 80×50 canvas.

## Memory and build

- Candidate code: `$8000..$83EF`.
- Packed tile cache: `$A000..$A0FF`.
- Per-pose cache tags: `$A100..$A1FF`.
- Private zero-page work: `$F6..$F9`.
- Common geometry/display/texture code remains imported from the shared main.

```sh
rtk proxy sh experiments/build-one.sh /Users/rogerjohansson/git/asynkron/c64demo/build/experiments/orthographic-competition/20261108T172619Z/tiles
```

## Development check

All64 RAM-only CPU frames match the declarative formula and exact visible
coverage. The source index error is at most one wrapped texel per axis for
every covered textured sample. The compiled midpoint candidate SHA-256 is
`99505eb2bd963cce0d40b191525da3bbdb0c5f07c308f91dd0e4133a369dfba9`.
The observed nominal CPU frame cost is77,084..133,302cycles, mean103,368.33.
These numbers exclude VIC/IRQ costs and publication waiting; parent native
VICE measurements are the deciding performance evidence.

The bounded development receipt is `build/cpu-sampler-proof.json`. It uses
actual projected vertices as inputs; independent runtime geometry, complete
native screenshots and frame cadence belong to the parent verifier.
