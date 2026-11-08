# Three moving pattern layers

This original PAL C64 example creates three independently moving pattern
layers. It is our own counterpart to the three-layer visual idea documented
for [Aloft](../../docs/research/february-2026.md). Aloft's original mechanism
remains unknown; this example declares its own XOR composition explicitly.

```sh
sh build.sh
sh run.sh
python3 verify.py
```

Three reusable 64×64 masks contain diamond rings, square rings and diagonal
stripes. Four horizontal sample phases per mask occupy 12,288 prepared bytes.
They contain patterns, not animation frames. The C64 independently updates
the three source positions, selects rows, samples all three masks and composes
the complete hidden bitmap before publishing it.

Layer A contributes selector `01`, B contributes `10`, and C contributes `11`.
Their XOR selects black, cyan, purple or white. Equal combined contributions
cancel: all three layers together select black. This is deliberate palette
logic, not physical alpha blending or three independently colored framebuffers.

The window contains 128×96 logical samples, displayed as 256×192 physical
pixels in a centered 320×200 bitmap. The sampler shares source with
[bitmap-layers](../bitmap-layers/README.md). Only this entry enables its
three-layer variant; the original two-layer program retains its OR contract.

The declared mask functions are `(abs(2*x-63)+abs(2*y-63)) mod 32 < 8`,
`max(abs(2*x-63),abs(2*y-63)) mod 16 < 4`, and `(x+3*y) mod 16 < 4`.
Their source positions advance by `(1,2)`, `(-1,1)`, and `(2,-1)` respectively.
The combined source state repeats after 64 images.

Native verification checks 65 complete bitmaps including wraparound, all
12,288 prepared mask bytes, both attribute matrices and eight full VIC images.
All eight layer-membership combinations occur. Each of the three masks changes
independently; the captured sequence contains 64, 64 and 16 distinct masks.
All 520,000 bitmap bytes and 512,000 screenshot pixels match the independent
integer-pattern model. The owned VICE process is closed after checking.

The simple sampler takes eleven PAL fields per image, about **4.5 updates/s**.
It holds the last complete image while rendering the next. This is a readable
reference implementation, not an optimization or an Aloft frame-rate claim.
See the [receipt](build/verification/20261108T080853.966967Z/verification.json)
and [sampled animation](build/verification/20261108T080853.966967Z/animation.gif).
