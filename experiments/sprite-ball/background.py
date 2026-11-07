#!/usr/bin/env python3
"""Preserve the Art Studio image while reversing its foreground/background roles."""

from pathlib import Path


def prepare(output):
    source = (Path(__file__).resolve().parent / "assets" / "ball-hexagon.art").read_bytes()
    if len(source) != 9009 or source[:2] != b"\x00\x20":
        raise ValueError("Expected a 9009-byte Art Studio hires image")
    bitmap, screen = source[2:8002], source[8002:9002]
    # A hires 1 bit selects the foreground nibble and hides a behind-graphics
    # sprite. Inverting both selectors preserves every original image pixel.
    (output / "ball-bitmap.bin").write_bytes(bytes(value ^ 255 for value in bitmap))
    (output / "ball-screen.bin").write_bytes(bytes((value << 4 | value >> 4) & 255 for value in screen))


if __name__ == "__main__":
    prepare(Path(__file__).resolve().parent / "build")
