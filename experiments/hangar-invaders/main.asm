// Own small playable hangar game: character enemies and two hardware sprites.
.label pointer=$f0
BasicUpstart2(start)
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
    sta $dc03
    sta $d010
    sta $d017
    sta $d01b
    sta $d01c
    sta $d01d
    sta $d021
    lda #$e0
    sta $dc02
    lda #$ff
    sta $dc00
    lda $dd02
    ora #3
    sta $dd02
    lda #3
    sta $dd00
    lda #$0b
    sta $d011
    lda #8
    sta $d016
    lda #$18
    sta $d018
    lda #6
    sta $d020
    ldx #0
!screen:
    lda #32
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
    ldx #0
!enemyColors:
    lda #13
    .for(var row=4;row<=10;row++) { sta $d800+row*40,x }
    inx
    cpx #40
    bne !enemyColors-
    ldx #0
!heading:
    lda title,x
    sta $0400+40+12,x
    lda #7
    sta $d800+40+12,x
    inx
    cpx #15
    bne !heading-
    ldx #0
!hud:
    lda hudText,x
    sta $0400+2*40+5,x
    inx
    cpx #27
    bne !hud-
    ldx #0
!controls:
    lda controls,x
    sta $0400+23*40+9,x
    lda #12
    sta $d800+23*40+9,x
    inx
    cpx #23
    bne !controls-
    .for(var row=4;row<=20;row++) {
        lda #3
        sta $0400+row*40+3
        sta $0400+row*40+29
        lda #12
        sta $d800+row*40+3
        sta $d800+row*40+29
    }
    ldx #3
!floor:
    lda #4
    sta $0400+21*40,x
    lda #12
    sta $d800+21*40,x
    inx
    cpx #30
    bne !floor-
    lda #$c0
    sta $07f8
    lda #$c1
    sta $07f9
    lda #5
    sta $d027
    lda #7
    sta $d028
    // VIC begins visible sprite data one raster after its Y compare.
    lda #202
    sta $d001
    jsr resetGame
    jsr renderScene
    jsr waitBottom
    lda #$1b
    sta $d011
    jsr waitBottom
framePresented:
    nop
inputSample:
    jsr readControls
    jsr updateGame
    jsr renderScene
renderComplete:
    jsr waitBottom
    jmp framePresented

waitBottom:
!leave:
    lda $d012
    cmp #252
    beq !leave-
!bottom:
    lda $d012
    cmp #252
    bne !bottom-
    rts

readControls:
    lda $dc00
    and #31
    sta lastJoystick
    lda #0
    sta newFire
    lda lastJoystick
    and #16
    bne !released+
    lda fireHeld
    bne !done+
    inc newFire
    inc fireHeld
!done:
    rts
!released:
    lda #0
    sta fireHeld
    rts

updateGame:
    inc updates
    bne !count+
    inc updates+1
!count:
    lda mode
    beq !playing+
    lda newFire
    beq !winHeld+
    inc restarts
    jsr resetGame
!winHeld:
    rts
!playing:
    lda lastJoystick
    and #12
    cmp #8
    bne !right+
    lda playerX
    cmp #32
    beq !movementDone+
    dec playerX
    dec playerX
    jmp !movementDone+
!right:
    cmp #4
    bne !movementDone+
    lda playerX
    cmp #216
    beq !movementDone+
    inc playerX
    inc playerX
!movementDone:
    inc gameTick
    inc formationTimer
    lda formationTimer
    cmp #32
    bne !projectile+
    lda #0
    sta formationTimer
    lda direction
    bmi !moveLeft+
    lda formation
    cmp #10
    bne !advanceRight+
    lda #$ff
    sta direction
    dec formation
    jmp !projectile+
!advanceRight:
    inc formation
    jmp !projectile+
!moveLeft:
    lda formation
    cmp #5
    bne !advanceLeft+
    lda #1
    sta direction
    inc formation
    jmp !projectile+
!advanceLeft:
    dec formation
!projectile:
    lda bulletActive
    beq !fire+
    lda bulletY
    cmp #4
    bcs !travel+
    lda #0
    sta bulletActive
    inc misses
    lda misses
    cmp #100
    bne !fire+
    lda #0
    sta misses
    jmp !fire+
!travel:
    sbc #4
    sta bulletY
    jsr checkHit
!fire:
    lda mode
    bne !done+
    lda newFire
    beq !done+
    lda bulletActive
    bne !done+
    lda #1
    sta bulletActive
    lda playerX
    clc
    adc #7
    sta bulletX
    lda #148
    sta bulletY
    inc shots
    lda shots
    cmp #100
    bne !done+
    lda #0
    sta shots
!done:
    rts

checkHit:
    ldx #0
!enemy:
    lda alive,x
    beq !next+
    lda bulletY
    cmp enemyBottom,x
    bcs !next+
    clc
    adc #4
    cmp enemyTop,x
    bcc !next+
    lda formation
    asl
    asl
    asl
    clc
    adc enemyXOffset,x
    sta enemyLeft
    lda bulletX
    cmp enemyLeft
    bcc !next+
    sec
    sbc enemyLeft
    cmp #8
    bcs !next+
    lda #0
    sta alive,x
    sta bulletActive
    inc score
    dec remaining
    bne !hit+
    inc mode
!hit:
    rts
!next:
    inx
    cpx #12
    bne !enemy-
    rts

resetGame:
    lda #0
    sta mode
    sta score
    sta misses
    sta shots
    sta bulletActive
    sta bulletX
    sta bulletY
    sta gameTick
    sta formationTimer
    lda #120
    sta playerX
    lda #12
    sta remaining
    lda #5
    sta formation
    lda #1
    sta direction
    ldx #11
!alive:
    sta alive,x
    dex
    bpl !alive-
    // Held fire is intentionally preserved: restart requires a fresh edge.
    rts

renderScene:
    ldx #0
    lda #32
!clear:
    .for(var row=4;row<=10;row++) { sta $0400+row*40,x }
    sta $0400+15*40,x
    sta $0400+17*40,x
    inx
    cpx #40
    bne !clear-
    lda #3
    .for(var row=4;row<=10;row++) {
        sta $0400+row*40+3
        sta $0400+row*40+29
    }
    sta $0400+15*40+3
    sta $0400+15*40+29
    sta $0400+17*40+3
    sta $0400+17*40+29
    lda gameTick
    and #16
    beq !a+
    lda #2
    bne !glyph+
!a:
    lda #1
!glyph:
    sta enemyGlyph
    ldx #0
!drawEnemy:
    lda alive,x
    beq !next+
    lda enemyCellLo,x
    clc
    adc formation
    sta pointer
    lda enemyCellHi,x
    adc #0
    sta pointer+1
    ldy #0
    lda enemyGlyph
    sta (pointer),y
!next:
    inx
    cpx #12
    bne !drawEnemy-
    lda #<($0400+2*40+11)
    sta pointer
    lda #>($0400+2*40+11)
    sta pointer+1
    lda score
    jsr twoDigits
    lda #<($0400+2*40+20)
    sta pointer
    lda #>($0400+2*40+20)
    sta pointer+1
    lda misses
    jsr twoDigits
    lda #<($0400+2*40+30)
    sta pointer
    lda #>($0400+2*40+30)
    sta pointer+1
    lda shots
    jsr twoDigits
    lda mode
    beq !sprites+
    ldx #0
!win:
    lda winText,x
    sta $0400+15*40+13,x
    inx
    cpx #12
    bne !win-
    ldx #0
!restart:
    lda restartText,x
    sta $0400+17*40+11,x
    inx
    cpx #17
    bne !restart-
!sprites:
    lda playerX
    clc
    adc #24
    sta $d000
    lda bulletX
    clc
    adc #24
    sta $d002
    lda bulletY
    clc
    adc #50
    sta $d003
    lda bulletActive
    asl
    ora #1
    sta $d015
    rts
twoDigits:
    ldx #0
!tens:
    cmp #10
    bcc !ones+
    sbc #10
    inx
    bne !tens-
!ones:
    clc
    adc #48
    ldy #1
    sta (pointer),y
    txa
    clc
    adc #48
    dey
    sta (pointer),y
    rts

mode: .byte 0
score: .byte 0
misses: .byte 0
shots: .byte 0
remaining: .byte 12
playerX: .byte 120
bulletActive: .byte 0
bulletX: .byte 0
bulletY: .byte 0
gameTick: .byte 0
formationTimer: .byte 0
formation: .byte 5
direction: .byte 1
fireHeld: .byte 0
newFire: .byte 0
lastJoystick: .byte 31
restarts: .byte 0
updates: .word 0
enemyLeft: .byte 0
enemyGlyph: .byte 1
alive: .fill 12,1
enemyXOffset: .fill 12,mod(i,4)*40
enemyTop: .fill 12,40+floor(i/4)*16
enemyBottom: .fill 12,48+floor(i/4)*16
enemyCellLo: .fill 12,<($0400+(5+floor(i/4)*2)*40+mod(i,4)*5)
enemyCellHi: .fill 12,>($0400+(5+floor(i/4)*2)*40+mod(i,4)*5)
.encoding "ascii"
title: .text "HANGAR INVADERS"
hudText: .text "SCORE 00  MISS 00  SHOTS 00"
controls: .text "LEFT RIGHT FIRE  PORT 2"
winText: .text "HANGAR CLEAR"
restartText: .text "RELEASE THEN FIRE"
.errorif *> $2000,"Code overlaps own font"

*=$2000 "Own font and enemy art"
font:
    .fill 8,0
    .byte $3c,$7e,$db,$ff,$a5,$24,$5a,0
    .byte $3c,$7e,$db,$ff,$a5,$5a,$a5,0
    .fill 8,$18
    .byte 0,0,0,$ff,0,0,0,0
    .fill (48-5)*8,0
    // ASCII 0..9. Six-pixel glyphs, one blank bottom row.
    .byte $3c,$42,$46,$4a,$52,$62,$3c,0
    .byte $18,$28,$08,$08,$08,$08,$3e,0
    .byte $3c,$42,$02,$0c,$30,$40,$7e,0
    .byte $3c,$42,$02,$1c,$02,$42,$3c,0
    .byte $0c,$14,$24,$44,$7e,$04,$04,0
    .byte $7e,$40,$7c,$02,$02,$42,$3c,0
    .byte $1c,$20,$40,$7c,$42,$42,$3c,0
    .byte $7e,$02,$04,$08,$10,$10,$10,0
    .byte $3c,$42,$42,$3c,$42,$42,$3c,0
    .byte $3c,$42,$42,$3e,$02,$04,$38,0
    .fill (65-58)*8,0
    .byte $18,$24,$42,$42,$7e,$42,$42,0
    .byte $7c,$42,$42,$7c,$42,$42,$7c,0
    .byte $3c,$42,$40,$40,$40,$42,$3c,0
    .byte $78,$44,$42,$42,$42,$44,$78,0
    .byte $7e,$40,$40,$7c,$40,$40,$7e,0
    .byte $7e,$40,$40,$7c,$40,$40,$40,0
    .byte $3c,$42,$40,$4e,$42,$42,$3c,0
    .byte $42,$42,$42,$7e,$42,$42,$42,0
    .byte $3e,$08,$08,$08,$08,$08,$3e,0
    .byte $1e,$04,$04,$04,$44,$44,$38,0
    .byte $42,$44,$48,$70,$48,$44,$42,0
    .byte $40,$40,$40,$40,$40,$40,$7e,0
    .byte $42,$66,$5a,$5a,$42,$42,$42,0
    .byte $42,$62,$52,$4a,$46,$42,$42,0
    .byte $3c,$42,$42,$42,$42,$42,$3c,0
    .byte $7c,$42,$42,$7c,$40,$40,$40,0
    .byte $3c,$42,$42,$42,$4a,$44,$3a,0
    .byte $7c,$42,$42,$7c,$48,$44,$42,0
    .byte $3c,$42,$40,$3c,$02,$42,$3c,0
    .byte $7f,$08,$08,$08,$08,$08,$08,0
    .byte $42,$42,$42,$42,$42,$42,$3c,0
    .byte $42,$42,$42,$42,$42,$24,$18,0
    .byte $42,$42,$42,$5a,$5a,$66,$42,0
    .byte $42,$42,$24,$18,$24,$42,$42,0
    .byte $41,$22,$14,$08,$08,$08,$08,0
    .byte $7e,$02,$04,$18,$20,$40,$7e,0
    .fill (256-91)*8,0
*=$3000 "Own hardware sprite art"
playerArt:
    .byte $01,$80,0,$01,$80,0,$03,$c0,0,$07,$e0,0
    .byte $0f,$f0,0,$3f,$fc,0,$7f,$fe,0,$ff,$ff,0
    .byte $c3,$c3,0,$81,$81,0,$24,$24,0,$18,$18,0
    .fill 64-12*3,0
bulletArt:
    .for(var row=0;row<5;row++) { .byte $80,0,0 }
    .fill 64-5*3,0
