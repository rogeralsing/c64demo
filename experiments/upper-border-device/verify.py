#!/usr/bin/env python3
"""Independent upper-border pixels, generated stores and true sprite crunch.

Protects this case's upper-border/mode/idle-fetch/pointer-repeat contract,
which the separate lower-border example does not exercise. Credible failures
include a late expansion write, wrong packed sprite offset, nonrepeated skip
row or one-cycle cell drift. Normal program, natural breakpoints, no test flags.
"""
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
MEMBERS = (0, 2, 4, 5)
POSITIONS = (96, 144, 208, 256)
PATTERNS = (0x81, 0x42, 0x42, 0x24, 0x18, 0x3C, 0x66, 0xC3, 0x99, 0xBD, 0xE7,
            0xBD, 0x99, 0xC3, 0x66, 0x3C, 0x18, 0x18, 0x24, 0x42, 0x81)
# Provenance of the inspected rules, not a runtime dependency on ignored
# research captures or source extractions. The native snapshot pins VICE3.10.
HARDWARE_SOURCE = {
    "vicii-fetch.c": "83fe621bfd6c3f9aadfe7c725f02392ba04db70c36248cdfea88d79883bb21d0",
    "vicii-mem.c": "f8e2bdd30fbe8abf60a7e77647723f4615834e5b414f2695698ed28b31857edf",
    "vicii-cycle.c": "561876187fde8bfe8636e64593543aa77a5e0855ebbd9fe56d9da4fa6eb564ba",
    "vicii-draw-cycle.c": "78f70f99f77d26c507d7ebb2dba46ea5e8d2083f71c28d1c4c56420486dafaf6",
}
TRACE = re.compile(r"#\d+ \(Trace store ([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\n"
                   r"\.C:([0-9a-f]{4})[^\n]* A:([0-9a-f]{2}) X:([0-9a-f]{2}) Y:([0-9a-f]{2})[^\n]*\s+(\d+)\r?$", re.I | re.M)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def rotated(value, phase):
    return ((value << phase) | (value >> (8 - phase))) & 255


def generated_cells(phase):
    output = bytearray()
    for row in range(21):
        cell = bytearray.fromhex("a5 f2 2c 00 00 ea 8d 21 d0 a5 f3 8d 11 d0 ea 9d b1 cf 8c 21 d0 8e 21 d0 8e 11 d0 a9 00 8d ff 7f 24 00")
        cell[28] = rotated(PATTERNS[row], phase)
        if row in (2, 17):
            assert PATTERNS[row] == PATTERNS[row - 1]
            cell[28] = 0x50 if row == 2 else 0x60
            cell[30:32] = bytes((0x18, 0xD0))
        output.extend(cell)
    return bytes(output) + b"\x60"


def artwork():
    result = bytearray()
    for column in range(4):
        for section in range(3):
            for offset in range(64):
                row, byte_column = divmod(offset, 3)
                symbols = []
                for pair in range(4):
                    x = 4 * byte_column + pair
                    if x in (0, 11) or (row + 2 * section) % 11 == 0:
                        symbol = 3
                    else:
                        symbol = 1 if x % 4 == 0 else 0
                        if (row + column + section) % 5 == 0 and x % 3 == 0:
                            symbol = 2
                    symbols.append(symbol)
                result.append(sum(symbol << (6 - 2 * pair) for pair, symbol in enumerate(symbols)))
    return bytes(result)


def events_from(response, ram):
    result = []
    for address, line, cycle, pc, a, x, y, clock in TRACE.findall(response):
        address, pc, a, x, y = (int(value, 16) for value in (address, pc, a, x, y))
        opcode = ram[pc]
        value = {0x8D: a, 0x9D: a, 0x8C: y, 0x8E: x}.get(opcode)
        if value is None:
            # IRQ acknowledgement uses INC D012 and generates two RMW writes;
            # those do not participate in the graphics state below.
            assert address in (0xD012, 0xD019), (address, pc, opcode)
            continue
        result.append({"address": address, "line": int(line), "cycle": int(cycle),
                       "pc": pc, "value": value, "clock": int(clock)})
    return result


def value_at(events, address, clock, initial):
    candidates = [event for event in events if event["address"] == address and event["clock"] <= clock]
    return candidates[-1]["value"] if candidates else initial


def pixels(events, frame_clock, assets, variant=None):
    """Direct idle-bit/pair compositor; does not emulate CPU or VICE rendering.

    PAL6569 store checkpoint T follows the Phi2 write at T-1. An idle fetch
    at T sees that byte. Color output changes at 8*(cycle-13)+1; old-PAL mode
    rising/falling edges arrive at subpixels4/6 of that same output group.
    These rules follow the inspected VICE3.10 fetch/draw-cycle source.
    """
    output = bytearray(384 * 272)
    owners = Counter()
    mode_edges = [(event["line"] * 504 + 8 * (event["cycle"] - 13)
                   + (4 if event["value"] & 0x60 else 6), event["value"])
                  for event in events if event["address"] == 0xD011]
    color_edges = [(event["line"] * 504 + 8 * (event["cycle"] - 13) + 1, event["value"] & 15)
                   for event in events if event["address"] == 0xD021]
    for line in range(16, 288):
        for x in range(32, 352):
            point = line * 504 + x
            mode = next((value for at, value in reversed(mode_edges) if at <= point), 8)
            background = next((value for at, value in reversed(color_edges) if at <= point), 0)
            color, owner = 0, "invalid_mode_or_black"
            if not mode & 0x60:
                column, bit = divmod(x - 37, 8)
                fetch = frame_clock + line * 63 + 15 + column
                fetch_mode = value_at(events, 0xD011, fetch, 8)
                pattern = value_at(events, 0x7FFF, fetch, 0) if not fetch_mode & 0x40 else 0
                if variant == "no_ghost":
                    pattern = 0
                foreground = 0 <= column < 40 and bool(pattern & (128 >> bit))
                color = 0 if foreground else background
                owner = "ghost_foreground" if foreground else "background_split"
            if variant != "no_sprites" and 10 <= line <= 74:
                if line <= 12:
                    counter = 3 * (line - 10)
                else:
                    counter = (5 + 3 * (line - 13)) & 63
                if variant == "no_crunch":
                    counter = 3 * (line - 10)
                for column, (sprite, xpos) in enumerate(zip(MEMBERS, POSITIONS)):
                    if not xpos + 8 <= x < xpos + 56 or counter >= 63:
                        continue
                    fetch_line = line - 1 if sprite < 3 else line
                    fetch_cycle = (57 + 2 * sprite) if sprite < 3 else (2 + 2 * (sprite - 4))
                    table = value_at(events, 0xD018, frame_clock + 63 * fetch_line + fetch_cycle, 0x40)
                    section = (table >> 4) - 4
                    if variant == "no_pointer_switch":
                        section = 0
                    assert section in (0, 1, 2)
                    pair = (x - xpos - 8) // 4
                    offset = (counter + pair // 4) & 63
                    value = assets[(column * 3 + section) * 64 + offset]
                    symbol = (value >> (6 - 2 * (pair % 4))) & 3
                    if symbol:
                        color, owner = (0, 0, 6, 1)[symbol], f"sprite_{sprite}"
                        break
            output[(line - 16) * 384 + x] = color
            owners[owner] += 1
    return bytes(output), dict(owners)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fields", type=int, default=9)
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    shared = module("device_native_monitor", ROOT / "verify.py")
    reader = module("device_snapshot_reader", ROOT / "research/quondam/snapshot_state.py")
    labels = shared.read_labels(HERE / "build/main.sym")
    program = (HERE / "build/example.prg").read_bytes()
    assets = artwork()
    palette = [tuple(int(value, 16) for value in line.split())
               for line in (ROOT / "palettes/colodore.vpl").read_text().splitlines()
               if line and not line.startswith("#")]
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    command = shared.vice_command(os.environ.get("VICE", "x64sc"), HERE / "build/example.prg", port,
                                  ROOT / "palettes/colodore.vpl") + ["-VICIImodel", "6569"]
    monitor = None
    with (OUTPUT / "vice.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            with shared.connect_monitor(process, port) as connection:
                monitor = shared.Monitor(connection)
                monitor.run("r")
                def checkpoint(command):
                    return int(re.search(r"(?:BREAK|TRACE):\s+(\d+)", monitor.run(command))[1])

                start = checkpoint(f"break {labels['start']:04x}")
                monitor.run("x")
                monitor.run("bank ram")
                loaded = monitor.memory(OUTPUT / "loaded-ram.bin", 0, 0xFFFF)
                monitor.run("bank cpu")
                assert loaded[0x0801:0x0801 + len(program) - 2] == program[2:]
                assert loaded[0x6000:0x6300] == assets
                monitor.run(f"delete {start}")
                ready = checkpoint(f"break {labels['ready']:04x}")
                monitor.run("x")
                monitor.run("bank ram")
                ram = monitor.memory(OUTPUT / "initialized-ram.bin", 0, 0xFFFF)
                monitor.run("bank cpu")
                assert ram[0x3000:0x3000 + 715] == generated_cells(0)
                for section in range(3):
                    for column, sprite in enumerate(MEMBERS):
                        assert ram[0x53F8 + section * 0x400 + sprite] == 0x80 + column * 3 + section
                monitor.run(f"delete {ready}")
                checkpoint("trace store d000 d02e")
                checkpoint("trace store 7fff")
                before = checkpoint(f"break {labels['crunch']:04x}")
                prefix = monitor.run("x")
                monitor.run(f'dump "{OUTPUT / "before-crunch.vsf"}"')
                pre = reader.read_snapshot(OUTPUT / "before-crunch.vsf")["vicii"]
                assert pre["model"] == 0 and pre["raster_line"] == 12 and pre["raster_cycle"] == 11
                assert pre["vborder"] == pre["set_vborder"] == 0 and pre["idle_state"] == 1
                for sprite in MEMBERS:
                    state = pre["sprites"][sprite]
                    assert (state["mc"], state["mcbase"], state["exp_flop"]) == (9, 6, 0)
                monitor.run(f"delete {before}")
                after = checkpoint(f"break {labels['afterCrunch']:04x}")
                prefix += monitor.run("x")
                monitor.run(f'dump "{OUTPUT / "after-crunch.vsf"}"')
                post = reader.read_snapshot(OUTPUT / "after-crunch.vsf")["vicii"]
                assert post["raster_line"] == 12 and post["raster_cycle"] == 15
                for sprite in MEMBERS:
                    state = post["sprites"][sprite]
                    assert (state["mc"], state["mcbase"], state["exp_flop"]) == (5, 5, 1)
                monitor.run(f"delete {after}")
                checkpoint(f"break {labels['frameComplete']:04x}")
                images, records = [], []
                for field in range(1, args.fields + 1):
                    response = prefix + monitor.run("x")
                    prefix = ""
                    monitor.run("bank ram")
                    ram = monitor.memory(OUTPUT / "latest-ram.bin", 0, 0xFFFF)
                    monitor.run("bank cpu")
                    phase = (field - 1) & 7
                    assert ram[labels["phase"]] == phase
                    assert int.from_bytes(ram[labels["frameCounter"]:labels["frameCounter"] + 2], "little") == field
                    assert ram[0x3000:0x3000 + 715] == generated_cells(phase)
                    assert ram[0x6000:0x6300] == assets
                    events = events_from(response, ram)
                    expansion = [event for event in events if event["address"] == 0xD017]
                    assert [(event["line"], event["cycle"], event["value"]) for event in expansion] == [(11, 17, 0x35), (12, 15, 0)]
                    assert not any(event["address"] in range(0xD001, 0xD010, 2) for event in events)
                    crunches = [event for event in events if event["address"] == 0xD017 and event["value"] == 0]
                    assert len(crunches) == 1 and (crunches[0]["line"], crunches[0]["cycle"]) == (12, 15)
                    frame_clock = crunches[0]["clock"] - 12 * 63 - 15
                    cells = [event for event in events if 0x3000 <= event["pc"] < 0x3000 + 714]
                    assert len(cells) == 147
                    for row in range(21):
                        group = cells[row * 7:(row + 1) * 7]
                        addresses = [0xD021, 0xD011, 0xD021, 0xD021, 0xD021, 0xD011,
                                     0xD018 if row in (2, 17) else 0x7FFF]
                        values = [2, 0x1A, 0x1A, 5, 0x70, 0x70,
                                  (0x50 if row == 2 else 0x60) if row in (2, 17) else rotated(PATTERNS[row], phase)]
                        assert [event["address"] for event in group] == addresses
                        assert [event["value"] for event in group] == values
                        assert [event["cycle"] for event in group] == [16, 23, 30, 34, 38, 42, 48]
                        assert all(event["line"] == 26 + row for event in group)
                    starts = [cells[7 * row]["clock"] for row in range(21)]
                    assert all(b - a == 63 for a, b in zip(starts, starts[1:]))
                    indices, contributions = pixels(events, frame_clock, assets)
                    screenshot = OUTPUT / f"field-{field:02d}.png"
                    monitor.run(f'scrsh "{screenshot}" 2')
                    image = Image.open(screenshot).convert("RGB")
                    reference = Image.new("RGB", (384, 272))
                    reference.putdata([palette[index] for index in indices])
                    difference = ImageChops.difference(image, reference)
                    if difference.getbbox() is not None:
                        reference.save(OUTPUT / "expected-failed.png")
                        difference.save(OUTPUT / "difference-failed.png")
                        wrong = [(i % 384, i // 384, a, b) for i, (a, b) in enumerate(zip(image.get_flattened_data(), reference.get_flattened_data())) if a != b]
                        (OUTPUT / "pixel-failure.json").write_text(json.dumps({"count": len(wrong), "first": wrong[:60]}, indent=2))
                        raise AssertionError((field, phase, len(wrong), "complete upper-border picture"))
                    controls = {}
                    for variant in ("no_ghost", "no_sprites", "no_crunch", "no_pointer_switch"):
                        alternate, _ = pixels(events, frame_clock, assets, variant)
                        controls[variant] = sum(a != b for a, b in zip(indices, alternate))
                        assert controls[variant] > 0
                    _, raster, clock = monitor.registers()
                    records.append({"field": field, "phase": phase, "raster": raster, "clock": clock,
                                    "frame_start_clock": frame_clock, "cell_events": cells,
                                    "pixel_contributions": contributions, "negative_control_pixels": controls,
                                    "screenshot": screenshot.name})
                    images.append(image)
                    print(f"Checked complete native field {field}/{args.fields}", flush=True)
                monitor.run(f'dump "{OUTPUT / "completed-field.vsf"}"')
                final = reader.read_snapshot(OUTPUT / "completed-field.vsf")["vicii"]
                assert final["model"] == 0 and final["sprite_dma"] == 0
                assert final["idle_state"] == 1 and final["allow_bad_lines"] == 0
                assert final["vborder"] == final["set_vborder"] == 0
                assert all(final["sprites"][sprite]["mcbase"] == 63 for sprite in MEMBERS)
                images[0].save(OUTPUT / "upper-border-device.gif", save_all=True,
                               append_images=images[1:], duration=100, loop=0)
                images[0].crop((32, 0, 352, 64)).resize((960, 192), Image.Resampling.NEAREST).save(OUTPUT / "upper-detail.png")
                intervals = [b["frame_start_clock"] - a["frame_start_clock"] for a, b in zip(records, records[1:])]
                assert not intervals or set(intervals) == {19656}
                result = {"pass": True, "fields": args.fields, "generated_cell_bytes": 715,
                          "cell_stores_checked": 147 * args.fields, "cell_period_PAL_clocks": 63,
                          "all_full_screenshot_pixels_checked_each_field": 384 * 272,
                          "crunch_before_mc_mcbase_flop": [9, 6, 0], "crunch_after_mc_mcbase_flop": [5, 5, 1],
                          "sprite_display_lines": [10, 74], "sprite_counter_wraps": 2,
                          "final_VIC_idle_border_and_DMA_end_match": True,
                          "hardware_model": "VICE3.10 PAL6569",
                          "hardware_source_sha256": HARDWARE_SOURCE,
                          "field_interval_PAL_clocks": sorted(set(intervals)), "records": records,
                          "command": command, "program_sha256": hashlib.sha256(program).hexdigest(),
                          "scope": "Own generated upper-border cells, PAL6569 mode/color fetch pipeline, true one-time crunch and repeated-row pointer-table switches. One explicit alignment; no original detector-family, other-VIC, analog or physical-hardware claims."}
                (OUTPUT / ("receipt.json" if args.fields >= 9 else "trial-receipt.json")).write_text(json.dumps(result, indent=2) + "\n")
                print(json.dumps({k: v for k, v in result.items() if k not in ("records", "command")}, indent=2))
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
