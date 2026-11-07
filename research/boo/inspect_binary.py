#!/usr/bin/env python3
"""Inspect CPU-unpacked Boo! bytes and check its small RAM-only BRR routines.

The drive image is statically reconstructed from original C64 send ranges;
this does not execute the 1541 program, ROM receiver, IEC protocol or display.
"""

import argparse
import hashlib
import importlib.util
import json
import random
from collections import Counter
from pathlib import Path

from py65.devices.mpu6502 import MPU

from unpack_6502 import NmosBootstrap


ROOT = Path(__file__).resolve().parents[2]
REVERSE = [int(f"{i:08b}"[::-1], 2) for i in range(256)]


class SelectorCpu(NmosBootstrap):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instruct[0x27] = self.rla_zero_page
        self.cycletime[0x27] = 5

    @staticmethod
    def rla_zero_page(cpu):
        address = cpu.ByteAt(cpu.pc)
        old = cpu.memory[address]
        value = ((old << 1) | (cpu.p & cpu.CARRY)) & 255
        cpu.p = (cpu.p & ~cpu.CARRY) | (old >> 7)
        cpu.memory[address] = value
        cpu.a &= value
        cpu.FlagsNZ(cpu.a)
        cpu.pc += 1


def run_until(cpu, target, limit=1000):
    count = 0
    while cpu.pc != target:
        if count >= limit:
            raise RuntimeError(f"Instruction limit at ${cpu.pc:04x}, target ${target:04x}")
        opcode = cpu.memory[cpu.pc]
        if cpu.instruct[opcode].__name__ == "inst_not_implemented":
            raise RuntimeError(f"Unsupported opcode ${opcode:02x} at ${cpu.pc:04x}")
        cpu.step()
        count += 1
    return count


def selector_case(cpu, start, end, rank):
    cpu.memory[0x34], cpu.memory[0x35], cpu.memory[0x38] = start, end, rank
    cpu.pc, cpu.a, cpu.x, cpu.y, cpu.p, cpu.sp = 0x0401, 0, 0, 0, 0x20, 255
    cpu.processorCycles = 0
    steps = run_until(cpu, 0x047F)
    expected = sorted(REVERSE[start:end])[rank]
    actual = cpu.memory[0x31]
    assert actual == expected, (start, end, rank, actual, expected)
    return steps, cpu.processorCycles


def validate_selector(drive):
    cpu = SelectorCpu(memory=bytearray(drive))
    cases = []
    # Complete horizontal endpoint domain of our 64-pixel logical canvas.
    for start in range(64):
        for end in range(start + 1, 64):
            for rank in range(end - start):
                cases.append((start, end, rank))
    small_count = len(cases)
    # Broader byte-coordinate samples, including the published cube's scale.
    extra = set()
    for length in (1, 2, 3, 7, 8, 15, 16, 31, 32, 63, 64, 127, 128, 171, 172, 173, 254, 255):
        for start in range(256 - length):
            for rank in (0, length // 2, length - 1):
                extra.add((start, start + length, rank))
    generator = random.Random(2023)
    for _ in range(4096):
        start = generator.randrange(255)
        end = generator.randrange(start + 1, 256)
        extra.add((start, end, generator.randrange(end - start)))
    counts, cycles = Counter(), Counter()
    for case in cases + sorted(extra):
        steps, nominal = selector_case(cpu, *case)
        counts[steps] += 1
        cycles[nominal] += 1
    total = len(cases) + len(extra)
    return {"pass": True, "exhaustive_64_pixel_endpoint_rank_cases": small_count,
            "additional_byte_coordinate_cases": len(extra), "total_cases": total,
            "entry": 0x0401, "stop_before_result_consumer": 0x047F,
            "inputs": {"start": "$34", "exclusive_end": "$35", "rank": "$38"},
            "result": "$31", "oracle": "sorted(reverse8[start:end])[rank]",
            "domain_note": "0<=start<end<=255; end=256 is not representable by this byte API",
            "instruction_counts": {"min": min(counts), "max": max(counts),
                                   "mean": sum(k * v for k, v in counts.items()) / total},
            "nominal_cpu_cycles_excluding_call_setup_and_result_consumer": {
                "min": min(cycles), "max": max(cycles),
                "mean": sum(k * v for k, v in cycles.items()) / total},
            "cpu_model_addition": "NMOS27 RLA zero page: rotate memory through carry, AND into A, set N/Z"}


def validate_generator(main):
    memory = bytearray(main)
    cpu = MPU(memory=memory)
    checked = 0
    for row in range(255):
        memory[0x20] = row
        cpu.pc, cpu.p = 0x26CD, 0x20
        run_until(cpu, 0x26EB)  # stop before the original VIC register store
        assert memory[0x1F] == REVERSE[row] + 1
        memory[0x28:0x2A] = bytes((0x00, 0x90))
        memory[0x30:0x32] = bytes((row, 0xE0))
        cpu.pc, cpu.x = 0x275D, 0
        run_until(cpu, 0x2785)
        expected = bytes((0x8D, row, 0xE0, 0xE0, REVERSE[row] + 1, 0x65, 0x16))
        assert memory[0x9000:0x9007] == expected
        for position in (0, 17, 255):
            for threshold in (0, 1, 64, 127, 128, 254, 255):
                for step in (0, 1, 128, 255):
                    for carry in (0, 1):
                        cpu.pc, cpu.a, cpu.x, cpu.p = 0x9000, position, threshold, 0x20 | carry
                        memory[0x16] = step
                        cpu.processorCycles = 0
                        run_until(cpu, 0x9007)
                        assert memory[0xE000 + row] == position
                        assert cpu.a == (position + step + (REVERSE[row] < threshold)) & 255
                        assert cpu.processorCycles == 9
                        checked += 1
    return {"pass": True, "rows_checked": 255, "generated_cell_cases": checked,
            "original_template": {"address": 0x27A5, "bytes": bytes(main[0x27A5:0x27AC]).hex(" ")},
            "original_reversal_constructor": [0x26CD, 0x26EB],
            "original_cell_constructor": [0x275D, 0x2785],
            "generated_cell": "STA absolute; CPX #(reverse8(row)+1); ADC $16",
            "interpolation_core_cycles": 5, "position_store_plus_interpolation_cycles": 9,
            "comparison": "Carry is threshold>=reverse8(row)+1, equivalently reverse8(row)<threshold",
            "excluded_row": "row255 would wrap reverse8(row)+1; no claim for that generator row",
            "limitations": "Nominal instruction cycles; no fill, setup, interrupts, VIC contention or drive timing"}


def current_scene_setup_cost(drive):
    source = ROOT / "research/bit-reversal/analyze.py"
    spec = importlib.util.spec_from_file_location("current_brr_scene", source)
    model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    cpu = SelectorCpu(memory=bytearray(drive))
    calls = cycles = steps = markers = corrections = 0
    by_frame = []
    cache = {}
    for index in range(512):
        points, visible = model.scene(index)
        frame_cycles = 0
        for a, b, f, g in model.model_edges():
            color = (model.COLORS[f] if visible[f] else 0) ^ (model.COLORS[g] if visible[g] else 0)
            if not color:
                continue
            first, last = model.ordered_edge(points[a], points[b])
            length = last[0] - first[0]
            if length <= 1:
                continue  # existing vertical skip / single-marker fast path
            remainder = (last[1] - first[1]) % length
            markers += length
            corrections += remainder
            if not remainder:
                continue  # threshold zero produces no corrections, no selector
            case = (first[0], last[0], remainder)
            if case not in cache:
                cache[case] = selector_case(cpu, *case)
            count, nominal = cache[case]
            calls += 1
            steps += count
            cycles += nominal
            frame_cycles += nominal
        by_frame.append(frame_cycles)
    gross = 9 * markers + 4 * corrections  # 21/25 current vs 12-cycle compatible BRR
    return {"poses": 512, "scene_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "nonzero_fraction_selector_calls": calls, "total_selector_instructions": steps,
            "total_selector_cycles": cycles, "mean_selector_cycles_per_call": cycles / calls,
            "mean_selector_cycles_per_presentation": cycles / 512,
            "max_selector_cycles_per_presentation": max(by_frame),
            "gross_12_cycle_brr_saving_per_presentation": gross / 512,
            "gross_minus_selector_only_per_presentation": (gross - cycles) / 512,
            "model": "Transpose Boo's scalar selector to our absolute horizontal phase; bypass rank0 and dx<=1",
            "exclusions": "No JSR, parameter/result setup, original division changes, marker plotting, IRQ/VIC or drive transfer",
            "conclusion_scope": "CPU-cycle adaptation estimate, not a renderer benchmark or Boo frame-time measurement"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "build/research/boo/static")
    args = parser.parse_args()
    root = args.root
    receipt = json.loads((root / "bootstrap-execution.json").read_text())
    assert receipt["ram_postprocess_completed"] and not receipt["visible_io_accesses"]
    memory = (root / "ram-after-bootstrap.bin").read_bytes()
    assert hashlib.sha256(memory).hexdigest() == receipt["ram_sha256"]
    drive = bytearray(65536)
    segments = [(0x3837, 0x3927, 0x0010), (0x3927, 0x39AE, 0x0100), (0x2BDD, 0x3256, 0x0187)]
    for start, end, destination in segments:
        drive[destination:destination + end - start] = memory[start:end]
    (root / "drive-ram-reconstructed.bin").write_bytes(drive)
    (root / "drive-0010-07ff.bin").write_bytes(drive[0x10:0x800])
    # Reuse the repository's existing NMOS disassembly utility; no bytes execute.
    utility = ROOT / "research/tower-power/static_loader.py"
    spec = importlib.util.spec_from_file_location("nmos_disassembly", utility)
    disassembly = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(disassembly)
    for name, data, start, end in [
        ("c64-generator.asm", memory, 0x26CD, 0x27AC),
        ("drive-selector.asm", drive, 0x0401, 0x048B),
        ("c64-drive-upload.asm", memory, 0x2A87, 0x2AD1),
    ]:
        lines, pc = [], start
        while pc < end:
            item = disassembly.decode(data, pc)
            lines.append(f"{pc:04x}: {item['bytes']:<8} {item['mnemonic']} {item['text']}")
            pc = item["next"]
        (root / name).write_text("\n".join(lines) + "\n")
    result = {
        "program_sha256": receipt["program_sha256"], "ram_sha256": receipt["ram_sha256"],
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "drive_reconstruction": {"method": "Static source ranges from original C64 send loops; not drive RAM capture",
                                 "segments": [{"source_start": a, "source_end_exclusive": b, "drive_destination": c}
                                              for a, b, c in segments],
                                 "bytes": 2032, "sha256": hashlib.sha256(drive[0x10:0x800]).hexdigest(),
                                 "bootstrap_command": "M-E $0205 with command-buffer receive stub",
                                 "in_drive_receive_destination": "$0010..$07ff", "program_entry": 0x0187},
        "generator": validate_generator(memory), "drive_selector": validate_selector(drive),
        "current_scene_setup_cost_model": current_scene_setup_cost(drive),
    }
    (root / "binary-analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
