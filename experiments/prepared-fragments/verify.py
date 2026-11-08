#!/usr/bin/env python3
"""Verify resolved cube regions, native glyph allocation and an input overload."""

import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess

from PIL import Image, ImageChops


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT = HERE / "build/verification"
PATTERNS = ((0, 0), (0x00, 0x33), (0xCC, 0x33), (0xCC, 0xFF),
            (0xFF, 0xFF), (0xFF, 0xEE), (0xBB, 0xEE), (0xBB, 0xAA),
            (0xAA, 0xAA), (0xAA, 0x99), (0x66, 0x99), (0x66, 0x55), (0x55, 0x55))
PALETTE = ((0x27, 0x24, 0xC4), (255, 255, 255), (0x91, 0xFF, 0x84), (0x41, 0xB9, 0x36))


def signed_area(poly):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))


def cube(x, y):
    faces = [[(x, y - 64), (x + 24, y - 88), (x, y - 112), (x - 24, y - 88)],
             [(x, y), (x + 24, y - 24), (x + 24, y - 88), (x, y - 64)],
             [(x, y), (x, y - 64), (x - 24, y - 88), (x - 24, y - 24)]]
    return [poly if signed_area(poly) > 0 else poly[::-1] for poly in faces]


def covered(poly, x, y):
    for a, b in zip(poly, poly[1:] + poly[:1]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        cross = dx * (2 * y + 1 - 2 * a[1]) - dy * (2 * x + 1 - 2 * a[0])
        if cross < 0 or cross == 0 and not (dy < 0 or dy == 0 and dx > 0):
            return False
    return True


def reference(phase, frame):
    bx = 82 + 2 * math.floor(3 * math.sin(phase * math.tau / 16) + 0.5)
    by = 132 + 2 * math.floor(2 * math.cos(phase * math.tau / 16) + 0.5)
    aa, bb = cube(44, 156), cube(bx, by)
    assert frame["cube_a"] == [[list(point) for point in poly] for poly in aa]
    assert frame["cube_b"] == [[list(point) for point in poly] for poly in bb]
    fragment_masks = []
    boundary = {(28, 0)}
    shared = {}
    for fragment in frame["fragments"]:
        poly, material = fragment["vertices"], fragment["material"]
        mask = {(x, y) for y in range(160) for x in range(128) if covered(poly, x, y)}
        fragment_masks.append(mask)
        for cx, cy in {(x // 4, y // 8) for x, y in mask}:
            count = sum((x, y) in mask for y in range(cy * 8, cy * 8 + 8)
                        for x in range(cx * 4, cx * 4 + 4))
            if count == 32:
                shared[(cx, cy)] = material
            else:
                boundary.add((cx, cy))
    assert len(boundary) == frame["private_boundary_cells"] <= 243
    pixels = []
    for y in range(160):
        for x in range(128):
            af = [i for i, face in enumerate(aa) if covered(face, x, y)]
            bf = [i for i, face in enumerate(bb) if covered(face, x, y)]
            assert len(af) <= 1 and len(bf) <= 1
            if af:
                material = (12, 3, 4)[af[0]] if af[0] != 1 or not bf else (7, 4, 5)[bf[0]]
            else:
                material = (12, 4, 8)[bf[0]] if bf else 0
            matches = [fragment["material"] for fragment, mask in zip(frame["fragments"], fragment_masks)
                       if (x, y) in mask]
            assert matches == ([material] if af or bf else []), (phase, x, y, material, matches)
            pixels.append((PATTERNS[material][y % 2] >> (6 - 2 * (x % 4))) & 3)
    for cy in range(8):
        for cx in range(2, 14):
            material = cx - 1
            pixels[cy * 128 + cx * 4:cy * 128 + cx * 4 + 4] = [
                (PATTERNS[material][cy % 2] >> (6 - 2 * lane)) & 3 for lane in range(4)]
            shared[(cx, 0)] = material
        pixels[cy * 128 + 112:cy * 128 + 116] = [
            (PATTERNS[6][cy % 2] >> (6 - 2 * lane)) & 3 for lane in range(4)]
    pixels[1 * 128 + 112:1 * 128 + 114] = [1, 1]
    pixels[6 * 128 + 114:6 * 128 + 116] = [3, 3]
    glyphs = {}
    for cy in range(20):
        for cx in range(32):
            glyphs[(cx, cy)] = bytes(sum(pixels[(cy * 8 + row) * 128 + cx * 4 + lane]
                                             << (6 - 2 * lane) for lane in range(4))
                                    for row in range(8))
    image = Image.new("RGB", (256, 160))
    image.putdata([PALETTE[pixels[y * 128 + x // 2]] for y in range(160) for x in range(256)])
    return {"image": image, "glyphs": glyphs, "boundary": boundary, "shared": shared}


def verify_pair(ram, labels, oracle):
    font = ram[labels["frontFontHigh"]] << 8
    screen = ram[labels["frontScreenHigh"]] << 8
    matrix = ram[screen:screen + 1024]
    expected_font = bytearray(2048)
    for code in range(13):
        expected_font[8 * code:8 * code + 8] = bytes(PATTERNS[code][row % 2] for row in range(8))
    private_ids = []
    for sy in range(25):
        for sx in range(40):
            code = matrix[sy * 40 + sx]
            if 4 <= sx < 36 and 2 <= sy < 22:
                cell = sx - 4, sy - 2
                wanted = oracle["glyphs"][cell]
                if cell in oracle["boundary"]:
                    assert code >= 13, (cell, code, "boundary glyph was not private")
                    private_ids.append(code)
                    expected_font[8 * code:8 * code + 8] = wanted
                else:
                    assert code == oracle["shared"].get(cell, 0), (cell, code, "shared interior")
                assert ram[font + 8 * code:font + 8 * code + 8] == wanted, (cell, code, "cell pixels")
            else:
                assert code == 0
    assert matrix[1000:] == bytes(24)
    assert len(set(private_ids)) == len(private_ids) == len(oracle["boundary"])
    assert sorted(private_ids) == list(range(13, 13 + len(private_ids)))
    assert matrix[(2 * 40) + 4 + 28] == 13
    assert ram[font:font + 2048] == expected_font
    assert ram[labels["nextFree"]] == 13 + len(private_ids)
    assert ram[labels["allocatorFull"]] == ram[labels["allocationError"]] == 0
    return font, screen, len(private_ids)


def start_session(shared, output, labels):
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    command = shared.vice_command(os.environ.get("VICE", "x64sc"), HERE / "build/example.prg",
                                  port, ROOT / "palettes/colodore.vpl")
    log = (output / "vice.log").open("w")
    process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
    return process, port, log, command


def close_session(process, monitor, output, log):
    if monitor:
        (output / "monitor.log").write_text("\n".join(monitor.transcript))
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    log.close()


def normal_proof(shared, labels, references):
    output = OUTPUT / "normal"
    output.mkdir(parents=True, exist_ok=True)
    process, port, log, command = start_session(shared, output, labels)
    monitor = None
    scene = (HERE / "build/scene.bin").read_bytes()
    try:
        with shared.connect_monitor(process, port) as connection:
            monitor = shared.Monitor(connection)
            monitor.run("r")
            monitor.run(f"break {labels['displayComplete']:04x}")
            monitor.run("x")
            frames, images, field_counts = [], [], []
            for index in range(17):
                if index:
                    monitor.run("x")
                _, raster, clock = monitor.registers()
                monitor.run("bank ram")
                ram = monitor.memory(output / f"ram-{index:02d}.bin", 0, 0xFFFF)
                monitor.run("bank cpu")
                assert ram[labels["sceneData"]:labels["sceneData"] + len(scene)] == scene
                pose = index % 16
                assert ram[labels["frontPose"]] == ram[labels["poseUsed"]] == pose
                font, screen, allocated = verify_pair(ram, labels, references[pose])
                assert (font, screen) == ((0x2800, 0x0C00) if index % 2 == 0 else (0x2000, 0x0400))
                count = int.from_bytes(ram[labels["presentationCounter"]:labels["presentationCounter"] + 2], "little")
                assert count == index + 1
                fields = int.from_bytes(ram[labels["frameCounter"]:labels["frameCounter"] + 2], "little")
                field_counts.append(fields)
                vic = monitor.memory(output / "vic.bin", 0xD000, 0xD03F)
                assert vic[0x16] & 0x1F == 0x18 and vic[0x18] & 0xFE == (0x3A if index % 2 == 0 else 0x18)
                screenshot = output / f"pose-{index:02d}.png"
                monitor.run(f'scrsh "{screenshot}" 2')
                image = Image.open(screenshot).convert("RGB")
                expected = Image.new("RGB", image.size, PALETTE[0])
                expected.paste(references[pose]["image"], (64, 51))
                difference = ImageChops.difference(image, expected)
                if difference.getbbox() is not None:
                    expected.save(output / "expected-failed.png")
                    difference.save(output / "difference-failed.png")
                    raise AssertionError((pose, "full multicolor character pixels"))
                images.append(image)
                frames.append({"presentation": count, "pose": pose, "clock": clock,
                               "PAL_fields": fields, "raster": raster, "font": font,
                               "screen": screen, "private_glyphs": allocated,
                               "screenshot": screenshot.name})
            images[0].save(output / "prepared-fragments.gif", save_all=True,
                           append_images=images[1:], duration=250, loop=0)
            intervals = [b - a for a, b in zip(field_counts, field_counts[1:])]
            return {"pass": True, "presentations": 17, "distinct_poses": 16,
                    "complete_font_bytes_per_presentation": 2048, "matrix_bytes_per_presentation": 1024,
                    "private_glyph_counts": [item["private_glyphs"] for item in frames],
                    "capacity": 243, "PAL_fields_per_presentation": intervals,
                    "mean_PAL_fields_per_presentation": sum(intervals) / len(intervals),
                    "frames": frames, "command": command,
                    "scope": "Unmodified normal scene. Expected selectors come directly from original cube-face half-plane tests; serialized fragment masks independently verify partition and boundary capacity. All glyph bytes, matrix cell ownership and complete native screenshots match."}
    finally:
        close_session(process, monitor, output, log)


def capacity_proof(shared, labels):
    output = OUTPUT / "capacity-control"
    output.mkdir(parents=True, exist_ok=True)
    process, port, log, command = start_session(shared, output, labels)
    monitor = None
    try:
        with shared.connect_monitor(process, port) as connection:
            monitor = shared.Monitor(connection)
            monitor.run("r")
            response = monitor.run(f"break {labels['consumeFragments']:04x}")
            checkpoint = int(re.search(r"BREAK:\s*(\d+)", response)[1])
            monitor.run(f"ignore {checkpoint} 1")
            monitor.run("x")
            monitor.run("bank ram")
            before = monitor.memory(output / "before-input.bin", 0, 0xFFFF)
            monitor.run("bank cpu")
            assert before[labels["poseUsed"]] == 1 and before[labels["frontPose"]] == 0
            target = before[labels["poseLow"] + 1] + 256 * before[labels["poseHigh"] + 1]
            stream = bytearray([243])
            cells = [(x, y) for y in range(20) for x in range(32) if (x, y) != (28, 0)][:243]
            for cx, cy in cells:
                x, y = cx * 4 + 1, cy * 8 + 1
                poly = ((x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1))
                stream.extend((12, 4))
                for a, b in zip(poly, poly[1:] + poly[:1]):
                    stream.extend((*a, *b))
            assert target + len(stream) < 0xD000
            payload = output / "over-capacity-input.prg"
            payload.write_bytes(target.to_bytes(2, "little") + stream)
            monitor.run(f'load "{payload}" 0')
            monitor.run(f"delete {checkpoint}")
            monitor.run(f"break {labels['capacityStopped']:04x}")
            monitor.run("x")
            monitor.run("bank ram")
            after = monitor.memory(output / "after-guard.bin", 0, 0xFFFF)
            monitor.run("bank cpu")
            assert after[labels["allocationError"]] == after[labels["allocatorFull"]] == 1
            assert after[labels["nextFree"]] == 0
            assert after[labels["frontPose"]] == before[labels["frontPose"]]
            assert after[labels["presentationCounter"]:labels["presentationCounter"] + 2] == before[labels["presentationCounter"]:labels["presentationCounter"] + 2]
            font, screen = before[labels["frontFontHigh"]] << 8, before[labels["frontScreenHigh"]] << 8
            assert after[font:font + 2048] == before[font:font + 2048]
            assert after[screen:screen + 1024] == before[screen:screen + 1024]
            back_font, back_screen = after[labels["drawFontHigh"]] << 8, after[labels["drawScreenHigh"]] << 8
            used = [value for value in after[back_screen:back_screen + 1000] if value >= 13]
            assert sorted(used) == list(range(13, 256))
            for code in range(13):
                assert after[back_font + 8 * code:back_font + 8 * code + 8] == bytes(PATTERNS[code][row % 2] for row in range(8))
            return {"pass": True, "injected_input_address": target, "input_bytes": len(stream),
                    "disjoint_one_pixel_rectangles": len(cells), "private_slots_consumed": 243,
                    "last_private_code": 255, "shared_glyphs_preserved": 13,
                    "published_front_preserved": True, "command": command,
                    "scope": "Isolated input-overload control. A crafted upcoming frame stream replaces prepared INPUT bytes before normal decoding. No PC, executable code, caller, or allocator-state change. Normal renderer naturally exhausts all private slots and stops before publication without wrapping into shared glyphs."}
    finally:
        close_session(process, monitor, output, log)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name in ("receipt.json", "normal-proof.json", "capacity-proof.json"):
        (OUTPUT / name).unlink(missing_ok=True)
    spec = importlib.util.spec_from_file_location("shared_native_monitor", ROOT / "verify.py")
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    labels = shared.read_labels(HERE / "build/main.sym")
    geometry = json.loads((HERE / "build/geometry.json").read_text())
    serialized = bytearray()
    for frame, offset in zip(geometry["frames"], geometry["offsets"]):
        assert len(serialized) == offset
        serialized.append(len(frame["fragments"]))
        for fragment in frame["fragments"]:
            vertices = fragment["vertices"]
            serialized.extend((fragment["material"], len(vertices)))
            for a, b in zip(vertices, vertices[1:] + vertices[:1]):
                serialized.extend((*a, *b))
    assert serialized == (HERE / "build/scene.bin").read_bytes()
    references = [reference(index, frame) for index, frame in enumerate(geometry["frames"])]
    normal = normal_proof(shared, labels, references)
    (OUTPUT / "normal-proof.json").write_text(json.dumps(normal, indent=2) + "\n")
    capacity = capacity_proof(shared, labels)
    (OUTPUT / "capacity-proof.json").write_text(json.dumps(capacity, indent=2) + "\n")
    receipt = {"pass": True, "normal": normal, "capacity_control": capacity,
               "program_sha256": hashlib.sha256((HERE / "build/example.prg").read_bytes()).hexdigest()}
    (OUTPUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"pass": True, "normal_presentations": normal["presentations"],
                      "private_glyph_counts": normal["private_glyph_counts"],
                      "PAL_fields_per_presentation": normal["PAL_fields_per_presentation"],
                      "mean_PAL_fields_per_presentation": normal["mean_PAL_fields_per_presentation"],
                      "capacity_control_passed": capacity["pass"]}, indent=2))


if __name__ == "__main__":
    main()
