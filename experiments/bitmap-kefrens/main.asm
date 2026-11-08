// Original bitmap ribbons with direction/speed controls on joystick port two.
// Six overlapping shaded bars are composed at runtime, never stored as frames.
.label lineBuffer = $80
.label destination = $f0

BasicUpstart2(start)

start:
    sei
    lda #$35
    sta $01
    lda #$7f
    sta $dc0d
    sta $dd0d
    lda $dc0d
    lda $dd0d
    lda #$e0
    sta $dc02
    lda #0
    sta $dc03
    lda #$ff
    sta $dc00
    lda #0
    sta $d01a
    sta $d015
    sta $d020
    sta $d021
    lda $dd02
    ora #3
    sta $dd02
    lda #3
    sta $dd00
    lda #$3b
    sta $d011
    lda #$18
    sta $d016
    sta $d018
    ldx #0
!attributes:
    lda #$34
    sta $0400,x
    sta $0500,x
    sta $0600,x
    sta $0700,x
    sta $8400,x
    sta $8500,x
    sta $8600,x
    sta $8700,x
    lda #1
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    inx
    bne !attributes-
    lda #0
    ldx #0
    ldy #32
!clear:
clearA:
    sta $2000,x
clearB:
    sta $a000,x
    inx
    bne !clear-
    inc clearA+2
    inc clearB+2
    dey
    bne !clear-

inputSample:
    jsr readControls
    lda orientation
    beq !vertical+
    jsr renderHorizontal
    jmp !publish+
!vertical:
    jsr renderVertical
!publish:
!waitHigh:
    bit $d011
    bpl !waitHigh-
!waitLow:
    bit $d011
    bmi !waitLow-
    lda drawBank
    sta $dd00
!scanout:
    bit $d011
    bpl !scanout-
displayComplete:
    inc iteration
    lda phase
    clc
    adc speed
    sta phase
    lda drawBitmapHi
    eor #$80
    sta drawBitmapHi
    lda drawBank
    eor #2
    sta drawBank
    jmp inputSample

readControls:
    lda $dc00
    and #31
    sta lastJoystick
    and #1
    bne !down+
    lda speed
    cmp #4
    beq !down+
    inc speed
!down:
    lda lastJoystick
    and #2
    bne !left+
    lda speed
    cmp #1
    beq !left+
    dec speed
!left:
    lda lastJoystick
    and #4
    bne !right+
    lda bend
    cmp #1
    beq !right+
    dec bend
!right:
    lda lastJoystick
    and #8
    bne !fire+
    lda bend
    cmp #4
    beq !fire+
    inc bend
!fire:
    lda lastJoystick
    and #16
    bne !released+
    lda fireHeld
    bne !done+
    lda orientation
    eor #1
    sta orientation
    lda #1
    sta fireHeld
!done:
    rts
!released:
    lda #0
    sta fireHeld
    rts

renderVertical:
    lda phase
    sta scanPhase
    lda #0
    sta scan
!row:
    lda #0
    ldx #31
!clear:
    sta lineBuffer,x
    dex
    bpl !clear-
    lda scanPhase
    sta barPhase
    lda #6
    sta barsLeft
!bar:
    ldx barPhase
    lda widePositions,x
    pha
    and #3
    tax
    lda shiftOffsets,x
    sta shapeOffset
    pla
    lsr
    lsr
    tax
    ldy shapeOffset
    lda #5
    sta spanLeft
!span:
    lda lineBuffer,x
    and verticalMasks,y
    ora verticalInk,y
    sta lineBuffer,x
    inx
    iny
    dec spanLeft
    bne !span-
    lda barPhase
    clc
    adc #37
    sta barPhase
    dec barsLeft
    bne !bar-

    ldy scan
    lda rowAddressLo,y
    sta destination
    lda rowAddressHi,y
    clc
    adc drawBitmapHi
    sta destination+1
    ldx #31
!flush:
    lda lineBuffer,x
    ldy columnOffsets,x
    sta (destination),y
    iny
    sta (destination),y
    dex
    bpl !flush-
    lda scanPhase
    clc
    adc bend
    sta scanPhase
    inc scan
    lda scan
    cmp #64
    beq !done+
    jmp !row-
!done:
    rts

renderHorizontal:
    lda phase
    sta scanPhase
    lda #0
    sta scan
!column:
    lda #0
    ldx #63
!clear:
    sta lineBuffer,x
    dex
    bpl !clear-
    lda scanPhase
    sta barPhase
    lda #6
    sta barsLeft
!bar:
    ldx barPhase
    lda narrowPositions,x
    tax
    ldy #0
!span:
    lda horizontalInk,y
    sta lineBuffer,x
    inx
    iny
    cpy #8
    bne !span-
    lda barPhase
    clc
    adc #37
    sta barPhase
    dec barsLeft
    bne !bar-

    lda #0
    sta row
!flush:
    ldy row
    lda rowAddressLo,y
    clc
    ldx scan
    adc columnOffsets,x
    sta destination
    lda rowAddressHi,y
    adc drawBitmapHi
    sta destination+1
    ldx row
    lda lineBuffer,x
    ldy #0
    sta (destination),y
    iny
    sta (destination),y
    inc row
    lda row
    cmp #64
    bne !flush-
    lda bend
    asl
    asl
    clc
    adc scanPhase
    sta scanPhase
    inc scan
    lda scan
    cmp #32
    beq !done+
    jmp !column-
!done:
    rts

phase: .byte 0
iteration: .byte 0
speed: .byte 1
bend: .byte 2
orientation: .byte 0
fireHeld: .byte 0
lastJoystick: .byte 31
drawBitmapHi: .byte $a0
drawBank: .byte 1
scan: .byte 0
scanPhase: .byte 0
barPhase: .byte 0
barsLeft: .byte 0
spanLeft: .byte 0
shapeOffset: .byte 0
row: .byte 0

shiftOffsets: .byte 0,5,10,15
columnOffsets: .fill 32, i*8
rowAddressLo: .fill 64, <(floor((36+2*i)/8)*320+mod(36+2*i,8)+32)
rowAddressHi: .fill 64, >(floor((36+2*i)/8)*320+mod(36+2*i,8)+32)
widePositions: .fill 256, round(56+48*sin(i*2*PI/256))
narrowPositions: .fill 256, round(28+24*sin(i*2*PI/256))

.function ShapeByte(index,mask) {
    .var phase = floor(index/5)
    .var column = mod(index,5)
    .var value = 0
    .for (var pixel=0; pixel<4; pixel++) {
        .var offset = column*4+pixel-phase
        .var color = 0
        .if (offset<0 || offset>=16) {
            .eval color = mask ? 3 : 0
        } else {
            .eval color = mask ? 0 : (offset<2 || offset>=14 ? 1 : (offset<4 || offset>=12 ? 2 : 3))
        }
        .eval value = value*4+color
    }
    .return value
}
verticalMasks: .fill 20, ShapeByte(i,true)
verticalInk: .fill 20, ShapeByte(i,false)
horizontalInk: .byte $55,$aa,$ff,$ff,$ff,$ff,$aa,$55
.errorif * > $2000, "Code/data overlap bitmap A"
