# Coupled audiovisual feedback

An original PAL C64 teaching counterpart of the mechanisms investigated in
**A Mind Is Born**: melody and palette share a small state machine, procedural
screen feedback uses live chip inputs, and the processor stack doubles as font
storage. This readable program makes no 256-byte or original-song claim.

```sh
sh build.sh
sh run.sh
python3 verify.py
```

The normal launcher keeps sound enabled. The program plays a pulse-wave melody,
triangle bass and gated noise percussion through three real SID voices at
volume fifteen. The generated file is `build/example.prg`; it has a normal
BASIC autostart header.

## Coupled state

One raster IRQ per PAL frame advances a 16-bit clock. Every eighth frame updates
the nonzero LFSR and chooses a melody note:

```text
s' = (s >> 1) XOR (0xB8 if s & 1 else 0)
note = s' & 7
```

The same state sets melody pulse width and four bright ECM background colors.
Every 32 frames selects a bass note. Each eighth frame closes the melody gate
for one frame and opens the percussion gate; the following frame reopens the
melody gate and closes the percussion gate. SID envelopes continue evolving
between writes. The explicit PAL raster clock differs from the original intro's
inherited approximately 60 Hz system-timer service.

The main loop samples CIA1 timer A and SID voice-three envelope output, then
pushes this font byte:

```text
font = (timer_sample XOR sampled_lfsr) OR envelope_sample
```

It also replaces each screen code using two neighboring cells:

```text
new_code = (floor((neighbor_a + neighbor_b) / 2) XOR sampled_lfsr) OR 0x20
```

The feedback pointer visits all 1,000 visible cells. Every screen code has bit
five set, so its six ECM glyph-index bits select glyphs 32–63. With screen
`$0400` and charset base `$0000`, these glyphs occupy **`$0100–$01FF`, the actual
CPU stack page**. Color RAM is black; zero glyph bits reveal one of the four
ECM backgrounds.

After initialization the main loop has no active JSR/RTS return address. Each
PHA wraps the stack pointer naturally. Hardware IRQ entry, the handler's saved
registers and its matching restore/RTI use that same page while the main loop
is suspended. Those interrupt bytes become visible font content. The program
runs continuously and does not return through the overwritten BASIC call stack.

## Verification and limits

`verify.py` starts only an owned VICE instance. An independent recurrence and
music model predicts LFSR, notes, gates, pulse width, bass state and palette.
The verifier compares real SID store traces, rather than treating SID's
write-only registers as ordinary readback. It separately checks the sampled
font-byte arithmetic and every address of one complete 256-PHA stack wrap.
Changing ECM screenshots and a native SID WAV recording establish visible
and audible output without claiming an analog sound oracle.

The timer phase, live SID envelope and intervening IRQ stack writes deliberately
affect the image. There is no fixed-frame visual replay or whole-screen pixel
oracle here. The font changes continuously; the music/palette control cadence
does not describe an independent visual frame rate. The example has its own
texture, tune structure and feedback rule, without the original intro's finite
song script, code/state byte overlaps, undocumented opcodes or reset ending.

The technique is attributed to [Linus Åkesson's walkthrough](https://www.linusakesson.net/scene/a-mind-is-born/index.php).
No original intro code, artwork or song data is copied. See the separate
[mechanism investigation](../../docs/research/a-mind-is-born.md) and
[original native evidence](../../docs/research/a-mind-is-born-native.md).

The native check passed 256 IRQ frames and 32 LFSR note updates. It compared
6,375 actual SID store values with the independent model, checked 256
consecutive PHA operations across all 256 stack/font addresses, and captured
four distinct ECM images. End-of-handler timestamps average 19,656.35 PAL
clocks apart; individual intervals vary with the handler's music branches.
The WAV output contains 398,688 samples at 48 kHz, with nonzero signal peak
8,667 and RMS 1,675.69. These are signal-presence measurements, not a sound
fidelity claim. The owned emulator exited cleanly after capture.

Generated evidence: [receipt](build/verification/receipt.json),
[monitor transcript](build/verification/monitor.log),
[visual animation](build/verification/feedback.gif) and
[SID recording](build/verification/sid-output.wav).
