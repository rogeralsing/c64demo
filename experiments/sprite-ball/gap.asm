// Paint the full cell bounding box of each lit, front-facing pentagon.
// Sprites and the fixed rim hide most overspill; small color clashes are
// accepted in this PoC, including where a neighboring hexagon has no sprite.
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

paintGapColors:
    // Farther faces go first, so their coarse cell rectangles cannot replace
    // the colors of nearer faces. Ties retain the static mesh order.
    lda #127
    sta gapWeakest
    ldy #$ff
    ldx #0
!find:
    lda gapFacing,x
    beq !next+
    cmp gapWeakest
    bcs !next+
    sta gapWeakest
    txa
    tay
!next:
    inx
    cpx #12
    bne !find-
    cpy #$ff
    beq !done+
    lda #0
    sta gapFacing,y
    lda gapFaceColors,y
    sta gapColor
    lda gapOffsets,y
    sta gapVertexOffset
    jsr shadeGap
    jmp paintGapColors
!done:
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
    cpx gapEndRow
    bcs !done+
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
!done:
    rts

gapFacing: .fill 12, 0
gapFaceColors: .fill 12, 0
gapWeakest: .byte 0
gapOffsets: .fill 12, i*5

// Outside this region the bitmap has no animated selector-01 pixels. Keep
// color writes inside the cells that clearGapScreen restores every frame.
gapColumnFloor: .fill 128, max(SCENE_GAP_LEFT, min(SCENE_GAP_RIGHT, floor((SCENE_X_OFFSET+2*i)/8)))
gapColumnCeil: .fill 128, max(SCENE_GAP_LEFT, min(SCENE_GAP_RIGHT, floor((SCENE_X_OFFSET+2*i+7)/8)))
gapRowFloor: .fill 128, max(SCENE_GAP_TOP, min(SCENE_GAP_BOTTOM, floor((SCENE_Y_OFFSET+2*i)/8)))
gapRowCeil: .fill 128, max(SCENE_GAP_TOP, min(SCENE_GAP_BOTTOM, floor((SCENE_Y_OFFSET+2*i+7)/8)))
gapScreenLow: .fill 25, <($0400+i*40)
gapScreenHigh: .fill 25, >($0400+i*40)
