// Original 1541 program: VIA serial output is the video DAC; Timer1 PB7 drives
// adjacent stepper phases. No C64 VIC/SID generates the resulting signal.
.label frameCounter = $02f0
.label BLACK = $02
.label SYNC = $08
.label MOTOR = $64

* = $0300 "1541 video and stepper controller"
driveStart:
    sei
    cld
    ldx #$ff
    txs
    lda #$7f
    sta $180e
    sta $1c0e
    lda $180d
    lda $1c0d
    lda #$1a
    sta $1802
    lda #$6f
    sta $1c02
    lda #0
    sta $1c0b
    lda #$c0
    sta $180b
    lda #<$046e
    sta $1804
    lda #>$046e
    sta $1805
    lda #BLACK
    sta $1800
    lda #0
    sta frameCounter

frameStart:
    // Timer2 bounds the field; Timer1 remains available for mechanical sound.
    lda #<(20000-2)
    sta $1c08
    lda #>(20000-2)
    sta $1c09
    inc frameCounter
    lda frameCounter
    lsr
    lsr
    lsr
    lsr
    tax
    lda noteLo,x
    sta $1806
    lda noteHi,x
    sta $1807

    jsr verticalSync
    ldx #28
    jsr blankLines
    ldx #0
    ldy frameCounter
    jsr visibleLines
    ldx #21
    jsr blankLines
!timer:
    // Keep sampling the actual timer waveform while waiting for field end.
    lda $1800
    asl
    lda #MOTOR
    adc #0
    sta $1c00
    lda $1c0d
    and #$20
    beq !timer-
    jmp frameStart

// Every continuing visible iteration takes exactly64 drive CPU cycles.
// The aligned tables avoid indexed-load page penalties. Each output value
// remains on the pins for eight cycles, giving deliberately coarse columns.
visibleLines:
!line:
    bit $00
    // Explicit sync does not rely on the released demo's port-read precondition.
    // LDA/ASL samples the real timer PB7; LDA/STA preserves that carry.
    lda $1800
    asl
    lda #SYNC
    sta $1800
    lda #BLACK
    sta $1800
    adc #MOTOR-BLACK
    sta $1c00
    lda column0,y
    sta $1800
    lda column1,y
    sta $1800
    lda column2,y
    sta $1800
    lda #BLACK
    sta $1800
    iny
    dex
    bne !line-
    rts

// Offscreen line timing also services the stepper. The final branch and
// routine handovers are explicit gaps, not a claim of PAL conformance.
blankLines:
!line:
    bit $00
    lda $1800
    asl
    lda #SYNC
    sta $1800
    lda #BLACK
    sta $1800
    adc #MOTOR-BLACK
    sta $1c00
    .for (var delay=0; delay<16; delay++) { nop }
    dex
    bne !line-
    rts

verticalSync:
    lda #SYNC
    ldy #BLACK
    // Ten32-cycle broad half-lines:28 cycles of sync and4 of black.
    // Sampling PB7 inside each pulse preserves waveform-to-stepper coupling.
    .for (var pulse=0; pulse<10; pulse++) {
        sta $1800
        lda $1800
        asl
        lda #MOTOR
        adc #0
        sta $1c00
        lda #SYNC
        nop
        nop
        nop
        nop
        sty $1800
    }
    rts

noteLo: .fill 16, <(i<4 ? $046e : (i<8 ? $03f0 : (i<12 ? $0354 : $02f0)))
noteHi: .fill 16, >(i<4 ? $046e : (i<8 ? $03f0 : (i<12 ? $0354 : $02f0)))
.errorif * > $0500, "Drive code overlaps prepared column tables"

* = $0500 "Reusable first column"
column0: .fill 256, mod(floor(i/16),2)==0 ? 0 : BLACK
* = $0600 "Reusable second column"
column1: .fill 256, mod(floor((i+8)/16),2)==0 ? 0 : BLACK
* = $0700 "Reusable third column"
column2: .fill 256, mod(floor((i+16)/16)+floor(i/64),2)==0 ? 0 : BLACK
