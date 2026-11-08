#!/usr/bin/env python3
"""Create our original eight-row teaching picture; no production assets."""
from pathlib import Path

FONT = {
    "A": [14,17,17,31,17,17,17], "L": [16,16,16,16,16,16,31],
    "8": [14,17,17,14,17,17,14], "R": [30,17,17,30,20,18,17],
    "O": [14,17,17,17,17,17,14], "W": [17,17,17,21,21,21,10],
    "S": [15,16,16,14,1,1,30], " ": [0]*7,
}
out = Path(__file__).resolve().parent / "build"
out.mkdir(exist_ok=True)
picture = bytearray(320)
message = "ALL 8 ROWS"
left = (320-len(message)*24)//2
for y in range(8):
    for x in range(320):
        bit = (x % 8 == y) if x < 24 or x >= 296 else y == 7
        if y < 7 and left <= x < left+len(message)*24:
            character, column = divmod((x-left)//4, 6)
            bit = column < 5 and bool(FONT[message[character]][y] & (16 >> column))
        if bit:
            picture[y*40+x//8] |= 128 >> (x%8)
(out / "picture.bin").write_bytes(picture)
