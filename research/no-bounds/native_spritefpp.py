#!/usr/bin/env python3
"""Passively audit original No Bounds SpriteFPP snapshots and retained wire.

No emulator, CPU, assembler, subprocess or live connection is started.
"""

import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import re
import sys
import tarfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "build/research/no-bounds"
CAPTURE = BASE / "native-02"
OUTPUT = BASE / "native-spritefpp-analysis"
DISK = BASE / "original/zip-members/NoBounds-GP-Side1.d64"
CASE_SHA = "7ba2f44ed1dc2775e6db09dd239a64a26a03c261f0f20728904d95e22e425033"
PINS = {
    "research/verify_vice_live.py": "f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a",
    "research/vice_session_live.py": "4340d1b0394fa612f5e6a71edddcbc2daf947e59c4c3013ab3b850c886dc621c",
    "research/quondam/snapshot_state.py": "c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a",
    "build/research/no-bounds/original-analysis/original-binding.json": "c4f25403d9c737ec15873d7bb2aee4a4175a0af76151f5924a49230c3d474373",
    "build/research/no-bounds/original-analysis/side1-bundle031.ram": "8a1affa7e2d58061214ba5e0af0388ece30d8cc501611a643f1194b2a99f929d",
    "build/research/no-bounds/original-analysis/side1-bundle031.known": "0dcd551960cab15fad234f9bc6d53a937ee6b60ca2a12877e57ddc532690e3d3",
    "build/research/no-bounds/original-analysis/side1-boot.prg": "40cd90f462434ea395d1c03e09d5cb6336186ab2229e4889c4d3abb48a2816ea",
    "build/research/no-bounds/original/zip-members/NoBounds-GP-Side1.d64": "f603e03f94ed4df416584419a696e1832b0710308de8faf2d0179b0a7725fe70",
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
    assert len(data) >= 15
    registers = dict(clock=int.from_bytes(data[:8], "little"), a=data[8], x=data[9],
                     y=data[10], sp=data[11], pc=int.from_bytes(data[12:14], "little"), flags=data[14])
    memory = reader.module_payload(snapshot, "C64MEM")
    state = reader.read_snapshot(snapshot)
    registers.update(port00=memory[1], port01=memory[0], line=state["vicii"]["raster_line"],
                     cycle=state["vicii"]["raster_cycle"])
    assert state["modules"]["MAINCPU"]["version"] == [1, 4]
    assert state["modules"]["C64MEM"]["version"] == [0, 1]
    return registers, memory[4:65540], state


def wire_case():
    """Reuse the pinned wire proof with one explicit startup-contract adaptation.

    The frozen auditor accepts only its original manually loaded cases. This
    run instead uses the original disk's ordinary autostart. All serialization,
    raw-byte coverage, timeout, interruption and close checks remain identical.
    """
    if CASE_SHA is None:
        raise RuntimeError("Native case is not closed and pinned yet")
    wire = load("spritefpp_wire_reader", "research/verify_vice_live.py")
    wire.BASE, wire.CASE_PINS = BASE, {"native-02": CASE_SHA}
    source = inspect.getsource(wire.audit_session)
    before = 'assert session["startup_mode"] == "manual monitor load" and "-autostart" not in session["command"]'
    after = ('assert session["startup_mode"] == "autostart"\n'
             '    assert session["command"].count("-autostart") == 1\n'
             f'    assert session["command"][session["command"].index("-autostart") + 1] == {str(DISK)!r}')
    assert source.count(before) == 1
    adapted = source.replace(before, after)
    exec(compile(adapted, "<pinned-wire-auditor-autostart-contract>", "exec"), wire.__dict__)
    case = wire.audit_session("native-02")
    command = case["session"]["command"]
    assert case["session"]["program"] == str(DISK)
    assert command[command.index("-8") + 1] == str(DISK)
    assert "-pal" in command and "+autostart-warp" in command and "-drive8truedrive" in command
    assert command[command.index("-speed") + 1] == "100"
    return wire, case, dict(original_function_sha256=sha(source.encode()),
                            adapted_function_sha256=sha(adapted.encode()),
                            replaced_assertion=before, replacement_assertions=after,
                            reason="Original disk autostart replaces only the manual-start metadata contract")


def capture_contexts(wire, case):
    """Require explicit stationary CPU/VIC coordinates for both files in a pair."""
    contexts, last = {}, None
    for sequence, queued in case["queued"].items():
        response = case["responses"].get(sequence)
        if response is None:
            continue
        command = queued["command"]
        if command == "r":
            last = wire.registers(response["response"])
        if command.startswith(("bsave ", "dump ")):
            assert response["status"] == "completed" and last is not None
            filename = Path(command.split('"')[1])
            assert filename.parent == CAPTURE
            assert filename.name not in contexts
            contexts[filename.name] = dict(last)
        if command in ("x", "exit"):
            last = None
    return contexts


def captures(reader, contexts):
    records, decoded = [], {}
    for snapshot in sorted(CAPTURE.glob("*.vsf")):
        stem = snapshot.stem
        ram_path = CAPTURE / ("ram-" + stem + ".bin")
        registers, ram, state = cpu(snapshot, reader)
        assert len(ram) == 65536 and ram_path.read_bytes() == ram
        assert registers == contexts[snapshot.name] == contexts[ram_path.name]
        assert state["vicii"]["model"] == 1  # PAL MOS8565 in this owned VICE run.
        records.append(dict(stem=stem, ram=artifact(ram_path), snapshot=artifact(snapshot), registers=registers))
        decoded[stem] = (registers, ram, state)
    assert len(contexts) == 2 * len(records)
    return records, decoded


def bank_state(state):
    vic, cia = state["vicii"], state["cia"]["CIA2"]
    pins = (cia["pra"] | (~cia["ddra"] & 255)) & 3
    bank = (~pins & 3) * 0x4000
    pointers = bank + ((vic["regs"][0x18] & 0xf0) << 6) + 0x3f8
    return dict(pra=cia["pra"], ddra=cia["ddra"], pulled_up_low_pins=pins,
                bank=bank, pointer_table=pointers)


TRACE = re.compile(
    r"(?m)^#(\d+) \(Trace store ([0-9a-fA-F]{4})\)\s+(\d+)/\$[0-9a-fA-F]+,\s+(\d+)/\$[0-9a-fA-F]+\n"
    r"\.C:([0-9a-fA-F]{4})\s+([^\n]+?)\s+- A:([0-9a-fA-F]{2}) X:([0-9a-fA-F]{2}) "
    r"Y:([0-9a-fA-F]{2}) SP:([0-9a-fA-F]{2}) ([NV\-BDIZC.]{8})\s+(\d+)\s*$")


def trace_rows(case):
    rows = []
    for sequence, response in case["responses"].items():
        for match in TRACE.finditer(response["response"]):
            values = match.groups()
            checkpoint, address, line, cycle, pc = (int(values[i], 16 if i in (1, 4) else 10)
                                                   for i in range(5))
            instruction = values[5].strip()
            a, x, y, sp = (int(value, 16) for value in values[6:10])
            store = re.search(r"\b(STA|STX|STY)\s+\$([0-9a-fA-F]{4})\b", instruction)
            value = {"STA": a, "STX": x, "STY": y}[store[1]] if store else None
            if store:
                assert int(store[2], 16) == address
            rows.append(dict(response_sequence=sequence, trace_checkpoint=checkpoint, target=address,
                             observer_line=line, observer_raw_cycle=cycle, pc=pc,
                             instruction=instruction, value=value, a=a, x=x, y=y, sp=sp,
                             flags=values[10], clock=int(values[11])))
    assert rows
    # The broad init trace and the specific D017 trace deliberately overlap.
    # Preserve both records while counting their shared instruction only once.
    unique, duplicates = {}, []
    for row in rows:
        key = (row["clock"], row["pc"], row["target"], row["value"])
        if key in unique:
            duplicates.append(dict(first=unique[key], duplicate=row))
        else:
            unique[key] = row
    return rows, sorted(unique.values(), key=lambda row: row["clock"]), duplicates


def source_rules():
    guards = {
        "vicii-fetch.c": [
            "vicii.sprite[i].pointer = fetch_phi1(v_fetch_addr(0x3f8 + i));",
            "sprdata = fetch_phi2((vicii.sprite[i].pointer << 6) + vicii.sprite[i].mc);",
            "sprdata = fetch_phi1((vicii.sprite[i].pointer << 6) + vicii.sprite[i].mc);",
            "vicii.sprite[i].mc &= 0x3f;"],
        "vicii-cycle.c": [
            "vicii.sprite[i].mc = vicii.sprite[i].mcbase;",
            "if (vicii.sprite[i].exp_flop)",
            "vicii.sprite[i].mcbase = vicii.sprite[i].mc;",
            "vicii.sprite[i].exp_flop ^= 1;",
            "Update sprite mcbase (Cycle 16 on PAL)"],
        "vicii-mem.c": [
            "if (value == vicii.regs[0x17])", "if (!(value & b) && !vicii.sprite[i].exp_flop)",
            "if (cycle_is_check_spr_crunch(vicii.cycle_flags))",
            "vicii.sprite[i].mc = (0x2a & (mcbase & mc)) | (0x15 & (mcbase | mc));",
            "vicii.sprite[i].exp_flop = 1;"],
        "vicii-chip-model.c": [
            "cycle_tab_pal", "{ Phi1(1),  0x194, None,    SprPtr(3)",
            "{ Phi1(3),  0x1a4, None,    SprPtr(4)", "{ Phi1(5),  0x1b4, None,    SprPtr(5)",
            "{ Phi1(7),  0x1c4, None,    SprPtr(6)", "{ Phi1(9),  0x1d4, None,    SprPtr(7)",
            "{ Phi1(58), 0x164, None,    SprPtr(0)", "{ Phi1(60), 0x174, None,    SprPtr(1)",
            "{ Phi1(62), 0x184, None,    SprPtr(2)"],
    }
    records = []
    archive = ROOT / "build/research/quondam/hardware-source/vice-3.10.tar.gz"
    with tarfile.open(archive, "r:gz") as tar:
        for name, needles in guards.items():
            member = "vice-3.10/src/viciisc/" + name
            data = tar.extractfile(member).read()
            assert all(needle in data.decode() for needle in needles), name
            target = OUTPUT / "vic-source" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            records.append(dict(member=member, guarded_fragments=len(needles), **artifact(target)))
    return dict(archive=artifact(archive), files=records,
                url="https://sourceforge.net/projects/vice-emu/files/releases/vice-3.10.tar.gz/")


def main():
    for path, digest in PINS.items():
        assert sha((ROOT / path).read_bytes()) == digest, ("Changed input", path)
    wire, case, adaptation = wire_case()
    reader = load("spritefpp_snapshot_reader", "research/quondam/snapshot_state.py")
    records, decoded = captures(reader, capture_contexts(wire, case))
    expected = {
        "original-boot": (0x0810, 6977568, 307, 3),
        "production-entry": (0xc300, 141106918, 256, 22),
        "production-initialized": (0x08a7, 141123577, 208, 49),
        "first-prepared": (0x9237, 141190588, 24, 28),
        "first-prefix": (0x8026, 141193881, 76, 45),
        "cell62-preclear": (0x8846, 141197850, 139, 45),
        "cell62-postclear": (0x8849, 141197854, 139, 49),
        "cell63-preclear": (0x8867, 141197913, 140, 45),
        "cell63-postclear": (0x886a, 141197917, 140, 49),
        "cell64-preclear": (0x8888, 141197976, 141, 45),
        "cell64-postclear": (0x888b, 141197980, 141, 49),
    }
    assert set(decoded) == set(expected)
    for stem, (pc, clock, line, cycle) in expected.items():
        cpu_state = decoded[stem][0]
        assert (cpu_state["pc"], cpu_state["clock"], cpu_state["line"], cpu_state["cycle"]) == (pc, clock, line, cycle)
        assert cpu_state["port00"] == 0x2f
        assert cpu_state["port01"] == (0x37 if stem == "original-boot" else 0x35)

    commands = [row["command"] for row in case["queued"].values()]
    allowed = re.compile(r'^(?:r|sidefx off|warp(?: on| off)?|resourceget "Speed"|bank ram|x|'
                         r'delete [0-9]+|break [0-9a-f]{4}(?: if .+)?|'
                         r'trace store [0-9a-f]{4} [0-9a-f]{4}|bsave "[^"]+" 0 0000 ffff|dump "[^"]+")$')
    assert len(commands) == len(case["responses"]) == 99
    assert all(allowed.fullmatch(command) for command in commands)
    assert not case["partial"] and not case["cancelled"]
    assert all(row["status"] == "completed" and "interrupt" not in row for row in case["responses"].values())
    navigation, unwarped, warp_mode = [], [], False
    for sequence, queued in case["queued"].items():
        command = queued["command"]
        response = wire.PROMPT.sub(b"", case["responses"][sequence]["response"].encode()).strip()
        if command == "warp on":
            warp_mode = True
        elif command == "warp off":
            warp_mode = False
        elif command == "warp":
            assert response == (b"Warp mode is on." if warp_mode else b"Warp mode is off.")
        elif command == 'resourceget "Speed"':
            assert response == b"Speed=100"
        elif command == "x":
            (navigation if warp_mode else unwarped).append(sequence)
    assert navigation == [5, 17] and unwarped == [32, 42, 49, 58, 65, 72, 79, 86, 93]
    boot = (BASE / "original-analysis/side1-boot.prg").read_bytes()
    load_address = int.from_bytes(boot[:2], "little")
    assert len(boot) == 834 and load_address == 0x0801
    assert decoded["original-boot"][1][load_address:load_address + len(boot) - 2] == boot[2:]
    original = (BASE / "original-analysis/side1-bundle031.ram").read_bytes()
    known = (BASE / "original-analysis/side1-bundle031.known").read_bytes()
    assert len(original) == len(known) == 65536 and set(known) == {0, 1} and sum(known) == 20261
    entry_cpu, entry_ram, entry_state = decoded["production-entry"]
    assert all(entry_ram[i] == original[i] for i, value in enumerate(known) if value)
    assert known[0x4000:0x4003] == b"\0\0\0" and entry_ram[0x4000:0x4003] == bytes.fromhex("47 ec 98")
    assert entry_ram[0x08a4:0x08a7] == bytes.fromhex("20 00 c3") and entry_cpu["sp"] == 0x5d
    saved_return = bytes(entry_ram[0x100 | ((entry_cpu["sp"] + i) & 255)] for i in (1, 2))
    assert saved_return == bytes.fromhex("a6 08")
    initialized_cpu, initialized_ram, initialized_state = decoded["production-initialized"]
    assert initialized_cpu["sp"] == entry_cpu["sp"] + 2
    assert initialized_ram[0x700:0x800] == bytes([255]) * 256
    assert initialized_ram[0x7f00:0x8000] == bytes(256)
    assert initialized_state["vicii"]["regs"][1:16:2] == list(range(75, 67, -1))
    assert bank_state(entry_state)["bank"] == bank_state(initialized_state)["bank"] == 0

    prepared_cpu, prepared_ram, prepared_state = decoded["first-prepared"]
    assert [prepared_ram[i] for i in (0x35, 0x44, 0x45)] == [0, 0, 127]
    assert prepared_ram[0x700 + 58:0x700 + 69] == bytes((5, 6, 5, 6, 5, 10, 11, 10, 11, 10, 11))
    assert bank_state(prepared_state) == dict(pra=0xc0, ddra=0x3d, pulled_up_low_pins=2,
                                              bank=0x4000, pointer_table=0x43f8)
    initial_y = initialized_state["vicii"]["regs"][1:16:2]
    predicted_base = [3 * (76 - y) for y in initial_y]
    assert predicted_base == list(range(3, 25, 3))
    prefix_cpu, prefix_ram, prefix_state = decoded["first-prefix"]
    assert [sprite["mcbase"] for sprite in prefix_state["vicii"]["sprites"]] == predicted_base
    assert [sprite["mc"] for sprite in prefix_state["vicii"]["sprites"]] == predicted_base
    assert all(sprite["pointer"] == 255 and sprite["data"] == 0 for sprite in prefix_state["vicii"]["sprites"])
    assert prefix_state["vicii"]["regs"][0x17] == 0

    all_trace, unique_trace, duplicates = trace_rows(case)
    assert len(all_trace) == 2095 and len(unique_trace) == 2094 and len(duplicates) == 1
    duplicate = duplicates[0]
    assert duplicate["first"]["pc"] == duplicate["duplicate"]["pc"] == 0x9908
    assert duplicate["first"]["target"] == duplicate["duplicate"]["target"] == 0xd017
    assert {duplicate["first"]["trace_checkpoint"], duplicate["duplicate"]["trace_checkpoint"]} == {1, 3}
    by_store = {(row["pc"], row["target"]): row for row in unique_trace
                if prefix_cpu["clock"] <= row["clock"]}
    for cell in range(65):
        start = 0x802a + 33 * cell
        row = by_store[(start, 0xd017)]
        assert row["value"] == 255 and row["observer_line"] == 76 + cell and row["observer_raw_cycle"] == 53
        for sprite in range(8):
            row = by_store[(start + 6 + 3 * sprite, 0x43f8 + sprite)]
            assert row["value"] == prepared_ram[0x700 + cell]
            assert row["observer_line"] == 77 + cell and row["observer_raw_cycle"] == 17 + 4 * sprite
        if cell < 64:
            row = by_store[(start + 30, 0xd017)]
            assert row["value"] == 0 and row["observer_line"] == 77 + cell and row["observer_raw_cycle"] == 49
    assert (0x8888, 0xd017) not in by_store  # Final stop's pending trace is not fabricated.

    transitions, fetches, negative_controls = [], [], []
    for cell in (62, 63, 64):
        pre_cpu, pre_ram, pre_state = decoded[f"cell{cell}-preclear"]
        post_cpu, post_ram, post_state = decoded[f"cell{cell}-postclear"]
        pre, post = pre_state["vicii"], post_state["vicii"]
        assert post_cpu["clock"] - pre_cpu["clock"] == 4
        assert pre_cpu["line"] == post_cpu["line"] == 77 + cell
        assert (pre_cpu["cycle"], post_cpu["cycle"]) == (45, 49)
        assert pre_ram == post_ram
        assert bank_state(pre_state) == bank_state(post_state) == bank_state(prepared_state)
        assert pre["regs"][0x17] == 255 and post["regs"][0x17] == 0
        assert pre["sprite_dma"] == post["sprite_dma"] == pre["sprite_display_bits"] == post["sprite_display_bits"] == 255
        assert pre["regs"][0x1c] == post["regs"][0x1c] == 255
        assert pre["regs"][0x20:0x2f] == post["regs"][0x20:0x2f] == [0] * 15
        assert pre_ram[0x43f8:0x4400] == post_ram[0x43f8:0x4400] == bytes([prepared_ram[0x700 + cell]]) * 8
        atlas_differences = [address for address in range(0x4003, 0x5103)
                             if pre_ram[address] != original[address]]
        assert atlas_differences == list(range(0x43f8, 0x4400))
        # The live pointer table occupies slot15's unused bytes56..63. All
        # generated strip payloads occupy bytes3..26 and remain original.
        for slot in range(68):
            first = 0x4000 + slot * 64 + 3
            assert pre_ram[first:first + 24] == original[first:first + 24]
        assert pre_ram[0x8026:0x9172] == post_ram[0x8026:0x9172] == original[0x8026:0x9172]
        controls = dict(cell=cell, zero_counter_mismatches=0, all_sprites_offset3_mismatches=0,
                        current_RAM_pointer_mismatches=0)
        for sprite in range(8):
            a, b = pre["sprites"][sprite], post["sprites"][sprite]
            assert a["mcbase"] == b["mcbase"] == predicted_base[sprite]
            assert a["mc"] == b["mc"] == predicted_base[sprite] + 3
            assert (a["exp_flop"], b["exp_flop"]) == (0, 1)
            assert all(a[key] == b[key] for key in ("data", "mc", "mcbase", "pointer"))
            assert a["pointer"] == prepared_ram[0x700 + cell - 1]
            address = 0x4000 + a["pointer"] * 64 + a["mcbase"]
            data = (a["data"] & 0xffffff).to_bytes(3, "big")
            assert a["data"] <= 0xffffff and all(known[address:address + 3])
            assert data == original[address:address + 3] == pre_ram[address:address + 3] and any(data)
            zero_address = 0x4000 + a["pointer"] * 64
            flat_address = zero_address + 3
            current_address = 0x4000 + pre_ram[0x43f8 + sprite] * 64 + a["mcbase"]
            controls["zero_counter_mismatches"] += data != original[zero_address:zero_address + 3]
            controls["all_sprites_offset3_mismatches"] += data != original[flat_address:flat_address + 3]
            controls["current_RAM_pointer_mismatches"] += data != original[current_address:current_address + 3]
            fetches.append(dict(cell=cell, sprite=sprite, latched_pointer=a["pointer"],
                                current_RAM_pointer=pre_ram[0x43f8 + sprite], MC=a["mc"], MCBASE=a["mcbase"],
                                source_address=address, data_hex=data.hex(),
                                original_file_defined=True, held_across_clear=True))
        assert controls["zero_counter_mismatches"] == controls["current_RAM_pointer_mismatches"] == 8
        assert controls["all_sprites_offset3_mismatches"] == 7
        negative_controls.append(controls)
        crunch = [(0x2a & (base & (base + 3))) | (0x15 & (base | (base + 3))) for base in predicted_base]
        actual_mc = [sprite["mc"] for sprite in post["sprites"]]
        assert crunch != actual_mc
        transitions.append(dict(cell=cell, pre_PC=pre_cpu["pc"], post_PC=post_cpu["pc"],
                                elapsed_cycles=4, line=pre_cpu["line"], pre_raw_cycle=45, post_raw_cycle=49,
                                MCBASE=predicted_base, MC=actual_mc, pre_D017=255, post_D017=0,
                                pre_exp_flop=[0] * 8, post_exp_flop=[1] * 8,
                                atlas_original_domain_exceptions=[
                                    dict(address=address, original=original[address], actual=pre_ram[address])
                                    for address in atlas_differences],
                                hypothetical_cycle15_crunch_MC=crunch,
                                cycle15_crunch_matches_observation=False))
    for cell in (62, 63):
        a = decoded[f"cell{cell}-preclear"][0]
        b = decoded[f"cell{cell + 1}-preclear"][0]
        assert b["clock"] - a["clock"] == 63

    OUTPUT.mkdir(parents=True, exist_ok=True)
    trace_path = OUTPUT / "store-trace.json"
    trace_path.write_text(json.dumps(dict(all_records=all_trace, duplicate_observer_records=duplicates,
                                          unique_records=len(unique_trace)), indent=2) + "\n")
    result = dict(pass_=True, script=artifact(Path(__file__).resolve()),
                  input_pins=[artifact(ROOT / path) for path in PINS],
                  case_pin=CASE_SHA, wire_audit=wire.summary(case),
                  wire_startup_adaptation=adaptation,
                  checkpoints=sorted(records, key=lambda row: row["registers"]["clock"]),
                  original_boot=dict(file=artifact(BASE / "original-analysis/side1-boot.prg"),
                                     file_bytes=834, load_header_bytes=2, loaded_bytes_checked=832, entry_PC=0x0810),
                  original_bundle=dict(known_bytes_checked=20261, mismatches=0,
                                       initializer_PC=0xc300, callsite=0x08a4, saved_JSR_return=0x08a6,
                                       observed_RTS_return=0x08a7,
                                       unloaded_atlas_header_addresses=[0x4000, 0x4001, 0x4002],
                                       unloaded_atlas_header_observed_hex="47ec98",
                                       header_fetch_proved=False),
                  atlas_runtime_ownership=dict(original_loaded_domain=[0x4003, 0x5103],
                                               unchanged_original_bytes=4344,
                                               live_pointer_table=[0x43f8, 0x4400],
                                               pointer_table_slot=15, pointer_table_slot_offsets=[56, 64],
                                               original_payload_slots_checked=68,
                                               original_payload_bytes_per_slot=24,
                                               payload_slot_offsets=[3, 27]),
                  runtime_start=dict(initialized_bank=bank_state(initialized_state),
                                     prepared_bank=bank_state(prepared_state),
                                     frame_index=0, x_size=0, y_size=127,
                                     sprite_Y=initial_y, predicted_MCBASE=predicted_base,
                                     X_expand_mask=prepared_state["vicii"]["regs"][0x1d],
                                     sprite_X_registers=prepared_state["vicii"]["regs"][0:16:2]),
                  expansion_transitions=transitions, original_atlas_fetches=fetches,
                  negative_controls=negative_controls,
                  trace=dict(file=artifact(trace_path), total_observer_records=len(all_trace),
                             unique_store_observer_records=len(unique_trace), duplicate_init_store_records=1,
                             kernel_pointer_cells_checked=65, kernel_pointer_store_records_checked=520,
                             kernel_D017_set_records_checked=65, kernel_D017_clear_records_checked=64,
                             final_cell64_clear_observed_by_snapshot_not_flushed_trace=True,
                             timing="Store-hook observer boundaries, not individual physical bus-write timestamps"),
                  execution=dict(native_resumes=len(navigation) + len(unwarped), navigation_warp_resumes=navigation,
                                 unwarped_proof_resumes=unwarped, speed=100, restores=0,
                                 CPU_memory_or_PC_injections=[], cancellations=0, restarts=0),
                  VIC_source=source_rules(),
                  last_valid_continuation=artifact(CAPTURE / "cell64-postclear.vsf"),
                  next_capture=dict(output_case="NEW native-03", restore="cell64-postclear.vsf",
                                    candidate_PC=0x8c24, candidate_cell=92,
                                    reason="Observe actual pointer0 and distinguish its nonzero 4000..4002 header from offset3 data; not collected here"),
                  limits=[
                      "The original disk was booted through natural execution; two earlier navigation resumes used declared warp. No full-demo timing or loading margin is measured.",
                      "All 24 nonzero data-latch checks concern three consecutive first-field interior cells. They are not complete displayed pixels or all-frame DMA continuity.",
                      "All selected sprite colors are still black during these captures. This proves nonzero fetched data, not visible shaded geometry or a mature 192-pixel-wide display.",
                      "RAM pointer stores are one row newer than the actual cached pointers in these cells; current RAM entries cannot be substituted for saved VIC latches.",
                      "Original 4000..4002 values are observed but remain outside bundle31's file-defined mask. No pointer0 fetch was collected to prove those bytes unused.",
                      "The supplied standalone was not launched; no standalone/common startup or pixel equivalence is claimed.",
                      "The observer was explicitly closed and its owned emulator reaped. Native02 remains immutable; further capture requires a new case."])
    result["pass"] = result.pop("pass_")
    target = OUTPUT / "native-spritefpp-proof.json"
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"pass": True, "capture_pairs": len(records), "original_bytes_checked": 20261,
                      "nonzero_sprite_fetches": len(fetches), "receipt": artifact(target)}, indent=2))


if __name__ == "__main__":
    main()
