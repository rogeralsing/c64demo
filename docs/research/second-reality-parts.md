# Second Reality C64: the first custom-loader file sequence

Research date: 7 November 2026. This batch binds observed requests to six original side 1 DOS files. It follows the [bootstrap reconstruction](second-reality-binary.md), but does not rerun or alter that proof. The payload references come from disk bytes; native RAM is used only for comparison. No CPU execution, hardware stub or emulator action is performed by [parts.py](../../research/second-reality/parts.py).

## Source and loader contract

The source is the original `2ndReality_S1.D64`, 174,848 bytes, SHA-256 `05aa03c00be26cab0618f8802477d0bc7226af029c003a253a34bd32c630acf2`. The script independently follows each selected DOS chain and pins the resulting PRG hash. Directory artwork and displayed block counts are not interpreted as payload boundaries. The [complete disk inventory](second-reality-disk-map.md) provides the wider context. [Original author archive](http://www.smash-designs.de/releases/c64/2nd_reality.zip), [CSDb original archive](https://csdb.dk/getinternalfile.php/71054/2ndreality.zip)

The independently unpacked loader at `$CF00` supplies the file protocol evidence:

- `$CF74` sends **X first, then Y** through `$CF94`. These two bytes identify the requested directory prefix.
- Two received bytes become the low/high destination operands at `$CF3B/$CF3C`. `$CF3A` then stores the received payload and increments that destination.
- `$CF01` is the operand of the entry `BIT` instruction. `$CF32` increments it after each received header. Its changing value is recorded separately from the fixed loader signature.
- A is masked with `$EF`. The observed modes here are `$00` and `$08`; this note does not infer the complete semantics of every mode.

The loader therefore directly places the following file bodies at their two-byte PRG load addresses. Calling them all compressed parts would be unsupported.

| Prefix | PRG bytes, including header | Payload bytes | Loaded range, inclusive |
|---|---:|---:|---|
| `AA` | 322 | 320 | `$9000..$913F` |
| `BC` | 14,658 | 14,656 | `$8600..$BF3F` |
| `BA` | 5,122 | 5,120 | `$0C00..$1FFF` |
| `BB` | 12,290 | 12,288 | `$3000..$5FFF` |
| `BD` | 2,306 | 2,304 | `$C000..$C8FF` |
| `CA` | 6,146 | 6,144 | `$6000..$77FF` |

All six complete file and payload hashes, sector links and original sector hashes are in [parts.json](../../build/research/second-reality/parts/parts.json). The extracted `side1-*.prg` files live beside that receipt.

## The observed request chain

The native continuation selected SID through the original configuration handler. At that configuration checkpoint, `$50` changed from 0 to 3; `$51/$52` remained 0. Those zero-page addresses are reused later and are not persistent configuration storage.

The first actual `$CF00` call in this continuation has A=`$00`, X=Y=`$41`: **`AA`**. The stack return is `$CE33`. The caller at `$CE2A` requests `AA` at `$CE30`, repeats the same request at `$CE39`, and jumps to `$9000` at `$CE3C`. This is distinct from the earlier, statically found `$CE0B` launcher phase with X=`$5A`.

`AA` starts with ordinary setup code: it disables raster IRQ generation, restores an IRQ vector, selects `$01=$37`, copies a page from `$9100` to `$CE00`, clears `$C900/$CA00`, and jumps to `$CE00`. The executed launcher head is fully present in the file:

```text
CE00  A2 42 A0 43 A9 00 20 00 CF A2 00 A9 00 9D 00 CB
CE10  E8 D0 FA 4C 00 90
```

It requests **`BC`** at `$CE06`, clears `$CB00..$CBFF`, then jumps to `$9000`. This is a launcher, not an entry depacker.

There is an important source boundary: `AA` establishes only `$9100..$913F`, or **64 bytes** of the 256-byte copied source page. The remaining **192 bytes at `$9140..$91FF` are not established by AA**. No zero fill or stale bootstrap image is substituted for them. A complete native page-copy transition needs the actual pre-copy RAM, separately from this file-derived head.

`BC` contains code at `$9000` that directly initializes display memory and VIC registers. Its later helper supplies this sequence:

| Call instruction | Request | A | Immediate successor |
|---|---|---:|---|
| `$97C0` | `BA`, inherited from caller and observed natively | `$00` | `$97C3` |
| `$97C9` | `BB` | `$08` | `$97CC` |
| `$97D2` | `BD` | `$08` | `$97D5` |
| `$97E0` | `CA` | `$00` | `$97E3` |

Between `BD` and `CA`, `$97D7` calls `$0C00`, inside the loaded `BA` body. After these preloads, the continuation at `$91C0` fills `$CC00..$CFFF` with `$BC`, overwriting the resident loader. Later bytes at `$CF00` cannot be interpreted using its earlier signature.

## CA is staged at $6000

The `CA` header establishes a **load destination**, not an execution entry. Its first bytes at `$6000` are:

```text
A9 00 8D 20 D0 8D 21 D0 8D 11 D0 8D 15 D0 20 90 C3
A2 00 BD 00 04 9D 00
```

The staged code contains `$C000`-space absolute targets, including the first `JSR $C390`. That target also lies within the prior `BD` load range, but overlap alone does not establish an executed dependency. **This note does not identify `$6000` as a graphics entry.** Relocation, the actual handoff and the effect's renderer belong to the subsequent part analysis.

## Native comparison and limits

Seven complete raw-payload comparisons pass, with no byte exclusions:

| File | Native checkpoint | Bytes compared |
|---|---|---:|
| `AA` | First loader return and first `$9000` part checkpoint | 320 at each |
| `BC` | Its `$9000` checkpoint | 14,656 |
| `BA` | Following `BB` request | 5,120 |
| `BB` | Its loader return | 12,288 |
| `BD` | `$97D5` return | 2,304 |
| `CA` | `$97E3` return | 6,144 |

That is **41,152 byte comparisons** including the repeated AA observation. Each record retains the raw RAM hash, exact range and every mismatch; all mismatch lists are empty. These checks establish placement of the original file bodies, not an effect's timing, visual role or compression method. The separate [native continuation note](second-reality-native-parts.md) owns capture context, RAM/VSF correspondence, lifecycle and any broader transition proof. Native-02 is a continuation from a previously validated snapshot, not a second uninterrupted cold boot.

Reproduce this extraction/comparison without an emulator:

```sh
python3 research/second-reality/parts.py
```

The standard-library script reads the original disk and frozen bootstrap proof, extracts six files, and optionally compares the named native captures. Its JSON separates `files`, `protocol`, `AA_projection`, `BC_requests`, `CA_staging`, `observed_native_calls` and `native_payload_comparisons`. Missing optional native files are listed rather than silently treated as a successful native observation.
