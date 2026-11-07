# BRR host research

Run `rtk proxy python3 research/bit-reversal/analyze.py` from the repository root.
See [the research note](../../docs/research/bit-reversal-lines.md) for the primary
sources, pixel convention, finite-domain results and cycle-model exclusions.

The script uses only Python's standard library. It downloads the pinned author
pages when missing, retaining them and the extracted code only under ignored
`build/research/boo-math/`. It never assembles code, edits a renderer, or starts
an emulator. Its generated scene is self-contained; `--report PATH` optionally
validates it against the archived `d5baf50b…` 512-pose report.
