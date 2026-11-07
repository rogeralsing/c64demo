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
    ldx drawBank
    beq !bankA+
    jmp !bankB+
!bankA:
    .for (var row=SCENE_GAP_TOP; row<SCENE_GAP_BOTTOM; row++) {
        .for (var col=SCENE_GAP_LEFT; col<SCENE_GAP_RIGHT; col++) {
            lda backgroundScreen+row*40+col
            sta $0400+row*40+col
        }
    }
    rts
!bankB:
    .for (var row=SCENE_GAP_TOP; row<SCENE_GAP_BOTTOM; row++) {
        .for (var col=SCENE_GAP_LEFT; col<SCENE_GAP_RIGHT; col++) {
            lda backgroundScreen+row*40+col
            sta $0800+row*40+col
        }
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
!cell:
    // Keep the second bitmap color intact in cells shared with scene artwork.
    lda (gapPaintPointer),y
    and #$0f
    ora gapColor
    sta (gapPaintPointer),y
    iny
    cpy gapPaintEnd
    bcc !cell-
!nextRow:
    inx
    cpx gapEndRow
    bcc !row-
    rts

gapColumnFloor: .fill 128, floor((SCENE_X_OFFSET+2*i)/8) & $ff
gapColumnCeil: .fill 128, floor((SCENE_X_OFFSET+2*i+7)/8) & $ff
gapRowFloor: .fill 128, floor((SCENE_Y_OFFSET+2*i)/8) & $ff
gapRowCeil: .fill 128, floor((SCENE_Y_OFFSET+2*i+7)/8) & $ff
gapScreenLow: .fill 25, <($0400+i*40)
gapScreenHigh: .fill 25, >($0400+i*40)
