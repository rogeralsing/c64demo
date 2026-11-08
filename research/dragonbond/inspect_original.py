#!/usr/bin/env python3
"""Inspect the unchanged Dragonbond D64 and run its RAM-only bootstrap.

Requires py65. No emulator, drive, ROM or downloaded host program is started.
The CPU model stops before original $2000, whose first stores access VIC IO.
All initial RAM except the original PRG and processor-port defaults is unknown;
an unknown read, ROM read, visible IO access or unimplemented opcode aborts.
"""

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import re
import sys
import tarfile
from collections import Counter
from pathlib import Path

from py65.devices.mpu6502 import MPU
from py65.disassembler import Disassembler


ROOT = Path(__file__).resolve().parents[2]
DISK_SHA256 = "37854b4e3426349ee03bc759f5bed8ad9a6c7f0404a469f1ae5163918cf50300"
PRG_SHA256 = "91e2aa52bcca8edda4dbf580709d294ff87deeb4a853aa2e14c2df9c92bb3fcc"
PDF_SHA256 = "b6ad3ad2e96dae340f995ac7f8dbd1012c4c773272ccaed44c36ba9ee64fde2f"
SNAPSHOT_READER_SHA256 = "c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a"
VICE_SOURCE_SHA256 = "8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1"


def sha256(blob):
    return hashlib.sha256(blob).hexdigest()


def spans(addresses):
    result = []
    for address in sorted(addresses):
        if result and result[-1][1] == address:
            result[-1][1] += 1
        else:
            result.append([address, address + 1])
    return result


def sector_offset(track, sector):
    sizes = [0] + [21] * 17 + [19] * 7 + [18] * 6 + [17] * 5
    assert 1 <= track <= 35 and 0 <= sector < sizes[track]
    return (sum(sizes[:track]) + sector) * 256


def extract_chain(disk, start):
    track, sector = start
    visited, result = [], bytearray()
    while track:
        assert [track, sector] not in visited, "Cyclic DOS chain"
        visited.append([track, sector])
        offset = sector_offset(track, sector)
        block = disk[offset:offset + 256]
        assert len(block) == 256
        next_track, next_sector = block[:2]
        result.extend(block[2:256 if next_track else next_sector + 1])
        track, sector = next_track, next_sector
    return bytes(result), visited


class KnownMemory:
    """Reject reads with no byte provenance and hardware-visible accesses."""

    def __init__(self, program):
        self.ram = bytearray(65536)
        self.known = bytearray(65536)
        load = int.from_bytes(program[:2], "little")
        self.ram[load:load + len(program) - 2] = program[2:]
        self.known[load:load + len(program) - 2] = b"\x01" * (len(program) - 2)
        self.ram[0:2] = bytes((0x2F, 0x37))
        self.known[0:2] = b"\x01\x01"
        self.pc = None
        self.reads = Counter()
        self.writes = Counter()
        self.output = bytearray(65536)
        self.output_events = bytearray()
        self.encoded_reads = []

    def pins(self):
        return (self.ram[1] & self.ram[0]) | (~self.ram[0] & 7)

    def check_access(self, address, write=False):
        assert 0 <= address < 65536
        pins = self.pins()
        if 0xD000 <= address < 0xE000 and pins & 3 and pins & 4:
            raise RuntimeError(f"Visible IO {'write' if write else 'read'} ${address:04x} at ${self.pc:04x}")
        if not write and ((0xA000 <= address < 0xC000 and pins & 3 == 3)
                          or (address >= 0xE000 and pins & 2)
                          or (0xD000 <= address < 0xE000 and pins & 3 and not pins & 4)):
            raise RuntimeError(f"Visible ROM read ${address:04x} at ${self.pc:04x}")

    def __getitem__(self, address):
        if isinstance(address, slice):
            return [self[x] for x in range(*address.indices(65536))]
        self.check_access(address)
        if not self.known[address]:
            raise RuntimeError(f"Unknown RAM read ${address:04x} at ${self.pc:04x}")
        self.reads[address] += 1
        if self.pc in (0x0041, 0x00AA, 0x00EF) and address >= 0xF900:
            self.encoded_reads.append(address)
        return self.ram[address]

    def __setitem__(self, address, value):
        self.check_access(address, write=True)
        self.ram[address] = value
        self.known[address] = 1
        self.writes[address] += 1
        if self.pc in (0x004A, 0x00DA):
            self.output[address] = 1
            self.output_events.extend((address & 255, address >> 8, value))


def listing(memory, lo, hi):
    disassembler = Disassembler(MPU(memory=memory))
    lines = []
    pc = lo
    while pc < hi:
        count, text = disassembler.instruction_at(pc)
        lines.append(f"{pc:04x}  {memory[pc:pc + count].hex(' '):8}  {text}")
        pc += count
    return "\n".join(lines) + "\n"


def capture_contexts(directory):
    """Bind saved filenames to the last reported original PC/clock in the log."""
    path = directory / "monitor.log"
    if not path.exists():
        return {}
    contexts, state, request = {}, None, None
    for line in path.read_text().splitlines():
        traced_request = re.match(r"\.C:06bb\s+.*- A:([0-9a-fA-F]{2})\s+.*\s+(\d+)\s*$", line)
        if traced_request:
            request = {"a": int(traced_request[1], 16), "clock": int(traced_request[2])}
        register = re.match(r"\.\;([0-9a-fA-F]{4})\s+.*\s+(\d+)\s*$", line)
        if register:
            state = {"pc": int(register[1], 16), "clock": int(register[2])}
            if request:
                state["latest_load_request"] = dict(request)
        save = re.match(r'(?:bsave|dump) "([^"]+)"', line)
        if save and state:
            contexts[Path(save[1]).name] = dict(state)
    return contexts


def snapshot_reader():
    path = ROOT / "research/quondam/snapshot_state.py"
    assert sha256(path.read_bytes()) == SNAPSHOT_READER_SHA256, "Audited snapshot reader changed"
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("dragonbond_passive_snapshot_reader", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def vic_source_rules(output):
    archive = ROOT / "build/research/quondam/hardware-source/vice-3.10.tar.gz"
    assert sha256(archive.read_bytes()) == VICE_SOURCE_SHA256
    guards = {
        "src/viciisc/vicii-fetch.c": [
            "vicii.sprite[i].pointer = fetch_phi1(v_fetch_addr(0x3f8 + i));",
            "sprdata = fetch_phi2((vicii.sprite[i].pointer << 6) + vicii.sprite[i].mc);",
            "sprdata = fetch_phi1((vicii.sprite[i].pointer << 6) + vicii.sprite[i].mc);",
            "vicii.sprite[i].mc &= 0x3f;", "vicii.sprite[i].data |= sprdata << 16;",
            "vicii.sprite[i].data |= sprdata << 8;", "vicii.sprite[i].data |= sprdata;"],
        "src/viciisc/vicii-cycle.c": [
            "vicii.sprite[i].mc = vicii.sprite[i].mcbase;",
            "vicii.sprite[i].mcbase = vicii.sprite[i].mc;",
            "if (vicii.sprite[i].mcbase == 63)", "vicii.sprite[i].mcbase = 0;",
            "vicii.prefetch_cycles = 3 + 1;"],
        "src/viciisc/vicii-chip-model.c": [
            "{ Phi1(58), 0x164, None,    SprPtr(0)",
            "{ Phi2(58), 0x168, None,    SprDma0(0)",
            "{ Phi1(59), 0x16c, None,    SprDma1(0)",
            "{ Phi2(59), 0x170, None,    SprDma2(0)", "cycle_tab_pal"],
        "src/vicii.h": ["#define VICII_MODEL_8565    1", "/* PAL, 63 cycle, 9 luma, \"new\" */"],
    }
    files = []
    with tarfile.open(archive, "r:gz") as tar:
        for name, needles in guards.items():
            member = "vice-3.10/" + name
            data = tar.extractfile(member).read()
            assert all(needle in data.decode() for needle in needles), name
            path = output / "vic-source" / Path(name).name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            files.append({"member": member, "sha256": sha256(data), "guarded_fragments": len(needles)})
    return {"url": "https://sourceforge.net/projects/vice-emu/files/releases/vice-3.10.tar.gz/",
            "archive_sha256": VICE_SOURCE_SHA256, "files": files,
            "interpretation": "PAL sprite0 pointer at cycle58 phi1, three data bytes through cycle59 phi2; MC advances by3",
            "prefetch_note": "The current prefetch counter returns to4 outside BA-low; it does not invalidate a completed earlier fetch"}


def traced_stores(directory, original):
    events, header = [], None
    for line in (directory / "monitor.log").read_text().splitlines():
        match = re.match(r"#\d+ \(Trace\s+store ([0-9a-fA-F]+)\)\s+(\d+)/\$[0-9a-fA-F]+,\s+(\d+)/\$[0-9a-fA-F]+", line)
        if match:
            header = {"target": int(match[1], 16), "line": int(match[2]), "cycle_zero_based": int(match[3])}
            continue
        match = re.match(r"\.C:([0-9a-fA-F]{4})\s+.*- A:([0-9a-fA-F]{2}) X:([0-9a-fA-F]{2}) Y:([0-9a-fA-F]{2}) SP:([0-9a-fA-F]{2})\s+\S+\s+(\d+)", line)
        if match and header:
            pc, a, x, y, sp, clock = [int(match[i], 16 if i < 6 else 10) for i in range(1, 7)]
            opcode = original[pc]
            value = {0x8D: a, 0x8C: y, 0x8E: x}.get(opcode)
            events.append({**header, "pc": pc, "a": a, "x": x, "y": y, "sp": sp,
                           "clock": clock, "opcode": opcode, "stored_value": value})
            header = None
    unique = {(e["clock"], e["pc"], e["target"]): e for e in events}
    return sorted(unique.values(), key=lambda e: e["clock"])


def passive_snapshots(directory):
    """Inspect saved VIC state only; never start VICE or advance the C64."""
    directory = directory.resolve()
    reader, contexts = snapshot_reader(), capture_contexts(directory)
    result = []
    for path in sorted(directory.glob("*.vsf")):
        snapshot = reader.read_snapshot(path)
        assert snapshot["modules"]["C64MEM"]["version"] == [0, 1]
        assert snapshot["modules"]["MAINCPU"]["version"] == [1, 4]
        memory = reader.module_payload(path, "C64MEM")
        cpu = reader.module_payload(path, "MAINCPU")
        ram = memory[4:65540]
        assert len(ram) == 65536
        clock, pc = int.from_bytes(cpu[:8], "little"), int.from_bytes(cpu[12:14], "little")
        if path.name in contexts:
            assert contexts[path.name]["pc"] == pc and contexts[path.name]["clock"] == clock, \
                "Snapshot disagrees with its original CPU stop context"
        ram_path = directory / ("ram-" + path.stem + ".bin")
        if ram_path.exists():
            assert ram_path.read_bytes() == ram, "Same-stop full physical RAM/VSF mismatch"
        vic, cia2 = snapshot["vicii"], snapshot["cia"]["CIA2"]
        # Both low CIA2 bits are outputs in this original; reject guessing pins
        # from the output latch when either bit has become an input.
        assert cia2["ddra"] & 3 == 3
        bank = (~cia2["pra"] & 3) * 0x4000
        screen = bank + ((vic["regs"][0x18] & 0xF0) << 6)
        pointer_table = screen + 0x3F8
        sprite = vic["sprites"][0]
        latched_data = (sprite["data"] & 0xFFFFFF).to_bytes(3, "big")
        # Sprite0 fetches at PAL cycles58..59 (hardware numbering). At a
        # complete-fetch stop away from those cycles, MC has advanced by3.
        # This is a candidate witness, not a blanket assertion: a bank write
        # after the latest fetch can legitimately make current-bank data differ.
        complete = (2 <= vic["raster_cycle"] <= 55 and sprite["mc"] >= 3
                    and sprite["mc"] % 3 == 0 and vic["sprite_dma"] & 1)
        candidate = None
        if complete:
            counter = sprite["mc"] - 3
            address = bank + sprite["pointer"] * 64 + counter
            expected = ram[address:address + 3]
            candidate = {"counter": counter, "row": counter // 3, "address": address,
                         "expected_current_bank_bytes": list(expected), "latched_data_bytes": list(latched_data),
                         "matches_current_bank": expected == latched_data}
        result.append({"snapshot": str(path.relative_to(ROOT)), "snapshot_sha256": sha256(path.read_bytes()),
                       "physical_ram_sha256": sha256(ram), "ram_pair_present_and_equal": ram_path.exists(),
                       "pc": pc, "clock": clock, "monitor_context": contexts.get(path.name),
                       "cpu": {"a": cpu[8], "x": cpu[9], "y": cpu[10], "sp": cpu[11], "p": cpu[14]},
                       "vic_model": vic["model"],
                       "raster_line": vic["raster_line"], "raster_cycle_zero_based": vic["raster_cycle"],
                       "processor_port_ddr": memory[1], "processor_port_latch": memory[0],
                       "cia2_pra": cia2["pra"], "cia2_ddra": cia2["ddra"], "vic_bank": bank,
                       "screen": screen, "pointer_table": pointer_table,
                       "prepared_pointer0": ram[pointer_table], "sprite0_y": vic["regs"][1],
                       "sprite0_enabled": bool(vic["regs"][0x15] & 1),
                       "sprite0_y_expanded": bool(vic["regs"][0x17] & 1),
                       "sprite0_multicolor": bool(vic["regs"][0x1C] & 1),
                       "sprite0_dma": bool(vic["sprite_dma"] & 1),
                       "sprite0_display": bool(vic["sprite_display_bits"] & 1),
                       "prefetch_cycles_at_stop": vic["prefetch_cycles"],
                       "sprite0": sprite, "complete_fetch_candidate": candidate,
                       "all_sprites": vic["sprites"],
                       "schema_source": snapshot["schema_source"]})
    return {"reader_sha256": SNAPSHOT_READER_SHA256, "snapshots": result,
            "scope": "Passive original VSF/physical-RAM/monitor-context inspection; no native advancement",
            "limits": ["Candidate latch comparison is restricted to complete sprite0 fetch phases",
                       "Current CIA2 bank need not be the bank used by an earlier latched fetch",
                       "No pixel scanout, border/priority composition or whole-demo conclusion"]}


def handover_acceptance(directory, survey, original, output):
    """Close only the retained original sprite0 handovers, with native latches."""
    directory = directory.resolve()
    named = {Path(x["snapshot"]).stem: x for x in survey["snapshots"]}
    specifications = [
        ("before-intermediate", 0x4000, 0x2D, 145, "old_tail", 0x2D, 0x3D),
        ("after-intermediate", 0x4000, 0x35, 145, "intermediate_old_tail", 0x2D, 0x3D),
        ("before-full-new", 0x4000, 0x35, 145, "intermediate_new_head", 0x3D, 0x2D),
        ("after-full-new", 0x4000, 0x3D, 145, "complete_new_head", 0x3D, 0x2D),
        ("before-next-intermediate", 0x4000, 0x3D, 166, "complete_new_tail", 0x3D, 0x35),
        ("bank80-after-intermediate", 0x8000, 0x18, 250, "intermediate_old_tail", 0x10, 0x20),
        ("bank80-before-full-new", 0x8000, 0x18, 250, "intermediate_new_head", 0x20, 0x10),
        ("bank80-after-full-new", 0x8000, 0x20, 250, "complete_new_head", 0x20, 0x10),
    ]
    missing = [name for name, *_ in specifications if name not in named]
    if missing:
        return {"complete": False, "missing": missing}
    tail = [x for x in named.values() if x["vic_bank"] == 0x8000 and x["prepared_pointer0"] == 0x20
            and x["sprite0"]["pointer"] == 0x20 and x["sprite0_y"] == 250
            and x["sprite0_dma"] and x["sprite0_display"] and x["complete_fetch_candidate"]
            and x["complete_fetch_candidate"]["counter"] >= 33
            and x["clock"] > named["bank80-after-full-new"]["clock"]]
    if tail:
        last = min(tail, key=lambda x: x["clock"])
        last_name = Path(last["snapshot"]).stem
        specifications.append((last_name, 0x8000, 0x20, 250, "complete_new_tail", 0x20, 0x18))
    reader, witnesses = snapshot_reader(), []
    for name, bank, pointer, y, role, expected_pointer, other_pointer in specifications:
        item = named[name]
        candidate = item["complete_fetch_candidate"]
        assert item["ram_pair_present_and_equal"] and candidate and candidate["matches_current_bank"]
        assert item["vic_model"] == 1 and item["processor_port_ddr"] == 0x2F and item["processor_port_latch"] == 0x35
        assert item["vic_bank"] == bank and item["pointer_table"] == bank + 0x3F8
        assert item["sprite0"]["pointer"] == item["prepared_pointer0"] == pointer
        assert item["sprite0_y"] == y and item["sprite0_dma"] and item["sprite0_display"]
        assert item["sprite0_enabled"] and not item["sprite0_y_expanded"]
        counter = candidate["counter"]
        assert counter >= 33 if role.endswith("tail") else counter < 33
        ram = reader.module_payload(ROOT / item["snapshot"], "C64MEM")[4:65540]
        assert ram[0x3000:0x3405] == original[0x3000:0x3405], "Original handover kernels changed"
        bases = (0x2D, 0x35, 0x3D) if bank == 0x4000 else (0x10, 0x18, 0x20)
        for base in bases:
            for sprite in range(8):
                address = bank + (base + sprite) * 64
                assert ram[address:address + 63] == original[address:address + 63], "Released sprite pixels changed"
        address = bank + expected_pointer * 64 + counter
        other_address = bank + other_pointer * 64 + counter
        data = bytes(candidate["latched_data_bytes"])
        assert data == original[address:address + 3]
        differs = data != original[other_address:other_address + 3]
        if role.startswith("intermediate_") or role == "complete_new_tail":
            assert differs, "Witness does not distinguish the intended image half"
        witnesses.append({"role": role, "snapshot": item["snapshot"], "snapshot_sha256": item["snapshot_sha256"],
                          "physical_ram_sha256": item["physical_ram_sha256"], "same_stop_full_ram_vsf_equal": True,
                          "pc": item["pc"], "cpu": item["cpu"], "clock": item["clock"],
                          "line": item["raster_line"], "cycle_zero_based": item["raster_cycle_zero_based"],
                          "field_base_clock": item["clock"] - item["raster_line"] * 63 - item["raster_cycle_zero_based"],
                          "bank": bank, "pointer": pointer, "y_register": y, "byte_counter": counter,
                          "row": counter // 3, "data_hex": data.hex(), "expected_full_pointer": expected_pointer,
                          "distinguishes_other_pointer": differs, "multicolor": item["sprite0_multicolor"],
                          "kernel_and_all_24_relevant_pixel_slots_original": True})
    for bank in (0x4000, 0x8000):
        assert len({x["field_base_clock"] for x in witnesses if x["bank"] == bank}) == 1
    stores = traced_stores(directory, original)

    def one(field, target, value, pc):
        found = [e for e in stores if field <= e["clock"] < field + 19656 and e["target"] == target
                 and e["stored_value"] == value and e["pc"] == pc]
        assert len(found) == 1, (field, target, value, pc, len(found))
        return found[0]

    field40 = next(x["field_base_clock"] for x in witnesses if x["bank"] == 0x4000)
    field80 = next(x["field_base_clock"] for x in witnesses if x["bank"] == 0x8000)
    trace40 = [one(field40, target, value, pc) for target, value, pc in
               ((0xD001, 124, 0x3279), (0x43F8, 0x2D, 0x3239), (0xD001, 145, 0x3279),
                (0x43F8, 0x35, 0x3239), (0x43F8, 0x3D, 0x3239))]
    trace80 = [one(field80, target, value, pc) for target, value, pc in
               ((0x83F8, 0x10, 0x3259), (0xD001, 229, 0x3279), (0xDD00, 0xC1, 0x33C9),
                (0xD001, 250, 0x3279), (0x83F8, 0x18, 0x3259), (0x83F8, 0x20, 0x3259))]
    assert all(a["clock"] < b["clock"] for chain in (trace40, trace80) for a, b in zip(chain, chain[1:]))
    groups = []
    for bank, bases in ((0x4000, (0x2D, 0x35, 0x3D)), (0x8000, (0x10, 0x18, 0x20))):
        for sprite in range(8):
            images = [original[bank + (base + sprite) * 64:bank + (base + sprite) * 64 + 63] for base in bases]
            assert images[1] == images[2][:33] + images[0][33:]
            groups.append({"bank": bank, "hardware_sprite": sprite,
                           "pointers": [base + sprite for base in bases], "split33_matches": True,
                           "split30_matches": images[1] == images[2][:30] + images[0][30:],
                           "pixel_sha256": [sha256(data) for data in images]})
    result = {"complete": True, "pass": True, "scope": "Original two-bank sprite0 intermediate handovers and native DMA latches",
              "producer_sha256": sha256(Path(__file__).read_bytes()), "original_scene41_ram_sha256": sha256(original),
              "snapshot_reader_sha256": SNAPSHOT_READER_SHA256,
              "witnesses": witnesses, "completed_store_trace_bank4000": trace40,
              "completed_store_trace_bank8000": trace80, "all_16_sprite_triples": groups,
              "source_rules": vic_source_rules(output), "monitor_sha256": sha256((directory / "monitor.log").read_bytes()),
              "optional_bank8000_complete_new_tail": {"observed": bool(tail),
                  "limit": "Additional main-loop-only raster267 checkpoint did not return; no tail capture or DMA continuity beyond the retained full-new head is claimed"},
              "separate_collection_receipts": [
                  {"path": str(path.relative_to(ROOT)), "sha256": sha256(path.read_bytes())}
                  for name in ("restore-check.json", "uncompleted-tail-observation.json", "owner-cleanup.json")
                  if (path := directory / name).exists()],
              "limits": ["No independent framebuffer/pixel/border/priority reconstruction",
                         "No nine-line timing-window or whole-demo-success measurement",
                         "The released split is33, not the PDF's simplified30; byte63 is excluded",
                         "Bank8000 sprite0 changes from hires to multicolor between retained samples"]}
    (output / "native-handover.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def bootstrap(program, max_steps):
    memory = KnownMemory(program)
    cpu = MPU(memory=memory, pc=0x081E)
    cpu.p, cpu.sp = cpu.UNUSED, 255
    instructions, last = Counter(), []
    relocated = None
    steps = 0
    while cpu.pc != 0x2000:
        assert steps < max_steps, "Instruction limit"
        pc = cpu.pc
        assert 0x081E <= pc <= 0x0845 or 0x0020 <= pc <= 0x011F, f"Unexpected PC ${pc:04x}"
        memory.pc = pc
        if pc == 0x0020 and relocated is None:
            relocated = bytes(memory.ram)
        opcode = memory[pc]
        assert cpu.instruct[opcode].__name__ != "inst_not_implemented", f"Unsupported opcode ${opcode:02x}"
        instructions[pc] += 1
        last.append(pc)
        last = last[-32:]
        cpu.step()
        steps += 1
    assert relocated is not None
    assert last[-4:] == [0x0100, 0x0102, 0x0103, 0x0105]
    assert memory.ram[0x2000:0x2005] == bytes.fromhex("a9 00 8d 20 d0")
    assert memory.encoded_reads == list(range(0xF961, 0x10000)), "Encoded bytes not read exactly once"
    return cpu, memory, relocated, {
        "entry": 0x081E, "stop_pc": cpu.pc, "steps": steps,
        "status": "Reached original JMP $2000; stopped before any $2000 instruction",
        "registers": {"a": cpu.a, "x": cpu.x, "y": cpu.y, "p": cpu.p, "sp": cpu.sp},
        "instruction_counts": {f"{k:04x}": v for k, v in sorted(instructions.items())},
        "last_pcs": last, "ram_sha256": sha256(memory.ram),
        "known_sha256": sha256(memory.known), "known_bytes": sum(memory.known),
        "written_ranges_exclusive": spans(memory.writes),
        "output_ranges_exclusive": spans(i for i, value in enumerate(memory.output) if value),
        "output_events": len(memory.output_events) // 3,
        "output_events_sha256": sha256(memory.output_events),
        "encoded_input_bytes": len(memory.encoded_reads),
        "encoded_input_range_exclusive": [0xF961, 0x10000],
        "encoded_input_consumed_once_in_order": True,
        "unknown_reads": 0, "visible_io_accesses": 0, "rom_reads": 0,
        "initial_conditions": {"port_ddr": 0x2F, "port_latch": 0x37,
                               "registers": "A=X=Y=0, P=$20, SP=$ff",
                               "ram": "Only loaded PRG and processor port known; every other read rejected"},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, default=ROOT / "build/research/frontier-20261108")
    parser.add_argument("--output", type=Path, default=ROOT / "build/research/dragonbond/original-analysis")
    parser.add_argument("--native", type=Path, default=ROOT / "build/research/dragonbond/native-01",
                        help="Optional retained native RAM directory; compare only when captures exist")
    parser.add_argument("--handover", type=Path, help="Optional additional saved native pointer/Y/DMA capture directory")
    parser.add_argument("--max-steps", type=int, default=2_000_000)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    disk = (args.inputs / "dragonbond.d64").read_bytes()
    other_disk = (args.inputs / "dragonbond-csdb.d64").read_bytes()
    pdf = (args.inputs / "dragonbond-making-of.pdf").read_bytes()
    assert len(disk) == 174848 and sha256(disk) == DISK_SHA256 and disk == other_disk
    assert len(pdf) == 2286989 and sha256(pdf) == PDF_SHA256
    program, chain = extract_chain(disk, (18, 2))
    assert len(program) == 2022 and sha256(program) == PRG_SHA256
    assert program == (args.inputs / "dragonbond-boot.prg").read_bytes()
    cpu, memory, relocated, run = bootstrap(program, args.max_steps)
    ram = memory.ram
    (args.output / "bootstrap-ram.bin").write_bytes(ram)
    (args.output / "bootstrap-known.bin").write_bytes(memory.known)
    (args.output / "bootstrap-output-writes.bin").write_bytes(memory.output_events)
    (args.output / "relocated-depacker.bin").write_bytes(relocated[0x20:0x120])
    original_ram = bytearray(65536)
    original_ram[0x0801:0x0801 + len(program) - 2] = program[2:]
    (args.output / "relocator.asm").write_text(listing(original_ram, 0x081E, 0x0846))
    (args.output / "depacker-relocated.asm").write_text(listing(relocated, 0x0020, 0x0108))
    (args.output / "loader-start.asm").write_text(listing(ram, 0x2000, 0x2025) + listing(ram, 0x1000, 0x1134))
    resident = bytearray(ram)
    # Exact $108f/$1095 loop semantics: X=0,ff,...,01; the second store wins
    # each overlap. This copies bytes only; installer IO/ROM calls are not run.
    for x in [0, *range(255, 0, -1)]:
        resident[0x0600 + x] = ram[0x16B3 + x]
        resident[0x06A7 + x] = ram[0x175A + x]
    assert resident[0x0600:0x07A7] == ram[0x16B3:0x185A]
    (args.output / "resident-loader-0600.bin").write_bytes(resident[0x0600:0x07A7])
    (args.output / "resident-loader.asm").write_text(listing(resident, 0x0600, 0x07A7))
    (args.output / "installer-drive-stage-0700.bin").write_bytes(ram[0x1161:0x11E1])
    (args.output / "installer-drive-body.bin").write_bytes(ram[0x11D6:0x16B3])
    native_comparisons = []
    contexts = capture_contexts(args.native)
    for filename, start, end, expected, expected_pc in (
        ("ram-boot-entry.bin", 0x0801, 0x0FE5, program[2:], 0x081E),
        ("ram-depacker-entry.bin", 0x0020, 0x0120, relocated[0x0020:0x0120], 0x0020),
        ("ram-loader-entry.bin", 0x1000, 0x2025, ram[0x1000:0x2025], 0x2000),
        ("ram-first-load-entry.bin", 0x0600, 0x07A7, resident[0x0600:0x07A7], 0x06BB),
    ):
        path = args.native / filename
        if path.exists():
            assert contexts[filename]["pc"] == expected_pc, "Capture filename disagrees with observed PC"
            native = path.read_bytes()
            assert len(native) == 65536
            actual = native[start:end]
            mismatches = sum(a != b for a, b in zip(actual, expected))
            assert len(actual) == len(expected) and mismatches == 0, f"Native mismatch: {filename}"
            native_comparisons.append({"path": str(path.relative_to(ROOT)), "ram_sha256": sha256(native),
                                       "capture": contexts[filename],
                                       "range_exclusive": [start, end], "compared_bytes": len(actual),
                                       "range_sha256": sha256(actual), "mismatches": mismatches})
    drive_comparisons = []
    drive_path = args.native / "drive-ram-first-load.bin"
    if drive_path.exists():
        assert contexts[drive_path.name]["pc"] == 0x06BB
        drive = drive_path.read_bytes()
        assert len(drive) == 2048
        for source, destination, length, expected_changes in (
            (0x1161, 0x0700, 128, {0x0756: [0x00, 0x04]}),
            (0x11D6, 0x0000, 1245, {0x00A5: [0xFF, 0x13], 0x0106: [0x00, 0x5A],
                                   0x0107: [0x00, 0x03], 0x01B5: [0xFE, 0x02],
                                   0x01CA: [0xFE, 0x02]}),
        ):
            original = ram[source:source + length]
            actual = drive[destination:destination + length]
            changes = {destination + i: [a, b] for i, (a, b) in enumerate(zip(original, actual)) if a != b}
            assert changes == expected_changes, "Unexpected installed drive bytes"
            drive_comparisons.append({"source_range_exclusive": [source, source + length],
                                      "destination_range_exclusive": [destination, destination + length],
                                      "compared_bytes": length, "unchanged_bytes": length - len(changes),
                                      "observed_changes": {f"{k:04x}": v for k, v in changes.items()}})
        (args.output / "native-drive-installed.asm").write_text(
            listing(bytearray(drive) + bytearray(65536 - len(drive)), 0x0350, 0x04DD))
        drive_comparisons = {"path": str(drive_path.relative_to(ROOT)), "bytes": len(drive),
                             "capture": contexts[drive_path.name],
                             "sha256": sha256(drive), "comparisons": drive_comparisons,
                             "changes_explained_by": ["$075a INC $0756 after each received page",
                                                      "$03fa STX $a5 establishes 19 sectors in the initial zone",
                                                      "$0358 JSR $0484 pushes $035a at stack $0106/$0107 with SP=$07",
                                                      "$0405/$0408 patch branch timing at $01b5/$01ca"]}
    scene_survey = []
    for name, filename, start, end, wait, exit_pc, exit_target in (
        ("3e", "ram-scene-3e-entry.bin", 0x2800, 0x2CC2, 0x28CC, 0x28D1, 0x0403),
        ("3f", "ram-scene-3f-entry.bin", 0x2800, 0x311E, 0x2832, 0x2835, 0x0406),
        ("42", "ram-scene-42-entry-valid.bin", 0x2800, 0x2D00, 0x28D6, 0x28EA, 0x040F),
        ("40", "ram-scene-40-entry.bin", 0x2800, 0x2EFA, 0x2832, 0x284E, 0x0409),
        ("41", "ram-scene-41-entry.bin", 0x2800, 0x2CAE, 0x2808, 0x281D, 0x040C),
    ):
        path = args.native / filename
        if path.exists():
            assert contexts[filename]["pc"] == start, "Scene filename disagrees with observed original PC"
            request = contexts[filename]["latest_load_request"]
            assert request["a"] == int(name, 16) and request["clock"] < contexts[filename]["clock"], \
                "Scene filename disagrees with observed original A-index load request"
            scene = bytearray(path.read_bytes())
            assert len(scene) == 65536
            assert scene[exit_pc:exit_pc + 3] == bytes((0x4C, exit_target & 255, exit_target >> 8))
            (args.output / f"scene-{name}-code.asm").write_text(listing(scene, start, end))
            scene_survey.append({"load_request_index": int(name, 16), "entry": start,
                                 "path": str(path.relative_to(ROOT)), "ram_sha256": sha256(scene),
                                 "capture": contexts[filename],
                                 "code_range_exclusive": [start, end], "wait_anchor": wait,
                                 "exit_jump": exit_pc, "exit_target": exit_target,
                                 "scope": "Static anchors from retained natural-entry RAM; no scene CPU execution"})
    sprite_checks = {}
    scene_path = args.native / "ram-scene-41-entry.bin"
    if scene_path.exists():
        scene = scene_path.read_bytes()
        assert contexts[scene_path.name]["pc"] == 0x2800
        assert contexts[scene_path.name]["latest_load_request"]["a"] == 0x41
        for address, code in (
            (0x305B, "a0 10 8c f8 43"), (0x3079, "a9 67 8d 01 d0"),
            (0x3099, "a0 1b 8c f8 43"), (0x30CA, "a0 20 8c f8 43"),
            (0x28F9, "ad 00 dd 29 fc 09 02 8d 00 dd"),
        ):
            expected = bytes.fromhex(code)
            assert scene[address:address + len(expected)] == expected

        def sprite(pointer):
            address = 0x4000 + pointer * 64
            return scene[address:address + 63]

        old, intermediate, successor = sprite(0x2D), sprite(0x35), sprite(0x3D)
        split = 33
        assert intermediate == successor[:split] + old[split:]
        assert len(set(intermediate[:split])) > 1 and len(set(intermediate[split:])) > 1
        valid_splits = [i for i in range(64) if intermediate == successor[:i] + old[i:]]
        valid_row_splits = [i for i in valid_splits if i % 3 == 0]
        assert valid_row_splits == [33], "Sprite0 transition no longer has its unique row-11 split"
        differences_at_pdf_split = [i for i in range(63) if intermediate[i] != (successor[:30] + old[30:])[i]]
        assert differences_at_pdf_split, "The PDF's simplified split unexpectedly became exact"
        images = []
        for label, pointer, image in (("old", 0x2D, old), ("intermediate", 0x35, intermediate),
                                      ("successor", 0x3D, successor)):
            path = args.output / f"sprite0-{pointer:02x}-{label}.bin"
            path.write_bytes(image)
            images.append({"role": label, "pointer": pointer, "address": 0x4000 + pointer * 64,
                           "pixel_bytes": len(image), "sha256": sha256(image), "hex": image.hex()})
        group = []
        for hardware_sprite in range(8):
            a, b, c = (sprite(base + hardware_sprite) for base in (0x2D, 0x35, 0x3D))
            assert b == c[:33] + a[33:]
            group.append({"hardware_sprite": hardware_sprite, "pointers": [0x2D + hardware_sprite,
                           0x35 + hardware_sprite, 0x3D + hardware_sprite],
                          "byte33_composite": True, "byte30_composite": b == c[:30] + a[30:],
                          "old_sha256": sha256(a), "intermediate_sha256": sha256(b), "new_sha256": sha256(c)})
        (args.output / "scene-41-sprite-kernels.asm").write_text(listing(bytearray(scene), 0x3000, 0x33CC))
        sprite_checks = {
            "source": str(scene_path.relative_to(ROOT)), "source_sha256": sha256(scene),
            "capture": contexts[scene_path.name], "bank": 0x4000, "pointer_table": 0x43F8,
            "scope": "Released bytes and original code publication anchors; not a DMA/raster execution trace",
            "preferred_pair": {"hardware_sprite": 0, "old_y": 124, "next_y": 145,
                           "pointers": [0x2D, 0x35, 0x3D], "unique_row_split": 33,
                           "valid_byte_splits": valid_splits,
                           "new_head_range_exclusive": [0, 33], "old_tail_range_exclusive": [33, 63],
                           "images": images, "literal_pdf_split30_matches": False,
                           "literal_pdf_split30_mismatch_offsets": differences_at_pdf_split,
                           "original_store_anchors": {"old_y": 0x3279, "old_pointer": 0x3239,
                                                      "next_y": 0x3279, "intermediate_pointer": 0x3239,
                                                      "successor_pointer": 0x3239},
                           "original_call_sites": {"old_y": 0x30FB, "old_pointer": 0x3150,
                                                   "next_y": 0x3156, "intermediate_pointer": 0x315B,
                                                   "successor_pointer": 0x319E},
                           "irq_handlers": {"old_y": 0x2935, "old_pointer": 0x2944,
                                            "next_y_and_intermediate": 0x2953, "successor": 0x2962},
                           "irq_programmed_lines": {"old_y": 114, "old_pointer": 122,
                                                    "next_y_and_intermediate": 136, "successor": 144}},
            "complete_group": {"old_y": 124, "next_y": 145, "split": 33,
                                      "all_eight_composites_match": True, "sprites": group},
            "limits": ["64th byte of each sprite slot is excluded",
                       "Programmed IRQ lines are not completed-store raster/cycle positions",
                       "The actual released byte-33 split differs from the PDF's simplified byte-30 example",
                       "Active native RAM and pointer/Y store trace must establish this data is fetched"],
        }
    handover_survey = passive_snapshots(args.handover) if args.handover else None
    if args.handover:
        assert scene_path.exists(), "The original retained scene41 RAM is required for native handover validation"
    native_handover = handover_acceptance(args.handover, handover_survey, scene_path.read_bytes(), args.output) \
        if args.handover else None
    evidence = {
        "producer": {"path": str(Path(__file__).relative_to(ROOT)), "sha256": sha256(Path(__file__).read_bytes()),
                     "py65_version": importlib.metadata.version("py65")},
        "sources": {"group_disk": "https://englishclass.de/~wolf/ac/assets/downloads/demos/the-dragonbond.d64",
                    "csdb_disk": "https://csdb.dk/getinternalfile.php/280588/the-dragonbond.d64",
                    "author_pdf": "https://englishclass.de/~wolf/ac/assets/downloads/demos/the-dragonbond-making_of.pdf"},
        "disk": {"bytes": len(disk), "sha256": sha256(disk), "two_original_bodies_equal": True},
        "pdf": {"bytes": len(pdf), "sha256": sha256(pdf), "intermediate_example_printed_page": 7},
        "boot_chain": {"start": [18, 2], "sectors": chain, "bytes": len(program), "sha256": sha256(program),
                       "load": 0x0801, "basic_sys": 2078},
        "bootstrap": run,
        "anchors": {"basic_entry": 0x081E, "relocated_depacker": 0x0020,
                    "bootstrap_exit": 0x2000, "loader_install": 0x1000,
                    "request_first_file_a_zero": 0x06BB, "first_file_target": 0x0400,
                    "receive": 0x061F, "literal_output_store": 0x06FD,
                    "match_output_store": 0x0775},
        "resident_loader": {"copied_source_range_exclusive": [0x16B3, 0x185A],
                            "destination_range_exclusive": [0x0600, 0x07A7],
                            "sha256": sha256(resident[0x0600:0x07A7]),
                            "copy_only_not_installer_execution": True},
        "native_comparisons": native_comparisons,
        "native_drive_comparisons": drive_comparisons,
        "scene_survey": scene_survey,
        "released_sprite_checks": sprite_checks,
        "passive_handover_snapshots": handover_survey,
        "native_handover_acceptance": native_handover,
        "rejected_filename_contexts": {name: context for name, context in contexts.items()
                                       if name == "ram-scene-42-entry.bin" and context["pc"] != 0x2800},
        "limitations": ["No emulator/drive execution, machine advancement, IEC transport or ROM execution in this producer",
                        "No packer/loader family inferred from a byte pattern or author statement",
                        "First file bytes and sprite schedule require the separately retained native capture",
                        "Linear listings may include embedded data and unimplemented undocumented-opcode renderings"],
    }
    (args.output / "original-analysis.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps({"pass": True, "steps": run["steps"], "stop_pc": run["stop_pc"],
                      "output_ranges_exclusive": run["output_ranges_exclusive"],
                      "ram_sha256": run["ram_sha256"], "resident_loader_sha256": evidence["resident_loader"]["sha256"],
                      "native_handover_complete": native_handover["complete"] if native_handover else None}, indent=2))


if __name__ == "__main__":
    main()
