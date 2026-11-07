#!/usr/bin/env python3
"""Check N2's product/rotation formulas against original 6502 instructions.

Flat py65 RAM only: no disk, VIC, SID, interrupts, native timing, or visual
identification. Inputs are the independently validated unpacked N2 payload.
The host formulas never invoke the CPU routine to obtain expected results.
"""

import argparse
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path

from py65.devices.mpu6502 import MPU


REPOSITORY = Path(__file__).resolve().parents[2]
STOP = 0x02FF
SMC = [0x327E, 0x3281, 0x3289, 0x328C,
       0x3294, 0x3297, 0x32AA, 0x32AD,
       0x32B5, 0x32B8, 0x32C0, 0x32C3]
OUTPUTS = [(0x32F3, 0x3325), (0x3357, 0x3389), (0x33BB, 0x33ED)]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def execute(memory, entry, low, high, limit):
    """Original instructions only; synthetic caller supplies one normal RTS."""
    cpu = MPU(memory=memory, pc=entry)
    cpu.p = cpu.UNUSED | cpu.INTERRUPT
    cpu.sp = 255
    cpu.stPushWord(STOP - 1)
    steps = 0
    while cpu.pc != STOP:
        assert low <= cpu.pc <= high, f"Unexpected PC ${cpu.pc:04X}"
        assert steps < limit, f"Instruction limit at ${cpu.pc:04X}"
        cpu.step()
        steps += 1
    assert cpu.sp == 255
    return steps, cpu.processorCycles


def product(seed, coordinate):
    # Literal closed form of both generator loops; return an encoded byte.
    if coordinate >= 128:
        return ((coordinate - 127) * seed // 256) & 255
    return (-1 - (128 - coordinate) * seed // 256) & 255


def selector(angle):
    """Quarter-wave magnitude page and signed operation for cos(angle)."""
    page = angle & 63
    if angle & 64:
        page ^= 63
    subtract = (angle & 192) in (64, 128)
    return page, subtract


def arithmetic(a, b, carry, subtract):
    # Binary NMOS ADC/SBC, including carry between otherwise separate outputs.
    total = a + (255 - b if subtract else b) + carry
    return total & 255, int(total > 255)


def reference(seeds, points, angles):
    selections = [selector(angle) for angle in angles]
    quadratures = [selector((angle + 64) & 255) for angle in angles]
    carry = 0  # Last ADC #$80 in the original patcher cannot overflow.
    result = []
    for source_a, source_b, source_c in points:
        # The original source coordinate order is Y=A, immediate X=C, B saved.
        x, y = source_c, source_a
        pair = []
        for step, (co, si) in enumerate(zip(selections, quadratures)):
            co_page, co_sub = co
            si_page, si_sub = si  # cos(a+64) = -sin(a)
            a, carry = arithmetic(128, product(seeds[si_page], x), carry, si_sub)
            u, carry = arithmetic(a, product(seeds[co_page], y), carry, co_sub)
            if step == 1:
                depth = u >> 1
                carry = u & 1  # LSR occurs before this plane's second output.
            a, carry = arithmetic(128, product(seeds[co_page], x), carry, co_sub)
            v, carry = arithmetic(a, product(seeds[si_page], y), carry, not si_sub)
            if step == 0:
                # Stage one stores u for final plane rotation, and uses v now.
                saved = u
                x, y = source_b, v
            elif step == 1:
                x, y = saved, v
            else:
                horizontal = u >> 2
                vertical = v >> 1
                # CPU shifts v once, then u twice: final carry is u bit 1.
                carry = (u >> 1) & 1
                pair = [horizontal, vertical, depth]
        result.append(pair)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPOSITORY / "build/research/tower-power")
    args = parser.parse_args()
    root = args.root.resolve()
    prefix = root / "static/unpacked/side2-n2"
    initial = bytearray(prefix.with_suffix(".memory.bin").read_bytes())
    known = prefix.with_suffix(".known.bin").read_bytes()
    output = root / "static/n2-math"
    output.mkdir(parents=True, exist_ok=True)
    assert all(known[a] for a in range(0x30F4, 0x32F2))
    seeds = list(initial[0x47C0:0x4800])
    seed_formula = [math.floor(255 * math.cos((i + 0.5) * math.pi / 128) + 0.5)
                    for i in range(64)]
    assert seeds == seed_formula
    for angle in range(256):
        page, negative = selector(angle)
        signed_seed = -seeds[page] if negative else seeds[page]
        assert signed_seed == math.floor(255 * math.cos((angle + 0.5) * math.pi / 128) + 0.5)
    generated = bytearray(initial)
    generator_steps, _ = execute(generated, 0x30F4, 0x30F4, 0x313F, 500_000)
    expected_table = bytes(product(seed, value) for seed in seeds for value in range(256))
    assert generated[0x8000:0xC000] == expected_table
    (output / "product-table-8000.bin").write_bytes(expected_table)
    points = []
    i = 0
    while initial[0x46A0 + i]:
        points.append(tuple(initial[address + i] for address in (0x4600, 0x4650, 0x46A0)))
        i += 1
        assert i < 50
    edge_indices = set(initial[0x25E2:0x25E2 + 150]) | set(initial[0x2678:0x2678 + 150])
    assert edge_indices == set(range(40)) | set(range(50, 90))
    poses = sorted({(a, 0, 0) for a in range(256)} |
                   {(0, a, 0) for a in range(256)} |
                   {(0, 0, a) for a in range(256)} |
                   {((7 * a) & 255, (6 * a) & 255, (3 * a) & 255) for a in range(256)})
    total_steps = generator_steps
    minima, maxima = [255] * 3, [0] * 3
    samples = []
    for angles in poses:
        memory = bytearray(generated)
        memory[0x2A23:0x2A26] = bytes(angles)
        steps, _ = execute(memory, 0x3140, 0x3140, 0x32F1, 100_000)
        total_steps += steps
        assert memory[3] == len(points)
        wanted = reference(seeds, points, angles)
        for point, values in enumerate(wanted):
            for axis, ((base, mirror), value) in enumerate(zip(OUTPUTS, values)):
                assert memory[base + point] == value, (angles, point, axis, memory[base + point], value)
                mask = 63 if axis == 0 else 127
                assert memory[mirror + point] == value ^ mask
                if point < 40:
                    minima[axis] = min(minima[axis], value, value ^ mask)
                    maxima[axis] = max(maxima[axis], value, value ^ mask)
        if angles in ((0, 0, 0), (64, 0, 0), (0, 64, 0), (0, 0, 64)):
            samples.append({"angles": angles, "first_point_outputs": wanted[0],
                            "patched_opcodes": [memory[a] for a in SMC]})
    report = {
        "pass": True,
        "scope": "Original product generator and original self-modifying transform in flat py65 RAM; no IO or native timing",
        "memory_sha256": digest(initial), "script_sha256": digest(Path(__file__).read_bytes()),
        "py65_version": importlib.metadata.version("py65"),
        "product_generator_entry": 0x30F4, "transform_entry": 0x3140,
        "product_table_range_end_exclusive": [0x8000, 0xC000],
        "product_table_sha256": digest(expected_table),
        "seed_values": seeds, "seed_formula": "floor(255*cos((i+0.5)*pi/128)+0.5)",
        "all_product_cells_checked": 64 * 256,
        "product_formula": "b>=128: floor((b-127)*s/256); b<128: -1-floor((128-b)*s/256), modulo256",
        "source_points_processed": len(points), "mesh_points_per_half": 40,
        "extra_point_not_used_by_default_edges": {"index": 40, "biased_coordinates": points[40]},
        "edge_index_set": sorted(edge_indices), "output_mirror_index_delta": 50,
        "output_bases": OUTPUTS, "poses_checked": len(poses),
        "transformed_point_pairs_checked": len(poses) * len(points),
        "total_original_instructions": total_steps,
        "mesh_sampled_min_h_v_depth": minima, "mesh_sampled_max_h_v_depth": maxima,
        "initial_angle_bytes": list(initial[0x2A23:0x2A26]),
        "initial_angle_increments": list(initial[0x2A26:0x2A29]),
        "samples": samples,
        "limitations": ["Pose coverage is named finite sampling, not all 256^3 angle triples",
                        "No full renderer, culling, topology adjacency, native visual identity, or frame-rate proof"],
    }
    (output / "math-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ("seed_values", "edge_index_set", "samples")}, indent=2))


if __name__ == "__main__":
    main()
