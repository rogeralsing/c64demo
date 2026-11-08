# Anomaly: completing the saved floor line in five original clocks

The closed `native-06` continuation supplies the final 32 pixels excluded from
the earlier lower-floor proof. The independent [sprite compositor](anomaly-sprites.md)
now checks all **96×384 floor pixels**, rows 155–250, with zero differences.
The [native owner audit](../../research/anomaly/native_tail.py) verifies this
capture's execution and provenance separately from its pixel interpretation.

## Exact continuation

Parent: `build/research/anomaly/native-05/field-post.vsf`, SHA-256
`2185b4f932c49c900223c9e5c3598fc66c6fd8b1e04704158699659aa574b28a`.
Its closed owner receipt is retained in [native-05](anomaly-native-scanout.md).
The original side-one disk remains SHA-256
`d452497845598cca8936fdf57c60fdc9c70cd7e64110e049fa6fc7d735f940cd`.

A new owned PAL VICE 3.10 process starts without autostart and restores that
parent once. Before execution, every C64MEM and MAINCPU byte matches; decoded
ports, CPU state and beam agree. Two full RAM/snapshot pairs are saved:

| Capture | Original PC | Observer clock | Raster / raw cycle | DBUF offset |
|---|---:|---:|---:|---:|
| `restored-floor-post` | `$B828` | 167,013,183 | 250 / 57 | 456 |
| `floor-line-drawn` | `$B82A` | 167,013,188 | 250 / 62 | 496 |

Only original instruction `E6 D9`, `INC $D9`, executes. RAM changes solely at
`$D9`, from 3 to 4. A/X/Y/SP stay equal; PC, clock and the INC N/Z flags
match the instruction. All other C64MEM bytes, including CPU port state,
remain equal. This is a final-memory comparison, not enumeration of both
RMW bus writes.

VIC configuration and CIA ports/configuration do not change. CIA2 timer B
advances from 60 to 55, and both relative TOD alarm counters decrease by five.
The initial assumption of complete CIA equality was rejected and its producer
and observations are archived. Timers advance while configuration stays fixed.

The source-defined visible DBUF interval is `[104,488)`. Offset 456 covered
352 pixels; offset 496 covers all 384. The separate compositor checks all 95
previously committed floor rows remain unchanged and uses this completed DBUF
for the final row. It retains the earlier source/bitmap/sprite oracle and all
negative controls.

## Ownership, reproduction and limits

The transcript admits one restore, one resume, read-only inspection and capture,
and a breakpoint at original `$B82A`. Warp is off and Speed=100 before the
resume. There are no code or PC patches. The helper closes its own VICE process;
metadata records closure and exit code −15. Two pairs contain 131,072 checked
RAM bytes. No screenshot is needed for this final-line acceptance.

```sh
rtk proxy python3 research/anomaly/native_tail.py
rtk proxy python3 research/anomaly/sprite_scanout.py
```

Owner receipt:
`build/research/anomaly/native-tail-analysis/native-tail-evidence.json`.
Native inputs and transcript:
`build/research/anomaly/native-06/`.
The updated sprite proof preserves the frozen native-05-only producer and its
20 evidence files before extending the claim.

This closes one complete floor field. It does not establish upper-wall scanout,
all later game states, maximum workload, physical VIC variants or whole-demo
frame rate. The exact retained continuation is now `native-06/floor-line-drawn.vsf`
at `$B82A`, before the next original `LDA $D9`.
