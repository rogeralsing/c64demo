.importonce

// An opaque cube with a separate inset triangle painted on each face. The body
// keeps its eight cube corners. Three shared scratch vertices hold one visible
// marking at a time; all body and marking edges feed a single prefix fill.
.const PAINTED_BODY_VERTEX_COUNT = 8
.const PAINTED_PATCH_VERTEX_COUNT = 3
.const PAINTED_VERTEX_COUNT = PAINTED_BODY_VERTEX_COUNT+PAINTED_PATCH_VERTEX_COUNT
.const PAINTED_FACE_COUNT = 6
.const PAINTED_PARENT_COUNT = PAINTED_FACE_COUNT
.const PAINTED_EDGE_COUNT = 12
.const PAINTED_PATCH_FIRST = PAINTED_BODY_VERTEX_COUNT
.label paintedHalfSize = HALF_SIZE
.label paintedMarkNormalLimit = -13
.errorif HALF_SIZE != 32, "Inset painted cube requires thirty-two-unit cube corners"

// Existing culling workspace, defined early because preparation is emitted
// below the BASIC entry point and before the shared cull.asm implementation.
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

// Reusable exact projection products, generated once during blanked startup.
// The 83x83 entries cover signed coordinates/depths -41..41, biased by 64.
// Row pointers use index z+41. Invalid pointer slots and the 23-byte gap are zero.
.const PAINTED_PROJECTION_MIN = -41
.const PAINTED_PROJECTION_MAX = 41
.const PAINTED_PROJECTION_WIDTH = 83
.label paintedProjectionTablesStart = $e000
.label paintedProjectionOffsets = paintedProjectionTablesStart
.label paintedProjectionOffsetsEnd = paintedProjectionOffsets+PAINTED_PROJECTION_WIDTH*PAINTED_PROJECTION_WIDTH
.label paintedProjectionRowLo = $fb00
.label paintedProjectionRowHi = $fb80
.label paintedProjectionTablesEnd = $fc00
.errorif paintedProjectionOffsetsEnd > paintedProjectionRowLo, "Painted projection products overlap their row pointers"
.errorif paintedProjectionTablesEnd-paintedProjectionTablesStart != 28*$100, "Painted projection table reservation must be twenty-eight pages"

.function PaintedQuad(a, b, c, d) {
    .var result = List()
    .eval result.add(a)
    .eval result.add(b)
    .eval result.add(c)
    .eval result.add(d)
    .return result
}

// Outward faces follow the shared cube visibility order X-,X+,Y-,Y+,Z-,Z+.
.var paintedQuads = List()
.eval paintedQuads.add(PaintedQuad(0, 4, 6, 2))
.eval paintedQuads.add(PaintedQuad(1, 3, 7, 5))
.eval paintedQuads.add(PaintedQuad(0, 1, 5, 4))
.eval paintedQuads.add(PaintedQuad(2, 6, 7, 3))
.eval paintedQuads.add(PaintedQuad(0, 2, 3, 1))
.eval paintedQuads.add(PaintedQuad(4, 5, 7, 6))

.var paintedBaseColors = List()
.eval paintedBaseColors.add(2)
.eval paintedBaseColors.add(2)
.eval paintedBaseColors.add(3)
.eval paintedBaseColors.add(3)
.eval paintedBaseColors.add(1)
.eval paintedBaseColors.add(1)
.var paintedPatchColors = List()
.eval paintedPatchColors.add(1)
.eval paintedPatchColors.add(1)
.eval paintedPatchColors.add(2)
.eval paintedPatchColors.add(2)
.eval paintedPatchColors.add(3)
.eval paintedPatchColors.add(3)

// Derive only the twelve physical cube edges. Markings have independent
// triangle perimeters and do not subdivide or replace the body faces.
.var paintedEdges = List()
.for (var first = 0; first < PAINTED_BODY_VERTEX_COUNT; first++) {
    .for (var last = first+1; last < PAINTED_BODY_VERTEX_COUNT; last++) {
        .var adjacentFaces = List()
        .for (var face = 0; face < PAINTED_FACE_COUNT; face++) {
            .var hasFirst = false
            .var hasLast = false
            .for (var corner = 0; corner < 4; corner++) {
                .if (paintedQuads.get(face).get(corner) == first) { .eval hasFirst = true }
                .if (paintedQuads.get(face).get(corner) == last) { .eval hasLast = true }
            }
            .if (hasFirst && hasLast) { .eval adjacentFaces.add(face) }
        }
        .if (adjacentFaces.size() == 2) {
            .var difference = first ^ last
            .errorif (difference & (difference-1)) != 0, "Painted body edge must lie along one cube axis"
            .var edge = List()
            .eval edge.add(first)
            .eval edge.add(last)
            .eval edge.add(adjacentFaces.get(0))
            .eval edge.add(adjacentFaces.get(1))
            .eval paintedEdges.add(edge)
            .errorif paintedBaseColors.get(adjacentFaces.get(0)) == paintedBaseColors.get(adjacentFaces.get(1)), "Adjacent painted body faces need different base colors"
        } else {
            .errorif adjacentFaces.size() > 2, "Painted cube edge has too many incident faces"
        }
    }
}
.errorif paintedEdges.size() != PAINTED_EDGE_COUNT, "Painted cube must have twelve physical edges"
.errorif PAINTED_BODY_VERTEX_COUNT-PAINTED_EDGE_COUNT+PAINTED_FACE_COUNT != 2, "Painted cube Euler characteristic must be two"
.for (var face = 0; face < PAINTED_FACE_COUNT; face++) {
    .errorif paintedBaseColors.get(face) < 1 || paintedBaseColors.get(face) > 3, "Painted body materials must be nonblack selectors"
    .errorif paintedPatchColors.get(face) < 1 || paintedPatchColors.get(face) > 3, "Painted markings must be nonblack selectors"
    .errorif paintedBaseColors.get(face) == paintedPatchColors.get(face), "An inset marking must differ from its body face"
}

.macro PaintedModelData() {
@paintedTablesStart:
@paintedFaceA:        .fill PAINTED_FACE_COUNT, paintedQuads.get(i).get(0)
@paintedFaceB:        .fill PAINTED_FACE_COUNT, paintedQuads.get(i).get(1)
@paintedFaceC:        .fill PAINTED_FACE_COUNT, paintedQuads.get(i).get(2)
@paintedFaceD:        .fill PAINTED_FACE_COUNT, paintedQuads.get(i).get(3)
@paintedFaceColor:    .fill PAINTED_FACE_COUNT, paintedBaseColors.get(i)
@paintedMarkColor:    .fill PAINTED_FACE_COUNT, paintedPatchColors.get(i)
@paintedMarkDelta:    .fill PAINTED_FACE_COUNT, paintedBaseColors.get(i)^paintedPatchColors.get(i)
@paintedFaceBits:     .fill PAINTED_FACE_COUNT, 1 << i
@paintedNormalAxis:   .fill PAINTED_FACE_COUNT, floor(i/2)
@paintedNormalOffset: .fill PAINTED_FACE_COUNT, floor(i/2)*3
@paintedNormalSign:   .fill PAINTED_FACE_COUNT, (i & 1) == 0 ? $ff : 1
@paintedEdgeA:        .fill PAINTED_EDGE_COUNT, paintedEdges.get(i).get(0)
@paintedEdgeB:        .fill PAINTED_EDGE_COUNT, paintedEdges.get(i).get(1)
@paintedEdgeFaceA:    .fill PAINTED_EDGE_COUNT, paintedEdges.get(i).get(2)
@paintedEdgeFaceB:    .fill PAINTED_EDGE_COUNT, paintedEdges.get(i).get(3)
@paintedTablesEnd:
    .assert "Inset painted model table bytes", paintedTablesEnd-paintedTablesStart, PAINTED_FACE_COUNT*11+PAINTED_EDGE_COUNT*4
    .errorif axisYZ-axisXZ != 3 || axisZZ-axisXZ != 6, "Painted normal lookup requires the shared axis layout"
}

// CPU signed floor(value/2). Every sum is within signed-byte range. CMP
// supplies the sign bit to ROR without adding a branch or a separate sign byte.
.macro PaintedSignedHalf() {
    cmp #$80
    ror
}

.macro PaintedPrepareCode() {
@paintedPrepareCodeStart:
@paintedPrepareColors:
    lda #0
    sta paintedMarkFaces
    ldx #PAINTED_FACE_COUNT-1
!face:
    lda visibleFaces
    and paintedFaceBits,x
    bne !visible+
    sta xorFaceColors,x
    jmp !next+
!visible:
    lda paintedFaceColor,x
    sta xorFaceColors,x
    ldy paintedNormalOffset,x
    lda axisXZ,y
    ldy paintedNormalSign,x
    bpl !normal+
    eor #$ff
    clc
    adc #1
!normal:
    eor #$80
    cmp #paintedMarkNormalLimit+$80+1
    bcs !next+
    lda paintedMarkFaces
    ora paintedFaceBits,x
    sta paintedMarkFaces
!next:
    dex
    bpl !face-
    rts

// Startup only: CPU port $35, interrupts disabled, display blank. C0 is a
// temporary row counter; the complete table reservation is initialized first.
@paintedInitProjection:
    lda #<paintedProjectionTablesStart
    sta linePointer
    lda #>paintedProjectionTablesStart
    sta linePointer+1
    ldx #(paintedProjectionTablesEnd-paintedProjectionTablesStart)/$100
    ldy #0
    lda #0
!clear:
    sta (linePointer),y
    iny
    bne !clear-
    inc linePointer+1
    dex
    bne !clear-
    lda #<paintedProjectionOffsets
    sta linePointer
    lda #>paintedProjectionOffsets
    sta linePointer+1
    lda #0
    sta cullDX1
!row:
    ldx cullDX1
    lda linePointer
    sta paintedProjectionRowLo,x
    lda linePointer+1
    sta paintedProjectionRowHi,x
    txa
    clc
    adc #64+PAINTED_PROJECTION_MIN
    tax
    lda depthFactors,x
    sta factor
    ldy #0
!coordinate:
    tya
    sec
    sbc #-PAINTED_PROJECTION_MIN
    jsr multiplyScaled
    clc
    adc #64
    sta (linePointer),y
    iny
    cpy #PAINTED_PROJECTION_WIDTH
    bne !coordinate-
    lda linePointer
    clc
    adc #PAINTED_PROJECTION_WIDTH
    sta linePointer
    bcc !nextRow+
    inc linePointer+1
!nextRow:
    inc cullDX1
    lda cullDX1
    cmp #PAINTED_PROJECTION_WIDTH
    bne !row-
    rts
@paintedPrepareCodeEnd:
}

.macro PaintedDrawCode() {
    .errorif VERTEX_COUNT != PAINTED_VERTEX_COUNT, "Inset painted renderer needs three shared scratch vertices"
    .errorif rotatedY-rotatedX != VERTEX_COUNT || rotatedZ-rotatedY != VERTEX_COUNT, "Painted scratch generation requires contiguous coordinate rows"
@paintedDrawCodeStart:
    jsr paintedPrepareColors
    ldy #PAINTED_EDGE_COUNT-1
!bodyEdge:
    sty cullProductSign
    ldx paintedEdgeFaceA,y
    lda xorFaceColors,x
    sta boundaryColor
    ldx paintedEdgeFaceB,y
    lda xorFaceColors,x
    eor boundaryColor
    beq !bodyNext+
    sta boundaryColor
    ldx paintedEdgeA,y
    lda projectedX,x
    sta lineX0
    lda projectedY,x
    sta lineY0
    ldx paintedEdgeB,y
    lda projectedX,x
    sta lineX1
    lda projectedY,x
    sta lineY1
    jsr drawBoundary
!bodyNext:
    ldy cullProductSign
    dey
    bpl !bodyEdge-

@paintedPatchCodeStart:
    ldx #PAINTED_FACE_COUNT-1
!mark:
    lda paintedMarkFaces
    and paintedFaceBits,x
    beq !markNext+
    stx cullProductSign
    jsr paintedMakePatch
    jsr paintedProjectPatch
    ldx cullProductSign
    lda paintedMarkDelta,x
    sta boundaryColor
    .for (var edge = 0; edge < PAINTED_PATCH_VERTEX_COUNT; edge++) {
        .var first = PAINTED_PATCH_FIRST+edge
        .var last = PAINTED_PATCH_FIRST+((edge+1)-floor((edge+1)/PAINTED_PATCH_VERTEX_COUNT)*PAINTED_PATCH_VERTEX_COUNT)
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
    ldx cullProductSign
!markNext:
    dex
    bpl !mark-
    rts

// Input X is a visible parent face. C0..C3 hold its corner indices, C4 remains
// the outer face cursor, C5 is the current-axis center, and C6 counts axes.
// N=(A+C)/2; P0=(A+N)/2; P1=(B+N)/2; P2=(((C+D)/2)+N)/2.
// All divisions are signed floors. The three scratch positions occupy slots
// 8..10 in each coordinate row and never replace the eight body corners.
@paintedMakePatch:
    ldy paintedFaceA,x
    sty cullDX1
    ldy paintedFaceB,x
    sty cullDY1
    ldy paintedFaceC,x
    sty cullDX2
    ldy paintedFaceD,x
    sty cullDY2
    lda #<rotatedX
    sta linePointer
    lda #>rotatedX
    sta linePointer+1
    lda #3
    sta cullProductHi
!axis:
    ldy cullDX1
    lda (linePointer),y
    ldy cullDX2
    clc
    adc (linePointer),y
    PaintedSignedHalf()
    sta cullProductLo
    ldy cullDX1
    lda (linePointer),y
    clc
    adc cullProductLo
    PaintedSignedHalf()
    ldy #PAINTED_PATCH_FIRST
    sta (linePointer),y
    ldy cullDY1
    lda (linePointer),y
    clc
    adc cullProductLo
    PaintedSignedHalf()
    ldy #PAINTED_PATCH_FIRST+1
    sta (linePointer),y
    ldy cullDX2
    lda (linePointer),y
    ldy cullDY2
    clc
    adc (linePointer),y
    PaintedSignedHalf()
    clc
    adc cullProductLo
    PaintedSignedHalf()
    ldy #PAINTED_PATCH_FIRST+2
    sta (linePointer),y
    lda linePointer
    clc
    adc #VERTEX_COUNT
    sta linePointer
    bcc !nextAxis+
    inc linePointer+1
!nextAxis:
    dec cullProductHi
    bne !axis-
    rts

// Exact original Q6 perspective on the three scratch vertices. The cached
// product includes +64: X is table>>1 and Y is 128-table, both modulo a byte.
// No body bounds are updated here; the inset-containment contract keeps every
// accepted marking inside the existing body rectangle.
@paintedProjectPatch:
    ldx #PAINTED_PATCH_FIRST
!vertex:
    lda rotatedZ,x
    clc
    adc #-PAINTED_PROJECTION_MIN
    tay
    lda paintedProjectionRowLo,y
    sta linePointer
    lda paintedProjectionRowHi,y
    sta linePointer+1
    lda rotatedX,x
    clc
    adc #-PAINTED_PROJECTION_MIN
    tay
    lda (linePointer),y
    lsr
    sta projectedX,x
    lda rotatedY,x
    clc
    adc #-PAINTED_PROJECTION_MIN
    tay
    lda (linePointer),y
    eor #$ff
    clc
    adc #129
    sta projectedY,x
    inx
    cpx #PAINTED_VERTEX_COUNT
    bne !vertex-
    rts
@paintedPatchCodeEnd:
@paintedDrawCodeEnd:
}
