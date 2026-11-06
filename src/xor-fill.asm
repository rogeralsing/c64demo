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
.label xorMarkerMask = $d2
.label xorMarkerBase = $d3
.label xorRemainder = $d4
.label xorRemainderStep = $d5
.label xorRowStep = $d6
.label xorDirection = $d7
.label xorColumnCount = $d8
.label xorRestoreOpcode = $d9
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
    ldx #0
    sec
!divide:
    sbc lineDX
    bcc !divided+
    inx
    bcs !divide-
!divided:
    adc lineDX
    sta xorRemainderStep
    txa
    ldx xorDirection
    beq !positiveStep+
    eor #$ff
    clc
    adc #1
    sta xorRowStep
    lda #0
    sta xorRemainder
    jmp !stepReady+
!positiveStep:
    sta xorRowStep
    lda lineDX
    sec
    sbc #1
    sta xorRemainder
!stepReady:
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
    sta xorMarkerMask
    ldx boundaryColor
    lda xorPairBaseMasks,x
    sta xorMarkerBase
    ldx lineDX
    ldy lineY0
    lda xorDirection
    bmi xorBoundaryUp
    jmp xorBoundaryDown

.macro XorBoundaryLoop(down) {
!pixel:
    lda xorMarkerMask
    eor (xorPointer),y
    sta (xorPointer),y
    dex
    beq !done+

    // The signed quotient moves directly to the next intersection row. Only
    // the residual fraction can add one further row; intermediate rows are not marked.
    tya
    clc
    adc xorRowStep
    tay
    lda xorRemainder
    clc
    adc xorRemainderStep
    cmp lineDX
    bcc !fractionReady+
    sbc lineDX
    .if (down) { iny } else { dey }
!fractionReady:
    sta xorRemainder

    lsr xorMarkerMask
    lsr xorMarkerMask
    bne !pixel-
    lda xorMarkerBase
    sta xorMarkerMask
    lda xorPointer
    eor #$80
    sta xorPointer
    bmi !pixel-
    inc xorPointer+1
    jmp !pixel-
!done:
    rts
}

xorBoundaryDown:
    XorBoundaryLoop(true)
xorBoundaryUp:
    XorBoundaryLoop(false)
xorBoundaryCodeEnd:

// Each logical X lane occupies one two-bit pair. Index by color*4 + (x&3).
xorPairMasks:
    .byte $00,$00,$00,$00, $40,$10,$04,$01
    .byte $80,$20,$08,$02, $c0,$30,$0c,$03
xorPairBaseMasks:
    .byte $00,$40,$80,$c0

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

// Persistent SMC: xorFillEntry+1..+2. During xorFill only, one byte at
// columnKernel + 6*(dirtyMaxRow+1) is temporarily RTS and restored before return.
// The generated code, transition tables, and row tables are otherwise immutable.
