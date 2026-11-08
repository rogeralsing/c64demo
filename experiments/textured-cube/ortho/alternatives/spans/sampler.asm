// Whole-parallelogram affine scanline candidate. Geometry and span coverage
// come from the common live orthographic path; only sampling differs here.
.label spPairs=$f6
.label spTail=$f7
.label spPackedPair=$f8

renderTexturedQuad:
    jsr prepareOrthoQuad
    lda area+1
    bmi !empty+
    ora area
    bne !nonempty+
!empty:
    rts
!nonempty:
    // Scaling V by16 modulo65536 preserves its wrapped texture-row nibble.
    .for (var bit=0; bit<4; bit++) {
        asl dvDx
        rol dvDx+1
        asl dvDy
        rol dvDy+1
    }
    // Each covered sample advances by the same exact quantized Q8 slopes.
    lda duDx
    sta spPrefixDuLo+1
    sta spBetweenDuLo+1
    sta spWithinDuLo+1
    sta spTailDuLo+1
    lda duDx+1
    sta spPrefixDuHi+1
    sta spBetweenDuHi+1
    sta spWithinDuHi+1
    sta spTailDuHi+1
    lda dvDx
    sta spPrefixDvLo+1
    sta spBetweenDvLo+1
    sta spWithinDvLo+1
    sta spTailDvLo+1
    lda dvDx+1
    sta spPrefixDvHi+1
    sta spBetweenDvHi+1
    sta spWithinDvHi+1
    sta spTailDvHi+1
    lda #0
    sta rowU
    sta rowU+1
    sta rowV
    sta rowV+1
    lda quadX
    sta leftAnchor
    lda quadY
    sec
    sbc minY
    tax
    beq !startRows+
!shiftY:
    sec
    lda rowU
    sbc duDy
    sta rowU
    lda rowU+1
    sbc duDy+1
    sta rowU+1
    sec
    lda rowV
    sbc dvDy
    sta rowV
    lda rowV+1
    sbc dvDy+1
    sta rowV+1
    dex
    bne !shiftY-
!startRows:
    lda minY
    sta scanY
!row:
    ldx scanY
    lda leftSpan,x
    sta spCurrentLeft
    cmp rightSpan,x
    bcc !nonemptyRow+
    jmp !rowDone+
!nonemptyRow:
    cmp leftAnchor
    beq !originReady+
    bcc !moveLeft+
    sec
    sbc leftAnchor
    tax
!moveRight:
    clc
    lda rowU
    adc duDx
    sta rowU
    lda rowU+1
    adc duDx+1
    sta rowU+1
    clc
    lda rowV
    adc dvDx
    sta rowV
    lda rowV+1
    adc dvDx+1
    sta rowV+1
    dex
    bne !moveRight-
    jmp !originReady+
!moveLeft:
    lda leftAnchor
    sec
    sbc spCurrentLeft
    tax
!leftStep:
    sec
    lda rowU
    sbc duDx
    sta rowU
    lda rowU+1
    sbc duDx+1
    sta rowU+1
    sec
    lda rowV
    sbc dvDx
    sta rowV
    lda rowV+1
    sbc dvDx+1
    sta rowV+1
    dex
    bne !leftStep-
!originReady:
    lda spCurrentLeft
    sta leftAnchor
    lsr
    ldx scanY
    clc
    adc matrixRowLow,x
    sta samplePointer
    lda matrixRowHigh,x
    adc drawScreenHigh
    sta samplePointer+1
    lda rightSpan,x
    sec
    sbc spCurrentLeft
    sta pixelsLeft
    lda scanY
    and #1
    asl
    clc
    adc #>texture
    sta spEvenTexture+2
    sta spTailTexture+2
    adc #1
    sta spPrefixTexture+2
    sta spOddTexture+2
    lda rowU
    sta pixelU
    lda rowU+1
    and #15
    sta pixelU+1
    lda rowV
    sta pixelV
    lda rowV+1
    sta pixelV+1
    ldy #0
    lda spCurrentLeft
    and #1
    beq !countPairs+
    dec pixelsLeft
!countPairs:
    lda pixelsLeft
    and #1
    sta spTail
    lda pixelsLeft
    lsr
    sta spPairs
    lda spCurrentLeft
    and #1
    beq !chooseBody+
    // An odd left endpoint contributes only this character's right sample.
    lda pixelV+1
    and #$f0
    ora pixelU+1
    tax
spPrefixTexture:
    lda textureShift2,x
    ora (samplePointer),y
    sta (samplePointer),y
    iny
    lda spPairs
    ora spTail
    bne !prefixAdvance+
    jmp !rowDone+
!prefixAdvance:
    clc
    lda pixelU
spPrefixDuLo:
    adc #0
    sta pixelU
    lda pixelU+1
spPrefixDuHi:
    adc #0
    and #15
    sta pixelU+1
    clc
    lda pixelV
spPrefixDvLo:
    adc #0
    sta pixelV
    lda pixelV+1
spPrefixDvHi:
    adc #0
    sta pixelV+1
!chooseBody:
    lda spPairs
    bne !firstPair+
    jmp !tailPixel+
!betweenPairs:
    clc
    lda pixelU
spBetweenDuLo:
    adc #0
    sta pixelU
    lda pixelU+1
spBetweenDuHi:
    adc #0
    and #15
    sta pixelU+1
    clc
    lda pixelV
spBetweenDvLo:
    adc #0
    sta pixelV
    lda pixelV+1
spBetweenDvHi:
    adc #0
    sta pixelV+1
!firstPair:
    lda pixelV+1
    and #$f0
    ora pixelU+1
    tax
spEvenTexture:
    lda texture,x
    sta spPackedPair
    clc
    lda pixelU
spWithinDuLo:
    adc #0
    sta pixelU
    lda pixelU+1
spWithinDuHi:
    adc #0
    and #15
    sta pixelU+1
    clc
    lda pixelV
spWithinDvLo:
    adc #0
    sta pixelV
    lda pixelV+1
spWithinDvHi:
    adc #0
    sta pixelV+1
    lda pixelV+1
    and #$f0
    ora pixelU+1
    tax
spOddTexture:
    lda textureShift2,x
    ora spPackedPair
    ora (samplePointer),y
    sta (samplePointer),y
    iny
    dec spPairs
    beq !pairsDone+
    jmp !betweenPairs-
!pairsDone:
    lda spTail
    bne !tailAdvance+
    jmp !rowDone+
!tailAdvance:
    clc
    lda pixelU
spTailDuLo:
    adc #0
    sta pixelU
    lda pixelU+1
spTailDuHi:
    adc #0
    and #15
    sta pixelU+1
    clc
    lda pixelV
spTailDvLo:
    adc #0
    sta pixelV
    lda pixelV+1
spTailDvHi:
    adc #0
    sta pixelV+1
!tailPixel:
    // The last even-X sample needs neither a partner nor a following UV step.
    lda pixelV+1
    and #$f0
    ora pixelU+1
    tax
spTailTexture:
    lda texture,x
    ora (samplePointer),y
    sta (samplePointer),y
!rowDone:
    clc
    lda rowU
    adc duDy
    sta rowU
    lda rowU+1
    adc duDy+1
    sta rowU+1
    clc
    lda rowV
    adc dvDy
    sta rowV
    lda rowV+1
    adc dvDy+1
    sta rowV+1
    inc scanY
    lda scanY
    cmp maxY
    beq !done+
    jmp !row-
!done:
    rts
spCurrentLeft: .byte 0
.assert "Whole-quad sampler remains below I/O", *<$d000,true
