# The Impossible Thing: the actual affine sampler

Research date: 7 November 2026. An independent integer/texture model now predicts **all 2,048 newly written glyph bytes and all 1,000 screen bytes** in the captured `select-01 → select-02` update. It also predicts the texture pointers, patched screen-column operands, row offsets and scalar transform state. This adds a mathematical oracle to [the earlier original-instruction replay](impossible-thing.md); the new model does not execute 6502 instructions.

**The captured preset is static.** Its U, V and zoom phase increments are all zero, and the input/output phases are `(16,16,0)`. This is native validation of one fixed initial pose. It is not moving-angle, other-preset or whole-intro coverage. The source formulas below describe additional paths, but those paths are distinguished from the captured comparison.

The subject remains the **2003 Smash Designs/Oxyron intro**, not the 1997 Second Reality renderer.

## Independent inputs and byte contracts

[affine.py](../../research/impossible-thing/affine.py) reads the original decoded texture, stored profile and preset tables, plus the captured input phases and active preset index. The source image is checked against its producer's byte count/hash and the frozen decoder output hash. Captured RAM is checked against the corrected native receipt. Native output pointers, gradients, glyphs and screen bytes are comparison targets, not inputs to the oracle.

The host uses ordinary integer division, whole-word arithmetic, direct texture indexing and byte packing. It does not use the generated glyph code, a CPU emulator, the prepared packed-texture tables or the previous replay's output as its rendering oracle.

| Predicted native data | Bytes | Result |
|---|---:|---|
| Entire new charset at `$E000..$E7FF` | 2,048 | Exact |
| Entire new matrix at `$F000..$F3E7` | 1,000 | Exact |
| All glyph-local texture pointers | 32 | Exact |
| All patched screen-column ADC operands | 40 | Exact |
| Final row/remaining-column scratch array | 40 | Exact |

Phase, divisor, sign flags and all four gradient pairs also match. The [receipt](../../build/research/impossible-thing/affine-analysis/affine-proof.json) preserves every mismatch list, all empty, alongside the complete model inputs and intermediate arrays. It pins the original-source, corrected-native and script identities. Earlier sources and receipts remain unchanged.

## Phase table and four Q8 gradients

The stored 64-byte profile at `$2855..$2894` is unsigned **0..63**. Initialization mirrors it and repeats it:

```text
S(k) = profile[k mod 128]         when k mod 128 < 64
       profile[127-(k mod 128)]   otherwise
```

Thus the actual sampled wave has a **128-phase period**, repeated across the initialized lookup pages. The oracle independently checks all 512 bytes at `$0600..$07FF`. These are literal stored samples resembling a biased cosine; this batch does not infer the historical floating-point formula used to create them.

The original preset tables at `$1F00/$1F40/$1F80` supply three byte increments. Each image advances the corresponding byte phase modulo 256, then samples:

```text
D = 16 + S(zoom_phase)

U0 = S(u_phase)       V0 = S(v_phase+32)
U1 = S(u_phase+32)    V1 = S(v_phase+64)
U2 = S(u_phase+64)    V2 = S(v_phase+96)

a = Q(U0-U1, D)      b = Q(V0-V1, D)
c = Q(U2-U1, D)      e = Q(V2-V1, D)
```

`(c,e)` is the horizontal texture increment and `(a,b)` the vertical increment. Values are signed 16-bit **Q8**, meaning raw integer divided by 256. Their coefficient byte pairs are stored **high:low**, unlike the little-endian texture pointers:

| Gradient | Original pair |
|---|---|
| `a` | `$10:$11` |
| `b` | `$14:$15` |
| `c` | `$02:$03` |
| `e` | `$06:$07` |

The divider at `$2721` returns `floor(256*n/D)` for the source domain `D=16..79`. It is not a generic proof for arbitrary byte divisors. The callers' negative conversion is particularly important:

```text
Q(delta,D) = floor(256*delta/D)                delta >= 0
             -1-floor(256*(-delta-1)/D)        delta < 0
```

The code complements the negative numerator and both quotient bytes without adding one. This **one's-complement shortcut** differs from ordinary signed division: `delta=-1` produces raw `$FFFF`, or `-1/256`, rather than `floor(-256/D)`.

Across the broad integer operand domain `delta=-63..63, D=16..79`, an exact rational host sweep of 8,128 pairs finds an error relative to `delta/D` greater than `-1/256` and at most **`15/256` texel per logical step**. Positive inputs truncate downward; negative inputs receive the shortcut's upward bias. This is a domain bound, not an all-angle native sweep or a complete-image error bound.

For the captured pose:

```text
phase increments = (0,0,0)       phases = (16,16,0)
U = (54,9,10)                   V = (9,10,55)
D = 79                         deltas = (45,-1,1,45)
(a,b,c,e) = (145,-1,3,145)      raw Q8
```

Independent U and V phases permit more than a rigid rotation. The exact source contract is the four sampled gradients above; treating every preset as an ideal orthogonal rotation would add an unsupported constraint.

## The 256 reusable glyphs

A character covers **4×4 logical samples**, expanded into an 8×8 physical glyph at 2×2 sampling. Each glyph-origin code `g=0..255` uses the same sixteen local offsets `L[r,c]`. With the original 256-byte two-bit texture `T`:

```text
sample(g,r,c) = T[(g + L[r,c]) mod 256]
glyph_byte(g,2*r) = glyph_byte(g,2*r+1)
                 = sum(sample(g,r,c) << (6-2*c), c=0..3)
```

This directly predicts the full 2 KB charset. The oracle reads `T` from original `$2755..$2854`, masks each value to two bits, and packs the four lanes itself. It does not consume the shifted lookup tables that the original generated code reads.

The local offsets come from the integer parts of 16-bit coordinates. Their low/high nibbles are packed as U/V. Two implementation details prevent replacing the source with a naive `floor(c*x+a*y)` formula:

- A negative horizontal U or V gradient starts that component at raw `$FF00`, a **minus-one-texel origin bias**, rather than zero.
- The U horizontal helper `$2226` retains the incoming unsigned carry between whole-word additions. Its V counterpart `$222F` explicitly clears carry every time. Each new local row restores its origin with ordinary carry-cleared addition of `a` or `b`.

The host models these as whole-word sums and carry values, not as a sequence of LDA/ADC instructions. For the captured pose, the sixteen exact packed offsets are:

```text
00 00 10 10
F0 00 10 10
F1 01 11 11
F1 01 11 11
```

The local-pointer checks cover both nibble packing and the four bit-lane table bases `$3800/$3A00/$3C00/$3E00`.

## Character origins and the packed screen index

The matrix spans 40×25 characters. Its coordinate center is character **`(19,12)`**. Four logical samples separate character origins, so the source doubles each relevant Q8 gradient twice.

For rows, ordinary carry-cleared addition/subtraction gives:

```text
R[y] = pack((y-12)*4*a, (y-12)*4*b)
pack(u,v) = ((u >> 8) & 15) | (((v >> 8) & 15) << 4)
```

For positive columns, origin words are `(x-19)*4*c` and `(x-19)*4*e`, reduced to 16 bits. The left-hand columns differ: the original negative-column loops retain borrow between iterations. For either unsigned 16-bit operand `s=(4*gradient)&65535`, the stored words for increasing distance left of center obey:

```text
w=0; borrow=0
t = w-s-borrow
w = t mod 65536
borrow = 1 if t<0 else 0
```

The last positive-column comparison clears carry for its next addition; the negative loops' DEX/BPL sequence does not. The host preserves that distinction when constructing `C[x]`.

Finally, each screen row starts with carry clear and executes this packed-byte recurrence:

```text
carry = 0
total = R[y] + C[x] + carry
screen[y,x] = total mod 256
carry = floor(total/256)
```

Carry therefore crosses neighboring cells within a row. The code is **not** independently adding and wrapping U and V nibbles. Low-nibble overflow can increment V, and byte overflow can add one to the following cell's code. Likewise, glyph sampling adds its local packed offset to `g` in one 256-entry linear ring. The duplicated texture pages make that addition safe without changing its addressing rule.

The complete source sampler factorizes as:

```text
texture_index(y,x,r,c) = (screen[y,x] + L[r,c]) mod 256
```

This factorization explains both the speed and the approximation: every character reuses the same local fractional pattern, indexed only by an integer texture origin.

## Comparison with a declared continuous affine reference

The source does not preserve each character origin's fractional position for its local sampling. To quantify the difference without inventing an intended output, the script defines a separate reference on the **160×100 logical sample grid**. Let `X=x-76`, `Y=y-48`; these offsets correspond to the source's character center. The first reference uses the same Q8 gradients but floors only once:

```text
u = floor((c*X+a*Y)/256)
v = floor((e*X+b*Y)/256)
reference_index = (u mod16) + 16*(v mod16)
```

A second reference replaces the Q8 gradients with the exact rational sample differences divided by `D`. Both references use independent 16×16 coordinate wrapping, rather than the original packed-index carry rules. Neither is asserted to be the author's intended sampler.

| Declared reference, captured pose only | Different indices / 16,000 | Different texture codes / 16,000 | Maximum cyclic U/V difference, in texture texels |
|---|---:|---:|---|
| Same Q8 gradients, one final floor | 13,397 | 6,088 | 2 / 2 |
| Exact rational sample differences | 13,085 | 6,007 | 2 / 3 |

These are source-coordinate differences, not screen-pixel displacement, analog error or a native-rendering mismatch. Different indices can select the same texture code.

For the first declared reference, neighboring coordinate increments differ across **1,964 of 3,900 horizontal character-boundary pairs** and **2,775 of 3,840 vertical boundary pairs**. The receipt also retains within-character comparisons. This measures the captured sampler's block/floor/packed-carry behavior against that explicit reference; it does not count visible seams in a VIC screenshot.

## Scope and reproduction

```sh
rtk proxy python3 research/impossible-thing/affine.py
```

The script uses only the Python standard library and saved evidence. It writes [predicted-charset.bin](../../build/research/impossible-thing/affine-analysis/predicted-charset.bin), [predicted-screen.bin](../../build/research/impossible-thing/affine-analysis/predicted-screen.bin), all 16,000 logical texture indices and the [proof receipt](../../build/research/impossible-thing/affine-analysis/affine-proof.json).

The captured test covers preset 0, divisor 79 and one fixed transform. It exercises negative `b`, but not negative horizontal `c/e` paths, moving U/V/zoom phases, other divisors or preset transitions. The general formulas are source-derived; the byte-for-byte native acceptance applies only to the declared captured half-image. No additional CPU or native execution was performed, and no prior frozen receipt was rewritten.
