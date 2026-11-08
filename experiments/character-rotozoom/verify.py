#!/usr/bin/env python3
"""Check the declared affine/glyph contract against bounded native PAL output."""

import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import socket
import subprocess

from PIL import Image, ImageChops


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT = HERE / "build/verification"


def texture_bit(index):
    x, y = index % 16, index // 16
    return int(x == 0 or y == 0 or (x < 8 and y < 8 and x == y)
               or (x - 11) ** 2 + (y - 11) ** 2 < 9)


def reference(phase):
    """Direct integer coordinates; no code replay or native output is an input."""
    angle = phase * math.tau / 32
    scale = 12 + 4 * math.sin(2 * angle)
    c = math.floor(scale * math.cos(angle) + 0.5)
    e = math.floor(scale * math.sin(angle) + 0.5)
    a, b = -e, c
    offsets = [(((c * x + a * y) // 16) % 16)
               | ((((e * x + b * y) // 16) % 16) << 4)
               for y in range(4) for x in range(4)]
    glyphs = bytearray()
    for origin in range(256):
        for y in range(4):
            row = sum(texture_bit((origin + offsets[y * 4 + x]) % 256)
                      * (0xC0 >> (2 * x)) for x in range(4))
            glyphs.extend((row, row))
    matrix = bytearray()
    for y in range(25):
        for x in range(40):
            u = 4 * c * (x - 19) + 4 * a * (y - 12) + 3 * phase
            v = 4 * e * (x - 19) + 4 * b * (y - 12) + 5 * phase
            matrix.append(((u // 16) % 16) | (((v // 16) % 16) << 4))
    pixels = []
    for y in range(200):
        for x in range(320):
            origin = matrix[(y // 8) * 40 + x // 8]
            row = glyphs[origin * 8 + y % 8]
            pixels.append((255, 255, 255) if row & (0x80 >> (x % 8))
                          else (0x27, 0x24, 0xC4))
    canvas = Image.new("RGB", (320, 200))
    canvas.putdata(pixels)
    return glyphs, matrix, canvas, (a, b, c, e)


def assert_bytes(actual, expected, description):
    differences = [index for index, pair in enumerate(zip(actual, expected))
                   if pair[0] != pair[1]]
    if len(actual) != len(expected) or differences:
        raise AssertionError(f"{description}: {len(differences)} mismatches; "
                             f"first offsets {differences[:12]}")


def screen_origin(image, expected):
    for top in range(28, 43):
        for left in range(28, 39):
            crop = image.crop((left, top, left + 320, top + 200))
            if ImageChops.difference(crop, expected).getbbox() is None:
                return left, top
    raise AssertionError("VICE capture does not match any complete expected 320x200 canvas")


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "receipt.json").unlink(missing_ok=True)
    spec = importlib.util.spec_from_file_location("shared_native_monitor", ROOT / "verify.py")
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    labels = shared.read_labels(HERE / "build/main.sym")
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    command = shared.vice_command(os.environ.get("VICE", "x64sc"), HERE / "build/example.prg",
                                  port, ROOT / "palettes/colodore.vpl")
    monitor = None
    with (OUTPUT / "vice.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            with shared.connect_monitor(process, port) as connection:
                monitor = shared.Monitor(connection)
                monitor.run("r")
                monitor.run(f"break {labels['framePresented']:04x}")
                monitor.run("x")
                samples, captures, intervals = [], [], []
                previous_canvas = None
                previous_clock = None
                for index in range(33):
                    if index:
                        monitor.run("x")
                    _, raster, clock = monitor.registers()
                    monitor.run("bank ram")
                    ram = monitor.memory(OUTPUT / f"ram-{index:02d}.bin", 0, 0xFFFF)
                    monitor.run("bank cpu")
                    phase = index % 32
                    assert ram[labels["phaseUsed"]] == phase
                    glyphs, matrix, canvas, gradients = reference(phase)
                    selection = ram[labels["displaySelection"]]
                    font, screen = (0x2800, 0x0C00) if index % 2 == 0 else (0x2000, 0x0400)
                    assert selection == (0x3A if index % 2 == 0 else 0x18)
                    assert_bytes(ram[font:font + 2048], glyphs, f"phase {phase} charset")
                    assert_bytes(ram[screen:screen + 1000], matrix, f"phase {phase} matrix")
                    assert_bytes(ram[labels["texture"]:labels["texture"] + 256],
                                 bytes(texture_bit(i) for i in range(256)), "source texture")
                    record = {"presentation": index + 1, "phase": phase,
                              "gradients_Q4_a_b_c_e": gradients, "raster_line": raster,
                              "clock": clock, "frame_counter": int.from_bytes(
                                  ram[labels["frameCounter"]:labels["frameCounter"] + 2], "little"),
                              "font": font, "screen": screen}
                    if previous_clock is not None:
                        intervals.append(clock - previous_clock)
                    if index in (1, 5, 9, 17, 25, 32):
                        filename = f"phase-{(phase - 1) % 32:02d}.png"
                        monitor.run(f'scrsh "{OUTPUT / filename}" 2')
                        image = Image.open(OUTPUT / filename).convert("RGB")
                        previous_canvas.save(OUTPUT / f"expected-{(phase - 1) % 32:02d}.png")
                        record["captured_previous_phase"] = (phase - 1) % 32
                        record["capture_origin"] = screen_origin(image, previous_canvas)
                        record["screenshot"] = filename
                        captures.append(image)
                    samples.append(record)
                    previous_clock, previous_canvas = clock, canvas
                captures[0].save(OUTPUT / "rotozoom.gif", save_all=True,
                                 append_images=captures[1:], duration=250, loop=0)
                receipt = {"pass": True, "presentations": 33, "distinct_phases": 32,
                           "compared_charset_bytes_per_presentation": 2048,
                           "compared_matrix_bytes_per_presentation": 1000,
                           "pixel_compared_captures": len(captures),
                           "pixels_per_capture": 64000,
                           "selection_intervals_PAL_clocks": intervals,
                           "mean_selection_interval_PAL_clocks": sum(intervals) / len(intervals),
                           "samples": samples, "command": command,
                           "program_sha256": hashlib.sha256((HERE / "build/example.prg").read_bytes()).hexdigest(),
                           "scope": "Independent integer-coordinate/glyph oracle for all 32 moving phases plus wrap; native complete charset/matrix matches and six full VIC canvases. Physical hardware and original-intro equivalence are not claimed."}
                (OUTPUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
                print(json.dumps({key: value for key, value in receipt.items()
                                  if key not in ("samples", "command")}, indent=2))
        finally:
            if monitor:
                (OUTPUT / "monitor.log").write_text("\n".join(monitor.transcript))
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
