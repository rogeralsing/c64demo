# Dragonbond: all-eight full-successor tail fetches

The separate closed `native-03` continuation supplies the previously missing
bank-`$8000` full-successor tail data. All eight actual VIC sprite latches match
the original released successor bytes at offset 48 and differ from the old
and intermediate tail bytes. The passive
[owner/data audit](../../research/dragonbond/native_tail.py) checks that result,
its raw monitor wire, restored state and owned-process closure without starting
an emulator or executing C64 code.

## Exact continuation and stop

Parent is `native-02/bank80-after-full-new.vsf`, SHA-256
`79a7cd97a25334167698fac3603037c6069e2c3d98e6de7ce3b1824bf3f86ea1`:
PC `$3278`, clock 149,028,238, raster 255 / raw cycle 37. Before execution,
the new capture's complete **C64MEM, MAINCPU, CIA1, CIA2 and VIC-II module
payloads** equal that parent. Both new checkpoints include same-stop full
65,536-byte RAM dumps and matching CPU registers, ports, beam and snapshots.

The new live observer starts once with the original disk attached and no
autostart. One explicit restore is declared; no CPU data/PC patch follows it.
Observed warp-off and Speed=100 precede the only execution resume. This new
case uses an any-PC condition:

```text
break exec 0000 ffff if RL == $10b
```

It naturally stops **730 clocks later**, at PC `$12A9`, clock 149,028,968,
raster **267 / raw cycle 11**. The original current instruction is
`LDA $2306,Y`. The saved stack return `$2A6D` corresponds to the original
`JSR $1006` at `$2A6B`, placing this stop inside the music-call path rather
than the `$2808` main loop. This is consistent with why a main-loop-only
raster condition could miss; it is not an instruction trace of the entire
old failed observation.

The prior `native-02` missing capture, incomplete helper metadata and external
cleanup stay unchanged. This is a new bounded continuation from its last
valid snapshot. The [earlier lineage note](dragonbond-native.md) remains the
record of those original outcomes.

## Actual tail data

CIA2 PRA `$C1` and DDRA `$3F` select VIC bank `$8000`. The actual pointer
table is `$83F8..$83FF`, with pointers `$20..$27`; all saved sprite Y values
are 250. All eight DMA and display bits are active, `$D017=0`, and each
sprite has MC=51 and MCBASE=48. The completed three-byte fetch therefore
comes from offset `MC−3=48`, row 16 of the corresponding 63-byte sprite.

| Sprite | Full pointer | Actual latch | Original old-tail bytes |
|---|---:|---|---|
| 0 | `$20` | `00 00 00` | `00 00 03` |
| 1 | `$21` | `2A 80 8C` | `00 70 21` |
| 2 | `$22` | `F8 0A A8` | `01 00 00` |
| 3 | `$23` | `E4 A0 00` | `20 00 00` |
| 4 | `$24` | `00 00 01` | `00 00 00` |
| 5 | `$25` | `EA AC FC` | `00 80 00` |
| 6 | `$26` | `F0 0C 80` | `06 51 07` |
| 7 | `$27` | `08 00 00` | `84 A1 BD` |

Every row matches direct original bytes at
`$8000 + pointer*64 + 48` and differs from the corresponding old pointer
`$10..$17`. The intermediate pointers `$18..$1F` contain that same old tail
at offset 48, so these data also distinguish the complete successor from
the intermediate. Sprite 0's zero latch is a distinguishing witness because
the old/intermediate bytes are `00 00 03`.

The official pinned VICE 3.10 PAL table places sprites 0–2's fetches late in
line 266 and sprites 3–7's fetches early in line 267. At raw cycle 11 all
eight triplets are complete. The audit copies and guards the relevant
fetch/counter/table source from the official archived release. The snapshot
reader is separately pinned to the audited schema.

The original sprite kernels `$3000..$3404` and all 24 relevant old,
intermediate and successor slots retain their released 63 pixel bytes at
both endpoints. VIC registers, CIA2 ports/configuration and prepared pointer
bytes are equal across the endpoints. **No store trace was collected**, so
this equality does not certify the absence of transient changes during all
730 clocks.

`$D01C=$E7` retains mixed multicolor and hires interpretation. Data-latch
acceptance makes no claim about composed pixels, borders, priority, visible
colors or the whole picture.

## Wire ownership, closure and reproduction

The audit reuses the frozen passive live-wire verifier in a fresh in-memory
case configuration. It leaves that verifier, its earlier receipts and both
observer helpers untouched. Exact input/sent/received ranges, serialized
commands, natural response ownership and same-stop register context are
checked from the new case's own raw streams and event history.

There is one process/monitor endpoint, one restore and one completed resume.
No interruption, timeout, retry or replacement session occurs in this case.
The owned VICE process is recorded as terminated, exit code −15, and reaped.
That recorded child exit is not the helper process's own exit status.

```sh
rtk proxy python3 research/dragonbond/native_tail.py
```

Receipt:
`build/research/dragonbond/native-tail-analysis/native-tail-evidence.json`.
It pins the raw captures, old owner/data receipts, original scene RAM,
observer/verifier sources and official VIC source archive.

The first passive checker run incorrectly treated live-event responses as
prompt-free legacy transcript rows. Its producer and actual rejected response
remain under `native-tail-analysis/rejected-prompt-guard/`. The corrected
guard removes only the already-validated trailing prompt before comparing
warp and speed text. No native input changed to resolve that checker error.

Last valid continuation is now `native-03/bank80-new-tail.vsf`, at `$12A9`,
clock 149,028,968, raster 267/11. Further work must verify its full restored
state before execution. Continuous DMA history, complete-picture pixels,
physical hardware, exact bus phases and whole-demo timing remain open.
