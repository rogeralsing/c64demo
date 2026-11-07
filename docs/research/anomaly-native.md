# We Are The Anomaly: original-disk native boot evidence

The owner-closed `native-02` batch follows **normal autostart of the original side-one D64**, through the Sparkle resident installation, early bundles, a completed fade call and the natural HumanMade entry at `$2D00`. All **eight raw RAM/snapshot pairs, totaling 524,288 RAM bytes**, agree exactly. The recorded CPU registers, clock and VIC beam position also agree with every snapshot. Five PNGs are bound to their matching stops as output observations.

This closes a bounded early-boot capture task. It is not a native Arcade Scroller run, a full-demo timing result or a reconstruction of each displayed pixel. The separate [original boot and payload analysis](anomaly-binary.md) owns the Sparkle source binding and offline disk decoder; the [Arcade source analysis](anomaly-arcade.md) owns its floor/upper-wall mechanisms.

The mounted disk is the 174,848-byte `WeAreTheAnomaly-Side1.d64`, SHA-256 **`d452497845598cca8936fdf57c60fdc9c70cd7e64110e049fa6fc7d735f940cd`**, already extracted from the [author's release ZIP](https://www.elder0010.com/uploads/we_are_the_anomaly/we_are_the_anomaly_gp_ext.zip). The capture metadata records `/opt/homebrew/bin/x64sc`, PAL, speed 100, warp disabled and dummy SID output, with normal `-autostart` and true-drive configuration. This is the particular recorded VICE setup, not an assertion about other VIC revisions or physical machines.

The session began **7 November 2026 at 14:01:30 UTC** and was owner-closed at **14:17:56 UTC**. Its controlling helper exited normally; VICE's cleanup exit code was `-15`. Closure is a capture-lifecycle event, not a claim that the demo naturally exited. The passive checker starts no processes and makes no process-liveness inference of its own.

## Accepted stops

| Capture stem | PC | Clock | Raw raster / cycle |
| --- | --- | ---: | ---: |
| `boot-entry` | `$0810` | 6,884,680 | 80 / 40 |
| `resident-copied` | `$08B5` | 6,958,800 | 9 / 9 |
| `first-return` | `$FF40` | 8,685,093 | 266 / 39 |
| `entry-fade-return` | `$FF40` | 8,691,402 | 54 / 48 |
| `base-music-return` | `$FF54` | 8,983,055 | 4 / 11 |
| `fade-assets-return` | `$FF63` | 11,120,728 | 239 / 31 |
| `fade-call-return` | `$FF66` | 33,258,015 | 1 / 0 |
| `humanmade-entry` | `$2D00` | 37,568,580 | 94 / 42 |

The two `$FF40` captures are different original program states: the first installed bundle contains CIA detection, and the second replaces that area with the entry/fade driver. The checker pairs files by their explicit capture stems and stop records, rather than assuming a PC identifies one unique state.

`fade-assets-return` is before the original call to `$8500`; `fade-call-return` is after it. Their **22,137,287-clock interval** is the measured duration of that complete call, including the original program's waits and work. It is not labelled a preparation-only interval, one-frame render or frame-rate measurement. `$2D00` is the natural HumanMade execution entry; the batch stops before running or validating that effect's renderer.

For each stem, the checker requires a complete 65,536-byte `ram-*.bin` save from `bank ram` and its same-stop `.vsf`. It compares every physical RAM byte through the pinned snapshot reader, without masks or exclusions. The `MAINCPU` register/clock fields and VIC raster line/cycle must equal the preceding monitor register query. Exactly the eight expected RAM files, eight snapshots and five PNGs must be present. A missing, extra or rejected observation cannot silently be omitted.

The PNGs are at `first-return`, `entry-fade-return`, `fade-assets-return`, `fade-call-return` and `humanmade-entry`. Each is decoded and hashed, and its stop must agree with its snapshot. No late register read is used to explain the whole image, and no snapshot is treated as an independent visual oracle.

## Interventions and the separate setup attempt

The complete `native-02` monitor transcript contains **61 commands**: register reads, `sidefx off`, breakpoints and deletion, resume, `bank ram`, full-RAM saves, snapshots and screenshots. The checker admits only these observer operations. It records **zero synthetic inputs, snapshot restores, direct RAM/code writes, register/PC writes, resource/speed changes or rejected timeout observations**. This is a transcript audit, not a claim to have audited every host activity or tested keyboard hardware.

The preceding `native-01` attempt is kept separate. Its metadata is terminal and records VICE cleanup `-15`; the owner reports that the helper closed when stdin closed. Its transcript contains only `r` and `sidefx off`, while the observed CPU was at `$FD75`. It has **no saved RAM, VSF, PNG or recorded monitor execution resume**. Those facts make it setup-only evidence, not another successful boot or original-program execution proof. No native-01 state is supplied to native-02.

## Independent payload and source binding

The lifecycle receipt pins the source owner's final results before using them:

- `binary-analysis/side1-binary-proof.json`: **`b8744b0184128330a069a7366c4f843193306074f4a55a03d10f092a6fa8800c`**.
- `binary-analysis/native-payload-comparisons.json`: **`a6d48ec5123ca1ee9f621dfc52de8317a75e362feb0d8019384e6da21ec504e5`**.

Every source/helper/decoded-RAM/known-mask artifact exposed by those receipts is hash-checked. All eight source-capture RAM/snapshot identities are then joined to this checker's independently parsed records. Each of the **15 exact native comparison domains** is rebound to the actual saved RAM range and its SHA-256.

Those domains establish all **832 DOS-loaded boot bytes**, the initial resident relationship, and the loaded ranges of bundles **0 through 4**. The resident distinction matters: **412 bytes** are checked against the original PRG; its remaining **four bytes** are compared with the actual source tail at the **same post-copy native stop**. They are not supplied as file bytes, synthesized zero padding or a continuous CPU copy proof. The full 416-byte relationship and the 412-byte file-defined comparison are labelled separately. Later self-modifying loader state is not assumed pristine.

The source owner's decoder separately recovers **39 real bundles**, each starting with wholly unknown RAM and accepting only bytes established inside that bundle. Its final directory entry is explicitly a terminal reset/side-continuation dummy, not a fabricated fortieth payload. Bundle 36 matches all **41,523 loaded Arcade bytes** in the production Link artifact. This is useful original-disk/artifact evidence, but **native-02's payload checks cover only bundles 0 through 4**; the decoder result is not presented as native Arcade execution or a fresh assembly of the published source.

Peer review found that the source receipt initially reported the wrong embedded-loader array offset because a later loop reused its variable. The source owner preserved the old source and both receipts, corrected the field from `$B802` to **`$11B520`**, and gated the corrected output. The embedded-byte assertion and every decoded/native byte result were unchanged. The earlier passive receipt/script and a mapping to those archived dependencies remain under `native-analysis/before-boot-offset-correction/`; the current receipt uses only the corrected pins above.

The strict original-CPU source check ends before the first KERNAL call at `$081C`. Nothing here supplies invented ROM, IEC, CIA, drive or interrupt responses to extend it. The native checkpoints bridge actual execution observations to independently decoded data; they do not constitute a continuous loader CPU/hardware model, whole-machine equality, sound proof or runtime frame budget.

Reproduce the passive gate with:

```sh
rtk proxy python3 research/anomaly/native_capture.py
```

[The checker](../../research/anomaly/native_capture.py) writes `build/research/anomaly/native-analysis/native-evidence.json`, with session/transcript hashes, the setup-only classification, all commands, full RAM comparisons, CPU/beam stops, PNG hashes and pinned source domains. Its current source hash is recorded in the receipt, and a byte-identical checked script is archived beside it. No original capture, prior proof or production file is changed by this check.
