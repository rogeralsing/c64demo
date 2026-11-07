#!/usr/bin/env python3
"""Reconstruct F1 cube topology, model records, projection and loader route.

Validated unpacked bytes plus original 6502 table/transform execution in flat
py65 RAM. No VICE, disk transport, renderer changes, UV texture, or native
frame-rate claim. The independent arithmetic reference reuses N2's already
checked product/selector definitions, not CPU-produced expected coordinates.
"""

import argparse
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path

from py65.devices.mpu6502 import MPU

from n2_math import arithmetic, product, selector


REPOSITORY = Path(__file__).resolve().parents[2]
STOP = 0x02FF


def digest(data):
    return hashlib.sha256(data).hexdigest()


def execute(memory, entry, low, high, end=STOP):
    cpu = MPU(memory=memory, pc=entry)
    cpu.p = cpu.UNUSED | cpu.INTERRUPT
    cpu.sp = 255
    if end == STOP:
        cpu.stPushWord(STOP - 1)
    steps = 0
    while cpu.pc != end:
        assert low <= cpu.pc < high, hex(cpu.pc)
        assert steps < 500_000
        cpu.step()
        steps += 1
    assert cpu.sp == 255
    return steps


def model_record(memory, address, topology):
    position = address
    edges = None
    if topology:
        count = memory[position]
        position += 1
        edges = list(zip(memory[position:position + count],
                         memory[position + count:position + count * 2],
                         memory[position + count * 2:position + count * 3]))
        position += count * 3
    count = memory[position]
    position += 1
    stride = count + int(topology)
    axes = [list(memory[position + axis * stride:position + (axis + 1) * stride])
            for axis in range(3)]
    if topology:
        assert all(values[-1] == 255 for values in axes)
    return {"address": address, "kind": "topology-and-coordinates" if topology else "coordinate-morph-target",
            "point_count": count, "points_biased": list(zip(*[values[:count] for values in axes])),
            "edges_with_masks": edges, "end_exclusive": position + stride * 3}


def reference(seeds, points, angles, zoom_offset):
    carry = 0
    result = []
    for source_a, source_b, source_c in points:
        x, y = source_c, source_b
        for plane, angle in enumerate(angles):
            co_page, co_sub = selector(angle)
            si_page, si_sub = selector((angle + 64) & 255)
            a, carry = arithmetic(128, product(seeds[si_page], x), carry, si_sub)
            u, carry = arithmetic(a, product(seeds[co_page], y), carry, co_sub)
            a, carry = arithmetic(128, product(seeds[co_page], x), carry, co_sub)
            v, carry = arithmetic(a, product(seeds[si_page], y), carry, not si_sub)
            if plane == 0:
                saved = u
                x, y = source_a, v
            elif plane == 1:
                depth = u
                # Exact value description matching every literal table byte.
                factor = math.ceil(76500 / (300 + zoom_offset + depth) - 0.5)
                projection_page = min(63, math.floor(math.acos(factor / 255) * 128 / math.pi))
                x, y = saved, v
            else:
                vertical = (64 + product(seeds[projection_page], v)) & 255
                horizontal_pre_shift = (64 + product(seeds[projection_page], u)) & 255
                horizontal = horizontal_pre_shift >> 1
                carry = horizontal_pre_shift & 1
                result.append([horizontal, vertical, depth])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPOSITORY / "build/research/tower-power")
    args = parser.parse_args()
    root = args.root.resolve()
    prefix = root / "static/unpacked/side2-f1"
    initial = bytearray(prefix.with_suffix(".memory.bin").read_bytes())
    known = prefix.with_suffix(".known.bin").read_bytes()
    assert all(known[a] for lo, hi in [(0x2534, 0x2566), (0x2953, 0x3233),
                                     (0x3438, 0x3642), (0x47C0, 0x4C00), (0x4F00, 0x5000)]
               for a in range(lo, hi))
    output = root / "static/f1"
    output.mkdir(parents=True, exist_ok=True)
    vertices = list(zip(initial[0x296C:0x2974], initial[0x2975:0x297D], initial[0x297E:0x2986]))
    assert set(vertices) == {(x, y, z) for x in (79, 177) for y in (79, 177) for z in (79, 177)}
    edges = list(zip(initial[0x2987:0x2993], initial[0x2994:0x29A0]))
    assert len(set(frozenset(edge) for edge in edges)) == 12
    assert all(sum(vertices[a][axis] != vertices[b][axis] for axis in range(3)) == 1 for a, b in edges)
    triangles = list(zip(initial[0x29A0:0x29A6], initial[0x29A7:0x29AD], initial[0x29AD:0x29B3]))
    faces, position = [], 0x29B3
    for triangle in triangles:
        size, mask = initial[position:position + 2]
        assert size == 6
        edge_ids = list(initial[position + 2:position + size])
        corners = set(vertex for edge in edge_ids for vertex in edges[edge])
        assert len(corners) == 4 and set(triangle) < corners
        assert sum(len({vertices[vertex][axis] for vertex in corners}) == 1 for axis in range(3)) == 1
        assert all(sum(vertex in edges[edge] for edge in edge_ids) == 2 for vertex in corners)
        faces.append({"record_address": position, "cull_triangle": triangle,
                      "edge_ids": edge_ids, "corners": sorted(corners), "mask": mask})
        position += size
    assert len({tuple(face["corners"]) for face in faces}) == 6
    assert all(sum(edge in face["edge_ids"] for face in faces) == 2 for edge in range(12))
    models = [model_record(initial, initial[0x3032 + i] | initial[0x3038 + i] << 8, i in (0, 2))
              for i in range(6)]
    assert [model["point_count"] for model in models] == [12, 12, 24, 24, 24, 24]
    assert all(models[i]["end_exclusive"] == models[i + 1]["address"] for i in range(5))
    seeds = list(initial[0x47C0:0x4800])
    assert seeds == [math.floor(255 * math.cos((i + 0.5) * math.pi / 128) + 0.5) for i in range(64)]
    reciprocal = bytes(math.ceil(76500 / (300 + i) - 0.5) for i in range(1024))
    inverse_cos = bytes(128 + min(63, math.floor(math.acos(i / 255) * 128 / math.pi)) for i in range(256))
    assert initial[0x4800:0x4C00] == reciprocal
    assert initial[0x4F00:0x5000] == inverse_cos
    generated = bytearray(initial)
    total_steps = execute(generated, 0x3438, 0x3438, 0x3484)
    assert generated[0x8000:0xC000] == bytes(product(seed, coordinate) for seed in seeds for coordinate in range(256))
    # Original phase code copies the cube, including its FF sentinels.
    total_steps += execute(generated, 0x2534, 0x2534, 0x254D, 0x254D)
    points = list(zip(generated[0xFEC0:0xFEC9], generated[0xFE80:0xFE89], generated[0xFF00:0xFF09]))
    assert points[:8] == vertices and points[8] == (255, 255, 255)
    patterned = bytearray(generated)
    total_steps += execute(patterned, 0x2556, 0x2556, 0x2566, 0x2566)
    pattern_masks = [patterned[face["record_address"] + 1] for face in faces]
    assert pattern_masks == [0x9D, 0x9D, 0x67, 0x55, 0x67, 0x55]
    poses = sorted({(a, 0, 0) for a in range(256)} | {(0, a, 0) for a in range(256)} |
                   {(0, 0, a) for a in range(256)} |
                   {((7 * a) & 255, (2 * a) & 255, (5 * a) & 255) for a in range(256)})
    pose_checks = 0
    for offset in (0, 27, 256, 512, 768):
        for angles in poses:
            memory = bytearray(generated)
            memory[0x303E:0x3041] = bytes(angles)
            memory[0x35E2:0x35E4] = (0x4800 + offset).to_bytes(2, "little")
            total_steps += execute(memory, 0x3484, 0x3484, 0x3642)
            wanted = reference(seeds, points, angles, offset)
            assert memory[3] == 9
            for vertex, (horizontal, vertical, _) in enumerate(wanted):
                assert memory[0xFF40 + vertex] == horizontal, (offset, angles, vertex, "horizontal")
                assert memory[0xFF80 + vertex] == vertical, (offset, angles, vertex, "vertical")
            pose_checks += 1
    route = [
        ("c1", 0x5034, 0x50AF, 0x50D0, 0x5043, "M2.*"),
        ("c1", 0x5034, 0x50AF, 0x50D4, 0x508C, "C7.*"),
        ("c7", 0x8740, 0x87AA, 0x8B77, 0x8760, "C2.*"),
        ("c2", 0x5836, 0x5B28, 0x669D, 0x59BC, "D1.*"),
        ("d1", 0x882A, 0x8B1E, 0x95BF, 0x89FE, "E1.*"),
        ("e1", 0x5831, 0x5982, 0x654B, 0x5961, "F1.*"),
    ]
    requests = []
    for name, entry, irq, literal, call_pc, filename in route:
        part = (root / f"static/unpacked/side2-{name}.memory.bin").read_bytes()
        assert part[literal:literal + 4] == filename.encode("ascii")
        assert part[call_pc:call_pc + 3] == bytes((0x20, 0x10, 0xC0))
        assert int.from_bytes(part[0xC2F0:0xC2F2], "little") == entry
        assert int.from_bytes(part[0xC2F2:0xC2F4], "little") == irq
        requests.append({"part": name, "memory_sha256": digest(part), "entry": entry, "irq": irq,
                         "filename_address": literal, "request_pc": call_pc, "request": filename})
    report = {
        "pass": True, "scope": "Static validated F1 geometry/consumers plus original transform in flat py65 RAM; not native identification",
        "script_sha256": digest(Path(__file__).read_bytes()), "input_memory_sha256": digest(initial),
        "py65_version": importlib.metadata.version("py65"), "entry": 0x2194, "irq": 0x3C29,
        "boot_selector": {"basic_line": 1, "sys_decimal": 9731, "machine_entry": 0x2603},
        "original_loader_requests": requests, "cube_vertices_biased": vertices,
        "cube_edges": edges, "cube_faces": faces, "no_face_diagonal_edges": True,
        "cube_pattern_masks_after_counter96": pattern_masks,
        "cube_final_pattern_bytes_ff_seed": [255 ^ mask for mask in pattern_masks],
        "model_catalog": models, "model_sequence_bytes_3044": list(initial[0x3044:0x3051]),
        "reciprocal_formula": "ceil(76500/(300+i)-0.5),i=0..1023",
        "inverse_cos_formula": "128+min(63,floor(acos(i/255)*128/pi)),i=0..255",
        "product_table_sha256": digest(generated[0x8000:0xC000]),
        "transform_poses_checked": pose_checks, "unique_angle_triples": len(poses),
        "zoom_offsets_checked": [0, 27, 256, 512, 768],
        "transformed_records_checked": pose_checks * len(points), "total_original_instructions": total_steps,
        "limitations": ["Finite sampled angles/zoom offsets, not all possible runtime states",
                        "Pattern interpretation is packed-pixel mask behavior, not native screenshot matching",
                        "No VIC, IRQ, IEC, full drawing, or native timing proof"],
    }
    (output / "inventory.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ("model_catalog", "cube_vertices_biased", "cube_edges", "cube_faces", "original_loader_requests")}, indent=2))


if __name__ == "__main__":
    main()
