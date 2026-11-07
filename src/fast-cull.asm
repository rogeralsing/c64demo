.importonce

#if FAST_SOLID
// The paired routine is emitted before cull.asm. Define its shared zero-page
// workspace now so forward references cannot select slower absolute opcodes.
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

// FAST_SOLID's transform is odd under vertex negation. Antipodal triangles
// therefore have exactly opposite signed depth sums. The audited guard makes
// the positive-sum face hidden; only its negative-sum partner can need an area
// test. The model/camera/zoom assertions remain in cull.asm.
.macro FastPairedCullCode() {
@fastCullCodeStart:
@fastCullPairedFaces:
    lda #0
    .for (var face = 0; face < ICOSA_FACE_COUNT; face++) {
        sta visibleFaces+face
    }
    .var pairs = 0
    .for (var face = 0; face < ICOSA_FACE_COUNT; face++) {
        .var opposite = -1
        .for (var candidate = 0; candidate < ICOSA_FACE_COUNT; candidate++) {
            .var matches = 0
            .for (var first = 0; first < 3; first++) {
                .var a = icosaFaces.get(face).get(first)
                .for (var second = 0; second < 3; second++) {
                    .var b = icosaFaces.get(candidate).get(second)
                    .if (icosaX.get(a) == -icosaX.get(b) && icosaY.get(a) == -icosaY.get(b) && icosaZ.get(a) == -icosaZ.get(b)) {
                        .eval matches = matches+1
                    }
                }
            }
            .if (matches == 3) {
                .errorif opposite >= 0, "Icosahedron face has multiple antipodes"
                .eval opposite = candidate
            }
        }
        .errorif opposite < 0, "Icosahedron face lacks an antipode"
        .if (face < opposite) {
            .eval pairs = pairs+1
            lda rotatedZ+icosaFaces.get(face).get(0)
            clc
            adc rotatedZ+icosaFaces.get(face).get(1)
            clc
            adc rotatedZ+icosaFaces.get(face).get(2)
            sta fastFaceDepth+face
            eor #$ff
            clc
            adc #1
            sta fastFaceDepth+opposite
            bmi !oppositeNegative+
            // -sum is nonnegative: the first face is the candidate.
            ldy #face
            jmp !candidate+
        !oppositeNegative:
            // -sum is negative: the opposite face is the candidate.
            eor #$ff
            clc
            adc #1
            ldy #opposite
        !candidate:
            jsr fastCullCandidate
        }
    }
    .assert "Icosahedron antipodal face pairs", pairs, 10
    rts

// A=absolute pair depth0..97; Y=its nonpositive-sum face. Both flags start0.
// Equality at12 is hidden,31 is visible; only13..30 needs the exact area.
fastCullCandidate:
    cmp #13
    bcc !done+
    cmp #31
    bcc !area+
    lda #1
    sta visibleFaces,y
!done:
    rts
!area:
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
    sta visibleFaces,y
    rts
@fastCullCodeEnd:
}
