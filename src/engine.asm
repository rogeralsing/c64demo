// A real-time wireframe cube for a stock PAL C64.
// The filled entry point reuses the runtime with a multicolor XOR edge renderer.
// Kick Assembler generates the lookup tables, not animation frames.
// Screen codes run down columns, making a 128x128 canvas in each 2 KB charset.

.const SCREEN = $0400
.const CHARSET_A = $2000
.const CHARSET_B = $2800
#if GLENZ || PAINTED || PONG
.const HALF_SIZE = 32
#else
.const HALF_SIZE = 24
#endif
.const SCALE = 64
.const CAMERA_DISTANCE = 144
.const FOCAL_LENGTH = 128
.const CANVAS_ROW = 4
.const CANVAS_COLUMN = 12
#if ICOSAHEDRON
#if FAST_SOLID
.const FRAME_TICKS = 2
#else
#if GOURAUD
.const FRAME_TICKS = 16
#else
.const FRAME_TICKS = 3
#endif
#endif
.const VERTEX_COUNT = ICOSA_VERTEX_COUNT
#else
.const FRAME_TICKS = FILLED_MODE ? 2 : 1
#if PAINTED
// Three temporary vertices hold the current face's inset marking.
.const VERTEX_COUNT = 11
#else
#if PONG
// Four shared scratch vertices hold one Pong rectangle on the front face.
.const VERTEX_COUNT = 12
#else
.const VERTEX_COUNT = 8
#endif
#endif
#endif
#if PAINTED || PONG
.const PROJECT_VERTEX_COUNT = 8
#else
.const PROJECT_VERTEX_COUNT = VERTEX_COUNT
#endif

// Zero-page workspace. The ROMs are disabled while the demo owns the machine.
.label linePointer = $f0
.label pixelMask = $f2
.label lineX0 = $f3
.label lineY0 = $f4
.label lineX1 = $f5
.label lineY1 = $f6
.label lineDX = $f7
.label lineDY = $f8
.label lineError = $f9
.label factor = $fa
.label multiplicand = $fb
.label squareSum = $fc

.import source "macros.asm"
#if GLENZ
.import source "glenz-renderer.asm"
#endif
#if PAINTED
.import source "painted-renderer.asm"
#endif
#if PONG
.import source "pong-renderer.asm"
#endif
#if FAST_SOLID
.import source "fast-rotation.asm"
.import source "fast-projection.asm"
.import source "fast-cull.asm"
.import source "fast-bounds.asm"
#endif
#if GOURAUD
.import source "gouraud.asm"
#endif
#if TONAL
.import source "tonal-shade.asm"
#endif
#if XOR_TEXTURE
.import source "../experiments/textured-cube/xor-hybrid/runtime.asm"
#endif

BasicUpstart2(start)

start:
    sei
    cld
    lda #$7f
    sta $dc0d
    sta $dd0d
    lda $dc0d
    lda $dd0d
    lda #$35
    sta $01
    lda #<rasterIRQ
    sta $fffe
    lda #>rasterIRQ
    sta $ffff
    lda #<nmiReturn
    sta $fffa
    lda #>nmiReturn
    sta $fffb

    // Select VIC bank zero, the character mode, and the first RAM charset.
    lda $dd02
    ora #3
    sta $dd02
    lda $dd00
    ora #3
    sta $dd00
    lda #$0b
    sta $d011
    lda #FILLED_MODE ? $18 : $08
    sta $d016
    .if (FILLED_MODE) {
        lda #6
        sta $d022
#if GLENZ || PAINTED || PONG || XOR_TEXTURE
        lda #3
#else
#if FAST_SOLID
        lda #5
#else
#if INTERLACED
        lda #5
#else
        lda #14
#endif
#endif
#endif
        sta $d023
    }
    lda #$18
    sta $d018
    lda #0
    sta $d020
    sta $d021
    sta $d015
    sta $d01a
    sta angleYaw
    sta anglePitch
    sta rasterTick
#if INTERLACED
    sta interlaceTerminalMarker
#endif
    lda #>CHARSET_B
    sta drawBufferHi

    // Every screen cell outside the canvas has black foreground and background.
    // All 256 glyphs remain available to the canvas; no blank glyph is reserved.
    ldx #0
    lda #0
!clearScreen:
    sta SCREEN,x
    sta SCREEN+$100,x
    sta SCREEN+$200,x
    sta SCREEN+$300,x
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    inx
    bne !clearScreen-

    .for (var row = 0; row < 16; row++) {
        .for (var column = 0; column < 16; column++) {
            lda #column * 16 + row
            sta SCREEN + (CANVAS_ROW + row) * 40 + CANVAS_COLUMN + column
#if GLENZ || PAINTED || PONG || XOR_TEXTURE
            lda #$09
#else
#if FAST_SOLID
            lda #$0c
#else
#if INTERLACED
            lda #$0c
#else
            lda #FILLED_MODE ? $0b : 3
#endif
#endif
#endif
            sta $d800 + (CANVAS_ROW + row) * 40 + CANVAS_COLUMN + column
        }
    }

#if FAST_SOLID
    // Reusable exact math tables are generated once while the display is blank.
    jsr fastInitRotationTables
    jsr fastInitProjectionTables
#endif
#if PAINTED
    jsr paintedInitProjection
#endif
#if PONG
    jsr pongInit
#endif
#if XOR_TEXTURE
    jsr hybridInit
#endif
    jsr clearCharsetA
    jsr clearCharsetB
    lda #$1b
    sta $d011

    // A tiny raster IRQ provides a real frame clock, including during rendering.
    // Swap in the upper border. Wireframe presents every frame; the filled
    // renderers use a larger budget for boundary generation and prefix fill.
    lda #0
    sta $d012
    lda #1
    sta $d019
    sta $d01a
    cli

    // Align the first render with the same upper-border deadline as later ones.
    // Without this, autostart's arbitrary raster phase shortens the first budget.
    lda rasterTick
!synchronize:
    cmp rasterTick
    beq !synchronize-

nextFrame:
    // Rendering begins at the upper-border frame clock. White measures all work;
    // black measures the remaining time before the next scheduled presentation.
#if !XOR_TEXTURE
#if FAST_SOLID || GLENZ || PAINTED || PONG || XOR_TEXTURE
    lda #0
#else
#if INTERLACED
    // Keep the visible experiment's border black throughout rendering.
    lda #0
#else
    lda #1
#endif
#endif
    sta $d020
#endif
    lda rasterTick
    clc
    adc #FRAME_TICKS
    sta presentationTick
#if FILLED
    jsr prepareFilledFrame
#else
    jsr clearDirtyRect
#endif
#if XOR_TEXTURE
    jsr hybridFrameGeometry
    jsr hybridCullFaces
#else
    jsr rotateCube
    jsr projectCube
    jsr cullFaces
#endif
    jsr drawCube

// Boundary markers are complete here. The filled build consumes its operands
// while writing charset pixels and resetting those operands.
boundariesReady:
#if FILLED
#if GOURAUD
    jsr gouraudFillFrame
#else
    jsr xorFill
#endif
#endif
#if XOR_TEXTURE
hybridBaseReady:
    jsr hybridTextureOverlay
#endif
#if TONAL
// The selected rows contain raw face IDs here; shade them before presentation.
tonalRawReady:
    jsr tonalShade
tonalShadedReady:
#endif

#if !XOR_TEXTURE
    lda #0
    sta $d020
#endif

// At this label the back buffer and projected vertices form one complete frame.
frameReady:
#if XOR_TEXTURE
    // Work may exceed the ordinary solid target's budget. Publish only on a
    // fresh upper-border IRQ after the complete overlay has finished.
    lda rasterTick
!hybridUpperBorder:
    cmp rasterTick
    beq !hybridUpperBorder-
#else
    lda rasterTick
    sec
    sbc presentationTick
    bmi frameReady
#endif
    lda drawBufferHi
    cmp #>CHARSET_A
    bne !showB+
    lda #$18
    sta $d018
    lda #>CHARSET_B
    sta drawBufferHi
    jmp framePresented
!showB:
    lda #$1a
    sta $d018
    lda #>CHARSET_A
    sta drawBufferHi
framePresented:
#if XOR_TEXTURE
hybridPresented:
    inc hybridPhase
    lda hybridPhase
    and #63
    sta hybridPhase
    jmp nextFrame
#endif
#if PONG
    jsr pongUpdate
#else
#if ICOSAHEDRON
#if FAST_SOLID
    // Two PAL ticks advance yaw by two and pitch by one, preserving speed.
    lda angleYaw
    clc
    adc #FRAME_TICKS
    sta angleYaw
    inc anglePitch
#else
#if GOURAUD
    // Preserve angular speed when the heavier lighting path uses more ticks.
    lda angleYaw
    clc
    adc #FRAME_TICKS
    sta angleYaw
    lda anglePitch
    clc
    adc #floor(FRAME_TICKS/2)
    sta anglePitch
    .if ((FRAME_TICKS & 1) != 0) {
        lda angleYaw
        and #1
        bne !pitchUnchanged+
        inc anglePitch
    }
#else
    // Three PAL ticks advance yaw by three and pitch alternately by one or two.
    // This preserves the cube's angular speed despite fewer presentations.
    lda angleYaw
    clc
    adc #3
    sta angleYaw
    inc anglePitch
    and #1
    bne !pitchUnchanged+
    inc anglePitch
#endif
#endif
#else
    inc angleYaw
    .if (FRAME_TICKS == 2) { inc angleYaw }
    // Keep the original rotation speed while doubling the presentation rate.
    lda angleYaw
    and #1
    bne !pitchUnchanged+
    inc anglePitch
#endif
#endif
!pitchUnchanged:
    jmp nextFrame

rasterIRQ:
    pha
    inc rasterTick
    lda #1
    sta $d019
    pla
nmiReturn:
    rti

clearCharsetA:
    lda #0
    FillPages(CHARSET_A, 8)
    rts
clearCharsetB:
    lda #0
    FillPages(CHARSET_B, 8)
    rts

#if GOURAUD
// Both row groups were rendered from the same vertices and lighting. Complete
// both back-buffer halves before the only display-bank flip at framePresented.
gouraudFillFrame:
    jsr xorFill
gouraudEvenFilled:
    jsr prepareFilledFrame
    jsr rememberBounds
    jsr xorFill
gouraudFrameFilled:
    rts
#endif

.import source "clear.asm"

// Q6 coefficients represent 1.0 as 64. Cube axis lengths are already scaled
// by HALF_SIZE, so the eight corners only need signed sums of these three axes.
// The transform is Rx(pitch) * Ry(yaw), applied to the original cube each frame.
rotateCube:
#if FAST_SOLID
    FastRotationCode()
#else
#if ICOSAHEDRON
    // Generic vertices use Ry followed by Rx. MultiplyScaled preserves Y,
    // allowing one compact indexed loop instead of unrolling 96 multiplies.
    ldx angleYaw
    lda sineUnit,x
    sta axisZX
    txa
    clc
    adc #64
    tax
    lda sineUnit,x
    sta axisXX
    ldx anglePitch
    lda sineUnit,x
    sta axisYZ
    txa
    clc
    adc #64
    tax
    lda sineUnit,x
    sta axisYY

    ldy #VERTEX_COUNT-1
!vertex:
    lda axisXX
    sta factor
    lda modelX,y
    jsr multiplyScaled
    sta objectYawX
    lda modelZ,y
    jsr multiplyScaled
    sta objectYawZ
    lda axisZX
    sta factor
    lda modelZ,y
    jsr multiplyScaled
    clc
    adc objectYawX
    sta rotatedX,y
    lda modelX,y
    jsr multiplyScaled
    sta objectTerm
    lda objectYawZ
    sec
    sbc objectTerm
    sta objectYawZ

    lda axisYY
    sta factor
    lda modelY,y
    jsr multiplyScaled
    sta objectPitchY
    lda objectYawZ
    jsr multiplyScaled
    sta objectPitchZ
    lda axisYZ
    sta factor
    lda objectYawZ
    jsr multiplyScaled
    sta objectTerm
    lda objectPitchY
    sec
    sbc objectTerm
    sta rotatedY,y
    lda modelY,y
    jsr multiplyScaled
    clc
    adc objectPitchZ
    sta rotatedZ,y
    dey
    bmi !done+
    jmp !vertex-
!done:
    rts
#else
    ldx angleYaw
    lda sineSize,x
    sta axisZX
    txa
    clc
    adc #64
    tax
    lda sineSize,x
    sta axisXX

    ldx anglePitch
    lda sineUnit,x
    sta factor
    lda sineSize,x
    sta axisYZ
    lda axisZX
    jsr multiplyScaled
    sta axisXY
    lda axisXX
    jsr multiplyScaled
    eor #$ff
    clc
    adc #1
    sta axisZY

    lda anglePitch
    clc
    adc #64
    tax
    lda sineUnit,x
    sta factor
    lda sineSize,x
    sta axisYY
    lda axisZX
    jsr multiplyScaled
    eor #$ff
    clc
    adc #1
    sta axisXZ
    lda axisXX
    jsr multiplyScaled
    sta axisZZ

    .for (var vertex = 0; vertex < 8; vertex++) {
        SumAxes(vertex, axisXX, axisYX, axisZX)
        sta rotatedX + vertex
        SumAxes(vertex, axisXY, axisYY, axisZY)
        sta rotatedY + vertex
        SumAxes(vertex, axisXZ, axisYZ, axisZZ)
        sta rotatedZ + vertex
    }
    rts
#endif
#endif

.macro SumAxes(vertex, xAxis, yAxis, zAxis) {
    lda #0
    .if ((vertex & 1) != 0) { clc; adc xAxis } else { sec; sbc xAxis }
    .if ((vertex & 2) != 0) { clc; adc yAxis } else { sec; sbc yAxis }
    .if ((vertex & 4) != 0) { clc; adc zAxis } else { sec; sbc zAxis }
}

projectCube:
#if FAST_SOLID
    FastProjectionCode()
#else
    // Constant vertex addresses remove the index loop; inline multiplication
    // avoids sixteen JSR/RTS pairs in this hot path.
    .for (var vertex = 0; vertex < PROJECT_VERTEX_COUNT; vertex++) {
        lda rotatedZ+vertex
        clc
        adc #64
        tax
        lda depthFactors,x
        sta factor
        lda rotatedX+vertex
        MultiplyScaled()
#if ICOSAHEDRON
        tax
        lda icosahedronZoom,x
#endif
        clc
        adc #64
        .if (FILLED_MODE) { lsr }
        sta projectedX+vertex
        lda rotatedY+vertex
        MultiplyScaled()
#if ICOSAHEDRON
        tax
        lda icosahedronZoom,x
#endif
        sta multiplicand
        lda #64
        sec
        sbc multiplicand
        sta projectedY+vertex
    }
    jsr rememberBounds
    rts
#endif

// Return approximately A * factor / 64. A and factor are signed bytes; Y survives.
// Q(n)=floor(n*n/256), so Q(a+b)-Q(a-b) approximates a*b/64 within one unit.
// Inputs in this scene guarantee both a+b and a-b stay within signed byte range.
multiplyScaled:
    MultiplyScaled()
    rts

.macro MultiplyScaled() {
    sta multiplicand
    clc
    adc factor
    tax
    lda quarterSquares,x
    sta squareSum
    lda multiplicand
    sec
    sbc factor
    tax
    lda squareSum
    sec
    sbc quarterSquares,x
}

#if FILLED
.label drawCube = drawCubeBoundaries
#else
.macro DrawVisibleEdge(first, last) {
    .var adjacentFaces = 0
    .for (var axis = 0; axis < 3; axis++) {
        .if (((first ^ last) & (1 << axis)) == 0) {
            .eval adjacentFaces = adjacentFaces | (1 << (axis * 2 + ((first >> axis) & 1)))
        }
    }
    lda visibleFaces
    and #adjacentFaces
    beq !hidden+
    lda projectedX+first
    sta lineX0
    lda projectedY+first
    sta lineY0
    lda projectedX+last
    sta lineX1
    lda projectedY+last
    sta lineY1
    jsr drawLine
!hidden:
}

drawCube:
    // Each differing coordinate bit identifies one cube edge. Generate each
    // edge once, with constant vertex addresses and adjacent-face masks.
    .for (var vertex = 0; vertex < 8; vertex++) {
        .for (var axis = 0; axis < 3; axis++) {
            .if ((vertex & (1 << axis)) == 0) {
                DrawVisibleEdge(vertex, vertex ^ (1 << axis))
            }
        }
    }
    rts
#endif

angleYaw:         .byte 0
anglePitch:       .byte 0
rasterTick:       .byte 0
presentationTick: .byte 0
drawBufferHi:     .byte >CHARSET_B
axisXX: .byte 0
axisXY: .byte 0
axisXZ: .byte 0
axisYX: .byte 0
axisYY: .byte 0
axisYZ: .byte 0
axisZX: .byte 0
axisZY: .byte 0
axisZZ: .byte 0
#if ICOSAHEDRON
objectYawX: .byte 0
objectYawZ: .byte 0
objectTerm: .byte 0
objectPitchY: .byte 0
objectPitchZ: .byte 0
objectFaceIndex: .byte 0
objectEdgeIndex: .byte 0
#endif
rotatedX:   .fill VERTEX_COUNT, 0
rotatedY:   .fill VERTEX_COUNT, 0
rotatedZ:   .fill VERTEX_COUNT, 0
projectedX: .fill VERTEX_COUNT, 0
projectedY: .fill VERTEX_COUNT, 0
bitMasks: .byte $80,$40,$20,$10,$08,$04,$02,$01

.align $100
sineUnit:
    .fill 256, round(SCALE * sin(toRadians(i * 360 / 256))) & $ff
sineSize:
#if !FAST_SOLID
#if GOURAUD
    GouraudLightingPage()
    .assert "Gouraud lighting page size", *-sineSize, 256
#else
#if TONAL
    // The icosahedron never reads this cube-only sine table. Reuse its page
    // without moving the remaining tables or the two charset buffers.
    TonalShadeLowPage()
    .assert "Tonal low page size", *-sineSize, 256
#else
    .fill 256, round(HALF_SIZE * sin(toRadians(i * 360 / 256))) & $ff
#endif
#endif
#endif
quarterSquares:
    .fill 256, floor(pow(i < 128 ? i : i - 256, 2) / 256)
depthFactors:
    .fill 128, round(FOCAL_LENGTH * SCALE / (CAMERA_DISTANCE + i - 64))
#if INTERLACED
// The selected field occupies two pages of each four-page fill column.
// X contains crossingY | (fieldParity<<7). Even crossing127 is past row126;
// page$FF routes that terminal marker to the separately owned discard byte.
.align $100
xorOperandPage:
    .fill 256, i == 127 ? >interlaceTerminalMarker : floor(floor(((i & 127)+1-floor(i/128))/2)/32)+floor(i/128)*2
xorOperandPageEnd:
    .assert "Interlaced row page alignment", xorOperandPage & $ff, 0
    .assert "Interlaced row page table size", xorOperandPageEnd-xorOperandPage, 256
#endif
#if FAST_SOLID
    FastPairedCullCode()
    FastBoundsCode()
#endif
#if PAINTED
    PaintedModelData()
    PaintedPrepareCode()
#endif
#if PONG
    PongModelData()
    PongPrepareCode()
#endif
#if XOR_TEXTURE
    HybridRuntimeLowCode()
#endif
codeEnd:
    .errorif * > CHARSET_A, "Program overlaps the first charset"

#if XOR_TEXTURE
// Stage the live high-RAM core inside the two not-yet-used VIC charsets.
* = $2000 "Hybrid high-RAM runtime staging"
hybridStageA:
.pseudopc $e400 {
hybridRuntimeStart:
    .import source "../experiments/textured-cube/ortho-geometry.asm"
    .import source "../experiments/textured-cube/xor-hybrid/sampler.asm"
hybridRuntimeEnd:
}
hybridStageAEnd:
    .errorif hybridStageAEnd > $3000, "Hybrid runtime staging exceeds both charsets"
#endif

// Generated line kernels trade spare RAM for fewer instructions per pixel.
// Keep them above the two VIC charsets, away from the BASIC loader and tables.
* = $3000 "Generated line drawing"
#if FILLED
#if GLENZ
    GlenzModelData()
#endif
#if ICOSAHEDRON
    IcosahedronModelData()
#endif
.import source "cull.asm"
.import source "xor-fill.asm"
#if PONG
    PongRuntimeCode()
#endif
#else
.import source "lines.asm"
.import source "cull.asm"
#endif
#if XOR_TEXTURE
// This plain-cube target leaves the last1KiB below I/O free after the actual
// XOR fill banks. Its second startup-only chunk becomes runtime scratch RAM.
* = $cc01 "Hybrid texture-builder staging"
hybridStageB:
.pseudopc hybridRuntimeEnd {
hybridBuilderRuntimeStart:
    .import source "../experiments/textured-cube/texture-builder.asm"
plasmaWave:
    .fill 256,round(16+15*sin(i*2*PI/256))
hybridBuilderRuntimeEnd:
}
hybridStageBEnd:
    .errorif hybridStageBEnd > $d000, "Hybrid builder staging reaches I/O"
    .errorif hybridBuilderRuntimeEnd > $fd00, "Hybrid runtime exceeds high-RAM allocation"
#endif
    .errorif * > (FILLED_MODE ? $d000 : $a000), "Generated line code exceeds its reserved RAM"
