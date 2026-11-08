# Candidate C: separable coordinate lookup

The cube keeps the shared live orthographic geometry, exact top-left spans,
80×50 sample image and one fixed textured face. Only UV sampling changes.

Let `(x0, y0) = quad[0]`, and let the shared signed Q8 gradients be `duDx`,
`duDy`, `dvDx`, and `dvDy`. For every covered integer screen sample:

```text
u = (floor(duDx * (x-x0) / 256) + floor(duDy * (y-y0) / 256)) mod 16
v = (floor(dvDx * (x-x0) / 256) + floor(dvDy * (y-y0) / 256)) mod 16
selector = texture[v*16 + u]
```

Each coordinate is either the exact affine Q8 texel or the immediately
preceding texel, periodically. This follows from
`floor(a)+floor(b) = floor(a+b)` or `floor(a+b)-1`, including negative inputs.
No geometry or rendered animation frames are stored.

The affine Q8 plane comes from the first three rounded face corners. The
one-texel bound compares against that plane, not an ideal physical UV plane.
The common geometry retains Q10 precision until final screen-corner rounding;
its rounded convex quads can differ slightly from exact parallelograms.

Every visible-face call runs `prepareOrthoQuad`, then rebuilds the current
column and row contributions from its live quad and gradients. Even and odd
column tables share the destination matrix byte index. A generic 4 KiB table
adds the row U offset modulo 16 without carrying into V; a byte addition
adds the row V offset. Thus the pixel loop has no 16-bit UV accumulators.

Leading and trailing single samples preserve the neighboring packed matrix
lanes. Interior pairs combine the two existing shifted source texture pages.
All table preparation is part of the native frame cost.

Memory: code starts at `$8000`, column tables occupy `$8C00/$8D00`, row
contributions use `$8E00`, and the generic coordinate table is `$9000..$9FFF`.
Private zero page is `$F6..$FB`; the sampler preserves the phase, face index,
quad, live geometry and selected hidden matrix.
