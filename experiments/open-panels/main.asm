// Six detached, two-sided cube-face panels on a common rotated supporting box.
// A-entry boundaries carry delta1; B-exit boundaries carry delta3. Bitmap
// selectors01/10 alias the A tone, so actual A/B overlap retains opaque A priority.
.label markerPointer = $f0
.label commandPointer = $f2

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
    lda $dd02
    ora #3
    sta $dd02
    lda #3
    sta $dd00
    lda #$3b
    sta $d011
    lda #$18
    sta $d016
    sta $d018
    ldx #0
!attributes:
    .for (var page=0; page<3; page++) {
        lda screenAttributes+page*256,x
        sta $0400+page*256,x
        sta $5c00+page*256,x
        lda colorAttributes+page*256,x
        sta $d800+page*256,x
    }
    inx
    bne !attributes-
    ldx #0
!lastAttributes:
    lda screenAttributes+768,x
    sta $0700,x
    sta $5f00,x
    lda colorAttributes+768,x
    sta $db00,x
    inx
    cpx #232
    bne !lastAttributes-
    ldx #0
    lda #0
!clear:
    .for (var page=0; page<32; page++) {
        sta $2000+page*256,x
        sta $6000+page*256,x
    }
    .for (var page=0; page<12; page++) { sta $4000+page*256,x }
    inx
    beq !cleared+
    jmp !clear-
!cleared:

nextPose:
    ldx pose
    lda posePointersLo,x
    sta commandPointer
    lda posePointersHi,x
    sta commandPointer+1
    lda #6
    sta panelsLeft
!panel:
    ldy #0
    lda (commandPointer),y
    sta boundaryColor
    lda #0
    sta edgeIndex
!edge:
    ldx edgeIndex
    ldy edgeOffsets,x
    lda (commandPointer),y
    sta lineX0
    iny
    lda (commandPointer),y
    sta lineY0
    ldy nextOffsets,x
    lda (commandPointer),y
    sta lineX1
    iny
    lda (commandPointer),y
    sta lineY1
    jsr drawBoundary
    inc edgeIndex
    lda edgeIndex
    cmp #4
    bne !edge-
    lda commandPointer
    clc
    adc #9
    sta commandPointer
    bcc !pointer+
    inc commandPointer+1
!pointer:
    dec panelsLeft
    bne !panel-
markersReady:
    jsr fillBitmap
!waitHigh:
    bit $d011
    bpl !waitHigh-
!waitLow:
    bit $d011
    bmi !waitLow-
    lda drawD018
    sta $d018
    lda drawBank
    sta $dd00
!scanout:
    bit $d011
    bpl !scanout-
framePresented:
    inc pose
    lda pose
    and #63
    sta pose
    lda drawBitmapHi
    eor #$40
    sta drawBitmapHi
    lda drawBank
    eor #1
    sta drawBank
    lda drawD018
    eor #$60
    sta drawD018
    jmp nextPose

// Storage adapter for the shared exact half-open crossing sampler.
plotBoundaryMarker:
    sta markerColor
    txa
    cmp #96
    bcs !outside+
    cpy #128
    bcs !outside+
    sty markerRow
    and #3
    sta markerLane
    lda markerColor
    asl
    asl
    ora markerLane
    tay
    lda pairMasks,y
    sta markerMask
    txa
    lsr
    lsr
    tax
    lda markerColumnLo,x
    sta markerPointer
    lda markerColumnHi,x
    sta markerPointer+1
    ldy markerRow
    lda (markerPointer),y
    eor markerMask
    sta (markerPointer),y
    rts
!outside:
    inc markerOverflow
    rts

fillBitmap:
    lda #0
    sta fillColumn
!column:
    ldx fillColumn
    lda markerColumnLo,x
    sta markerPointer
    lda markerColumnHi,x
    sta markerPointer+1
    lda columnOffsets,x
    tax
    ldy #0
    lda drawBitmapHi
    cmp #$20
    beq !bankA+
    lda #0
    jsr fillB
    jmp !reset+
!bankA:
    lda #0
    jsr fillA
!reset:
    // Markers are transition data only; reset the complete column after use.
    ldy #127
    lda #0
!clear:
    sta (markerPointer),y
    dey
    bpl !clear-
    inc fillColumn
    lda fillColumn
    cmp #24
    bne !column-
    rts

.macro FillRows(bitmap) {
    .for (var row=0; row<128; row++) {
        eor (markerPointer),y
        sta bitmap+64+floor((36+row)/8)*320+mod(36+row,8),x
        iny
    }
    rts
}
fillA: FillRows($2000)
fillB: FillRows($6000)

lineX0: .byte 0
lineY0: .byte 0
lineX1: .byte 0
lineY1: .byte 0
boundaryColor: .byte 0
pose: .byte 0
panelsLeft: .byte 0
edgeIndex: .byte 0
drawBitmapHi: .byte $60
drawBank: .byte 2
drawD018: .byte $78
fillColumn: .byte 0
markerColor: .byte 0
markerLane: .byte 0
markerRow: .byte 0
markerMask: .byte 0
markerOverflow: .byte 0
edgeOffsets: .byte 1,3,5,7
nextOffsets: .byte 3,5,7,1
pairMasks: .byte 0,0,0,0,$40,$10,$04,$01,$80,$20,$08,$02,$c0,$30,$0c,$03
markerColumnLo: .fill 24, <($4000+i*128)
markerColumnHi: .fill 24, >($4000+i*128)
columnOffsets: .fill 24, i*8
posePointersLo: .fill 64, <(poseCommands+i*54)
posePointersHi: .fill 64, >(poseCommands+i*54)

.import source "../lib/polygon-edges.asm"
.errorif * > $2000, "Panel renderer code overlaps bitmap A"

* = $8000 "Prepared projected panels and layer labels, not filled frames"
poseCommands:
    .import binary "build/commands.bin"
.assert "Sixty-four six-panel command poses", *-poseCommands, 64*6*9

* = $9000 "Static local bitmap palettes with aliased A selectors"
screenAttributes: .fill 1000, mod(i,40)<20 ? $33 : $77
colorAttributes: .fill 1000, floor(i/40)<12 ? 4 : 14
.assert "Static attributes fit below BASIC ROM", * <= $a000, true
