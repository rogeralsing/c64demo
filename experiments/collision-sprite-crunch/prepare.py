#!/usr/bin/env python3
"""Pack new geometric tiles and their per-sprite hardware crunch decisions."""

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
SCHEDULES = (
    (0x35,0x38,0x3b,0x3e,0x15,0x18,0x1b,0x1e,0x21,0x25,0x28,0x2b,0x2e,0x31),
    (0x35,0x38,0x3b,0x3e,0x01,0x05,0x08,0x0b,0x0f,0x17,0x1a,0x1d,0x20,0x23,0x27,0x2a,0x2d),
    (0x35,0x38,0x3b,0x3e,0x01,0x04,0x07,0x0a,0x0d,0x15,0x18,0x1b,0x1e,0x21,0x25,0x28,0x2b,0x2e,0x31),
    (0x35,0x38,0x3b,0x3e,0x01,0x05,0x08,0x0b,0x0e,0x11,0x14,0x17,0x1a,0x1d,0x20,0x23,0x26,0x29,0x2c,0x2f,0x32),
)


def crunch(base):
    candidate = (base + 3) % 64
    return ((base | candidate) & 0x15) | ((base & candidate) & 0x2a)


def artwork(column, row, x, height):
    if row == 0 or x == 23:
        return 0
    rim = (x in (2, 20) and 2 <= row <= height - 2) or (row in (2, height - 2) and 2 <= x <= 20)
    inside = 3 <= x <= 19 and 3 <= row <= height - 3
    return int(rim or inside and (x + row + column * 3) % 7 == 0)


def main():
    output = HERE / "build"
    output.mkdir(exist_ok=True)
    sprites, records = bytearray(), []
    for column in range(8):
        schedule = SCHEDULES[column % 4]
        transitions = []
        for row, base in enumerate(schedule):
            next_base = schedule[(row + 1) % len(schedule)]
            needed = next_base != (base + 3) % 64
            if needed and crunch(base) != next_base:
                raise ValueError("Schedule is not a valid VIC crunch loop.")
            transitions.append(int(needed))
        pattern = bytearray(64)
        used = set()
        for row, base in enumerate(schedule):
            bits = [artwork(column, row, x, len(schedule)) for x in range(24)]
            bits[23] = transitions[(row + 2) % len(schedule)]
            for part in range(3):
                address = (base + part) % 64
                if address in used:
                    raise ValueError("Fetch rows overlap in a sprite data structure.")
                used.add(address)
                pattern[address] = sum(bits[part * 8 + bit] << (7 - bit) for bit in range(8))
        sprites.extend(pattern)
        records.append({"column": column, "height": len(schedule), "offsets": schedule,
                        "crunch_decisions": transitions, "sha256": hashlib.sha256(pattern).hexdigest()})
    bitmap = bytearray(8000)
    for y in range(200):
        for cell in range(40):
            value = 255 if y < 26 or y >= 186 else 1 if cell in (10,13,16,19,22,25,28,31) else 0
            bitmap[(y // 8) * 320 + cell * 8 + y % 8] = value
    (output / "sprites.bin").write_bytes(sprites)
    (output / "background.bin").write_bytes(bitmap)
    (output / "artwork.json").write_text(json.dumps(records, indent=2) + "\n")
    print("Prepared eight original sprite tiles, four crunch-loop heights and hidden collision stripes.")


if __name__ == "__main__":
    main()
