#!/usr/bin/env python3
"""Paint a black circle in the supplied Koala scene without palette changes."""

from collections import deque
import hashlib
import json
from pathlib import Path

BLACK_CIRCLE_RADIUS = 43
BLACK_CIRCLE_VERTICAL_INSET = 1


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
    black_circle = {(x, y) for y in range(200) for x in range(160)
                    if (2*x+1-center_x)**2+(abs(y+0.5-center_y)+BLACK_CIRCLE_VERTICAL_INSET)**2
                    <= BLACK_CIRCLE_RADIUS**2}
    # Selector 00 uses the image's existing global black. Change only the
    # chosen circle's bits; keep all surrounding pixels and color slots intact.
    for x, y in black_circle:
        cell = (y // 8) * 40 + x // 4
        bitmap[cell*8+y%8] &= ~(3 << (6-2*(x%4)))
    output.mkdir(parents=True, exist_ok=True)
    (output / "ball-bitmap.bin").write_bytes(bitmap)
    (output / "ball-screen.bin").write_bytes(screen)
    (output / "ball-colors.bin").write_bytes(colors)
    metadata = {"source": "assets/scene.koa", "source_sha256": hashlib.sha256(source).hexdigest(),
                "center": [center_x, center_y], "white_circle_pixels": len(circle),
                "black_circle_radius": BLACK_CIRCLE_RADIUS, "black_circle_pixels": len(black_circle),
                "black_circle_vertical_inset": BLACK_CIRCLE_VERTICAL_INSET,
                "background": background, "interior_background": 0, "dithering": False,
                "rim_dithering": False, "circle_selector": "00 for solid black interior",
                "opaque_rim_pixels": 0}
    (output / "scene.json").write_text(json.dumps(metadata, indent=2)+"\n")
    constants = {"CENTER_X": center_x, "CENTER_Y": center_y,
                 "X_BIAS": (center_x-104) & 255, "Y_BIAS": (center_y-78) & 255,
                 "X_OFFSET": center_x-128, "Y_OFFSET": center_y-128}
    (output / "scene.asm").write_text("// Graphics origin measured from the supplied white circle.\n"+
                                    "".join(f".const SCENE_{key} = {value}\n" for key, value in constants.items()))
    print(json.dumps(metadata))


if __name__ == "__main__":
    prepare(Path(__file__).resolve().parent / "build")
