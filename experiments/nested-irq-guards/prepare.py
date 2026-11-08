#!/usr/bin/env python3
"""Create a small original status font and screen."""
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from font5x7 import font_bytes
out = Path(__file__).resolve().parent / "build"
out.mkdir(exist_ok=True)
font = font_bytes()
screen = bytearray([32])*1024
for row,text in {
2:"      PER CALL SITE IRQ GUARDS",
4:"SITE    START    DONE     SKIP",
6:"  0     0000     0000     0000",
8:"  1     0000     0000     0000",
11:"CURRENT DEPTH 0    MAX DEPTH 0",
14:"SAME ROUTINE FROM TWO CALL SITES",
16:"EACH SITE SKIPS ITS OWN REENTRY",
18:"OTHER IRQ JOBS KEEP RUNNING",
20:"FAST JOBS 0000   FIELDS 0000",
23:"COUNTERS ARE HEXADECIMAL",
}.items():
    assert len(text)<=40
    screen[row*40:row*40+len(text)] = text.encode("ascii")
(out / "font.bin").write_bytes(font)
(out / "screen.bin").write_bytes(screen)
