#!/usr/bin/env python3
"""Prepare original panorama strips, then package their real files on a D64."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess

from PIL import Image


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BUILD = HERE / "build"
INK = (6, 4, 2, 8, 5, 3, 14, 4)
PAPER = (14, 10, 8, 7, 13, 1, 1, 10)


def selector(x, y):
    ridge = math.floor(96 + 28 * math.sin(x * math.tau / 180)
                       + 15 * math.sin(x * math.tau / 61) + 0.5)
    if y < ridge - 14:
        return 3 if y < 80 and (17 * x + 29 * y) % 257 == 0 else 0
    if y < ridge:
        return 2 if y % 4 < 2 else 1
    return 1 + (x // 6 + y // 5) % 3


def attributes(tile_x, tile_y):
    index = (tile_x // 8 + tile_y // 3) % 8
    return INK[index] * 16 + PAPER[index], 1


def window(physical_x, columns):
    bitmap, screen, colors = bytearray(), bytearray(), bytearray()
    for tile_y in range(25):
        for column in range(columns):
            tile_x = physical_x // 8 + column
            for row in range(8):
                value = 0
                for pixel in range(4):
                    value = value * 4 + selector(tile_x * 4 + pixel, tile_y * 8 + row)
                bitmap.append(value)
            ink, color = attributes(tile_x, tile_y)
            screen.append(ink)
            colors.append(color)
    return bytes(bitmap + screen + colors)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def prepare():
    BUILD.mkdir(parents=True, exist_ok=True)
    initial = window(0, 40)
    (BUILD / "initial.bin").write_bytes(initial)
    entries = []
    for strip in range(20):
        payload = window(320 + strip * 64, 8)
        if len(payload) != 2000:
            raise ValueError("A stream strip must contain exactly 2,000 payload bytes.")
        filename = f"strip-{strip:02d}.prg"
        program = b"\x00\x80" + payload
        (BUILD / filename).write_bytes(program)
        entries.append({"id": strip, "disk_name": f"{strip:02d}", "file": filename,
                        "source_x": 320 + strip * 64, "bytes": len(payload),
                        "payload_sha256": digest(payload), "prg_sha256": digest(program)})
    palette = [tuple(int(value, 16) for value in row.split()[:3])
               for row in (ROOT / "palettes/colodore.vpl").read_text().splitlines()
               if row.strip() and not row.lstrip().startswith("#")]
    image = Image.new("RGB", (1600, 200))
    pixels = []
    for y in range(200):
        for x in range(800):
            packed, color = attributes(x // 4, y // 8)
            index = (0, packed >> 4, packed & 15, color)[selector(x, y)]
            pixels.extend([palette[index], palette[index]])
    image.putdata(pixels)
    image.save(BUILD / "panorama.png")
    manifest = {"width": 1600, "height": 200, "initial_viewport_width": 320,
                "strip_width": 64, "strip_count": 20,
                "strip_components": {"bitmap": 1600, "screen": 200, "color_ram": 200},
                "resident_slots": ["$8000", "$8800", "$9000", "$9800"],
                "slot_bytes": 2048, "initial_bytes": len(initial),
                "initial_sha256": digest(initial), "strips": entries}
    (BUILD / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def disk():
    executable = shutil.which("c1541")
    if not executable:
        raise RuntimeError("VICE c1541 is required to create the D64.")
    image = BUILD / "example.d64"
    command = [executable, "-format", "stream strips,01", "d64", str(image),
               "-write", str(BUILD / "example.prg"), "stream"]
    for strip in range(20):
        command.extend(["-write", str(BUILD / f"strip-{strip:02d}.prg"), f"{strip:02d}"])
    result = subprocess.run(command, cwd=HERE, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, check=True)
    (BUILD / "c1541.log").write_text(result.stdout)
    if not image.is_file() or image.stat().st_size != 174848:
        raise RuntimeError("c1541 did not create a complete standard D64 image.")
    manifest_path = BUILD / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["disk_sha256"] = digest(image.read_bytes())
    manifest["program_sha256"] = digest((BUILD / "example.prg").read_bytes())
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Created {image}: boot program plus twenty 2,000-byte strip files.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=("prepare", "disk"))
    args = parser.parse_args()
    {"prepare": prepare, "disk": disk}[args.step]()


if __name__ == "__main__":
    main()
