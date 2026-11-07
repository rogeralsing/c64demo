#!/usr/bin/env python3
"""Offline The Lab side-two bootstrap and Bitfire directory investigation.

Original bootstrap instructions execute in flat py65 RAM until a new entry is
reached. Custom files use the pinned Bitfire producer's metadata/sector order,
not the decorative DOS directory. No VICE or hardware protocol is run.
"""

import argparse
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

from py65.devices.mpu6502 import MPU


ROOT = Path(__file__).resolve().parents[2]
DISK_SHA = "d34101d9b5852020ed56b3574aae854c7b16befff893df77a6d6ec08198cdf3b"
BOOT_SHA = "a1d61674083c1c8f5b7e7532a0b6709ebdd897375ba26d23e0892042ebe25d78"
SECTORS = [0] + [21] * 17 + [19] * 7 + [18] * 6 + [17] * 10
BITFIRE_COMMIT = "5a3964b533656332c12cc0904f2ce92f44499c6f"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class Cpu(MPU):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instruct = list(self.instruct)
        self.cycletime = list(self.cycletime)
        self.instruct[0xC7] = self.dcp_zp
        self.cycletime[0xC7] = 5
        self.instruct[0xA7] = self.lax_zp
        self.cycletime[0xA7] = 3
        self.instruct[0x0C] = self.nop_abs
        self.cycletime[0x0C] = 4

    @staticmethod
    def dcp_zp(cpu):
        address = cpu.ByteAt(cpu.pc)
        value = (cpu.memory[address] - 1) & 255
        cpu.memory[address] = value
        cpu.p = (cpu.p & ~cpu.CARRY) | (cpu.a >= value)
        cpu.FlagsNZ((cpu.a - value) & 255)
        cpu.pc += 1

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
        self.pc = 0
        self.writes = Counter()
        self.io_accesses = []
        self.output_addresses = set()
        self.known = bytearray(65536)
        self.unknown_backrefs = []

    def io_visible(self):
        pins = self.data[1] & self.data[0] | ~self.data[0] & 7
        return bool((pins & 3) and (pins & 4))

    def __getitem__(self, address):
        if isinstance(address, int) and 0xD000 <= address < 0xE000 and self.io_visible():
            self.io_accesses.append([self.pc, "read", address])
            raise RuntimeError("Hardware-visible IO")
        return self.data[address]

    def __setitem__(self, address, value):
        if 0xD000 <= address < 0xE000 and self.io_visible():
            self.io_accesses.append([self.pc, "write", address])
            raise RuntimeError("Hardware-visible IO")
        self.data[address] = value
        self.writes[address] += 1
        if self.pc in (0x0385, 0x03C9):
            self.output_addresses.add(address)
            self.known[address] = 1


def bootstrap(blob, output):
    assert sha(blob) == BOOT_SHA
    memory = bytearray(65536)
    load = int.from_bytes(blob[:2], "little")
    memory[load:load + len(blob) - 2] = blob[2:]
    memory[0], memory[1] = 0x2F, 0x37
    ram = Ram(memory)
    cpu = Cpu(memory=ram, pc=0x080D)
    cpu.p, cpu.sp = cpu.UNUSED, 255
    cpu.stPushWord(0x02FE)
    ram.writes.clear()
    status = "instruction_limit"
    trace = []
    for steps in range(3_000_000):
        pc = cpu.pc
        if not (0x080D <= pc < 0x081B or 0x0003 <= pc < 0x00B8):
            status = "transfer_outside_bootstrap"
            break
        opcode = memory[pc]
        if cpu.instruct[opcode].__name__ == "inst_not_implemented":
            status = "unsupported_opcode"
            break
        trace.append([pc, opcode, cpu.a, cpu.x, cpu.y, cpu.p, cpu.sp])
        trace = trace[-24:]
        ram.pc = pc
        try:
            cpu.step()
        except RuntimeError:
            status = "hardware_io_dependency"
            break
    (output / "bootstrap-ram.bin").write_bytes(memory)
    result = {"status": status, "instructions": steps, "stop_pc": cpu.pc,
              "stop_opcode": memory[cpu.pc], "ram_sha256": sha(memory),
              "distinct_written_addresses": len(ram.writes), "io_accesses": ram.io_accesses,
              "last_instructions": trace,
              "cpu_extension": "C7 DCP zero page (decrement memory, compare A; stable NMOS semantics)",
              "initial_conditions": "Flat zero RAM, PRG, DDR2F/latch37, A/X/Y0, binary arithmetic/carry0, SYS sentinel02FF",
              "scope": "Original bootstrap only; no VICE, disk/IEC/drive/ROM execution"}
    (output / "bootstrap.json").write_text(json.dumps(result, indent=2) + "\n")
    return memory, result


def sector(disk, track, index):
    assert 1 <= track <= 40 and 0 <= index < SECTORS[track]
    start = (sum(SECTORS[:track]) + index) * 256
    return disk[start:start + 256]


def extract_bitfire(disk, output):
    assert sha(disk) == DISK_SHA
    order = []
    for track in range(1, 41):
        if track == 18:
            continue
        interleave = 4 if track < 18 else 3
        for residue in range(interleave):
            order.extend((track, index) for index in range(residue, SECTORS[track], interleave))
    stream = b"".join(sector(disk, *position) for position in order)
    directory = []
    (output / "packed").mkdir(exist_ok=True)
    for directory_sector in (18, 17):
        table = sector(disk, 18, directory_sector)
        if not table[0]:
            continue
        start_track, consumed_slots, byte_offset, side = table[:4]
        first_slot = next(i for i, (t, _) in enumerate(order) if t == start_track)
        cursor = (first_slot + consumed_slots) * 256 + byte_offset
        for index in range(63):
            fields = [table[4 + index + stripe * 63] for stripe in range(4)]
            if not any(fields):
                break
            low, high_minus_one, size_low, size_high = fields
            load = low | ((high_minus_one + 1) & 255) << 8
            length = (size_low | size_high << 8) + 1
            payload = stream[cursor:cursor + length]
            assert len(payload) == length and load + length <= 65536
            number = index + (63 if directory_sector == 17 else 0)
            path = output / "packed" / f"{number:02d}-{load:04x}.prg"
            path.write_bytes(load.to_bytes(2, "little") + payload)
            directory.append({"file": number, "directory_sector": directory_sector,
                              "side_byte": side, "load": load, "bytes": length,
                              "end_exclusive": load + length, "stream_offset": cursor,
                              "first_disk_sector": list(order[cursor // 256]),
                              "offset_in_first_sector": cursor % 256,
                              "payload_sha256": sha(payload), "path": str(path),
                              "payload_first16": payload[:16].hex(" ")})
            cursor += length
    (output / "bitfire-files.json").write_text(json.dumps(directory, indent=2) + "\n")
    return directory


def depack_entries(initial, entries, output):
    # Reproduce only the installer's two literal RAM copies, not its hardware
    # detection, serial upload, drive installation or raster-wait paths.
    resident = bytearray(initial)
    for x in range(256):
        resident[0x200 + x] = initial[0x3ABA + x]
        resident[0x2F9 + x] = initial[0x3BB3 + x]
    (output / "resident-0200-03f8.bin").write_bytes(resident[0x200:0x3F9])
    memory = bytearray(resident)
    known = bytearray(65536)
    results = []
    directory = output / "depacked"
    directory.mkdir(exist_ok=True)
    for entry in entries:
        blob = Path(entry["path"]).read_bytes()
        load, payload = int.from_bytes(blob[:2], "little"), blob[2:]
        assert sha(payload) == entry["payload_sha256"]
        memory[load:load + len(payload)] = payload
        memory[0x200:0x3F9] = resident[0x200:0x3F9]
        memory[2], memory[3] = load & 255, load >> 8
        memory[0], memory[1] = 0x2F, 0x34  # all-RAM plain-depack context
        ram = Ram(memory)
        ram.known[:] = known
        ram.known[load:load + len(payload)] = b"\x01" * len(payload)
        cpu = Cpu(memory=ram, pc=0x02DE)
        cpu.p, cpu.sp = cpu.UNUSED, 255
        cpu.stPushWord(0x1FFE)
        ram.writes.clear()
        status = "instruction_limit"
        for steps in range(3_000_000):
            pc = cpu.pc
            if pc == 0x1FFF:
                status = "returned"
                break
            if not 0x0200 <= pc < 0x03F9:
                status = "unexpected_control_transfer"
                break
            if pc == 0x0240:
                status = "unexpected_hardware_loader_call"
                break
            if cpu.instruct[memory[pc]].__name__ == "inst_not_implemented":
                status = "unsupported_opcode"
                break
            ram.pc = pc
            if pc == 0x03C6:
                address = (int.from_bytes(memory[0x3C7:0x3C9], "little") + cpu.y) & 65535
                if not ram.known[address] and len(ram.unknown_backrefs) < 16:
                    ram.unknown_backrefs.append(address)
            try:
                cpu.step()
            except RuntimeError:
                status = "hardware_io_dependency"
                break
        addresses = sorted(ram.output_addresses)
        segments = []
        for address in addresses:
            if not segments or segments[-1][1] != address:
                segments.append([address, address + 1])
            else:
                segments[-1][1] += 1
        stem = f"{entry['file']:02d}"
        for low, high in segments:
            (directory / f"{stem}-{low:04x}-{high-1:04x}.prg").write_bytes(low.to_bytes(2, "little") + memory[low:high])
        (directory / f"{stem}.ram.bin").write_bytes(memory)
        (directory / f"{stem}.written.bin").write_bytes(bytes(int(i in ram.output_addresses) for i in range(65536)))
        result = {"file": entry["file"], "status": status, "instructions": steps,
                  "stop_pc": cpu.pc, "stop_opcode": memory[cpu.pc],
                  "source_start": load, "source_end": int.from_bytes(memory[2:4], "little"),
                  "packed_end": load + len(payload),
                  "output_ranges": segments, "output_bytes": len(addresses),
                  "unknown_backref_examples": ram.unknown_backrefs, "io_accesses": ram.io_accesses,
                  "output_sha256": sha(bytes(memory[a] for a in addresses)),
                  "ram_path": str(directory / f"{stem}.ram.bin")}
        results.append(result)
        print(json.dumps({k: result[k] for k in ("file", "status", "instructions", "output_ranges", "unknown_backref_examples")}), flush=True)
        known = ram.known
        if status != "returned":
            break
    (output / "depacked-files.json").write_text(json.dumps(results, indent=2) + "\n")
    return results


def run_to(cpu, target, limit=5000):
    count = 0
    while cpu.pc != target:
        assert count < limit, f"Instruction limit at ${cpu.pc:04x}"
        opcode = cpu.memory[cpu.pc]
        assert cpu.instruct[opcode].__name__ != "inst_not_implemented", f"Unsupported ${opcode:02x}"
        cpu.step()
        count += 1
    return count


def span_candidate_contract(output):
    memory = bytearray((output / "depacked/15.ram.bin").read_bytes())
    expected_rows = bytes(64 * (y // 21) + 3 * (y % 21) for y in range(84))
    assert memory[0x8E61:0x8EB5] == expected_rows
    assert memory[0x8072:0x8132] == bytes(x // 8 for x in range(192))
    assert memory[0x8200:0x82C0] == bytes(255 >> (x & 7) for x in range(192))
    assert memory[0x8300:0x83C0] == bytes((255 << (7 - (x & 7))) & 255 for x in range(192))
    cpu = Cpu(memory=memory)
    cpu.p, cpu.sp, cpu.pc = 0x20, 255, 0x5901
    cpu.stPushWord(0x1FFE)
    run_to(cpu, 0x1FFF)
    memory[0x61] = 0xD0
    cpu.sp, cpu.pc = 255, 0x5938
    cpu.stPushWord(0x1FFE)
    run_to(cpu, 0x1FFF)
    # Independent sprite-shaped mapping: three columns per 256-byte block,
    # four 21-row sprites per column, with one unused byte after each sprite.
    def address(column, row):
        return 0xD000 + (column // 3) * 256 + column % 3 + 64 * (row // 21) + 3 * (row % 21)
    initial = bytes(((i * 37 + 19) ^ 0xA5) & 255 for i in range(2048))
    all_spans = [(left, right, 20, 8, 0) for left in range(192) for right in range(left, 192)]
    extra = set()
    for row in (0, 20, 21, 41, 42, 62, 63, 83):
        for material in (0, 1, 7, 8, 15):
            for phase in (0, 4):
                for left in (0, 1, 6, 7, 8, 22, 23, 24, 63, 80, 183, 191):
                    for width in (1, 2, 7, 8, 9, 17, 64, 192):
                        extra.add((left, min(191, left + width - 1), row, material, phase))
    instructions = 0
    for left, right, row, material, phase in all_spans + sorted(extra):
        base = 0x8400 + (material // 2) * 256 + (material & 1) * 88 + phase
        pattern = memory[base + row]
        memory[0x59C9:0x59CB] = base.to_bytes(2, "little")
        memory[0xD000:0xD800] = initial
        wanted = bytearray(initial)
        first, last = left // 8, right // 8
        for column in range(first, last + 1):
            offset = address(column, row) - 0xD000
            if first == last:
                wanted[offset] |= pattern & (255 >> (left & 7)) & ((255 << (7 - (right & 7))) & 255)
            elif column == first:
                wanted[offset] |= pattern & (255 >> (left & 7))
            elif column == last:
                wanted[offset] |= pattern & ((255 << (7 - (right & 7))) & 255)
            else:
                wanted[offset] = pattern
        cpu.pc, cpu.a, cpu.x, cpu.y, cpu.p = 0x59B0, right, left, row, 0x20
        instructions += run_to(cpu, 0x5B0D)
        assert memory[0xD000:0xD800] == wanted, (left, right, row, material, phase)
    patterns = []
    for material in range(16):
        base = 0x8400 + (material // 2) * 256 + (material & 1) * 88
        assert all(memory[base + row] == memory[base + row % 4] for row in range(88))
        patterns.append({"material": material, "base": base,
                         "first8rows": list(memory[base:base + 8]),
                         "four_row_ones": sum(x.bit_count() for x in memory[base:base + 4])})
    result = {"pass": True, "source_snapshot": "depacked/15.ram.bin",
              "candidate_only_not_visual_stage_identification": True,
              "span_entry": 0x59B0, "stop_before_continuation": 0x5B0D,
              "same_byte_and_split_span_core": [0x3651, 0x36B9],
              "inputs": "X=left pixel, A=right pixel inclusive, Y=row0..83",
              "pointer_setup_entries": [0x5901, 0x5938],
              "logical_span_domain": [192, 84], "pointer_columns": 24,
              "row_map_formula": "64*(y//21)+3*(y%21)",
              "column_map_formula": "(column//3)*256+column%3",
              "all_horizontal_spans_at_row20_material8": len(all_spans),
              "additional_sprite_boundary_material_phase_cases": len(extra),
              "total_cases": len(all_spans) + len(extra), "original_instructions": instructions,
              "contract": "OR masked boundary bytes; direct replacement of complete interior byte columns",
              "pattern_pointer_formula": "8400+(material//2)*256+(material%2)*88+phase(0 or4)",
              "pattern_period_rows": 4,
              "pattern_storage_rows": 88,
              "patterns": patterns,
              "scope": "Isolated original RAM-only span primitive, caller-supplied buffer/pattern inputs; not native display proof"}
    (output / "span-candidate-validation.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def candidate_listings(output, utility):
    specifications = [
        (15, "span-edge-and-interior", 0x3651, 0x36B9),
        (15, "span-edge-steppers", 0x3423, 0x3651),
        (15, "span-fast-chunks", 0x4CF5, 0x4E40),
        (15, "span-dispatch", 0x5901, 0x5C06),
        (15, "pattern-selection", 0x7E1B, 0x7F08),
        (0, "side2-main-controller", 0x0480, 0x053F),
        (3, "span-candidate-handoff", 0x28A7, 0x2A6A),
        (15, "span-candidate-controller", 0x7C89, 0x7D43),
        (16, "engine16-entry", 0x2600, 0x26F0),
        (19, "engine19-tile-compositor", 0x3B00, 0x3C17),
        (20, "engine20-entry", 0x2000, 0x20EF),
    ]
    for number, name, start, end in specifications:
        memory = (output / f"depacked/{number:02d}.ram.bin").read_bytes()
        pc, lines = start, []
        while pc < end:
            item = utility.decode(memory, pc)
            lines.append(f"{pc:04x}: {item['bytes']:<8} {item['mnemonic']} {item['text']}")
            pc = item["next"]
        (output / (name + ".asm")).write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "build/research/the-lab")
    args = parser.parse_args()
    root = args.root.resolve()
    output = root / "side2-analysis"
    output.mkdir(exist_ok=True)
    memory, boot = bootstrap((root / "side2-bootstrap.prg").read_bytes(), output)
    entries = extract_bitfire((root / "release/side2.d64").read_bytes(), output)
    depacked = depack_entries(memory, entries, output) if boot["status"] == "transfer_outside_bootstrap" else []
    utility = module(ROOT / "research/tower-power/static_loader.py", "nmos_disassembly")
    span = span_candidate_contract(output) if len(depacked) == 25 and all(x["status"] == "returned" for x in depacked) else None
    candidate_listings(output, utility) if span else None
    if boot["status"] == "transfer_outside_bootstrap":
        pc = boot["stop_pc"]
        lines = []
        for _ in range(120):
            item = utility.decode(memory, pc)
            lines.append(f"{pc:04x}: {item['bytes']:<8} {item['mnemonic']} {item['text']}")
            pc = item["next"]
        (output / "entry.asm").write_text("\n".join(lines) + "\n")
    result = {"script_sha256": sha(Path(__file__).read_bytes()), "disk_sha256": DISK_SHA,
              "bootstrap_sha256": BOOT_SHA, "bootstrap": boot,
              "bitfire_format_source_commit": BITFIRE_COMMIT,
              "directory_entries": len(entries), "packed_payload_bytes": sum(x["bytes"] for x in entries),
              "extraction_scope": "Pinned producer-format interpretation; all extracted files return through The Lab's original resident plain depacker. No native disk/drive protocol or displayed-stage identity is proved.",
              "depacked": depacked,
              "span_candidate": span,
              "entries": entries}
    (output / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"bootstrap_status": boot["status"],
                      "bootstrap_instructions": boot["instructions"],
                      "directory_entries": len(entries),
                      "packed_payload_bytes": result["packed_payload_bytes"],
                      "depack_instructions": sum(x["instructions"] for x in depacked),
                      "span_cases": span["total_cases"] if span else None}, indent=2))


if __name__ == "__main__":
    main()
