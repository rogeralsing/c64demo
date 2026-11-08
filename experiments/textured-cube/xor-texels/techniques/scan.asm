// Sample each covered column and emit only changes from the preceding color.
// The body already contributes material3; the closing marker restores it.
// All painting is performed later by the shared XOR-prefix fill.

texelTechniquePrepare:
    rts

texelBuildColumn:
    ldy texelColumnTop
    cpy texelColumnBottom
    bcc !covered+
    rts
!covered:
    lda #3
    sta scanPrevious
!sample:
    jsr texelSampleColor
    sta scanCurrent
    eor scanPrevious
    beq !unchanged+
    jsr texelEmitTransition
!unchanged:
    lda scanCurrent
    sta scanPrevious
    iny
    cpy texelColumnBottom
    bne !sample-
    lda scanPrevious
    eor #3
    beq !done+
    jmp texelEmitTransition
!done:
    rts

scanPrevious: .byte 0
scanCurrent: .byte 0
