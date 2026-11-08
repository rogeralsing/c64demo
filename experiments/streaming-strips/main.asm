// Twenty real IEC file loads feed four resident slots; IRQ music stays separate.
.label source = $f0
.label destination = $f2
.label stripSource = $f4
.label temporary = $f6

BasicUpstart2(start)

start:
    sei
    lda #$37
    sta $01
    lda #0
    jsr $ff90
    lda #$7f
    sta $dc0d
    sta $dd0d
    lda $dc0d
    lda $dd0d
    lda #0
    sta $d01a
    sta $d015
    sta $d020
    sta $d021
    lda $dd02
    ora #3
    sta $dd02
    lda #3
    sta $dd00
    lda #$3b
    sta $d011
    lda #$18
    sta $d016
    sta $d018

    ldx #0
!initial:
    .for (var page=0; page<31; page++) {
        lda initialBitmap+page*256,x
        sta $2000+page*256,x
    }
    .for (var page=0; page<3; page++) {
        lda initialScreen+page*256,x
        sta $0400+page*256,x
        lda initialColors+page*256,x
        sta $d800+page*256,x
    }
    inx
    beq !initialDone+
    jmp !initial-
!initialDone:
    ldx #0
!lastBitmap:
    lda initialBitmap+7936,x
    sta $3f00,x
    inx
    cpx #64
    bne !lastBitmap-
    ldx #0
!lastAttributes:
    lda initialScreen+768,x
    sta $0700,x
    lda initialColors+768,x
    sta $db00,x
    inx
    cpx #232
    bne !lastAttributes-

    ldx #0
    lda #$cc
!emptySlots:
    .for (var page=0; page<32; page++) { sta $8000+page*256,x }
    inx
    bne !emptySlots-
    lda #<irq
    sta $0314
    lda #>irq
    sta $0315
    lda #0
    sta $d012
    lda #1
    sta $d019
    sta $d01a
    lda #$09
    sta $d405
    lda #$a8
    sta $d406
    lda #$21
    sta $d404
    lda #8
    sta $d418
    cli

!prefill:
    jsr loadNext
    lda loadIndex
    cmp #4
    bne !prefill-
    jsr scheduleMusic

nextStrip:
    jsr waitMusic
    lda consumeIndex
    and #3
    tax
    stx currentSlot
    lda slotStates,x
    cmp #2
    beq !ready+
    jmp notReady
!ready:
    lda slotIds,x
    cmp consumeIndex
    beq !correct+
    jmp wrongStrip
!correct:
    lda #3
    sta slotStates,x
consumeBegin:
    jsr prepareViewport
!waitHigh:
    bit $d011
    bpl !waitHigh-
!waitLow:
    bit $d011
    bmi !waitLow-
    lda backD018
    sta $d018
    lda backBank
    sta $dd00
    .for (var pair=0; pair<4; pair++) {
        lda frontSettings+pair
        ldx backSettings+pair
        stx frontSettings+pair
        sta backSettings+pair
    }
!scanout:
    bit $d011
    bpl !scanout-
    inc consumedCount
stripPresented:
    ldx currentSlot
    lda #0
    sta slotStates,x
slotReleased:
    inc consumeIndex
    lda consumeIndex
    cmp #20
    bne !more+
    jmp finishStream
!more:
    jsr scheduleMusic
    lda loadIndex
    cmp #20
    bne !load+
    jmp nextStrip
!load:
    jsr loadNext
    jmp nextStrip

notReady:
    lda #$81
    jmp failed
wrongStrip:
    lda #$82
    jmp failed

loadNext:
    lda loadIndex
    sta loadedStripId
    and #3
    tax
    stx loadingSlot
    lda slotStates,x
    beq !free+
    lda #$80
    jmp failed
!free:
    lda #1
    sta slotStates,x
    lda #0
    sta irqDuringLoad
    sta irqDuringLoad+1
    lda #1
    sta loadActive
    lda loadIndex
    ldx #$30
    cmp #10
    bcc !name+
    sec
    sbc #10
    inx
!name:
    stx filename
    clc
    adc #$30
    sta filename+1
    lda #2
    ldx #<filename
    ldy #>filename
    jsr $ffbd
    lda #1
    ldx #8
    ldy #0
    jsr $ffba
    ldx loadingSlot
    lda slotHigh,x
    tay
    ldx #0
    lda #0
loadStarted:
    jsr $ffd5
loadReturned:
    bcc !loaded+
    jmp failed
!loaded:
    stx loadedEnd
    sty loadedEnd+1
    cpx #$d0
    bne badLength
    ldx loadingSlot
    lda slotHigh,x
    clc
    adc #7
    cmp loadedEnd+1
    bne badLength
    lda loadedStripId
    sta slotIds,x
    lda #2
    sta slotStates,x
    lda #0
    sta loadActive
loadComplete:
    inc loadIndex
    rts
badLength:
    lda #$83
failed:
    sta errorCode
    lda #$ff
    sta stage
fault:
    jmp fault

scheduleMusic:
    // Briefly mask IRQs so a line-zero wrap cannot split the low/high read.
!border:
    bit $d011
    bpl !border-
    php
    sei
    lda musicCounter
    clc
    adc #24
    sta musicTarget
    lda musicCounter+1
    adc #0
    sta musicTarget+1
    plp
    rts

waitMusic:
!border:
    bit $d011
    bpl !border-
    // Ordinary unsigned 16-bit low-compare/high-subtract handshake.
    php
    sei
    lda musicCounter
    cmp musicTarget
    lda musicCounter+1
    sbc musicTarget+1
    bcc !again+
    plp
    rts
!again:
    plp
    jmp !border-

prepareViewport:
    lda #0
    sta tileRow
!row:
    ldx tileRow
    lda bitmapRowsLo,x
    clc
    adc #64
    sta source
    lda bitmapRowsHi,x
    adc frontBitmapHi
    sta source+1
    lda bitmapRowsLo,x
    sta destination
    lda bitmapRowsHi,x
    clc
    adc backBitmapHi
    sta destination+1
    ldy #0
!shiftBitmap:
    lda (source),y
    sta (destination),y
    iny
    bne !shiftBitmap-
    inc destination+1
    lda stripBitmapLo,x
    sta stripSource
    lda stripBitmapHi,x
    ldx currentSlot
    clc
    adc slotHigh,x
    sta stripSource+1
    ldy #0
!appendBitmap:
    lda (stripSource),y
    sta (destination),y
    iny
    cpy #64
    bne !appendBitmap-

    ldx tileRow
    lda screenRowsLo,x
    clc
    adc #8
    sta source
    lda screenRowsHi,x
    adc frontScreenHi
    sta source+1
    lda screenRowsLo,x
    sta destination
    lda screenRowsHi,x
    clc
    adc backScreenHi
    sta destination+1
    ldy #0
!shiftScreen:
    lda (source),y
    sta (destination),y
    iny
    cpy #32
    bne !shiftScreen-
    lda stripScreenLo,x
    sta stripSource
    lda stripScreenHi,x
    ldx currentSlot
    clc
    adc slotHigh,x
    sta stripSource+1
    jsr appendAttributes

    ldx tileRow
    lda screenRowsLo,x
    clc
    adc #8
    sta source
    lda screenRowsHi,x
    adc #$d8
    sta source+1
    lda screenRowsLo,x
    sta destination
    lda screenRowsHi,x
    clc
    adc #$d8
    sta destination+1
    ldy #0
!shiftColors:
    lda (source),y
    sta (destination),y
    iny
    cpy #32
    bne !shiftColors-
    lda stripColorLo,x
    sta stripSource
    lda stripColorHi,x
    ldx currentSlot
    clc
    adc slotHigh,x
    sta stripSource+1
    jsr appendAttributes
    inc tileRow
    lda tileRow
    cmp #25
    beq !done+
    jmp !row-
!done:
    rts

appendAttributes:
    ldx #0
!byte:
    txa
    tay
    lda (stripSource),y
    sta temporary
    txa
    clc
    adc #32
    tay
    lda temporary
    sta (destination),y
    inx
    cpx #8
    bne !byte-
    rts

finishStream:
    lda #1
    sta stage
    jsr scheduleMusic
    jsr waitMusic
    // Prepare the inactive bank completely before publishing text mode.
    // Character ROM is visible to the CPU only while I/O is banked out.
    sei
    lda #$33
    sta $01
    ldx #0
!font:
    .for (var page=0; page<8; page++) {
        lda $d000+page*256,x
        sta $4000+page*256,x
    }
    inx
    bne !font-
    lda #$37
    sta $01
    cli
    ldx #0
!text:
    lda #32
    sta $5c00,x
    sta $5d00,x
    sta $5e00,x
    sta $5f00,x
    inx
    bne !text-
    ldx #14
!title:
    lda title,x
    sta $5d9c,x
    dex
    bpl !title-
    ldx #15
!subtitle:
    lda subtitle,x
    sta $5dec,x
    dex
    bpl !subtitle-
!waitHigh:
    bit $d011
    bpl !waitHigh-
!waitLow:
    bit $d011
    bmi !waitLow-
    lda #2
    sta $dd00
    lda #$1b
    sta $d011
    lda #8
    sta $d016
    lda #$70
    sta $d018
    lda #2
    sta stage
textPublished:
!scanout:
    bit $d011
    bpl !scanout-
firstTextFieldComplete:
finalScene:
    jmp finalScene

irq:
    lda $d019
    and #1
    beq !other+
    lda #1
    sta $d019
    jsr playMusic
    inc musicCounter
    bne !counter+
    inc musicCounter+1
!counter:
    lda loadActive
    beq !border+
    inc irqDuringLoad
    bne !border+
    inc irqDuringLoad+1
!border:
    lda stage
    cmp #$ff
    beq !red+
    lda musicCounter
    lsr
    lsr
    lsr
    and #7
    tax
    lda borderColors,x
    sta $d020
    jmp !other+
!red:
    lda #2
    sta $d020
!other:
    lda $dc0d
    jmp $ea81

playMusic:
    lda musicCounter
    and #7
    bne !done+
    lda musicCounter
    lsr
    lsr
    lsr
    and #7
    tax
    lda noteLow,x
    sta $d400
    lda noteHigh,x
    sta $d401
!done:
    rts

frontSettings:
frontBitmapHi: .byte $20
frontScreenHi: .byte $04
frontBank: .byte 3
frontD018: .byte $18
backSettings:
backBitmapHi: .byte $60
backScreenHi: .byte $5c
backBank: .byte 2
backD018: .byte $78
loadIndex: .byte 0
consumeIndex: .byte 0
consumedCount: .byte 0
loadedStripId: .byte 0
loadingSlot: .byte 0
currentSlot: .byte 0
loadedEnd: .word 0
loadActive: .byte 0
stage: .byte 0
errorCode: .byte 0
tileRow: .byte 0
musicCounter: .word 0
musicTarget: .word 0
irqDuringLoad: .word 0
slotStates: .fill 4,0
slotIds: .fill 4,$ff
slotHigh: .byte $80,$88,$90,$98
filename: .text "00"
bitmapRowsLo: .fill 25, <(i*320)
bitmapRowsHi: .fill 25, >(i*320)
screenRowsLo: .fill 25, <(i*40)
screenRowsHi: .fill 25, >(i*40)
stripBitmapLo: .fill 25, <(i*64)
stripBitmapHi: .fill 25, >(i*64)
stripScreenLo: .fill 25, <(1600+i*8)
stripScreenHi: .fill 25, >(1600+i*8)
stripColorLo: .fill 25, <(1800+i*8)
stripColorHi: .fill 25, >(1800+i*8)
borderColors: .byte 6,4,3,14,3,4,6,0
noteLow: .byte $68,$d6,$60,$d6,$68,$43,$60,$3a
noteHigh: .byte $11,$15,$1a,$15,$11,$0e,$1a,$23
title: .byte 19,20,18,5,1,13,32,3,15,13,16,12,5,20,5
subtitle: .byte 50,48,32,19,20,18,9,16,19,32,12,15,1,4,5,4
.errorif * > $2000, "Runtime code overlaps bitmap A"

* = $4000 "Initial 320-pixel viewport only"
initialBitmap:
    .import binary "build/initial.bin"
.label initialScreen = initialBitmap+8000
.label initialColors = initialScreen+1000
.assert "Initial viewport has bitmap and both attributes", *, initialBitmap+10000
