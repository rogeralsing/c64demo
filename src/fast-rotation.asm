.importonce

// Fixed 21/34 icosahedron, exact existing Q6 quarter-square rounding.
// These are reusable arithmetic products, not transformed/projected poses.
.label fastProduct21 = $e000
.label fastProduct34 = $e100
.label fastRotationTablesStart = fastProduct21
.label fastRotationTablesEnd = fastProduct34+$100
.assert "Fast rotation product table alignment", fastRotationTablesStart & $ff, 0
.assert "Fast rotation product bytes", fastRotationTablesEnd-fastRotationTablesStart, 512
.errorif fastRotationTablesEnd > $f400, "Fast rotation tables reach reserved high RAM"

// Store one result and its exact antipode. Existing m(a,b) is odd in either
// operand in this model's signed-byte domain; no rounding is added here.
.macro FastRotationPair(axis, first, opposite) {
    sta axis+first
    eor #$ff
    clc
    adc #1
    sta axis+opposite
}

.macro FastRotationCode() {
    .errorif SCALE != 64 || ICOSA_VERTEX_COUNT != 12, "Fast rotation requires the fixed Q6 icosahedron"
    .var expectedX = List().add(0,0,0,0,-21,-21,21,21,-34,-34,34,34)
    .var expectedY = List().add(-21,-21,21,21,-34,34,-34,34,0,0,0,0)
    .var expectedZ = List().add(-34,34,-34,34,0,0,0,0,-21,21,-21,21)
    .for (var vertex = 0; vertex < 12; vertex++) {
        .errorif icosaX.get(vertex) != expectedX.get(vertex) || icosaY.get(vertex) != expectedY.get(vertex) || icosaZ.get(vertex) != expectedZ.get(vertex), "Fast rotation requires the audited vertex order and 21/34 coordinates"
    }
@fastRotationCodeStart:
    ldx angleYaw
    lda sineUnit,x
    sta axisZX
    lda fastProduct21,x
    sta fastYawS21
    lda fastProduct34,x
    sta fastYawS34
    txa
    clc
    adc #64
    tax
    lda sineUnit,x
    sta axisXX
    lda fastProduct21,x
    sta fastYawC21
    lda fastProduct34,x
    sta fastYawC34

    ldx anglePitch
    lda sineUnit,x
    sta axisYZ
    lda fastProduct21,x
    sta fastPitchS21
    lda fastProduct34,x
    sta fastPitchS34
    txa
    clc
    adc #64
    tax
    lda sineUnit,x
    sta axisYY
    lda fastProduct21,x
    sta fastPitchC21
    lda fastProduct34,x
    sta fastPitchC34

    // Every yaw-Z is one of these four bases or its exact negative.
    lda fastYawC21
    clc
    adc fastYawS34
    sta fastYawZPlus
    lda fastYawC21
    sec
    sbc fastYawS34
    sta fastYawZMinus

    // Only eight dynamic products remain, using the unchanged original helper.
    lda axisYZ
    sta factor
    lda fastYawC34
    jsr multiplyScaled
    sta fastPitchSinC34
    lda fastYawS21
    jsr multiplyScaled
    sta fastPitchSinS21
    lda fastYawZPlus
    jsr multiplyScaled
    sta fastPitchSinPlus
    lda fastYawZMinus
    jsr multiplyScaled
    sta fastPitchSinMinus
    lda axisYY
    sta factor
    lda fastYawC34
    jsr multiplyScaled
    sta fastPitchCosC34
    lda fastYawS21
    jsr multiplyScaled
    sta fastPitchCosS21
    lda fastYawZPlus
    jsr multiplyScaled
    sta fastPitchCosPlus
    lda fastYawZMinus
    jsr multiplyScaled
    sta fastPitchCosMinus

    // Four X values repeat across the first two groups.
    lda fastYawS34
    sta rotatedX+1
    sta rotatedX+3
    eor #$ff
    clc
    adc #1
    sta rotatedX+0
    sta rotatedX+2
    lda fastYawC21
    sta rotatedX+6
    sta rotatedX+7
    eor #$ff
    clc
    adc #1
    sta rotatedX+4
    sta rotatedX+5

    lda fastPitchC21
    sec
    sbc fastPitchSinC34
    FastRotationPair(rotatedY, 3, 0)
    lda fastPitchS21
    clc
    adc fastPitchCosC34
    FastRotationPair(rotatedZ, 3, 0)
    lda fastPitchC21
    clc
    adc fastPitchSinC34
    FastRotationPair(rotatedY, 2, 1)
    lda fastPitchS21
    sec
    sbc fastPitchCosC34
    FastRotationPair(rotatedZ, 2, 1)

    lda fastPitchC34
    clc
    adc fastPitchSinS21
    FastRotationPair(rotatedY, 7, 4)
    lda fastPitchS34
    sec
    sbc fastPitchCosS21
    FastRotationPair(rotatedZ, 7, 4)
    lda fastPitchC34
    sec
    sbc fastPitchSinS21
    FastRotationPair(rotatedY, 5, 6)
    lda fastPitchS34
    clc
    adc fastPitchCosS21
    FastRotationPair(rotatedZ, 5, 6)

    lda fastYawC34
    clc
    adc fastYawS21
    FastRotationPair(rotatedX, 11, 8)
    lda fastYawC34
    sec
    sbc fastYawS21
    FastRotationPair(rotatedX, 10, 9)
    lda fastPitchSinMinus
    FastRotationPair(rotatedY, 8, 11)
    lda fastPitchSinPlus
    FastRotationPair(rotatedY, 10, 9)
    lda fastPitchCosMinus
    FastRotationPair(rotatedZ, 11, 8)
    lda fastPitchCosPlus
    FastRotationPair(rotatedZ, 9, 10)
    rts

// Call after CPU port $35, before CLI. Y survives multiplyScaled, allowing the
// generator to use the exact original helper and visit all 256 angle bytes.
@fastInitRotationTables:
    ldy #0
!angle:
    lda sineUnit,y
    sta factor
    lda #21
    jsr multiplyScaled
    sta fastProduct21,y
    lda #34
    jsr multiplyScaled
    sta fastProduct34,y
    iny
    bne !angle-
    rts
@fastRotationCodeEnd:

@fastRotationStateStart:
fastYawS21: .byte 0
fastYawS34: .byte 0
fastYawC21: .byte 0
fastYawC34: .byte 0
fastPitchS21: .byte 0
fastPitchS34: .byte 0
fastPitchC21: .byte 0
fastPitchC34: .byte 0
fastYawZPlus: .byte 0
fastYawZMinus: .byte 0
fastPitchSinC34: .byte 0
fastPitchSinS21: .byte 0
fastPitchSinPlus: .byte 0
fastPitchSinMinus: .byte 0
fastPitchCosC34: .byte 0
fastPitchCosS21: .byte 0
fastPitchCosPlus: .byte 0
fastPitchCosMinus: .byte 0
@fastRotationStateEnd:
    .assert "Fast rotation cache bytes", fastRotationStateEnd-fastRotationStateStart, 18
}
