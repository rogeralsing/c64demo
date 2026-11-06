// Perspective-correct face culling uses the actual projected corners. Outward
// triangle windings, in face-bit order X-, X+, Y-, Y+, Z-, Z+, are:
// (0,4,2), (1,3,5), (0,1,4), (2,6,3), (0,2,1), (4,5,6).
// Screen Y points down, so a front-facing triangle has positive signed area.
// Keep zero-area faces visible to retain their edges at quantized silhouettes.

// Public contract: call cullFaces after projectCube. It writes visibleFaces.
// Draw an edge when either adjacent face bit is set. Coordinates must remain
// in the 128x128 canvas, making each signed delta fit in one byte.
// This module owns $c0..$c9, clobbers A/X/Y, and does not modify its code.
.label cullDX1 = $c0
.label cullDY1 = $c1
.label cullDX2 = $c2
.label cullDY2 = $c3
.label cullProductSign = $c4
.label cullProductLo = $c5
.label cullProductHi = $c6
.label cullMultiplyA = $c7
.label cullSumLo = $c8
.label cullSumHi = $c9

.macro CullFace(v0, v1, v2, mask) {
    lda projectedX+v1
    sec
    sbc projectedX+v0
    sta cullDX1
    lda projectedY+v1
    sec
    sbc projectedY+v0
    sta cullDY1
    lda projectedX+v2
    sec
    sbc projectedX+v0
    sta cullDX2
    lda projectedY+v2
    sec
    sbc projectedY+v0
    sta cullDY2
    jsr cullTriangleArea
    bcc !hidden+
    lda visibleFaces
    ora #mask
    sta visibleFaces
!hidden:
}

cullFaces:
    lda #0
    sta visibleFaces
    CullFace(0, 4, 2, $01)
    CullFace(1, 3, 5, $02)
    CullFace(0, 1, 4, $04)
    CullFace(2, 6, 3, $08)
    CullFace(0, 2, 1, $10)
    CullFace(4, 5, 6, $20)
    rts

// For area P-Q, differing product signs decide the answer without multiplying.
// Handle zero products separately so their sign is always canonical.
cullZeroProductP:
    lda cullDY1
    beq cullAreaVisible
    lda cullDX2
    beq cullAreaVisible
    eor cullDY1
    bmi cullAreaVisible
    clc
    rts
cullZeroProductQ:
    bit cullProductSign
    bmi cullAreaHidden
cullAreaVisible:
    sec
    rts
cullAreaHidden:
    clc
    rts

.macro CullAbsolute(address) {
    lda address
    bpl !positive+
    eor #$ff
    clc
    adc #1
    sta address
!positive:
}

// Return C=1 for area >= 0. P=DX1*DY2 and Q=DY1*DX2 are signed products.
cullTriangleArea:
    lda cullDX1
    beq cullZeroProductP
    lda cullDY2
    beq cullZeroProductP
    eor cullDX1
    sta cullProductSign
    lda cullDY1
    beq cullZeroProductQ
    lda cullDX2
    beq cullZeroProductQ
    eor cullDY1
    eor cullProductSign
    bpl !sameSign+
    bit cullProductSign
    bmi cullAreaHidden
    sec
    rts
!sameSign:
    CullAbsolute(cullDX1)
    CullAbsolute(cullDY1)
    CullAbsolute(cullDX2)
    CullAbsolute(cullDY2)

    lda cullDX1
    ldx cullDY2
    jsr cullUnsignedMultiply
    stx cullProductLo
    sta cullProductHi
    lda cullDY1
    ldx cullDX2
    jsr cullUnsignedMultiply

    // Compare |Q| with |P|. Equal products make a zero-area visible face.
    cmp cullProductHi
    bne !compared+
    txa
    cmp cullProductLo
    beq !visible+
!compared:
    bit cullProductSign
    bmi !negativeProducts+
    bcc !visible+
    clc
    rts
!negativeProducts:
    bcs !visible+
    clc
    rts
!visible:
    sec
    rts

// Exact unsigned 0..127 multiplication: input A and X, output A:X (high:low).
// Q(n)=floor(n*n/4), so a*b=Q(a+b)-Q(abs(a-b)); table indices are at most 254.
cullUnsignedMultiply:
    sta cullMultiplyA
    txa
    clc
    adc cullMultiplyA
    tay
    lda cullQuarterLo,y
    sta cullSumLo
    lda cullQuarterHi,y
    sta cullSumHi
    txa
    sec
    sbc cullMultiplyA
    bcs !positiveDifference+
    eor #$ff
    adc #1
!positiveDifference:
    tay
    lda cullSumLo
    sec
    sbc cullQuarterLo,y
    tax
    lda cullSumHi
    sbc cullQuarterHi,y
    rts

visibleFaces: .byte 0

.align $100
cullTablesStart:
cullQuarterLo:
    .fill 256, <floor(i*i/4)
cullQuarterHi:
    .fill 256, >floor(i*i/4)
cullTablesEnd:
