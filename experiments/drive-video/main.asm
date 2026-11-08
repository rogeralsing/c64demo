// C64 bootstraps our drive program through the real DOS command channel.
// After M-E, it releases its IEC outputs; the1541 owns video generation.
.label uploadPointer = $fb
.var drive = LoadBinary("drive/build/example.prg")
.const DRIVE_BYTES = drive.getSize()-2
.errorif mod(DRIVE_BYTES,32)!=0, "Drive upload needs complete32-byte packets"

BasicUpstart2(start)
start:
    lda #$37
    sta $01
    lda #0
    sta $d020
    sta $d021
    jsr $e544
    ldx #0
!title:
    lda title,x
    beq !open+
    sta $0400+2*40+5,x
    lda #1
    sta $d800+2*40+5,x
    inx
    bne !title-
!open:
    lda #0
    jsr $ffbd
    lda #15
    ldx #8
    ldy #15
    jsr $ffba
    jsr $ffc0
    bcc !opened+
    jmp uploadFault
!opened:
    lda #<drivePayload
    sta uploadPointer
    lda #>drivePayload
    sta uploadPointer+1
    lda #DRIVE_BYTES/32
    sta blocksRemaining
    lda #$00
    sta writeAddress
    lda #$03
    sta writeAddress+1

uploadBlock:
    ldx #15
    jsr $ffc9
    bcc !selected+
    jmp uploadFault
!selected:
    ldx #0
!header:
    lda writeCommand,x
    jsr $ffd2
    inx
    cpx #3
    bne !header-
    lda writeAddress
    jsr $ffd2
    lda writeAddress+1
    jsr $ffd2
    lda #32
    jsr $ffd2
    ldy #0
!bytes:
    lda (uploadPointer),y
    jsr $ffd2
    iny
    cpy #32
    bne !bytes-
    jsr $ffcc
    jsr $ffb7
    and #$80
    beq !status+
    jmp uploadFault
!status:
    clc
    lda uploadPointer
    adc #32
    sta uploadPointer
    bcc !source+
    inc uploadPointer+1
!source:
    clc
    lda writeAddress
    adc #32
    sta writeAddress
    bcc !target+
    inc writeAddress+1
!target:
    dec blocksRemaining
    bne uploadBlock

    ldx #15
    jsr $ffc9
    ldx #0
!execute:
    lda executeCommand,x
    jsr $ffd2
    inx
    cpx #5
    bne !execute-
    jsr $ffcc
    sei
    lda $dd00
    and #$c7
    sta $dd00
driveRunning:
    lda #5
    sta $d020
    jmp driveRunning

uploadFault:
    jsr $ffcc
    sei
    lda #2
    sta $d020
faultIdle:
    jmp faultIdle

blocksRemaining: .byte 0
writeAddress: .word $0300
writeCommand: .text "M-W"
executeCommand: .text "M-E"
    .word $0300
title:
    .encoding "screencode_mixed"
    .text "1541 video - drive owns signal"
    .byte 0
drivePayload:
    .fill DRIVE_BYTES, drive.get(i+2)
