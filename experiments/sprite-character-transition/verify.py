#!/usr/bin/env python3
"""Prove the 2D transition's live state, complete native pixels and wrap.

One primary boundary for paired trajectory sprites, opposite character/color
rotation, expanding raster borders, bounded quadrant wipe and both screen
buffers. Existing sprite/font proofs do not cover their sequence/publication.
Wrong in-place direction, unshifted colors, off-by-one wipes, X-MSB mistakes or
second-buffer operands fail here. No production test switches or PC writes.
"""
import argparse
from collections import Counter
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
TRACE = re.compile(r"#\d+ \(Trace store ([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\n"
                   r"\.C:([0-9a-f]{4})[^\n]* A:([0-9a-f]{2})[^\n]*\s+(\d+)\r?$", re.I | re.M)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def controls(position):
    if position < 48:
        return 0, position, 146, 162, 0
    if position < 96:
        return 1, position - 48, 146, 162, 6
    phase = position - 96
    extent = min(48, phase + 1)
    return 2, phase, 146 - 2 * extent, 162 + min(88, 2 * extent), 14


def advance(position, front, screens, colors, seed, seed_colors):
    """Independent list rotations and rectangular regions, no command tables."""
    position = (position + 1) % 192
    if position == 0:
        front ^= 1
    if 48 < position < 96:
        for row, left in ((10, True), (14, False)):
            first = row * 40
            for data in (screens[front], colors):
                line = data[first:first + 40]
                data[first:first + 40] = line[1:] + line[:1] if left else line[-1:] + line[:-1]
    if position >= 144:
        quadrant, step = divmod(position - 144, 12)
        if step < 10:
            rows = range(12) if quadrant in (0, 2) else range(12, 25)
            columns = (20 + 2 * step, 21 + 2 * step) if quadrant in (0, 3) else (19 - 2 * step, 18 - 2 * step)
            for row in rows:
                for column in columns:
                    index = row * 40 + column
                    screens[front][index] = 32
                    colors[index] = seed_colors[index]
    if position < 64:
        first = position * 16
        screens[front ^ 1][first:first + 16] = seed[first:first + 16]
    return position, front


def parse_events(response):
    return [{"address": int(address, 16), "line": int(line), "cycle": int(cycle),
             "pc": int(pc, 16), "value": int(value, 16), "clock": int(clock)}
            for address, line, cycle, pc, value, clock in TRACE.findall(response)]


def pixels(position, screen, colors, font, borders, frame_clock):
    output = bytearray(384 * 272)
    edges = [((event["clock"] - frame_clock - 13) * 8 + 1, event["value"] & 15) for event in borders]
    cursor, border = 0, 0
    for raster in range(16, 288):
        for x in range(384):
            point = raster * 504 + x
            while cursor < len(edges) and edges[cursor][0] <= point:
                border = edges[cursor][1]
                cursor += 1
            output[(raster - 16) * 384 + x] = border
    for y in range(200):
        row, glyph_row = divmod(y, 8)
        for column in range(40):
            index = row * 40 + column
            bits = font[screen[index] * 8 + glyph_row]
            for bit in range(8):
                output[(35 + y) * 384 + 32 + column * 8 + bit] = colors[index] if bits & (128 >> bit) else 0
    owners = [-1] * len(output)
    if position < 48:
        pair_colors = (1, 15, 14, 6)
        for sprite in range(7, -1, -1):
            pair, half = divmod(sprite, 2)
            sample = position + pair
            x = 40 + 5 * sample + 16 * half + 8
            y = 132 + round(52 * math.sin(sample * math.tau / 48)) - 15
            for row in range(16):
                first = (y + row) * 384 + x
                output[first:first + 16] = bytes([pair_colors[pair]]) * 16
                owners[first:first + 16] = [sprite] * 16
    return bytes(output), dict(Counter(sprite for sprite in owners if sprite >= 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fields", type=int, default=385,
                        help="Default proves both full screen-buffer cycles and the next wrap.")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    receipt = OUTPUT / ("receipt.json" if args.fields >= 385 else "trial-receipt.json")
    # Invalidate current success before any fallible setup; retain historical
    # timestamped receipts even when a short trial or setup later fails.
    for destination in {OUTPUT / "receipt.json", receipt}:
        destination.unlink(missing_ok=True)
    shared = module("transition_native_monitor", ROOT / "verify.py")
    labels = shared.read_labels(HERE / "build/main.sym")
    program = (HERE / "build/example.prg").read_bytes()
    seed = (HERE / "build/screen.bin").read_bytes()
    seed_colors = (HERE / "build/colors.bin").read_bytes()
    font = (HERE / "build/font.bin").read_bytes()
    palette = [tuple(int(value, 16) for value in line.split())
               for line in (ROOT / "palettes/colodore.vpl").read_text().splitlines()
               if line and not line.startswith("#")]
    screens, colors = [bytearray(seed), bytearray(seed)], bytearray(seed_colors)
    position = front = 0
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
                ram = monitor.memory(OUTPUT / "loaded-ram.bin", 0, 0xFFFF)
                monitor.run("bank cpu")
                assert ram[0x0801:0x0801 + len(program) - 2] == program[2:]
                monitor.run(f"delete {start}")
                ready = checkpoint(f"break {labels['ready']:04x}")
                monitor.run("x")
                monitor.run(f"delete {ready}")
                checkpoint("trace store d000 d02e")
                checkpoint("trace store d800 dbff")
                checkpoint(f"break {labels['frameComplete']:04x}")
                records, images, frames = [], [], []
                sprite_contributions = Counter()
                color_stores = sprite_stores = 0
                for field in range(1, args.fields + 1):
                    response = monitor.run("x")
                    events = parse_events(response)
                    stage, phase, upper, lower, band_color = controls(position)
                    borders = [event for event in events if event["address"] == 0xD020]
                    assert [event["value"] for event in borders] == ([0] if stage == 0 else [0, band_color, 0])
                    assert borders[0]["line"] == 0
                    if stage:
                        assert [event["line"] for event in borders[1:]] == [upper, lower]
                    frame_clock = borders[0]["clock"] - borders[0]["cycle"]
                    frames.append(frame_clock)
                    color_events = [event for event in events if 0xD800 <= event["address"] < 0xDC00]
                    assert all(frame_clock - 52 * 63 <= event["clock"] < frame_clock for event in color_events), (field, "visible color writes escaped the blank interval")
                    xy_events = [event for event in events if event["address"] <= 0xD010]
                    assert all(event["clock"] < frame_clock for event in xy_events)
                    color_stores += len(color_events)
                    sprite_stores += len(xy_events)
                    monitor.run("bank ram")
                    ram = monitor.memory(OUTPUT / "latest-ram.bin", 0, 0xFFFF)
                    monitor.run("bank cpu")
                    assert ram[0x0400:0x0800] == screens[0], (field, position, front, "screenA")
                    assert ram[0x0C00:0x1000] == screens[1], (field, position, front, "screenB")
                    assert ram[0x2000:0x2800] == font
                    for name, value in (("position", position), ("frontBuffer", front), ("stage", stage),
                                        ("phase", phase), ("bandTop", upper), ("bandBottom", lower), ("bandColor", band_color)):
                        assert ram[labels[name]] == value, (field, name, value, ram[labels[name]])
                    assert int.from_bytes(ram[labels["fieldCounter"]:labels["fieldCounter"] + 2], "little") == field
                    color_ram = monitor.memory(OUTPUT / "color-ram.bin", 0xD800, 0xDBFF)
                    assert bytes(value & 15 for value in color_ram) == colors, (field, position, "ColorRAM")
                    vic = monitor.memory(OUTPUT / "vic.bin", 0xD000, 0xD03F)
                    assert vic[0x11] & 0x7F == 0x1B and vic[0x16] & 31 == 8
                    assert vic[0x18] & 0xFE == (0x18 if front == 0 else 0x38)
                    assert vic[0x15] == (255 if stage == 0 else 0)
                    assert vic[0x17] == vic[0x1B] == vic[0x1C] == vic[0x1D] == 0
                    if stage == 0:
                        for sprite in range(8):
                            pair, half = divmod(sprite, 2)
                            sample = phase + pair
                            x = vic[2 * sprite] + (256 if vic[0x10] & (1 << sprite) else 0)
                            assert x == 40 + 5 * sample + 16 * half
                            assert vic[2 * sprite + 1] == 132 + round(52 * math.sin(sample * math.tau / 48))
                            assert vic[0x27 + sprite] & 15 == (1, 15, 14, 6)[pair]
                    indices, owners = pixels(position, screens[front], colors, font, borders, frame_clock)
                    sprite_contributions.update(owners)
                    screenshot = OUTPUT / f"field-{field:03d}.png"
                    monitor.run(f'scrsh "{screenshot}" 2')
                    image = Image.open(screenshot).convert("RGB")
                    expected = Image.new("RGB", (384, 272))
                    expected.putdata([palette[color] for color in indices])
                    difference = ImageChops.difference(image, expected)
                    if difference.getbbox() is not None:
                        expected.save(OUTPUT / "expected-failed.png")
                        difference.save(OUTPUT / "difference-failed.png")
                        wrong = sum(a != b for a, b in zip(image.get_flattened_data(), expected.get_flattened_data()))
                        raise AssertionError((field, position, wrong, "full native pixels"))
                    _, raster, clock = monitor.registers()
                    records.append({"field": field, "position": position, "stage": stage, "phase": phase,
                                    "front_buffer": front, "clock": clock, "raster": raster,
                                    "frame_start_clock": frame_clock, "border_events": borders,
                                    "ColorRAM_stores": len(color_events), "sprite_XY_stores": len(xy_events),
                                    "screenshot": screenshot.name, "sprite_pixel_ownership": owners})
                    images.append(image)
                    if field % 24 == 0:
                        print(f"Checked {field}/{args.fields} fields; stage{stage} phase{phase} buffer{front}", flush=True)
                    position, front = advance(position, front, screens, colors, seed, seed_colors)
                intervals = [b - a for a, b in zip(frames, frames[1:])]
                assert not intervals or set(intervals) == {19656}
                if args.fields >= 48:
                    assert set(sprite_contributions) == set(range(8))
                images[0].save(OUTPUT / "sprite-character-transition.gif", save_all=True,
                               append_images=images[1:], duration=40, loop=0)
                result = {"pass": True, "fields": args.fields, "full_screenshot_pixels_checked_each_field": 104448,
                          "screen_bytes_checked_each_field": 2048, "ColorRAM_bytes_checked_each_field": 1024,
                          "font_bytes_checked_each_field": 2048, "ColorRAM_stores_checked": color_stores,
                          "sprite_XY_stores_checked": sprite_stores, "sprite_pixel_ownership": dict(sprite_contributions),
                          "field_interval_PAL_clocks": sorted(set(intervals)), "sequence_fields": 192,
                          "records": records, "command": command,
                          "program_sha256": hashlib.sha256(program).hexdigest(),
                          "scope": "Own2D transition: adjacent prepared trajectory samples for four real sprite pairs, live opposite char/ColorRAM rotations, timed expanding border band, bounded quadrant wipe and coherent two-screen wrap. No transparent3D or released-charset/pixel-match claim. PAL6569 digital proof; no analog/physical-hardware claim."}
                receipt.write_text(json.dumps(result, indent=2) + "\n")
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
            if "result" in locals():
                result["owned_process_closed"] = process.poll() is not None
                result["owned_process_returncode"] = process.returncode
                receipt.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
