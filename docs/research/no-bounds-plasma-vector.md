# No Bounds PlasmaVector: fill the color lookup choices

This saved static investigation concerns **No Bounds (2023)**, not a new 2026
renderer. The primary implementation is
[`PlasmaVector.asm`](https://github.com/RobertTroughton/C64Demo-PublicReleases/blob/965807c511e2025b5c5e1ffb2a6235a4efd6ae5b/NoBounds/Parts/PlasmaVector/PlasmaVector.asm),
with the supplied PRG and inputs at the same immutable repository commit,
**`965807c511e2025b5c5e1ffb2a6235a4efd6ae5b`**, dated 25 December 2025.
The production and its 3 June 2023 release are also identified on a credited
coder's [own project page](https://www.elder0010.com/projects/no-bounds/).
This lane makes no individual part-coder attribution beyond those sources.

The user subsequently chose to optimize the Pong cube. Research stops at
the coherent saved state below. No Pong files were changed by this lane.

## What is prepared, and what the C64 calculates

`Cube.bin` contains **256 projected poses**: eight 256-byte coordinate pages
followed by eight more, totaling 4,096 bytes. `FaceVis.bin` supplies one
six-face visibility mask per pose. Runtime `DrawCube` selects those bytes;
it does not transform eight arbitrary 3D vertices in the checked path.
The host producer of those pose/visibility files was not recovered.

The runtime work is still substantial: determine twelve edge XOR colors,
rasterize the selected edges, fill their interior, clear transition operands,
warp three plasma samplers, and update bitmap color attributes.

The unusual optimization is the fill destination. A generated Color RAM
plotter contains an indexed load such as `LDA $0400,X`. The prefix filler
patches **that instruction's high address byte**, selecting a lookup page
`$04`, `$05`, `$06` or `$07`. It does not fill the bitmap with face pixels.
The face selects which color table will supply that character cell later.

The fixed multicolor bitmap selects among three separately animated color
channels: Color RAM and the two screen-byte nibbles. Generated sampler 1
loads an index from `Pattern80-BF.bin`, then a face-selected color page,
and writes Color RAM. Sampler 2 patches sampler 3's `ORA zp` operand to
choose a shifted high-nibble value. Sampler 3 loads its low-nibble color,
ORs that high value, and writes screen RAM. The bitmap itself can retain
its prepared pattern and artwork while its attribute colors move.

These are coarse **character-cell material choices**, not 160,000 native
bitmap pixels or generic transparent polygons.

## Boundary, prefix and reset contract

The line kernels enter generated chains at their first row and temporarily
place `RTS` at the excluded end. Each row writes one XOR crossing marker.
For sorted endpoints `(x0,y0),(x1,y1)`, let `dx=x1-x0`, `dy=abs(y1-y0)` and
`s=sign(y1-y0)`. At row `x0+k`, the source's crossing is:

```text
y0 + s * ceil(((k+1)*dy - floor(dy/2)) / dx),  0 <= k < dx
```

The independent model compares this closed form with the original byte
carry/subtraction recurrence. Equal-row endpoints emit no marker. This
part's coordinate names are transposed relative to an ordinary screen-X
line routine; the first eight coordinate pages advance the row chains.

There are **426 fill cells across 22 rows**. A row starts with `LDA #$04`;
later cells use `EOR #marker`. Each following `STA` patches a color-load
high byte. The generated filler occupies 2,130 bytes at `$C000`; it falls
through directly to 1,279 bytes of generated reset code at `$C852`.
Reset writes retained A=`$04` to each row's first immediate and X=`$00`
to the remaining immediates. Clearing every immediate to zero would break
the lookup-page seed.

The source models check all 256 poses:

| Bounded result | Count |
| --- | ---: |
| Selected visible face instances | 538 |
| Drawn edges | 1,732 |
| Equal-row edges skipped | 62 |
| Exact crossing markers | 12,844 |
| Complete 25×25 material-grid comparisons | 160,000 |
| Generated lookup-page stores checked | 109,056 |
| Nonzero face cells | 62,242 |
| Overlapping opaque face cells | 0 |
| Complete operand-reset passes | 256 |

The edge-based prefix output equals independently assigned opaque face
coverage under this declared integer crossing rule. Every marker stays
within the fixed fill footprint and every row closes to outside page `$04`.
OR markers instead of XOR change **2,977 cells**; omitting the half-`dy`
bias changes **4,847**. This rasterization cannot be replaced by our
renderer's different exact DDA without checking its coverage.

Projected integer face area alone disagrees with the supplied visibility
mask in **73 poses / 90 bits**. All supplied visible faces have consistent
nonzero winding, but hidden bits cannot be regenerated from that shortcut.
The original visibility preparation remains unknown.

## Plasma warp and generated layout

The small sine table is truncated toward zero. Startup converts its samples
to differences plus `$C0`, then patches `AXS` immediates in a pointer generator.
The resulting immediates are **191, 192 and 193**. With A=`$FF`, subtraction
and carry handling advance the source pointer by **65, 64 or 63 bytes**.

For starting map column `n`, horizontal phase `p` and generated column `j`,
the independent telescoping expression is:

```text
$2000 + 64*(n+j) - (sin2[p+j-1] - sin2[p-1])
```

All **113,664 pointer cases** agree with the byte recurrence over 128 used
phases, 24 possible starts and 37 columns. Including the largest checked
vertical offset, addresses stay at or below `$2F0B`, within the supplied
4 KB map. Ignoring the warp changes **103,008 pointer cases**. No sampled
plasma output or runtime duration was measured.

The actual embedded `RowLenTab` sums to **691 cells**, while `NumBlocks`
reserves 692. Source-defined generated kernels therefore leave 8-, 5- and
10-byte gaps before the next reserved routines. Predicted kernel bytes and
all operand addresses are saved, but have not been compared with executed
generated RAM. Final line-chain operand cells 23 and 24 depend on unused,
uninitialized table slots; their values are not invented. The checked poses
never execute those cells as drawing work.

## Concrete supplied bytes and retained failed hypothesis

The supplied `PlasmaVector.prg` is **5,865 bytes**, loading at `$E000`.
The checker binds **971 original bytes**: the full 861-byte sine/color/row
table block, 49 clip-table bytes, and actual line/fill/reset/three-channel
instruction templates. That is a literal-byte binding, not a full source
rebuild or a generated-RAM observation.

An initial asset hypothesis failed: the disabled `MkPattern` formula with
the source's literal 16-byte pattern differs from `CombinedBitmap.map` in
**5,434 bytes**. Its prediction and observation remain under
`rejected-combined-regeneration/`. Reversing each four-byte pattern group
reconstructs **all 8,000 supplied combined bitmap bytes** under the same
mask/OR rule. This identifies the stored relationship, not the historical
edit or tool that produced it.

The C++ picture-attribute crop independently matches both supplied 450-byte
outputs. Its ancillary `RowLength.bin` sums to **669**, so it must remain
separate from the runtime's 691-cell `RowLenTab`.

## Reproduce and continue

```sh
rtk proxy python3 research/frontier-2026/plasma_vector.py
```

The standard-library producer validates the retained acquisition indexes,
**36 acquired HTTP bodies and headers**, and **15 selected immutable Git
blobs**. New bodies, predictions, rejected hypotheses, generated address
ledger and receipt live under ignored
`build/research/no-bounds/plasma-vector-analysis/`. Earlier inputs remain
unchanged under `frontier-geometry-20261108/`.

Current receipt is `plasma-vector-proof.json`. It pins the exact producer,
inputs and results. No downloaded host code, original assembler, original
6502 instructions, VICE or native process was executed. There is no original
disk/payload binding, full displayed-frame proof, physical-hardware claim
or timing measurement in this lane.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Tracked producer | 21,782 | `5e8b69da4e744e9bae4457c0c4a83c7887fc406ddb195ebe2b6dc67e438abe14` |
| `plasma-vector-proof.json` | 14,909 | `11f6cb2276f40338a696a8e3ded9bda4e9a1e63cedaa6d8bf24a1a5aed123447` |
| Supplied `PlasmaVector.prg` | 5,865 | `0c7fcaf10c7c45cef35e185c081e959c48fb321f242fbf05bbb5bf0af180b1f3` |

For a future research continuation, first bind the supplied part and pose
files to the original released disk. Then capture the naturally generated
691-cell color kernels, 426-cell fill/reset code and lookup-page changes.
Compare those bytes and original state transitions before investigating
display publication or estimating benefits for another renderer.
