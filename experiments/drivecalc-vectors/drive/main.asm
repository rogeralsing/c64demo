// Own fixed-point 3D pipeline. DOS M-E calls this like SYS; return with RTS.
*=$0300 "1541 rotation and perspective"
.label vx=$80
.label vy=$81
.label vz=$82
.label rx=$83
.label rz=$84
.label ry=$85
.label zz=$86
.label temp=$87
.label cy=$88
.label sy=$89
.label cp=$8a
.label sp=$8b
.label depth=$8c
.label vertexIndex=$8d
.label outputIndex=$8e
.label operandA=$8f
.label operandB=$90
.label negative=$91
.label multiplicand=$92
.label multiplier=$94
.label product=$95
.label bits=$97
.label quotient=$98

driveCalcStart:
    php
    sei
    cld
    pha
    txa
    pha
    tya
    pha
    ldx #31
!save:
    lda $80,x
    sta savedZeroPage,x
    dex
    bpl !save-
    lda #0
    sta result+18
    sta vertexIndex
    sta outputIndex
    lda inputPhase
    and #15
    tax
    lda sine,x
    sta sy
    lda cosine,x
    sta cy
    txa
    asl
    clc
    adc inputPhase
    and #15
    tax
    lda sine,x
    sta sp
    lda cosine,x
    sta cp
nextVertex:
    ldx vertexIndex
    lda vertices,x
    sta vx
    lda vertices+1,x
    sta vy
    lda vertices+2,x
    sta vz
    lda vx
    ldx cy
    jsr fixedMultiply
    sta temp
    lda vz
    ldx sy
    jsr fixedMultiply
    clc
    adc temp
    sta rx
    lda vz
    ldx cy
    jsr fixedMultiply
    sta temp
    lda vx
    ldx sy
    jsr fixedMultiply
    sta rz
    lda temp
    sec
    sbc rz
    sta rz
    lda vy
    ldx cp
    jsr fixedMultiply
    sta temp
    lda rz
    ldx sp
    jsr fixedMultiply
    sta ry
    lda temp
    sec
    sbc ry
    sta ry
    lda rz
    ldx cp
    jsr fixedMultiply
    sta temp
    lda vy
    ldx sp
    jsr fixedMultiply
    clc
    adc temp
    sta zz
    clc
    adc #96
    sta depth
    ldx vertexIndex
    lda rx
    sta rotated,x
    lda ry
    sta rotated+1,x
    lda zz
    sta rotated+2,x
    lda rx
    jsr perspective
    clc
    adc #160
    ldx outputIndex
    sta result,x
    lda ry
    jsr perspective
    clc
    adc #100
    ldx outputIndex
    sta result+1,x
    inc outputIndex
    inc outputIndex
    clc
    lda vertexIndex
    adc #3
    sta vertexIndex
    cmp #24
    beq !complete+
    jmp nextVertex
!complete:
    lda inputPhase
    sta result+16
    lda #0
    ldx #16
!sum:
    eor result,x
    dex
    bpl !sum-
    sta result+17
    lda #$a5
    sta result+18
driveCalcDone:
    ldx #31
!restore:
    lda savedZeroPage,x
    sta $80,x
    dex
    bpl !restore-
    pla
    tay
    pla
    tax
    pla
    plp
driveReturn:
    rts

// A,X signed. Multiply absolute values, keep sign separately.
multiply:
    sta operandA
    stx operandB
    eor operandB
    and #$80
    sta negative
    lda operandA
    bpl !apos+
    eor #$ff
    clc
    adc #1
!apos:
    sta multiplicand
    lda #0
    sta multiplicand+1
    sta product
    sta product+1
    lda operandB
    bpl !bpos+
    eor #$ff
    clc
    adc #1
!bpos:
    sta multiplier
    lda #8
    sta bits
!bit:
    lsr multiplier
    bcc !noadd+
    clc
    lda product
    adc multiplicand
    sta product
    lda product+1
    adc multiplicand+1
    sta product+1
!noadd:
    asl multiplicand
    rol multiplicand+1
    dec bits
    bne !bit-
    rts
fixedMultiply:
    jsr multiply
    ldx #6
!scale:
    lsr product+1
    ror product
    dex
    bne !scale-
    lda product
applySign:
    bit negative
    bpl !positive+
    eor #$ff
    clc
    adc #1
!positive:
    rts
perspective:
    ldx #80
    jsr multiply
    lda #0
    sta quotient
!divide:
    lda product+1
    bne !subtract+
    lda product
    cmp depth
    bcc !finish+
!subtract:
    sec
    lda product
    sbc depth
    sta product
    lda product+1
    sbc #0
    sta product+1
    inc quotient
    bne !divide-
!finish:
    lda quotient
    jmp applySign

sine: .fill 16, round(64*sin(2*PI*i/16))
cosine: .fill 16, round(64*cos(2*PI*i/16))
vertices:
    .byte -20,-20,-20, 20,-20,-20, 20,20,-20, -20,20,-20
    .byte -20,-20,20, 20,-20,20, 20,20,20, -20,20,20
.errorif *>$0700, "Drive code must leave input/result/scratch space"
*=$0700 "Protocol and preserved scratch"
inputPhase: .byte 0
*=$0710
result: .fill 19,0
*=$0740
rotated: .fill 24,0
*=$0780
savedZeroPage: .fill 32,0
*=$07ff
.byte 0
