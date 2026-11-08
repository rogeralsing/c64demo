#!/usr/bin/env python3
"""Compare complete native bitmaps and VIC captures with independent ring sampling."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import socket
import subprocess

from PIL import Image, ImageChops


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("cube_verification", ROOT / "verify.py")
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)


def ring(x, y):
    # Integer square root avoids reproducing the assembler's floating arithmetic.
    squared_distance = (2 * (x % 64) - 63) ** 2 + (2 * (y % 64) - 63) ** 2
    return int((math.isqrt(squared_distance) // 2) % 8 < 3)


def prepared_mask(high_bit):
    output = bytearray()
    for phase in range(4):
        for y in range(64):
            for column in range(16):
                output.append(sum(ring(column * 4 + pixel + phase, y)
                                  << (6 - 2 * pixel + high_bit) for pixel in range(4)))
    return bytes(output)


def reference(offsets, palette):
    ax, ay, bx, by = offsets
    bitmap = bytearray(8000)
    image = Image.new("RGB", (320, 200), palette[0])
    pixels = image.load()
    counts = Counter()
    for row in range(96):
        for column in range(32):
            value = 0
            for pixel in range(4):
                x = column * 4 + pixel
                selector = ring(x + ax, row + ay) | (ring(x + bx, row + by) << 1)
                counts[selector] += 1
                value |= selector << (6 - 2 * pixel)
                color = palette[(0, 3, 4, 1)[selector]]
                for physical_y in (2 * row, 2 * row + 1):
                    for physical_x in (32 + 2 * x, 33 + 2 * x):
                        pixels[physical_x, physical_y] = color
            address = (2 * row // 8) * 320 + (column + 4) * 8 + (2 * row % 8)
            bitmap[address] = bitmap[address + 1] = value
    return bytes(bitmap), image, dict(counts)


def native_crop(image, expected):
    candidates = [(32, 35)] + [(left, top) for top in range(30, 41)
                              for left in range(28, 37) if (left, top) != (32, 35)]
    for left, top in candidates:
        crop = image.crop((left, top, left + 320, top + 200))
        if ImageChops.difference(crop, expected).getbbox() is None:
            return crop, [left, top]
    raise AssertionError("Native VIC screenshot differs from the independently sampled 320x200 image.")


def verify(args):
    program = HERE / "build" / "example.prg"
    labels = common.read_labels(HERE / "build" / "main.sym")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output = HERE / "build" / "verification" / stamp
    output.mkdir(parents=True)
    palette_file = ROOT / "palettes" / "colodore.vpl"
    palette = [tuple(int(value, 16) for value in line.split()[:3])
               for line in palette_file.read_text().splitlines()
               if line.strip() and not line.lstrip().startswith("#")]
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    expected_a, expected_b = prepared_mask(0), prepared_mask(1)
    report = {
        "pass": False,
        "program_sha256": hashlib.sha256(program.read_bytes()).hexdigest(),
        "logical_samples": [128, 96],
        "physical_viewport": [256, 192],
        "palette_selectors": [0, 3, 4, 1],
        "source": "original example code and ring mask; no production assets",
        "samples": [],
    }
    captures, durations, bitmaps, displayed_banks = [], [], set(), set()
    process = monitor = None
    try:
        with (output / "vice.log").open("w") as log:
            process = subprocess.Popen(
                common.vice_command(args.vice, program, port, palette_file),
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
            )
            with common.connect_monitor(process, port) as connection:
                monitor = common.Monitor(connection)
                monitor.run("r")
                monitor.run("sidefx off")
                monitor.run(f"break {labels['displayComplete']:04x}")
                previous_cycles = None
                for index in range(args.frames):
                    monitor.run("x")
                    pc, raster, cycles = monitor.registers()
                    if pc != labels["displayComplete"] or not 256 <= raster <= 260:
                        raise AssertionError(f"Unexpected publication stop: PC=${pc:04x}, raster={raster}.")
                    monitor.run("bank ram")
                    ram = monitor.memory(output / f"ram-{index:03d}.bin", 0, 0xffff)
                    if ram[0x4000:0x5000] != expected_a or ram[0x5000:0x6000] != expected_b:
                        raise AssertionError("Prepared source mask bytes differ from integer-distance oracle.")
                    offsets = tuple(ram[labels[name]] for name in ("offsetAX", "offsetAY", "offsetBX", "offsetBY"))
                    expected_offsets = (index % 64, 2 * index % 64, (17 - index) % 64, (11 + index) % 64)
                    if offsets != expected_offsets or ram[labels["iteration"]] != index % 256:
                        raise AssertionError(f"Independent layer motion differs: {offsets} != {expected_offsets}.")
                    bitmap_address = ram[labels["drawBitmapHi"]] << 8
                    expected_address = 0xa000 if index % 2 == 0 else 0x2000
                    if bitmap_address != expected_address:
                        raise AssertionError("Completed bitmap buffers did not alternate.")
                    expected_bitmap, expected_image, counts = reference(offsets, palette)
                    actual = ram[bitmap_address:bitmap_address + 8000]
                    if actual != expected_bitmap:
                        differences = sum(a != b for a, b in zip(actual, expected_bitmap))
                        raise AssertionError(f"Full displayed bitmap differs in {differences} of 8,000 bytes.")
                    if set(counts) != {0, 1, 2, 3}:
                        raise AssertionError("Image does not exercise background, both layers and overlap.")
                    for screen in (0x0400, 0x8400):
                        if ram[screen:screen + 1000] != bytes([0x34]) * 1000:
                            raise AssertionError("A screen color plane changed.")
                    monitor.run("bank io")
                    vic = monitor.memory(output / f"vic-{index:03d}.bin", 0xd000, 0xd03f)
                    colors = monitor.memory(output / f"colors-{index:03d}.bin", 0xd800, 0xdbe7)
                    cia = monitor.memory(output / f"cia-{index:03d}.bin", 0xdd00, 0xdd03)
                    if bytes(value & 15 for value in colors) != bytes([1]) * 1000:
                        raise AssertionError("Overlap color RAM differs from white.")
                    expected_bank = 1 if index % 2 == 0 else 3
                    if cia[0] & 3 != expected_bank or cia[2] & 3 != 3:
                        raise AssertionError("CIA2 did not select the completed bitmap bank.")
                    if vic[0x11] & 0x7f != 0x3b or vic[0x16] & 0x3f != 0x18 or vic[0x18] & 0xfe != 0x18:
                        raise AssertionError("VIC left the expected multicolor bitmap configuration.")
                    if vic[0x15] != 0 or vic[0x20] & 15 or vic[0x21] & 15:
                        raise AssertionError("Sprites or nonblack border/background affect the image.")
                    monitor.run("bank cpu")
                    screenshot = output / f"native-{index:03d}.png"
                    monitor.run(f'screenshot "{screenshot}" 2')
                    crop, origin = native_crop(Image.open(screenshot).convert("RGB"), expected_image)
                    crop.save(output / f"native-crop-{index:03d}.png")
                    expected_image.save(output / f"expected-{index:03d}.png")
                    captures.append(crop.resize((640, 400), Image.Resampling.NEAREST))
                    duration = 200 if previous_cycles is None else round((cycles - previous_cycles) / 19656 * 20)
                    durations.append(duration)
                    digest = hashlib.sha256(actual).hexdigest()
                    bitmaps.add(digest)
                    displayed_banks.add(expected_bank)
                    report["samples"].append({
                        "iteration": index,
                        "offsets": list(offsets),
                        "bitmap": f"${bitmap_address:04x}",
                        "bitmap_bytes_checked": 8000,
                        "bitmap_sha256": digest,
                        "logical_selector_counts": counts,
                        "presentation_clock": cycles,
                        "raster": raster,
                        "native_screenshot": screenshot.name,
                        "native_pixels_checked": 64000,
                        "screen_origin": origin,
                    })
                    previous_cycles = cycles
                    print(f"Verified native bitmap and screenshot {index + 1}/{args.frames}", flush=True)
        if displayed_banks != {1, 3} or len(bitmaps) != args.frames:
            raise AssertionError("Verification must exercise both buffers and changing composed images.")
        captures[0].save(output / "animation.gif", save_all=True, append_images=captures[1:],
                         duration=durations, loop=0, optimize=False, disposal=2)
        report.update({
            "pass": True,
            "native_images": args.frames,
            "prepared_source_bytes_checked": 8192,
            "full_bitmap_bytes_checked": args.frames * 8000,
            "native_pixels_checked": args.frames * 64000,
            "distinct_bitmaps": len(bitmaps),
            "animation": "animation.gif",
            "limits": ["bounded PAL VICE run", "no whole-production or physical-hardware timing claim"],
        })
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        if monitor is not None:
            (output / "monitor.log").write_text("\n".join(monitor.transcript))
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"Verification: {output / 'verification.json'}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=int, default=8, help="Native completed images to check (2–64).")
    parser.add_argument("--vice", default=shutil.which("x64sc") or "x64sc")
    args = parser.parse_args()
    if not 2 <= args.frames <= 64:
        parser.error("--frames must be between 2 and 64.")
    verify(args)


if __name__ == "__main__":
    main()
