#!/usr/bin/env python3
"""Compare three live native mask layers with independent integer patterns."""

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import socket
import subprocess
from datetime import datetime, timezone

from PIL import Image


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("cube_verifier", ROOT / "verify.py")
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)


def pattern(layer, x, y):
    x, y = x % 64, y % 64
    if layer == 0:
        return (abs(2 * x - 63) + abs(2 * y - 63)) % 32 < 8
    if layer == 1:
        return max(abs(2 * x - 63), abs(2 * y - 63)) % 16 < 4
    return (x + 3 * y) % 16 < 4


def coordinates(iteration):
    return ((iteration % 64, (2 * iteration) % 64),
            ((17 - iteration) % 64, (11 + iteration) % 64),
            ((9 + 2 * iteration) % 64, (29 - iteration) % 64))


def expected_bitmap(iteration):
    bitmap = bytearray(8000)
    flags = [0] * 8
    layer_samples = [bytearray() for _ in range(3)]
    origins = coordinates(iteration)
    for y in range(96):
        for x in range(128):
            selector, membership = 0, 0
            for layer, (ox, oy) in enumerate(origins):
                ink = pattern(layer, x + ox, y + oy)
                layer_samples[layer].append(int(ink))
                if ink:
                    selector ^= layer + 1
                    membership |= 1 << layer
            flags[membership] += 1
            offset = (y // 4) * 320 + (4 + x // 4) * 8 + (y % 4) * 2
            bits = selector << (6 - 2 * (x % 4))
            bitmap[offset] |= bits
            bitmap[offset + 1] |= bits
    return bytes(bitmap), flags, [hashlib.sha256(data).hexdigest() for data in layer_samples]


def expected_sources():
    result = bytearray()
    for layer in range(3):
        for phase in range(4):
            for y in range(64):
                for column in range(16):
                    value = 0
                    for pixel in range(4):
                        if pattern(layer, column * 4 + pixel + phase, y):
                            value |= (layer + 1) << (6 - pixel * 2)
                    result.append(value)
    return bytes(result)


def image_for(bitmap, palette):
    colors = [palette[index] for index in (0, 3, 4, 1)]
    image = Image.new("RGB", (320, 200))
    image.putdata([colors[(bitmap[(y // 8) * 320 + (x // 8) * 8 + y % 8]
                          >> (6 - 2 * ((x // 2) % 4))) & 3]
                   for y in range(200) for x in range(320)])
    return image


def main():
    output = HERE / "build/verification" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output.mkdir(parents=True)
    program = HERE / "build/example.prg"
    labels = tools.read_labels(HERE / "build/main.sym")
    palette_file = ROOT / "palettes/colodore.vpl"
    palette = [tuple(int(value, 16) for value in line.split()[:3])
               for line in palette_file.read_text().splitlines()
               if line.strip() and not line.lstrip().startswith("#")]
    names = ["iteration", "offsetAX", "offsetAY", "offsetBX", "offsetBY", "offsetCX", "offsetCY",
             "drawBitmapHi", "drawBank"]
    first, last = min(labels[name] for name in names), max(labels[name] for name in names)
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    command = tools.vice_command(shutil.which("x64sc"), program, port, palette_file)
    observations, captures, fields = [], [], []
    membership_totals = [0] * 8
    layer_hashes = [set() for _ in range(3)]
    transcript = None
    origin = None
    with (output / "vice.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            with tools.connect_monitor(process, port) as connection:
                monitor = tools.Monitor(connection)
                transcript = monitor.transcript
                monitor.run("r")
                monitor.run(f"break {labels['displayComplete']:04x}")
                for iteration in range(65):
                    monitor.run("x")
                    pc, raster, clock = monitor.registers()
                    if pc != labels["displayComplete"]:
                        raise AssertionError("Unexpected native stop outside completed scanout")
                    raw = monitor.memory(output / "state.bin", first, last)
                    state = {name: raw[labels[name] - first] for name in names}
                    if state["iteration"] != iteration:
                        raise AssertionError("Iteration skipped or repeated")
                    for layer, (x, y) in zip("ABC", coordinates(iteration)):
                        if (state[f"offset{layer}X"], state[f"offset{layer}Y"]) != (x, y):
                            raise AssertionError(f"Layer {layer} source movement differs")
                    bitmap_base = 0xa000 if iteration % 2 == 0 else 0x2000
                    if state["drawBitmapHi"] * 256 != bitmap_base:
                        raise AssertionError("Front bitmap buffers failed to alternate")
                    actual = monitor.memory(output / "bitmap.bin", bitmap_base, bitmap_base + 7999)
                    expected, counts, hashes = expected_bitmap(iteration)
                    if actual != expected:
                        raise AssertionError(f"Image {iteration}: full native bitmap differs")
                    for combination, count in enumerate(counts):
                        membership_totals[combination] += count
                    for layer, digest in enumerate(hashes):
                        layer_hashes[layer].add(digest)
                    fields.append((clock - raster * 63) // 19656)
                    observations.append({"iteration": iteration, "clock": clock, "raster": raster,
                                         "bitmap": bitmap_base, "layer_membership_counts": counts,
                                         "sha256": hashlib.sha256(actual).hexdigest()})
                    if iteration in (0, 1, 7, 15, 31, 47, 63, 64):
                        path = output / f"image-{iteration:03d}.png"
                        monitor.run(f'scrsh "{path}" 2')
                        capture = Image.open(path).convert("RGB")
                        expected_pixels = list(image_for(expected, palette).get_flattened_data())
                        positions = [(left, top) for top in range(28, 42) for left in range(28, 38)] if origin is None else [origin]
                        candidates = []
                        for left, top in positions:
                            actual_pixels = list(capture.crop((left, top, left + 320, top + 200)).get_flattened_data())
                            candidates.append((sum(a != b for a, b in zip(actual_pixels, expected_pixels)), left, top))
                        mismatch, left, top = min(candidates)
                        if mismatch:
                            raise AssertionError(f"Image {iteration}: {mismatch} native pixel mismatches")
                        origin = (left, top)
                        captures.append({"file": path.name, "iteration": iteration, "mismatched_pixels": 0})
                prepared = monitor.memory(output / "prepared.bin", 0x4000, 0x6fff)
                if prepared != expected_sources():
                    raise AssertionError("Prepared mask bytes differ from independent pattern equations")
                for base in (0x0400, 0x8400):
                    if monitor.memory(output / f"screen-{base:04x}.bin", base, base + 999) != bytes([0x34]) * 1000:
                        raise AssertionError("Native bitmap screen attributes changed")
                colors = monitor.memory(output / "colors.bin", 0xd800, 0xdbe7)
                if any(value & 15 != 1 for value in colors):
                    raise AssertionError("Native Color RAM changed")
                if not all(membership_totals) or any(len(hashes) < 2 for hashes in layer_hashes):
                    raise AssertionError("Not all eight overlaps or all three moving masks were exercised")
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
    intervals = [b - a for a, b in zip(fields, fields[1:])]
    report = {"pass": True, "program_sha256": hashlib.sha256(program.read_bytes()).hexdigest(),
              "images_checked": len(observations), "full_bitmap_bytes_checked": len(observations) * 8000,
              "prepared_bytes_checked": 12288, "native_pixels_checked": len(captures) * 64000,
              "pal_fields_per_image": [min(intervals), max(intervals)],
              "all_eight_membership_counts": membership_totals,
              "distinct_layer_masks": [len(hashes) for hashes in layer_hashes],
              "screenshots": captures, "observations": observations,
              "scope": "Three independently moving masks, all eight membership combinations, full bitmaps over a complete 64-state cycle and wrap, eight complete VIC canvases."}
    (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    images = [Image.open(output / item["file"]).convert("RGB") for item in captures]
    images[0].save(output / "animation.gif", save_all=True, append_images=images[1:], duration=250, loop=0)
    print(json.dumps({key: value for key, value in report.items() if key != "observations"}, indent=2))
    print(f"Receipt: {output / 'verification.json'}")


if __name__ == "__main__":
    main()
