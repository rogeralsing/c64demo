// Original point-field example inspired by the documented architecture of
// Second Reality / Smash Designs' CA part. No original code or assets used.
// Prepared profiles feed live position arithmetic and whole-byte plot stores.
// Each generated row routine first clears its own sixteen cached addresses.

.const POINTER=$e0
.const CLEAR_SINK=$5f00
.const BITMAP=$2000

BasicUpstart2(start)

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
    sta $d01a
    sta $d015
    sta $d020
    sta $d021
    sta rasterTick
    sta phase
    sta iteration
    sta iteration+1
    lda #3
    sta $dd02
    sta $dd00
    lda #$18
    sta $d016
    sta $d018
    lda #$3b
    sta $d011

    ldx #0
!screen:
    lda #$d5
    sta $0400,x
    sta $0500,x
    sta $0600,x
    sta $0700,x
    lda #1
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    inx
    bne !screen-

    lda #0
    .for (var page=0; page<32; page++) {
        ldx #0
    !clear:
        sta BITMAP+page*256,x
        inx
        bne !clear-
    }
    sta CLEAR_SINK

    lda #<nmi
    sta $fffa
    lda #>nmi
    sta $fffb
    lda #<irq
    sta $fffe
    lda #>irq
    sta $ffff
    lda #0
    sta $d012
    lda #1
    sta $d019
    sta $d01a
    cli

nextIteration:
    lda rasterTick
    clc
    adc #4
    sta deadline
    jsr drawField
renderComplete:
    lda rasterTick
    cmp deadline
    bne renderComplete
frameComplete:
    inc iteration
    bne !iteration+
    inc iteration+1
!iteration:
    lda phase
    clc
    adc #5
    sta phase
    jmp nextIteration

irq:
    pha
    inc rasterTick
    lda #1
    sta $d019
    pla
nmi:
    rti

rasterTick: .byte 0
deadline: .byte 0
phase: .byte 0
iteration: .word 0
horizontalShift: .byte 0

*=$1000 "Prepared wave and bitmap address tables"
wave:
    .fill 256, round(15*sin(i*2*PI/256))&255
bitmapRowLo:
    .fill 200, <(BITMAP+floor(i/8)*320+(i&7))
bitmapRowHi:
    .fill 200, >(BITMAP+floor(i/8)*320+(i&7))
bitmapColLo:
    .fill 160, <(floor(i/4)*8)
bitmapColHi:
    .fill 160, >(floor(i/4)*8)
pointMasks: .byte $c0,$30,$0c,$03

*=$6000 "Generated cached-clear and plotting rows"
drawField:
    .for (var row=0; row<16; row++) {
        // Cache lives in these self-modifying absolute STA operands. A row
        // clears its previous addresses before plotting its new positions.
        // Later rows can therefore clear bytes drawn by an earlier row.
        .var clearStores=List()
        lda #0
        .for (var column=0; column<16; column++) {
            .eval clearStores.add(*)
            sta CLEAR_SINK
        }

        lda phase
        clc
        adc #(row*16)&255
        tax
        lda wave,x
        cmp #$80
        ror
        sta horizontalShift

        .var step=2+floor(row/2)
        .var origin=floor((160-15*step)/2)
        .for (var column=0; column<16; column++) {
            lda phase
            clc
            adc #(row*16+column*8)&255
            tax
            lda wave,x
            clc
            adc #48+row*7
            tay

            lda horizontalShift
            clc
            adc #origin+column*step
            tax
            lda bitmapRowLo,y
            clc
            adc bitmapColLo,x
            sta POINTER
            sta clearStores.get(column)+1
            lda bitmapRowHi,y
            adc bitmapColHi,x
            sta POINTER+1
            sta clearStores.get(column)+2

            txa
            and #3
            tax
            lda pointMasks,x
            ldy #0
            // Deliberate whole-byte assignment, not OR/XOR accumulation.
            // If two points occupy different lanes of one byte, the last
            // store replaces the earlier lane, matching this chosen contract.
            sta (POINTER),y
        }
    }
    rts
drawFieldEnd:
.errorif drawFieldEnd > $d000, "Generated code must remain below mapped I/O"
