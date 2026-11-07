# Colors: native bootstrap and first handoff

Research date: 7 November 2026. The owner cold-boots the acquired original side 1 D64 in VICE C64SC. This lane passively checks the saved RAM and snapshots against [the extracted boot and identified Sparkle loader](colors-binary.md). It starts no emulator or CPU interpretation.

The **final closed-session gate passes all 17 RAM/VSF pairs**, the known boot/resident byte contracts, and three bounded stable-field phase intervals. It records 11 PNGs as observations. Complete first-image decoding, pixel/color ownership, and analog interpretation remain separate contracts.

## Original route and exact byte checks

The disk is `Colors [Lethargy] 1.d64`, SHA-256 `94bde11ed515f6312fbd77efff9f1fe5c2cdbf25587f0eabada566e0430b1ad6`. This is the acquired current pack's side A, not a substituted boot PRG or older mirror. The owner reports normal original-disk autostart without program-counter or algorithm patches. The command and transcript are preserved in `build/research/colors/native-01/`.

The owner stopped capture at **11:41:57 UTC**. The helper exited with status 0 and cleaned up its owned VICE process with status −15. This is a completed capture session, not a claim that the demo naturally terminated or reached its end.

| Natural stop | Emulated clock | Register-observed raster | Contract |
|---|---:|---:|---|
| BASIC `SYS2064` entry, `$0810` | 6,886,148 | 103, cycle 59 | All 847 loaded boot bytes at `$0801..$0B4F` match the original PRG payload. |
| After resident copy, `$08C7` | 6,963,899 | 90, cycle 5 | All 416 bytes at `$0160..$02FF` match the literal copy oracle; all 416 source bytes at `$09B0..$0B4F` remain original. |
| First configured return, `$8000` | 13,118,578 | 127, cycle 25 | Observed original first-image handoff; no independent unpacked-image byte oracle yet. |

For every capture, all **65,536 physical RAM bytes** equal the same-stop VSF RAM. The 17 pairs provide **1,114,112 exact comparisons**, with no excluded addresses. Both the monitor-observed PC and clock must match the `MAINCPU` snapshot fields. Snapshot schema and reader hashes are recorded; underlying RAM is taken from the official `C64MEM` layout, not CPU-visible ROM or I/O reads.

The clean resident checkpoint precedes the boot's PAL/NTSC receiver adjustment. Later self-modification is not accepted through a broad mutable mask: the first-handoff record retains every difference from the original resident as an observation. This separates the exact installation proof from the later loader state.

## What the `$8000` observation establishes

The original side 1 boot pushes `$7FFF` and jumps into Sparkle's `LoadFetched` entry at `$019F`. Its eventual return reaches `$8000` naturally. The captured first bytes are:

```text
8000  78 A9 35 85 01 A9 00 A8 AA 20 00 09 A9 7F 8D 0D
8010  DC 8D 0D DD AD 0D DC AD 0D DD EE 19 D0 A9 00 8D 0E
```

That signature is a native observation, not bytes predicted by an offline bundle decoder. The loader/source identification does not by itself reconstruct the first bundle or validate the renderer. No Bitfire directory, Dali entry, RGB-line schedule, effective palette size, or analog blending behavior is inferred from it.

## Four consecutive stable fields

After the owner allowed the initial transition and 64 multiplex fields to run, four captures stop at **`$8E4E` before the next phase update**. This point follows the completed previous PAL beam. The captured phase and `$D018` therefore belong to that completed field, while the CIA2 direction register still reflects its last bank.

| Capture | Clock | Register-observed raster/cycle | Phase | `$D018` |
|---|---:|---:|---:|---:|
| `stable-field-a` | 22,820,879 | 4 / 11 | 0 | `$9A` |
| `stable-field-b` | 22,840,534 | 4 / 10 | 1 | `$9C` |
| `stable-field-c` | 22,860,190 | 4 / 10 | 2 | `$9E` |
| `stable-field-d` | 22,879,845 | 4 / 9 | 0 | `$9A` |

Their raw clock gaps are 19,655, 19,656 and 19,655. The corresponding capture-position differences are −1, 0 and −1 clocks. Subtracting those offsets gives **19,656 clocks for every interval**, exactly one 312×63 PAL frame. Phase advances by one modulo three in each interval. This validates those three native controller intervals; it does not establish the cadence of every scene or a three-frame period for the moving image.

The remaining captures include five helper observations, multiplex entry/warmup, and three traced fields. The checker enumerates all of them and retains phase, selected charset, sprite colors and pointer tables at each `$8E4E` stop. It records all 11 same-stop PNGs without treating them as an independent pixel oracle. Store-trace interpretation and the full pixel model belong to their separate analyzer.

## Reproduce the passive preflight

```sh
python3 research/colors/native_capture.py --allow-live
```

The [passive checker](../../research/colors/native_capture.py) reads the existing original input and capture files only. It requires register-observed capture context, full raw RAM, and a matching snapshot. Explicit basenames distinguish restored comparisons that share a PC and clock. It records all mismatches and retains first-image/resident observations separately from established byte assertions.

The earlier [provisional receipt](../../build/research/colors/native-analysis/native-evidence-provisional.json) remains separate. The final closed-session command is:

```sh
python3 research/colors/native_capture.py
```

The [final receipt](../../build/research/colors/native-analysis/native-evidence.json), SHA-256 `d38ea71eaa9a7e5cfa9bf20aeefa968e59c99b46287c3a4abf949cc573af3e9c`, requires the known boot/resident stops and first-handoff observation, checks every capture pair, and separately records the bounded field cadence.

Later screenshots or unclassified capture states remain observations unless an independent consumer, pixel, or timing contract is added by their owning lane. The session lifecycle and original disk integrity remain explicit in the evidence.
