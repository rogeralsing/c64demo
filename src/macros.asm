.importonce

// Fill complete, page-aligned pages with the byte in A. The page stores are
// generated at assembly time; X visits all 256 offsets at runtime.
// Preserves A and Y. Clobbers X and N/Z; returns X = 0. No RTS is emitted.
.macro FillPages(address, pages) {
    .errorif address < 0 || address > $ffff || (address & $ff) != 0, "FillPages requires a page-aligned 16-bit address"
    .errorif pages < 1 || pages > 256 || pages != floor(pages), "FillPages requires 1..256 whole pages"
    .errorif address + pages * $100 > $10000, "FillPages exceeds the 16-bit address space"
    ldx #0
!loop:
    .for (var page = 0; page < pages; page++) {
        sta address + page * $100,x
    }
    inx
    .if (pages <= 41) {
        bne !loop-
    } else {
        beq !done+
        jmp !loop-
    }
!done:
}

// Emit one absolute indexed store per column of a column-major charset canvas.
// A supplies the fill byte; X supplies the pixel row, in 0..127.
// Preserves all registers and flags. No loop, register load, or RTS is emitted.
.macro StoreColumns(address, count) {
    .errorif address < $100 || address > $ffff || address != floor(address), "StoreColumns requires an absolute 16-bit address"
    .errorif count < 1 || count > 16 || count != floor(count), "StoreColumns requires 1..16 whole columns"
    .errorif address + count * $80 > $10000, "StoreColumns exceeds the 16-bit address space"
    .for (var column = 0; column < count; column++) {
        sta address + column * $80,x
    }
}
