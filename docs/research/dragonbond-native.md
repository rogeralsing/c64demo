# Dragonbond: original native lineage and active sprite handover

The original disk reaches scene index `$41` through its own bootstrap, drive
loader and dispatcher. Saved native DMA data then binds prepared intermediate
sprite bytes to actual fetches in VIC banks `$4000` and `$8000`.
The [original-byte investigation](dragonbond.md) owns the instruction/data
interpretation. The passive [native owner audit](../../research/dragonbond/native_capture.py)
separately checks capture context, permitted monitor operations and closure.

## Original boot and scene identity

The unchanged disk is 174,848 bytes, SHA-256
`37854b4e3426349ee03bc759f5bed8ad9a6c7f0404a469f1ae5163918cf50300`.
`native-01` uses normal disk autostart, without synthetic SYS/PC entry or a
replacement payload. Natural checkpoints retain the original `$081E` entry,
relocated `$0020` depacker, `$2000` startup, `$06BB` load request, `$0400`
dispatcher and subsequent `$2800` scene entries.

Actual loader trace values are `$3E,$3F,$42,$40,$41`, in that order. The first
request has A=0 in its own `$06BB` capture. Those observations identify loaded
scenes independently of output filenames. The file named `scene-42-entry`
was actually captured at `$2832` in the previous scene after `delete 3` failed.
It remains preserved and rejected. `scene-42-entry-valid` is the actual next
`$2800` stop following A=`$42`. Likewise, `intro-entry` at `$0400` is common
dispatcher code, rather than proof of a particular artwork.

Fifteen RAM/snapshot pairs retain every physical C64 RAM byte and matching
register/port/beam context. A separate 2,048-byte drive dump at the first load
binds uploaded code to the original bootstrap. The original-byte producer checks
the unpacked 4,133-byte image, installed 423-byte resident receiver and exact
drive self-modification/stack differences.

Ten completed resumes are unwarped. Five explicitly warped intervals navigate
the earlier text/logo scenes; they supply no real-time performance claim.
The helper closed `native-01` normally, recording exit code −15.

## Unwarped handover continuation

Parent: `native-01/scene-41-entry.vsf`, SHA-256
`96f34d4beaec41de6f997aac42f8dcbc5e758fe3564c11c6c323c6a954bc1a3e`.
`native-02` starts with the same disk and no autostart, restoring that state once.
Complete **C64MEM, MAINCPU, CIA1, CIA2 and VIC-II module payloads** match before
execution. All eleven completed resumes are preceded by observed warp-off and
Speed=100. No code/data/PC replacement occurs.

| Capture | PC | Clock | Raster / raw cycle |
|---|---:|---:|---:|
| Restored scene `$41` | `$2800` | 139,667,377 | 182 / 31 |
| Original wait ready | `$2808` | 139,667,473 | 184 / 1 |
| First picture IRQ | `$28F6` | 148,997,405 | 78 / 11 |
| Before pointer `$35` | `$3239` | 149,001,185 | 138 / 11 |
| After all `$35..$3C` pointers | `$3258` | 149,001,250 | 139 / 13 |
| Before pointer `$3D` | `$3239` | 149,001,780 | 147 / 39 |
| After all `$3D..$44` pointers | `$3258` | 149,001,844 | 148 / 40 |
| Before next intermediate | `$3239` | 149,002,445 | 158 / 11 |
| Next picture IRQ | `$28F6` | 149,017,061 | 78 / 11 |
| Bank `$8000`, after `$18..$1F` | `$3278` | 149,027,395 | 242 / 13 |
| Bank `$8000`, before `$20` | `$3259` | 149,028,173 | 254 / 35 |
| Bank `$8000`, after `$20..$27` | `$3278` | 149,028,238 | 255 / 37 |

The two `$28F6` observations differ by exactly 19,656 clocks. This is one
observed field interval, not a complete production timing or workload proof.

Store traces cover VIC registers, CIA2 selection, and both pointer tables.
Saved sprite data/counters distinguish reading the old tail through the
intermediate from reading its successor head after the Y restart. The actual
released split is **33 new bytes and 30 old bytes**, matching all eight slots in
each checked group. The author's simplified PDF example uses the opposite
30/33 split; the [data and DMA note](dragonbond.md) preserves that difference.
Bank `$8000` changes sprite-0 multicolor mode between saved samples, so its
data-fetch acceptance does not imply unchanged pixel interpretation.

## Closure and retained failed observation

An optional extra breakpoint, `break 2808 if RL == $10b`, did not return a
monitor prompt. An intact main loop does not guarantee that CPU visits it on
line 267: the music call follows the bottom IRQ. The exact reason for this
missed condition was not established by an instruction trace. No final-tail
RAM/snapshot files were created, and that optional observation is excluded.

The owned process was confirmed live while waiting. Ctrl-C ended its RTK/Python
wrapper before the helper's cleanup ran, leaving the exact VICE PID orphaned.
The owner then checked that PID's command and unique monitor port, sent SIGTERM
to that process only, and verified its absence. `owner-cleanup.json` records this
separate closure. Original `session.json` remains untouched; no helper exit code,
final machine state or completed optional capture is invented. There was no
restart to replace the failed observation.

The audit therefore distinguishes **26 completed resumes** across both sessions
from one uncompleted optional attempt. It checks **27 RAM/snapshot pairs,
1,769,472 physical RAM bytes**, plus drive/context and trace identities. The
single PNG is an initial-transition observation, not complete-picture proof.

## Reproduction and continuation

```sh
rtk proxy python3 research/dragonbond/native_capture.py
rtk proxy build/research/tower-power/cpu-venv/bin/python research/dragonbond/inspect_original.py --handover build/research/dragonbond/native-02
```

The original-byte checker needs py65; the retained CPU environment supplies it.
The owner audit uses the ordinary Python environment and does not execute a CPU.

Owner receipt: `build/research/dragonbond/native-analysis/native-evidence.json`.
Native inputs: `build/research/dragonbond/native-01/` and `native-02/`.
Original byte/DMA receipts: `build/research/dragonbond/original-analysis/`.

The last valid continuation is `native-02/bank80-after-full-new.vsf`, at `$3278`,
clock 149,028,238, raster 255/37. A later continuation must verify full restored
state before execution. Before another potentially unbounded observation, add
a cancellable monitor reader. For the optional full-new-tail witness, use an
any-original-instruction raster checkpoint, rather than requiring main-loop
execution during a possibly active music IRQ. Keep the missed condition and
external cleanup explicit when extending this lineage.

Complete-picture pixels, all sprite multiplexing regions, later animation
states, physical hardware, exact bus-write phases and whole-demo timing remain
open. No loader-family attribution is inferred from this bounded execution.
