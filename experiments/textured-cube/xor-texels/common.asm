// Texture corrections are color transitions in the actual XOR fill operands.
// Each column starts outside material3, enters its texture and returns to3.
// No technique writes a charset; the one shared xorFill paints the final image.
.label texelMarkerPointer=$e0
.label texelSampleValue=$e2
.label texelMarkerValue=$e3
.label texelSavedY=$e4
.label texelSavedX=$e5
.label texelTop=$cf00
.label texelBottom=$cf40

texelBuildFaceSpans:
    .for (var edge=0; edge<4; edge++) {
        .var corners=List().add(0,2,3,1)
        .var a=corners.get(edge)
        .var b=corners.get((edge+1)&3)
        lda projectedX+a
        sta lineX0
        lda projectedY+a
        sta lineY0
        lda projectedX+b
        sta lineX1
        cmp lineX0
        beq !vertical+
        lda #1
        bcs !entry+
        lda #2
    !entry:
        sta boundaryColor
        lda projectedY+b
        sta lineY1
        jsr texelSpanEdge
    !vertical:
    }
    rts

.import source "../../lib/polygon-edges.asm"
texelSpanEdge: PolygonEdgeCode(texelStoreSpanCrossing)
texelStoreSpanCrossing:
    cmp #1
    bne !exit+
    tya
    sta texelTop,x
    rts
!exit:
    tya
    sta texelBottom,x
    rts

texelBuildFaceMarkers:
    jsr texelTechniquePrepare
    ldx #0
    lda drawBufferHi
    and #8
    beq !buffer+
    inx
!buffer:
    lda xorFillBankHigh,x
    sta texelFrameMarkerBase
    lda hybridMinX
    sta texelColumnX
!column:
    ldx texelColumnX
    lda texelTop,x
    sta texelColumnTop
    cmp texelBottom,x
    bcs !next+
    lda texelBottom,x
    sta texelColumnBottom
    lda hybridColumnUCache,x
    sta texelColumnU
    lda hybridColumnVCache,x
    sta texelColumnV
    txa
    and #$fc
    clc
    adc texelFrameMarkerBase
    sta texelColumnMarkerBase
    txa
    and #3
    asl
    asl
    tax
    .for (var delta=1; delta<4; delta++) {
        lda texelLaneColors+delta,x
        sta texelDeltaColors+delta
    }
    jsr texelBuildColumn
!next:
    inc texelColumnX
    lda texelColumnX
    cmp hybridMaxX
    bne !column-
    rts

// Y is the sampled screen row. Preserve X/Y; return the unshifted selector.
texelSampleColor:
    stx texelSavedX
    lda hybridRowUCache,y
    clc
    adc texelColumnU
    and #15
    sta texelSampleValue
    lda hybridRowVCache,y
    clc
    adc texelColumnV
    and #$f0
    ora texelSampleValue
    tax
    lda texture,x
    ldx texelSavedX
    rts

// A is a color delta, Y its integer crossing row. Preserve X/Y. These are
// the real immediate marker operands, not an intermediate texture image.
texelEmitTransition:
    cmp #0
    beq !done+
    sty texelSavedY
    tay
    lda texelDeltaColors,y
    sta texelMarkerValue
    ldy texelSavedY
    lda xorOperandLo,y
    sta texelMarkerPointer
    lda xorOperandPage,y
    clc
    adc texelColumnMarkerBase
    sta texelMarkerPointer+1
    ldy #0
    lda texelMarkerValue
    eor (texelMarkerPointer),y
    sta (texelMarkerPointer),y
    ldy texelSavedY
!done:
    rts

texelLaneColors:
    .byte 0,$40,$80,$c0, 0,$10,$20,$30, 0,4,8,12, 0,1,2,3
texelDeltaColors: .byte 0,0,0,0
texelFrameMarkerBase: .byte 0
texelColumnMarkerBase: .byte 0
texelColumnX: .byte 0
texelColumnTop: .byte 0
texelColumnBottom: .byte 0
texelColumnU: .byte 0
texelColumnV: .byte 0

#if XOR_TEXEL_SCAN
.import source "techniques/scan.asm"
#endif
#if XOR_TEXEL_JUMPS
.import source "techniques/jumps.asm"
#endif
#if XOR_TEXEL_EVENTS
.import source "techniques/row-events.asm"
#endif
