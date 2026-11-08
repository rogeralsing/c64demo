# Two third-frame draw groups can be omitted offline

In the third captured Gouraud frame, keeping face-latch groups **`[2,0,3]`**
and omitting **`[1,7]`** produces exactly the same completed bitmap, Screen
RAM, physical Color RAM and decoded display indices as all five groups.
The first and second captured frames require all four of their groups. This
is a pose-specific overdraw result: face 1 is required in the second frame,
where omitting it changes 640 displayed pixels.

The experiment changes no program or culling policy and measures no speedup.
It exhausts captured span-group subsets with the previously accepted scalar
raster reference. The new producer is
[`omit_groups.py`](../../research/3dvibe64-overdraw/omit_groups.py); its receipt
is `build/research/3dvibe64-overdraw/omission-analysis/accepted-01/omission-proof.json`.

## Exhaustive results

Groups are identified by the actual captured `mode4_current_face_id=$0C`
latch, with source sharing off. Their order below is their observed drawing
order, not numeric face-ID order. Each face ID occurs in one contiguous group
in each accepted frame. All **64 subsets** are examined: 16, 16 and 32.

| Captured frame | Original groups | Unique minimum retained groups | Retained spans | Display-preserving subsets |
|---|---|---|---:|---:|
| First | `[3,2,1,0]` | `[3,2,1,0]` | 168 / 168 | 1 / 16 |
| Second | `[1,2,0,3]` | `[1,2,0,3]` | 159 / 159 | 1 / 16 |
| Third | `[1,7,2,0,3]` | **`[2,0,3]`** | **123 / 203** | **4 / 32** |

The minimum is identical for the full-memory objective and the decoded-image
objective in all three frames. In the third frame, retaining neither, either,
or both of groups 1 and 7 is image- and memory-preserving. No subset has the
same image while differing in any compared memory array.

Third face 1 contributes 35 spans and 136 logical pixel writes; face 7
contributes 45 spans and 203 writes. Omitting both removes **80 captured spans
and 339 input pixel writes** from this offline replay. The untouched full
stream has 2,666 pixel writes, including overlap. These counts are input work,
not elapsed time or a native saving.

The full third replay and its minimum subset decode to byte-identical PNGs:

- [All five groups](/Users/rogerjohansson/git/asynkron/c64demo/build/research/3dvibe64-overdraw/omission-analysis/accepted-01/third-full.png)
- [Only groups 2, 0 and 3](/Users/rogerjohansson/git/asynkron/c64demo/build/research/3dvibe64-overdraw/omission-analysis/accepted-01/third-minimum-display-1.png)

These are decoded completed-buffer images. They are not new committed-VIC
captures or physical-hardware observations.

## Single-group omissions

Each row omits only the named group. Display differences count physical
**320×200** palette-index pixels. Each logical 160×100 sample covers four
display pixels under the observed duplicated-row layout.

| Frame | Omitted face latch | Bitmap bytes changed | Screen bytes changed | Color RAM bytes changed | Display pixels changed |
|---|---:|---:|---:|---:|---:|
| First | 3 | 482 | 0 | 55 | 3,444 |
| First | 2 | 462 | 0 | 55 | 3,444 |
| First | 1 | 462 | 0 | 55 | 3,444 |
| First | 0 | 482 | 0 | 45 | 3,444 |
| Second | 1 | 130 | 0 | 0 | 640 |
| Second | 2 | 314 | 0 | 0 | 1,896 |
| Second | 0 | 366 | 0 | 0 | 2,572 |
| Second | 3 | 674 | 0 | 0 | 4,832 |
| Third | 1 | **0** | **0** | **0** | **0** |
| Third | 7 | **0** | **0** | **0** | **0** |
| Third | 2 | 206 | 0 | 0 | 1,128 |
| Third | 0 | 322 | 0 | 0 | 2,224 |
| Third | 3 | 650 | 0 | 0 | 4,444 |

## Baseline, ordering and palette semantics

Every subset starts from the corresponding actual `$1153` post-clear/shade
baseline, including its entire bitmap and both palette arrays. Selected
spans retain original order and captured endpoints, shades and Bayer phase.
The frozen `scalar()` function is imported without its `main()` and remains
unchanged. No SDK, generated C64 instructions, assembler or emulator runs.

Before omitting anything, the full replay must match the native `$08D4`
completion in all **8,000 bitmap bytes, 1,024 Screen bytes and 1,024 physical
Color RAM bytes** for every frame. The RAM portion of each consumed snapshot
must equal its paired 65,536-byte RAM dump. Every consumed artifact is checked
against the hash in the accepted profile-pixel receipt.

An independent display decoder then maps both physical bitmap rows
separately into **64,000 palette indices**, using the completed snapshot's
background color and each replay's attributes. It does not assume that
duplicated rows remain equal after omission. The fixed accepted material is
`$BF/$01`; palette code 0 is the background, codes 1/2 use the Screen nibbles,
and code 3 uses physical Color RAM. The decoder also agrees with the old
logical decoder for each full accepted image.

Memory and visible equality remain separate. For each subset, a second
decode holds its bitmap fixed but substitutes the full replay's attributes.
This isolates the visible effect of changed palette cells from missing
bitmap pixels. All 15 non-full first-frame subsets have some changed Color
RAM cells that are invisible on their retained bitmap; at most 252 cells
change. In every subset of all three frames, substituting the full
attributes changes **zero** display pixels. The first-frame images still
differ because of their bitmap changes. Thus an invisible attribute change
is not silently treated as memory equality.

Each `*-all-subsets.json` records every numeric mask, retained group IDs,
span and write counts, four array hashes, byte/pixel differences and display
bounds, and changed/invisible attribute cells. Group join keys also retain
frame, first span index and first span clock.

## Source and measured-cost context stay separate

The separate [cull-policy investigation](3dvibe64-cull-policy.md) binds the source classifier and
observed draw-subtree costs. Its findings can help explain why the renderer
submitted this work, but are not inputs to this omission model. In
particular, removing a captured group offline does not establish that a
source-side classifier can omit it safely for other poses, clipping cases,
lighting, materials or scene meshes. Group 1's second-frame result already
rules out simply dropping that face ID unconditionally.

The separate measured subtrees for third groups 1 and 7 total 172,828 modeled
PAL cycles, 25.56% of the captured third-frame interval. That is the cost of
observed work, **not a measured recoverable saving**: a changed classifier or
submission path could change other work and control flow. No modified C64
program is timed here.

## Inputs, replay and continuation

The accepted profile case remains the 29-file closed native case, directory
SHA-256
`13bfd23f30bf0b7a2db7a9e8dc4ceb8dc69e77d81c76862fe9b372a1f23ef714`.
Its [profile pixel acceptance](3dvibe64-profile-pixels.md) binds source,
loaded PRG, stack/ABI dumps, read-only trace inputs and completed arrays.
The generated-PRG autostart mode 1 loader injection is declared there; there
are no later manual CPU/RAM patches. The present experiment consumes those
accepted inputs and does not repeat native capture or whole-wire auditing.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Frozen scalar producer | 28,293 | `859e1ece975ea57c283cf0c4dcef47be95cf91c72d8d9eba29cd4765da8e16a2` |
| Accepted profile pixel receipt | 50,301 | `a564dc770db6b02afc66607b259cd71971b9ef2810200c642fd5c4cae1cb2710` |
| New omission producer | 15,311 | `3683d59029dbb251e56a33536d83837ae22b799407ff54501c0c694c777accb4` |
| New omission receipt | 27,195 | `e6e2fe1d2f952399333ec7340098ddcf95be2ee00966ce911ec5aa462cc712e9` |

Run from the repository root with a **fresh** output directory:

```sh
rtk proxy python3 research/3dvibe64-overdraw/omit_groups.py \
  --output build/research/3dvibe64-overdraw/omission-analysis/replay-next
```

The default is `omission-analysis/accepted-01`; nonempty outputs are refused.
All generated paths are confined to the owned `omission-analysis/` tree.
Receipts use output-local filenames and contain no output-directory prefix
or timestamp. The accepted output and a fresh `replay-01` contain **23
byte-identical files, including the receipt and checked producer**, totaling
387,210 bytes in each directory. No output-path normalization is needed.

The next useful step is to join the separate source-policy classification
and group-cost keys to these exact omission results, then assess a bounded
pose-dependent culling proposal before any product change. Keep the full
scalar memory and image checks as acceptance conditions for a later measured
variant. This finite three-frame experiment does not prove projection,
geometry, clipping, vertex illumination, a general culling policy, native
speedup or delivered FPS. All prior frozen artifacts and Pong remain intact.
