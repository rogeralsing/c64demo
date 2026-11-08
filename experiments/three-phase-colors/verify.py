#!/usr/bin/env python3
"""Check literal three-phase pixels, live bank timing and retained sprite state."""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import subprocess

from PIL import Image, ImageChops


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT = HERE / "build/verification"
TRACE = re.compile(r"#\d+ \(Trace store ([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\n"
                   r"\.C:([0-9a-f]{4})[^\n]* A:([0-9a-f]{2})[^\n]*\s+(\d+)\r?$", re.I | re.M)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def ink(phase, x, y):
    radius = ((x - 160) ** 2 + (2 * y - 191) ** 2) // 192
    return (radius + x // 7 + y // 5 + 5 * phase) % 16 < 8


def font_bytes(bank, phase):
    return bytes(sum(int(ink(phase, (code // 6) * 8 + bit,
                            bank * 48 + (code % 6) * 8 + row)) << (7 - bit)
                     for bit in range(8)) for code in range(240) for row in range(8))


def mask_bytes(residue):
    return bytes(sum(int((x + 2 * y + x // 6) % 3 == residue) << (7 - bit)
                     for bit in range(8) for x in [(column * 8 + bit)])
                 for y in range(21) for column in range(3))


def trace_events(response):
    return [{"address": int(address, 16), "line": int(line), "cycle": int(cycle),
             "pc": int(pc, 16), "value": int(value, 16), "clock": int(clock)}
            for address, line, cycle, pc, value, clock in TRACE.findall(response)]


def pixels(phase, base_x, low_pointer, high_pointer, colors, slots, banks):
    frame_clock = banks[0]["clock"] - 63 * banks[0]["line"] - banks[0]["cycle"]
    assert all(event["clock"] == frame_clock + 63 * event["line"] + event["cycle"] for event in banks)
    output, owners = bytearray(), Counter()
    transient_fetches = transient_differences = whole_row_differences = 0
    for y in range(192):
        raster, row = 55 + y, y % 48
        sprite_row = y % 21
        for column in range(40):
            fetch = frame_clock + 63 * raster + 15 + column
            event = max((event for event in banks if event["clock"] - 1 < fetch), key=lambda item: item["clock"])
            selected = event["value"] & 3
            final = selected
            if event["value"] == 0x3E and fetch == event["clock"]:
                selected = 3
                transient_fetches += 1
            for bit in range(8):
                x = column * 8 + bit
                underlay = 6
                owner = "blue_background"
                sx = (x - (base_x - 24)) % 24
                if base_x - 24 <= x < base_x - 24 + 96:
                    address, flag = 3 * sprite_row + sx // 8, 0x80 >> (sx % 8)
                    if slots[low_pointer - 0x8C][address] & flag:
                        underlay, owner = colors[0], "lower_numbered_sprite"
                    elif slots[high_pointer - 0x8C][address] & flag:
                        underlay, owner = colors[1], "upper_numbered_sprite"
                foreground = ink(phase, x, selected * 48 + row)
                color = 0 if foreground else underlay
                output.append(color)
                owners["black_character" if foreground else owner] += 1
                if selected != final:
                    transient_differences += foreground != ink(phase, x, final * 48 + row)
                whole_row_differences += foreground != ink(phase, x, (y // 48) * 48 + row)
    return bytes(output), {"ownership": dict(owners), "temporary_bank3_glyph_fetches": transient_fetches,
                           "pixels_changed_if_GLUE_transient_ignored": transient_differences,
                           "pixels_changed_if_six_whole_rows_assumed": whole_row_differences,
                           "frame_start_clock": frame_clock}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fields", type=int, default=99)
    args = parser.parse_args()
    if args.fields < 3:
        parser.error("At least three fields are required.")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    shared = module("shared_native_monitor", ROOT / "verify.py")
    snapshots = module("colors_snapshot_helpers", ROOT / "research/quondam/snapshot_state.py")
    labels = shared.read_labels(HERE / "build/main.sym")
    program = (HERE / "build/example.prg").read_bytes()
    load_address = int.from_bytes(program[:2], "little")
    load_end = load_address + len(program) - 2
    assert load_address == 0x0801 and load_end == 0x7A00 and load_end < 0xD000
    fonts = {(bank, phase): font_bytes(bank, phase) for bank in range(4) for phase in range(3)}
    masks = [mask_bytes(residue) for residue in range(3)]
    permutation = [(index * 17 + 5) % 63 for index in range(63)]
    assert sorted(permutation) == list(range(63))
    assert all(sum(bool(mask[i] & (0x80 >> bit)) for i in range(63) for bit in range(8)) == 168 for mask in masks)
    assert all(sum(bool(mask[i] & (0x80 >> bit)) for mask in masks) == 1 for i in range(63) for bit in range(8))
    palette = [tuple(int(value, 16) for value in line.split())
               for line in (ROOT / "palettes/colodore.vpl").read_text().splitlines()
               if line and not line.startswith("#")]
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    command = shared.vice_command(os.environ.get("VICE", "x64sc"), HERE / "build/example.prg",
                                  port, ROOT / "palettes/colodore.vpl") + ["-gluelogictype", "1"]
    monitor = None
    with (OUTPUT / "vice.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            with shared.connect_monitor(process, port) as connection:
                monitor = shared.Monitor(connection)
                monitor.run("r")
                monitor.run(f"break {labels['start']:04x}")
                monitor.run("x")
                monitor.run("bank ram")
                loaded = monitor.memory(OUTPUT / "normal-loaded-ram.bin", 0, 0xFFFF)
                monitor.run("bank cpu")
                assert loaded[load_address:load_end] == program[2:]
                monitor.run("delete 1")
                monitor.run(f"break {labels['ready']:04x}")
                monitor.run("x")
                monitor.run(f'dump "{OUTPUT / "initialized.vsf"}"')
                assert snapshots.module_payload(OUTPUT / "initialized.vsf", "GLUE") == bytes((1, 0, 0))
                monitor.run("bank ram")
                initialized = monitor.memory(OUTPUT / "initialized-ram.bin", 0, 0xFFFF)
                monitor.run("bank cpu")
                for (bank, phase), data in fonts.items():
                    base = bank * 0x4000 + 0x2800 + phase * 0x800
                    assert initialized[base:base + 1920] == data
                monitor.run("delete 2")
                monitor.run("trace store dd00 dd02")
                monitor.run("trace store d000 d02e")
                monitor.run(f"break {labels['fieldComplete']:04x}")
                low_pointer, high_pointer = 0x8D, 0x8C
                slots = [bytearray(64) for _ in range(3)]
                records, images, clocks = [], [], []
                y_stores = bank_stores = transient_negative = whole_row_negative = 0
                for field in range(1, args.fields + 1):
                    response = monitor.run("x")
                    events = trace_events(response)
                    banks = [event for event in events if event["address"] == 0xDD02]
                    assert [event["value"] for event in banks] == [0x3C, 0x3D, 0x3E, 0x3F]
                    assert [event["line"] for event in banks] == [4, 102, 150, 198], banks
                    assert not [event for event in events if event["address"] == 0xDD00]
                    phase, motion = field % 3, (field - 1) % 32
                    if phase == 0:
                        low_pointer, high_pointer, colors = 0x8C, 0x8D, (2, 5)
                    elif phase == 1:
                        high_pointer, colors = 0x8E, (5, 2)
                    else:
                        low_pointer, colors = 0x8D, (2, 5)
                    if field <= 63:
                        at = permutation[field - 1]
                        for slot, source in zip(slots, masks):
                            slot[at] = source[at]
                    y_events = [event for event in events if 0xD001 <= event["address"] <= 0xD00F and event["address"] % 2]
                    assert [(event["address"], event["value"]) for event in y_events] == [
                        (0xD001 + 2 * sprite, value) for value in range(54, 244, 21) for sprite in range(8)]
                    assert all(event["line"] < event["value"] for event in y_events)
                    d018 = [event for event in events if event["address"] == 0xD018]
                    assert len(d018) == 1 and d018[0]["value"] == 0x9A + 2 * phase and d018[0]["line"] < 55
                    assert not [event for event in events if 55 <= event["line"] <= 246
                                and event["address"] not in {0xDD02, *range(0xD001, 0xD010, 2)}]
                    monitor.run("bank ram")
                    ram = monitor.memory(OUTPUT / "latest-ram.bin", 0, 0xFFFF)
                    monitor.run("bank cpu")
                    assert int.from_bytes(ram[labels["fieldCounter"]:labels["fieldCounter"] + 2], "little") == field
                    assert ram[labels["phase"]] == phase and ram[labels["motion"]] == motion
                    assert ram[labels["lowPointer"]] == low_pointer and ram[labels["highPointer"]] == high_pointer
                    assert ram[labels["revealCount"]] == min(field, 63)
                    for (bank, selected_phase), data in fonts.items():
                        base = bank * 0x4000 + 0x2800 + selected_phase * 0x800
                        assert ram[base:base + 1920] == data
                    matrix = bytes(6 * column + row % 6 for row in range(24) for column in range(40))
                    for bank in range(4):
                        base = bank * 0x4000
                        assert ram[base + 0x2400:base + 0x2400 + 960] == matrix
                        assert ram[base + 0x27F8:base + 0x2800] == bytes([low_pointer] * 4 + [high_pointer] * 4)
                        for residue in range(3):
                            offset = base + 0x2300 + residue * 64
                            assert ram[offset:offset + 64] == slots[residue]
                    vic = monitor.memory(OUTPUT / "vic.bin", 0xD000, 0xD03F)
                    assert vic[0x11] & 0x7F == 0x17 and vic[0x16] & 0x1F == 8
                    assert vic[0x15] == vic[0x1B] == 255
                    assert vic[0x17] == vic[0x1C] == vic[0x1D] == 0
                    assert vic[0x18] & 0xFE == 0x9A + 2 * phase
                    assert bytes(value & 15 for value in vic[0x27:0x2F]) == bytes([colors[0]] * 4 + [colors[1]] * 4)
                    base_x = 120 + 3 * motion
                    for sprite in range(8):
                        hardware_x = vic[sprite * 2] + (256 if vic[0x10] & (1 << sprite) else 0)
                        assert hardware_x == base_x + 24 * (sprite % 4)
                        assert vic[sprite * 2 + 1] == 243
                    color_ram = monitor.memory(OUTPUT / "color-ram.bin", 0xD800, 0xDBFF)
                    assert all(value & 15 == 0 for value in color_ram)
                    expected_indices, geometry = pixels(phase, base_x, low_pointer, high_pointer, colors, slots, banks)
                    expected = Image.new("RGB", (320, 192))
                    expected.putdata([palette[index] for index in expected_indices])
                    screenshot = OUTPUT / f"field-{field:03d}.png"
                    monitor.run(f'scrsh "{screenshot}" 2')
                    image = Image.open(screenshot).convert("RGB")
                    canvas = Image.new("RGB", image.size, palette[0])
                    canvas.paste(expected, (32, 39))
                    difference = ImageChops.difference(image, canvas)
                    if difference.getbbox() is not None:
                        expected.save(OUTPUT / "expected-failed.png")
                        difference.save(OUTPUT / "difference-failed.png")
                        raise AssertionError((field, phase, "full pixels including banks and paired sprites"))
                    images.append(image)
                    _, raster, clock = monitor.registers()
                    clocks.append(clock)
                    records.append({"field": field, "phase": phase, "motion": motion,
                                    "retained_pointers": [low_pointer, high_pointer], "sprite_colors": colors,
                                    "revealed_bytes_per_mask": min(field, 63), "clock": clock, "raster": raster,
                                    "bank_events": banks, "screenshot": screenshot.name, **geometry})
                    y_stores += len(y_events)
                    bank_stores += len(banks)
                    transient_negative += geometry["pixels_changed_if_GLUE_transient_ignored"]
                    whole_row_negative += geometry["pixels_changed_if_six_whole_rows_assumed"]
                    if field in (1, 4, 63, args.fields):
                        (OUTPUT / f"ram-field-{field:03d}.bin").write_bytes(ram)
                    if field % 12 == 0:
                        print(f"Checked {field} complete native fields", flush=True)
                if args.fields >= 4:
                    assert records[0]["phase"] == records[3]["phase"] == 1
                    assert records[0]["retained_pointers"] != records[3]["retained_pointers"]
                assert transient_negative > 0 and whole_row_negative > 0
                images[0].save(OUTPUT / "three-phase-colors.gif", save_all=True,
                               append_images=images[1:], duration=100, loop=0)
                receipt = {"pass": True, "fields": args.fields,
                           "normal_load_range": [load_address, load_end - 1],
                           "all_loaded_payload_bytes_match_before_start": True,
                           "used_character_bytes_checked_per_field": 23040,
                           "matrix_bytes_checked_per_field": 3840,
                           "pixels_checked_per_field": 61440,
                           "full_screenshot_pixels_checked_per_field": images[0].width * images[0].height,
                           "bank_direction_stores_checked": bank_stores, "sprite_Y_stores_checked": y_stores,
                           "negative_control_pixels_ignoring_GLUE_transient": transient_negative,
                           "negative_control_pixels_assuming_whole_bank_rows": whole_row_negative,
                           "mean_field_interval_PAL_clocks": (clocks[-1] - clocks[0]) / (len(clocks) - 1),
                           "field_interval_PAL_clocks": sorted(set(b - a for a, b in zip(clocks, clocks[1:]))),
                           "records": records, "command": command,
                           "program_sha256": hashlib.sha256(program).hexdigest(),
                           "scope": "Own stored three-phase mathematical image, four column-ordered banks, retained paired-sprite pointers and63-byte reveal. Every normal native pixel follows independent character math/mask data and actual DDR-bank store timing including GLUE1 transient. No original Colors artwork, static RGB mixture, effective palette or analog/physical-hardware claim. GIF is slowed to100ms perfield for inspection."}
                filename = "receipt.json" if args.fields >= 99 else "trial-receipt.json"
                (OUTPUT / filename).write_text(json.dumps(receipt, indent=2) + "\n")
                print(json.dumps({key: value for key, value in receipt.items()
                                  if key not in ("records", "command", "field_interval_PAL_clocks")}, indent=2))
        finally:
            if monitor:
                (OUTPUT / "monitor.log").write_text("\n".join(monitor.transcript))
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
