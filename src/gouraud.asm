.importonce

// Exact Gouraud thresholding for one coherent image. Each triangle shares its
// setup across both physical-row parities. A 2x4 Bayer tile gives one threshold
// per logical-X lane within either parity.
// Existing prefix-fill workspace is reused; $df must retain its parity bit.
.label gH = $c0
.label gStep = $c3
.label gDelta = $c6
.label gQ = $c9
.label gProduct = $d0
.label gSign = $d3
.label gMulValue = $d4
.label gMulFactor = $d7
.label gPointer = $d8
.label gColumnPage = $da
.label gMask = $db
.label gTemporary = $dc

.macro GCopy24(source, destination) {
    .for (var byte = 0; byte < 3; byte++) {
        lda source+byte
        sta destination+byte
    }
}
.macro GAdd24(first, second, destination) {
    clc
    .for (var byte = 0; byte < 3; byte++) {
        lda first+byte
        adc second+byte
        sta destination+byte
    }
}
.macro GSub24(first, second, destination) {
    sec
    .for (var byte = 0; byte < 3; byte++) {
        lda first+byte
        sbc second+byte
        sta destination+byte
    }
}
.macro GNegate24(value) {
    sec
    .for (var byte = 0; byte < 3; byte++) {
        lda #0
        sbc value+byte
        sta value+byte
    }
}

.macro GouraudLightingPage() {
@gouraudLightTable:
    .assert "Gouraud light table alignment", * & $ff, 0
    .fill 256, max(1, min(8, 1+floor(7*max(0, i < 128 ? i : i-256)/sqrt(3194)+0.5)))
@gouraudLightTableEnd:
    .assert "Gouraud light table size", gouraudLightTableEnd-gouraudLightTable, 256
}

.macro GouraudRendererCode() {
@gouraudCodeStart:
@drawCubeBoundaries:
    ldy #ICOSA_VERTEX_COUNT-1
!light:
    lda rotatedY,y
    sec
    sbc rotatedZ,y
    tax
    lda gouraudLightTable,x
    sta gouraudVertexI,y
    dey
    bpl !light-
    ldy #ICOSA_FACE_COUNT-1
!face:
    sty gouraudFaceIndex
    lda visibleFaces,y
    beq !next+
    lda modelFaceColor,y
    sta gouraudMaterial
    ldx modelFaceA,y
    lda projectedX,x
    sta gouraudInputX
    lda projectedY,x
    sta gouraudInputY
    lda gouraudVertexI,x
    sta gouraudInputI
    ldx modelFaceB,y
    lda projectedX,x
    sta gouraudInputX+1
    lda projectedY,x
    sta gouraudInputY+1
    lda gouraudVertexI,x
    sta gouraudInputI+1
    ldx modelFaceC,y
    lda projectedX,x
    sta gouraudInputX+2
    lda projectedY,x
    sta gouraudInputY+2
    lda gouraudVertexI,x
    sta gouraudInputI+2
    jsr gouraudTriangle
!next:
    ldy gouraudFaceIndex
    dey
    bpl !face-
    rts

// Production triangle API: X[3]=0..63, Y[3]=0..128, I[3]=1..8, material1..3.
// Signed edge differences must fit -127..127. Either winding is accepted.
@gouraudTriangle:
    jsr gouraudPrepareTriangle
    bcc !done+
    lda #0
    sta gouraudParity
    jsr gouraudRenderField
    inc gouraudParity
    jmp gouraudRenderField
!done:
    rts

// Shared production setup. Carry reports whether a nondegenerate material
// triangle was prepared. gouraudRenderField consumes it without recomputation.
@gouraudPrepareTriangle:
    lda gouraudMaterial
    bne !material+
    clc
    rts
!material:
    lda gouraudInputI
    sta gouraudMinI
    sta gouraudMaxI
    .for (var vertex = 1; vertex < 3; vertex++) {
        lda gouraudInputI+vertex
        cmp gouraudMinI
        bcs !notMinI+
        sta gouraudMinI
    !notMinI:
        cmp gouraudMaxI
        bcc !notMaxI+
        sta gouraudMaxI
    !notMaxI:
    }
    .for (var vertex = 1; vertex < 3; vertex++) {
        lda gouraudInputX+vertex
        sec
        sbc gouraudInputX
        sta gouraudDX+vertex-1
        lda gouraudInputY+vertex
        sec
        sbc gouraudInputY
        sta gouraudDY+vertex-1
        lda gouraudInputI+vertex
        sec
        sbc gouraudInputI
        sta gouraudDI+vertex-1
    }
    lda gouraudDX
    ldx gouraudDY+1
    jsr gouraudSigned8Product
    GCopy24(gProduct, gouraudArea)
    lda gouraudDY
    ldx gouraudDX+1
    jsr gouraudSigned8Product
    GSub24(gouraudArea, gProduct, gouraudArea)
    lda gouraudArea
    ora gouraudArea+1
    ora gouraudArea+2
    bne !area+
    clc
    rts
!area:
    lda gouraudDI
    ldx gouraudDY+1
    jsr gouraudSigned8Product
    GCopy24(gProduct, gouraudPlaneX)
    lda gouraudDI+1
    ldx gouraudDY
    jsr gouraudSigned8Product
    GSub24(gouraudPlaneX, gProduct, gouraudPlaneX)
    lda gouraudDX
    ldx gouraudDI+1
    jsr gouraudSigned8Product
    GCopy24(gProduct, gouraudPlaneY)
    lda gouraudDX+1
    ldx gouraudDI
    jsr gouraudSigned8Product
    GSub24(gouraudPlaneY, gProduct, gouraudPlaneY)
    lda gouraudArea+2
    bpl !oriented+
    GNegate24(gouraudArea)
    GNegate24(gouraudPlaneX)
    GNegate24(gouraudPlaneY)
!oriented:
    lda gouraudInputX
    sta gouraudMinX
    sta gouraudMaxX
    .for (var vertex = 1; vertex < 3; vertex++) {
        lda gouraudInputX+vertex
        cmp gouraudMinX
        bcs !notMin+
        sta gouraudMinX
    !notMin:
        cmp gouraudMaxX
        bcc !notMax+
        sta gouraudMaxX
    !notMax:
    }
    ldx gouraudMinX
!clear:
    lda #128
    sta gouraudTop,x
    lda #0
    sta gouraudBottom,x
    inx
    cpx gouraudMaxX
    bcc !clear-
    lda #0
    sta gouraudEdgeIndex
!edge:
    jsr gouraudGeometryEdge
    inc gouraudEdgeIndex
    lda gouraudEdgeIndex
    cmp #3
    bne !edge-

    // Threshold k uses k*D, k1..8. Area is positive and its products fit24bits.
    lda #0
    sta gProduct
    sta gProduct+1
    sta gProduct+2
    ldx #0
!threshold:
    GAdd24(gProduct, gouraudArea, gProduct)
    lda gProduct
    sta gouraudThresholdLo,x
    lda gProduct+1
    sta gouraudThresholdMid,x
    lda gProduct+2
    sta gouraudThresholdHi,x
    inx
    cpx #8
    bne !threshold-
    ldx gouraudInputI
    dex
    lda gouraudThresholdLo,x
    sta gouraudBaseN
    lda gouraudThresholdMid,x
    sta gouraudBaseN+1
    lda gouraudThresholdHi,x
    sta gouraudBaseN+2
    GCopy24(gouraudPlaneX, gMulValue)
    lda gouraudMinX
    sec
    sbc gouraudInputX
    jsr gouraudMultiply24By8
    GAdd24(gouraudBaseN, gProduct, gouraudBaseN)
    GCopy24(gouraudPlaneY, gMulValue)
    lda #0
    sec
    sbc gouraudInputY
    jsr gouraudMultiply24By8
    GAdd24(gouraudBaseN, gProduct, gouraudBaseN)

    // H increases with q. For B<0, H=-G-1 implements the strict first-outside
    // upper boundary while retaining equality on the illuminated side.
    lda #0
    sta gouraudBSide
    lda gouraudPlaneY
    ora gouraudPlaneY+1
    ora gouraudPlaneY+2
    beq !slopeReady+
    lda #1
    ldx gouraudPlaneY+2
    bpl !slopeSign+
    lda #$ff
!slopeSign:
    sta gouraudBSide
!slopeReady:
    GCopy24(gouraudPlaneY, gStep)
    GCopy24(gouraudPlaneX, gDelta)
    lda gouraudBSide
    bpl !positiveSlope+
    GNegate24(gStep)
    GNegate24(gDelta)
!positiveSlope:
    asl gStep
    rol gStep+1
    rol gStep+2
    .for (var shift = 0; shift < 2; shift++) {
        asl gDelta
        rol gDelta+1
        rol gDelta+2
    }
    // Binary initialization needs only the six positive step powers.
    GCopy24(gStep, gTemporary)
    ldx #0
!power:
    lda gTemporary
    sta gouraudStepPowerLo,x
    lda gTemporary+1
    sta gouraudStepPowerMid,x
    lda gTemporary+2
    sta gouraudStepPowerHi,x
    asl gTemporary
    rol gTemporary+1
    rol gTemporary+2
    inx
    cpx #6
    bne !power-
    lda drawBufferHi
    and #8
    beq !bankA+
    lda #>xorFillKernelsB
    bne !bank+
!bankA:
    lda #>xorFillKernelsA
!bank:
    sta gouraudBankHigh
    sec
    rts

// One real subfield stage, called twice by gouraudTriangle. It deliberately
// leaves the engine's parity/dirty-history metadata and $df unchanged.
@gouraudRenderField:
    lda gouraudParity
    asl
    sta gouraudFieldPage
    asl
    sta gouraudBayerBase
    GCopy24(gouraudBaseN, gouraudInitialN)
    lda gouraudParity
    beq !baseReady+
    GAdd24(gouraudInitialN, gouraudPlaneY, gouraudInitialN)
!baseReady:
    lda gouraudMinX
    sta gouraudInitialX
    lda #4
    sta gouraudInitialCount
!initializeLane:
    lda gouraudInitialX
    and #3
    sta gouraudLane
    ora gouraudBayerBase
    tay
    ldx gouraudBayer,y
    // Affine interpolation stays between the vertex intensities. Whole/dark
    // lanes need neither a light cut nor any later error stepping.
    txa
    clc
    adc #1
    cmp gouraudMinI
    bcc !whole+
    beq !whole+
    cmp gouraudMaxI
    bcc !partial+
    beq !partial+
    lda #0
    beq !simpleLane+
!whole:
    lda #1
!simpleLane:
    ldy gouraudLane
    sta gouraudLaneMode,y
    lda #0
    sta gH
    sta gH+1
    sta gH+2
    sta gQ
    jmp !storeInitial+
!partial:
    lda #2
    ldy gouraudLane
    sta gouraudLaneMode,y
    lda gouraudBSide
    bmi !negativeH+
    sec
    lda gouraudInitialN
    sbc gouraudThresholdLo,x
    sta gH
    lda gouraudInitialN+1
    sbc gouraudThresholdMid,x
    sta gH+1
    lda gouraudInitialN+2
    sbc gouraudThresholdHi,x
    sta gH+2
    jmp !haveH+
!negativeH:
    // Carry clear subtracts the extra one required for strict G<0.
    clc
    lda gouraudThresholdLo,x
    sbc gouraudInitialN
    sta gH
    lda gouraudThresholdMid,x
    sbc gouraudInitialN+1
    sta gH+1
    lda gouraudThresholdHi,x
    sbc gouraudInitialN+2
    sta gH+2
!haveH:
    lda #0
    sta gQ
    lda gouraudBSide
    beq !storeInitial+
    jsr gouraudBinaryCut
!storeInitial:
    jsr gouraudStoreLane
    GAdd24(gouraudInitialN, gouraudPlaneX, gouraudInitialN)
    inc gouraudInitialX
    dec gouraudInitialCount
    beq !columns+
    jmp !initializeLane-

!columns:
    lda gouraudMinX
    sta gouraudColumn
!column:
    ldx gouraudColumn
    lda gouraudTop,x
    jsr gouraudRowToQ
    sta gouraudSpanLow
    ldx gouraudColumn
    lda gouraudBottom,x
    jsr gouraudRowToQ
    sta gouraudSpanHigh
    lda gouraudColumn
    and #3
    sta gouraudLane
    tax
    lda gouraudLaneMode,x
    bne !litLane+
    jmp !nextColumn+
!litLane:
    cmp #1
    bne !partialLane+
    jmp !span+
!partialLane:
    lda gouraudHLo,x
    sta gH
    lda gouraudHMid,x
    sta gH+1
    lda gouraudHHi,x
    sta gH+2
    lda gouraudCutQ,x
    sta gQ
    lda gouraudBSide
    bmi !upperCut+
    beq !horizontalLight+
    lda gQ
    cmp gouraudSpanLow
    bcc !span+
    sta gouraudSpanLow
    jmp !span+
!upperCut:
    lda gQ
    cmp gouraudSpanHigh
    bcs !span+
    sta gouraudSpanHigh
    jmp !span+
!horizontalLight:
    lda gH+2
    bmi !advance+
!span:
    lda gouraudSpanLow
    cmp gouraudSpanHigh
    bcs !advance+
    lda gouraudMaterial
    asl
    asl
    ora gouraudLane
    tax
    lda gouraudPairMasks,x
    sta gMask
    lda gouraudColumn
    and #$3c
    clc
    adc gouraudBankHigh
    sta gColumnPage
    lda gouraudSpanLow
    jsr gouraudMarker
    lda gouraudSpanHigh
    jsr gouraudMarker
!advance:
    ldx gouraudLane
    lda gouraudLaneMode,x
    cmp #2
    beq !partialAdvance+
    jmp !nextColumn+
!partialAdvance:
    GAdd24(gH, gDelta, gH)
    lda gouraudBSide
    beq !save+
    lda gDelta+2
    bmi !raise+
    jsr gouraudLowerCut
    jmp !save+
!raise:
    jsr gouraudRaiseCut
!save:
    jsr gouraudStoreLane
!nextColumn:
    inc gouraudColumn
    lda gouraudColumn
    cmp gouraudMaxX
    bcs !done+
    jmp !column-
!done:
    rts

gouraudRowToQ:
    // ceil((row-p)/2): even fields round up, odd fields round down.
    ldx gouraudParity
    bne !odd+
    clc
    adc #1
!odd:
    lsr
    rts

gouraudStoreLane:
    ldx gouraudLane
    lda gH
    sta gouraudHLo,x
    lda gH+1
    sta gouraudHMid,x
    lda gH+2
    sta gouraudHHi,x
    lda gQ
    sta gouraudCutQ,x
    rts

// Find the first H(q)>=0 in q0..64. Starting from negative H(0), six trials
// find the greatest still-negative q0..63, then one exact step gives its cut.
// All-negative columns naturally finish at64 with their true negative error.
gouraudBinaryCut:
    lda gH+2
    bpl !done+
    ldx #5
!bit:
    clc
    lda gH
    adc gouraudStepPowerLo,x
    sta gTemporary
    lda gH+1
    adc gouraudStepPowerMid,x
    sta gTemporary+1
    lda gH+2
    adc gouraudStepPowerHi,x
    sta gTemporary+2
    bpl !next+
    GCopy24(gTemporary, gH)
    lda gQ
    ora gouraudBinaryBits,x
    sta gQ
!next:
    dex
    bpl !bit-
    inc gQ
    GAdd24(gH, gStep, gH)
!done:
    rts

// At clamps retain the actual signed24-bit error; an offscreen cut can reenter.
gouraudRaiseCut:
    lda gH+2
    bpl !done+
    lda gQ
    cmp #64
    bcs !done+
    GAdd24(gH, gStep, gH)
    inc gQ
    jmp gouraudRaiseCut
!done:
    rts

gouraudLowerCut:
    lda gQ
    beq !done+
    GSub24(gH, gStep, gTemporary)
    lda gTemporary+2
    bmi !done+
    GCopy24(gTemporary, gH)
    dec gQ
    jmp gouraudLowerCut
!done:
    rts

gouraudMarker:
    cmp #64
    beq !terminal+
    tax
    ldy gouraudQLo,x
    lda gouraudQPage,x
    ora gouraudFieldPage
    ora gColumnPage
    sta gPointer+1
    lda #0
    sta gPointer
    lda gMask
    eor (gPointer),y
    sta (gPointer),y
    rts
!terminal:
    lda gMask
    eor interlaceTerminalMarker
    sta interlaceTerminalMarker
    rts

// Exact signed8 product via the already audited unsigned quarter-square helper.
gouraudSigned8Product:
    sta gProduct
    stx gProduct+1
    eor gProduct+1
    sta gSign
    lda gProduct
    bpl !firstPositive+
    eor #$ff
    clc
    adc #1
!firstPositive:
    sta gProduct
    lda gProduct+1
    bpl !secondPositive+
    eor #$ff
    clc
    adc #1
!secondPositive:
    tax
    lda gProduct
    jsr cullUnsignedMultiply
    stx gProduct
    sta gProduct+1
    lda #0
    sta gProduct+2
    bit gSign
    bpl !done+
    GNegate24(gProduct)
!done:
    rts

// gMulValue (signed24) times A (signed8); result gProduct, no truncation.
gouraudMultiply24By8:
    cmp #0
    bpl !positive+
    eor #$ff
    clc
    adc #1
    pha
    GNegate24(gMulValue)
    pla
!positive:
    sta gMulFactor
    lda #0
    sta gProduct
    sta gProduct+1
    sta gProduct+2
!multiply:
    lda gMulFactor
    beq !done+
    lsr gMulFactor
    bcc !noAdd+
    GAdd24(gProduct, gMulValue, gProduct)
!noAdd:
    asl gMulValue
    rol gMulValue+1
    rol gMulValue+2
    jmp !multiply-
!done:
    rts

// Build exact ceil-Y intersections for one half-open edge. Temporary edge
// workspace d0..d7 is dead before the plane/error state is installed.
gouraudGeometryEdge:
    ldx gouraudEdgeIndex
    lda gouraudInputX,x
    sta gProduct
    lda gouraudInputY,x
    sta gProduct+1
    inx
    cpx #3
    bne !nextVertex+
    ldx #0
!nextVertex:
    lda gouraudInputX,x
    sta gMulFactor
    lda gouraudInputY,x
    sta gouraudEdgeY1
    lda gProduct
    cmp gMulFactor
    bne !nonvertical+
    rts
!nonvertical:
    bcc !ordered+
    ldx gMulFactor
    stx gProduct
    sta gMulFactor
    lda gProduct+1
    ldx gouraudEdgeY1
    stx gProduct+1
    sta gouraudEdgeY1
!ordered:
    lda gMulFactor
    sec
    sbc gProduct
    sta gProduct+2
    lda gouraudEdgeY1
    sec
    sbc gProduct+1
    ldx #0
    bcs !direction+
    eor #$ff
    clc
    adc #1
    dex
!direction:
    stx gouraudEdgeDirection
    ldx #0
!divide:
    cmp gProduct+2
    bcc !divided+
    sec
    sbc gProduct+2
    inx
    jmp !divide-
!divided:
    sta gMulValue+1
    stx gMulValue
    lda gouraudEdgeDirection
    beq !positive+
    lda gMulValue+1
    beq !negativeInteger+
    lda gProduct+2
    sec
    sbc gMulValue+1
    sta gMulValue+1
    lda gMulValue
    eor #$ff
    sta gMulValue
    jmp !stepReady+
!negativeInteger:
    lda #0
    sec
    sbc gMulValue
    sta gMulValue
    jmp !stepReady+
!positive:
!stepReady:
    lda #$ff
    sta gMulValue+2
!sample:
    ldx gProduct
    lda gProduct+1
    cmp gouraudTop,x
    bcs !notTop+
    sta gouraudTop,x
!notTop:
    cmp gouraudBottom,x
    bcc !notBottom+
    sta gouraudBottom,x
!notBottom:
    lda gMulValue+2
    clc
    adc gMulValue+1
    bcc !fraction+
    sbc gProduct+2
    inc gProduct+1
!fraction:
    sta gMulValue+2
    lda gProduct+1
    adc gMulValue
    sta gProduct+1
    inc gProduct
    lda gProduct
    cmp gMulFactor
    bcs !done+
    jmp !sample-
!done:
    rts
@gouraudCodeEnd:

@gouraudTablesStart:
gouraudBayer: .byte 0,4,1,5, 6,2,7,3
gouraudBinaryBits: .byte 1,2,4,8,16,32
gouraudPairMasks:
    .byte 0,0,0,0, $40,$10,$04,$01, $80,$20,$08,$02, $c0,$30,$0c,$03
gouraudQLo: .fill 64, (i & 31)*8+1
gouraudQPage: .fill 64, floor(i/32)
@gouraudTablesEnd:

@gouraudStateStart:
@gouraudVertexI: .fill 12, 0
@gouraudInputX: .fill 3, 0
@gouraudInputY: .fill 3, 0
@gouraudInputI: .fill 3, 1
@gouraudMaterial: .byte 0
gouraudFaceIndex: .byte 0
@gouraudParity: .byte 0
gouraudMinI: .byte 0
gouraudMaxI: .byte 0
gouraudDX: .fill 2, 0
gouraudDY: .fill 2, 0
gouraudDI: .fill 2, 0
gouraudArea: .fill 3, 0
gouraudPlaneX: .fill 3, 0
gouraudPlaneY: .fill 3, 0
gouraudBaseN: .fill 3, 0
gouraudInitialN: .fill 3, 0
gouraudMinX: .byte 0
gouraudMaxX: .byte 0
gouraudEdgeIndex: .byte 0
gouraudEdgeY1: .byte 0
gouraudEdgeDirection: .byte 0
gouraudBSide: .byte 0
gouraudFieldPage: .byte 0
gouraudBayerBase: .byte 0
gouraudBankHigh: .byte 0
gouraudInitialX: .byte 0
gouraudInitialCount: .byte 0
gouraudColumn: .byte 0
gouraudLane: .byte 0
gouraudSpanLow: .byte 0
gouraudSpanHigh: .byte 0
gouraudThresholdLo: .fill 8, 0
gouraudThresholdMid: .fill 8, 0
gouraudThresholdHi: .fill 8, 0
gouraudStepPowerLo: .fill 6, 0
gouraudStepPowerMid: .fill 6, 0
gouraudStepPowerHi: .fill 6, 0
gouraudLaneMode: .fill 4, 0
gouraudHLo: .fill 4, 0
gouraudHMid: .fill 4, 0
gouraudHHi: .fill 4, 0
gouraudCutQ: .fill 4, 0
gouraudTop: .fill 64, 128
gouraudBottom: .fill 64, 0
@gouraudStateEnd:
}
