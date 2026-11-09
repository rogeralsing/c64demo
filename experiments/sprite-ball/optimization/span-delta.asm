
.label localX=$30
.label localY=$36
.label count=$3c
.label oldPointer=$40
.label outputPointer=$42
.label mirrorPointer=$44
.label sampleBias=$46
.label mask=$47
.label intervalStart=$48
.label intervalEnd=$49
.label column=$4a
.label columnOffset=$4b
.label slotIndex=$4c
.label newTop=$7000
.label newBottom=$7020
*=$2000 "Span generation and delta update"
generate:
    lda count
    beq !empty+
    jmp !active+
!empty:
    lda #0
    .for(var i=0;i<24;i++) { sta newTop+i; sta newBottom+i }
    rts
!active:
    lda #$ff
    .for(var i=0;i<24;i++) { sta newTop+i }
    lda #0
    .for(var i=0;i<24;i++) { sta newBottom+i }
    jsr edge0
    jsr edge1
    jsr edge2
    jsr edge3
    lda count
    cmp #5
    beq !pentagon+
    jsr edge4
    jsr edge5
    jmp normalize
!pentagon:
    jsr pentEdge4
normalize:
    ldx #23
!column:
    lda newTop,x
    cmp #$ff
    bne !present+
    lda #0
    sta newTop,x
!present:
    dex
    bpl !column-
    rts

.macro SpanEdge(a,b) {
    lda localX+a
    cmp localX+b
    bcc !forward+
    bne !reverse+
    rts
!forward:
    OrderedSpan(localX+a,localY+a,localX+b,localY+b)
!reverse:
    OrderedSpan(localX+b,localY+b,localX+a,localY+a)
}
.macro OrderedSpan(startX,startY,endX,endY) {
    lda startY
    sec
    sbc #20
    sta sampleBias
    lda endX
    sec
    sbc startX
    tax
    lda endY
    sec
    sbc startY
    clc
    adc curveIndexBase,x
    tax
    lda curveLow,x
    sec
    sbc startX
    sta sample+1
    lda curveHigh,x
    sbc #0
    sta sample+2
    ldx startX
!pixel:
sample:
    lda $ffff,x
    clc
    adc sampleBias
    cmp newTop,x
    bcs !notTop+
    sta newTop,x
!notTop:
    cmp newBottom,x
    bcc !notBottom+
    sta newBottom,x
!notBottom:
    inx
    cpx endX
    bne !pixel-
    rts
}
edge0: SpanEdge(0,1)
edge1: SpanEdge(1,2)
edge2: SpanEdge(2,3)
edge3: SpanEdge(3,4)
edge4: SpanEdge(4,5)
edge5: SpanEdge(5,0)
pentEdge4: SpanEdge(4,0)

update:
    ldx slotIndex
    lda oldLow,x
    sta oldPointer
    lda oldHigh,x
    sta oldPointer+1
    lda outputLow,x
    sta outputPointer
    sta mirrorPointer
    lda outputHigh,x
    sta outputPointer+1
    clc
    adc #$10
    sta mirrorPointer+1
    ldx #0
!column:
    stx column
    lda bitMasks,x
    sta mask
    lda byteColumns,x
    sta columnOffset
    txa
    tay
    lda (oldPointer),y
    cmp newTop,x
    beq !topSame+
    sta intervalStart
    lda newTop,x
    sta (oldPointer),y
    sta intervalEnd
    jsr toggleInterval
!topSame:
    ldx column
    txa
    clc
    adc #24
    tay
    lda (oldPointer),y
    cmp newBottom,x
    beq !bottomSame+
    sta intervalStart
    lda newBottom,x
    sta (oldPointer),y
    sta intervalEnd
    jsr toggleInterval
!bottomSame:
    ldx column
    inx
    cpx #24
    bne !column-
    rts

// XOR between the two top endpoints, then between the bottom endpoints.
// Disjoint spans may visit an intermediate pixel twice. XOR cancels those
// visits, retaining exact symmetric-difference coverage without a sort of four
// endpoints. Both MCI mirrors receive the same value after every changed bit.
toggleInterval:
    lda intervalStart
    cmp intervalEnd
    bcc !ordered+
    ldx intervalEnd
    sta intervalEnd
    stx intervalStart
!ordered:
    ldx intervalEnd
    lda rowOffsets,x
    clc
    adc columnOffset
    sta intervalEnd
    ldx intervalStart
    lda rowOffsets,x
    clc
    adc columnOffset
    tay
!pixel:
    lda (outputPointer),y
    eor mask
    sta (outputPointer),y
    sta (mirrorPointer),y
    iny
    iny
    iny
    cpy intervalEnd
    bne !pixel-
    rts
codeEnd:
bitMasks: .fill 24,$80 >> (i&7)
byteColumns: .fill 24,floor(i/8)
rowOffsets: .fill 22,i*3
oldLow: .fill 16,<($6000+i*48)
oldHigh: .fill 16,>($6000+i*48)
outputLow: .fill 16,<($4000+floor(i/8)*$400+(i&7)*64)
outputHigh: .fill 16,>($4000+floor(i/8)*$400+(i&7)*64)
curveIndexBase: .byte 0,10,31,52,73,94,115,136,157,178
tablesEnd:
*=$8000 "Exact ceil crossing curve pointers"
curveLow: .import binary "curve-low.bin"
curveHigh: .import binary "curve-high.bin"
*=$a000 "Exact ceil crossing samples"
curveSamples: .import binary "curve-samples.bin"
curvesEnd:
