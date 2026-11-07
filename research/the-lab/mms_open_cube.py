#!/usr/bin/env python3
"""Audit the original AND NOW open-panel capture and palette priority.

No VICE runs here. Original RAM-only 6502 APIs are replayed in py65 and compared
with the separately captured native buffers. Bitmap markers/prefixes also have
an independent arithmetic oracle. Attribute replay is explicitly not a complete
independent color/visibility oracle.
"""

import argparse
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OPEN_SHA = "800c5a0157d11b8a013cf8dd387f5b58d48a2ff38246a9bd623f46216a763cc7"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prefix(markers):
    result = bytearray(len(markers))
    for column in range(24):
        value = 0
        for row in range(192):
            value ^= markers[column * 192 + row]
            result[column * 192 + row] = value
    return result


def bitmap_address(bank, column, row):
    return bank + 0x40 + (row // 8) * 320 + row % 8 + column * 8


def priority_algebra():
    cases = []
    for outside, palette in ((0, [0, 7, 7, 13]), (3, [13, 7, 7, 0])):
        for a in range(2):
            for b in range(2):
                code = outside ^ a ^ (3 * b)
                wanted = 7 if a else (13 if b else 0)
                assert palette[code] == wanted
                cases.append({"outside_code": outside, "A": a, "B": b,
                              "output_code": code, "palette_color": wanted})
    # B may be stippled against empty black while A remains opaque/constant.
    for a in range(2):
        for b in range(2):
            for lit in range(2):
                code = 3 ^ a ^ (3 * b * lit)
                assert [13, 7, 7, 0][code] == (7 if a else (13 if b and lit else 0))
    # Omitting A's marker at a black sample instead exposes B, rather than
    # making an opaque black A sample over B.
    code = 3 ^ 0 ^ 3
    assert [13, 7, 7, 0][code] == 13
    return {"pass": True, "cases": cases,
            "condition": "At most one accepted covering region in each A/B layer; equal-color selectors01/10",
            "far_B_stipple_against_empty_black": True,
            "opaque_black_A_counterexample": {"seed": 3, "omitted_A_delta": 0,
                                               "B_delta": 3, "code": code,
                                               "actual_color": 13, "wanted_black": 0},
            "scope": "Two-layer palette truth table, not a general geometric depth test or textured compositor"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "build/research/the-lab")
    args = parser.parse_args()
    root = args.root.resolve()
    native_dir = root / "side2-targeted-02"
    native_path = native_dir / "ram-open-cube-frame.bin"
    native = native_path.read_bytes()
    assert len(native) == 65536 and sha(native) == OPEN_SHA
    helper = load(ROOT / "research/the-lab/mms_inventory.py", "mms_inventory")
    cpu = load(ROOT / "research/the-lab/inspect_side2.py", "lab_cpu")
    decoded = root / "side2-analysis/depacked"
    original21 = (decoded / "21.ram.bin").read_bytes()
    assert native[0x9AF8:0xBEFD] == original21[0x9AF8:0xBEFD]
    frames = helper.frames_from_stream(original21, 0x9AF8, 0xBEFD, 64)
    pointer = int.from_bytes(native[0x3E:0x40], "little")
    index, (_, records) = next((i, f) for i, f in enumerate(frames) if f[0] == pointer)
    assert index == 9 and pointer == 0x9FFF and len(records) == 24
    assert [native[p] for p in (0x43, 0x44, 0x47, 0x50, 0x51, 0x52)] == [1, 0, 1, 0, 0, 0]
    assert native[0x5F40:0x5F50] == bytes(range(16))
    markers, samples = helper.marker_reference(native, records, native[0x51], native[0x52])
    assert markers == native[0xC800:0xDA00]
    pixels = prefix(markers)
    fill, fill_instructions = helper.execute(cpu.Cpu, native, 0x260B)
    stores = [(a, v) for pc, a, v in fill.writes if helper.FILL_START <= pc < helper.FILL_END]
    assert len(stores) == 3600
    for address, value in stores:
        offset = address - 0xE040
        row, column = (offset // 320) * 8 + offset % 8, (offset % 320) // 8
        assert value == pixels[column * 192 + row] == native[address]

    # Replay boundary and attribute commands from clear event buffers. The
    # native checkpoint is before INC44, so current ColorRAM events await IRQ.
    image = bytearray(native)
    image[0xC380:0xDA00] = bytes(0x1680)
    image[0x53:0x56] = bytes((0x60, 0, 0xC0))
    edge, edge_instructions = helper.execute(cpu.Cpu, image, 0x2287, {"y": 0})
    assert edge.data[0xC800:0xDA00] == markers
    assert edge.data[0xC5C0:0xC800] == native[0xC5C0:0xC800]
    attributes, attribute_instructions = helper.execute(cpu.Cpu, edge.data, 0x6EE8)
    screen_stores = [(a, v) for _, a, v in attributes.writes if 0xDC00 <= a < 0xE000]
    assert len(screen_stores) == 484
    assert all(native[a] == v for a, v in screen_stores)
    colors, color_instructions = helper.execute(cpu.Cpu, native, 0x26B9)
    color_stores = [(a, v & 15) for _, a, v in colors.writes if 0xD800 <= a < 0xDC00]
    assert len(color_stores) == 484

    # Establish the displayed older input without calling the next pointer the
    # already-displayed frame. This checks covered samples, not all old bounds.
    front_candidates = []
    for candidate in (7, 8, 9):
        expected = prefix(helper.marker_reference(native, frames[candidate][1])[0])
        covered = differences = 0
        for x in range(96):
            shift = 6 - 2 * (x % 4)
            for y in range(192):
                value = (expected[(x // 4) * 192 + y] >> shift) & 3
                if value:
                    covered += 1
                    actual = (native[bitmap_address(0x4000, x // 4, y)] >> shift) & 3
                    differences += value != actual
        front_candidates.append({"pose": candidate, "covered_samples": covered,
                                 "mismatches": differences})
    assert [v["mismatches"] for v in front_candidates] == [3547, 0, 3605]

    by_code = {code: [e for e in records if 2 * (e[0] >> 7) + (e[1] >> 7) == code]
               for code in range(4)}
    assert not by_code[0] and not by_code[2]
    layer_a = prefix(helper.marker_reference(native, by_code[1])[0])
    layer_b = prefix(helper.marker_reference(native, by_code[3])[0])
    combinations, a_colors, touched_cells = Counter(), Counter(), set()
    for x in range(96):
        shift = 6 - 2 * (x % 4)
        for y in range(192):
            offset = (x // 4) * 192 + y
            a, b = (layer_a[offset] >> shift) & 3, (layer_b[offset] >> shift) & 3
            assert a in (0, 1) and b in (0, 3)
            combinations[a, b] += 1
            if a or b:
                address = 0xDC00 + (y // 8) * 40 + 8 + x // 4
                value = native[address]
                assert value >> 4 == value & 15
                touched_cells.add(address)
                assert ((native[bitmap_address(0xE000, x // 4, y)] >> shift) & 3) == a ^ b
                if a:
                    a_colors[value & 15] += 1
    after_speech = (native_dir / "ram-and-now-after-speech.bin").read_bytes()
    assert int.from_bytes(after_speech[0x3E:0x40], "little") == pointer
    commands = [{"raw": e.hex(" "), "x_start": e[0] & 127, "x_end": e[1] & 127,
                 "slope_bytes": list(e[2:4]), "y_start": e[4],
                 "bitmap_delta": 2 * (e[0] >> 7) + (e[1] >> 7),
                 "attribute_style": e[5] & 0xF0, "palette_index": e[5] & 15}
                for e in records]
    result = {"pass": True, "script_sha256": sha(Path(__file__).read_bytes()),
              "native_ram_path": str(native_path), "native_ram_sha256": sha(native),
              "entry_payload_receipt": str(native_dir / "file21-comparison.json"),
              "stream": {"file": 21, "range": [0x9AF8, 0xBEFD], "frames": 64,
                         "unchanged_in_native": True, "frame_being_completed": index,
                         "pointer": pointer, "records": len(records), "sampled_x": samples},
              "buffer_state": {"front_bank": 0x4000, "pending_back_bank": 0xE000,
                               "stopped_before": 0x2265, "pending_request_flag": native[0x44],
                               "after_speech_sha256": sha(after_speech),
                               "after_speech_pointer_is_next_input_not_displayed_pose": pointer,
                               "front_pose_candidates": front_candidates},
              "native_bitmap_proof": {"pass": True, "markers_compared": 4608,
                                      "actual_bitmap_stores_compared": len(stores),
                                      "original_fill_instructions": fill_instructions,
                                      "scope": "All actual pending-back bitmap stores; direct marker/prefix reference, preserved background outside stores untouched"},
              "attribute_replay": {"pass": True, "original_edge_instructions": edge_instructions,
                                   "pending_ColorRAM_shadow_bytes_compared": 576,
                                   "original_screen_attribute_instructions": attribute_instructions,
                                   "native_back_screen_stores_compared": len(screen_stores),
                                   "original_ColorRAM_copy_instructions": color_instructions,
                                   "literal_future_ColorRAM_stores": len(color_stores),
                                   "literal_future_ColorRAM_colors": dict(Counter(v for _, v in color_stores)),
                                   "scope": "Original-CPU attribute replay matches native pending state/backscreen; no independent per-panel color/depth oracle or native post-swap ColorRAM comparison"},
              "priority_layers": {"A_delta": 1, "B_delta": 3,
                                  "edges_by_delta": {k: len(v) for k, v in by_code.items()},
                                  "pixel_combinations": {f"{a},{b}": n for (a, b), n in combinations.items()},
                                  "all_touched_native_screen_cells_alias01_10": True,
                                  "touched_cells": len(touched_cells),
                                  "A_sample_colors": dict(a_colors),
                                  "scope": "Palette priority A over B is proven; the stream contains no 3D depths proving A is always geometrically nearer"},
              "commands": commands, "priority_algebra": priority_algebra(),
              "generator": helper.generator_proof(cpu.Cpu, (decoded / "20.ram.bin").read_bytes(), native)}
    output = root / "mms-open-cube-analysis"
    output.mkdir(exist_ok=True)
    (output / "proof.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("pass", "stream", "native_bitmap_proof",
                                                   "attribute_replay", "priority_layers")}, indent=2))


if __name__ == "__main__":
    main()
