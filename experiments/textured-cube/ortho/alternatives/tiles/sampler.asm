// Runtime packed 2x2-sample tiles. One lookup produces one character code.
// Each cell quantizes its UV-origin fractions to the midpoint. Exact half-open quad coverage
// remains independent of that bounded (at most one texel) sampling change.
.label tileCache=$a000
.label tileTags=$a100
.label tileBaseU=$f6
.label tileBaseV=$f7
.label tileWork=$f8
.label tileCode=$f9

renderTexturedQuad:
    jsr prepareOrthoQuad
    lda #0
    ldx #0
!clearTags:
    sta tileTags,x
    inx
    bne !clearTags-

    // A cell represents its UV-origin fractions by the midpoint128/256.
    // Child offsets are floor((gradientDelta+128)/256); the anchor itself
    // remains its integer UV value. This removes a systematic floor bias.
    clc
    lda duDx
    adc #128
    lda duDx+1
    adc #0
    and #15
    sta tileUOffsetB+1
    clc
    lda duDy
    adc #128
    lda duDy+1
    adc #0
    and #15
    sta tileUOffsetC+1
    clc
    lda duDx
    adc duDy
    sta tileWork
    lda duDx+1
    adc duDy+1
    sta tileCode
    clc
    lda tileWork
    adc #128
    lda tileCode
    adc #0
    and #15
    sta tileUOffsetD+1
    clc
    lda dvDx
    adc #128
    lda dvDx+1
    adc #0
    asl
    asl
    asl
    asl
    sta tileVOffsetB+1
    clc
    lda dvDy
    adc #128
    lda dvDy+1
    adc #0
    asl
    asl
    asl
    asl
    sta tileVOffsetC+1
    clc
    lda dvDx
    adc dvDy
    sta tileWork
    lda dvDx+1
    adc dvDy+1
    sta tileCode
    clc
    lda tileWork
    adc #128
    lda tileCode
    adc #0
    asl
    asl
    asl
    asl
    sta tileVOffsetD+1

    // V*16 modulo 65536 keeps the wrapped integer texture row in its high
    // nibble. No fractional information relevant to the source index is lost.
    .for (var bit=0;bit<4;bit++) {
        asl dvDx
        rol dvDx+1
        asl dvDy
        rol dvDy+1
    }
    clc
    lda duDx
    adc duDx
    sta tileStepXU
    lda duDx+1
    adc duDx+1
    sta tileStepXU+1
    clc
    lda dvDx
    adc dvDx
    sta tileStepXV
    lda dvDx+1
    adc dvDx+1
    sta tileStepXV+1
    clc
    lda duDy
    adc duDy
    sta tileStepYU
    lda duDy+1
    adc duDy+1
    sta tileStepYU+1
    clc
    lda dvDy
    adc dvDy
    sta tileStepYV
    lda dvDy+1
    adc dvDy+1
    sta tileStepYV+1

    lda minY
    and #$fe
    sta tileY
    lda quadX
    lsr
    sta tileAnchorCell
    lda #0
    sta rowU
    sta rowU+1
    sta rowV
    sta rowV+1
    lda quadX
    and #1
    beq !shiftY+
    sec
    lda rowU
    sbc duDx
    sta rowU
    lda rowU+1
    sbc duDx+1
    sta rowU+1
    sec
    lda rowV
    sbc dvDx
    sta rowV
    lda rowV+1
    sbc dvDx+1
    sta rowV+1
!shiftY:
    lda quadY
    sec
    sbc tileY
    tax
    beq !row+
!shiftYLoop:
    sec
    lda rowU
    sbc duDy
    sta rowU
    lda rowU+1
    sbc duDy+1
    sta rowU+1
    sec
    lda rowV
    sbc dvDy
    sta rowV
    lda rowV+1
    sbc dvDy+1
    sta rowV+1
    dex
    bne !shiftYLoop-
!row:
    // Invalid/empty top or bottom rows are represented as empty intervals.
    lda #0
    sta tileTopL
    sta tileTopR
    sta tileBottomL
    sta tileBottomR
    ldx tileY
    cpx minY
    bcc !bottom+
    cpx maxY
    bcs !bottom+
    lda leftSpan,x
    cmp rightSpan,x
    bcs !bottom+
    sta tileTopL
    lda rightSpan,x
    sta tileTopR
!bottom:
    ldx tileY
    inx
    cpx minY
    bcc !bounds+
    cpx maxY
    bcs !bounds+
    lda leftSpan,x
    cmp rightSpan,x
    bcs !bounds+
    sta tileBottomL
    lda rightSpan,x
    sta tileBottomR
!bounds:
    lda tileTopR
    beq !bottomOnly+
    lda tileBottomR
    beq !topOnly+
    lda tileTopL
    cmp tileBottomL
    bcc !firstTop+
    lda tileBottomL
!firstTop:
    lsr
    sta tileFirstCell
    lda tileTopR
    cmp tileBottomR
    bcs !lastTop+
    lda tileBottomR
!lastTop:
    clc
    adc #1
    lsr
    sta tileEndCell
    lda tileTopL
    cmp tileBottomL
    bcs !fullLeft+
    lda tileBottomL
!fullLeft:
    clc
    adc #1
    lsr
    sta tileFullLeft
    lda tileTopR
    cmp tileBottomR
    bcc !fullEnd+
    lda tileBottomR
!fullEnd:
    lsr
    sta tileFullEnd
    jmp !position+
!bottomOnly:
    lda tileBottomR
    bne !onlyBottom+
    jmp !nextRow+
!onlyBottom:
    clc
    adc #1
    lsr
    sta tileEndCell
    lda tileBottomL
    lsr
    sta tileFirstCell
    jmp !noFull+
!topOnly:
    lda tileTopR
    clc
    adc #1
    lsr
    sta tileEndCell
    lda tileTopL
    lsr
    sta tileFirstCell
!noFull:
    lda #40
    sta tileFullLeft
    lda #0
    sta tileFullEnd
!position:
    lda tileFirstCell
    cmp tileAnchorCell
    beq !originReady+
    bcc !moveLeft+
    sec
    sbc tileAnchorCell
    tax
!moveRight:
    clc
    lda rowU
    adc tileStepXU
    sta rowU
    lda rowU+1
    adc tileStepXU+1
    sta rowU+1
    clc
    lda rowV
    adc tileStepXV
    sta rowV
    lda rowV+1
    adc tileStepXV+1
    sta rowV+1
    dex
    bne !moveRight-
    jmp !originReady+
!moveLeft:
    lda tileAnchorCell
    sec
    sbc tileFirstCell
    tax
!leftStep:
    sec
    lda rowU
    sbc tileStepXU
    sta rowU
    lda rowU+1
    sbc tileStepXU+1
    sta rowU+1
    sec
    lda rowV
    sbc tileStepXV
    sta rowV
    lda rowV+1
    sbc tileStepXV+1
    sta rowV+1
    dex
    bne !leftStep-
!originReady:
    lda tileFirstCell
    sta tileAnchorCell
    ldx tileY
    lda matrixRowLow,x
    sta samplePointer
    lda matrixRowHigh,x
    clc
    adc drawScreenHigh
    sta samplePointer+1
    lda rowU
    sta pixelU
    lda rowU+1
    sta pixelU+1
    lda rowV
    sta pixelV
    lda rowV+1
    sta pixelV+1
    ldy tileFirstCell
!cell:
    cpy tileFullLeft
    bcc !edgeCell+
    cpy tileFullEnd
    bcs !edgeCell+
    lda #$ff
    sta tileMask
    jmp !readGlyph+
!edgeCell:
    jsr tileCoverageMask
!readGlyph:
    lda pixelU+1
    and #15
    sta tileBaseU
    lda pixelV+1
    and #$f0
    ora tileBaseU
    tax
    lda tileTags,x
    bne !cached+
    stx tileIndex
    jsr tileBuildGlyph
!cached:
    lda tileCache,x
    and tileMask
    ora (samplePointer),y
    sta (samplePointer),y
    clc
    lda pixelU
    adc tileStepXU
    sta pixelU
    lda pixelU+1
    adc tileStepXU+1
    sta pixelU+1
    clc
    lda pixelV
    adc tileStepXV
    sta pixelV
    lda pixelV+1
    adc tileStepXV+1
    sta pixelV+1
    iny
    cpy tileEndCell
    beq !nextRow+
    jmp !cell-
!nextRow:
    clc
    lda rowU
    adc tileStepYU
    sta rowU
    lda rowU+1
    adc tileStepYU+1
    sta rowU+1
    clc
    lda rowV
    adc tileStepYV
    sta rowV
    lda rowV+1
    adc tileStepYV+1
    sta rowV+1
    inc tileY
    inc tileY
    lda tileY
    cmp maxY
    bcs !done+
    jmp !row-
!done:
    rts

// Exact mask of the quad's four samples in the current packed cell.
// X may change. Y, UV accumulators and the screen pointer survive.
tileCoverageMask:
    lda #0
    sta tileMask
    tya
    asl
    sta tileSampleX
    cmp tileTopL
    bcc !topOdd+
    cmp tileTopR
    bcs !topOdd+
    lda #3
    sta tileMask
!topOdd:
    lda tileSampleX
    clc
    adc #1
    cmp tileTopL
    bcc !bottomEven+
    cmp tileTopR
    bcs !bottomEven+
    lda tileMask
    ora #$0c
    sta tileMask
!bottomEven:
    lda tileSampleX
    cmp tileBottomL
    bcc !bottomOdd+
    cmp tileBottomR
    bcs !bottomOdd+
    lda tileMask
    ora #$30
    sta tileMask
!bottomOdd:
    lda tileSampleX
    clc
    adc #1
    cmp tileBottomL
    bcc !done+
    cmp tileBottomR
    bcs !done+
    lda tileMask
    ora #$c0
    sta tileMask
!done:
    rts

// Populate one cached packed code. The three relative offsets were rounded
// once per face. Only integer UV anchor coordinates participate in this cache.
tileBuildGlyph:
    txa
    and #$f0
    sta tileBaseV
    lda texture,x
    sta tileCode
    lda tileBaseV
    clc
tileVOffsetB:
    adc #0
    sta tileWork
    lda tileBaseU
    clc
tileUOffsetB:
    adc #0
    and #15
    ora tileWork
    tax
    lda textureShift2,x
    ora tileCode
    sta tileCode
    lda tileBaseV
    clc
tileVOffsetC:
    adc #0
    sta tileWork
    lda tileBaseU
    clc
tileUOffsetC:
    adc #0
    and #15
    ora tileWork
    tax
    lda textureShift4,x
    ora tileCode
    sta tileCode
    lda tileBaseV
    clc
tileVOffsetD:
    adc #0
    sta tileWork
    lda tileBaseU
    clc
tileUOffsetD:
    adc #0
    and #15
    ora tileWork
    tax
    lda textureShift6,x
    ora tileCode
    ldx tileIndex
    sta tileCache,x
    lda #1
    sta tileTags,x
    rts

tileStepXU: .word 0
tileStepXV: .word 0
tileStepYU: .word 0
tileStepYV: .word 0
tileY: .byte 0
tileAnchorCell: .byte 0
tileTopL: .byte 0
tileTopR: .byte 0
tileBottomL: .byte 0
tileBottomR: .byte 0
tileFirstCell: .byte 0
tileEndCell: .byte 0
tileFullLeft: .byte 0
tileFullEnd: .byte 0
tileMask: .byte 0
tileSampleX: .byte 0
tileIndex: .byte 0
