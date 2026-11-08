#!/usr/bin/env python3
"""Passively audit the closed Dragonbond native03 full-successor tail witness."""

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tarfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "build/research/dragonbond"
CAPTURE = BASE / "native-03"
OUTPUT = BASE / "native-tail-analysis"
PARENT_SHA = "79a7cd97a25334167698fac3603037c6069e2c3d98e6de7ce3b1824bf3f86ea1"
CASE_SHA = "a66338ad4ed9ba55cd78369ffd4c20fbbce578e92ec62b71e639dbfae70449c6"
PINS = {
    "research/verify_vice_live.py": "f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a",
    "research/vice_session_live.py": "4340d1b0394fa612f5e6a71edddcbc2daf947e59c4c3013ab3b850c886dc621c",
    "research/quondam/snapshot_state.py": "c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a",
    "build/research/vice-live-verification/verification/verification.json": "a9e38e278e3ebee0cf492ad75e7b0a00d66d31e116ac3709e2d7987d35fc3e77",
    "build/research/dragonbond/native-analysis/native-evidence.json": "f6be9f8c2e9acf40199743fe49f74c03137ca0d83935a2c4caea0b65721113e1",
    "build/research/dragonbond/original-analysis/original-analysis.json": "ad4d83c3d32dcc341e9ad8bcdbc510957d4a668368d659b06ad5ec7aa3ea87cb",
    "build/research/dragonbond/original-analysis/native-handover.json": "450f867d9bfbfcb492aeec4fdbeb8252b604d2e6bbf4576143788d9626698c25",
    "build/research/frontier-20261108/dragonbond.d64": "37854b4e3426349ee03bc759f5bed8ad9a6c7f0404a469f1ae5163918cf50300",
    "build/research/quondam/hardware-source/vice-3.10.tar.gz": "8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=sha(data))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cpu(snapshot, reader):
    data = reader.module_payload(snapshot, "MAINCPU")
    result = dict(clock=int.from_bytes(data[:8], "little"), a=data[8], x=data[9], y=data[10], sp=data[11],
                  pc=int.from_bytes(data[12:14], "little"), flags=data[14])
    memory = reader.module_payload(snapshot, "C64MEM")
    state = reader.read_snapshot(snapshot)
    result.update(port00=memory[1], port01=memory[0], line=state["vicii"]["raster_line"],
                  cycle=state["vicii"]["raster_cycle"])
    return result, memory, state


def source_rules():
    archive = ROOT / "build/research/quondam/hardware-source/vice-3.10.tar.gz"
    guards = {
        "vicii-fetch.c": [
            "vicii.sprite[i].pointer = fetch_phi1(v_fetch_addr(0x3f8 + i));",
            "sprdata = fetch_phi2((vicii.sprite[i].pointer << 6) + vicii.sprite[i].mc);",
            "sprdata = fetch_phi1((vicii.sprite[i].pointer << 6) + vicii.sprite[i].mc);",
            "vicii.sprite[i].mc &= 0x3f;", "vicii.sprite[i].data |= sprdata << 16;",
            "vicii.sprite[i].data |= sprdata << 8;", "vicii.sprite[i].data |= sprdata;"],
        "vicii-cycle.c": ["vicii.sprite[i].mc = vicii.sprite[i].mcbase;",
                          "vicii.sprite[i].mcbase = vicii.sprite[i].mc;"],
        "vicii-chip-model.c": [
            "cycle_tab_pal", "{ Phi1(1),  0x194, None,    SprPtr(3)",
            "{ Phi1(3),  0x1a4, None,    SprPtr(4)", "{ Phi1(5),  0x1b4, None,    SprPtr(5)",
            "{ Phi1(7),  0x1c4, None,    SprPtr(6)", "{ Phi1(9),  0x1d4, None,    SprPtr(7)",
            "{ Phi1(58), 0x164, None,    SprPtr(0)", "{ Phi1(60), 0x174, None,    SprPtr(1)",
            "{ Phi1(62), 0x184, None,    SprPtr(2)"],
    }
    files = []
    with tarfile.open(archive, "r:gz") as tar:
        for name, needles in guards.items():
            member = "vice-3.10/src/viciisc/" + name
            data = tar.extractfile(member).read()
            assert all(needle in data.decode() for needle in needles), name
            target = OUTPUT / "vic-source" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            files.append(dict(member=member, guarded_fragments=len(needles), **artifact(target)))
    return dict(archive=artifact(archive), files=files,
                url="https://sourceforge.net/projects/vice-emu/files/releases/vice-3.10.tar.gz/",
                interpretation="At267/raw11 all eight saved sprite triplets are complete: sprite0..2 fetched late in line266, sprite3..7 early in line267.")


def main():
    for path, digest in PINS.items():
        assert sha((ROOT / path).read_bytes()) == digest, ("Changed input", path)
    wire = load("dragonbond_tail_wire_auditor", "research/verify_vice_live.py")
    # Configure a fresh in-memory reader instance for this closed case. This
    # neither rewrites nor reruns the frozen observer-verification receipt.
    wire.BASE, wire.CASE_PINS = BASE, {"native-03": CASE_SHA}
    case = wire.audit_session("native-03")
    reader = load("dragonbond_tail_snapshot_reader", "research/quondam/snapshot_state.py")
    parent = BASE / "native-02/bank80-after-full-new.vsf"
    assert sha(parent.read_bytes()) == PARENT_SHA
    owner = json.loads((BASE / "native-analysis/native-evidence.json").read_text())
    assert owner["pass"]
    parent_record = next(row for session in owner["sessions"] for row in session["checkpoints"]
                         if row["snapshot"]["path"] == str(parent.relative_to(ROOT)))
    assert parent_record["snapshot"] == artifact(parent)
    handover = json.loads((BASE / "original-analysis/native-handover.json").read_text())
    assert handover["pass"] and not handover["optional_bank8000_complete_new_tail"]["observed"]
    original_receipt = json.loads((BASE / "original-analysis/original-analysis.json").read_text())
    original_entry = next(row for row in original_receipt["scene_survey"] if row["load_request_index"] == 0x41)
    original_path = ROOT / original_entry["path"]
    original = original_path.read_bytes()
    assert len(original) == 65536 and sha(original) == original_entry["ram_sha256"]
    assert handover["original_scene41_ram_sha256"] == sha(original)
    records, contexts, last_registers, commands = [], {}, None, []
    for sequence, row in case["queued"].items():
        command = row["command"]
        commands.append(command)
        response = case["responses"][sequence]
        assert response["status"] == "completed" and "interrupt" not in response
        if command == "r":
            last_registers = wire.registers(response["response"])
        if command.startswith(("bsave ", "dump ")):
            filename = command.split('"')[1]
            assert last_registers is not None
            contexts[Path(filename).name] = dict(last_registers)
    expected_commands = ["r", "sidefx off", f'undump "{parent}"', "bank ram", "r",
                         f'bsave "{CAPTURE / "ram-restored-bank80.bin"}" 0 0000 ffff', "r",
                         f'dump "{CAPTURE / "restored-bank80.vsf"}"',
                         "break exec 0000 ffff if RL == $10b", "warp", 'resourceget "Speed"', "x", "r",
                         f'bsave "{CAPTURE / "ram-bank80-new-tail.bin"}" 0 0000 ffff', "r",
                         f'dump "{CAPTURE / "bank80-new-tail.vsf"}"']
    assert commands == expected_commands
    assert not case["partial"] and not case["waits"] and not case["cancelled"]
    assert case["session"]["command"][case["session"]["command"].index("-8") + 1] == str(ROOT / "build/research/frontier-20261108/dragonbond.d64")
    # Live response events include the trailing prompt; the older sequential
    # transcript parser returned prompt-free command response rows.
    assert wire.PROMPT.sub(b"", case["responses"][10]["response"].encode()).strip() == b"Warp mode is off."
    assert wire.PROMPT.sub(b"", case["responses"][11]["response"].encode()).strip() == b"Speed=100"
    assert "Stop on  exec 12a9" in case["responses"][12]["response"]
    assert "267/$10b" in case["responses"][12]["response"]
    expected = {"restored-bank80": (0x3278, 149028238, 255, 37),
                "bank80-new-tail": (0x12a9, 149028968, 267, 11)}
    captures = {}
    for stem, stop in expected.items():
        snapshot, ram_path = CAPTURE / (stem + ".vsf"), CAPTURE / ("ram-" + stem + ".bin")
        registers, memory, state = cpu(snapshot, reader)
        assert registers == contexts[snapshot.name] == contexts[ram_path.name]
        assert (registers["pc"], registers["clock"], registers["line"], registers["cycle"]) == stop
        assert (registers["port00"], registers["port01"]) == (0x2f, 0x35)
        assert memory[4:65540] == ram_path.read_bytes() and len(ram_path.read_bytes()) == 65536
        assert state["modules"]["MAINCPU"]["version"] == [1, 4]
        assert state["modules"]["C64MEM"]["version"] == [0, 1] and state["vicii"]["model"] == 1
        captures[stem] = (memory[4:65540], state, registers)
        records.append(dict(stem=stem, ram=artifact(ram_path), snapshot=artifact(snapshot), registers=registers))
    restored = CAPTURE / "restored-bank80.vsf"
    restore_modules = ("C64MEM", "MAINCPU", "CIA1", "CIA2", "VIC-II")
    for module in restore_modules:
        assert reader.module_payload(parent, module) == reader.module_payload(restored, module)
    restore_check = json.loads((CAPTURE / "restore-check.json").read_text())
    assert restore_check["pass"] and restore_check["parent_sha256"] == PARENT_SHA
    before, pre, cpu0 = captures["restored-bank80"]
    after, post, cpu1 = captures["bank80-new-tail"]
    assert cpu1["clock"] - cpu0["clock"] == (cpu1["line"] - cpu0["line"]) * 63 + cpu1["cycle"] - cpu0["cycle"] == 730
    assert pre["vicii"]["regs"] == post["vicii"]["regs"]
    for key in ("pra", "prb", "ddra", "ddrb", "cra", "crb"):
        assert pre["cia"]["CIA2"][key] == post["cia"]["CIA2"][key]
    regs, cia2 = post["vicii"]["regs"], post["cia"]["CIA2"]
    assert (cia2["pra"], cia2["ddra"]) == (0xc1, 0x3f) and cia2["ddra"] & 3 == 3
    bank = (~cia2["pra"] & 3) * 0x4000
    pointer_table = bank + ((regs[0x18] & 0xf0) << 6) + 0x3f8
    assert bank == 0x8000 and pointer_table == 0x83f8
    assert before[pointer_table:pointer_table + 8] == after[pointer_table:pointer_table + 8] == bytes(range(0x20, 0x28))
    assert regs[1:16:2] == [250] * 8 and regs[0x17] == 0 and regs[0x1c] == 0xe7
    assert post["vicii"]["sprite_dma"] == post["vicii"]["sprite_display_bits"] == 255
    assert before[0x3000:0x3405] == after[0x3000:0x3405] == original[0x3000:0x3405]
    slot_checks, witnesses = [], []
    for base in (0x10, 0x18, 0x20):
        for sprite in range(8):
            address = bank + (base + sprite) * 64
            assert before[address:address + 63] == after[address:address + 63] == original[address:address + 63]
            slot_checks.append(dict(pointer=base + sprite, first=address, bytes=63, sha256=sha(original[address:address + 63])))
    expected_latches = ("000000", "2a808c", "f80aa8", "e4a000", "000001", "eaacfc", "f00c80", "080000")
    for sprite, latch_hex in enumerate(expected_latches):
        actual = post["vicii"]["sprites"][sprite]
        assert (actual["pointer"], actual["mc"], actual["mcbase"], actual["exp_flop"]) == (0x20 + sprite, 51, 48, 1)
        counter = actual["mc"] - 3
        address = bank + actual["pointer"] * 64 + counter
        old_address = bank + (0x10 + sprite) * 64 + counter
        intermediate_address = bank + (0x18 + sprite) * 64 + counter
        data = (actual["data"] & 0xffffff).to_bytes(3, "big")
        assert counter == 48 and data.hex() == latch_hex and data == original[address:address + 3]
        assert data == after[address:address + 3]
        old_data = original[old_address:old_address + 3]
        assert old_data == original[intermediate_address:intermediate_address + 3] and data != old_data
        witnesses.append(dict(sprite=sprite, pointer=actual["pointer"], MC=51, MCBASE=48,
                              byte_offset=counter, row=counter // 3, source_address=address, data_hex=data.hex(),
                              old_pointer=0x10 + sprite, old_data_hex=old_data.hex(), distinguishes_old_and_intermediate=True,
                              multicolor=bool(regs[0x1c] & (1 << sprite))))
    assert after[0x12a9:0x12ac] == original[0x12a9:0x12ac] == bytes.fromhex("b9 06 23")
    assert after[0x2a6b:0x2a6e] == original[0x2a6b:0x2a6e] == bytes.fromhex("20 06 10")
    assert cpu1["sp"] == 0xf1 and after[0x1f2:0x1f4] == bytes.fromhex("6d 2a")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rejected = OUTPUT / "rejected-prompt-guard"
    assert sha((rejected / "native_tail.py").read_bytes()) == "16749a7e4b1b69539956904ac101a9ade16ad466fe7bacd87f017b210249aa02"
    result = dict(pass_=True, script=artifact(Path(__file__).resolve()),
                  input_pins=[artifact(ROOT / path) for path in PINS], original_scene41_RAM=artifact(original_path),
                  parent=artifact(parent), parent_record=parent_record, wire_audit=wire.summary(case),
                  checkpoints=records, restore=dict(complete_equal_modules=list(restore_modules), owner_check=artifact(CAPTURE / "restore-check.json")),
                  elapsed_cycles=730, native_resumes=1, declared_restores=1, code_data_or_PC_writes_other_than_restore=[],
                  final_bank=bank, final_pointer_table=pointer_table, final_multicolor_mask=0xe7,
                  endpoint_equal_VIC_registers=True, endpoint_equal_CIA2_ports_and_configuration=True,
                  kernel_range=dict(first=0x3000, end_exclusive=0x3405, sha256=sha(original[0x3000:0x3405])),
                  endpoint_original_sprite_slots=slot_checks, witnesses=witnesses, VIC_source=source_rules(),
                  observed_music_call_context=dict(pc=0x12a9, instruction="LDA $2306,Y", callsite=0x2a6b,
                                                   call="JSR $1006", stack_return=0x2a6d, stack_addresses=[0x1f2, 0x1f3]),
                  previous_failed_collection_unchanged=True,
                  rejected_checker_guard=[artifact(rejected / "native_tail.py"), artifact(rejected / "failure.json")],
                  last_valid_continuation=artifact(CAPTURE / "bank80-new-tail.vsf"),
                  limits=["Endpoint identity does not prove no transient bank, pointer, register or artwork change throughout730cycles; no native store trace was collected.",
                          "Eight actual saved data latches close the successor-tail data gap; this is not a pixel, border, color or priority reconstruction.",
                          "The old native02 missed main-loop-only observation remains failed and unchanged. This separate continuation does not certify its entire missed interval.",
                          "The new267 stop is inside the $1006 call with saved return$2a6d, consistent with music occupying the requested raster position.",
                          "Raw monitor observer coordinates and retained snapshot phases do not establish individual physical-chip bus-write phases.",
                          "No continuous DMA history, whole-demo FPS, physical-hardware equivalence or helper-process exit code is claimed."])
    result["pass"] = result.pop("pass_")
    target = OUTPUT / "native-tail-evidence.json"
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"pass": True, "sprites": len(witnesses), "elapsed_cycles": 730,
                      "capture_pairs": len(records), "receipt": artifact(target)}, indent=2))


if __name__ == "__main__":
    main()
