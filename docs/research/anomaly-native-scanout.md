# Anomaly: closed native-05 fetch and scanout observations

On 8 November 2026, one owned PAL VICE session resumed the exact final
`native-04` checkpoint and captured five complete RAM/snapshot pairs plus
one PNG. The [passive owner audit](../../research/anomaly/native_scanout.py)
checks **327,680 RAM bytes**, every pair's CPU/beam context, the full restore
identity and all **96 original-source-matched `$D016` observations**.
The separate [scanout model](anomaly-scanout.md) interprets the saved pixels
and fetch latches. Capture integrity and pixel reconstruction remain distinct.

## Original state and execution

The sole restore is `native-04/field-04-pre.vsf`, SHA-256
`70fbfcde49a6c1b9a1b18ad538d7e0684cc1c7fdaf2ec6a42b40ad734bbf1b5b`.
Its complete `C64MEM` and `MAINCPU` payloads match the restored snapshot,
including all 65,536 physical RAM bytes. Recorded registers, ports `$2F/$35`,
clock 167,006,965 and beam 152/13 also match. The attached original side-one
disk remains SHA-256
`d452497845598cca8936fdf57c60fdc9c70cd7e64110e049fa6fc7d735f940cd`.

There is one restore and four natural execution resumes, each immediately
preceded by observed warp-off and Speed=100 queries. Breakpoints and traces
observe the original flow. No data, code or PC is written; no substitute
part, keyboard input or synthetic hardware response is supplied.

| Capture stem | Actual PC | Clock | Raster / raw cycle |
|---|---:|---:|---:|
| `restored-arcade` | B400 | 167006965 | 152 / 13 |
| `first-row-fetched` | B47B | 167007200 | 155 / 59 |
| `floor-strip-complete` | B54A | 167008643 | 178 / 53 |
| `floor-strip-drawn` | B54D | 167008649 | 178 / 59 |
| `field-post` | B828 | 167013183 | 250 / 57 |

The `floor-strip-complete` filename preserves an initially premature
assumption. At cycle 53, the final graphics fetches have not finished.
The next capture follows naturally six clocks later; physical RAM is
identical, while the VIC's output/fetch state advances. The first name is
not evidence that every pixel of line 178 was already drawn.

An initial restore summary also incorrectly read physical RAM offsets 0/1
as CPU ports. That summary is retained as
`native-05/rejected-physical-ram-as-ports.json`. The corrected restore check
uses the `C64MEM` header and monitor port values; RAM beneath those special
registers is a separate domain.

## Register history and fetched data

The complete recorded ranges are `$D000..$D02E`, `$DD00..$DD03` and
`$63F8..$63FF`. All trace events are retained in the receipt, including
sprite registers/pointers and the RMW IRQ stores. The audit does not turn
one RMW event into a claimed dummy/final bus-write chronology.

All 96 floor scroll observations have the expected PC, index and actual
prestate table value, on consecutive raster lines 155 through 250.
`$DD02=$3D` is observed once at `$B468`; `$D018=$80` is observed **three**
times at `$B472`, because the first eight-line block repeats three times.
Monitor timestamps remain observer coordinates, not certified bus phases.

The saved VIC state supplies stronger evidence than those timestamps:

- At 155/59, all 40 VBUF bytes equal `$6208..$622F`, and all 40 CBUF bytes
  equal the corresponding actual Color RAM entries. VCBASE=520, VC=560
  and VMLI=40 bind the first floor matrix row to the real fetch latches.
- At 178/53, VC=639 and VMLI=39 follow the fetch using counter 638 and
  row counter 7. The calculated bitmap address is `$53F7`; its actual
  nonzero byte `$07` matches both GBUF and draw-pipeline slot 0.
- At 178/59, the independent model checks the committed preceding 23
  rows and the 304 active pixels of the current line's separate DBUF.
  The later `field-post` retains the complete 24-row strip.

Together with the three earlier native-04 fields, the independent model
matches **four strips of 24×384 pixels: 36,864 palette indices**, including
their borders. Sprites start below this checked strip. This is not a full
96-row sprite compositor, upper-wall scanout, universal deadline or whole
demo frame-rate proof.

## Reproduce and continue

```sh
rtk proxy python3 research/anomaly/native_scanout.py
rtk proxy python3 research/anomaly/scanout.py
```

The owner receipt is
`build/research/anomaly/native-scanout-analysis/native-scanout-evidence.json`.
The independent result is
`build/research/anomaly/scanout-analysis/scanout-proof.json`.
Both commands read saved evidence and run no emulator.

The session closed at 08:26:59 UTC on 8 November; VICE cleanup returned
−15. This records owner cleanup, not a natural demo exit. Its exact final
continuation is `native-05/field-post.vsf`, SHA-256
`2185b4f932c49c900223c9e5c3598fc66c6fd8b1e04704158699659aa574b28a`.
Resume that original `$B828` state only after revalidating RAM, CPU, ports
and beam. Next extend the sprite/composition model below line 178 using
the retained pointer/register history, then broaden workload and timing
coverage. Old native-04 evidence and rejected hypotheses remain frozen.
