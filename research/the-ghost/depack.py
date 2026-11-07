#!/usr/bin/env python3
"""Call the release's original plain-depack API on statically extracted files.

The loader's literal resident copies are reproduced, then the source pointer
normally supplied by its receiver is provided by the host. No serial/drive
routine is called. Uninitialized reads stop the run instead of inventing RAM.
"""

import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

from py65.disassembler import Disassembler

from inspect_disk import OUTPUT, ROOT, digest


class Memory:
    def __init__(self, data, known):
        self.data, self.known = data, known
        self.pc = None
        self.writes = Counter()
        self.uninitialized = []

    def __getitem__(self, address):
        if not self.known[address]:
            self.uninitialized.append({"pc": self.pc, "read": address})
            raise RuntimeError("uninitialized_read")
        return self.data[address]

    def __setitem__(self, address, value):
        self.data[address], self.known[address] = value, 1
        self.writes[address] += 1


def contiguous(addresses):
    result = []
    for address in sorted(addresses):
        if result and address == result[-1][1]:
            result[-1][1] += 1
        else:
            result.append([address, address + 1])
    return result


def main():
    helper = ROOT / "research/next-round/analyze_boot.py"
    spec = importlib.util.spec_from_file_location("ghost_boot_cpu", helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class Cpu(module.BootCpu):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.instruct[0x0C] = self.nop_abs
            self.cycletime[0x0C] = 4
            self.disassemble[0x0C] = ("NOP", "abs")

        @staticmethod
        def nop_abs(cpu):
            cpu.ByteAt(cpu.WordAt(cpu.pc))
            cpu.pc += 2

    original = bytearray((OUTPUT / "bootstrap-ram.bin").read_bytes())
    assert digest(original) == "28568e19e8f4df3c07e94af53aa048a3951fec279039111dc4f86e58f08065ee"
    known_original = bytearray((OUTPUT / "bootstrap-known.bin").read_bytes())
    resident = bytearray(original)
    for x in range(256):
        resident[0x200 + x] = original[0x8701 + x]
        resident[0x2D9 + x] = original[0x87DA + x]
    assert resident[0x2E1:0x2E7] == bytes.fromhex("a9 60 a0 17 a2 00")
    out = OUTPUT / "depacked"
    out.mkdir(exist_ok=True)
    streams = json.loads((OUTPUT / "streams.json").read_text())["files"]
    receipts, failed = [], False
    for side in "ab":
        data, known = bytearray(original), bytearray(known_original)
        # Side B can depend on resident state from side A. Here it is an
        # independent audit; unknown references will stop and be reported.
        for entry in (row for row in streams if row["side"] == side):
            raw = (ROOT / entry["path"]).read_bytes()
            assert digest(raw) == entry["file_sha256"]
            load, packed = int.from_bytes(raw[:2], "little"), raw[2:]
            data[load:load + len(packed)] = packed
            known[load:load + len(packed)] = b"\1" * len(packed)
            data[0x200:0x3D9] = resident[0x200:0x3D9]
            known[0x200:0x3D9] = b"\1" * 0x1D9
            # Original receiver setup helper $022A writes these high bytes.
            for address in (0x2AF, 0x324, 0x387):
                data[address] = load & 255
            for address in (0x2B0, 0x325, 0x388):
                data[address] = load >> 8
            data[0], data[1] = 0x2F, 0x34
            known[0], known[1] = 1, 1
            ram = Memory(data, known)
            cpu = Cpu(memory=ram, pc=0x02E1)
            cpu.p, cpu.sp = cpu.UNUSED, 255
            cpu.stPushWord(0x1FFE)
            ram.writes.clear()
            status, steps, last = "step_limit", 0, []
            for steps in range(1_000_000):
                pc = cpu.pc
                if pc == 0x1FFF:
                    status = "returned"
                    break
                if not (0x02AE <= pc < 0x03D2) or 0x02C5 <= pc < 0x02D1:
                    status = "unexpected_control_transfer"
                    break
                opcode = data[pc]
                if cpu.instruct[opcode].__name__ == "inst_not_implemented":
                    status = "unsupported_opcode"
                    break
                last.append({"pc": pc, "opcode": opcode})
                last = last[-16:]
                ram.pc = pc
                try:
                    cpu.step()
                except RuntimeError as error:
                    status = str(error)
                    break
            target = int.from_bytes(packed[:2], "little")
            end = data[6] | data[7] << 8
            spans = contiguous(address for address in ram.writes if address >= 0x400)
            outputs = []
            stem = f"{side}-{entry['file']:03d}"
            for low, high in spans:
                path = out / f"{stem}-{low:04x}-{high:04x}.prg"
                path.write_bytes(low.to_bytes(2, "little") + data[low:high])
                outputs.append({"path": str(path.relative_to(ROOT)), "low": low, "end_exclusive": high,
                                "bytes": high - low, "sha256": digest(data[low:high])})
            (out / f"{stem}-ram.bin").write_bytes(data)
            receipt = {"side": side, "file": entry["file"], "status": status, "steps": steps,
                       "stop_pc": cpu.pc, "stop_opcode": data[cpu.pc], "packed_load": load,
                       "packed_bytes": len(packed), "input_sha256": entry["file_sha256"],
                       "header_target": target, "destination_pointer_end": end,
                       "outputs": outputs, "ram_sha256": digest(data),
                       "uninitialized_reads": ram.uninitialized, "last_instructions": last,
                       "source_cursor_base_high": data[0x2B0], "source_cursor_x": cpu.x}
            receipts.append(receipt)
            print(json.dumps({k: receipt[k] for k in ("side", "file", "status", "steps", "header_target", "destination_pointer_end", "uninitialized_reads")}), flush=True)
            if status != "returned":
                failed = True
                break
    result = {"pass": not failed and len(receipts) == len(streams), "script_sha256": digest(Path(__file__).read_bytes()),
              "cpu_helper_sha256": digest(helper.read_bytes()), "resident_sha256": digest(resident[0x200:0x3D9]),
              "files": receipts,
              "host_setup": {"entry": 0x2E1, "source_low_byte_operands": [0x2AF, 0x324, 0x387],
                             "source_high_byte_operands": [0x2B0, 0x325, 0x388],
                             "processor_port": 0x34, "return_sentinel": 0x1FFF},
              "limitations": ["Literal installer copy reproduced; drive and hardware loader never executed",
                              "Original plain-depack code unpatched beyond its documented source-pointer inputs",
                              "Flat RAM, no interrupts, hardware fetches, frame/cycle timing or release display",
                              "Files processed in directory order without original scene code; preserved earlier unpacked RAM is not a complete live machine state"]}
    (OUTPUT / "depack.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
