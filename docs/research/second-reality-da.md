# Second Reality: CA exit, DA/DB preloads and the restored CB bridge

Research date: 7 November 2026. The next request after CA is **DA**, but DA's `$4000` header is a **data transfer address**. The next observed execution entry is **DB at `$C000`**. Between them, code from the previously loaded CB file is restored from RAM under I/O, initializes a temporary display, and loads **DA, DB, EA and EB**. No assumed CC file or direct `$6000` entry is used.

All four complete file bodies match their native loader returns. Their actual loader end pointers also match the exact payload ends. This [passive checker](../../research/second-reality/inspect_da.py) performs no CPU, loader, drive, emulator or new acquisition work. The [DB effect analysis](second-reality-db.md) separately owns preparation and runtime rendering.

## The code that crosses the effect boundary

CA exits its point field through `$C8AA → $C989 → $CA2A`. Its reachable exit code uses `$01=$34` to read physical RAM beneath I/O, with raster polling between copy groups:

- `$DC00..$DFFF → $0800..$0BFF`: the last 1 KiB of the previously parked CB file.
- `$D000..$DBFF → $8000..$8BFF`: CB's first 3 KiB of graphic data.

It restores `$01=$36` after each group and executes **`JMP $0900` at `$CAE2`**. The input CB is the original 4,096-byte payload with header `$8000`, PRG SHA-256 `7ae9c9ad3040539c4659b4b370f161ccfd1b99677f2a8db042b21d8de9201955`.

The frozen CA iteration-D capture contains all 4,096 original CB bytes at `$D000..$DFFF`, and they remain exact at the later DA call. The restored CB graphic range and instruction ranges also match. The receipt retains a complete comparison of the 1 KiB restored tail, including its three color-table cells; **this particular capture has no differences**.

CB's restored entry `$0900` initializes a multicolor character display, then reaches `$0B50 → $0880`. The original `JSR $0800` there enters the preload routine. Thus the bridge is existing original code, not a newly injected program or a guessed execution address from a header.

## Actual requests, exact payloads and returns

Each setup loads X/Y with the two ASCII filename bytes and A with `$00`, then calls `$CF00`. The first request was captured directly at `$CF00`, **clock 307,281,968**, A=`$00`, X=`$44`, Y=`$41`. The later back-to-back request setups are checked against the original CB bytes.

| File | Original payload | JSR / real return | Native return clock | Actual `$CF3B/$CF3C` end pointer |
|---|---|---|---:|---|
| DA | `$4000..$47FF`, 2,048 bytes | `$0840 / $0843` | 309,201,376 | `$4800` |
| DB | `$C000..$CBFF`, 3,072 bytes | `$0849 / $084C` | 311,246,041 | `$CC00` |
| EA | `$6000..$6EE8`, 3,817 bytes | `$0852 / $0855` | 313,650,839 | `$6EE9` |
| EB | `$7000..$7F87`, 3,976 bytes | `$085B / $085E` | 316,242,809 | `$7F88` |

All **12,913 payload bytes** match their original files at these returns. The complete PRG hashes, including each two-byte load header, are:

| File | SHA-256 |
|---|---|
| DA | `e3cb254ab2362ec54cca87386dd388658736953c163f89b607cb7781af65c137` |
| DB | `1c820bd4bc9d47a78f4c3c291be3a2ef7fd4f7a6754843632cfaf8410a48a8f2` |
| EA | `2444dd10effe58b3bc96decaf0199f75433aa74f03a5815bb4445512943ca8ce` |
| EB | `9c0758f571f5ba71b3224a9d1ed1084d07b1adc7e50374e68f07fbcec548f887` |

These are the pinned original DOS-chain files, not bytes reconstructed from a viewer or a fabricated disk response. The loader's actual end pointers show that the non-page-aligned EA and EB bodies stop at their logical ends.

## The 399 bytes that are not EA/EB file data

The EA transfer leaves **279** bytes at `$6EE9..$6FFF` unchanged; the EB transfer leaves **120** bytes at `$7F88..$7FFF` unchanged. The checker compares the actual before/after RAM at each boundary rather than supplying zero padding.

The bridge then changes part of the first gap deliberately. At `$085E..$0877`, it copies the current **256-byte loader page `$CF00 → $6F00`** and clears **`$CC00..$CFFF`**, including the retired original loader page. Every backed-up and cleared byte matches that literal transition. After a short palette transition, **`JMP $C000` at `$08C6`** enters the newly loaded DB file. The native entry is clock **316,575,687**, raster 250/raw cycle 57, with its original `A9 00 85 50 A9 E0 85 51...` guard.

DB's `$C039` routine subsequently copies the **entire** `$6000..$7FFF` staging interval to `$2000..$3FFF`. The prepared capture matches all 8,192 bytes against the actual DB-entry prestate, divided precisely as follows:

| Later destination | Proven origin |
|---|---|
| `$2000..$2EE8` | All 3,817 EA payload bytes. |
| `$2EE9..$2EFF` | 23 preserved pre-RAM bytes; not EA data. |
| `$2F00..$2FFF` | 256 explicitly copied loader-backup bytes; not EA data. |
| `$3000..$3F87` | All 3,976 EB payload bytes. |
| `$3F88..$3FFF` | 120 preserved pre-RAM bytes; not EB data. |

Thus **399 bytes outside the EA/EB bodies comprise 143 stale prestate bytes and 256 loader-backup bytes**. The full copy is a conditional native-prestate contract. Only the two stated payload subranges are independently labelled EA/EB file data. Later code jumps toward `$2E00`, but the headers alone do not establish future effect identities or algorithms.

## Reproduction and limits

```sh
rtk proxy build/research/tower-power/cpu-venv/bin/python \
  research/second-reality/inspect_da.py
```

The [receipt](../../build/research/second-reality/da-analysis/da-transition-proof.json) passes all **18 transition checks**, preserves the raw/snapshot hashes, complete comparisons and source call arguments, and requires the owner-closed `native-03` session. The [separate native continuation record](second-reality-native-next.md) owns restore/CPU/beam lineage and joins these exact payload results.

Script SHA-256: `b82fd261e2a167e8592aff59a427a60cf3354f28ccaf0bf28249652b6cb93737`. Receipt SHA-256: **`eb75376e089794a6d1468090274b8a27259e3550b91f3139566e95e87beffe2c`**.

This proves the original request chain, actual transfers, preserved gaps and DB entry. It does not infer execution at DA/EA/EB headers, invent missing bytes, establish drive timing, or identify a named renderer from the directory order.
