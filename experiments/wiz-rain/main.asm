// Own PAL AGSP/WIZ implementation. No Lunatico code or assets.
BasicUpstart2(start)
*=$1000 "Initialization and AGSP control"
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
    sta $d015
    sta $d01a
    sta $d020
    sta $d418
    sta $3fff
    lda #6
    sta $d021
    lda #14
    sta $d022
    lda #3
    sta $d023
    lda #$18
    sta $d016
    lda #$1c
    sta $d018
    lda $dd02
    ora #3
    sta $dd02
    lda #3
    sta $dd00
    ldx #0
!copy:
    .for (var page=0;page<4;page++) {
        lda initialMatrix+page*256,x
        sta $0400+page*256,x
        sta $0800+page*256,x
        lda #9
        sta $d800+page*256,x
    }
    inx
    bne !copy-
    lda #8
    sta workMatrixHi
    lda #1
    sta workLight
    jsr prepareView
    lda #<firstIRQ
    sta $fffe
    lda #>firstIRQ
    sta $ffff
    lda #45
    sta $d012
    lda #$1b
    sta $d011
    lda #1
    sta $d019
    sta $d01a
    cli
idle:
    jmp idle

prepareView:
    ldy phase
    lda viewX,y
    tax
    lda vspLo,x
    sta vspJump+1
    lda vspHi,x
    sta vspJump+2
    lda viewCrunch,y
    sta crunchCount
    lda #$7b
    ldx crunchCount
    bne !first+
    lda #$7c
!first:
    sta firstValue
    ldx #0
!row:
    txa
    clc
    adc #1
    cmp crunchCount
    bcc !active+
    lda idleValues,x
    jmp !store+
!active:
    lda activeValues,x
!store:
    sta lateValues,x
    inx
    cpx #29
    bne !row-
    lda #$78
    sta lateValues+28
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
    // Calibrated stable point: line47, zero-based cycle3.
    lda #$11
    sta $d011
vspJump:
    jmp $ffff

crunchPrelude:
    lda #66
!wait66:
    cmp $d012
    bne !wait66-
    lda firstValue
    sta $d011
    ldx #67
    lda #$7d
!wait67:
    cpx $d012
    bne !wait67-
lineCrunch:
    // Each slot is exactly63 CPU clocks; badlines are cancelled before14.
    // Active slots first enter display state with RC7, then abort RC reset.
    // Idle slots stay idle. Only active slots advance VCBASE by40.
    .var crunchSites=List()
    .for (var line=67;line<=95;line++) {
        .eval crunchSites.add(*)
        sta $d011
        .fill 12,$ea
        bit $00
        lda lateValues+line-67
        sta $d011
        .fill 11,$ea
        .if (line==95) { lda #$18 } else { lda #($78 | ((line+3)&7)) }
    }
displayStart:
    sta $d011
displayEnabled:
    lda #<firstIRQ
    sta $fffe
    lda #>firstIRQ
    sta $ffff
    lda #45
    sta $d012
    lda #1
    sta $d019
    jsr lightChunk
!bottom:
    bit $d011
    bpl !bottom-
framePresented:
    lda workReady
    beq !unpublished+
    lda workMatrixHi
    sta activeMatrixHi
    asl
    asl
    ora #$0c
    sta $d018
    lda workLight
    sta activeLight
    lda activeMatrixHi
    eor #$0c
    sta workMatrixHi
    lda activeLight
    clc
    adc #1
    and #15
    sta workLight
    lda #0
    sta workReady
!unpublished:
    inc phase
    lda phase
    and #15
    sta phase
    jsr prepareView
    lda #$1b
    sta $d011
    pla
    tay
    pla
    tax
    pla
    rti

// Central differences and signed light products execute on the C64.
// Forty-byte halos around heightAtlas provide the same modulo1024 topology.
lightChunk:
    .for (var pointer=0;pointer<4;pointer++) {
        .var delta=List().add(1,-1,40,-40).get(pointer)
        clc
        lda workIndex
        adc #<(heightAtlas+delta)
        sta $02+pointer*2
        lda workIndex+1
        adc #>(heightAtlas+delta)
        sta $03+pointer*2
    }
    lda workIndex
    sta $0a
    lda workIndex+1
    clc
    adc workMatrixHi
    sta $0b
    ldx workLight
    lda lightXHi,x
    sta lightXLoad+2
    lda lightYHi,x
    sta lightYLoad+2
    ldy #0
lightChunkStart:
!cell:
    lda ($02),y
    sec
    sbc ($04),y
    tax
lightXLoad:
    lda $5000,x
    sta $10
    lda ($06),y
    sec
    sbc ($08),y
    tax
lightYLoad:
    lda $5000,x
    clc
    adc $10
    clc
    adc #128
    tax
    lda shadeTable,x
    sta ($0a),y
    iny
    cpy #128
    bne !cell-
lightChunkFinished:
    clc
    lda workIndex
    adc #128
    sta workIndex
    lda workIndex+1
    adc #0
    and #3
    sta workIndex+1
    ora workIndex
    bne !pending+
    lda #1
    sta workReady
!pending:
    rts

phase: .byte 0
activeMatrixHi: .byte 4
workMatrixHi: .byte 8
activeLight: .byte 0
workLight: .byte 1
workReady: .byte 0
workIndex: .word 0
crunchCount: .byte 0
firstValue: .byte 0
lateValues: .fill 29,0
activeValues: .fill 29,$78|((68+i)&7)
idleValues: .fill 29,$78|((69+i)&7)
// Baseline viewport120; VSP removes x from120 and linecrunch adds40*n.
viewX: .fill 16,mod(40-mod(i*64,40),40)
viewCrunch: .fill 16,floor((i*64+mod(40-mod(i*64,40),40))/40)
lightXHi: .byte $54,$54,$54,$53,$52,$51,$50,$50,$50,$50,$50,$51,$52,$53,$54,$54
lightYHi: .byte $52,$53,$54,$54,$54,$54,$54,$53,$52,$51,$50,$50,$50,$50,$50,$51

.var vspSites=List()
.var vspFallingSites=List()
.for (var offset=0;offset<40;offset++) {
    .eval vspSites.add(*)
    .var delay=57+offset
    .if (mod(delay,2)==1) {
        .fill (delay-3)/2,$ea
        bit $00
    } else { .fill delay/2,$ea }
    lda #$7b
    .eval vspFallingSites.add(*)
    dec $d011
    inc $d011
    sta $d011
    jmp crunchPrelude
}
vspLo: .fill 40,<vspSites.get(i)
vspHi: .fill 40,>vspSites.get(i)
vspFallingLo: .fill 40,<vspFallingSites.get(i)
vspFallingHi: .fill 40,>vspFallingSites.get(i)
crunchLo: .fill 29,<crunchSites.get(i)
crunchHi: .fill 29,>crunchSites.get(i)
.errorif *>=$3000,"AGSP code overlaps font"

*=$3000 "Original multicolor luminance font"
    .import binary "build/font.bin"
*=$5fd8 "Original seamless WIZ height field with40-byte halos"
    .import binary "build/height-padded.bin"
.label heightAtlas=$6000
*=$5000 "Reusable signed light multiplication"
    .import binary "build/multiply.bin"
*=$5500 "Light quantization"
shadeTable:
    .import binary "build/shade.bin"
*=$5600 "Initial computed lighting"
initialMatrix:
    .import binary "build/initial.bin"
