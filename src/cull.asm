// Perspective-correct face culling uses the actual projected corners. Outward
// triangle windings, in face-bit order X-, X+, Y-, Y+, Z-, Z+, are:
// (0,4,2), (1,3,5), (0,1,4), (2,6,3), (0,2,1), (4,5,6).
// Screen Y points down, so a front-facing triangle has positive signed area.
// Keep zero-area faces visible to retain their edges at quantized silhouettes.

// Public contract: call cullFaces after projectCube. It writes visibleFaces.
// Draw an edge when either adjacent face bit is set. Coordinates must remain
// in the 128x128 canvas, making each signed delta fit in one byte.
// This module owns $c0..$c9, clobbers A/X/Y, and does not modify its code.
#if !FAST_SOLID && !PAINTED && !PONG
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
#endif

#if INTERLACED || FAST_SOLID
// These cutoffs were exhaustively audited over all 65,536 yaw/pitch pairs for
// the current 21/34 integer icosahedron, Q6 transform, and 29/20 projection zoom.
// Re-audit them before changing the model, camera, or projection. The three-Z
// sum stays within -97..97, so signed byte addition is sufficient.
.errorif CAMERA_DISTANCE != 144 || FOCAL_LENGTH != 128 || SCALE != 64, "Depth culling requires the audited camera and Q6 transform"
.errorif ICOSA_VERTEX_COUNT != 12 || ICOSA_FACE_COUNT != 20, "Depth culling requires the audited icosahedron"
.for (var vertex = 0; vertex < ICOSA_VERTEX_COUNT; vertex++) {
    .var x = abs(icosaX.get(vertex))
    .var y = abs(icosaY.get(vertex))
    .var z = abs(icosaZ.get(vertex))
    .errorif !((x == 0 && y == 21 && z == 34) || (x == 21 && y == 34 && z == 0) || (x == 34 && y == 0 && z == 21)), "Depth culling requires the audited 21/34 vertices"
}

// Emit in the existing padding after fillStateEnd, keeping the culling tables
// at $3200/$3300 and the fill banks at $4c00/$8c00. Y is the preserved face index.
// Return C=1/A=0 or 1 when decided; C=0 requests the exact projected-area test.
.macro IcosahedronDepthCull() {
@cullDepthCodeStart:
@cullDepthShortcut:
    ldx modelFaceA,y
    lda rotatedZ,x
    ldx modelFaceB,y
    clc
    adc rotatedZ,x
    ldx modelFaceC,y
    clc
    adc rotatedZ,x
#if FAST_SOLID
    // Keep every signed sum, including hidden faces, for flat face tones.
    // STA preserves carry and the audited visibility comparisons below.
    sta fastFaceDepth,y
#endif
    eor #$80
    cmp #98
    bcc !visible+
    cmp #116
    bcs !hidden+
    clc
    rts
!visible:
    lda #1
    sec
    rts
!hidden:
    lda #0
    sec
    rts
@cullDepthCodeEnd:
}
#endif

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
#if GLENZ
glenzCullCodeStart:
    // Both sides of both tetrahedra contribute to the intended XOR image.
    lda #$ff
    sta visibleFaces
    rts
glenzCullCodeEnd:
#else
#if PONG
// Every audited Pong pose exposes X+, Y+, and Z-. Keep this shortcut tied to
// that bounded motion and camera; the independent audit checks all 64 poses.
.label pongVisibleFaceMask = $1a
.errorif HALF_SIZE != 32 || SCALE != 64 || CAMERA_DISTANCE != 144 || FOCAL_LENGTH != 128, "Pong visibility shortcut requires the audited camera and cube"
.errorif pongYawBias != 16 || pongYawAmplitude != 4 || pongPitchBias != -14 || pongPitchAmplitude != 3 || pongPhaseStep != 4, "Pong visibility shortcut requires the audited rocking motion"
pongCullCodeStart:
    lda #pongVisibleFaceMask
    sta visibleFaces
    rts
pongCullCodeEnd:
#else
#if FAST_SOLID
    jmp fastCullPairedFaces
#else
#if ICOSAHEDRON
    // Each face gets its own flag; the model has more than eight triangles.
    ldy #ICOSA_FACE_COUNT-1
!face:
#if INTERLACED || FAST_SOLID
    jsr cullDepthShortcut
    bcs !store+
#endif
    sty objectFaceIndex
    ldx modelFaceA,y
    lda projectedX,x
    sta cullSumLo
    lda projectedY,x
    sta cullSumHi
    ldx modelFaceB,y
    lda projectedX,x
    sec
    sbc cullSumLo
    sta cullDX1
    lda projectedY,x
    sec
    sbc cullSumHi
    sta cullDY1
    ldx modelFaceC,y
    lda projectedX,x
    sec
    sbc cullSumLo
    sta cullDX2
    lda projectedY,x
    sec
    sbc cullSumHi
    sta cullDY2
    jsr cullTriangleArea
    lda #0
    rol
    ldy objectFaceIndex
!store:
    sta visibleFaces,y
    dey
    bpl !face-
    rts
#else
    lda #0
    sta visibleFaces
    CullFace(0, 4, 2, $01)
    CullFace(1, 3, 5, $02)
    CullFace(0, 1, 4, $04)
    CullFace(2, 6, 3, $08)
    CullFace(0, 2, 1, $10)
    CullFace(4, 5, 6, $20)
    rts
#endif
#endif

#endif
#endif
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

#if INTERLACED || FAST_SOLID
// Per-face flags are emitted inside fillState instead of this tight table page.
#else
#if ICOSAHEDRON
visibleFaces: .fill ICOSA_FACE_COUNT, 0
#else
visibleFaces: .byte 0
#endif
#endif

.align $100
cullTablesStart:
cullQuarterLo:
    .fill 256, <floor(i*i/4)
cullQuarterHi:
    .fill 256, >floor(i*i/4)
cullTablesEnd:
