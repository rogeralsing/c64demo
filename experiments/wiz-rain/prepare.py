#!/usr/bin/env python3
"""Own WIZ ripple height atlas and reusable character/light tables."""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    output = HERE / "build"
    output.mkdir(exist_ok=True)
    heights = [15.0] * 1024
    for phase in range(16):
        age = phase / 16
        radius = .4 + age * 5.2
        center = phase * 64
        for dy in range(-7,8):
            for dx in range(-8,9):
                distance = math.hypot(dx,dy*1.5)
                wave = 10 * (1-age) * math.sin((distance-radius)*math.pi)
                wave *= math.exp(-((distance-radius)/1.1)**2)
                heights[(center+dx+40*dy)%1024] += wave
    height = bytes(max(0,min(31,math.floor(value+.5))) for value in heights)
    (output/"height.bin").write_bytes(height)
    (output/"height-padded.bin").write_bytes(height[-40:]+height+height[:40])
    bayer = ((0,8,2,10),(12,4,14,6),(3,11,1,9),(15,7,13,5))
    font = bytearray(2048)
    for shade in range(16):
        for y in range(8):
            for x in range(4):
                level = max(0,min(3,math.floor(shade/5+(bayer[y%4][x]+.5)/16)))
                font[shade*8+y] |= level << (6-2*x)
    (output/"font.bin").write_bytes(font)
    shades = bytes(max(0,min(15,(value-96)//4)) for value in range(256))
    (output/"shade.bin").write_bytes(shades)
    multiply = bytes((factor*value if value<128 else factor*(value-256))%256
                     for factor in (-2,-1,0,1,2) for value in range(256))
    (output/"multiply.bin").write_bytes(multiply)
    initial = bytes(shades[(128+2*(height[(i+1)%1024]-height[(i-1)%1024]))%256]
                    for i in range(1024))
    (output/"initial.bin").write_bytes(initial)
    (output/"atlas.json").write_text(json.dumps({"phases":16,"view_step_cells":64,
        "height_min":min(height),"height_max":max(height),
        "height_equation":"15 + sum 10*(1-age)*sin(pi*(r-radius))*exp(-((r-radius)/1.1)^2)",
        "radius":".4 + 5.2*age","distance":"sqrt(dx^2+(1.5*dy)^2)"},indent=2)+"\n")
    print("Prepared one 1024-cell WIZ height atlas, font and reusable lighting tables.")


if __name__ == "__main__":
    main()
