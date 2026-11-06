.importonce
.import source "macros.asm"

// Dirty rectangles belong to their physical charset buffer. Clear the previous
// rectangle before drawing into that buffer, then call rememberBounds after
// projection. Projected vertices must remain inside the 128x128 canvas.
// Both routines clobber A, X, Y and flags. The raster IRQ may remain enabled:
// it preserves A and never executes or modifies this code.
// This module exclusively owns zero-page $e0..$e1.
.label clearPatchPointer = $e0

clearCodeStart:
clearDirtyRect:
    ldx #0
    lda drawBufferHi
    and #$08
    beq !buffer+
    inx
!buffer:
    lda dirtyMinRow,x
    sta clearFirstRow+1
    lda dirtyMaxRow,x
    clc
    adc #1
    sta clearLastRow+1

    // Enter the first dirty column's fixed-address store chain.
    ldy dirtyMinColumn,x
    lda clearColumnOffsets,y
    clc
    adc clearChainLo,x
    sta clearEntry+1
    lda clearChainHi,x
    adc #0
    sta clearEntry+2

    lda #0
    sta clearPatched
    ldy dirtyMaxColumn,x
    cpy #15
    beq clearFill

    // Temporarily replace the next column's STA with JMP clearNextRow.
    // A rectangle ending at column 15 already reaches the chain's own JMP.
    iny
    lda clearColumnOffsets,y
    clc
    adc clearChainLo,x
    sta clearPatchPointer
    lda clearChainHi,x
    adc #0
    sta clearPatchPointer+1
    ldy #2
!patch:
    lda (clearPatchPointer),y
    sta clearSavedBytes,y
    lda clearJumpBytes,y
    sta (clearPatchPointer),y
    dey
    bpl !patch-
    inc clearPatched

clearFill:
    lda #0
clearFirstRow:
    ldx #0
clearEntry:
    jmp clearChainA

clearChainA:
    StoreColumns(CHARSET_A, 16)
    jmp clearNextRow
clearChainB:
    StoreColumns(CHARSET_B, 16)
    jmp clearNextRow

clearNextRow:
    inx
clearLastRow:
    cpx #1
    bne clearEntry

    // Restore every changed chain byte before any later render can use it.
    lda clearPatched
    beq !done+
    ldy #2
!restore:
    lda clearSavedBytes,y
    sta (clearPatchPointer),y
    dey
    bpl !restore-
!done:
    rts

rememberBounds:
    ldx #0
    lda drawBufferHi
    and #$08
    beq !buffer+
    inx
!buffer:
    lda projectedX
    lsr
    lsr
    .if (!FILLED_MODE) { lsr }
    sta dirtyMinColumn,x
    sta dirtyMaxColumn,x
    lda projectedY
    sta dirtyMinRow,x
    sta dirtyMaxRow,x

    ldy #7
!vertex:
    lda projectedX,y
    lsr
    lsr
    .if (!FILLED_MODE) { lsr }
    cmp dirtyMinColumn,x
    bcs !minColumn+
    sta dirtyMinColumn,x
!minColumn:
    cmp dirtyMaxColumn,x
    bcc !maxColumn+
    sta dirtyMaxColumn,x
!maxColumn:
    lda projectedY,y
    cmp dirtyMinRow,x
    bcs !minRow+
    sta dirtyMinRow,x
!minRow:
    cmp dirtyMaxRow,x
    bcc !maxRow+
    sta dirtyMaxRow,x
!maxRow:
    dey
    bne !vertex-
    rts
clearCodeEnd:

clearChainLo:
    .byte <clearChainA, <clearChainB
clearChainHi:
    .byte >clearChainA, >clearChainB
clearColumnOffsets:
    .fill 16, i * 3
clearJumpBytes:
    .byte $4c, <clearNextRow, >clearNextRow

clearStateStart:
dirtyMinColumn: .byte 0, 0
dirtyMaxColumn: .byte 0, 0
dirtyMinRow:    .byte 0, 0
dirtyMaxRow:    .byte 0, 0
clearPatched:   .byte 0
clearSavedBytes: .fill 3, 0
clearStateEnd:
