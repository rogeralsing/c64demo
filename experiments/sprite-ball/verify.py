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
    highlights = np.zeros(65536, dtype=np.int32)
    face_depths = []
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
        face_depths.append(z)
        highlights += -z / sum(v*v for v in n)**0.5 >= 0.94
        counts += z < 0
        # Include hidden faces too, for a stronger size bound.
        maximum_width = max(maximum_width, int(np.max(np.ptp(x, axis=1))))
        maximum_height = max(maximum_height, int(np.max(np.ptp(y, axis=1))))
    maximum_visible = int(np.max(counts))
    if any("basis" in face for face in faces):
        for _, neighbors in reference_gap_faces(faces):
            normal = [sum(faces[i]["normal"][axis] for i in neighbors) for axis in range(3)]
            facing = -sum(face_depths[i] for i in neighbors)
            highlights += facing / sum(v*v for v in normal)**0.5 >= 0.94
    assert highlights.max() <= 2, "Three faces lie within the near-front cone"
    capacity = 10 if any("basis" in face for face in faces) else 8
    if maximum_width >= 24 or maximum_height >= 21 or maximum_visible > capacity:
        raise AssertionError(f"Sprite capacity exceeded: {maximum_width=}, {maximum_height=}, visible={np.max(counts)}")
    return {"angle_pairs": 65536, "maximum_face_span": [maximum_width, maximum_height],
            "maximum_visible_faces": maximum_visible,
            "maximum_rendered_faces": min(8, maximum_visible),
            "maximum_nearly_front_faces": int(highlights.max()),
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


def decode_bitmap(bitmap, screen, color_ram, background):
    packed = np.frombuffer(bitmap, dtype=np.uint8).reshape(25, 40, 8)
    rows = packed.transpose(0, 2, 1).reshape(200, 40)
    codes = ((rows[:, :, None] >> np.array([6, 4, 2, 0])) & 3).reshape(200, 160)
    attributes = np.frombuffer(screen, dtype=np.uint8).reshape(25, 40).repeat(8, axis=0).repeat(4, axis=1)
    local = np.frombuffer(color_ram, dtype=np.uint8).reshape(25, 40).repeat(8, axis=0).repeat(4, axis=1) & 15
    indices = np.choose(codes, [np.full_like(local, background), attributes >> 4, attributes & 15, local])
    return indices, codes


def check_scene(artwork, bitmap, screen, color_ram, scene, phase=0):
    calibration = json.loads((HERE / "assets" / "scene-circle-repair.json").read_text())
    assert hashlib.sha256(artwork).hexdigest() == calibration["source_sha256"]
    assert scene["center"] == calibration["center"]
    if scene["format"] == "truepaint_mci":
        assert len(artwork) == 19434 and artwork[:2] == bytes((0, 0x9c))
        bitmap_start = (1026, 9218)[phase]
        screen_start = (2, 17410)[phase]
        assert bitmap == artwork[bitmap_start:bitmap_start+8000], "Source MCI bitmap changed"
        assert screen == artwork[screen_start:screen_start+1000], "Source MCI screen colors changed"
        assert color_ram == bytes(value & 15 for value in artwork[18434:19434]), "Shared MCI Color RAM changed"
        assert scene["background"] == artwork[1002]&15
    else:
        assert bitmap == artwork[2:8002], "Source bitmap changed, including sphere artwork"
        assert screen == artwork[8002:9002], "Source screen colors changed"
        assert color_ram == bytes(value & 15 for value in artwork[9002:10002]), "Source color RAM changed"
        assert scene["background"] == artwork[10002]&15
    assert scene["bitmap_passthrough"] is True




def render_preview(ram, labels, colors, color_ram, background, sprite_colors=None, phase=0, horizontal_shift=0):
    base = ram[labels["shownMetadataBase"]]
    screen = (0x400, 0x7c00)[phase]
    bitmap = (0x2000, 0x4000)[phase]
    indices, _ = decode_bitmap(ram[bitmap:bitmap+8000], ram[screen:screen+1000], color_ram, background)
    indices = indices.repeat(2, axis=1)
    if phase and horizontal_shift:
        indices = np.pad(indices, ((0, 0), (horizontal_shift, 0)), constant_values=background)[:, :320]
    image = Image.fromarray(np.asarray(colors, dtype=np.uint8)[indices])
    pixels = image.load()
    base = ram[labels["shownMetadataBase"]]
    buffer = (0x0c00, 0x7800)[phase] + (base // 8) * 512
    count = ram[labels["usedSprites"]]
    for slot in reversed(range(count)):
        x = ram[labels["slotX"] + base + slot] - 24
        y = ram[labels["slotY"] + base + slot] + 1 - 51
        color_index = ram[labels["slotColor"] + base + slot] if sprite_colors is None else sprite_colors[slot]
        color = colors[color_index]
        data = ram[buffer + slot * 64:buffer + slot * 64 + 63]
        for row in range(21):
            for column in range(24):
                if data[row * 3 + column // 8] & (0x80 >> (column & 7)):
                    for py in (y+2*row, y+2*row+1):
                        for px in (x+2*column, x+2*column+1):
                            if 0<=px<320 and 0<=py<200:
                                pixels[px, py] = color
    return image


def reference_gap_faces(faces):
    # Independently recover each pentagon from its icosahedral vertex normal.
    # The five most outward mesh vertices form that pentagonal face.
    vertices = {p for face in faces for p in face["vertices"]}
    gaps = []
    for pentagon in model("pentagon"):
        normal = pentagon["normal"]
        points = sorted(vertices, key=lambda p: sum(a*b for a,b in zip(p,normal)), reverse=True)[:5]
        neighbors = [i for i,face in enumerate(faces) if len(set(points)&set(face["vertices"]))==2]
        assert len(neighbors)==5
        gaps.append(({"normal":normal,"basis":True,"vertices":points},neighbors))
    return gaps


def expected_front_color(depth):
    """Camera-light bands, using the independently rotated Z normal."""
    strength = -depth-1
    return 6 if strength < 6 else 4 if strength < 12 else 10 if strength < 18 else 15 if strength < 24 else 1


def darker_color(color):
    palette = (6, 4, 10, 15, 1)
    return palette[max(0, palette.index(color)-1)]


def check_native(args, faces, geometry):
    build = HERE / "build" / args.variant
    output = build / "verification"
    output.mkdir(parents=True, exist_ok=True)
    labels = common.read_labels(build / "main.sym")
    program = build / "sprite-ball.prg"
    scene = json.loads((HERE / "build" / "scene.json").read_text())
    artwork = (HERE / scene["source"]).read_bytes()
    expected_bitmap = (HERE / "build" / "ball-bitmap.bin").read_bytes()
    expected_screen = (HERE / "build" / "ball-screen.bin").read_bytes()
    expected_colors = (HERE / "build" / "ball-colors.bin").read_bytes()
    expected_bitmap_b = (HERE / "build" / "ball-bitmap-b.bin").read_bytes()
    expected_screen_b = (HERE / "build" / "ball-screen-b.bin").read_bytes()
    check_scene(artwork, expected_bitmap, expected_screen, expected_colors, scene)
    check_scene(artwork, expected_bitmap_b, expected_screen_b, expected_colors, scene, phase=1)
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
                monitor.run(f"break {labels['frameColorsUpdated']:04x}")
                monitor.run("disable 2")
                previous_cycles = None
                for index in range(args.frames):
                    monitor.run("x")
                    pc, raster, cycles = monitor.registers()
                    assert pc == labels["framePresented"], f"Unexpected stop: ${pc:04x}"
                    monitor.run("bank ram")
                    ram = monitor.memory(output / "ram.bin", 0, 0xffff)
                    if index == 0:
                        curve_samples = check_edge_curves(ram, labels)
                    assert ram[0x2000:0x3f40] == expected_bitmap, "Field A bitmap changed"
                    assert ram[0x4000:0x5f40] == expected_bitmap_b, "Field B bitmap changed"
                    assert ram[0x7c00:0x7fe8] == expected_screen_b, "Field B screen colors changed"
                    monitor.run("bank io")
                    vic = monitor.memory(output / "vic.bin", 0xd000, 0xd03f)
                    color_ram = bytes(value & 15 for value in monitor.memory(output / "colors.bin", 0xd800, 0xdbe7))
                    assert color_ram == expected_colors, "Koala color RAM differs"
                    monitor.run("bank cpu")
                    yaw, pitch = ram[labels["angleYaw"]], ram[labels["anglePitch"]]
                    expected_yaw = (6*index) & 255
                    expected_pitch = (3*index) & 255
                    assert (yaw, pitch) == (expected_yaw, expected_pitch), "Rotation path or phase differs"
                    base = ram[labels["shownMetadataBase"]]
                    screen = 0x400
                    buffer = 0x0c00 + (base // 8) * 512
                    mirror = 0x7800 + (base // 8) * 512
                    assert ram[buffer:buffer+512] == ram[mirror:mirror+512], "VIC banks show different sprite poses"
                    count = ram[labels["usedSprites"]]
                    assert ram[labels["overflowCount"]] == 0, "Runtime sprite overflow"
                    assert ram[labels["missedDeadlines"]] == 0, "Runtime missed a presentation deadline"
                    assert count <= 8
                    assert vic[0x17] == vic[0x1d] == 255 and vic[0x1c] == 0
                    assert vic[0x15] == (1 << count) - 1
                    assert vic[0x10] == 0
                    assert vic[0x1b] == 0 and vic[0x11]&0x60 == 0x20
                    assert vic[0x16]&0x10 and vic[0x21]&15 == scene["background"]
                    assert vic[0x18]&0xfe == 0x18 and vic[0x16]&7 == 0
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
                        expected_color = expected_front_color(depths[face])
                        assert vic[0x27+slot]&15 == expected_color, (index,face,vic[0x27+slot]&15,expected_color)
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
                        assert vic[slot * 2] == (scene["center"][0]-104+2*min_x)&255
                        assert vic[slot * 2 + 1] == (scene["center"][1]-78+2*min_y)&255
                        assert ram[0x7f8 + slot] == buffer // 64 + slot
                        assert ram[0x7ff8 + slot] == (mirror-0x4000)//64+slot
                    assert ram[screen:screen+1000] == expected_screen, "Static source artwork attributes changed"
                    duration = ram[labels["renderCycles"]] | ram[labels["renderCycles"] + 1] << 8
                    if previous_cycles is not None:
                        interval = 19656*2
                        assert abs(cycles - previous_cycles - interval) < 64, (index,cycles-previous_cycles,duration)
                    previous_cycles = cycles
                    samples.append({"yaw": yaw, "pitch": pitch,
                                    "sprite_colors": [vic[0x27+slot]&15 for slot in range(count)],
                                    "sprites": count, "nonempty_sprites": nonempty,
                                    "visible_faces": len(visible_faces), "selected_faces": actual_faces,
                                    "render_cycles": duration, "presentation_cycle": cycles, "raster": raster})
                    frames.append(render_preview(ram, labels, colors, color_ram, scene["background"]))
                    if index == 48:
                        # A VICE screenshot records the actual VIC output, not the host preview.
                        monitor.run(f'screenshot "{output / "native.png"}" 2')
                        screenshot = Image.open(output / "native.png").convert("RGB").crop((32, 35, 352, 235))
                        frames[-2].save(output / "expected-native.png")
                        assert np.array_equal(np.asarray(screenshot), np.asarray(frames[-2])), "Native VIC screenshot differs from verified sprites"
                    # Stop on the intervening PAL frame. Its displayed geometry
                    # must stay intact while every active color shifts one shade.
                    monitor.run("enable 2")
                    monitor.run("x")
                    half_pc, _, half_cycles = monitor.registers()
                    assert half_pc == labels["frameColorsUpdated"], "Missing intervening color update"
                    assert abs(half_cycles-cycles-19656) < 512, "Color update skipped a PAL frame"
                    monitor.run("bank io")
                    half_vic = monitor.memory(output / "half-vic.bin", 0xd000, 0xd03f)
                    half_colors = [value & 15 for value in half_vic[0x27:0x2f]]
                    assert half_vic[0x18]&0xfe == 0xf0, "MCI field B screen not selected"
                    assert half_vic[0x16]&7 == scene["horizontal_phase_shift"], "MCI field B X phase differs"
                    assert half_vic[:0x11] == vic[:0x11] and half_vic[0x15] == vic[0x15], "Intervening frame moved sprites"
                    for slot in range(count):
                        assert half_colors[slot] == darker_color(vic[0x27+slot]&15), "Intervening frame did not darken one shade"
                    monitor.run("bank ram")
                    front = monitor.memory(output / "half-sprites.bin", buffer, buffer+511)
                    assert front == ram[buffer:buffer+512], "Intervening frame changed displayed sprite pixels"
                    field_b_front = monitor.memory(output / "half-mirror.bin", mirror, mirror+511)
                    assert field_b_front == front, "MCI field B sprites differ from field A"
                    shown = monitor.memory(output / "half-shown.bin", labels["shownMetadataBase"], labels["shownMetadataBase"])
                    assert shown == bytes([base]), "Intervening frame swapped sprite buffers"
                    monitor.run("bank cpu")
                    monitor.run("disable 2")
                    samples[-1]["darker_sprite_colors"] = half_colors[:count]
                    if index == 48:
                        monitor.run(f'screenshot "{output / "native-a.png"}" 2')
                        image_a = Image.open(output / "native-a.png").convert("RGB").crop((32, 35, 352, 235))
                        frames[-1].save(output / "expected-native-a.png")
                        assert np.array_equal(np.asarray(image_a), np.asarray(frames[-1])), "Native MCI field A differs"
                    frames.append(render_preview(ram, labels, colors, color_ram, scene["background"], half_colors, phase=1, horizontal_shift=scene["horizontal_phase_shift"]))
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
    frames[0].save(output / "animation.gif", save_all=True, append_images=frames[1:],
                   duration=20, loop=0,
                   optimize=False, disposal=2)
    if args.variant == "hexagon" and len(samples) >= 64:
        assert max(s["nonempty_sprites"] for s in samples) == 8
        assert {color for sample in samples for color in sample["sprite_colors"]} == {6, 4, 10, 15, 1}
    (output / "monitor.log").write_text("\n".join(transcript))
    result = {"variant": args.variant, "prg_sha256": hashlib.sha256(program.read_bytes()).hexdigest(), "geometry": geometry,
              "face_selection": "eight_largest_by_facing_depth",
              "rotation": "constant_yaw_6_pitch_3",
              "lighting": "camera_facing_rotated_normal_z",
              "lighting_restored_from": "9e10543",
              "brightness": "brighter_toward_camera",
              "sprite_palette": [6, 4, 10, 15, 1], "shade_index_thresholds": [6, 12, 18, 24],
              "color_animation": "normal_then_one_shade_darker_each_pal_frame",
              "native_color_frames": len(samples)*2,
              "background_art_sha256": hashlib.sha256(artwork).hexdigest(),
              "bitmap_mode": "multicolor_interlace" if scene["phase_count"]==2 else "multicolor", "sphere_center": scene["center"],
              "bitmap_passthrough": scene["bitmap_passthrough"], "generated_dithering": scene["generated_dithering"],
              "pentagon_coloring": False, "color_screen_count": 2, "vic_banks": [0, 1], "sprite_buffers_mirrored": True, "color_screen_static": True,
              "per_frame_color_reset": False,
              "source_artwork_pixel_differences": 0,
              "sprite_priority": "in_front_of_graphics", "bitmap_unchanged_across_frames": True,
              "native_frames": len(samples), "native_sprite_bytes_checked": len(samples) * 504,
              "exact_edge_samples": curve_samples,
              "maximum_nonempty_sprites": max(s["nonempty_sprites"] for s in samples),
              "native_screenshot_pixel_differences": 0 if len(samples)>48 else None,
              "pal_ticks_per_presentation": 2,
              "frames_per_second": 50.124542124542124 / 2,
              "render_cycles_min": min(s["render_cycles"] for s in samples),
              "render_cycles_mean": sum(s["render_cycles"] for s in samples) / len(samples),
              "render_cycles_max": max(s["render_cycles"] for s in samples), "samples": samples}
    (output / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "samples"}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=int, default=257)
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
