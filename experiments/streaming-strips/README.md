# Real disk streaming through four strip buffers

An original 1,600×200 multicolor panorama moves through a 320×200 viewport in
twenty 64-pixel steps. The initial viewport is embedded in the program. Every
remaining strip is read from an actual file on an attached D64 by the C64's
KERNAL IEC loader. Four resident buffers hold only four strips at a time.

An independent raster IRQ animates the border and runs a small looping SID
voice while the main thread loads or prepares the next viewport. After all
twenty strips are consumed, a music-counter handshake leads to a final text
scene. This is an educational counterpart to the loading contracts studied
in [No Bounds](../../docs/research/no-bounds-loading.md), using new code and
mathematical artwork.

## Build and run

```sh
rtk proxy sh build.sh
rtk proxy sh run.sh
rtk proxy python3 verify.py
```

The build uses existing Python/Pillow, KickAssembler and VICE `c1541` tools.
It generates `build/example.prg`, `build/example.d64`, `build/panorama.png`,
and `build/manifest.json`. The D64 contains the boot program and files
`00` through `19`. The launcher injects the boot PRG, attaches the D64 to
drive 8, enables true 1541 emulation and disables device-8 loading traps.
The twenty runtime strip transfers therefore use the emulated IEC bus.

`verify.py` uses the same true-drive settings at normal PAL speed. A complete
run takes several minutes because it performs the real serial loads. Each
run starts and closes its own VICE instance and preserves its own copies of
the exact program and D64.

## Payload and resident memory

Each strip covers eight character columns across all 25 rows:

| Component | Bytes |
| --- | ---: |
| Bitmap | 1,600 |
| Screen attributes | 200 |
| Color RAM attributes | 200 |
| Payload total | 2,000 |
| PRG load-address prefix on disk | 2 |

The twenty payloads total **40,000 bytes**, including 32,000 bitmap bytes and
8,000 attribute bytes. Slots at `$8000`, `$8800`, `$9000` and `$9800` allocate
2,048 bytes each: **8,192 resident bytes containing at most 8,000 payload bytes**.
Their unused 48-byte tails retain `$CC` guards. The complete stream is not
embedded in the PRG or preloaded elsewhere in RAM.

The initial viewport occupies 10,000 prepared bytes at `$4000..$670F` before
startup copies it to the first display. That initialization source is then
reused as display working memory. Complete bitmap buffers use `$2000` and
`$6000`; their screen matrices use `$0400` and `$5C00`. Both live outside the
four resident strip slots. Color RAM is deliberately white in every source
cell, allowing its streamed copies to remain constant while bitmap/screen
buffers change coherently.

## Producer, consumer and music ownership

The program first loads four real files. Each slot moves through explicit
states: **free, loading, ready, consuming, free**. The loader requires a free
slot, publishes it only after LOAD returns the expected end address, and
records its strip identity. The consumer requires the oldest ready identity.
It releases that slot only after a complete shifted viewport has been
published and scanned out; the producer may then refill it with strip `n+4`.

Viewport preparation shifts the previous bitmap/screen left eight character
columns and appends the loaded strip and both attribute planes. Publication
switches the completed display bank at the top border. The surrounding
initialization data and original source files are not used as a hidden
runtime stream cache.

The raster IRQ calls the SID player and increments a 16-bit music-call
counter. Main-thread synchronization compares its low byte and subtracts its
high byte against a target of 24 further calls. Brief IRQ masking makes those
two-byte reads coherent. This is an ordinary unsigned deadline within this
bounded scene, not a counter-wrap protocol or a claim that music calls equal
every PAL field.

The final scene is prepared in inactive bank 1: a copy of the machine's
uppercase character ROM at `$4000`, plus the completed text matrix at `$5C00`.
Character-ROM copying temporarily banks out I/O with IRQs masked. Publication
then changes bank/mode at the top border, leaving the previous panorama
intact until the text's first complete scanout.

## Deliberate differences from No Bounds

This uses the stock KERNAL loader, without Sparkle, compression, generated
loader code or a preloaded next production part. The main thread serializes
disk loading and viewport preparation. The visible panorama holds between
coarse 64-pixel steps while the border and music IRQ continue. Real loading
pauses are expected.

KERNAL IEC timing masks interrupts during parts of the transfer, suppressing
some raster/music calls. Thus the music is not guaranteed to keep a gap-free
50 Hz cadence. The four-slot ownership and complete-image handover are the
demonstrated contracts; this is not a reproduction of the original smooth
scrolling, loader deadlines, zero-gap presentation or physical-drive margin.

## Native proof

The tracked verifier follows normal startup without RAM/PC writes. It checks
all twenty actual LOAD calls, their slot targets and returned end addresses,
all 2,000 payload bytes against an independent pixel/attribute model, every
slot guard, and all producer/consumer ownership transitions.

It also verifies every completed viewport's full bitmap, both attribute
planes and native screenshot against independently sampled panorama pixels.
Four additional IRQ stops occur inside actual LOAD calls after at least 64
music calls, checking that the old image remains visible during loading.
The final text handover checks the prepared matrix/font before publication,
then compares the **first complete text field**, within one PAL frame of
publication, against the explicitly configured installed C64 character ROM.
It does not wait for a later settled frame to hide a partial first field.

Each run retains immutable input copies, complete RAM/event records,
per-file transfer clocks and music counts, native/expected images, a sampled
viewport GIF and `verification.json` under
`build/verification/<UTC timestamp>/`. The GIF holds viewport poses for their
measured emulated publication intervals; it omits border animation and audio.

The 8 November 2026 final run passed all **20 real strip loads and consumes**,
all **126 ownership/publication events**, every slot guard, and all 40,000
loaded payload bytes. Twenty-five panorama images and the first final-text
field matched **200,000 bitmap bytes and 1,664,000 native screenshot pixels**.
That first text field completed 15,949 clocks after publication, within the
same PAL frame, with zero incorrect pixels.

Each IEC transfer took **5,524,110–6,667,436 PAL clocks**, approximately
5.62–6.78 seconds. The first 64-pixel move followed about 24.4 seconds of
initial preloading, and the full scene took about 130 seconds of emulated
time. The music player ran **217–225 times per actual LOAD**, 4,406 calls
during loading in total. Those measurements include the deliberate loading
stalls and do not imply a steady music or scrolling cadence.

The current [full native receipt](build/verification/20261108T074743.160716Z/verification.json)
and [sampled native animation](build/verification/20261108T074743.160716Z/animation.gif)
preserve that run, its exact input copies and its first-field evidence.

The [first-field negative control](build/coherence-regression/20261108T074254.645583Z/receipt.json)
captures the earlier publication order after normal startup and twenty actual
loads. Its first text field had **2,582 incorrect pixels**, although the text
matrix was already correct at the capture stop. This establishes why checking
only a later settled text frame would miss the publication defect. Warp was
enabled only for that regression's wall time; no RAM or PC state was injected.
