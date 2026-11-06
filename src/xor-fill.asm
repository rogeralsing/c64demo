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
// All routines clobber A/X/Y and flags. This module exclusively owns $d0..$df.
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
.label xorBoundaryTable = $dc
.label xorBufferIndex = $de

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

drawCubeBoundaries:
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

    // Select one fixed-X chain for this physical charset. Color masks are
    // loaded after the table lookup because their lanes reuse its workspace.
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
    sta xorBoundaryEnd
    tya
    ora #64
    tay
    lda (xorBoundaryTable),y
    sta xorBoundaryEnd+1

    // The right endpoint is excluded. Every valid endpoint block starts with
    // LDY rowLo,X; temporarily return there, then restore its original opcode.
    ldy #0
    lda #$60
    sta (xorBoundaryEnd),y
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
    lda #0
    sta xorPointer
    ldx lineY0
xorBoundaryDispatch:
    jsr $ffff
    ldy #0
    lda #$bc
    sta (xorBoundaryEnd),y
    rts

// Select the first packed byte and color pair. The caller receives the pair
// mask in A; no slope state is read or changed by this address calculation.
.macro XorBoundaryTarget() {
    lda drawBufferHi
    and #$08
    lsr
    lsr
    lsr
    tax
    lda xorFillBankHigh,x
    sta xorPointer+1
    lda lineX0
    and #$3c
    clc
    adc xorPointer+1
    sta xorPointer+1
    lda #0
    sta xorPointer
    ldx lineY0
    ldy xorOperandLo,x
    lda xorOperandPage,x
    ora xorPointer+1
    sta xorPointer+1
    lda boundaryColor
    asl
    asl
    sta xorMarkerBase
    lda lineX0
    and #3
    ora xorMarkerBase
    tax
    lda xorPairMasks,x
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
        ldy xorOperandLo,x
        lda xorOperandPage,x
        ora #((>bank) + floor(pixelX / 4) * 4)
        sta xorPointer+1
        lda xorLaneMasks + (pixelX & 3)
        eor (xorPointer),y
        sta (xorPointer),y

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

// Each logical X lane occupies one two-bit pair. Index by color*4 + (x&3).
xorPairMasks:
    .byte $00,$00,$00,$00, $40,$10,$04,$01
    .byte $80,$20,$08,$02, $c0,$30,$0c,$03

xorFillCodeStart:
xorFill:
    ldx #0
    lda drawBufferHi
    and #$08
    beq !buffer+
    inx
!buffer:
    stx xorBufferIndex

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

    ldy filledMinRow
    lda xorOperandLo,y
    and #$f8
    sta xorFillEntry+1
    lda xorOperandPage,y
    clc
    adc xorFillBankHi
    sta xorFillEntry+2

    // OperandLo is 8*y+1. Adding seven reaches the row after maxY, including
    // its carry into the next page or column when maxY is 31, 63, 95, or 127.
    ldy filledMaxRow
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
    rts
xorFillCodeEnd:

// Align the marker lookup tables so every row lookup stays in one page.
.align $80
xorFillTablesStart:
xorOperandLo:
    .fill 128, ((i & 31) * 8) + 1
xorOperandPage:
    .fill 128, floor(i / 32)
xorFillBankHigh:
    .byte >xorFillKernelsA, >xorFillKernelsB
xorFillTablesEnd:

fillStateStart:
boundaryColor: .byte 0
xorFaceColors: .fill 6, 0
filledBufferUsed: .byte 0, 0
filledOldMinColumn: .byte 15
filledOldMaxColumn: .byte 0
filledOldMinRow: .byte 127
filledOldMaxRow: .byte 0
filledMinColumn: .byte 0
filledMaxColumn: .byte 0
filledMinRow: .byte 0
filledMaxRow: .byte 0
fillStateEnd:

// Each cell reads its transition marker, writes one packed charset byte, and
// resets the consumed marker without changing A. X must be zero on entry.
.macro XorFillColumns(buffer) {
    .for (var column = 0; column < 16; column++) {
        .for (var row = 0; row < 128; row++) {
        cell:
            eor #0
            sta buffer + column * 128 + row
            stx cell+1
        }
    }
}

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

// Persistent SMC: xorBoundaryDispatch+1..+2 and xorFillEntry+1..+2.
// During drawBoundary only, the first byte at the excluded endpoint's block
// is temporarily RTS and restored to LDY absolute,X before returning.
// During xorFill only, one byte at columnKernel + 8*(filledMaxRow+1) is
// temporarily RTS and restored before returning. Marker operands at cell+1
// change while building the boundaries, then every visited cell resets itself.
// The generated opcodes, destination addresses, and row tables stay immutable.
