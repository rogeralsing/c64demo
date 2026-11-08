// Original audiovisual feedback teaching example inspired by A Mind Is Born.
// SID, palette and feedback share an LFSR. Cyclic PHA output and IRQ traffic
// intentionally share the stack page, which the VIC reads as ECM glyphs 32..63.

BasicUpstart2(start)

.const FEEDBACK_POINTER = $f0
.const SCREEN = $0400

* = $1000 "Coupled audiovisual state"
start:
    sei
    cld
    ldx #$ff
    txs
    lda #$7f
    sta $dc0d
    sta $dd0d
    lda $dc0d
    lda $dd0d
    lda #$35
    sta $01
    lda #3
    sta $dd00
    lda $dd02
    ora #3
    sta $dd02
    lda #$5b
    sta $d011
    lda #8
    sta $d016
    lda #$10
    sta $d018
    lda #0
    sta $d015
    sta $d020
    sta frameCounter
    sta frameCounter+1
    sta noteCounter
    lda #$41
    sta lfsr
    lda #0
    sta FEEDBACK_POINTER
    lda #4
    sta FEEDBACK_POINTER+1

    ldx #0
!initialize:
    txa
    ora #$20
    sta SCREEN,x
    sta SCREEN+$100,x
    sta SCREEN+$200,x
    sta SCREEN+$300,x
    eor #$a5
    sta $0100,x
    lda #0
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    inx
    bne !initialize-

    // A free-running timer provides live font input; its IRQ stays disabled.
    lda #$ff
    sta $dc04
    sta $dc05
    lda #$11
    sta $dc0e

    ldx #24
!initialSound:
    lda sidShadow,x
    sta $d400,x
    dex
    bpl !initialSound-
    lda #9
    sta $d021
    lda #8
    sta $d022
    lda #10
    sta $d023
    lda #8
    sta $d024

    lda #<irq
    sta $fffe
    lda #>irq
    sta $ffff
    lda #<nmiReturn
    sta $fffa
    lda #>nmiReturn
    sta $fffb
    lda #250
    sta $d012
    lda #1
    sta $d019
    sta $d01a
    cli

// No JSR/RTS path is active here: the stack is a cyclic image stream. IRQ entry
// and its balanced register saves can safely interrupt it, leaving visible bytes.
feedback:
    lda $dc04
    sta timerSample
    lda $d41c
    sta envelopeSample
    lda lfsr
    sta lfsrSample
    lda timerSample
    eor lfsrSample
    ora envelopeSample
beforeFontPush:
    pha
afterFontPush:
    ldy #0
    lda (FEEDBACK_POINTER),y
    sta neighborA
    iny
    lda (FEEDBACK_POINTER),y
    sta neighborB
    lda neighborA
    clc
    adc neighborB
    ror
    eor lfsrSample
    ora #$20
    ldy #0
    sta (FEEDBACK_POINTER),y
    inc FEEDBACK_POINTER
    bne !checkEnd+
    inc FEEDBACK_POINTER+1
!checkEnd:
    lda FEEDBACK_POINTER+1
    cmp #7
    bne feedback
    lda FEEDBACK_POINTER
    cmp #$e8
    bne feedback
    lda #0
    sta FEEDBACK_POINTER
    lda #4
    sta FEEDBACK_POINTER+1
    jmp feedback

irq:
    pha
    txa
    pha
    tya
    pha
    inc frameCounter
    bne !clockReady+
    inc frameCounter+1
!clockReady:
    lda frameCounter
    and #7
    bne !notBeat+
    lda lfsr
    lsr
    bcc !storeLfsr+
    eor #$b8
!storeLfsr:
    sta lfsr
    inc noteCounter
    and #7
    tax
    lda melodyLow,x
    sta sidShadow
    lda melodyHigh,x
    sta sidShadow+1
    lda #$40
    sta sidShadow+4
    lda #$81
    sta sidShadow+18
    lda frameCounter
    lsr
    lsr
    lsr
    and #$0f
    clc
    adc #$20
    sta sidShadow+15
    jmp !beatDone+
!notBeat:
    lda #$41
    sta sidShadow+4
    lda #$80
    sta sidShadow+18
!beatDone:
    lda frameCounter
    and #31
    bne !bassDone+
    lda lfsr
    and #3
    tax
    lda bassLow,x
    sta sidShadow+7
    lda bassHigh,x
    sta sidShadow+8
!bassDone:
    lda lfsr
    sta sidShadow+2
    lsr
    lsr
    lsr
    lsr
    lsr
    ora #8
    sta sidShadow+3

    // The same melody state determines bright ECM background choices.
    lda lfsr
    and #7
    ora #8
    sta paletteShadow
    sta $d021
    lda lfsr
    lsr
    lsr
    lsr
    and #7
    ora #8
    sta paletteShadow+1
    sta $d022
    lda lfsr
    lsr
    lsr
    lsr
    lsr
    lsr
    ora #8
    sta paletteShadow+2
    sta $d023
    lda lfsr
    eor frameCounter
    and #7
    ora #8
    sta paletteShadow+3
    sta $d024

    ldx #24
!sound:
    lda sidShadow,x
sidStore:
    sta $d400,x
    dex
    bpl !sound-
frameComplete:
    lda #1
    sta $d019
    pla
    tay
    pla
    tax
    pla
nmiReturn:
    rti

frameCounter: .word 0
noteCounter: .byte 0
lfsr: .byte $41
timerSample: .byte 0
envelopeSample: .byte 0
lfsrSample: .byte 0
neighborA: .byte 0
neighborB: .byte 0
paletteShadow: .byte 9,8,10,8

melodyLow: .byte <$08b4,<$09c4,<$0af6,<$0d09,<$0ea1,<$1168,<$1388,<$15ec
melodyHigh: .byte >$08b4,>$09c4,>$0af6,>$0d09,>$0ea1,>$1168,>$1388,>$15ec
bassLow: .byte <$045a,<$0684,<$0750,<$05d0
bassHigh: .byte >$045a,>$0684,>$0750,>$05d0

// Three audible voices: gated pulse melody, triangle bass and a noise drum.
// A/D and S/R bytes are ordinary SID envelopes; volume remains fifteen.
sidShadow:
    .byte $c4,$09,$41,$0a,$41,$25,$88
    .byte $84,$06,$00,$08,$11,$08,$88
    .byte $00,$30,$00,$08,$80,$05,$00
    .byte $00,$00,$00,$0f
