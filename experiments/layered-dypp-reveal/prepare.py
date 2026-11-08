#!/usr/bin/env python3
"""Prepare original source strips and reusable byte expansion, never poses."""
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'build'


def raw_bitmap(pixels):
    return bytes(sum(128 >> bit for bit in range(8) if row[x + bit])
                 for row in pixels for x in range(0, 256, 8))


def windows(pixels):
    # Every byte contains two adjacent four-pixel columns. Runtime phase 0..3
    # chooses any four-pixel window, including the next column at a fine wrap.
    return bytes(sum(128 >> bit for bit in range(8) if row[(column * 4 + bit) & 255])
                 for column in range(64) for row in pixels)


def expansion(plane):
    return bytes(sum(plane << (6 - lane * 2) for lane in range(4)
                     if value & (128 >> (phase + lane)))
                 for phase in range(4) for value in range(256))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('shared_font', HERE.parent / 'lib/font5x7.py')
    font = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(font)
    message = '  LAYERED DYPP  BYTE REVEAL C64  '.ljust(32)[:32]
    text = [[False] * 256 for _ in range(24)]
    for character, letter in enumerate(message):
        for y, row in enumerate(font.GLYPHS[letter]):
            for x in range(5):
                if row & (16 >> x):
                    for dy in range(3):
                        text[y * 3 + dy][character * 8 + x + 1] = True

    # Original night-city strip, a ringed planet, stars and a broken floor.
    # Windows cut holes into a silhouette rather than adding another color.
    picture = [[False] * 256 for _ in range(48)]
    for y in range(48):
        for x in range(256):
            building = x // 16
            height = 10 + ((building * 11 + building * building * 3) % 21)
            wall = x % 16 < 13 and 44 - height <= y < 44
            window = 2 <= x % 16 <= 10 and x % 4 in (2, 3) and y % 5 in (1, 2)
            skyline = wall and not window
            dx, dy = x - 178, y - 13
            planet = dx * dx + dy * dy <= 81 and (y + x // 3) % 5 != 0
            ring = 180 <= dx * dx + 9 * (dy - dx / 4) ** 2 <= 245
            star = y < 16 and ((x * 37 + y * 101) % 281 == 17 or (x, y) in ((8, 4), (72, 9), (238, 3)))
            floor = y in (44, 47) or (y == 46 and x % 16 < 5)
            picture[y][x] = skyline or planet or ring or star or floor

    for name, pixels in (('text', text), ('picture', picture)):
        (OUT / f'{name}-raw.bin').write_bytes(raw_bitmap(pixels))
        (OUT / f'{name}-windows.bin').write_bytes(windows(pixels))
    (OUT / 'expand-text.bin').write_bytes(expansion(1))
    (OUT / 'expand-picture.bin').write_bytes(expansion(2))
    (OUT / 'sines.bin').write_bytes(bytes(round(amplitude * math.sin(math.tau * phase / 256)) & 255
                                         for amplitude in (18, 12) for phase in range(256)))
    (OUT / 'art.json').write_text(json.dumps(dict(message=message, width=256, text_height=24,
                                                 picture_height=48, source='Original mathematical city and shared own font'), indent=2) + '\n')
    print('Prepared two original 1-bit source strips, 64 overlapping columns each, and reusable expansion/sine tables.')


if __name__ == '__main__':
    main()
