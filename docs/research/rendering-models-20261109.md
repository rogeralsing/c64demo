# Three different ways to avoid drawing a whole new bitmap

These examples move different work into assets, tables, generated code or
display control.

| Engine | Stored or prepared work | Work during display | Current evidence |
| --- | --- | --- | --- |
| The Lab colored ball | 56 projected poses, 2,173 edge commands | Scale/translate, XOR boundary rasterization, vertical fill and per-cell attributes | One pose's complete committed viewports independently matched |
| Aloft captured mask-cell engine | Generated OR/AND cells, lookup tables; actual 200-call list admitted as input | Four glyph stores per line and timed `$D011` changes; forty RAM glyph bytes feed 200 different lines | Two full 200-row bodies matched; the colored body independently recovers all 8,000 fetched bytes |
| Perpetual Fragility | Spatially arranged animation data and compiled timing schedule | AGSP changes the bitmap view; cached matrix data limits attribute work | Author explanation, linked PRG header and finite offset arithmetic; released code/pixels not yet reconstructed |

[The Lab's pipeline](the-lab-ball-pixels.md) still draws and fills pixels on
the C64. Its captured body costs 87,209 machine cycles. Prepared 2D geometry
does not imply prepared bitmap frames or demonstrated live 3D projection.

[Aloft's reconstructed body](aloft-pixels-continuation-20261109.md) uses RAM as
a scanline staging area. The same forty bytes are read repeatedly after
software changes only the relevant boundary/state bytes. The measured
pre-call/return interval is 12,612 PAL machine cycles, about 64.2% of a PAL
field. This is a specialized, timed source path, not proof of a general 3D
renderer or delivered animation FPS. Its motion-to-call-list generator remains
an input boundary.

The [WIZ reading](row-cache-and-wiz-20261109.md) concerns a different tradeoff:
animation phases occupy space in one wrapping bitmap. That construction is
useful when the phases and their overlap are designed together. It does not
provide independent storage for arbitrary large filled frames. The new
arithmetic checker proves the declared offset cycle, not the original PRG's
graphics output.

The practical lesson is to identify which work the effect removes: geometry
projection, rasterization, attribute updates, whole-buffer clearing, or copying
an image to a new position. The remaining work and its constraints still need
measurement in the actual display arrangement.
