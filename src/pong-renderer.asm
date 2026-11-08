.importonce

// Live, self-playing Pong on the front Z- face of a gently rocking cube.
// Face-local u points right and v points down. A black court cuts into the
// blue front face; separate white rectangles provide the paddles and ball.
// All rectangles feed the same exact boundary sampler and one prefix fill.
.const PONG_BODY_VERTEX_COUNT = 8
.const PONG_VERTEX_COUNT = 12
.const PONG_FACE_COUNT = 6
.const PONG_EDGE_COUNT = 12
.const PONG_SCRATCH_FIRST = 8
.label pongHalfSize = HALF_SIZE
.label pongCourtHalfSize = 27
.label pongPaddleInner = 20
.label pongPaddleOuter = 24
.label pongPaddleHalfHeight = 6
.label pongPaddleLimit = 17
.label pongBallHalfSize = 2
.label pongCollisionRadius = 4
.label pongPaddleContact = 16
.label pongWallContact = 22
.label pongPaddleHitHalfHeight = 10
.label pongYawBias = 16
.label pongPitchBias = -14
.label pongYawAmplitude = 4
.label pongPitchAmplitude = 3
.label pongPhaseStep = 4
.errorif HALF_SIZE != 32, "Pong requires thirty-two-unit cube corners"

// The existing cull workspace is reused after body culling. Rectangle inputs
// occupy C0..C3, four mapping terms occupy C4..C7, and C9 selects a world axis.
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

// The front court remains at negative depth throughout the bounded motion.
// Cached coordinates are -41..41; depths are -48..0. Even the complete table
// grid obeys |coordinate|+depthFactor <= 41+85, within the Q6 product domain.
.const PONG_PROJECTION_COORD_MIN = -41
.const PONG_PROJECTION_COORD_MAX = 41
.const PONG_PROJECTION_WIDTH = 83
.const PONG_PROJECTION_DEPTH_MIN = -48
.const PONG_PROJECTION_DEPTH_MAX = 0
.const PONG_PROJECTION_ROWS = 49
.label pongProjectionTablesStart = $e000
.label pongProjectionOffsets = pongProjectionTablesStart
.label pongProjectionOffsetsEnd = pongProjectionOffsets+PONG_PROJECTION_WIDTH*PONG_PROJECTION_ROWS
.label pongProjectionRowLo = $fb00
.label pongProjectionRowHi = $fb80
.label pongProjectionTablesEnd = $fc00
.errorif pongProjectionOffsetsEnd > pongProjectionRowLo, "Pong projection products overlap their row pointers"
.errorif pongProjectionTablesEnd-pongProjectionTablesStart != 28*$100, "Pong projection reservation must be twenty-eight pages"

.function PongQuad(a, b, c, d) {
    .var result = List()
    .eval result.add(a)
    .eval result.add(b)
    .eval result.add(c)
    .eval result.add(d)
    .return result
}

.var pongQuads = List()
.eval pongQuads.add(PongQuad(0, 4, 6, 2))
.eval pongQuads.add(PongQuad(1, 3, 7, 5))
.eval pongQuads.add(PongQuad(0, 1, 5, 4))
.eval pongQuads.add(PongQuad(2, 6, 7, 3))
.eval pongQuads.add(PongQuad(0, 2, 3, 1))
.eval pongQuads.add(PongQuad(4, 5, 7, 6))
.var pongFaceColors = List()
.eval pongFaceColors.add(2)
.eval pongFaceColors.add(2)
.eval pongFaceColors.add(3)
.eval pongFaceColors.add(3)
.eval pongFaceColors.add(1)
.eval pongFaceColors.add(1)
.var pongEdges = List()
.for (var first = 0; first < PONG_BODY_VERTEX_COUNT; first++) {
    .for (var last = first+1; last < PONG_BODY_VERTEX_COUNT; last++) {
        .var adjacent = List()
        .for (var face = 0; face < PONG_FACE_COUNT; face++) {
            .var hasFirst = false
            .var hasLast = false
            .for (var corner = 0; corner < 4; corner++) {
                .if (pongQuads.get(face).get(corner) == first) { .eval hasFirst = true }
                .if (pongQuads.get(face).get(corner) == last) { .eval hasLast = true }
            }
            .if (hasFirst && hasLast) { .eval adjacent.add(face) }
        }
        .if (adjacent.size() == 2) {
            .var edge = List()
            .eval edge.add(first)
            .eval edge.add(last)
            .eval edge.add(adjacent.get(0))
            .eval edge.add(adjacent.get(1))
            .eval pongEdges.add(edge)
        }
    }
}
.errorif pongEdges.size() != PONG_EDGE_COUNT, "Pong cube must have twelve body edges"

.macro PongModelData() {
@pongTablesStart:
@pongFaceA:     .fill PONG_FACE_COUNT, pongQuads.get(i).get(0)
@pongFaceB:     .fill PONG_FACE_COUNT, pongQuads.get(i).get(1)
@pongFaceC:     .fill PONG_FACE_COUNT, pongQuads.get(i).get(2)
@pongFaceD:     .fill PONG_FACE_COUNT, pongQuads.get(i).get(3)
@pongFaceColor: .fill PONG_FACE_COUNT, pongFaceColors.get(i)
@pongFaceBits:  .fill PONG_FACE_COUNT, 1 << i
@pongEdgeA:     .fill PONG_EDGE_COUNT, pongEdges.get(i).get(0)
@pongEdgeB:     .fill PONG_EDGE_COUNT, pongEdges.get(i).get(1)
@pongEdgeFaceA: .fill PONG_EDGE_COUNT, pongEdges.get(i).get(2)
@pongEdgeFaceB: .fill PONG_EDGE_COUNT, pongEdges.get(i).get(3)
@pongTablesEnd:
    .assert "Pong body table bytes", pongTablesEnd-pongTablesStart, PONG_FACE_COUNT*6+PONG_EDGE_COUNT*4
}

// Startup arithmetic cache. Called by pongInit with interrupts disabled and
// the display blank. The complete range, including gaps/invalid rows, is zeroed.
.macro PongPrepareCode() {
@pongPrepareCodeStart:
@pongInitProjection:
    lda #<pongProjectionTablesStart
    sta linePointer
    lda #>pongProjectionTablesStart
    sta linePointer+1
    ldx #(pongProjectionTablesEnd-pongProjectionTablesStart)/$100
    ldy #0
    lda #0
!clear:
    sta (linePointer),y
    iny
    bne !clear-
    inc linePointer+1
    dex
    bne !clear-
    lda #<pongProjectionOffsets
    sta linePointer
    lda #>pongProjectionOffsets
    sta linePointer+1
    lda #0
    sta cullDX1
!row:
    ldx cullDX1
    lda linePointer
    sta pongProjectionRowLo,x
    lda linePointer+1
    sta pongProjectionRowHi,x
    txa
    clc
    adc #64+PONG_PROJECTION_DEPTH_MIN
    tax
    lda depthFactors,x
    sta factor
    ldy #0
!coordinate:
    tya
    sec
    sbc #-PONG_PROJECTION_COORD_MIN
    jsr multiplyScaled
    clc
    adc #64
    sta (linePointer),y
    iny
    cpy #PONG_PROJECTION_WIDTH
    bne !coordinate-
    lda linePointer
    clc
    adc #PONG_PROJECTION_WIDTH
    sta linePointer
    bcc !nextRow+
    inc linePointer+1
!nextRow:
    inc cullDX1
    lda cullDX1
    cmp #PONG_PROJECTION_ROWS
    bne !row-
    rts
@pongPrepareCodeEnd:
}

// Main drawing stays in the existing renderer prelude. The game and shared
// quad helpers are emitted separately into the free page range above $CC00.
.macro PongDrawCode() {
    .errorif VERTEX_COUNT != PONG_VERTEX_COUNT, "Pong needs four shared scratch vertices"
    .errorif rotatedY-rotatedX != VERTEX_COUNT || rotatedZ-rotatedY != VERTEX_COUNT, "Pong mapping requires contiguous coordinate rows"
@pongDrawCodeStart:
@drawPongCube:
    jsr pongPrepareColors
    ldy #PONG_EDGE_COUNT-1
!body:
    sty cullSumLo
    ldx pongEdgeFaceA,y
    lda xorFaceColors,x
    sta boundaryColor
    ldx pongEdgeFaceB,y
    lda xorFaceColors,x
    eor boundaryColor
    beq !bodyNext+
    sta boundaryColor
    ldx pongEdgeA,y
    lda projectedX,x
    sta lineX0
    lda projectedY,x
    sta lineY0
    ldx pongEdgeB,y
    lda projectedX,x
    sta lineX1
    lda projectedY,x
    sta lineY1
    jsr drawBoundary
!bodyNext:
    ldy cullSumLo
    dey
    bpl !body-

    // Black court replaces blue: selector 1 XOR 1 = 0.
    lda #-pongCourtHalfSize
    sta cullDX1
    sta cullDX2
    lda #pongCourtHalfSize
    sta cullDY1
    sta cullDY2
    lda #1
    sta boundaryColor
    jsr pongDrawQuad

    // White rectangles lie inside the black court and remain disjoint.
    lda #3
    sta boundaryColor
    lda #-pongPaddleOuter
    sta cullDX1
    lda #-pongPaddleInner
    sta cullDY1
    lda pongLeftY
    sec
    sbc #pongPaddleHalfHeight
    sta cullDX2
    lda pongLeftY
    clc
    adc #pongPaddleHalfHeight
    sta cullDY2
    jsr pongDrawQuad
    lda #pongPaddleInner
    sta cullDX1
    lda #pongPaddleOuter
    sta cullDY1
    lda pongRightY
    sec
    sbc #pongPaddleHalfHeight
    sta cullDX2
    lda pongRightY
    clc
    adc #pongPaddleHalfHeight
    sta cullDY2
    jsr pongDrawQuad
    lda pongBallX
    sec
    sbc #pongBallHalfSize
    sta cullDX1
    lda pongBallX
    clc
    adc #pongBallHalfSize
    sta cullDY1
    lda pongBallY
    sec
    sbc #pongBallHalfSize
    sta cullDX2
    lda pongBallY
    clc
    adc #pongBallHalfSize
    sta cullDY2
    jsr pongDrawQuad
    rts
@pongDrawCodeEnd:
}

.macro PongRuntimeCode() {
@pongRuntimeCodeStart:

// A collision radius of four and a drawn half-size of two leave a two-unit
// black gap at contact. This keeps independently projected white quads from
// cancelling through XOR. Positions are live signed integer face units.
@pongInit:
    jsr pongInitProjection
    lda #0
    sta pongBallX
    sta pongBallY
    sta pongLeftY
    sta pongRightY
    sta pongPhase
    sta pongMisses
    lda #1
    sta pongBallVX
    sta pongBallVY
    jmp pongApplyMotion

// Update once after presentation. AI observes the old ball, then the ball
// advances, walls clamp/reflect, and the selected paddle either reflects X or
// causes an immediate center serve. Motion advances after all game decisions.
@pongUpdate:
    jsr pongMovePaddles
    lda pongBallX
    clc
    adc pongBallVX
    sta pongBallX
    lda pongBallY
    clc
    adc pongBallVY
    sta pongBallY
    eor #$80
    cmp #$80+pongWallContact
    bcs !bottom+
    cmp #$80-pongWallContact+1
    bcc !top+
    jmp !wallsDone+
!top:
    lda #-pongWallContact
    bne !wall+
!bottom:
    lda #pongWallContact
!wall:
    sta pongBallY
    lda pongBallVY
    eor #$ff
    clc
    adc #1
    sta pongBallVY
!wallsDone:
    lda pongBallX
    eor #$80
    cmp #$80+pongPaddleContact
    bcs !right+
    cmp #$80-pongPaddleContact+1
    bcc !left+
    jmp !motion+
!right:
    ldx #1
    bne !paddle+
!left:
    ldx #0
!paddle:
    lda pongBallY
    sec
    sbc pongLeftY,x
    bpl !distance+
    eor #$ff
    clc
    adc #1
!distance:
    cmp #pongPaddleHitHalfHeight+1
    bcs !miss+
    lda pongBallVX
    eor #$ff
    clc
    adc #1
    sta pongBallVX
    jmp !motion+
!miss:
    lda #0
    sta pongBallX
    sta pongBallY
    inc pongMisses
    lda pongBallVY
    eor #$ff
    clc
    adc #1
    sta pongBallVY
!motion:
    lda pongPhase
    clc
    adc #pongPhaseStep
    sta pongPhase
    jmp pongApplyMotion

// Incoming paddle follows the old ball Y; the other returns toward center.
// Both move at most one unit and remain inside the court's vertical margin.
@pongMovePaddles:
    ldx #1
!paddle:
    lda #0
    sta cullDX1
    lda pongBallVX
    eor pongPaddleDirections,x
    bmi !target+
    lda pongBallY
    sta cullDX1
!target:
    lda cullDX1
    sec
    sbc pongLeftY,x
    beq !next+
    bmi !up+
    lda pongLeftY,x
    cmp #pongPaddleLimit
    beq !next+
    inc pongLeftY,x
    jmp !next+
!up:
    lda pongLeftY,x
    cmp #-pongPaddleLimit
    beq !next+
    dec pongLeftY,x
!next:
    dex
    bpl !paddle-
    rts

// Bounded 64-pose rocking uses the existing sine and exact Q6 multiply. It
// stores motion functions rather than prepared game positions or images.
@pongApplyMotion:
    lda #pongYawAmplitude
    sta factor
    ldx pongPhase
    lda sineUnit,x
    jsr multiplyScaled
    clc
    adc #pongYawBias
    sta angleYaw
    lda #pongPitchAmplitude
    sta factor
    lda pongPhase
    clc
    adc #64
    tax
    lda sineUnit,x
    jsr multiplyScaled
    clc
    adc #pongPitchBias
    sta anglePitch
    rts

@pongPrepareColors:
    ldx #PONG_FACE_COUNT-1
!face:
    lda visibleFaces
    and pongFaceBits,x
    beq !hidden+
    lda pongFaceColor,x
!hidden:
    sta xorFaceColors,x
    dex
    bpl !face-
    rts

// Input rectangle: C0=u0, C1=u1, C2=v0, C3=v1. For each world component,
// P=M(u,2*axisX)-M(v,2*axisY)-axisZ, with independent signed subtractions.
// Four products per axis are shared between the rectangle's four corners.
@pongMakeQuad:
    lda #<rotatedX
    sta linePointer
    lda #>rotatedX
    sta linePointer+1
    lda #0
    sta cullSumHi
!axis:
    ldx cullSumHi
    lda axisXX,x
    asl
    sta factor
    lda cullDX1
    jsr multiplyScaled
    sta cullProductSign
    lda cullDY1
    jsr multiplyScaled
    sta cullProductLo
    ldx cullSumHi
    lda axisYX,x
    asl
    sta factor
    // The Y axis has no world-X component. Its two products are exactly zero.
    // Skip those multiplies while keeping the four corner sums unchanged.
    bne !verticalProducts+
    sta cullProductHi
    sta cullMultiplyA
    jmp !termsReady+
!verticalProducts:
    lda cullDX2
    jsr multiplyScaled
    sta cullProductHi
    lda cullDY2
    jsr multiplyScaled
    sta cullMultiplyA
!termsReady:
    ldx cullSumHi
    .for (var corner = 0; corner < 4; corner++) {
        .var uTerm = (corner == 0 || corner == 3) ? cullProductSign : cullProductLo
        .var vTerm = corner < 2 ? cullProductHi : cullMultiplyA
        lda uTerm
        sec
        sbc vTerm
        sec
        sbc axisZX,x
        ldy #PONG_SCRATCH_FIRST+corner
        sta (linePointer),y
    }
    inc cullSumHi
    lda cullSumHi
    cmp #3
    beq !done+
    lda linePointer
    clc
    adc #VERTEX_COUNT
    sta linePointer
    bcc !nextAxis+
    inc linePointer+1
!nextAxis:
    jmp !axis-
!done:
    rts

@pongProjectQuad:
    ldx #PONG_SCRATCH_FIRST
!vertex:
    lda rotatedZ,x
    clc
    adc #-PONG_PROJECTION_DEPTH_MIN
    tay
    lda pongProjectionRowLo,y
    sta linePointer
    lda pongProjectionRowHi,y
    sta linePointer+1
    lda rotatedX,x
    clc
    adc #-PONG_PROJECTION_COORD_MIN
    tay
    lda (linePointer),y
    lsr
    sta projectedX,x
    lda rotatedY,x
    clc
    adc #-PONG_PROJECTION_COORD_MIN
    tay
    lda (linePointer),y
    eor #$ff
    clc
    adc #129
    sta projectedY,x
    inx
    cpx #PONG_VERTEX_COUNT
    bne !vertex-
    rts

@pongDrawQuad:
    jsr pongMakeQuad
    jsr pongProjectQuad
    .for (var edge = 0; edge < 4; edge++) {
        .var first = PONG_SCRATCH_FIRST+edge
        .var last = PONG_SCRATCH_FIRST+((edge+1) & 3)
        lda projectedX+first
        sta lineX0
        lda projectedY+first
        sta lineY0
        lda projectedX+last
        sta lineX1
        lda projectedY+last
        sta lineY1
        jsr drawBoundary
    }
    rts
@pongRuntimeCodeEnd:
    .errorif pongRuntimeCodeEnd > $d000, "Pong runtime overlaps mapped I/O"

@pongStateStart:
@pongBallX:  .byte 0
@pongBallY:  .byte 0
@pongBallVX: .byte 1
@pongBallVY: .byte 1
@pongLeftY:  .byte 0
@pongRightY: .byte 0
@pongPhase:  .byte 0
@pongMisses: .byte 0
@pongStateEnd:
@pongPaddleDirections: .byte $ff, 1
    .errorif * > $d000, "Pong state overlaps mapped I/O"
}
