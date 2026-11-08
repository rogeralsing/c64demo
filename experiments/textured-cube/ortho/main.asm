#define ONE_FACE
#define ORTHOGRAPHIC
.import source "../main.asm"
.errorif *> $8000, "Shared orthographic runtime overlaps sampler"
*=$8000 "Selected orthographic lookup sampler"
.import source "sampler.asm"
