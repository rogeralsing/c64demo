// A standalone demonstration of raster continuations and cooperative waits.
// The technique follows Trident's published anonymous-IRQ/protothread example.
// This implementation is original to this repository; no author code is copied.

BasicUpstart2(start)

.const SCREEN = $0400
.const COLOR_RAM = $d800
.const FRAMES_PER_SCENE = 100

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
    sta $d020
    sta $d021
    sta frameCounter
    sta frameCounter+1
    sta sceneTicks
    sta scenePhase
    lda #$1b
    sta $d011
    lda #$08
    sta $d016
    lda #$14
    sta $d018
    lda #$03
    sta $dd00

    ldx #0
!clear:
    lda #$20
    sta SCREEN,x
    sta SCREEN+$100,x
    sta SCREEN+$200,x
    sta SCREEN+$300,x
    lda #1
    sta COLOR_RAM,x
    sta COLOR_RAM+$100,x
    sta COLOR_RAM+$200,x
    sta COLOR_RAM+$300,x
    inx
    bne !clear-

    ldx #0
!title:
    lda title,x
    beq !subtitle+
    sta SCREEN+3*40+4,x
    inx
    bne !title-
!subtitle:
    ldx #0
!copySubtitle:
    lda subtitle,x
    beq !instructions+
    sta SCREEN+6*40+3,x
    inx
    bne !copySubtitle-
!instructions:
    ldx #0
!copyInstructions:
    lda instructions,x
    beq !ready+
    sta SCREEN+10*40+3,x
    inx
    bne !copyInstructions-
!ready:
    lda #<sceneGreen
    sta sceneResume
    lda #>sceneGreen
    sta sceneResume+1
    lda #<rasterTop
    sta rasterResume
    lda #>rasterTop
    sta rasterResume+1
    lda #<irqEntry
    sta $fffe
    lda #>irqEntry
    sta $ffff
    lda #<nmiReturn
    sta $fffa
    lda #>nmiReturn
    sta $fffb
    lda #0
    sta $d012
    lda #1
    sta $d019
    sta $d01a
    cli
idle:
    jmp idle

// Each IRQ enters through this register-preserving dispatcher. The continuation
// selects the next segment, while the IRQ vector itself stays fixed.
irqEntry:
    pha
    txa
    pha
    tya
    pha
    jmp (rasterResume)

irqReturn:
    lda #1
    sta $d019
    pla
    tay
    pla
    tax
    pla
nmiReturn:
    rti

// This macro yields the current raster segment and resumes its following code
// at a later IRQ. It schedules a line; it does not stabilize a particular cycle.
.macro WaitRaster(line) {
    lda #<!resume+
    sta rasterResume
    lda #>!resume+
    sta rasterResume+1
    lda #line
    sta $d012
    jmp irqReturn
!resume:
}

rasterTop:
    lda #14
    sta $d020
    WaitRaster($40)
    lda #2
    sta $d020
    WaitRaster($80)
    lda #3
    sta $d020
    WaitRaster($f8)
    lda #4
    sta $d020
    inc frameCounter
    bne !counterDone+
    inc frameCounter+1
!counterDone:
    jsr sceneTick
frameComplete:
    WaitRaster(0)
    jmp rasterTop

// A scene call either consumes one frame of its wait or jumps to the saved
// continuation. The IRQ caller remains free to finish immediately after RTS.
sceneTick:
    lda sceneTicks
    beq !resume+
    dec sceneTicks
    bne !waiting+
!resume:
    jmp (sceneResume)
!waiting:
    rts

.macro WaitSceneFrames(frames) {
    lda #frames
    sta sceneTicks
    lda #<!resume+
    sta sceneResume
    lda #>!resume+
    sta sceneResume+1
    rts
!resume:
}

sceneGreen:
    lda #5
    sta $d021
    lda #0
    sta scenePhase
    lda #$31
    sta SCREEN+10*40+10
    WaitSceneFrames(FRAMES_PER_SCENE)
sceneBlue:
    lda #6
    sta $d021
    lda #1
    sta scenePhase
    lda #$32
    sta SCREEN+10*40+10
    WaitSceneFrames(FRAMES_PER_SCENE)
    jmp sceneGreen

rasterResume: .word rasterTop
sceneResume: .word sceneGreen
sceneTicks: .byte 0
scenePhase: .byte 0
frameCounter: .word 0

.encoding "screencode_mixed"
title: .text "irq continuations + frame waits"
    .byte 0
subtitle: .text "border: four scheduled raster bands"
    .byte 0
instructions: .text "scene: 1  changes every 100 frames"
    .byte 0
