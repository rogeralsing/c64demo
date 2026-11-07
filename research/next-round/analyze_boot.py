#!/usr/bin/env python3
"""Bounded, flat-RAM execution of Next Round's identical DOS entry depacker.

No VICE, drive model, interrupts, ROM, or native timing. Stop before the first
instruction at the unpacked $0900 handoff. Original PRG bytes are not patched.
"""
import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
from pathlib import Path
from py65.devices.mpu6502 import MPU
from py65.disassembler import Disassembler

EXPECTED = "a5441eea42eab6f7bbe9566403cf5eae9b86e2e17dbdadeca7813ad6ae6682ec"


class BootCpu(MPU):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instruct = list(self.instruct)
        self.cycletime = list(self.cycletime)
        self.extracycles = list(self.extracycles)
        self.disassemble = list(self.disassemble)
        for opcode, method, cycles, name, mode in (
            (0xB7, self.lax_zpy, 4, "LAX", "zpy"),
            (0xC7, self.dcp_zp, 5, "DCP", "zpg"),
        ):
            self.instruct[opcode] = method
            self.cycletime[opcode] = cycles
            self.disassemble[opcode] = (name, mode)

    @staticmethod
    def lax_zpy(cpu):
        cpu.a = cpu.x = cpu.ByteAt(cpu.ZeroPageYAddr())
        cpu.FlagsNZ(cpu.a)
        cpu.pc += 1

    @staticmethod
    def dcp_zp(cpu):
        address = cpu.ZeroPageAddr()
        value = (cpu.ByteAt(address) - 1) & 255
        cpu.memory[address] = value
        result = cpu.a - value
        cpu.p &= ~(cpu.CARRY | cpu.ZERO | cpu.NEGATIVE)
        if result >= 0:
            cpu.p |= cpu.CARRY
        cpu.FlagsNZ(result & 255)
        cpu.pc += 1


class Ram:
    def __init__(self, data):
        self.data = data
        self.writes = Counter()

    def __getitem__(self, address):
        return self.data[address]

    def __setitem__(self, address, value):
        self.data[address] = value
        self.writes[address] += 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("build/research/next-round/boot-analysis/round1-bootstrap.prg"))
    parser.add_argument("--output", type=Path, default=Path("build/research/next-round/boot-analysis/unpacked"))
    args = parser.parse_args()
    blob = args.input.read_bytes()
    assert len(blob) == 2487 and hashlib.sha256(blob).hexdigest() == EXPECTED
    memory = bytearray(65536)
    load = int.from_bytes(blob[:2], "little")
    memory[load:load + len(blob) - 2] = blob[2:]
    memory[0], memory[1] = 0x2F, 0x37
    ram = Ram(memory)
    cpu = BootCpu(memory=ram, pc=0x080D)
    cpu.p = cpu.UNUSED
    cpu.sp = 255
    counts = Counter()
    trace = []
    status = "step_limit"
    for steps in range(2_000_000):
        pc, opcode = cpu.pc, memory[cpu.pc]
        if pc == 0x0900:
            status = "handoff_0900"
            break
        if cpu.instruct[opcode].__name__ == "inst_not_implemented":
            status = "unsupported_opcode"
            break
        trace.append({"pc": pc, "opcode": opcode, "a": cpu.a, "x": cpu.x, "y": cpu.y, "p": cpu.p, "sp": cpu.sp})
        trace = trace[-32:]
        counts[pc] += 1
        cpu.step()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "ram.bin").write_bytes(memory)
    receipt = {
        "status": status, "steps": steps, "stop_pc": cpu.pc,
        "stop_opcode": memory[cpu.pc], "input_sha256": EXPECTED,
        "ram_sha256": hashlib.sha256(memory).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "py65_version": importlib.metadata.version("py65"),
        "last_instructions": trace, "instruction_counts": dict(sorted(counts.items())),
        "distinct_written_addresses": len(ram.writes),
        "scope": "Flat-RAM depacker analysis; no hardware, native timing, drive, or ROM proof",
        "extensions": ["B7 LAX zero-page,Y", "C7 DCP zero page"],
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    dis = Disassembler(cpu)
    listing = []
    for start, end in ((0x0900, 0x1000), (0x1000, 0x1B00)):
        address = start
        while address < end:
            count, instruction = dis.instruction_at(address)
            listing.append(f"{address:04x}  {memory[address:address+count].hex(' '):9}  {instruction}")
            address += count
    (args.output / "listing.txt").write_text("\n".join(listing) + "\n")
    print(json.dumps({k: receipt[k] for k in ("status", "steps", "stop_pc", "stop_opcode", "ram_sha256")}, indent=2))


if __name__ == "__main__":
    main()
