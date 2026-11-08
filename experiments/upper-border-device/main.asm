// Original upper-border raster device. One explicit PAL timing family.
BasicUpstart2(start)
.const CELL_CODE = $3000
.const BUILD_POINTER = $f0
.const COLOR_A = $f2
.const NORMAL_MODE = $f3
.const SPRITES = $35
.const CRUNCH_PAD = 17
.const CELL_PAD = 10
.var members = List().add(0,2,4,5)
.var positions = List().add(96,144,208,256)

* = $1000 "Own generated upper-border cells and sprite-crunch control"
start:
    sei
    cld
    lda #$35
    sta $01
    lda #$7f
    sta $dc0d
    sta $dd0d
    lda $dc0d
    lda $dd0d
    lda #0
    sta $d01a
    sta $d020
    sta $d021
    sta $d015
    sta $d017
    sta $d01b
    sta phase
    sta frameCounter
    sta frameCounter+1
    sta $7fff
    sta $79ff
    sta $d025
    lda #1
    sta $d026
    lda #2
    sta COLOR_A
    lda #$1a
    sta NORMAL_MODE
    lda $dd02
    ora #3
    sta $dd02
    lda #2
    sta $dd00
    lda #$40
    sta $d018
    lda #13
    sta $d016
    lda #$1b
    sta $d011
    ldx #0
!clear:
    lda #0
    .for (var page = $40; page < $48; page++) {
        sta page*$100,x
    }
    .for (var page = $50; page < $5c; page++) {
        sta page*$100,x
    }
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    inx
    beq !cleared+
    jmp !clear-
!cleared:
    .for (var column = 0; column < 4; column++) {
        .var sprite = members.get(column)
        lda #<positions.get(column)
        sta $d000+2*sprite
        lda #9
        sta $d001+2*sprite
        lda #6
        sta $d027+sprite
        .for (var section = 0; section < 3; section++) {
            lda #$80+3*column+section
            sta $53f8+section*$400+sprite
        }
    }
    lda #$20
    sta $d010
    lda #SPRITES
    sta $d01c
    sta $d01d
    jsr generateCells
    jsr patchPatterns
    lda #<nmiReturn
    sta $fffa
    lda #>nmiReturn
    sta $fffb
    // Establish an open vertical border in an ordinary warmup frame.
!warmHigh:
    bit $d011
    bpl !warmHigh-
!warmLow:
    bit $d011
    bmi !warmLow-
!warmBottom:
    lda $d012
    cmp #248
    bne !warmBottom-
    lda #$13
    sta $d011
!warmWrap:
    bit $d011
    bpl !warmWrap-
    lda #8
    sta $d011
    lda #<firstIRQ
    sta $fffe
    lda #>firstIRQ
    sta $ffff
    lda #6
    sta $d012
    lda #1
    sta $d019
    sta $d01a
    // The top IRQ enables DMA before Y=9. Keeping it off here avoids the
    // same low-eight-bit Y match at raster265 during this warmup frame.
ready:
    cli
idle:
    jmp idle

generateCells:
    lda #<CELL_CODE
    sta BUILD_POINTER
    lda #>CELL_CODE
    sta BUILD_POINTER+1
    ldx #0
!cell:
    ldy #cellEnd-cellTemplate-1
!byte:
    lda cellTemplate,y
    sta (BUILD_POINTER),y
    dey
    bpl !byte-
    cpx #2
    beq !tableA+
    cpx #17
    bne !next+
    lda #$60
    bne !table+
!tableA:
    lda #$50
!table:
    ldy #cellPattern-cellTemplate+1
    sta (BUILD_POINTER),y
    ldy #cellPattern-cellTemplate+3
    lda #$18
    sta (BUILD_POINTER),y
    iny
    lda #$d0
    sta (BUILD_POINTER),y
!next:
    clc
    lda BUILD_POINTER
    adc #cellEnd-cellTemplate
    sta BUILD_POINTER
    bcc !page+
    inc BUILD_POINTER+1
!page:
    inx
    cpx #21
    bne !cell-
    ldy #0
    lda #$60
    sta (BUILD_POINTER),y
    rts

patchPatterns:
    .for (var row = 0; row < 21; row++) {
        .if (row != 2 && row != 17) {
            lda basePatterns+row
            ldy phase
            beq !store+
        !rotate:
            asl
            adc #0
            dey
            bne !rotate-
        !store:
            sta CELL_CODE+row*(cellEnd-cellTemplate)+cellPattern-cellTemplate+1
        }
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
!delay:
    dex
    bne !delay-
    bit $00
    lda $d012
    cmp $d012
    beq !stable+
!stable:
stableStart:
    lda #<firstIRQ
    sta $fffe
    lda #>firstIRQ
    sta $ffff
    lda #6
    sta $d012
    lda #1
    sta $d019
    lda #$40
    sta $d018
    lda #SPRITES
    sta $d015
    lda #$70
    sta $d011
!eleven:
    lda $d012
    cmp #11
    bne !eleven-
    lda #SPRITES
    sta $d017
    .fill CRUNCH_PAD,$ea
    bit $00
    bit $00
    lda #0
crunch:
    sta $d017
afterCrunch:
!twentyFive:
    lda $d012
    cmp #25
    bne !twentyFive-
    lda CELL_CODE+cellPattern-cellTemplate+1
    sta $7fff
    ldx #$70
    ldy #5
    clc
    .fill CELL_PAD,$ea
beforeCells:
    jsr CELL_CODE
afterCells:
    lda #8
    sta $d011
    lda #0
    sta $d021
    sta $7fff
!eighty:
    lda $d012
    cmp #80
    bne !eighty-
    lda #$40
    sta $d018
    lda #0
    sta $d015
!bottom:
    lda $d012
    cmp #248
    bne !bottom-
    lda #0
    sta $d011
!high:
    bit $d011
    bpl !high-
    lda #8
    sta $d011
!complete:
    lda $d012
    cmp #34
    bcc !complete-
    inc frameCounter
    bne frameComplete
    inc frameCounter+1
frameComplete:
    inc phase
    lda phase
    and #7
    sta phase
    jsr patchPatterns
    pla
    tay
    pla
    tax
    pla
nmiReturn:
    rti

phase: .byte 0
frameCounter: .word 0
basePatterns:
    .byte $81,$42,$42,$24,$18,$3c,$66,$c3,$99,$bd,$e7
    .byte $bd,$99,$c3,$66,$3c,$18,$18,$24,$42,$81

cellTemplate:
    lda COLOR_A
    .byte $2c,$00,$00 // Absolute BIT, four cycles rather than zero-page three.
    nop
    sta $d021
    lda NORMAL_MODE
    sta $d011
    nop
    sta $cfb1,x
    sty $d021
    stx $d021
    stx $d011
cellPattern:
    lda #0
    sta $7fff
    bit $00
cellEnd:
.assert "Own cell has34bytes", cellEnd-cellTemplate, 34
.assert "Setup stays below generated cells", * <= CELL_CODE, true

* = $6000 "Own three-section multicolor masks for four crunched sprites"
    .for (var column = 0; column < 4; column++) {
        .for (var section = 0; section < 3; section++) {
            .for (var offset = 0; offset < 64; offset++) {
                .var row = floor(offset/3)
                .var value = 0
                .for (var pair = 0; pair < 4; pair++) {
                    .var x = mod(offset,3)*4+pair
                    .var symbol = 0
                    .if (x==0 || x==11 || mod(row+section*2,11)==0) {
                        .eval symbol = 3
                    } else {
                        .if (mod(x,4)==0) { .eval symbol = 1 }
                        .if (mod(row+column+section,5)==0 && mod(x,3)==0) { .eval symbol = 2 }
                    }
                    .eval value = (value<<2)|symbol
                }
                .byte value
            }
        }
    }
