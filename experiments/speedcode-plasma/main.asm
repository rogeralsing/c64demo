// Original generated-code plasma. Reusable sine/density tables are prepared;
// the C64 combines both live phases into all 1,000 cells on every update.
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
    sta phaseX
    sta phaseY
    sta displayedBuffer
    lda #6
    sta $d021
    lda #2
    sta $dd00
    sta $d018
    lda #$1b
    sta $d011
    lda #$08
    sta $d016
    ldx #0
    lda #1
!colors:
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    inx
    bne !colors-

render:
    ldx phaseY
    .for (var row=0; row<25; row++) {
        lda sinus+row*7,x
        sta rowValues+row
    }
    ldx phaseX
    lda displayedBuffer
    bne !drawA+
    jsr drawMatrixB
    lda #1
    sta nextBuffer
    lda #$12
    bne !wait+
!drawA:
    jsr drawMatrixA
    lda #0
    sta nextBuffer
    lda #$02
!wait:
    // A stays live while raster polling waits for the coherent matrix swap.
!high:
    bit $d011
    bpl !high-
!low:
    bit $d011
    bmi !low-
    sta $d018
    lda nextBuffer
    sta displayedBuffer
framePresented:
    inc phaseX
    lda phaseY
    clc
    adc #3
    sta phaseY
    jmp render

phaseX: .byte 0
phaseY: .byte 0
displayedBuffer: .byte 0
nextBuffer: .byte 0
rowValues: .fill 25, 0

* = $2800 "Reusable arithmetic table"
sinus: .fill 512, round(7.5+7.5*sin(mod(i,256)*2*PI/256))

* = $4000 "Screen matrix A"
matrixA: .fill 1024, 0
* = $4400 "Screen matrix B"
matrixB: .fill 1024, 0
* = $4800 "Sixteen shared density glyphs"
.var bayer = List().add(0,8,2,10,12,4,14,6,3,11,1,9,15,7,13,5)
font:
    .for (var level=0; level<16; level++) {
        .for (var row=0; row<8; row++) {
            .var bits=0
            .for (var column=0; column<8; column++) {
                .eval bits=bits*2+(bayer.get(mod(row,4)*4+mod(column,4))<level ? 1 : 0)
            }
            .byte bits
        }
    }

* = $5000 "Generated matrix writers"
.macro MatrixWriter(address) {
    .for (var cell=0; cell<1000; cell++) {
        lda sinus+mod(cell,40)*5,x
        clc
        adc rowValues+floor(cell/40)
        lsr
        sta address+cell
    }
    rts
}
drawMatrixA: MatrixWriter(matrixA)
drawMatrixB: MatrixWriter(matrixB)
writersEnd:
.errorif * > $c000, "Generated plasma writers exceed available RAM"
