// Original character-reuse rotate/zoom example, inspired by The Impossible Thing.
// Runtime builds 256 transformed glyphs and a matching 40x25 origin matrix.
// The texture and scalar coefficient tables contain no rendered animation poses.

BasicUpstart2(start)

.const FONT_POINTER = $f0
.const SCREEN_POINTER = $f2
.const PHASE_COUNT = 32

* = $1000 "Runtime character rotate/zoom"
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
    lda #$03
    sta $dd00
    lda $dd02
    ora #3
    sta $dd02
    lda #$1b
    sta $d011
    lda #8
    sta $d016
    lda #$18
    sta $d018
    sta displaySelection
    lda #6
    sta $d021
    lda #14
    sta $d020
    lda #0
    sta $d015
    sta phaseIndex
    sta presentationCounter
    sta presentationCounter+1
    sta frameCounter
    sta frameCounter+1

    ldx #0
!clear:
    lda #0
    sta $0400,x
    sta $0500,x
    sta $0600,x
    sta $0700,x
    sta $0c00,x
    sta $0d00,x
    sta $0e00,x
    sta $0f00,x
    .for (var page = $20; page < $30; page++) {
        sta page*$100,x
    }
    lda #1
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    inx
    bne !clear-

    lda #<irq
    sta $fffe
    lda #>irq
    sta $ffff
    lda #<nmiReturn
    sta $fffa
    lda #>nmiReturn
    sta $fffb
    lda #250
    sta $d012
    lda #1
    sta $d019
    sta $d01a
    cli

render:
    ldx phaseIndex
    stx phaseUsed
    lda cosineStep,x
    sta horizontalU
    sta verticalV
    lda sineStep,x
    sta horizontalV
    eor #$ff
    clc
    adc #1
    sta verticalU

    jsr prepareLocalOffsets

    jsr patchTextureOperands

    lda #0
    sta FONT_POINTER
    sta SCREEN_POINTER
    lda displaySelection
    cmp #$18
    bne !drawA+
    lda #$28
    sta FONT_POINTER+1
    lda #$0c
    sta SCREEN_POINTER+1
    jmp !draw+
!drawA:
    lda #$20
    sta FONT_POINTER+1
    lda #$04
    sta SCREEN_POINTER+1
!draw:
    jsr generateGlyphs
    jsr generateMatrix

    // Publish only a complete font/matrix pair at the next PAL frame boundary.
!waitHigh:
    bit $d011
    bpl !waitHigh-
!waitLow:
    bit $d011
    bmi !waitLow-
    lda displaySelection
    eor #$22
    sta displaySelection
    sta $d018
    inc presentationCounter
    bne framePresented
    inc presentationCounter+1
framePresented:
    inc phaseIndex
    lda phaseIndex
    and #PHASE_COUNT-1
    sta phaseIndex
    jmp render

irq:
    pha
    inc frameCounter
    bne !done+
    inc frameCounter+1
!done:
    lda #1
    sta $d019
    pla
nmiReturn:
    rti

// Q4 coordinates wrap modulo 256: the low byte contains the full fractional
// coordinate required for a repeating sixteen-texel domain.
prepareLocalOffsets:
    lda #0
    sta localRowU
    sta localRowV
    sta localRow
    ldy #0
!row:
    lda localRowU
    sta localU
    lda localRowV
    sta localV
    ldx #4
!column:
    lda localU
    lsr
    lsr
    lsr
    lsr
    sta packedLow
    lda localV
    and #$f0
    ora packedLow
    sta localOffsets,y
    clc
    lda localU
    adc horizontalU
    sta localU
    clc
    lda localV
    adc horizontalV
    sta localV
    iny
    dex
    bne !column-
    clc
    lda localRowU
    adc verticalU
    sta localRowU
    clc
    lda localRowV
    adc verticalV
    sta localRowV
    inc localRow
    lda localRow
    cmp #4
    bne !row-
    rts

.var textureInstructions = List()
generateGlyphs:
    ldx #0
!glyph:
    .for (var row = 0; row < 4; row++) {
        .for (var column = 0; column < 4; column++) {
            .eval textureInstructions.add(*)
            .if (column == 0) {
                lda textureLanes+column*$200,x
            } else {
                ora textureLanes+column*$200,x
            }
        }
        ldy #row*2
        sta (FONT_POINTER),y
        iny
        sta (FONT_POINTER),y
    }
    clc
    lda FONT_POINTER
    adc #8
    sta FONT_POINTER
    bcc !samePage+
    inc FONT_POINTER+1
!samePage:
    inx
    bne !glyph-
    rts

// Patch the sixteen texture operands once per image. X then selects the
// integer origin shared by the corresponding glyph, using a 256-byte ring.
patchTextureOperands:
    .for (var row = 0; row < 4; row++) {
        .for (var column = 0; column < 4; column++) {
            lda localOffsets+row*4+column
            sta textureInstructions.get(row*4+column)+1
        }
    }
    rts

generateMatrix:
    lda horizontalU
    asl
    asl
    sta cellStepU
    lda horizontalV
    asl
    asl
    sta cellStepV
    lda verticalU
    asl
    asl
    sta rowStepU
    lda verticalV
    asl
    asl
    sta rowStepV

    // Translation varies as scalar Q4 coordinates, independently of the angle.
    lda phaseUsed
    asl
    clc
    adc phaseUsed
    sta matrixRowU
    lda phaseUsed
    asl
    asl
    clc
    adc phaseUsed
    sta matrixRowV
    ldx #19
!centerColumns:
    sec
    lda matrixRowU
    sbc cellStepU
    sta matrixRowU
    sec
    lda matrixRowV
    sbc cellStepV
    sta matrixRowV
    dex
    bne !centerColumns-
    ldx #12
!centerRows:
    sec
    lda matrixRowU
    sbc rowStepU
    sta matrixRowU
    sec
    lda matrixRowV
    sbc rowStepV
    sta matrixRowV
    dex
    bne !centerRows-

    lda #25
    sta matrixRowsRemaining
!row:
    lda matrixRowU
    sta matrixU
    lda matrixRowV
    sta matrixV
    ldy #0
!column:
    lda matrixU
    lsr
    lsr
    lsr
    lsr
    sta packedLow
    lda matrixV
    and #$f0
    ora packedLow
    sta (SCREEN_POINTER),y
    clc
    lda matrixU
    adc cellStepU
    sta matrixU
    clc
    lda matrixV
    adc cellStepV
    sta matrixV
    iny
    cpy #40
    bne !column-
    clc
    lda SCREEN_POINTER
    adc #40
    sta SCREEN_POINTER
    bcc !samePage+
    inc SCREEN_POINTER+1
!samePage:
    clc
    lda matrixRowU
    adc rowStepU
    sta matrixRowU
    clc
    lda matrixRowV
    adc rowStepV
    sta matrixRowV
    dec matrixRowsRemaining
    bne !row-
    rts

phaseIndex: .byte 0
phaseUsed: .byte 0
displaySelection: .byte $18
presentationCounter: .word 0
frameCounter: .word 0
horizontalU: .byte 0
horizontalV: .byte 0
verticalU: .byte 0
verticalV: .byte 0
localRowU: .byte 0
localRowV: .byte 0
localU: .byte 0
localV: .byte 0
localRow: .byte 0
packedLow: .byte 0
localOffsets: .fill 16, 0
cellStepU: .byte 0
cellStepV: .byte 0
rowStepU: .byte 0
rowStepV: .byte 0
matrixRowU: .byte 0
matrixRowV: .byte 0
matrixU: .byte 0
matrixV: .byte 0
matrixRowsRemaining: .byte 0

// Scalar coefficients represent a full rotation with two zoom oscillations.
// They are Q4 transform inputs; every glyph and screen cell is built at runtime.
cosineStep:
    .fill PHASE_COUNT, round((12+4*sin(i*4*PI/PHASE_COUNT))*cos(i*2*PI/PHASE_COUNT)) & $ff
sineStep:
    .fill PHASE_COUNT, round((12+4*sin(i*4*PI/PHASE_COUNT))*sin(i*2*PI/PHASE_COUNT)) & $ff
.assert "Runtime stays below the first generated charset", * <= $2000, true

.function TextureBit(index) {
    .var x = index & 15
    .var y = (index >> 4) & 15
    .return (x == 0 || y == 0 || (x < 8 && y < 8 && x == y) || ((x-11)*(x-11)+(y-11)*(y-11) < 9)) ? 1 : 0
}

* = $3000 "Duplicated shifted texture lookups"
textureLanes:
    .for (var lane = 0; lane < 4; lane++) {
        .fill 512, TextureBit(i & 255) * ($c0 >> (lane*2))
    }
texture:
    .fill 256, TextureBit(i)
