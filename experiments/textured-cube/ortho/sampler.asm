// Quantize the X and Y contributions independently. For each UV axis,
// floor(A/256)+floor(B/256) differs from floor((A+B)/256) by 0 or -1.
// Column and row tables are built from the current live quad every call.
.label lookupU=$f6
.label lookupV=$f8
.label lookupPacked=$fa
.label lookupEndByte=$fb

renderTexturedQuad:
    jsr prepareOrthoQuad
    jsr lookupPrepareCoordinates
    lda minY
    sta lookupScanY
lookupRow:
    ldy lookupScanY
    lda leftSpan,y
    cmp rightSpan,y
    bcc !nonempty+
    jmp lookupNextRow
!nonempty:
    sta lookupLeft
    lda rightSpan,y
    and #1
    sta lookupRightOdd
    lda rightSpan,y
    lsr
    sta lookupEndByte

    // One generic modulo-U page per possible row U offset. V is added in
    // the high nibble, with byte wrap providing modulo 16 automatically.
    lda lookupRows,y
    and #15
    clc
    adc #>lookupUWrap
    sta lookupEvenTranslate+2
    sta lookupOddTranslate+2
    sta lookupTailTranslate+2
    lda lookupRows,y
    and #$f0
    sta lookupEvenV+1
    sta lookupOddV+1
    sta lookupTailV+1

    // Choose the already packed source pages for this physical matrix row.
    tya
    and #1
    asl
    clc
    adc #>texture
    sta lookupEvenTexture+2
    sta lookupTailTexture+2
    adc #1
    sta lookupOddTexture+2

    ldx lookupScanY
    lda matrixRowLow,x
    sta lookupPairRead+1
    sta lookupPairWrite+1
    sta lookupTailRead+1
    sta lookupTailWrite+1
    lda matrixRowHigh,x
    clc
    adc drawScreenHigh
    sta lookupPairRead+2
    sta lookupPairWrite+2
    sta lookupTailRead+2
    sta lookupTailWrite+2
    lda lookupLeft
    lsr
    tax
    bcc !evenStart+
    lda #0
    sta lookupPacked
    jmp lookupOdd
!evenStart:
    cpx lookupEndByte
    bcc lookupPair
    jmp lookupTail

lookupPair:
    ldy lookupColumnEven,x
lookupEvenTranslate:
    lda lookupUWrap,y
    clc
lookupEvenV:
    adc #0
    tay
lookupEvenTexture:
    lda texture,y
    sta lookupPacked
lookupOdd:
    ldy lookupColumnOdd,x
lookupOddTranslate:
    lda lookupUWrap,y
    clc
lookupOddV:
    adc #0
    tay
lookupOddTexture:
    lda textureShift2,y
    ora lookupPacked
lookupPairRead:
    ora $0400,x
lookupPairWrite:
    sta $0400,x
    inx
    cpx lookupEndByte
    bcc lookupPair

lookupTail:
    lda lookupRightOdd
    beq lookupNextRow
    ldy lookupColumnEven,x
lookupTailTranslate:
    lda lookupUWrap,y
    clc
lookupTailV:
    adc #0
    tay
lookupTailTexture:
    lda texture,y
lookupTailRead:
    ora $0400,x
lookupTailWrite:
    sta $0400,x
lookupNextRow:
    inc lookupScanY
    lda lookupScanY
    cmp maxY
    beq !done+
    jmp lookupRow
!done:
    rts

lookupPrepareCoordinates:
    lda quadX
    sta lookupMinX
    sta lookupMaxX
    ldx #1
!bounds:
    lda quadX,x
    cmp lookupMinX
    bcs !notMin+
    sta lookupMinX
!notMin:
    cmp lookupMaxX
    bcc !notMax+
    sta lookupMaxX
!notMax:
    inx
    cpx #4
    bne !bounds-
    inc lookupMaxX

    lda #0
    sta lookupU
    sta lookupU+1
    sta lookupV
    sta lookupV+1
    lda quadX
    sec
    sbc lookupMinX
    tax
    beq !columns+
!shiftX:
    sec
    lda lookupU
    sbc duDx
    sta lookupU
    lda lookupU+1
    sbc duDx+1
    sta lookupU+1
    sec
    lda lookupV
    sbc dvDx
    sta lookupV
    lda lookupV+1
    sbc dvDx+1
    sta lookupV+1
    dex
    bne !shiftX-
!columns:
    ldy lookupMinX
!column:
    lda lookupU+1
    and #15
    sta lookupPacked
    lda lookupV+1
    asl
    asl
    asl
    asl
    ora lookupPacked
    sta lookupPacked
    tya
    lsr
    tax
    lda lookupPacked
    bcc !even+
    sta lookupColumnOdd,x
    jmp !advanceX+
!even:
    sta lookupColumnEven,x
!advanceX:
    clc
    lda lookupU
    adc duDx
    sta lookupU
    lda lookupU+1
    adc duDx+1
    sta lookupU+1
    clc
    lda lookupV
    adc dvDx
    sta lookupV
    lda lookupV+1
    adc dvDx+1
    sta lookupV+1
    iny
    cpy lookupMaxX
    bne !column-

    lda #0
    sta lookupU
    sta lookupU+1
    sta lookupV
    sta lookupV+1
    lda quadY
    sec
    sbc minY
    tax
    beq !rows+
!shiftY:
    sec
    lda lookupU
    sbc duDy
    sta lookupU
    lda lookupU+1
    sbc duDy+1
    sta lookupU+1
    sec
    lda lookupV
    sbc dvDy
    sta lookupV
    lda lookupV+1
    sbc dvDy+1
    sta lookupV+1
    dex
    bne !shiftY-
!rows:
    ldy minY
!row:
    lda lookupU+1
    and #15
    sta lookupPacked
    lda lookupV+1
    asl
    asl
    asl
    asl
    ora lookupPacked
    sta lookupRows,y
    clc
    lda lookupU
    adc duDy
    sta lookupU
    lda lookupU+1
    adc duDy+1
    sta lookupU+1
    clc
    lda lookupV
    adc dvDy
    sta lookupV
    lda lookupV+1
    adc dvDy+1
    sta lookupV+1
    iny
    cpy maxY
    bne !row-
    rts

lookupScanY: .byte 0
lookupMinX: .byte 0
lookupMaxX: .byte 0
lookupLeft: .byte 0
lookupRightOdd: .byte 0

.errorif *> $8c00, "Lookup sampler code exceeds reserved code region"
*=$8c00 "Runtime X contributions, indexed by destination byte column"
lookupColumnEven: .fill 256,0
lookupColumnOdd: .fill 256,0
lookupRows: .fill 256,0
.errorif *> $9000, "Runtime coordinate tables overlap modulo-U pages"
*=$9000 "Generic modulo-U addition; no image or geometry data"
lookupUWrap:
.for (var rowU=0; rowU<16; rowU++) {
    .fill 256,((i&15)+rowU)&15 | (i&$f0)
}
.assert "Lookup sampler and tables remain below I/O", *<=$d000,true
