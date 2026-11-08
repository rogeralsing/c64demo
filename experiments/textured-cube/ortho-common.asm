// One canonical affine plane from the first three rounded corners. Return
// signed Q8 gradients and exact convex-quad top-left spans. The fourth rounded
// corner may differ from this UV plane by at most one sample; geometry retains
// its high precision until each screen corner is rounded independently.
prepareOrthoQuad:
    lda #0
    sta triangleIndex
    jsr loadTriangle
    jsr triangleArea
    lda dy2
    sec
    sbc dy1
    jsr divideGradient
    sta duDx
    stx duDx+1
    lda dx1
    sec
    sbc dx2
    jsr divideGradient
    sta duDy
    stx duDy+1
    lda #0
    sec
    sbc dy1
    jsr divideGradient
    sta dvDx
    stx dvDx+1
    lda dx1
    jsr divideGradient
    sta dvDy
    stx dvDy+1
    jmp prepareOrthoBounds

renderFlatQuad:
    jsr prepareOrthoBounds
    jmp renderFlatSpans

prepareOrthoBounds:
    lda quadY
    sta minY
    sta maxY
    ldx #1
!bounds:
    lda quadY,x
    cmp minY
    bcs !notMin+
    sta minY
!notMin:
    cmp maxY
    bcc !notMax+
    sta maxY
!notMax:
    inx
    cpx #4
    bne !bounds-
    jsr buildQuadSpans
    rts

buildQuadSpans:
    lda #0
    sta edgeIndex
!edge:
    ldy edgeIndex
    tya
    clc
    adc #1
    cmp #4
    bcc !nextIndex+
    lda #0
!nextIndex:
    tax
    lda quadY,x
    cmp quadY,y
    bne !notHorizontal+
    jmp !nextEdge+
!notHorizontal:
    bcc !leftEdge+
    // Original edge moves down, hence supplies the exclusive right crossing.
    lda #>rightSpan
    sta quadSpanStore+2
    lda quadY,x
    sta bottomY
    lda quadX,x
    sta bottomX
    lda quadY,y
    sta topY
    lda quadX,y
    sta walkX
    jmp !setup+
!leftEdge:
    lda #>leftSpan
    sta quadSpanStore+2
    lda quadY,y
    sta bottomY
    lda quadX,y
    sta bottomX
    lda quadY,x
    sta topY
    lda quadX,x
    sta walkX
!setup:
    lda bottomY
    sec
    sbc topY
    sta walkHeight
    lda #0
    sta walkNegative
    sta walkStep
    sta walkError
    lda bottomX
    sec
    sbc walkX
    bpl !magnitude+
    inc walkNegative
    eor #$ff
    clc
    adc #1
!magnitude:
    sta walkRemainder
!divide:
    lda walkRemainder
    cmp walkHeight
    bcc !quotient+
    sbc walkHeight
    sta walkRemainder
    inc walkStep
    jmp !divide-
!quotient:
    lda walkNegative
    beq !walk+
    lda walkRemainder
    beq !negateStep+
    inc walkStep
    lda walkHeight
    sec
    sbc walkRemainder
    sta walkRemainder
!negateStep:
    lda #0
    sec
    sbc walkStep
    sta walkStep
!walk:
    ldy topY
!row:
    lda walkError
    beq !integer+
    lda walkX
    clc
    adc #1
    bne !store+
!integer:
    lda walkX
!store:
quadSpanStore:
    sta leftSpan,y
    clc
    lda walkX
    adc walkStep
    sta walkX
    clc
    lda walkError
    adc walkRemainder
    cmp walkHeight
    bcc !remainder+
    sbc walkHeight
    inc walkX
!remainder:
    sta walkError
    iny
    cpy bottomY
    bne !row-
!nextEdge:
    inc edgeIndex
    lda edgeIndex
    cmp #4
    beq !done+
    jmp !edge-
!done:
    rts
