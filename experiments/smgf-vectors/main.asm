// Original hardware polygon composition:4 moving edges and4 gap underlays.
.var poses=LoadBinary("build/poses.bin")
.const ROWS=144
.const STRIDE=36
BasicUpstart2(start)
*=$080e "Initialization, scheduler and bootstrap"
start:
    sei
    lda #$35
    sta $01
    lda #$7f
    sta $dc0d
    sta $dd0d
    lda $dc0d
    lda $dd0d
    lda #0
    sta $d01a
    sta $d015
    sta $d017
    sta $d01b
    sta $d01c
    sta $d010
    sta $d020
    sta $d021
    sta $d418
    lda $dd02
    ora #3
    sta $dd02
    lda #2
    sta $dd00
    lda #8
    sta $d016
    lda #$20
    sta $d018
    lda #$6b
    sta $d011
    lda #$ff
    sta $d01d
    .for (var sprite=0;sprite<8;sprite++) {
        lda spriteX+sprite
        sta $d000+sprite*2
        lda #60
        sta $d001+sprite*2
        lda spriteColors+sprite
        sta $d027+sprite
    }
    lda #<kernelA
    sta activeJump+1
    lda #>kernelA
    sta activeJump+2
    lda #<kernelBRows
    sta $02
    lda #>kernelBRows
    sta $03
    jsr setSource
    jmp armNextField

idle:
    jmp idle

afterKernel:
    lda #0
    sta $d017
    sta $d015
    lda #36
    sta patchCount
    ldx patchRow
!patch:
patchOperands:
    .for (var plane=0;plane<5;plane++) {
        .var offsets=List().add(9,14,19,24,31)
    patchLoad:
        lda $ffff,x
        ldy #offsets.get(plane)
        sta ($02),y
    }
    clc
    lda $02
    adc #STRIDE
    sta $02
    bcc !page+
    inc $03
!page:
    inx
    dec patchCount
    bne !patch-
    stx patchRow
    // The frame is complete by the time the bounded patch job has finished.
framePresented:
    inc fieldCounter
    lda patchRow
    cmp #ROWS
    bne !pending+
    lda workPose
    sta activePose
    lda activeJump+2
    eor #($10^$26)
    sta activeJump+2
    // Inactive destination is the code buffer we just stopped displaying.
    lda #<kernelARows
    sta $02
    lda activeJump+2
    eor #($10^$26)
    sta $03
    lda #0
    sta patchRow
    inc workPose
    lda workPose
    and #15
    sta workPose
    jsr setSource
!pending:
    // Wait through the low-byte256 wrap before arming the next line50.
armNextField:
!high:
    bit $d011
    bpl !high-
!low:
    bit $d011
    bmi !low-
!fifty:
    lda $d012
    cmp #50
    bne !fifty-
    lda #$7b
    sta $d011
    lda #<firstIRQ
    sta $fffe
    lda #>firstIRQ
    sta $ffff
    lda #52
    sta $d012
    lda #1
    sta $d019
    sta $d01a
    lda #$ff
    sta $d015
    lda started
    bne !return+
    inc started
    cli
    jmp idle
!return:
    pla
    tay
    pla
    tax
    pla
    rti

setSource:
    ldy workPose
    .for (var plane=0;plane<5;plane++) {
        lda sourceLo+plane*16,y
        sta patchOperands+plane*7+1
        lda sourceHi+plane*16,y
        sta patchOperands+plane*7+2
    }
    rts

.align $100
firstIRQ:
    pha
    txa
    pha
    tya
    pha
    lda #<secondIRQ
    sta $fffe
    lda #>secondIRQ
    sta $ffff
    inc $d012
    lda #1
    sta $d019
    tsx
    cli
    .fill 8,$ea
secondIRQ:
    txs
    ldx #8
!align:
    dex
    bne !align-
    bit $00
    lda $d012
    cmp $d012
    beq !stable+
!stable:
stableStart:
    lda #$6b
    sta $d011
    lda #0
    sta $d01a
    ldx #0
    ldy #0
    .fill 19,$ea
    bit $00
    jmp prelude
prelude:
    .for (var line=55;line<60;line++) {
        .fill 30,$ea
        bit $00
    }
    .fill 24,$ea
    bit $00
    sty $d000
    .for (var line=61;line<79;line++) {
        sta $d017,x
        lda #(line<75 ? 0 : $ff)
        sta $d017
        lda #0
        .fill 14,$ea
        sty $d000
    }
    sta $d017,x
    lda #$ff
    sta $d017
    lda #0
    ldy #240
    .fill 10,$ea
    bit $00
activeJump:
    jmp kernelA

spriteX: .byte 240,168,96,64,88,128,152,192
spriteColors: .byte 0,14,4,3,3,4,4,14
started: .byte 0
fieldCounter: .byte 0
activePose: .byte 0
workPose: .byte 1
patchRow: .byte 0
patchCount: .byte 0
.errorif *>$1000,"Scheduler overlaps first raster buffer"

.macro EmitRows() {
    .for (var row=0;row<ROWS;row++) {
        sta $d017,x
        lda #$ff
        sta $d017
        ldy #poses.get(row)
        sty $d002
        ldy #poses.get(144+row)
        sty $d004
        ldy #poses.get(288+row)
        sty $d006
        lda #poses.get(432+row)
        sta $d018
        lda #0
        ldy #poses.get(576+row)
        nop
        sty $d000
    }
    jmp afterKernel
}
*=$1000 "Raster bufferA"
kernelA:
    sty $d000
kernelARows:
    :EmitRows()
*=$2600 "Raster bufferB"
kernelB:
    sty $d000
kernelBRows:
    :EmitRows()
.errorif *>$3b00,"Second raster buffer overlaps source pointers"

*=$3b00 "Schedule input pointers"
sourceLo: .fill 80,<(phaseData+(i&15)*720+floor(i/16)*144)
sourceHi: .fill 80,>(phaseData+(i&15)*720+floor(i/16)*144)
// Five patch instructions above are contiguous7-byte LDA/LDY/STA triples.

*=$4000 "Constant solid and blank stretched sprite rows"
    .fill 53,0
    .byte $ff,$ff,$ff
    .fill 72,0
*=$47f8 "All solid pointers"
    .fill 8,0
*=$4bf8 "All blank pointers"
    .fill 8,1
*=$8000 "Prepared own polygon edge schedules"
phaseData:
    .import binary "build/poses.bin"
