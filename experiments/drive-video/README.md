# Video and stepper control from a 1541

This original example follows Freespin's separate output-machine idea: the
1541 CPU toggles VIA serial outputs for video and samples a real Timer1 PB7
waveform into adjacent stepper phases. The C64 uploads the program through
DOS `M-W`/`M-E`, releases its IEC outputs, and displays a status title.

```sh
sh build.sh
sh run.sh
python3 verify.py
```

The normal C64 window shows status. Physical drive video uses the external
serial-to-monitor resistor arrangement described by
[Freespin's author](https://www.quiss.org/freespin/raster.html). This is our
small signal example, with original code and graphics.

Three reusable 256-entry tables produce moving coarse black/white columns.
No movie frames are stored. A live field counter selects the table offset
and four Timer1 reload values. Software copies actual PB7 samples into two
adjacent stepper phases; the program does not traverse the drive head.
The drive code and tables fit in `$0300..$07FF`. The C64 boot program embeds
those bytes, so runtime needs no disk image or research cache. The nested
`drive/build/example.prg` is a drive payload; `build/example.prg` uploads it.

The native verifier starts an actual emulated 1541 with true-drive emulation
and disabled virtual-device traps. All 1,280 uploaded RAM bytes match the
payload. Across 258 consecutive drive fields, the live counter covers all
256 states and wraps; all four timer latch values match. Sixteen complete
port traces check every visible row and column, ten broad sync half-lines,
and the actual timer-read-to-stepper-write coupling.

Continuing visible lines take exactly 64 drive CPU cycles. Each sync pulse
lasts six cycles; each coarse column lasts eight cycles. Explicit sync
writes avoid relying on the original production's port-read precondition.
Each field takes 20,041 drive clocks, about 49.9 fields/s at nominal 1 MHz.
Routine handovers have explicit offscreen timing gaps.

[Verification receipt](build/verification/verification.json),
[digital signal preview](build/verification/drive-signal.gif), and raw port
traces are retained under `build/verification/`. The preview reconstructs
our digital output stores; it is not a C64 screenshot or analog capture.
The VICE process exits successfully after the check.

Analog monitor locking, the resistor network, physical acoustic output and
full PAL conformance remain outside this CPU/VIA proof. No SID soundtrack
substitutes for the drive's stepper control.
