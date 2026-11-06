// A real-time wireframe cube for a stock PAL C64.
// The filled entry point reuses the runtime with a multicolor XOR edge renderer.
// Kick Assembler generates the lookup tables, not animation frames.
// Screen codes run down columns, making a 128x128 canvas in each 2 KB charset.

.const SCREEN = $0400
.const CHARSET_A = $2000
.const CHARSET_B = $2800
.const HALF_SIZE = 24
.const SCALE = 64
.const CAMERA_DISTANCE = 144
.const FOCAL_LENGTH = 128
.const CANVAS_ROW = 4
.const CANVAS_COLUMN = 12
.const FRAME_TICKS = FILLED_MODE ? 2 : 1

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
        lda #14
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
            lda #FILLED_MODE ? $0b : 3
            sta $d800 + (CANVAS_ROW + row) * 40 + CANVAS_COLUMN + column
        }
    }

    jsr clearCharsetA
    jsr clearCharsetB
    lda #$1b
    sta $d011

    // A tiny raster IRQ provides a real frame clock, including during rendering.
    // Swap in the upper border. Wireframe presents every frame; the filled
    // renderer has a two-frame budget for boundary generation and prefix fill.
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
    lda #1
    sta $d020
    lda rasterTick
    clc
    adc #FRAME_TICKS
    sta presentationTick
    jsr clearDirtyRect
    jsr rotateCube
    jsr projectCube
    jsr cullFaces
    jsr drawCube

// Boundary markers are complete here; the filled build integrates them in place.
boundariesReady:
#if FILLED
    jsr xorFill
#endif

    lda #0
    sta $d020

// At this label the back buffer and projected vertices form one complete frame.
frameReady:
    lda rasterTick
    sec
    sbc presentationTick
    bmi frameReady
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
    inc angleYaw
    .if (FRAME_TICKS == 2) { inc angleYaw }
    // Keep the original rotation speed while doubling the presentation rate.
    lda angleYaw
    and #1
    bne !pitchUnchanged+
    inc anglePitch
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

.import source "clear.asm"

// Q6 coefficients represent 1.0 as 64. Cube axis lengths are already scaled
// by HALF_SIZE, so the eight corners only need signed sums of these three axes.
// The transform is Rx(pitch) * Ry(yaw), applied to the original cube each frame.
rotateCube:
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

.macro SumAxes(vertex, xAxis, yAxis, zAxis) {
    lda #0
    .if ((vertex & 1) != 0) { clc; adc xAxis } else { sec; sbc xAxis }
    .if ((vertex & 2) != 0) { clc; adc yAxis } else { sec; sbc yAxis }
    .if ((vertex & 4) != 0) { clc; adc zAxis } else { sec; sbc zAxis }
}

projectCube:
    // Constant vertex addresses remove the index loop; inline multiplication
    // avoids sixteen JSR/RTS pairs in this hot path.
    .for (var vertex = 0; vertex < 8; vertex++) {
        lda rotatedZ+vertex
        clc
        adc #64
        tax
        lda depthFactors,x
        sta factor
        lda rotatedX+vertex
        MultiplyScaled()
        clc
        adc #64
        .if (FILLED_MODE) { lsr }
        sta projectedX+vertex
        lda rotatedY+vertex
        MultiplyScaled()
        sta multiplicand
        lda #64
        sec
        sbc multiplicand
        sta projectedY+vertex
    }
    jsr rememberBounds
    rts

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
rotatedX:   .fill 8, 0
rotatedY:   .fill 8, 0
rotatedZ:   .fill 8, 0
projectedX: .fill 8, 0
projectedY: .fill 8, 0
bitMasks: .byte $80,$40,$20,$10,$08,$04,$02,$01

.align $100
sineUnit:
    .fill 256, round(SCALE * sin(toRadians(i * 360 / 256))) & $ff
sineSize:
    .fill 256, round(HALF_SIZE * sin(toRadians(i * 360 / 256))) & $ff
quarterSquares:
    .fill 256, floor(pow(i < 128 ? i : i - 256, 2) / 256)
depthFactors:
    .fill 128, round(FOCAL_LENGTH * SCALE / (CAMERA_DISTANCE + i - 64))
codeEnd:
    .errorif * > CHARSET_A, "Program overlaps the first charset"

// Generated line kernels trade spare RAM for fewer instructions per pixel.
// Keep them above the two VIC charsets, away from the BASIC loader and tables.
* = $3000 "Generated line drawing"
#if FILLED
.import source "xor-fill.asm"
#else
.import source "lines.asm"
#endif
.import source "cull.asm"
    .errorif * > $a000, "Generated line code exceeds its reserved RAM"
