// Own educational Drivecalc/PREPLINE pipeline, using real DOS commands.
.var drive=LoadBinary("drive/build/example.prg")
.const DRIVE_BYTES=drive.getSize()-2
.label uploadPointer=$fb
.label codePointer=$f9
.label bitmapPointer=$f7
.label clearPointer=$f5
BasicUpstart2(start)
start:
    sei
    lda #$36
    sta $01
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
    lda #1
    sta $cc
    lda #$3b
    sta $d011
    lda #$08
    sta $d016
    lda #$18
    sta $d018
    lda $dd00
    and #$fc
    ora #3
    sta $dd00
    ldx #0
!matrices:
    lda #$10
    sta $0400,x
    sta $0500,x
    sta $0600,x
    sta $0700,x
    sta $4400,x
    sta $4500,x
    sta $4600,x
    sta $4700,x
    inx
    bne !matrices-
    lda #$20
    sta clearPointer+1
    jsr clearBitmap
    lda #$60
    sta clearPointer+1
    jsr clearBitmap
    lda #0
    jsr $ffbd
    lda #15
    ldx #8
    ldy #15
    jsr $ffba
    jsr $ffc0
    bcc !opened+
    jmp fault
!opened:
    lda #<drivePayload
    sta uploadPointer
    lda #>drivePayload
    sta uploadPointer+1
    lda #DRIVE_BYTES/32
    sta blocksRemaining
uploadBlock:
    jsr selectOutput
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
    jsr commandEnd
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
uploadComplete:
    nop
requestStart:
    // Only phase goes to the drive: it owns all rotation and projection.
    jsr selectOutput
    ldx #0
!phaseHeader:
    lda phaseCommand,x
    jsr $ffd2
    inx
    cpx #6
    bne !phaseHeader-
    lda phase
    jsr $ffd2
    jsr commandEnd
    jsr selectOutput
    ldx #0
!execute:
    lda executeCommand,x
    jsr $ffd2
    inx
    cpx #5
    bne !execute-
    jsr commandEnd
requestSent:
    jsr selectOutput
    ldx #0
!readHeader:
    lda readCommand,x
    jsr $ffd2
    inx
    cpx #6
    bne !readHeader-
    jsr commandEnd
    ldx #15
    jsr $ffc6
    bcc !input+
    jmp fault
!input:
    ldx #0
!read:
    jsr $ffcf
    sta packet,x
    inx
    cpx #19
    bne !read-
    jsr $ffcc
    lda packet+18
    cmp #$a5
    beq !marker+
    jmp fault
!marker:
    lda packet+16
    cmp phase
    beq !echo+
    jmp fault
!echo:
    ldx #16
    lda #0
!sum:
    eor packet,x
    dex
    bpl !sum-
    cmp packet+17
    beq coordinatesReady
    jmp fault
coordinatesReady:
    lda displayBank
    eor #1
    sta drawBank
    tax
    lda bitmapHigh,x
    sta clearPointer+1
clearStart:
    jsr clearBitmap
clearDone:
    lda #<$8000
    sta codePointer
    lda #>$8000
    sta codePointer+1
    lda #0
    sta edgeIndex
    sta pixelCount
    sta pixelCount+1
generateStart:
    jsr PREPLINE
generateDone:
    nop
executeStart:
    jsr $8000
executeDone:
    jsr waitBottom
    lda drawBank
    sta displayBank
    tax
    lda $dd00
    and #$fc
    ora bankBits,x
    sta $dd00
    lda phase
    sta shownPhase
bankPublished:
    jsr waitBottom
framePresented:
    inc presentations
    inc phase
    lda phase
    and #15
    sta phase
    jmp requestStart

selectOutput:
    ldx #15
    jsr $ffc9
    bcc !ok+
    jmp fault
!ok:
    rts
commandEnd:
    jsr $ffcc
    jsr $ffb7
    and #$80
    beq !ok+
    jmp fault
!ok:
    rts
clearBitmap:
    lda #0
    sta clearPointer
    ldx #32
    ldy #0
!clear:
    sta (clearPointer),y
    iny
    bne !clear-
    inc clearPointer+1
    dex
    bne !clear-
    rts
waitBottom:
!high:
    bit $d011
    bpl !high-
!low:
    bit $d011
    bmi !low-
!bottom:
    lda $d012
    cmp #252
    bne !bottom-
    rts

// PREPLINE emits LDA abs / ORA #mask / STA abs for every sampled edge pixel.
// C64 rendering uses only received XY pairs. Its embedded drive payload is
// uploaded unchanged, and all 3D arithmetic executes on the drive CPU.
PREPLINE:
    ldx edgeIndex
    lda edgeFrom,x
    tax
    lda packet,x
    sta lineX
    lda packet+1,x
    sta lineY
    ldx edgeIndex
    lda edgeTo,x
    tax
    lda packet,x
    sec
    sbc lineX
    ldx #1
    bcs !dx+
    eor #$ff
    clc
    adc #1
    ldx #$ff
!dx:
    stx signX
    sta deltaX
    ldx edgeIndex
    lda edgeTo,x
    tax
    lda packet+1,x
    sec
    sbc lineY
    ldx #1
    bcs !dy+
    eor #$ff
    clc
    adc #1
    ldx #$ff
!dy:
    stx signY
    sta deltaY
    cmp deltaX
    bcs !major+
    lda deltaX
!major:
    sta steps
    sta remaining
    lsr
    sta errorX
    sta errorY
!pixel:
    jsr emitPixel
    lda remaining
    beq !next+
    dec remaining
    clc
    lda errorX
    adc deltaX
    cmp steps
    bcc !xstill+
    sbc steps
    sta errorX
    clc
    lda lineX
    adc signX
    sta lineX
    jmp !ystep+
!xstill:
    sta errorX
!ystep:
    clc
    lda errorY
    adc deltaY
    cmp steps
    bcc !ystill+
    sbc steps
    sta errorY
    clc
    lda lineY
    adc signY
    sta lineY
    jmp !pixel-
!ystill:
    sta errorY
    jmp !pixel-
!next:
    inc edgeIndex
    lda edgeIndex
    cmp #12
    beq !finish+
    jmp PREPLINE
!finish:
    lda codePointer+1
    cmp #$c0
    bcc !terminator+
    jmp capacityStopped
!terminator:
    ldy #0
    lda #$60
    sta (codePointer),y
    rts
emitPixel:
    lda codePointer+1
    cmp #$c0
    bcc !capacity+
    jmp capacityStopped
!capacity:
    ldx lineY
    lda rowLow,x
    sta bitmapPointer
    lda rowHigh,x
    ldx drawBank
    clc
    adc bankDelta,x
    sta bitmapPointer+1
    lda lineX
    and #$f8
    clc
    adc bitmapPointer
    sta bitmapPointer
    bcc !address+
    inc bitmapPointer+1
!address:
    lda lineX
    and #7
    tax
    lda masks,x
    sta pixelMask
    ldy #0
    lda #$ad
    sta (codePointer),y
    iny
    lda bitmapPointer
    sta (codePointer),y
    iny
    lda bitmapPointer+1
    sta (codePointer),y
    iny
    lda #$09
    sta (codePointer),y
    iny
    lda pixelMask
    sta (codePointer),y
    iny
    lda #$8d
    sta (codePointer),y
    iny
    lda bitmapPointer
    sta (codePointer),y
    iny
    lda bitmapPointer+1
    sta (codePointer),y
    clc
    lda codePointer
    adc #8
    sta codePointer
    bcc !pointer+
    inc codePointer+1
!pointer:
    inc pixelCount
    bne !count+
    inc pixelCount+1
!count:
    rts
capacityStopped:
    lda #7
    sta $d020
    jmp capacityStopped
fault:
    jsr $ffcc
    lda #2
    sta $d020
faultIdle:
    jmp faultIdle

phase: .byte 0
shownPhase: .byte $ff
presentations: .byte 0
displayBank: .byte 0
drawBank: .byte 1
blocksRemaining: .byte 0
writeAddress: .word $0300
writeCommand: .text "M-W"
phaseCommand: .text "M-W"
    .word $0700
    .byte 1
executeCommand: .text "M-E"
    .word $0300
readCommand: .text "M-R"
    .word $0710
    .byte 19
packet: .fill 19,0
edgeIndex: .byte 0
lineX: .byte 0
lineY: .byte 0
deltaX: .byte 0
deltaY: .byte 0
signX: .byte 0
signY: .byte 0
steps: .byte 0
remaining: .byte 0
errorX: .byte 0
errorY: .byte 0
pixelMask: .byte 0
pixelCount: .word 0
bankBits: .byte 3,2
bitmapHigh: .byte $20,$60
bankDelta: .byte 0,$40
masks: .byte $80,$40,$20,$10,$08,$04,$02,$01
edgeFrom: .byte 0,2,4,6,8,10,12,14,0,2,4,6
edgeTo: .byte 2,4,6,0,10,12,14,8,8,10,12,14
rowLow: .fill 200, <($2000+floor(i/8)*320+mod(i,8))
rowHigh: .fill 200, >($2000+floor(i/8)*320+mod(i,8))
drivePayload: .fill DRIVE_BYTES,drive.get(i+2)
.errorif *> $2000,"C64 program must stay below first bitmap"
