// Factor the live plasma into 16 horizontal, 16 vertical and 32 diagonal
// scalar waves. No image phases or geometry are prepared on the host.
// The three sums are at most 93, so the second ADC cannot inherit a carry.
buildTexture:
    lda phase
    asl
    asl
    sta textureBuilderMotion
    tax
    ldy #0
!horizontal:
    lda plasmaWave,x
    sta textureWaveU,y
    txa
    clc
    adc #16
    tax
    iny
    cpy #16
    bne !horizontal-
    lda textureBuilderMotion
    asl
    eor #$ff
    clc
    adc #1
    tax
    ldy #0
!vertical:
    lda plasmaWave,x
    sta textureWaveV,y
    txa
    clc
    adc #16
    tax
    iny
    cpy #16
    bne !vertical-
    ldx textureBuilderMotion
    ldy #0
!diagonal:
    lda plasmaWave,x
    sta textureWaveDiagonal,y
    txa
    clc
    adc #8
    tax
    iny
    cpy #32
    bne !diagonal-
    ldx #0
    ldy #0
!row:
    .for (var u=0; u<16; u++) {
        lda textureWaveU+u
        clc
        adc textureWaveV,x
        adc textureWaveDiagonal+u,x
        lsr
        lsr
        lsr
        and #3
        sta texture+u,y
        asl
        asl
        sta textureShift2+u,y
        asl
        asl
        sta textureShift4+u,y
        asl
        asl
        sta textureShift6+u,y
    }
    tya
    clc
    adc #16
    tay
    inx
    cpx #16
    beq !done+
    jmp !row-
!done:
    rts
textureBuilderMotion: .byte 0
.align $40
textureWaveU: .fill 16,0
textureWaveV: .fill 16,0
textureWaveDiagonal: .fill 32,0
