# Retained column-span delta prototype

This isolated experiment replaces the crossing-buffer clear, edge construction,
and full sprite fill with live convex-column span construction and incremental
coverage updates. It does not change the production renderer.

For each target bank and sprite slot, it retains 24 top and 24 bottom endpoints.
The constructor samples the same half-open integer X intervals and exact
`ceil(Y)` edge crossings as the native renderer. For each column, the updater
XORs the interval between the old and new top endpoints, then the interval
between the old and new bottom endpoints. Both MCI sprite mirrors receive each
updated byte. This works when spans overlap, separate, become empty, or switch
from pentagon to hexagon. Separated spans can cause redundant intermediate
writes that cancel through XOR.

Each alternating target bank has its own retained state. Consequently, an
update compares against the actual target buffer from two presentations earlier.
Slot identity changes require no special case: the retained coverage belongs
to the physical bank and slot, and the new coverage replaces it exactly.

## Reproduce

Requires Python 3 with `py65`, Kick Assembler on `PATH`, the complete 513-pose
native `delta-trace.json`, and its `reference-cpu-cycles.json` profile.

```sh
rtk proxy python3 boundary_delta.py --trace delta-trace.json --profile reference-cpu-cycles.json
```

`boundary_delta.py` contains the deterministic assembly generator. The run writes
`span-delta.asm`, arithmetic curve tables, the assembled PRG and symbols, and
`report.json`. The report records source and trace SHA-256 hashes, exact byte
comparisons, CPU cycles, sprite stores, and memory sizes.

The result is an assembled NMOS 6502 kernel measurement using py65. It includes
new-span construction from the actual live local vertices, span normalization,
history comparisons and updates, pointer setup, and both sprite mirrors. It
excludes VIC bus steals, IRQs, shared 3D transforms, position/color metadata,
and external JSR dispatch. No host-generated spans are treated as free work.

Expected sprite bytes come from the native baseline trace. The test verifies
the initial target-buffer contents, every final 63-byte sprite, both mirrors,
and retained endpoints for every update. Input count, coordinate limits, and
curve-table bounds are checked before executing the assembly.

## Memory and practical limit

The retained history requires 768 bytes; new spans require 48 scratch bytes.
That scratch can replace the original 512-byte crossing area, giving a net
304-byte increase in this portion of CPU data. The standalone prototype uses
13 zero-page bytes for pointers and temporary state. Code and table sizes are
recorded separately in the report; they are gross prototype sizes, not a claim
about the net production memory map. Existing arithmetic tables could be reused
with address adaptations.

The prototype keeps one bit per column in each toggle operation. Multiple
changed columns therefore read and write the same sprite byte repeatedly.
The original unrolled fill writes each sprite byte once. A slower result here
rejects this specific span strategy; it does not prove every possible delta
encoding must lose. Byte-oriented strategies are measured separately.
