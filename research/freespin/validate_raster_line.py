#!/usr/bin/env python3
"""Check a released Freespin raster loop's nominal CPU cadence and output.

Original official-opcode loop, flat py65 RAM. No 6522 timer/port, analog signal,
motor, PAL compliance or native execution claim; no emulator process is started.
"""

import hashlib
import json
from pathlib import Path

from py65.devices.mpu6502 import MPU


REPOSITORY = Path(__file__).resolve().parents[2]
ROOT = REPOSITORY / "build/research/freespin"


def digest(data):
    return hashlib.sha256(data).hexdigest()


class ObservedMemory:
    def __init__(self, image, wave):
        self.ram = bytearray(65536)
        self.ram[:2048] = image
        self.ram[0x1800] = 0x04 | (wave << 7)
        self.pending = []

    def __getitem__(self, address):
        return self.ram[address]

    def __setitem__(self, address, value):
        self.ram[address] = value
        if address in (0x1800, 0x1C00):
            self.pending.append((address, value))


def video_level(value):
    # Output-latch interpretation of the author's DATA-resistor wiring.
    if value & 8:
        return "sync"
    return "black" if value & (2 | 16) else "white"


def run(image, wave, initial_x, carry, cross_boundary=False):
    memory = ObservedMemory(image, wave)
    cpu = MPU(memory=memory, pc=0x200)
    cpu.x, cpu.y, cpu.sp = initial_x, 4, 255
    cpu.p = cpu.UNUSED | cpu.INTERRUPT | carry
    records, steps = [], 0
    endpoint = 0x233 if cross_boundary else (0x200 if initial_x > 1 else 0x22E)
    while steps == 0 or cpu.pc != endpoint:
        assert 0x200 <= cpu.pc < 0x233 and steps < 100
        pc = cpu.pc
        memory.pending.clear()
        cpu.step()
        for address, value in memory.pending:
            records.append({"pc": pc, "address": address, "value": value,
                            "instruction_end_cycle": cpu.processorCycles,
                            "latch_level": video_level(value) if address == 0x1800 else None})
        steps += 1
    sound = [row for row in records if row["address"] == 0x1C00]
    assert sound == [{"pc": 0x207, "address": 0x1C00, "value": 0x14 | wave,
                      "instruction_end_cycle": 15, "latch_level": None}]
    video = [row for row in records if row["address"] == 0x1800]
    assert video[0]["pc"] == 0x202 and video[0]["instruction_end_cycle"] == 8
    assert [row["instruction_end_cycle"] for row in video[1:12]] == list(range(19, 60, 4))
    assert [row["latch_level"] for row in video[1:12]] == ["white", "black"] * 5 + ["white"]
    if cross_boundary:
        assert video[-1]["pc"] == 0x230 and video[-1]["instruction_end_cycle"] == 72
        assert video[-1]["instruction_end_cycle"] - video[0]["instruction_end_cycle"] == 64
    else:
        assert cpu.processorCycles == (64 if initial_x > 1 else 63)
    return {"wave_bit": wave, "initial_x": initial_x, "incoming_carry": carry,
            "cross_fragment_boundary": cross_boundary, "instructions": steps,
            "cycles": cpu.processorCycles, "writes": records}


def main():
    index = json.loads((ROOT / "decoded-index.json").read_text())
    image = (ROOT / "parts/track02.memory.bin").read_bytes()
    row = next(row for row in index["tracks"] if row["track"] == 2)
    assert digest(image) == row["memory_sha256"]
    assert image[0x1D6:0x1DD] == bytes.fromhex("a0 04 a6 00 20 00 02")
    expected = bytes.fromhex("a9 00 0e 00 18 69 14 99 fc 1b 8c 00 18 8d 00 18 8c 00 18 8d 00 18 8c 00 18 8d 00 18 8c 00 18 8d 00 18 8c 00 18 8d 00 18 8c 00 18 ca d0 d2 a5 10 0e 00 18")
    assert image[0x200:0x233] == expected
    cases = [run(image, wave, initial_x, carry)
             for wave in (0, 1) for initial_x in (1, 2) for carry in (0, 1)]
    cases += [run(image, wave, 1, carry, True) for wave in (0, 1) for carry in (0, 1)]
    result = {"pass": True, "scope": "Nominal CPU cycle/output-latch check of released track2 fragment; flat RAM, not VIA or analog simulation",
              "script_sha256": digest(Path(__file__).read_bytes()), "part_sha256": digest(image),
              "loop_range_end_exclusive": [0x200, 0x22E], "normal_iteration_cycles": 64,
              "caller_sets_y4_at": 0x1D6, "caller_jsr_at": 0x1DA,
              "last_iteration_cycles": 63, "next_fragment_load_cycles": 3,
              "sync_to_sync_boundary_cycles": 64, "consecutive_graphic_store_cycles": 4,
              "sound_store_cycle": 15, "wave_bit_copied_to_motor_bit0": True,
              "nominal_cycle_mhz": 1, "cases": cases,
              "limitations": ["No asynchronous VIA Timer1/PB7 sampling or readback behavior emulated",
                              "RMW dummy writes and analog voltage/pulse shape are outside this test",
                              "No complete raster frame, PAL compliance, speaker mechanics or whole-demo timing proof"]}
    (ROOT / "raster-line-validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "cases"}, indent=2))


if __name__ == "__main__":
    main()
