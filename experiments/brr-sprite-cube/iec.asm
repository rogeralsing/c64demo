// Own custom IEC transport, bootstrapped through the real DOS command channel.
serviceWire:
    lda wireState
    cmp #1
    beq !send+
    cmp #2
    beq !checkReady+
    cmp #3
    beq !receive+
    rts
!checkReady:
    bit $dd00
    bmi !return+
    inc wireState
!receive:
    lda #3
    sta wireBudget
!receiveByte:
    jsr receiveByte
    ldx wireIndex
    sta wireResponse,x
    inc wireIndex
    lda wireIndex
    cmp responseLength
    bne !moreReceive+
    inc wireState
    rts
!moreReceive:
    dec wireBudget
    bne !receiveByte-
!return:
    rts
!send:
    lda #3
    sta wireBudget
!sendByte:
    ldx wireIndex
    lda wirePacket,x
    jsr sendByte
    inc wireIndex
    lda wireIndex
    cmp packetLength
    bne !moreSend+
    lda #0
    sta wireIndex
    inc wireState
    rts
!moreSend:
    dec wireBudget
    bne !sendByte-
    rts

sendByte:
    sta wireByte
    .for (var bit=0;bit<8;bit++) {
        asl wireByte
        lda #3
        bcs !one+
        ora #$20
    !one:
        sta wireOutput
        ora #$10
        sta $dd00
        jsr halfPeriod
        lda wireOutput
        sta $dd00
        jsr halfPeriod
    }
    lda #3
    sta $dd00
!ack:
    bit $dd00
    bmi !ack-
    lda #$13
    sta $dd00
!released:
    bit $dd00
    bpl !released-
    lda #3
    sta $dd00
    rts

receiveByte:
    lda #0
    sta wireByte
    .for (var bit=0;bit<8;bit++) {
        lda #$13
        sta $dd00
        jsr halfPeriod
        lda $dd00
        asl
        rol wireByte
        lda #3
        sta $dd00
        jsr halfPeriod
    }
    lda wireByte
    rts

.align $10
halfPeriod:
    // JSR6 + LDX2 + loop(4*5-1) + RTS6 =33C64cycles.
    ldx #4
!wait:
    dex
    bne !wait-
    rts

uploadDrive:
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
    lda #0
    sta writeAddress
    lda #3
    sta writeAddress+1
!block:
    ldx #15
    jsr $ffc9
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
    bne uploadFault
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
    bne !block-
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
    rts
uploadFault:
    lda #2
    sta $d020
    jmp uploadFault
