#!/usr/bin/env python3
"""Prepare the supplied Koala scene for sprites behind its undithered circle."""

from collections import deque
import hashlib
import json
from pathlib import Path


def prepare(output):
    source = (Path(__file__).resolve().parent / "assets" / "scene.koa").read_bytes()
    if len(source) != 10003:
        raise ValueError("Expected a 10003-byte Koala multicolor image")
    bitmap = bytearray(source[2:8002])
    screen = bytearray(source[8002:9002])
    colors = bytearray(value & 15 for value in source[9002:10002])
    background = source[10002] & 15
    if background != 0:
        raise ValueError("The supplied scene must have a black global background")
    pixels = [[0] * 160 for _ in range(200)]
    for y in range(200):
        for x in range(160):
            cell = (y // 8) * 40 + x // 4
            value = bitmap[cell * 8 + y % 8]
            code = (value >> (6 - 2 * (x % 4))) & 3
            pixels[y][x] = (background, screen[cell] >> 4, screen[cell] & 15, colors[cell])[code]

    remaining = {(x, y) for y in range(200) for x in range(160) if pixels[y][x] == 1}
    circle = set()
    while remaining:
        first = remaining.pop()
        component, pending = {first}, deque([first])
        while pending:
            x, y = pending.popleft()
            for point in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
                if point in remaining:
                    remaining.remove(point)
                    component.add(point)
                    pending.append(point)
        if len(component) > len(circle):
            circle = component
    if len(circle) < 1000:
        raise ValueError("No large white circle found")
    center_x = round(sum(2*x+1 for x, y in circle) / len(circle))
    center_y = round(sum(y+0.5 for x, y in circle) / len(circle))
    mask = (Path(__file__).resolve().parent / "assets" / "scene-rim.pbm").read_bytes()
    header = b"P4\n160 200\n"
    if not mask.startswith(header) or len(mask) != len(header)+4000:
        raise ValueError("Expected a 160x200 binary PBM rim mask")
    mask = mask[len(header):]
    # PBM stores black as 1; white mask pixels select the opaque black rim.
    rim = {(x, y) for y in range(200) for x in range(160)
           if not mask[y*20+x//8] & (128 >> (x & 7))}
    if not rim <= circle:
        raise ValueError("The opaque rim must stay inside the source circle")
    gap_left, gap_right = (center_x-40)//8, (center_x+47)//8
    gap_top, gap_bottom = (center_y-36)//8, (center_y+43)//8
    fixed_rim_cells = []
    for cell in sorted({(y // 8) * 40 + x // 4 for x, y in circle}):
        row, column = divmod(cell, 40)
        outside = sorted({pixels[y][x] for y in range(row*8, row*8+8)
                          for x in range(column*4, column*4+4)
                          if (x, y) not in circle and pixels[y][x] != background})
        masked = any((x, y) in rim for y in range(row*8, row*8+8)
                     for x in range(column*4, column*4+4))
        if masked:
            # Selector 10 uses fixed black in the low nibble and hides sprites.
            # Reserve 01 for moving gaps only within the palette update region.
            mutable = gap_top <= row < gap_bottom and gap_left <= column < gap_right
            if len(outside) > (1 if mutable else 2):
                raise ValueError(f"Rim cell {(row, column)} needs a boundary palette correction")
            screen[cell] = 0 if mutable or not outside else outside[0] << 4
            colors[cell] = (outside[0] if outside else 0) if mutable else (outside[1] if len(outside) == 2 else 0)
            slots = (3,) if mutable else (1, 3)
            encode = {background: 0, **dict(zip(outside, slots))}
            circle_code = 1 if mutable else 0
        elif len(outside) <= 2:
            # Selector 01 is behind-sprite transparent and uses the screen high
            # nibble. Reserve it for animated gap colors; keep artwork in 10/11.
            screen[cell] = outside[0] if outside else 0
            colors[cell] = outside[1] if len(outside) == 2 else 0
            encode = {background: 0, **{color: code+2 for code, color in enumerate(outside)}}
            circle_code = 1
        else:
            # Some boundary cells need all three local artwork colors. Their
            # circle pixels use transparent global black, outside the gap area.
            fixed_rim_cells.append([row, column])
            circle_code = 0
        for y in range(row*8, row*8+8):
            packed = 0
            for x in range(column*4, column*4+4):
                original = (source[2+cell*8+y%8] >> (6-2*(x%4))) & 3
                code = (2 if (x, y) in rim else circle_code) if (x, y) in circle else (encode[pixels[y][x]] if masked or len(outside) <= 2 else original)
                decoded = (background, screen[cell] >> 4, screen[cell] & 15, colors[cell])[code]
                assert decoded == (0 if (x, y) in circle else pixels[y][x])
                packed = (packed << 2) | code
            bitmap[cell*8+y%8] = packed
    output.mkdir(parents=True, exist_ok=True)
    (output / "ball-bitmap.bin").write_bytes(bitmap)
    (output / "ball-screen.bin").write_bytes(screen)
    (output / "ball-colors.bin").write_bytes(colors)
    metadata = {"source": "assets/scene.koa", "source_sha256": hashlib.sha256(source).hexdigest(),
                "center": [center_x, center_y], "white_circle_pixels": len(circle),
                "fixed_rim_cells": fixed_rim_cells, "background": background, "dithering": False,
                "circle_selector": "01 for gaps; 00 for fixed black; 10 for opaque rim",
                "opaque_rim_pixels": len(rim)}
    (output / "scene.json").write_text(json.dumps(metadata, indent=2)+"\n")
    constants = {"CENTER_X": center_x, "CENTER_Y": center_y,
                 "X_BIAS": (center_x-104) & 255, "Y_BIAS": (center_y-78) & 255,
                 "X_OFFSET": center_x-128, "Y_OFFSET": center_y-128,
                 "GAP_LEFT": (center_x-40)//8, "GAP_RIGHT": (center_x+47)//8,
                 "GAP_TOP": (center_y-36)//8, "GAP_BOTTOM": (center_y+43)//8}
    (output / "scene.asm").write_text("// Graphics origin measured from the supplied white circle.\n"+
                                    "".join(f".const SCENE_{key} = {value}\n" for key, value in constants.items()))
    print(json.dumps(metadata))


if __name__ == "__main__":
    prepare(Path(__file__).resolve().parent / "build")
