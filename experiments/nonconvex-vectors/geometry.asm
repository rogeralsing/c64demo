// Live Q6two-axis rotation and reciprocal-depth perspective,16vertices.
transformVertices:
    ldx phase
    lda yawMotion,x
    tax
    lda sineUnit,x
    sta sinYaw
    txa
    clc
    adc #64
    tax
    lda sineUnit,x
    sta cosYaw
    ldx phase
    lda pitchMotion,x
    tax
    lda sineUnit,x
    sta sinPitch
    txa
    clc
    adc #64
    tax
    lda sineUnit,x
    sta cosPitch
    ldy #15
!vertex:
    lda cosYaw
    sta factor
    lda modelX,y
    jsr scaledProduct
    sta yawX
    lda modelZ,y
    jsr scaledProduct
    sta yawZ
    lda sinYaw
    sta factor
    lda modelZ,y
    jsr scaledProduct
    clc
    adc yawX
    sta rotatedX,y
    lda modelX,y
    jsr scaledProduct
    sta term
    sec
    lda yawZ
    sbc term
    sta yawZ
    lda cosPitch
    sta factor
    lda modelY,y
    jsr scaledProduct
    sta pitchY
    lda yawZ
    jsr scaledProduct
    sta pitchZ
    lda sinPitch
    sta factor
    lda yawZ
    jsr scaledProduct
    sta term
    sec
    lda pitchY
    sbc term
    sta rotatedY,y
    lda modelY,y
    jsr scaledProduct
    clc
    adc pitchZ
    sta rotatedZ,y
    clc
    adc #64
    tax
    lda depthFactors,x
    sta factor
    lda rotatedX,y
    jsr scaledProduct
    clc
    adc #32
    sta projectedX,y
    lda rotatedY,y
    jsr scaledProduct
    asl
    sta term
    sec
    lda #64
    sbc term
    sta projectedY,y
    dey
    bmi !done+
    jmp !vertex-
!done:
    rts
// Small own arithmetic primitive reused conceptually across the examples.
scaledProduct:
    sta multiplicand
    clc
    adc factor
    tax
    lda quarterSquares,x
    sta productSum
    sec
    lda multiplicand
    sbc factor
    tax
    sec
    lda productSum
    sbc quarterSquares,x
    rts

loadTriangle:
    lda triangleIndex
    asl
    clc
    adc triangleIndex
    tax
    lda triangleVertices,x
    sta vertexA
    lda triangleVertices+1,x
    sta vertexB
    lda triangleVertices+2,x
    sta vertexC
    rts
cullTriangles:
    lda #0
    sta triangleIndex
!triangle:
    jsr loadTriangle
    ldx vertexB
    ldy vertexA
    sec
    lda projectedX,x
    sbc projectedX,y
    sta dx1
    sec
    lda projectedY,x
    sbc projectedY,y
    sta dy1
    ldx vertexC
    sec
    lda projectedX,x
    sbc projectedX,y
    sta dx2
    sec
    lda projectedY,x
    sbc projectedY,y
    sta dy2
    lda dx1
    ldx dy2
    jsr signedProduct
    lda wideProduct
    sta firstProduct
    lda wideProduct+1
    sta firstProduct+1
    lda dy1
    ldx dx2
    jsr signedProduct
    sec
    lda firstProduct
    sbc wideProduct
    sta areaLo
    lda firstProduct+1
    sbc wideProduct+1
    sta areaHi
    lda #0
    ldx areaHi
    bmi !hidden+
    lda #1
!hidden:
    ldx triangleIndex
    sta triangleVisible,x
    inc triangleIndex
    lda triangleIndex
    cmp #32
    bne !triangle-
    rts

// Exact signed byte product via Q(a+b)-Q(abs(a-b)), Q(n)=floor(n*n/4).
signedProduct:
    sta wideLeft
    txa
    eor wideLeft
    sta wideSign
    lda wideLeft
    bpl !left+
    eor #$ff
    clc
    adc #1
!left:
    sta wideLeft
    txa
    bpl !right+
    eor #$ff
    clc
    adc #1
!right:
    tax
    clc
    adc wideLeft
    tay
    lda wideSquaresLo,y
    sta wideSum
    lda wideSquaresHi,y
    sta wideSum+1
    txa
    sec
    sbc wideLeft
    bcs !difference+
    eor #$ff
    clc
    adc #1
!difference:
    tay
    sec
    lda wideSum
    sbc wideSquaresLo,y
    sta wideProduct
    lda wideSum+1
    sbc wideSquaresHi,y
    sta wideProduct+1
    bit wideSign
    bpl !done+
    sec
    lda #0
    sbc wideProduct
    sta wideProduct
    lda #0
    sbc wideProduct+1
    sta wideProduct+1
!done:
    rts
