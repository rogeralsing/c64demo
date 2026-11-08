#!/usr/bin/env python3
"""Prove the real XOR-filled, texture-overlaid 2x1 C64 canvas in PAL VICE.

The owning boundary is the native three-stage frame. It catches incompatible
edge ownership, a selector-zero overlay implemented as OR, dirty-buffer reuse,
and early publication. Existing solid and 4x4-texture verifiers do not exercise
that integration. Only ordinary routine/publication labels are observed.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from PIL import GifImagePlugin, Image, ImageChops


HERE = Path(__file__).resolve().parent
TEXTURED = HERE.parent
ROOT = HERE.parents[2]
WIDTH, HEIGHT = 64, 128
PRESENTATIONS = 66
PALETTE = (0, 6, 3, 1)
QUADS = ((0, 4, 6, 2), (1, 3, 7, 5), (0, 1, 5, 4),
         (2, 6, 7, 3), (0, 2, 3, 1), (4, 5, 7, 6))


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


sys.path.insert(0, str(ROOT))
ortho = module("hybrid_orthographic_reference", TEXTURED / "verify-ortho.py")
filled = module("hybrid_xor_reference", ROOT / "verify-filled.py")
shared, core = ortho.shared, ortho.core


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contains(polygon, x, y):
    """Exact half-planes, with the vertical-prefix fill's boundary ownership.

    This differs from row-span top-left ownership. It is equivalent to sampling
    at (x+epsilon**2,y+epsilon), independently of a crossing DDA or prefix loop.
    """
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        edge = core.cross(a, b, (x, y))
        owns_boundary = b[0] > a[0] or (b[0] == a[0] and b[1] < a[1])
        if edge < 0 or (edge == 0 and not owns_boundary):
            return False
    return True


def reference(phase):
    row = ortho.geometry(phase)
    projected = [(32 + (x + 512) // 1024, 64 - (y + 256) // 512)
                 for x, y, z in row["vertices"]]
    assert all(0 <= x < WIDTH and 0 <= y < HEIGHT for x, y in projected)
    visible, polygons, masks, owners = [], [], {}, set()
    for face, corners in enumerate(QUADS):
        polygon = [projected[index] for index in corners]
        a, b, c, d = polygon
        area = core.cross(a, b, c) + core.cross(a, c, d)
        visible.append(int(area > 0))
        if area <= 0:
            continue
        assert all(core.cross(polygon[i], polygon[(i + 1) % 4], polygon[(i + 2) % 4]) >= 0
                   for i in range(4)), (phase, face, "nonconvex projected face")
        assert core.cross(a, b, c) > 0, (phase, face, "degenerate UV triangle")
        mask = {(x, y) for y in range(min(p[1] for p in polygon), max(p[1] for p in polygon))
                for x in range(min(p[0] for p in polygon), max(p[0] for p in polygon))
                if contains(polygon, x, y)}
        assert not owners & mask, (phase, face, "overlapping visible faces")
        owners.update(mask)
        masks[face] = mask
        polygons.append((polygon, face // 2 + 1))
    hull = ortho.convex_hull(projected)
    silhouette = {(x, y) for y in range(HEIGHT) for x in range(WIDTH) if contains(hull, x, y)}
    assert owners == silhouette, (phase, "silhouette gaps or excess", len(owners ^ silhouette))

    # A second, exact rational-intersection oracle supplies the expected solid
    # image. It neither reads pending markers nor executes the C64 prefix fill.
    base = bytes(filled.polygon_reference(polygons))
    half_plane_base = bytearray(WIDTH * HEIGHT)
    for face, mask in masks.items():
        for x, y in mask:
            half_plane_base[y * WIDTH + x] = face // 2 + 1
    core.assert_bytes(base, half_plane_base, f"phase{phase} independent coverage oracles")
    texture_mask = masks.get(4, set())
    if visible[4]:
        assert {divmod(i, WIDTH)[::-1] for i, value in enumerate(base) if value == 3} == texture_mask
    texture = core.source_texture(phase)
    samples = bytearray(base)
    black_texels = changed_uv = changed_colors = 0
    addresses = set()
    gradients = None
    if visible[4]:
        a, b, c = (projected[QUADS[4][i]] for i in range(3))
        area = core.cross(a, b, c)
        gradients = ((4096 * (c[1] - b[1]) // area, 4096 * (b[0] - c[0]) // area),
                     (-4096 * (b[1] - a[1]) // area, 4096 * (b[0] - a[0]) // area))
        for x, y in texture_mask:
            u, v = ortho.mapped_uv("separable", gradients, a, x, y)
            address = u[0] + 16 * v[0]
            value = texture[address]
            samples[y * WIDTH + x] = value
            black_texels += value == 0
            changed_uv += u[2] or v[2]
            changed_colors += value != texture[u[1] + 16 * v[1]]
            addresses.add(address)
    return dict(**{k: v for k, v in row.items() if k not in ("projected", "visible")},
                projected=projected, visible=visible, texture=texture, base=base,
                samples=bytes(samples), mask=texture_mask, covered_samples=len(owners),
                textured_samples=len(texture_mask), black_texture_samples=black_texels,
                changed_uv_samples=changed_uv, changed_texture_colors=changed_colors,
                sampled_texture_addresses=addresses, gradients=gradients)


def precision(phase, basis, vertices, projected):
    """Physical rigidity and projection against a direct floating-point model."""
    axes = [tuple(n / 1024 for n in axis) for axis in basis]
    lengths = [math.sqrt(sum(n * n for n in axis)) for axis in axes]
    angles = [math.degrees(math.acos(max(-1, min(1, sum(a * b for a, b in zip(axes[i], axes[j]))
                  / (lengths[i] * lengths[j]))))) for i, j in ((0, 1), (0, 2), (1, 2))]
    yaw = (4 * phase + 1) * math.tau / 256
    pitch = core.rounded(24 * math.sin(math.tau * phase / 64 + .4)) * math.tau / 256
    roll = 4 * phase * math.tau / 256
    internal, screen_x, screen_y = [], [], []
    for vertex, actual in enumerate(vertices):
        x, y, z = (14 if vertex & (1 << axis) else -14 for axis in range(3))
        rx, rz = x * math.cos(yaw) + z * math.sin(yaw), z * math.cos(yaw) - x * math.sin(yaw)
        ry, rz = y * math.cos(pitch) - rz * math.sin(pitch), rz * math.cos(pitch) + y * math.sin(pitch)
        rx, ry = rx * math.cos(roll) - ry * math.sin(roll), rx * math.sin(roll) + ry * math.cos(roll)
        internal.extend(abs(a / 1024 - b) for a, b in zip(actual, (rx, ry, rz)))
        screen_x.append(abs(projected[vertex][0] - (32 + rx)))
        screen_y.append(abs(projected[vertex][1] - (64 - 2 * ry)))
    result = dict(basis_length_min=min(lengths), basis_length_max=max(lengths),
                  max_basis_relative_length_error=max(abs(n / 14 - 1) for n in lengths),
                  axis_angle_min_degrees=min(angles), axis_angle_max_degrees=max(angles),
                  max_axis_angle_error_degrees=max(abs(n - 90) for n in angles),
                  max_internal_coordinate_error_samples=max(internal),
                  max_screen_x_error_logical_samples=max(screen_x),
                  max_screen_y_error_logical_samples=max(screen_y))
    assert result["max_basis_relative_length_error"] < .002, (phase, "nonrigid basis", result)
    assert result["max_axis_angle_error_degrees"] < .2, (phase, "nonorthogonal basis", result)
    assert max(internal) < .01 and max(screen_x + screen_y) < .51, (phase, "projection precision", result)
    return result


def sources():
    paths = set(HERE.glob("*.asm")) | {Path(__file__).resolve()}
    paths.update(ROOT.joinpath("src").glob("*.asm"))
    paths.update((TEXTURED / "ortho-geometry.asm", TEXTURED / "texture-builder.asm",
                  TEXTURED / "verify-ortho.py", TEXTURED / "verify.py", ROOT / "verify.py",
                  ROOT / "verify-filled.py", ROOT / "palettes/colodore.vpl",
                  ROOT / "experiments/build-one.sh"))
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths)}


def registers(monitor):
    response = monitor.run("r")
    match = re.search(r"^\.;([0-9a-fA-F]{4})\s+(.*)$", response, re.M)
    if not match:
        raise RuntimeError(f"Unreadable native registers: {response}")
    raster, cycle, clock = map(int, match[2].split()[-3:])
    return int(match[1], 16), raster, cycle, clock


def continue_to(monitor, address):
    monitor.run("x")
    state = registers(monitor)
    assert state[0] == address, ("unexpected native checkpoint", state, address)
    return state


def read_ram(monitor, path):
    monitor.run("bank ram")
    result = monitor.memory(path, 0, 65535)
    monitor.run("bank cpu")
    return result


def words(ram, labels, name, count):
    first = labels[name]
    return [int.from_bytes(ram[first + i * 2:first + i * 2 + 2], "little", signed=True)
            for i in range(count)]


def check_geometry(ram, labels, phase, ref):
    assert ram[labels["phase"]] == phase, (phase, "phase progression")
    for label, name in (("angleYaw", "yaw"), ("anglePitch", "pitch"), ("orthoAngleRoll", "roll")):
        assert ram[labels[label]] == (ref[name] & 255), (phase, label)
    basis = list(zip(*(words(ram, labels, "orthoBasis" + axis, 3) for axis in "XYZ")))
    vertices = list(zip(*(words(ram, labels, "orthoVertex" + axis, 8) for axis in "XYZ")))
    assert basis == ref["basis"], (phase, "native Q10 basis", basis, ref["basis"])
    assert vertices == ref["vertices"], (phase, "native Q10 corners", vertices, ref["vertices"])
    for axis, name in enumerate(("rotatedX", "rotatedY", "rotatedZ")):
        core.assert_bytes(ram[labels[name]:labels[name] + 8],
                          bytes(point[axis] & 255 for point in ref["rotated"]), f"phase{phase} {name}")
    projected = list(zip(*(ram[labels[name]:labels[name] + 8] for name in ("projectedX", "projectedY"))))
    assert projected == ref["projected"], (phase, "native projected corners", projected, ref["projected"])
    expected_mask = sum(value << face for face, value in enumerate(ref["visible"]))
    assert ram[labels["visibleFaces"]] == expected_mask, (phase, "strict whole-quad culling")
    return precision(phase, basis, vertices, projected)


def expected_image(ref, size, palette):
    canvas = Image.new("RGB", (WIDTH, HEIGHT))
    canvas.putdata([palette[PALETTE[value]] for value in ref["samples"]])
    image = Image.new("RGB", size, palette[0])
    image.paste(canvas.resize((128, 128), Image.Resampling.NEAREST), (32 + 96, 35 + 32))
    return image


def save_gif(images, path, durations):
    palette = images[0].convert("P", palette=Image.Palette.ADAPTIVE, colors=4)
    header, _ = GifImagePlugin.getheader(palette, info={"loop": 0, "optimize": False})
    with path.open("wb") as stream:
        for block in header:
            stream.write(block)
        for image, duration in zip(images, durations):
            indexed = image.quantize(palette=palette, dither=Image.Dither.NONE)
            for block in GifImagePlugin.getdata(indexed, duration=duration, disposal=1):
                stream.write(block)
        stream.write(b";")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output = args.output.resolve() if args.output else HERE / "build/verification" / stamp
    output.mkdir(parents=True, exist_ok=True)
    status = HERE / "build/latest-verification.json"
    status.parent.mkdir(parents=True, exist_ok=True)
    status.write_text(json.dumps(dict(status="running", output=str(output))) + "\n")
    (output / "proof.json").unlink(missing_ok=True)
    observations, images, metrics = [], [], []
    try:
        refs = [reference(phase) for phase in range(64)]
        assert any(ref["black_texture_samples"] for ref in refs), "No selector-zero overlay was exercised"
        assert any(ref["visible"][4] for ref in refs) and any(not ref["visible"][4] for ref in refs)
        before_build = sources()
        with (output / "build.log").open("w") as log:
            subprocess.run(["sh", str(ROOT / "experiments/build-one.sh"), str(HERE)],
                           check=True, stdout=log, stderr=subprocess.STDOUT)
        frozen_sources = sources()
        assert before_build == frozen_sources, "Source changed while assembling"
        program = HERE / "build/example.prg"
        symbols = HERE / "build/main.sym"
        program_hash = sha(program)
        labels = shared.read_labels(symbols)
        for name in ("boundariesReady", "hybridBaseReady", "framePresented", "phase", "drawBufferHi",
                     "visibleFaces", "orthoBasisX", "orthoVertexX", "projectedX"):
            assert name in labels, ("missing ordinary runtime symbol", name)
        for rel in frozen_sources:
            target = output / "inputs" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, target)
        shutil.copy2(program, output / "example.prg")
        shutil.copy2(symbols, output / "main.sym")
        for name in ("main.vs", "assembler.log"):
            artifact = HERE / "build" / name
            if artifact.exists():
                shutil.copy2(artifact, output / name)
        original = program.read_bytes()
        load_address = int.from_bytes(original[:2], "little")
        loaded_end = load_address + len(original) - 2
        assert load_address == 0x0801 and loaded_end <= 0xd000, (
            "PRG autoload must stop below I/O", load_address, loaded_end)
        relocations = []
        for source_start, source_end, target_start, target_end in (
                ("hybridStageA", "hybridStageAEnd", "hybridRuntimeStart", "hybridRuntimeEnd"),
                ("hybridStageB", "hybridStageBEnd", "hybridBuilderRuntimeStart", "hybridBuilderRuntimeEnd")):
            first, last = labels[source_start], labels[source_end]
            target, end = labels[target_start], labels[target_end]
            assert load_address <= first < last <= loaded_end and last - first == end - target
            assert 0xe400 <= target < end <= 0xfffa
            relocations.append(dict(source=first, target=target, size=last - first,
                                    data=original[2 + first - load_address:2 + last - load_address]))
        prefix = filled.PrefixImage(original, labels)
        assert prefix.operands, "Expected the actual immediate-marker XOR filler"
        generated = filled.boundary_kernel_image(original, labels)
        palette_file, palette = filled.read_palette()
        buffer_images = {0x2000: bytes(2048), 0x2800: bytes(2048)}
        buffer_bounds = {}
        seen_buffers = set()
        with filled.machine(os.environ.get("VICE", "x64sc"), program, output) as monitor:
            # First real frame entry follows relocation and charset clearing,
            # before high-RAM geometry, shader state or SMC operands are used.
            monitor.run(f"break ${labels['nextFrame']:04x}")
            continue_to(monitor, labels["nextFrame"])
            startup = read_ram(monitor, output / "startup-relocated.ram")
            for relocation in relocations:
                first = relocation["target"]
                core.assert_bytes(startup[first:first + relocation["size"]], relocation["data"],
                                  f"staged runtime copied to${first:04x}")
            core.assert_bytes(startup[0x2000:0x3000], bytes(4096), "both initialized charset buffers")
            prefix.check_restored(startup)
            monitor.run("delete")
            for name in ("boundariesReady", "hybridBaseReady", "framePresented"):
                monitor.run(f"break ${labels[name]:04x}")
            color_ram = None
            for index in range(PRESENTATIONS):
                phase, ref = index % 64, refs[index % 64]
                boundary_state = continue_to(monitor, labels["boundariesReady"])
                pending = read_ram(monitor, output / f"pose-{index:02d}-boundaries.ram")
                metrics.append(check_geometry(pending, labels, phase, ref))
                draw = pending[labels["drawBufferHi"]] << 8
                assert draw in buffer_images and (not observations or draw != observations[-1]["charset"])
                opposite = draw ^ 0x0800
                for bank, previous in buffer_images.items():
                    core.assert_bytes(pending[bank:bank + 2048], previous,
                                      f"phase{phase} boundary stage preserved charset${bank:04x}")
                prefix.check_pending(pending, draw >> 8, filled.marker_reference(ref["base"]))
                if generated:
                    first, last, image = generated
                    core.assert_bytes(pending[first:last], image, "restored XOR boundary kernels")
                current = (min(x for x, y in ref["projected"]) // 4,
                           min(y for x, y in ref["projected"]),
                           max(x for x, y in ref["projected"]) // 4,
                           max(y for x, y in ref["projected"]))
                union = filled.union_bounds_reference(current, buffer_bounds.get(draw))
                slot = int(draw == 0x2800)
                assert filled.dirty_bounds(pending, labels, slot) == current, (phase, "current dirty bounds")

                base_state = continue_to(monitor, labels["hybridBaseReady"])
                base_ram = read_ram(monitor, output / f"pose-{index:02d}-base.ram")
                prefix.check_restored(base_ram)
                core.assert_bytes(filled.decode_charset(base_ram[draw:draw + 2048]), ref["base"],
                                  f"phase{phase} complete native XOR solid base")
                core.assert_bytes(base_ram[opposite:opposite + 2048], buffer_images[opposite],
                                  f"phase{phase} XOR fill preserved displayed charset")
                actual_union = tuple(base_ram[labels[name]] for name in
                                     ("filledMinColumn", "filledMinRow", "filledMaxColumn", "filledMaxRow"))
                assert actual_union == union, (phase, "old/new dirty rectangle union", actual_union, union)
                if ref["visible"][4]:
                    raw = filled.decode_charset(base_ram[draw:draw + 2048])
                    assert {(i % WIDTH, i // WIDTH) for i, value in enumerate(raw) if value == 3} == ref["mask"]

                published = continue_to(monitor, labels["framePresented"])
                after = read_ram(monitor, output / f"pose-{index:02d}-presented.ram")
                assert after[labels["phase"]] == phase, (index, "phase advanced before publication observation")
                assert (after[labels["drawBufferHi"]] << 8) == opposite, (phase, "back/front lifecycle")
                shown = (after[labels["drawBufferHi"]] ^ 8) << 8
                assert shown == draw
                prefix.check_restored(after)
                core.assert_bytes(filled.decode_charset(after[draw:draw + 2048]), ref["samples"],
                                  f"phase{phase} all8192 final canvas samples")
                core.assert_bytes(after[opposite:opposite + 2048], buffer_images[opposite],
                                  f"phase{phase} overlay preserved displayed charset")
                for shift in range(4):
                    expected = bytes(value << (2 * shift) for value in ref["texture"])
                    core.assert_bytes(after[0xe000 + 256 * shift:0xe100 + 256 * shift], expected,
                                      f"phase{phase} runtime plasma shift{2 * shift}")
                expected_screen = bytearray(1000)
                for row in range(16):
                    for column in range(16):
                        expected_screen[(row + 4) * 40 + column + 12] = column * 16 + row
                core.assert_bytes(after[0x0400:0x07e8], expected_screen, "actual column-major screen mapping")
                vic = monitor.memory(output / f"vic-{index:02d}.bin", 0xd000, 0xd03f)
                assert (vic[0x11] & 0x7f) == 0x1b and (vic[0x16] & 0x3f) == 0x18
                assert (vic[0x18] & 0xfe) == (0x10 | (draw // 1024))
                assert vic[0x15] == 0 and tuple(value & 15 for value in vic[0x20:0x24]) == (0, 0, 6, 3)
                if color_ram is None:
                    color_ram = monitor.memory(output / "color-ram.bin", 0xd800, 0xdbe7)
                    expected_colors = bytearray(1000)
                    for row in range(16):
                        for column in range(16):
                            expected_colors[(row + 4) * 40 + column + 12] = 9
                    core.assert_bytes(bytes(value & 15 for value in color_ram), expected_colors, "canvas color RAM")
                assert 0 <= published[1] < 35, (index, "publication outside upper border", published)
                record = dict(phase=phase, charset=draw, clock=published[3], raster=list(published[1:3]),
                              boundary_clock=boundary_state[3], base_clock=base_state[3],
                              texture_visible=bool(ref["visible"][4]), textured_samples=ref["textured_samples"],
                              black_texture_samples=ref["black_texture_samples"],
                              base_sha256=hashlib.sha256(base_ram[draw:draw + 2048]).hexdigest(),
                              charset_sha256=hashlib.sha256(after[draw:draw + 2048]).hexdigest())
                if index:
                    previous_phase = (phase - 1) % 64
                    image_path = output / f"visible-phase-{previous_phase:02d}-{index:02d}.png"
                    monitor.run(f'screenshot "{image_path}" 2')
                    image = Image.open(image_path).convert("RGB")
                    expected = expected_image(refs[previous_phase], image.size, palette)
                    difference = ImageChops.difference(image, expected)
                    if difference.getbbox():
                        expected.save(output / "expected-failed.png")
                        difference.save(output / "difference-failed.png")
                        raise AssertionError((index, "full native screenshot pixels", difference.getbbox()))
                    images.append(image)
                    record["screenshot"] = image_path.name
                observations.append(record)
                buffer_images[draw] = after[draw:draw + 2048]
                buffer_bounds[draw] = current
                seen_buffers.add(draw)
        assert seen_buffers == {0x2000, 0x2800}
        assert sources() == frozen_sources and sha(program) == program_hash, "Inputs changed during native proof"
        intervals, fields, groups = [], [], {True: [], False: []}
        for first, last in zip(observations, observations[1:]):
            elapsed = last["clock"] - first["clock"]
            beam_delta = 63 * (last["raster"][0] - first["raster"][0]) + last["raster"][1] - first["raster"][1]
            assert elapsed > 0 and (elapsed - beam_delta) % 19656 == 0
            intervals.append(elapsed)
            fields.append((elapsed - beam_delta) // 19656)
            groups[last["texture_visible"]].append(elapsed)
        durations = [max(10, round(value / 985248 * 100) * 10) for value in intervals[:64]]
        gif = output / "xor-hybrid-cube.gif"
        save_gif(images[:64], gif, durations)
        precision_summary = {key: (min(row[key] for row in metrics) if key.endswith("_min") or
                                   "_min_degrees" in key else max(row[key] for row in metrics))
                             for key in metrics[0]}
        report = dict(status="pass", program_sha256=program_hash, source_sha256=frozen_sources,
                      prg_load_address=load_address, prg_loaded_end_exclusive=loaded_end,
                      startup_relocations=[{key: value for key, value in item.items() if key != "data"}
                                           for item in relocations],
                      presentations=PRESENTATIONS, poses=64, canvas=[WIDTH, HEIGHT], physical_sample=[2, 1],
                      complete_final_samples=PRESENTATIONS * WIDTH * HEIGHT,
                      complete_solid_base_samples=PRESENTATIONS * WIDTH * HEIGHT,
                      complete_native_images=len(images), decoded_marker_operands=sum(map(len, prefix.operands.values())),
                      geometry=precision_summary, live_geometry=True, stored_projected_poses=False,
                      mean_updates_per_second=985248 / (sum(intervals) / len(intervals)),
                      cycle_updates_per_second=985248 * 64 / sum(intervals[:64]),
                      pal_fields_per_update=[min(fields), max(fields)],
                      visibility_timing={"visible" if visible else "hidden":
                          dict(jobs=len(values), updates_per_second=985248 / (sum(values) / len(values)))
                          for visible, values in groups.items() if values},
                      coverage=dict(edge_contract="vertical crossings at ceil(y(x)), left-X inclusive/right-X exclusive",
                                    visible_texture_phases=sum(row["visible"][4] for row in refs),
                                    texture_mask_samples=sum(row["textured_samples"] for row in refs),
                                    intentional_black_texture_samples=sum(row["black_texture_samples"] for row in refs),
                                    silhouette_gaps=0, overlapping_face_samples=0, stale_outside_samples=0,
                                    raw_selector3_mask_mismatches=0),
                      shader=dict(mapping="separable floors of the canonical first-three-corner signed-Q8 plane",
                                  max_periodic_uv_error_texels_per_axis=1,
                                  changed_colors_vs_exact=sum(row["changed_texture_colors"] for row in refs),
                                  changed_uv_samples=sum(row["changed_uv_samples"] for row in refs),
                                  sampled_texture_addresses=len(set().union(*(row["sampled_texture_addresses"] for row in refs)))),
                      native_resources=dict(machine="PAL C64", speed_percent=100, warp=False,
                                            helper="verify-filled.py machine / verify.py vice_command"),
                      gif=gif.name, animation_duration_ms=durations, observations=observations,
                      limits=["The one-texel periodic UV bound is against the declared Q8 plane from the first three rounded corners, not ideal physical UV.",
                              "Each complete image is published in the next upper border; variable work causes variable angular speed.",
                              "Digital VICE output is verified; physical C64 and analog display output are not covered."])
        (output / "proof.json").write_text(json.dumps(report, indent=2) + "\n")
        shutil.copy2(gif, HERE / "build/xor-hybrid-cube.gif")
        status.write_text(json.dumps(dict(status="pass", output=str(output), program_sha256=program_hash)) + "\n")
        print(json.dumps({key: value for key, value in report.items()
                          if key not in ("source_sha256", "observations", "animation_duration_ms")}, indent=2))
    except BaseException as error:
        status.write_text(json.dumps(dict(status="fail", output=str(output), error=repr(error))) + "\n")
        raise


if __name__ == "__main__":
    main()
