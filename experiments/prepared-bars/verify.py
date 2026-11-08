#!/usr/bin/env python3
"""Check native character bars, prepared paths, separate sprites, and VIC output."""

import argparse
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
SLOPES = (-2, -1, 0, 1, 2)
ANGLE_ORDER = (0, 1, 2, 3, 4, 3, 2, 1)
CAPTURE_UPDATES = {0, 1, 8, 16, 24, 32, 40, 48, 56, 64, 96, 128, 160, 192, 224, 255, 256, 257}


def rounded(value):
    return math.floor(value + 0.5)


def angle_for(phase):
    return ANGLE_ORDER[(phase // 8) % 8]


def base_y(phase, bar):
    return rounded(44 + 26 * bar + 6 * math.sin((phase + bar * 29) * math.tau / 256))


def font_reference(slope):
    font = bytearray(2048)
    for code in range(1, 25):
        local_y = (code - 1) % 8
        origin_y = ((code - 1) // 8 - 1) * 8
        for x in range(8):
            center = local_y + slope * x // 8
            for y in range(center - 2, center + 3):
                if origin_y <= y < origin_y + 8:
                    font[code * 8 + y - origin_y] |= 128 >> x
    return bytes(font)


def beacon_pattern(sprite):
    result = bytearray(64)
    for y in range(21):
        for x in range(24):
            distance = abs(2 * x - 23) + abs(2 * y - 20)
            outline = 15 <= distance <= 19
            center = (abs(2 * x - 23) <= 1 if sprite == 0
                      else y == 10 if sprite == 1 else (x + y) % 6 == 0)
            if outline or center and distance < 15:
                result[y * 3 + x // 8] |= 128 >> (x % 8)
    return bytes(result)


def beacon_position(phase, sprite):
    angle = ((phase + sprite * 85) % 256) * math.tau / 256
    return rounded(172 + 125 * math.cos(angle)), rounded(138 + 78 * math.sin(angle))


def reference(phase, palette):
    """Draw global line pixels directly, then derive the required matrix cells."""
    angle = angle_for(phase)
    slope = SLOPES[angle]
    image = Image.new("RGB", (320, 200), palette[0])
    pixels = image.load()
    cells = [bytearray(8) for _ in range(1000)]
    for bar in range(5):
        origin = base_y(phase, bar)
        for x in range(256):
            center = origin + slope * (x // 8 - 16) + slope * (x % 8) // 8
            px = x + 32
            for py in range(center - 2, center + 3):
                if not 0 <= py < 200:
                    raise AssertionError("Prepared line escaped the screen.")
                cells[(py // 8) * 40 + px // 8][py % 8] |= 128 >> (px % 8)
                pixels[px, py] = palette[3]
    for sprite in reversed(range(3)):
        sx, sy = beacon_position(phase, sprite)
        pattern = beacon_pattern(sprite)
        for y in range(21):
            for x in range(24):
                if pattern[y * 3 + x // 8] & (128 >> (x % 8)):
                    px, py = sx - 24 + x, sy - 50 + y
                    if 0 <= px < 320 and 0 <= py < 200:
                        pixels[px, py] = palette[(7, 1, 10)[sprite]]
    return image, cells


def check_matrix(matrix, font, expected_cells):
    for cell, code in enumerate(matrix):
        expected = bytes(expected_cells[cell])
        if font[code * 8:code * 8 + 8] != expected:
            raise AssertionError(f"Matrix cell {cell} does not reproduce independently drawn line pixels.")
        if not any(expected) and code != 0:
            raise AssertionError(f"An empty matrix cell retained glyph {code} at cell {cell}.")


def crop_native(image, expected):
    origins = [(32, 35)] + [(x, y) for y in range(30, 41) for x in range(28, 37)
                           if (x, y) != (32, 35)]
    for x, y in origins:
        crop = image.crop((x, y, x + 320, y + 200))
        if ImageChops.difference(crop, expected).getbbox() is None:
            return crop, [x, y]
    raise AssertionError("Native screenshot differs from independent bars and beacon composition.")


def check_prepared_data(ram, labels):
    fonts = b"".join(font_reference(slope) for slope in SLOPES)
    if ram[0x4800:0x7000] != fonts:
        raise AssertionError("Five prepared angle fonts differ from independent glyph pixels.")
    beacons = b"".join(beacon_pattern(sprite) for sprite in range(3))
    if ram[0x7000:0x70c0] != beacons:
        raise AssertionError("Prepared sprite artwork differs from independent diamond masks.")
    expected_paths = bytes(base_y(phase, bar) for bar in range(5) for phase in range(256))
    expected_angles = bytes(angle_for(phase) for phase in range(256))
    expected_x = [beacon_position(phase, 0)[0] for phase in range(256)]
    expected_y = bytes(beacon_position(phase, 0)[1] for phase in range(256))
    for name, expected in (
        ("barPaths", expected_paths), ("anglePath", expected_angles),
        ("beaconXLo", bytes(value & 255 for value in expected_x)),
        ("beaconXHi", bytes(value >> 8 for value in expected_x)),
        ("beaconY", expected_y),
    ):
        address = labels[name]
        if ram[address:address + len(expected)] != expected:
            raise AssertionError(f"Prepared path {name} differs from independent coordinates.")


def verify(args):
    labels = common.read_labels(HERE / "build/main.sym")
    program = HERE / "build/example.prg"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output = HERE / "build/verification" / stamp
    output.mkdir(parents=True)
    palette_path = ROOT / "palettes/colodore.vpl"
    palette = [tuple(int(value, 16) for value in line.split()[:3])
               for line in palette_path.read_text().splitlines()
               if line.strip() and not line.lstrip().startswith("#")]
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    report = {"pass": False, "program_sha256": hashlib.sha256(program.read_bytes()).hexdigest(),
              "native_updates": args.updates, "samples": []}
    process = monitor = None
    clocks, angles, buffers, captures, durations = [], set(), set(), [], []
    try:
        with (output / "vice.log").open("w") as log:
            process = subprocess.Popen(
                common.vice_command(args.vice, program, port, palette_path),
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
            )
            with common.connect_monitor(process, port) as connection:
                monitor = common.Monitor(connection)
                monitor.run("r")
                monitor.run("sidefx off")
                monitor.run(f"break {labels['displayComplete']:04x}")
                last_capture_clock = None
                for index in range(args.updates):
                    monitor.run("x")
                    pc, raster, clock = monitor.registers()
                    if pc != labels["displayComplete"] or not 256 <= raster <= 260:
                        raise AssertionError(f"Unexpected completed-scanout stop: ${pc:04x}, raster {raster}.")
                    phase = monitor.memory(output / "phase.bin", labels["phase"], labels["phase"])[0]
                    if phase != index % 256:
                        raise AssertionError(f"Native phase skipped: {phase} != {index % 256}.")
                    clocks.append(clock)
                    if index not in CAPTURE_UPDATES and index != args.updates - 1:
                        continue
                    monitor.run("bank ram")
                    ram = monitor.memory(output / f"ram-{index:03d}.bin", 0, 0xffff)
                    check_prepared_data(ram, labels)
                    current_angle = angle_for(phase)
                    screen = 0x4400 if index % 2 == 0 else 0x4000
                    if ram[labels["drawScreenHi"]] << 8 != screen:
                        raise AssertionError("Completed screen matrices did not alternate.")
                    if ram[labels["currentAngle"]] != current_angle:
                        raise AssertionError("Runtime angle does not follow its prepared path.")
                    expected_image, expected_cells = reference(phase, palette)
                    font_address = 0x4800 + current_angle * 2048
                    font = ram[font_address:font_address + 2048]
                    matrix = ram[screen:screen + 1000]
                    check_matrix(matrix, font, expected_cells)
                    if ram[screen + 0x3f8:screen + 0x3fb] != bytes((0xc0, 0xc1, 0xc2)):
                        raise AssertionError("Visible matrix has wrong beacon sprite pointers.")
                    monitor.run("bank io")
                    vic = monitor.memory(output / f"vic-{index:03d}.bin", 0xd000, 0xd03f)
                    cia = monitor.memory(output / f"cia-{index:03d}.bin", 0xdd00, 0xdd03)
                    colors = monitor.memory(output / f"colors-{index:03d}.bin", 0xd800, 0xdbe7)
                    if bytes(value & 15 for value in colors) != bytes([3]) * 1000:
                        raise AssertionError("Character ink no longer uses cyan.")
                    expected_d018 = (0x10 if screen == 0x4400 else 0) | (current_angle + 1) * 2
                    if vic[0x18] & 0xfe != expected_d018 or vic[0x11] & 0x7f != 0x1b or vic[0x16] & 0x3f != 8:
                        raise AssertionError("VIC screen/font selection differs from the completed matrix.")
                    if cia[0] & 3 != 2 or cia[2] & 3 != 3:
                        raise AssertionError("Display left the ROM-free $4000 VIC bank.")
                    if vic[0x15] != 7 or any(vic[index] for index in (0x17, 0x1b, 0x1c, 0x1d)):
                        raise AssertionError("Beacon enable, priority, expansion or hires mode changed.")
                    expected_msb = 0
                    sprite_positions = []
                    for sprite in range(3):
                        sx, sy = beacon_position(phase, sprite)
                        if vic[sprite * 2] != sx & 255 or vic[sprite * 2 + 1] != sy:
                            raise AssertionError("Hardware beacon position differs from its independent path.")
                        if vic[0x27 + sprite] & 15 != (7, 1, 10)[sprite]:
                            raise AssertionError("Hardware beacon palette changed.")
                        expected_msb |= (sx >> 8) << sprite
                        sprite_positions.append([sx, sy])
                    if vic[0x10] != expected_msb or vic[0x20] & 15 or vic[0x21] & 15:
                        raise AssertionError("Sprite high-X bits or black backdrop differ.")
                    monitor.run("bank cpu")
                    screenshot = output / f"native-{index:03d}.png"
                    monitor.run(f'screenshot "{screenshot}" 2')
                    crop, origin = crop_native(Image.open(screenshot).convert("RGB"), expected_image)
                    crop.save(output / f"native-crop-{index:03d}.png")
                    expected_image.save(output / f"expected-{index:03d}.png")
                    captures.append(crop.resize((640, 400), Image.Resampling.NEAREST))
                    durations.append(160 if last_capture_clock is None else round((clock - last_capture_clock) / 19656 * 20))
                    last_capture_clock = clock
                    angles.add(current_angle)
                    buffers.add(screen)
                    report["samples"].append({"update": index, "phase": phase, "angle": current_angle,
                                              "slope_pixels_per_character": SLOPES[current_angle],
                                              "screen": f"${screen:04x}", "font": f"${font_address:04x}",
                                              "matrix_bytes_checked": 1000, "native_pixels_checked": 64000,
                                              "sprite_positions": sprite_positions, "screenshot": screenshot.name,
                                              "screen_origin": origin})
                    print(f"Verified native prepared-bars phase {phase}, angle {current_angle}", flush=True)
        intervals = [second - first for first, second in zip(clocks, clocks[1:])]
        if buffers != {0x4000, 0x4400}:
            raise AssertionError("Native samples did not cover both screen matrices.")
        if args.updates >= 33 and angles != set(range(5)):
            raise AssertionError("Native samples did not cover all five angle fonts.")
        rounded_fields = [round(interval / 19656) for interval in intervals]
        if any(abs(interval - fields * 19656) > 63 for interval, fields in zip(intervals, rounded_fields)):
            raise AssertionError("Completed images are not separated by whole PAL fields.")
        captures[0].save(output / "animation.gif", save_all=True, append_images=captures[1:],
                         duration=durations, loop=0, optimize=False, disposal=2)
        report.update({"pass": True, "sampled_images": len(captures), "angles_checked": sorted(angles),
                       "prepared_font_bytes_checked": 10240, "prepared_sprite_bytes_checked": 192,
                       "prepared_path_bytes_checked": 2304,
                       "matrix_bytes_checked": len(captures) * 1000,
                       "native_pixels_checked": len(captures) * 64000,
                       "interval_clocks": [min(intervals), max(intervals)],
                       "pal_fields_per_update": sorted(set(rounded_fields)),
                       "animation": "animation.gif",
                       "limits": ["own educational composition, not original production code",
                                  "bounded PAL VICE validation; no physical-hardware claim"]})
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
    parser.add_argument("--updates", type=int, default=258, help="Native completed updates to observe (2–258).")
    parser.add_argument("--vice", default=shutil.which("x64sc") or "x64sc")
    args = parser.parse_args()
    if not 2 <= args.updates <= 258:
        parser.error("--updates must be between 2 and 258.")
    verify(args)


if __name__ == "__main__":
    main()
