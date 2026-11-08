// Original 2D sprite-to-character transition, inspired by NextLevel TransBox.
// Prepared adjacent path samples; live character/color shifts and quadrant wipe.
BasicUpstart2(start)
.const SOURCE = $f0
.const DESTINATION = $f2
.const COLOR = $f4
.const SEED_COLOR = $f6
.var pairColors = List().add(1,15,14,6)

* = $1000 "Three-stage normal PAL sequence"
start:
    sei
    cld
    lda #$35
    sta $01
    lda #$7f
    sta $dc0d
    sta $dd0d
    lda $dc0d
    lda $dd0d
    lda #0
    sta $d011
    sta $d015
    sta $d017
    sta $d01b
    sta $d01c
    sta $d01d
    sta $d020
    sta $d021
    sta position
    sta stage
    sta phase
    sta frontBuffer
    sta fieldFlag
    sta fieldCounter
    sta fieldCounter+1
    lda #146
    sta bandTop
    lda #162
    sta bandBottom
    lda #0
    sta bandColor
    lda $dd02
    ora #3
    sta $dd02
    lda #3
    sta $dd00
    lda #8
    sta $d016
    lda #$18
    sta $d018
    ldx #0
!initialize:
    .for (var page = 0; page < 4; page++) {
        lda seedScreen+page*$100,x
        sta $0400+page*$100,x
        sta $0c00+page*$100,x
        lda seedColors+page*$100,x
        sta $d800+page*$100,x
    }
    inx
    bne !initialize-
    .for (var pair = 0; pair < 4; pair++) {
        lda #pairColors.get(pair)
        sta $d027+pair*2
        sta $d028+pair*2
    }
    jsr configureSprites
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
    lda #$1b
    sta $d011
    lda #0
    sta $d012
    lda #1
    sta $d019
    sta $d01a
ready:
    cli
main:
    lda fieldFlag
    beq main
    lda #0
    sta fieldFlag
!high:
    bit $d011
    bpl !high-
!bottom:
    lda $d012
    cmp #4
    bcc !bottom-
frameComplete:
    jsr advanceScene
    jmp main

advanceScene:
    inc position
    lda position
    cmp #192
    bcc !position+
    lda #0
    sta position
    lda frontBuffer
    eor #1
    sta frontBuffer
!position:
    lda position
    cmp #48
    bcs !characters+
    sta phase
    lda #0
    sta stage
    sta bandColor
    lda #146
    sta bandTop
    lda #162
    sta bandBottom
    jsr configureSprites
    jmp prepaintHidden
!characters:
    cmp #96
    bcs !wipe+
    sec
    sbc #48
    sta phase
    lda #1
    sta stage
    lda #6
    sta bandColor
    lda #146
    sta bandTop
    lda #162
    sta bandBottom
    lda phase
    beq !prepaint+
    jsr shiftRows
!prepaint:
    jmp prepaintHidden
!wipe:
    sec
    sbc #96
    sta phase
    lda #2
    sta stage
    lda #14
    sta bandColor
    lda phase
    cmp #48
    bcs !quadrants+
    clc
    adc #1
    asl
    sta temporary
    lda #146
    sec
    sbc temporary
    sta bandTop
    lda temporary
    cmp #88
    bcc !lower+
    lda #88
!lower:
    clc
    adc #162
    sta bandBottom
    rts
!quadrants:
    lda #50
    sta bandTop
    lda #250
    sta bandBottom
    jmp wipeQuadrant

configureSprites:
    lda #0
    sta spriteMsb
    .for (var pair = 0; pair < 4; pair++) {
        lda phase
        clc
        adc #pair
        tax
        lda pathY,x
        sta $d001+pair*4
        sta $d003+pair*4
        lda pathXLow,x
        sta $d000+pair*4
        clc
        adc #16
        sta $d002+pair*4
        lda pathXHigh,x
        adc #0
        beq !oddLow+
        lda spriteMsb
        ora #(2 << (pair*2))
        sta spriteMsb
    !oddLow:
        lda pathXHigh,x
        beq !evenLow+
        lda spriteMsb
        ora #(1 << (pair*2))
        sta spriteMsb
    !evenLow:
    }
    lda spriteMsb
    sta $d010
    rts

shiftRows:
    lda frontBuffer
    beq !frontA+
    lda #$0c
    bne !front+
!frontA:
    lda #$04
!front:
    sta shiftLeftRead+2
    sta shiftLeftWrite+2
    sta shiftRightRead+2
    sta shiftRightWrite+2
    // Add the row offsets to the common screen base in the patched highs.
    clc
    adc #>(10*40)
    sta shiftLeftRead+2
    sta shiftLeftWrite+2
    sta shiftLeftFirst+2
    sta shiftLeftLast+2
    lda frontBuffer
    beq !rightA+
    lda #$0c
    bne !right+
!rightA:
    lda #$04
!right:
    clc
    adc #>(14*40)
    sta shiftRightRead+2
    sta shiftRightWrite+2
    sta shiftRightFirst+2
    sta shiftRightLast+2
    ldx #0
shiftLeftFirst:
    lda $0400+10*40
    // This nonindexed first read is patched alongside its row loop below.
    sta savedCharacter
    lda $d800+10*40
    sta savedColor
!left:
shiftLeftRead:
    lda $0400+10*40+1,x
shiftLeftWrite:
    sta $0400+10*40,x
    lda $d800+10*40+1,x
    sta $d800+10*40,x
    inx
    cpx #39
    bne !left-
    lda savedCharacter
shiftLeftLast:
    sta $0400+10*40+39
    lda savedColor
    sta $d800+10*40+39
shiftRightFirst:
    lda $0400+14*40+39
    sta savedCharacter
    lda $d800+14*40+39
    sta savedColor
    ldx #38
!right:
shiftRightRead:
    lda $0400+14*40,x
shiftRightWrite:
    sta $0400+14*40+1,x
    lda $d800+14*40,x
    sta $d800+14*40+1,x
    dex
    bpl !right-
    lda savedCharacter
shiftRightLast:
    sta $0400+14*40
    lda savedColor
    sta $d800+14*40
    rts

prepaintHidden:
    lda position
    cmp #64
    bcs !done+
    lsr
    lsr
    lsr
    lsr
    sta temporary
    clc
    adc #>seedScreen
    sta SOURCE+1
    lda frontBuffer
    beq !hiddenB+
    lda #$04
    bne !hidden+
!hiddenB:
    lda #$0c
!hidden:
    clc
    adc temporary
    sta DESTINATION+1
    lda position
    asl
    asl
    asl
    asl
    sta SOURCE
    sta DESTINATION
    ldy #0
!byte:
    lda (SOURCE),y
    sta (DESTINATION),y
    iny
    cpy #16
    bne !byte-
!done:
    rts

wipeQuadrant:
    lda phase
    sec
    sbc #48
    asl
    asl
    tax
    lda wipeCommands+2,x
    cmp #255
    beq !done+
    sta wipeColumnA
    lda wipeCommands+3,x
    sta wipeColumnB
    lda wipeCommands,x
    sta wipeRow
    lda wipeCommands+1,x
    sta wipeEnd
!row:
    ldx wipeRow
    lda rowLow,x
    sta DESTINATION
    sta COLOR
    sta SEED_COLOR
    lda frontBuffer
    beq !screenA+
    lda #$0c
    bne !screen+
!screenA:
    lda #$04
!screen:
    clc
    adc rowHigh,x
    sta DESTINATION+1
    lda rowHigh,x
    clc
    adc #$d8
    sta COLOR+1
    lda rowHigh,x
    clc
    adc #>seedColors
    sta SEED_COLOR+1
    ldy wipeColumnA
    jsr clearCell
    ldy wipeColumnB
    jsr clearCell
    inc wipeRow
    lda wipeRow
    cmp wipeEnd
    bne !row-
!done:
    rts
clearCell:
    lda #32
    sta (DESTINATION),y
    // Restoring its seed color is invisible once its glyph is blank. At the
    // end all Color RAM is ready for the next atomic screen publication.
    lda (SEED_COLOR),y
    sta (COLOR),y
    rts

irq:
    pha
    txa
    pha
    tya
    pha
    jmp (irqPart)
displayTop:
    inc fieldCounter
    bne !counter+
    inc fieldCounter+1
!counter:
    lda #1
    sta fieldFlag
    lda #0
    sta $d020
    lda frontBuffer
    beq !screenA+
    lda #$38
    bne !screen+
!screenA:
    lda #$18
!screen:
    sta $d018
    lda stage
    bne !characters+
    lda #$ff
    sta $d015
    lda #<displayTop
    sta irqPart
    lda #>displayTop
    sta irqPart+1
    lda #0
    sta $d012
    jmp irqReturn
!characters:
    lda #0
    sta $d015
    lda #<displayBandTop
    sta irqPart
    lda #>displayBandTop
    sta irqPart+1
    lda bandTop
    sta $d012
    jmp irqReturn
displayBandTop:
    lda bandColor
    sta $d020
    lda #<displayBandBottom
    sta irqPart
    lda #>displayBandBottom
    sta irqPart+1
    lda bandBottom
    sta $d012
    jmp irqReturn
displayBandBottom:
    lda #0
    sta $d020
    lda #<displayTop
    sta irqPart
    lda #>displayTop
    sta irqPart+1
    lda #0
    sta $d012
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

position: .byte 0
stage: .byte 0
phase: .byte 0
frontBuffer: .byte 0
fieldFlag: .byte 0
fieldCounter: .word 0
irqPart: .word displayTop
bandTop: .byte 146
bandBottom: .byte 162
bandColor: .byte 0
spriteMsb: .byte 0
temporary: .byte 0
savedCharacter: .byte 0
savedColor: .byte 0
wipeColumnA: .byte 0
wipeColumnB: .byte 0
wipeRow: .byte 0
wipeEnd: .byte 0
rowLow: .fill 25, <(i*40)
rowHigh: .fill 25, >(i*40)
.assert "Controller stays below font", * <= $2000, true

* = $2000 "Shared own font plus local geometric glyphs"
    .import binary "build/font.bin"
* = $2800 "Own solid16x16sprite"
    .import binary "build/sprite.bin"
* = $4000 "Own initial character and color design"
seedScreen: .import binary "build/screen.bin"
seedColors: .import binary "build/colors.bin"
pathXLow: .import binary "build/path-x-low.bin"
pathXHigh: .import binary "build/path-x-high.bin"
pathY: .import binary "build/path-y.bin"
wipeCommands: .import binary "build/wipe.bin"
