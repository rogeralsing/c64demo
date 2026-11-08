// Original nonconvex square-frame prism. No Next Level source or artwork.
// Live geometry and shared exact edges feed runtime-generated span writers.
.label codePointer=$f0
.label addressPointer=$f2
.label tablePointer=$f4
.label leftMask=$20
.label rightMask=$21
.label spanMask=$22
.label ink=$23
.const DISPATCH_A_LO=$8000
.const DISPATCH_A_HI=$8100
.const DISPATCH_B_LO=$8200
.const DISPATCH_B_HI=$8300
.const GENERATED=$9000
.const OUTER=22
.const INNER=10
.const DEPTH=7
BasicUpstart2(start)
*=$5000 "Original nonconvex runtime and span generator"
start:
    sei
    cld
    lda #$7f
    sta $dc0d
    sta $dd0d
    lda $dc0d
    lda $dd0d
    lda #$35
    sta $01
    lda #0
    sta $d011
    sta $d015
    sta $d01b
    sta $d01c
    sta $d01d
    sta $d020
    sta $d021
    sta $d01a
    sta frontBuffer
    sta renderReady
    sta phase
    sta publicationCounter
    sta publicationCounter+1
    sta fieldCounter
    sta fieldCounter+1
    ldx #0
!screen:
    sta $0400,x
    sta $0500,x
    sta $0600,x
    sta $0700,x
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    inx
    bne !screen-
    .for (var row=0;row<16;row++) {
        .for (var column=0;column<16;column++) {
            lda #column*16+row
            sta $0400+(4+row)*40+12+column
            lda #9
            sta $d800+(4+row)*40+12+column
        }
    }
    ldx #0
!background:
    .for (var page=0;page<8;page++) {
        lda background+page*256,x
        sta $2000+page*256,x
        sta $2800+page*256,x
    }
    inx
    bne !background-
    jsr generateSpans
generationComplete:
    lda #3
    sta $dd02
    sta $dd00
    lda #6
    sta $d022
    lda #3
    sta $d023
    lda #$18
    sta $d016
    sta $d018
    lda #$1b
    sta $d011
    lda #<irqTop
    sta $fffe
    lda #>irqTop
    sta $ffff
    lda #<nmi
    sta $fffa
    lda #>nmi
    sta $fffb
    lda #0
    sta $d012
    lda #1
    sta $d019
    sta $d01a
    cli
nextScene:
    jsr transformVertices
    jsr cullTriangles
geometryPrepared:
    jsr renderScene
renderComplete:
    lda phase
    sta pendingPhase
    lda #1
    sta renderReady
!wait:
    lda renderReady
    bne !wait-
    inc phase
    lda phase
    and #63
    sta phase
    jmp nextScene

irqTop:
    pha
    txa
    pha
    tya
    pha
    lda renderReady
    beq !unchanged+
publication:
    lda frontBuffer
    eor #1
    sta frontBuffer
    asl
    ora #$18
    sta $d018
    lda pendingPhase
    sta shownPhase
    inc publicationCounter
    bne !counter+
    inc publicationCounter+1
!counter:
    lda #0
    sta renderReady
!unchanged:
    lda #<irqEnd
    sta $fffe
    lda #>irqEnd
    sta $ffff
    lda #252
    sta $d012
    jmp irqReturn
irqEnd:
    pha
    txa
    pha
    tya
    pha
    inc fieldCounter
    bne displayFrameComplete
    inc fieldCounter+1
displayFrameComplete:
    lda #<irqTop
    sta $fffe
    lda #>irqTop
    sta $ffff
    lda #0
    sta $d012
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

.import source "geometry.asm"
.import source "span-generator.asm"
.import source "render.asm"
.errorif *>$7000,"Runtime overlaps shared edge sampler"
*=$7000 "Shared exact boundary sampler, transposed to horizontal spans"
.import source "../lib/polygon-edges.asm"

.function Quad(a,b,c,d) { .return List().add(a,b,c,d) }
.var quads=List()
.for (var i=0;i<4;i++) { .eval quads.add(Quad(4+i,12+i,12+((i+1)&3),4+((i+1)&3))) }
.for (var i=0;i<4;i++) { .eval quads.add(Quad(i,(i+1)&3,8+((i+1)&3),8+i)) }
.for (var i=0;i<4;i++) { .eval quads.add(Quad(i,4+i,4+((i+1)&3),(i+1)&3)) }
.for (var i=0;i<4;i++) { .eval quads.add(Quad(8+i,8+((i+1)&3),12+((i+1)&3),12+i)) }
*=$3000 "Scalar arithmetic and original closed genus-one mesh"
sineUnit: .fill 256,round(64*sin(i*2*PI/256))&255
quarterSquares: .fill 256,floor((i<128 ? i : i-256)*(i<128 ? i : i-256)/256)
depthFactors: .fill 128,round(112*64/(144+i-64))
yawMotion: .fill 64,round(32+18*sin(i*2*PI/64))
pitchMotion: .fill 64,round(18+14*sin(i*2*PI/64+0.4))
.var xs=List().add(-1,1,1,-1)
.var ys=List().add(-1,-1,1,1)
modelX: .fill 16,xs.get(i&3)*((i&4)==0 ? OUTER : INNER)
modelY: .fill 16,ys.get(i&3)*((i&4)==0 ? OUTER : INNER)
modelZ: .fill 16,i<8 ? -DEPTH : DEPTH
triangleVertices:
    .for (var face=0;face<16;face++) {
        .var quad=quads.get(face)
        .byte quad.get(0),quad.get(1),quad.get(2),quad.get(0),quad.get(2),quad.get(3)
    }
triangleColors: .fill 32,i<8 ? 2 : (i<16 ? 1 : 3)
leftMasks: .byte $ff,$3f,$0f,$03
rightMasks: .byte $c0,$f0,$fc,$ff
repeatColor: .byte $00,$55,$aa,$ff
.align $100
wideSquaresLo: .fill 256,<floor(i*i/4)
wideSquaresHi: .fill 256,>floor(i*i/4)
.errorif *>$3600,"Tables overlap live state"

*=$3600 "Live geometry and renderer state"
projectedX: .fill 16,0
projectedY: .fill 16,0
rotatedX: .fill 16,0
rotatedY: .fill 16,0
rotatedZ: .fill 16,0
triangleVisible: .fill 32,0
phase: .byte 0
shownPhase: .byte 0
pendingPhase: .byte 0
frontBuffer: .byte 0
drawBuffer: .byte 0
renderReady: .byte 0
publicationCounter: .word 0
fieldCounter: .word 0
sinYaw: .byte 0
cosYaw: .byte 0
sinPitch: .byte 0
cosPitch: .byte 0
factor: .byte 0
multiplicand: .byte 0
productSum: .byte 0
yawX: .byte 0
yawZ: .byte 0
pitchY: .byte 0
pitchZ: .byte 0
term: .byte 0
triangleIndex: .byte 0
vertexA: .byte 0
vertexB: .byte 0
vertexC: .byte 0
dx1: .byte 0
dy1: .byte 0
dx2: .byte 0
dy2: .byte 0
firstProduct: .word 0
areaLo: .byte 0
areaHi: .byte 0
wideSign: .byte 0
wideLeft: .byte 0
wideSum: .word 0
wideProduct: .word 0
minimumY: .byte 0
maximumY: .byte 0
currentRow: .byte 0
lineX0: .byte 0
lineY0: .byte 0
lineX1: .byte 0
lineY1: .byte 0
boundaryColor: .byte 1
spanIndex: .byte 0
genBuffer: .byte 0
genBaseHi: .byte 0
genLeft: .byte 0
genRight: .byte 0
genColumn: .byte 0
genInterior: .byte 0
generationEnd: .word 0
.errorif *>$3800,"Live state exceeds reserved space"
*=$4000 "Original background grid, not animated screen poses"
background:
    .for (var column=0;column<16;column++) {
        .for (var y=0;y<128;y++) {
            .var value=0
            .for (var lane=0;lane<4;lane++) {
                .var x=column*4+lane
                .if (((x&7)==0 && (y&7)==0) || (y==64 && (x&3)<2) || (x==32 && (y&3)==0)) {
                    .eval value=value|(1<<(6-lane*2))
                }
            }
            .byte value
        }
    }
*=$4800 "Live prepared horizontal crossings"
spanLeft: .fill 128,$ff
spanRight: .fill 128,0
*=$8000 "Runtime-generated endpoint-byte dispatch pointers"
    .fill 1024,0
