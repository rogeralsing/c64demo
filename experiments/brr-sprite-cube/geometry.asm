// Live Q6two-axis rotation and orthographic projection. No projected poses.
transformCube:
    lda phase
    asl
    asl
    clc
    adc #3
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
    ldy #7
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
    lda #48
    sta factor
    lda rotatedX,y
    jsr scaledProduct
    clc
    adc #36
    sta projectedX,y
    lda #96
    sta factor
    lda rotatedY,y
    jsr scaledProduct
    sta term
    sec
    lda #42
    sbc term
    sta projectedY,y
    dey
    bmi !done+
    jmp !vertex-
!done:
    lda cosPitch
    sta factor
    lda sinYaw
    jsr scaledProduct
    eor #$ff
    clc
    adc #1
    sta normalZ
    lda sinPitch
    sta normalZ+1
    lda cosYaw
    jsr scaledProduct
    sta normalZ+2
    rts
// Own primitive also used by morphing-cube. Q(a+b)-Q(a-b), Q(n)=n*n//256.
// All signed inputs fit |a±b|<=128. Y survives.
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
prepareRequest:
    ldx #11
    lda #0
!clearEdges:
    sta edgeColors,x
    dex
    bpl !clearEdges-
    ldx #5
!clearFaces:
    sta faceVisible,x
    dex
    bpl !clearFaces-
    ldx #0
!axis:
    lda normalZ,x
    beq !nextAxis+
    bmi !positiveFace+
    txa
    asl
    tay
    jmp !visible+
!positiveFace:
    txa
    asl
    ora #1
    tay
!visible:
    lda #1
    sta faceVisible,y
!nextAxis:
    inx
    cpx #3
    bne !axis-
    lda #0
    sta faceIndex
!face:
    ldx faceIndex
    lda faceVisible,x
    beq !nextFace+
    lda faceColors,x
    sta faceColor
    txa
    asl
    asl
    tax
    lda #4
    sta faceCursor
!faceEdge:
    ldy faceEdges,x
    lda edgeColors,y
    eor faceColor
    sta edgeColors,y
    inx
    dec faceCursor
    bne !faceEdge-
!nextFace:
    inc faceIndex
    lda faceIndex
    cmp #6
    bne !face-
    lda #0
    sta requestCount
    sta edgeIndex
    lda #1
    sta packetIndex
!edge:
    ldx edgeIndex
    lda edgeColors,x
    beq !nextEdge+
    ldy edgeFirst,x
    lda projectedX,y
    sta leftX
    lda projectedY,y
    sta leftY
    ldy edgeLast,x
    lda projectedX,y
    sta rightX
    lda projectedY,y
    cmp leftY
    beq !nextEdge+
    bcs !ordered+
    ldx leftY
    stx rightY
    sta leftY
    ldx leftX
    lda rightX
    sta leftX
    stx rightX
    jmp !record+
!ordered:
    sta rightY
!record:
    ldx requestCount
    lda edgeIndex
    sta requestEdges,x
    inc requestCount
    ldx packetIndex
    lda leftY
    sta wirePacket,x
    lda rightY
    sta wirePacket+1,x
    lda leftX
    sta wirePacket+2,x
    lda rightX
    sta wirePacket+3,x
    txa
    clc
    adc #4
    sta packetIndex
!nextEdge:
    inc edgeIndex
    lda edgeIndex
    cmp #12
    bne !edge-
    lda requestCount
    sta wirePacket
    asl
    clc
    adc #2
    sta responseLength
    lda packetIndex
    sta packetLength
    rts
