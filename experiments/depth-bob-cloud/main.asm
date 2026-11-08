// Original prepared depth-bob cloud. No Next Level source or release assets.
// Host geometry; live shifted stamps, first-touch glyphs, OR merging and clears.
.label framePointer=$f0
.label coordinatePointer=$f2
.label patternPointer=$f4
.label screenPointer=$f6
.label glyphPointer=$f8
.label codePointer=$fa
.label mapPointer=$fc
.const PRIVATE_LIMIT=192
.const CLEAR_CODE=$7000
BasicUpstart2(start)
*=$1000 "Own point-stamp pipeline and shared display publication"
start:
    jsr initializeDisplay
    sei
    lda #0
    sta $d020
    sta $d021
    sta $d022
    sta $d023
    lda #8
    sta $d016
    ldx #0
!initialize:
    lda #0
    .for (var page=0;page<8;page++) {
        sta $2000+page*256,x
        sta $2800+page*256,x
    }
    .for (var page=0;page<2;page++) {
        lda staticFont+page*256,x
        sta $2600+page*256,x
        sta $2e00+page*256,x
    }
    .for (var page=0;page<4;page++) {
        lda baseScreen+page*256,x
        sta $0400+page*256,x
        sta $0c00+page*256,x
        lda baseColors+page*256,x
        sta $d800+page*256,x
    }
    inx
    beq !initialized+
    jmp !initialize-
!initialized:
    jsr generateClears
generationComplete:
    lda #$20
    sta frontFontHigh
    lda #4
    sta frontScreenHigh
    lda #0
    sta frontPose
    cli
nextScene:
    lda frontFontHigh
    cmp #$20
    bne !drawA+
    lda #$28
    sta drawFontHigh
    lda #$0c
    sta drawScreenHigh
    lda #$3a
    sta drawSelection
    lda clearB
    sta clearDispatch+1
    lda clearB+1
    sta clearDispatch+2
    jmp !clear+
!drawA:
    lda #$20
    sta drawFontHigh
    lda #4
    sta drawScreenHigh
    lda #$18
    sta drawSelection
    lda clearA
    sta clearDispatch+1
    lda clearA+1
    sta clearDispatch+2
!clear:
clearBegin:
    lda #0
clearDispatch:
    jsr $ffff
clearedBackBuffer:
    lda #1
    sta nextCode
    ldx poseUsed
    lda frameLo,x
    sta framePointer
    clc
    adc #9
    sta coordinatePointer
    lda frameHi,x
    sta framePointer+1
    adc #0
    sta coordinatePointer+1
    lda #0
    sta bucketIndex
!bucket:
    ldy bucketIndex
    lda (framePointer),y
    sta pointsRemaining
    beq !nextBucket+
!point:
    ldy #0
    lda (coordinatePointer),y
    tax
    iny
    lda (coordinatePointer),y
    tay
    lda bucketIndex
    clc
    adc #1
pointPrepared:
    jsr stampPoint
    clc
    lda coordinatePointer
    adc #2
    sta coordinatePointer
    bcc !coordinate+
    inc coordinatePointer+1
!coordinate:
    dec pointsRemaining
    bne !point-
!nextBucket:
    inc bucketIndex
    lda bucketIndex
    cmp #9
    bne !bucket-
renderComplete:
    jsr publishImage
    inc poseUsed
    lda poseUsed
    and #63
    sta poseUsed
    jmp nextScene

.import source "glyph-stamps.asm"
.import source "clear-generator.asm"
// Reuse only the fitted font/matrix publication module, with our own hires
// mode, palette, matrices and initial fonts applied after its generic setup.
.import source "../prepared-fragments/display.asm"
.errorif *>$2000,"Runtime overlaps font buffers"

*=$3000 "Prepared-frame and shifted-pattern address tables"
frameLo: .fill 64,<(frames+i*121)
frameHi: .fill 64,>(frames+i*121)
patternLo: .fill 72,<(patterns+8*(floor(i/8)+1)*floor(i/8)+2*(floor(i/8)+1)*(i&7))
patternHi: .fill 72,>(patterns+8*(floor(i/8)+1)*floor(i/8)+2*(floor(i/8)+1)*(i&7))
screenRowLo: .fill 16,<((i+4)*40+10)
screenRowHi: .fill 16,>((i+4)*40+10)
.errorif *>$3400,"Tables overlap point state"
*=$3400 "Live publication, point and allocator state"
frameCounter: .word 0
presentationCounter: .word 0
poseUsed: .byte 0
frontPose: .byte 0
frontFontHigh: .byte $20
frontScreenHigh: .byte 4
drawFontHigh: .byte $28
drawScreenHigh: .byte $0c
drawSelection: .byte $3a
nextCode: .byte 1
bucketIndex: .byte 0
pointsRemaining: .byte 0
pointSize: .byte 0
pointX: .byte 0
pointY: .byte 0
pointColumn: .byte 0
stampColumn: .byte 0
stampRow: .byte 0
sourceOffset: .byte 0
stampBits: .byte 0
pixelRow: .byte 0
characterColumn: .byte 0
glyphCode: .byte 0
genBuffer: .byte 0
clearA: .word 0
clearB: .word 0
clearEnd: .word 0
.errorif *>$3800,"State overlaps shifted bob patterns"

.function Disk(size,x,y) {
    .var dx=2*x-(size-1)
    .var dy=2*y-(size-1)
    .return x>=0 && x<size && y>=0 && y<size && 4*(dx*dx+dy*dy)<=(2*size-1)*(2*size-1)
}
*=$3800 "Nine reusable disk sizes with eight horizontal pixel phases"
patterns:
    .for (var size=1;size<=9;size++) {
        .for (var shift=0;shift<8;shift++) {
            .for (var column=0;column<2;column++) {
                .for (var y=0;y<size;y++) {
                    .var value=0
                    .for (var bit=0;bit<8;bit++) {
                        .if (Disk(size,column*8+bit-shift,y)) { .eval value=value|(128>>bit) }
                    }
                    .byte value
                }
            }
        }
    }
.errorif *!=patterns+720,"Reusable shifted disk data size"
*=$4000 "Own prepared point coordinates and nine size-count buckets"
frames: .import binary "build/frames.bin"
.errorif *!=frames+64*121,"Prepared point frame format"
*=$6000 "Original immutable shared glyphs and matrix"
staticFont: .import binary "build/static-font.bin"
baseScreen: .import binary "build/base-screen.bin"
baseColors: .import binary "build/colors.bin"
clearMap: .import binary "build/clear-map.bin"
.errorif *>$7000,"Prepared inputs overlap runtime-generated clears"
