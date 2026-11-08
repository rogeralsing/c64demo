// Font/matrix pair publication reuses the character-rotozoom display contract.
// These routines operate only on this example's own complete back/front pairs.
initializeDisplay:
    sei
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
    lda #$18
    sta $d016
    sta $d018
    lda #6
    sta $d020
    sta $d021
    lda #1
    sta $d022
    lda #13
    sta $d023
    lda #0
    sta $d015
    sta frameCounter
    sta frameCounter+1
    sta presentationCounter
    sta presentationCounter+1
    sta poseUsed
    ldx #0
!blank:
    lda #0
    sta $0400,x
    sta $0500,x
    sta $0600,x
    sta $0700,x
    .for (var page = $20; page < $28; page++) {
        sta page*$100,x
    }
    lda #$0d
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    inx
    bne !blank-
    lda #<irq
    sta $fffe
    lda #>irq
    sta $ffff
    lda #<nmiReturn
    sta $fffa
    lda #>nmiReturn
    sta $fffb
    lda #250
    sta $d012
    lda #1
    sta $d019
    sta $d01a
    cli
    rts

publishImage:
!waitHigh:
    bit $d011
    bpl !waitHigh-
!waitLow:
    bit $d011
    bmi !waitLow-
    lda drawSelection
    sta $d018
    lda drawFontHigh
    sta frontFontHigh
    lda drawScreenHigh
    sta frontScreenHigh
    lda poseUsed
    sta frontPose
    inc presentationCounter
    bne !scanout+
    inc presentationCounter+1
!scanout:
    bit $d011
    bpl !scanout-
displayComplete:
    rts

irq:
    pha
    inc frameCounter
    bne !done+
    inc frameCounter+1
!done:
    lda #1
    sta $d019
    pla
nmiReturn:
    rti
