// Three 128-presentation phases: different ramps, matching ramps, color cycling.
// Swap the primary ramp each round so the matching phase visits both families.
initializePalette:
    lda #0
    sta paletteTick
    sta paletteMode
    sta paletteBase
    sta paletteShift
    jmp loadPalette

advancePalette:
    inc paletteTick
    bpl !withinPhase+
    lda #0
    sta paletteTick
    sta paletteShift
    inc paletteMode
    lda paletteMode
    cmp #3
    bcc loadPalette
    lda #0
    sta paletteMode
    lda paletteBase
    eor #48
    sta paletteBase
    jmp loadPalette
!withinPhase:
    lda paletteMode
    cmp #2
    bne !done+
    lda paletteTick
    and #7
    bne !done+
    inc paletteShift
    lda paletteShift
    cmp #6
    bcc loadPalette
    lda #0
    sta paletteShift
    jmp loadPalette
!done:
    rts

loadPalette:
    lda paletteShift
    asl
    asl
    asl
    sta paletteOffset
    clc
    adc paletteBase
    tax
    ldy #0
!hexagons:
    lda paletteSequences,x
    sta activeHexColors,y
    inx
    iny
    cpy #8
    bne !hexagons-
    lda paletteBase
    ldy paletteMode
    cpy #1
    beq !matching+
    eor #48
!matching:
    clc
    adc paletteOffset
    tax
    ldy #0
!pentagons:
    lda paletteSequences,x
    asl
    asl
    asl
    asl
    sta activeGapColors,y
    inx
    iny
    cpy #8
    bne !pentagons-
    rts

paletteTick: .byte 0
paletteMode: .byte 0
paletteBase: .byte 0
paletteShift: .byte 0
paletteOffset: .byte 0
activeHexColors: .fill 8, 0
activeGapColors: .fill 8, 0

// Keep black shadows and white highlights; rotate the six middle shades.
paletteSequences:
    .byte 0,9,11,5,12,3,13,1
    .byte 0,11,5,12,3,13,9,1
    .byte 0,5,12,3,13,9,11,1
    .byte 0,12,3,13,9,11,5,1
    .byte 0,3,13,9,11,5,12,1
    .byte 0,13,9,11,5,12,3,1
    .byte 0,6,2,4,10,15,7,1
    .byte 0,2,4,10,15,7,6,1
    .byte 0,4,10,15,7,6,2,1
    .byte 0,10,15,7,6,2,4,1
    .byte 0,15,7,6,2,4,10,1
    .byte 0,7,6,2,4,10,15,1
