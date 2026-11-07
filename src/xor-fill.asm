.importonce

// Multicolor polygons use four logical pixels per byte. An edge contributes
// color-transition markers, not a Bresenham outline. Sort its endpoints by X,
// ignore vertical edges, and sample integer x in [leftX,rightX). The marker row
// is ceil(leftY + (x-leftX)*dy/dx). This half-open rule counts a shared corner
// consistently and lets coincident markers cancel without a repair pass.
//
// xorFill starts each byte column at zero, XORs each marker into the running
// color, and writes that color back. Thus polygon coverage is lowerY <= y < upperY.
// Two adjacent visible faces contribute the XOR of their two color codes.
// Markers occupy immediate operands in the fill code. Each filled byte also
// resets its operand, so an old/current rectangle union erases stale pixels
// without a separate charset clear.
//
// Public APIs: drawCubeBoundaries, drawBoundary, xorFill. drawBoundary consumes
// lineX0/Y0/X1/Y1 and boundaryColor (1..3), and may reorder its endpoint variables.
// DITHERED uses a full packed transition byte instead of one repeated selector.
// All routines clobber A/X/Y and flags. This module owns $d0..$df; FAST_SOLID
// also keeps its per-frame buffer cache at $e6..$e8 across edge calls.
// FAST_SOLID edge calls use prepareFilledFrame's buffer cache and the zero
// pointer low byte established once by drawCubeBoundaries (or by a caller).
.label xorPointer = $d0
.label xorFillBankHi = $d2
.label xorMarkerBase = $d3
.label xorRemainder = $d4
.label xorRemainderStep = $d5
.label xorRowStep = $d6
.label xorDirection = $d7
.label xorColumnCount = $d8
.label xorRestoreOpcode = $d9
.label xorBoundaryEnd = $d8
.label xorLaneMasks = $da
#if FAST_SOLID
.label fastBoundaryStateStart = $e6
.label xorBoundaryTable = $e6
.label fastBoundaryBankHi = $e8
.label fastBoundaryStateEnd = $e9
#else
.label xorBoundaryTable = $dc
#endif
.label xorBufferIndex = $de
#if INTERLACED
.label interlaceRowIndexBit = $df
// RAM under disabled KERNAL. A terminal crossing has no selected output row.
// This byte is initialized at startup and reset after every prefix fill.
.label interlaceTerminalMarker = $ff01
#endif

xorBoundaryCodeStart:

// Capture the old rectangle before projectCube replaces this buffer's bounds.
// A never-used charset is empty; min/max sentinels leave the current bounds intact.
prepareFilledFrame:
    ldx #0
    lda drawBufferHi
    and #$08
    beq !buffer+
    inx
!buffer:
#if FAST_SOLID
    // X already identifies this physical back buffer. These pointers survive
    // projection/culling and every edge, including the four lane-mask stores.
    lda xorBoundaryTableLo,x
    sta xorBoundaryTable
    lda xorBoundaryTableHi,x
    sta xorBoundaryTable+1
    lda xorFillBankHigh,x
    sta fastBoundaryBankHi
#endif
#if INTERLACED
    lda interlaceNextParity,x
    sta interlaceFieldParity
    eor #1
    sta interlaceNextParity,x
    lda interlaceFieldParity
    lsr
    lda #0
    ror
    sta interlaceRowIndexBit
    txa
    asl
    ora interlaceFieldParity
    tax
    stx interlaceDirtyIndex
#endif
    lda filledBufferUsed,x
    bne !used+
    lda #1
    sta filledBufferUsed,x
    lda #15
    sta filledOldMinColumn
    lda #127
    sta filledOldMinRow
    lda #0
    sta filledOldMaxColumn
    sta filledOldMaxRow
    rts
!used:
    lda dirtyMinColumn,x
    sta filledOldMinColumn
    lda dirtyMaxColumn,x
    sta filledOldMaxColumn
    lda dirtyMinRow,x
    sta filledOldMinRow
    lda dirtyMaxRow,x
    sta filledOldMaxRow
    rts

#if GOURAUD
    GouraudRendererCode()
#else
.macro XorCubeEdge(first, last) {
    .var firstFace = -1
    .var lastFace = -1
    .for (var axis = 0; axis < 3; axis++) {
        .if (((first ^ last) & (1 << axis)) == 0) {
            .var face = axis * 2 + ((first >> axis) & 1)
            .if (firstFace < 0) { .eval firstFace = face } else { .eval lastFace = face }
        }
    }
    lda xorFaceColors+firstFace
    eor xorFaceColors+lastFace
    beq !hidden+
    sta boundaryColor
    lda projectedX+first
    sta lineX0
    lda projectedY+first
    sta lineY0
    lda projectedX+last
    sta lineX1
    lda projectedY+last
    sta lineY1
    jsr drawBoundary
!hidden:
}

#if INTERLACED || FAST_SOLID
// Compile each mesh edge into constant face/vertex addresses. Its caller keeps
// the original descending edge order; drawBoundary still owns exact crossings.
.macro XorIcosahedronEdge(first, last, firstFace, lastFace) {
    lda xorFaceColors+firstFace
    eor xorFaceColors+lastFace
    beq !hidden+
    sta boundaryColor
    lda projectedX+first
    sta lineX0
    lda projectedY+first
    sta lineY0
    lda projectedX+last
    sta lineX1
    lda projectedY+last
    sta lineY1
    jsr drawBoundary
!hidden:
}
#endif

drawCubeBoundaries:
#if FAST_SOLID
    lda #0
    sta xorPointer
#endif
#if ICOSAHEDRON
    // A hidden face contributes zero; adjacent face colors toggle at their edge.
#if FAST_SOLID
    // Paired culling produces literal0/1 flags. Compile each fixed material
    // directly, avoiding indexed topology reads and the runtime face loop.
    .for (var face = 0; face < ICOSA_FACE_COUNT; face++) {
        .var color = icosaFaceColors.get(face)
        .errorif color < 1 || color > 3, "FAST_SOLID requires selectors1..3"
        lda visibleFaces+face
        .if (color == 2) {
            asl
        }
        .if (color == 3) {
            beq !colorReady+
            lda #3
        !colorReady:
        }
        sta xorFaceColors+face
    }
#else
    ldy #ICOSA_FACE_COUNT-1
!face:
    lda visibleFaces,y
    beq !hidden+
#if DITHERED
    // Select the screen-anchored row pattern for this actual field, rather
    // than presentation parity: each physical buffer keeps its own phase.
    ldx modelFaceColor,y
    lda interlaceFieldParity
    beq !evenPattern+
    lda ditherPatternOdd,x
    jmp !hidden+
!evenPattern:
    lda ditherPatternEven,x
#else
    lda modelFaceColor,y
#endif
!hidden:
    sta xorFaceColors,y
    dey
    bpl !face-
#endif

#if INTERLACED || FAST_SOLID
    jmp xorEdgeDispatchStart
#else
    ldy #ICOSA_EDGE_COUNT-1
!edge:
    sty objectEdgeIndex
    ldx modelEdgeFaceA,y
    lda xorFaceColors,x
    sta boundaryColor
    ldx modelEdgeFaceB,y
    lda xorFaceColors,x
    eor boundaryColor
    beq !skip+
    sta boundaryColor
    ldx modelEdgeA,y
    lda projectedX,x
    sta lineX0
    lda projectedY,x
    sta lineY0
    ldx modelEdgeB,y
    lda projectedX,x
    sta lineX1
    lda projectedY,x
    sta lineY1
    jsr drawBoundary
!skip:
    ldy objectEdgeIndex
    dey
    bpl !edge-
    rts
#endif
#else
    // Opposite faces share a color: X=1, Y=2, Z=3. A hidden face contributes zero.
    .for (var face = 0; face < 6; face++) {
        lda visibleFaces
        and #(1 << face)
        beq !hidden+
        lda #floor(face / 2) + 1
    !hidden:
        sta xorFaceColors+face
    }
    .for (var vertex = 0; vertex < 8; vertex++) {
        .for (var axis = 0; axis < 3; axis++) {
            .if ((vertex & (1 << axis)) == 0) {
                XorCubeEdge(vertex, vertex ^ (1 << axis))
            }
        }
    }
    rts
#endif

drawBoundary:
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
    lda lineX1
    sec
    sbc lineX0
    sta lineDX
    cmp #1
    bne !multipleSamples+
    // A half-open edge one column wide contributes only its left endpoint.
    // No slope, remainder, or vertical stepping is needed for that one marker.
    jmp xorBoundarySingle
!multipleSamples:
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
    stx xorDirection

    // Divide abs(dy) by dx. The quotient is normally small; this short exact
    // subtraction loop also handles steep boundaries without a slope table.
    // Small quotients fall through unrolled subtraction attempts. Only steep
    // power-of-two cases pay for dispatch to exact shift-and-mask division.
    tay
    ldx #0
    sec
    .for (var attempt = 0; attempt < 9; attempt++) {
        sbc lineDX
        bcc !divided+
        inx
    }

    ldx lineDX
    cpx #2
    beq !divideByTwo+
    cpx #4
    beq !divideByFour+
    cpx #8
    beq !divideByEight+
    ldx #9
    // The comparisons above change carry; restore the SBC no-borrow invariant.
    sec
    jmp !divide+

!divideByTwo:
    tya
    lsr
    tax
    tya
    and #1
    sta xorRemainderStep
    txa
    jmp !quotientReady+
!divideByFour:
    tya
    lsr
    lsr
    tax
    tya
    and #3
    sta xorRemainderStep
    txa
    jmp !quotientReady+
!divideByEight:
    tya
    lsr
    lsr
    lsr
    tax
    tya
    and #7
    sta xorRemainderStep
    txa
    jmp !quotientReady+

!divide:
    sbc lineDX
    bcc !divided+
    inx
    bcs !divide-
!divided:
    adc lineDX
    sta xorRemainderStep
    txa
!quotientReady:
    ldx xorDirection
    beq !positiveStep+
    eor #$ff
    clc
    adc #1
    sta xorRowStep
    lda xorRemainderStep
    beq !stepReady+
    // Use floor(dy/dx) and a nonnegative remainder for either direction.
    // A negative fractional slope needs one lower integer step, then INY
    // corrections, so both directions can use the same generated code.
    dec xorRowStep
    lda lineDX
    sec
    sbc xorRemainderStep
    sta xorRemainderStep
    jmp !stepReady+
!positiveStep:
    sta xorRowStep
!stepReady:
    // Bias the ceiling accumulator by -dx: (dx-1)-dx is always -1.
    // Overflow from adding the fractional step now replaces CMP dx.
    lda #$ff
    sta xorRemainder

    // Select one fixed-X chain for this physical charset. FAST_SOLID has cached
    // its table outside lane-mask workspace; other modes select it per edge.
#if !FAST_SOLID
    ldx #0
    lda drawBufferHi
    and #$08
    beq !buffer+
    inx
!buffer:
    lda xorBoundaryTableLo,x
    sta xorBoundaryTable
    lda xorBoundaryTableHi,x
    sta xorBoundaryTable+1
#endif
    ldy lineX0
    lda (xorBoundaryTable),y
    sta xorBoundaryDispatch+1
    tya
    ora #64
    tay
    lda (xorBoundaryTable),y
    sta xorBoundaryDispatch+2
    ldy lineX1
    lda (xorBoundaryTable),y
#if FAST_SOLID
    // table[rightX]-16 is the step following the last included marker.
    // Keep this subtraction's carry through the high-byte table lookup.
    sec
    sbc #16
#endif
    sta xorBoundaryEnd
    tya
    ora #64
    tay
    lda (xorBoundaryTable),y
#if FAST_SOLID
    sbc #0
#endif
    sta xorBoundaryEnd+1

#if FAST_SOLID
    // Return after the final marker, before its unused DDA advance. That site
    // is LDA xorRemainder (A5), rather than the next block's LDY (BC).
#else
    // The right endpoint is excluded. Every valid endpoint block starts with
    // LDY rowLo,X; temporarily return there, then restore its original opcode.
#endif
    ldy #0
    lda #$60
    sta (xorBoundaryEnd),y
#if DITHERED
    // A packed face transition may contain a different selector in every
    // logical-X lane. Isolate each pair so neighboring lanes cannot toggle.
    lda boundaryColor
    and #$c0
    sta xorLaneMasks
    lda boundaryColor
    and #$30
    sta xorLaneMasks+1
    lda boundaryColor
    and #$0c
    sta xorLaneMasks+2
    lda boundaryColor
    and #$03
    sta xorLaneMasks+3
#else
    lda boundaryColor
    sta xorLaneMasks+3
    asl
    asl
    sta xorLaneMasks+2
    asl
    asl
    sta xorLaneMasks+1
    asl
    asl
    sta xorLaneMasks
#endif
#if !FAST_SOLID
    lda #0
    sta xorPointer
#endif
#if INTERLACED
    lda lineY0
    ora interlaceRowIndexBit
    tax
#else
    ldx lineY0
#endif
xorBoundaryDispatch:
    jsr $ffff
    ldy #0
#if FAST_SOLID
    lda #$a5
#else
    lda #$bc
#endif
    sta (xorBoundaryEnd),y
    rts

// Select the first packed byte and color pair. The caller receives the pair
// mask in A; no slope state is read or changed by this address calculation.
.macro XorBoundaryTarget() {
#if FAST_SOLID
    lda fastBoundaryBankHi
#else
    lda drawBufferHi
    and #$08
    lsr
    lsr
    lsr
    tax
    lda xorFillBankHigh,x
#endif
    sta xorPointer+1
    lda lineX0
    and #$3c
    clc
    adc xorPointer+1
    sta xorPointer+1
    lda #0
    sta xorPointer
#if INTERLACED
    lda lineY0
    ora interlaceRowIndexBit
    tax
#else
    ldx lineY0
#endif
    ldy xorOperandLo,x
    lda xorOperandPage,x
    ora xorPointer+1
    sta xorPointer+1
#if DITHERED
    lda lineX0
    and #3
    tax
    lda ditherPairMasks,x
    and boundaryColor
#else
    lda boundaryColor
    asl
    asl
    sta xorMarkerBase
    lda lineX0
    and #3
    ora xorMarkerBase
    tax
    lda xorPairMasks,x
#endif
}

xorBoundarySingle:
    XorBoundaryTarget()
    eor (xorPointer),y
    sta (xorPointer),y
    rts

xorBoundaryCodeEnd:

// Each X owns one 32-byte block. Color lanes and column pages are constants;
// execution falls directly into the next X without shifting or pointer work.
.const XOR_BOUNDARY_BLOCK_SIZE = 32
.macro XorBoundaryKernel(bank) {
    .for (var pixelX = 0; pixelX < 64; pixelX++) {
    blockStart:
        ldy xorOperandLo,x
        lda xorOperandPage,x
        ora #((>bank) + floor(pixelX / 4) * 4)
        sta xorPointer+1
        lda xorLaneMasks + (pixelX & 3)
        eor (xorPointer),y
        sta (xorPointer),y

#if FAST_SOLID
        .assert "FAST boundary step offset", *-blockStart, 16
#endif
        // The signed quotient moves directly to the next intersection row. Only
        // the residual fraction can add one further row; intermediate rows are not marked.
        lda xorRemainder
        clc
        adc xorRemainderStep
        bcc !fractionReady+
        sbc lineDX
        inx
    !fractionReady:
        sta xorRemainder
        // No overflow leaves carry clear. After overflow, SBC dx borrows,
        // also clearing carry, so the signed row addition needs no CLC.
        txa
        adc xorRowStep
        tax
    }
    rts
}

xorBoundaryKernelsStart:
xorBoundaryA: XorBoundaryKernel(xorFillKernelsA)
xorBoundaryB: XorBoundaryKernel(xorFillKernelsB)
xorBoundaryKernelsEnd:
    .assert "XOR boundary kernel sizes", xorBoundaryKernelsEnd-xorBoundaryKernelsStart, 2*(64*XOR_BOUNDARY_BLOCK_SIZE+1)

.macro XorBoundaryTable(kernel) {
    .fill 64, <(kernel + i*XOR_BOUNDARY_BLOCK_SIZE)
    .fill 64, >(kernel + i*XOR_BOUNDARY_BLOCK_SIZE)
}

// Each 128-byte table fits in a page, including its high-byte half.
.align $80
xorBoundaryTablesStart:
xorBoundaryTableA: XorBoundaryTable(xorBoundaryA)
xorBoundaryTableB: XorBoundaryTable(xorBoundaryB)
xorBoundaryTableLo:
    .byte <xorBoundaryTableA, <xorBoundaryTableB
xorBoundaryTableHi:
    .byte >xorBoundaryTableA, >xorBoundaryTableB
xorBoundaryTablesEnd:

#if DITHERED
// Full packed patterns: four logical-X pairs per byte, selected by physical
// row parity. Material zero is the hidden/outside contribution.
ditherPairMasks:
    .byte $c0,$30,$0c,$03
ditherPatternEven:
    .byte $00,$66,$bb,$dd
ditherPatternOdd:
    .byte $00,$99,$ee,$77
    // Retain the solid pair table's 16-byte allocation before the fill code.
    .fill 4, 0
#else
// Each logical X lane occupies one two-bit pair. Index by color*4 + (x&3).
xorPairMasks:
    .byte $00,$00,$00,$00, $40,$10,$04,$01
    .byte $80,$20,$08,$02, $c0,$30,$0c,$03
#endif
#endif

xorFillCodeStart:
xorFill:
    ldx #0
    lda drawBufferHi
    and #$08
    beq !buffer+
    inx
!buffer:
    stx xorBufferIndex
#if INTERLACED
    ldx interlaceDirtyIndex
#endif

    // Visit the union to erase the old image while writing the new one.
    // Keep the real dirty arrays as the current image's bounds for its next reuse.
    lda dirtyMinColumn,x
    cmp filledOldMinColumn
    bcc !minColumn+
    lda filledOldMinColumn
!minColumn:
    sta filledMinColumn
    lda dirtyMaxColumn,x
    cmp filledOldMaxColumn
    bcs !maxColumn+
    lda filledOldMaxColumn
!maxColumn:
    sta filledMaxColumn
    lda dirtyMinRow,x
    cmp filledOldMinRow
    bcc !minRow+
    lda filledOldMinRow
!minRow:
    sta filledMinRow
    lda dirtyMaxRow,x
    cmp filledOldMaxRow
    bcs !maxRow+
    lda filledOldMaxRow
!maxRow:
    sta filledMaxRow

#if INTERLACED
    // Consume through the closing marker, even when its physical row lies one
    // row beyond the raw geometry bounds. Leaving it would poison a later field.
    lda filledMinRow
    clc
    adc #1
    sec
    sbc interlaceFieldParity
    lsr
    sta interlaceMinQ
    cmp #64
    bcc !nonempty+
    lda #63
    sta interlaceMaxQ
    jmp !done+
!nonempty:
    lda filledMaxRow
    clc
    adc #1
    sec
    sbc interlaceFieldParity
    lsr
    cmp #64
    bcc !lastRow+
    lda #63
!lastRow:
    sta interlaceMaxQ
    ldx xorBufferIndex
#endif

    lda filledMaxColumn
    sec
    sbc filledMinColumn
    clc
    adc #1
    sta xorColumnCount
    lda filledMinColumn
    asl
    asl
    clc
    adc xorFillBankHigh,x
    sta xorFillBankHi

#if INTERLACED
    lda interlaceMinQ
    asl
    ora interlaceRowIndexBit
    tay
#else
    ldy filledMinRow
#endif
    lda xorOperandLo,y
    and #$f8
    sta xorFillEntry+1
#if FAST_SOLID
    sta fastFillEntry+1
#endif
    lda xorOperandPage,y
    clc
    adc xorFillBankHi
    sta xorFillEntry+2
#if FAST_SOLID
    sta fastFillEntry+2
#endif

    // OperandLo is 8*y+1. Adding seven reaches the row after maxY, including
    // its carry into the next page or column when maxY is 31, 63, 95, or 127.
#if INTERLACED
    lda interlaceMaxQ
    asl
    ora interlaceRowIndexBit
    tay
#else
    ldy filledMaxRow
#endif
    lda xorOperandLo,y
    clc
    adc #7
    sta xorPointer
    lda xorOperandPage,y
    adc xorFillBankHi
    sta xorPointer+1

    // The row after the rectangle normally starts with EOR. At row 128 it is
    // the next column's EOR, or the B bank's native RTS. Save each actual opcode.
    // X stays zero throughout the generated code so STX resets every operand.
    ldx #0
#if FAST_SOLID
    // Below row127 the stop always replaces an EOR opcode within this column.
    // Both generated fill cells and the IRQ preserve Y, so one zero load serves
    // the complete loop. Keep the original path for the row128/native-RTS case.
    lda filledMaxRow
    cmp #127
    bcs !column+
    ldy #0
!fastColumn:
    lda #$60
    sta (xorPointer),y
    lda #0
fastFillEntry:
    jsr $ffff
    lda #$49
    sta (xorPointer),y
    dec xorColumnCount
    beq !fastDone+
    lda fastFillEntry+2
    clc
    adc #4
    sta fastFillEntry+2
    lda xorPointer+1
    clc
    adc #4
    sta xorPointer+1
    jmp !fastColumn-
!fastDone:
    rts
#endif
!column:
    ldy #0
    lda (xorPointer),y
    sta xorRestoreOpcode
    lda #$60
    sta (xorPointer),y
    lda #0
xorFillEntry:
    jsr $ffff
    ldy #0
    lda xorRestoreOpcode
    sta (xorPointer),y
    dec xorColumnCount
    beq !done+

    // Every column has 128 eight-byte EOR/STA/STX cells and no trailing RTS.
    // Its $400-byte stride preserves the row offsets in both pointers.
    lda xorFillEntry+2
    clc
    adc #4
    sta xorFillEntry+2
    lda xorPointer+1
    clc
    adc #4
    sta xorPointer+1
    jmp !column-
!done:
#if INTERLACED
#if GOURAUD
    // Both marker subfields belong to one pose. Retain their aggregate discard
    // byte after the first prefix pass; the second pass completes cleanup.
    lda interlaceFieldParity
    beq !terminalRetained+
#endif
    lda #0
    sta interlaceTerminalMarker
#if GOURAUD
!terminalRetained:
#endif
#endif
    rts
xorFillCodeEnd:

// Align the marker lookup tables so every row lookup stays in one page.
#if INTERLACED
.align $100
#else
.align $80
#endif
xorFillTablesStart:
xorOperandLo:
#if INTERLACED
    .fill 256, ((floor(((i & 127)+1-floor(i/128))/2) & 31)*8)+1
#else
    .fill 128, ((i & 31) * 8) + 1
xorOperandPage:
    .fill 128, floor(i / 32)
#endif
xorFillBankHigh:
    .byte >xorFillKernelsA, >xorFillKernelsB
xorFillTablesEnd:

fillStateStart:
boundaryColor: .byte 0
#if ICOSAHEDRON
xorFaceColors: .fill ICOSA_FACE_COUNT, 0
#else
xorFaceColors: .fill 6, 0
#endif
#if INTERLACED
filledBufferUsed: .fill 4, 0
interlaceFieldParity: .byte 0
interlaceNextParity: .byte 0, 0
interlaceDirtyIndex: .byte 0
interlaceMinQ: .byte 0
interlaceMaxQ: .byte 0
#else
filledBufferUsed: .byte 0, 0
#endif
filledOldMinColumn: .byte 15
filledOldMaxColumn: .byte 0
filledOldMinRow: .byte 127
filledOldMaxRow: .byte 0
filledMinColumn: .byte 0
filledMaxColumn: .byte 0
filledMinRow: .byte 0
filledMaxRow: .byte 0
#if INTERLACED || FAST_SOLID
visibleFaces: .fill ICOSA_FACE_COUNT, 0
#endif
#if FAST_SOLID
fastFaceDepth: .fill ICOSA_FACE_COUNT, 0
#endif
fillStateEnd:

#if INTERLACED || FAST_SOLID
    IcosahedronDepthCull()
#endif

#if TONAL
    TonalShadeHighCode()
#endif

#if ICOSAHEDRON
// Enlarge projected offsets without increasing the reciprocal-depth factor.
// Signed nearest rounding uses floor(value+0.5), including negative half ties.
.align $100
icosahedronZoom:
    .fill 256, floor((29*(i < 128 ? i : i-256)+10)/20) & $ff
icosahedronZoomEnd:
    .assert "Icosahedron zoom alignment", icosahedronZoom & $ff, 0
    .assert "Icosahedron zoom table size", icosahedronZoomEnd-icosahedronZoom, 256
#endif

// Each cell reads its transition marker, writes one packed charset byte, and
// resets the consumed marker without changing A. X must be zero on entry.
.macro XorFillColumns(buffer) {
    .for (var column = 0; column < 16; column++) {
#if INTERLACED
        // Each half-column contains one field; literal stores skip other rows.
        .for (var parity = 0; parity < 2; parity++) {
            .for (var row = 0; row < 64; row++) {
            cell:
                eor #0
                sta buffer + column * 128 + row*2 + parity
                stx cell+1
            }
        }
#else
        .for (var row = 0; row < 128; row++) {
        cell:
            eor #0
            sta buffer + column * 128 + row
            stx cell+1
        }
#endif
    }
}

#if GOURAUD || FAST_SOLID
    .errorif * > $4c00, "Filled renderer exceeds its reserved prelude"
    .fill $4c00-*, 0
#endif
.align $400
xorFillKernelsStart:
xorFillKernelsA:
    .errorif xorFillKernelsA > $4c00, "Immediate fill banks would reach mapped I/O"
    .assert "Immediate fill A alignment", xorFillKernelsA & $3ff, 0
    XorFillColumns(CHARSET_A)
xorFillKernelsB:
    .assert "Immediate fill A kernel size", xorFillKernelsB-xorFillKernelsA, $4000
    .assert "Immediate fill B alignment", xorFillKernelsB & $3ff, 0
    XorFillColumns(CHARSET_B)
xorFillNativeReturn:
    rts
xorFillKernelsEnd:
    .assert "Immediate fill B kernel size", xorFillNativeReturn-xorFillKernelsB, $4000
    .errorif xorFillKernelsEnd > $d000, "Immediate fill banks overlap mapped I/O"

#if INTERLACED || FAST_SOLID
#if !GOURAUD
// The 30 fixed-address calls occupy the last 1 KB below mapped I/O. Leave the
// native fill return at $cc00 intact, including its temporary endpoint patch.
xorEdgeDispatchStart:
    .for (var edge = ICOSA_EDGE_COUNT-1; edge >= 0; edge--) {
        XorIcosahedronEdge(icosaEdges.get(edge).get(0), icosaEdges.get(edge).get(1), icosaEdges.get(edge).get(2), icosaEdges.get(edge).get(3))
    }
    rts
xorEdgeDispatchEnd:
    .assert "Unrolled edge dispatch start", xorEdgeDispatchStart, $cc01
    .assert "Unrolled edge dispatch size", xorEdgeDispatchEnd-xorEdgeDispatchStart, 30*34+1
    .errorif xorEdgeDispatchEnd > $d000, "Unrolled edge dispatch overlaps mapped I/O"
#endif
#endif

// Persistent SMC: xorBoundaryDispatch+1..+2 and xorFillEntry+1..+2. FAST_SOLID
// additionally owns fastFillEntry+1..+2 for its known-EOR-stop column loop.
// During drawBoundary only, the first byte at the excluded endpoint's block
// is temporarily RTS and restored to LDY absolute,X before returning. FAST_SOLID
// instead patches table[rightX]-16 and restores its LDA zero-page opcode A5,
// preserving the final marker while skipping the unused final DDA advance.
// During xorFill only, one byte at columnKernel + 8*(filledMaxRow+1) is
// temporarily RTS and restored before returning. Marker operands at cell+1
// change while building the boundaries, then every visited cell resets itself.
// The generated opcodes, destination addresses, and row tables stay immutable.
