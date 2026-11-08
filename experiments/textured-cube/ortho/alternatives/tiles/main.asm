#define ONE_FACE
#define ORTHOGRAPHIC
.import source "../../../main.asm"
.errorif *> $8000, "Shared orthographic runtime overlaps sampler"
*=$8000 "Packed tile-cache alternative"
.import source "sampler.asm"
