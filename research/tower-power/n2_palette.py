#!/usr/bin/env python3
"""Verify N2's FF-seeded prefix/color encoding using original generated cells.

Flat py65 RAM, no VIC/IO emulation or VICE process. Original generator and
initialization code run unchanged; prefix cells run as bounded column spans,
omitting the unrelated sprite helper between the two generated halves.
"""

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

from py65.devices.mpu6502 import MPU


REPOSITORY = Path(__file__).resolve().parents[2]
STOP = 0x02FF


def digest(data):
    return hashlib.sha256(data).hexdigest()


def call(memory, entry, allowed, accumulator=0):
    cpu = MPU(memory=memory, pc=entry)
    cpu.a = accumulator
    cpu.p = cpu.UNUSED | cpu.INTERRUPT
    cpu.sp = 255
    cpu.stPushWord(STOP - 1)
    steps = 0
    while cpu.pc != STOP:
        assert any(lo <= cpu.pc < hi for lo, hi in allowed), hex(cpu.pc)
        assert steps < 500_000
        cpu.step()
        steps += 1
    assert cpu.sp == 255
    return steps


def prefix_runs(memory, starts, ends):
    runs = []
    first, second = 0xCB00, 0x6800
    for column, (start, end) in enumerate(zip(starts, ends)):
        marker = 0xF700 + column * 128
        output = 0x0800 + column * 128
        assert memory[first:first + 2] == bytes((0xA9, 0xFF))
        first_end = first + 2
        for row in range(start, 64):
            wanted = bytes((0x4D, (marker + row) & 255, (marker + row) >> 8,
                            0x8D, (output + row) & 255, (output + row) >> 8))
            assert memory[first_end:first_end + 6] == wanted
            first_end += 6
        assert memory[second:second + 3] == bytes((0xAD, (output + 63) & 255, (output + 63) >> 8))
        second_end = second + 3
        for row in range(64, end):
            wanted = bytes((0x4D, (marker + row) & 255, (marker + row) >> 8,
                            0x8D, (output + row) & 255, (output + row) >> 8))
            assert memory[second_end:second_end + 6] == wanted
            second_end += 6
        runs.append((first, first_end, second, second_end))
        first, second = first_end, second_end
    # Original non-pixel helper, then transfer to second-half code.
    assert memory[first:first + 6] == bytes((0x20, 0x63, 0x30, 0x4C, 0x00, 0x68))
    assert memory[second] == 0x60
    return runs, [(0xCB00, first + 6), (0x6800, second + 1)]


def execute_spans(memory, runs):
    cpu = MPU(memory=memory, pc=0)
    cpu.p = cpu.UNUSED | cpu.INTERRUPT
    steps = 0
    for which in (0, 2):
        for run in runs:
            start, end = run[which:which + 2]
            cpu.pc = start
            while cpu.pc != end:
                assert start <= cpu.pc < end
                cpu.step()
                steps += 1
    return steps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPOSITORY / "build/research/tower-power")
    args = parser.parse_args()
    root = args.root.resolve()
    prefix = root / "static/unpacked/side2-n2"
    initial = bytearray(prefix.with_suffix(".memory.bin").read_bytes())
    known = prefix.with_suffix(".known.bin").read_bytes()
    assert all(known[a] for lo, hi in [(0x28B7, 0x2A22), (0x2C6B, 0x2C97), (0x3791, 0x3828)]
               for a in range(lo, hi))
    output = root / "static/n2-palette"
    output.mkdir(parents=True, exist_ok=True)
    memory = bytearray(initial)
    total_steps = call(memory, 0x2C6B, [(0x2C6B, 0x2C85)])
    assert memory[0x0800:0x1000] == bytes((255,)) * 2048
    total_steps += call(memory, 0x3791, [(0x3791, 0x37A3)])
    total_steps += call(memory, 0x37A3, [(0x37A3, 0x37FE)])
    canvas = {0x0400 + (4 + row) * 40 + 12 + col: col * 16 + row
              for row in range(16) for col in range(16)}
    assert all(memory[a] == canvas.get(a, 0) for a in range(0x0400, 0x07E8))
    total_steps += call(memory, 0x2C85, [(0x2C85, 0x2C97)], 0x88)
    assert memory[0xD800:0xDC00] == bytes((0x88,)) * 1024
    starts, ends = initial[0x37FE:0x380E], initial[0x380E:0x381E]
    total_steps += call(memory, 0x28B7, [(0x28B7, 0x29C6)])
    runs, code_ranges = prefix_runs(memory, starts, ends)
    total_steps += call(memory, 0x29C9, [(0x29C9, 0x2A22)])
    clear_cells = [0xF700 + column * 128 + row for column in range(16)
                   for row in range(starts[column], ends[column])]
    clear_end = 0xE000 + 3 * len(clear_cells)
    for offset, address in enumerate(clear_cells):
        assert memory[0xE000 + offset * 3:0xE003 + offset * 3] == bytes((0x8D, address & 255, address >> 8))
    assert memory[clear_end] == 0x60
    cleared = bytearray(memory)
    cleared[0xF700:0xFF00] = bytes((0xA5,)) * 2048
    total_steps += call(cleared, 0xE000, [(0xE000, clear_end + 1)], 0)
    selected = set(clear_cells)
    assert all(cleared[a] == (0 if a in selected else 0xA5) for a in range(0xF700, 0xFF00))
    cases = [{"name": "empty", "markers": []}]
    for mask in (0x55, 0xAA, 0xFF):
        cases.append({"name": f"face-{mask:02x}", "markers": [(20, mask), (80, mask)]})
    for a in (0x55, 0xAA, 0xFF):
        for b in (0x55, 0xAA, 0xFF):
            if a == b:
                continue
            for lane in range(4):
                lane_mask = 0xC0 >> (lane * 2)
                cases.append({"name": f"shared-{a:02x}-{b:02x}-lane{lane}",
                              "markers": [(45, a & lane_mask), (70, (a ^ b) & lane_mask), (95, b & lane_mask)]})
    for case in cases:
        actual = bytearray(memory)
        actual[0xF700:0xFF00] = bytes(2048)
        for row, value in case["markers"]:
            actual[0xF700 + 7 * 128 + row] ^= value
        wanted = bytearray((255,)) * 2048
        for column in range(16):
            accumulator = 255
            for row in range(starts[column], ends[column]):
                accumulator ^= actual[0xF700 + column * 128 + row]
                wanted[column * 128 + row] = accumulator
        total_steps += execute_spans(actual, runs)
        assert actual[0x0800:0x1000] == wanted, case["name"]
    face_values = set(initial[0x24FC:0x24FC + 70])
    assert face_values == {0x55, 0xAA, 0xFF}
    native_path = root / "n2-live-01/ram-sphere-01.bin"
    native = native_path.read_bytes()
    assert len(native) == 65536
    assert native[0x0800:0x0808] == bytes((255,)) * 8
    assert all(native[a] == 0 for a in range(0x0400, 0x07E8) if a not in canvas)
    assert all(native[lo:hi] == memory[lo:hi] for lo, hi in code_ranges)
    report = {
        "pass": True, "scope": "Original N2 init/generators and generated prefix cells in flat py65 RAM; static VIC interpretation from Commodore manual",
        "script_sha256": digest(Path(__file__).read_bytes()), "py65_version": importlib.metadata.version("py65"),
        "input_memory_sha256": digest(initial), "native_ram_sha256": digest(native),
        "charset_init_range_end_exclusive": [0x0800, 0x1000], "charset_init_value": 255,
        "color_ram_literal_store": 0x88, "hardware_low_nibble": 8,
        "palette_mode1_d021_d022_d023": list(initial[0x381E:0x3821]),
        "canvas_rows_columns": [[4, 19], [12, 27]], "outside_matrix_character": 0,
        "native_glyph0": native[0x0800:0x0808].hex(), "native_outside_screen_cells_zero": True,
        "prefix_code_ranges_end_exclusive": code_ranges, "native_generated_prefix_matches": True,
        "prefix_seed": 255, "marker_range_end_exclusive": [0xF700, 0xFF00], "marker_clear_value": 0,
        "column_start_rows": list(starts), "column_end_rows_exclusive": list(ends),
        "generated_cells": len(clear_cells), "face_masks": sorted(face_values),
        "face_mask_to_final_code": {f"{mask:02x}": (255 ^ mask) & 3 for mask in sorted(face_values)},
        "cases_checked": len(cases), "case_names": [case["name"] for case in cases],
        "total_original_instructions": total_steps,
        "limitations": ["No hardware Color RAM readback from raw bank-RAM dump",
                        "Pixel cells execute unchanged but unrelated sprite helper between halves is omitted",
                        "Not a full line/culling renderer or native timing proof; palette claim scoped to mode1 sphere phase"],
    }
    (output / "palette-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "case_names"}, indent=2))


if __name__ == "__main__":
    main()
