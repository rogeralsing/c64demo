.importonce

// Reusable arithmetic for the audited -40..40 rotated-coordinate domain.
// Every entry retains the original reciprocal-depth, quarter-square product,
// and signed 29/20 zoom, biased by 64. No animation frame is stored here.
.const FAST_PROJECTION_MIN = -40
.const FAST_PROJECTION_MAX = 40
.const FAST_PROJECTION_WIDTH = FAST_PROJECTION_MAX-FAST_PROJECTION_MIN+1
.label fastProjectionOffsets = $e200
.label fastProjectionOffsetsEnd = fastProjectionOffsets+FAST_PROJECTION_WIDTH*FAST_PROJECTION_WIDTH
.label fastProjectionRowLo = $fc00
.label fastProjectionRowHi = $fd00
.label fastProjectionTablesStart = fastProjectionOffsets
.label fastProjectionTablesEnd = fastProjectionRowHi+$100
.assert "Fast projection offset bytes", fastProjectionOffsetsEnd-fastProjectionOffsets, 6561
.assert "Fast projection table pages", fastProjectionTablesEnd-fastProjectionTablesStart, 28*$100
.errorif fastProjectionOffsetsEnd > fastProjectionRowLo, "Fast projection offsets overlap row pointers"
.errorif fastProjectionTablesEnd > $ff00, "Fast projection tables reach the terminal marker or vectors"

.macro FastProjectionCode() {
    .errorif SCALE != 64 || ICOSA_VERTEX_COUNT != 12, "Fast projection requires the audited Q6 icosahedron"
@fastProjectionCodeStart:
    .for (var vertex = 0; vertex < ICOSA_VERTEX_COUNT; vertex++) {
        // Raw signed Z indexes the initialized row-pointer pages directly.
        ldx rotatedZ+vertex
        lda fastProjectionRowLo,x
        sta linePointer
        lda fastProjectionRowHi,x
        sta linePointer+1

        lda rotatedX+vertex
        clc
        adc #-FAST_PROJECTION_MIN
        tay
        lda (linePointer),y
        lsr
        sta projectedX+vertex

        lda rotatedY+vertex
        clc
        adc #-FAST_PROJECTION_MIN
        tay
        lda (linePointer),y
        // 128-(offset+64) is the original byte result 64-offset.
        eor #$ff
        clc
        adc #129
        sta projectedY+vertex
    }
    jsr fastRememberBounds
    rts

// Call with CPU port $35 and interrupts disabled, after rotation-table init.
// Clear the complete declared range, including invalid pointers and the gap
// after the 81x81 offsets. $FF01 and the interrupt vectors are never touched.
@fastInitProjectionTables:
    lda #<fastProjectionTablesStart
    sta linePointer
    lda #>fastProjectionTablesStart
    sta linePointer+1
    ldx #(fastProjectionTablesEnd-fastProjectionTablesStart)/$100
    ldy #0
    lda #0
!clear:
    sta (linePointer),y
    iny
    bne !clear-
    inc linePointer+1
    dex
    bne !clear-

    lda #<fastProjectionOffsets
    sta linePointer
    lda #>fastProjectionOffsets
    sta linePointer+1
    lda #FAST_PROJECTION_MIN & $ff
    sta fastProjectionInitZ
!row:
    ldx fastProjectionInitZ
    lda linePointer
    sta fastProjectionRowLo,x
    lda linePointer+1
    sta fastProjectionRowHi,x
    txa
    clc
    adc #64
    tax
    lda depthFactors,x
    sta factor
    ldy #0
!coordinate:
    tya
    sec
    sbc #-FAST_PROJECTION_MIN
    jsr multiplyScaled
    tax
    lda icosahedronZoom,x
    clc
    adc #64
    sta (linePointer),y
    iny
    cpy #FAST_PROJECTION_WIDTH
    bne !coordinate-
    lda linePointer
    clc
    adc #FAST_PROJECTION_WIDTH
    sta linePointer
    bcc !nextRow+
    inc linePointer+1
!nextRow:
    inc fastProjectionInitZ
    lda fastProjectionInitZ
    cmp #FAST_PROJECTION_MAX+1
    bne !row-
    rts
@fastProjectionCodeEnd:

@fastProjectionStateStart:
fastProjectionInitZ: .byte 0
@fastProjectionStateEnd:
    .assert "Fast projection initialization state bytes", fastProjectionStateEnd-fastProjectionStateStart, 1
}
