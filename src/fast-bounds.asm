.importonce

// Exact full-row dirty rectangle for the fixed twelve-vertex fast renderer.
// Keep extrema in pixels while comparing; only the final X extrema are divided
// by four. No generated code or self-modification is needed.
.label fastBoundsStateStart = $e2
.label fastBoundsMinX = $e2
.label fastBoundsMaxX = $e3
.label fastBoundsMinY = $e4
.label fastBoundsMaxY = $e5
.label fastBoundsStateEnd = $e6

.macro FastBoundsCode() {
    .errorif VERTEX_COUNT != 12 || !FILLED_MODE, "Fast bounds requires the filled twelve-vertex model"
@fastBoundsCodeStart:
@fastRememberBounds:
    lda projectedX
    sta fastBoundsMinX
    sta fastBoundsMaxX
    lda projectedY
    sta fastBoundsMinY
    sta fastBoundsMaxY
    .for (var vertex = 1; vertex < 12; vertex++) {
        lda projectedX+vertex
        cmp fastBoundsMinX
        bcs !minX+
        sta fastBoundsMinX
    !minX:
        cmp fastBoundsMaxX
        bcc !maxX+
        sta fastBoundsMaxX
    !maxX:
        lda projectedY+vertex
        cmp fastBoundsMinY
        bcs !minY+
        sta fastBoundsMinY
    !minY:
        cmp fastBoundsMaxY
        bcc !maxY+
        sta fastBoundsMaxY
    !maxY:
    }
    ldx #0
    lda drawBufferHi
    and #$08
    beq !buffer+
    inx
!buffer:
    lda fastBoundsMinX
    lsr
    lsr
    sta dirtyMinColumn,x
    lda fastBoundsMaxX
    lsr
    lsr
    sta dirtyMaxColumn,x
    lda fastBoundsMinY
    sta dirtyMinRow,x
    lda fastBoundsMaxY
    sta dirtyMaxRow,x
    rts
@fastBoundsCodeEnd:
    .errorif fastBoundsCodeEnd-fastBoundsCodeStart > 384, "Unrolled fast bounds exceeds its low-code allowance"
}
