// Twelve independent pentagons on a truncated icosahedron. The twenty hexagons
// are black and omitted. Opposite normal pairs guarantee at most six visible
// faces in this orthographic projection. All geometry transforms run on the C64.
.const SPRITES_A = $2000
.const SPRITES_B = $2200
.const MARKERS = $2400
.const FRAME_TICKS = 2
.const FACE_COUNT = 12
.const ACTIVE_SPRITES = 6
.label spritePointer = $f0
.label divisionPointer = $f2
.label factor = $f4
.label multiplicand = $f5
.label squareSum = $f6
.label edgeX = $f7
.label edgeEndX = $f8
.label edgeY = $f9
.label edgeDX = $fa
.label edgeError = $fb
.label edgeStep = $fc
.label edgeRemainder = $fd

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
    lda $dd02
    ora #3
    sta $dd02
    lda $dd00
    ora #3
    sta $dd00
    // DEN stays low across line 48 to suppress badlines. The line-49 IRQ sets
    // it again before the vertical border opens at line 51, exposing sprites.
    lda #$0b
    sta $d011
    lda #$08
    sta $d016
    lda #$14
    sta $d018
    lda #$ff
    sta $d017
    sta $d01d
    lda #0
    sta $d020
    sta $d021
    sta $d015
    sta $d01c
    sta $d01b
    sta $d010
    sta angleYaw
    sta anglePitch
    sta rasterTick
    sta ready
    sta drawBank
    sta frameNumber
    sta frameNumber+1
    sta overflowCount
    sta missedDeadlines
    ldx #0
!blackScreen:
    sta $0400,x
    sta $0500,x
    sta $0600,x
    sta $0700,x
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    inx
    bne !blackScreen-
    lda #FRAME_TICKS
    sta presentationCountdown
    lda #$ff
    sta $dc04
    sta $dc05
    lda #$11
    sta $dc0e
    jsr clearMarkers
    lda #0
    sta $d012
    lda #1
    sta $d019
    sta $d01a
    cli

nextFrame:
    lda $dc04
    sta timerStart
    lda $dc05
    sta timerStart+1
    jsr prepareMatrix
    jsr clearMarkers
    lda #0
    sta usedSprites
    sta faceIndex
    lda drawBank
    asl
    asl
    asl
    sta metadataBase
    tax
    lda #$ff
    .for (var slot=0; slot<8; slot++) { sta slotFace+slot,x }

!face:
    jsr faceDepth
    bpl !hidden+
    sta normalDepth
    jsr projectFace
    jsr drawFace
!hidden:
    inc faceIndex
    lda faceIndex
    cmp #FACE_COUNT
    bne !face-
    lda drawBank
    bne !fillB+
    jsr fillA
    jmp !filled+
!fillB:
    jsr fillB
!filled:
    lda $dc04
    sta timerEnd
    lda $dc05
    sta timerEnd+1
    lda timerStart
    sec
    sbc timerEnd
    sta renderCycles
    lda timerStart+1
    sbc timerEnd+1
    sta renderCycles+1
    lda #1
    sta ready
frameReady:
    lda ready
    bne frameReady
    lda drawBank
    eor #1
    sta drawBank
    lda angleYaw
    clc
    adc #2
    sta angleYaw
    inc anglePitch
    jmp nextFrame

rasterIRQ:
    pha
    txa
    pha
    tya
    pha
    lda $d012
    cmp #49
    beq !openBorder+
    lda #$0b
    sta $d011
    lda #49
    sta $d012
    inc rasterTick
    dec presentationCountdown
    bne !return+
    lda #FRAME_TICKS
    sta presentationCountdown
    lda ready
    beq !missed+
    jsr presentSprites
    lda #0
    sta ready
    inc frameNumber
    bne framePresented
    inc frameNumber+1
framePresented:
    jmp !return+
!missed:
    inc missedDeadlines
    jmp !return+
!openBorder:
    lda #$1b
    sta $d011
    lda #0
    sta $d012
!return:
    lda #1
    sta $d019
    pla
    tay
    pla
    tax
    pla
nmiReturn:
    rti

presentSprites:
    lda drawBank
    asl
    asl
    asl
    sta shownMetadataBase
    tax
    lda drawBank
    asl
    asl
    asl
    clc
    adc #SPRITES_A/64
    sta presentPointer
    .for (var slot=0; slot<8; slot++) {
        lda slotX+slot,x
        sta $d000+slot*2
        lda slotY+slot,x
        sta $d001+slot*2
        lda slotColor+slot,x
        sta $d027+slot
        lda presentPointer
        clc
        adc #slot
        sta $07f8+slot
    }
    ldx usedSprites
    lda enableMasks,x
    sta $d015
    rts

// Q6 rotation matrix: Ry(yaw), then Rx(pitch). Only the normal needs Z.
prepareMatrix:
    ldx angleYaw
    lda sine,x
    sta axisXZ
    lda cosine,x
    sta axisXX
    ldx anglePitch
    lda sine,x
    sta axisZY
    sta factor
    lda cosine,x
    sta axisYY
    lda axisXZ
    Multiply()
    sta axisYX
    lda axisXX
    Multiply()
    eor #$ff
    clc
    adc #1
    sta axisYZ
    lda axisYY
    sta factor
    lda axisXZ
    Multiply()
    eor #$ff
    clc
    adc #1
    sta axisZX
    lda axisXX
    Multiply()
    sta axisZZ
    rts

faceDepth:
    ldy faceIndex
    lda axisZX
    sta factor
    lda normalX,y
    Multiply()
    sta pointTerm
    lda axisZY
    sta factor
    lda normalY,y
    Multiply()
    clc
    adc pointTerm
    sta pointTerm
    lda axisZZ
    sta factor
    lda normalZ,y
    Multiply()
    clc
    adc pointTerm
    rts

projectFace:
    ldx faceIndex
    lda faceOffsets,x
    tay
    lda #0
    sta maxX
    sta maxY
    lda #$ff
    sta minX
    sta minY
    ldx #0
!point:
    stx pointIndex
    lda axisXX
    sta factor
    lda modelX,y
    Multiply()
    sta pointTerm
    lda axisXZ
    sta factor
    lda modelZ,y
    Multiply()
    clc
    adc pointTerm
    clc
    adc #64
    ldx pointIndex
    sta localX,x
    sta projectedX,y
    cmp minX
    bcs !notMinX+
    sta minX
!notMinX:
    cmp maxX
    bcc !notMaxX+
    sta maxX
!notMaxX:
    lda axisYX
    sta factor
    lda modelX,y
    Multiply()
    sta pointTerm
    lda axisYY
    sta factor
    lda modelY,y
    Multiply()
    clc
    adc pointTerm
    sta pointTerm
    lda axisYZ
    sta factor
    lda modelZ,y
    Multiply()
    clc
    adc pointTerm
    sta pointTerm
    lda #64
    sec
    sbc pointTerm
    ldx pointIndex
    sta localY,x
    sta projectedY,y
    cmp minY
    bcs !notMinY+
    sta minY
!notMinY:
    cmp maxY
    bcc !notMaxY+
    sta maxY
!notMaxY:
    iny
    inx
#if GOLDEN_PENTAGON
    iny
    inx
    cpx #6
#else
    cpx #5
#endif
    beq !done+
    jmp !point-
!done:
#if GOLDEN_PENTAGON
    // A regular pentagon obeys P1=P0+k*(P2-P4), P3=P4+k*(P2-P0),
    // where k=1/phi. Three well-separated corners keep rounding error bounded.
    // Project only three corners. Four small constant-multiply lookups recover
    // the remaining two; pixel rounding introduces a bounded shape difference.
    ReconstructPentagon(localX, projectedX)
    ReconstructPentagon(localY, projectedY)
    .for (var point=1; point<4; point+=2) {
        lda localX+point
        cmp minX
        bcs !notMinX+
        sta minX
!notMinX:
        cmp maxX
        bcc !notMaxX+
        sta maxX
!notMaxX:
        lda localY+point
        cmp minY
        bcs !notMinY+
        sta minY
!notMinY:
        cmp maxY
        bcc !notMaxY+
        sta maxY
!notMaxY:
    }
#endif
    rts

#if GOLDEN_PENTAGON
.macro ReconstructPentagon(local, projected) {
    ldx faceIndex
    lda faceOffsets,x
    clc
    adc #1
    tay
    lda local+2
    sec
    sbc local+4
    tax
    lda goldenRatio,x
    clc
    adc local
    sta local+1
    sta projected,y
    iny
    iny
    lda local+2
    sec
    sbc local
    tax
    lda goldenRatio,x
    clc
    adc local+4
    sta local+3
    sta projected,y
}
#endif

drawFace:
    // The generator/verifier proves these bounds. Keep guards for experiments.
    lda maxX
    sec
    sbc minX
    cmp #24
    bcs !overflow+
    lda maxY
    sec
    sbc minY
    cmp #21
    bcs !overflow+
    lda usedSprites
    cmp #8
    bcc !fits+
!overflow:
    inc overflowCount
    rts
!fits:
    clc
    adc metadataBase
    tax
    lda faceIndex
    sta slotFace,x
    lda minX
    asl
    clc
    adc #56
    sta slotX,x
    lda minY
    asl
    clc
    adc #22
    sta slotY,x
    lda #5
    ldy normalDepth
    cpy #$f4
    bcs !color+
    lda #13
    cpy #$e8
    bcs !color+
    lda #1
!color:
    sta slotColor,x
    ldx usedSprites
    lda spriteLow,x
    sta facePointerLow
    txa
    lsr
    lsr
    clc
    adc #>MARKERS
    sta spritePointer+1
    ldx #4
!local:
    lda localX,x
    sec
    sbc minX
    sta localX,x
    lda localY,x
    sec
    sbc minY
    sta localY,x
    dex
    bpl !local-
    lda #0
    sta polygonEdge
!edge:
    ldx polygonEdge
    lda localX,x
    sta x0
    lda localY,x
    sta y0
    inx
    cpx #5
    bne !next+
    ldx #0
!next:
    lda localX,x
    sta x1
    lda localY,x
    sta y1
    jsr drawBoundary
    inc polygonEdge
    lda polygonEdge
    cmp #5
    bne !edge-
    inc usedSprites
    rts

// For every integer X in [left,right), toggle exactly one crossing at ceil(Y).
// Vertical edges are ignored. This endpoint rule prevents corner parity leaks.
drawBoundary:
    lda x0
    cmp x1
    bcc !ordered+
    bne !swap+
    rts
!swap:
    ldx x1
    sta x1
    stx x0
    lda y0
    ldx y1
    sta y1
    stx y0
!ordered:
    lda x0
    sta edgeX
    tax
    lda byteColumns,x
    clc
    adc facePointerLow
    sta spritePointer
    lda x1
    sta edgeEndX
    sec
    sbc x0
    sta edgeDX
    lda y1
    sec
    sbc y0
    clc
    adc #20
    tax
    lda divisionLow,x
    sta divisionPointer
    lda divisionHigh,x
    sta divisionPointer+1
    ldy edgeDX
    lda (divisionPointer),y
    sta edgeRemainder
    lda divisionPointer+1
    clc
    adc #4
    sta divisionPointer+1
    lda (divisionPointer),y
    sta edgeStep
    lda divisionPointer+1
    clc
    adc #4
    sta divisionPointer+1
    lda (divisionPointer),y
    sta edgeError
    lda y0
    sta edgeY
    ldx edgeX
!pixel:
    ldy edgeY
    lda bitMasks,x
    eor (spritePointer),y
    sta (spritePointer),y
    inx
    cpx edgeEndX
    beq !done+
    // Advance a byte column only when X crosses a multiple of eight.
    txa
    and #7
    bne !sameByte+
    lda spritePointer
    clc
    adc #21
    sta spritePointer
!sameByte:
    lda edgeError
    clc
    adc edgeRemainder
    sta edgeError
    lda edgeY
    adc edgeStep
    sta edgeY
    jmp !pixel-
!done:
    rts

// A*factor/64 through quarter squares. Signed inputs and Y survive the lookup.
.macro Multiply() {
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

angleYaw: .byte 0
anglePitch: .byte 0
rasterTick: .byte 0
ready: .byte 0
drawBank: .byte 0
presentationCountdown: .byte FRAME_TICKS
frameNumber: .word 0
overflowCount: .byte 0
missedDeadlines: .byte 0
timerStart: .word 0
timerEnd: .word 0
renderCycles: .word 0
usedSprites: .byte 0
faceIndex: .byte 0
normalDepth: .byte 0
metadataBase: .byte 0
shownMetadataBase: .byte 0
presentPointer: .byte 0
facePointerLow: .byte 0
pointIndex: .byte 0
pointTerm: .byte 0
polygonEdge: .byte 0
x0: .byte 0
y0: .byte 0
x1: .byte 0
y1: .byte 0
minX: .byte 0
maxX: .byte 0
minY: .byte 0
maxY: .byte 0
axisXX: .byte 0
axisXZ: .byte 0
axisYX: .byte 0
axisYY: .byte 0
axisYZ: .byte 0
axisZX: .byte 0
axisZY: .byte 0
axisZZ: .byte 0
localX: .fill 5, 0
localY: .fill 5, 0
projectedX: .fill 60, 0
projectedY: .fill 60, 0
slotX: .fill 16, 0
slotY: .fill 16, 0
slotColor: .fill 16, 0
slotFace: .fill 16, $ff
enableMasks: .byte 0,1,3,7,15,31,63,127,255
spriteLow: .byte 0,64,128,192,0,64,128,192
faceOffsets: .fill 12, i*5
bitMasks: .fill 24, $80 >> (i&7)
byteColumns: .fill 24, floor(i/8)*21
.import source "build/model.asm"

.align $100
sine: .fill 256, round(64*sin(toRadians(i*360/256))) & $ff
cosine: .fill 256, round(64*cos(toRadians(i*360/256))) & $ff
quarterSquares: .fill 256, floor(pow(i<128 ? i : i-256,2)/256)
#if GOLDEN_PENTAGON
goldenRatio: .fill 256, round((i<128 ? i : i-256)*(sqrt(5)-1)/2) & $ff
#endif
.errorif * > SPRITES_A, "Runtime overlaps sprite buffers"

* = SPRITES_A "Two sprite sets and column-major crossing markers"
.fill 1024, 0
.fill ACTIVE_SPRITES*64, 0

* = $2800 "Unrolled sprite clearing and vertical XOR filling"
.macro ClearSprites(base) {
    lda #0
    .for (var sprite=0; sprite<ACTIVE_SPRITES; sprite++) {
        .for (var offset=0; offset<63; offset++) { sta base+sprite*64+offset }
    }
    rts
}
.macro FillSprites(base) {
    .for (var sprite=0; sprite<ACTIVE_SPRITES; sprite++) {
        .for (var column=0; column<3; column++) {
            lda #0
            .for (var row=0; row<21; row++) {
                eor MARKERS+sprite*64+column*21+row
                sta base+sprite*64+row*3+column
            }
        }
    }
    rts
}
clearMarkers: ClearSprites(MARKERS)
fillA: FillSprites(SPRITES_A)
fillB: FillSprites(SPRITES_B)
.align $400
divisionFractions: .import binary "build/edge-fractions.bin"
.align $400
divisionSteps: .import binary "build/edge-steps.bin"
.align $400
divisionBiases: .import binary "build/edge-biases.bin"
.assert "Edge table stride", divisionSteps-divisionFractions, 1024
.assert "Bias table stride", divisionBiases-divisionSteps, 1024
divisionLow: .fill 41, <(divisionFractions+i*24)
divisionHigh: .fill 41, >(divisionFractions+i*24)
programEnd:
.errorif * > $d000, "Program reaches I/O"
