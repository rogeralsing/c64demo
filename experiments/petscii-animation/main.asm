// Original prepared PETSCII player. No RAM charset: VIC reads its real ROM.
.const source = $02
.const destination = $04
.const match = $06
.const colorSource = $08
.const count = $0a

* = $0801 "BASIC"
.byte $0b,$08,$01,$00,$9e
.text "4096"
.byte 0,0,0

* = $1000 "Player (CPU RAM beneath VIC character ROM)"
start:
    sei
    lda #$7f
    sta $dc0d
    sta $dd0d
    lda $dc0d
    lda $dd0d
    lda #$35
    sta $01
    lda #0
    sta $d011
    sta $d015
    sta $d020
    sta $d021
    sta $d01b
    sta $d01c
    sta $d01d
    lda #3
    sta $dd02
    sta $dd00
    lda #8
    sta $d016
    lda #$84
    sta $d018
    lda #0
    sta frontBuffer
    sta shownFrame
    sta nextFrame
    sta fieldCounter
    sta fieldCounter+1
    sta publications
    sta colorReady
    lda #$20
    sta destination+1
    jsr decompressFrame
    ldx #0
initialColors:
    .for (var page=0; page<4; page++) {
        lda $2400+page*$100,x
        sta $d800+page*$100,x
    }
    inx
    bne initialColors
    inc nextFrame
    lda #<irq
    sta $fffe
    lda #>irq
    sta $ffff
    lda #$1b
    sta $d011
    lda #0
    sta irqStage
    sta $d012
    lda #1
    sta $d019
    sta $d01a
ready:
    cli

next:
    lda frontBuffer
    eor #1
    sta targetBuffer
    asl
    asl
    asl
    clc
    adc #$20
    sta destination+1
    jsr decompressFrame
decoded:
    lda fieldCounter
waitUploadField:
    cmp fieldCounter
    beq waitUploadField
    lda targetBuffer
    asl
    asl
    asl
    clc
    adc #$24
    sta colorSource+1
    lda #0
    sta colorSource
    jsr uploadColors
    lda #1
    sta colorReady
waitPublication:
    lda colorReady
    bne waitPublication
    inc nextFrame
    lda nextFrame
    and #15
    sta nextFrame
    jmp next

// Standalone byte-command decoder, with legal forward-overlapping matches.
decompressFrame:
    ldx nextFrame
    lda frameLo,x
    sta source
    lda frameHi,x
    sta source+1
    lda #0
    sta destination
command:
    jsr getByte
    beq decodeDone
    bmi matchCommand
    sta count
literal:
    jsr getByte
    jsr putByte
    dec count
    bne literal
    jmp command
matchCommand:
    and #$7f
    sta count
    jsr getByte
    sta match
    lda destination
    sec
    sbc match
    sta match
    lda destination+1
    sbc #0
    sta match+1
matchByte:
    ldy #0
    lda (match),y
    jsr putByte
    inc match
    bne !+
    inc match+1
!:
    dec count
    bne matchByte
    jmp command
decodeDone:
    rts
getByte:
    ldy #0
    lda (source),y
    inc source
    bne !+
    inc source+1
!:
    cmp #0
    rts
putByte:
    ldy #0
    sta (destination),y
    inc destination
    bne !+
    inc destination+1
!:
    rts

irq:
    pha
    txa
    pha
    tya
    pha
    lda #1
    sta $d019
    lda irqStage
    bne bottom
    inc fieldCounter
    bne !+
    inc fieldCounter+1
!:
    lda colorReady
    beq retain
    lda targetBuffer
    sta frontBuffer
    lda nextFrame
    sta shownFrame
    inc publications
    lda #0
    sta colorReady
retain:
    lda frontBuffer
    asl
    asl
    asl
    asl
    asl
    ora #$84
    sta $d018
    lda #$9b
    sta $d011
    lda #34
    sta $d012
    lda #1
    sta irqStage
    jmp irqExit
bottom:
frameComplete:
    lda #$1b
    sta $d011
    lda #0
    sta $d012
    sta irqStage
irqExit:
    pla
    tay
    pla
    tax
    pla
    rti

frontBuffer: .byte 0
targetBuffer: .byte 0
shownFrame: .byte 0
nextFrame: .byte 0
publications: .byte 0
colorReady: .byte 0
fieldCounter: .word 0
irqStage: .byte 0
.assert "Player fits below screen A", * <= $2000, true

* = $2000 "Screen A + color shadow A"
.fill 2048, 0
* = $2800 "Screen B + color shadow B"
.fill 2048, 0

* = $4000 "Beam-following ColorRAM upload"
uploadColors:
    .for (var row=0; row<25; row++) {
    !wait:
        bit $d011
        bmi !passed+
        lda $d012
        cmp #59+8*row
        bcc !wait-
    !passed:
        ldy #0
        .for (var column=0; column<40; column++) {
            lda (colorSource),y
            sta $d800+row*40+column
            iny
        }
        clc
        lda colorSource
        adc #40
        sta colorSource
        bcc !+
        inc colorSource+1
    !:
    }
    rts
.assert "Upload kernel below packed artwork", * <= $6000, true

* = $6000 "Compressed original scene data"
.import source "build/frames.asm"
.assert "Packed scene does not load into I/O", * <= $d000, true
