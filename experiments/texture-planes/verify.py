#!/usr/bin/env python3
"""Prove live packed-plane sampling, coherent publication and both scanout fields.

This owns the independent mathematical/physical-pixel contract. Wrong Q8 carry,
plane selection, scatter address, buffer publication or raster bands fail here;
other examples do not cover this EC-specific combination. It uses natural code
breakpoints and ordinary memory/trace reads, with no production test flags.
"""

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess

from PIL import Image, ImageChops


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT = HERE / "build/verification"
TRACE = re.compile(r"#\d+ \(Trace\s+(load|store) ([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\n"
                   r"\.C:([0-9a-f]{4})[^\n]* A:([0-9a-f]{2})[^\n]*\s+(\d+)\r?$", re.I | re.M)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def coefficients(pose):
    a, b = pose * math.tau / 16, math.pi / 4 - pose * math.tau / 16
    return ([round(192 * math.cos(a)), round(96 * math.sin(a)),
             round(160 * math.cos(b)), round(128 * math.sin(b))],
            [round(-48 * math.sin(a)), round(40 * math.cos(a)),
             round(-64 * math.sin(b)), round(48 * math.cos(b))],
            [0x0340 + pose * 0x1B3, 0x0340 + pose * 0x27D,
             0xF840 + pose * 0x183, 0x0740 + pose * 0x19D])


def texture_byte(u, v):
    result = 0
    for pair in range(4):
        x = 4 * u + pair
        bit = ((x // 8 + v // 2) % 2) ^ ((x + v) % 13 < 3)
        result = (result << 2) | (2 if bit else 0)
    return result


def source_planes():
    first = bytes(texture_byte(index % 256, index // 512) for index in range(8192))
    return first + bytes(value >> 1 for value in first)


def render_reference(pose):
    horizontal, vertical, origin = coefficients(pose)
    output, reads = bytearray(6144), []
    low_plane_changes = fractional_carries = duplicate_reads = 0
    for row in range(96):
        for column in range(31):
            coordinates = [(origin[k] + horizontal[k] * column + vertical[k] * row) & 0xFFFF
                           for k in range(4)]
            values = []
            for plane in range(2):
                k = 2 * plane
                u, v = coordinates[k] >> 8, (coordinates[k + 1] >> 8) & 15
                values.append(texture_byte(u, v) >> plane)
                col = (horizontal[k] * column) & 0xFFFF
                start = (origin[k] + vertical[k] * row) & 0xFFFF
                carry = ((col & 255) + (start & 255)) >> 8
                base = ((col >> 8) + carry) & 255
                indexed = base + (start >> 8)
                reads.append(0x2000 + 0x2000 * plane + 512 * v + indexed)
                fractional_carries += carry
                duplicate_reads += indexed >= 256
            value = values[0] | values[1]
            target = (row // 32) * 2048 + column * 64 + 2 * (row % 32)
            output[target] = value
            low_plane_changes += value != values[0]
    return bytes(output), reads, {"low_plane_changes": low_plane_changes,
                                 "fractional_carries": fractional_carries,
                                 "duplicate_page_reads": duplicate_reads}


def trace_events(response):
    return [{"kind": kind, "address": int(address, 16), "line": int(line),
             "cycle": int(cycle), "pc": int(pc, 16), "value": int(value, 16),
             "clock": int(clock)}
            for kind, address, line, cycle, pc, value, clock in TRACE.findall(response)]


def field_image(font, parity, palette):
    output = Image.new("RGB", (384, 272), palette[0])
    colors = [0, 4, 6, 1]
    pixels = output.load()
    for row in range(96):
        for column in range(31):
            value = font[(row // 32) * 2048 + column * 64 + 2 * (row % 32)]
            for pair in range(4):
                color = palette[colors[(value >> (6 - 2 * pair)) & 3]]
                x, y = 64 + 8 * column + 2 * pair, 35 + 2 * row + parity
                pixels[x, y] = pixels[x + 1, y] = color
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publications", type=int, default=16)
    parser.add_argument("--fields", type=int, help="Bounded trial; does not write the final receipt.")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    shared = module("texture_plane_native_monitor", ROOT / "verify.py")
    labels = shared.read_labels(HERE / "build/main.sym")
    prg = (HERE / "build/example.prg").read_bytes()
    load_address = int.from_bytes(prg[:2], "little")
    assert load_address == 0x0801 and load_address + len(prg) - 2 < 0xD000
    planes = source_planes()
    expected = [render_reference(pose) for pose in range(16)]
    assert all(item[2]["low_plane_changes"] > 0 and item[2]["fractional_carries"] > 0 for item in expected)
    assert expected[0][2]["duplicate_page_reads"] > 0
    matrix = bytes(8 * (column - 4) + row % 8 if row < 24 and 4 <= column < 35 else 255
                   for row in range(25) for column in range(40)) + bytes([255]) * 24
    palette = [tuple(int(value, 16) for value in line.split())
               for line in (ROOT / "palettes/colodore.vpl").read_text().splitlines()
               if line and not line.startswith("#")]
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    command = shared.vice_command(os.environ.get("VICE", "x64sc"), HERE / "build/example.prg",
                                  port, ROOT / "palettes/colodore.vpl")
    monitor = None
    with (OUTPUT / "vice.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            with shared.connect_monitor(process, port) as connection:
                monitor = shared.Monitor(connection)
                monitor.run("r")
                def checkpoint(command):
                    response = monitor.run(command)
                    return int(re.search(r"(?:BREAK|TRACE):\s+(\d+)", response)[1])

                start_break = checkpoint(f"break {labels['start']:04x}")
                monitor.run("x")
                monitor.run("bank ram")
                ram = monitor.memory(OUTPUT / "loaded-ram.bin", 0, 0xFFFF)
                monitor.run("bank cpu")
                assert ram[load_address:load_address + len(prg) - 2] == prg[2:]
                assert ram[0x2000:0x6000] == planes
                monitor.run(f"delete {start_break}")
                render_break = checkpoint(f"break {labels['renderScene']:04x}")
                monitor.run("x")
                _, _, preparation_start = monitor.registers()
                monitor.run(f"delete {render_break}")
                source_trace = checkpoint("trace load 2000 5fff")
                complete_break = checkpoint(f"break {labels['renderComplete']:04x}")
                response = monitor.run("x")
                loads = trace_events(response)
                (OUTPUT / "initial-source-loads.log").write_text(response)
                assert [event["address"] for event in loads] == expected[0][1], (len(loads), "all5952 physical source addresses")
                _, _, preparation_end = monitor.registers()
                monitor.run(f"delete {source_trace}")
                monitor.run(f"delete {complete_break}")
                ready_break = checkpoint(f"break {labels['ready']:04x}")
                monitor.run("x")
                monitor.run("bank ram")
                ram = monitor.memory(OUTPUT / "initialized-ram.bin", 0, 0xFFFF)
                monitor.run("bank cpu")
                assert ram[0xA000:0xB800] == expected[0][0]
                assert ram[0xE000:0xF800] == bytes(6144)
                assert ram[0xB800:0xBC00] == ram[0xF800:0xFC00] == matrix
                monitor.run(f"delete {ready_break}")
                monitor.run("trace store dd00")
                monitor.run("trace store d011 d018")
                monitor.run(f"trace store {labels['renderReady']:04x}")
                monitor.run(f"break {labels['fieldComplete']:04x}")
                records, screenshots, publication_fields, pairs = [], [], [], {}
                prior_publication, last_ready_clock = 0, None
                for field in range(1, 1001):
                    response = monitor.run("x")
                    events = trace_events(response)
                    monitor.run("bank ram")
                    ram = monitor.memory(OUTPUT / "latest-ram.bin", 0, 0xFFFF)
                    monitor.run("bank cpu")
                    state = {name: ram[labels[name]] for name in
                             ("frontBuffer", "frontPose", "renderPose", "renderReady", "fieldParity")}
                    publication = int.from_bytes(ram[labels["publicationCounter"]:labels["publicationCounter"] + 2], "little")
                    assert int.from_bytes(ram[labels["fieldCounter"]:labels["fieldCounter"] + 2], "little") == field
                    parity, pose, front = state["fieldParity"], state["frontPose"], state["frontBuffer"]
                    assert parity == (field - 1) % 2
                    assert pose == publication % 16 and front == publication % 2
                    assert publication in (prior_publication, prior_publication + 1)
                    ready_events = [event for event in events if event["address"] == labels["renderReady"]]
                    for event in ready_events:
                        if event["value"] == 1:
                            last_ready_clock = event["clock"]
                        else:
                            assert event["value"] == 0 and last_ready_clock is not None
                            assert event["clock"] > last_ready_clock and parity == 0
                    if publication != prior_publication:
                        assert parity == 0 and ready_events[-1]["value"] == 0
                        publication_fields.append(field)
                    font = expected[pose][0]
                    front_base = 0xA000 + front * 0x4000
                    assert ram[front_base:front_base + 6144] == font, (field, pose, "full visible font")
                    assert ram[0xB800:0xBC00] == ram[0xF800:0xFC00] == matrix
                    if state["renderReady"]:
                        back_base = 0xE000 - front * 0x4000
                        assert ram[back_base:back_base + 6144] == expected[state["renderPose"]][0]
                    banks = [event for event in events if event["address"] == 0xDD00]
                    charsets = [event for event in events if event["address"] == 0xD018]
                    assert len(banks) == 1 and banks[0]["value"] == (0x81 ^ front) and banks[0]["line"] < 51
                    assert [event["value"] for event in charsets] == [0xE8, 0xEA, 0xEC]
                    assert [event["line"] for event in charsets][1:] == [114 + parity, 178 + parity], charsets
                    assert charsets[0]["line"] < 51
                    for event in events:
                        if event["address"] == 0xD011 and 51 <= event["line"] <= 250:
                            assert event["value"] & 0x7F == 0x1B + parity
                    vic = monitor.memory(OUTPUT / "vic.bin", 0xD000, 0xD03F)
                    assert vic[0x11] & 0x7F == 0x1B + parity and vic[0x16] & 0x1F == 0x18
                    assert vic[0x15] == 0 and (vic[0x21] & 15, vic[0x22] & 15, vic[0x23] & 15) == (0, 4, 6)
                    should_capture = (publication, parity) not in pairs
                    screenshot = None
                    if should_capture:
                        screenshot = OUTPUT / f"publication-{publication:02d}-field-{parity}.png"
                        monitor.run(f'scrsh "{screenshot}" 2')
                        image = Image.open(screenshot).convert("RGB")
                        reference = field_image(font, parity, palette)
                        difference = ImageChops.difference(image, reference)
                        if difference.getbbox() is not None:
                            reference.save(OUTPUT / "expected-failed.png")
                            difference.save(OUTPUT / "difference-failed.png")
                            raise AssertionError((field, publication, parity, "full field pixels"))
                        pairs[publication, parity] = image
                        screenshots.append(image)
                        if parity == 1:
                            woven = Image.new("RGB", image.size, palette[0])
                            for row in range(192):
                                source = pairs[publication, row % 2]
                                woven.paste(source.crop((64, 35 + row, 312, 36 + row)), (64, 35 + row))
                            reference_pair = field_image(font, 0, palette)
                            for row in range(96):
                                reference_pair.paste(reference_pair.crop((64, 35 + 2 * row, 312, 36 + 2 * row)),
                                                     (64, 36 + 2 * row))
                            assert ImageChops.difference(woven, reference_pair).getbbox() is None
                            woven.save(OUTPUT / f"publication-{publication:02d}-digital-weave.png")
                    _, raster, clock = monitor.registers()
                    records.append({"field": field, "publication": publication, "pose": pose,
                                    "parity": parity, "front_buffer": front, "clock": clock,
                                    "raster": raster, "render_ready": state["renderReady"],
                                    "bank_events": banks, "charset_events": charsets,
                                    "ready_events": ready_events,
                                    "screenshot": screenshot.name if screenshot else None})
                    prior_publication = publication
                    if field % 32 == 0:
                        print(f"Checked {field} fields, {publication} complete publications", flush=True)
                    if args.fields and field >= args.fields:
                        break
                    if not args.fields and publication >= args.publications and parity == 1:
                        break
                else:
                    raise AssertionError("Publication watchdog expired")
                monitor.run("bank ram")
                ram = monitor.memory(OUTPUT / "final-ram.bin", 0, 0xFFFF)
                monitor.run("bank cpu")
                assert ram[0x2000:0x6000] == planes
                color_ram = monitor.memory(OUTPUT / "color-ram.bin", 0xD800, 0xDBFF)
                assert all(value & 15 == 9 for value in color_ram)
                intervals = [b - a for a, b in zip(publication_fields, publication_fields[1:])]
                screenshots[0].save(OUTPUT / "texture-planes.gif", save_all=True,
                                    append_images=screenshots[1:], duration=100, loop=0)
                result = {"pass": True, "fields": len(records), "publications": prior_publication,
                          "initial_ordered_source_reads_checked": len(loads),
                          "initial_source_duplicate_page_reads": expected[0][2]["duplicate_page_reads"],
                          "initial_display_disabled_render_clocks": preparation_end - preparation_start,
                          "visible_font_bytes_checked_each_field": 6144,
                          "matrix_bytes_checked_each_field": 2048,
                          "full_native_screenshots_checked": len(screenshots),
                          "pixels_checked_per_screenshot": 384 * 272,
                          "digital_two_field_weaves_checked": len(pairs) // 2,
                          "publication_intervals_in_PAL_fields": intervals,
                          "mean_publication_interval_fields": sum(intervals) / len(intervals) if intervals else None,
                          "field_intervals_in_PAL_clocks": sorted(set(b["clock"] - a["clock"] for a, b in zip(records, records[1:]))),
                          "reference_pose_controls": [item[2] for item in expected],
                          "records": records, "command": command,
                          "program_sha256": hashlib.sha256(prg).hexdigest(),
                          "scope": "Own complementary packed bit planes, live independent fixed-point transforms and OR sampling; coherent double-buffer publication, three-band charset scanout and two literal scroll fields. Digital weave is an offline reconstruction, not an analog/CRT or original EC temporal claim. No stored animation frames or original artwork."}
                (OUTPUT / ("trial-receipt.json" if args.fields else "receipt.json")).write_text(json.dumps(result, indent=2) + "\n")
                print(json.dumps({key: value for key, value in result.items()
                                  if key not in ("records", "command", "reference_pose_controls")}, indent=2))
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
