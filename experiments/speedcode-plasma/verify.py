#!/usr/bin/env python3
"""Check native generated plasma writers against direct cell/pixel equations."""

import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import socket
import subprocess

from PIL import Image


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("cube_verifier", ROOT / "verify.py")
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)
BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))


def wave(angle):
    return math.floor(7.5 + 7.5 * math.sin((angle % 256) * 2 * math.pi / 256) + 0.5)


def matrix(phase):
    return bytes((wave(phase + 5 * x) + wave(3 * phase + 7 * y)) // 2
                 for y in range(25) for x in range(40))


def image_for(phase, palette):
    cells = matrix(phase)
    image = Image.new("RGB", (320, 200))
    image.putdata([palette[1 if BAYER[y % 4][x % 4] < cells[(y // 8) * 40 + x // 8] else 6]
                   for y in range(200) for x in range(320)])
    return image


def main():
    output = HERE / "build/verification"
    output.mkdir(parents=True, exist_ok=True)
    (output / "receipt.json").unlink(missing_ok=True)
    program = HERE / "build/example.prg"
    labels = tools.read_labels(HERE / "build/main.sym")
    palette_file = ROOT / "palettes/colodore.vpl"
    palette = [tuple(int(value, 16) for value in line.split()[:3])
               for line in palette_file.read_text().splitlines()
               if line.strip() and not line.lstrip().startswith("#")]
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    command = tools.vice_command(shutil.which("x64sc"), program, port, palette_file)
    observations, captures, fields = [], [], []
    transcript = None
    origin = None
    with (output / "vice.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            with tools.connect_monitor(process, port) as connection:
                monitor = tools.Monitor(connection)
                transcript = monitor.transcript
                monitor.run(f"break {labels['framePresented']:04x}")
                for index in range(258):
                    monitor.run("x")
                    pc, raster, clock = monitor.registers()
                    if pc != labels["framePresented"] or raster > 1:
                        raise AssertionError("Matrix publication moved outside the top border")
                    phase = monitor.memory(output / "phase.bin", labels["phaseX"], labels["phaseX"])[0]
                    if phase != index % 256:
                        raise AssertionError("Plasma phase progression skipped or repeated")
                    selected = 1 - index % 2
                    first = 0x4400 if selected else 0x4000
                    actual = monitor.memory(output / "matrix.bin", first, first + 999)
                    if actual != matrix(phase):
                        raise AssertionError(f"Phase {phase}: independently derived screen cells differ")
                    io = monitor.memory(output / "vic.bin", 0xd000, 0xd03f)
                    if io[0x18] & 0xfe != 2 + selected * 16 or io[0x21] & 15 != 6:
                        raise AssertionError("Native matrix/font selection or background changed")
                    fields.append((clock - raster * 63) // 19656)
                    observations.append({"phase": phase, "matrix": first, "clock": clock,
                                         "raster": raster, "sha256": hashlib.sha256(actual).hexdigest()})
                    if index in (1, 65, 129, 193, 257):
                        path = output / f"frame-{index:03d}.png"
                        monitor.run(f'scrsh "{path}" 2')
                        capture = Image.open(path).convert("RGB")
                        expected_pixels = list(image_for((phase - 1) % 256, palette).get_flattened_data())
                        positions = [(left, top) for top in range(28, 42) for left in range(28, 38)] if origin is None else [origin]
                        candidates = []
                        for left, top in positions:
                            actual_pixels = list(capture.crop((left, top, left + 320, top + 200)).get_flattened_data())
                            candidates.append((sum(a != b for a, b in zip(actual_pixels, expected_pixels)), left, top))
                        mismatch, left, top = min(candidates)
                        if mismatch:
                            raise AssertionError(f"Frame {index}: {mismatch} native pixel mismatches")
                        origin = (left, top)
                        captures.append({"file": path.name, "displayed_phase": (phase - 1) % 256,
                                         "mismatched_pixels": 0})
                if any(b - a != 1 for a, b in zip(fields, fields[1:])):
                    raise AssertionError("Generated plasma missed its one-PAL-field update budget")
                expected_font = bytes(sum((128 >> x) for x in range(8) if BAYER[y % 4][x % 4] < level)
                                      for level in range(16) for y in range(8))
                font = monitor.memory(output / "font.bin", 0x4800, 0x487f)
                if font != expected_font:
                    raise AssertionError("Native density glyphs differ from independent thresholds")
                colors = monitor.memory(output / "colors.bin", 0xd800, 0xdbe7)
                if any(color & 15 != 1 for color in colors):
                    raise AssertionError("Native plasma ink colors changed")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            if transcript is not None:
                (output / "monitor.txt").write_text("\n".join(transcript))
    report = {"pass": True, "program_sha256": hashlib.sha256(program.read_bytes()).hexdigest(),
              "frames_checked": len(observations), "matrix_bytes_per_frame": 1000,
              "pal_fields_per_update": 1, "generated_writer_bytes": labels["writersEnd"] - labels["drawMatrixA"],
              "native_pixels_checked": len(captures) * 64000, "origin": origin,
              "screenshots": captures, "observations": observations,
              "scope": "All 256 live phases plus wraparound, complete screen matrices, independent glyph thresholds, and five complete native canvases."}
    (output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    images = [Image.open(output / row["file"]).convert("RGB") for row in captures]
    images[0].save(output / "plasma.gif", save_all=True, append_images=images[1:], duration=350, loop=0)
    print(json.dumps({key: value for key, value in report.items() if key != "observations"}, indent=2))


if __name__ == "__main__":
    main()
