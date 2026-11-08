// Original drive-assisted BRR cube. No Boo code, data or original artwork.
// Reusable scalar tables feed LIVE geometry; the1541 divides/selects ranks.
.label uploadPointer=$fb
.label markerPointer=$f0
.label outputPointer=$f2
.label stopPointer=$f4
.label rowStep=$26
.var drive=LoadBinary("drive/build/example.prg")
.const DRIVE_BYTES=drive.getSize()-2
.const MARKERS=$4000
.const HEIGHT=84
.const WIDTH=72
.const CELL_BYTES=7
.var screens=List().add($0400,$0800)
.errorif mod(DRIVE_BYTES,32)!=0,"Drive upload needs whole32-byte packets"
BasicUpstart2(start)
*=$6000 "Live cube, own IEC transport and sprite display"
start:
    lda #$37
    sta $01
    lda #0
    sta $d020
    sta $d021
    jsr $e544
    jsr uploadDrive
    sei
    cld
    lda #$7f
    sta $dc0d
    sta $dd0d
    lda $dc0d
    lda $dd0d
    lda #$35
    sta $01
    lda #$3f
    sta $dd02
    lda #3
    sta $dd00
    lda #$18
    sta $d011
    lda #8
    sta $d016
    lda #$1e
    sta $d018
    lda #0
    sta $d015
    sta $d01b
    ldx #0
!clear:
    .for (var screen=0;screen<2;screen++) {
        .for (var page=0;page<4;page++) { sta screens.get(screen)+page*256,x }
    }
    .for (var page=0;page<16;page++) { sta $2000+page*256,x }
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    inx
    beq !cleared+
    jmp !clear-
!cleared:
    ldx #7
!emptyGlyph:
    sta $3800,x
    dex
    bpl !emptyGlyph-
    .for (var sprite=0;sprite<6;sprite++) {
        lda #((40+48*sprite)&255)
        sta $d000+sprite*2
        lda #13
        sta $d027+sprite
    }
    lda #6
    sta $d025
    lda #3
    sta $d026
    lda #$20
    sta $d010
    lda #$3f
    sta $d017
    sta $d01c
    sta $d01d
    lda #<irq
    sta $fffe
    lda #>irq
    sta $ffff
    lda #<nmi
    sta $fffa
    lda #>nmi
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
    cli
nextPose:
    jsr transformCube
    jsr prepareRequest
requestPrepared:
    lda #0
    sta wireIndex
    lda #1
    sta wireState
!waitResponse:
    lda wireState
    cmp #4
    bne !waitResponse-
driveResponseReady:
    lda wireResponse+1
    cmp requestCount
    bne protocolFault
    lda publicationCounter
    clc
    adc #1
    cmp wireResponse
    bne protocolFault
    lda #0
    sta wireState
    jsr renderCube
renderComplete:
    lda phase
    sta pendingPhase
    lda #1
    sta renderReady
!publication:
    lda renderReady
    bne !publication-
    inc phase
    lda phase
    and #63
    sta phase
    jmp nextPose
protocolFault:
    lda #2
    sta $d020
    jmp protocolFault
irq:
    pha
    txa
    pha
    tya
    pha
    jmp (irqPart)
.macro NextPart(address,line) {
    lda #<address
    sta irqPart
    lda #>address
    sta irqPart+1
    lda #line
    sta $d012
    jmp irqReturn
}
displayTop:
    lda renderReady
    beq !front+
    lda frontBuffer
    eor #1
    sta frontBuffer
    lda pendingPhase
    sta shownPhase
    inc publicationCounter
    bne !published+
    inc publicationCounter+1
!published:
    lda #0
    sta renderReady
!front:
    lda frontBuffer
    asl
    asl
    asl
    asl
    asl
    clc
    adc #$80
    sta frontPointer
    .for (var sprite=0;sprite<6;sprite++) {
        lda frontPointer
        clc
        adc #sprite
        sta $07f8+sprite
    }
    lda #$1e
    sta $d018
    lda #64
    .for (var sprite=0;sprite<6;sprite++) { sta $d001+sprite*2 }
    lda #$3f
    sta $d015
    jsr serviceWire
wireSlotComplete:
    NextPart(displayBand1,96)
displayBand1:
    lda #106
    .for (var sprite=0;sprite<6;sprite++) { sta $d001+sprite*2 }
    // Prepare the currently hidden pointer page before switching it at106.
    .for (var sprite=0;sprite<6;sprite++) {
        lda frontPointer
        clc
        adc #6+sprite
        sta $0bf8+sprite
    }
!wait:
    lda $d012
    cmp #106
    bne !wait-
    lda #$2e
    sta $d018
    NextPart(displayBand2,138)
displayBand2:
    lda #148
    .for (var sprite=0;sprite<6;sprite++) { sta $d001+sprite*2 }
    .for (var sprite=0;sprite<6;sprite++) {
        lda frontPointer
        clc
        adc #12+sprite
        sta $07f8+sprite
    }
!wait:
    lda $d012
    cmp #148
    bne !wait-
    lda #$1e
    sta $d018
    NextPart(displayBand3,180)
displayBand3:
    lda #190
    .for (var sprite=0;sprite<6;sprite++) { sta $d001+sprite*2 }
    .for (var sprite=0;sprite<6;sprite++) {
        lda frontPointer
        clc
        adc #18+sprite
        sta $0bf8+sprite
    }
!wait:
    lda $d012
    cmp #190
    bne !wait-
    lda #$2e
    sta $d018
    NextPart(displayEnd,240)
displayEnd:
    inc fieldCounter
    bne displayFrameComplete
    inc fieldCounter+1
displayFrameComplete:
    NextPart(displayTop,0)
irqReturn:
    lda #1
    sta $d019
    pla
    tay
    pla
    tax
    pla
nmi:
    rti
.import source "iec.asm"
.import source "geometry.asm"
.import source "render.asm"
.errorif *>$8000,"C64runtime overlaps embedded drive payload"
*=$8000 "Own1541binary, bootstrapped through M-W/M-E"
drivePayload: .fill DRIVE_BYTES,drive.get(i+2)
*=$4800 "Reusable arithmetic and sprite layout tables"
sineUnit: .fill 256,round(64*sin(i*2*PI/256))&255
quarterSquares: .fill 256,floor((i<128 ? i : i-256)*(i<128 ? i : i-256)/256)
pitchMotion: .fill 64,round(32+12*sin(i*2*PI/64))
modelX: .fill 8,(i&1)!=0 ? 15 : -15
modelY: .fill 8,(i&2)!=0 ? 15 : -15
modelZ: .fill 8,(i&4)!=0 ? 15 : -15
edgeFirst: .byte 0,2,4,6,0,1,4,5,0,1,2,3
edgeLast: .byte 1,3,5,7,2,3,6,7,4,5,6,7
faceEdges: .byte 4,10,6,8,5,11,7,9,0,9,2,8,1,11,3,10,0,5,1,4,2,7,3,6
faceColors: .byte 1,1,2,2,3,3
rowMarkerLo: .fill HEIGHT,<(MARKERS+i*18)
rowMarkerHi: .fill HEIGHT,>(MARKERS+i*18)
rowSpriteLo: .fill HEIGHT,<(floor(i/21)*384+mod(i,21)*3)
rowSpriteHi: .fill HEIGHT,>(floor(i/21)*384+mod(i,21)*3)
columnSpriteLo: .fill 18,<(floor(i/3)*64+mod(i,3))
columnSpriteHi: .fill 18,>(floor(i/3)*64+mod(i,3))
markerMasks:
    .for (var delta=0;delta<4;delta++) { .for (var lane=0;lane<4;lane++) { .byte delta<<(6-lane*2) } }
edgeTraceLo: .fill 12,<(allTraces+i*HEIGHT)
edgeTraceHi: .fill 12,>(allTraces+i*HEIGHT)
repeatColor: .byte $00,$55,$aa,$ff
prefixTable:
    .for (var value=0;value<256;value++) {
        .var c=0
        .var result=0
        .for (var lane=0;lane<4;lane++) {
            .eval c=c^((value>>(6-lane*2))&3)
            .eval result=result|(c<<(6-lane*2))
        }
        .byte result
    }
.errorif *>$5000,"Tables overlap live state"
*=$5000 "Live geometry, request and renderer state"
projectedX: .fill 8,0
projectedY: .fill 8,0
rotatedX: .fill 8,0
rotatedY: .fill 8,0
rotatedZ: .fill 8,0
faceVisible: .fill 6,0
edgeColors: .fill 12,0
requestEdges: .fill 12,0
requestCount: .byte 0
phase: .byte 0
shownPhase: .byte 0
pendingPhase: .byte 0
frontBuffer: .byte 0
renderReady: .byte 0
publicationCounter: .word 0
fieldCounter: .word 0
irqPart: .word displayTop
frontPointer: .byte $80
sinYaw: .byte 0
cosYaw: .byte 0
sinPitch: .byte 0
cosPitch: .byte 0
normalZ: .fill 3,0
factor: .byte 0
multiplicand: .byte 0
productSum: .byte 0
yawX: .byte 0
yawZ: .byte 0
pitchY: .byte 0
pitchZ: .byte 0
term: .byte 0
faceIndex: .byte 0
faceCursor: .byte 0
faceColor: .byte 0
edgeIndex: .byte 0
packetIndex: .byte 0
leftX: .byte 0
leftY: .byte 0
rightX: .byte 0
rightY: .byte 0
drawBaseHi: .byte 0
requestIndex: .byte 0
rowIndex: .byte 0
columnIndex: .byte 0
markerDelta: .byte 0
markerLane: .byte 0
markerValue: .byte 0
fillCarry: .byte 0
fillByte: .byte 0
endpointActual: .byte 0
stopRow: .byte 0
blocksRemaining: .byte 0
writeAddress: .word $0300
writeCommand: .text "M-W"
executeCommand: .text "M-E"
    .word $0300
wireState: .byte 0
wireIndex: .byte 0
wireBudget: .byte 0
wireByte: .byte 0
wireOutput: .byte 0
packetLength: .byte 0
responseLength: .byte 0
wirePacket: .fill 49,0
wireResponse: .fill 26,0
allTraces: .fill 12*HEIGHT,0
.errorif *>$5800,"State overlaps BRRgenerated cells"
.function Reverse(value) {
    .var result=0
    .for (var bit=0;bit<8;bit++) { .eval result=result|(((value>>bit)&1)<<(7-bit)) }
    .return result
}
*=$5800 "Generated direct-position BRRcells"
brrCells:
    .for (var row=0;row<HEIGHT;row++) {
        sta allTraces+row
        cpx #Reverse(row)+1
        adc rowStep
    }
brrTerminal:
    jmp brrDone
