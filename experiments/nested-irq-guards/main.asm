// Original per-call-site nested IRQ guards. Both sites call the same long
// routine, whose working registers are preserved by every nested IRQ frame.
BasicUpstart2(start)
start:
    sei
    ldx #$ff
    txs
    lda #$35
    sta $01
    lda #$7f
    sta $dc0d
    sta $dd0d
    lda $dc0d
    lda $dd0d
    lda #3
    sta $dd00
    sta $dd02
    lda #$1b
    sta $d011
    lda #8
    sta $d016
    lda #$18
    sta $d018
    lda #0
    sta $d015
    sta $d020
    sta $d021
    sta slot
    sta frameCounter
    sta frameCounter+1
    sta fastJobs
    sta fastJobs+1
    sta activeDepth
    sta maximumDepth
    ldx #0
!clear:
    sta starts,x
    inx
    cpx #12
    bne !clear-
    ldx #0
!screen:
    .for (var page=0; page<4; page++) {
        lda screenSource+page*256,x
        sta $0400+page*256,x
        lda #15
        sta $d800+page*256,x
    }
    inx
    bne !screen-
    lda #<nmi
    sta $fffa
    lda #>nmi
    sta $fffb
    lda #<irq
    sta $fffe
    lda #>irq
    sta $ffff
    lda #32
    sta $d012
    lda #1
    sta $d019
    sta $d01a
    cli
idle:
    jmp idle

irq:
    pha
    txa
    pha
    tya
    pha
    lda #1
    sta $d019
    ldx slot
    bne !notFirst+
frameTick:
    inc frameCounter
    bne !notFirst+
    inc frameCounter+1
!notFirst:
    lda slotColors,x
    sta $d020
    lda nextRaster,x
    sta $d012
    txa
    and #1
    sta site
    inx
    cpx #7
    bne !slot+
    ldx #0
!slot:
    stx slot
    jsr fastJob
    lda site
    bne guardOne

// Two separate literal flags model two macro expansions. A flag protects
// this call site only: the other site may enter the same routine concurrently.
guardZero:
    lda #0
    bne skipZero
    inc guardZero+1
    ldx #0
    cli
    jsr longWorker
    sei
    dec guardZero+1
    inc finishes
    bne siteZeroCompleted
    inc finishesHi
siteZeroCompleted:
    jmp irqReturn
skipZero:
    inc skips
    bne irqReturn
    inc skipsHi
    jmp irqReturn
guardOne:
    lda #0
    bne skipOne
    inc guardOne+1
    ldx #1
    cli
    jsr longWorker
    sei
    dec guardOne+1
    inc finishes+1
    bne siteOneCompleted
    inc finishesHi+1
siteOneCompleted:
    jmp irqReturn
skipOne:
    inc skips+1
    bne irqReturn
    inc skipsHi+1
irqReturn:
    pla
    tay
    pla
    tax
    pla
nmi:
    rti

longWorker:
    sei
    inc starts,x
    bne !started+
    inc startsHi,x
!started:
    inc activeDepth
    lda activeDepth
    cmp maximumDepth
    bcc !depth+
    sta maximumDepth
!depth:
    cli
workStarted:
    ldy #9
!outer:
    lda #255
!inner:
    sec
    sbc #1
    bne !inner-
    dey
    bne !outer-
    sei
    dec activeDepth
    rts

// This job runs on every IRQ, including IRQs that skip a busy call site.
// It executes with I set, so each displayed counter snapshot is consistent.
fastJob:
    inc fastJobs
    bne !counted+
    inc fastJobs+1
!counted:
    // Update the whole status matrix once per field, before its text rows.
    // The counter itself still advances on every IRQ.
    lda slot
    cmp #1
    beq !display+
    rts
!display:
    .for (var i=0; i<2; i++) {
        lda startsHi+i
        ldx #<(6*40+i*80+8)
        ldy #>(6*40+i*80+8+$0400)
        jsr writeHex
        lda starts+i
        ldx #<(6*40+i*80+10)
        ldy #>(6*40+i*80+10+$0400)
        jsr writeHex
        lda finishesHi+i
        ldx #<(6*40+i*80+17)
        ldy #>(6*40+i*80+17+$0400)
        jsr writeHex
        lda finishes+i
        ldx #<(6*40+i*80+19)
        ldy #>(6*40+i*80+19+$0400)
        jsr writeHex
        lda skipsHi+i
        ldx #<(6*40+i*80+26)
        ldy #>(6*40+i*80+26+$0400)
        jsr writeHex
        lda skips+i
        ldx #<(6*40+i*80+28)
        ldy #>(6*40+i*80+28+$0400)
        jsr writeHex
    }
    lda activeDepth
    clc
    adc #48
    sta $0400+11*40+14
    lda maximumDepth
    clc
    adc #48
    sta $0400+11*40+27
    lda fastJobs+1
    ldx #<(20*40+10)
    ldy #>(20*40+10+$0400)
    jsr writeHex
    lda fastJobs
    ldx #<(20*40+12)
    ldy #>(20*40+12+$0400)
    jsr writeHex
    lda frameCounter+1
    ldx #<(20*40+24)
    ldy #>(20*40+24+$0400)
    jsr writeHex
    lda frameCounter
    ldx #<(20*40+26)
    ldy #>(20*40+26+$0400)
    jsr writeHex
    rts

writeHex:
    stx hexStore+1
    sty hexStore+2
    pha
    lsr
    lsr
    lsr
    lsr
    tax
    lda digits,x
hexStore:
    sta $0400
    inc hexStore+1
    bne !address+
    inc hexStore+2
!address:
    pla
    and #15
    tax
    lda hexStore+1
    sta hexStoreSecond+1
    lda hexStore+2
    sta hexStoreSecond+2
    lda digits,x
hexStoreSecond:
    sta $0401
    rts

slot: .byte 0
site: .byte 0
activeDepth: .byte 0
maximumDepth: .byte 0
frameCounter: .word 0
fastJobs: .word 0
starts: .byte 0,0
startsHi: .byte 0,0
finishes: .byte 0,0
finishesHi: .byte 0,0
skips: .byte 0,0
skipsHi: .byte 0,0
nextRaster: .byte 64,96,128,160,192,224,32
slotColors: .byte 6,14,3,5,13,7,10
digits: .text "0123456789ABCDEF"
.errorif * > $2000, "Code overlaps status font"
* = $2000 "Original status font"
.import binary "build/font.bin"
* = $3000 "Original initial screen"
screenSource: .import binary "build/screen.bin"
