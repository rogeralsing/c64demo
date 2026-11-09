# Aloft: fresh original startup and two clean loader returns

A new original-side-one run captures the real bootstrap and the first two loader-return boundaries. **All seven RAM/VSF pairs follow natural checkpoints**, with no interrupt, observation timeout, warp, restart, snapshot restore, disk change, PC assignment or memory injection. The separate [source decoder](aloft-stream-20261109.md) and [independent native binding](aloft-stream-binding-20261109.md) use these states only after their original-disk predictions exist.

This case is `build/research/aloft-decode-20261109/native-01`. The earlier `build/research/aloft-20261109/native-01` remains a different, unchanged case. Local filenames and process identifiers must not merge their histories.

## Original input and closure

The original side-one D64 remains 174,848 bytes, SHA-256 `d13eae8daeada64bc61772a2dad2d3e62d1a0d30a34b29103119535610e4cfce`. Both autostart and drive8 arguments point to that unchanged original. VICE 3.10 runs MOS8565 PAL, true 1541, `Speed=100`, warp off. The final resource queries are retained; dummy-access checkpoints are off.

Root owned PID **1362**, monitor port **50817**, tool session **38123**. The case opened **9 November 2026 08:01:02 UTC** and closed **08:12:43 UTC**. The observer exited zero; its owned VICE process exited −15 after explicit closure and was reaped. That tool session is terminal. Any future native work needs a new owned case. A restore must establish both C64 and full drive/IEC lineage; a C64-only match is insufficient.

The [closed file listing](../../build/research/aloft-decode-20261109/native-01-files.json) freezes **21 files / 1,931,646 bytes**. The 3,375-byte listing has SHA-256 `6f9ed78bcb25851fce974ae521436052cfa7d0529830ffa1b51fa5a8b4b4c475`; its canonical sorted file rows hash to `e568147ffd6ce025aca5868b95748db5b93925cb37d8d2240be7e4ea2c88bfe9`.

Complete raw input/sent/received streams, events, text logs, session metadata and seven pairs remain. There are **56 completed ordinary responses**, two internal and 54 public. No command is retried or cancelled. The passive auditor checks exact wire ranges and serialized framing, all active checkpoint/stop associations, complete 65,536-byte physical RAM equality, CPU registers/flags/clock/ports and VIC/monitor beam agreement for every pair. It does not execute a CPU.

## Natural source phases

| Capture | CPU PC | PAL machine clock | Line/cycle | SP |
| --- | --- | ---: | --- | --- |
| `sys` | `$0810` | 6,977,187 | 301/0 | $F6 |
| `postcopy` | `$08B5` | 7,056,424 | 310/46 | $5F |
| `first-receive-entry` | `$019F` | 8,739,203 | 189/32 | $5D |
| `first-packet-ready` | `$021C` | 9,380,860 | 78/34 | $5D |
| `first-payload-entry` | `$FE00` | 9,423,692 | 134/26 | $5F |
| `second-request` | `$FE41` | 9,434,894 | 0/14 | $5F |
| `second-return` | `$FE44` | 10,036,048 | 182/22 | $5F |

At `$0810`, **all 830 loaded payload bytes** equal the authentic original DOS PRG at `$0801..$0B3E`. This is a complete bootstrap comparison, not only an opcode resemblance. At `$08B5`, all **416 bytes at `$0160..$02FF`** equal the independently derived resident before subsequent PAL/receiver patches. The original archive, DOS and resident source identities remain owned by the earlier studies.

The original installer pushes `$FDFF`; first receive entry `$019F` has SP `$5D` and exact stack bytes `FF FD` at `$015E/$015F`. The natural first return is `$FE00`, SP `$5F`. Thus the previously source-derived initial destination is now observed directly.

The `$021C` pair is before the first depacker entry consumes the received packet. The prior `$019F` state and unchanged original stack/source generation identify that path. `$0300..$03FF` is an **unconsumed received-packet oracle**, not source data for the disk transport predictor. Later packet-buffer metadata belongs to another generation and cannot replace it.

At `$FE00`, the first payload has returned but has not run its initialization. Its independently predicted bytes can therefore be compared without application patches. The original decoded path later calls `JSR $021C` at `$FE41`; `$FE44` is the natural continuation after the next bundle. There is no new indexed-command argument at that call. The [binding study](aloft-stream-binding-20261109.md) checks source-derived directory equivalence, format state and the intervening application boundary separately.

## The earlier missed guard is now explained

The older case accepted a syntactically valid but unparenthesized compound predicate. VICE's condition grammar evaluates all operators at one left-associative precedence. The exact old expression is always false, regardless of RAM contents. The [new condition study](vice-condition-precedence-20261109.md) proves that cause without rewriting any older observation or uncertainty statement.

This fresh SYS stop is unconditional. Before first packet decoding, root separately installed the old ungrouped predicate as checkpoint6 and the correctly grouped predicate as checkpoint7 at `$021C`. Both setup responses completed before execution; the unconditional packet checkpoint was disabled. The natural stop is **checkpoint7**, while the original byte pair at `$0810/$0811` is still `$A9/$FF`. The raw witness and official parser/evaluator remain in the separate proof.

## Scope, failures and replay

These are startup/loading observations, not complete effects, delivered FPS, physical IEC timing or analog display output. The native auditor does not reconstruct decompressed bytes from disk; that is the separate source decoder's job. It also does not pretend the chosen software packet order is a native rotational trace.

The first auditor candidate passed its narrower same-stop checks. A later source-binding addition temporarily shadowed its Python adapter-source variable with a Path; receipt serialization failed before the output directory existed. Its exact checked source was retained by reversing the three name-only corrections, with that reconstruction explicitly declared. The first retention attempt's missing-file error is also recorded. The corrected current producer passes. No native state changed, no capture was discarded and no case restarted.

The [current native proof](../../build/research/aloft-decode-20261109/native-analysis/accepted-01/native-proof.json) is 64,905 bytes, SHA-256 `bf53a544369a8acddde7354874b9f93302728497bd59a12c5c97b19e5c691b41`. The [producer](../../research/aloft-decode-20261109/native.py) is 15,821 bytes, SHA-256 `61adb5cd5449c0742f2286de00061d6ecf182684f33888ea28feb9ba18ce2ea8`.

Independent full-source peer review and fresh replay reproduced **both outputs / 80,726 bytes exactly**. The [peer report](../../build/research/aloft-decode-20261109/native-analysis/peer-replay-check.json) is 1,312 bytes, SHA-256 `6892cc4c00a9cce63040d65e4e2bf012094b8c5eb703e9791f4f6f4b3687511b`.

```sh
rtk proxy python3 -B research/aloft-decode-20261109/native.py --output build/research/aloft-decode-20261109/native-analysis/replay-NEW
```
