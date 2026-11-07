# Freespin: released loader and raster evidence

Freespin moves the display and sound workload onto the 1541 itself. The [frontier overview](frontier-demos.md) covers the release and author claims; this note adds pinned source snapshots, reconstruction of the released disk's first seventeen parts, original-CPU decoder checks, and a measured raster fragment. No VICE or other system-emulator process was started for this lane.

Primary material is Quiss/Matthias Kramm's [release page](https://www.quiss.org/freespin/), [video article](https://www.quiss.org/freespin/raster.html), [music article](https://www.quiss.org/freespin/music.html), [loader explanation](https://www.quiss.org/freespin/loading.html), and [published loader assembly](https://www.quiss.org/freespin/loader.html). The inspected author links expose that loader and selected effect/music fragments, rather than a full effect-source Git revision. Here the reproducible revision pins are exact content hashes.

## What reaches the monitor and the motor

The author connects the serial outputs to a monitor through a resistor network. DATA/CLK output combinations provide sync, black and white levels; there is no VIC, SID, or independent video controller. At the drive's nominal 1 MHz, four-cycle port stores constrain adjacent graphics transitions to at least 32 of the article's nominal horizontal dots. Its 412×256 layout therefore does not mean 412 arbitrary independent pixels per row. The author describes timing-sensitive visible code and offscreen computation with frequent waveform copies; the 1084 monitor tolerates missing horizontal syncs in those offscreen intervals. [Video mechanism and constraints](https://www.quiss.org/freespin/raster.html)

Both 6522 Timer1s can generate PB7 waveforms. Software samples them and drives the stepper control; combining two timer waves with OR changes the mechanical timbre. The published optimized path combines waveform sampling and sync generation using RRA, with strict carry/output-state preconditions. Those timer resources consequently serve music rather than general frame timing. The released code's loader transfers frame phase between Timer2 and Timer1 while switching operating modes. [Shared video/audio code](https://www.quiss.org/freespin/raster.html), [released loader source](https://www.quiss.org/freespin/loader.html)

This is one mechanical sound output, rather than two independent sound-chip voices. The author reports no ordinary volume envelope, note changes at frame granularity, and timbre/loudness dependent on drive mechanics. The combined instrument uses waves at f and 1.5f. “Silence” uses a roughly 15 kHz note to keep the head from settling and clicking; loading still interrupts audio. These are reported hardware observations, not acoustics measured here. [Music design](https://www.quiss.org/freespin/music.html)

## Exact artifact and source pins

The author D64 fetched on 7 November 2026 is 174,848 bytes, SHA-256:

```text
7798f74046ee767a2e05e4e05c12e7b7453640c579ebc3d5daed20ce019f890c
```

It matches the earlier overview's download. The conventional directory contains a 3,774-byte `$0801` bootstrap PRG, stored in fifteen sectors on track 35. The separate released drive loader occupies the 254-byte payload at track 18 / sector 18, beginning at RAM `$0702`; its SHA-256 is `ba4576cb9337496375f3263a55b5a89fb392bb1ab1a7390256464a0da7ec4452`.

`build/research/freespin/downloads.json` pins all six author pages and the disk. The extracted published assembly has SHA-256 `df345e8812d48209daf33956d92e7e1cf1e590023c31d2280c3c117ca9465ec0`; `assembly.json` pins the Kick Assembler JAR and output. Third-party bytes remain in ignored research artifacts.

## The published source and released loader differ

The published source requires an external `FRAME_CYCLES` parameter. Supplying the **release-derived value 20,000** and assembling the unmodified text with Kick Assembler 5.25 produces 244 code bytes at `$0702..$07F5`.

Comparison with the release is exact except for one inserted sequence:

| Portion | Result |
|---|---|
| `$0702..$07C0` | Published assembly and release match exactly |
| Release `$07C1..$07C7` | Additional seven-byte subtract/branch/decrement delay |
| Remaining published code | Matches after accounting for that insertion |
| Released tail | Three padding bytes |

Thus the released resident allocation is 254 bytes, containing 251 bytes before padding. It is not correct to treat the published listing alone as the complete released timing schedule.

The timer reload immediates are `$4E1E = 19,998`, used for `FRAME_CYCLES−2`: a nominal 20,000-cycle frame. This differs from C64 PAL's CPU budget and from simply multiplying 312 by a 64-cycle line. Visible line timing and the offscreen timer schedule are separate jobs.

There is also a small comment discrepancy worth preserving. The fixed delay at `$07B4..$07BD` takes **6,431 CPU cycles**, including sixteen LDY instructions. Its source comment says 6,399; the missing 32 cycles are exactly those loads. This check excludes the preceding LDX, motor store, extra released delay and hardware-dependent timer polling. It does not establish the full loading duration.

## Recovering the custom disk payload

The disk remains writable as an ordinary D64, while the meaning of its sector bytes is custom. The author describes using expensive offline constraint solving to make a small add/XOR decoder recover the desired payload from standard GCR data, deliberately carrying ADC's carry between operations. This exchanges disk capacity and encoder work for a tiny resident decoder. The stated loading contract is seven blank frames per transition. [Encoding design](https://www.quiss.org/freespin/loading.html)

Our offline reconstruction first re-encodes each standard sector body into its GCR byte stream. Seven initial raw bytes identify the block and its destination using XOR pairs. Then 312 raw GCR bytes yield 208 output bytes through the released constants `(80,133,102,68)` and the original carry chain.

Tracks 1..17 each contain nine unique chunks, with byte-identical redundant sector copies. The destination bases are:

```text
$0010, $00E0, $01B0, $0280, $0350, $0420, $04F0, $05C0, $0690
```

Consequently each part writes **1,872 bytes at `$0010..$075F`**. This includes its entry vector at `$0700/$0701` and the first 94 bytes of the next loader. That prefix has already executed before the active decode loop at `$0779`; reloading it is safe. Across all seventeen reconstructed parts, the prefix matches the released loader except for the next motor-control immediate at `$0703`.

The remaining loader tail stays resident. The refreshed memory genuinely includes code in zero page and stack space: reconstructed entry vectors include `$0073`, `$0124`, and `$0023`. Flat memory images have known-byte masks; `$0000..$000F` placeholders must not be interpreted as proven startup state.

Tracks 19..34 also contain custom-looking headers. Track 19 is coherent under the same default decoder state; track 20 fails the expected next-loader-prefix check. Those secondary tracks are not promoted to validated effect code. Their role or alternate decoder state remains unidentified.

As a separate finite encoding check, enumerating every standard GCR nibble quadruple yields 8,192 distinct first-sixteen-bit windows whose byte XOR covers all 256 output values. This full-set count differs from the article's illustrative 3,072 count; the checked surjectivity result holds, with 14..71 windows per output. The released 3:2 decoder validation below does not depend on that illustrative count.

## Independent original-decoder execution

The [CPU validator](../../research/freespin/validate_decoder.py) executes the released `$0779..$07A3` payload decoder unchanged in py65 1.2.0. The harness supplies the next `$1C01` data byte and byte-ready V events. Original ADC/EOR carry flow, output pointer writes and INC delay instructions all execute normally.

All **153 unique blocks**, representing **357 byte-identical sector copies**, pass. Their **31,824 chronological output writes** match the offline decoder. The check performs 47,736 raw GCR reads during 350,064 original instructions. It also proves that reloading the prefix never changes the currently executing decoder range.

`cpu-validation.json` records those comparisons. The supplied byte-ready events do not reproduce rotational position, VIA timing, physical GCR sync, or analog video. The author's seven-frame contract is consistent with the released 50 Hz timer parameter, but this mocked-input proof does not independently establish that loading deadline.

## A real released 64-cycle raster fragment

Track 2's part has an explicit caller at `$01D6` that sets Y = 4 and calls `$0200`. The loop at `$0200..$022D` samples the first port's PB7 through ASL, carries it into the motor-control value, then alternates port stores for graphics.

The [raster-fragment validator](../../research/freespin/validate_raster_line.py) runs those original official instructions for both waveform bits, both incoming carry values, and continuing/final loop paths:

| Observable instruction event | Nominal CPU cycle |
|---|---:|
| ASL `$1800` completes | 8 |
| Store to motor port `$1C00` | 15 |
| Alternating graphic stores to `$1800` | 19, 23, 27, …, 59 |
| Continuing iteration ends | 64 |

The final iteration takes 63 cycles; the following fragment begins with a three-cycle zero-page load instead of the two-cycle immediate load. The next ASL completion remains exactly **64 cycles** after the previous one. This is concrete evidence of instruction scheduling across a fragment boundary, as well as the four-cycle graphics-store interval.

At a nominal 1 MHz these are microsecond-scale schedules. The test uses flat RAM and output-latch interpretation: it does not model asynchronous PB7, VIA readback, RMW dummy-write effects, analog pulse shapes or the stepper's acoustic response. It establishes CPU cadence and bit routing under the caller's register preconditions, not full PAL compliance or a whole-frame capture.

## Video recordings are not released-binary timing receipts

The author explicitly recorded a special approximately 49.23 Hz build to match a camera, retimed its video to 50 Hz, and combined separately recorded sound. The released version is described as 50 Hz. Therefore a movie's frame cadence is not an independent trace of the D64's timer schedule or loading intervals. The drive/case and microphone setup also affect the recorded sound. [Recording account](https://www.quiss.org/freespin/recording.html)

The engineering lesson is a tightly coupled output program: instruction timing creates the picture, timer bits are copied into mechanics, and the disk representation is chosen for a cheap decoder. The finite checks above make parts of that mechanism reviewable without assuming a C64 framebuffer or treating a recording as execution evidence.

Reproduction commands and artifact definitions are in [the research README](../../research/freespin/README.md). Production renderer files, binaries and running previews were not changed.
