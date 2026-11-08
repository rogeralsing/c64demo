// Emit selective STA screen-cell clears from the prepared possible-touch map.
// Matrices are cleared; private font rows are initialized only on first touch.
generateClears:
    lda #<CLEAR_CODE
    sta codePointer
    lda #>CLEAR_CODE
    sta codePointer+1
    lda #0
    sta genBuffer
!buffer:
    lda codePointer
    ldx genBuffer
    beq !pointerA+
    sta clearB
    lda codePointer+1
    sta clearB+1
    jmp !pointerReady+
!pointerA:
    sta clearA
    lda codePointer+1
    sta clearA+1
!pointerReady:
    lda #<clearMap
    sta mapPointer
    lda #>clearMap
    sta mapPointer+1
    lda #0
    sta screenPointer
    lda genBuffer
    asl
    asl
    asl
    clc
    adc #4
    sta screenPointer+1
!cell:
    ldy #0
    lda (mapPointer),y
    beq !skip+
    lda #$8d
    jsr emitA
    lda screenPointer
    jsr emitA
    lda screenPointer+1
    jsr emitA
!skip:
    inc screenPointer
    bne !matrix+
    inc screenPointer+1
!matrix:
    inc mapPointer
    bne !cell-
    inc mapPointer+1
    lda mapPointer+1
    cmp #>(clearMap+1024)
    bne !cell-
    lda #$60
    jsr emitA
    inc genBuffer
    lda genBuffer
    cmp #2
    bne !buffer-
    lda codePointer
    sta clearEnd
    lda codePointer+1
    sta clearEnd+1
    rts
emitA:
    ldy #0
    sta (codePointer),y
    inc codePointer
    bne !done+
    inc codePointer+1
!done:
    rts
