.importonce

.macro UVGradientCode(area,remainder,numerator,divisionSign,subtraction) {
// Shared exact signed Q8 UV gradient division. Caller supplies area, remainder,
// numerator, divisionSign and subtraction. Original perspective bounds below
// describe that caller; other bounded callers separately audit their ranges.
// Return floor(4096*A/area) in X:A, including negative numerators.
// A is signed; the positive area is at most842 for this authored motion.
// Factor the exact 24-bit numerator into an integer quotient plus12fractional
// bits. The authored |A|<=42 and area>=12 keep the integer quotient at most3.
divideGradient:
    sta remainder
    lda #0
    sta remainder+1
    sta numerator
    sta numerator+1
    sta divisionSign
    lda remainder
    bpl !absolute+
    inc divisionSign
    eor #$ff
    clc
    adc #1
    sta remainder
!absolute:
    // Divide the small integer magnitude first, retaining its exact remainder.
!integer:
    lda remainder
    sec
    sbc area
    sta subtraction
    lda remainder+1
    sbc area+1
    bcc !fraction+
    sta remainder+1
    lda subtraction
    sta remainder
    inc numerator
    jmp !integer-
!fraction:
    ldx #12
!bit:
    asl numerator
    rol numerator+1
    asl remainder
    rol remainder+1
    lda remainder
    sec
    sbc area
    sta subtraction
    lda remainder+1
    sbc area+1
    bcc !less+
    sta remainder+1
    lda subtraction
    sta remainder
    inc numerator
!less:
    dex
    bne !bit-
    lda divisionSign
    beq !result+
    // Negative truncation differs from floor exactly when a remainder exists.
    lda remainder
    ora remainder+1
    beq !negate+
    inc numerator
    bne !negate+
    inc numerator+1
!negate:
    sec
    lda #0
    sbc numerator
    sta numerator
    lda #0
    sbc numerator+1
    sta numerator+1
!result:
    lda numerator
    ldx numerator+1
    rts

}
