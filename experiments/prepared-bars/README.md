# Prepared bar paths and angle-specific character sets

Five cyan bars tilt through five prepared angles while three colored diamond
sprites orbit in front. Character graphics draw the bars; hardware sprites
provide a separate foreground beacon animation.

## Build, run, verify

```sh
rtk proxy sh build.sh
rtk proxy sh run.sh
rtk proxy python3 verify.py
```

The shared KickAssembler wrapper writes `build/example.prg`. Playback uses
PAL VICE. Verification uses the repository's existing Python/Pillow and VICE
tools and closes its own emulator after the bounded run.

## Prepared data and runtime work

The five hires character sets each contain 24 reusable bar fragments and a
blank glyph. Their slopes are `-2,-1,0,1,2` vertical pixels per eight-pixel
character. A fragment is selected by the line's sub-character Y phase and
whether the cell lies above, on, or below its center row. Font slots occupy
10,240 bytes in the ROM-free `$4000` VIC bank; most glyphs remain blank.

Prepared data contains five 256-sample baseline-Y paths, one 256-sample angle
path, reusable column slope offsets, and one 256-sample X/Y sprite orbit.
The three sprites reuse that orbit at different phase offsets. Their three
24×21 diamond patterns are original artwork. No complete screen matrices or
animation frames are stored.

For each new image, the C64 clears the hidden screen matrix, reads the current
path coordinates, selects and places the required line glyphs, restores the
screen's sprite pointers, and publishes the completed matrix/font selection
at the top border. It also updates the three hardware sprite positions.
Character Color RAM remains cyan throughout. Five bars span 256 pixels and
remain separated; individual glyph fragments never need arbitrary overlap
composition. Screen matrices at `$4000` and `$4400` alternate.

This implementation deliberately uses double buffering. Its update cadence
must be measured from the runnable program; it does not inherit a 50 fps
claim from the original production or its viewers.

## Verification scope

The default native run observes 258 completed updates, covering the complete
256-phase motion path and wraparound. Selected phases exercise all five fonts
and both screen matrices. The verifier independently constructs glyph pixels,
prepared path coordinates, full matrix-cell pixels, sprite masks, sprite
positions and priority composition. It compares complete 320×200 VIC screenshots
after scanout. Register checks also cover bank/font selection, Color RAM,
sprite pointers, colors, expansion and high-X bits. Actual PAL update intervals
are recorded rather than inferred from a loop count.

Each run preserves RAM dumps, native screenshots, expected images,
`animation.gif`, and `verification.json` under
`build/verification/<UTC timestamp>/`. The GIF contains the sampled native
frames, with elapsed emulated time between samples.

The 8 November 2026 run passed all 258 phase/cadence observations, including
wraparound. Eighteen sampled native images covered all five fonts and both
matrices: **18,000 matrix bytes and 1,152,000 screenshot pixels**, with no
differences. All 10,240 font bytes, 192 sprite bytes and 2,304 prepared path
bytes matched their independent models. Update intervals were
**58,962–58,974 PAL clocks**, or three video fields per update, approximately
16.7 updates per second.

The retained [receipt](build/verification/20261108T070323.582562Z/verification.json)
and [native animation](build/verification/20261108T070323.582562Z/animation.gif)
record that bounded run.

## Relation to Codeboys & Endians

The [owning research note](../../docs/research/frontier-2026.md) preserves
Mahoney's explanation: prepared horizontal-line coordinates traverse five
angle-specific charsets, while multicolor sprites draw separate vertical
lines. It also records the limits of that author-only source investigation.

This example contains new code, paths, glyphs and sprites. It demonstrates the
prepared-coordinate and reusable-angle-glyph choices, with independent sprite
imagery. It does not reproduce the release's seven horizontal/four vertical
line composition, roughly 80 sprite slopes, white intersection priority,
top-to-bottom single-buffer schedule, or unacquired original implementation.
