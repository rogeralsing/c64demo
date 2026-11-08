// Original three-character-phase picture with paired sprite underlays.
// VIC banks use CIA2 DIRECTION bits; the data latch keeps both bank bits low.
BasicUpstart2(start)

* = $1000 "Packed-picture relocation and field controller"
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
    sta $d01a
    sta $d020
    sta $d021
    sta $dd00
    sta fieldCounter
    sta fieldCounter+1
    sta motion
    sta revealCount
    .import source "relocate.asm"

    // Identical initialized matrix codes also define otherwise-unused rows.
    // Each bank's relevant six-row portion follows 6*column+localRow exactly.
    .for (var row = 0; row < 24; row++) {
        ldx #0
        lda #mod(row,6)
    !column:
        .for (var bank = 0; bank < 4; bank++) {
            sta bank*$4000+$2400+row*40,x
        }
        clc
        adc #6
        inx
        cpx #40
        bne !column-
    }
    ldx #0
    lda #0
!clear:
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    sta $2300,x
    sta $6300,x
    sta $a300,x
    sta $e300,x
    inx
    bne !clear-
    sta $d017
    sta $d01c
    sta $d01d
    lda #$ff
    sta $d01b
    lda #8
    sta $d016
    lda #6
    sta $d021
    lda #$17
    sta $d011
    lda #$3c
    sta $dd02
    lda #$9c
    sta $d018
    lda #<nmiReturn
    sta $fffa
    sta $fffe
    lda #>nmiReturn
    sta $fffb
    sta $ffff
    // The first phase1 deliberately starts with a non-warmed retained pointer.
    lda #1
    sta phase
    lda #$8d
    sta lowPointer
    lda #$8c
    sta highPointer
ready:
    jmp frame

.import source "raster.asm"

setupPhase:
    lda phase
    beq !zero+
    cmp #1
    beq !one+
    lda #$8d
    sta lowPointer
    jmp !redLow+
!one:
    lda #$8e
    sta highPointer
    lda #5
    sta lowColor
    lda #2
    sta highColor
    jmp !replicate+
!zero:
    lda #$8c
    sta lowPointer
    lda #$8d
    sta highPointer
!redLow:
    lda #2
    sta lowColor
    lda #5
    sta highColor
!replicate:
    .for (var pair = 0; pair < 4; pair++) {
        lda lowPointer
        .for (var bank = 0; bank < 4; bank++) {
            sta bank*$4000+$27f8+pair
        }
        lda highPointer
        .for (var bank = 0; bank < 4; bank++) {
            sta bank*$4000+$27fc+pair
        }
        lda lowColor
        sta $d027+pair
        lda highColor
        sta $d02b+pair
    }
    lda phase
    asl
    clc
    adc #$9a
    sta $d018
    lda motion
    asl
    clc
    adc motion
    adc #120
    sta spriteBase
    lda #0
    sta spriteMsb
    .for (var pair = 0; pair < 4; pair++) {
        lda spriteBase
        clc
        adc #pair*24
        sta $d000+pair*2
        sta $d008+pair*2
        bcc !low+
        lda spriteMsb
        ora #((1<<pair)|(1<<(pair+4)))
        sta spriteMsb
    !low:
    }
    lda spriteMsb
    sta $d010
    rts

revealByte:
    ldx revealCount
    cpx #63
    beq !done+
    ldy revealPermutation,x
    .for (var mask = 0; mask < 3; mask++) {
        lda maskSource+mask*63,y
        .for (var bank = 0; bank < 4; bank++) {
            sta bank*$4000+$2300+mask*64,y
        }
    }
    inc revealCount
!done:
    rts

nmiReturn:
    rti
fieldCounter: .word 0
phase: .byte 1
motion: .byte 0
revealCount: .byte 0
lowPointer: .byte $8d
highPointer: .byte $8c
lowColor: .byte 5
highColor: .byte 2
spriteBase: .byte 120
spriteMsb: .byte 0
rasterNow: .byte 0
nextY: .byte 75
nextYLine: .byte 67
yRemaining: .byte 9
nextBankLine: .byte 102
nextDirection: .byte $3d
banksRemaining: .byte 3
revealPermutation: .fill 63, mod(i*17+5,63)

.function MaskByte(mask, index) {
    .var value = 0
    .var y = floor(index/3)
    .for (var bit = 0; bit < 8; bit++) {
        .var x = mod(index,3)*8+bit
        .eval value = (value << 1) | ((mod(x+2*y+floor(x/6),3) == mask) ? 1 : 0)
    }
    .return value
}
maskSource:
    .for (var mask = 0; mask < 3; mask++) {
        .fill 63, MaskByte(mask,i)
    }
.assert "Controller stays below packed font input", * <= $2000, true

.function PictureByte(bank, phase, index) {
    .var glyph = floor(index/8)
    .var column = floor(glyph/6)
    .var y = bank*48+mod(glyph,6)*8+mod(index,8)
    .var value = 0
    .for (var bit = 0; bit < 8; bit++) {
        .var x = column*8+bit
        .var dx = x-160
        .var dy = 2*y-191
        .var ring = floor((dx*dx+dy*dy)/192)
        .var ink = mod(ring+floor(x/7)+floor(y/5)+phase*5,16) < 8
        .eval value = (value << 1) | (ink ? 1 : 0)
    }
    .return value
}

* = $2000 "Packed original mathematical picture phases"
fontSource:
    .for (var bank = 0; bank < 4; bank++) {
        .for (var phase = 0; phase < 3; phase++) {
            .fill 1920, PictureByte(bank,phase,i)
        }
    }
.assert "Normal LOAD ends below I/O", *, $7a00
