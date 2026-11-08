// Collision pixels pack eight independent crunch decisions in hardware $D01F.
// The visible kernel reads/resets that register and feeds $D017 directly.
.const SYNC_PAD = 29
.label collisionLog = $c000

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
    sta $d01c
    sta $d01d
    sta $d418
    lda #$ff
    sta $d01b
    lda $dd02
    ora #3
    sta $dd02
    lda #2
    sta $dd00
    lda #$3b
    sta $d011
    lda #8
    sta $d016
    lda #$78
    sta $d018
    ldx #0
!screen:
    lda #0
    sta $5c00,x
    sta $5d00,x
    sta $5e00,x
    sta $5f00,x
    sta collisionLog,x
    inx
    bne !screen-
    .for (var sprite=0; sprite<8; sprite++) {
        lda #<(88+24*sprite)
        sta $d000+2*sprite
        lda #60
        sta $d001+2*sprite
        lda #sprite
        sta $5ff8+sprite
        lda spriteColors+sprite
        sta $d027+sprite
    }
    lda #$80
    sta $d010
    jsr prepareHolds
    lda #<firstIRQ
    sta $fffe
    lda #>firstIRQ
    sta $ffff
    lda #52
    sta $d012
    lda #1
    sta $d019
    sta $d01a
    lda #$ff
    sta $d015
    cli
idle:
    jmp idle

prepareHolds:
    ldx #0
!column:
    txa
    asl
    asl
    asl
    clc
    adc phase
    and #63
    tay
    lda holdCurve,y
    sta holdOffsets,x
    inx
    cpx #8
    bne !column-
    ldy #0
!row:
    sty holdRow
    lda #0
    sta holdValue
    ldx #0
!bit:
    lda holdOffsets,x
    cmp holdRow
    beq !skip+
    bcc !skip+
    lda holdValue
    ora bitMasks,x
    sta holdValue
!skip:
    inx
    cpx #8
    bne !bit-
    ldy holdRow
    lda holdValue
    sta holdMasks,y
    iny
    cpy #7
    bne !row-
    rts

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
    lda #<firstIRQ
    sta $fffe
    lda #>firstIRQ
    sta $ffff
    lda #52
    sta $d012
    lda #1
    sta $d019
    ldx #0
    ldy #0
    .fill floor(SYNC_PAD/2)-1,$ea
    bit $00
    jmp prelude

kernelFinished:
    lda #0
    sta $d015
    sta $d017
    lda #$3b
    sta $d011
!bottom:
    bit $d011
    bpl !bottom-
framePresented:
    inc phase
    lda phase
    and #63
    sta phase
    jsr prepareHolds
    lda #$ff
    sta $d015
    pla
    tay
    pla
    tax
    pla
    rti

phase: .byte 0
holdRow: .byte 0
holdValue: .byte 0
bootstrapWritten: .byte 0
holdOffsets: .fill 8,0
holdMasks: .fill 7,0
bitMasks: .byte 1,2,4,8,16,32,64,128
spriteColors: .byte 3,4,5,14,8,10,7,1
holdCurve: .fill 64, round(3.5+3.5*sin(i*2*PI/64))
.errorif * > $2000, "Setup code overlaps unused low bitmap memory"

* = $4000 "Original packed sprite artwork and collision control pixels"
    .import binary "build/sprites.bin"
* = $5c00 "Black foreground and background attributes"
    .fill 1024,0
* = $6000 "Hidden foreground stripes plus warmup/end masks"
    .import binary "build/background.bin"

* = $8000 "Own timed raster program"
prelude:
    // Full CPU lines before sprite DMA begins at raster60 cycle55.
    .for (var line=55; line<=60; line++) {
        .if (mod(line,2)==0) {
            .fill 23,$ea
            bit $00
            lda #($38 | (line & 7))
            sta $d011
            .if (line!=60) { .fill 4,$ea }
        } else {
            .fill 30,$ea
            bit $00
        }
    }

 .var crunchSites = List()
 .var sampledSites = List()
 .var appliedSites = List()
carpetKernel:
    .for (var line=61; line<=236; line++) {
        .eval crunchSites.add(*)
        // SHY abs,X: five-cycle NMOS operation, X=Y=0, write zero on cycle15.
        .byte $9c,$17,$d0
        lda $d01f
        .eval sampledSites.add(*)
        .if (line==75) {
            sta collisionLog+line-61
            lda #$ff
            sta $d017
            .eval appliedSites.add(*)
            .fill 11,$ea
            sta bootstrapWritten
        } else {
            .if (line<76) {
                bit $d017
            } else {
                .if (line==76 || line==77) {
                    lda holdMasks+line-76
                } else {
                    .if (line<=82) { ora holdMasks+line-76 }
                }
                sta $d017
            }
            .eval appliedSites.add(*)
            .if (mod(line,2)==0) {
                sta collisionLog+line-61
                .if (line>=76 && line<=82) { .fill 9,$ea } else { .fill 11,$ea }
                lda #($38 | (line & 7))
                sta $d011
            } else {
                .if (line>=76 && line<=82) { .fill 12,$ea } else { .fill 14,$ea }
                sta collisionLog+line-61
            }
        }
    }
    jmp kernelFinished
crunchLo: .fill 176,<crunchSites.get(i)
crunchHi: .fill 176,>crunchSites.get(i)
sampledLo: .fill 176,<sampledSites.get(i)
sampledHi: .fill 176,>sampledSites.get(i)
appliedLo: .fill 176,<appliedSites.get(i)
appliedHi: .fill 176,>appliedSites.get(i)
.errorif * > $a000, "Timed raster code exceeds its private RAM window"
