# Twenty-line sprite interleave

The tighter sibling of the [16-line carpet](../sprite-interleave/README.md):
the same original 192×168 woven image moves horizontally, but pointer groups
advance every **20 lines**, while ordinary-height sprites restart every
**21 lines**. Neighboring groups share exactly one image row.

```sh
./experiments/sprite-interleave-20/build.sh
./experiments/sprite-interleave-20/run.sh
python3 experiments/sprite-interleave-20/verify.py
```

Run from the repository root. The launcher uses PAL at normal speed.
The output is `build/example.prg`.
Its build first rebuilds the default 16-line sibling through that example's
own build script, producing the verifier's required identity reference, then
builds this 20-line variant. No preexisting sibling build artifact is required.

## Shared engine, different scheduling

The three-line `main.asm` enables `INTERLEAVE_20` and imports the existing
engine. There is no second copy of its initialization, artwork generator,
Y restarts or rolled-data implementation. Only the tight pointer scheduler
and faster pointer stores are conditional.

For block b, image rows `[20*b,20*b+20]` are stored at internal sprite row
`sourceY mod 21`. Source rows 20, 40, …, 160 occur in both neighboring
groups. Nine groups occupy **4,608 bytes** at `$2000–$31ff`, with **192**
extra byte destinations for duplicated rows. The last pointer group is
`$c0–$c7`.

Pointer IRQs are requested at shared-row boundaries 84, 104, …, 224.
The handler preserves A/X/Y and uses paired SAX/STX stores with three INX
instructions. This is the aligned-base optimization described in
[Raistlin's article](https://c64demo.com/sprite-interleave/) and
[the source research note](../../docs/research/sprite-interleave.md).
Each pointer base is divisible by eight, as the SAX mask requires.

Y writes remain independent: sprites start at raster 64 and restart at
85, 106, …, 211. The main polling loop requests each Y update eight lines
early. Normal character badlines and actual sprite DMA remain enabled.
No framebuffer or animation frames are prepared.

The rebuilt default 16-line program remains **byte-identical**, SHA-256
`94709e5bea31d7d9a10cb4c0d4551a059d4a3c6fa5f85e5a0b4a3496e08fe16e`.
Its retained native proof still applies. Its verifier's interval helper now
accepts explicit step/group arguments; its defaults and 5,632-byte result
remain unchanged.

## Native pixel and deadline proof

Passing receipt:
`build/verification/20261108T095608.367157Z/verification.json`.

- **33 consecutive complete fields** cover all 32 horizontal positions and
  wrap. All 4,608 source bytes match the independent interval-ownership
  oracle in every field: **152,064 bytes** checked.
- Those fields plus five timed fields match **3,969,024 pixels** across
  complete 384×272 native screenshots, including black surroundings.
- **2,304 pointer stores** and **2,048 Y stores** have the expected values
  and order. Native modes, final pointers, horizontal MSBs, positions,
  blank screen and blank glyph also match.
- **320 exact post-store checkpoints** cover all eight shared boundaries
  in five motion phases. Each CPU write follows that sprite's final
  old-only pointer fetch and precedes its first new-only pointer fetch.
  The smallest measured deadline margin is **22 PAL clocks**.
- Corrupting only the new group's copy of shared source row 20 changes
  exactly **eight real DMA pixels**. The normal image oracle rejects it.

The exact pointer timing uses instruction completion clocks and the PAL VIC
pointer-fetch slots, rather than deferred memory-watchpoint timestamps.
Some stores finish on the shared boundary raster; others finish on the next.
That is valid because the shared image row's eight pointer fetches themselves
span two raster lines. It is not a claim that all eight writes fit within one
63-clock raster line.

Motion advances one pixel each **19,656-clock PAL field**. No unrelated
workload or SID player is included, and physical hardware has not been tested.
The deadline observations apply to this program and its measured entry phases.

PRG SHA-256:
`7a2281c29e65bd9e6c53f9d36378fbad5df2b66d8aab584cc022e677dfefe8e3`.
The verifier creates a new dated receipt initialized with `passed: false`,
preserves failed runs and closes its own VICE process.
