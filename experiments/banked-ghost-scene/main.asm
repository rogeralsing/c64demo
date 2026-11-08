// Own bank-aware scene: hires bitmap above an idle-byte/sprite cutout band.
// It exercises The Ghost's documented $4000 bank/$6000 matrix/$7FFF idle-byte
// contract. Its artwork and raster schedule do not clone the original scene.
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
    sta $d020
    sta $d025
    sta $7fff
    lda #$ff
    sta frameCounter
    lda #14
    sta $d021
    sta $d026
    lda #3
    sta $dd02
    lda #2
    sta $dd00
    lda #$80
    sta $d018
    lda #$08
    sta $d016
    lda #$3b
    sta $d011
    ldx #0
!matrix:
    lda #$16
    sta $6000,x
    sta $6100,x
    sta $6200,x
    sta $6300,x
    lda #0
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    inx
    bne !matrix-
    .for (var sprite=0; sprite<8; sprite++) {
        lda #<(24+48*sprite)
        sta $d000+2*sprite
        lda #255
        sta $d001+2*sprite
        lda #$90+sprite
        sta $63f8+sprite
        lda #14
        sta $d027+sprite
    }
    lda #$e0
    sta $d010
    lda #$ff
    sta $d01c
    sta $d01d
    lda #<nmi
    sta $fffa
    lda #>nmi
    sta $fffb
nextFrame:
!high:
    bit $d011
    bpl !high-
!low:
    bit $d011
    bmi !low-
!line39:
    lda $d012
    cmp #39
    bne !line39-
    ldx #9
!modeDelay:
    dex
    bne !modeDelay-
    nop
    nop
    lda #$3b
    sta $d011
updateFrame:
    inc frameCounter
    lda frameCounter
    and #15
    sta phase
    asl
    clc
    adc #$80
    sta copyFirst+2
    clc
    adc #1
    sta copySecond+2
    ldx #0
!copy:
copyFirst:
    lda $8000,x
    sta $6400,x
copySecond:
    lda $8100,x
    sta $6500,x
    inx
    bne !copy-
    lda #$ff
    sta $d015
    lda phase
    and #7
    tax
    lda idlePatterns,x
    sta idleValue
!line248:
    lda $d012
    cmp #248
    bne !line248-
    // Keep bitmap mode until all 200 rows have been displayed. RSEL changes
    // after the 24-row bottom test and before the 25-row bottom test.
    lda #$33
    sta $d011
!line250:
    lda $d012
    cmp #250
    bne !line250-
    // Polling ends in cycles0..8. Fifty delay cycles put the mode write
    // after the last bitmap pixels and before the first idle fetches.
    ldx #9
!delay:
    dex
    bne !delay-
    nop
    nop
    lda #$13
    sta $d011
    lda idleValue
    sta $7fff
!line258:
    lda $d012
    cmp #2
    bne !line258-
    lda #$1b
    sta $d011
!line290:
    lda $d012
    cmp #34
    bne !line290-
    lda #0
    sta $7fff
frameComplete:
    jmp nextFrame
nmi:
    rti
frameCounter: .byte 0
phase: .byte 0
idleValue: .byte 0
idlePatterns: .byte $81,$c0,$60,$30,$18,$0c,$06,$03
.errorif * > $4000, "Code overlaps bitmap"
* = $4000 "Original hires scene"
bitmap: .import binary "build/bitmap.bin"
.errorif * > $6000, "Bitmap overlaps matrix"
* = $8000 "Reusable moving cutout masks"
masks: .import binary "build/masks.bin"
