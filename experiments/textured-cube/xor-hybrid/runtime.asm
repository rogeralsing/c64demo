// Integration for the shared 64x128 multicolor XOR character canvas.
// High-RAM code is staged below I/O and relocated before both charsets clear.
.label texture=$e000
.label textureShift2=$e100
.label textureShift4=$e200
.label textureShift6=$e300
.label phase=hybridPhase

.macro HybridRuntimeLowCode() {
@hybridInit:
    lda #0
    sta hybridPhase
    lda #<hybridStageA
    sta $e0
    lda #>hybridStageA
    sta $e1
    lda #<hybridRuntimeStart
    sta $e2
    lda #>hybridRuntimeStart
    sta $e3
    lda #<(hybridStageAEnd-hybridStageA)
    sta $e4
    lda #>(hybridStageAEnd-hybridStageA)
    sta $e5
    jsr !copy+
    lda #<hybridStageB
    sta $e0
    lda #>hybridStageB
    sta $e1
    lda #<hybridBuilderRuntimeStart
    sta $e2
    lda #>hybridBuilderRuntimeStart
    sta $e3
    lda #<(hybridStageBEnd-hybridStageB)
    sta $e4
    lda #>(hybridStageBEnd-hybridStageB)
    sta $e5
    jsr !copy+
    rts
!copy:
    ldy #0
!byte:
    lda ($e0),y
    sta ($e2),y
    inc $e0
    bne !source+
    inc $e1
!source:
    inc $e2
    bne !destination+
    inc $e3
!destination:
    lda $e4
    bne !low+
    dec $e5
!low:
    dec $e4
    lda $e4
    ora $e5
    bne !byte-
    rts

@hybridFrameGeometry:
    jsr transformModel
    jmp rememberBounds

// Strict positive area of all four rounded corners. The shared XOR renderer
// consumes this ordinary six-bit face mask without any replacement filler.
@hybridCullFaces:
    lda #0
    sta visibleFaces
    sta hybridCullFace
!face:
    lda #0
    sta hybridCullArea
    sta hybridCullArea+1
    sta hybridCullCorner
    lda hybridCullFace
    asl
    asl
    sta hybridCullOffset
!edge:
    lda hybridCullCorner
    clc
    adc hybridCullOffset
    tax
    lda hybridCullCorners,x
    tax
    lda projectedX,x
    sta hybridCullX
    lda projectedY,x
    sta hybridCullY
    lda hybridCullCorner
    clc
    adc #1
    and #3
    clc
    adc hybridCullOffset
    tax
    lda hybridCullCorners,x
    sta hybridCullNext
    tay
    lda hybridCullX
    ldx projectedY,y
    jsr cullUnsignedMultiply
    stx hybridCullProduct
    sta hybridCullProduct+1
    ldy hybridCullNext
    lda hybridCullY
    ldx projectedX,y
    jsr cullUnsignedMultiply
    stx hybridCullOther
    sta hybridCullOther+1
    clc
    lda hybridCullArea
    adc hybridCullProduct
    sta hybridCullArea
    lda hybridCullArea+1
    adc hybridCullProduct+1
    sta hybridCullArea+1
    sec
    lda hybridCullArea
    sbc hybridCullOther
    sta hybridCullArea
    lda hybridCullArea+1
    sbc hybridCullOther+1
    sta hybridCullArea+1
    inc hybridCullCorner
    lda hybridCullCorner
    cmp #4
    bne !edge-
    lda hybridCullArea+1
    bmi !hidden+
    ora hybridCullArea
    beq !hidden+
    ldx hybridCullFace
    lda hybridCullMasks,x
    ora visibleFaces
    sta visibleFaces
!hidden:
    inc hybridCullFace
    lda hybridCullFace
    cmp #6
    beq !done+
    jmp !face-
!done:
    rts

@hybridPhase: .byte 0
@pitchMotion: .fill 64,round(24*sin(i*2*PI/64+0.4))&255
hybridCullCorners:
    .byte 0,4,6,2, 1,3,7,5, 0,1,5,4
    .byte 2,6,7,3, 0,2,3,1, 4,5,7,6
hybridCullMasks: .byte 1,2,4,8,16,32
hybridCullFace: .byte 0
hybridCullCorner: .byte 0
hybridCullOffset: .byte 0
hybridCullNext: .byte 0
hybridCullX: .byte 0
hybridCullY: .byte 0
hybridCullArea: .word 0
hybridCullProduct: .word 0
hybridCullOther: .word 0
}
