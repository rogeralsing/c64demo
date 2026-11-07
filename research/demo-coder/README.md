# Demo Coder offline inspection

This directory contains reproducible analysis of the original **The Demo Coder / Fairlight (2024)** disk. It does not start VICE, emulate a drive, run the effects, or modify the disk or renderer. The accompanying [research note](../../docs/research/demo-coder.md) separates author statements, original CPU execution, and static candidates.

The input is the already preserved original 40-track D64:

```text
build/research/frontier-followup/demo-coder.d64
SHA-256 b8c54fc1ca41c00cd81773ecff780649d892bc6497a84b7c67c79a9235d95e9b
```

From the repository root, use the existing research interpreter with **py65 1.2.0**:

```sh
rtk proxy build/research/tower-power/cpu-venv/bin/python research/demo-coder/inspect_boot.py
rtk proxy build/research/tower-power/cpu-venv/bin/python research/demo-coder/unpack_streams.py
rtk proxy build/research/tower-power/cpu-venv/bin/python research/demo-coder/map_parts.py
rtk proxy build/research/tower-power/cpu-venv/bin/python research/demo-coder/inspect_selectors.py
```

`inspect_boot.py` extracts the DOS chain, then interprets the original boot depacker with startup RAM filled with `$00` and `$A5`. Mapped I/O/ROM reads are rejected. It stops before the unpacked `$8A00` wrapper executes. Original NMOS `LAX`/`DCP` support comes from the hash-recorded `research/next-round/analyze_boot.py` helper.

`unpack_streams.py` reads the two raw Bitfire directories and their 68 streams. It reproduces the wrapper's literal resident-copy operation, loads each stream at its original address, and interprets only the original plain-depack entry at `$02CC`. Its explicit host precondition is all RAM visible (`$00=$2F`, `$01=$34`); it supplies no ROM, drive, interrupt, or I/O responses. The original plain routine patches itself normally. Hardware-loader and IRQ entries are rejected, and back-references must read established RAM. The NMOS absolute NOP's unused target reads are retained and reported separately.

Every stream terminates through the original in-place convergence path. The receipt therefore records two different quantities: bytes written by the CPU, and untouched raw tail bytes already present at their final addresses. The exported full image contains both. Tail equality is checked against the original packed file, and its bytes must not occur among the CPU's output stores. A preliminary prefix-only export is retained under `streams/prefix-only-attempt/` with an explicit rejection note; it is not the current output.

`map_parts.py` follows direct control flow from the actual first handoff and exact repeated wrapper prologues. Literal IRQ-vector installations add further roots. These are static branch overapproximations; the script does not resolve all self-modifying jumps or identify an effect from its appearance.

`inspect_selectors.py` checks one particular source-linked table in stream 46. It verifies all 50 routines, their 1,275 cells, exact endpoint jumps, two `$D011` pages, and the code that patches the dispatch jump. Its cycle counts are nominal CPU counts only.

Outputs are ignored under `build/research/demo-coder/`:

- `boot-proof.json`: original DOS chain, startup assumptions, complete write accounting, and both boot runs.
- `streams/unpacked-index.json`: original sector segments, packed/full-image hashes, written prefixes, preserved tails, and instruction counts for every stream.
- `static-map/part-map.json` and listings: bounded candidate entry/IRQ maps.
- `selector-analysis/selector-proof.json`: finite table and instruction-cell checks.

The first exploratory attempt incorrectly borrowed Next Round's `$0900` stop address and eventually polled the unmodelled VIC in flat RAM. Its files are explicitly retained as `attempt-flatram-no-handoff.*`; they are excluded from the proof. All current entry addresses were established from Demo Coder's own code.
