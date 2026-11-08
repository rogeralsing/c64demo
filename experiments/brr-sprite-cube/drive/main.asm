// Original1541BRR setup worker. No Boo program or selector bytes.
// Inputs: count, then (inclusiveY0,exclusiveY1,X0,X1) records.
// Results: sequence,count, then signed floor quotient and exact rank separator.
.const VIA=$1800
.const inputs=$0700
.const results=$0740
.const diagnostics=$0780
.const count=$40
.const inputIndex=$41
.const outputIndex=$42
.const first=$43
.const last=$44
.const denominator=$45
.const remainder=$46
.const quotient=$47
.const negative=$48
.const threshold=$49
.const candidate=$4a
.const rankCount=$4b
.const rankMask=$4c
.const transferByte=$4d
.const transferBits=$4e
.const recordIndex=$4f
.const stage=$02f0
.const sequence=$02f1
.const completedRequests=$02f2

*=$0300 "Own1541receive,divide,rank-select and send"
driveStart:
    sei
    cld
    ldx #$ff
    txs
    lda #$7f
    sta $180e
    sta $1c0e
    lda $180d
    lda $1c0d
    lda #$1a
    sta $1802
    lda #0
    sta VIA
    sta sequence
    sta completedRequests
nextPacket:
    lda #1
    sta stage
    lda #0
    sta VIA
    jsr receiveByte
    sta count
    asl
    asl
    sta inputIndex
    ldx #0
!receive:
    jsr receiveByte
    sta inputs,x
    inx
    cpx inputIndex
    bne !receive-
    lda #2
    sta stage
    lda #0
    sta inputIndex
    sta outputIndex
    sta recordIndex
calculationBegin:
!record:
    ldx inputIndex
    lda inputs,x
    sta first
    lda inputs+1,x
    sta last
    sec
    sbc first
    sta denominator
    lda #0
    sta negative
    sta quotient
    sec
    lda inputs+3,x
    sbc inputs+2,x
    bpl !magnitude+
    inc negative
    eor #$ff
    clc
    adc #1
!magnitude:
    sta remainder
!divide:
    lda remainder
    cmp denominator
    bcc !divided+
    sec
    sbc denominator
    sta remainder
    inc quotient
    jmp !divide-
!divided:
    lda negative
    beq !signed+
    lda quotient
    eor #$ff
    ldx remainder
    bne !fractionalNegative+
    clc
    adc #1
!fractionalNegative:
    sta quotient
    lda remainder
    beq !signed+
    sec
    lda denominator
    sbc remainder
    sta remainder
!signed:
    lda #0
    sta threshold
    lda remainder
    beq !selected+
    lda #$80
    sta rankMask
!selectBit:
    lda threshold
    ora rankMask
    sta candidate
    lda #0
    sta rankCount
    ldx first
!rank:
    lda reversal,x
    cmp candidate
    bcs !skip+
    inc rankCount
!skip:
    inx
    cpx last
    bne !rank-
    lda remainder
    cmp rankCount
    bcc !reject+
    lda candidate
    sta threshold
!reject:
    lsr rankMask
    bne !selectBit-
!selected:
    ldx outputIndex
    lda quotient
    sta results,x
    lda threshold
    sta results+1,x
    lda remainder
    sta diagnostics,x
    lda denominator
    sta diagnostics+1,x
    inc outputIndex
    inc outputIndex
    clc
    lda inputIndex
    adc #4
    sta inputIndex
    inc recordIndex
    lda recordIndex
    cmp count
    beq calculationComplete
    jmp !record-
calculationComplete:
    inc completedRequests
    inc sequence
    lda #3
    sta stage
    lda sequence
    jsr sendByte
    lda count
    jsr sendByte
    ldx #0
!send:
    lda results,x
    jsr sendByte
    inx
    cpx outputIndex
    bne !send-
    jmp nextPacket

// C64 clocks data with bounded32-cycle half-periods. The acknowledgement
// after each byte is level-handshaken and can safely span C64raster IRQs.
receiveByte:
    lda #0
    sta transferByte
    lda #8
    sta transferBits
!bit:
!low:
    lda VIA
    and #4
    beq !low-
    lda VIA
    eor #1
    lsr
    rol transferByte
!high:
    lda VIA
    and #4
    bne !high-
    dec transferBits
    bne !bit-
    lda #2
    sta VIA
!ackLow:
    lda VIA
    and #4
    beq !ackLow-
    lda #0
    sta VIA
!ackHigh:
    lda VIA
    and #4
    bne !ackHigh-
    lda transferByte
    rts

sendByte:
    sta transferByte
    lda #8
    sta transferBits
    lda #2
    sta VIA
!bit:
!low:
    lda VIA
    and #4
    beq !low-
    asl transferByte
    lda #0
    bcs !highBit+
    lda #2
!highBit:
    sta VIA
!high:
    lda VIA
    and #4
    bne !high-
    dec transferBits
    bne !bit-
    rts
.errorif *>$0600,"Drive worker overlaps reversal table"

.function Reverse(value) {
    .var result=0
    .for (var bit=0;bit<8;bit++) { .eval result=result|(((value>>bit)&1)<<(7-bit)) }
    .return result
}
*=$0600 "Reusable bit reversal, not prepared slopes"
reversal: .fill 256,Reverse(i)
*=$0700 "Live request/result buffers"
    .fill 256,0
