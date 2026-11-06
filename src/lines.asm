// Inclusive integer Bresenham, specialized for the four top-to-bottom octants.
// The previous loop-based drawer kept Y as the actual pixel row, shifted a mask
// on horizontal steps, and changed the pointer by 128 bytes at column crossings.
// Here each possible X has generated code with its mask and column baked in.
// Horizontal steps therefore fall through to the next block without pointer work.

// This module owns $d0..$d4. The cube's coordinates and deltas remain at $f3..$f8.
.label fastLineTable = $d0
.label fastLineEnd = $d2
.label fastLineError = $d4

drawLine:
    lda lineY0
    cmp lineY1
    bcc !ordered+
    beq !ordered+
    ldx lineY1
    stx lineY0
    sta lineY1
    lda lineX0
    ldx lineX1
    stx lineX0
    sta lineX1
!ordered:
    lda lineY1
    sec
    sbc lineY0
    sta lineDY
    lda lineX1
    sec
    sbc lineX0
    bcs !right+
    eor #$ff
    clc
    adc #1
    sta lineDX
    cmp lineDY
    bcc !steepLeft+
    lsr
    sta fastLineError
    lda #>fastFlatLeftTableA
    ldx #>fastFlatLeftTableB
    jmp fastLineSelected
!steepLeft:
    lda lineDY
    lsr
    sta fastLineError
    lda #>fastSteepLeftTableA
    ldx #>fastSteepLeftTableB
    jmp fastLineSelected
!right:
    sta lineDX
    cmp lineDY
    bcc !steepRight+
    lsr
    sta fastLineError
    lda #>fastFlatRightTableA
    ldx #>fastFlatRightTableB
    jmp fastLineSelected
!steepRight:
    lda lineDY
    lsr
    sta fastLineError
    lda #>fastSteepRightTableA
    ldx #>fastSteepRightTableB

fastLineSelected:
    ldy drawBufferHi
    cpy #>CHARSET_B
    bne !bufferSelected+
    txa
!bufferSelected:
    sta fastLineTable+1
    lda #0
    sta fastLineTable

    // Every dispatch table occupies one page: 128 low bytes, then 128 high bytes.
    ldy lineX0
    lda (fastLineTable),y
    sta fastLineDispatch+1
    tya
    ora #$80
    tay
    lda (fastLineTable),y
    sta fastLineDispatch+2
    ldy lineX1
    lda (fastLineTable),y
    sta fastLineEnd
    tya
    ora #$80
    tay
    lda (fastLineTable),y
    sta fastLineEnd+1

    // Replace TAX at the final X with RTS, returning before that column is drawn.
    // The common final run then draws the remaining pixels at the final X.
    // Its remaining pixels are vertical. A flat line has only one pixel left.
    ldy #0
    lda #$60
    sta (fastLineEnd),y

    // Endpoint tables replace per-edge mask shifts and column arithmetic.
    ldx lineX1
    lda fastLineEndMasks,x
    sta fastLineTailMask+1
    lda fastLineEndAddressLo,x
    sta fastLineTailRead+1
    sta fastLineTailWrite+1
    lda fastLineEndAddressHi,x
    clc
    adc drawBufferHi
    sta fastLineTailRead+2
    sta fastLineTailWrite+2
    lda lineY1
    clc
    adc #1
    sta fastLineTailEnd+1

    ldy lineY0
    lda fastLineError
    sec
fastLineDispatch:
    jsr $ffff
    jsr fastLineTail

    // Restore the original TAX before another edge can use this block.
    ldy #0
    lda #$aa
    sta (fastLineEnd),y
    rts

fastLineTail:
fastLineTailMask:
    lda #0
fastLineTailRead:
    ora $ffff,y
fastLineTailWrite:
    sta $ffff,y
    iny
fastLineTailEnd:
    cpy #0
    bne fastLineTail
    rts

// Carry is set on entry to every pixel. A successful SBC preserves it; after
// a borrow, ADC major restores it because major is at least as large as minor.
// IRQs preserve A and processor flags, so this invariant also survives the clock.
.macro FastLineKernel(steep, right, buffer) {
    .for (var index = 0; index < 128; index++) {
        .var pixelX = right ? index : 127-index
        .var mask = $80 >> (pixelX & 7)
        .var address = buffer + floor(pixelX / 8) * 128
    pixel:
        tax
        lda #mask
        ora address,y
        sta address,y
        .if (steep) { iny }
        txa
        .if (steep) { sbc lineDX } else { sbc lineDY }
        .if (steep) { bcs pixel } else { bcs !next+ }
        .if (steep) { adc lineDY } else { adc lineDX; iny }
    !next:
    }
}

// Each block is exactly 17 bytes. These ranges are temporarily patched only at
// the first byte of the current line's final-X block, then restored.
fastLineKernelsStart:
fastSteepRightA:
    FastLineKernel(true, true, CHARSET_A)
    .assert "Steep right A kernel size", *-fastSteepRightA, 128*17
fastSteepLeftA:
    FastLineKernel(true, false, CHARSET_A)
    .assert "Steep left A kernel size", *-fastSteepLeftA, 128*17
fastFlatRightA:
    FastLineKernel(false, true, CHARSET_A)
    .assert "Flat right A kernel size", *-fastFlatRightA, 128*17
fastFlatLeftA:
    FastLineKernel(false, false, CHARSET_A)
    .assert "Flat left A kernel size", *-fastFlatLeftA, 128*17
fastSteepRightB:
    FastLineKernel(true, true, CHARSET_B)
    .assert "Steep right B kernel size", *-fastSteepRightB, 128*17
fastSteepLeftB:
    FastLineKernel(true, false, CHARSET_B)
    .assert "Steep left B kernel size", *-fastSteepLeftB, 128*17
fastFlatRightB:
    FastLineKernel(false, true, CHARSET_B)
    .assert "Flat right B kernel size", *-fastFlatRightB, 128*17
fastFlatLeftB:
    FastLineKernel(false, false, CHARSET_B)
    .assert "Flat left B kernel size", *-fastFlatLeftB, 128*17
fastLineKernelsEnd:

.macro FastLineTable(kernel, right) {
    .fill 128, <(kernel + (right ? i : 127-i) * 17)
    .fill 128, >(kernel + (right ? i : 127-i) * 17)
}

.align $100
fastLineTablesStart:
fastSteepRightTableA: FastLineTable(fastSteepRightA, true)
fastSteepLeftTableA:  FastLineTable(fastSteepLeftA, false)
fastFlatRightTableA:  FastLineTable(fastFlatRightA, true)
fastFlatLeftTableA:   FastLineTable(fastFlatLeftA, false)
fastSteepRightTableB: FastLineTable(fastSteepRightB, true)
fastSteepLeftTableB:  FastLineTable(fastSteepLeftB, false)
fastFlatRightTableB:  FastLineTable(fastFlatRightB, true)
fastFlatLeftTableB:   FastLineTable(fastFlatLeftB, false)
fastLineTablesEnd:

// Each 128-byte table starts at page offset $00 or $80. Since X is in 0..127,
// indexed loads never cross a page and keep a fixed four-cycle lookup cost.
.align $100
fastLineEndpointTablesStart:
fastLineEndMasks:
    .fill 128, $80 >> (i & 7)
fastLineEndAddressLo:
    .fill 128, <(floor(i / 8) * $80)
fastLineEndAddressHi:
    .fill 128, >(floor(i / 8) * $80)
fastLineEndpointTablesEnd:

// Persistent code patches: fastLineDispatch+1..+2, fastLineTailMask+1,
// fastLineTailRead+1..+2, fastLineTailWrite+1..+2, fastLineTailEnd+1.
// Runtime workspace: $d0..$d4 plus the caller's line coordinates and deltas.
// No undocumented opcodes are used.
