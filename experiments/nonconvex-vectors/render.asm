renderScene:
    lda frontBuffer
    eor #1
    sta drawBuffer
    beq !bufferA+
    ldx #0
!clearB:
    .for (var page=0;page<8;page++) {
        lda background+page*256,x
        sta $2800+page*256,x
    }
    inx
    bne !clearB-
    jmp !cleared+
!bufferA:
    ldx #0
!clearA:
    .for (var page=0;page<8;page++) {
        lda background+page*256,x
        sta $2000+page*256,x
    }
    inx
    bne !clearA-
!cleared:
    lda #0
    sta triangleIndex
!triangle:
    ldx triangleIndex
    lda triangleVisible,x
    bne !visible+
    jmp !nextTriangle+
!visible:
    lda triangleColors,x
    tax
    lda repeatColor,x
    sta ink
    jsr loadTriangle
    ldx #127
!clearSpans:
    lda #$ff
    sta spanLeft,x
    lda #0
    sta spanRight,x
    dex
    bpl !clearSpans-
    lda #$ff
    sta minimumY
    lda #0
    sta maximumY
    ldx vertexA
    jsr includeY
    ldx vertexB
    jsr includeY
    ldx vertexC
    jsr includeY
    ldx vertexA
    ldy vertexB
    jsr prepareEdge
    ldx vertexB
    ldy vertexC
    jsr prepareEdge
    ldx vertexC
    ldy vertexA
    jsr prepareEdge
trianglePrepared:
    lda minimumY
    sta currentRow
!row:
    ldy currentRow
    lda spanLeft,y
    cmp spanRight,y
    bcs !empty+
    pha
    and #3
    tax
    lda leftMasks,x
    sta leftMask
    lda spanRight,y
    sec
    sbc #1
    pha
    and #3
    tax
    lda rightMasks,x
    sta rightMask
    and leftMask
    sta spanMask
    pla
    lsr
    lsr
    sta spanIndex
    pla
    lsr
    lsr
    asl
    asl
    asl
    asl
    ora spanIndex
    tax
    jmp !dispatch+
!empty:
    // Inclusive row loop consumes the half-open bottom row through a genuine
    // empty writer. Other degenerate rows use the same safe sentinel pair.
    ldx #$f0
!dispatch:
    lda drawBuffer
    bne !tableB+
    lda DISPATCH_A_LO,x
    sta spanDispatch+1
    lda DISPATCH_A_HI,x
    sta spanDispatch+2
    jmp !ready+
!tableB:
    lda DISPATCH_B_LO,x
    sta spanDispatch+1
    lda DISPATCH_B_HI,x
    sta spanDispatch+2
!ready:
    lda ink
spanDispatch:
    jsr $ffff
    lda currentRow
    cmp maximumY
    beq !nextTriangle+
    inc currentRow
    jmp !row-
!nextTriangle:
    inc triangleIndex
    lda triangleIndex
    cmp #32
    beq !done+
    jmp !triangle-
!done:
    rts
includeY:
    lda projectedY,x
    cmp minimumY
    bcs !minimum+
    sta minimumY
!minimum:
    cmp maximumY
    bcc !done+
    sta maximumY
!done:
    rts
prepareEdge:
    // Shared sampler is transposed: itsX is our rasterY; itsY is our pixelX.
    lda projectedY,x
    sta lineX0
    lda projectedX,x
    sta lineY0
    lda projectedY,y
    sta lineX1
    lda projectedX,y
    sta lineY1
    jmp drawBoundary
plotBoundaryMarker:
    // X=raster row, Y=ceil crossing. Preserve all sampler inputs/private state.
    tya
    cmp spanLeft,x
    bcs !left+
    sta spanLeft,x
!left:
    cmp spanRight,x
    bcc !done+
    sta spanRight,x
!done:
    rts
