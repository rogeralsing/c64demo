// Original live corner-cut cube with face-local colored stencils.
// Topology and artwork are new; no Tower Power release bytes are included.
.const HALF=24
.const VERTICES=42
.const MARKERS=$4000
.label markerPointer=$e0
.label outputPointer=$e2

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
    lda #0
    sta $d011
    sta $d015
    sta $d01a
    sta $d020
    sta $d021
    sta phase
    sta rasterTick
    sta presentationCount
    sta presentationCount+1
    lda #$28
    sta drawCharsetHigh
    lda #3
    sta $dd02
    sta $dd00
    lda #$18
    sta $d016
    sta $d018
    lda #6
    sta $d022
    lda #3
    sta $d023
    ldx #0
!clear:
    lda #0
    sta $0400,x
    sta $0500,x
    sta $0600,x
    sta $0700,x
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    .for (var page=0; page<16; page++) { sta $2000+page*256,x }
    inx
    bne !clear-
    .for (var column=0; column<16; column++) {
        .for (var row=0; row<16; row++) {
            lda #column*16+row
            sta $0400+(row+4)*40+column+12
            lda #9
            sta $d800+(row+4)*40+column+12
        }
    }
    lda #<irq
    sta $fffe
    lda #>irq
    sta $ffff
    lda #<nmi
    sta $fffa
    lda #>nmi
    sta $fffb
    lda #0
    sta $d012
    lda #1
    sta $d019
    sta $d01a
    lda #$1b
    sta $d011
    cli

nextPose:
    jsr clearMarkers
    jsr buildModel
    jsr transformModel
    jsr classifyFaces
    jsr drawBody
    jsr fillHidden
renderComplete:
    lda rasterTick
!nextField:
    cmp rasterTick
    beq !nextField-
    lda drawCharsetHigh
    cmp #$20
    beq !first+
    lda #$1a
    bne !select+
!first:
    lda #$18
!select:
    sta $d018
    lda phase
    sta shownPhase
    inc presentationCount
    bne !count+
    inc presentationCount+1
!count:
framePresented:
    lda phase
    clc
    adc #1
    and #63
    sta phase
    lda drawCharsetHigh
    eor #8
    sta drawCharsetHigh
    jmp nextPose

irq:
    pha
    inc rasterTick
    lda #1
    sta $d019
    pla
nmi:
    rti

clearMarkers:
    lda #0
    ldx #0
!clear:
    .for (var page=0; page<8; page++) { sta MARKERS+page*256,x }
    inx
    bne !clear-
    rts

buildModel:
    ldx phase
    lda cutMotion,x
    sta cutValue
    lda #HALF
    sec
    sbc cutValue
    sta innerMagnitude
    // Each cube corner contributes the three points along its cut edges.
    .for (var corner=0; corner<8; corner++) {
        .for (var edgeAxis=0; edgeAxis<3; edgeAxis++) {
            .for (var axis=0; axis<3; axis++) {
                .if (axis==edgeAxis) { lda innerMagnitude } else { lda #HALF }
                .if ((corner&(1<<axis))==0) {
                    eor #$ff
                    clc
                    adc #1
                }
                sta modelX+axis*VERTICES+corner*3+edgeAxis
            }
        }
    }
    // Three explicit coplanar pattern points on each large face. Their central
    // placement remains within the octagon at every cut value from4 through14.
    .var stencilU=List().add(-7,9,0)
    .var stencilV=List().add(-7,-7,10)
    .for (var face=0; face<6; face++) {
        .var fixedAxis=floor(face/2)
        .var sign=(face&1)==0 ? -1 : 1
        .var u=(fixedAxis+1)-floor((fixedAxis+1)/3)*3
        .var v=(fixedAxis+2)-floor((fixedAxis+2)/3)*3
        .for (var point=0; point<3; point++) {
            .for (var axis=0; axis<3; axis++) {
                .var coordinate=axis==fixedAxis ? sign*HALF : axis==u ? stencilU.get(point) : stencilV.get(point)
                lda #coordinate&255
                sta modelX+axis*VERTICES+24+face*3+point
            }
        }
    }
    rts

transformModel:
    lda phase
    asl
    asl
    clc
    adc #1
    sta angleYaw
    tax
    lda sineUnit,x
    sta sinYaw
    txa
    clc
    adc #64
    tax
    lda sineUnit,x
    sta cosYaw
    ldx phase
    lda pitchMotion,x
    sta anglePitch
    tax
    lda sineUnit,x
    sta sinPitch
    txa
    clc
    adc #64
    tax
    lda sineUnit,x
    sta cosPitch
    ldy #VERTICES-1
!vertex:
    lda cosYaw
    sta factor
    lda modelX,y
    jsr scaledProduct
    sta yawX
    lda modelZ,y
    jsr scaledProduct
    sta yawZ
    lda sinYaw
    sta factor
    lda modelZ,y
    jsr scaledProduct
    clc
    adc yawX
    sta rotatedX,y
    lda modelX,y
    jsr scaledProduct
    sta term
    lda yawZ
    sec
    sbc term
    sta yawZ
    lda cosPitch
    sta factor
    lda modelY,y
    jsr scaledProduct
    sta pitchY
    lda yawZ
    jsr scaledProduct
    sta pitchZ
    lda sinPitch
    sta factor
    lda yawZ
    jsr scaledProduct
    sta term
    lda pitchY
    sec
    sbc term
    sta rotatedY,y
    lda modelY,y
    jsr scaledProduct
    clc
    adc pitchZ
    sta rotatedZ,y
    clc
    adc #64
    tax
    lda depthFactors,x
    sta factor
    lda rotatedX,y
    jsr scaledProduct
    clc
    adc #32
    sta projectedX,y
    lda rotatedY,y
    jsr scaledProduct
    asl
    sta term
    lda #64
    sec
    sbc term
    sta projectedY,y
    dey
    bmi !done+
    jmp !vertex-
!done:
    lda cosPitch
    sta factor
    lda sinYaw
    jsr scaledProduct
    eor #$ff
    clc
    adc #1
    sta normalZ
    lda sinPitch
    sta normalZ+1
    lda cosYaw
    jsr scaledProduct
    sta normalZ+2
    rts

// Q(a+b)-Q(a-b), Q(n)=floor(n*n/256), approximates signed a*b/64.
// Y survives. The scene's audited input domain stays within |a±b|<=128.
scaledProduct:
    sta multiplicand
    clc
    adc factor
    tax
    lda quarterSquares,x
    sta productSum
    lda multiplicand
    sec
    sbc factor
    tax
    lda productSum
    sec
    sbc quarterSquares,x
    rts

classifyFaces:
    lda #0
    sta faceIndex
!face:
    lda #0
    sta areaLo
    sta areaHi
    ldy faceIndex
    lda faceStarts,y
    sta listStart
    tay
    ldx faceVertices,y
    lda projectedX,x
    sta anchorX
    lda projectedY,x
    sta anchorY
    lda #2
    sta fanIndex
!fan:
    lda listStart
    clc
    adc fanIndex
    tay
    ldx faceVertices,y
    lda projectedX,x
    sec
    sbc anchorX
    sta dx2
    lda projectedY,x
    sec
    sbc anchorY
    sta dy2
    dey
    ldx faceVertices,y
    lda projectedX,x
    sec
    sbc anchorX
    sta dx1
    lda projectedY,x
    sec
    sbc anchorY
    sta dy1
    lda dx1
    ldx dy2
    jsr signedProduct
    lda wideProduct
    sta firstProduct
    lda wideProduct+1
    sta firstProduct+1
    lda dy1
    ldx dx2
    jsr signedProduct
    lda firstProduct
    sec
    sbc wideProduct
    sta crossLo
    lda firstProduct+1
    sbc wideProduct+1
    sta crossHi
    lda areaLo
    clc
    adc crossLo
    sta areaLo
    lda areaHi
    adc crossHi
    sta areaHi
    inc fanIndex
    ldy faceIndex
    lda fanIndex
    cmp faceCounts,y
    beq !fanDone+
    jmp !fan-
!fanDone:
    lda #0
    ldx areaHi
    bmi !visible+
    lda areaLo
    ora areaHi
    beq !visible+
    lda #1
!visible:
    ldy faceIndex
    sta faceVisible,y
    inc faceIndex
    lda faceIndex
    cmp #14
    beq !facesDone+
    jmp !face-
!facesDone:

    ldy #0
!stencil:
    lda #0
    sta markVisible,y
    lda faceVisible,y
    beq !nextStencil+
    tya
    lsr
    tax
    lda normalZ,x
    sta term
    tya
    and #1
    bne !normal+
    lda term
    eor #$ff
    clc
    adc #1
    sta term
!normal:
    lda term
    eor #$80
    cmp #97
    bcs !nextStencil+
    lda #1
    sta markVisible,y
!nextStencil:
    iny
    cpy #6
    bne !stencil-
    rts

// Exact signed-byte product for projected polygon-area tests.
signedProduct:
    sta wideLeft
    stx wideRight
    lda #0
    sta wideSign
    lda wideLeft
    bpl !left+
    eor #$ff
    clc
    adc #1
    sta wideLeft
    inc wideSign
!left:
    lda wideRight
    bpl !right+
    eor #$ff
    clc
    adc #1
    sta wideRight
    inc wideSign
!right:
    lda #0
    sta wideProduct
    sta wideProduct+1
    sta wideShift+1
    lda wideLeft
    sta wideShift
    ldx #8
!bit:
    lsr wideRight
    bcc !skip+
    lda wideProduct
    clc
    adc wideShift
    sta wideProduct
    lda wideProduct+1
    adc wideShift+1
    sta wideProduct+1
!skip:
    asl wideShift
    rol wideShift+1
    dex
    bne !bit-
    lda wideSign
    and #1
    beq !done+
    lda wideProduct
    eor #$ff
    clc
    adc #1
    sta wideProduct
    lda wideProduct+1
    eor #$ff
    adc #0
    sta wideProduct+1
!done:
    rts

drawBody:
    lda #0
    sta faceIndex
!face:
    ldy faceIndex
    lda faceVisible,y
    beq !next+
    lda faceColors,y
    sta boundaryColor
    lda faceStarts,y
    sta polygonStart
    lda faceCounts,y
    sta polygonCount
    jsr drawPolygon
!next:
    inc faceIndex
    lda faceIndex
    cmp #14
    bne !face-
    lda #0
    sta faceIndex
!mark:
    ldy faceIndex
    lda markVisible,y
    beq !nextMark+
    lda faceColors,y
    eor markColors,y
    sta boundaryColor
    lda faceIndex
    asl
    clc
    adc faceIndex
    adc #72
    sta polygonStart
    lda #3
    sta polygonCount
    jsr drawPolygon
!nextMark:
    inc faceIndex
    lda faceIndex
    cmp #6
    bne !mark-
    rts

drawPolygon:
    lda #0
    sta polygonCursor
!edge:
    lda polygonStart
    clc
    adc polygonCursor
    tay
    ldx faceVertices,y
    lda projectedX,x
    sta lineX0
    lda projectedY,x
    sta lineY0
    lda polygonCursor
    clc
    adc #1
    cmp polygonCount
    bcc !next+
    lda #0
!next:
    clc
    adc polygonStart
    tay
    ldx faceVertices,y
    lda projectedX,x
    sta lineX1
    lda projectedY,x
    sta lineY1
    jsr drawBoundary
    inc polygonCursor
    lda polygonCursor
    cmp polygonCount
    bne !edge-
    rts

plotBoundaryMarker:
    cpy #128
    bcs !terminal+
    sta markerColor
    txa
    pha
    and #3
    sta markerLane
    lda markerColor
    asl
    asl
    ora markerLane
    tax
    lda shiftedColors,x
    sta markerValue
    pla
    lsr
    lsr
    tax
    lda markerLow,x
    sta markerPointer
    lda markerHigh,x
    sta markerPointer+1
    lda markerValue
    eor (markerPointer),y
    sta (markerPointer),y
!terminal:
    rts
.errorif * > $2000, "Main code overlaps charset buffers"

*=$3000 "Geometry parameters and scalar arithmetic tables"
.align $100
sineUnit: .fill 256, round(64*sin(i*2*PI/256))&255
quarterSquares: .fill 256, floor((i<128 ? i : i-256)*(i<128 ? i : i-256)/256)
depthFactors: .fill 128, round(96*64/(144+i-64))
cutMotion: .fill 64, 9+round(5*sin(i*2*PI/64))
pitchMotion: .fill 64, round(24*sin(i*2*PI/64+0.4))&255

.function Quad(a,b,c,d) {
    .return List().add(a,b,c,d)
}
.var cubeFaces=List().add(Quad(0,4,6,2),Quad(1,3,7,5),Quad(0,1,5,4),Quad(2,6,7,3),Quad(0,2,3,1),Quad(4,5,7,6))
.function AxisOf(difference) {
    .return difference==1 ? 0 : difference==2 ? 1 : 2
}
faceStarts: .byte 0,8,16,24,32,40,48,51,54,57,60,63,66,69
faceCounts: .byte 8,8,8,8,8,8,3,3,3,3,3,3,3,3
faceColors: .byte 1,1,2,2,3,3,1,2,3,1,2,3,1,2
markColors: .byte 2,2,3,3,1,1
faceVertices:
    .for (var face=0; face<6; face++) {
        .var corners=cubeFaces.get(face)
        .for (var point=0; point<4; point++) {
            .var corner=corners.get(point)
            .var previous=corners.get((point+3)&3)
            .var next=corners.get((point+1)&3)
            .byte corner*3+AxisOf(corner^previous),corner*3+AxisOf(corner^next)
        }
    }
    .for (var corner=0; corner<8; corner++) {
        .var positives=(corner&1)+((corner>>1)&1)+((corner>>2)&1)
        .if ((positives&1)!=0) { .byte corner*3,corner*3+1,corner*3+2 }
        else { .byte corner*3,corner*3+2,corner*3+1 }
    }
    .fill 18,24+i
shiftedColors: .fill 16, floor(i/4)<<(6-(i&3)*2)
markerLow: .fill 16, <(MARKERS+i*128)
markerHigh: .fill 16, >(MARKERS+i*128)

*=$3400 "Live geometry and renderer state"
modelX: .fill VERTICES,0
modelY: .fill VERTICES,0
modelZ: .fill VERTICES,0
rotatedX: .fill VERTICES,0
rotatedY: .fill VERTICES,0
rotatedZ: .fill VERTICES,0
projectedX: .fill VERTICES,0
projectedY: .fill VERTICES,0
faceVisible: .fill 14,0
markVisible: .fill 6,0
normalZ: .fill 3,0
phase: .byte 0
shownPhase: .byte 0
presentationCount: .word 0
rasterTick: .byte 0
drawCharsetHigh: .byte 0
cutValue: .byte 0
innerMagnitude: .byte 0
angleYaw: .byte 0
anglePitch: .byte 0
sinYaw: .byte 0
cosYaw: .byte 0
sinPitch: .byte 0
cosPitch: .byte 0
factor: .byte 0
multiplicand: .byte 0
productSum: .byte 0
yawX: .byte 0
yawZ: .byte 0
pitchY: .byte 0
pitchZ: .byte 0
term: .byte 0
faceIndex: .byte 0
listStart: .byte 0
fanIndex: .byte 0
anchorX: .byte 0
anchorY: .byte 0
dx1: .byte 0
dy1: .byte 0
dx2: .byte 0
dy2: .byte 0
areaLo: .byte 0
areaHi: .byte 0
firstProduct: .word 0
crossLo: .byte 0
crossHi: .byte 0
wideLeft: .byte 0
wideRight: .byte 0
wideSign: .byte 0
wideProduct: .word 0
wideShift: .word 0
polygonStart: .byte 0
polygonCount: .byte 0
polygonCursor: .byte 0
lineX0: .byte 0
lineY0: .byte 0
lineX1: .byte 0
lineY1: .byte 0
boundaryColor: .byte 0
markerColor: .byte 0
markerLane: .byte 0
markerValue: .byte 0
.errorif * > $3800, "Live geometry exceeds reserved RAM"

*=$5000 "Shared exact half-open boundary sampler"
.import source "../lib/polygon-edges.asm"

*=$6000 "Hidden charset prefix fill"
fillHidden:
    .for (var column=0; column<16; column++) {
        lda #<(column*128)
        sta outputPointer
        lda drawCharsetHigh
        clc
        adc #>(column*128)
        sta outputPointer+1
        lda #0
        ldy #0
    !fill:
        eor MARKERS+column*128,y
        sta (outputPointer),y
        iny
        bpl !fill-
    }
    rts
