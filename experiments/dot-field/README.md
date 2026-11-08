# Moving dot field

This original PAL C64 example plots a waving perspective-like grid from
**256 point requests per update**, organized as sixteen rows of sixteen points.
It is an educational counterpart to the architecture documented for
*Second Reality* / Smash Designs' CA part. No production code or artwork is
included, and it is not a reconstruction of that scene.

## Build and run

```sh
sh build.sh
sh run.sh
```

Requires the project's existing KickAssembler and PAL VICE installation.
Output is `build/example.prg`.

## Prepared data and runtime work

Assembly prepares one 256-entry sine profile, bitmap-address tables and
row-specific horizontal spacing/origins. It also expands sixteen plotting
routines, each containing sixteen point calculations and cached clear stores.
These are reusable code and profiles, not stored animation frames.

The C64 adds the current phase to each point's profile offset, reads the wave,
calculates current X/Y coordinates, computes a multicolor-bitmap address and
writes its point mask. A phase advances by five after each displayed update.
The changing coordinates and bitmap stores happen on the C64. No arbitrary
live 3D rotation, projection matrix, polygon filling or hidden-surface removal
is claimed; the expanding row spacing supplies the depth impression.

## Cached clearing and collisions

Each point patches the address operand of its corresponding absolute clear
store. On the next update, each row clears its sixteen previous addresses,
then plots its new sixteen points. Clearing and drawing are interleaved by
row, rather than a global clear followed by a global plot.

Point stores deliberately replace a complete byte. Multiple requested points
may occupy different two-bit lanes in the same byte; the final store keeps
only its own lane. A later row's cached clear can also erase a freshly drawn
byte. Consequently, 256 requested points do not promise 256 endpoint samples.
This makes the original architecture's ordering constraints visible instead
of silently changing the operation to OR accumulation.

The program schedules an update every four PAL fields. It draws directly
into one bitmap, so intermediate rendering is visible; this is not an atomic
framebuffer swap. The subsequent wait exposes the completed endpoint.

## Provenance

See [the CA investigation](../../docs/research/second-reality-ca.md) and
[the coverage analysis](../../docs/research/second-reality-ca-coverage.md).
The production uses a different multicolor-character atlas, 992 plot requests,
runtime-expanded code and its own prepared profiles. This example uses a
standard multicolor bitmap and assembly-expanded code to isolate the reusable
point/cache mechanism.

## Native verification

```sh
sh build.sh
python3 verify.py
```

The verifier needs Python 3 with Pillow and the existing `x64sc` executable.
Set `VICE` to select another VICE path. It starts and closes its own emulator;
the spatial oracle requires no previous native captures or research cache.

Verified in PAL VICE on 8 November 2026. An independent spatial model predicted
the initial empty bitmap and all ordered clear/plot operations for 32 consecutive
updates, at phases 0 through 155 in steps of five. Every native endpoint matched
all 8,000 bitmap bytes: **256,000 byte comparisons, zero mismatches**.

Five native screenshots at updates 0, 1, 7, 15 and 31 matched the complete
320 × 200 visible image: **320,000 pixel comparisons, zero mismatches**.
The checks included 217 later-row clears of current plots and 350 point-lane
replacements. Native endpoints retained between 229 and 250 point lanes from
the 256 requests, agreeing with the defined whole-byte assignment behavior.

Measured rendering took 23,281–23,408 elapsed PAL cycles in this sample.
The 31 observed presentation intervals were all four PAL fields after accounting
for the breakpoint's beam phase. Complete RAM dumps, screenshots, the monitor
transcript, command and program hash are retained under ignored `build/native/`.
The owned VICE process exited after capture.

This verifies 32 consecutive updates and five completed scanouts. It does not
cover all 256 phases, intermediate drawing scanout, other VIC-II revisions or
physical hardware.
