#!/usr/bin/env python3
"""Execute the released Freespin decoder against its D64-derived GCR inputs.

Only $1c01 data reads and byte-ready V events are supplied. Original ADC/EOR,
pointer stores, INC timing-delay instructions and carry flow run unchanged.
This is not physical disk, VIA, analog video, mechanical audio or timing proof.
"""

import hashlib
import importlib.metadata
import json
from pathlib import Path

from py65.devices.mpu6502 import MPU


REPOSITORY = Path(__file__).resolve().parents[2]
ROOT = REPOSITORY / "build/research/freespin"


def digest(data):
    return hashlib.sha256(data).hexdigest()


class InputMemory:
    def __init__(self, released, raw, destination, identity):
        self.ram = bytearray(65536)
        self.ram[0x702:0x800] = released
        self.ram[:16] = bytes((9,)) * 16
        self.ram[0:2] = destination.to_bytes(2, "little")
        self.pc = None
        self.input = raw[7:319]
        self.pos = 0
        self.events = []

    def __getitem__(self, address):
        if address == 0x1C01:
            assert self.pc in (0x77B, 0x78D, 0x797), hex(self.pc)
            assert self.pos < len(self.input)
            value = self.input[self.pos]
            self.pos += 1
            return value
        return self.ram[address]

    def __setitem__(self, address, value):
        self.ram[address] = value
        if self.pc in (0x793, 0x7A0):
            self.events.append((address, value))


def validate_block(released, row):
    prefix = ROOT / row["prefix"]
    raw = Path(str(prefix) + ".gcr.bin").read_bytes()
    expected = Path(str(prefix) + ".decoded.bin").read_bytes()
    assert digest(raw) == row["raw_sha256"] and digest(expected) == row["decoded_sha256"]
    memory = InputMemory(released, raw, row["destination"], row["block"])
    cpu = MPU(memory=memory, pc=0x779)
    cpu.p = cpu.UNUSED | cpu.INTERRUPT  # Binary ADC, initial C=0 from header.
    cpu.x, cpu.y, cpu.sp = row["block"], 208, 255
    steps, ready_events = 0, 0
    while cpu.pc != 0x7A4:
        assert 0x779 <= cpu.pc < 0x7A4 and steps < 10_000, hex(cpu.pc)
        if cpu.pc in (0x779, 0x795):
            # Represents a byte-ready SO edge. It changes V, never carry.
            cpu.p |= cpu.OVERFLOW
            ready_events += 1
        memory.pc = cpu.pc
        cpu.step()
        steps += 1
    assert cpu.y == 0 and cpu.x == row["block"] and cpu.sp == 255
    assert memory.pos == 312 and ready_events == 208
    assert memory.events == [(row["destination"] + y, expected[y]) for y in range(207, -1, -1)]
    assert memory.ram[row["destination"]:row["destination"] + 208] == expected
    assert memory.ram[4 + row["block"]] == 0xD9
    assert memory.ram[0x779:0x7A4] == released[0x779 - 0x702:0x7A4 - 0x702]
    trace = bytearray()
    for address, value in memory.events:
        trace.extend((address & 255, address >> 8, value))
    return {"track": row["track"], "block": row["block"], "copies_covered": len(row["copies"]),
            "pass": True, "instructions": steps, "raw_reads": memory.pos,
            "ready_events": ready_events, "output_events": len(memory.events),
            "write_trace_sha256": digest(trace)}


def delay_count(released):
    # Measurable finite fixed loop from the release, outside hardware polling.
    memory = bytearray(65536)
    memory[0x702:0x800] = released
    memory[:16] = bytes((0xD9,)) * 16
    cpu = MPU(memory=memory, pc=0x7B4)
    cpu.p = cpu.UNUSED | cpu.INTERRUPT
    cpu.x, cpu.y, cpu.a = 16, 0, 0x66
    steps = 0
    while cpu.pc != 0x7BE:
        assert 0x7B4 <= cpu.pc < 0x7BE and steps < 5000
        cpu.step()
        steps += 1
    assert cpu.x == cpu.y == 0
    return {"range_start": 0x7B4, "range_end_exclusive": 0x7BE,
            "instructions": steps, "cycles": cpu.processorCycles,
            "published_comment_cycles": 6399,
            "interpretation": "Fixed loop only, includes LDY each iteration; excludes preceding LDX and following STA/extra release delay/timer polling"}


def main():
    index_path = ROOT / "decoded-index.json"
    index = json.loads(index_path.read_text())
    released = (ROOT / "loader-release.bin").read_bytes()
    assert index["pass"] and digest(released) == index["loader_release_sha256"]
    rows = [validate_block(released, row) for row in index["blocks"]]
    assert len(rows) == 153 and sum(row["copies_covered"] for row in rows) == 357
    result = {"pass": True, "scope": "Original released 6502 payload decoder with mocked port data/byte-ready edges; no disk or signal timing emulation",
              "script_sha256": digest(Path(__file__).read_bytes()), "py65_version": importlib.metadata.version("py65"),
              "input_index_sha256": digest(index_path.read_bytes()), "loader_release_sha256": digest(released),
              "code_range_end_exclusive": [0x779, 0x7A4], "blocks_checked": len(rows),
              "identical_sector_copies_covered": sum(row["copies_covered"] for row in rows),
              "output_events": sum(row["output_events"] for row in rows),
              "raw_gcr_reads": sum(row["raw_reads"] for row in rows),
              "instructions_executed": sum(row["instructions"] for row in rows),
              "fixed_delay": delay_count(released), "blocks": rows,
              "limitations": ["Port arrival timing, SO edges, VIA side effects, sync and disk rotation are mocked",
                              "No analog video, physical audio, whole-demo execution or seven-frame timing proof",
                              "Tracks19..34 remain outside the validated coherent part set"]}
    (ROOT / "cpu-validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "blocks"}, indent=2))


if __name__ == "__main__":
    main()
