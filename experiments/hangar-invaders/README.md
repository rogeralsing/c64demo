# Playable hangar invaders

Own small PAL C64 game: twelve moving character-grid enemies, a hardware-sprite
ship and projectile, score, misses, victory and restart. This is a playable
counterpart of the hangar minigame identified in our
[Aloft source note](../../docs/research/february-2026.md). Quiss's
[1 February creator note](https://csdb.dk/release/?id=259056&show=hidden) confirms
the original's playability; our code, rules, font and art are original. No Aloft
algorithm or original game source has been recovered here. Mermaid's separate
note describes its sprite version; our own enemies deliberately use characters.

```sh
sh build.sh
sh run.sh
python3 verify.py
```

Run from this directory. Existing repository tools provide Java/KickAssembler,
PAL `x64sc`, and Python/Pillow for verification. No disk image or asset cache is
required. `run.sh` builds and selects joystick **port 2**, with VICE's numeric
keypad mapping: **4 = left, 6 = right, 0 = fire**. Click the emulator window to
give it keyboard focus; these are numeric-keypad keys, rather than the number
row. Keyset input is enabled and joystick autofire is disabled. This follows
the [VICE joystick manual](https://vice-emu.sourceforge.io/vice_1.html)
and the installed VICE 3.10 command-line help.

For a laptop without a numeric keypad, configure VICE's **Keyset A / Keyset 1**
in its joystick settings: West = **A**, East = **D**, Fire = **Space**. Keep
keyset joysticks enabled, and start with `sh run.sh -joydev2 2`. A connected
controller can be selected instead through the same port-2 joystick settings
or a later `-joydev2` option. The C64 program always reads actual CIA1 port-A
joystick lines at `$dc00`; its gameplay has no keyboard-matrix or test-input
substitute.

Move two pixels per PAL field, bounded to screen X 32–216, keeping the complete
ship between the hangar walls. The four-column,
three-row formation moves one character every 32 fields between base columns
5 and 10, reversing at each boundary. Enemy glyphs alternate every sixteen
fields. Up/down do nothing; simultaneous left/right cancel. A fresh fire press
launches one projectile, moving four pixels upward per field. A held button
never repeats. Fire edges while a projectile is active are discarded; release
and press again to launch the next shot.

Collision is the explicit logical rule: the projectile's one-pixel-wide,
five-pixel-high rectangle intersects a live enemy's 8×8 character cell.
Transparent glyph gaps remain part of that cell. A hit removes one enemy and
adds one point. An unhit projectile leaving the top adds one miss. Miss and
shot counters display modulo 100; score runs from zero to twelve. Destroy all
twelve enemies to display **HANGAR CLEAR**. Release fire, then press to restart;
the held restart press does not also launch a shot. This bounded game has no
enemy bullets, loss state, sound, original scene artwork or background demo.

The owned font is at `$2000`, two 64-byte sprite records at `$3000`, and the
screen at `$0400`. Hardware sprites render the ship and shot; the CPU updates
the enemy characters and HUD. All changes run after raster 252 and finish
before the following visible area. No raster multiplexing or framebuffer movie
is involved. Prepared data consists of reusable font/sprite art, twelve tile
offsets and UI strings. Movement, flight, collisions, score and state transitions
are calculated on the C64 each field.

The native verifier reuses our existing VICE Joyport bridge and sends explicit
synthetic port-2 input **lines**. It writes no game RAM, projected output or PC.
An independent rules model predicts every field's state; a separate character
and sprite compositor predicts full pixels from our authored art. The proof
checks CIA pins/direction, all live enemies, both sprite positions/enables,
screen/color planes, font and sprite bytes, complete pixel images and deadlines.
It drives the actual game through both movement clamps, opposed directions,
ignored up/down, two guaranteed misses, held/busy fire suppression, twelve hits,
victory while fire remains held, release/new-press restart and a new shot.

Successful native proof covers 671 field updates, 671,000 matrix bytes, 63 full
320×200 captures (4,032,000 exact pixels), all twelve enemy removals and restart.
Visible state updates once per PAL field: 19,648–19,664 clocks between observed
presentation points, within eight clocks of 19,656. Input, game logic and drawing
take 2,798–3,727 C64 clocks including VIC stalls, below the 6,993-clock budget
from raster 252 to the next visible area. This is native PAL VICE evidence;
physical joystick/keyboard hardware and NTSC timing are outside the proof.

Timestamped `build/verification/<UTC>/verification.json` receipts bind source,
the reused joystick bridge and PRG hashes. They retain explicit failures and
successful evidence separately, together with input packet acknowledgements,
field states, native screenshots, memory dumps and a gameplay animation. The
verifier closes only its own emulator process.
The completed source-bound run is
[`20261108T104441.088439Z`](build/verification/20261108T104441.088439Z/verification.json).
