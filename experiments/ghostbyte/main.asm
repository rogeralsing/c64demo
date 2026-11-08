// Original teaching example by this project, informed by Trident's 2023 article:
// https://github.com/trident64/c64/tree/80d1027742815e55cda13a80cb4826744dd75c83/unexpanded-border-scroll
// This demonstrates idle-graphics shine-through, not the Orbit Untold or
// The Ghost scroller. No third-party code, font or artwork is included.

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
    sta $d017
    sta $d01b
    sta frameCounter
    sta frameCounter+1
    sta mode
    sta modeAge
    sta $d020
    sta $d025
    lda #$0f
    sta $d021
    sta $d026
    lda #$03
    sta $dd02
    sta $dd00
    lda #$1b
    sta $d011
    lda #$08
    sta $d016
    lda #$14
    sta $d018

    ldx #0
!clear:
    lda #$20
    sta $0400,x
    sta $0500,x
    sta $0600,x
    sta $0700,x
    lda #$00
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    inx
    bne !clear-

    .for (var row=0; row<9; row++) {
        ldx #39
    !text:
        lda text+row*40,x
        sta $0400+(row+3)*40,x
        dex
        bpl !text-
    }
    ldx #13
!view:
    lda currentView,x
    sta $0400+13*40+5,x
    dex
    bpl !view-

    .for (var sprite=0; sprite<8; sprite++) {
        lda #<(24+48*sprite)
        sta $d000+sprite*2
        lda #255
        sta $d001+sprite*2
        lda #$80+sprite
        sta $07f8+sprite
        lda #15
        sta $d027+sprite
    }
    lda #$e0
    sta $d010
    lda #$ff
    sta $d01c
    sta $d01d

    // IRQs remain disabled: the lower-border switch uses raster polling.
    // The NMI vector is initialized because the KERNAL ROM is banked out.
    lda #<nmi
    sta $fffa
    lda #>nmi
    sta $fffb

nextFrame:
    // Test bit 8 explicitly. The low raster byte alone wraps at line 256.
!high:
    bit $d011
    bpl !high-
!low:
    bit $d011
    bmi !low-
!line40:
    lda $d012
    cmp #40
    bne !line40-

updateFrame:
    inc frameCounter
    bne !counter+
    inc frameCounter+1
!counter:
    inc modeAge
    lda modeAge
    cmp #128
    bne !mode+
    lda #0
    sta modeAge
    inc mode
    lda mode
    cmp #3
    bne !mode+
    lda #0
    sta mode
!mode:
    ldx mode
    lda spriteEnable,x
    sta $d015
    lda modeLetters,x
    sta $0400+13*40+19

    lda frameCounter
    lsr
    lsr
    lsr
    and #7
    tax
    lda idlePatterns,x
    ldx mode
    cpx #2
    bne !ghost+
    lda #0
!ghost:
    sta $3fff

!bottom:
    lda $d012
    cmp #248
    bne !bottom-
    // Select 24 rows after its bottom-border comparison has passed, but
    // before the 25-row comparison. Idle graphics remain visible below it.
    lda #$13
    sta $d011
!line258:
    lda $d012
    cmp #2
    bne !line258-
    // After line 248 this is line 258, not next frame's line 2.
    lda #$1b
    sta $d011
frameComplete:
    jmp nextFrame

nmi:
    rti

frameCounter: .word 0
mode: .byte 0
modeAge: .byte 0
spriteEnable: .byte $ff,0,$ff
modeLetters: .byte 1,2,3
idlePatterns: .byte $81,$42,$24,$18,$18,$24,$42,$81

.encoding "screencode_upper"
text:
    .text "      GHOSTBYTE SHINE-THROUGH           "
    .text "                                        "
    .text "  EIGHT EXPANDED MULTICOLOR SPRITES     "
    .text "  EACH SYMBOL COVERS FOUR SCREEN PIXELS "
    .text "                                        "
    .text "  A  COMBINED: IDLE PIXELS THROUGH HOLES"
    .text "  B  IDLE GRAPHICS ONLY, NO SPRITES     "
    .text "  C  SPRITE MASK ONLY, IDLE BYTE ZERO   "
    .text "  VIEW CHANGES EVERY 128 PAL FRAMES     "

.errorif *-text != 9*40, "Text rows must be forty columns"
currentView: .text "CURRENT VIEW: "

// Each sprite has 12 expanded multicolor symbols per row. Palette symbol
// 00 is transparent, 01 is black, 10/11 match the light-gray background.
// Solid symbols remain four pixels wide. Transparent symbols reveal the
// idle byte's one-pixel detail beneath the sprites.
*=$2000 "Expanded multicolor masks"
.for (var sprite=0; sprite<8; sprite++) {
    .for (var row=0; row<21; row++) {
        .if (row==0 || row==20 || row==7 || row==13) {
            .byte $55,$55,$55
        } else {
            .if (((sprite+floor(row/7))&1)==0) {
                .byte $80,$0a,$02
            } else {
                .byte $a0,$00,$0a
            }
        }
    }
    .byte 0
}
