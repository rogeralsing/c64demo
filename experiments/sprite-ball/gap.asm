// Paint the full cell bounding box of each enclosed pentagon. Neighboring
// sprites hide most overspill; small color clashes are accepted in this PoC.
.label gapVertexOffset = $06
.label gapTopRow = $07
.label gapEndRow = $08
.label gapFirstColumn = $09
.label gapEndColumn = $0a
.label gapPaintPointer = $0e
.label gapPaintEnd = $10
.label gapColor = $11

clearGapScreen:
    lda #$40
    ldx drawBank
    beq !bankA+
    jmp !bankB+
!bankA:
    .for (var row=8; row<17; row++) {
        .for (var col=15; col<25; col++) { sta $0400+row*40+col }
    }
    rts
!bankB:
    .for (var row=8; row<17; row++) {
        .for (var col=15; col<25; col++) { sta $0800+row*40+col }
    }
    rts

shadeGap:
    ldy gapVertexOffset
    lda gapVertices,y
    tax
    lda sharedX,x
    sta minX
    sta maxX
    lda sharedY,x
    sta minY
    sta maxY
    iny
    .for (var point=1; point<5; point++) {
        lda gapVertices,y
        tax
        lda sharedX,x
        cmp minX
        bcs !notMinX+
        sta minX
        bcc !notMaxX+
!notMinX:
        cmp maxX
        bcc !notMaxX+
        sta maxX
!notMaxX:
        lda sharedY,x
        cmp minY
        bcs !notMinY+
        sta minY
        bcc !notMaxY+
!notMinY:
        cmp maxY
        bcc !notMaxY+
        sta maxY
!notMaxY:
        iny
    }
    ldx minX
    lda gapColumnFloor,x
    sta gapFirstColumn
    ldx maxX
    lda gapColumnCeil,x
    sta gapEndColumn
    ldx minY
    lda gapRowFloor,x
    sta gapTopRow
    ldx maxY
    lda gapRowCeil,x
    sta gapEndRow
    ldx gapTopRow
!row:
    lda gapFirstColumn
    cmp gapEndColumn
    bcs !nextRow+
    tay
    lda gapEndColumn
    sta gapPaintEnd
    lda gapScreenLow,x
    sta gapPaintPointer
    lda drawBank
    asl
    asl
    clc
    adc gapScreenHigh,x
    sta gapPaintPointer+1
    lda gapColor
!cell:
    sta (gapPaintPointer),y
    iny
    cpy gapPaintEnd
    bcc !cell-
!nextRow:
    inx
    cpx gapEndRow
    bcc !row-
    rts

gapColumnFloor: .fill 128, floor(i/4)+4
gapColumnCeil: .fill 128, floor((i+3)/4)+4
gapRowFloor: .fill 128, floor((i-14)/4) & $ff
gapRowCeil: .fill 128, floor((i-11)/4) & $ff
gapScreenLow: .fill 25, <($0400+i*40)
gapScreenHigh: .fill 25, >($0400+i*40)
