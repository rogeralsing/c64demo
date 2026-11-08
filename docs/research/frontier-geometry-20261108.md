# SpriteFPP: prepared geometry as a palette of horizontal sprite strips

Research date: **8 November 2026**. This is a new source/asset case in the
research map: **Elder0010's SpriteFPP part from No Bounds (2023)**. It is
separate from that production's previously checked loading, bob restoration,
periodic screen maps and Star Wars font functions. No new 2025/2026 effect
implementation is claimed here; the pinned public source snapshot is from
December 2025.

Elder0010's [own project page](https://www.elder0010.com/projects/no-bounds/)
identifies the production and its **3 June 2023** release. The actual
[`SpriteFpp.asm`](https://github.com/RobertTroughton/C64Demo-PublicReleases/blob/965807c511e2025b5c5e1ffb2a6235a4efd6ae5b/NoBounds/Parts/SpriteFPP/SpriteFpp.asm)
header credits **Elder0010**. The source files, input texture and supplied
part PRG are pinned to commit
**`965807c511e2025b5c5e1ffb2a6235a4efd6ae5b`**, committed 25 December 2025.
This is source-author evidence, not an attribution inferred from a video.

## The geometry representation is prepared row selection

The included Unity project contains a host-side preparation path.
[`RotateEuler.cs`](https://github.com/RobertTroughton/C64Demo-PublicReleases/blob/965807c511e2025b5c5e1ffb2a6235a4efd6ae5b/NoBounds/Parts/SpriteFPP/Unity/SpriteFPP/Assets/Scenes/Rotation/RotateEuler.cs)
rotates source rows, groups their rounded Y positions, chooses a row by Z and
maps its depth to a quantized width. Its output record carries a texture-row
ID and width. `SceneController.cs` deduplicates those pairs into a palette
and writes frame lists of palette indices.

The **active C64 input** is `data/frames_list.asm`, rather than the older
`data/frames.asm` or alternate exported directories. It supplies **64 prepared
frames**, each containing exactly **91 row indices**. Every index refers to
one of **68 `(texture row, width)` pairs**. This checked path selects prepared
geometry on the C64; it does not establish live 3D vertex rotation there.
The Unity project was not run, and its current scene/export settings have not
been shown to regenerate the active lists exactly.

Runtime code still controls motion. `draw_frame` selects a frame, resamples
its rows using a vertical accumulator, writes an FPP pointer table and
selects horizontal sprite positions/expansion flags. Other routines advance
the frame, change speed, move the effect and change colors. Thus prepared
shape data is combined with runtime presentation and motion; it is not a
set of complete bitmap frames copied verbatim to the screen.

## A 105-byte source texture becomes 68 reusable strips

The input [`texture_gradient.png`](https://github.com/RobertTroughton/C64Demo-PublicReleases/blob/965807c511e2025b5c5e1ffb2a6235a4efd6ae5b/NoBounds/Parts/SpriteFPP/data/texture_gradient.png)
is **174×4**. Each row has one constant RGB value:

| Source row | RGB | Multicolor selector |
| --- | --- | --- |
| 0 | `$BBBBBB` | `01` |
| 1 | `$777777` | `11` |
| 2 | `$333333` | `10` |
| 3 | `$000000` | `00` |

These are the assembler's input-color mappings, not fixed native C64 palette
indices. Runtime sprite-color registers assign the eventual colors.

The palette includes one zero-width blank and nonblank widths **142–190**.
At assembly time, `texture_mapper.asm` centers and scales a selected source
row inside a **192-pixel** horizontal canvas. `sprite_writer.asm` samples
positions 0,2,4,6 from each eight-pixel group and packs their two-bit selectors.
That produces **24 bytes per strip**, or 96 logical multicolor samples.

Each strip occupies bytes **3–26 of a separate 64-byte sprite slot** starting
at `$4000`; the remaining bytes are zero. The complete atlas is **4,352 bytes**,
containing **1,632 packed payload bytes**. The 68 source palette keys produce
**57 distinct packed rows** after multicolor sampling. Distinct source widths
can collapse to the same sampled representation.

An independent producer checks the source texture's constant-row prerequisite,
then constructs the strip as a solid interval, rather than replaying the
individual source-pixel splats. For a nonzero width `w`, its inclusive bounds
are:

```text
left  = (192 - w) / 2
right = left + floor(173w/174 + 0.5) + ceil(w/174) - 1
```

It samples that interval at the 96 even physical positions. All **6,528**
palette samples agree with the forward-splat source model and actual PRG
bytes. The formula deliberately preserves the source's endpoint rounding;
it does not silently replace the result with an ideal centered width-`w`
rectangle.

Starting each row at sprite-slot byte 0 instead of byte 3 gives **1,184 wrong
logical samples**. Swapping selectors `10` and `11` gives **3,547 wrong
samples**. These controls distinguish both the stored offset and material
encoding.

## Exact supplied-code and data binding

The supplied `SpriteFpp.prg` loads at `$0801` and contains 48,386 bytes.
Separate, nonoverlapping domains match the independently predicted source
representation:

| Domain | Loaded location | Exact checked bytes |
| --- | --- | ---: |
| Complete 68-slot sprite atlas | `$4000` | 4,352 |
| All 64×91 row indices | `$AB00` | 5,824 |
| Frame pointer/start/length tables | `$C200` | 224 |
| Unrolled pointer-update cells | `$802A` | 4,389 |
| Immediately preceding X/Y setup | `$8026` | 4 |
| **Total in these domains** | | **14,793** |

The 64 frame addresses use a **91-byte stride**. The unused source height
metadata varies from 74 to 91; treating that metadata as the packed stride
would select different data. The source's frame writer computes its stride
from the maximum actual index-list length, and every active list has 91
entries.

Resolving every frame index against the actual PRG atlas and comparing with
the independent interval model checks **559,104 prepared logical strip
samples**, with zero differences. This is a prepared-data reconstruction,
not a comparison against the original VIC-II's displayed pixels.

The FPP kernel contains **133 repeated cells**, each **33 machine-code
bytes**. A cell sets `$D017` through Y, loads one `$0700..$0784` row value,
stores that same value into **all eight pointers `$43F8..$43FF`**, and resets
`$D017` through X. The matched prefix loads Y=`$FF`, X=`$00`.
All 4,389 cell bytes occur as one unique block at the listed PRG address.

The initializer gives sprites staggered Y positions and adjacent X positions.
The strip bytes occupy successive three-byte portions of a single shared
sprite slot, so changing one common pointer can select the horizontal strip
representation for all eight sprites. The precise MCBASE/DMA behavior that
makes those portions appear as one line still needs original execution and
fetch evidence. Literal register-store bytes alone are not a native FPP proof.
The source's unused `fpp_line_bytes=$24` constant is not substituted for the
matched **33-byte** cell size.

## What the apparent shading costs here

The active frame rows already select the texture shade and width. Alternating
indices can alternate shades line by line; the C64 does not need to compute
a lighting equation for each displayed pixel in this path. Since the input
texture contains only four constant horizontal rows, this representation is
much narrower than arbitrary image texture mapping or a live Pong game on
a polygon face.

The retained contact sheet visualizes eight prepared strip sequences using
the input gray values. It is intentionally labeled as a data reconstruction;
it omits the original FPP fetches, runtime X/Y scaling, palettes, composition
and scanout:

[Eight prepared strip sequences, not native output](../../build/research/frontier-geometry-20261108/strip-sequence-contact.png)

## Reproduction and remaining boundary

```sh
rtk proxy python3 research/frontier-2026/geometry_next.py
```

[`geometry_next.py`](../../research/frontier-2026/geometry_next.py) uses Python
and Pillow. It checks **29 acquired HTTP bodies** and saved headers, a pinned
acquisition index, the immutable commit/tree relationship and **25 Git blob
identities**. Bodies and receipts live under ignored
`build/research/frontier-geometry-20261108/`; a fresh checkout needs that
retained archive for offline reproduction.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Supplied `SpriteFpp.prg` | 48,386 | `7aba9b129119ec31aa31d06e663ebaca0bf221247c71af532f3b529c4a359e1a` |
| Predicted/matched atlas | 4,352 | `d27b67882d17fa040f89bfb119b847562776ecabf74401f6012c40f6dbb6d247` |
| Predicted/matched frame rows | 5,824 | `cf38ac1b2a0be9d857894370ceab5ed5381b06c5a5f859c2b11814c013176f89` |
| Predicted/matched pointer kernel | 4,389 | `02e339bdb3e2cdd90475c5eb23d6ab85245489d9fd010918a017ab42cc86635c` |
| Tracked producer | 12,962 | `d1124d19b45a0871788cab3c4163a150b2e33a55d675e4a81faf694cc18608be` |
| `geometry-findings.json` | 16,158 | `45f056681a0fab3f91826c703d1c754bb78f363e91712ff9c0832c0ae595be6b` |

PlasmaVector source, its supplied PRG and selected binary inputs were acquired
in the same archive as a separate possible next case. They have identity
checks, but no geometry, rasterization or execution claim is made for them.

There was **no downloaded-code execution, original source build, original
CPU/native/VICE execution, original-disk payload binding, complete displayed
frame reconstruction or measured timing**. A concrete continuation would
first bind this supplied SpriteFPP part to the original loaded image, then
observe the pointer stores and each sprite's actual fetch offsets under the
`$D017` schedule. That would test the hardware half of the representation
without mistaking prepared host geometry for live C64 3D calculation.
