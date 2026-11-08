.importonce

// Exact vertical-prefix polygon crossings, separated from their storage layout.
// Caller provides byte variables lineX0, lineY0, lineX1, lineY1, boundaryColor.
// drawBoundary may reorder the two endpoints. It skips zero transitions and
// vertical edges, then samples logical X in [leftX,rightX), crossing at the
// exact rational ceiling. Coordinates are unsigned bytes; callers own clipping
// and any terminal-row sink. There is no charset/bitmap/interlace assumption.
//
// Caller implements plotBoundaryMarker. At each call, X is logical X, Y is the
// crossing row and A is boundaryColor. The callback may clobber A/X/Y and flags,
// but must preserve the inputs and polygonEdge* state. drawBoundary clobbers
// A/X/Y and flags and owns only its private scalar state below, with no zero page.
//
// The floor-step/nonnegative-remainder representation and -1 fraction bias
// preserve src/xor-fill.asm's exact half-open crossing rule. This compact seam
// uses ordinary callback dispatch rather than the original generated kernels.

// The macro form lets another renderer reuse these exact crossings with
// its own entry and storage callback. The default entry retains its old ABI.
.macro PolygonEdgeCode(plotCallback) {
    lda boundaryColor
    bne !colored+
    rts
!colored:
    lda lineX0
    cmp lineX1
    bne !nonVertical+
    rts
!nonVertical:
    bcc !ordered+
    ldx lineX1
    stx lineX0
    sta lineX1
    lda lineY0
    ldx lineY1
    stx lineY0
    sta lineY1
!ordered:
    lda lineX0
    sta polygonEdgeX
    lda lineY0
    sta polygonEdgeY
    lda lineX1
    sec
    sbc lineX0
    sta polygonEdgeDX
    cmp #1
    bne !slope+
    ldx polygonEdgeX
    ldy polygonEdgeY
    lda boundaryColor
    jmp plotCallback
!slope:
    lda lineY1
    sec
    sbc lineY0
    bcs !positive+
    eor #$ff
    clc
    adc #1
    ldx #$ff
    bne !direction+
!positive:
    ldx #0
!direction:
    stx polygonEdgeDirection
    ldx #0
    sec
!divide:
    sbc polygonEdgeDX
    bcc !divided+
    inx
    bcs !divide-
!divided:
    adc polygonEdgeDX
    sta polygonEdgeFractionStep
    txa
    ldx polygonEdgeDirection
    beq !positiveStep+
    eor #$ff
    clc
    adc #1
    sta polygonEdgeRowStep
    lda polygonEdgeFractionStep
    beq !stepReady+
    dec polygonEdgeRowStep
    lda polygonEdgeDX
    sec
    sbc polygonEdgeFractionStep
    sta polygonEdgeFractionStep
    jmp !stepReady+
!positiveStep:
    sta polygonEdgeRowStep
!stepReady:
    lda #$ff
    sta polygonEdgeFraction
!sample:
    ldx polygonEdgeX
    ldy polygonEdgeY
    lda boundaryColor
    jsr plotCallback
    inc polygonEdgeX
    lda polygonEdgeX
    cmp lineX1
    beq !done+
    lda polygonEdgeFraction
    clc
    adc polygonEdgeFractionStep
    bcc !fractionReady+
    sbc polygonEdgeDX
    inc polygonEdgeY
!fractionReady:
    sta polygonEdgeFraction
    lda polygonEdgeY
    clc
    adc polygonEdgeRowStep
    sta polygonEdgeY
    jmp !sample-
!done:
    rts

@polygonEdgeDX: .byte 0
@polygonEdgeDirection: .byte 0
@polygonEdgeRowStep: .byte 0
@polygonEdgeFractionStep: .byte 0
@polygonEdgeFraction: .byte 0
@polygonEdgeX: .byte 0
@polygonEdgeY: .byte 0
}

#if !POLYGON_EDGES_MACRO_ONLY
drawBoundary: PolygonEdgeCode(plotBoundaryMarker)
#endif
