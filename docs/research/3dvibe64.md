# 3Dvibe64: what the shading code actually does

The useful result is an ordinary 6510 Gouraud fill with **33 quantized shade values**, three multicolor pixel codes and a 4×4 ordered threshold matrix. It computes vertex shades, interpolates them and converts each sample into bits. The matrix stays fixed to the screen; the interpolated lighting field changes with the object. This is more than placing a checker pattern over a face, but it is not 33 simultaneous VIC-II colors or a hires framebuffer.

A particularly reusable idea is its **uniform-span classifier**: for the selected Bayer row, if the packed byte at the two endpoint shades is equal, every shade between them produces that same byte. The renderer can use a masked bulk fill instead of sampling every pixel. The independent proof below establishes that property for this matrix and shade mapping. It establishes no speedup or complete rendered-frame result.

## Access, revision and custody

Starting source: [Retromind article, 2026-10-01](https://www.retromind.it/blog/3dvibe64-gouraud-textures-and-raycasting-in-commodores-8-bit-world/). Its actual project link is [Librologica/3Dvibe64](https://github.com/Librologica/3Dvibe64). On 2026-11-08 the default branch resolved to **`b19df459b7efe50d514b59fe876c0bc7c326c5b4`**, committed 2026-10-30. The newest listed release was [v1.15.1](https://github.com/Librologica/3Dvibe64/releases/tag/v1.15.1), published 2026-10-30.

All seven HTTP acquisitions returned **200**. Original URLs, response hashes and byte counts are in `build/research/3dvibe64/proof.json`. Key pins:

| Retained input | Bytes | SHA-256 |
|---|---:|---|
| Article HTML | 149,291 | `ae042a4686db5ce71daae8bd3d9f5191863e47f684e6b0aa63606edbf88dca51` |
| Commit source tar | 1,399,558 | `fbccc522110b1fe4beb85ba1378183f70b5d8fc76227c2482306cd5354b4c998` |
| Official `3Dvibe64_1.15.1_source.zip` | 1,619,950 | `1ba034569a0beff013800322bc6c8f1134894ab6e13eb3bb2bb055482a668cbc` |
| Official `SHA256SUMS.txt` | 93 | `4b3862d59d24a719c20aa83d1f21c43ec66a4892da6fa997f4f630127090ec00` |
| `work/build-3Dvibe64.ps1` | 978,375 | `b03d5d7ce6e9e5af85d47c04950841da96f1f3e6dc7b50f5c26a1f97c5bb7e70` |
| `work/mode7-kernel.asm` | 4,258 | `bdf4f341dc8d2826effed58a5e1d315bbe371a7815f2257a6c4c1fb253e9b010` |

The ZIP matches both the published checksum text and release-API SHA-256 digest. Its 387 entries contain **zero PRGs**, and no `examples/` or `validation/` tree. Current distribution is a source SDK; external polygonal scenes, artwork and raw native evidence are not bundled. Engine templates, tables and font inputs remain. Eighteen selected source/doc members match byte-for-byte between the pinned tar, release ZIP and retained source copies. Their Git blob hashes also match the retained tree entries; this is not a claim that every archive member was compared.

Software's retained `LICENSE` identifies **PolyForm Noncommercial 1.0.0** and the required 3Dvibe64 attribution. Documentation has a separate license. These are research inputs, not a blanket permission to copy the engine into another project.

No upstream scripts, tests, binaries, generators or build tools were run. No assembler, emulator, native process or shared research index was changed. Upstream files were treated only as source/data.

## Host work versus 6510 work

The large PowerShell builder contains assembly templates and scene specialization. In the [pinned builder](https://github.com/Librologica/3Dvibe64/blob/b19df459b7efe50d514b59fe876c0bc7c326c5b4/work/build-3Dvibe64.ps1):

* `2704–2788`: the host computes area-weighted smooth normals, applies a crease-angle threshold, normalizes/quantizes components to −63…63 and emits separate shade vertices at hard creases. This changes lighting data, not silhouette geometry.
* `7633–7642`, `37680–37724`, `37765–37770`: the host prepares eleven 64-entry intensity tables, vertex metadata and Bayer lookup bytes. A particular generated program also specializes code, memory placement and scene data.
* `13184–13253`: runtime prepares the object-space light using fixed-point matrix products and saturated sums.
* `13257–13354`: runtime forms three signed normal/light products per shade vertex, subtracts a prepared center-dot term, clamps the nonnegative high-byte domain and reads the intensity table. Later updates approach the target by at most four levels; the first `$ff` sentinel adopts the target directly.
* `26652–27089`, `31542–31562`: edge and scanline integer DDAs transport/interpolate shade; the fill then writes multicolor bytes.

This supports a normal/light-derived dynamic vertex-shading mechanism. It does not prove physically correct photometry, all normal/light transforms, culling, clipping, materials or complete scene output. No actual generated PRG was bound by this audit. The additional legacy-plus coherent/material source transformers were read but not executed or accepted as a complete emitted pipeline.

## Bayer fill and the bounded proof

The actual matrix appears both as a host literal and an assembly `.byte` array (`37690`, `33850`):

```text
 0  8  2 10
12  4 14  6
 3 11  1  9
15  7 13  5
```

At shade `s = 0…16`, a threshold below `s` selects code `10`, otherwise `01`. At `s = 17…32`, a threshold below `s−16` selects `11`, otherwise `10`. Code `00` remains background. Thus shade 0 is entirely `01`, shade 16 entirely `10`, and shade 32 entirely `11`. Each intermediate level changes one of the sixteen tile samples. Perceived brightness still depends on the palette assigned to those codes; density is not a luminance calibration.

The ordinary Mode 6 byte-span flag is enabled at `2000–2001`. Its current LUT is **four rows × 33 packed bytes = 132 bytes**. The scalar/Mode 7-compatible layout has **four rows × 33 shades × four phases = 528 bytes**. The historical [Mode 6 report](https://github.com/Librologica/3Dvibe64/blob/b19df459b7efe50d514b59fe876c0bc7c326c5b4/GOURAUD-MODE6-REPORT.md) describes the older 528-byte stage; do not carry that footprint forward as the current ordinary byte-span layout.

The runtime selects a lookup row with logical `y & 3` (`27007–27031`). The four pixel-pair masks are `$c0,$30,$0c,$03`; aligned spans combine them and write a whole byte, while partial bytes preserve the untouched pairs (`31300–31427`). The standard renderer is 160×100 logical pixels expanded to 320×200 display pixels (`9002`, adjacent-row stores at `31379–31382`). Its 4×4 threshold phase is in logical pixel units, not four hires display pixels.

Run our own passive producer from the repository root:

```sh
rtk proxy python3 research/3dvibe64/inspect.py
```

It reads pinned retained files, imports no upstream code, performs no network access and writes only ignored `build/research/3dvibe64/` outputs. Independent checks pass:

| Check | Exhaustive domain | Result |
|---|---:|---|
| Stored matrix versus recursive Bayer construction | 16 ranks | Exact permutation/match |
| Two-band shade mapping | 33 × 16 samples | 33 distinct tiles, exact pigment counts |
| Partial-pair replacement versus decode/replace/repack | 135,168 old-byte cases | No differences |
| Equal packed endpoint bytes imply equal interior bytes | 628 equal pairs, 1,724 interior checks | No differences |
| Integer scanline DDA versus closed-form rational sampling | 173,151 spans, 14,025,231 samples | No differences |
| Light table versus exact nearest-integer `2×dotHi×intensity/15` | 704 entries | No differences |
| Temporal target clamp versus ±4 formulation | 1,122 states | No differences |
| Default affine UV address versus row-major indexing | 65,536 byte pairs | No differences |

The DDA domain is shade endpoints 0…32 and nonzero span extents 1…159. Its largest accumulated error before reduction is 190, so the checked scalar arithmetic never loses an eight-bit carry. The producer proves that manually translated arithmetic against an independent formula; it does not execute 6510 instructions or validate geometry setup, zero-length spans, the optional coherent shortcut, memory addressing or complete scanout.

The uniform classifier compares the two packed endpoint bytes (`31254–31280`). Monotone shade interpolation and the verified interval property justify its bulk path (`31452–31527`). This is an exact simplification within the checked LUT mapping, not a generic rule for arbitrary dither palettes or pattern tables.

Derived data for later emitted-byte checks:

| File | Bytes | SHA-256 |
|---|---:|---|
| `bayer-packed.bin` | 132 | `08fb32589e23f8fe20c88beff0b2dad16510ff21581c1442bf0467b3f7ee84a9` |
| `bayer-scalar-layout.bin` | 528 | `1d14d8136d6b869331bdb6dd9ff0ff09d805853e51165b32fe05e1ab47a27752` |
| `light-levels.bin` | 704 | `4f8ef9b43a3cde7bab67e55b2cbb61aa215ce6a2e08126bd4a23c1d1fe00b912` |

These are independently reconstructed tables, not bytes dumped from a running C64.

## The 16×16 texture claim, precisely

The default unlit [Mode 7 kernel](https://github.com/Librologica/3Dvibe64/blob/b19df459b7efe50d514b59fe876c0bc7c326c5b4/work/mode7-kernel.asm#L109) computes `(V & $f0) | (U >> 4)` and reads one byte from a page-aligned texture. Exhaustive checking gives `16×floor(V/16)+floor(U/16)`, always 0…255. Each texel address has 256 possible fractional UV inputs. The host validator requires 16×16 textures, 256 codes from 1/2/3 and exact unsigned Q4.4 UVs (`work/mode7.py:29–45,79–88`).

The kernel interpolates U/V with quotient/remainder increments; it does not interpolate neighboring texel colors. The default path is affine and nearest-neighbor. This audit accepts its address arithmetic only: no actual texture asset, final page placement, clipped triangle, lit compositor or complete rendered sample was checked. Current SDK also has an optional bounded projective Q8 path; the article's affine description must not be expanded into a claim that current Mode 7 has no projective option. See pinned `MODE7.en.md:30–38,85–102`.

## Stock versus acceleration, and how to continue

The runtime source is 6510 assembly, with modern-host preparation. That is a compatibility statement; it does not establish enjoyable speed at roughly 1 MHz. The article explicitly motivates expensive Gouraud/texture work with acceleration. Current qualification describes separate VICE Turbo6510 PAL 1×/20×/64× observations, with raw scenes/native evidence external to this package. Those author results were not replayed here. No stock FPS, 20/64 MHz speed, hardware result or unchanged accelerated image is claimed from screenshots or source arithmetic.

The next concrete test needs a newly authored minimal scene because the old example paths are external. A future build/native check should:

1. Keep this exact SDK revision. Start with ordinary legacy Mode 6, `high-basic-v2`, PAL, normal viewport, fixed camera and `NoFpsOverlay`; use a small curved mesh such as an eight-triangle octahedron with crease angle 180° and a light placed to produce varying vertex shades. A planar face with uniform normals would not exercise the intended gradient. Preserve the source scene and full build configuration.
2. Build with the documented PowerShell/64tass toolchain. Compare the emitted Bayer/intensity bytes with the three derived files, record actual layout and every applied source transformation, and bind the resulting PRG before running it.
3. At stock timing, capture transformed/shade vertices, edge/scanline endpoints, output bitmap and actual VIC palette state. Compare bounded committed pixels with an independent scalar reference. A screen-fixed dither phase is expected; the scalar lighting field must follow the object.
4. Only after correctness, collect actual render-cycle/frame-delivery measurements for that scene. Treat 1×, 20× and 64× as separate cases with explicit emulator/CPU settings. Native visual parity, physical hardware and general engine performance remain separate acceptance steps.

Do not substitute this source proof for those missing build/runtime observations, or copy the current 1.15.1 qualification numbers into our vector demo's CPU budget.
