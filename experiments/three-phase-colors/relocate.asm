// The row-counter-tunnel relocation technique fits here without its FLD kernel.
// All destinations move upward. Copy highest assets and highest bytes first,
// preserving every still-unread packed source through the bank1 destinations.
.for (var asset = 11; asset >= 0; asset--) {
    .var bank = floor(asset/3)
    .var phase = mod(asset,3)
    .var destination = bank*$4000+$2800+phase*$800
    .for (var page = 7; page >= 0; page--) {
        ldx #(page == 7 ? $7f : $ff)
    !copy:
        lda fontSource+asset*1920+page*$100,x
        sta destination+page*$100,x
        dex
        cpx #$ff
        bne !copy-
    }
}
