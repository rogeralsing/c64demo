# Mufflon 1.0 / NUFLI research

This lane extracts original data and executes bounded original 6502 routines
in flat RAM. It does not run the downloaded host binaries or launch VICE.
The findings and native handoff are in
[the research note](../../docs/research/nufli.md).

The existing archive must be at
`build/research/frontier/Mufflon1.0-source+GUI+Bonus.zip`, extracted beside it.
The extraction script pins its SHA-256 and compares the inspected source and
both D64 files directly with their ZIP members.

From the repository root:

```sh
python3 research/nufli/extract.py
build/research/tower-power/cpu-venv/bin/python research/nufli/validate_generator.py
python3 research/nufli/decode_nuf.py
```

The CPU script needs `py65==1.2.0`; the existing ignored Tower research venv
provides it. The logical decoder needs Pillow. No additional dependency was
installed. The scripts reuse the repository's static 6502 instruction decoder
only to print listings; the CPU proof uses py65's original instructions.

Outputs go to ignored `build/research/nufli/`:

- `extraction.json`: archive/source/file hashes, D64 sector chains, exact
  source-array comparison against all four bundled NUFs.
- `source-arrays.json`, `displayer-*.bin`, `displayer.txt`: extracted source
  tables and disassembly, with the template's data excluded from code listing.
- `generator-validation.json`: original generator versus host builder,
  all switch-helper cases and per-file CPU counts.
- `*-generated.ram`, `*-speedcode.bin/.txt`, `*-register-trace.json`: generated
  code and original-CPU output-latch trace. Cycle tags are instruction entry;
  they omit VIC stalls, interrupt entry and bus-write phase.
- `decode-validation.json`, `*-indices.bin`, `*-logical.png`: four logical
  composites, independent address-formula checks and image-plane ownership.

The logical PNG is not a screenshot. Input BMP comparisons are descriptive,
not a lossless oracle: the stored NUF may replace colours, and several input
BMP palette shades differ from the converter palette by one RGB unit. The
decoder models Mufflon's intended bitmap/sprite composition, including its
odd/even colour grids, but not VIC fetch/open-bus artefacts, borders, exact
raster placement, composite output, PAL/NTSC compatibility or the slideshow
loader. Its `pass_` flag covers the explicit format invariants only.
