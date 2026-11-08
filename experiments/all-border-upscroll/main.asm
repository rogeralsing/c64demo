// Original all-border sprite upscroll; not The Hat's unknown implementation.
BasicUpstart2(start)
*=$1000 "Initialization and stable bootstrap"
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
    sta $d017
    sta $d01b
    sta $d01c
    sta $d020
    sta $d021
    sta $d418
    // Copy the staging bank toVIC bank3, including RAM underI/O andROM.
    lda #0
    sta $02
    sta $04
    lda #$80
    sta $03
    lda #$c0
    sta $05
    lda #$34
    sta $01
    ldx #64
    ldy #0
!bankByte:
    lda ($02),y
    sta ($04),y
    iny
    bne !bankByte-
    inc $03
    inc $05
    dex
    bne !bankByte-
    lda #$35
    sta $01
    lda $dd02
    ora #3
    sta $dd02
    lda #2
    sta $dd00
    lda #$02
    sta $d018
    lda #8
    sta $d016
    lda #$7b
    sta $d011
    // Prime the vertical latch with one actual screen-on frame.
!high:
    bit $d011
    bpl !high-
!low:
    bit $d011
    bmi !low-
!line249:
    lda $d012
    cmp #249
    bne !line249-
    lda #$73
    sta $d011
!line253:
    lda $d012
    cmp #253
    bne !line253-
    lda #$6b
    sta $d011
    .for (var sprite=0;sprite<8;sprite++) {
        lda #<(48*sprite)
        sta $d000+sprite*2
        lda #60
        sta $d001+sprite*2
        lda spriteColors+sprite
        sta $d027+sprite
    }
    lda #$c0
    sta $d010
    lda #$ff
    sta $d01d
    sta $d015
    lda #<firstIRQ
    sta $fffe
    lda #>firstIRQ
    sta $ffff
    lda #52
    sta $d012
    lda #1
    sta $d019
    sta $d01a
    cli
idle:
    jmp idle

.align $100
firstIRQ:
    pha
    txa
    pha
    tya
    pha
    lda #<secondIRQ
    sta $fffe
    lda #>secondIRQ
    sta $ffff
    inc $d012
    lda #1
    sta $d019
    tsx
    cli
    .fill 8,$ea
secondIRQ:
    txs
    ldx #8
!delay:
    dex
    bne !delay-
    bit $00
    lda $d012
    cmp $d012
    beq !stable+
!stable:
stableStart:
    lda #0
    sta $d01a
    ldx #0
    ldy #62
    .fill 22,$ea
    bit $00
    jmp prelude

spriteColors: .byte 3,14,7,1,10,8,5,4
.align $100
// Row31 is blank; alias bank1 row7 so bank3 IRQ vectors are never pointers.
rowControl: .fill 256,(i&31)==31 ? $72 : (((i&15)<<4)|((i&16)==0 ? 2 : 0))
.errorif *>$1400,"Bootstrap overlaps raster kernel"

*=$1400 "Bounded raster program"
.var tail76Address=0
prelude:
    .for (var line=55;line<60;line++) {
        .fill 30,$ea
        bit $00
    }
    .fill 25,$ea
    dec $d016
    // Start all DMA streams normally, then crunch45->$35 at line76.
    .for (var line=61;line<=76;line++) {
        sta $d017,x
        lda #(line<75 ? 0 : $ff)
        sta $d017
        lda #8
        sta $d016
        lda rowControl,y
        sta $d018
        sta $dd00
        iny
        lda #0
        .fill 2,$ea
        bit $00
        .if (line==76) {
            .eval tail76Address=*
            dec $d016
        } else { dec $d016 }
    }

.label tail76=tail76Address
.var frameSite=0
.var bottomBorderSite=0
.var phaseSite=0
.var crunchSites=List()
.var borderSites=List()
.var lineNumbers=List()
    .for (var index=0;index<312;index++) {
        .var line=mod(77+index,312)
        .eval lineNumbers.add(line)
        .eval crunchSites.add(*)
        .if (line==289) {
            .eval frameSite=*
        }
        sta $d017,x
        lda #$ff
        sta $d017
        lda #8
        sta $d016
        lda rowControl,y
        sta $d018
        sta $dd00
        .if (line==249 || line==252) {
            .if (line==249) { .eval bottomBorderSite=*+1 }
            lda #(line==249 ? $63 : $6b)
            sta $d011,x
            iny
            lda #0
        } else {
            .if (line==309) {
                iny
                lda #0
                inc nextPhase,x
            } else {
                .if (line==310) {
                    .eval phaseSite=*+1
                    ldy #0
                    lda #0
                    .fill 2,$ea
                    bit $00
                } else {
                    iny
                    lda #0
                    .fill 2,$ea
                    .if (line==76) {
                        jmp tail76
                    } else { bit $00 }
                }
            }
        }
        .if (line!=76) {
            .eval borderSites.add(*)
            dec $d016
        } else { .eval borderSites.add(tail76) }
    }
.label bottomBorderValue=bottomBorderSite
.label nextPhase=phaseSite
.label framePresented=frameSite
.errorif *>=$4000,"Raster program overlaps sprite banks"
*=$080e "Native observation address tables"
crunchLo: .fill 312,<crunchSites.get(i)
crunchHi: .fill 312,>crunchSites.get(i)
borderLo: .fill 312,<borderSites.get(i)
borderHi: .fill 312,>borderSites.get(i)
rasterLines: .fill 312,lineNumbers.get(i)

*=$4000 "Original frozen-row text bank1"
    .import binary "build/bank1.bin"
*=$8000 "Original bank3 data staged belowI/O"
    .import binary "build/bank2.bin"
