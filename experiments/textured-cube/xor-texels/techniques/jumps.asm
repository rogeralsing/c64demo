// Exact arithmetic jumps to the next integer U/V row contribution.
// For f=(g*(y-originY))&255, the first changed floor is at distance
// floor((255-f)/g)+1 for0<g<256, or floor(f/(-g))+1 for-256<g<0.
// A zero gradient has no event; larger magnitudes change on every row.
// Fraction caches are rebuilt from the live gradients once per visible face.
.label texelJumpFractionU=$ce80
.label texelJumpFractionV=$cf80
.label texelJumpPrevious=$e6
.label texelJumpCurrent=$e7
.label texelJumpY=$e8
.label texelJumpBest=$e9
.label texelJumpDivisor=$ea
.label texelJumpDividend=$eb
.label texelJumpRemainder=$ec
.label texelJumpMode=$ed
.label texelJumpFractionAccU=$ee
.label texelJumpFractionAccV=$ef

texelTechniquePrepare:
    lda hybridDuDy
    ldx hybridDuDy+1
    jsr texelJumpClassify
    sta texelJumpMagnitudes
    stx texelJumpModes
    lda hybridDvDy
    ldx hybridDvDy+1
    jsr texelJumpClassify
    sta texelJumpMagnitudes+1
    stx texelJumpModes+1
    lda #0
    sta texelJumpFractionAccU
    sta texelJumpFractionAccV
    ldx projectedY
    beq !rows+
!origin:
    sec
    lda texelJumpFractionAccU
    sbc hybridDuDy
    sta texelJumpFractionAccU
    sec
    lda texelJumpFractionAccV
    sbc hybridDvDy
    sta texelJumpFractionAccV
    dex
    bne !origin-
!rows:
    ldy #0
!row:
    lda texelJumpFractionAccU
    sta texelJumpFractionU,y
    clc
    adc hybridDuDy
    sta texelJumpFractionAccU
    lda texelJumpFractionAccV
    sta texelJumpFractionV,y
    clc
    adc hybridDvDy
    sta texelJumpFractionAccV
    iny
    bpl !row-
    rts

// Input signed Q8 A:X, output magnitudeA and modeX:
// 0=no events,1=positive fraction,2=negative fraction,3=every row.
texelJumpClassify:
    cpx #0
    beq !positive+
    cpx #$ff
    bne !every+
    cmp #0
    beq !every+
    eor #$ff
    clc
    adc #1
    ldx #2
    rts
!positive:
    cmp #0
    beq !zero+
    ldx #1
    rts
!every:
    ldx #3
!zero:
    rts

texelBuildColumn:
    ldy texelColumnTop
    cpy texelColumnBottom
    bcc !nonempty+
    rts
!nonempty:
    jsr texelSampleColor
    sta texelJumpPrevious
    eor #3
    beq !next+
    jsr texelEmitTransition
!next:
    sty texelJumpY
    lda texelColumnBottom
    sec
    sbc texelJumpY
    sta texelJumpBest
    ldx #0
    jsr texelJumpNextAxis
    ldx #1
    jsr texelJumpNextAxis
    lda texelJumpY
    clc
    adc texelJumpBest
    tay
    cpy texelColumnBottom
    bcs !stop+
    jsr texelSampleColor
    sta texelJumpCurrent
    eor texelJumpPrevious
    beq !unchanged+
    jsr texelEmitTransition
!unchanged:
    lda texelJumpCurrent
    sta texelJumpPrevious
    jmp !next-
!stop:
    lda texelJumpPrevious
    eor #3
    beq !done+
    jsr texelEmitTransition
!done:
    rts

// Clamp the current jump distance to this axis's next floor change.
texelJumpNextAxis:
    lda texelJumpModes,x
    beq !done+
    cmp #3
    beq !one+
    sta texelJumpMode
    lda texelJumpMagnitudes,x
    sta texelJumpDivisor
    txa
    bne !v+
    lda texelJumpFractionU,y
    jmp !fraction+
!v:
    lda texelJumpFractionV,y
!fraction:
    ldx texelJumpMode
    dex
    bne !divide+
    eor #$ff
!divide:
    jsr texelJumpDivide
    cmp texelJumpBest
    bcs !done+
    sta texelJumpBest
!done:
    rts
!one:
    lda #1
    sta texelJumpBest
    rts

// Return min(255,floor(A/divisor)+1). Eight restoring steps avoid a pixel
// walk even for a one-unit gradient and a long constant-texture interval.
texelJumpDivide:
    sta texelJumpDividend
    lda #0
    sta texelJumpRemainder
    ldx #8
!bit:
    asl texelJumpDividend
    rol texelJumpRemainder
    lda texelJumpRemainder
    cmp texelJumpDivisor
    bcc !less+
    sbc texelJumpDivisor
    sta texelJumpRemainder
    inc texelJumpDividend
!less:
    dex
    bne !bit-
    lda texelJumpDividend
    clc
    adc #1
    bne !result+
    lda #255
!result:
    rts

texelJumpModes: .byte 0,0
texelJumpMagnitudes: .byte 0,0
texelJumpsEnd:
