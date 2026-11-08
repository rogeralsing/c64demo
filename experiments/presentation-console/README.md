# Mock DOS, source viewer and SID menu

An original counterpart to the C64 presentation described in the
[Second Reality note](../../docs/research/second-reality.md): a mock DOS
prompt, an editor-like note/source viewer and a sound-selection menu.
Our text, page layout, font, note patterns and program are our own.
No original production files, artwork, interface bytes or SID tune are used.

```sh
sh build.sh
sh run.sh
python3 verify.py
```

At the DOS prompt, type `DIR`, `HELP`, `EDIT`, `READ` or `SID`, then RETURN.
The command buffer holds sixteen characters and supports DELETE. Unknown
commands clear the prompt. `EDIT` and `READ` open the same **read-only**
64-row source/note viewer: W/S scroll, R returns to the top, Q returns to DOS.
The displayed directory is a mock environment; no host or disk file changes.

In the SID menu, 1/2/3 select and start pulse, triangle or noise patterns.
RETURN restarts the selection, SPACE stops it, and Q returns to DOS.
These are three small original oscillator sequences, rather than an external
music file. Each sequence advances a note every twelve PAL fields.

Normal KERNAL keyboard scanning and `GETIN` handle input. Page construction
uses an inactive matrix and publishes it at the next top border; the source
font remains fixed. The SID menu continues generating actual SID writes
while it accepts keys. The viewer is a presentation example, not a general
editor or a complete DOS implementation.

The [native verification receipt](build/verification/verification.json)
records normal VICE keyboard-queue input for command dispatch, viewer
scroll/clamps/reset, command capacity/DELETE, page returns and all sound
controls. Twenty viewport captures match independently predicted text and
font pixels: 1,280,000 exact comparisons. Both screen buffers and the loaded
program/font bytes are checked without code or PC patches.

Twenty-seven played notes cover all three patterns and wraparound. All
72 corresponding SID stores match independent frequency and waveform
predictions; note intervals are twelve actual PAL fields. The closed VICE
WAV contains 951,840 samples at 48 kHz, peak 6,075 and RMS about 1,063.
The verifier observes a normal instruction after the final SID store so
VICE's queued store checkpoint is drained before comparison.

[Preview](build/verification/presentation-console.gif), screenshots, key
inputs, SID traces and [audio](build/verification/sid-output.wav) remain
beside the receipt. The preview uses selected settled pages at 200 ms each.
It is not a recording of typing speed. VICE exits 0 after the check.
Original-production identity and physical SID/keyboard behavior remain
outside this bounded emulation proof.
