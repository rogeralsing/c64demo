# Arithmetic texel-boundary jumps

Use each UV gradient and its current fraction to calculate the next integer
texel change. Jump to the earliest U/V event or the face exit, sample the
texture there and emit its nonzero color delta into the real XOR operands.

The 290-byte implementation reduces lookups to 13,750 per loop, but repeated
divisions cost more than the saved samples. It reaches 3.78 complete updates/s
in PAL VICE. See the [comparison and reproduction commands](../../README.md).
