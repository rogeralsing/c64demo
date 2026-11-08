// Original representation-switch teaching example, informed by the documented
// Nine character path. No Nine code, digit graphics or prepared bytes used.

.const DIGIT_X=144
.const DIGIT_Y=88
.const STAMP=$0400+11*40+18
.const STAMP_COLOR=$d800+11*40+18
.const FONT=$2800
.const FIRST_DIGIT_CHAR=128

BasicUpstart2(start)

start:
    sei
    lda #$7f
    sta $dc0d
    sta $dd0d
    lda $dc0d
    lda $dd0d
    lda #0
    sta $d01a
    sta $d015
    sta $d017
    sta $d01b
    sta $d01c
    sta $d01d
    sta $d020
    sta $d021
    sta ready
    sta nextFrame
    sta nextFrame+1
    lda #$ff
    sta shownFrame
    sta shownFrame+1
    sta shownMode

    // Read the actual character ROM only during initialization. The custom
    // digit uses codes 128..136; normal text uses the copied ordinary codes.
    lda #$33
    sta $01
    .for (var page=0; page<8; page++) {
        ldx #0
    !font:
        lda $d000+page*256,x
        sta FONT+page*256,x
        inx
        bne !font-
    }
    lda #$35
    sta $01
    lda #0
    ldx #7
!blank:
    sta FONT,x
    dex
    bpl !blank-

    // Transpose a 21-row, three-byte sprite into nine row-major 8x8 glyphs.
    // The final three pixel rows are blank padding, not extra sprite data.
    .for (var row=0; row<24; row++) {
        .for (var lane=0; lane<3; lane++) {
            .if (row<21) { lda digitSprite+row*3+lane } else { lda #0 }
            sta FONT+FIRST_DIGIT_CHAR*8+(floor(row/8)*3+lane)*8+(row&7)
        }
    }

    ldx #0
!screen:
    lda #0
    sta $0400,x
    sta $0500,x
    sta $0600,x
    sta $0700,x
    lda #1
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    inx
    bne !screen-
    .for (var row=0; row<7; row++) {
        ldx #39
    !title:
        lda title+row*40,x
        sta $0400+(row+2)*40,x
        dex
        bpl !title-
    }
    .for (var row=0; row<3; row++) {
        ldx #39
    !footer:
        lda footer+row*40,x
        sta $0400+(row+18)*40,x
        dex
        bpl !footer-
    }

    lda #3
    sta $dd02
    sta $dd00
    lda #$1a
    sta $d018
    lda #8
    sta $d016
    lda #$1b
    sta $d011
    lda #$c0
    sta $d010
    .for (var sprite=0; sprite<8; sprite++) {
        lda #DIGIT_Y+50
        sta $d001+sprite*2
    }
    lda #$81
    sta $07f9
    lda #2
    sta $d028
    .var positions=List().add(16,48,80,224,256,288)
    .var colors=List().add(6,4,3,8,7,13)
    .for (var sprite=2; sprite<8; sprite++) {
        lda #<(24+positions.get(sprite-2))
        sta $d000+sprite*2
        lda #$83
        sta $07f8+sprite
        lda #colors.get(sprite-2)
        sta $d027+sprite
    }
    lda #<nmi
    sta $fffa
    lda #>nmi
    sta $fffb
    lda #<irq
    sta $fffe
    lda #>irq
    sta $ffff
    lda #0
    sta $d012
    lda #1
    sta $d019
    sta $d01a
    cli

preparePacket:
    lda ready
    bne preparePacket
    lda nextFrame
    sta packetFrame
    and #$80
    beq !sprite+
    lda #1
    sta packetMode
    lda #$82
    sta packetPointer
    lda #200
    sta packetX
    lda #5
    sta packetColor
    jmp !marker+
!sprite:
    lda #0
    sta packetMode
    lda #$80
    sta packetPointer
    lda #DIGIT_X+24
    sta packetX
    lda #1
    sta packetColor
!marker:
    lda nextFrame+1
    sta packetFrame+1
    ldx nextFrame
    lda markerOffsets,x
    clc
    adc #DIGIT_X+24
    sta packetMarkerX
    // All packet fields are ready before the single ownership flag changes.
    lda #1
packetPublished:
    sta ready
    inc nextFrame
    bne !next+
    inc nextFrame+1
!next:
    jmp preparePacket

irq:
    pha
    txa
    pha
    tya
    pha
    lda ready
    bne !consume+
    jmp !done+
!consume:
    // Screen, Color RAM and sprite registers commit in the same top-border
    // IRQ. Preparing a future packet never erases a currently visible stamp.
    lda #0
    .for (var row=0; row<3; row++) {
        .for (var column=0; column<3; column++) {
            sta STAMP+row*40+column
        }
    }
    lda packetMode
    beq !sprite+
    .for (var row=0; row<3; row++) {
        .for (var column=0; column<3; column++) {
            lda #FIRST_DIGIT_CHAR+row*3+column
            sta STAMP+row*40+column
            lda #1
            sta STAMP_COLOR+row*40+column
        }
    }
!sprite:
    lda packetPointer
    sta $07f8
    lda packetX
    sta $d000
    lda packetColor
    sta $d027
    lda packetMarkerX
    sta $d002
    lda #$ff
    sta $d015
    lda packetMode
    sta shownMode
    clc
    adc #1
    sta $0400+20*40+26
    lda packetFrame
    sta shownFrame
    lda packetFrame+1
    sta shownFrame+1
    lda #0
    sta ready
!done:
    lda #1
    sta $d019
    pla
    tay
    pla
    tax
    pla
nmi:
    rti

ready: .byte 0
nextFrame: .word 0
shownFrame: .word 0
shownMode: .byte 0
packetFrame: .word 0
packetMode: .byte 0
packetPointer: .byte 0
packetX: .byte 0
packetColor: .byte 0
packetMarkerX: .byte 0
markerOffsets:
    .fill 256, round(64*cos(i*2*PI/256))&255

.encoding "screencode_upper"
title:
line0: .text "   SPRITE / CHARACTER REPRESENTATION"
    .fill 40-(*-line0),$20
line1: .text ""
    .fill 40-(*-line1),$20
line2: .text " A: DIGIT USES SPRITE 0 (EIGHT OBJECTS)"
    .fill 40-(*-line2),$20
line3: .text " B: DIGIT USES 3X3 CHARACTERS (NINE)"
    .fill 40-(*-line3),$20
line4: .text " RED BALL: BEHIND A / IN FRONT OF B"
    .fill 40-(*-line4),$20
line5: .text " B REUSES SPRITE 0 FOR THE GREEN STAR"
    .fill 40-(*-line5),$20
line6: .text " ALL EIGHT HARDWARE SLOTS STAY ACTIVE"
    .fill 40-(*-line6),$20
footer:
line7: .text " SAME 24X21 DIGIT + THREE BLANK ROWS"
    .fill 40-(*-line7),$20
line8: .text " VIEW CHANGES EVERY 128 PAL FIELDS"
    .fill 40-(*-line8),$20
line9: .text "            CURRENT VIEW:"
    .fill 40-(*-line9),$20
.errorif *-footer != 3*40, "Footer must contain three rows"

*=$2000 "Own sprite artwork"
digitSprite:
    .var digitRows=List().add($0e,$11,$11,$0f,$01,$02,$1c)
    .for (var row=0; row<21; row++) {
        .for (var lane=0; lane<3; lane++) {
            .var value=0
            .for (var bit=0; bit<8; bit++) {
                .var x=lane*8+bit
                .if (x>=4 && x<19) {
                    .var column=floor((x-4)/3)
                    .if ((digitRows.get(floor(row/3))&(16>>column))!=0) {
                        .eval value=value|(128>>bit)
                    }
                }
            }
            .byte value
        }
    }
    .byte 0
markerSprite:
    .for (var row=0; row<21; row++) {
        .for (var lane=0; lane<3; lane++) {
            .var value=0
            .for (var bit=0; bit<8; bit++) {
                .var x=lane*8+bit
                .if ((x-11)*(x-11)+(row-10)*(row-10)<=81) {
                    .eval value=value|(128>>bit)
                }
            }
            .byte value
        }
    }
    .byte 0
starSprite:
    .for (var row=0; row<21; row++) {
        .for (var lane=0; lane<3; lane++) {
            .var value=0
            .for (var bit=0; bit<8; bit++) {
                .var dx=abs(lane*8+bit-11)
                .var dy=abs(row-10)
                .if (dx+dy<=10 && (dx<3 || dy<3 || dx==dy)) {
                    .eval value=value|(128>>bit)
                }
            }
            .byte value
        }
    }
    .byte 0
smallSprite:
    .for (var row=0; row<21; row++) {
        .for (var lane=0; lane<3; lane++) {
            .var value=0
            .for (var bit=0; bit<8; bit++) {
                .var x=lane*8+bit
                .if ((x-11)*(x-11)+(row-10)*(row-10)<=16) {
                    .eval value=value|(128>>bit)
                }
            }
            .byte value
        }
    }
    .byte 0
