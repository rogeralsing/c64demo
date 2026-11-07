# Freespin offline research

The [research note](../../docs/research/freespin.md) distinguishes author descriptions, released bytes, offline decoding and original-CPU checks. All downloaded source/data and generated evidence stay under ignored `build/research/freespin/`.

Run from the repository root:

```sh
python3 research/freespin/acquire.py
python3 research/freespin/assemble_loader.py
python3 research/freespin/decode_disk.py
build/research/tower-power/cpu-venv/bin/python research/freespin/validate_decoder.py
build/research/tower-power/cpu-venv/bin/python research/freespin/validate_raster_line.py
```

The first three commands use Python's standard library. Assembly uses the existing Java/Kick Assembler installation; `JAVA` and `KICKASS_JAR` override tool locations. The last two need py65 1.2.0; the commands above reuse the already-installed isolated research environment. Any Python with that package can run them. No new dependency was installed for this work.

The author pages publish the resident loader and selected raster/music fragments. The source pin is its exact extracted-text SHA-256, not an invented full-source Git revision. `acquire.py` validates the exact released-D64 hash; `assemble_loader.py` validates the pinned source and supplies only its external frame parameter, derived from the released timer bytes. It does not edit the published source.

| Artifact | Meaning |
|---|---|
| `downloads.json` / `*.html` | Original author URLs, retrieval time, sizes, exact content hashes |
| `loader-published.asm` | Text extracted from the published loader page |
| `loader-published-20000.prg` / `assembly.json` | Reassembled published listing, supplied frame constant, assembler/output hashes |
| `loader-release.bin` | 254-byte resident allocation from D64 track 18 / sector 18 |
| `bootstrap.prg` | Conventional `$0801` bootstrap extracted through the DOS file chain |
| `decoded-index.json` | First seventeen coherent track payloads, exact block copies, entry vectors, ranges and hashes |
| `parts/trackNN-blockK.gcr.bin` | Re-encoded standard GCR sector body, including marker/header/trailer |
| `parts/trackNN-blockK.decoded.bin` | 208 payload bytes from the released add/XOR formula |
| `parts/trackNN.memory.bin` | 2 KB reconstructed RAM plus resident loader tail |
| `parts/trackNN.known.bin` | Established-byte mask; addresses `$0000..$000F` remain placeholders |
| `cpu-validation.json` | Original released payload-loop comparisons and fixed-delay count |
| `raster-line-validation.json` | Original track-2 fragment cycle/port-write observations |

`unsupported-default-candidates/`, if present, preserves the exploratory secondary-track attempt. It is not part of the validated decoded corpus. Secondary custom-looking tracks remain an open identification problem.

The decoder validator supplies `$1C01` bytes and byte-ready V events, then executes the original arithmetic. It does not simulate a disk or VIA. The raster validator executes a bounded official-opcode fragment in flat RAM, not an entire drive or analog monitor. No VICE process, drive firmware, renderer source, disk image or display state is changed by these commands.
