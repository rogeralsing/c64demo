#!/usr/bin/env python3
"""Pure source ColorRAM publication from predicted attributes; no CPU execution."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import traceback

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "build/research/lab-polygons-20261109"
OUTPUT = BASE / "publication-analysis"
NATIVE = BASE / "native-analysis/accepted-01/ball-native-proof.json"
SOURCE = BASE / "display-source-analysis/accepted-01/display-source-proof.json"
PROFILE = {'attribute_proof': 'build/research/lab-polygons-20261109/attribute-analysis/accepted-01/ball-attribute-proof.json', 'attribute_proof_sha256': 'f0f4fa7941b24e9d9a3d4fbea1d39cf7e59bc387f87f4fb3a49fe17791cacbb6'}
PINS = {
    str(NATIVE.relative_to(ROOT)): "123732a8293916ffc9648b51686eeff314f1d0a9b371756efaab975976d968e5",
    str(SOURCE.relative_to(ROOT)): "30431ebfbef385a2b05a9983b2ef0094005053563ae3d60da95ef9ef980712ed",
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def artifact(path):
    b = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(b), sha256=sha(b))


def checked_artifact(row):
    path = ROOT / row["path"]
    assert artifact(path) == row, row["path"]
    return path.read_bytes()


def output_file(proof, directory, name):
    matches = [row for row in proof["outputs"] if row["name"] == name]
    assert len(matches) == 1, name
    row = matches[0]
    path = directory / row["name"]
    b = path.read_bytes()
    assert len(b) == row["bytes"] and sha(b) == row["sha256"], str(path)
    return path, b


def predict_color_copy(color_map, predicted_shadow, initial_color_ram):
    """Only source map + upstream prediction + genuine initial device state."""
    assert len(predicted_shadow) == 576 and len(initial_color_ram) == 1024
    assert all(value < 16 for value in initial_color_ram)
    shadow = bytearray(predicted_shadow)
    colors = bytearray(initial_color_ram)
    cells = color_map["cells"]
    assert len(cells) == 484 and len(color_map["groups"]) == 24
    stores, visited = [], set()
    consumed = 0
    cycles = 6 + 2  # caller JSR; LDY #0
    taken_crosses = 0
    for group in color_map["groups"]:
        accumulator = 0
        cycles += 2  # TYA at each column
        for index in range(group["first_cell"], group["end_cell"]):
            cell = cells[index]
            assert cell["index"] == index and cell["column"] == group["column"]
            slot = cell["source"] - 0xc5c0
            target = cell["destination"] - 0xd800
            assert 0 <= slot < 576 and 0 <= target < 1024 and slot not in visited
            visited.add(slot)
            event = shadow[slot]
            cycles += 4  # LDX absolute
            if event:
                accumulator = event
                shadow[slot] = 0
                consumed += 1
                cycles += 2 + 2 + 4  # BEQ not taken; TXA; STY absolute
            else:
                crossing = int((cell["first"] + 5) // 256 != cell["branch_zero_target"] // 256)
                taken_crosses += crossing
                cycles += 3 + crossing  # taken BEQ, including page crossing
            cycles += 4  # STA absolute
            colors[target] = accumulator & 15
            stores.append(dict(index=index, instruction_PC=cell["store_PC"],
                               address=cell["destination"], source=cell["source"],
                               raw_store_value=accumulator, stored_low_nibble=accumulator & 15,
                               input_event=event, source_cleared=bool(event),
                               completion_cycle_offset=cycles))
    assert len(stores) == len(visited) == 484
    assert all(shadow[i] == 0 for i in visited)
    assert all(shadow[i] == predicted_shadow[i] for i in range(576) if i not in visited)
    targets = {s["address"] - 0xd800 for s in stores}
    assert all(colors[i] == initial_color_ram[i] for i in range(1024) if i not in targets)
    cycles += 6  # RTS back to21AC
    return dict(color_ram=bytes(colors), cleared_shadow=bytes(shadow), stores=stores,
                nonzero_events_consumed=consumed, instruction_cycles=cycles,
                taken_branch_page_crosses=taken_crosses,
                changed_color_cells=sum(a != b for a, b in zip(colors, initial_color_ram)))


def color_state(context, stem):
    capture = context["captures"][stem]
    summary = capture["summary"]
    assert summary["accepted_natural_phase"]
    row = summary["actual_ColorRAM"]
    assert row["all1024_low_nibbles_equal_snapshot_device"]
    raw = checked_artifact(row["artifact"])
    low = bytes(value & 15 for value in raw)
    assert len(low) == 1024 and sha(low) == row["low_nibble_sha256"]
    assert low == bytes(capture["frozen_core_and_extended_state"]["vicii"]["color_ram"])
    return low, row["artifact"]


def is_IO_visible(registers):
    assert registers["port00"] & 7 == 7
    effective = registers["port01"]
    return bool(effective & 4) and bool(effective & 3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to(OUTPUT.resolve())
    assert PROFILE is not None, "Frozen attribute/custody provenance profile required"
    out.mkdir(parents=True, exist_ok=False)
    checked = Path(__file__).read_bytes()
    (out / "ball_publication.checked.py").write_bytes(checked)
    try:
        for name, pin in PINS.items():
            assert sha((ROOT / name).read_bytes()) == pin, name
        native = json.loads(NATIVE.read_text())
        source = json.loads(SOURCE.read_text())
        attr_path = ROOT / PROFILE["attribute_proof"]
        assert sha(attr_path.read_bytes()) == PROFILE["attribute_proof_sha256"]
        attributes = json.loads(attr_path.read_text())
        assert native["pass_"] and source["pass_"] and attributes["pass_"]
        color_map_path, color_raw = output_file(source, SOURCE.parent, "color-copy-map.json")
        color_map = json.loads(color_raw)
        shadow_path, predicted_shadow = output_file(attributes, attr_path.parent,
                                                    "predicted-color-shadow-c5c0.bin")
        context_path, raw_context = output_file(native, NATIVE.parent, "capture-machine-context.json")
        trace_path, raw_trace = output_file(native, NATIVE.parent, "trace-hits.json")
        context, traces = json.loads(raw_context), json.loads(raw_trace)
        captures = {row["stem"]: row for row in native["captures"]}
        names = dict(body="ball52-body-entry", edge="ball52-edge-entry",
                     pending="ball52-render-done", queued="ball52-request-queued",
                     selected="ball52-bank-selected", copied="ball52-color-copied",
                     cleared="ball52-request-cleared", wrap_a="ball52-wrap-a", wrap_b="ball52-wrap-b")
        for stem in names.values():
            assert captures[stem]["accepted_natural_phase"]
        assert captures[names["body"]]["registers"]["pc"] == 0x21bd
        assert captures[names["pending"]]["registers"]["pc"] == 0x2265
        assert captures[names["selected"]]["registers"]["pc"] == 0x21a9
        assert captures[names["copied"]]["registers"]["pc"] == 0x21ac
        body_ram = checked_artifact(captures[names["body"]]["ram"])
        assert list(body_ram[0x43:0x45]) == [0, 0]
        initial, initial_artifact = color_state(context, names["body"])

        # Only source/upstream prediction and genuine initial device bytes enter the pure model.
        predicted = predict_color_copy(color_map, predicted_shadow, initial)

        # Late RAM/device observations enter only the following comparison phase.
        ram = {role: checked_artifact(captures[stem]["ram"]) for role, stem in names.items()}
        assert list(ram["pending"][0x43:0x45]) == [0, 0]
        assert list(ram["queued"][0x43:0x45]) == [0, 1]
        assert list(ram["selected"][0x43:0x45]) == list(ram["copied"][0x43:0x45]) == [1, 1]
        assert list(ram["cleared"][0x43:0x45]) == [1, 0]
        source_rows = [row for row in source["inputs"] if Path(row["path"]).name == "20.ram.bin"]
        assert len(source_rows) == 1
        original20 = checked_artifact(source_rows[0])
        for role in ("pending", "selected", "copied"):
            assert ram[role][0x26b9:0x3d84] == original20[0x26b9:0x3d84]
            assert ram[role][0x21a9:0x21ac] == original20[0x21a9:0x21ac] == bytes.fromhex("20b926")
        assert predicted_shadow == ram["pending"][0xc5c0:0xc800]
        assert predicted_shadow == ram["selected"][0xc5c0:0xc800]
        edge_color, edge_artifact = color_state(context, names["edge"])
        before_copy, before_artifact = color_state(context, names["selected"])
        assert initial == edge_color == before_copy
        actual, actual_artifact = color_state(context, names["copied"])
        assert predicted["color_ram"] == actual
        assert predicted["cleared_shadow"] == ram["copied"][0xc5c0:0xc800]
        assert predicted["cleared_shadow"] == ram["cleared"][0xc5c0:0xc800]
        for role in ("cleared", "wrap_a", "wrap_b"):
            endpoint, _ = color_state(context, names[role])
            assert endpoint == predicted["color_ram"]
            summary = context["captures"][names[role]]["summary"]
            assert summary["VIC"]["normal_multicolor_bitmap"]
            assert summary["VIC"]["derived_bitmap"] == 0x4000
            assert summary["VIC"]["derived_screen"] == 0x6000
            assert summary["CIA2"]["driven_low_two_bits"]
            assert summary["CIA2"]["derived_VIC_bank"] == 0x4000

        # Watch coverage starts before every edge/event update and extends past wrap-b exports.
        edge = captures[names["edge"]]
        last = captures[names["wrap_b"]]
        watches = [p for p in native["checkpoint_bindings"]["setups"]
                   if p["operation"] == "store" and p["first"] == 0xd800 and p["last"] == 0xdbff]
        assert len(watches) == 1
        watch = watches[0]
        assert watch["setup"]["sequence"] < edge["stop_sequence"]
        assert watch["attached_r"]["sequence"] < edge["stop_sequence"]
        assert watch["deleted_sequence"] > last["snapshot_sequence"]
        assert watch["deleted_sequence"] > context["captures"][names["wrap_b"]]["summary"]["actual_ColorRAM"]["io_bank_export_sequence"]
        low = edge["registers"]["clock"]
        start = captures[names["selected"]]["registers"]["clock"]
        end = captures[names["copied"]]["registers"]["clock"]
        finish = last["registers"]["clock"]
        # Bounded timing preconditions: source writes only shadow/ColorRAM; no active sprite DMA,
        # CPU interrupt re-entry or potential PAL badline interval occurs during this routine.
        a_state = context["captures"][names["selected"]]["frozen_core_and_extended_state"]
        b_state = context["captures"][names["copied"]]["frozen_core_and_extended_state"]
        for state, role in [(a_state, "selected"), (b_state, "copied")]:
            v = state["vicii"]
            assert v["model"] == 1 and v["regs"][0x15] == v["sprite_dma"] == v["sprite_display_bits"] == 0
            assert captures[names[role]]["registers"]["flags"] & 4
            assert state["cia"]["CIA2"]["icr_mask"] == state["cia"]["CIA2"]["irq_enabled"] == 0
        assert end - start < 312 * 63
        assert all(not 48 <= (clock // 63) % 312 <= 247 for clock in range(start, end + 1))
        assert predicted["instruction_cycles"] == end - start
        device_hits = [h for h in traces if h["operation"] == "store"
                       and 0xd800 <= h["monitored_address"] < 0xdc00
                       and low <= h["registers"]["clock"] <= finish
                       and is_IO_visible(h["registers"])]
        assert len(device_hits) == 484
        assert all(start <= h["registers"]["clock"] <= end for h in device_hits)
        for expected, hit in zip(predicted["stores"], device_hits):
            assert expected["instruction_PC"] == hit["instruction_PC"]
            assert expected["address"] == hit["monitored_address"]
            assert hit["instruction_hex"] == bytes([0x8d, expected["address"] & 255,
                                                    expected["address"] >> 8]).hex()
            assert expected["raw_store_value"] == hit["raw_source_store_value"] == hit["registers"]["a"]
            assert hit["registers"]["port01"] == 0x35
            assert hit["registers"]["clock"] - start == expected["completion_cycle_offset"]
            expected["oracle_rawref"] = {key: hit[key] for key in ("sequence", "received_first",
                                                                 "received_end", "raw_block_sha256")}
        outputs = [dict(name="ball_publication.checked.py", bytes=len(checked), sha256=sha(checked))]
        for name, raw in [("predicted-color-ram-1024.bin", predicted["color_ram"]),
                          ("predicted-cleared-shadow-c5c0.bin", predicted["cleared_shadow"]),
                          ("ordered-logical-color-stores.json",
                           (json.dumps(predicted["stores"], indent=2) + "\n").encode())]:
            (out / name).write_bytes(raw)
            outputs.append(dict(name=name, bytes=len(raw), sha256=sha(raw)))
        proof = dict(pass_=True, scope="Source ColorRAM publication from independently predicted attributes and genuine initial device state; actual copy stages are oracles only.",
                     producer=artifact(Path(__file__)),
                     inputs=[artifact(NATIVE), artifact(SOURCE), artifact(attr_path),
                             artifact(color_map_path), artifact(shadow_path), artifact(context_path),
                             artifact(trace_path), source_rows[0], initial_artifact],
                     prediction_partition=dict(shadow=artifact(shadow_path), initial_ColorRAM=initial_artifact,
                                               source_map=artifact(color_map_path),
                                               native_current_or_late_output_used_as_prediction_seed=False),
                     oracle_partition=dict(pending_shadow=captures[names["pending"]]["ram"],
                                           selected_shadow=captures[names["selected"]]["ram"],
                                           edge_ColorRAM=edge_artifact, selected_ColorRAM=before_artifact,
                                           postcopy_ColorRAM=actual_artifact,
                                           postcopy_RAM=captures[names["copied"]]["ram"]),
                     results=dict(ColorRAM_low_bytes_equal=1024, shadow_bytes_equal=576,
                                  ordered_logical_stores_equal=484,
                                  nonzero_events_consumed=predicted["nonzero_events_consumed"],
                                  changed_ColorRAM_cells=predicted["changed_color_cells"],
                                  visible_device_state_stable_through_wrap_b=True,
                                  new_front_bitmap=0x4000, new_front_screen=0x6000),
                     ColorRAM_watch=watch, logical_copy_clock_interval=[start, end],
                     bounded_copy_timing=dict(predicted_cycles=predicted["instruction_cycles"],
                         observed_cycles=end-start, all484_store_completion_offsets_equal=True,
                         nonzero_events=predicted["nonzero_events_consumed"],
                         taken_branch_page_crosses=predicted["taken_branch_page_crosses"],
                         cycle_formula="JSR6+LDY2+24*TYA2+484*(LDX4+STA4)+zero*(BEQ3)+nonzero*(BEQ2+TXA2+STY4)+takenPageCrosses+RTS6",
                         source_contains_no_VIC_D015_or_CIA2_control_write=True,
                         actual_model1_sprite_DMA0_Iflag1_CIA2mask0=True,
                         all_elapsed_raster_lines_outside_PAL_badline48_to247=True,
                         scope="This fixed source copy interval and its observed device state only; no full renderer/scanout/FPS claim."),
                     outputs=outputs,
                     limits=["No CPU/interpreter/native/socket/build or downloaded host code is executed.",
                             "Attribute output is an upstream source prediction, not a native pending-event seed; actual pending/selected states are later comparisons.",
                             "Initial device state is genuine pre-body ColorRAM, with early-edge/pre-copy equality checked. Outside484cells is preserved.",
                             "All484 ordinary STA values/order are compared, not a claim about every physical bus transaction or unused I/O read bits.",
                             "Only declared natural phases are used; the custody proof retains its separate rejected export and all original events.",
                             "Stable ColorRAM/front selectors support the separate pixel compositor; this proof does not synthesize pixels or validate a complete renderer/scanout timing model."])
        encoded = (json.dumps(proof, indent=2) + "\n").encode()
        (out / "publication-proof.json").write_bytes(encoded)
        print(json.dumps(dict(pass_=True, stores=484, receipt_bytes=len(encoded),
                              receipt_sha256=sha(encoded), changed=predicted["changed_color_cells"])))
    except Exception as error:
        (out / "failure.json").write_text(json.dumps(dict(pass_=False, error_type=type(error).__name__,
            error=str(error), traceback=traceback.format_exc(),
            no_CPU_or_native_execution=True), indent=2) + "\n")
        raise


if __name__ == "__main__":
    main()
