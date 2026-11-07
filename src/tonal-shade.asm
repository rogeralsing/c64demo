.importonce

// TONAL first fills raw material selectors, then shades only the selected
// physical-row field. Zero stays black; every enabled pair preserves its hue.
// The engine emits the low macro in ICOSAHEDRON's unused sineSize page and
// calls tonalShade after xorFill. The high macro uses padding before the zoom.
// A/X/Y and flags are clobbered. Prefix-fill workspace is dead at this point.
.label tonalRowMask = $d3
.label tonalEndRow = $d4

.macro TonalShadeLowPage() {
@tonalLowPageStart:
    .assert "Tonal low-page alignment", * & $ff, 0
@tonalGradientMask:
    .var bayer = List().add(0,8,2,10, 12,4,14,6, 3,11,1,9, 15,7,13,5)
    .for (var row = 0; row < 128; row++) {
        .var density = max(0, min(16, 16-floor((row-8)*17/112)))
        .var mask = 0
        .for (var lane = 0; lane < 4; lane++) {
            .if (bayer.get((row & 3)*4+lane) < density) {
                .eval mask = mask | (3 << (6-2*lane))
            }
        }
        .byte mask
    }
@tonalGradientMaskEnd:
    .assert "Tonal gradient mask size", tonalGradientMaskEnd-tonalGradientMask, 128

@tonalLowCodeStart:
@tonalShade:
    // One shared absolute,Y row kernel serves both charsets. Patch the high
    // bytes for two neighboring columns per iteration; their low bytes differ
    // by $80. Patching also occurs on empty fields, keeping code state explicit.
    ldy drawBufferHi
    ldx #0
!patch:
    tya
    sta tonalShadeCells+2,x
    sta tonalShadeCells+7,x
    sta tonalShadeCells+10,x
    sta tonalShadeCells+15,x
    iny
    txa
    clc
    adc #16
    tax
    bpl !patch-

    lda interlaceMinQ
    cmp #64
    bcs !done+
    cmp interlaceMaxQ
    bcc !rows+
    bne !done+
!rows:
    // Prefix fill includes a possible final zero closure row. Shade that same
    // range, including its zeros; the opposite parity remains untouched.
    lda interlaceMaxQ
    clc
    adc #1
    asl
    ora interlaceFieldParity
    sta tonalEndRow
    lda interlaceMinQ
    asl
    ora interlaceFieldParity
    tay
    jmp tonalShadeRowLoop
!done:
    rts
@tonalLowCodeEnd:
    .errorif * > tonalLowPageStart+$100, "Tonal mask/setup exceeds its replacement page"
    .fill tonalLowPageStart+$100-*, 0
@tonalLowPageEnd:
    .assert "Tonal low-page size", tonalLowPageEnd-tonalLowPageStart, 256
}

.macro TonalShadeHighCode() {
@tonalShaderCodeStart:
@tonalShadeRowLoop:
    lda tonalGradientMask,y
    sta tonalRowMask
@tonalShadeCells:
    .for (var column = 0; column < 16; column++) {
        // Column bases end in $00/$80; Y is a physical row 0..127, so these
        // LDA absolute,Y reads never cross a page. STA always costs 5 cycles.
        lda CHARSET_A+column*128,y
        and tonalRowMask
        sta CHARSET_A+column*128,y
    }
@tonalShadeCellsEnd:
    .assert "Tonal row kernel size", tonalShadeCellsEnd-tonalShadeCells, 16*8
    iny
    iny
    cpy tonalEndRow
    bcs !done+
    jmp tonalShadeRowLoop
!done:
    rts
@tonalShaderCodeEnd:
    .errorif * > $4b00, "Tonal row shader overlaps the icosahedron zoom page"
}
