# Masked bobs and mirrored background restoration

This original PAL C64 example demonstrates the masked plotting and background
restoration techniques studied in [No Bounds](../../docs/research/primary-2026-notes.md).
It is a small teaching implementation, not a reconstruction of that production.

```sh
sh build.sh
sh run.sh
python3 verify.py
```

The C64 moves a 16×16 patterned circular bob over a 320×200 hires background.
Each plot combines the existing background with separate AND and OR masks.
Before moving, it restores the bob's old rectangle from immutable artwork.
The stored artwork contains only the left 160 pixels: the right half is read
from reflected byte columns with reversed bit order. Thus 4,000 background bytes
restore an 8,000-byte display without retaining a second complete bitmap.

Motion runs on the C64 using two reusable sine tables. Positions are aligned
to eight-pixel columns; vertical movement advances by individual pixels.
The display uses white ink and dark gray paper. The background and bob share
the bitmap palette, so this example does not demonstrate independent bob colors.

This implements the restoration contract and opaque masked composition.
No Bounds' larger character canvas, scene-specific hidden-row schedule,
streaming loader, and release assets are separate cases.

Rendering starts at PAL line 240. It restores behind the previous scanout and
finishes the new bob before the next scanout reaches it. Motion updates once
per PAL field, or 50 times per second. This schedule belongs to this bounded
motion path; arbitrary larger bobs or other positions need a new timing check.

The native verifier checks all 8,000 bitmap bytes for 258 successive states,
covering the entire motion period and buffer-free wraparound. Its independent
pixel model constructs circular coverage directly rather than reusing the
assembler's masks. Four complete 320×200 VIC screenshots also match with zero
differences. Reports, RAM, monitor transcripts and a preview remain under
ignored `build/verification/`; see the [receipt](build/verification/receipt.json).
Verification owns and closes its VICE instance.

Build output is `build/example.prg`; the assembler also writes debug symbols.
The shared builder accepts `JAVA` and `KICKASS_JAR`; the launcher accepts `VICE`.
