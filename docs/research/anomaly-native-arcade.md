# Anomaly Arcade: closed native checkpoint, provisional runtime investigation

This is the frozen native-03 inventory. The later
[native-04 audit](anomaly-native-upper.md) completes the first upper-job
chain/publication and three floor traces. Continue from its newer saved state.

The owner-closed `native-03` continuation reaches the original Arcade Scroller and records its first two floor-update calls plus one rejected upper-wall gate. The lifecycle audit passes **11 complete raw RAM/snapshot pairs, totaling 720,896 RAM bytes**, all same-stop CPU/clock/beam checks, and two PNG identities. The source owner's **20 bounded checks** also pass.

**The Arcade runtime witness remains incomplete.** No accepted upper job, completed upper-buffer publication, per-line `$D016` store trace or independently reconstructed field was captured. A passing closed-checkpoint receipt must not be read as a completed whole-effect or 50 Hz proof. The [runtime mechanism note](anomaly-runtime.md) keeps that distinction explicit; the earlier [boot/payload analysis](anomaly-binary.md) and [native boot batch](anomaly-native.md) remain frozen separately.

## One exact parent restore

The session began by restoring only `native-02/humanmade-entry.vsf`, SHA-256 **`6844cbfd8a36e3074cca7a06c16781cde49933494c36da21a85394b5691a1a98`**. The parent native receipt is pinned at **`25d9ef6cac9705f37999ab70af2b423dbdeff901e2192c1095a9e873272d9714`** before its references are used.

At `restored-humanmade`, every one of the **65,536 RAM bytes** equals the saved parent RAM, SHA-256 `2c23b905f69be4563102635c6b701ae6d650747eb7dc743dd43a48b1dba7a86c`. The complete `MAINCPU` snapshot payload is equal too. Recorded registers, CPU-port bytes and beam position equal the parent's `$2D00`, clock **37,568,580**, raster **94**, raw cycle **42**. This is an explicit snapshot continuation, not a second cold boot or a direct jump into Arcade.

The mounted original side-one D64 still hashes to `d452497845598cca8936fdf57c60fdc9c70cd7e64110e049fa6fc7d735f940cd`. No disk, code, PC or effect-state bytes were patched. The session metadata records start **7 November 2026, 14:32:40 UTC**, and owner closure **14:49:48 UTC**, with VICE cleanup exit `-15`. That closes the observation batch; it is not a natural demo-exit claim. This checker performs no process control or liveness probe.

## Warp transit is recorded, not hidden

The owner enabled warp only to traverse the intervening original demo scenes. Before this transit, `resourceget "Speed"` returned **100**, `resourceget "SoundEmulateOnWarp"` returned **1**, and `warp` reported off. The transcript then records `warp on`, confirms on, and resumes once to a guarded original loader call at **`$08AE`**.

At that stop, warp is explicitly turned **off** and queried as off **before** `arcade-load-call` is captured, clock **160,083,859**. Every subsequent resume in this batch occurs with warp off. No `resourceset` or `Speed` change is recorded. The transit is a deliberate observation intervention; its wall-clock behavior is not used as performance evidence, and dummy SID output supplies no audio-quality proof.

Two earlier read-only attempts to query warp are preserved:

- `resourceget "WarpMode"` returned an unknown-resource error.
- `resourceget WarpMode` returned a syntax error.

The subsequent `help` and `warp` commands resolve the query interface. Neither failed query is relabelled as a successful resource read, a missing capture or a data write. All **95 monitor commands**, their response text and line numbers are retained in the receipt. The audit allows the one parent restore, read-only queries/help, the explicit warp controls, execution breakpoints/conditions, the four job traces, resume and capture commands. It rejects unclassified operations. No synthetic input, direct RAM/code write, register/PC write or additional restore belongs to this transcript. This is a recorded-command audit, not an external audit of all host activity.

## Actual accepted capture inventory

| Stem | PC | Clock | Raw raster / cycle |
| --- | --- | ---: | ---: |
| `restored-humanmade` | `$2D00` | 37,568,580 | 94 / 42 |
| `arcade-load-call` | `$08AE` | 160,083,859 | 85 / 40 |
| `arcade-load-return` | `$08B1` | 163,832,261 | 304 / 5 |
| `arcade-entry` | `$3B00` | 164,459,398 | 274 / 40 |
| `arcade-ready` | `$3B88` | 164,560,071 | 0 / 39 |
| `floor-a-pre` | `$3D83` | 164,577,100 | 270 / 58 |
| `floor-a-post` | `$3D86` | 164,578,689 | 296 / 9 |
| `floor-b-pre` | `$3D83` | 164,596,893 | 273 / 6 |
| `floor-b-post` | `$3D86` | 164,602,100 | 43 / 47 |
| `upper-gate-rejected` | `$36E6` | 164,602,110 | 43 / 57 |
| `upper-rejected-post` | `$3D89` | 164,602,120 | 44 / 4 |

The conditional `$08AE` breakpoint reads original driver bytes to distinguish this late call from unrelated uses of the same low-memory address. It does not change those bytes. The loaded sections are independently bound to the production Link artifact in the source/runtime proof; `$2800` is a transfer/table address, while the natural execution entry is `$3B00`.

Every RAM save must be a full `bank ram` capture paired with the identically named snapshot at the exact recorded stop. All physical RAM bytes are compared without exclusions. The snapshot's CPU fields and VIC line/cycle must equal the monitor register query. The checker requires exactly the final 11 known RAM files and snapshots, with monotonically increasing capture clocks. PNGs exist only at `arcade-ready` and `upper-rejected-post`; they are decoded, hashed and tied to those snapshots as output observations. Neither is treated as a complete-field pixel oracle.

## What the source/runtime join adds

The frozen source-owner result is `runtime-analysis/runtime-proof.json`, SHA-256 **`17ed1c6adafb0b33f0a0ca0b9830bfcfa5ff913818a8ad4bd18bcd5c53f7b2fb`**. Its checker is `inspect_arcade.py`, SHA-256 `c016696ab829fec52b9b10830af2b8111806cc629f734d40b3c7cbc5a392b978`. This passive audit pins both, checks all exposed artifact hashes and joins **all 11 capture identities**. It propagates the source result's `runtime_witness_complete=false`, provisional status and unobserved cases.

Its exact domains include the **41,523 original production payload bytes** at both loader return and entry, the incoming driver's retained bytes and two specifically predicted self-modifications, and initialized helper placement. The helper copy is **3,328 bytes**, including **2,820 file-defined bytes plus 508 captured native-prestate bytes**. Those extra bytes are not renamed generated helper code or invented zero padding.

The two floor witnesses agree with the source owner's conditional integer/address model in its stated RAM domains. The first has **zero coarse shifts**, the second **eight**, implying **320 bitmap stores** in that second call. Their observed call intervals are **1,589** and **5,207 clocks**. These are two particular call intervals with different work, not a maximum renderer budget, complete-frame cadence or display-rate measurement. No CPU or VIC model is executed by this lifecycle checker.

The explicit rejected-gate witness has sampled `$D012` low byte **`$2B`**, threshold **`$24`**, and a nonnegative subtraction result. The signed `BMI` acceptance branch is not taken. The natural return takes **10 clocks**, preserves all **65,536 RAM bytes**, and leaves upper status 1 and its dispatch unchanged. This is one observed rejection, not coverage of every accepted path or of the entire 256-value low-byte predicate.

## Trace boundaries and the unfinished cases

Four execution tracepoints were installed while paused at `arcade-ready`: **`$36F3,$38BB,$39B1,$39CA`**. They remain bounded here to clocks **164,560,071 through 164,602,120**. There are **zero recorded job-entry trace hits** in that interval. Installing a tracepoint is not evidence that a job executed, and the lack of hits is not extended to the earlier warp transit or later unobserved execution.

No `$D016` store trace was collected before the owner closed this batch. Future store-watch timestamps must retain the [VICE observer timing limits](vice-trace-timing.md): a reported monitor clock and owner PC are not automatically the physical bus-write phase, and queued observations need their own controls. This batch supplies no per-line bus-phase claim.

The final preserved continuation state is `upper-rejected-post.vsf`, **PC `$3D89`, clock 164,602,120, raster 44/raw cycle 4**. Upper status is 1, row index 0, dispatch `$36F3`; buffer selection is 0, upper fine-scroll value `$C7` and fine delay 14. A follow-up should preserve this state and its lineage, then:

1. Capture a naturally accepted upper gate and one completed row/new-column job, with exact pre/post RAM and source-derived writes.
2. Observe the full 28-job update and the first publication, checking completion independently of the source's unconditional periodic swap.
3. Capture the 96 per-line `$D016` writes in the source-derived `$B400→$B828` interval, with timing and observer controls.
4. Only then extend to consecutive complete fields, image reconstruction and a genuine render/cadence budget.

These are pending witnesses. No register, PC or data patch is proposed to manufacture them, and no further native work was performed in this bounded batch.

Reproduce the passive audit with:

```sh
rtk proxy python3 research/anomaly/native_arcade.py
```

[The checker](../../research/anomaly/native_arcade.py) writes `build/research/anomaly/native-arcade-analysis/native-arcade-evidence.json`, with the full restore comparison, command/warp/query audit, trace window, capture and PNG hashes, parent/source pins and explicit runtime gaps. A byte-identical checked script is archived alongside it. The lifecycle result is complete for this closed inventory; the Arcade investigation remains provisional.
