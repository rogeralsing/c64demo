#!/usr/bin/env python3
"""Original small font/text packed into frozen-row sprite pointer sets."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ART=json.loads((HERE/"artwork.json").read_text())
GLYPHS=ART["glyph_rows"]
LINES=ART["lines"]


def main():
    output=HERE/"build"
    output.mkdir(exist_ok=True)
    scanlines=[]
    for text in LINES:
        for row in range(8):
            bits=[(GLYPHS[char][row]>>(4-x))&1 if row<7 and x<5 else 0
                  for char in text for x in range(6)]
            scanlines.append(bytes(sum(bits[start+bit]<<(7-bit) for bit in range(8))
                                   for start in range(0,192,8)))
    for half in range(2):
        bank=bytearray(16384)
        for row in range(16):
            for sprite in range(8):
                pointer=row*8+sprite
                bank[pointer*64+53:pointer*64+56]=scanlines[half*16+row][sprite*3:sprite*3+3]
                bank[row*1024+1016+sprite]=pointer
        (output/f"bank{half+1}.bin").write_bytes(bank)
    (output/"text.json").write_text(json.dumps({"lines":LINES,"glyph_rows":GLYPHS,
        "logical_width":192,"physical_width":384,"scanline_period":32},indent=2)+"\n")
    print("Prepared four original text rows and32 frozen-row sprite pointer sets.")


if __name__=="__main__":
    main()
