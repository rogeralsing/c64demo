// Endpoint masks follow the existing sprite-vector span contract, adapted to
// four two-bit samples per glyph row and a dynamically selected glyph address.
paintSpanRow:
    lda spanLeft
    cmp spanRight
    bcc !nonempty+
    rts
!nonempty:
    and #3
    tax
    lda leftMasks,x
    sta spanFirstMask
    lda spanLeft
    lsr
    lsr
    sta cellColumn
    sta spanFirstColumn
    sec
    lda spanRight
    sbc #1
    pha
    and #3
    tax
    lda rightMasks,x
    sta spanLastMask
    pla
    lsr
    lsr
    sta lastColumn
    lda spanY
    lsr
    lsr
    lsr
    sta cellRow
    ldx material
    lda spanY
    and #1
    beq !even+
    lda patternsOdd,x
    bne !pattern+
!even:
    lda patternsEven,x
!pattern:
    sta patternByte
!column:
    ldx cellRow
    lda cellColumn
    cmp firstFull,x
    bcc !partial+
    cmp endFull,x
    bcc !next+
!partial:
    jsr selectCell
    jsr ensurePrivateGlyph
    bcc !allocated+
    jmp capacityFailure
!allocated:
    lda #$ff
    ldx cellColumn
    cpx spanFirstColumn
    bne !notFirst+
    and spanFirstMask
!notFirst:
    cpx lastColumn
    bne !notLast+
    and spanLastMask
!notLast:
    sta spanMask
    lda spanY
    and #7
    tay
    lda spanMask
    eor #$ff
    and (GLYPH_POINTER),y
    sta savedOld
    lda patternByte
    and spanMask
    ora savedOld
    sta (GLYPH_POINTER),y
!next:
    lda cellColumn
    cmp lastColumn
    beq !done+
    inc cellColumn
    jmp !column-
!done:
    rts

selectCell:
    ldx cellRow
    clc
    lda matrixRowLow,x
    adc cellColumn
    sta CELL_POINTER
    lda matrixRowHigh,x
    adc drawScreenHigh
    sta CELL_POINTER+1
    rts

setGlyphPointer:
    pha
    and #31
    asl
    asl
    asl
    sta GLYPH_POINTER
    pla
    lsr
    lsr
    lsr
    lsr
    lsr
    clc
    adc drawFontHigh
    sta GLYPH_POINTER+1
    rts

ensurePrivateGlyph:
    ldy #0
    lda (CELL_POINTER),y
    cmp #FIRST_PRIVATE
    bcc allocateGlyph
    jsr setGlyphPointer
    clc
    rts
allocateGlyph:
    sta sourceGlyph
    lda allocatorFull
    beq !space+
    lda #1
    sta allocationError
    sec
    rts
!space:
    lda sourceGlyph
    asl
    asl
    asl
    sta COPY_POINTER
    lda drawFontHigh
    sta COPY_POINTER+1
    lda nextFree
    sta newGlyph
    jsr setGlyphPointer
    ldy #7
!copy:
    lda (COPY_POINTER),y
    sta (GLYPH_POINTER),y
    dey
    bpl !copy-
    ldy #0
    lda newGlyph
    sta (CELL_POINTER),y
    inc nextFree
    bne !done+
    lda #1
    sta allocatorFull
!done:
    clc
    rts

capacityFailure:
    lda #2
    sta $d020
capacityStopped:
    jmp capacityStopped
