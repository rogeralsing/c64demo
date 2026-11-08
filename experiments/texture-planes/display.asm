// Whole-buffer publication and three-band scanout. IRQs preserve the live
// sampler registers and zero page; no renderer data changes inside an IRQ.
irq:
    pha
    txa
    pha
    tya
    pha
    jmp (irqPart)

.macro NextPart(address, line) {
    lda #<address
    sta irqPart
    lda #>address
    sta irqPart+1
    lda #line
    sta $d012
    jmp irqReturn
}

displayTop:
    inc fieldCounter
    bne !counter+
    inc fieldCounter+1
!counter:
    lda fieldParity
    eor #1
    sta fieldParity
    bne !retain+
    lda renderReady
    beq !retain+
    lda frontBuffer
    eor #1
    sta frontBuffer
    lda pendingPose
    sta frontPose
    lda #0
    sta renderReady
    inc publicationCounter
    bne !retain+
    inc publicationCounter+1
!retain:
    lda frontBuffer
    eor #$81
    sta $dd00
    lda #$e8
    sta $d018
    lda fieldParity
    clc
    adc #$1b
    sta $d011
    lda #<displayBand1
    sta irqPart
    lda #>displayBand1
    sta irqPart+1
    lda fieldParity
    clc
    adc #113
    sta $d012
    jmp irqReturn

displayBand1:
    lda fieldParity
    clc
    adc #114
!wait:
    cmp $d012
    bne !wait-
    lda #$ea
    sta $d018
    lda #<displayBand2
    sta irqPart
    lda #>displayBand2
    sta irqPart+1
    lda fieldParity
    clc
    adc #177
    sta $d012
    jmp irqReturn

displayBand2:
    lda fieldParity
    clc
    adc #178
!wait:
    cmp $d012
    bne !wait-
    lda #$ec
    sta $d018
    NextPart(displayBottom, 270-256)

displayBottom:
    // The high raster compare bit is needed only for this bottom IRQ.
    // See irqReturn: it is set after band2 has selected the next low byte.
fieldComplete:
    NextPart(displayTop,0)

irqReturn:
    lda irqPart
    cmp #<displayBottom
    bne !low+
    lda irqPart+1
    cmp #>displayBottom
    bne !low+
    lda $d011
    ora #$80
    bne !raster+
!low:
    lda $d011
    and #$7f
!raster:
    sta $d011
    lda #1
    sta $d019
    pla
    tay
    pla
    tax
    pla
nmiReturn:
    rti
