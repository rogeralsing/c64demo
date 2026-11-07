#!/usr/bin/env python3
"""Execute Boo!'s original 4K PRG bootstrap in a bounded, flat-RAM py65 model.

No VICE or drive is started. CPU-model additions are the NMOS $89 immediate
NOP and $bf absolute,Y LAX used by the released bootstrap. No original PRG byte is
patched. It also executes the RAM-only postprocessor called at $4d19, then
stops at its original JMP $2a78 before any demo/drive initialization.
"""

import argparse
import hashlib
import importlib.metadata
import json
from collections import Counter
from pathlib import Path

from py65.devices.mpu6502 import MPU


ROOT = Path(__file__).resolve().parents[2]
EXPECTED = "4105eecdb5ee4e5927b22cc5afe029a1d14a0919d633cdf291460b94ec9b4920"


class NmosBootstrap(MPU):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instruct = list(self.instruct)
        self.cycletime = list(self.cycletime)
        self.extracycles = list(self.extracycles)
        self.instruct[0x89] = self.nop_immediate
        self.cycletime[0x89] = 2
        self.instruct[0xBF] = self.lax_absolute_y
        self.cycletime[0xBF] = 4
        self.extracycles[0xBF] = 1

    @staticmethod
    def nop_immediate(cpu):
        cpu.pc = (cpu.pc + 1) & 65535

    @staticmethod
    def lax_absolute_y(cpu):
        value = cpu.ByteAt(cpu.AbsoluteYAddr())
        cpu.a = cpu.x = value
        cpu.FlagsNZ(value)
        cpu.pc += 2


class Ram:
    def __init__(self, data):
        self.data = data
        self.pc = None
        self.writes = Counter()
        self.write_events = 0
        self.visible_io_accesses = []

    def io_visible(self):
        pins = (self.data[1] & self.data[0]) | (~self.data[0] & 7)
        return bool((pins & 3) and (pins & 4))

    def __getitem__(self, address):
        if isinstance(address, int) and 0xD000 <= address < 0xE000 and self.io_visible():
            self.visible_io_accesses.append((self.pc, "read", address))
            raise RuntimeError(f"Hardware-visible IO read at ${address:04x}")
        return self.data[address]

    def __setitem__(self, address, value):
        if 0xD000 <= address < 0xE000 and self.io_visible():
            self.visible_io_accesses.append((self.pc, "write", address))
            raise RuntimeError(f"Hardware-visible IO write at ${address:04x}")
        self.data[address] = value
        self.writes[address] += 1
        self.write_events += 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "build/research/boo/boo.prg")
    parser.add_argument("--output", type=Path, default=ROOT / "build/research/boo/static")
    parser.add_argument("--max-steps", type=int, default=5_000_000)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    blob = args.input.read_bytes()
    assert len(blob) == 4096 and hashlib.sha256(blob).hexdigest() == EXPECTED
    memory = bytearray(65536)
    load = int.from_bytes(blob[:2], "little")
    memory[load:load + len(blob) - 2] = blob[2:]
    memory[0], memory[1] = 0x2F, 0x37
    ram = Ram(memory)
    cpu = NmosBootstrap(memory=ram, pc=0x080B)
    cpu.p = cpu.UNUSED  # binary arithmetic, carry clear
    cpu.sp = 255
    cpu.stPushWord(0x02FE)  # diagnostic SYS return sentinel
    ram.writes.clear()
    ram.write_events = 0
    instructions = Counter()
    last = []
    status = "instruction_limit"
    steps = 0
    first_stage = None
    while steps < args.max_steps:
        pc = cpu.pc
        if pc == 0x4D19 and first_stage is None:
            (args.output / "ram-after-first-stage.bin").write_bytes(memory)
            first_stage = {"steps": steps, "entry": pc, "ram_sha256": hashlib.sha256(memory).hexdigest()}
        if not (0x080B <= pc < 0x0830 or 0x0002 <= pc < 0x0100
                or first_stage is not None and 0x4D04 <= pc <= 0x4D3C):
            status = "transfer_outside_bootstrap"
            break
        opcode = memory[pc]
        if cpu.instruct[opcode].__name__ == "inst_not_implemented":
            status = "unsupported_opcode"
            break
        last.append({"pc": pc, "opcode": opcode, "a": cpu.a, "x": cpu.x,
                     "y": cpu.y, "p": cpu.p, "sp": cpu.sp})
        last = last[-32:]
        ram.pc = pc
        instructions[pc] += 1
        try:
            cpu.step()
        except RuntimeError as exc:
            status = str(exc)
            break
        steps += 1
    (args.output / "ram-after-bootstrap.bin").write_bytes(memory)
    (args.output / "zero-page-after-bootstrap.bin").write_bytes(memory[:256])
    result = {
        "status": status, "program_sha256": EXPECTED, "input_bytes": len(blob),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "py65_version": importlib.metadata.version("py65"), "entry": 0x080B,
        "steps": steps, "stop_pc": cpu.pc, "stop_opcode": memory[cpu.pc],
        "first_stage": first_stage,
        "ram_postprocess_completed": cpu.pc == 0x2A78 and last[-1]["pc"] == 0x00F1,
        "visible_io_accesses": ram.visible_io_accesses,
        "stop_registers": {"a": cpu.a, "x": cpu.x, "y": cpu.y, "p": cpu.p, "sp": cpu.sp},
        "last_instructions": last, "instruction_counts": dict(sorted(instructions.items())),
        "distinct_written_addresses": len(ram.writes), "write_events": ram.write_events,
        "written_low_high": [min(ram.writes), max(ram.writes)] if ram.writes else None,
        "ram_sha256": hashlib.sha256(memory).hexdigest(),
        "initial_conditions": {"ram": "zero except loaded PRG and processor-port defaults",
                               "a_x_y": [0, 0, 0], "status": 0x20, "stack": "SYS return sentinel $02ff",
                               "port_ddr": 0x2F, "port_latch": 0x37},
        "cpu_model_extensions": ["89: NMOS immediate NOP, 2 bytes, 2 cycles, no flags changed",
                                 "BF: NMOS LAX absolute,Y, load A/X and N/Z, 4 cycles plus page crossing"],
        "limitations": ["Flat RAM model; no hardware IO, interrupts or drive execution",
                        "No real-time, raster, music or drive-performance conclusion",
                        "A control transfer is not by itself proof of successful unpacking"],
    }
    (args.output / "bootstrap-execution.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("status", "steps", "stop_pc", "stop_opcode", "stop_registers",
                                            "distinct_written_addresses", "write_events", "ram_sha256")}, indent=2))
    raise SystemExit(0 if result["ram_postprocess_completed"] else 2)


if __name__ == "__main__":
    main()
