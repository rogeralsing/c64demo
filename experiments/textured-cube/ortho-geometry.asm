// Live orthographic rotation of three basis vectors; shared by all candidates.
// Basis and vertices retain signed Q10 until the final raster conversion.
// Q14 trig coefficients and rounded 32-bit products preserve a rigid model.
transformModel:
    lda phase
    asl
    asl
    clc
    adc #1
    sta angleYaw
    tax
    lda orthoSineLo,x
    sta orthoSinYaw
    lda orthoSineHi,x
    sta orthoSinYaw+1
    txa
    clc
    adc #64
    tax
    lda orthoSineLo,x
    sta orthoCosYaw
    lda orthoSineHi,x
    sta orthoCosYaw+1
    ldx phase
    lda pitchMotion,x
    sta anglePitch
    tax
    lda orthoSineLo,x
    sta orthoSinPitch
    lda orthoSineHi,x
    sta orthoSinPitch+1
    txa
    clc
    adc #64
    tax
    lda orthoSineLo,x
    sta orthoCosPitch
    lda orthoSineHi,x
    sta orthoCosPitch+1
    lda phase
    asl
    asl
    sta orthoAngleRoll
    ldx orthoAngleRoll
    lda orthoSineLo,x
    sta orthoSinRoll
    lda orthoSineHi,x
    sta orthoSinRoll+1
    txa
    clc
    adc #64
    tax
    lda orthoSineLo,x
    sta orthoCosRoll
    lda orthoSineHi,x
    sta orthoCosRoll+1
    ldy #4
!axis:
    lda orthoCosYaw
    sta orthoFactor
    lda orthoCosYaw+1
    sta orthoFactor+1
    lda orthoModelX,y
    ldx orthoModelX+1,y
    jsr orthoMultiplyQ14
    sta orthoYawX
    stx orthoYawX+1
    lda orthoModelZ,y
    ldx orthoModelZ+1,y
    jsr orthoMultiplyQ14
    sta orthoYawZ
    stx orthoYawZ+1
    lda orthoSinYaw
    sta orthoFactor
    lda orthoSinYaw+1
    sta orthoFactor+1
    lda orthoModelZ,y
    ldx orthoModelZ+1,y
    jsr orthoMultiplyQ14
    clc
    adc orthoYawX
    sta orthoBasisX,y
    txa
    adc orthoYawX+1
    sta orthoBasisX+1,y
    lda orthoModelX,y
    ldx orthoModelX+1,y
    jsr orthoMultiplyQ14
    sta orthoTerm
    stx orthoTerm+1
    sec
    lda orthoYawZ
    sbc orthoTerm
    sta orthoYawZ
    lda orthoYawZ+1
    sbc orthoTerm+1
    sta orthoYawZ+1
    lda orthoCosPitch
    sta orthoFactor
    lda orthoCosPitch+1
    sta orthoFactor+1
    lda orthoModelY,y
    ldx orthoModelY+1,y
    jsr orthoMultiplyQ14
    sta orthoPitchY
    stx orthoPitchY+1
    lda orthoYawZ
    ldx orthoYawZ+1
    jsr orthoMultiplyQ14
    sta orthoPitchZ
    stx orthoPitchZ+1
    lda orthoSinPitch
    sta orthoFactor
    lda orthoSinPitch+1
    sta orthoFactor+1
    lda orthoYawZ
    ldx orthoYawZ+1
    jsr orthoMultiplyQ14
    sta orthoTerm
    stx orthoTerm+1
    sec
    lda orthoPitchY
    sbc orthoTerm
    sta orthoBasisY,y
    lda orthoPitchY+1
    sbc orthoTerm+1
    sta orthoBasisY+1,y
    lda orthoModelY,y
    ldx orthoModelY+1,y
    jsr orthoMultiplyQ14
    clc
    adc orthoPitchZ
    sta orthoBasisZ,y
    txa
    adc orthoPitchZ+1
    sta orthoBasisZ+1,y
    // Rz follows the existing Ry yaw then Rx pitch. Preserve both inputs
    // until all four individually rounded Q14 products have been consumed.
    lda orthoBasisX,y
    sta orthoRollInputX
    lda orthoBasisX+1,y
    sta orthoRollInputX+1
    lda orthoBasisY,y
    sta orthoRollInputY
    lda orthoBasisY+1,y
    sta orthoRollInputY+1
    lda orthoCosRoll
    sta orthoFactor
    lda orthoCosRoll+1
    sta orthoFactor+1
    lda orthoRollInputX
    ldx orthoRollInputX+1
    jsr orthoMultiplyQ14
    sta orthoYawX
    stx orthoYawX+1
    lda orthoRollInputY
    ldx orthoRollInputY+1
    jsr orthoMultiplyQ14
    sta orthoPitchY
    stx orthoPitchY+1
    lda orthoSinRoll
    sta orthoFactor
    lda orthoSinRoll+1
    sta orthoFactor+1
    lda orthoRollInputY
    ldx orthoRollInputY+1
    jsr orthoMultiplyQ14
    sta orthoTerm
    stx orthoTerm+1
    sec
    lda orthoYawX
    sbc orthoTerm
    sta orthoBasisX,y
    lda orthoYawX+1
    sbc orthoTerm+1
    sta orthoBasisX+1,y
    lda orthoRollInputX
    ldx orthoRollInputX+1
    jsr orthoMultiplyQ14
    clc
    adc orthoPitchY
    sta orthoBasisY,y
    txa
    adc orthoPitchY+1
    sta orthoBasisY+1,y
    dey
    dey
    bmi !basisDone+
    jmp !axis-
!basisDone:
    // Construct all corners from the same fixed-point basis. No vertex poses
    // are stored. Only final screen coordinates are rounded; independently
    // rounded screen edges need not remain exact integer parallelograms.
    .for (var axis=0; axis<3; axis++) {
        .for (var component=0; component<3; component++) {
            lda orthoBasisX+axis*6+component*2
            asl
            sta orthoBasisStep+axis*6+component*2
            lda orthoBasisX+axis*6+component*2+1
            rol
            sta orthoBasisStep+axis*6+component*2+1
        }
        lda #0
        sta orthoVertexAccumulator
        sta orthoVertexAccumulator+1
        .for (var component=0; component<3; component++) {
            sec
            lda orthoVertexAccumulator
            sbc orthoBasisX+axis*6+component*2
            sta orthoVertexAccumulator
            lda orthoVertexAccumulator+1
            sbc orthoBasisX+axis*6+component*2+1
            sta orthoVertexAccumulator+1
        }
        lda orthoVertexAccumulator
        sta orthoVertexX+axis*16
        lda orthoVertexAccumulator+1
        sta orthoVertexX+axis*16+1
    }
    // Remove the least significant set corner bit, then add its doubled axis.
    // All parent corners precede their children, and Q10 sums fit signed16.
    .for (var vertex=1; vertex<8; vertex++) {
        .var parent=vertex & (vertex-1)
        .var bit=vertex ^ parent
        .var component=bit==1 ? 0 : bit==2 ? 1 : 2
        .for (var axis=0; axis<3; axis++) {
            clc
            lda orthoVertexX+axis*16+parent*2
            adc orthoBasisStep+axis*6+component*2
            sta orthoVertexX+axis*16+vertex*2
            lda orthoVertexX+axis*16+parent*2+1
            adc orthoBasisStep+axis*6+component*2+1
            sta orthoVertexX+axis*16+vertex*2+1
        }
    }
    ldx #7
!rasterVertex:
    txa
    asl
    tay
    .for (var axis=0; axis<3; axis++) {
        lda orthoVertexX+axis*16+1,y
        jsr orthoRoundHigh
        sta rotatedX+axis*8,x
    }
    lda rotatedX,x
    clc
#if XOR_TEXTURE
    adc #32
#else
    adc #40
#endif
    sta projectedX,x
#if XOR_TEXTURE
    // A logical pixel is2x1 physical pixels. Round doubled Q10 Y only here:
    // floor((2*n+512)/1024)=floor((highByte(n)+1)/2).
    lda orthoVertexY+1,y
    clc
    adc #1
    cmp #$80
    ror
    sta orthoTerm
    lda #64
    sec
    sbc orthoTerm
#else
    lda #25
    sec
    sbc rotatedY,x
#endif
    sta projectedY,x
    dex
    bpl !rasterVertex-
    rts

// A is the high byte of signed Q10. The low byte cannot affect rounding by
// 512 then division by1024. Arithmetic shifts implement floor for negatives.
orthoRoundHigh:
    clc
    adc #2
    cmp #$80
    ror
    cmp #$80
    ror
    rts

// A:X(low:high) times the signed Q14 coefficient, rounded as
// floor((n*coefficient+8192)/16384). Y and the coefficient survive.
orthoMultiplyQ14:
    sta orthoLeft
    stx orthoLeft+1
    ora orthoLeft+1
    bne !nonzeroLeft+
    tax
    rts
!nonzeroLeft:
    lda orthoLeft
    bne !general+
    lda orthoLeft+1
    cmp #$38
    bne !general+
    jmp orthoScaleModelAxis
!general:
    lda orthoFactor
    ora orthoFactor+1
    bne !nonzero+
    lda #0
    tax
    rts
!nonzero:
    lda orthoFactor
    sta orthoRight
    lda orthoFactor+1
    sta orthoRight+1
    lda #0
    sta orthoSign
    sta orthoProduct
    sta orthoProduct+1
    sta orthoProduct+2
    sta orthoProduct+3
    sta orthoShift+2
    sta orthoShift+3
    lda orthoLeft+1
    bpl !leftPositive+
    inc orthoSign
    sec
    lda #0
    sbc orthoLeft
    sta orthoLeft
    lda #0
    sbc orthoLeft+1
    sta orthoLeft+1
!leftPositive:
    lda orthoRight+1
    bpl !rightPositive+
    inc orthoSign
    sec
    lda #0
    sbc orthoRight
    sta orthoRight
    lda #0
    sbc orthoRight+1
    sta orthoRight+1
!rightPositive:
    lda orthoLeft
    sta orthoShift
    lda orthoLeft+1
    sta orthoShift+1
    ldx #16
!bit:
    lsr orthoRight+1
    ror orthoRight
    bcc !skip+
    clc
    .for (var byte=0; byte<4; byte++) {
        lda orthoProduct+byte
        adc orthoShift+byte
        sta orthoProduct+byte
    }
!skip:
    asl orthoShift
    rol orthoShift+1
    rol orthoShift+2
    rol orthoShift+3
    dex
    bne !bit-
    lda orthoSign
    and #1
    beq !positiveProduct+
    sec
    .for (var byte=0; byte<4; byte++) {
        lda #0
        sbc orthoProduct+byte
        sta orthoProduct+byte
    }
!positiveProduct:
    // Add0x2000, then extract bits14..29 with two left shifts of bytes1..3.
    // Signed32 and logical extraction have identical low16 result bits.
    clc
    lda orthoProduct+1
    adc #$20
    sta orthoProduct+1
    lda orthoProduct+2
    adc #0
    sta orthoProduct+2
    lda orthoProduct+3
    adc #0
    sta orthoProduct+3
    .for (var bit=0; bit<2; bit++) {
        asl orthoProduct+1
        rol orthoProduct+2
        rol orthoProduct+3
    }
    lda orthoProduct+2
    ldx orthoProduct+3
    rts

// Exact specialization for the nonzero model axes:14336/16384=7/8.
// floor((7*c+4)/8) = c-floor((c+3)/8), including negative half ties.
orthoScaleModelAxis:
    clc
    lda orthoFactor
    adc #3
    sta orthoRight
    lda orthoFactor+1
    adc #0
    sta orthoRight+1
    .for (var bit=0; bit<3; bit++) {
        lda orthoRight+1
        cmp #$80
        ror orthoRight+1
        ror orthoRight
    }
    sec
    lda orthoFactor
    sbc orthoRight
    sta orthoLeft
    lda orthoFactor+1
    sbc orthoRight+1
    tax
    lda orthoLeft
    rts

orthoModelX: .word 14336,0,0
orthoModelY: .word 0,14336,0
orthoModelZ: .word 0,0,14336
// Axis-major Q10 computational state: three signed16 basis words per row,
// then eight signed16 vertex words per row, consumed by final rasterization.
orthoBasisX: .fill 6,0
orthoBasisY: .fill 6,0
orthoBasisZ: .fill 6,0
orthoVertexX: .fill 16,0
orthoVertexY: .fill 16,0
orthoVertexZ: .fill 16,0
orthoBasisStep: .fill 18,0
orthoVertexAccumulator: .word 0
orthoSinYaw: .word 0
orthoCosYaw: .word 0
orthoSinPitch: .word 0
orthoCosPitch: .word 0
orthoAngleRoll: .byte 0
orthoSinRoll: .word 0
orthoCosRoll: .word 0
orthoRollInputX: .word 0
orthoRollInputY: .word 0
orthoFactor: .word 0
orthoYawX: .word 0
orthoYawZ: .word 0
orthoPitchY: .word 0
orthoPitchZ: .word 0
orthoTerm: .word 0
orthoLeft: .word 0
orthoRight: .word 0
orthoShift: .fill 4,0
orthoProduct: .fill 4,0
orthoSign: .byte 0
orthoSineLo: .fill 256,round(16384*sin(i*2*PI/256))&255
orthoSineHi: .fill 256,(round(16384*sin(i*2*PI/256))>>8)&255
