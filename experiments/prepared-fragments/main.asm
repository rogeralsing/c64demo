// Original prepared-fragment renderer with shared interiors and private edges.
// The host resolves visible regions; the C64 walks their edges and builds glyphs.

BasicUpstart2(start)
.const CELL_POINTER = $d0
.const GLYPH_POINTER = $d2
.const COPY_POINTER = $d4
.const CLEAR_POINTER = $d6
.const STREAM_POINTER = $f0
.const FIRST_PRIVATE = 13
.const WIDTH = 128
.const HEIGHT = 160

* = $4000 "Patterns and prepared frame addresses"
.import source "build/scene-offsets.inc"
patternsEven: .byte $00,$00,$cc,$cc,$ff,$ff,$bb,$bb,$aa,$aa,$66,$66,$55
patternsOdd: .byte $00,$33,$33,$ff,$ff,$ee,$ee,$aa,$aa,$99,$99,$55,$55
leftMasks: .byte $ff,$3f,$0f,$03
rightMasks: .byte $c0,$f0,$fc,$ff
matrixRowLow: .fill 20, <((i+2)*40+4)
matrixRowHigh: .fill 20, >((i+2)*40+4)

* = $5000 "Runtime span bounds"
leftRows: .fill HEIGHT, 128
rightRows: .fill HEIGHT, 0
firstFull: .fill 20, 0
endFull: .fill 20, 0

* = $6000 "Runtime fragment rasterizer"
start:
    jsr initializeDisplay
main:
    jsr beginImage
consumeFragments:
    ldx poseUsed
    lda poseLow,x
    sta STREAM_POINTER
    lda poseHigh,x
    sta STREAM_POINTER+1
    jsr readByte
    sta fragmentsRemaining
!fragment:
    jsr readByte
    sta material
    jsr readByte
    sta edgesRemaining
    lda #HEIGHT
    sta fragmentMinY
    lda #0
    sta fragmentMaxY
    ldx #0
!clearBounds:
    lda #128
    sta leftRows,x
    lda #0
    sta rightRows,x
    inx
    cpx #HEIGHT
    bne !clearBounds-
!edge:
    jsr readByte
    sta edgeX0
    jsr readByte
    sta edgeY0
    jsr readByte
    sta edgeX1
    jsr readByte
    sta edgeY1
    jsr walkEdge
    dec edgesRemaining
    bne !edge-
    jsr fillInteriors
    lda fragmentMinY
    sta spanY
!row:
    ldx spanY
    lda leftRows,x
    sta spanLeft
    lda rightRows,x
    sta spanRight
    jsr paintSpanRow
    inc spanY
    lda spanY
    cmp fragmentMaxY
    bne !row-
    dec fragmentsRemaining
    bne !fragment-
    jsr publishImage
    inc poseUsed
    lda poseUsed
    and #15
    sta poseUsed
    lda drawFontHigh
    eor #8
    sta drawFontHigh
    lda drawScreenHigh
    eor #8
    sta drawScreenHigh
    lda drawSelection
    eor #$22
    sta drawSelection
    jmp main

readByte:
    ldy #0
    lda (STREAM_POINTER),y
    inc STREAM_POINTER
    bne !done+
    inc STREAM_POINTER+1
!done:
    rts

// Prepared edges are horizontal, vertical or unit diagonal. Intersections use
// centers (x+.5,y+.5). The resulting span is left-inclusive/right-exclusive.
walkEdge:
    lda edgeY0
    cmp edgeY1
    beq !done+
    bcc !ordered+
    ldx edgeY1
    stx edgeY0
    sta edgeY1
    lda edgeX0
    ldx edgeX1
    stx edgeX0
    sta edgeX1
!ordered:
    lda edgeY0
    cmp fragmentMinY
    bcs !minimumReady+
    sta fragmentMinY
!minimumReady:
    lda edgeY1
    cmp fragmentMaxY
    bcc !maximumReady+
    sta fragmentMaxY
!maximumReady:
    lda edgeX0
    sta edgeX
    cmp edgeX1
    beq !vertical+
    bcc !positive+
    dec edgeX
    lda #$ff
    bne !step+
!positive:
    lda #1
    bne !step+
!vertical:
    lda #0
!step:
    sta edgeStep
    ldx edgeY0
!row:
    lda edgeX
    cmp leftRows,x
    bcs !leftDone+
    sta leftRows,x
!leftDone:
    lda edgeX
    cmp rightRows,x
    bcc !rightDone+
    sta rightRows,x
!rightDone:
    clc
    lda edgeX
    adc edgeStep
    sta edgeX
    inx
    cpx edgeY1
    bne !row-
!done:
    rts

// A shared pattern is safe only when every one of a cell's32 samples belongs
// to this fragment. Partial cells go through the private-glyph path below.
fillInteriors:
    lda fragmentMaxY
    clc
    adc #7
    lsr
    lsr
    lsr
    sta fragmentEndCell
    lda fragmentMinY
    lsr
    lsr
    lsr
    sta cellRow
!cellRow:
    lda #0
    sta maximumLeft
    lda #128
    sta minimumRight
    lda cellRow
    asl
    asl
    asl
    tax
    ldy #8
!sampleRow:
    lda leftRows,x
    cmp rightRows,x
    bcc !nonempty+
    lda #128
    sta maximumLeft
    lda #0
    sta minimumRight
!nonempty:
    lda leftRows,x
    cmp maximumLeft
    bcc !leftDone+
    sta maximumLeft
!leftDone:
    lda rightRows,x
    cmp minimumRight
    bcs !rightDone+
    sta minimumRight
!rightDone:
    inx
    dey
    bne !sampleRow-
    lda maximumLeft
    clc
    adc #3
    lsr
    lsr
    ldx cellRow
    sta firstFull,x
    sta cellColumn
    lda minimumRight
    lsr
    lsr
    sta endFull,x
!cell:
    ldx cellRow
    lda cellColumn
    cmp endFull,x
    bcs !nextRow+
    jsr selectCell
    ldy #0
    lda material
    sta (CELL_POINTER),y
    inc cellColumn
    jmp !cell-
!nextRow:
    inc cellRow
    lda cellRow
    cmp fragmentEndCell
    bne !cellRow-
    rts

beginImage:
    lda #0
    sta CLEAR_POINTER
    lda drawFontHigh
    sta CLEAR_POINTER+1
    ldx #8
    jsr clearPages
    lda #0
    sta CLEAR_POINTER
    lda drawScreenHigh
    sta CLEAR_POINTER+1
    ldx #4
    jsr clearPages
    lda #FIRST_PRIVATE
    sta nextFree
    lda #0
    sta allocatorFull
    sta allocationError
    sta cellRow
    ldx #19
!fullBounds:
    sta firstFull,x
    sta endFull,x
    dex
    bpl !fullBounds-
    lda #0
    sta GLYPH_POINTER
    lda drawFontHigh
    sta GLYPH_POINTER+1
    ldx #0
    ldy #0
!shared:
    .for (var pair = 0; pair < 4; pair++) {
        lda patternsEven,x
        sta (GLYPH_POINTER),y
        iny
        lda patternsOdd,x
        sta (GLYPH_POINTER),y
        iny
    }
    inx
    cpx #13
    bne !shared-
    lda #1
    sta material
    lda #2
    sta cellColumn
!legend:
    jsr selectCell
    ldy #0
    lda material
    sta (CELL_POINTER),y
    inc material
    inc cellColumn
    lda material
    cmp #13
    bne !legend-
    // One visible mixed tile exercises a nonzero shared-glyph copy, followed
    // by a second modification that must reuse the same private allocation.
    lda #28
    sta cellColumn
    jsr selectCell
    ldy #0
    lda #6
    sta (CELL_POINTER),y
    lda #112
    sta spanLeft
    lda #114
    sta spanRight
    lda #1
    sta spanY
    lda #12
    sta material
    jsr paintSpanRow
    lda #114
    sta spanLeft
    lda #116
    sta spanRight
    lda #6
    sta spanY
    lda #4
    sta material
    jsr paintSpanRow
    rts

clearPages:
    lda #0
    ldy #0
!byte:
    sta (CLEAR_POINTER),y
    iny
    bne !byte-
    inc CLEAR_POINTER+1
    dex
    bne !byte-
    rts

.import source "glyph-spans.asm"
.import source "display.asm"

fragmentsRemaining: .byte 0
edgesRemaining: .byte 0
fragmentMinY: .byte 0
fragmentMaxY: .byte 0
fragmentEndCell: .byte 0
material: .byte 0
edgeX0: .byte 0
edgeY0: .byte 0
edgeX1: .byte 0
edgeY1: .byte 0
edgeX: .byte 0
edgeStep: .byte 0
maximumLeft: .byte 0
minimumRight: .byte 0
spanY: .byte 0
spanLeft: .byte 0
spanRight: .byte 0
cellRow: .byte 0
cellColumn: .byte 0
lastColumn: .byte 0
spanFirstMask: .byte 0
spanLastMask: .byte 0
spanFirstColumn: .byte 0
spanMask: .byte 0
patternByte: .byte 0
savedOld: .byte 0
newGlyph: .byte 0
sourceGlyph: .byte 0
nextFree: .byte FIRST_PRIVATE
allocatorFull: .byte 0
allocationError: .byte 0
poseUsed: .byte 0
frontPose: .byte $ff
drawFontHigh: .byte $28
drawScreenHigh: .byte $0c
drawSelection: .byte $3a
frontFontHigh: .byte $20
frontScreenHigh: .byte $04
frameCounter: .word 0
presentationCounter: .word 0
.assert "Runtime stays below prepared geometry", * < $8000, true

* = $8000 "Resolved vector fragments, not rendered images"
sceneData:
.import binary "build/scene.bin"
.assert "Prepared geometry stays below mapped I/O", * <= $d000, true
