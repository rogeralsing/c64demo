#!/usr/bin/env python3
"""Create original bitmap artwork and moving multicolor cutout masks."""
import math
from pathlib import Path

FONT = {
    "G":[14,17,16,23,17,17,14], "H":[17,17,17,31,17,17,17],
    "O":[14,17,17,17,17,17,14], "S":[15,16,16,14,1,1,30],
    "T":[31,4,4,4,4,4,4], "B":[30,17,17,30,17,17,30],
    "Y":[17,17,10,4,4,4,4], "E":[31,16,16,30,16,16,31],
    "7":[31,1,2,4,8,8,8], "F":[31,16,16,30,16,16,16], " ":[0]*7,
}
OUT = Path(__file__).resolve().parent / "build"


def bitmap():
    pixels = [[False]*320 for _ in range(200)]
    for y in range(200):
        for x in range(320):
            hill = 155+13*math.sin(x*.027)+6*math.sin(x*.081)
            active = (x-266)**2+(y-49)**2 < 21**2
            if y > hill:
                active = (x+2*y)%8 < 2
            ghost = ((x-160)/21)**2+((y-93)/27)**2 < 1 or (abs(x-160)<21 and 92<=y<139+4*math.sin(x*.3))
            if ghost:
                active = True
                if (x-152)**2+(y-91)**2 < 4**2 or (x-168)**2+(y-91)**2 < 4**2:
                    active = False
                if ((x-160)/5)**2+((y-109)/8)**2 < 1:
                    active = False
            for sx,sy in ((31,48),(75,63),(106,40),(215,67),(302,103),(37,112),(234,118)):
                if (x==sx and abs(y-sy)<=2) or (y==sy and abs(x-sx)<=2):
                    active = True
            pixels[y][x] = active
    text = "GHOST BYTE"
    left = (320-len(text)*18)//2
    for y in range(21):
        for x in range(len(text)*18):
            char,col = divmod(x//3,6)
            if col<5 and FONT[text[char]][y//3] & (16>>col):
                pixels[y+10][left+x] = True
    packed = bytearray(8000)
    for y,row in enumerate(pixels):
        for x,active in enumerate(row):
            if active:
                packed[(y//8)*320+(x//8)*8+y%8] |= 128>>(x%8)
    return bytes(packed)


def mask(phase):
    data = bytearray(512)
    message = "GHOST 7FFF"
    left = (80-len(message)*6)//2 + round(3*math.sin(math.tau*phase/16))
    for y in range(21):
        for symbol in range(96):
            value = 1 if y in (0,20) else 2
            if 3<=y<17 and left<=symbol<left+len(message)*6:
                char,col = divmod(symbol-left,6)
                if col<5 and FONT[message[char]][(y-3)//2] & (16>>col):
                    value = 0
            sprite,within = divmod(symbol,12)
            offset = sprite*64+y*3+within//4
            data[offset] |= value << (6-2*(within%4))
    return bytes(data)


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / "bitmap.bin").write_bytes(bitmap())
    (OUT / "masks.bin").write_bytes(b"".join(mask(i) for i in range(16)))


if __name__ == "__main__":
    main()
