#!/usr/bin/env python3
"""Compare live C64 UV rendering with a direct mathematical image oracle."""

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess

from PIL import Image, ImageChops


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
QUADS = ((0, 4, 6, 2), (1, 3, 7, 5), (0, 1, 5, 4),
         (2, 6, 7, 3), (0, 2, 3, 1), (4, 5, 7, 6))
UV = ((0, 0), (16, 0), (16, 16), (0, 16))
PALETTE_INDICES = (0, 6, 3, 1)
WIDTH, HEIGHT = 80, 50
PRESENTATIONS = 66
FLAT_COLORS = (1, 1, 2, 2, 3, 3)
FIXED_TEXTURE_FACE = 4


def rounded(value):
    return math.floor(value + 0.5)


def scaled(a, b):
    """The documented quantized product, derived without a table lookup."""
    assert -128 <= a + b <= 127 and -128 <= a - b <= 127
    return (a + b) ** 2 // 256 - (a - b) ** 2 // 256


def geometry(phase):
    yaw = (4 * phase + 1) % 256
    pitch = rounded(24 * math.sin(math.tau * phase / 64 + 0.4))
    sy, cy, sp, cp = (rounded(64 * math.sin(math.tau * angle / 256))
                      for angle in (yaw, yaw + 64, pitch, pitch + 64))
    ay, ap = math.tau * yaw / 256, math.tau * pitch / 256
    rotated, projected, ideal_errors = [], [], []
    for vertex in range(8):
        x, y, z = (24 if vertex & bit else -24 for bit in (1, 2, 4))
        rx = scaled(x, cy) + scaled(z, sy)
        rz = scaled(z, cy) - scaled(x, sy)
        ry = scaled(y, cp) - scaled(rz, sp)
        rz = scaled(rz, cp) + scaled(y, sp)
        factor = rounded(80 * 64 / (160 + rz))
        pixel = (40 + scaled(rx, factor), 25 - scaled(ry, factor))
        assert 0 <= pixel[0] < WIDTH and 0 <= pixel[1] < HEIGHT
        rotated.append((rx, ry, rz))
        projected.append(pixel)
        fx, fz = x * math.cos(ay) + z * math.sin(ay), z * math.cos(ay) - x * math.sin(ay)
        fy, fz = y * math.cos(ap) - fz * math.sin(ap), fz * math.cos(ap) + y * math.sin(ap)
        ideal = (40 + 80 * fx / (160 + fz), 25 - 80 * fy / (160 + fz))
        ideal_errors.append(4 * math.hypot(pixel[0] - ideal[0], pixel[1] - ideal[1]))
    assert max(ideal_errors) < 7
    visible = [int(sum(projected[a][0] * projected[b][1] - projected[a][1] * projected[b][0]
                       for a, b in zip(face, face[1:] + face[:1])) > 0) for face in QUADS]
    assert 1 <= sum(visible) <= 3
    return {"yaw": yaw, "pitch": pitch, "rotated": rotated, "projected": projected,
            "visible": visible, "max_ideal_error_physical_pixels": max(ideal_errors)}


def source_texture(phase):
    def wave(index):
        return rounded(16 + 15 * math.sin(math.tau * (index % 256) / 256))

    return bytes(((wave(16 * u + 4 * phase) + wave(16 * v - 8 * phase)
                   + wave(8 * (u + v) + 4 * phase)) // 8) & 3
                 for v in range(16) for u in range(16))


def cross(a, b, point):
    return (b[0] - a[0]) * (point[1] - a[1]) - (b[1] - a[1]) * (point[0] - a[0])


def top_left(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    return dy < 0 or (dy == 0 and dx > 0)


def reference(phase, variant="all"):
    """Direct point/triangle tests and closed-form UV; no assembler DDA replay."""
    row = geometry(phase)
    texture = source_texture(phase)
    samples = bytearray(WIDTH * HEIGHT)
    owners, addresses = {}, set()
    face_samples = [0] * 6
    textured_samples = 0
    for face, quad in enumerate(QUADS):
        if not row["visible"][face]:
            continue
        for corners in ((0, 1, 2), (0, 2, 3)):
            a, b, c = (row["projected"][quad[index]] for index in corners)
            uv0, uv1, uv2 = (UV[index] for index in corners)
            area = cross(a, b, c)
            assert area > 0
            dx1, dy1 = b[0] - a[0], b[1] - a[1]
            dx2, dy2 = c[0] - a[0], c[1] - a[1]
            gradients = []
            for axis in range(2):
                delta1, delta2 = uv1[axis] - uv0[axis], uv2[axis] - uv0[axis]
                gradients.append((256 * (delta1 * dy2 - delta2 * dy1) // area,
                                  256 * (dx1 * delta2 - dx2 * delta1) // area))
            edges = ((a, b), (b, c), (c, a))
            for y in range(min(a[1], b[1], c[1]), max(a[1], b[1], c[1]) + 1):
                for x in range(min(a[0], b[0], c[0]), max(a[0], b[0], c[0]) + 1):
                    if not all(cross(first, last, (x, y)) > 0
                               or (cross(first, last, (x, y)) == 0 and top_left(first, last))
                               for first, last in edges):
                        continue
                    assert (x, y) not in owners, (phase, face, "overlapping visible triangles", x, y)
                    owners[x, y] = face
                    face_samples[face] += 1
                    if variant == "one-face" and face != FIXED_TEXTURE_FACE:
                        samples[y * WIDTH + x] = FLAT_COLORS[face]
                        continue
                    u, v = ((256 * uv0[axis] + gradients[axis][0] * (x - a[0])
                             + gradients[axis][1] * (y - a[1])) % 65536 for axis in range(2))
                    address = ((u // 256) & 15) + 16 * ((v // 256) & 15)
                    addresses.add(address)
                    samples[y * WIDTH + x] = texture[address]
                    textured_samples += 1
    return {**row, "texture": texture, "samples": bytes(samples),
            "covered_samples": len(owners), "samples_by_face": face_samples,
            "textured_samples": textured_samples, "flat_samples": len(owners) - textured_samples,
            "fixed_face_visible": bool(row["visible"][FIXED_TEXTURE_FACE]),
            "sampled_texture_addresses": sorted(addresses)}


def charset():
    return bytes((((code >> (0 if row < 4 else 4)) & 3) * 0x50
                  + ((code >> (2 if row < 4 else 6)) & 3) * 0x05)
                 for code in range(256) for row in range(8))


def expected_canvas(row, palette):
    image = Image.new("RGB", (WIDTH, HEIGHT))
    image.putdata([palette[PALETTE_INDICES[value]] for value in row["samples"]])
    return image.resize((320, 200), Image.Resampling.NEAREST)


def assert_bytes(actual, expected, description):
    differences = [index for index, (first, last) in enumerate(zip(actual, expected)) if first != last]
    if len(actual) != len(expected) or differences:
        raise AssertionError(f"{description}: {len(differences)} differing bytes; first offsets {differences[:12]}")


def decode_matrix(matrix):
    """Read four 4x4 samples from each real VIC screen character code."""
    return bytes((matrix[(y // 2) * 40 + x // 2] >> (4 * (y % 2) + 2 * (x % 2))) & 3
                 for y in range(HEIGHT) for x in range(WIDTH))


def input_hashes(variant):
    paths = (*sorted(HERE.glob("*.asm")), HERE / "build.sh", HERE / "run.sh", Path(__file__).resolve(),
             HERE.parent / "build-one.sh", HERE.parent / "run-one.sh", ROOT / "verify.py")
    if variant == "one-face":
        paths += (HERE / "one-face/main.asm",)
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("all", "one-face"), default="all",
                        help="All faces textured, or fixed face 4 textured with the other five flat.")
    parser.add_argument("--output", type=Path, help="Retain this run separately from previous native proofs.")
    args = parser.parse_args()
    output = args.output.resolve() if args.output else HERE / ("build/verification-one-face" if args.variant == "one-face" else "build/verification")
    output.mkdir(parents=True, exist_ok=True)
    (output / "proof.json").unlink(missing_ok=True)
    (output / "textured-cube.gif").unlink(missing_ok=True)
    with (output / "build.log").open("w") as build_log:
        subprocess.run(["sh", str(HERE / "build.sh"), args.variant], cwd=HERE, check=True,
                       stdout=build_log, stderr=subprocess.STDOUT)
    sources = input_hashes(args.variant)
    references = [reference(phase, args.variant) for phase in range(64)]
    assert len({tuple(row["projected"]) for row in references}) == 64
    assert len({row["texture"] for row in references}) > 32
    assert set().union(*(set(row["sampled_texture_addresses"]) for row in references)) == set(range(256))
    assert any(row["fixed_face_visible"] for row in references)
    assert any(not row["fixed_face_visible"] for row in references)
    if args.variant == "one-face":
        assert all(row["textured_samples"] == row["samples_by_face"][FIXED_TEXTURE_FACE] for row in references)
    spec = importlib.util.spec_from_file_location("textured_native_monitor", ROOT / "verify.py")
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    artifact_folder = HERE / "one-face" if args.variant == "one-face" else HERE
    labels_file = artifact_folder / "build/main.sym"
    labels = shared.read_labels(labels_file)
    program = artifact_folder / "build/example.prg"
    program_hash = hashlib.sha256(program.read_bytes()).hexdigest()
    inputs = output / "inputs"
    inputs.mkdir(exist_ok=True)
    shutil.copy2(program, inputs / "example.prg")
    shutil.copy2(labels_file, inputs / "main.sym")
    for name in sources:
        destination = inputs / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    palette_file = ROOT / "palettes/colodore.vpl"
    palette = [tuple(int(value, 16) for value in line.split()[:3])
               for line in palette_file.read_text().splitlines()
               if line.strip() and not line.lstrip().startswith("#")]
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    command = shared.vice_command(os.environ.get("VICE", "x64sc"), program, port, palette_file)
    process = monitor = None
    observations, images, image_phases, clocks = [], [], [], []
    with (output / "vice.log").open("w") as log:
        try:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            monitor = shared.Monitor(shared.connect_monitor(process, port))
            monitor.run("r")
            monitor.run(f'break ${labels["framePresented"]:04x}')
            for index in range(PRESENTATIONS):
                monitor.run("x")
                registers = monitor.run("r")
                monitor.run("bank ram")
                ram = monitor.memory(output / f"pose-{index:02d}.ram", 0, 65535)
                monitor.run("bank cpu")
                phase = index % 64
                row = references[phase]
                assert ram[labels["shownPhase"]] == phase, (index, "shown phase")
                count = int.from_bytes(ram[labels["presentationCount"]:labels["presentationCount"] + 2], "little")
                assert count == index + 1, (index, "publication counter", count)
                for axis, name in enumerate(("rotatedX", "rotatedY", "rotatedZ")):
                    assert_bytes(ram[labels[name]:labels[name] + 8],
                                 bytes(point[axis] & 255 for point in row["rotated"]), f"phase {phase} {name}")
                for axis, name in enumerate(("projectedX", "projectedY")):
                    assert_bytes(ram[labels[name]:labels[name] + 8],
                                 bytes(point[axis] for point in row["projected"]), f"phase {phase} {name}")
                assert_bytes(ram[labels["faceVisible"]:labels["faceVisible"] + 6],
                             bytes(row["visible"]), f"phase {phase} face culling")
                if row["textured_samples"]:
                    assert_bytes(ram[labels["texture"]:labels["texture"] + 256], row["texture"],
                                 f"phase {phase} live plasma texture")
                screen = ram[labels["shownScreenHigh"]] * 256
                assert screen in (0x0400, 0x0C00), (index, "front screen", screen)
                if observations:
                    assert screen != observations[-1]["front_screen"], (index, "hidden buffer alternation")
                matrix = ram[screen:screen + 1000]
                assert_bytes(decode_matrix(matrix), row["samples"], f"phase {phase} complete displayed UV sample canvas")
                assert_bytes(ram[0x2000:0x2800], charset(), "static four-sample charset")
                vic = monitor.memory(output / f"vic-{index:02d}.bin", 0xD000, 0xD02E)
                assert (vic[0x11] & 0x7F) == 0x1B and (vic[0x16] & 0x3F) == 0x18
                assert (vic[0x18] & 0xFE) == (((screen // 1024) << 4) | 8)
                assert vic[0x15] == 0 and tuple(value & 15 for value in vic[0x20:0x24]) == (0, 0, 6, 3)
                if index == 0:
                    color_ram = monitor.memory(output / "color-ram.bin", 0xD800, 0xDBE7)
                    assert {value & 15 for value in color_ram} == {9}
                cpu = re.search(r"^\.;[0-9a-fA-F]{4}\s+(.*)$", registers, re.M)[1].split()
                raster, cycle, clock = map(int, cpu[-3:])
                assert 0 <= raster < 35, (index, "publication after top border", raster, cycle)
                clocks.append(clock)
                observation = {"presentation": count, "phase": phase, "yaw": row["yaw"], "pitch": row["pitch"],
                               "visible_faces": row["visible"], "covered_samples": row["covered_samples"],
                               "samples_by_face": row["samples_by_face"],
                               "textured_samples": row["textured_samples"], "flat_samples": row["flat_samples"],
                               "fixed_face_visible": row["fixed_face_visible"],
                               "front_screen": screen, "clock": clock, "raster": [raster, cycle]}
                # At raster zero the last complete VIC image belongs to the previous
                # publication. Compare its entire native image, including the border.
                if index:
                    previous = (phase - 1) % 64
                    filename = f"visible-phase-{previous:02d}-{index:02d}.png"
                    monitor.run(f'screenshot "{output / filename}" 2')
                    actual = Image.open(output / filename).convert("RGB")
                    expected = Image.new("RGB", actual.size, palette[0])
                    expected.paste(expected_canvas(references[previous], palette), (32, 35))
                    difference = ImageChops.difference(actual, expected)
                    if difference.getbbox() is not None:
                        expected.save(output / "expected-failed.png")
                        difference.save(output / "difference-failed.png")
                        raise AssertionError((index, "complete native image", difference.getbbox()))
                    observation["screenshot"] = filename
                    observation["screenshot_phase"] = previous
                    images.append(actual)
                    image_phases.append(previous)
                observations.append(observation)
            monitor.connection.sendall(b"quit\n")
            process.wait(timeout=5)
        finally:
            if process is not None and process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            if monitor is not None:
                (output / "monitor.log").write_text("\n".join(monitor.transcript))
                monitor.connection.close()
    assert input_hashes(args.variant) == sources, "Verification inputs changed during native playback"
    assert hashlib.sha256(program.read_bytes()).hexdigest() == program_hash, "PRG changed during native playback"
    intervals, field_intervals = [], []
    for first, last in zip(observations, observations[1:]):
        interval = last["clock"] - first["clock"]
        delta = 63 * (last["raster"][0] - first["raster"][0]) + last["raster"][1] - first["raster"][1]
        assert interval > 0 and (interval - delta) % 19656 == 0
        intervals.append(interval)
        field_intervals.append((interval - delta) // 19656)
    # Use the first complete cycle, retaining the measured hold time of every
    # pose instead of assigning an inspection-only fixed animation speed.
    durations = [max(10, round(intervals[index] / 985248 * 1000 / 10) * 10) for index in range(64)]
    images[0].save(output / "textured-cube.gif", save_all=True, append_images=images[1:64],
                   duration=durations, loop=0, optimize=False)
    mean_clocks = sum(intervals) / len(intervals)
    jobs = [{"rendered_phase": last["phase"], "interval_PAL_clocks": interval,
             "fixed_face_visible": last["fixed_face_visible"], "textured_samples": last["textured_samples"],
             "flat_samples": last["flat_samples"]}
            for last, interval in zip(observations[1:], intervals)]
    visibility_timing = {}
    for visible in (True, False):
        selected = [job for job in jobs if job["fixed_face_visible"] == visible]
        values = [job["interval_PAL_clocks"] for job in selected]
        visibility_timing["fixed_face_visible" if visible else "fixed_face_hidden"] = {
            "rendered_jobs": len(values), "mean_interval_PAL_clocks": sum(values) / len(values),
            "mean_updates_per_second": 985248 / (sum(values) / len(values)),
            "textured_sample_range": [min(job["textured_samples"] for job in selected), max(job["textured_samples"] for job in selected)],
            "flat_sample_range": [min(job["flat_samples"] for job in selected), max(job["flat_samples"] for job in selected)],
        }
    report = {"pass": True, "variant": args.variant,
              "textured_faces": [FIXED_TEXTURE_FACE] if args.variant == "one-face" else list(range(6)),
              "flat_face_selectors": list(FLAT_COLORS) if args.variant == "one-face" else None,
              "program_sha256": program_hash, "source_sha256": sources,
              "retained_program": "inputs/example.prg", "retained_symbols": "inputs/main.sym",
              "retained_sources_prefix": "inputs/",
              "presentations": len(observations), "moving_poses": 64,
              "complete_uv_sample_canvases_compared": len(observations), "samples_per_canvas": 4000,
              "complete_screen_matrices_compared": len(observations), "bytes_per_matrix": 1000,
              "live_texture_bytes_per_visible_pose": 256,
              "live_texture_states_compared": sum(bool(row["textured_samples"]) for row in (references[index % 64] for index in range(PRESENTATIONS))),
              "distinct_live_textures": len({row["texture"] for row in references if row["textured_samples"]}),
              "fixed_face_visible_phases": [phase for phase, row in enumerate(references) if row["fixed_face_visible"]],
              "fixed_face_hidden_phases": [phase for phase, row in enumerate(references) if not row["fixed_face_visible"]],
              "textured_samples_per_pose": [row["textured_samples"] for row in references],
              "flat_samples_per_pose": [row["flat_samples"] for row in references],
              "visibility_timing": visibility_timing, "render_jobs": jobs,
              "texture_coordinates_exercised": 256, "complete_native_images_compared": len(images),
              "pixels_per_native_image": images[0].width * images[0].height,
              "max_ideal_geometry_error_physical_pixels": max(row["max_ideal_error_physical_pixels"] for row in references),
              "publication_interval_pal_clocks": [min(intervals), max(intervals)],
              "mean_publication_interval_pal_clocks": mean_clocks,
              "mean_updates_per_second": 985248 / mean_clocks,
              "pal_fields_per_publication": field_intervals,
              "animation_phases": image_phases[:64], "animation_duration_ms": durations,
              "observations": observations, "command": command, "owned_process_returncode": process.returncode,
              "limits": ["Own affine-UV cube and plasma, independent from the original Second Reality production.",
                         "All 64 authored poses plus wrap; arbitrary camera/angles, perspective-correct UV, physical hardware and analog CRT output are not covered."]}
    (output / "proof.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ("observations", "command", "source_sha256", "animation_duration_ms", "animation_phases",
                                     "render_jobs", "textured_samples_per_pose", "flat_samples_per_pose", "fixed_face_visible_phases", "fixed_face_hidden_phases")}, indent=2))


if __name__ == "__main__":
    main()
