// Two independently moving one-bit masks occupy opposite multicolor bits.
// Each logical sample therefore selects background, A, B, or their overlap.
.label sourceA = $f0
.label sourceB = $f2
.label destination = $f4
.label firstBits = $f6

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

nextImage:
    jsr render
    // Publish only a complete bitmap, at the next top-border boundary.
!waitHigh:
    bit $d011
    bpl !waitHigh-
!waitLow:
    bit $d011
    bmi !waitLow-
    lda drawBank
    sta $dd00

    // Keep this image and its sample coordinates unchanged through scanout.
!display:
    bit $d011
    bpl !display-
displayComplete:
    inc iteration
    inc offsetAX
    lda offsetAX
    and #63
    sta offsetAX
    lda offsetAY
    clc
    adc #2
    and #63
    sta offsetAY
    dec offsetBX
    lda offsetBX
    and #63
    sta offsetBX
    inc offsetBY
    lda offsetBY
    and #63
    sta offsetBY
    lda drawBitmapHi
    eor #$80
    sta drawBitmapHi
    lda drawBank
    eor #2
    sta drawBank
    jmp nextImage

render:
    lda offsetAX
    and #3
    tax
    lda planeAHi,x
    sta selectedAHi
    lda offsetBX
    and #3
    tax
    lda planeBHi,x
    sta selectedBHi
    lda offsetAX
    lsr
    lsr
    sta byteA
    lda offsetBX
    lsr
    lsr
    sta byteB
    lda #0
    sta row
!row:
    lda row
    clc
    adc offsetAY
    and #63
    tax
    lda sourceRowsLo,x
    sta sourceA
    lda sourceRowsHi,x
    clc
    adc selectedAHi
    sta sourceA+1
    lda row
    clc
    adc offsetBY
    and #63
    tax
    lda sourceRowsLo,x
    sta sourceB
    lda sourceRowsHi,x
    clc
    adc selectedBHi
    sta sourceB+1
    ldy row
    lda bitmapRowsLo,y
    sta destination
    lda bitmapRowsHi,y
    clc
    adc drawBitmapHi
    sta destination+1
    ldx #31
!column:
    txa
    clc
    adc byteA
    and #15
    tay
    lda (sourceA),y
    sta firstBits
    txa
    clc
    adc byteB
    and #15
    tay
    lda (sourceB),y
    ora firstBits
    ldy columnOffsets,x
    sta (destination),y
    iny
    sta (destination),y
    dex
    bpl !column-
    inc row
    lda row
    cmp #96
    bne !row-
    rts

iteration: .byte 0
offsetAX: .byte 0
offsetAY: .byte 0
offsetBX: .byte 17
offsetBY: .byte 11
drawBitmapHi: .byte $a0
drawBank: .byte 1
selectedAHi: .byte 0
selectedBHi: .byte 0
byteA: .byte 0
byteB: .byte 0
row: .byte 0

planeAHi: .byte $40,$44,$48,$4c
planeBHi: .byte $50,$54,$58,$5c
sourceRowsLo: .fill 64, <(i*16)
sourceRowsHi: .fill 64, >(i*16)
columnOffsets: .fill 32, i*8
bitmapRowsLo: .fill 96, <(floor(i/4)*320+mod(i,4)*2+32)
bitmapRowsHi: .fill 96, >(floor(i/4)*320+mod(i,4)*2+32)
.errorif * > $2000, "Code/tables overlap bitmap A"

// Prepared data contains one 64x64 ring mask in four horizontal sample phases.
// A occupies only $55 bits; B occupies only $aa bits of every packed byte.
.function PatternByte(index, phase, highBit) {
    .var y = floor(index/16)
    .var value = 0
    .for (var pixel=0; pixel<4; pixel++) {
        .var x = mod(mod(index,16)*4+pixel+phase,64)
        .var dx = 2*x-63
        .var dy = 2*y-63
        .var radius = floor(sqrt(dx*dx+dy*dy)/2)
        .var ink = mod(radius,8)<3
        .eval value = value | (ink ? 1 << ((3-pixel)*2+highBit) : 0)
    }
    .return value
}

* = $4000 "Prepared low-bit mask phases"
maskA:
    .fill 4096, PatternByte(mod(i,1024),floor(i/1024),0)
* = $5000 "Prepared high-bit mask phases"
maskB:
    .fill 4096, PatternByte(mod(i,1024),floor(i/1024),1)
.assert "Mask storage ends before VIC bank two", *, $6000
