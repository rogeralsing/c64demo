# Sixteen-line sprite interleave

An original moving **192×168-pixel** hires sprite carpet with eight columns of
colored woven artwork. It demonstrates actual pointer changes during running
sprite DMA, using rolled rows and duplicated five-line overlap intervals.

```sh
sh build.sh
sh run.sh
python3 verify.py
```

The shared builder writes `build/example.prg`. The normal launcher selects PAL
at normal speed. All artwork is generated from a small original weave rule,
with a row-identification byte at the left edge. No release artwork or prepared
animation frames are included. Horizontal positions advance once per PAL field.

## Two independent schedules

The eight ordinary-height sprites start at raster line 64 and restart every
**21 lines**: 64, 85, 106, 127, 148, 169, 190 and 211. Separately, their pointer
group advances every **16 image lines**, with boundaries at raster lines
80, 96, 112, …, 224. The pointers are not changed only at sprite restarts.

For block `b`, source image rows `[16*b, 16*b+20]` are stored at internal sprite
row `y mod 21`. Every source row is written into all blocks whose interval owns
it. Thus adjacent blocks contain identical bytes for their five shared rows.
The VIC can fetch either block during a pointer transition and get the same
image pixels, despite the eight sequential pointer writes completing at
different times.

```text
offset = 64 * (8*block + floor(xByte/3))
       + 3*(sourceY mod 21) + (xByte mod 3)
```

Eleven groups of eight sprites occupy **5,632 bytes** at `$2000..$35FF`.
Pointers range from `$80` to `$D7` in the table at `$07F8..$07FF`. There are
1,200 extra byte destinations for the duplicated overlap rows. Rows beyond
the 168-pixel image and each sprite's unused 64th byte are zero.

Raster polling schedules the pointer work inside the shared intervals.
Y-register writes are requested eight lines before the next restart, while
the previous sprite is still drawing. The scheduler handles adjacent ready
jobs without waiting for an already-passed raster equality. Normal character
badlines and sprite DMA remain active. The background screen and its selected
glyph are blank, so the visible picture comes from the hardware sprites.

## Native proof

The checked run passed **33 complete fields**, covering all 32 horizontal
positions and wraparound. For every field, the independent verifier compares:

- All 5,632 sprite-data bytes against an interval-based ownership oracle.
- The complete 384×272 VICE screenshot against an independently generated image,
  including all 32,256 carpet pixels, its moving position and black surroundings.
- Sprite modes, positions, final pointers and blank background storage.

Across the following 32 fields it also checks **2,816 pointer stores** and
**2,048 Y-register stores**. Monitor-reported pointer completions lie one or
two raster lines after each overlap starts, within its five-line window.
Y stores complete four through seven lines before their requested restarts.
The completed-field intervals alternate 19,672 and 19,640 PAL clocks, averaging
exactly **19,656 clocks**, one PAL field. This marker jitter comes from polling;
it is not a claim of cycle-stable entry or physical bus timestamps.

Generated [receipt](build/verification/receipt.json),
[monitor transcript](build/verification/monitor.log),
[expected artwork](build/verification/expected-carpet.png) and
[native animation](build/verification/sprite-interleave.gif) remain under ignored
`build/`. Verification closes only its owned emulator.

## Attribution and scope

The technique follows [Raistlin's Sprite Interleave article](https://c64demo.com/sprite-interleave/),
which credits Christopher Jam for the original idea and assistance. This folder
contains original code and artwork. The [research note](../../docs/research/sprite-interleave.md)
documents the separate The Dive and Memento Mori source/layout investigations.

This example implements the **16-line variant** only. The tighter 20-line,
one-shared-row variant, full 200-line carpet, SAX optimization, vertically
scrolling background, production artwork blitters and physical-hardware timing
remain separate work. Its dedicated polling schedule does not establish a
deadline guarantee after adding unrelated IRQ or main-thread workloads.
