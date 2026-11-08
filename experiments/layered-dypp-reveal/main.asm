// Original layered DYPP/reveal counterpart. No Demo Coder release bytes.
// Prepared source strips; live fine/coarse scroll, independent column waves,
// two selector-plane OR passes, and stateful bytewise picture reveal.
.label sourcePointer=$f0
.label outputPointer=$f2
BasicUpstart2(start)
*=$1000 "Original live layered renderer and shared publication"
start:
    jsr initializeDisplay
    sei
    lda #0
    sta $d020
    sta $d021
    lda #14
    sta $d022
    lda #3
    sta $d023
    ldx #0
!blank:
    lda #0
    .for (var page=0;page<8;page++) {
        sta $2000+page*256,x
        sta $2800+page*256,x
    }
    .for (var page=0;page<4;page++) {
        sta $0400+page*256,x
        sta $d800+page*256,x
    }
    inx
    bne !blank-
    // Code 0's first eight rows stay blank; it is also the outside canvas.
    .for (var column=0;column<16;column++) {
        .for (var row=0;row<16;row++) {
            lda #column*16+row
            sta $0400+(row+4)*40+column+12
            lda #9
            sta $d800+(row+4)*40+column+12
        }
    }
    lda #$20
    sta frontFontHigh
    lda #4
    sta frontScreenHigh
    sta drawScreenHigh
    cli
stateAdvanced:
    lda frontFontHigh
    eor #8
    sta drawFontHigh
    lsr
    lsr
    ora #$10
    sta drawSelection
    lda #0
    sta outputPointer
    lda drawFontHigh
    sta outputPointer+1
    lda #0
    ldx #8
    ldy #0
!clear:
    sta (outputPointer),y
    iny
    bne !clear-
    inc outputPointer+1
    dex
    bne !clear-
hiddenCleared:
    jsr drawText
textLayerComplete:
    jsr drawPicture
renderComplete:
    jsr publishImage
    jsr advanceState
    jmp stateAdvanced

drawText:
    lda #0
    sta layerKind
    lda #24
    sta layerHeight
    lda textScroll
    sta scrollValue
    lda textWave
    sta waveCursor
    lda #13
    sta waveStep
    jmp drawLayer
drawPicture:
    lda #1
    sta layerKind
    lda #48
    sta layerHeight
    lda pictureScroll
    sta scrollValue
    lda pictureWave
    sta waveCursor
    lda #11
    sta waveStep
drawLayer:
    lda scrollValue
    and #3
    clc
    adc #>expandText
    ldx layerKind
    beq !lookup+
    clc
    adc #4
!lookup:
    sta expandLookup+2
    lda scrollValue
    lsr
    lsr
    sta sourceColumn
    lda #0
    sta outputColumn
!column:
    ldx waveCursor
    lda layerKind
    bne !pictureY+
    lda textSine,x
    clc
    adc #34
    ldx outputColumn
    sta textOffsets,x
    jmp !target+
!pictureY:
    lda pictureSine,x
    clc
    adc #42
    ldx outputColumn
    sta pictureOffsets,x
!target:
    sta destinationY
    lda outputColumn
    and #1
    beq !lowHalf+
    lda #$80
!lowHalf:
    clc
    adc destinationY
    sta outputPointer
    lda outputColumn
    lsr
    clc
    adc drawFontHigh
    sta outputPointer+1
    lda layerKind
    beq !textSource+
    ldx outputColumn
    lda revealMasks,x
    beq !nextColumn+
    ldx sourceColumn
    lda pictureLo,x
    sta sourcePointer
    lda pictureHi,x
    sta sourcePointer+1
    jmp !rows+
!textSource:
    ldx sourceColumn
    lda textLo,x
    sta sourcePointer
    lda textHi,x
    sta sourcePointer+1
!rows:
    ldy #0
!row:
    lda (sourcePointer),y
    tax
expandLookup:
    lda expandText,x
    ora (outputPointer),y
    sta (outputPointer),y
    iny
    cpy layerHeight
    bne !row-
!nextColumn:
    inc sourceColumn
    lda sourceColumn
    and #63
    sta sourceColumn
    clc
    lda waveCursor
    adc waveStep
    sta waveCursor
    inc outputColumn
    lda outputColumn
    cmp #16
    beq !done+
    jmp !column-
!done:
    rts

advanceState:
    inc poseUsed
    inc pictureScroll
    lda textScroll
    sec
    sbc #2
    sta textScroll
    clc
    lda textWave
    adc #5
    sta textWave
    clc
    lda pictureWave
    adc #3
    sta pictureWave
    lda revealMode
    beq !open+
    cmp #1
    beq !hold+
    cmp #2
    beq !close+
!hold:
    inc stageTick
    lda stageTick
    cmp #16
    bne !done+
    lda #0
    sta stageTick
    inc revealMode
    lda revealMode
    and #3
    sta revealMode
    rts
!open:
    ldx revealWidth
    lda #$ff
    sta revealMasks,x
    inc revealWidth
    lda revealWidth
    cmp #16
    bne !done+
    inc revealMode
    rts
!close:
    dec revealWidth
    ldx revealWidth
    lda #0
    sta revealMasks,x
    cpx #0
    bne !done+
    inc revealMode
!done:
    rts

// Reuse the complete hidden-font publication/IRQ contract, applying this
// scene's own palette, immutable matrix and two fonts after generic setup.
.import source "../prepared-fragments/display.asm"
.errorif *>$2000,"Runtime overlaps display fonts"
*=$3000 "Reusable sine displacement profiles and source-column pointers"
textSine: .import binary "build/sines.bin",0,256
pictureSine: .import binary "build/sines.bin",256,256
textLo: .fill 64,<(textSource+i*24)
textHi: .fill 64,>(textSource+i*24)
pictureLo: .fill 64,<(pictureSource+i*48)
pictureHi: .fill 64,>(pictureSource+i*48)
.errorif *>$3400,"Tables overlap live state"
*=$3400 "Live independent scroll/wave and bounded reveal state"
frameCounter: .word 0
presentationCounter: .word 0
poseUsed: .byte 0
frontPose: .byte 0
frontFontHigh: .byte $20
frontScreenHigh: .byte 4
drawFontHigh: .byte $28
drawScreenHigh: .byte 4
drawSelection: .byte $1a
textScroll: .byte 0
pictureScroll: .byte 0
textWave: .byte 0
pictureWave: .byte 0
revealMode: .byte 0
revealWidth: .byte 0
stageTick: .byte 0
revealMasks: .fill 16,0
textOffsets: .fill 16,0
pictureOffsets: .fill 16,0
layerKind: .byte 0
layerHeight: .byte 0
scrollValue: .byte 0
waveCursor: .byte 0
waveStep: .byte 0
sourceColumn: .byte 0
outputColumn: .byte 0
destinationY: .byte 0
.errorif *>$4000,"State overlaps original source strip"
*=$4000 "Own text source in overlapping four-pixel column windows"
textSource: .import binary "build/text-windows.bin"
.errorif *!=textSource+64*24,"Text strip format"
*=$4800 "Own skyline and planet source in overlapping column windows"
pictureSource: .import binary "build/picture-windows.bin"
.errorif *!=pictureSource+64*48,"Picture strip format"
*=$5800 "Four reusable fine phases per independent selector plane"
expandText: .import binary "build/expand-text.bin"
expandPicture: .import binary "build/expand-picture.bin"
.errorif *!=$6000,"Reusable expansion table format"
