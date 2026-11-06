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
//
// Public APIs: drawCubeBoundaries, drawBoundary, xorFill. drawBoundary consumes
// lineX0/Y0/X1/Y1 and boundaryColor (1..3), and may reorder its endpoint variables.
// All routines clobber A/X/Y and flags. This module exclusively owns $d0..$df.
.label xorPointer = $d0
.label xorMarkerBase = $d3
.label xorRemainder = $d4
.label xorRemainderStep = $d5
.label xorRowStep = $d6
.label xorDirection = $d7
.label xorColumnCount = $d8
.label xorRestoreOpcode = $d9
.label xorBoundaryEnd = $da
.label xorBoundaryTable = $dc
.label xorBufferIndex = $de

xorBoundaryCodeStart:

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

    // Select one fixed-mask chain for this color and physical charset.
    lda drawBufferHi
    and #$08
    lsr
    ora boundaryColor
    tax
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
    // LDA #mask; temporarily return there, then restore its original opcode.
    ldy #0
    lda #$60
    sta (xorBoundaryEnd),y
    ldy lineY0
xorBoundaryDispatch:
    jsr $ffff
    ldy #0
    lda #$a9
    sta (xorBoundaryEnd),y
    rts

// Select the first packed byte and color pair. The caller receives the pair
// mask in A; no slope state is read or changed by this address calculation.
.macro XorBoundaryTarget() {
    lda lineX0
    and #4
    asl
    asl
    asl
    asl
    asl
    sta xorPointer
    lda lineX0
    lsr
    lsr
    lsr
    clc
    adc drawBufferHi
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
    ldy lineY0
    eor (xorPointer),y
    sta (xorPointer),y
    rts

xorBoundaryCodeEnd:

// Each X owns one 24-byte block. Masks and byte addresses are constants;
// execution falls directly into the next X without shifting or pointer work.
.const XOR_BOUNDARY_BLOCK_SIZE = 24
.macro XorBoundaryKernel(buffer, color) {
    .for (var pixelX = 0; pixelX < 64; pixelX++) {
        .var mask = color << (6 - 2 * (pixelX & 3))
        .var address = buffer + floor(pixelX / 4) * 128
        lda #mask
        eor address,y
        sta address,y

        // The signed quotient moves directly to the next intersection row. Only
        // the residual fraction can add one further row; intermediate rows are not marked.
        lda xorRemainder
        clc
        adc xorRemainderStep
        bcc !fractionReady+
        sbc lineDX
        iny
    !fractionReady:
        sta xorRemainder
        // No overflow leaves carry clear. After overflow, SBC dx borrows,
        // also clearing carry, so the signed row addition needs no CLC.
        tya
        adc xorRowStep
        tay
    }
    rts
}

xorBoundaryKernelsStart:
xorBoundaryA1: XorBoundaryKernel(CHARSET_A, 1)
xorBoundaryA2: XorBoundaryKernel(CHARSET_A, 2)
xorBoundaryA3: XorBoundaryKernel(CHARSET_A, 3)
xorBoundaryB1: XorBoundaryKernel(CHARSET_B, 1)
xorBoundaryB2: XorBoundaryKernel(CHARSET_B, 2)
xorBoundaryB3: XorBoundaryKernel(CHARSET_B, 3)
xorBoundaryKernelsEnd:
    .assert "XOR boundary kernel sizes", xorBoundaryKernelsEnd-xorBoundaryKernelsStart, 6*(64*XOR_BOUNDARY_BLOCK_SIZE+1)

.macro XorBoundaryTable(kernel) {
    .fill 64, <(kernel + i*XOR_BOUNDARY_BLOCK_SIZE)
    .fill 64, >(kernel + i*XOR_BOUNDARY_BLOCK_SIZE)
}

// Each 128-byte table fits in a page, including its high-byte half.
.align $80
xorBoundaryTablesStart:
xorBoundaryTableA1: XorBoundaryTable(xorBoundaryA1)
xorBoundaryTableA2: XorBoundaryTable(xorBoundaryA2)
xorBoundaryTableA3: XorBoundaryTable(xorBoundaryA3)
xorBoundaryTableB1: XorBoundaryTable(xorBoundaryB1)
xorBoundaryTableB2: XorBoundaryTable(xorBoundaryB2)
xorBoundaryTableB3: XorBoundaryTable(xorBoundaryB3)
xorBoundaryTableLo:
    .byte 0, <xorBoundaryTableA1, <xorBoundaryTableA2, <xorBoundaryTableA3
    .byte 0, <xorBoundaryTableB1, <xorBoundaryTableB2, <xorBoundaryTableB3
xorBoundaryTableHi:
    .byte 0, >xorBoundaryTableA1, >xorBoundaryTableA2, >xorBoundaryTableA3
    .byte 0, >xorBoundaryTableB1, >xorBoundaryTableB2, >xorBoundaryTableB3
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
    ldy dirtyMinColumn,x
    cpx #0
    beq !kernelIndex+
    tya
    ora #16
    tay
!kernelIndex:
    lda xorColumnKernelLo,y
    sta xorFillEntry+1
    sta xorPointer
    lda xorColumnKernelHi,y
    sta xorFillEntry+2
    sta xorPointer+1

    ldy dirtyMinRow,x
    lda xorRowOffsetLo,y
    clc
    adc xorFillEntry+1
    sta xorFillEntry+1
    lda xorRowOffsetHi,y
    adc xorFillEntry+2
    sta xorFillEntry+2
    ldy dirtyMaxRow,x
    iny
    lda xorRowOffsetLo,y
    clc
    adc xorPointer
    sta xorPointer
    lda xorRowOffsetHi,y
    adc xorPointer+1
    sta xorPointer+1
    lda dirtyMaxColumn,x
    sec
    sbc dirtyMinColumn,x
    clc
    adc #1
    sta xorColumnCount

    // The row after the rectangle normally starts with EOR. At row 128 it is
    // already the column's native RTS; saving the actual opcode handles both.
    ldy #0
    lda (xorPointer),y
    sta xorRestoreOpcode
!column:
    ldy #0
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

    // Every column has 128 six-byte EOR/STA pairs and one RTS: 769 bytes.
    lda xorFillEntry+1
    clc
    adc #1
    sta xorFillEntry+1
    lda xorFillEntry+2
    adc #3
    sta xorFillEntry+2
    lda xorPointer
    clc
    adc #1
    sta xorPointer
    lda xorPointer+1
    adc #3
    sta xorPointer+1
    jmp !column-
!done:
    rts
xorFillCodeEnd:

.macro XorFillColumns(buffer) {
    .for (var column = 0; column < 16; column++) {
        .for (var row = 0; row < 128; row++) {
            eor buffer + column * 128 + row
            sta buffer + column * 128 + row
        }
        rts
    }
}

xorFillKernelsStart:
xorFillKernelsA:
    XorFillColumns(CHARSET_A)
    .assert "XOR fill A kernel size", *-xorFillKernelsA, 16*769
xorFillKernelsB:
    XorFillColumns(CHARSET_B)
    .assert "XOR fill B kernel size", *-xorFillKernelsB, 16*769
xorFillKernelsEnd:

xorFillTablesStart:
xorColumnKernelLo:
    .fill 16, <(xorFillKernelsA + i*769)
    .fill 16, <(xorFillKernelsB + i*769)
xorColumnKernelHi:
    .fill 16, >(xorFillKernelsA + i*769)
    .fill 16, >(xorFillKernelsB + i*769)
xorRowOffsetLo:
    .fill 129, <(i*6)
xorRowOffsetHi:
    .fill 129, >(i*6)
xorFillTablesEnd:

fillStateStart:
boundaryColor: .byte 0
xorFaceColors: .fill 6, 0
fillStateEnd:

// Persistent SMC: xorBoundaryDispatch+1..+2 and xorFillEntry+1..+2.
// During drawBoundary only, the first byte at the excluded endpoint's block
// is temporarily RTS and restored to LDA immediate before returning.
// During xorFill only, one byte at
// columnKernel + 6*(dirtyMaxRow+1) is temporarily RTS and restored before return.
// The generated code, transition tables, and row tables are otherwise immutable.
