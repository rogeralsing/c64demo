#!/usr/bin/env python3
"""Prepare original 80x50 semigraphic art using the C64 ROM's quadrant blocks."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "build"
# Uppercase/graphics ROM screen codes, quadrants TL, TR, BL, BR in bits 0..3.
BLOCKS = (32, 126, 124, 226, 123, 97, 255, 236, 108, 127, 225, 251, 98, 252, 254, 160)
COLORS = (6, 14, 3, 13, 7, 10, 8, 4)


def render(phase):
    angle = phase * math.tau / 16
    cx, cy = 40 + round(19 * math.cos(angle)), 25 + round(10 * math.sin(angle))
    dx, dy = 40 + round(15 * math.cos(angle + math.pi)), 25 + round(12 * math.sin(2 * angle + 1))
    screen, colors = bytearray([32] * 1024), bytearray(1024)
    for row in range(3, 22):
        for column in range(40):
            mask = 0
            for quadrant in range(4):
                x, y = column * 2 + quadrant % 2, row * 2 + quadrant // 2
                ring = (x - cx) ** 2 + 2 * (y - cy) ** 2
                disc = (x - dx) ** 2 + (y - dy) ** 2
                active = 76 <= ring <= 145 or disc < 65 and (x + y + phase) % 3 != 0
                active |= (x * 17 + y * 29) % 251 == 7
                mask |= int(active) << quadrant
            index = row * 40 + column
            screen[index] = BLOCKS[mask]
            colors[index] = COLORS[(column // 5 + row // 3 + phase) % len(COLORS)]
    def text(row, message, color):
        first = row * 40 + (40 - len(message)) // 2
        for offset, character in enumerate(message):
            screen[first + offset] = ord(character) - 64 if "A" <= character <= "Z" else ord(character)
            colors[first + offset] = color
    text(1, "PREPARED PETSCII", 1)
    text(23, f"16 FRAMES  ROM BLOCKS  {phase:02d}", 15)
    return bytes(screen + colors)


def main():
    spec = importlib.util.spec_from_file_location("petscii_shared_lz", HERE.parent / "prepared-bubbles/prepare.py")
    codec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(codec)
    OUT.mkdir(exist_ok=True)
    frames = [render(phase) for phase in range(16)]
    packed = [codec.compress(frame) for frame in frames]
    (OUT / "frames.raw").write_bytes(b"".join(frames))
    source = ["// Original prepared ROM-character artwork; screen then color shadow.",
              "frameLo: .byte " + ",".join(f"<packed{i}" for i in range(16)),
              "frameHi: .byte " + ",".join(f">packed{i}" for i in range(16))]
    for index, data in enumerate(packed):
        source.append(f"packed{index}: .byte " + ",".join(f"${value:02x}" for value in data))
    source.append("packedEnd:")
    (OUT / "frames.asm").write_text("\n".join(source) + "\n")
    info = {"frames": 16, "raw_bytes": 32768, "packed_bytes": sum(map(len, packed)),
            "packed_sizes": list(map(len, packed)), "raw_sha256": hashlib.sha256(b"".join(frames)).hexdigest(),
            "format": "Oscar64-compatible literal/back-distance byte commands, not standard LZO1X",
            "quadrant_screen_codes": BLOCKS}
    (OUT / "artwork.json").write_text(json.dumps(info, indent=2) + "\n")
    print(f"Prepared 16 own ROM PETSCII frames: 32768 raw, {info['packed_bytes']} packed bytes")


if __name__ == "__main__":
    main()
