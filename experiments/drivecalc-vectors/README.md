# Drive rotation, projection and generated C64 drawing

This folder contains an original PAL C64/1541 example: the actual drive CPU
rotates and projects eight cube vertices; the C64 receives their 2D positions,
generates `PREPLINE` drawing code and executes it into an inactive hires bitmap.
A completed image is published in the bottom border. The displayed bitmap
stays intact throughout subsequent drive calculations, IEC transfers and drawing.

```sh
sh build.sh
sh run.sh
python3 verify.py
```

Run from this directory. Java/KickAssembler, PAL `x64sc` with true 1541
emulation, and Python/Pillow for the verifier are the existing repository tools.
Device 8 is required; no disk image, original production or generated asset
cache is required. The build assembles the owned drive payload before embedding
it in the owned C64 program. The launcher disables virtual-device traps and
drive-idle skipping.

The [owning source note](../../docs/research/lines-and-vector-fill.md) points to
Wegi's [educational Drivecalc source](https://codebase64.net/doku.php?id=base:drivecalc_vectors).
Its drive `ROTATES` / `ROTPOINTS` / `PERSP4` path and `R` command calculate and
return projected points; C64 `PREPLINE` prepares drawing speedcode. That division
of work is the contract reproduced here. Our math, cube data, protocol and
generated writers are original. Their arithmetic, IEC efficiency and appearance
are independent of Wegi's example; no performance equivalence is claimed.

The drive uses two rotations with 16-entry Q6 sine/cosine tables. It calculates
each signed product with a bit-serial multiply, truncates that product toward
zero after division by 64, and applies perspective `(160,100) +
trunc(80*(x,y)/(96+z))`. Yaw advances through all 16 phases; pitch uses three
times the yaw phase. Eight own vertices at coordinates ±20 and reusable trig
coefficients are prepared data. Every transformed coordinate and projected pose
is calculated on the 1541 at runtime. Cube symmetry makes some phases share a
wireframe: the normal cycle contains 13 distinct bitmap images.

The C64 uploads 1,280 bytes to drive `$0300–$07ff` once, using 32-byte DOS
`M-W` packets. Each pose sends one phase byte to `$0700`, invokes `M-E $0300`,
then reads 19 binary bytes from `$0710` using `M-R`: sixteen XY bytes, phase,
XOR checksum and completion marker. The drive saves its touched zero page and
registers, calculates, restores them and returns to DOS with `RTS`. These are
ordinary DOS commands, following the [Commodore 1541-II manual](https://www.mocagh.org/cbm/c1541II-manual.pdf).
There is no custom fastloader or parallel calculation/transport protocol.

On the C64, `PREPLINE` samples all twelve edges using rational nearest-pixel
stepping with ties toward the endpoint. For each sample it writes an eight-byte
`LDA bitmap / ORA #mask / STA bitmap` sequence to `$8000`, then appends `RTS`.
The program executes those generated instructions, preserving crossings with
OR. It has no C64 rotation or perspective routine. The embedded 1541 payload
contains the object and trig data solely for uploading to the drive.

Bitmaps occupy `$2000` and `$6000`, with constant white/black matrices at
`$0400` and `$4400`. CIA2 switches their VIC banks at raster 252. There is no
music, culling, filling, texture mapping or raster renderer: this is a compact
wireframe pipeline. The default object occupies approximately 55×58 pixels
within the 320×200 canvas. The generated writer buffer is bounded below `$c000`;
an exceeded bound stops with a yellow border. Invalid transfer data stops red.

The native verifier checks 17 normal presentations (all 16 phases plus wrap)
and one explicitly synthetic **input** witness: it changes only vertex 0's X
coordinate in live drive RAM before the next real calculation. It never writes
projected coordinates, generated instructions, bitmap output or execution PC.
An independent mathematical oracle predicts the drive's 24 intermediate XYZ
bytes and every returned packet. A separate closed-form edge sampler predicts
every generated instruction and all 8,192 bitmap bytes. Full 320×200 native VIC
captures then check 1,152,000 pixels. The drive-only vertex change changes exactly
110 predicted image pixels while the other seven projected vertices retain
their normal values.

The proof also checks the complete uploaded payload, zero-page restoration at
the drive's actual return boundary, both bitmap banks, matrix contents, VIC bank
and mode registers, front-buffer preservation at four pipeline stages, and
bottom-border publication followed by a full display field. It binds source,
C64 PRG and drive PRG hashes and closes its own VICE process. Timestamped
`build/verification/<UTC>/verification.json` files retain successful and failed
runs separately; the output directory also contains raw memory, monitor traffic,
screenshots and an animation.
The completed source-bound run is
[`20261108T102940.314939Z`](build/verification/20261108T102940.314939Z/verification.json).

Measured in native PAL VICE with real drive emulation: setup/upload takes
2,440,455 C64 clocks (about 2.48 s). A drive calculation takes 42,519–45,210
drive clocks. Phase upload, execution and result transport together take
134,288–137,050 C64 clocks. Inactive-bitmap clearing takes 95,483–95,683 C64
clocks; writer generation takes 82,380–91,086; generated execution takes
2,814–3,474. Each image uses 280–316 plot writers (2,241–2,529 code bytes).
These ranges include the live-input witness and VIC stalls in C64 measurements.
Consecutive complete presentations are 18–19 PAL fields apart (roughly
2.64–2.78 poses/s); measurements count display scheduling and the deliberately
slow DOS transfers. This is emulator evidence, not a physical-drive timing claim.
