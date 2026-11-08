// Original complementary packed-plane texture sampler inspired by EC.
// Every stored byte contains four multicolor pairs, not four sampled texels.
BasicUpstart2(start)

.const POSES = 16
.const PARAM_POINTER = $e0
.const ROW_AU = $e2
.const ROW_AV = $e4
.const ROW_BU = $e6
.const ROW_BV = $e8
.const PACKED_A = $ea
.var stores = List()

* = $1000 "Two-plane renderer setup and complete-buffer handoff"
start:
    sei
    cld
    lda #$35
    sta $01
    lda #$7f
    sta $dc0d
    sta $dd0d
    lda $dc0d
    lda $dd0d
    lda #0
    sta $d011
    sta $d015
    sta $d020
    sta $d021
    sta $d01a
    sta frontBuffer
    sta frontPose
    sta renderPose
    sta renderReady
    sta fieldCounter
    sta fieldCounter+1
    sta publicationCounter
    sta publicationCounter+1
    lda #1
    sta fieldParity
    lda #4
    sta $d022
    lda #6
    sta $d023
    lda #$18
    sta $d016
    lda $dd02
    ora #3
    sta $dd02
    lda #$81
    sta $dd00
    lda #$e8
    sta $d018

    ldx #0
!clear:
    lda #0
    .for (var base = $a0; base < $b8; base++) {
        sta base*$100,x
        sta (base+$40)*$100,x
    }
    lda #255
    .for (var page = 0; page < 4; page++) {
        sta $b800+page*$100,x
        sta $f800+page*$100,x
    }
    lda #9
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    inx
    beq !cleared+
    jmp !clear-
!cleared:
    .for (var row = 0; row < 24; row++) {
        ldx #0
        lda #mod(row,8)
    !column:
        sta $b800+40*row+4,x
        sta $f800+40*row+4,x
        clc
        adc #8
        inx
        cpx #31
        bne !column-
    }
    lda #$a0
    sta drawBase
    jsr renderScene
    lda #1
    sta renderPose
    lda #<irq
    sta $fffe
    lda #>irq
    sta $ffff
    lda #<nmiReturn
    sta $fffa
    lda #>nmiReturn
    sta $fffb
    lda #<displayTop
    sta irqPart
    lda #>displayTop
    sta irqPart+1
    lda #0
    sta $d012
    lda #1
    sta $d019
    sta $d01a
ready:
    cli
main:
    lda frontBuffer
    eor #1
    beq !bufferA+
    lda #$e0
    bne !draw+
!bufferA:
    lda #$a0
!draw:
    sta drawBase
    jsr renderScene
    lda renderPose
    sta pendingPose
    lda #1
    sta renderReady
!wait:
    lda renderReady
    bne !wait-
    inc renderPose
    lda renderPose
    and #POSES-1
    sta renderPose
    jmp main

.import source "display.asm"

frontBuffer: .byte 0
frontPose: .byte 0
renderPose: .byte 0
pendingPose: .byte 0
renderReady: .byte 0
fieldParity: .byte 1
fieldCounter: .word 0
publicationCounter: .word 0
irqPart: .word displayTop
drawBase: .byte $a0
renderRow: .byte 0
rowOffset: .byte 0
band: .byte 0
current: .fill 8,0
parameters: .fill 24,0

.assert "Setup ends before source planes", * <= $2000, true

.function TextureByte(u,v) {
    .var value = 0
    .for (var pair = 0; pair < 4; pair++) {
        .var x = 4*u+pair
        .var bit = mod(floor(x/8)+floor(v/2),2) ^ ((mod(x+v,13)<3) ? 1 : 0)
        .eval value = (value << 2) | (bit != 0 ? 2 : 0)
    }
    .return value
}
* = $2000 "Own high pair-bit plane, sixteen duplicated rows"
planeA:
    .fill $2000, TextureByte(mod(i,256),floor(i/512))
* = $4000 "Complementary low pair-bit plane"
planeB:
    .fill $2000, TextureByte(mod(i,256),floor(i/512)) >> 1

* = $6000 "Runtime column coordinates and scalar motion coefficients"
columnAU: .fill 62,0
columnAV: .fill 62,0
columnBU: .fill 62,0
columnBV: .fill 62,0
poseLow: .fill POSES, <(poseParameters+24*i)
poseHigh: .fill POSES, >(poseParameters+24*i)
poseParameters:
    .for (var pose = 0; pose < POSES; pose++) {
        .var angleA = pose*2*PI/POSES
        .var angleB = PI/4-pose*2*PI/POSES
        // Four horizontal and four vertical signed Q8 increments.
        .word round(192*cos(angleA)),round(96*sin(angleA))
        .word round(160*cos(angleB)),round(128*sin(angleB))
        .word round(-48*sin(angleA)),round(40*cos(angleA))
        .word round(-64*sin(angleB)),round(48*cos(angleB))
        .word mod($0340+pose*$1b3,65536),mod($0340+pose*$27d,65536)
        .word mod($f840+pose*$183,65536),mod($0740+pose*$19d,65536)
    }

* = $7000 "Live C64 fixed-point packed-plane sampling"
renderScene:
    ldx renderPose
    lda poseLow,x
    sta PARAM_POINTER
    lda poseHigh,x
    sta PARAM_POINTER+1
    ldy #23
!parameters:
    lda (PARAM_POINTER),y
    sta parameters,y
    dey
    bpl !parameters-
    ldx #7
    lda #0
!zero:
    sta current,x
    dex
    bpl !zero-
    ldx #0
!columns:
    .for (var coordinate = 0; coordinate < 4; coordinate++) {
        lda current+coordinate*2
        sta columnAU+coordinate*62,x
        lda current+coordinate*2+1
        sta columnAU+coordinate*62+31,x
        clc
        lda current+coordinate*2
        adc parameters+coordinate*2
        sta current+coordinate*2
        lda current+coordinate*2+1
        adc parameters+coordinate*2+1
        sta current+coordinate*2+1
    }
    inx
    cpx #31
    beq !columnsDone+
    jmp !columns-
!columnsDone:
    ldx #7
!origin:
    lda parameters+16,x
    sta ROW_AU,x
    dex
    bpl !origin-
    lda #0
    sta renderRow
    sta rowOffset
    sta band
    jsr patchDestinations
renderRows:
    ldy rowOffset
    .for (var column = 0; column < 31; column++) {
        // Fractional carry is preserved into each integer coordinate byte.
        lda columnAU+column
        clc
        adc ROW_AU
        lda columnAU+31+column
        adc #0
        sta !sampleA+ +1
        lda columnAV+column
        clc
        adc ROW_AV
        lda columnAV+31+column
        adc ROW_AV+1
        and #15
        asl
        clc
        adc #$20
        sta !sampleA+ +2
        ldx ROW_AU+1
    !sampleA:
        lda $2000,x
        sta PACKED_A
        lda columnBU+column
        clc
        adc ROW_BU
        lda columnBU+31+column
        adc #0
        sta !sampleB+ +1
        lda columnBV+column
        clc
        adc ROW_BV
        lda columnBV+31+column
        adc ROW_BV+1
        and #15
        asl
        clc
        adc #$40
        sta !sampleB+ +2
        ldx ROW_BU+1
    !sampleB:
        lda $4000,x
        ora PACKED_A
        .eval stores.add(*)
        sta $a000+column*64,y
    }
    .for (var coordinate = 0; coordinate < 4; coordinate++) {
        clc
        lda ROW_AU+coordinate*2
        adc parameters+8+coordinate*2
        sta ROW_AU+coordinate*2
        lda ROW_AU+coordinate*2+1
        adc parameters+9+coordinate*2
        sta ROW_AU+coordinate*2+1
    }
    inc renderRow
    lda renderRow
    cmp #96
    beq renderComplete
    lda rowOffset
    clc
    adc #2
    and #63
    sta rowOffset
    bne !next+
    inc band
    jsr patchDestinations
!next:
    jmp renderRows
renderComplete:
    rts

patchDestinations:
    lda band
    asl
    asl
    asl
    clc
    adc drawBase
    .for (var column = 0; column < 31; column++) {
        .if (mod(column,4)==0 && column!=0) {
            clc
            adc #1
        }
        sta stores.get(column)+2
    }
    rts
.assert "Sampler stays below visible character buffers", * <= $a000, true
