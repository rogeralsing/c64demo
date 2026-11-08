#!/usr/bin/env python3
"""Check a complete native motion cycle against independent pixel composition."""

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
monitor_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor_tools)


def expected_bitmap(phase):
    """Compose individual pixels; do not reuse the assembler's AND/OR masks."""
    bob_x = 8 * math.floor(19 + 18 * math.sin(phase * 2 * math.pi / 256) + 0.5)
    bob_y = math.floor(92 + 84 * math.sin(phase * 4 * math.pi / 256) + 0.5)
    result = bytearray(8000)
    for y in range(200):
        for column in range(40):
            source_column = min(column, 39 - column)
            value = (255 if y % 16 == 0 else 128 if source_column == 0
                     else 24 if (y + source_column) % 8 == 0 else 0)
            if column >= 20:
                value = int(f"{value:08b}"[::-1], 2)
            result[(y // 8) * 320 + column * 8 + y % 8] = value
    for y in range(16):
        for x in range(16):
            if (x - 7.5) ** 2 + (y - 7.5) ** 2 > 56.25:
                continue
            px, py = bob_x + x, bob_y + y
            offset = (py // 8) * 320 + (px // 8) * 8 + py % 8
            bit = 128 >> (px % 8)
            if (x + y) % 4:
                result[offset] |= bit
            else:
                result[offset] &= 255 ^ bit
    return bytes(result)


def bitmap_image(bitmap, palette):
    image = Image.new("RGB", (320, 200))
    image.putdata([
        palette[1 if bitmap[(y // 8) * 320 + (x // 8) * 8 + y % 8]
                & (128 >> (x % 8)) else 11]
        for y in range(200) for x in range(320)
    ])
    return image


def main():
    output = HERE / "build/verification"
    output.mkdir(parents=True, exist_ok=True)
    (output / "receipt.json").unlink(missing_ok=True)
    program = HERE / "build/example.prg"
    labels = monitor_tools.read_labels(HERE / "build/main.sym")
    palette_path = ROOT / "palettes/colodore.vpl"
    palette = [tuple(int(value, 16) for value in line.split()[:3])
               for line in palette_path.read_text().splitlines()
               if line.strip() and not line.lstrip().startswith("#")]
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    command = monitor_tools.vice_command(shutil.which("x64sc"), program, port, palette_path)
    frames, captures, clocks, fields = [], [], [], []
    transcript = None
    with (output / "vice.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            with monitor_tools.connect_monitor(process, port) as connection:
                monitor = monitor_tools.Monitor(connection)
                transcript = monitor.transcript
                monitor.run(f"break {labels['presented']:04x}")
                for index in range(258):
                    monitor.run("x")
                    pc, raster, clock = monitor.registers()
                    if pc != labels["presented"]:
                        raise AssertionError(f"Unexpected native stop at ${pc:04x}")
                    phase = monitor.memory(output / "phase.bin", labels["phase"], labels["phase"])[0]
                    if phase != index % 256:
                        raise AssertionError(f"Motion phase {phase}, expected {index % 256}")
                    actual = monitor.memory(output / "bitmap.bin", 0x2000, 0x3f3f)
                    expected = expected_bitmap(phase)
                    if actual != expected:
                        differing = sum(a != b for a, b in zip(actual, expected))
                        raise AssertionError(f"Phase {phase}: {differing} incorrect bitmap bytes")
                    frames.append({"phase": phase, "raster": raster,
                                   "sha256": hashlib.sha256(actual).hexdigest()})
                    clocks.append(clock)
                    fields.append((clock - raster * 63) // 19656)
                    if index in (32, 96, 160, 224):
                        # The monitor stops before the next scanout. The visible
                        # screenshot therefore belongs to the preceding phase.
                        path = output / f"phase-{phase:03d}.png"
                        monitor.run(f'scrsh "{path}" 2')
                        capture = Image.open(path).convert("RGB")
                        expected_image = bitmap_image(expected_bitmap((phase - 1) % 256), palette)
                        expected_pixels = list(expected_image.get_flattened_data())
                        candidates = []
                        for top in range(28, 42):
                            for left in range(28, 38):
                                pixels = list(capture.crop((left, top, left + 320, top + 200)).get_flattened_data())
                                candidates.append((sum(a != b for a, b in zip(pixels, expected_pixels)), left, top))
                        mismatch, left, top = min(candidates)
                        if mismatch:
                            raise AssertionError(f"Phase {phase}: {mismatch} native screenshot pixel mismatches")
                        captures.append({"screenshot": path.name, "displayed_phase": (phase - 1) % 256,
                                         "mismatched_pixels": mismatch, "origin": [left, top]})
                screen = monitor.memory(output / "screen.bin", 0x0400, 0x07e7)
                if screen != bytes([0x1b]) * 1000:
                    raise AssertionError("The native bitmap palette attributes changed")
                intervals = [b - a for a, b in zip(clocks[1:], clocks[2:])]
                # Completion moves within the upper border as mirrored reads
                # change the workload. Count complete PAL fields instead of
                # treating that variable work as a fixed raster boundary.
                if any(b - a != 1 for a, b in zip(fields[1:], fields[2:])):
                    raise AssertionError("Motion does not maintain one PAL frame per update")
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
    report = {"pass": True, "frames_checked": len(frames), "bitmap_bytes_per_frame": 8000,
              "pixel_samples_checked": len(frames) * 64000,
              "program_sha256": hashlib.sha256(program.read_bytes()).hexdigest(),
              "presentation_interval_clocks": [min(intervals), max(intervals)],
              "pal_fields_per_update": 1,
              "screenshots": captures, "frames": frames,
              "scope": "All bitmap bytes over a complete motion period and wraparound; four complete native screen images; independent circular coverage and background restoration."}
    (output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    images = [Image.open(output / row["screenshot"]).convert("RGB") for row in captures]
    images[0].save(output / "preview.gif", save_all=True, append_images=images[1:], duration=500, loop=0)
    print(json.dumps({key: value for key, value in report.items() if key != "frames"}, indent=2))


if __name__ == "__main__":
    main()
