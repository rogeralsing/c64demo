// Original patterned-vector renderer on an expanded hardware-sprite canvas.
// Geometry packets are prepared; edge stepping, masks and filling run on C64.
// Six sprites per band form one plane, with coherent double-buffer publication.

BasicUpstart2(start)

.const PACKET_POINTER = $f0
.const PIXEL_POINTER = $f2
.const CLEAR_POINTER = $f4
.const WIDTH = 144
.const HEIGHT = 63
.const BUFFER_BYTES = 6*3*64
.var screenBases = List().add($0400,$0800,$0c00,$3000,$3400,$3c00)

* = $4000 "Prepared projected triangles and span runs"
poseLow: .fill 16, <(poses+i*13)
poseHigh: .fill 16, >(poses+i*13)
poses:
    .for (var pose = 0; pose < 16; pose++) {
        .var shift = round(3*sin(pose*2*PI/16))
        .byte 2
        // Apex X/Y, left-bottom X, bottom Y, right-bottom X, density material.
        .byte 72+shift,18,4+shift,62,140+shift,pose
        .byte 40-shift,24,18-shift,54,62-shift,(pose+8)&15
    }
spanRuns:
    .for (var material = 0; material < 16; material++) {
        // Inclusive left, exclusive right, starting Y, height, material.
        .byte 4+34*mod(material,4),34+34*mod(material,4),4*floor(material/4),3,material
    }

rowLow:
    .fill HEIGHT, <(floor(i/21)*384+mod(i,21)*3)
rowHigh:
    .fill HEIGHT, >(floor(i/21)*384+mod(i,21)*3)
columnLow:
    .fill 18, <(floor(i/3)*64+mod(i,3))
columnHigh:
    .fill 18, >(floor(i/3)*64+mod(i,3))
leftMasks: .fill 8, $ff >> i
rightMasks: .fill 8, ($ff << (7-i)) & $ff

.var bayer = List().add(0,8,2,10,12,4,14,6,3,11,1,9,15,7,13,5)
densityPatterns:
    .for (var material = 0; material < 16; material++) {
        .for (var row = 0; row < 4; row++) {
            .var bits = 0
            .for (var x = 0; x < 8; x++) {
                .eval bits = (bits << 1) | ((bayer.get(row*4+mod(x,4)) < material) ? 1 : 0)
            }
            .byte bits
        }
    }

* = $6000 "Runtime sprite-vector rasterizer"
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
    lda #3
    sta $dd00
    lda $dd02
    ora #3
    sta $dd02
    lda #$18
    sta $d011
    lda #8
    sta $d016
    lda #$1e
    sta $d018
    lda #0
    sta $d020
    sta $d021
    sta $d015
    sta $d01b
    sta $d01c
    sta frontBuffer
    sta frontPose
    sta renderPose
    sta renderReady
    sta frameCounter
    sta frameCounter+1
    sta publicationCounter
    sta publicationCounter+1
    ldx #0
!clearScreens:
    .for (var screen = 0; screen < 6; screen++) {
        .for (var page = 0; page < 4; page++) {
            sta screenBases.get(screen)+page*$100,x
        }
    }
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    inx
    bne !clearScreens-
    ldx #7
!clearGlyph:
    sta $3800,x
    dex
    bpl !clearGlyph-
    .for (var buffer = 0; buffer < 2; buffer++) {
        .for (var band = 0; band < 3; band++) {
            .for (var sprite = 0; sprite < 6; sprite++) {
                lda #$80+buffer*$20+band*6+sprite
                sta screenBases.get(buffer*3+band)+$3f8+sprite
            }
        }
    }
    .for (var sprite = 0; sprite < 6; sprite++) {
        lda #((40+48*sprite)&$ff)
        sta $d000+2*sprite
        lda #13
        sta $d027+sprite
    }
    lda #$20
    sta $d010
    lda #$3f
    sta $d017
    sta $d01d

    lda #$20
    sta drawBaseHigh
    jsr renderScene
    lda #<irq
    sta $fffe
    lda #>irq
    sta $ffff
    lda #<nmiReturn
    sta $fffa
    lda #>nmiReturn
    sta $fffb
    lda #<displayTop
    sta irqPart
    lda #>displayTop
    sta irqPart+1
    lda #0
    sta $d012
    lda #1
    sta $d019
    sta $d01a
    lda #1
    sta renderPose
    cli

main:
    lda renderReady
    bne main
    lda frontBuffer
    eor #1
    asl
    asl
    asl
    clc
    adc #$20
    sta drawBaseHigh
    jsr renderScene
    lda renderPose
    sta pendingPose
    lda #1
    sta renderReady
!waitPublication:
    lda renderReady
    bne !waitPublication-
    inc renderPose
    lda renderPose
    and #15
    sta renderPose
    jmp main

irq:
    pha
    txa
    pha
    tya
    pha
    jmp (irqPart)

.macro NextPart(address, line) {
    lda #<address
    sta irqPart
    lda #>address
    sta irqPart+1
    lda #line
    sta $d012
    jmp irqReturn
}

displayTop:
    lda renderReady
    beq !frontReady+
    lda frontBuffer
    eor #1
    sta frontBuffer
    lda pendingPose
    sta frontPose
    lda #0
    sta renderReady
    inc publicationCounter
    bne !frontReady+
    inc publicationCounter+1
!frontReady:
    lda frontBuffer
    beq !bufferA+
    lda #$de
    sta frontScreen1
    lda #$fe
    sta frontScreen2
    lda #$ce
    jmp !screenReady+
!bufferA:
    lda #$2e
    sta frontScreen1
    lda #$3e
    sta frontScreen2
    lda #$1e
!screenReady:
    sta frontScreen
    sta $d018
    lda #64
    .for (var sprite = 0; sprite < 6; sprite++) {
        sta $d001+2*sprite
    }
    lda #$3f
    sta $d015
    NextPart(displayBand1,96)

displayBand1:
    lda #106
    .for (var sprite = 0; sprite < 6; sprite++) {
        sta $d001+2*sprite
    }
!wait:
    lda $d012
    cmp #106
    bne !wait-
    lda frontScreen1
    sta $d018
    NextPart(displayBand2,138)

displayBand2:
    lda #148
    .for (var sprite = 0; sprite < 6; sprite++) {
        sta $d001+2*sprite
    }
!wait:
    lda $d012
    cmp #148
    bne !wait-
    lda frontScreen2
    sta $d018
    NextPart(displayEnd,198)

displayEnd:
    inc frameCounter
    bne displayFrameComplete
    inc frameCounter+1
displayFrameComplete:
    NextPart(displayTop,0)

irqReturn:
    lda #1
    sta $d019
    pla
    tay
    pla
    tax
    pla
nmiReturn:
    rti

renderScene:
    lda #0
    sta CLEAR_POINTER
    lda drawBaseHigh
    sta CLEAR_POINTER+1
    ldx #4
    ldy #0
    lda #0
!page:
    sta (CLEAR_POINTER),y
    iny
    bne !page-
    inc CLEAR_POINTER+1
    dex
    bne !page-
!tail:
    sta (CLEAR_POINTER),y
    iny
    cpy #128
    bne !tail-

    // Prepared scanline runs provide the sixteen density swatches.
    ldx #0
!run:
    lda spanRuns,x
    sta spanLeft
    lda spanRuns+1,x
    sta spanRight
    lda spanRuns+2,x
    sta spanY
    lda spanRuns+3,x
    sta runRows
    lda spanRuns+4,x
    sta spanMaterial
    txa
    clc
    adc #5
    sta nextRunOffset
!runRow:
    jsr drawSpan
    inc spanY
    dec runRows
    bne !runRow-
    ldx nextRunOffset
    cpx #80
    bne !run-

    // Triangle records contain projected vertices, not scanline bitmaps.
    ldx renderPose
    lda poseLow,x
    sta PACKET_POINTER
    lda poseHigh,x
    sta PACKET_POINTER+1
    ldy #0
    lda (PACKET_POINTER),y
    sta trianglesRemaining
    inc PACKET_POINTER
    bne !triangle+
    inc PACKET_POINTER+1
!triangle:
    ldy #0
    lda (PACKET_POINTER),y
    sta edgeLeft
    sta edgeRight
    iny
    lda (PACKET_POINTER),y
    sta spanY
    iny
    lda (PACKET_POINTER),y
    sta bottomLeft
    iny
    lda (PACKET_POINTER),y
    sta bottomY
    iny
    lda (PACKET_POINTER),y
    sta bottomRight
    iny
    lda (PACKET_POINTER),y
    sta spanMaterial
    clc
    lda PACKET_POINTER
    adc #6
    sta PACKET_POINTER
    bcc !packetReady+
    inc PACKET_POINTER+1
!packetReady:
    sec
    lda bottomY
    sbc spanY
    sta edgeDenominator
    sec
    sbc #1
    sta rightError
    lda #0
    sta leftError
    sec
    lda edgeLeft
    sbc bottomLeft
    sta leftDelta
    sec
    lda bottomRight
    sbc edgeRight
    sta rightDelta
!triangleRow:
    lda edgeLeft
    sta spanLeft
    lda edgeRight
    sta spanRight
    jsr drawSpan
    inc spanY
    lda spanY
    cmp bottomY
    beq !triangleDone+
    clc
    lda leftError
    adc leftDelta
!leftAdvance:
    cmp edgeDenominator
    bcc !leftDone+
    sec
    sbc edgeDenominator
    dec edgeLeft
    jmp !leftAdvance-
!leftDone:
    sta leftError
    clc
    lda rightError
    adc rightDelta
!rightAdvance:
    cmp edgeDenominator
    bcc !rightDone+
    sec
    sbc edgeDenominator
    inc edgeRight
    jmp !rightAdvance-
!rightDone:
    sta rightError
    jmp !triangleRow-
!triangleDone:
    dec trianglesRemaining
    beq !sceneDone+
    jmp !triangle-
!sceneDone:
    rts

// Inclusive left/exclusive right spans OR their material into the cleared plane.
drawSpan:
    lda spanLeft
    cmp spanRight
    bcc !nonempty+
    rts
!nonempty:
    and #7
    tax
    lda leftMasks,x
    sta firstMask
    lda spanLeft
    lsr
    lsr
    lsr
    sta firstByte
    sec
    lda spanRight
    sbc #1
    pha
    and #7
    tax
    lda rightMasks,x
    sta lastMask
    pla
    lsr
    lsr
    lsr
    sta lastByte
    lda spanMaterial
    asl
    asl
    sta patternOffset
    lda spanY
    and #3
    ora patternOffset
    tax
    lda densityPatterns,x
    sta patternByte
    ldx firstByte
!byte:
    lda #$ff
    cpx firstByte
    bne !notFirst+
    and firstMask
!notFirst:
    cpx lastByte
    bne !notLast+
    and lastMask
!notLast:
    and patternByte
    sta maskedPattern
    ldy spanY
    clc
    lda rowLow,y
    adc columnLow,x
    sta PIXEL_POINTER
    lda rowHigh,y
    adc columnHigh,x
    adc drawBaseHigh
    sta PIXEL_POINTER+1
    ldy #0
    lda (PIXEL_POINTER),y
    ora maskedPattern
    sta (PIXEL_POINTER),y
    cpx lastByte
    beq !done+
    inx
    jmp !byte-
!done:
    rts

frontBuffer: .byte 0
frontPose: .byte 0
renderPose: .byte 0
pendingPose: .byte 0
renderReady: .byte 0
drawBaseHigh: .byte $20
frontScreen: .byte $1e
frontScreen1: .byte $2e
frontScreen2: .byte $3e
irqPart: .word displayTop
frameCounter: .word 0
publicationCounter: .word 0
spanLeft: .byte 0
spanRight: .byte 0
spanY: .byte 0
spanMaterial: .byte 0
runRows: .byte 0
nextRunOffset: .byte 0
trianglesRemaining: .byte 0
bottomLeft: .byte 0
bottomRight: .byte 0
bottomY: .byte 0
edgeLeft: .byte 0
edgeRight: .byte 0
edgeDenominator: .byte 0
leftDelta: .byte 0
rightDelta: .byte 0
leftError: .byte 0
rightError: .byte 0
firstByte: .byte 0
lastByte: .byte 0
firstMask: .byte 0
lastMask: .byte 0
patternOffset: .byte 0
patternByte: .byte 0
maskedPattern: .byte 0
.assert "Rasterizer fits below I/O space", * < $d000, true
