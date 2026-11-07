// The doubled midpoint diagonal is the sum of the four bounds minus 256.
// Byte wrap removes that center offset. The lookup absorbs division, the
// per-face radius scale, gradient selection, and shade thresholds.
.macro BoundsDiagonal() {
    lda minX
    clc
    adc maxX
    clc
    adc minY
    clc
    adc maxY
    tay
}

faceLighting:
    // Preserve X, which holds the sprite metadata slot.
    BoundsDiagonal()
    lda facePositionColors,y
    rts
