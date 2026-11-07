#!/usr/bin/env python3
"""Run the release's own resident Dali routine offline on extracted files.

The loader installation's literal copy is reproduced; entry $02DE is the
documented plain-depack path, with source pointer $04/$05 supplied by the host.
No disk/IO/IRQ/ROM code is executed. Original depacker bytes are not patched.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
from analyze_boot import BootCpu

ROOT = Path("build/research/next-round/boot-analysis")


class DaliCpu(BootCpu):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instruct[0xA7] = self.lax_zp
        self.cycletime[0xA7] = 3
        self.disassemble[0xA7] = ("LAX", "zpg")
        self.instruct[0x0C] = self.nop_abs
        self.cycletime[0x0C] = 4
        self.disassemble[0x0C] = ("NOP", "abs")

    @staticmethod
    def lax_zp(cpu):
        cpu.a = cpu.x = cpu.ByteAt(cpu.ZeroPageAddr())
        cpu.FlagsNZ(cpu.a)
        cpu.pc += 1

    @staticmethod
    def nop_abs(cpu):
        cpu.ByteAt(cpu.WordAt(cpu.pc))
        cpu.pc += 2


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
    directory = json.loads((ROOT / "bitfire-files.json").read_text())
    original = bytearray((ROOT / "unpacked/ram.bin").read_bytes())
    resident = bytearray(original)
    for x in range(256):
        resident[0x200 + x] = original[0x12BA + x]
        resident[0x2F9 + x] = original[0x13B3 + x]
    output = ROOT / "depacked-round3"
    output.mkdir(exist_ok=True)
    # Preserve already decompressed data for valid cross-file references.
    memory = bytearray(resident)
    receipts = []
    for entry in (x for x in directory if x["side"] == 3 and 1 <= x["file"] <= 10):
        blob = Path(entry["path"]).read_bytes()
        load = int.from_bytes(blob[:2], "little")
        payload = blob[2:]
        target = int.from_bytes(payload[:2], "little")
        memory[load:load + len(payload)] = payload
        # Fresh resident code: its normal self-modification is local to a call.
        memory[0x200:0x3F9] = resident[0x200:0x3F9]
        memory[4], memory[5] = load & 255, load >> 8
        ram = Ram(memory)
        cpu = DaliCpu(memory=ram, pc=0x02DE)
        cpu.p = cpu.UNUSED
        cpu.sp = 255
        cpu.stPushWord(0x1FFE)  # diagnostic RTS return $1FFF
        ram.writes.clear()
        status = "step_limit"
        for steps in range(2_000_000):
            if cpu.pc == 0x1FFF:
                status = "returned"
                break
            if not 0x0200 <= cpu.pc < 0x03F9:
                status = "unexpected_control_transfer"
                break
            if cpu.pc == 0x0240:
                status = "unexpected_hardware_loader_call"
                break
            opcode = memory[cpu.pc]
            if cpu.instruct[opcode].__name__ == "inst_not_implemented":
                status = "unsupported_opcode"
                break
            cpu.step()
        source_end = memory[4] | memory[5] << 8
        target_end = memory[7] | memory[8] << 8
        size = (target_end - target) & 65535
        data = bytes(memory[(target + i) & 65535] for i in range(size))
        stem = f"{entry['file']:03d}-{target:04x}"
        (output / (stem + ".prg")).write_bytes(target.to_bytes(2, "little") + data)
        (output / (stem + "-ram.bin")).write_bytes(memory)
        result = {
            "file": entry["file"], "status": status, "steps": steps,
            "pc": cpu.pc, "opcode": memory[cpu.pc], "load": load,
            "target": target, "source_end": source_end, "target_end": target_end,
            "output_bytes": size, "packed_bytes": len(payload),
            "packed_end": load + len(payload),
            "original_payload_sha256": hashlib.sha256(payload).hexdigest(),
            "output_sha256": hashlib.sha256(data).hexdigest(),
            "written_bytes": len(ram.writes),
            "scope": "Original resident plain-depack routine; flat RAM; no native hardware proof",
        }
        receipts.append(result)
        print(json.dumps(result), flush=True)
        if status != "returned":
            break
    (output / "receipts.json").write_text(json.dumps(receipts, indent=2) + "\n")


if __name__ == "__main__":
    main()
