# Aloft: closed original side-one native case

A fresh run booted the original Aloft side-one D64 through VICE's normal disk autostart and true 1541 emulation. The closed case retains **25 complete RAM/VSF pairs and fourteen screenshots**. Twenty-four pairs follow natural execution checkpoints; the first is an explicitly interrupted orientation observation. This supplies original runtime generations for the separate [part-localization study](aloft-parts-20261109.md) and [Kefrens source study](aloft-kefrens-20261109.md). It does not independently decode compressed disk resources or predict committed pixels.

The [case listing](../../build/research/aloft-20261109/native-01-files.json) freezes **71 files / 7,001,061 bytes**. Its 11,098-byte JSON has SHA-256 `db333462f5b220f3eb987e13099de52e7c9bced440528182851dce9cfc93c65b`; the canonical sorted name/size/hash rows have SHA-256 `0164e695fa631e1789304a636381dcd4c460d11e61a89343b365d0d87844a187`. No file in the closed native case is subsequently edited.

## Original input, ownership and complete wire

The disk is [the unchanged original side one](../../build/research/aloft-20261109/disk-analysis/accepted-01/Aloft-Side1.d64), 174,848 bytes, SHA-256 `d13eae8daeada64bc61772a2dad2d3e62d1a0d30a34b29103119535610e4cfce`. [Original archive/DOS custody](aloft-original-20261109.md) and [source-bound loader identity](aloft-loader-20261109.md) remain distinct proofs.

The root owned one observer and one VICE process: PID 57148, monitor port 60796, opened **9 November 2026 07:16:13 UTC**, closed **07:34:14 UTC**. The observer exited zero; the owned VICE process exited −15 after explicit closure and was reaped. Tool session 42636 is terminal and must not be reused. The program and `-8` disk arguments both identify that original D64. No second disk, snapshot restore, payload injection, PC assignment or memory-write command occurs.

The complete `input.bin`, `sent.bin`, `received.bin`, `events.jsonl`, `monitor.log`, `vice.log` and `session.json` remain. The passive [native auditor](../../research/aloft-20261109/native.py) verifies contiguous byte ranges, serialized sends, every request/response, the one interrupt on the same pending connection, and process closure. There are **192 ordinary responses: 191 completed and one interrupted**, including two internal setup commands and 190 public monitor commands. One 30-second waiting notice is retained; it did not cause a resend or restart.

The auditor reuses the pinned strict wire validator with one explicit startup-assertion adaptation: original-disk autostart replaces its older manual-monitor-load assumption. The exact old assertion, replacement and function hashes are retained. No raw monitor bytes are regenerated from replacement-decoded Unicode. Disassembly and I/O text may contain PETSCII; raw bytes carry their identities.

## The initial SYS checkpoint was not observed

The first short checkpoint was accepted at `$0810` with two original bootstrap-byte predicates. The subsequent run did not stop there. A read-only interrupt observed music code at `$0CB4`, clock 73,218,600; the screenshot showed the in-flight menu and TunnelVision inset. The cause of the missed initial SYS stop remains unresolved. It is not evidence that the bootstrap failed or that a particular startup entry was observed.

That orientation state has wrapper counter `$13` and an already installed, runtime-patched loader. It cannot replace a genuine pre-installer capture or prove the configured first `$FE00` return. Later loader and driver checkpoints were created separately, their complete successful setup responses inspected before dependent execution. Their actual stop addresses, active checkpoint IDs and saved generations are checked independently.

## Same-stop state and phase boundaries

Each RAM file is exactly 65,536 bytes and equals the complete physical RAM in its paired VSF. CPU registers, flags, clock, port state and CPU-derived monitor beam coordinates agree. All twenty-four natural captures also agree with the core VIC line/cycle state. The orientation frame-boundary distinction below remains explicit.

The names `part01` through `part09` are local observation aliases. They are not DOS filenames, proven compressed-resource IDs or a definitive effect list. The byte at `$088D` is the observed wrapper counter; it is not automatically a directory slot. `$0890` is repeatedly overwritten by original loading, so the same PC denotes several different code generations. `$021C` can also re-enter inside depacking; stops there do not count external resources.

| Observation alias | CPU PC | PAL machine clock | Monitor line/cycle | `$088D` | Stop kind |
| --- | --- | ---: | --- | --- | --- |
| `orientation` | `$0CB4` | 73,218,600 | 0/0 | `$13` | read-only interrupt |
| `loadnext01` | `$021C` | 77,417,673 | 195/60 | `$14` | natural checkpoint |
| `part01-entry` | `$0890` | 77,899,516 | 44/16 | `$14` | natural checkpoint |
| `part02-entry` | `$0890` | 79,475,122 | 93/55 | `$15` | natural checkpoint |
| `part03-entry` | `$089A` | 80,893,308 | 140/48 | `$16` | natural checkpoint |
| `part04-entry` | `$08A0` | 81,884,631 | 276/3 | `$17` | natural checkpoint |
| `part05-entry` | `$0890` | 85,940,595 | 72/27 | `$18` | natural checkpoint |
| `engine-body` | `$E021` | 85,991,494 | 256/22 | `$18` | natural checkpoint |
| `engine-raster01` | `$E149` | 86,352,472 | 58/10 | `$18` | natural checkpoint |
| `engine-raster02` | `$E149` | 86,372,129 | 58/11 | `$18` | natural checkpoint |
| `part06-entry` | `$0890` | 99,375,303 | 225/48 | `$19` | natural checkpoint |
| `part06-initialized` | `$0893` | 99,495,185 | 256/41 | `$19` | natural checkpoint |
| `part06-precopy` | `$08A4` | 109,545,058 | 34/28 | `$1C` | natural checkpoint |
| `part06-postcopy` | `$08C5` | 110,408,766 | 16/6 | `$1C` | natural checkpoint |
| `part06-afterclear` | `$08DD` | 117,800,216 | 28/44 | `$1C` | natural checkpoint |
| `part07-entry` | `$0890` | 120,584,230 | 227/25 | `$1D` | natural checkpoint |
| `part07-armed` | `$08AA` | 121,376,762 | 15/17 | `$1D` | natural checkpoint |
| `part07-generated` | `$08AD` | 121,447,406 | 200/38 | `$1D` | natural checkpoint |
| `part07-frame01` | `$8239` | 122,724,460 | 191/19 | `$1E` | natural checkpoint |
| `part08-entry` | `$0890` | 129,591,314 | 300/62 | `$1F` | natural checkpoint |
| `part08-body` | `$F02B` | 130,163,026 | 15/49 | `$1F` | natural checkpoint |
| `part08-frame01` | `$F080` | 131,462,237 | 46/11 | `$20` | natural checkpoint |
| `part09-entry` | `$0890` | 139,024,525 | 274/31 | `$21` | natural checkpoint |
| `part09-body` | `$2116` | 139,024,549 | 274/55 | `$21` | natural checkpoint |
| `part09-frame01` | `$2190` | 141,283,305 | 248/9 | `$22` | natural checkpoint |

The native images distinguish an in-flight menu, seatbelt transition, keyboard scene, full-screen blue/green Kefrens, airline text/sprites over waves, vertical multicolor ribbons and yellow bob/coin shapes. These observations do not identify the discussion's named three-layer moving pattern. A separate [browser orientation record](../../build/research/aloft-20261109/video-orientation-01.json) records the real-hardware video's three horizontal checker bands at 2:31, with no source-to-code association inferred. No video or audio was downloaded, and the temporary browser tab was closed.

## CPU-derived coordinates and a genuine VIC frame-wrap state

The first auditor candidate incorrectly required the core VIC beam to equal monitor coordinates at every boundary. Its checked source, failure record and [diagnostic](../../build/research/aloft-20261109/native-analysis/candidate-01-diagnostic.json) remain. It found one exact exception: orientation has CPU clock **73,218,600**, monitor **line 0/cycle 0**, and core VIC **line 311/cycle 0 with `start_of_frame=1`**. CPU clock and all RAM/register state still agree.

The retained VICE 3.10 primary sources explain this distinction. `src/c64/c64.c` lines 1298–1303 derives monitor line/cycle directly from `maincpu_clk`. `src/viciisc/vicii-cycle.c` sets `start_of_frame` at the final line, while its frame-start branch resets `vicii.raster_line` at `VICII_PAL_CYCLE(2)`. `viciitypes.h` line 47 defines that macro as `(c)-1`, so the reset occurs at **zero-based cycle 1**. The snapshot writer serializes those raw VIC fields. The accepted auditor checks this exact source-bound orientation exception; it neither changes the snapshot nor silently equates the two counters. All other captures retain exact core/monitor equality.

## Observation limits and replay

Final resource queries report `VICIIModel=1` (MOS8565 PAL), `VICIIBorderMode=0`, `Speed=100` and warp enabled. Warp was enabled only after the first orientation observation; clock deltas remain emulated machine cycles, not wall time or delivered FPS. Dummy-access checkpoints were off. No complete bus-store trace was collected in this case.

Current snapshot mode/register values are boundary state. Raster code can change modes and banks within a field, so a single `$D011` value does not classify an entire effect. Screenshots are native output observations. Neither the images nor VSF draw buffers are independently reconstructed scanout, a complete animation, analog output or performance proof.

Choose a fresh output path:

```sh
rtk proxy python3 -B research/aloft-20261109/native.py --output build/research/aloft-20261109/native-analysis/replay-NEW
```

The [accepted native proof](../../build/research/aloft-20261109/native-analysis/accepted-01/native-proof.json) is 212,727 bytes, SHA-256 `02243d0cbae68edad8aa5a51aec9e22e9cfa4c52f918f1ba30db9e5226b19eb4`. The producer is 13,727 bytes, SHA-256 `dbb1a2f351cb0f60cb4ded9d4bae93ca65d3be2099bd8f7a475d6735a4287e45`.

Independent full-source peer review and a fresh replay reproduced both outputs / **226,454 bytes** exactly. The [peer report](../../build/research/aloft-20261109/native-analysis/peer-replay-check.json) is 2,352 bytes, SHA-256 `21d463b1c450df0541e0dff4c377ec005b2a1444f7727d3e855275804131a006`. The peer also verified all four retained beam-source bodies against unique members of the pinned original VICE archive.
