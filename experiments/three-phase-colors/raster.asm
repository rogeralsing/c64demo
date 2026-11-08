// Independent ready-job polling follows the sprite-interleave scheduler pattern.
// Late bank writes deliberately keep their literal timing in the pixel oracle.
frame:
!high:
    bit $d011
    bpl !high-
!low:
    bit $d011
    bmi !low-
!top:
    lda $d012
    cmp #4
    bcc !top-
fieldStart:
    lda #$3c
    sta $dd02
    jsr setupPhase
    jsr revealByte
    lda #54
    .for (var sprite = 0; sprite < 8; sprite++) {
        sta $d001+sprite*2
    }
    lda #$ff
    sta $d015
    lda #75
    sta nextY
    lda #67
    sta nextYLine
    lda #9
    sta yRemaining
    lda #102
    sta nextBankLine
    lda #$3d
    sta nextDirection
    lda #3
    sta banksRemaining
scan:
    lda $d012
    sta rasterNow
    cmp #250
    bcs !bottom+
    lda yRemaining
    beq !bank+
    lda rasterNow
    cmp nextYLine
    bcc !bank+
    jsr updateY
!bank:
    lda banksRemaining
    beq scan
    lda rasterNow
    clc
    adc #4
    cmp nextBankLine
    bcc scan
    // Enter before the target so the long ready-job loop cannot encounter
    // the following badline first. The short poll leaves a bounded write
    // window during the target's glyph fetches; the native oracle records it.
!waitBank:
    lda $d012
    cmp nextBankLine
    bcc !waitBank-
    .fill 6,$ea
    lda nextDirection
    sta $dd02
    inc nextDirection
    clc
    lda nextBankLine
    adc #48
    sta nextBankLine
    dec banksRemaining
    jmp scan
!bottom:
!highRaster:
    bit $d011
    bpl !highRaster-
!finished:
    lda $d012
    cmp #14
    bcc !finished-
    inc fieldCounter
    bne fieldComplete
    inc fieldCounter+1
fieldComplete:
    inc phase
    lda phase
    cmp #3
    bcc !phase+
    lda #0
    sta phase
!phase:
    inc motion
    lda motion
    and #31
    sta motion
    jmp frame

updateY:
    lda nextY
    .for (var sprite = 0; sprite < 8; sprite++) {
        sta $d001+sprite*2
    }
    clc
    adc #21
    sta nextY
    clc
    lda nextYLine
    adc #21
    sta nextYLine
    dec yRemaining
    rts
