# Tower Power offline tools

These scripts inspect the exact 100% final-release inputs already inventoried in `build/research/tower-power/files.json`. The [depacker note](../../docs/research/tower-power-depacker.md) explains the format and bounded conclusions; [the main ledger](../../docs/research/tower-power-binary.md) owns live VICE observations and release provenance.

Run from the repository root. The static tools use Python's standard library and do not execute C64 code, start VICE, alter a disk image, or modify the production renderer.

```sh
python3 research/tower-power/static_loader.py
python3 research/tower-power/unpack_stream.py
python3 research/tower-power/part_inventory.py
python3 research/tower-power/analyze_n2.py
```

`static_loader.py` reads `side1/>>tower power!<<`, models only its verified five-page loader copy, and traverses the actual `$C010`/`$C300` static entries. `unpack_stream.py` translates the original packed-stream algorithm into Python, recording output provenance. `part_inventory.py` uses decoded entry/IRQ vectors to seed a static walk. `analyze_n2.py` records literal coordinate rings and count operands.

## Artifacts

All third-party bytes and generated receipts stay under ignored `build/research/tower-power/`:

| Path under that root | Meaning |
|---|---|
| `files.json` | Extracted filenames, sizes, hashes, and initial words; the initial word is not a proven output address |
| `static/loader-c000.bin` | Exact 1,280-byte copied loader |
| `static/loader-analysis.json` / `loader-reachable.asm` | Static entry walk with unresolved indirect/self-modifying targets |
| `static/unpacked-index.json` | 42 decoded streams, consumption, ranges, unknown-byte counts, and output hashes |
| `static/unpacked/*.memory.bin` | 64 KB flat output image; **only known-mask addresses are meaningful** |
| `static/unpacked/*.known.bin` | One byte per address: nonzero means established decoded output |
| `static/unpacked/*-hhhh-hhhh.bin` | Exact contiguous decoded output segment |
| `static/unpacked/*.commands.json` | Ordered literal, match, destination, and end commands |
| `static/parts/` | Entry-seeded listings and JSON, not dynamic execution traces |
| `static/n2-geometry-candidate.json` | Literal points, ring coordinates, radius/count observations |
| `static/loader-live-match.json` | Loader comparison against the original native RAM capture |
| `cpu-validation/validation.json` | Independent original-6502 depacker validation |

`unpacked-index.json`'s `pass` initially means the parser reached the original end convention. The stronger consistency checks are exact consumption, zero unknown back-reference output, and the separate CPU validation. Unused literal-count escape forms are not claimed as a general tested compressor specification.

Static listing warnings are intentional. A direct call may still contain a runtime-patched placeholder, and a generated routine may not yet exist in the decoded image. Do not count apparent data bytes as executed instructions or call the listing a complete decompilation.

## Independent original-CPU validation

The validator is separately maintained and runs the original `$C023..$C177` depacker with py65 1.2.0. The existing isolated environment is `build/research/tower-power/cpu-venv/`:

```sh
build/research/tower-power/cpu-venv/bin/python research/tower-power/validate_6502.py
```

Only `$C18F` disk-block input is mocked: 254 raw file bytes enter `$C302..$C3FF`, with A/X/Y/P preserved and normal RTS stack behavior. The original raw and bit readers execute unchanged. The full receipt checks all 42 streams, all 340,371 chronological output address/value events, final bytes, written-address sets, and consumed input. This does not simulate IEC/1541 transport, interrupts, memory banking, or rendering and provides no timing result.

## Raw native-RAM comparisons

Provide a raw 65,536-byte capture, without a PRG header. The optional earlier capture records every changed byte:

```sh
python3 research/tower-power/compare_live.py \
  build/research/tower-power/live-02/ram-intro-entry.bin \
  --before build/research/tower-power/live-02/ram-before-intro.bin \
  --output build/research/tower-power/static/live-intro-comparison-complete.json
```

The comparison does not silently remove I/O, stack, or other addresses. It records mismatch counts, complete end-exclusive mismatch ranges, and a short address sample for every decoded payload. Current `live-02` captures establish the one-byte disk marker and the boot-resident bootstrap only, not an executing vector part. Native sessions and any deliberate state changes belong in the main binary ledger.
