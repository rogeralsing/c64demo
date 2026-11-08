# Texture transitions inside the XOR fill

The selected implementation builds the texture's start, stop and color-change
markers before the existing `src/xor-fill.asm` prefix pass. That single pass
paints both the solid cube and its textured face. The final texture is already
present when `xorFill` returns.

```sh
# From experiments/textured-cube:
sh build.sh xor-texels
python3 xor-texels/verify.py
sh run.sh xor-texels
```

Geometry, source texture and image output match the preceding
[pixel-overlay hybrid](../xor-hybrid/README.md): live Q10 yaw/pitch/roll,
64 poses, a 16×16 animated plasma texture, and a 64×128 logical canvas in a
128×128 physical window. Each logical sample occupies 2×1 physical pixels.

## One prefix pass

The ordinary cube edges first describe the solid materials. The textured
Z-minus face has material selector 3. For each covered column, texture
corrections contribute these additional XOR transitions:

```text
face entry:     textureColor ^ 3
color change:  previousTextureColor ^ nextTextureColor
face exit:     lastTextureColor ^ 3
```

Zero deltas are skipped. A black texel produces the required cancellation
of material 3. The face exit returns to the ordinary solid-material field,
so adjacent faces retain their colors and exact shared-edge ownership.

The markers live in the real prefix fill's immediate operands. Exact column
coverage reuses the shared rational-ceiling polygon edge sampler. All
techniques leave both charsets unchanged while preparing markers; only the
subsequent common prefix pass generates the new displayed image.

The existing canonical Q8 UV plane and separable rounding remain identical
to the pixel-overlay baseline. Each coordinate differs by at most one texel
from the combined Q8 plane; that bound is relative to the declared plane from
the first three rounded corners, not an ideal continuous physical UV plane.

## Competing techniques

Three subagents implemented independent column algorithms behind the same
coverage, sampling and marker helpers. Every implementation passed an actual
6502 pipeline check over 64 poses, then 66 normal-speed PAL VICE presentations
and 65 complete native screenshots against the same independent image oracle.

| Technique | Mean updates/s | Texture visible | Texture lookups per 64 poses |
| --- | ---: | ---: | ---: |
| Previous pixel-overlay hybrid | 7.26 | 5.14 | 29,988 |
| Scan every covered pixel for color changes | 6.79 | 4.69 | 29,988 |
| Arithmetic jumps to each next texel boundary | 3.78 | 2.25 | 13,750 |
| **Selected shared row events** | **8.01** | **5.91** | **13,750** |

The winner is about **10.3% faster overall** and **15.0% faster when the
textured face is visible** than the pixel-overlay baseline. Hidden-face jobs
remain about 12.63 updates/s. The exact 64-pose loop averages 8.06 updates/s;
individual jobs take 3–10 PAL fields. The preview preserves measured hold
times, including variable angular speed as rendering cost changes.

Shared row events exploit the separable mapping: a screen row's U/V
contribution is the same for every column. One descending scan records the
next row where that contribution changes. Each column samples its clipped
entry, jumps through those shared events, merges equal neighboring colors
and emits its closing marker. This avoids 54.1% of the pixel texture lookups.
All three techniques emit the same 8,203 nonzero correction markers per loop.

Arithmetic jumps reach the same events, but repeat divisions and fractional
state work in each column. That cost outweighs their saved texture lookups.
The simple scan adds marker preparation while retaining every pixel lookup,
so it also loses to the previous overlay renderer.

## Validation and memory

The selected native run observes exactly **66 entries into the real
`xorFill` for 66 completed images**. It checks all 4,096 real marker operands
before and after adding texture transitions, preserves both prior charsets
until filling, verifies all 540,672 resulting samples, and checks that the
image remains unchanged between fill completion and publication.

The full-loop reference exercises all 256 source texels, including 6,876
black samples. There are no mask gaps, overlapping faces or stale pixels.
Every candidate's final charset and native image match the pixel-overlay
baseline exactly. Runtime relocation, dirty-buffer reuse and upper-border
publication remain checked by the same verifier.

The selected marker core stages at `$1F0A–$2E09` and relocates to
`$E400–$F2FF`; the texture builder stages at `$CC01–$CFC0` and relocates to
`$F300–$F6BF`. Both copies happen before charset clearing. The PRG stops below
mapped I/O. Runtime row/column caches and next-event/spans use `$CD00–$CF7F`.
The real XOR prefix banks and their native return remain at `$4C00–$CC00`.

`build/latest-verification.json` points to the selected proof and frozen
inputs. The retained competition, baseline and comparison receipts are under
`build/experiments/xor-texel-competition/20261108T202118Z/` at the repository
root. The preceding overlay renderer remains independently runnable.

```text
Selected PRG SHA-256 d677059e949eb6a000c009c57b3d105819a39b20ccded0239dc52f44322df7ea
```

## Reproduce alternatives

```sh
# From experiments/textured-cube:
python3 xor-texels/verify.py --folder xor-texels/alternatives/scan
python3 xor-texels/verify.py --folder xor-texels/alternatives/jumps
python3 xor-texels/verify.py --folder xor-texels/alternatives/row-events
```

![One XOR pass including the texture](build/xor-texels-cube.gif)
