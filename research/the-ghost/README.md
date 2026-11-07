# The Ghost original-release investigation

Read [the analysis](../../docs/research/the-ghost.md) for primary routes,
identities, directory format, CPU model conditions and limits.

Run from the repository root using the existing py65 1.2.0 environment:

```sh
rtk proxy python3 research/the-ghost/acquire.py
rtk proxy python3 research/the-ghost/inspect_disk.py
rtk proxy build/research/tower-power/cpu-venv/bin/python research/the-ghost/bootstrap.py
rtk proxy python3 research/the-ghost/extract_streams.py
rtk proxy build/research/tower-power/cpu-venv/bin/python research/the-ghost/depack.py
rtk proxy python3 research/the-ghost/map_release.py
```

- `acquire.py`: original CSDb pages and ZIP; archive member hashes; HTTP failures recorded if encountered.
- `inspect_disk.py`: ordinary DOS directory aliases and linked bootstrap bytes.
- `bootstrap.py`: execute the original bootstrap until `$8A00`; guard hardware-visible I/O.
- `extract_streams.py`: archive pinned original Bitfire references; independently check the old six-byte directory and extract 62 raw payloads.
- `depack.py`: call the release's original plain-depack routine with explicit source-pointer inputs; unknown memory reads fail the run.
- `map_release.py`: audit every output against its packed destination header and hash; verify selected first-scene register/idle-byte anchors.

No installation, native emulator, hardware loader, serial protocol or drive
execution is involved. CPU helpers are reused read-only from
`research/next-round/analyze_boot.py`; their hash is recorded. Binaries, raw
third-party sources and generated receipts remain ignored under
`build/research/the-ghost/`.
