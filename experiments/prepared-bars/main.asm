// Prepared line paths select reusable angle-specific character fragments.
// Three hardware sprites have the separate job of foreground orbiting beacons.
.label destination = $f0

.var slopes = List().add(-2,-1,0,1,2)
.var angleOrder = List().add(0,1,2,3,4,3,2,1)

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
    sta $d020
    sta $d021
    sta $d017
    sta $d01b
    sta $d01c
    sta $d01d
    lda $dd02
    ora #3
    sta $dd02
    lda #2
    sta $dd00
    lda #$1b
    sta $d011
    lda #$08
    sta $d016
    lda #$02
    sta $d018
    lda #7
    sta $d015
    sta $d027
    lda #1
    sta $d028
    lda #10
    sta $d029
    ldx #0
!initialize:
    lda #0
    sta $4000,x
    sta $4100,x
    sta $4200,x
    sta $4300,x
    sta $4400,x
    sta $4500,x
    sta $4600,x
    sta $4700,x
    lda #3
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    inx
    bne !initialize-

nextImage:
    jsr drawBars
!waitHigh:
    bit $d011
    bpl !waitHigh-
!waitLow:
    bit $d011
    bmi !waitLow-
    jsr positionBeacons
    lda currentAngle
    asl
    clc
    adc #2
    ora screenSelect
    sta $d018
!scanout:
    bit $d011
    bpl !scanout-
displayComplete:
    inc phase
    lda drawScreenHi
    eor #4
    sta drawScreenHi
    lda screenSelect
    eor #$10
    sta screenSelect
    jmp nextImage

drawBars:
    ldx phase
    lda anglePath,x
    sta currentAngle
    tax
    lda slopeAddressLo,x
    sta slopeLookup+1
    lda slopeAddressHi,x
    sta slopeLookup+2
    lda upperAddressLo,x
    sta upperLookup+1
    lda upperAddressHi,x
    sta upperLookup+2
    lda lowerAddressLo,x
    sta lowerLookup+1
    lda lowerAddressHi,x
    sta lowerLookup+2
    lda drawScreenHi
    sta clear0+2
    clc
    adc #1
    sta clear1+2
    adc #1
    sta clear2+2
    adc #1
    sta clear3+2
    ldx #0
    lda #0
!clear:
clear0:
    sta $4400,x
clear1:
    sta $4500,x
clear2:
    sta $4600,x
clear3:
    sta $4700,x
    inx
    bne !clear-

    lda #>barPaths
    sta baseLookup+2
    lda #0
    sta bar
!bar:
    ldx phase
baseLookup:
    lda barPaths,x
    sta baseY
    lda #0
    sta column
!column:
    ldx column
slopeLookup:
    lda columnSlopes,x
    clc
    adc baseY
    pha
    and #7
    sta glyphPhase
    pla
    lsr
    lsr
    lsr
    tax
    lda screenRowsLo,x
    clc
    adc column
    sta destination
    lda screenRowsHi,x
    adc drawScreenHi
    sta destination+1
    ldx glyphPhase
    txa
    clc
    adc #9
    ldy #0
    sta (destination),y
upperLookup:
    lda upperPresent,x
    beq !lower+
    jsr pointerUp
    txa
    clc
    adc #1
    ldy #0
    sta (destination),y
    jsr pointerDown
!lower:
lowerLookup:
    lda lowerPresent,x
    beq !nextColumn+
    jsr pointerDown
    txa
    clc
    adc #17
    ldy #0
    sta (destination),y
!nextColumn:
    inc column
    lda column
    cmp #32
    bne !column-
    inc baseLookup+2
    inc bar
    lda bar
    cmp #5
    bne !bar-

    // Every matrix owns its own sprite pointer table, outside the visible cells.
    lda #$f8
    sta destination
    lda drawScreenHi
    clc
    adc #3
    sta destination+1
    ldy #0
    lda #$c0
    sta (destination),y
    iny
    lda #$c1
    sta (destination),y
    iny
    lda #$c2
    sta (destination),y
    rts

pointerUp:
    lda destination
    sec
    sbc #40
    sta destination
    lda destination+1
    sbc #0
    sta destination+1
    rts

pointerDown:
    lda destination
    clc
    adc #40
    sta destination
    lda destination+1
    adc #0
    sta destination+1
    rts

positionBeacons:
    .for (var sprite=0; sprite<3; sprite++) {
        lda phase
        clc
        adc #sprite*85
        tax
        lda beaconXLo,x
        sta $d000+sprite*2
        lda beaconY,x
        sta $d001+sprite*2
        lda beaconXHi,x
        .for (var shift=0; shift<sprite; shift++) { asl }
        .if (sprite!=0) { ora $d010 }
        sta $d010
    }
    rts

phase: .byte 0
currentAngle: .byte 0
drawScreenHi: .byte $44
screenSelect: .byte $10
baseY: .byte 0
bar: .byte 0
column: .byte 0
glyphPhase: .byte 0

screenRowsLo: .fill 25, <(i*40+4)
screenRowsHi: .fill 25, >(i*40+4)
slopeAddressLo: .fill 5, <(columnSlopes+i*32)
slopeAddressHi: .fill 5, >(columnSlopes+i*32)
upperAddressLo: .fill 5, <(upperPresent+i*8)
upperAddressHi: .fill 5, >(upperPresent+i*8)
lowerAddressLo: .fill 5, <(lowerPresent+i*8)
lowerAddressHi: .fill 5, >(lowerPresent+i*8)
columnSlopes: .fill 160, slopes.get(floor(i/32))*(mod(i,32)-16)
upperPresent: .fill 40, mod(i,8)+min(0,floor(slopes.get(floor(i/8))*7/8))-2<0 ? 1 : 0
lowerPresent: .fill 40, mod(i,8)+max(0,floor(slopes.get(floor(i/8))*7/8))+2>7 ? 1 : 0
.errorif * > $2000, "Code/tables overlap unused low-memory display space"

.function GlyphByte(index,slope) {
    .var glyph = floor(index/8)
    .var py = mod(index,8)
    .var result = 0
    .if (glyph>=1 && glyph<=24) {
        .var phase = mod(glyph-1,8)
        .var relativeRow = floor((glyph-1)/8)-1
        .for (var px=0; px<8; px++) {
            .var center = phase+floor(slope*px/8)
            .var ink = abs(relativeRow*8+py-center)<=2
            .eval result = result*2+(ink ? 1 : 0)
        }
    }
    .return result
}

* = $4800 "Five reusable angle-specific character sets"
angleFonts:
    .for (var angle=0; angle<5; angle++) {
        .fill 2048, GlyphByte(i,slopes.get(angle))
    }
.assert "Fonts end before sprite patterns", *, $7000

.function BeaconByte(index,sprite) {
    .var row = floor(index/3)
    .var result = 0
    .for (var bit=0; bit<8; bit++) {
        .var x = mod(index,3)*8+bit
        .var radius = abs(2*x-23)+abs(2*row-20)
        .var outline = radius>=15 && radius<=19
        .var center = (sprite==0 ? abs(2*x-23)<=1 : (sprite==1 ? row==10 : mod(x+row,6)==0)) && radius<15
        .eval result = result*2+((outline || center) ? 1 : 0)
    }
    .return result
}
beaconPatterns:
    .for (var sprite=0; sprite<3; sprite++) {
        .fill 63, BeaconByte(i,sprite)
        .byte 0
    }

* = $8000 "Prepared path coordinates"
barPaths:
    .for (var bar=0; bar<5; bar++) {
        .fill 256, round(44+26*bar+6*sin((i+bar*29)*2*PI/256))
    }
anglePath: .fill 256, angleOrder.get(mod(floor(i/8),8))
beaconXLo: .fill 256, <round(172+125*cos(i*2*PI/256))
beaconXHi: .fill 256, >round(172+125*cos(i*2*PI/256))
beaconY: .fill 256, round(138+78*sin(i*2*PI/256))
