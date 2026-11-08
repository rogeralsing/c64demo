// Selected live texel-transition renderer; one actual XOR prefix pass.
#define FILLED
#define XOR_TEXTURE
#define XOR_TEXELS
#define POLYGON_EDGES_MACRO_ONLY
#define XOR_TEXEL_EVENTS
.const FILLED_MODE = true
.import source "../../../src/engine.asm"
