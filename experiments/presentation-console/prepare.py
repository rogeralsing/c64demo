#!/usr/bin/env python3
"""Original mock-DOS/source-viewer/SID-menu assets and oscillator constants."""
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
from font5x7 import font_bytes

OUT = HERE / "build"
OUT.mkdir(exist_ok=True)
font = bytearray(font_bytes())
for char,rows in {
    ".":[0,0,0,0,0,6,6], ":":[0,6,6,0,6,6,0],
    ">":[16,8,4,2,4,8,16], "$":[4,15,20,14,5,30,4],
    "#":[10,31,10,10,31,10,0], "-":[0,0,0,31,0,0,0],
    ";":[0,6,6,0,6,4,8], "(":[2,4,8,8,8,4,2],
    ")":[8,4,2,2,2,4,8], "/":[1,2,2,4,8,8,16],
}.items():
    for y,v in enumerate(rows):
        font[ord(char)*8+y] = v<<1
(OUT / "font.bin").write_bytes(font)


def screen(lines):
    data = bytearray([32])*1024
    for row,text in lines.items():
        assert len(text)<=38,(row,text)
        data[row*40+1:row*40+1+len(text)] = text.encode("ascii")
    return bytes(data)


pages = [
    {2:"C64 DEMO DOS",4:"ORIGINAL PRESENTATION EXAMPLE",7:"DIR    SHOW THE DEMO FILES",
     9:"EDIT   OPEN THE SOURCE VIEWER",11:"SID    OPEN THE SOUND MENU",13:"HELP   SHOW THE CONTROLS",
     18:"READY.",21:">",23:"TYPE A COMMAND AND PRESS RETURN"},
    {2:"SOURCE AND NOTES VIEWER",22:"W S SCROLL   R TOP   Q DOS"},
    {2:"C64 SID SOUND CONFIGURATION",4:"SELECT AN ORIGINAL SYNTH PATTERN",7:"> 1 PULSE WALK",
     9:"  2 TRIANGLE DRIFT",11:"  3 NOISE TICKS",15:"1 2 3 SELECT AND PLAY",
     17:"RETURN RESTARTS THE SELECTION",20:"SPACE STOPS   Q RETURNS TO DOS"},
    {2:"DEMO DIRECTORY AND HELP",5:"DEMO.ASM     ORIGINAL SOURCE TEXT",
     7:"NOTES.TXT    OWN TECHNICAL NOTES",9:"SID.MENU     THREE OWN SYNTH LOOPS",
     13:"THIS IS A MOCK FILE ENVIRONMENT",15:"NO DISK OR HOST FILES ARE CHANGED",
     20:"Q RETURNS TO THE DOS PROMPT"},
]
(OUT / "pages.bin").write_bytes(b"".join(screen(p) for p in pages))
notes = ["; ORIGINAL C64 DEMO EXAMPLE","START:","    LDA #$00","    STA $D020","    STA $D021","    JSR MUSIC","LOOP:","    JMP LOOP","","; THE VIEWER IS READ ONLY","; W AND S MOVE THE VIEWPORT","; R RETURNS TO THE FIRST ROW","; Q RETURNS TO DEMO DOS","","; THIS TEXT IS OUR OWN","; IT IS NOT THE RELEASE NOTE","","MUSIC:","    LDA NOTELOW","    STA $D400","    LDA NOTEHIGH","    STA $D401","    RTS","","; THE REAL PROGRAM HAS THREE","; SMALL SYNTHETIC SID LOOPS","; ALL NOTES ARE GENERATED HERE","; NO EXTERNAL SID IS LOADED","","; PAGES USE A HIDDEN MATRIX","; PUBLICATION HAPPENS AT THE","; NEXT TOP BORDER","","; KEY INPUT USES KERNAL GETIN","; THE NORMAL KERNAL KEY SCAN","; CONTINUES WHILE WE DISPLAY","; OUR OWN ASCII INDEXED FONT","","; PULSE TRIANGLE AND NOISE","; ARE PHYSICAL SID WAVEFORMS","; THE MENU CHANGES REGISTERS","; THE AUDIO IS EMULATED SID","","; THIS TEACHING EXAMPLE IS","; INSPIRED BY THE DOCUMENTED","; C64 MOCK DOS PRESENTATION","; IT DOES NOT COPY ITS FILES","","; BUILD SH CREATES THE PRG","; RUN SH OPENS A NORMAL PAL","; VICE SESSION","","; THE NATIVE VERIFIER TYPES","; COMMANDS THROUGH THE NORMAL","; VICE KEYBOARD QUEUE","; IT CHECKS THE RESULTING UI","; AND THE ACTUAL SID WRITES","","; END OF THE OWN NOTE","","","","","",""]
while notes and not notes[-1]:
    notes.pop()
assert len(notes)<=64,len(notes)
notes.extend([" "]*(64-len(notes)))
(OUT / "notes.bin").write_bytes(b"".join(s[:32].ljust(32).encode("ascii") for s in notes))
freq = [round(440*2**((midi-69)/12)*2**24/985248) for midi in range(48,73)]
source = ["frequencyLo: .byte "+",".join(str(v&255) for v in freq),
          "frequencyHi: .byte "+",".join(str(v>>8) for v in freq)]
(OUT / "frequencies.asm").write_text("\n".join(source)+"\n")
