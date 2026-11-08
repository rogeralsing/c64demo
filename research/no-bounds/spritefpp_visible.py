#!/usr/bin/env python3
"""Independent direct-sprite composition from closed original SpriteFPP evidence.

Only retained files are read. No emulator, CPU or assembler is executed.
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
CAPTURE = BASE / "native-03"
OUTPUT = BASE / "spritefpp-visible-analysis"
CASE_SHA = "8c5d4587365f905277b0b57af076f68b7a2d8db7c03bc855ce6763355cbb51bc"
FIRST, LAST, LEFT, RIGHT = 78, 210, 32, 352
PINS = {
    "research/no-bounds/native_spritefpp.py": "8984f9c8bd55e880f71fc5acab3fdf5dafdf47414f1d871a310d796fa668b395",
    "research/anomaly/scanout.py": "c5e63a07f3060614710518aaf9b9e6c9365c297619af4e19719a4b5f8b62198f",
    "research/quondam/snapshot_state.py": "c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a",
    "research/verify_vice_live.py": "f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a",
    "build/research/no-bounds/native-spritefpp-analysis/native-spritefpp-proof.json": "55158e5ed27edb840106ddaf6363d2cf8cf8fd4c98be2e6651ba002dad186fee",
    "build/research/no-bounds/original-analysis/side1-bundle031.ram": "8a1affa7e2d58061214ba5e0af0388ece30d8cc501611a643f1194b2a99f929d",
    "build/research/no-bounds/original-analysis/side1-bundle031.known": "0dcd551960cab15fad234f9bc6d53a937ee6b60ca2a12877e57ddc532690e3d3",
    "build/research/no-bounds/original/zip-members/NoBounds-GP-Side1.d64": "f603e03f94ed4df416584419a696e1832b0710308de8faf2d0179b0a7725fe70",
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


def layout(index):
    """Closed form for the published overlap/expansion layout, not its loop."""
    left = 110 - index
    padding = 48 + 2 * index
    count = (padding + 47) // 48
    overlap = 48 * count - padding
    x = [left, left + 24, 0, 0, 0, 0, 0, 0]
    for j in range(count):
        x[2 + j] = left + 48 + 48 * j - (overlap if j == count - 1 else 0)
    x[6] = x[1 + count] + 48
    x[7] = x[6] + 24
    return x, sum((1 << s) for s, value in enumerate(x) if value > 255), ((1 << count) - 1) << 2


def model_sources(original):
    assert original[0x92a8:0x92ab] == bytes.fromhex("20 96 98")
    assert original[0x98a4:0x98a6] == bytes.fromhex("a2 00")
    acceleration = original[0x933b:0x936a]
    assert len(acceleration) == 47 and max(acceleration) == 11 and sum(acceleration) == 71
    rows = []
    for index in range(72):
        x, high, expanded = layout(index)
        pointer = original[0x9e80 + index] | (original[0x9ec8 + index] << 8)
        actual = [original[pointer + s] + (256 if original[0x9df0 + index] & (1 << s) else 0)
                  for s in range(8)]
        assert pointer == 0x9bb0 + index * 8
        assert actual == x and original[0x9df0 + index] == high and original[0x9e38 + index] == expanded
        rows.append(dict(index=index, source_table=pointer, X=x, high_X=high, X_expand=expanded))
    return dict(layouts=rows, checked_layouts=72, checked_X_coordinates=576,
                checked_high_X_and_expansion_bytes=144, acceleration_bytes=list(acceleration),
                fade_stage_operand=0x98a5, fade_irq_call=0x92a8,
                mature_condition='break 9237 if (@ram:$98a5 == $06) && (@ram:$44 >= $3c) && (@ram:$44 <= $44)',
                exact_layout59_condition='(@ram:$20 == $88) && (@ram:$21 == $9d)')


def compose(prepared_ram, regs, original, variant=None):
    """Decode twelve source pairs per sprite and paint by hardware number.

    This uses static prepared rows and direct bit pairs. It does not replay
    VICE's shifters, expansion flops, trigger pipeline or draw-cycle algorithm.
    """
    result, per_sprite, overlaps, row_sources = bytearray(), dict.fromkeys(range(8), 0), 0, []
    for line in range(FIRST, LAST + 1):
        index = line - prepared_ram[0xe9] - 2 + (1 if variant == "fresh_row" else 0)
        assert 0 <= index < 134
        pointer = prepared_ram[0x700 + index]
        assert pointer < 68 or pointer == 255
        pixels, owners = bytearray([regs[0x21]]) * (RIGHT - LEFT), bytearray(RIGHT - LEFT)
        order = range(7, -1, -1) if variant == "reverse_priority" else range(8)
        for sprite in order:
            if variant == "no_sprites" or not (regs[0x15] & (1 << sprite)):
                continue
            counter = 3 if variant == "uniform_offset3" else 3 * (sprite + 1)
            address = 0x4000 + pointer * 64 + counter
            data = prepared_ram[address:address + 3] if pointer == 255 else original[address:address + 3]
            assert len(data) == 3
            word = int.from_bytes(data, "big")
            high = bool(regs[0x10] & (1 << sprite)) and variant != "ignore_high_X"
            xpos = regs[2 * sprite] + 256 * high + 8
            expanded = bool(regs[0x1d] & (1 << sprite)) and variant != "ignore_X_expand"
            multicolor = bool(regs[0x1c] & (1 << sprite)) and variant != "hires"
            colors = (None, regs[0x25], regs[0x27 + sprite], regs[0x26])
            count, step = (12, 4 if expanded else 2) if multicolor else (24, 2 if expanded else 1)
            for sample in range(count):
                value = ((word >> (22 - 2 * sample)) & 3) if multicolor else (2 if word & (1 << (23 - sample)) else 0)
                if value == 0:
                    continue
                for offset in range(step):
                    x = xpos + sample * step + offset
                    if not LEFT <= x < RIGHT:
                        continue
                    local = x - LEFT
                    if owners[local]:
                        overlaps += 1
                        continue
                    owners[local] = sprite + 1
                    pixels[local] = colors[value]
                    per_sprite[sprite] += 1
        row_sources.append(dict(line=line, prepared_index=index, pointer=pointer))
        result.extend(pixels)
    return bytes(result), per_sprite, overlaps, row_sources


def trace_rows(case):
    # The frozen preceding reader's pattern supplies the retained observer
    # fields. This case also traces indexed init stores, so values are decoded
    # from the store register without treating its literal operand as its
    # effective address. The trace header supplies that actual address.
    old = load("visible_trace_schema", "research/no-bounds/native_spritefpp.py")
    rows = []
    for sequence, response in case["responses"].items():
        for match in old.TRACE.finditer(response["response"]):
            fields = match.groups()
            instruction = fields[5].strip()
            store = re.search(r"\b(STA|STX|STY)\b", instruction)
            a, x, y = (int(v, 16) for v in fields[6:9])
            value = {"STA": a, "STX": x, "STY": y}[store[1]] if store else None
            rows.append(dict(response_sequence=sequence, trace_checkpoint=int(fields[0]),
                             target=int(fields[1], 16), observer_line=int(fields[2]),
                             observer_raw_cycle=int(fields[3]), pc=int(fields[4], 16),
                             instruction=instruction, value=value, clock=int(fields[11])))
    return rows


def source_rules():
    archive = ROOT / "build/research/quondam/hardware-source/vice-3.10.tar.gz"
    assert sha(archive.read_bytes()) == "8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1"
    guards = {
        "src/viciisc/vicii-draw-cycle.c": [
            "for (s = 7; s >= 0; --s)",
            "sbuf_pixel_reg[s] = (uint8_t)((sbuf_reg[s] >> 22) & 0x03);",
            "render_buffer[i] = COL_D025;", "render_buffer[i] = COL_D027 + as;",
            "render_buffer[i] = COL_D026;", "sprite_expx_bits = vicii.regs[0x1d];"],
        "src/viciisc/vicii-draw.c": [
            "#define DBUF_OFFSET (17 * 8 - vicii.screen_leftborderwidth)",
            "src = &(vicii.dbuf[DBUF_OFFSET + xs * 8]);"],
        "src/viciisc/vicii-fetch.c": [
            "vicii.sprite[i].pointer = fetch_phi1(v_fetch_addr(0x3f8 + i));",
            "sprdata = fetch_phi1((vicii.sprite[i].pointer << 6) + vicii.sprite[i].mc);"],
    }
    records = []
    with tarfile.open(archive, "r:gz") as tar:
        for path, needles in guards.items():
            data = tar.extractfile("vice-3.10/" + path).read()
            assert all(needle in data.decode() for needle in needles), path
            records.append(dict(member="vice-3.10/" + path, sha256=sha(data), guarded_fragments=needles))
    return dict(archive=artifact(archive), files=records,
                note="Only source rules and serialized raster layout are reused; no VICE shifter execution is replayed")


def main():
    for path, digest in PINS.items():
        assert sha((ROOT / path).read_bytes()) == digest, path
    old = load("visible_prior_native", "research/no-bounds/native_spritefpp.py")
    for path, digest in old.PINS.items():
        assert sha((ROOT / path).read_bytes()) == digest, path
    # Reuse the preceding pinned autostart adaptation, selecting this new closed
    # case only. Its exact disk/startup and every raw-wire invariant still apply.
    wire_source = inspect.getsource(old.wire_case)
    assert wire_source.count('"native-02"') == 2
    adapted_wire_source = wire_source.replace('"native-02"', '"native-03"')
    old.CASE_SHA, old.CAPTURE = CASE_SHA, CAPTURE
    exec(compile(adapted_wire_source, "<native03-pinned-autostart-reader>", "exec"), old.__dict__)
    wire, case, startup_adaptation = old.wire_case()
    reader = load("visible_snapshot_reader", "research/quondam/snapshot_state.py")
    records, decoded = old.captures(reader, old.capture_contexts(wire, case))
    assert len(records) == 14 and len(case["queued"]) == len(case["responses"]) == 125
    assert not case["partial"] and not case["cancelled"]
    assert all(r["status"] == "completed" and "interrupt" not in r for r in case["responses"].values())
    allowed = re.compile(r'^(?:r|sidefx off|warp(?: on| off)?|resourceget "Speed"|bank (?:ram|cpu)|x|'
                         r'delete [0-9]+|break (?:[0-9a-f]{4}|exec 0000 ffff)(?: if .+)?|'
                         r'trace store [0-9a-f]{4} [0-9a-f]{4}|bsave "[^"]+" 0 0000 ffff|'
                         r'dump "[^"]+"|scrsh "[^"]+" 2)$')
    warp_mode, navigation, unwarped = False, [], []
    for sequence, row in case["queued"].items():
        command = row["command"]
        assert allowed.fullmatch(command), command
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
    assert navigation == [5, 17]
    assert unwarped == [31, 38, 45, 52, 64, 75, 82, 89, 96, 103, 110, 117]
    expected_stops = {
        "original-boot": (0x0810, 6913663, 228, 43),
        "production-entry": (0xc300, 141047950, 256, 22),
        "production-initialized": (0x08a7, 141064609, 208, 49),
        "first-prepared": (0x9237, 141131626, 24, 34),
        "pointer0-preclear": (0x8c24, 141140773, 169, 46),
        "pointer0-postclear": (0x8c27, 141140777, 169, 50),
        "mature-prepared": (0x9237, 143588643, 24, 51),
        "mature64-preclear": (0x8888, 143596009, 141, 46),
        "mature64-postclear": (0x888b, 143596013, 141, 50),
        "mature65-preclear": (0x88a9, 143596072, 142, 46),
        "mature65-postclear": (0x88ac, 143596076, 142, 50),
        "mature66-preclear": (0x88ca, 143596135, 143, 46),
        "mature66-postclear": (0x88cd, 143596139, 143, 50),
        "mature-window-complete": (0x0cfa, 143600978, 220, 38),
    }
    assert set(decoded) == set(expected_stops)
    for stem, expected in expected_stops.items():
        assert tuple(decoded[stem][0][key] for key in ("pc", "clock", "line", "cycle")) == expected
        assert decoded[stem][0]["port00"] == 0x2f
        assert decoded[stem][0]["port01"] == (0x37 if stem == "original-boot" else 0x35)
    original = (BASE / "original-analysis/side1-bundle031.ram").read_bytes()
    known = (BASE / "original-analysis/side1-bundle031.known").read_bytes()
    models = model_sources(original)
    boot = (BASE / "original-analysis/side1-boot.prg").read_bytes()
    assert len(boot) == 834 and decoded["original-boot"][1][0x801:0xb41] == boot[2:]
    entry_cpu, entry_ram, entry_state = decoded["production-entry"]
    assert sum(known) == 20261 and all(entry_ram[i] == original[i] for i, value in enumerate(known) if value)
    assert entry_cpu["sp"] == 0x5d and entry_ram[0x15e:0x160] == bytes.fromhex("a6 08")
    assert entry_ram[0x08a4:0x08a7] == bytes.fromhex("20 00 c3")
    assert decoded["production-initialized"][0]["sp"] == 0x5f
    header = entry_ram[0x4000:0x4003]
    assert header == bytes.fromhex("47 ec 98") and known[0x4000:0x4003] == bytes(3)
    base = list(range(3, 25, 3))
    pointer0 = []
    for stage in ("preclear", "postclear"):
        cpu, ram, state = decoded["pointer0-" + stage]
        vic = state["vicii"]
        assert old.bank_state(state)["bank"] == 0x4000
        assert vic["sprite_dma"] == vic["sprite_display_bits"] == 255
        assert vic["regs"][0x17] == (255 if stage == "preclear" else 0)
        for sprite, value in enumerate(vic["sprites"]):
            assert (value["pointer"], value["mcbase"], value["mc"], value["data"]) == (0, base[sprite], base[sprite] + 3, 0)
            assert value["exp_flop"] == (0 if stage == "preclear" else 1)
            address = 0x4000 + base[sprite]
            assert all(known[address:address + 3]) and original[address:address + 3] == ram[address:address + 3] == bytes(3)
            assert ram[0x4000:0x4003] == header != bytes(3)
        pointer0.append(dict(stage=stage, registers=cpu, bank=old.bank_state(state),
                             actual_data=[0] * 8, observed_unloaded_header=header.hex(),
                             wrong_zero_offset_data=header.hex(), wrong_zero_offset_mismatches=8))
    assert decoded["pointer0-postclear"][0]["clock"] - decoded["pointer0-preclear"][0]["clock"] == 4

    prepared_cpu, prepared_ram, prepared_state = decoded["mature-prepared"]
    proof_cpu, proof_ram, proof_state = decoded["mature64-preclear"]
    final_cpu, final_ram, final_state = decoded["mature-window-complete"]
    regs = proof_state["vicii"]["regs"]
    assert [prepared_ram[i] for i in (0x35, 0x44, 0x45, 0x55, 0x98a5)] == [4, 60, 127, 1, 6]
    assert prepared_ram[0x20:0x22] == bytes.fromhex("88 9d")
    assert prepared_ram[0x15:0x17] == bytes.fromhex("6c ac") and prepared_ram[0x22:0x24] == bytes.fromhex("15 07")
    assert prepared_ram[0x26:0x28] == bytes((91, 92))
    assert prepared_ram[0x715:0x715 + 92] == original[0xac6c:0xac6d] + original[0xac6c:0xac6c + 91]
    positions, high, expanded = layout(59)
    assert [regs[2 * s] + (256 if regs[0x10] & (1 << s) else 0) for s in range(8)] == positions
    assert regs[0x10] == high == 0xc0 and regs[0x1d] == expanded == 0x3c
    assert regs[0x15] == regs[0x1c] == 255 and regs[0x1b] == 0
    assert regs[0x20] == regs[0x21] == 1 and regs[0x25] == 11 and regs[0x26] == 12 and regs[0x27:0x2f] == [15] * 8
    assert prepared_ram[0xe9] == 76 and prepared_ram[0x700:0x715] == bytes([255]) * 21
    assert prepared_ram[0x771:0x785] == bytes([255]) * 20
    assert prepared_ram[0x7f00:0x8000] == final_ram[0x7f00:0x8000] == bytes(256)
    stable_regs = [*range(0x11), 0x16, 0x18, 0x1b, 0x1c, 0x1d, *range(0x20, 0x2f)]
    witnesses = []
    for cell in (64, 65, 66):
        before_cpu, before_ram, before_state = decoded[f"mature{cell}-preclear"]
        after_cpu, after_ram, after_state = decoded[f"mature{cell}-postclear"]
        assert after_cpu["clock"] - before_cpu["clock"] == 4
        assert (before_cpu["cycle"], after_cpu["cycle"]) == (46, 50)
        assert before_ram == after_ram and before_cpu["line"] == after_cpu["line"] == 77 + cell
        for stage, ram, state in (("preclear", before_ram, before_state), ("postclear", after_ram, after_state)):
            vic = state["vicii"]
            assert [vic["regs"][i] for i in stable_regs] == [regs[i] for i in stable_regs]
            assert old.bank_state(state)["bank"] == 0x4000
            assert vic["regs"][0x17] == (255 if stage == "preclear" else 0)
            assert vic["sprite_dma"] == vic["sprite_display_bits"] == 255
            assert ram[0x8026:0x9172] == original[0x8026:0x9172]
            for slot in range(68):
                address = 0x4000 + 64 * slot + 3
                assert ram[address:address + 24] == original[address:address + 24]
            for sprite, value in enumerate(vic["sprites"]):
                pointer = prepared_ram[0x700 + cell - 1]
                assert (value["pointer"], value["mcbase"], value["mc"]) == (pointer, base[sprite], base[sprite] + 3)
                assert value["exp_flop"] == (0 if stage == "preclear" else 1)
                address = 0x4000 + pointer * 64 + base[sprite]
                data = (value["data"] & 0xffffff).to_bytes(3, "big")
                assert all(known[address:address + 3]) and data == original[address:address + 3] == ram[address:address + 3]
                if stage == "preclear":
                    witnesses.append(dict(cell=cell, sprite=sprite, pointer=pointer, byte_offset=base[sprite],
                                          source_address=address, data_hex=data.hex(), nonzero=bool(any(data))))
    assert all(w["nonzero"] for w in witnesses)
    for state in (prepared_state, proof_state, final_state):
        vic = state["vicii"]
        assert not vic["vborder"] and not vic["set_vborder"] and not vic["main_border"]
        assert vic["idle_state"] == 1 and vic["allow_bad_lines"] == vic["bad_line"] == 0
        assert not (vic["regs"][0x11] & 0x10) and vic["gbuf"] == 0
        assert [vic["regs"][i] for i in stable_regs] == [regs[i] for i in stable_regs]
    assert final_state["vicii"]["regs"][0x15] == 0
    assert 0 < final_cpu["clock"] - prepared_cpu["clock"] < 19656
    trace = trace_rows(case)
    mature_trace = [row for row in trace if prepared_cpu["clock"] < row["clock"] <= final_cpu["clock"]]
    by_store = {(row["pc"], row["target"]): row for row in mature_trace}
    pointer_phase = by_store[(0x8030, 0x43f8)]["observer_raw_cycle"]
    assert pointer_phase == 18
    for cell in range(134):
        start = 0x802a + 33 * cell
        row_index = cell if cell < 133 else 0
        for sprite in range(8):
            row = by_store[(start + 6 + 3 * sprite, 0x43f8 + sprite)]
            assert row["value"] == prepared_ram[0x700 + row_index]
            assert (row["observer_line"], row["observer_raw_cycle"]) == (77 + cell, pointer_phase + 4 * sprite)
        assert by_store[(start, 0xd017)]["value"] == 255
        assert by_store[(start + 30, 0xd017)]["value"] == 0
    disabled = by_store[(0x9172, 0xd015)]
    assert disabled["value"] == 0 and disabled["observer_line"] == 211
    row_writes = [row for row in mature_trace if 0x700 <= row["target"] <= 0x785]
    assert len(row_writes) == 15 and all(row["clock"] > disabled["clock"] and row["value"] == 255 for row in row_writes)
    assert sorted(row["target"] for row in row_writes) == list(range(0x741, 0x750))
    assert not [row for row in mature_trace if 0xd020 <= row["target"] <= 0xd02e]
    stable_window_addresses = {0xd000 + i for i in stable_regs} | {0xd011, 0xd015, 0xdd00, 0xdd01, 0xdd02, 0xdd03}
    assert not [row for row in mature_trace
                if FIRST <= row["observer_line"] <= LAST and row["target"] in stable_window_addresses]
    raster_reader = load("visible_raster_layout", "research/anomaly/scanout.py")
    _, raster_meta, raster = raster_reader.draw_state(reader.module_payload(CAPTURE / "mature-window-complete.vsf", "VIC-II"))
    assert raster_meta["current_line"] == 220 > LAST
    actual = b"".join(raster[line * 384 + LEFT:line * 384 + RIGHT] for line in range(FIRST, LAST + 1))
    expected, coverage, overlaps, rows = compose(prepared_ram, regs, original)
    assert len(actual) == len(expected) == 42560 and actual == expected
    assert all(count > 0 for count in coverage.values()) and sum(coverage.values()) == 17028
    assert sha(expected) == "83f27386aa6570a6ef2e9477de2da44c726d340cb498ae4fc5641531352d656a"
    controls = []
    for variant in ("no_sprites", "hires", "ignore_high_X", "ignore_X_expand", "fresh_row", "uniform_offset3", "reverse_priority"):
        wrong, _, _, _ = compose(prepared_ram, regs, original, variant)
        count = sum(a != b for a, b in zip(actual, wrong))
        controls.append(dict(model=variant, differing_pixels=count,
                             discriminating=bool(count), interpretation="rejected by pixels" if count else "inconclusive in this scene"))
        if variant != "reverse_priority":
            assert count > 0, variant
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, data in (("expected-indices.bin", expected), ("actual-indices.bin", actual)):
        (OUTPUT / name).write_bytes(data)
    (OUTPUT / "mature-store-trace.json").write_text(json.dumps(mature_trace, indent=2) + "\n")
    (OUTPUT / "X-layout-model.json").write_text(json.dumps(models, indent=2) + "\n")
    result = {"pass": True, "script": artifact(Path(__file__).resolve()),
              "input_pins": [artifact(ROOT / path) for path in sorted(set(PINS) | set(old.PINS))],
              "case_pin": CASE_SHA, "wire_audit": wire.summary(case), "wire_startup_adaptation": startup_adaptation,
              "case_selection_adaptation": {"prior_function_sha256": sha(wire_source.encode()),
                                             "adapted_function_sha256": sha(adapted_wire_source.encode()), "case_name_replacements": 2},
              "checkpoints": sorted(records, key=lambda row: row["registers"]["clock"]),
              "original_entry": {"loaded_boot_bytes": 832, "known_bundle_bytes": 20261, "mismatches": 0,
                                 "callsite": 0x08a4, "stored_return": 0x08a6, "observed_return": 0x08a7},
              "pointer0_header_witness": pointer0,
              "prepared_pose_binding": {"pose": 4, "source_frame_address": 0xac6c, "source_rows": 91,
                                        "actual_destination": 0x715, "copied_rows": 92,
                                        "row_map": "source row0 twice, then rows1..90", "rows_match_original": True},
              "mature_layout": {"used_index": 59, "post_draw_size": 60, "Y_size": 127, "X": positions,
                                "high_X": high, "X_expand": expanded, "bank": old.bank_state(proof_state),
                                "background": 1, "D025": 11, "D026": 12, "individual_colors": [15] * 8},
              "visible_scope": {"first_line": FIRST, "last_line_inclusive": LAST, "left_X": LEFT,
                                "right_X_exclusive": RIGHT, "width": 320, "height": 133, "pixels": 42560,
                                "differences": 0, "expected": artifact(OUTPUT / "expected-indices.bin"),
                                "actual": artifact(OUTPUT / "actual-indices.bin"), "raster_storage": raster_meta,
                                "sprite_pixels_by_number": coverage, "visible_opaque_sprite_pixels": 17028,
                                "overlap_events": overlaps, "pixel_color_counts": {str(i): actual.count(i) for i in sorted(set(actual))}},
              "native_data_latches": witnesses, "negative_controls": controls,
              "pointer_and_cleanup_chronology": {"mature_trace": artifact(OUTPUT / "mature-store-trace.json"),
                                                 "ordinary_cells": 133, "extra_cells": 1,
                                                 "pointer_stores_checked": 1072, "pointer_store_first_raw_cycle": pointer_phase,
                                                 "sprite_disable": disabled, "later_row_clears": row_writes,
                                                 "prepared_rows_unchanged_until_after_display": True,
                                                 "color_register_writes_after_prepared": 0,
                                                 "store_timestamps_are_observer_boundaries": True},
              "source_model": artifact(OUTPUT / "X-layout-model.json"), "primary_VIC_source": source_rules(),
              "execution": {"restores": 0, "CPU_RAM_or_PC_injections": [], "native_resumes": 14,
                            "navigation_warp_resumes": navigation, "unwarped_resumes": unwarped, "speed": 100,
                            "owned_process_reaped": True, "ordinary_resends": 0, "restarts": 0},
              "native_screenshot": artifact(CAPTURE / "mature-window.png"),
              "last_valid_continuation": artifact(CAPTURE / "mature-window-complete.vsf"),
              "limits": ["The 133x320 component is exact; no complete 312-line frame, whole-demo FPS or physical hardware equivalence is claimed.",
                         "This is one natural mature pose/layout/palette. The 64 prepared poses and 72 X layouts do not imply all have native scanout coverage.",
                         "The screenshot is retained for visual review, not compared over its whole raster; the independent proof compares committed palette indices in the declared rectangle.",
                         "Overlapping slices can select identical colors. A zero-error reverse-priority control is inconclusive and is not evidence of uniquely distinguished priority.",
                         "The earlier native02 and its proof remain frozen; fresh boot avoids making an unsupported drive/IEC restore-equivalence claim."]}
    target = OUTPUT / "spritefpp-visible-proof.json"
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"pass": True, "capture_pairs": len(records), "pixels": len(actual), "differences": 0,
                      "all_eight_sprites_visible": all(coverage.values()), "controls": controls, "receipt": artifact(target)}, indent=2))


if __name__ == "__main__":
    main()
