// API A=size1..9, X/Y=top-left pixel position in the160x128 point window.
// Per-cell codes name private glyphs, so OR overlap never damages a shared tile.
stampPoint:
    sta pointSize
    stx pointX
    sty pointY
    sec
    sbc #1
    asl
    asl
    asl
    sta sourceOffset
    txa
    and #7
    ora sourceOffset
    tax
    lda patternLo,x
    sta patternPointer
    lda patternHi,x
    sta patternPointer+1
    lda pointX
    lsr
    lsr
    lsr
    sta pointColumn
    lda #0
    sta stampColumn
    sta sourceOffset
!column:
    lda pointColumn
    clc
    adc stampColumn
    sta characterColumn
    lda #0
    sta stampRow
!row:
    lda stampRow
    clc
    adc sourceOffset
    tay
    lda (patternPointer),y
    beq !skip+
    sta stampBits
    lda pointY
    clc
    adc stampRow
    sta pixelRow
    lsr
    lsr
    lsr
    tax
    clc
    lda screenRowLo,x
    adc characterColumn
    sta screenPointer
    lda screenRowHi,x
    adc drawScreenHigh
    sta screenPointer+1
    jsr getCellGlyph
    lda pixelRow
    and #7
    tay
    lda stampBits
    ora (glyphPointer),y
    sta (glyphPointer),y
!skip:
    inc stampRow
    lda stampRow
    cmp pointSize
    bne !row-
    inc stampColumn
    lda stampColumn
    cmp #2
    beq !done+
    lda pointSize
    sta sourceOffset
    jmp !column-
!done:
    rts
getCellGlyph:
    ldy #0
    lda (screenPointer),y
    bne !occupied+
    lda nextCode
    cmp #PRIVATE_LIMIT
    bcs allocationFault
    sta (screenPointer),y
glyphAllocated:
    inc nextCode
    jsr glyphAddress
    ldy #7
    lda #0
!blank:
    sta (glyphPointer),y
    dey
    bpl !blank-
    rts
!occupied:
    cmp #PRIVATE_LIMIT
    bcs allocationFault
    jmp glyphAddress
glyphAddress:
    sta glyphCode
    asl
    asl
    asl
    sta glyphPointer
    lda glyphCode
    lsr
    lsr
    lsr
    lsr
    lsr
    clc
    adc drawFontHigh
    sta glyphPointer+1
    rts
allocationFault:
    lda #2
    sta $d020
    jmp allocationFault
