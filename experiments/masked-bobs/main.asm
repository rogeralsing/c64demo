// A live masked bob over a horizontally mirrored, immutable half-background.
// The background uses 4,000 stored bytes for an 8,000-byte hires bitmap.
// Erasure restores the old 16x16 rectangle before the next masked AND/OR plot.

.label sourcePointer = $f4
.label bitmapPointer = $f6
.label temporary = $f8

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
    sta $d015
    sta $d020
    sta $d021
    lda #3
    sta $dd00
    lda #$3b
    sta $d011
    lda #$08
    sta $d016
    lda #$18
    sta $d018
    ldx #0
    lda #$1b
!colors:
    sta $0400,x
    sta $0500,x
    sta $0600,x
    sta $0700,x
    inx
    bne !colors-

    lda #0
    sta row
!backgroundRow:
    lda #0
    sta column
!backgroundColumn:
    jsr backgroundByte
    sta temporary
    jsr bitmapAddress
    lda temporary
    ldy #0
    sta (bitmapPointer),y
    inc column
    lda column
    cmp #40
    bne !backgroundColumn-
    inc row
    lda row
    cmp #200
    bne !backgroundRow-

    lda #0
    sta phase
    lda xPositions
    sta bobX
    sta oldX
    lda yPositions
    sta bobY
    sta oldY
    jsr plotBob

presented:
    lda #0
    sta stripe
    // Restore behind the old scanout, then draw before the next one reaches
    // the bob. Starting at line 240 keeps the work across the frame wrap.
!waitLower:
    lda $d012
    cmp #240
    bne !waitLower-

!restoreRow:
    lda oldY
    clc
    adc stripe
    sta row
    lda oldX
    sta column
    jsr restoreByte
    inc column
    jsr restoreByte
    inc stripe
    lda stripe
    cmp #16
    bne !restoreRow-

    inc phase
    ldx phase
    lda xPositions,x
    sta bobX
    sta oldX
    lda yPositions,x
    sta bobY
    sta oldY
    jsr plotBob
    jmp presented

restoreByte:
    jsr backgroundByte
    sta temporary
    jsr bitmapAddress
    ldy #0
    lda temporary
    sta (bitmapPointer),y
    rts

// Read one byte from the immutable left half. Reflect bit order on the right.
backgroundByte:
    ldy row
    lda sourceRowsLo,y
    sta sourcePointer
    lda sourceRowsHi,y
    sta sourcePointer+1
    lda column
    cmp #20
    bcs !mirror+
    tay
    lda (sourcePointer),y
    rts
!mirror:
    eor #$ff
    clc
    adc #40
    tay
    lda (sourcePointer),y
    tax
    lda reversedBytes,x
    rts

// Native C64 hires layout: (y/8)*320 + (x/8)*8 + (y&7).
bitmapAddress:
    ldx column
    ldy row
    clc
    lda bitmapRowsLo,y
    adc columnOffsetsLo,x
    sta bitmapPointer
    lda bitmapRowsHi,y
    adc columnOffsetsHi,x
    sta bitmapPointer+1
    rts

plotBob:
    lda #0
    sta stripe
!row:
    lda bobY
    clc
    adc stripe
    sta row
    lda bobX
    sta column
    jsr bitmapAddress
    lda stripe
    asl
    tax
    ldy #0
    lda (bitmapPointer),y
    and bobMasks,x
    ora bobInk,x
    sta (bitmapPointer),y
    inc column
    jsr bitmapAddress
    lda stripe
    asl
    tax
    inx
    ldy #0
    lda (bitmapPointer),y
    and bobMasks,x
    ora bobInk,x
    sta (bitmapPointer),y
    inc stripe
    lda stripe
    cmp #16
    bne !row-
    rts

phase: .byte 0
bobX: .byte 0
bobY: .byte 0
oldX: .byte 0
oldY: .byte 0
row: .byte 0
column: .byte 0
stripe: .byte 0

xPositions: .fill 256, round(19 + 18*sin(i*2*PI/256))
yPositions: .fill 256, round(92 + 84*sin(i*4*PI/256))
bitmapRowsLo: .fill 200, <($2000+floor(i/8)*320+mod(i,8))
bitmapRowsHi: .fill 200, >($2000+floor(i/8)*320+mod(i,8))
sourceRowsLo: .fill 200, <(halfBackground+i*20)
sourceRowsHi: .fill 200, >(halfBackground+i*20)
columnOffsetsLo: .fill 40, <(i*8)
columnOffsetsHi: .fill 40, >(i*8)

.function ReverseBits(value) {
    .var result = 0
    .for (var bit=0; bit<8; bit++) {
        .eval result = result*2+((value >> bit)&1)
    }
    .return result
}
reversedBytes: .fill 256, ReverseBits(i)

.function BobByte(byteIndex, mask) {
    .var y = floor(byteIndex/2)
    .var result = 0
    .for (var bit=0; bit<8; bit++) {
        .var x = mod(byteIndex,2)*8+bit
        .var inside = (x-7.5)*(x-7.5)+(y-7.5)*(y-7.5) <= 56.25
        .var ink = inside && (mod(x+y,4) != 0)
        .eval result = result*2+((mask ? !inside : ink) ? 1 : 0)
    }
    .return result
}
bobMasks: .fill 32, BobByte(i,true)
bobInk: .fill 32, BobByte(i,false)
.errorif * > $2000, "Bob code and tables overlap bitmap"

* = $4000 "Immutable mirrored half-background"
halfBackground:
    .fill 4000, mod(floor(i/20),16)==0 ? $ff : (mod(i,20)==0 ? $80 : (mod(floor(i/20)+mod(i,20),8)==0 ? $18 : 0))
