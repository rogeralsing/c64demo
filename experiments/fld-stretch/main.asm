// Original full-row bitmap stretch plus real flexible line distance.
// Each of the eight original rows has a separate bitmap base. Repeated
// badlines retain RC=0 while CIA2/D018 chooses the actual source row.
.label destination = $f0
.label patch = $f2
.label sourceRow = $f4
.label rowsRemaining = $f5
.label cellsRemaining = $f6
.label d011Table = $2200
.label suppressTable = $2300
.const CELLS = 128
.const CELL_BYTES = 15
.const SKIP_BYTES = 13
.var bases = List().add($0000,$2000,$4000,$6000,$8000,$a000,$c000,$e000)
.var selectors = List().add($f3,$fb,$f2,$fa,$f1,$f9,$f0,$f8)

BasicUpstart2(start)
* = $0c00 "Initialization and raster code"
start:
    sei
    lda #$7f
    sta $dc0d
    sta $dd0d
    lda $dc0d
    lda $dd0d
    lda #$35
    sta $01
    lda #0
    sta $d015
    sta $d01a
    sta $d020
    sta fieldCounter
    sta phase
    lda #$7b
    sta $d011
    lda #$08
    sta $d016
    lda #3
    sta $dd02
    sta $dd00
    lda #$f0
    sta $d018
    .for (var row=0; row<8; row++) {
        lda #<(bases.get(row)+$08c0)
        sta destination
        lda #>(bases.get(row)+$08c0)
        sta destination+1
        ldx #0
        ldy #0
    !copy:
        lda picture+row*40,x
        sta (destination),y
        clc
        lda destination
        adc #8
        sta destination
        bcc !address+
        inc destination+1
    !address:
        inx
        cpx #40
        bne !copy-
    }
    // Matrices at bank offset $3C00 avoid VIC character-ROM shadowing.
    // Initialize physical RAM before enabling interrupts or raster control.
    lda #$34
    sta $01
    ldx #0
!screens:
    lda #$16
    .for (var bank=0; bank<4; bank++) {
        .for (var page=0; page<4; page++) { sta bank*$4000+$3c00+page*256,x }
    }
    inx
    bne !screens-
    lda #$35
    sta $01
    ldx #0
!tables:
    txa
    clc
    adc #1
    and #7
    ora #$70
    sta d011Table,x
    txa
    clc
    adc #2
    and #7
    ora #$70
    sta suppressTable,x
    inx
    bne !tables-
    jsr prepareField
    lda #<nmi
    sta $fffa
    lda #>nmi
    sta $fffb
    lda #<irq
    sta $fffe
    lda #>irq
    sta $ffff
    lda #102
    sta $d012
    lda #1
    sta $d019
    sta $d01a
    cli
idle:
    jmp idle

prepareField:
    lda phase
    and #7
    sta gap
    tax
    lda skipLo,x
    sta fldDispatch+1
    lda skipHi,x
    sta fldDispatch+2
    ldx phase
    lda heights,x
    sta height
    sta rowsRemaining
    lda #0
    sta sourceRow
    lda #<(stretchCells+7)
    sta patch
    lda #>(stretchCells+7)
    sta patch+1
    ldx #106
!reset:
    lda suppressTable-1,x
    sta d011Table,x
    inx
    cpx #113
    bne !tail+
    ldx #234
!tail:
    cpx #241
    bne !reset-
    clc
    lda gap
    adc #106
    tax
    lda #CELLS
    sta cellsRemaining
!cell:
    ldy sourceRow
    lda rowSelector,y
    ldy #0
    sta (patch),y
    lda suppressTable-1,x
    ldy sourceRow
    cpy #8
    bcs !hidden+
    and #$3f
!hidden:
    sta d011Table,x
    clc
    lda patch
    adc #CELL_BYTES
    sta patch
    bcc !pointer+
    inc patch+1
!pointer:
    dec rowsRemaining
    bne !row+
    lda height
    sta rowsRemaining
    inc sourceRow
    lda sourceRow
    cmp #8
    bcc !row+
    lda #8
    sta sourceRow
!row:
    inx
    dec cellsRemaining
    bne !cell-
    rts

irq:
    pha
    txa
    pha
    tya
    pha
    lda #1
    sta $d019
    lda #103
    sta $d012
    lda #<stableIRQ
    sta $fffe
    lda #>stableIRQ
    sta $ffff
    tsx
    cli
    .fill 24,$ea
    jmp *
stableIRQ:
    txs
    lda #1
    sta $d019
    ldx #7
!align:
    dex
    bne !align-
    bit $ea
    nop
    nop
    lda $d012
    cmp $d012
    bne !aligned+
!aligned:
    ldx #20
!firstWindow:
    dex
    bne !firstWindow-
    bit $ea
rasterKernel:
    ldx #106
    ldy #11
!delay:
    dey
    bne !delay-
    nop
    nop
fldDispatch:
    jmp skipCells
.align $100
skipCells:
    .for (var line=0; line<7; line++) {
        lda suppressTable,x
        sta $d011
        inx
        ldy #10
    !delay:
        dey
        bne !delay-
        nop
    }
stretchCells:
    .for (var cell=0; cell<CELLS; cell++) {
        lda d011Table,x
        sta $d011
        lda #$f3
        sta $dd00
        sta $d018
        inx
    }
    lda #$7b
    sta $d011
!complete:
    lda $d012
    cmp #246
    bne !complete-
fieldComplete:
    inc fieldCounter
    lda fieldCounter
    and #15
    sta phase
    jsr prepareField
prepareFinished:
    lda #3
    sta $dd00
    lda #$f0
    sta $d018
    lda #$7b
    sta $d011
    lda #102
    sta $d012
    lda #<irq
    sta $fffe
    lda #>irq
    sta $ffff
    pla
    tay
    pla
    tax
    pla
nmi:
    rti

fieldCounter: .byte 0
phase: .byte 0
gap: .byte 0
height: .byte 0
rowSelector: .byte $f3,$fb,$f2,$fa,$f1,$f9,$f0,$f8,$f3
heights: .byte 8,9,10,11,12,13,14,15,16,15,14,13,12,11,10,9
skipLo: .fill 8, <(skipCells+(7-i)*SKIP_BYTES)
skipHi: .fill 8, >(skipCells+(7-i)*SKIP_BYTES)
.errorif (stretchCells-skipCells)!=7*SKIP_BYTES, "FLD cell size changed"
.errorif * > $1c00, "Raster code exceeds its reserved region"
* = $3000 "Original eight source rows"
picture: .import binary "build/picture.bin"
