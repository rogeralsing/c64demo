#!/usr/bin/env python3
"""Inspect F1's captured active polyhedron, face patterns and culling.

Reads saved native RAM only; executes the original isolated orientation helper
in flat py65 RAM. No VICE process, disk transport, IRQ or VIC emulation.
"""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from py65.devices.mpu6502 import MPU

from f1_inventory import execute, reference
from n2_math import product


REPOSITORY = Path(__file__).resolve().parents[2]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def word(memory, address):
    return memory[address] | memory[address + 1] << 8


def subtract(a, b):
    return tuple(x - y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPOSITORY / "build/research/tower-power")
    parser.add_argument("--ram", type=Path, help="Saved raw 64KB native RAM; defaults to f1-live-01/ram-f1-running.bin")
    args = parser.parse_args()
    root = args.root.resolve()
    path = args.ram or root / "f1-live-01/ram-f1-running.bin"
    memory = path.read_bytes()
    assert len(memory) == 65536
    original = (root / "static/unpacked/side2-f1.memory.bin").read_bytes()
    output = root / "static/f1"
    output.mkdir(parents=True, exist_ok=True)
    position, axes = 0x29D7, []
    for axis in range(3):
        end = original.index(255, position)
        axes.append(original[position:end])
        position = end + 1
    assert [len(axis) for axis in axes] == [39, 39, 39] and position == 0x2A4F
    for source, destination in zip(axes, (0xFEC0, 0xFE80, 0xFF00)):
        assert memory[destination:destination + 39] == source
    points = [tuple(value - 128 for value in point) for point in zip(*axes)]
    assert memory[0xFF27:0xFF29] == bytes((255, 0)) and memory[3] == 40
    seeds = list(memory[0x47C0:0x4800])
    assert memory[0x8000:0xC000] == bytes(product(seed, coordinate) for seed in seeds for coordinate in range(256))
    angles = list(memory[0x303E:0x3041])
    zoom_offset = word(memory, 0x35E2) - 0x4800
    transformed_points = list(zip(memory[0xFEC0:0xFEE8], memory[0xFE80:0xFEA8], memory[0xFF00:0xFF28]))
    expected = reference(seeds, transformed_points, angles, zoom_offset)
    transformed = bytearray(memory)
    transform_steps = execute(transformed, 0x3484, 0x3484, 0x3642)
    for i, (horizontal, vertical, _) in enumerate(expected):
        assert memory[0xFF40 + i] == transformed[0xFF40 + i] == horizontal
        assert memory[0xFF80 + i] == transformed[0xFF80 + i] == vertical
    # Active consumers, rather than the stale earlier cube tables, select these.
    face_tables = [word(memory, a) for a in (0x279D, 0x27B0, 0x27BF)]
    edge_tables = [word(memory, a) for a in (0x2829, 0x283C)]
    incidence = word(memory, 0x27EF)
    assert face_tables == [0x2AE4, 0x2AFF, 0x2B19]
    assert edge_tables == [0x2A4F, 0x2A9A] and incidence == 0x2B33
    count = memory.index(255, edge_tables[0]) - edge_tables[0]
    assert count == 74
    edges = list(zip(memory[edge_tables[0]:edge_tables[0] + count], memory[edge_tables[1]:edge_tables[1] + count]))
    face_count = memory.index(255, face_tables[0]) - face_tables[0]
    assert face_count == 26
    triangles = list(zip(*(memory[a:a + face_count] for a in face_tables)))
    assert memory[0x27D5:0x27D9] == bytes((0xC9, 0x00, 0xD0, 0x0F)), "No culling bypass"
    faces, geometric_incidence = [], Counter()
    cpu_steps = 0
    visible = []
    for index, triangle in enumerate(triangles):
        start = incidence
        end = start + memory[start]
        color = memory[start + 1]
        cursor = start + 2
        contributions = []
        changes = []
        while cursor < end:
            edge = memory[cursor]
            cursor += 1
            if edge == 0x99:
                color = memory[cursor]
                cursor += 1
                changes.append(color)
                continue
            assert edge < len(edges)
            contributions.append((edge, color))
        incidence = end
        geometric = [edge for edge, _ in contributions if edge < 48]
        corners = set(vertex for edge in geometric for vertex in edges[edge])
        assert len(corners) in (3, 4)
        assert set(triangle) <= corners
        assert all(sum(vertex in edges[edge] for edge in geometric) == 2 for vertex in corners)
        geometric_incidence.update(geometric)
        origin = points[triangle[0]]
        normal = cross(subtract(points[triangle[1]], origin), subtract(points[triangle[2]], origin))
        assert normal != (0, 0, 0)
        distances = [dot(normal, subtract(point, origin)) for point in points[:24]]
        assert min(distances) == 0 and max(distances) > 0, "Inward convex supporting plane"
        assert all(dot(normal, subtract(points[vertex], origin)) == 0
                   for edge, _ in contributions for vertex in edges[edge]), "Every pattern edge coplanar with owner"
        parity = defaultdict(int)
        for edge, mask in contributions:
            for vertex in edges[edge]:
                parity[vertex] ^= mask
        assert all(value == 0 for value in parity.values()), "Colored boundary graph must close at every vertex"
        probe = bytearray(memory)
        # Original helper takes projected corners in six self-modified immediates.
        for vertex, x_address, y_address in zip(triangle, (0x289B, 0x289E, 0x28BF), (0x28AD, 0x28B0, 0x28D7)):
            probe[x_address] = memory[0xFF40 + vertex]
            probe[y_address] = memory[0xFF80 + vertex]
        # Run exactly the original helper; recover A via an unchanged final path.
        cpu = MPU(memory=probe, pc=0x2898)
        cpu.p = cpu.UNUSED | cpu.INTERRUPT
        cpu.sp = 255
        cpu.stPushWord(0x02FE)
        steps = 0
        while cpu.pc != 0x02FF:
            assert 0x2898 <= cpu.pc < 0x2953 and steps < 10_000
            cpu.step()
            steps += 1
        assert cpu.sp == 255 and cpu.a in (0, 255)
        cpu_steps += steps
        projected = [(memory[0xFF40 + vertex], memory[0xFF80 + vertex]) for vertex in triangle]
        a, b, c = projected
        area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if cpu.a:
            visible.append(index)
        faces.append({"index": index, "record_address": start, "cull_triangle": triangle,
                      "geometric_corners": sorted(corners), "geometric_edges": geometric,
                      "contributions_edge_mask": contributions, "mask_changes": changes,
                      "inward_normal": normal, "projected_twice_area": area,
                      "original_cull_result": cpu.a})
    assert len(geometric_incidence) == 48 and set(geometric_incidence.values()) == {2}
    assert Counter(len(face["geometric_corners"]) for face in faces) == {3: 8, 4: 18}
    # Helper returns FF for this winding sign. Degenerate projected faces may
    # have their own tie rule; preserve results rather than silently recoding it.
    nondegenerate = [face for face in faces if face["projected_twice_area"]]
    assert all((face["original_cull_result"] != 0) == (face["projected_twice_area"] > 0)
               for face in nondegenerate)
    report = {
        "pass": True, "scope": "Active saved F1 native geometry and original isolated culling helper; not full rendering execution",
        "script_sha256": digest(Path(__file__).read_bytes()), "native_ram_file": str(path), "native_ram_sha256": digest(memory),
        "original_memory_sha256": digest(original), "source_coordinates_address": 0x29D7,
        "native_39_coordinates_match_source": True, "points_signed": points,
        "native_product_table_matches_formula": True, "native_pose_angles": angles,
        "native_pose_zoom_offset": zoom_offset, "native_transform_matches_cpu_and_host": True,
        "processed_records_including_ff_extra": 40, "transform_original_instructions": transform_steps,
        "base_vertices": 24, "coplanar_pattern_vertices": 15,
        "geometric_edges": 48, "pattern_edges": 26, "all_edges": edges,
        "faces": faces, "face_count": 26, "geometric_face_sizes": {"triangles": 8, "quads": 18},
        "euler_characteristic": 24 - 48 + 26, "all_base_faces_convex_supporting_planes": True,
        "all_pattern_edges_coplanar": True, "all_face_bitplanes_close": True,
        "active_face_tables": face_tables, "active_edge_tables": edge_tables, "active_incidence_table": 0x2B33,
        "original_cull_visible_faces": visible, "original_cull_hidden_faces": [i for i in range(26) if i not in visible],
        "cull_nondegenerate_matches_exact_positive_winding": True,
        "cull_zero_area_faces": [face["index"] for face in faces if not face["projected_twice_area"]],
        "cull_original_instructions": cpu_steps, "phase_counter_2551": memory[0x2551],
        "stale_morph_point_count_3031": memory[0x3031],
        "raster_mode_switch_source": {"cube_irq": 0x3367, "cube_raster": 114,
                                      "cube_d011": 0x13, "cube_dd00": 0x97, "cube_d018": 0x13},
        "limitations": ["Original culling helper tested on this saved pose only, not all rotations",
                        "Raw bank RAM does not establish physical Color RAM or an arbitrary raster phase",
                        "Native full-entry payload equality was not captured in this F1 run"],
    }
    (output / "native-geometry.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key not in ("points_signed", "all_edges", "faces")}, indent=2))


if __name__ == "__main__":
    main()
