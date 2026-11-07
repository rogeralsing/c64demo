// Independent soccer-ball patches. The hexagon build selects the eight largest
// visible hexagons from twenty; other surfaces use the bitmap. Pentagon comparison
// builds retain twelve patches. All geometry transforms run on the C64.
.import source "build/scene.asm"
.const SPRITES_A = $0c00
.const SPRITES_B = $0e00
.const MARKERS = $1800
#if HEXAGON
.const FRAME_TICKS = 3
.const FACE_COUNT = 20
.const ACTIVE_SPRITES = 8
.const VERTICES_PER_FACE = 6
.const MODEL_POINTS_PER_FACE = 6
#else
.const FRAME_TICKS = 2
.const FACE_COUNT = 12
.const ACTIVE_SPRITES = 6
.const VERTICES_PER_FACE = 5
.const MODEL_POINTS_PER_FACE = 5
#endif
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

BasicUpstart2(bootstrap)

// Enter RAM beneath the KERNAL only after disabling ROM reads. Keep the VIC's
// $1000..$1fff character-ROM window free of displayed sprite definitions.
bootstrap:
    sei
    lda #$35
    sta $01
    jmp start

* = $e000 "Runtime in RAM beneath KERNAL ROM"

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
    // Standard multicolor bitmap at $2000, screen attributes at $0400, bank zero.
    lda #$3b
    sta $d011
    lda #$18
    sta $d016
    lda #$18
    sta $d018
    lda #$ff
    sta $d017
    sta $d01d
    sta $d01b
    lda #0
    sta $d020
    sta $d021
    sta $d015
    sta $d01c
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
    lda backgroundColors,x
    sta $d800,x
    lda backgroundColors+$100,x
    sta $d900,x
    lda backgroundColors+$200,x
    sta $da00,x
    lda backgroundColors+$300,x
    sta $db00,x
    inx
    bne !blackScreen-
    // Copy 1000 bitmap color cells. The padded tail also initializes sprite
    // pointers; each presentation replaces the eight pointers before enabling.
    .for (var page=0; page<4; page++) {
        ldx #0
!attributes:
        lda backgroundScreen+page*$100,x
        sta $0400+page*$100,x
#if HEXAGON
        sta $0800+page*$100,x
#endif
        inx
        bne !attributes-
    }
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

#if HEXAGON
    jsr renderHexagons
#else
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
#endif
    lda drawBank
    bne !fillB+
    jsr fillA
    jmp !filled+
!fillB:
    jsr fillB
!filled:
#if HEXAGON
    jsr prepareGapColors
#endif
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
    adc #6
    sta angleYaw
    inc anglePitch
    inc anglePitch
    inc anglePitch
    jmp nextFrame

rasterIRQ:
    pha
    txa
    pha
    tya
    pha
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
#if HEXAGON
    lda drawBank
    asl
    asl
    asl
    asl
    clc
    adc #$18
    sta $d018
#endif
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
#if HEXAGON
        sta $0bf8+slot
#endif
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

#if !HEXAGON
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
#endif

#if HEXAGON
// Equal-size faces under orthographic projection have area proportional to
// facing depth. Hide only the weakest one or two when more than eight face us.
selectLargestHexagons:
    lda #0
    sta visibleFaces
    sta weakestDepth
    sta secondWeakestDepth
    .for (var face=0; face<FACE_COUNT; face++) {
        lda faceDepths+face
        bpl !hidden+
        inc visibleFaces
        cmp weakestDepth
        bcc !second+
        ldx weakestDepth
        stx secondWeakestDepth
        ldx weakestFace
        stx secondWeakestFace
        sta weakestDepth
        lda #face
        sta weakestFace
        jmp !hidden+
!second:
        cmp secondWeakestDepth
        bcc !hidden+
        sta secondWeakestDepth
        lda #face
        sta secondWeakestFace
!hidden:
    }
    lda visibleFaces
    cmp #9
    bcc !done+
    ldx weakestFace
    lda #0
    sta faceDepths,x
    lda visibleFaces
    cmp #10
    bcc !done+
    ldx secondWeakestFace
    lda #0
    sta faceDepths,x
!done:
    rts
#endif

projectFace:
#if HEXAGON
    // All adjoining faces fetch the same projected vertices. Derive each
    // sprite's bounds before translating those global coordinates to local.
    ldx faceIndex
    lda faceOffsets,x
    sta faceVertexStart
    tay
    lda hexFaceVertices,y
    tax
    lda sharedX,x
    sta minX
    sta maxX
    lda sharedY,x
    sta minY
    sta maxY
    iny
    .for (var point=1; point<VERTICES_PER_FACE; point++) {
        lda hexFaceVertices,y
        tax
        lda sharedX,x
        cmp minX
        bcs !notMinX+
        sta minX
        bcc !notMaxX+
!notMinX:
        cmp maxX
        bcc !notMaxX+
        sta maxX
!notMaxX:
        lda sharedY,x
        cmp minY
        bcs !notMinY+
        sta minY
        bcc !notMaxY+
!notMinY:
        cmp maxY
        bcc !notMaxY+
        sta maxY
!notMaxY:
        iny
    }
    ldy faceVertexStart
    .for (var point=0; point<VERTICES_PER_FACE; point++) {
        lda hexFaceVertices,y
        tax
        lda sharedX,x
        sec
        sbc minX
        sta localX+point
        lda sharedY,x
        sec
        sbc minY
        sta localY+point
        iny
    }
    rts
#else
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
#endif

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
    adc #SCENE_X_BIAS
    sta slotX,x
    lda minY
    asl
    clc
    adc #SCENE_Y_BIAS
    sta slotY,x
    // Fade from the silhouette toward the face looking straight at the camera.
    // Add brown below the existing four gray brightness bands.
    lda normalDepth
    eor #$ff
    tay
    lda spriteFadeColors,y
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
    sta facePointerHigh
#if !HEXAGON
    ldx #VERTICES_PER_FACE-1
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
#endif
#if HEXAGON
    .for (var edge=0; edge<VERTICES_PER_FACE; edge++) {
        .var next = edge==VERTICES_PER_FACE-1 ? 0 : edge+1
        lda localX+edge
        sta x0
        lda localY+edge
        sta y0
        lda localX+next
        sta x1
        lda localY+next
        sta y1
        jsr drawBoundary
    }
#else
    lda #0
    sta polygonEdge
!edge:
    ldx polygonEdge
    lda localX,x
    sta x0
    lda localY,x
    sta y0
    inx
    cpx #VERTICES_PER_FACE
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
    cmp #VERTICES_PER_FACE
    bne !edge-
#endif
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
    // Short-edge crossing curves replace the fractional step in the hot loop.
    // The +20 sample bias permits unsigned Y indexing for either slope sign.
    lda x0
    sta edgeX
    tax
    lda facePointerHigh
    sta spritePointer+1
    lda byteColumns,x
    clc
    adc facePointerLow
    clc
    adc y0
    sec
    sbc #20
    sta spritePointer
    bcs !pointerReady+
    dec spritePointer+1
!pointerReady:
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
    lda curveRowsLow,x
    sta divisionPointer
    lda curveRowsHigh,x
    sta divisionPointer+1
    ldy edgeDX
    lda (divisionPointer),y
    sta curveRead+1
    lda divisionPointer+1
    clc
    adc #4
    sta divisionPointer+1
    lda (divisionPointer),y
    sta curveRead+2
    lda curveRead+1
    sec
    sbc x0
    sta curveRead+1
    bcs !curveReady+
    dec curveRead+2
!curveReady:
    ldx edgeX
!pixel:
curveRead:
    ldy $ffff,x
    lda bitMasks,x
    eor (spritePointer),y
    sta (spritePointer),y
    inx
    cpx edgeEndX
    beq !done+
    txa
    and #7
    bne !sameByte+
    lda spritePointer
    clc
    adc #21
    sta spritePointer
    bcc !sameByte+
    inc spritePointer+1
!sameByte:
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
facePointerHigh: .byte 0
pointIndex: .byte 0
pointTerm: .byte 0
faceVertexStart: .byte 0
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
localX: .fill VERTICES_PER_FACE, 0
localY: .fill VERTICES_PER_FACE, 0
#if HEXAGON
sharedX: .fill 60, 0
sharedY: .fill 60, 0
faceDepths: .fill FACE_COUNT, 0
visibleFaces: .byte 0
weakestDepth: .byte 0
secondWeakestDepth: .byte 0
weakestFace: .byte 0
secondWeakestFace: .byte 0
#else
projectedX: .fill FACE_COUNT*VERTICES_PER_FACE, 0
projectedY: .fill FACE_COUNT*VERTICES_PER_FACE, 0
#endif
slotX: .fill 16, 0
slotY: .fill 16, 0
slotColor: .fill 16, 0
slotFace: .fill 16, $ff
enableMasks: .byte 0,1,3,7,15,31,63,127,255
// Brown, dark gray, mid gray, light gray, white; saturate stronger normals.
spriteFadeColors: .fill 128, i<6 ? 9 : (i<12 ? 11 : (i<18 ? 12 : (i<24 ? 15 : 1)))
spriteLow: .byte 0,64,128,192,0,64,128,192
faceOffsets: .fill FACE_COUNT, i*MODEL_POINTS_PER_FACE
projectedOffsets: .fill FACE_COUNT, i*VERTICES_PER_FACE
bitMasks: .fill 24, $80 >> (i&7)
byteColumns: .fill 24, floor(i/8)*21
#if !HEXAGON
.import source "build/model.asm"
#endif

.align $100
sine: .fill 256, round(64*sin(toRadians(i*360/256))) & $ff
cosine: .fill 256, round(64*cos(toRadians(i*360/256))) & $ff
quarterSquares: .fill 256, floor(pow(i<128 ? i : i-256,2)/256)
#if GOLDEN_PENTAGON
goldenRatio: .fill 256, round((i<128 ? i : i-256)*(sqrt(5)-1)/2) & $ff
#endif
.errorif * > $fffa, "Runtime overlaps hardware vectors"

* = SPRITES_A "Two sprite sets outside the VIC character-ROM window"
.fill 1024, 0
* = MARKERS "Column-major CPU crossing buffers"
.fill ACTIVE_SPRITES*64, 0

* = $2000 "Static Koala multicolor bitmap"
.import binary "build/ball-bitmap.bin"

* = $4000 "Unrolled sprite clearing and vertical XOR filling"
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
curveRowsLow: .fill 41, <($9800+i*24)
curveRowsHigh: .fill 41, >($9800+i*24)
.errorif * > $d000, "Program reaches I/O"
#if HEXAGON
* = $6000 "Shared-vertex projection specialized for constant coordinates"
.import source "build/hex-projection.asm"
.errorif * > $8000, "Hexagon routines overlap product tables"
* = $8000 "Coordinate products for all rotation coefficients"
.import binary "build/hex-products.bin"
.errorif * > $9400, "Hexagon tables overlap background attributes"
#endif
* = $1000 "Initial multicolor bitmap color RAM"
backgroundColors: .import binary "build/ball-colors.bin"
.fill 24, 0
* = $9400 "Initial multicolor bitmap screen colors"
backgroundScreen: .import binary "build/ball-screen.bin"
.fill 24, 0
* = $9800 "Edge crossing curve pointers"
hexEdgeLow: .import binary "build/hex-edge-low.bin"
* = $9c00
hexEdgeHigh: .import binary "build/hex-edge-high.bin"
* = $a000 "Exact bounded edge crossings"
hexEdgeSamples: .import binary "build/hex-edge-samples.bin"
.errorif * > $d000, "Edge curves reach I/O"
programEnd:

#if HEXAGON
* = $7000 "Enclosed pentagon color mapping"
.import source "gap.asm"
.import source "build/hex-gaps.asm"
.errorif * > $8000, "Gap mapper overlaps coordinate products"
#endif
