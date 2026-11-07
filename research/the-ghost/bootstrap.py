#!/usr/bin/env python3
"""Bounded original bootstrap CPU execution; stop before unpacked entry code."""

import hashlib
import importlib.metadata
import importlib.util
import json
from collections import Counter
from pathlib import Path

from py65.disassembler import Disassembler


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "build/research/the-ghost"
BOOT_SHA256 = "6feb3cfa5e6ae767d1e9a60c3d03b2d58fbb31a86843fdf8e0faa4d91fc7e1c4"


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Ram:
    def __init__(self, blob):
        self.data = bytearray(65536)
        load = int.from_bytes(blob[:2], "little")
        self.data[load:load + len(blob) - 2] = blob[2:]
        self.data[0], self.data[1] = 0x2F, 0x37
        self.writes = Counter()
        self.pc = None
        self.io = []

    def visible_io(self):
        pins = (self.data[1] & self.data[0]) | (~self.data[0] & 7)
        return bool(pins & 3) and bool(pins & 4)

    def __getitem__(self, address):
        if 0xD000 <= address < 0xE000 and self.visible_io():
            self.io.append({"pc": self.pc, "read": address})
            raise RuntimeError("hardware-visible IO read")
        return self.data[address]

    def __setitem__(self, address, value):
        if 0xD000 <= address < 0xE000 and self.visible_io():
            self.io.append({"pc": self.pc, "write": address, "value": value})
            raise RuntimeError("hardware-visible IO write")
        self.data[address] = value
        self.writes[address] += 1


def main():
    helper = ROOT / "research/next-round/analyze_boot.py"
    spec = importlib.util.spec_from_file_location("ghost_existing_boot_cpu", helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = OUTPUT / "dos-files/a/000.prg"
    blob = source.read_bytes()
    assert len(blob) == 2680 and digest(blob) == BOOT_SHA256
    ram = Ram(blob)
    cpu = module.BootCpu(memory=ram, pc=0x081E)
    cpu.p, cpu.sp = cpu.UNUSED, 255
    trace, counts = [], Counter()
    status, steps = "step_limit", 0
    for steps in range(500_000):
        pc = cpu.pc
        if not (0x081E <= pc < 0x0846 or 0x0020 <= pc < 0x0120):
            status = "transfer_outside_bootstrap"
            break
        opcode = ram.data[pc]
        if cpu.instruct[opcode].__name__ == "inst_not_implemented":
            status = "unsupported_opcode"
            break
        trace.append({"pc": pc, "opcode": opcode, "a": cpu.a, "x": cpu.x, "y": cpu.y,
                      "p": cpu.p, "sp": cpu.sp})
        trace = trace[-32:]
        ram.pc = pc
        counts[pc] += 1
        try:
            cpu.step()
        except RuntimeError as error:
            status = str(error)
            break
    (OUTPUT / "bootstrap-ram.bin").write_bytes(ram.data)
    known = bytearray(65536)
    known[0x801:0x801 + len(blob) - 2] = b"\1" * (len(blob) - 2)
    for address in ram.writes:
        known[address] = 1
    (OUTPUT / "bootstrap-known.bin").write_bytes(known)
    dis = Disassembler(cpu)
    listings = {}
    for name, low, high in (("bootstrap-relocated", 0x20, 0x120), ("unpacked-entry", cpu.pc, min(cpu.pc + 0x900, 65536))):
        pc, lines = low, []
        while pc < high:
            length, instruction = dis.instruction_at(pc)
            lines.append(f"{pc:04x} {ram.data[pc:pc + length].hex(' '):9} {instruction}")
            pc += length
        (OUTPUT / (name + ".txt")).write_text("\n".join(lines) + "\n")
        listings[name] = {"low": low, "end_exclusive": high}
    result = {"status": status, "steps": steps, "stop_pc": cpu.pc, "stop_opcode": ram.data[cpu.pc],
              "input_sha256": BOOT_SHA256, "script_sha256": digest(Path(__file__).read_bytes()),
              "cpu_helper": str(helper.relative_to(ROOT)), "cpu_helper_sha256": digest(helper.read_bytes()),
              "py65_version": importlib.metadata.version("py65"),
              "ram_sha256": digest(ram.data), "known_sha256": digest(known),
              "written_addresses": len(ram.writes), "io_accesses": ram.io,
              "instruction_counts": dict(sorted(counts.items())), "last_instructions": trace,
              "listings": listings,
              "initial_conditions": "Zero RAM except original PRG and processor-port DDR=$2F/latch=$37; A=X=Y=0,P=$20,SP=$FF",
              "limitations": ["Original bytes are unpatched; existing CPU helper supplies NMOS B7/C7 semantics",
                              "Flat RAM with visible-IO guard; no VIC, CIA, ROM, interrupts, drive, serial bus or timing model",
                              "An out-of-bootstrap transfer alone is not proof of a valid complete demo load"]}
    (OUTPUT / "bootstrap.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("status", "steps", "stop_pc", "stop_opcode", "ram_sha256", "written_addresses", "io_accesses")}, indent=2))


if __name__ == "__main__":
    main()
