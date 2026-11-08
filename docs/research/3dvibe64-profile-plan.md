# Stock Mode 6: linked profiling boundaries

This passive audit checks the **existing** PRG, assembly and 968-symbol file from the [completed build](3dvibe64-build.md). It does not run PowerShell, 64tass, C64 code or VICE, and reports no measured cycles or FPS. `research/3dvibe64-profile/anchors.py` pins those products, reuses the pinned static 6502 decoder, checks 25 selected JSR instructions and their continuations, and inventories the normal RTS sites of 24 named procedures, following direct tail jumps but never executing instructions. Its receipt also binds all 46 IDs/addresses/commands of the root-owned `native-plan.json` to those linked boundaries.

The accepted receipt is `build/research/3dvibe64-profile/source-analysis/accepted-02/anchors.json`, **24,680 bytes**, SHA-256 **`f61a80d70d90fe58b48c3f3f7109d58f62551d6d81aff4f71fde6f3aeb3c5937`**. The initial receipt preceded the added native-plan binding; the intervening `accepted/` run wrote its receipt but failed while formatting a relative output path. The producer now resolves paths first. Both earlier outputs remain retained; use the successful `accepted-02` receipt.

Replay into a fresh output directory, because the producer intentionally refuses an existing directory:

```sh
rtk proxy python3 -B research/3dvibe64-profile/anchors.py --output build/research/3dvibe64-profile/source-analysis/replay-01
```

## Actual call tree

Every continuation below is the instruction **after** the indicated JSR. These are code addresses for natural execution; this plan does not propose CPU-state writes.

| Work | Entry | JSR → continuation |
|---|---|---|
| Whole render | `$08CB` | Ends at `$08D4`, before presentation wait |
| Light intensity | `$0966` | `$08CB → $08CE` |
| Dirty clear | `$0E38` | `$08CE → $08D1` |
| Scene | `$142B` | `$08D1 → $08D4` |
| Bucket initialization | `$1450` | `$142B → $142E` |
| Select object | `$0A61` | `$1432 → $1435` |
| Angles, matrix, coordinate products | `$0FCF` | `$1435 → $1438` |
| Object-space light | `$101E` | `$1438 → $143B` |
| Vertex shades | `$10A2` | `$143B → $143E` |
| Rotation and depth | `$1368` | `$143E → $1441` |
| Face collection, lazy projection and buckets | `$145C` | `$1441 → $1444` |
| Draw buckets | `$4000` | `$144C → $144F` |
| Load corner shades | `$91AD` | `$401D → $4020` |
| Load face | `$40EC` | `$4020 → $4023` |
| Load material | `$0B22` | `$4027 → $402A` |
| Apply reflectivity to corner shades | `$91FE` | `$402A → $402D` |
| Draw Gouraud face | `$9223` | `$402D → $4030` |
| Geometry bounds | `$95DD`, tail `$AC96` | `$9223 → $9226` |
| Shade edges | `$9232` | `$922B → $922E` |
| Fill bounds | `$9455` | Tail jump from `$922E`; inherits `$4030` |
| Material A | `$0B44` | `$94B9 → $94BC` |
| Material B | `$0B67` | `$94D5 → $94D8` |
| Shade span | `$A000` | `$957A → $957D` |

There are two important naming traps. `rotate_project_vertices` at `$1368` only rotates into `rxbuf/rybuf`, prepares depth and clears `projdone`; its linked control-flow graph contains no JSR. Actual lazy projection enters `$9051` inside `load_face_visible`, with four compiled call/continuation pairs: **`$42F3→$42F6`, `$42FB→$42FE`, `$4303→$4306`, `$4314→$4317`**. The fourth is a quad path, not proof of its execution in this triangle-only scene. If `$9051` is traced, subtract it from collection and charge it to projection; otherwise label collection as including lazy projection.

Geometry bounds follows **`$95DD JMP $95E0; $95E0 JMP $AC96`**, the enabled XYQ2 builder. The ordinary convex walker at `$966C` is not this entry's active geometry path. The separate shade-edge pass remains at `$9232`; these are two different passes over the edges. The XYQ2 source comment promises a saved-stack restoration on a contract fault, but actual linked final code at `$B3FA` is **`SEI; JMP $B3FB`**, a terminal self-loop. It does not return or restore SP. Normal builder RTS sites are `$ACAA/$AE58`.

## Pair the stack, not a guessed RTS duration

At every traced procedure entry, retain registers/clock and `m 0100 01ff`. The JSR has stored `continuation−1` at page-one offsets `(SP+1)&255` and `(SP+2)&255`, low byte first. A completed normal return reaches that continuation with **SP = entry SP + 2 modulo 256**. Page-one indexes wrap within page one. Root-owned monitor semantics must bind each trace to the pre-instruction PC/clock.

Pair an entry with its **observed matching continuation and SP**. The entry-to-continuation interval includes the RTS instruction and any intervening VIC stalls; adding a nominal six cycles to an RTS trace is not an exact elapsed-time measurement. It excludes the initiating JSR, which remains in the parent residual. For trace-only points not accompanied by a separate register query, the trace's own SP is the matching state.

Tail jumps require special handling. `$AC96` is an alternative start for the geometry-bound interval, not an additional billable child of `$95DD`. `$9455` inherits the face call's return `$4030` and SP. When that continuation arrives, close fill and then face at the same clock; do not demand two physical RTS operations or add their durations twice. `$A143` is a path marker under `$A000`, not a fresh call. IRQ/RTI frames must not be mistaken for renderer calls; retain the IRQ timeline if isolating interrupt time is required.

Compute exclusive time by subtracting each **immediate child's inclusive interval once**. The root render interval must equal the sum of exclusive buckets, including the explicit residual for untraced setup, bucket traversal, caller JSRs, loops and interrupts outside child intervals. Record inclusive helper totals separately; they cannot simply be added together. The native plan omits some plumbing helpers from the table, so its residual must remain visible rather than be relabeled as a specific algorithm.

## Span route markers and ABI

At `$A000`, root's trace command is:

```text
m 0100 01ff; m 000b 002f; m b43b b441
```

This includes `drawbuf=$0B`, bitmap row pointers `$25–$28`, `yrow=$2F`, and the contiguous seven-byte span state **x, end, delta, direction, error, extent, shade** at `$B43B–$B441`.

| Marker | PC | Interpretation |
|---|---|---|
| General route | `$A035` | Extent below 7, or endpoint Bayer patterns unequal |
| Uniform bulk route | `$A143` | Exact constant-pattern interval selected by the classifier |
| General full byte | `$A053` | Four DDA samples producing one full byte; repeats per span |
| General partial byte | `$A0DF` | One masked byte aggregate; repeats per span |

Extent is **end−x**, so the classifier starts at eight inclusive logical pixels. The general route can still produce a constant pattern on a short span; it is not synonymous with visible shading. Exactly one general/uniform marker should occur for every completed `$A000` call. Full/partial markers belong only to the general route and count byte groups, not separate spans. Uniform route has its own full-byte loop at `$A179` which this minimal marker surface does not count.

The Bayer operand at `$A054–$A055` is self-modified by row setup. The file's initial `LDA $B526,Y` is a linked-code identity guard, not a requirement that live operand bytes remain unchanged. Native guards must allow the four bound Bayer rows and verify the selected row from actual `yrow`.

## What the profile can establish

Clock differences from an unwarped PAL run are **elapsed emulated machine cycles**, including VIC steals and interrupt work. They are not retired-6510-only counts, physical C64 timings or a wall-time FPS measurement. Presentation waiting and tick consumption lie outside `$08CB–$08D4`. Keep per-render elapsed time distinct from display cadence.

The first render's target was initialized clean. Its clear fast path is not representative of steady dirty clearing. With alternating buffers, the third render is the first reuse of B; capture at least that render before deciding whether clearing matters. Preserve object pose, buffer identity, span inputs and path counts with each timing sample. A few observed poses support a bounded cost profile, not a claim about every rotation.
