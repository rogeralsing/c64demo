# Tower Power: packed streams and offline reconstruction

This note concerns the **100% final release** used in [the binary investigation](tower-power-binary.md). Release provenance and author statements are in [the source note](tower-power-sources.md). It records a completed offline depacker reconstruction and a static sphere candidate; it does not identify the user's screenshots with an executing effect or establish a frame rate.

## Input and the actual loader

The boot PRG loads at `$0801` and its BASIC entry calls `$2600`. Its SHA-256 is `467a27f7055bf96de9cd8431bdcefd1d1febeacd01e6e22f1822ca2e19cc0b04`.

The code at `$2775` copies five pages from `$2100..$25FF` to `$C000..$C4FF`. `$265E` calls the installed loader initializer at `$C300`; requests enter at `$C010`, with a sixteen-byte name at `$C000`. The copied 1,280 bytes have SHA-256 `7c47457a20e75f37bcc5d7473778af3bee5c771d9845ed4e3cee6d35dc837322` and match the original live loader capture byte for byte. That comparison is recorded in `build/research/tower-power/static/loader-live-match.json`.

The first word of an extracted custom file is **not its decompressed destination**. The original reader skips that word. For example, `m1` begins with `$8500` but reconstructs `$1000..$1FF7`; `o4` begins with `$2B00` but reconstructs `$2000..$3F3F`. Destination changes are commands inside the stream. The directory/extraction manifest's `load_address` field names only that initial word.

BASIC line 3 is `SYS 9737` (`$2609`). Its original selector loads `N1.*`, enters the decoded `$092F` wrapper, loads `M5.*` music and then `N7.*`. N7's entry is `$9436`; its literal request at `$99C2` is `N2.*`, called through `$C010` at `$9456`. After its original wait logic, `$947B` jumps through `$C2F0`. N2's decoded entry/IRQ vectors are `$2034` / `$2CDC`. This identifies a static route to the candidate, not proof that a native session has completed it.

## Decoder structure

These addresses refer to the installed original code, not a new implementation:

| Address | Established function |
|---|---|
| `$C023` | Depacker initialization: zero high count, initialize byte index and bit state |
| `$C139` | Raw-byte reader, including block refill when X wraps |
| `$C156` | LSB-first bit reader with eager refill |
| `$C0E5` | Variable-length value decoder |
| `$C0D8` | Read a little-endian word into a selected zero-page pair |
| `$C12C` | Store a byte through `$05/$06`, then advance destination |
| `$C0B1` | Forward, overlapping back-reference copy |
| `$C08E` | Set a new output destination |
| `$C09A` | End-of-stream return |

The sector transport presents 254 bytes at `$C302..$C3FF`. Initial X = 4 skips the file's first two bytes; after wrap/refill, X = 2 consumes the next block from its beginning. Modeling the extracted file as one contiguous byte sequence is therefore sufficient for depacking, while saying nothing about whether the drive transports those bytes correctly.

Two details are essential:

1. The bit reader returns the old least-significant bit. When its remaining-bit count reaches zero it **immediately fetches the next bit byte**, before the caller consumes any following literal/command bytes. The returned carry still belongs to the old bit byte.
2. A literal run finishes by falling directly into `$C06D`, the match/control decoder. It does not return to the ordinary two-bit token prefix at `$C02E`. Missing this fall-through makes otherwise plausible decoders lose synchronization.

In ordinary token state, `10` selects one literal byte; `010`, `0110`, and `0111` select two, three, and four. `00` selects an extended literal count with base 5. `11` enters match/control decoding. After literals, that last prefix is implicit.

Match/control selects length two, length three, or an extended value with base 4. Extended value 1 changes destination, value 2 ends the stream, and other values copy earlier output. Encoded distances become `distance + 1`; copying forward permits overlapping repetitions. Short offsets combine a raw low byte with one high bit; a flag permits a full sixteen-bit offset.

The extended-value decoder has compact small cases, a three-bit extension, and a raw-byte escape. An unusual sixteen-bit literal-count escape exists in the machine code but is unused by these 42 streams; no claim about unseen encoders depends on that case.

## Independent validation

The high-level [decoder](../../research/tower-power/unpack_stream.py) reconstructs all **42 custom streams**, consuming all **176,947 input-file bytes** exactly. It records **340,371 output-write events**, with no trailing bytes and no back-reference to unknown output. This includes three side-1 payloads, the two side markers, and 37 side-2 payloads. Boot, the separate note PRG, and `win386.swp` are excluded.

This is independently checked by [the original-6502 validator](../../research/tower-power/validate_6502.py), using py65 1.2.0:

- It executes the original depacker at `$C023`, including the unmodified `$C139` and `$C156` readers, until the original `$C09A` return.
- Only `$C18F`, the disk-block receive routine, is mocked. It places the next 254 file bytes at `$C302..$C3FF`, preserves A/X/Y/P, and returns with the normal stack effect.
- All 340,371 chronological output address/value events, final bytes, written-address sets/ranges, and byte consumption match the offline decoder. All 254,530 back-reference reads use previous output.
- The 42 runs execute 10,309,937 original instructions. The 674 refills exercise both carry values. These are validation counts, **not performance measurements**.

The complete receipt is `build/research/tower-power/cpu-validation/validation.json`, including input, decoder, validator, loader, and live-capture hashes. It reports all 42 streams passing.

This proves the depacking algorithm against the original CPU code under the stated input mock. It does **not** prove IEC/1541 transport, interrupts, banking, hardware-visible pixels, or the live execution path of a selected effect. A post-load native RAM comparison remains a separate check.

## Reconstructed parts and entry vectors

The index `static/unpacked-index.json` records every output range. Each stream also has a flat memory image, a known-output mask, exact segments, and a command log. Unknown bytes in those flat images are placeholders and must not be treated as established zero-filled memory.

Many files write four bytes at `$C2F0..$C2F3`: the entry and IRQ vectors used by the boot's indirect handoff. Representative decoded results are:

| File | Entry / IRQ | Selected actual output ranges |
|---|---|---|
| `a1` | `$902D` / `$9076` | `$0800..$0FFE`, `$8C00..$999F` |
| `b2` | `$C524` / `$CBC9` | `$2000..$37FF`, `$A800..$AFFF`; entry code is in separate `b1` output |
| `c2` | `$5836` / `$5B28` | `$2000..$4FB7`, `$5800..$6A5D`, `$C500..$CFFF` |
| `f1` | `$2194` / `$3C29` | `$20FD..$3EF9`, `$E000..$E9FF`, additional data ranges |
| `i2` | `$9FF5` / `$A3D8` | `$2000..$471F`, `$8000..$BF8D`, additional data ranges |
| `n2` | `$2034` / `$2CDC` | `$2000..$382D`, `$4600..$46CF`, `$C500..$CAFF`, additional ranges |

The entry-seeded listings are **static over-approximations**. Unresolved self modification can make an initial JSR operand a placeholder; following it may reach data or code that will be generated later. For example, the initial `i2` target `$2800` must not be interpreted as proven executable code merely because a static walk followed it. Packed input was never used as disassembly input.

## N2: strong sphere candidate, not yet visually matched

`n2` contains a substantial geometry/line/fill pipeline. The following are source-byte observations from the validated unpacked payload:

| Location | Static observation |
|---|---|
| `$30F4` | Generates 64 pages at `$8000..$BFFF`, using the 64 step values at `$47C0` and fixed-point accumulation |
| `$3140` | Uses three angle bytes at `$2A23..$2A25` to patch indexed ADC/SBC operations and table addresses |
| `$327C..$32F1` | Combines coordinate inputs through those tables and emits paired 2D/depth results; EOR operations generate centrally opposed outputs |
| `$4600`, `$4650`, `$46A0` | Literal coordinate components for four ten-point upper-half latitude rings |
| `$2219` | Uses depth/topology data to choose XOR edge-color contributions |
| `$3661` | Orders line endpoints, selects generated line code, and temporarily installs/restores RTS endpoints |
| `$28B7`, `$29C9` | Generate prefix-XOR fill and plain-store clear code |
| `$37A3` | Builds a 16×16 column-major screen map starting at `$04AC`, screen row 4 / column 12 |

Interpreting the literal coordinate bytes around bias 128 gives ring Y values 121, 103, 68, and 24. The forty points' radii range from approximately 122.935 to 124.744, consistent with a quantized sphere surface. Runtime paired outputs supply the other half. Default count operands are 70 strip faces and 150 edges; two cap cases receive separate handling. An 80-vertex / 150-edge / 72-face sphere topology is consistent with these observations, but full adjacency reconstruction has not yet been proven.

The generated fill reads marker bytes around `$F700` and writes the wrapped `$1100`-offset charset around `$0800`. This is a close architectural relative of a column-major charset/prefix-fill renderer. The generated lookup tables are computation aids; their presence is not evidence of stored complete animation frames. Conversely, this static analysis alone does not prove which branches execute each displayed frame, a native frame rate, or that this is the exact sphere in the user's screenshot.

The reproducible coordinate/count receipt is `static/n2-geometry-candidate.json`. `f1` is another geometry/line candidate: it contains three evolving angle-like bytes, generated clear code, coordinate interpolation, and XOR line routines. Its cube/sphere image identity remains open.

## Live comparison limits

The original loader copy matches the `live-01/ram-loader-init.bin` capture exactly. A second native session compares `live-02/ram-before-intro.bin` with `ram-intro-entry.bin`:

- Only eleven raw RAM bytes change: `$00A2`, `$01EF..$01F6`, and `$C2A7..$C2A8`.
- `$C2F0..$C2F3` remain zero. The side-2 marker `$C2F8 = 2` matches its one-byte decoded output.
- No complete part payload matches at this point. `$0810` is the boot-resident page copied from `$2000`, not a newly unpacked vector effect.

`static/live-intro-comparison-complete.json` records raw comparisons with **no I/O or stack exclusions**, all mismatch ranges, and the eleven before/after values. This explains precisely what the captures establish without turning a bootstrap breakpoint into a claimed running renderer.

Reproduction commands and artifact meanings are in [the research README](../../research/tower-power/README.md). No production renderer code, emulator preview, or renderer build output was changed by this lane.
