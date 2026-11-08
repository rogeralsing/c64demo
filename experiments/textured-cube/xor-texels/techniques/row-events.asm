// Shared row-coordinate events for the exact separable Q8 texture mapping.
// Equal packed row contributions imply equal sampled texels for every column.
// A next-event table avoids searching past events above a column's clipped top.
// Preparation owns CE80..CEFF and E6; column replay owns E7. Clobbers A/X/Y.
.label texelRowEventNext = $ce80
.label texelRowEventPacked = $e6
.label texelRowEventColor = $e7

texelTechniquePrepare:
    lda hybridMinY
    cmp hybridMaxY
    bcs !done+
    ldx hybridMaxY
    ldy hybridMaxY
    dey
    lda hybridRowUCache,y
    ora hybridRowVCache,y
    sta texelRowEventPacked
!row:
    // X is the next strictly greater Y where the packed contribution changes,
    // or maxY when the remainder of the bounding interval is constant.
    txa
    sta texelRowEventNext,y
    cpy hybridMinY
    beq !done+
    dey
    lda hybridRowUCache,y
    ora hybridRowVCache,y
    cmp texelRowEventPacked
    beq !row-
    sta texelRowEventPacked
    tya
    tax
    inx
    jmp !row-
!done:
    rts

texelBuildColumn:
    ldy texelColumnTop
    cpy texelColumnBottom
    bcs !done+
    jsr texelSampleColor
    sta texelRowEventColor
    eor #3
    beq !next+
    jsr texelEmitTransition
!next:
    lda texelRowEventNext,y
    cmp texelColumnBottom
    bcs !close+
    tay
    jsr texelSampleColor
    cmp texelRowEventColor
    beq !next-
    tax
    eor texelRowEventColor
    stx texelRowEventColor
    jsr texelEmitTransition
    jmp !next-
!close:
    ldy texelColumnBottom
    lda texelRowEventColor
    eor #3
    beq !done+
    jmp texelEmitTransition
!done:
    rts
