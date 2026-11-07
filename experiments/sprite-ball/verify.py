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


def decode_bitmap(bitmap, screen, color_ram, background):
    packed = np.frombuffer(bitmap, dtype=np.uint8).reshape(25, 40, 8)
    rows = packed.transpose(0, 2, 1).reshape(200, 40)
    codes = ((rows[:, :, None] >> np.array([6, 4, 2, 0])) & 3).reshape(200, 160)
    attributes = np.frombuffer(screen, dtype=np.uint8).reshape(25, 40).repeat(8, axis=0).repeat(4, axis=1)
    local = np.frombuffer(color_ram, dtype=np.uint8).reshape(25, 40).repeat(8, axis=0).repeat(4, axis=1) & 15
    indices = np.choose(codes, [np.full_like(local, background), attributes >> 4, attributes & 15, local])
    return indices, codes


def check_scene(artwork, bitmap, screen, color_ram, scene):
    original, _ = decode_bitmap(artwork[2:8002], artwork[8002:9002], artwork[9002:10002], artwork[10002] & 15)
    circle = np.zeros((200, 160), dtype=bool)
    pending = [(scene["center"][0]//2, scene["center"][1])]
    while pending:
        x, y = pending.pop()
        if not (0 <= x < 160 and 0 <= y < 200) or circle[y, x] or original[y, x] != 1:
            continue
        circle[y, x] = True
        pending.extend(((x-1, y), (x+1, y), (x, y-1), (x, y+1)))
    yy, xx = np.where(circle)
    assert [round(np.mean(2*xx+1)), round(np.mean(yy+0.5))] == scene["center"]
    prepared, codes = decode_bitmap(bitmap, screen, color_ram, scene["background"])
    rim = np.asarray(Image.open(HERE / "assets" / "scene-rim.pbm").convert("1"), dtype=bool)
    lighting = (HERE / "assets" / "scene-rim-light.koa").read_bytes()
    rim_indices, _ = decode_bitmap(lighting[2:8002], lighting[8002:9002], lighting[9002:10002], lighting[10002] & 15)
    assert rim.shape == circle.shape and not np.any(rim & ~circle)
    assert np.array_equal(prepared[~circle], original[~circle]), "Scene artwork changed outside the circle"
    assert np.array_equal(prepared[rim], rim_indices[rim]), "Rim bitmap differs from authored lighting"
    assert np.all(prepared[circle & ~rim] == 0), "Circle interior is not solid black"
    assert np.all(codes[rim] >= 2), "Rim does not mask behind-graphics sprites"
    assert np.all(codes[circle & ~rim] < 2), "Circle interior hides behind-graphics sprites"
    return circle, codes, rim.repeat(2, axis=1), rim_indices.repeat(2, axis=1)


def render_preview(ram, labels, colors, color_ram, background):
    base = ram[labels["shownMetadataBase"]]
    screen = 0x400+(base//8)*0x400 if "gapVertices" in labels else 0x400
    indices, codes = decode_bitmap(ram[0x2000:0x3f40], ram[screen:screen+1000], color_ram, background)
    indices = indices.repeat(2, axis=1)
    foreground = (codes >= 2).repeat(2, axis=1)
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


def check_gap_colors(ram, screen, original, gaps, matrix, depths, selected, scene, circle, scene_codes, ramp):
    """Check full screen-cell rectangles, including the accepted overspill."""
    expected = bytearray(original)
    for face,neighbors in gaps:
        if not all(i in selected for i in neighbors):
            continue
        facing = -sum(depths[i] for i in neighbors)
        if facing<88:
            continue
        color = ramp[min(7, 1+(facing-88)//4)]
        _,points = project(face,matrix)
        offset_x, offset_y = (value-128 for value in scene["center"])
        left = (offset_x+2*min(x for x,y in points))//8
        right = (offset_x+2*max(x for x,y in points)+7)//8
        top = (offset_y+2*min(y for x,y in points))//8
        bottom = (offset_y+2*max(y for x,y in points)+7)//8
        for row in range(top,bottom):
            for col in range(left,right):
                area = np.s_[row*8:row*8+8, col*4:col*4+4]
                assert not np.any((scene_codes[area] == 1) & ~circle[area]), "Gap color reaches scene artwork"
                expected[row*40+col] = (original[row*40+col] & 15) | (color << 4)
    actual = ram[screen:screen+1000]
    if actual != expected:
        cell = next(i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b)
        raise AssertionError(f"Gap color cell {divmod(cell,40)}: {actual[cell]:02x} != {expected[cell]:02x}")
    return sum(a!=b for a,b in zip(actual,original))


def check_native(args, faces, geometry):
    build = HERE / "build" / args.variant
    output = build / "verification"
    output.mkdir(parents=True, exist_ok=True)
    labels = common.read_labels(build / "main.sym")
    program = build / "sprite-ball.prg"
    artwork = (HERE / "assets" / "scene.koa").read_bytes()
    expected_bitmap = (HERE / "build" / "ball-bitmap.bin").read_bytes()
    expected_screen = (HERE / "build" / "ball-screen.bin").read_bytes()
    expected_colors = (HERE / "build" / "ball-colors.bin").read_bytes()
    scene = json.loads((HERE / "build" / "scene.json").read_text())
    circle, scene_codes, rim, rim_indices = check_scene(artwork, expected_bitmap, expected_screen, expected_colors, scene)
    palette_file = ROOT / "palettes" / "colodore.vpl"
    colors = [tuple(int(v, 16) for v in line.split()[:3])
              for line in palette_file.read_text().splitlines()
              if line.strip() and not line.startswith("#")]
    rim_rgb = np.asarray(colors, dtype=np.uint8)[rim_indices[rim]]
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    command = common.vice_command(args.vice, program, port, palette_file)
    gaps = reference_gap_faces(faces) if args.variant=="hexagon" else []
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
                    monitor.run("bank io")
                    vic = monitor.memory(output / "vic.bin", 0xd000, 0xd03f)
                    color_ram = bytes(value & 15 for value in monitor.memory(output / "colors.bin", 0xd800, 0xdbe7))
                    assert color_ram == expected_colors, "Koala color RAM differs"
                    monitor.run("bank cpu")
                    yaw, pitch = ram[labels["angleYaw"]], ram[labels["anglePitch"]]
                    phase = index & 255
                    t = phase * 2 * np.pi / 256
                    expected_yaw = int(np.floor(2*phase+64*np.sin(t)+32*(np.cos(3*t)-1)+0.5)) & 255
                    expected_pitch = int(np.floor(phase+48*np.sin(2*t)+24*(np.cos(5*t)-1)+0.5)) & 255
                    assert ram[labels["motionPhase"]] == phase
                    assert (yaw, pitch) == (expected_yaw, expected_pitch), "Rotation path or phase differs"
                    stage = index // 128
                    mode = stage % 3
                    primary = (stage // 3) % 2
                    shift = ((index % 128) // 8) % 6 if mode == 2 else 0
                    ramps = ((0, 9, 11, 5, 12, 3, 13, 1), (0, 6, 2, 4, 10, 15, 7, 1))
                    shifted = lambda ramp: (ramp[0], *ramp[1+shift:7], *ramp[1:1+shift], ramp[7])
                    hex_ramp = shifted(ramps[primary])
                    pent_ramp = shifted(ramps[primary if mode == 1 else 1-primary])
                    base = ram[labels["shownMetadataBase"]]
                    screen = 0x400+(base//8)*0x400 if args.variant == "hexagon" else 0x400
                    buffer = 0x0c00 + (base // 8) * 512
                    count = ram[labels["usedSprites"]]
                    assert ram[labels["overflowCount"]] == 0, "Runtime sprite overflow"
                    assert count <= 8
                    assert vic[0x17] == vic[0x1d] == 255 and vic[0x1c] == 0
                    assert vic[0x15] == (1 << count) - 1
                    assert vic[0x10] == 0
                    assert vic[0x1b] == 255 and vic[0x11]&0x60 == 0x20
                    assert vic[0x16]&0x10 and vic[0x21]&15 == scene["background"]
                    assert vic[0x18]&0xfe == (0x18+(base//8)*0x10 if args.variant=="hexagon" else 0x18)
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
                        facing = -depths[face]
                        expected_color = hex_ramp[min(7, facing*8//29)]
                        assert vic[0x27+slot]&15 == expected_color, (index,face,vic[0x27+slot]&15,expected_color)
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
                        assert vic[slot * 2] == (scene["center"][0]-104+2*min_x)&255
                        assert vic[slot * 2 + 1] == (scene["center"][1]-78+2*min_y)&255
                        assert ram[0x7f8 + slot] == buffer // 64 + slot
                    if args.variant == "hexagon":
                        gap_cells = check_gap_colors(ram,screen,expected_screen,gaps,matrix,depths,expected_faces,scene,circle,scene_codes,pent_ramp)
                        if index == 0:
                            assert gap_cells, "Initial enclosed pentagons received no color"
                    else:
                        assert ram[screen:screen+1000] == expected_screen, "Artwork attributes changed"
                        gap_cells = 0
                    duration = ram[labels["renderCycles"]] | ram[labels["renderCycles"] + 1] << 8
                    if previous_cycles is not None:
                        interval = 19656*(3 if args.variant=="hexagon" else 2)
                        assert abs(cycles - previous_cycles - interval) < 64, (index,cycles-previous_cycles,duration)
                    previous_cycles = cycles
                    samples.append({"yaw": yaw, "pitch": pitch, "phase": phase,
                                    "palette_mode": mode, "primary_ramp": primary, "color_shift": shift,
                                    "sprite_colors": [vic[0x27+slot]&15 for slot in range(count)],
                                    "sprites": count, "nonempty_sprites": nonempty,
                                    "visible_faces": len(visible_faces), "selected_faces": actual_faces,
                                    "gap_color_cells": gap_cells,
                                    "render_cycles": duration, "presentation_cycle": cycles, "raster": raster})
                    frames.append(render_preview(ram, labels, colors, color_ram, scene["background"]))
                    assert np.array_equal(np.asarray(frames[-1])[rim], rim_rgb), "Gap colors or sprites bleed through the lit rim"
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
    frames[0].save(output / "animation.gif", save_all=True, append_images=frames[1:],
                   duration=60 if args.variant=="hexagon" else 40, loop=0,
                   optimize=False, disposal=2)
    if args.variant == "hexagon" and len(samples) >= 64:
        assert max(s["nonempty_sprites"] for s in samples) == 8
    (output / "monitor.log").write_text("\n".join(transcript))
    result = {"variant": args.variant, "prg_sha256": hashlib.sha256(program.read_bytes()).hexdigest(), "geometry": geometry,
              "face_selection": "eight_largest_by_facing_depth",
              "rotation": "mixed_sine_cosine_with_speed_changes_and_reversals",
              "hexagon_ramp": [0, 9, 11, 5, 12, 3, 13, 1],
              "pentagon_ramp": [0, 6, 2, 4, 10, 15, 7, 1],
              "palette_phase_presentations": 128, "palette_period_presentations": 768,
              "background_art_sha256": hashlib.sha256(artwork).hexdigest(),
              "bitmap_mode": "multicolor", "sphere_center": scene["center"], "dithering": False,
              "opaque_rim_pixels": scene["opaque_rim_pixels"], "rim_pixel_differences": 0,
              "lit_rim_pixels": scene["lit_rim_pixels"], "rim_lighting_sha256": scene["rim_lighting_sha256"],
              "outside_circle_artwork_pixel_differences": 0,
              "sprite_priority": "behind_graphics", "bitmap_unchanged_across_frames": True,
              "gap_mapping": "full_bounding_boxes_allow_color_clashes",
              "maximum_gap_color_cells": max(s["gap_color_cells"] for s in samples),
              "native_frames": len(samples), "native_sprite_bytes_checked": len(samples) * 504,
              "exact_edge_samples": curve_samples,
              "maximum_nonempty_sprites": max(s["nonempty_sprites"] for s in samples),
              "native_screenshot_pixel_differences": 0 if len(samples)>48 else None,
              "pal_ticks_per_presentation": 3 if args.variant=="hexagon" else 2,
              "frames_per_second": 50.124542124542124 / (3 if args.variant=="hexagon" else 2),
              "render_cycles_min": min(s["render_cycles"] for s in samples),
              "render_cycles_mean": sum(s["render_cycles"] for s in samples) / len(samples),
              "render_cycles_max": max(s["render_cycles"] for s in samples), "samples": samples}
    (output / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "samples"}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=int, default=769)
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
