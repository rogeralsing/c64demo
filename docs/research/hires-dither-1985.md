# An earlier hires shading reference, with a different rendering scope

The original article [Räumliche Grafik auf dem C 64](https://www.64er-magazin.de/SH8504/graphics.html),
by Richard Rylander and Christoph Sauer in *64'er Sonderheft 4/85*, pages
96–108, describes hires shading through an 8×8 threshold matrix and an
alternative random-dot routine. Brightness becomes pixel coverage.

Its `FACET` interface accepts one shade for a triangle, so that interface is
flat shading rather than interpolation between vertex intensities. Its curved
shape routines calculate shading per point, but the article explicitly limits
those primitives to front views without rotation. These examples therefore
provide no evidence of fast rotating Gouraud objects.

The useful follow-up is the assembly's `SHADE`/`RSHADE` implementation and its
integer arithmetic. Recover those routines and test their threshold convention
before treating the printed matrix as a drop-in replacement for another filler.

This is a primary-source reading lead, not a build, disassembly, performance
measurement or demonstrated speed improvement. The
[retrieval record](../../build/research/3dvibe64-profile/primary-reading/graphics-1985-retrieval.json)
pins the downloaded HTML's digest and metadata; the full HTML was not retained.
The current measured Gouraud study remains separate.
