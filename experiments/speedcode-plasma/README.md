# Generated-code plasma

This original full-screen PAL C64 example demonstrates the generated-code
memory/speed trade discussed in the [line/rendering source survey](../../docs/research/lines-and-vector-fill.md).
It combines two live sine phases into 1,000 screen cells on every update.

```sh
sh build.sh
sh run.sh
python3 verify.py
```

The assembler prepares a reusable sine table and sixteen 8×8 density glyphs.
No screen animation frames are stored. Two generated writers bake all screen
addresses, horizontal table offsets, and row operands into machine code.
The C64 computes the row terms, runs the writer for the hidden screen matrix,
then publishes the complete matrix at the PAL frame boundary.

For cell `(x,y)`, the density index is
`floor((round(7.5+7.5*sin((phaseX+5*x)*2*pi/256)) +
round(7.5+7.5*sin((phaseY+7*y)*2*pi/256)))/2)`.
The X phase advances by one and the Y phase by three after publication.
White/blue ordered patterns express sixteen density levels; this is a
two-color dithered plasma, not an additional C64 palette.

The standalone PRG is `build/example.prg`. Each generated writer contains
1,000 unrolled cell operations. The source remains one shared assembler macro.
This example makes no comparative speedup claim against another renderer.

The checked native build publishes one complete matrix every PAL field,
or **50 updates per second**. Its two generated writers occupy **22,002 bytes**.
Verification checks all 256 phases plus wraparound over 258 publications,
every active matrix byte, all shared density glyphs, and five complete
320×200 VIC canvases. All 320,000 sampled screenshot pixels match the
independent sine/density model. The owned emulator is closed after checking.
See the generated [receipt](build/verification/receipt.json) and
[preview](build/verification/plasma.gif).
