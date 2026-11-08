// Build two complete256-case endpoint-byte dispatch tables in C64RAM.
generateSpans:
    lda #<GENERATED
    sta codePointer
    lda #>GENERATED
    sta codePointer+1
    lda #0
    sta genBuffer
!buffer:
    lda genBuffer
    asl
    asl
    asl
    clc
    adc #$20
    sta genBaseHi
    lda #0
    sta genLeft
!left:
    lda #0
    sta genRight
!case:
    lda genLeft
    asl
    asl
    asl
    asl
    ora genRight
    tay
    lda genBuffer
    bne !tableB+
    lda codePointer
    sta DISPATCH_A_LO,y
    lda codePointer+1
    sta DISPATCH_A_HI,y
    jmp !tableReady+
!tableB:
    lda codePointer
    sta DISPATCH_B_LO,y
    lda codePointer+1
    sta DISPATCH_B_HI,y
!tableReady:
    lda genLeft
    cmp genRight
    beq !same+
    bcs !empty+
    jsr generatePositive
    jmp !next+
!same:
    jsr generateSame
    jmp !next+
!empty:
    lda #$60
    jsr emitA
!next:
    inc genRight
    lda genRight
    cmp #16
    bne !case-
    inc genLeft
    lda genLeft
    cmp #16
    bne !left-
    inc genBuffer
    lda genBuffer
    cmp #2
    bne !buffer-
    lda codePointer
    sta generationEnd
    lda codePointer+1
    sta generationEnd+1
    rts
generateSame:
    lda genLeft
    sta genColumn
    lda #$59
    jsr emitAbsolute
    lda #$25
    jsr emitA
    lda #spanMask
    jsr emitA
    lda #$59
    jsr emitAbsolute
    lda #$99
    jsr emitAbsolute
    lda #$60
    jmp emitA
generatePositive:
    lda genLeft
    clc
    adc #1
    sta genInterior
!interior:
    lda genInterior
    cmp genRight
    beq !ends+
    sta genColumn
    lda #$99
    jsr emitAbsolute
    inc genInterior
    jmp !interior-
!ends:
    lda genLeft
    sta genColumn
    lda #$59
    jsr emitAbsolute
    lda #$25
    jsr emitA
    lda #leftMask
    jsr emitA
    lda #$59
    jsr emitAbsolute
    lda #$99
    jsr emitAbsolute
    lda #$a5
    jsr emitA
    lda #ink
    jsr emitA
    lda genRight
    sta genColumn
    lda #$59
    jsr emitAbsolute
    lda #$25
    jsr emitA
    lda #rightMask
    jsr emitA
    lda #$59
    jsr emitAbsolute
    lda #$99
    jsr emitAbsolute
    lda #$60
    jmp emitA
emitAbsolute:
    jsr emitA
    lda genColumn
    and #1
    asl
    asl
    asl
    asl
    asl
    asl
    asl
    jsr emitA
    lda genColumn
    lsr
    clc
    adc genBaseHi
    jmp emitA
emitA:
    ldy #0
    sta (codePointer),y
    inc codePointer
    bne !done+
    inc codePointer+1
!done:
    rts
