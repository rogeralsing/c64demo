# Character-reuse rotate/zoom

An original standalone PAL C64 counterpart of the glyph-reuse idea documented
for **The Impossible Thing**. It rotates, scales and translates a repeating
16×16 one-bit texture over a full 40×25-character screen.

```sh
sh build.sh
sh run.sh
python3 verify.py
```

The installed Kick Assembler builds `build/example.prg`. The launcher selects
PAL at normal speed. Native verification uses the existing VICE, Python and
Pillow setup; it installs no dependencies.

## Runtime representation

The C64 generates all 256 glyphs for every new image. Each glyph corresponds to
one integer texture origin and contains a transformed 4×4 sample patch. Every
sample becomes a 2×2 physical pixel block in an ordinary hires character, so
the full screen contains 160×100 logical samples. The matrix selects one
origin glyph for each screen cell.

Only the 16×16 source texture and 32 pairs of scalar Q4 sine/cosine coefficients
are prepared at assembly time. Their magnitude varies to add zoom. There are
no stored screen matrices, glyph animation frames or prepared projected poses.
The font and matching matrix are double buffered and published together at
a PAL frame boundary. Both rotation and translation advance after publication.

The runtime uses these signed Q4 gradients:

```text
angle = phase * 2*pi/32
scale = 12 + 4*sin(2*angle)
c = round(scale*cos(angle))      e = round(scale*sin(angle))
a = -e                          b = c

local[r,s] = pack(c*s + a*r, e*s + b*r)
matrix[y,x] = pack(4*c*(x-19) + 4*a*(y-12) + 3*phase,
                   4*e*(x-19) + 4*b*(y-12) + 5*phase)
pack(u,v) = (floor(u/16) mod 16) | ((floor(v/16) mod 16) << 4)
sample(g,r,s) = texture[(g + local[r,s]) mod 256]
```

This factorization intentionally reuses one fractional sampling pattern for
all glyph origins. The final packed-index addition is a 256-entry ring:
overflow from the U nibble can increment V. Consequently, the result is the
declared integer glyph sampler, rather than an exact continuous affine image.

## Relation to the investigated intro

The example preserves the central trade: runtime generation of 256 transformed
glyphs followed by a cheap character-origin matrix. It uses original texture
artwork, one-bit hires samples, Q4 arithmetic, 32 moving phases and ordinary
loops. The investigated 2003 intro uses two-bit texture values, Q8 arithmetic,
generated writers and additional carry/borrow shortcuts. Its code and artwork
are not copied here. This is a teaching counterpart, not a byte-exact recreation
or a reproduction of its music, presets or 4 KB packaging.

See the [original mechanism investigation](../../docs/research/impossible-thing.md)
and [affine sampler analysis](../../docs/research/impossible-thing-affine.md).

## Verification

`verify.py` runs an owned VICE instance and compares native output with a
separate direct integer-coordinate oracle. Expected pixels do not come from
the assembled code, generated lookup tables or captured font/matrix data.
The oracle checks all 32 moving phases and the wrap to phase zero. It compares
every generated glyph and matrix byte, then checks six complete 320×200 VIC
canvases against the corresponding independent pixel images. It also records
native presentation clocks so the actual update cadence is explicit.

Reports, raw RAM captures, screenshots and an animation remain under ignored
`build/verification/`. Verification stops only its own emulator. Physical
hardware behavior and equivalence to the original intro remain outside scope.

The checked run passed 33 presentations, including all 32 moving phases and
wraparound. All 2,048 font bytes and 1,000 matrix bytes matched per presentation;
six complete 64,000-pixel canvases also matched. Captured presentations were
six or seven PAL frames apart, averaging 6.625 frames per update, about **7.6
updates per second**. This straightforward loop-based counterpart does not
claim the original intro's stated 25 fps. See the generated
[receipt](build/verification/receipt.json) and
[animation](build/verification/rotozoom.gif).
