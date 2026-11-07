#!/usr/bin/env python3
"""Check geometry bounds, then compare native PAL VICE sprites with polygon coverage."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

from model import HEXAGON_CORNERS, coefficients, model, project

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("cube_verification", ROOT / "verify.py")
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)


def check_bounds(faces, golden):
    # All 65,536 yaw/pitch pairs, including poses not used by the animation.
    matrix = np.asarray([coefficients(yaw, pitch)
                         for yaw in range(256) for pitch in range(256)], dtype=np.int32)
    mul = lambda a, b: ((a + b) ** 2 // 256) - ((a - b) ** 2 // 256)
    counts = np.zeros(65536, dtype=np.int32)
    maximum_width = maximum_height = 0
    maximum_error = 0
    for face in faces:
        p = np.asarray(face["vertices"], dtype=np.int32)
        x = 64 + mul(p[:, 0], matrix[:, 0, None]) + mul(p[:, 2], matrix[:, 1, None])
        y = (64 - mul(p[:, 0], matrix[:, 2, None]) - mul(p[:, 1], matrix[:, 3, None])
             - mul(p[:, 2], matrix[:, 4, None]))
        if "basis" in face:
            original_x, original_y = x, y
            exact = lambda a, b: np.sign(a*b)*((np.abs(a*b)+32)//64)
            x = 64+exact(p[:, 0], matrix[:, 0, None])+exact(p[:, 2], matrix[:, 1, None])
            y = (64-exact(p[:, 0], matrix[:, 2, None])-exact(p[:, 1], matrix[:, 3, None])
                 -exact(p[:, 2], matrix[:, 4, None]))
            maximum_error = max(maximum_error, int(np.max(np.abs(x-original_x))),
                                int(np.max(np.abs(y-original_y))))
        if golden:
            inverse_phi = (5 ** 0.5 - 1) / 2
            for coordinates in (x, y):
                original = coordinates.copy()
                rounded = lambda v: np.sign(v) * np.floor(np.abs(v) * inverse_phi + 0.5).astype(np.int32)
                coordinates[:, 1] = coordinates[:, 0] + rounded(coordinates[:, 2] - coordinates[:, 4])
                coordinates[:, 3] = coordinates[:, 4] + rounded(coordinates[:, 2] - coordinates[:, 0])
                maximum_error = max(maximum_error, int(np.max(np.abs(coordinates-original))))
        n = face["normal"]
        normal_mul = exact if "basis" in face else mul
        z = normal_mul(n[0], matrix[:, 5]) + normal_mul(n[1], matrix[:, 6]) + normal_mul(n[2], matrix[:, 7])
        counts += z < 0
        # Include hidden faces too, for a stronger size bound.
        maximum_width = max(maximum_width, int(np.max(np.ptp(x, axis=1))))
        maximum_height = max(maximum_height, int(np.max(np.ptp(y, axis=1))))
    maximum_visible = int(np.max(counts))
    capacity = 10 if any("basis" in face for face in faces) else 8
    if maximum_width >= 24 or maximum_height >= 21 or maximum_visible > capacity:
        raise AssertionError(f"Sprite capacity exceeded: {maximum_width=}, {maximum_height=}, visible={np.max(counts)}")
    return {"angle_pairs": 65536, "maximum_face_span": [maximum_width, maximum_height],
            "maximum_visible_faces": maximum_visible,
            "maximum_rendered_faces": min(8, maximum_visible),
            "maximum_corner_difference_from_baseline": maximum_error}


def check_edge_curves(ram, labels):
    samples = 0
    for dy in range(-20, 21):
        for dx in range(1, 24):
            offset = (dy+20)*24+dx
            address = ram[labels["hexEdgeLow"]+offset] | ram[labels["hexEdgeHigh"]+offset]<<8
            for n in range(dx):
                assert ram[address+n]-20 == -((-n*dy)//dx), (dx, dy, n)
                samples += 1
    return samples


def polygon_bytes(points):
    """Independent rational intersections; fill spans directly, without XOR."""
    data = bytearray(63)
    for x in range(24):
        crossings = []
        for p, q in zip(points, points[1:] + points[:1]):
            if p[0] > q[0]:
                p, q = q, p
            if p[0] <= x < q[0]:
                dx = q[0] - p[0]
                numerator = (q[1] - p[1]) * (x - p[0])
                crossings.append(p[1] - ((-numerator) // dx))
        if len(crossings) % 2:
            raise AssertionError("Polygon reference has an unpaired intersection")
        crossings.sort()
        for first, last in zip(crossings[::2], crossings[1::2]):
            for y in range(first, last):
                if not 0 <= y < 21:
                    raise AssertionError(f"Polygon left sprite bounds at {(x, y)}")
                data[y * 3 + x // 8] |= 0x80 >> (x & 7)
    return bytes(data)


def render_preview(ram, labels, colors):
    packed = np.frombuffer(ram[0x2000:0x3f40], dtype=np.uint8).reshape(25, 40, 8)
    foreground = np.unpackbits(packed.transpose(0, 2, 1).reshape(200, 40), axis=1).astype(bool)
    attributes = np.frombuffer(ram[0x400:0x7e8], dtype=np.uint8).reshape(25, 40).repeat(8, axis=0).repeat(8, axis=1)
    indices = np.where(foreground, attributes>>4, attributes&15)
    image = Image.fromarray(np.asarray(colors, dtype=np.uint8)[indices])
    pixels = image.load()
    base = ram[labels["shownMetadataBase"]]
    buffer = 0x0c00 + (base // 8) * 512
    count = ram[labels["usedSprites"]]
    for slot in reversed(range(count)):
        x = ram[labels["slotX"] + base + slot] - 24
        y = ram[labels["slotY"] + base + slot] + 1 - 51
        color = colors[ram[labels["slotColor"] + base + slot]]
        data = ram[buffer + slot * 64:buffer + slot * 64 + 63]
        for row in range(21):
            for column in range(24):
                if data[row * 3 + column // 8] & (0x80 >> (column & 7)):
                    for py in (y+2*row, y+2*row+1):
                        for px in (x+2*column, x+2*column+1):
                            if 0<=px<320 and 0<=py<200 and not foreground[py, px]:
                                pixels[px, py] = color
    return image


def check_native(args, faces, geometry):
    build = HERE / "build" / args.variant
    output = build / "verification"
    output.mkdir(parents=True, exist_ok=True)
    labels = common.read_labels(build / "main.sym")
    program = build / "sprite-ball.prg"
    artwork = (HERE / "assets" / "ball-hexagon.art").read_bytes()
    expected_bitmap = bytes(value^255 for value in artwork[2:8002])
    expected_screen = bytes((value<<4 | value>>4)&255 for value in artwork[8002:9002])
    palette_file = ROOT / "palettes" / "colodore.vpl"
    colors = [tuple(int(v, 16) for v in line.split()[:3])
              for line in palette_file.read_text().splitlines()
              if line.strip() and not line.startswith("#")]
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    command = common.vice_command(args.vice, program, port, palette_file)
    frames, samples, transcript = [], [], []
    with (output / "vice.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            with common.connect_monitor(process, port) as connection:
                monitor = common.Monitor(connection)
                monitor.run("r")
                monitor.run("sidefx off")
                monitor.run(f"break {labels['framePresented']:04x}")
                previous_cycles = None
                for index in range(args.frames):
                    monitor.run("x")
                    pc, raster, cycles = monitor.registers()
                    assert pc == labels["framePresented"], f"Unexpected stop: ${pc:04x}"
                    monitor.run("bank ram")
                    ram = monitor.memory(output / "ram.bin", 0, 0xffff)
                    if index == 0:
                        curve_samples = check_edge_curves(ram, labels)
                    assert ram[0x2000:0x3f40] == expected_bitmap, "Artwork bitmap changed"
                    assert ram[0x400:0x7e8] == expected_screen, "Artwork attributes changed"
                    monitor.run("bank io")
                    vic = monitor.memory(output / "vic.bin", 0xd000, 0xd03f)
                    monitor.run("bank cpu")
                    yaw, pitch = ram[labels["angleYaw"]], ram[labels["anglePitch"]]
                    base = ram[labels["shownMetadataBase"]]
                    buffer = 0x0c00 + (base // 8) * 512
                    count = ram[labels["usedSprites"]]
                    assert ram[labels["overflowCount"]] == 0, "Runtime sprite overflow"
                    assert count <= 8
                    assert vic[0x17] == vic[0x1d] == 255 and vic[0x1c] == 0
                    assert vic[0x15] == (1 << count) - 1
                    assert vic[0x10] == 0
                    assert vic[0x1b] == 255 and vic[0x11]&0x60 == 0x20 and vic[0x18]&0xfe == 0x18
                    matrix = coefficients(yaw, pitch)
                    depths = [project(face, matrix)[0] for face in faces]
                    visible_faces = [i for i, depth in enumerate(depths) if depth < 0]
                    # Independent ranked result: preserve the eight strongest
                    # facing depths, resolving equal sizes by the face index.
                    expected_faces = sorted(sorted(visible_faces, key=lambda i: (depths[i], i))[:8])
                    actual_faces = list(ram[labels["slotFace"] + base:labels["slotFace"] + base + count])
                    assert actual_faces == expected_faces, (yaw, pitch, actual_faces, expected_faces)
                    assert count == min(8, len(visible_faces))
                    nonempty = 0
                    for slot in range(8):
                        data = ram[buffer + slot * 64:buffer + slot * 64 + 63]
                        if slot >= count:
                            assert data == bytes(63), "An unused sprite retained old pixels"
                            continue
                        face = actual_faces[slot]
                        _, points = project(faces[face], matrix, golden=args.variant == "golden")
                        min_x, min_y = min(x for x, y in points), min(y for x, y in points)
                        local = [(x - min_x, y - min_y) for x, y in points]
                        size = len(faces[face]["vertices"])
                        if args.variant == "hexagon":
                            ids = ram[labels["hexFaceVertices"]+face*size:labels["hexFaceVertices"]+(face+1)*size]
                            native_points = [(ram[labels["sharedX"]+vertex], ram[labels["sharedY"]+vertex]) for vertex in ids]
                            assert native_points == points, (index, face, native_points, points)
                        else:
                            native_points = [(ram[labels["projectedX"] + face * size + i],
                                              ram[labels["projectedY"] + face * size + i]) for i in range(size)]
                            assert native_points == points, (index, face, native_points, points)
                        expected = polygon_bytes(local)
                        nonempty += bool(any(data))
                        if data != expected:
                            offset = next(i for i, pair in enumerate(zip(data, expected)) if pair[0] != pair[1])
                            raise AssertionError(f"Frame {index}, face {face}, byte {offset}: {data[offset]:02x} != {expected[offset]:02x}")
                        assert vic[slot * 2] == 56 + 2 * min_x
                        assert vic[slot * 2 + 1] == 22 + 2 * min_y
                        assert ram[0x7f8 + slot] == buffer // 64 + slot
                    if previous_cycles is not None:
                        assert abs(cycles - previous_cycles - 39312) < 64, (index, cycles - previous_cycles)
                    previous_cycles = cycles
                    duration = ram[labels["renderCycles"]] | ram[labels["renderCycles"] + 1] << 8
                    samples.append({"yaw": yaw, "pitch": pitch, "sprites": count, "nonempty_sprites": nonempty,
                                    "visible_faces": len(visible_faces), "selected_faces": actual_faces,
                                    "render_cycles": duration, "presentation_cycle": cycles, "raster": raster})
                    frames.append(render_preview(ram, labels, colors))
                    if index == 48:
                        # A VICE screenshot records the actual VIC output, not the host preview.
                        monitor.run(f'screenshot "{output / "native.png"}" 2')
                        screenshot = Image.open(output / "native.png").convert("RGB").crop((32, 35, 352, 235))
                        frames[-2].save(output / "expected-native.png")
                        assert np.array_equal(np.asarray(screenshot), np.asarray(frames[-2])), "Native VIC screenshot differs from verified sprites"
                    if index % 64 == 0:
                        print(f"Verified native frame {index}/{args.frames}", flush=True)
                transcript = monitor.transcript
        finally:
            if "monitor" in locals():
                (output / "monitor.log").write_text("\n".join(monitor.transcript))
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
    frames[0].resize((640, 400), Image.Resampling.NEAREST).save(output / "preview.png")
    frames[0].save(output / "animation.gif", save_all=True, append_images=frames[1:], duration=40, loop=0,
                   optimize=False, disposal=2)
    if args.variant == "hexagon" and len(samples) >= 64:
        assert max(s["nonempty_sprites"] for s in samples) == 8
    (output / "monitor.log").write_text("\n".join(transcript))
    result = {"variant": args.variant, "prg_sha256": hashlib.sha256(program.read_bytes()).hexdigest(), "geometry": geometry,
              "face_selection": "eight_largest_by_facing_depth",
              "background_art_sha256": hashlib.sha256(artwork).hexdigest(),
              "sprite_priority": "behind_graphics", "bitmap_unchanged_across_frames": True,
              "native_frames": len(samples), "native_sprite_bytes_checked": len(samples) * 504,
              "exact_edge_samples": curve_samples,
              "maximum_nonempty_sprites": max(s["nonempty_sprites"] for s in samples),
              "native_screenshot_pixel_differences": 0 if len(samples)>48 else None,
              "pal_ticks_per_presentation": 2, "frames_per_second": 50.124542124542124 / 2,
              "render_cycles_min": min(s["render_cycles"] for s in samples),
              "render_cycles_mean": sum(s["render_cycles"] for s in samples) / len(samples),
              "render_cycles_max": max(s["render_cycles"] for s in samples), "samples": samples}
    (output / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "samples"}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=int, default=256)
    parser.add_argument("--vice", default=shutil.which("x64sc"))
    parser.add_argument("--geometry-only", action="store_true")
    parser.add_argument("--variant", choices=("baseline", "golden", "hexagon"), default="hexagon")
    args = parser.parse_args()
    faces = model("hexagon" if args.variant == "hexagon" else "pentagon")
    geometry = check_bounds(faces, golden=args.variant == "golden")
    print(json.dumps(geometry), flush=True)
    if not args.geometry_only:
        check_native(args, faces, geometry)


if __name__ == "__main__":
    main()
