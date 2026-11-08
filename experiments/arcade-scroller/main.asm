// Original Arcade workload demonstrator. No Anomaly code, artwork or payload.
// Prepared skewed floor bytes, independent fractional line rates, live copies;
// a signed-raster-gated28-job wall chain publishes only completed buffers.
.const FLOOR_LINES=64
.const fineScroll=$8000
.const accumulators=$8040
.const incomingIndex=$8080
.const sourcePointer=$20
.const destinationPointer=$22
.const columnPointer=$24
.const FLOOR_BITMAP=$a000
.const FLOOR_START=FLOOR_BITMAP+17*320
.const WALL_DIVIDER=6

.function WallBit(column, bit, y) {
    .var x=mod(column,8)*8+bit
    .var on=false
    .if (y<8) { .eval on=(y==1 || y==6 || x==2 || x==61) }
    .if (y>=8 && y<24) {
        // Original compact neon sign: six five-column letter shapes.
        .var letters=List().add($0e111f1111,$1e111e1211,$0f1010100f,$0e111f1111,$1e1111111e,$1f101e101f)
        .var local=x-14
        .if (local>=0 && local<36 && y>=12 && y<17) {
            .var letter=floor(local/6)
            .var gx=mod(local,6)
            .if (gx<5) { .eval on=((letters.get(letter)>>(8*(16-y)))&(16>>gx))!=0 }
        }
        .if (x==7 || x==56 || y==21) { .eval on=true }
    }
    .if (y>=24 && y<68) {
        .eval on=(x==7 || x==56 || y==25 || y==66)
        .if (x>=12 && x<52 && y>=30 && y<61) {
            .eval on=(x==12 || x==51 || y==30 || y==60)
            .var ax=x-32
            .var ay=y-45
            .if (abs(ax)<=10 && abs(ay)<=7) {
                .eval on=(abs(ay)<=4 && abs(ax)<8) || (abs(ay)==7 && abs(ax)==7) || (ay==6 && abs(ax)==9)
                .if (ay==-1 && (ax==-4 || ax==4)) { .eval on=false }
            }
            .if (y==55 && mod(x,8)<3) { .eval on=true }
        }
    }
    .if (y>=68 && y<88) {
        .eval on=(x==7 || x==56 || y==68 || y==86)
        .if (y>=72 && y<=78) { .eval on=on || (x>=16 && x<=20) || (x>=38 && x<=42) || (x==29 && y<76) }
    }
    .if (y>=88) { .eval on=(x==7 || x==56 || y==101 || (y==95 && x>=22 && x<=41)) }
    .return on
}
.function WallByte(column,y) {
    .var b=0
    .for (var bit=0;bit<8;bit++) { .if (WallBit(column,bit,y)) { .eval b=b|(128>>bit) } }
    .return b
}
.function WallColor(column,row) {
    .var inks=List().add(3,14,7,13)
    .var ink=inks.get(mod(floor(column/8),4))
    .if (row==0 || row==2 || row==8 || row==10) { .eval ink=3 }
    .return ink*16
}
.function HorizonByte(column,y) {
    .var b=0
    .for (var bit=0;bit<8;bit++) {
        .var x=column*8+bit
        .var on=(y==0 || y==3 || y==27 || y==31 || abs(x-160)==(31-y)*4 || (y>12 && mod(x,64)<2))
        .if (on) { .eval b=b|(128>>bit) }
    }
    .return b
}
.function FloorByte(line,column) {
    .var b=0
    .var spacing=16+line
    .var offsets=List().add(0,2,4,6)
    .var initialPhase=(line+offsets.get(floor(line/16)))&7
    .for (var bit=0;bit<8;bit++) {
        // Preparation compensates the stagger so the initial grid is coherent.
        .var x=column*8+bit+initialPhase
        .var on=mod(x+256,spacing)<2 || line==0 || line==6 || line==16 || line==31 || line==53
        .if (line>=32 && ((floor((x+256)/spacing)+floor((line-32)/22))&1)==1) { .eval on=true }
        .if (on) { .eval b=b|(128>>bit) }
    }
    .return b
}

BasicUpstart2(start)
*=$1000 "Runtime scheduler and stable floor raster"
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
    sta $d011
    sta $d015
    sta $d01a
    sta $d020
    sta $d021
    sta $d022
    sta $d023
    sta $d01b
    sta $d01c
    sta $d01d
    ldx #0
!clearColors:
    sta $d800,x
    sta $d900,x
    sta $da00,x
    sta $db00,x
    inx
    bne !clearColors-
    ldx #0
!attributes:
    .for (var page=0;page<4;page++) {
        lda wallAttributes+page*256,x
        sta $0400+page*256,x
    }
    inx
    bne !attributes-
    // Startup mirrors all17wall/horizon bitmap rows and complete attributes.
    ldx #0
!mirror:
    .for (var page=0;page<21;page++) {
        lda $2000+page*256,x
        sta $6000+page*256,x
    }
    .for (var page=0;page<4;page++) {
        lda $0400+page*256,x
        sta $4400+page*256,x
    }
    inx
    beq !mirrored+
    jmp !mirror-
!mirrored:
    ldx #63
!tail:
    lda $3500,x
    sta $7500,x
    dex
    bpl !tail-
    lda #3
    sta $dd02
    sta $dd00
    lda #$18
    sta $d018
    lda #7
    sta $d016
    // DEN must be enabled before line48, including the very first field.
    // Waiting for low byte zero alone would also accept raster256.
!firstField:
    lda $d012
    bne !firstField-
    bit $d011
    bmi !firstField-
    lda #$3b
    sta $d011
    lda #<nmi
    sta $fffa
    lda #>nmi
    sta $fffb
    lda #<irq
    sta $fffe
    lda #>irq
    sta $ffff
    lda #183
    sta $d012
    lda #1
    sta $d019
    sta $d01a
    cli
mainField:
    lda fieldCounter
    sta activeField
    and #3
    tax
    lda gateSlots,x
    sta targetRaster
!waitGate:
    // Call-site context excludes the low-byte aliases at raster291/292.
    // The gate itself deliberately retains the signed low-byte predicate.
    bit $d011
    bmi !waitGate-
    lda $d012
    cmp targetRaster
    bne !waitGate-
    jsr gateWallJob
gateComplete:
    lda activeField
!waitField:
    cmp fieldCounter
    beq !waitField-
    lda fieldCounter
    and #1
    beq mainField
floorUpdateBegin:
    jsr updateFloor
    inc updateCounter
    bne !update+
    inc updateCounter+1
!update:
floorUpdateComplete:
    jmp mainField

// A is the actual D012 sample retained by the polling call site. Re-reading
// here could cross from163to164 after a bad-line BA hold and change the gate.
// Exact signed subtraction intentionally acceptsA4..FF as well as00..23.
gateWallJob:
    sta gateSample
    lda jobIndex
    sta jobBefore
    lda #0
    sta gateAccepted
    sta jobDidRun
    lda gateSample
    cmp #$24
    bmi !accepted+
    rts
!accepted:
    inc gateAccepted
    lda wallPending
    beq !return+
    inc jobDidRun
    ldx jobIndex
    cpx #13
    bcc copyBitmapRow
    cpx #26
    bcc copyAttributeRow
    beq writeAttributeColumn
    jmp writeBitmapColumn
!return:
    rts

copyBitmapRow:
    lda frontBuffer
    beq !bankA+
    txa
    clc
    adc #13
    tax
!bankA:
    lda pixelJobsLo,x
    sta pixelDispatch+1
    lda pixelJobsHi,x
    sta pixelDispatch+2
    ldy #0
!line:
pixelDispatch:
    jsr $ffff
    iny
    cpy #8
    bne !line-
    inc jobIndex
    rts

copyAttributeRow:
    txa
    sec
    sbc #13
    tax
    lda attributeRowsLo,x
    sta sourcePointer
    sec
    sbc #1
    sta destinationPointer
    lda attributeRowsHi,x
    ldx frontBuffer
    beq !source+
    ora #$40
!source:
    sta sourcePointer+1
    eor #$40
    sta destinationPointer+1
    ldy #0
!copy:
    lda (sourcePointer),y
    sta (destinationPointer),y
    iny
    cpy #40
    bne !copy-
    inc jobIndex
    rts

writeAttributeColumn:
    ldx publicationCounter
    txa
    and #31
    asl
    tax
    lda incomingAttributesLo,x
    sta columnPointer
    lda incomingAttributesHi,x
    sta columnPointer+1
    .for (var row=0;row<13;row++) {
        ldy #row
        lda (columnPointer),y
        ldx frontBuffer
        beq !toB+
        sta $0400+row*40+39
        jmp !written+
    !toB:
        sta $4400+row*40+39
    !written:
    }
    inc jobIndex
    rts

writeBitmapColumn:
    lda publicationCounter
    and #31
    tax
    lda incomingPixelsLo,x
    sta columnPointer
    lda incomingPixelsHi,x
    sta columnPointer+1
    .for (var row=0;row<13;row++) {
        ldx frontBuffer
        beq !toB+
        .for (var byte=0;byte<8;byte++) {
            ldy #row*8+byte
            lda (columnPointer),y
            sta $2000+row*320+39*8+byte
        }
        jmp !written+
    !toB:
        .for (var byte=0;byte<8;byte++) {
            ldy #row*8+byte
            lda (columnPointer),y
            sta $6000+row*320+39*8+byte
        }
    !written:
    }
    inc jobIndex
    lda #0
    sta wallPending
    rts

irq:
    pha
    txa
    pha
    tya
    pha
    lda #1
    sta $d019
    lda #184
    sta $d012
    lda #<stableIrq
    sta $fffe
    lda #>stableIrq
    sta $ffff
    tsx
    cli
    .fill 24,$ea
    jmp *
stableIrq:
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
    // Delay110cycles from the normalized beam, then change bank after the
    // last horizon fetch. Native traces check every subsequent D016store.
    ldx #21
!delay:
    dex
    bne !delay-
    nop
    nop
    lda #1
    sta $dd00
rasterKernel:
    .for (var line=0;line<FLOOR_LINES;line++) {
        lda fineScroll+line
        sta $d016
        .if (((187+line)&7)==3) {
            // The first read waits on BA's three-cycle lead as well as the
            // forty matrix fetches:12executed delay cycles, not15.
            .fill 6,$ea
        } else {
            jsr normalLineDelay
        }
    }
    // The complete lower bitmap line has left the VIC before publication.
!lowerBorder:
    lda $d012
    cmp #252
    bne !lowerBorder-
fieldComplete:
    inc wallTick
    lda wallWrap
    bne !tryPublish+
    lda wallTick
    cmp #WALL_DIVIDER
    bcc !noWallStep+
    lda #0
    sta wallTick
    lda wallFine
    beq !wrap+
    dec wallFine
    jmp !noWallStep+
!wrap:
    inc wallWrap
!tryPublish:
    lda wallPending
    bne !noWallStep+
publication:
    lda frontBuffer
    eor #1
    sta frontBuffer
    inc publicationCounter
    lda #0
    sta jobIndex
    sta wallWrap
    sta wallTick
    lda #1
    sta wallPending
    lda #7
    sta wallFine
!noWallStep:
    lda frontBuffer
    eor #3
    sta $dd00
    lda wallFine
    sta $d016
    inc fieldCounter
    bne !field+
    inc fieldCounter+1
!field:
    lda #183
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

// One aligned routine avoids a page-crossing taken branch in a replicated
// delay loop. Including JSR/RTS it is55cycles, on every call site.
.align $10
normalLineDelay:
    ldx #8
!delay:
    dex
    bne !delay-
    nop
    rts

.errorif *>$2000,"Runtime overlaps initial wall bitmap"
*=$5000 "Independent fractional floor updates"
updateFloor:
    .for (var line=0;line<FLOOR_LINES;line++) {
        lda accumulators+line
        clc
        adc #112+line
        sta accumulators+line
        bcc !next+
        dec fineScroll+line
        bpl !next+
        lda #7
        sta fineScroll+line
        ldy #line&7
        jsr floorCopyJobs+floor(line/8)*235
        ldx incomingIndex+line
        lda floorStream+line*64,x
        sta FLOOR_START+floor(line/8)*320+39*8+(line&7)
        inx
        txa
        and #63
        sta incomingIndex+line
    !next:
    }
    rts
.errorif *>$6000,"Floor updater overlaps hidden wall"

*=$7a00 "Own wall attributes, copied to screen RAM on startup"
wallAttributes:
    .for (var row=0;row<25;row++) {
        .for (var col=0;col<40;col++) {
            .if (row<13) { .byte WallColor(col,row) }
            else { .byte (row<17 ? $30 : $00) }
        }
    }
    .fill 24,0
*=$4800 "Scheduler state and incoming wall columns"
fieldCounter: .word 0
activeField: .byte 0
updateCounter: .word 0
frontBuffer: .byte 0
publicationCounter: .byte 0
wallFine: .byte 7
wallTick: .byte 0
wallWrap: .byte 0
wallPending: .byte 1
jobIndex: .byte 0
gateSample: .byte 0
gateAccepted: .byte 0
jobDidRun: .byte 0
jobBefore: .byte 0
targetRaster: .byte 0
gateSlots: .byte 35,163,36,164
pixelJobsLo: .fill 26,<(pixelJobs+i*241)
pixelJobsHi: .fill 26,>(pixelJobs+i*241)
attributeRowsLo: .fill 13,<($0401+i*40)
attributeRowsHi: .fill 13,>($0401+i*40)
incomingPixelsLo: .fill 32,<(incomingPixels+i*104)
incomingPixelsHi: .fill 32,>(incomingPixels+i*104)
// Padded two-byte indexing keeps the column number arithmetic visible.
incomingAttributesLo: .fill 64,<(incomingAttributes+floor(i/2)*13)
incomingAttributesHi: .fill 64,>(incomingAttributes+floor(i/2)*13)
.errorif *>$5000,"Scheduler tables overlap floor updater"
*=$7800 "Prepared incoming wall attribute columns"
incomingAttributes:
    .for (var col=40;col<72;col++) { .for (var row=0;row<13;row++) { .byte WallColor(col,row) } }
*=$3600 "Prepared incoming wall bitmap columns"
incomingPixels:
    .for (var col=40;col<72;col++) { .for (var row=0;row<104;row++) { .byte WallByte(col,row) } }
.errorif *>$4400,"Incoming columns overlap hidden attributes"

*=$2000 "Own original wall and horizon artwork"
    .for (var row=0;row<17;row++) {
        .for (var col=0;col<40;col++) {
            .for (var line=0;line<8;line++) {
                .if (row<13) { .byte WallByte(col,row*8+line) }
                else { .byte HorizonByte(col,(row-13)*8+line) }
            }
        }
    }
*=$8000 "Per-floor-line runtime state"
    .for (var line=0;line<FLOOR_LINES;line++) {
        .var offsets=List().add(0,2,4,6)
        .byte (line+offsets.get(floor(line/16)))&7
    }
    .fill FLOOR_LINES,0
    .fill FLOOR_LINES,40
*=$8400 "Floor bitmap attributes"
    .for (var row=0;row<25;row++) {
        .for (var col=0;col<40;col++) { .byte (row<17 ? $00 : ((row&1)==1 ? $60 : $e0)) }
    }

*=$9000 "Hidden wall row copy functions"
pixelJobs:
    .for (var bank=0;bank<2;bank++) {
        .for (var row=0;row<13;row++) {
            .for (var col=0;col<40;col++) {
                lda $2000+bank*$4000+row*320+(col+1)*8,y
                sta $2000+(1-bank)*$4000+row*320+col*8,y
            }
            rts
        }
    }
.errorif * != pixelJobs+26*241,"Pixel job table stride"
.errorif *>$aa00,"Pixel functions overlap floor helpers"
*=$aa00 "Generated live floor byte-shift helpers"
floorCopyJobs:
    .for (var row=0;row<8;row++) {
        .for (var col=0;col<39;col++) {
            lda FLOOR_START+row*320+(col+1)*8,y
            sta FLOOR_START+row*320+col*8,y
        }
        rts
    }
.errorif * != floorCopyJobs+8*235,"Floor helper stride"
.errorif *>FLOOR_START,"Floor helpers overlap visible bitmap"
* = FLOOR_START "Initial own floor bitmap, later shifted live"
    .for (var row=0;row<8;row++) {
        .for (var col=0;col<40;col++) {
            .for (var line=0;line<8;line++) { .byte FloorByte(row*8+line,col) }
        }
    }
*=$c000 "Prepared skewed floor streams,512pixels per line"
floorStream:
    .for (var line=0;line<FLOOR_LINES;line++) {
        .for (var col=0;col<64;col++) { .byte FloorByte(line,col) }
    }
.errorif *!=$d000,"Normal LOAD must end before I/O"
