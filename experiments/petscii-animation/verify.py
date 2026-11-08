#!/usr/bin/env python3
"""Native ROM PETSCII, LZ output, beam-following colors and complete loop proof.

This is the primary boundary for this prepared screen/color player. A wrong
ROM bank, screen code, overlapping LZ copy, ColorRAM row deadline, premature
screen publication or frame wrap fails here. Expected pixels use the physical
ROM and asset bytes, never prepare.render or player-generated pixel output.
The monitor only observes natural boundaries; no test flags or PC/RAM edits.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
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


def events(response):
    return [{"address": int(address, 16), "line": int(line), "cycle": int(cycle),
             "pc": int(pc, 16), "value": int(value, 16), "clock": int(clock)}
            for address, line, cycle, pc, value, clock in TRACE.findall(response)]


def unpack(data, first):
    """Independent byte-command reader: growing output handles overlap naturally."""
    cursor, output = first, bytearray()
    literal_commands = match_commands = overlapping_matches = 0
    while data[cursor]:
        command = data[cursor]
        cursor += 1
        if command < 128:
            output.extend(data[cursor:cursor + command])
            cursor += command
            literal_commands += 1
        else:
            length, distance = command & 127, data[cursor]
            cursor += 1
            assert 0 < distance <= len(output)
            for _ in range(length):
                output.append(output[-distance])
            match_commands += 1
            overlapping_matches += length > distance
    assert len(output) == 2048
    return bytes(output), {"literal_commands": literal_commands, "match_commands": match_commands,
                           "overlapping_matches": overlapping_matches}


def picture(frame, font, palette):
    indexed = bytearray(384 * 272)
    for y in range(200):
        row, glyph_y = divmod(y, 8)
        for column in range(40):
            cell = row * 40 + column
            bits = font[frame[cell] * 8 + glyph_y]
            color = frame[1024 + cell]
            for x in range(8):
                indexed[(35 + y) * 384 + 32 + column * 8 + x] = color if bits & (128 >> x) else 0
    image = Image.new("RGB", (384, 272))
    image.putdata([palette[color] for color in indexed])
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publications", type=int, default=16,
                        help="16 proves all frames and wrap to frame zero; smaller is a trial.")
    args = parser.parse_args()
    assert 1 <= args.publications <= 32
    OUTPUT.mkdir(parents=True, exist_ok=True)
    common = module("petscii_native_monitor", ROOT / "verify.py")
    labels = common.read_labels(HERE / "build/main.sym")
    program = (HERE / "build/example.prg").read_bytes()
    load = int.from_bytes(program[:2], "little")
    loaded = bytes(load) + program[2:]
    raw = (HERE / "build/frames.raw").read_bytes()
    assert len(raw) == 32768 and load == 0x0801 and len(loaded) <= 0xD000
    frames = [raw[index:index + 2048] for index in range(0, len(raw), 2048)]
    codec_stats = Counter()
    for index, frame in enumerate(frames):
        decoded, stats = unpack(loaded, labels[f"packed{index}"])
        assert decoded == frame, (index, "prepared byte-command stream")
        assert all(value < 16 for value in frame[1024:])
        codec_stats.update(stats)
    assert codec_stats["overlapping_matches"] > 0
    executable = shutil.which(os.environ.get("VICE", "x64sc"))
    chargen_path = Path(executable).resolve().parents[1] / "share/vice/C64/chargen-901225-01.bin"
    if not chargen_path.is_file():
        chargen_path = Path("/opt/homebrew/share/vice/C64/chargen-901225-01.bin")
    chargen = chargen_path.read_bytes()
    assert len(chargen) == 4096
    # Independently identify every quadrant pattern from physical ROM contents.
    quadrant_codes = []
    for mask in range(16):
        ideal = bytes(sum((128 >> x) for x in range(8)
                          if mask & (1 << ((y // 4) * 2 + x // 4))) for y in range(8))
        matches = [code for code in range(256) if chargen[code * 8:code * 8 + 8] == ideal]
        assert matches, (mask, "ROM lacks expected quadrant block")
        quadrant_codes.append(matches)
    used = set(b"".join(frame[120:880] for frame in frames))
    assert all(any(code in used for code in matches) for matches in quadrant_codes)
    palette_path = ROOT / "palettes/colodore.vpl"
    palette = [tuple(int(value, 16) for value in line.split()[:3])
               for line in palette_path.read_text().splitlines()
               if line and not line.startswith("#")]
    expected_images = [picture(frame, chargen[:2048], palette) for frame in frames]
    assert len({image.tobytes() for image in expected_images}) == 16
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    command = common.vice_command(executable, HERE / "build/example.prg", port, palette_path)
    command += ["-VICIImodel", "6569", "-chargen", str(chargen_path)]
    monitor = None
    result = {"pass": False, "program_sha256": hashlib.sha256(program).hexdigest(),
              "chargen_path": str(chargen_path), "chargen_sha256": hashlib.sha256(chargen).hexdigest(),
              "raw_sha256": hashlib.sha256(raw).hexdigest(), "codec": dict(codec_stats), "command": command}
    receipt = OUTPUT / ("receipt.json" if args.publications >= 16 else "trial-receipt.json")
    with (OUTPUT / "vice.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            with common.connect_monitor(process, port) as connection:
                monitor = common.Monitor(connection)
                monitor.run("r")
                def checkpoint(text):
                    return int(re.search(r"(?:BREAK|TRACE):\s+(\d+)", monitor.run(text))[1])
                start = checkpoint(f"break {labels['start']:04x}")
                monitor.run("x")
                monitor.run("bank ram")
                ram = monitor.memory(OUTPUT / "loaded-ram.bin", 0, 0xFFFF)
                assert ram[load:len(loaded)] == program[2:]
                monitor.run("bank cpu")
                monitor.run(f"delete {start}")
                ready = checkpoint(f"break {labels['ready']:04x}")
                monitor.run("x")
                monitor.run(f"delete {ready}")
                checkpoint("trace store d800 dbe7")
                checkpoint("trace store d018")
                checkpoint(f"break {labels['decoded']:04x}")
                checkpoint(f"break {labels['frameComplete']:04x}")
                records, decodes, publications, all_images = [], [], [], []
                pending = []
                last_phase = last_publication = 0
                physical_colors = bytes(frames[0][1024:])
                total_color_stores = 0
                while len(records) < 512:
                    response = monitor.run("x")
                    pending.extend(events(response))
                    pc, raster, clock = monitor.registers()
                    monitor.run("bank ram")
                    ram = monitor.memory(OUTPUT / "latest-ram.bin", 0, 0xFFFF)
                    monitor.run("bank cpu")
                    state = {name: ram[labels[name]] for name in
                             ("shownFrame", "frontBuffer", "targetBuffer", "nextFrame", "publications", "colorReady")}
                    field = int.from_bytes(ram[labels["fieldCounter"]:labels["fieldCounter"] + 2], "little")
                    phase, front = state["shownFrame"], state["frontBuffer"]
                    assert ram[0x2000 + front * 0x800:0x2800 + front * 0x800] == frames[phase], (field, state, "front coherence")
                    if pc == labels["decoded"]:
                        target, next_frame = state["targetBuffer"], state["nextFrame"]
                        assert target == front ^ 1
                        assert next_frame == (phase + 1) % 16
                        assert ram[0x2000 + target * 0x800:0x2800 + target * 0x800] == frames[next_frame]
                        decodes.append({"frame": next_frame, "buffer": target, "field": field, "clock": clock})
                        continue
                    assert pc == labels["frameComplete"] and raster == 290
                    bank_events = [event for event in pending if event["address"] == 0xD018]
                    assert len(bank_events) == 1, (field, bank_events)
                    bank = bank_events[0]
                    origin = bank["clock"] - bank["line"] * 63 - bank["cycle"]
                    assert bank["line"] < 10 and bank["value"] == (0x84 | front * 0x20)
                    if records:
                        assert origin - records[-1]["field_origin_clock"] == 19656
                    color_events = [event for event in pending if 0xD800 <= event["address"] <= 0xDBE7]
                    if state["publications"] != last_publication:
                        assert state["publications"] == last_publication + 1
                        assert phase == (last_phase + 1) % 16 and front == (state["publications"] & 1)
                        assert decodes[-1]["frame"] == phase
                        assert records[-1]["color_upload_target"] == phase
                        assert physical_colors == frames[phase][1024:]
                        publications.append({"frame": phase, "buffer": front, "field": field, "clock": origin})
                        last_phase, last_publication = phase, state["publications"]
                    else:
                        assert phase == last_phase
                    upload_target, row_bounds = None, []
                    if color_events:
                        assert len(color_events) == 1000, (field, len(color_events))
                        upload_target = (phase + 1) % 16
                        assert decodes[-1]["frame"] == upload_target
                        assert [event["address"] for event in color_events] == list(range(0xD800, 0xDBE8))
                        for event in color_events:
                            cell = event["address"] - 0xD800
                            row = cell // 40
                            assert event["value"] == frames[upload_target][1024 + cell]
                            assert event["clock"] - origin >= (59 + 8 * row) * 63, (field, row, event, "write before old row scanout")
                            assert event["clock"] - origin < 312 * 63, (field, event, "missed publication field")
                        for row in range(25):
                            stores = color_events[row * 40:row * 40 + 40]
                            row_bounds.append([stores[0]["line"], stores[0]["cycle"], stores[-1]["line"], stores[-1]["cycle"]])
                        physical_colors = frames[upload_target][1024:]
                        total_color_stores += 1000
                    colors = monitor.memory(OUTPUT / "color-ram.bin", 0xD800, 0xDBFF)
                    assert bytes(value & 15 for value in colors) == physical_colors
                    vic = monitor.memory(OUTPUT / "vic.bin", 0xD000, 0xD03F)
                    assert vic[0x11] & 0x7F == 0x1B and vic[0x16] & 31 == 8
                    assert vic[0x18] & 0xFE == (0x84 | front * 0x20) and vic[0x15] == 0
                    assert vic[0x20] & 15 == vic[0x21] & 15 == 0
                    cia = monitor.memory(OUTPUT / "cia2.bin", 0xDD00, 0xDD03)
                    assert cia[0] & 3 == cia[2] & 3 == 3
                    screenshot = OUTPUT / f"field-{field:03d}.png"
                    monitor.run(f'scrsh "{screenshot}" 2')
                    actual = Image.open(screenshot).convert("RGB")
                    difference = ImageChops.difference(actual, expected_images[phase])
                    if difference.getbbox():
                        expected_images[phase].save(OUTPUT / "expected-failed.png")
                        difference.save(OUTPUT / "difference-failed.png")
                        wrong = sum(a != b for a, b in zip(actual.get_flattened_data(), expected_images[phase].get_flattened_data()))
                        raise AssertionError((field, phase, wrong, "full ROM screen pixels"))
                    records.append({"field": field, "frame": phase, "buffer": front, "publications": state["publications"],
                                    "field_origin_clock": origin, "color_upload_target": upload_target,
                                    "ColorRAM_stores": len(color_events), "row_store_bounds": row_bounds,
                                    "screenshot": screenshot.name})
                    all_images.append(actual)
                    pending = []
                    if field % 16 == 0:
                        print(f"Checked {field} PAL fields; frame {phase}, {last_publication} publications", flush=True)
                    if state["publications"] >= args.publications:
                        break
                else:
                    raise AssertionError("Publication deadline: 512 fields elapsed")
                assert len(publications) == args.publications
                if args.publications >= 16:
                    assert [entry["frame"] for entry in publications[:16]] == list(range(1, 16)) + [0]
                    assert len(decodes) >= 16
                intervals = [b["field"] - a["field"] for a, b in zip(publications, publications[1:])]
                all_images[0].save(OUTPUT / "petscii-animation.gif", save_all=True, append_images=all_images[1:],
                                   duration=20, loop=0)
                result.update({"pass": True, "fields": len(records), "publications": publications, "decodes": decodes,
                               "presentation_interval_PAL_fields": sorted(set(intervals)),
                               "mean_presentation_interval_PAL_fields": sum(intervals) / len(intervals) if intervals else None,
                               "full_screenshot_pixels_checked_per_field": 104448,
                               "front_buffer_bytes_checked_per_boundary": 2048,
                               "native_decoded_bytes_checked_per_frame": 2048,
                               "ColorRAM_bytes_checked_per_field": 1024,
                               "ColorRAM_stores_checked": total_color_stores,
                               "field_interval_PAL_clocks": 19656, "records": records,
                               "scope": "Own16 prepared ROM PETSCII screen/color frames, overlapping LZ decode, full normal PAL scanout and beam-following ColorRAM updates before coherent screen publication; full wrap. No original500-frame artwork, original player/packing algorithm, all-border ending, analog blending or physical-hardware claim."})
                receipt.write_text(json.dumps(result, indent=2) + "\n")
                print(json.dumps({key: value for key, value in result.items()
                                  if key not in ("records", "publications", "decodes", "command")}, indent=2))
        finally:
            if monitor:
                (OUTPUT / "monitor.log").write_text("\n".join(monitor.transcript))
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            result["owned_process_closed"] = process.poll() is not None
            result["owned_process_returncode"] = process.returncode
            receipt.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
