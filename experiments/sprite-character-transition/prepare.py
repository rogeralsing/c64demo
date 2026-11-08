#!/usr/bin/env python3
"""Prepare original 2D transition art, scalar path and bounded wipe commands."""
import importlib.util
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "build"


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("shared_own_font", HERE.parent / "lib/font5x7.py")
    font_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(font_module)
    font = bytearray(font_module.font_bytes())
    patterns = ((0x81, 0x42, 0x24, 0x18, 0x18, 0x24, 0x42, 0x81),
                (0x18, 0x24, 0x42, 0x81, 0x81, 0x42, 0x24, 0x18),
                (0x88, 0x44, 0x22, 0x11, 0x88, 0x44, 0x22, 0x11),
                (0xFF, 0x81, 0x81, 0x81, 0x81, 0x81, 0x81, 0xFF))
    for glyph, rows in enumerate(patterns, 1):
        font[glyph * 8:glyph * 8 + 8] = bytes(rows)
    screen = bytearray([32] * 1024)
    colors = bytearray(1024)
    palette = (6, 14, 3, 13, 7, 10, 4, 15)
    for row in range(25):
        for column in range(40):
            screen[row * 40 + column] = 1 + (column // 5 + row // 3) % 4
            colors[row * 40 + column] = palette[(column // 4 + row) % 8]
    lines = {2: "SPRITES TO CHARACTERS", 4: "PREPARED PATH 2D TRANSITION",
             10: "LEFT SHIFT 0123456789 COLOR LANE ABCDEFGH",
             14: "RIGHT SHIFT ABCDEFGHIJK COLOR LANE 98765",
             22: "FOUR QUADRANTS CLEAR AND REPEAT"}
    for row, text in lines.items():
        line = text.center(40)[:40].encode("ascii")
        screen[row * 40:row * 40 + 40] = line
    screen[1016:1024] = bytes([0xA0] * 8)
    (OUTPUT / "font.bin").write_bytes(font)
    (OUTPUT / "screen.bin").write_bytes(screen)
    (OUTPUT / "colors.bin").write_bytes(colors)
    (OUTPUT / "sprite.bin").write_bytes(bytes((255, 255, 0)) * 16 + bytes(16))
    x = [40 + 5 * sample for sample in range(51)]
    y = [132 + round(52 * math.sin(sample * math.tau / 48)) for sample in range(51)]
    (OUTPUT / "path-x-low.bin").write_bytes(bytes(value & 255 for value in x))
    (OUTPUT / "path-x-high.bin").write_bytes(bytes(value >> 8 for value in x))
    (OUTPUT / "path-y.bin").write_bytes(bytes(y))
    commands = bytearray()
    for quadrant in range(4):
        for step in range(12):
            first, end = (0, 12) if quadrant in (0, 2) else (12, 25)
            left_to_right = quadrant in (0, 3)
            first_column = 20 + 2 * step if left_to_right else 19 - 2 * step
            second_column = first_column + (1 if left_to_right else -1)
            commands.extend((first, end, first_column if step < 10 else 255,
                             second_column if step < 10 else 255))
    (OUTPUT / "wipe.bin").write_bytes(commands)


if __name__ == "__main__":
    main()
