# Candidate A: exact whole-face affine spans

Uses the shared live orthographic geometry, exact top-left convex-quad spans,
Q8 gradients and one textured face. No geometry poses or animation frames are
stored. For each covered integer sample, the target is

```
U = duDx*(x-quadX[0]) + duDy*(y-quadY[0])  (mod 65536)
V = dvDx*(x-quadX[0]) + dvDy*(y-quadY[0])  (mod 65536)
texel = ((U >> 8) & 15) | ((V >> 4) & 240)
```

The runtime shifts the UV origin along the left span edge. V is internally
scaled by16 modulo65536, preserving the wrapped row nibble; U's integer part
wraps modulo16. Complete even/odd sample pairs share one matrix OR/store.
Odd leading samples and even trailing samples preserve all other character
lanes. Immediate per-quad gradient operands remove zero-page ADC reads.
The terminal sample does not compute an unused next UV coordinate.

Private zero page: `$f6..$f8`; code starts at `$8000`. The sampler only changes
shared drawing temporaries and private state. Geometry, phase, face index,
quad coordinates and hidden-buffer selection survive.

Build with the existing `experiments/build-one.sh` pointed at this folder.
Native correctness and performance are measured by the central comparison
verifier; no performance or pixel claim is made before that proof.
