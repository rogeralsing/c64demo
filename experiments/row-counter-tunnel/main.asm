// Original cached-character-row tunnel. No Quondam release bytes or artwork.
// Late D011 writes restart RC without replacing the forty cached screen codes.
.const BAND_COUNT=24
.var charsetOffsets=List().add($0000,$0800,$2000,$2800,$3000,$3800)

BasicUpstart2(start)
*=$1000 "Initialization and raster kernel"
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
    sta $d01a
    sta $d020
    sta $d021
    sta $dd00
    sta fieldCounter
    sta fieldCounter+1
    sta phase

    // The packed source stays below $9800, so a normal LOAD never writes I/O.
    // Copy upward-moving destinations backwards, then lower destinations
    // forwards. This preserves unread packed glyphs while relocating in place.
    .for (var band=23; band>=5; band--) {
        .var destination=floor(band/6)*$4000+charsetOffsets.get(band-floor(band/6)*6)+512
        .for (var page=4; page>=0; page--) {
            ldx #$ff
        !copy:
            lda glyphSource+band*1280+page*256,x
            sta destination+page*256,x
            dex
            cpx #$ff
            bne !copy-
        }
    }
    .for (var band=0; band<5; band++) {
        .var destination=charsetOffsets.get(band)+512
        .for (var page=0; page<5; page++) {
            ldx #0
        !copy:
            lda glyphSource+band*1280+page*256,x
            sta destination+page*256,x
            inx
            bne !copy-
        }
    }

    // All candidate matrices deliberately have a different second row.
    // Only bank zero's first forty entries supply the displayed character cache.
    ldx #79
!matrix:
    lda #$f0
    sta $3000,x
    sta $7000,x
    sta $b000,x
    sta $f000,x
    dex
    bpl !matrix-
    jsr prepareRow
    lda #0
    sta $3fff
    ldx #0
!colors:
    lda #9
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    inx
    bne !colors-
    lda #6
    sta $d022
    lda #3
    sta $d023
    lda #$18
    sta $d016
    lda #$3c
    sta $dd02
    lda #$c0
    sta $d018
    lda #$1b
    sta $d011
    lda #<nmi
    sta $fffa
    lda #>nmi
    sta $fffb
    lda #<irq
    sta $fffe
    lda #>irq
    sta $ffff
    lda #55
    sta $d012
    lda #1
    sta $d019
    sta $d01a
    cli
idle:
    jmp idle

prepareRow:
    lda phase
    asl
    asl
    asl
    sta rowCode
    asl
    asl
    clc
    adc rowCode
    adc #64
    ldx #0
!entry:
    sta $3000,x
    clc
    adc #1
    inx
    cpx #40
    bne !entry-
    rts

irq:
    pha
    txa
    pha
    tya
    pha
    lda #1
    sta $d019
    lda #56
    sta $d012
    lda #<stableIrq
    sta $fffe
    lda #>stableIrq
    sta $ffff
    // A second raster IRQ enters a two-cycle NOP slide. Restore the first
    // stack frame and compensate the remaining one-cycle boundary difference.
    tsx
    cli
    .fill 24,$ea
    jmp *
stableIrq:
    txs
    lda #1
    sta $d019
    ldx #7
!align:
    dex
    bne !align-
    bit $ea
    nop
    nop
    lda $d012
    cmp $d012
    bne !aligned+
!aligned:
    // The first late-window instruction starts at raster58, zero-based cycle49
    // in the native PAL proof; its STA completes at cycle55.
    ldx #20
!firstWindow:
    dex
    bne !firstWindow-
    bit $ea
rasterKernel:
    .for (var band=0; band<BAND_COUNT-1; band++) {
        lda #$1a
        sta $d011
        .var nextBand=band+1
        lda #$3c+floor(nextBand/6)
        sta $dd02
        lda #$c0|(charsetOffsets.get(nextBand-floor(nextBand/6)*6)>>10)
        sta $d018
        // 234 cycles, followed by the six-cycle restoring register write.
        ldx #46
    !wait:
        dex
        bne !wait-
        bit $ea
        lda #$1b
        sta $d011
        // 246 cycles; the next six-cycle late write is 252 cycles away.
        ldx #49
    !wait:
        dex
        bne !wait-
    }
    // Stop repeating after the final band. YSCROLL=0 next matches line248,
    // outside the bad-line interval, when all 24 bands are enabled.
    lda #$18
    sta $d011
    lda #$3c
    sta $dd02
    lda #$c0
    sta $d018
!complete:
    lda $d012
    cmp #246
    bne !complete-
fieldComplete:
    inc fieldCounter
    bne !field+
    inc fieldCounter+1
!field:
    lda fieldCounter
    lsr
    lsr
    and #3
    sta phase
    jsr prepareRow
    lda #$1b
    sta $d011
    lda #55
    sta $d012
    lda #<irq
    sta $fffe
    lda #>irq
    sta $ffff
    pla
    tay
    pla
    tax
    pla
nmi:
    rti

fieldCounter: .word 0
phase: .byte 0
rowCode: .byte 0
.errorif * > $2000, "Raster code overlaps packed glyph source"

.function TunnelByte(band, animation, column, row) {
    .var value=0
    .for (var pixel=0; pixel<4; pixel++) {
        .var x=column*4+pixel
        .var y=band*8+row
        .var dx=abs(x-80)
        .var dy=abs(y-96)/2
        .var radius=dx
        .var across=dy
        .if (dy>dx) {
            .eval radius=dy
            .eval across=dx
        }
        .var ring=floor(180/(radius+4))+animation
        .var sector=floor(across*8/(radius+1))
        .var color=(ring+sector*2)&3
        .eval value=value|(color<<(6-pixel*2))
    }
    .return value
}

*=$2000 "Packed original tunnel glyphs"
glyphSource:
    .for (var band=0; band<24; band++) {
        .for (var animation=0; animation<4; animation++) {
            .for (var column=0; column<40; column++) {
                .for (var row=0; row<8; row++) {
                    .byte TunnelByte(band,animation,column,row)
                }
            }
        }
    }
.errorif * != $9800, "Expected twenty-four four-phase glyph sets"
