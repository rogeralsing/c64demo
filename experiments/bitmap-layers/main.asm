// Two independently moving one-bit masks occupy opposite multicolor bits.
// Each logical sample therefore selects background, A, B, or their overlap.
// THREE_LAYER_PATTERN adds a third independently sampled mask and uses XOR
// selector composition. The default two-plane OR example stays unchanged.
.label sourceA = $f0
.label sourceB = $f2
.label destination = $f4
.label firstBits = $f6
#if THREE_LAYER_PATTERN
.label sourceC = $f8
#endif

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
#if THREE_LAYER_PATTERN
    lda offsetCX
    clc
    adc #2
    and #63
    sta offsetCX
    dec offsetCY
    lda offsetCY
    and #63
    sta offsetCY
#endif
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
#if THREE_LAYER_PATTERN
    lda offsetCX
    and #3
    tax
    lda planeCHi,x
    sta selectedCHi
    lda offsetCX
    lsr
    lsr
    sta byteC
    // These reusable per-image indices remove wrapping arithmetic from each
    // pixel-row sampling pass. They are not prepared animation images.
    ldx #31
!indices:
    txa
    clc
    adc byteA
    and #15
    sta columnsA,x
    txa
    clc
    adc byteB
    and #15
    sta columnsB,x
    txa
    clc
    adc byteC
    and #15
    sta columnsC,x
    dex
    bpl !indices-
#endif
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
#if THREE_LAYER_PATTERN
    lda row
    clc
    adc offsetCY
    and #63
    tax
    lda sourceRowsLo,x
    sta sourceC
    lda sourceRowsHi,x
    clc
    adc selectedCHi
    sta sourceC+1
#endif
    ldy row
    lda bitmapRowsLo,y
    sta destination
    lda bitmapRowsHi,y
    clc
    adc drawBitmapHi
    sta destination+1
#if THREE_LAYER_PATTERN
    .for (var column=0; column<32; column++) {
        ldy columnsA+column
        lda (sourceA),y
        sta firstBits
        ldy columnsB+column
        lda (sourceB),y
        eor firstBits
        sta firstBits
        ldy columnsC+column
        lda (sourceC),y
        eor firstBits
        ldy #column*8
        sta (destination),y
        iny
        sta (destination),y
    }
#else
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
#endif
    inc row
    lda row
    cmp #96
#if THREE_LAYER_PATTERN
    beq !done+
    jmp !row-
!done:
#else
    bne !row-
#endif
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
#if THREE_LAYER_PATTERN
offsetCX: .byte 9
offsetCY: .byte 29
selectedCHi: .byte 0
byteC: .byte 0
columnsA: .fill 32, 0
columnsB: .fill 32, 0
columnsC: .fill 32, 0
planeCHi: .byte $60,$64,$68,$6c
#endif

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

#if THREE_LAYER_PATTERN
.function ThreePatternByte(index, phase, layer) {
    .var y = floor(index/16)
    .var value = 0
    .for (var pixel=0; pixel<4; pixel++) {
        .var x = mod(mod(index,16)*4+pixel+phase,64)
        .var dx = abs(2*x-63)
        .var dy = abs(2*y-63)
        .var ink = layer==0 ? mod(dx+dy,32)<8 : (layer==1 ? mod(max(dx,dy),16)<4 : mod(x+3*y,16)<4)
        .eval value = value | (ink ? (layer+1) << ((3-pixel)*2) : 0)
    }
    .return value
}
#endif

* = $4000 "Prepared low-bit mask phases"
maskA:
#if THREE_LAYER_PATTERN
    .fill 4096, ThreePatternByte(mod(i,1024),floor(i/1024),0)
#else
    .fill 4096, PatternByte(mod(i,1024),floor(i/1024),0)
#endif
* = $5000 "Prepared high-bit mask phases"
maskB:
#if THREE_LAYER_PATTERN
    .fill 4096, ThreePatternByte(mod(i,1024),floor(i/1024),1)
* = $6000 "Prepared third-selector mask phases"
maskC:
    .fill 4096, ThreePatternByte(mod(i,1024),floor(i/1024),2)
.errorif * != $7000, "Three prepared mask planes have wrong size"
#else
    .fill 4096, PatternByte(mod(i,1024),floor(i/1024),1)
.assert "Mask storage ends before VIC bank two", *, $6000
#endif
