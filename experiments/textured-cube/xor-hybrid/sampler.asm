// Overlay one live affine texture on the real XOR-filled character canvas.
// The untouched prefix-fill selector3 is the exact face4 coverage mask.
// Only that face may be visible with material3 when this routine runs.
// Destination bytes hold four 2x1 physical pixels, leftmost in bits7..6.
.label hybridTexturePointer=$e0
.label hybridTextureValue=$e2
.label hybridColumnU=$e3
.label hybridColumnV=$e4
.label hybridColumnUCache=$cd00
.label hybridColumnVCache=$cd40
.label hybridRowUCache=$cd80
.label hybridRowVCache=$ce00

#if XOR_TEXELS
texelBuildMarkers:
#else
hybridTextureOverlay:
#endif
    jsr buildTexture
    lda visibleFaces
    and #$10
    bne !visible+
    jmp hybridTextureComplete
!visible:
    // Canonical UV corners0,2,3,1 have UV(0,0),(16,0),(16,16),(0,16).
    lda projectedX+2
    sec
    sbc projectedX
    sta hybridDX1
    lda projectedY+2
    sec
    sbc projectedY
    sta hybridDY1
    lda projectedX+3
    sec
    sbc projectedX
    sta hybridDX2
    lda projectedY+3
    sec
    sbc projectedY
    sta hybridDY2
    lda hybridDX1
    ldx hybridDY2
    jsr hybridSignedProduct
    lda hybridProduct
    sta hybridTextureArea
    lda hybridProduct+1
    sta hybridTextureArea+1
    lda hybridDY1
    ldx hybridDX2
    jsr hybridSignedProduct
    sec
    lda hybridTextureArea
    sbc hybridProduct
    sta hybridTextureArea
    lda hybridTextureArea+1
    sbc hybridProduct+1
    sta hybridTextureArea+1
    bmi !skip+
    ora hybridTextureArea
    bne !positive+
!skip:
    jmp hybridTextureComplete
!positive:

    lda hybridDY2
    sec
    sbc hybridDY1
    jsr hybridDivideGradient
    sta hybridDuDx
    stx hybridDuDx+1
    lda hybridDX1
    sec
    sbc hybridDX2
    jsr hybridDivideGradient
    sta hybridDuDy
    stx hybridDuDy+1
    lda #0
    sec
    sbc hybridDY1
    jsr hybridDivideGradient
    sta hybridDvDx
    stx hybridDvDx+1
    lda hybridDX1
    jsr hybridDivideGradient
    sta hybridDvDy
    stx hybridDvDy+1
    jsr hybridPrepareCoordinates

#if XOR_TEXELS
    jsr texelBuildFaceSpans
    jsr texelBuildFaceMarkers
#else
    lda hybridMinX
    sta hybridTextureX
!column:
    ldx hybridTextureX
    lda hybridColumnUCache,x
    sta hybridColumnU
    lda hybridColumnVCache,x
    sta hybridColumnV
    txa
    and #3
    tax
    lda hybridLaneLow,x
    sta hybridLaneDispatch+1
    lda hybridLaneHigh,x
    sta hybridLaneDispatch+2
    lda hybridTextureX
    lsr
    lsr
    tax
    lda hybridColumnLow,x
    sta hybridTexturePointer
    lda hybridColumnHigh,x
    clc
    adc drawBufferHi
    sta hybridTexturePointer+1
    jsr hybridLaneDispatch
    inc hybridTextureX
    lda hybridTextureX
    cmp hybridMaxX
    bne !column-
#endif
hybridTextureComplete:
    rts

#if !XOR_TEXELS
hybridLaneDispatch:
    jmp $ffff

.macro HybridTextureLane(pairMask,clearMask,source) {
    ldy hybridMinY
!row:
    lda (hybridTexturePointer),y
    and #pairMask
    cmp #pairMask
    bne !next+
    // Quantize the live X/Y contributions separately. Each axis differs
    // from floor(the combined Q8 plane) by exactly0 or -1 texel.
    lda hybridRowUCache,y
    clc
    adc hybridColumnU
    and #15
    sta hybridTextureValue
    lda hybridRowVCache,y
    clc
    adc hybridColumnV
    and #$f0
    ora hybridTextureValue
    tax
    lda source,x
    sta hybridTextureValue
    // Replacement is essential: zero texels must erase the raw material3.
    lda (hybridTexturePointer),y
    and #clearMask
    ora hybridTextureValue
    sta (hybridTexturePointer),y
!next:
    iny
    cpy hybridMaxY
    bne !row-
    rts
}

hybridLane0: HybridTextureLane($c0,$3f,textureShift6)
hybridLane1: HybridTextureLane($30,$cf,textureShift4)
hybridLane2: HybridTextureLane($0c,$f3,textureShift2)
hybridLane3: HybridTextureLane($03,$fc,texture)
#endif

hybridPrepareCoordinates:
    lda projectedX
    sta hybridMinX
    sta hybridMaxX
    lda projectedY
    sta hybridMinY
    sta hybridMaxY
    ldy #3
!bounds:
    ldx hybridFaceCorners,y
    lda projectedX,x
    cmp hybridMinX
    bcs !notMinX+
    sta hybridMinX
!notMinX:
    cmp hybridMaxX
    bcc !notMaxX+
    sta hybridMaxX
!notMaxX:
    lda projectedY,x
    cmp hybridMinY
    bcs !notMinY+
    sta hybridMinY
!notMinY:
    cmp hybridMaxY
    bcc !notMaxY+
    sta hybridMaxY
!notMaxY:
    dey
    bpl !bounds-
    lda #0
    sta hybridU
    sta hybridU+1
    sta hybridV
    sta hybridV+1
    lda projectedX
    sec
    sbc hybridMinX
    tax
    beq !columns+
!shiftX:
    sec
    lda hybridU
    sbc hybridDuDx
    sta hybridU
    lda hybridU+1
    sbc hybridDuDx+1
    sta hybridU+1
    sec
    lda hybridV
    sbc hybridDvDx
    sta hybridV
    lda hybridV+1
    sbc hybridDvDx+1
    sta hybridV+1
    dex
    bne !shiftX-
!columns:
    ldy hybridMinX
!column:
    lda hybridU+1
    and #15
    sta hybridColumnUCache,y
    lda hybridV+1
    asl
    asl
    asl
    asl
    sta hybridColumnVCache,y
    clc
    lda hybridU
    adc hybridDuDx
    sta hybridU
    lda hybridU+1
    adc hybridDuDx+1
    sta hybridU+1
    clc
    lda hybridV
    adc hybridDvDx
    sta hybridV
    lda hybridV+1
    adc hybridDvDx+1
    sta hybridV+1
    iny
    cpy hybridMaxX
    bne !column-

    lda #0
    sta hybridU
    sta hybridU+1
    sta hybridV
    sta hybridV+1
    lda projectedY
    sec
    sbc hybridMinY
    tax
    beq !rows+
!shiftY:
    sec
    lda hybridU
    sbc hybridDuDy
    sta hybridU
    lda hybridU+1
    sbc hybridDuDy+1
    sta hybridU+1
    sec
    lda hybridV
    sbc hybridDvDy
    sta hybridV
    lda hybridV+1
    sbc hybridDvDy+1
    sta hybridV+1
    dex
    bne !shiftY-
!rows:
    ldy hybridMinY
!row:
    lda hybridU+1
    and #15
    sta hybridRowUCache,y
    lda hybridV+1
    asl
    asl
    asl
    asl
    sta hybridRowVCache,y
    clc
    lda hybridU
    adc hybridDuDy
    sta hybridU
    lda hybridU+1
    adc hybridDuDy+1
    sta hybridU+1
    clc
    lda hybridV
    adc hybridDvDy
    sta hybridV
    lda hybridV+1
    adc hybridDvDy+1
    sta hybridV+1
    iny
    cpy hybridMaxY
    bne !row-
    rts

// Exact signed product without the old |a+b|<=128 quarter-table limit.
// The shared culler accepts absolute factors0..127 and returns high:A/low:X.
hybridSignedProduct:
    sta hybridProductLeft
    stx hybridProductRight
    eor hybridProductRight
    sta hybridProductSign
    lda hybridProductLeft
    bpl !left+
    eor #$ff
    clc
    adc #1
!left:
    sta hybridProductLeft
    txa
    bpl !right+
    eor #$ff
    clc
    adc #1
!right:
    tax
    lda hybridProductLeft
    jsr cullUnsignedMultiply
    stx hybridProduct
    sta hybridProduct+1
    lda hybridProductSign
    bpl !done+
    sec
    lda #0
    sbc hybridProduct
    sta hybridProduct
    lda #0
    sbc hybridProduct+1
    sta hybridProduct+1
!done:
    rts

.import source "../uv-gradient.asm"
hybridDivideGradient: UVGradientCode(hybridTextureArea,hybridRemainder,hybridNumerator,hybridDivisionSign,hybridSubtraction)

#if !XOR_TEXELS
hybridLaneLow: .byte <hybridLane0,<hybridLane1,<hybridLane2,<hybridLane3
hybridLaneHigh: .byte >hybridLane0,>hybridLane1,>hybridLane2,>hybridLane3
hybridColumnLow: .fill 16,<(i*128)
hybridColumnHigh: .fill 16,>(i*128)
#endif
hybridFaceCorners: .byte 0,2,3,1
hybridTextureX: .byte 0
hybridMinX: .byte 0
hybridMaxX: .byte 0
hybridMinY: .byte 0
hybridMaxY: .byte 0
hybridDX1: .byte 0
hybridDY1: .byte 0
hybridDX2: .byte 0
hybridDY2: .byte 0
hybridTextureArea: .word 0
hybridDuDx: .word 0
hybridDuDy: .word 0
hybridDvDx: .word 0
hybridDvDy: .word 0
hybridU: .word 0
hybridV: .word 0
hybridProductLeft: .byte 0
hybridProductRight: .byte 0
hybridProductSign: .byte 0
hybridProduct: .word 0
hybridRemainder: .word 0
hybridNumerator: .word 0
hybridDivisionSign: .byte 0
hybridSubtraction: .byte 0
#if XOR_TEXELS
.import source "../xor-texels/common.asm"
#endif
hybridSamplerEnd:
