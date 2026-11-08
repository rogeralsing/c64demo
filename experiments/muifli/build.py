#!/usr/bin/env python3
"""Own mathematical MUIFLI art and serializer, with unchanged Mufflon viewer.

Layout port based on Mufflon1.0 convert_muifli(), not its image fitting code.
Original viewer/format authors and complete permission notice: SOURCE.json
and MUFFLON-LICENSE.txt. This Python port and artwork are new project code.
"""
import hashlib
import json
import math
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "build"


def arrays():
    provenance = json.loads((HERE / "SOURCE.json").read_text())
    for entry in provenance["vendored_files"]:
        data = (HERE / entry["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"], entry["file"]
    header = (HERE / "vendor/mufflon.h").read_text()
    result = {}
    for name in ("muifli_spram", "muifli_scram", "muifli_sprite_pointers",
                 "muifli_displayer_code1", "muifli_displayer_code2", "sprite_conf"):
        body = re.search(r"\b" + name + r"\[[^;]+?=\s*\{(.*?)\};", header, re.S)[1]
        body = re.sub(r"/\*.*?\*/|//[^\n]*", "", body, flags=re.S)
        result[name] = [int(value, 16) for value in re.findall(r"0x([\da-f]+)", body, re.I)]
    for name, digest in provenance["player_arrays"].items():
        assert len(result[name]) == 768 and hashlib.sha256(bytes(result[name])).hexdigest() == digest
    mixes = re.search(r"\bcolor_mixes\[\]\[3\]\s*=\s*\{(.*?)\};", header, re.S)[1]
    mixes = re.sub(r"/\*.*?\*/|//[^\n]*", "", mixes, flags=re.S)
    allowed = {tuple(sorted((int(a, 16), int(b, 16)))) for a, b in
               re.findall(r"\{\s*0x([\da-f]+),\s*0x([\da-f]+),\s*\d+\s*\}", mixes, re.I)}
    assert all(tuple(sorted(pair)) in allowed for pair in PAIRS)
    return result


# A chosen subset of pairs listed by the author, plus the sixteen physical
# colors paired with themselves. These are field pairs, not extra VIC colors.
PAIRS = ((9, 6), (2, 11), (8, 4), (12, 14), (10, 5), (15, 3), (7, 13),
         (12, 10), (12, 5), (14, 5), (14, 10), (0, 9), (0, 11),
         (9, 2), (9, 11), (6, 11), (6, 2), (2, 8), (2, 4),
         (11, 8), (11, 4), (8, 12), (8, 14), (4, 12), (4, 14),
         (12, 15), (12, 3), (14, 15), (14, 3), (10, 15), (10, 3),
         (5, 15), (5, 3), (15, 7), (15, 13), (3, 7), (3, 13),
         (7, 1), (13, 1)) + tuple((color, color) for color in range(16))


def artwork():
    fields = []
    for field in range(2):
        plan = {"bitmap": bytearray(8000), "attributes": bytearray(4000),
                "sprites": bytearray(3600), "colors": bytearray(606)}
        for row in range(101):
            for sprite in range(6):
                group = 7 if sprite == 0 and 61 <= row <= 71 else row // 8
                pair = PAIRS[(7 * sprite + 3 * group + 5) % len(PAIRS)]
                plan["colors"][row * 6 + sprite] = pair[field]
        for row in range(100):
            for column in range(40):
                ink = PAIRS[(3 * column + row // 3) % len(PAIRS)][field]
                paper = PAIRS[(column // 3 + 2 * (row // 7) + 19) % len(PAIRS)][field]
                if column < 3 or column >= 39:
                    ink = paper = 0
                if column < 3:
                    ink = 15
                if row >= 88 and 3 <= column < 39:
                    ink, paper = ((1, 0) if field == 0 else (0, 1))
                plan["attributes"][row * 40 + column] = ink * 16 + paper
        for y in range(200):
            for x in range(24):
                if (x // 3 + y // 4) % 5 == 0:
                    plan["bitmap"][(y // 8) * 320 + (x // 8) * 8 + y % 8] |= 128 >> (x % 8)
            for x in range(24, 312):
                dx, dy = x - 168, 2 * y - 176
                contour = ((dx * dx + dy * dy) // 192 + x // 5 + y // 7) % 17
                ink = contour < 6
                if y >= 176:
                    ink = bool(((x // 2 + y // 2) & 1) ^ field)
                if ink:
                    plan["bitmap"][(y // 8) * 320 + (x // 8) * 8 + y % 8] |= 128 >> (x % 8)
            for x in range(24, 312, 2):
                paired_y = 2 * ((y + 1) // 2)
                exposed = y < 176 and ((x // 10 + paired_y // 6) % 5 < 2 or
                                      ((x - 168) ** 2 + (2 * paired_y - 176) ** 2) // 256 % 7 == 0)
                if exposed:
                    bit = (x - 24) // 2
                    plan["sprites"][y * 18 + bit // 8] |= 128 >> (bit % 8)
        fields.append(plan)
    assert fields[0]["bitmap"] != fields[1]["bitmap"]
    return fields


def serialize(fields, table):
    result = bytearray(0x10000)
    pointer_offsets = (0x02F8, 0x06F8, 0x0AF8, 0x0EF8, 0x22F8, 0x26F8,
                       0x2AF8, 0x2EF8, 0x32F8, 0x36F8, 0x3AF8, 0x3EF8)
    color_offsets = (0x0300, 0x0380, 0x0700, 0x0780, 0x0B00, 0x0B80)
    for field, plan in enumerate(fields):
        base = field * 0x8000
        for index, offset in enumerate(pointer_offsets):
            result[base + offset:base + offset + 8] = bytes(table["muifli_sprite_pointers"][index * 8:index * 8 + 8])
        for offset in (0x5500, 0x1E40):
            result[base + offset:base + offset + 64] = b"\xff" * 64
        for row in range(101):
            for sprite, offset in enumerate(color_offsets):
                result[base + offset + row] = plan["colors"][row * 6 + sprite]
        result[base + 0x3F00:base + 0x5300] = plan["bitmap"][:0x1400]
        result[base + 0x1300:base + 0x1E40] = plan["bitmap"][0x1400:]
        for row, address in enumerate(table["muifli_scram"]):
            result[base + address:base + address + 40] = plan["attributes"][row * 40:row * 40 + 40]
        sprite_row = 5
        for y in range(200):
            for column in range(18):
                within = (sprite_row + column % 3) & 63
                address = (0x5300 + (((y // 2) & 7) ^ 7) * 64 + within if column >= 15 and y < 128
                           else table["muifli_spram"][y // 2] + within + (column // 3) * 64)
                result[base + address] = plan["sprites"][y * 18 + column]
            if y % 2 == 0:
                sprite_row += 3
            if sprite_row > 63:
                sprite_row &= 63
            elif sprite_row == 63:
                sprite_row = 0
        result[base + 0x1EF8:base + 0x1F00] = bytes(table["sprite_conf"])
        # Seven handoffs replace redundant first-slot colors with Y=$D4.
        # Color entries61..71 are equal, including each replaced phase+1.
        result[base + 0x2EE0:base + 0x2EE8] = bytes(range(62, 70))
        result[base + 0x2EE8:base + 0x2EF0] = bytes([6] * 8)
    result[0x7FFF] = 15
    result[0x0F00:0x1200] = bytes(table["muifli_displayer_code1"])
    result[0x8F00:0x9200] = bytes(table["muifli_displayer_code2"])
    # Pack the high picture tail below I/O. Unchanged startup restores it with
    # CPU port$34, where RAM is accessible beneath the I/O and ROM ranges.
    result[0x5600:0x8000] = result[0xAC00:0xD600]
    return b"\x00\x21" + bytes(result[:0xAC00])


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    table = arrays()
    fields = artwork()
    mui = serialize(fields, table)
    program = bytearray(2 + 0xCD00 - 0x0801)
    program[:16] = bytes((1, 8, 0x0D, 8, 10, 0, 0x9E, 0x20, 0x31, 0x32, 0x32, 0x38, 0x38, 0, 0, 0))
    program[2 + 0x2100 - 0x0801:] = mui[2:]
    (OUTPUT / "example.mui").write_bytes(mui)
    (OUTPUT / "example.prg").write_bytes(program)
    for field, plan in enumerate(fields):
        for name, data in plan.items():
            (OUTPUT / f"field-{field}-{name}.bin").write_bytes(data)
    report = {"title": "Chromatic orbital lattice", "fields": 2, "width": 320, "height": 200,
              "picture_window": [24, 0, 312, 200], "static_image": True,
              "program_bytes": len(program), "mui_bytes": len(mui),
              "program_sha256": hashlib.sha256(program).hexdigest(),
              "mui_sha256": hashlib.sha256(mui).hexdigest(),
              "player_unchanged": True,
              "note": "Two C64 physical-color fields; temporal previews do not add VIC palette entries. No source fitting or runtime image-synthesis claim."}
    (OUTPUT / "artwork.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
