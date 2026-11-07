#!/usr/bin/env python3
"""Regenerate Tower Power line kernels and check their crossing/cycle rules.

Original 6502 generators and line routines execute in flat py65 RAM. No VICE,
VIC stalls, IRQ, disk IO or production renderer modifications. Expected marker
rows come from closed integer formulas, not the CPU trace.
"""

import argparse
import hashlib
import importlib.metadata
import json
from collections import Counter
from pathlib import Path

from py65.devices.mpu6502 import MPU


REPOSITORY = Path(__file__).resolve().parents[2]
STOP = 0x02FF
KERNELS = [(0x5000, 0x5640), (0x5700, 0x5D40), (0x5E00, 0x6240), (0x6300, 0x6740)]
CONFIG = {
    "n2": {"generator": 0x341F, "generator_range": (0x341F, 0x3605),
           "mask": 0x3605, "draw": 0x3661, "draw_range": (0x3660, 0x3745),
           "marker": 0xF700, "inputs": [0xEC, 0xED, 0xEE, 0xEF],
           "native": "n2-live-01/ram-sphere-01.bin"},
    "f1": {"generator": 0x3643, "generator_range": (0x3643, 0x3877),
           "mask": 0x3877, "draw": 0x38D5, "draw_range": (0x38D4, 0x39DA),
           "marker": 0x3F00, "inputs": [0x3EE7, 0x3EE8, 0x3EE9, 0x3EEA],
           "native": "f1-live-01/ram-f1-running.bin"},
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def cpu_call(memory, entry, allowed, accumulator=0, collect=False):
    cpu = MPU(memory=memory, pc=entry)
    cpu.a = accumulator
    cpu.p = cpu.UNUSED | cpu.INTERRUPT
    cpu.sp = 255
    cpu.stPushWord(STOP - 1)
    steps = 0
    categories = Counter()
    opcode_counts = Counter()
    while cpu.pc != STOP:
        assert any(lo <= cpu.pc < hi for lo, hi in allowed), hex(cpu.pc)
        assert steps < 1_000_000, hex(cpu.pc)
        pc, opcode = cpu.pc, memory[cpu.pc]
        in_kernel = any(lo <= pc < hi for lo, hi in KERNELS)
        before = cpu.processorCycles
        cpu.step()
        if collect:
            kind = "kernel" if in_kernel else "setup_restore"
            cycles = cpu.processorCycles - before
            categories[kind] += cycles
            if in_kernel:
                opcode_counts[(opcode, cycles)] += 1
        steps += 1
    assert cpu.sp == 255
    return {"instructions": steps, "cycles": cpu.processorCycles,
            "categories": dict(categories), "kernel_opcode_cycles": [[op, cycles, count] for (op, cycles), count in sorted(opcode_counts.items())]}


def crossing_rows(x0, y0, x1, y1):
    if x0 == x1:
        return []
    if x1 < x0:
        x0, x1, y0, y1 = x1, x0, y1, y0
    width, height = x1 - x0, abs(y1 - y0)
    denominator, numerator = width + 1, height + 1
    sign = 1 if y1 >= y0 else -1
    result = []
    for j in range(width):
        if height >= width:
            offset = (j * numerator + denominator - 1) // denominator
        else:
            offset = max(0, (j * numerator - 1) // denominator)
        result.append((x0 + j, y0 + sign * offset))
    return result


def run_line(canonical, config, endpoints, collect=False):
    memory = bytearray(canonical)
    marker = config["marker"]
    memory[marker:marker + 2048] = bytes(2048)
    for address, value in zip(config["inputs"], (endpoints[0], endpoints[2], endpoints[1], endpoints[3])):
        memory[address] = value
    stats = cpu_call(memory, config["draw"], [config["draw_range"], *KERNELS], collect=collect)
    wanted = bytearray(2048)
    rows = crossing_rows(*endpoints)
    for x, y in rows:
        assert 0 <= x < 64 and 0 <= y < 128, endpoints
        wanted[(x // 4) * 128 + y] ^= 0xC0 >> (2 * (x & 3))
    actual = memory[marker:marker + 2048]
    assert actual == wanted, (endpoints, [(i, a, b) for i, (a, b) in enumerate(zip(actual, wanted)) if a != b][:12])
    assert all(memory[lo:hi] == canonical[lo:hi] for lo, hi in KERNELS), "Endpoint patches must restore"
    stats["endpoints"] = endpoints
    stats["logical_x_samples"] = len(rows)
    stats["marker_bytes_nonzero"] = sum(value != 0 for value in actual)
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPOSITORY / "build/research/tower-power")
    args = parser.parse_args()
    root = args.root.resolve()
    output = root / "static/lines"
    output.mkdir(parents=True, exist_ok=True)
    programs = {}
    # All width/height ratios, both Y directions; extra X phases and reversed
    # endpoint ordering exercise packed partial bytes and sorting.
    cases = [(0, 0, width, height) for width in range(1, 64) for height in range(128)]
    cases += [(0, 127, width, 127 - height) for width in range(1, 64) for height in range(1, 128)]
    cases += [(phase, 20, phase + width, 20 + height)
              for phase in (1, 2, 3) for width in (1, 2, 3, 4, 7, 15, 31, 59)
              for height in (0, 1, 2, 3, 7, 31, 60, 100) if phase + width < 64]
    cases += [(x1, y1, x0, y0) for x0, y0, x1, y1 in cases[-192:]]
    cases += [(17, 0, 17, 127), (17, 127, 17, 0)]
    representatives = [(0, 20, 60, 20), (1, 20, 60, 20), (0, 20, 60, 35),
                       (0, 20, 60, 79), (0, 0, 60, 60), (0, 0, 60, 120),
                       (0, 0, 2, 127), (0, 0, 1, 127), (0, 127, 60, 7)]
    for name, config in CONFIG.items():
        initial = bytearray((root / f"static/unpacked/side2-{name}.memory.bin").read_bytes())
        native = (root / config["native"]).read_bytes()
        memory = bytearray(initial)
        generation = cpu_call(memory, config["generator"], [config["generator_range"]])
        # The actual mode uses XOR kernels; F1's separate unused constant-store
        # templates are outside this task and later share RAM with prefix code.
        if name == "f1":
            assert memory[0x3924] == 0
        mask = cpu_call(memory, config["mask"], [(config["mask"], config["draw"])], accumulator=255)
        native_differences = [{"address": address, "generated": memory[address], "native": native[address]}
                              for lo, hi in KERNELS for address in range(lo, hi)
                              if memory[address] != native[address]]
        total_steps = generation["instructions"] + mask["instructions"]
        for endpoints in cases:
            stats = run_line(memory, config, endpoints)
            total_steps += stats["instructions"]
        sample_results = [run_line(memory, config, endpoints, collect=True) for endpoints in representatives]
        programs[name] = {"input_memory_sha256": digest(initial), "native_memory_sha256": digest(native),
                          "generator_entry": config["generator"], "draw_entry": config["draw"],
                          "marker_base": config["marker"], "kernel_ranges_end_exclusive": KERNELS,
                          "kernel_bytes": sum(hi - lo for lo, hi in KERNELS),
                          "kernel_sha256": digest(b"".join(memory[lo:hi] for lo, hi in KERNELS)),
                          "generation": generation, "mask_setup": mask,
                          "native_kernel_differences": native_differences,
                          "cases_checked": len(cases), "all_patches_restored": True,
                          "total_original_instructions": total_steps,
                          "representative_lines": sample_results}
        (output / f"{name}-canonical-ram.bin").write_bytes(memory)
    report = {"pass": True, "script_sha256": digest(Path(__file__).read_bytes()),
              "py65_version": importlib.metadata.version("py65"),
              "scope": "Original regenerated XOR line routines in flat py65 RAM; cycles exclude VIC/IRQ and caller JSR",
              "crossing_rule": {"endpoint": "sort increasing X; one marker for X in [x0,x1); vertical edges ignored",
                                "steep": "y0+sign*ceil(j*(abs(dy)+1)/(dx+1))",
                                "shallow": "y0+sign*max(0,floor((j*(abs(dy)+1)-1)/(dx+1)))"},
              "programs": programs,
              "limitations": ["Not the exact rational ceil crossing rule used by our renderer",
                              "Original input range is bounded to the 64x128 marker canvas",
                              "No native frame-rate or complete native pixel proof"]}
    (output / "kernels-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"pass": True, "cases_per_program": len(cases),
                      "programs": {name: {key: value for key, value in program.items()
                                         if key in ("kernel_bytes", "cases_checked", "native_kernel_differences", "total_original_instructions", "mask_setup")}
                                   for name, program in programs.items()}}, indent=2))


if __name__ == "__main__":
    main()
