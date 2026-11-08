# Drive-assisted BRR sprite cube

An original runnable counterpart to **Boo!**'s documented bit-reversal-rendered
line interpolation and drive-side slope preparation. A live rotating cube is
filled into multicolor hardware sprites. The C64 and a real emulated 1541
exchange actual geometry requests and computed results; no original Boo code,
artwork, drive payload or screen poses are included.

```sh
sh build.sh
sh run.sh
python3 verify.py
```

Build needs Java/KickAssembler through the shared repository helper. The nested
`drive/main.asm` builds first; its 1280-byte payload is then embedded in the
standalone C64 PRG. Run requires PAL VICE with a true 1541 at device 8 and device
traps disabled. The wrapper supplies those settings, normal speed and sound.
No disk image, sibling repository, research cache or downloaded program is
needed. Verification additionally needs Python3/Pillow and the repository's
tracked monitor helper and Colodore palette.

## Live work on each machine

The C64 transforms eight original cube vertices with Q6 two-axis rotation and
orthographic projection. Sine and quarter-square tables are reusable scalar
arithmetic, not projected poses. Rotated face normals select the visible faces.
Their shared edges have one canonical representation and XOR transition color.
Up to nine nonhorizontal edges become requests containing two Y endpoints and
their corresponding X positions.

The 1541 receives those endpoints through IEC. For each interval `[a,b)`, it
calculates signed floor division

```text
x1-x0 = q*(b-a) + r,   0 <= r < b-a
T = sorted(reverse8(y) for a <= y < b)[r]
```

A zero remainder uses separator 0. For nonzero remainders, an own eight-stage
binary selection counts reversed values below each candidate. There is no
stored table of slopes or thresholds. The drive returns signed `q` and `T`;
it retains `r` and the denominator in live RAM for a separate arithmetic audit.

The C64 consumes the returned results in real generated position-output cells:

```asm
sta edgePositionForThisRow
cpx #(reverse8(row)+1)
adc rowStep                 // zero page
```

X holds the returned separator, A the current X position. Compare carry means
`reverse8(row) < T`, so exactly `r` fractional increments occur. The endpoint
displacement is exact. The C64 patches a half-open entry/stop and the direct
position-store targets, restores the stop instruction and checks the resulting
endpoint before continuing. The output arrays are consumed by the marker pass.

This is the documented **five nominal CPU cycles for CPX/ADC**, or nine with
the absolute position store. It is not the cost of plotting, setup, transfer,
filling or display. The whole example's measured cadence is stated below.
BRR intentionally places fractional steps differently from an exact ceiling
DDA; its characteristic small boundary wiggles are part of the algorithm.

## Transport and coherent sprite display

The C64 initially uploads the entire own drive program with real KERNAL DOS
`M-W` packets, then starts it with `M-E`. The drive takes over its VIA and runs
without DOS. An own half-duplex IEC protocol then sends endpoints and receives
results. C64 clock strobes have 33-cycle helper delays; byte acknowledgements
are level-handshaken. The 1541's inverted input polarity is handled explicitly.
Sequence and count fields detect a stale or incoherent response.

Only the top-border IRQ services IEC, at most three bytes per PAL field.
While the drive divides/selects ranks, C64 fields continue displaying the
previous completed cube. The foreground draws only into the hidden sprite
buffer. Publication swaps that buffer at the next top border after completion.

The canvas is 72×84 logical multicolor pixels, expanded to 288×168 physical
pixels. Six sprites are reused in four 42-line bands. Two legal screen pages,
`$0400/$0800`, alternate their sprite-pointer tables: the next table is prepared
while its page is hidden, then selected at the band boundary. This avoids the
VIC's character-ROM shadow at `$1000..$1FFF`. There are no bitmap/character cube
pixels behind the sprites. Packed XOR crossings are prefix-filled horizontally
into the actual hardware sprite data. Three selectors distinguish the faces.

## Native evidence and actual cadence

The retained verifier independently reconstructs all 64 moving poses and checks
that visible face interiors do not overlap. It obtains edge positions through
the mathematical rank/count rule, not the C64 generator or drive selector.
Separate opaque per-face intervals produce the pixel oracle, avoiding reliance
on the C64's marker-prefix implementation.

The normal PAL VICE run passes **66 publications**, including a complete pose
cycle and wraparound. It verifies 594 real drive requests, all uploaded code and
reversal-table bytes, signed quotients from −23 to 23, and 370 nonzero remainders.
Native drive input, output and diagnostic RAM agree with the independent oracle.

All **6,893,568 full-screenshot pixels**, **99,792 marker bytes**,
**66,528 live position bytes** and **101,376 hidden sprite bytes** match.
The generated cells are restored correctly between uses. Across **2487
continuous display fields**, all **9948 actual `$D018` stores** follow the four
sprite-band schedule. Every IEC slot completes at raster 3–44, before the first
sprite band. The owned VICE process exits normally with code 0.

This intentionally straightforward example publishes every **37–38 PAL
fields**, averaging 37.6923 fields, about **1.33 poses/second**. Request/result
transport takes 19–21 fields; foreground rendering takes 316,309–326,938 native
clocks, including display interrupts and VIC stalls. The display repeats the
completed pose during that work. This is not a 50Hz renderer or an integrated
speedup claim for BRR. The five-cycle arithmetic core does not remove the
example's setup, fill and communication costs.

`build/verification/proof.json` retains the commands, hashes, timings, native
drive RAM, full images and observer trace. `brr-sprite-cube.gif` uses uniform
160ms playback for the sampled poses and does not show native cadence. A failed
rerun removes the current success receipt. PAL VICE 8565/1541 execution is not
a physical-hardware or analog-video proof.

## Provenance and differences

Primary mechanism: Matthias Kramm / Quiss,
[Boo! BRR article](https://www.quiss.org/boo/) and
[rank-selector explanation](https://www.quiss.org/boo/bitreverse.html).
The repository's [interpolation study](../../docs/research/bit-reversal-lines.md)
and [released-binary analysis](../../docs/research/boo-binary.md) establish the
strict comparison convention and drive-side role. The archived author article
and binary notes were read before choosing this design. No author source was
vendored; the selector, transport, renderer and artwork here are our own.

Own cube dimensions, orthographic projection, multicolor sprite canvas,
packet protocol, selector implementation and slower publication cadence differ
from Boo's reported 172×172 sprite-filled cube. The original's 4K packaging,
50Hz claim, complete sprite-fill engine and drive protocol are not reproduced.
The scalar product primitive follows our existing `morphing-cube` example;
the DOS upload shape follows our `drive-video` example. Both are copied into
this standalone source, with no live executable dependency on those folders.
