// Original mock DOS, source/note viewer and live SID selection menu.
.label source = $fb
.label destination = $fd
BasicUpstart2(start)
start:
    lda #$37
    sta $01
    lda #1
    sta $cc
    lda #3
    sta $dd00
    lda $dd02
    ora #3
    sta $dd02
    lda #$1b
    sta $d011
    lda #8
    sta $d016
    lda #0
    sta $d015
    sta $d020
    sta $d021
    sta page
    sta commandLength
    sta scrollRow
    sta playing
    sta selected
    sta frameCounter
    sta frameCounter+1
    ldx #24
!sid:
    sta $d400,x
    dex
    bpl !sid-
    lda #$34
    sta frontHi
    ldx #0
!colors:
    lda #15
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    inx
    bne !colors-
    jsr renderPage

mainLoop:
    jsr nextField
    inc frameCounter
    bne !frame+
    inc frameCounter+1
!frame:
    jsr musicTick
    jsr $ffe4
    beq frameComplete
    jsr handleKey
frameComplete:
    jmp mainLoop

nextField:
!high:
    bit $d011
    bpl !high-
!low:
    bit $d011
    bmi !low-
    rts

handleKey:
    sta lastKey
    ldx page
    beq dosKey
    cmp #81
    bne !page+
    lda #0
    jmp changePage
!page:
    cpx #1
    bne !sound+
    jmp viewerKey
!sound:
    cpx #2
    bne !return+
    jmp sidKey
!return:
    rts

dosKey:
    cmp #13
    beq commandReturn
    cmp #20
    beq commandDelete
    cmp #32
    bcc !return+
    cmp #96
    bcs !return+
    ldx commandLength
    cpx #16
    bcs !return+
    sta commandBuffer,x
    jsr commandPointer
    ldy commandLength
    lda lastKey
    sta (destination),y
    inc commandLength
!return:
    rts
commandDelete:
    lda commandLength
    beq !return+
    dec commandLength
    jsr commandPointer
    ldy commandLength
    lda #32
    sta (destination),y
!return:
    rts
commandReturn:
    ldx #4
!word:
    lda commandLength
    cmp commandSizes,x
    bne !next+
    lda commandLo,x
    sta source
    lda commandHi,x
    sta source+1
    ldy #0
!letter:
    lda (source),y
    cmp commandBuffer,y
    bne !next+
    iny
    cpy commandLength
    bne !letter-
    lda commandPages,x
    cmp #1
    beq !editor+
    cmp #2
    beq !sid+
    jmp changePage
!next:
    dex
    bpl !word-
!clear:
    lda #0
    jmp changePage
!editor:
    lda #0
    sta scrollRow
    lda #1
    jmp changePage
!sid:
    lda #0
    sta selected
    lda #2
    jmp changePage
commandPointer:
    lda #<(21*40+2)
    sta destination
    lda frontHi
    clc
    adc #>(21*40+2)
    sta destination+1
    rts

viewerKey:
    cmp #87
    beq !up+
    cmp #83
    beq !down+
    cmp #82
    beq !top+
    rts
!up:
    lda scrollRow
    beq !return+
    dec scrollRow
    jmp renderPage
!down:
    lda scrollRow
    cmp #48
    beq !return+
    inc scrollRow
    jmp renderPage
!top:
    lda #0
    sta scrollRow
    jmp renderPage
!return:
    rts

sidKey:
    cmp #32
    beq stopMusic
    cmp #13
    beq startTrack
    cmp #49
    bcc !return+
    cmp #52
    bcs !return+
    sec
    sbc #49
    sta selected
    jsr markSelection
    jmp startTrack
!return:
    rts
stopMusic:
    lda #0
    sta playing
    sta $d404
    sta $d418
    rts
startTrack:
    lda #1
    sta playing
    sta noteCountdown
    lda #0
    sta noteIndex
    sta $d402
    lda #8
    sta $d403
    lda #$12
    sta $d405
    lda #$b4
    sta $d406
    ldx selected
    lda waveforms,x
    sta $d404
    lda #15
    sta $d418
    rts
musicTick:
    lda playing
    beq !return+
    dec noteCountdown
    bne !return+
    lda selected
    asl
    asl
    asl
    clc
    adc noteIndex
    tax
    lda patterns,x
    sta currentNote
    tax
    lda frequencyLo,x
    sta $d400
    lda frequencyHi,x
    sta $d401
noteApplied:
    inc noteIndex
    lda noteIndex
    and #7
    sta noteIndex
    lda #12
    sta noteCountdown
!return:
    rts

changePage:
    sta page
    lda #0
    sta commandLength
    jsr stopMusic
renderPage:
    lda frontHi
    eor #4
    sta backHi
    sta copyStore0+2
    clc
    adc #1
    sta copyStore1+2
    adc #1
    sta copyStore2+2
    adc #1
    sta copyStore3+2
    lda page
    asl
    asl
    clc
    adc #$40
    sta copyLoad0+2
    adc #1
    sta copyLoad1+2
    adc #1
    sta copyLoad2+2
    adc #1
    sta copyLoad3+2
    ldx #0
!copy:
copyLoad0:
    lda $4000,x
copyStore0:
    sta $3000,x
copyLoad1:
    lda $4100,x
copyStore1:
    sta $3100,x
copyLoad2:
    lda $4200,x
copyStore2:
    sta $3200,x
copyLoad3:
    lda $4300,x
copyStore3:
    sta $3300,x
    inx
    bne !copy-
    lda page
    cmp #1
    beq !viewer+
    jmp !publish+
!viewer:
    lda scrollRow
    ldx #5
    ldy #0
    sty source+1
!shift:
    asl
    rol source+1
    dex
    bne !shift-
    sta source
    lda source+1
    clc
    adc #$50
    sta source+1
    .for (var row=0; row<16; row++) {
        lda #<((row+5)*40+4)
        sta destination
        lda backHi
        clc
        adc #>((row+5)*40+4)
        sta destination+1
        ldy #31
    !copyRow:
        lda (source),y
        sta (destination),y
        dey
        bpl !copyRow-
        clc
        lda source
        adc #32
        sta source
        bcc !next+
        inc source+1
    !next:
    }
!publish:
    jsr nextField
    lda backHi
    sta frontHi
    asl
    asl
    ora #8
    sta $d018
    lda page
    cmp #2
    bne !return+
    jsr markSelection
!return:
    rts

markSelection:
    lda #<(7*40+1)
    sta destination
    lda frontHi
    clc
    adc #>(7*40+1)
    sta destination+1
    ldy #0
    lda #32
    sta (destination),y
    ldy #80
    sta (destination),y
    ldy #160
    sta (destination),y
    ldx selected
    lda markerOffsets,x
    tay
    lda #62
    sta (destination),y
    rts

page: .byte 0
frontHi: .byte $34
backHi: .byte 0
scrollRow: .byte 0
commandLength: .byte 0
commandBuffer: .fill 16,0
lastKey: .byte 0
selected: .byte 0
playing: .byte 0
noteIndex: .byte 0
noteCountdown: .byte 0
currentNote: .byte 0
frameCounter: .word 0
markerOffsets: .byte 0,80,160
commandSizes: .byte 3,4,3,4,4
commandPages: .byte 3,1,2,3,1
commandLo: .byte <wordDir,<wordEdit,<wordSid,<wordHelp,<wordRead
commandHi: .byte >wordDir,>wordEdit,>wordSid,>wordHelp,>wordRead
wordDir: .text "DIR"
wordEdit: .text "EDIT"
wordSid: .text "SID"
wordHelp: .text "HELP"
wordRead: .text "READ"
waveforms: .byte $41,$11,$81
patterns: .byte 0,4,7,12,7,4,0,7, 0,2,5,9,12,9,5,2, 0,7,0,12,0,7,2,9
#import "build/frequencies.asm"
.errorif * > $2000, "Code overlaps own font"
* = $2000 "Own ASCII status font"
.import binary "build/font.bin"
* = $4000 "Own page templates"
.import binary "build/pages.bin"
* = $5000 "Own64-row source and notes"
.import binary "build/notes.bin"
