// Original 16-line interleaved sprite carpet, using a five-line overlap window.
// Pointer groups advance every 16 image lines; sprite DMA restarts every 21.
// Rolled rows preserve the live internal sprite row across pointer changes.

BasicUpstart2(start)

.const IMAGE_HEIGHT = 168
.const FIRST_Y = 64
#if INTERLEAVE_20
.const POINTER_STEP = 20
.const BLOCK_COUNT = 9
#else
.const POINTER_STEP = 16
.const BLOCK_COUNT = 11
#endif
.const POINTERS = $07f8

* = $1000 "Independent Y and pointer schedules"
start:
    sei
#if INTERLEAVE_20
    lda #0
    sta $d01a
#endif
    cld
    lda #$7f
    sta $dc0d
    sta $dd0d
    lda $dc0d
    lda $dd0d
    lda #$35
    sta $01
    lda #3
    sta $dd00
    lda $dd02
    ora #3
    sta $dd02
    lda #$1b
    sta $d011
    lda #8
    sta $d016
    lda #$1e
    sta $d018
    lda #0
    sta $d020
    sta $d021
    sta $d015
    sta $d017
    sta $d01b
    sta $d01c
    sta $d01d
    sta frameCounter
    sta frameCounter+1
    ldx #0
!clear:
    sta $0400,x
    sta $0500,x
    sta $0600,x
    sta $0700,x
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    inx
    bne !clear-
    ldx #7
!clearGlyph:
    sta $3800,x
    dex
    bpl !clearGlyph-
    .for (var sprite = 0; sprite < 8; sprite++) {
        lda spriteColors+sprite
        sta $d027+sprite
    }

frame:
!waitHigh:
    bit $d011
    bpl !waitHigh-
!waitLow:
    bit $d011
    bmi !waitLow-
    lda frameCounter
    and #31
    sta phaseUsed
    .for (var sprite = 0; sprite < 8; sprite++) {
        clc
        adc #((88+sprite*24) & $ff)
        sta $d000+sprite*2
        lda phaseUsed
    }
    cmp #24
    lda #$80
    bcc !msbReady+
    ora #$40
!msbReady:
    sta $d010
    lda #FIRST_Y
    .for (var sprite = 0; sprite < 8; sprite++) {
        sta $d001+sprite*2
    }
    lda #$80
    sta pointerBase
    jsr setPointers
    lda #FIRST_Y+21
    sta nextYValue
    lda #FIRST_Y+21-8
    sta nextYLine
    lda #7
    sta yChangesRemaining
    lda #FIRST_Y+POINTER_STEP
    sta nextPointerLine
    lda #BLOCK_COUNT-1
    sta pointerChangesRemaining
    lda #$ff
    sta $d015
#if INTERLEAVE_20
    lda #<pointerIRQ
    sta $fffe
    lda #>pointerIRQ
    sta $ffff
    lda nextPointerLine
    sta $d012
    lda #1
    sta $d019
    sta $d01a
    cli
#endif

// Polling lets adjacent jobs run back-to-back even when a preceding job crosses
// the next target line. Each pointer job must still finish inside its overlap.
scan:
    lda $d012
    sta rasterNow
    cmp #240
    bcs frameComplete
    lda yChangesRemaining
    beq !pointer+
    lda rasterNow
    cmp nextYLine
    bcc !pointer+
    jsr setNextY
!pointer:
#if INTERLEAVE_20
    jmp scan
#else
    lda pointerChangesRemaining
    beq scan
    lda rasterNow
    cmp nextPointerLine
    bcc scan
    jsr setPointers
    clc
    lda nextPointerLine
    adc #POINTER_STEP
    sta nextPointerLine
    dec pointerChangesRemaining
    jmp scan
#endif

frameComplete:
    inc frameCounter
    bne framePresented
    inc frameCounter+1
framePresented:
    jmp frame

setNextY:
    lda nextYValue
    .for (var sprite = 0; sprite < 8; sprite++) {
        sta $d001+sprite*2
    }
    clc
    adc #21
    sta nextYValue
    clc
    lda nextYLine
    adc #21
    sta nextYLine
    dec yChangesRemaining
    rts

setPointers:
#if INTERLEAVE_20
    // Four paired SAX/STX stores reduce the update to three INX operations.
    lda pointerBase
    clc
    adc #4
    tax
    lda #$fb
    .var pointerStoreSites=List()
    .for (var pair=0;pair<4;pair++) {
        sax POINTERS+pair
        .eval pointerStoreSites.add(*)
        stx POINTERS+4+pair
        .eval pointerStoreSites.add(*)
        .if (pair!=3) { inx }
    }
#else
    ldx pointerBase
    .for (var sprite = 0; sprite < 8; sprite++) {
        stx POINTERS+sprite
        .if (sprite != 7) {
            inx
        }
    }
#endif
    inx
    stx pointerBase
    rts

#if INTERLEAVE_20
pointerIRQ:
    pha
    txa
    pha
    tya
    pha
    jsr setPointers
    clc
    lda nextPointerLine
    adc #POINTER_STEP
    sta nextPointerLine
    dec pointerChangesRemaining
    beq !finished+
    sta $d012
    jmp !ack+
!finished:
    lda #0
    sta $d01a
!ack:
    lda #1
    sta $d019
    pla
    tay
    pla
    tax
    pla
    rti
pointerStoreLo: .fill 8,<pointerStoreSites.get(i)
pointerStoreHi: .fill 8,>pointerStoreSites.get(i)
#endif

frameCounter: .word 0
phaseUsed: .byte 0
rasterNow: .byte 0
pointerBase: .byte $80
nextYValue: .byte 0
nextYLine: .byte 0
yChangesRemaining: .byte 0
nextPointerLine: .byte 0
pointerChangesRemaining: .byte 0
spriteColors: .byte 2,8,7,5,3,14,4,1
.assert "Code stays below sprite storage", * < $2000, true

.function ImageByte(xByte, y) {
    .if (y >= IMAGE_HEIGHT) {
        .return 0
    }
    // The first byte encodes the source row, making a wrong roll visible.
    .if (xByte == 0) {
        .return (y ^ $a5) & $ff
    }
    .var result = 0
    .for (var bit = 0; bit < 8; bit++) {
        .var x = xByte*8+bit
        .var warp = mod(x + mod(floor(y/7),2)*3, 8) < 3
        .var weft = mod(y + mod(floor(x/12),2)*2, 9) < 3
        .eval result = (result << 1) | ((warp != weft) ? 1 : 0)
    }
    .return result
}

* = $2000 "Rolled sprite groups with duplicated overlap rows"
spriteData:
    .for (var block = 0; block < BLOCK_COUNT; block++) {
        .for (var sprite = 0; sprite < 8; sprite++) {
            .for (var row = 0; row < 21; row++) {
                .var first = POINTER_STEP*block
                .var y = first + mod(row - mod(first,21) + 21,21)
                .for (var column = 0; column < 3; column++) {
                    .byte ImageByte(sprite*3+column, y)
                }
            }
            .byte 0
        }
    }
#if INTERLEAVE_20
.assert "Nine eight-sprite groups occupy 4608 bytes", *-spriteData, BLOCK_COUNT*8*64
#else
.assert "Eleven eight-sprite groups occupy 5632 bytes", *-spriteData, BLOCK_COUNT*8*64
#endif
