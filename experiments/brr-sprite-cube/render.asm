// Runtime BRRpositions -> XORcrossing markers -> packed multicolor sprites.
renderCube:
    lda frontBuffer
    eor #1
    asl
    asl
    asl
    clc
    adc #$20
    sta drawBaseHi
    ldx #0
    lda #0
!clear:
    .for (var page=0;page<6;page++) { sta MARKERS+page*256,x }
    .for (var page=0;page<4;page++) { sta allTraces+page*256,x }
    inx
    bne !clear-
    lda #0
    sta requestIndex
!request:
    lda requestIndex
    asl
    asl
    tax
    lda wirePacket+1,x
    sta leftY
    lda wirePacket+2,x
    sta rightY
    sta stopRow
    lda wirePacket+3,x
    sta leftX
    lda wirePacket+4,x
    sta rightX
    ldx requestIndex
    lda requestEdges,x
    sta edgeIndex
    tax
    lda edgeColors,x
    sta markerDelta
    jsr preparePositionStores
    lda requestIndex
    asl
    tax
    lda wireResponse+2,x
    sta rowStep
    lda wireResponse+3,x
    sta brrThreshold+1
    lda stopRow
    jsr cellAddress
    stx stopPointer
    sty stopPointer+1
    // Half-open endpoint patches only one instruction; restore before reuse.
    ldy #0
    lda #$4c
    sta (stopPointer),y
    iny
    lda #<brrDone
    sta (stopPointer),y
    iny
    lda #>brrDone
    sta (stopPointer),y
    lda leftY
    jsr cellAddress
    stx brrDispatch+1
    sty brrDispatch+2
brrThreshold:
    ldx #0
    lda leftX
brrDispatch:
    jsr $ffff
    lda endpointActual
    cmp rightX
    beq !endpoint+
    jmp protocolFault
!endpoint:
    lda stopRow
    cmp #HEIGHT
    beq !restored+
    ldx edgeIndex
    clc
    adc edgeTraceLo,x
    pha
    lda edgeTraceHi,x
    adc #0
    sta term
    ldy #0
    lda #$8d
    sta (stopPointer),y
    iny
    pla
    sta (stopPointer),y
    iny
    lda term
    sta (stopPointer),y
!restored:
    lda leftY
    sta rowIndex
!row:
    ldx edgeIndex
    lda edgeTraceLo,x
    sta outputPointer
    lda edgeTraceHi,x
    sta outputPointer+1
    ldy rowIndex
    lda (outputPointer),y
    jsr plotMarker
    inc rowIndex
    lda rowIndex
    cmp rightY
    bne !row-
    inc requestIndex
    lda requestIndex
    cmp requestCount
    beq !filled+
    jmp !request-
!filled:
    jsr fillSprites
    rts
brrDone:
    sta endpointActual
    rts
// Direct STA cells target this edge's live position array. The marker pass
// consumes that array; there is no extra diagnostic-only copy of positions.
preparePositionStores:
    ldx edgeIndex
    lda edgeTraceLo,x
    sta outputPointer
    lda edgeTraceHi,x
    sta outputPointer+1
    lda #<(brrCells+1)
    sta markerPointer
    lda #>(brrCells+1)
    sta markerPointer+1
    ldx #HEIGHT
!store:
    ldy #0
    lda outputPointer
    sta (markerPointer),y
    iny
    lda outputPointer+1
    sta (markerPointer),y
    inc outputPointer
    bne !target+
    inc outputPointer+1
!target:
    clc
    lda markerPointer
    adc #CELL_BYTES
    sta markerPointer
    bcc !code+
    inc markerPointer+1
!code:
    dex
    bne !store-
    rts
// A=row; return X/Y=absolute generated cell address, with a16-bit7*row.
cellAddress:
    sta term
    lda #0
    sta productSum
    lda term
    asl
    rol productSum
    asl
    rol productSum
    asl
    rol productSum
    sec
    sbc term
    tax
    lda productSum
    sbc #0
    clc
    adc #>brrCells
    tay
    rts
plotMarker:
    pha
    and #3
    sta markerLane
    lda markerDelta
    asl
    asl
    ora markerLane
    tax
    lda markerMasks,x
    sta markerValue
    pla
    lsr
    lsr
    tay
    ldx rowIndex
    lda rowMarkerLo,x
    sta markerPointer
    lda rowMarkerHi,x
    sta markerPointer+1
    lda (markerPointer),y
    eor markerValue
    sta (markerPointer),y
    rts
fillSprites:
    lda #0
    sta rowIndex
!row:
    ldx rowIndex
    lda rowMarkerLo,x
    sta markerPointer
    lda rowMarkerHi,x
    sta markerPointer+1
    lda #0
    sta fillCarry
    sta columnIndex
!byte:
    ldy columnIndex
    lda (markerPointer),y
    tax
    lda prefixTable,x
    ldx fillCarry
    eor repeatColor,x
    sta fillByte
    and #3
    sta fillCarry
    ldx rowIndex
    ldy columnIndex
    clc
    lda rowSpriteLo,x
    adc columnSpriteLo,y
    sta outputPointer
    lda rowSpriteHi,x
    adc columnSpriteHi,y
    adc drawBaseHi
    sta outputPointer+1
    ldy #0
    lda fillByte
    sta (outputPointer),y
    inc columnIndex
    lda columnIndex
    cmp #18
    bne !byte-
    inc rowIndex
    lda rowIndex
    cmp #HEIGHT
    bne !row-
    rts
