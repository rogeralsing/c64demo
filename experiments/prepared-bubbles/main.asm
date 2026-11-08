// Original prepared 3D animation, expanded on the C64 outside raster IRQs.
.label stream = $f0
.label destination = $f2
.label matchSource = $f4
.label chunkLength = $f6
.label matchDistance = $f7

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
    lda #$03
    sta $dd00
    sta $dd02
    lda #$5b
    sta $d011
    lda #$08
    sta $d016
    lda #$1a
    sta $d018
    lda #6
    sta $d020
    sta $d021
    lda #11
    sta $d022
    lda #0
    sta $d023
    lda #14
    sta $d024
    ldx #0
!clear:
    lda #0
    sta $2000,x
    sta $2100,x
    sta $2200,x
    sta $2300,x
    lda #14
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    inx
    bne !clear-
    .for (var row=0; row<25; row++) {
        .for (var col=0; col<40; col++) {
            lda #((mod(row+col,4)<<6) | mod(col+3*row,64))
            sta $0400+row*40+col
        }
    }
    ldx #0
!spriteSetup:
    lda spriteX,x
    sta $d000,x
    lda spriteY,x
    sta $d001,x
    inx
    inx
    cpx #16
    bne !spriteSetup-
    ldx #7
!colors:
    lda #1
    sta $d027,x
    lda #$80
    sta $07f8,x
    dex
    bpl !colors-
    lda #$ff
    sta $d015
    sta $d017
    sta $d01d
    lda #0
    sta $d010
    sta $d01b
    sta $d01c
    sta ready
    sta frontBuffer
    sta nextFrame
    lda #<rasterIRQ
    sta $fffe
    lda #>rasterIRQ
    sta $ffff
    lda #20
    sta $d012
    lda #1
    sta $d019
    sta $d01a
    cli

mainLoop:
    lda ready
    bne mainLoop
    lda frontBuffer
    eor #1
    sta readyBuffer
    asl
    clc
    adc #$20
    sta destination+1
    lda #0
    sta destination
    ldx nextFrame
    stx readyFrame
    lda frameLo,x
    sta stream
    lda frameHi,x
    sta stream+1
decompressStart:
    jsr expandFrame
decompressFinished:
    inc nextFrame
    lda nextFrame
    cmp #25
    bne !next+
    lda #0
    sta nextFrame
!next:
    lda #1
    sta ready
    jmp mainLoop

// Own decoder for Oscar64's small LZ command format. The copy intentionally
// advances forward, so a match may overlap the destination (including runs).
expandFrame:
!command:
    jsr readStream
    beq !done+
    bmi !match+
    sta chunkLength
    lda stream
    sta matchSource
    lda stream+1
    sta matchSource+1
    lda chunkLength
    jsr advanceStream
    jmp !copy+
!match:
    and #$7f
    sta chunkLength
    jsr readStream
    sta matchDistance
    sec
    lda destination
    sbc matchDistance
    sta matchSource
    lda destination+1
    sbc #0
    sta matchSource+1
!copy:
    ldy #0
!byte:
    lda (matchSource),y
    sta (destination),y
    iny
    cpy chunkLength
    bne !byte-
    clc
    lda destination
    adc chunkLength
    sta destination
    bcc !command-
    inc destination+1
    jmp !command-
!done:
    rts
readStream:
    ldy #0
    lda (stream),y
    inc stream
    bne !return+
    inc stream+1
!return:
    ora #0
    rts
advanceStream:
    clc
    adc stream
    sta stream
    bcc !return+
    inc stream+1
!return:
    rts

rasterIRQ:
    pha
    txa
    pha
    tya
    pha
    lda #1
    sta $d019
    inc rasterTick
    lda ready
    beq !return+
    lda readyBuffer
    sta frontBuffer
    asl
    asl
    asl
    ora #$80
    ldx #0
!pointers:
    sta $07f8,x
    clc
    adc #1
    inx
    cpx #8
    bne !pointers-
    lda readyFrame
    sta shownFrame
framePublished:
    lda #0
    sta ready
!return:
    pla
    tay
    pla
    tax
    pla
    rti

ready: .byte 0
readyBuffer: .byte 0
readyFrame: .byte 0
frontBuffer: .byte 0
shownFrame: .byte 0
nextFrame: .byte 0
rasterTick: .byte 0
spriteX: .byte 88,0,136,0,184,0,232,0,88,0,136,0,184,0,232,0
spriteY: .byte 100,0,100,0,100,0,100,0,142,0,142,0,142,0,142,0
.errorif * >= $2000, "Code overlaps animation buffers"

* = $2800 "Original ECM pattern font"
.fill 64*8, mod(floor(i/8)+mod(i,8),8)==0 ? $81 : (mod(i,8)==0 ? $ff : $00)
* = $3000 "Prepared compressed animation"
#import "build/frames.asm"
.errorif * >= $d000, "Animation overlaps I/O"
