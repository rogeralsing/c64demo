#!/usr/bin/env python3
"""Check detached panels, exact native markers, opaque palette priority and scanout."""

import argparse
from datetime import datetime, timezone
from fractions import Fraction
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
CAPTURES = {0, 1, 4, 8, 12, 16, 24, 32, 40, 48, 56, 63, 64, 65}


def geometry(phase):
    """Use a directly expanded rotation matrix, independently of sequential rotations."""
    angle = phase * math.tau / 64
    yaw, pitch, roll = angle + 0.55, 0.32 + 0.2 * math.sin(2 * angle), 0.12 * math.sin(angle)
    cy, sy, cp, sp, cr, sr = (math.cos(yaw), math.sin(yaw), math.cos(pitch),
                             math.sin(pitch), math.cos(roll), math.sin(roll))
    matrix = ((cr * cy - sr * sp * sy, -sr * cp, cr * sy + sr * sp * cy),
              (sr * cy + cr * sp * sy, cr * cp, sr * sy - cr * sp * cy),
              (-cp * sy, sp, cp * cy))
    radius = 38 + 3 * math.sin(angle)
    panels = []
    for axis in range(3):
        other = [coordinate for coordinate in range(3) if coordinate != axis]
        for side in (-1, 1):
            normal = tuple(side * row[axis] for row in matrix)
            points = []
            for first, second in ((-25, -25), (25, -25), (25, 25), (-25, 25)):
                source = [0, 0, 0]
                source[axis], source[other[0]], source[other[1]] = side * radius, first, second
                x, y, z = (sum(a * b for a, b in zip(row, source)) for row in matrix)
                points.append((math.floor(48 + 90 * x / (180 + z) + 0.5),
                               math.floor(64 - 180 * y / (180 + z) + 0.5)))
            panels.append({"points": points, "normal": normal, "radius": radius,
                           "layer": 0 if -180 * normal[2] > radius else 1})
    return panels


def panel_samples(points):
    result = set()
    for x in range(96):
        intersections = []
        for p, q in zip(points, points[1:] + points[:1]):
            if p[0] > q[0]:
                p, q = q, p
            if p[0] <= x < q[0]:
                intersections.append(Fraction(p[1]) + Fraction((x - p[0]) * (q[1] - p[1]), q[0] - p[0]))
        intersections.sort()
        if len(intersections) not in (0, 2):
            raise AssertionError("Independent convex-panel intersections are inconsistent.")
        if intersections:
            first, last = (-(-value.numerator // value.denominator) for value in intersections)
            for y in range(first, last):
                if not 0 <= y < 128:
                    raise AssertionError("A prepared panel escaped the canvas.")
                result.add((x, y))
    return result


def layers_for(panels):
    layers = ({}, {})
    for panel in panels:
        for pixel in panel_samples(panel["points"]):
            layer = layers[panel["layer"]]
            if pixel in layer:
                raise AssertionError("Same-layer panel coverage overlaps and would XOR-cancel.")
            layer[pixel] = panel
    overlap = layers[0].keys() & layers[1].keys()
    minimum_depth_gap = float("inf")
    for x, y in overlap:
        ray = (2 * x - 96, 64 - y, 180)
        distances = []
        for layer in layers:
            panel = layer[(x, y)]
            normal = panel["normal"]
            distances.append((panel["radius"] + 180 * normal[2])
                             / sum(a * b for a, b in zip(normal, ray)))
        if not 0 < distances[0] < distances[1]:
            raise AssertionError("A-over-B priority is not justified by ray/plane depth.")
        minimum_depth_gap = min(minimum_depth_gap, distances[1] - distances[0])
    counts = {"a_only": len(layers[0].keys() - layers[1].keys()),
              "b_only": len(layers[1].keys() - layers[0].keys()), "overlap": len(overlap),
              "same_layer_overlaps": 0, "minimum_ray_depth_gap": minimum_depth_gap}
    if not all(counts[name] > 0 for name in ("a_only", "b_only", "overlap")):
        raise AssertionError("Each pose must visibly exercise both layers and their overlap.")
    return layers, counts


def reference(panels, palette):
    layers, counts = layers_for(panels)
    codes = [[(int((x, y) in layers[0]) ^ (3 * int((x, y) in layers[1])))
              for x in range(96)] for y in range(128)]
    markers = bytearray(3072)
    bitmap = bytearray(8000)
    image = Image.new("RGB", (320, 200), palette[0])
    pixels = image.load()
    for column in range(24):
        previous = 0
        for row in range(128):
            packed = sum(codes[row][column * 4 + lane] << (6 - 2 * lane) for lane in range(4))
            markers[column * 128 + row] = packed ^ previous
            previous = packed
            global_y = row + 36
            address = (global_y // 8) * 320 + (column + 8) * 8 + global_y % 8
            bitmap[address] = packed
            for lane in range(4):
                x = column * 4 + lane
                a, b = (x, row) in layers[0], (x, row) in layers[1]
                # Independent opaque selection, without XOR or painter submission order.
                color_a = 3 if (x + 32) // 4 < 20 else 7
                color_b = 4 if global_y // 8 < 12 else 14
                color = color_a if a else color_b if b else 0
                for px in (64 + 2 * x, 65 + 2 * x):
                    pixels[px, global_y] = palette[color]
    return bytes(markers), bytes(bitmap), image, counts


def prepared_bytes():
    result = bytearray()
    for phase in range(64):
        for panel in geometry(phase):
            result.append(1 if panel["layer"] == 0 else 3)
            result.extend(coordinate for point in panel["points"] for coordinate in point)
    return bytes(result)


def crop_native(image, expected):
    for x, y in [(32, 35)] + [(x, y) for y in range(30, 41) for x in range(28, 37)
                             if (x, y) != (32, 35)]:
        crop = image.crop((x, y, x + 320, y + 200))
        if ImageChops.difference(crop, expected).getbbox() is None:
            return crop, [x, y]
    raise AssertionError("Native VIC image differs from independent opaque A-over-B geometry.")


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
    expected_commands = prepared_bytes()
    if (HERE / "build/commands.bin").read_bytes() != expected_commands:
        raise AssertionError("Prepared projected commands differ from the independent matrix model.")
    all_geometry = [layers_for(geometry(phase))[1] for phase in range(64)]
    (output / "geometry-audit.json").write_text(json.dumps(all_geometry, indent=2) + "\n")
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    expected_screen = bytes(0x33 if cell % 40 < 20 else 0x77 for cell in range(1000))
    expected_colors = bytes(4 if cell // 40 < 12 else 14 for cell in range(1000))
    report = {"pass": False, "program_sha256": hashlib.sha256(program.read_bytes()).hexdigest(),
              "edge_include_sha256": hashlib.sha256((HERE.parent / "lib/polygon-edges.asm").read_bytes()).hexdigest(),
              "prepared_command_bytes": 3456, "geometry_poses_audited": 64,
              "geometry_contract": "six parallel outward-translated cube faces on a common convex supporting box",
              "palette_priority": "deltaA1/deltaB3; selectors01/10 alias A; actual overlap selector10",
              "samples": []}
    process = monitor = None
    clocks, captures, capture_clocks, shown_buffers = [], [], [], set()
    try:
        with (output / "vice.log").open("w") as log:
            process = subprocess.Popen(common.vice_command(args.vice, program, port, palette_path),
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            with common.connect_monitor(process, port) as connection:
                monitor = common.Monitor(connection)
                monitor.run("r")
                monitor.run("sidefx off")
                monitor.run(f"break {labels['markersReady']:04x}")
                monitor.run(f"break {labels['framePresented']:04x}")
                for index in range(args.frames):
                    phase = index % 64
                    expected_markers, expected_bitmap, expected_image, counts = reference(geometry(phase), palette)
                    monitor.run("x")
                    pc, _, _ = monitor.registers()
                    if pc != labels["markersReady"]:
                        raise AssertionError("Native renderer did not reach its complete marker boundary.")
                    monitor.run("bank ram")
                    ram = monitor.memory(output / f"markers-{index:03d}.ram", 0, 0xffff)
                    if ram[labels["pose"]] != phase or ram[labels["markerOverflow"]] != 0:
                        raise AssertionError("Native pose progression or clipping differs.")
                    if ram[0x8000:0x8d80] != expected_commands:
                        raise AssertionError("Native prepared panel commands changed.")
                    if ram[0x4000:0x4c00] != expected_markers:
                        differing = sum(a != b for a, b in zip(ram[0x4000:0x4c00], expected_markers))
                        raise AssertionError(f"Exact native edge markers differ in {differing} packed bytes.")
                    monitor.run("bank cpu")
                    monitor.run("x")
                    pc, raster, clock = monitor.registers()
                    if pc != labels["framePresented"] or not 256 <= raster <= 260:
                        raise AssertionError("Native presentation did not follow a complete scanout.")
                    monitor.run("bank ram")
                    ram = monitor.memory(output / f"presented-{index:03d}.ram", 0, 0xffff)
                    bitmap = 0x6000 if index % 2 == 0 else 0x2000
                    if ram[labels["drawBitmapHi"]] << 8 != bitmap:
                        raise AssertionError("Completed bitmap buffers did not alternate.")
                    if ram[bitmap:bitmap + 8000] != expected_bitmap:
                        raise AssertionError("Full native bitmap differs from the independent layer coverage selectors.")
                    if ram[0x4000:0x4c00] != bytes(3072):
                        raise AssertionError("Prefix consumption did not reset all marker bytes.")
                    if ram[0x0400:0x07e8] != expected_screen or ram[0x5c00:0x5fe8] != expected_screen:
                        raise AssertionError("Screen nibbles lost their per-cell aliasing or local A colors.")
                    monitor.run("bank io")
                    vic = monitor.memory(output / f"vic-{index:03d}.bin", 0xd000, 0xd03f)
                    cia = monitor.memory(output / f"cia-{index:03d}.bin", 0xdd00, 0xdd03)
                    colors = monitor.memory(output / f"colors-{index:03d}.bin", 0xd800, 0xdbe7)
                    if bytes(value & 15 for value in colors) != expected_colors:
                        raise AssertionError("Local B colors in Color RAM differ.")
                    if vic[0x11] & 0x7f != 0x3b or vic[0x16] & 0x3f != 0x18:
                        raise AssertionError("VIC left multicolor bitmap mode.")
                    if vic[0x18] & 0xfe != (0x78 if index % 2 == 0 else 0x18) or cia[0] & 3 != (2 if index % 2 == 0 else 3):
                        raise AssertionError("VIC bank/screen/bitmap selection differs from the completed buffer.")
                    if cia[2] & 3 != 3 or vic[0x15] or vic[0x20] & 15 or vic[0x21] & 15:
                        raise AssertionError("Unexpected sprites, border/background or bank direction registers.")
                    monitor.run("bank cpu")
                    sample = {"pose": phase, "clock": clock, "raster": raster,
                              "bitmap": f"${bitmap:04x}", "coverage": counts,
                              "marker_bytes_checked": 3072, "bitmap_bytes_checked": 8000,
                              "bitmap_sha256": hashlib.sha256(expected_bitmap).hexdigest()}
                    if index in CAPTURES or index == args.frames - 1:
                        path = output / f"native-{index:03d}.png"
                        monitor.run(f'screenshot "{path}" 2')
                        crop, origin = crop_native(Image.open(path).convert("RGB"), expected_image)
                        crop.save(output / f"native-crop-{index:03d}.png")
                        expected_image.save(output / f"expected-{index:03d}.png")
                        captures.append(crop.resize((640, 400), Image.Resampling.NEAREST))
                        capture_clocks.append(clock)
                        sample.update({"screenshot": path.name, "native_pixels_checked": 64000, "origin": origin})
                    report["samples"].append(sample)
                    clocks.append(clock)
                    shown_buffers.add(bitmap)
                    if index % 8 == 0:
                        print(f"Verified native open panels {index + 1}/{args.frames}, overlap {counts['overlap']}", flush=True)
        if shown_buffers != {0x2000, 0x6000}:
            raise AssertionError("Both physical bitmap buffers must be checked.")
        intervals = [b - a for a, b in zip(clocks, clocks[1:])]
        field_counts = [round(value / 19656) for value in intervals]
        if any(abs(value - fields * 19656) > 63 for value, fields in zip(intervals, field_counts)):
            raise AssertionError("Bitmap publications are not separated by complete PAL fields.")
        durations = [max(20, round((b - a) / 19656 * 20)) for a, b in zip(capture_clocks, capture_clocks[1:])] + [200]
        captures[0].save(output / "animation.gif", save_all=True, append_images=captures[1:],
                         duration=durations, loop=0, optimize=False, disposal=2)
        report.update({"pass": True, "native_poses_checked": args.frames,
                       "marker_bytes_checked": args.frames * 3072, "bitmap_bytes_checked": args.frames * 8000,
                       "native_screenshots": len(captures), "native_pixels_checked": len(captures) * 64000,
                       "interval_clocks": [min(intervals), max(intervals)],
                       "pal_fields_per_pose": sorted(set(field_counts)), "animation": "animation.gif",
                       "limits": ["bounded two-layer supporting-box geometry, not arbitrary intersecting cards",
                                  "prepared 3D projection; C64 runtime exact edge rasterization and XOR-prefix fill",
                                  "bounded PAL VICE proof, not physical hardware timing"]})
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
    parser.add_argument("--frames", type=int, default=66, help="Native poses to check (2–66; 66 includes wraparound).")
    parser.add_argument("--vice", default=shutil.which("x64sc") or "x64sc")
    args = parser.parse_args()
    if not 2 <= args.frames <= 66:
        parser.error("--frames must be between 2 and 66.")
    verify(args)


if __name__ == "__main__":
    main()
