#!/usr/bin/env python3
"""Check independent row ownership and actual interleaved sprite DMA output."""

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
COLORS = (2, 8, 7, 5, 3, 14, 4, 1)
TRACE = re.compile(r"#\d+ \(Trace store ([0-9a-f]{4})\)\s+(\d+)/[^\n]*\n"
                   r"\.C:([0-9a-f]{4})[^\n]*\b(STA|STX)\b[^\n]* A:([0-9a-f]{2}) X:([0-9a-f]{2})", re.I)


def image_byte(x_byte, y):
    if y >= 168:
        return 0
    if x_byte == 0:
        return y ^ 0xA5
    value = 0
    for bit in range(8):
        x = x_byte * 8 + bit
        vertical_thread = (x + ((y // 7) % 2) * 3) % 8 < 3
        horizontal_thread = (y + ((x // 12) % 2) * 2) % 9 < 3
        value = value * 2 + int(vertical_thread != horizontal_thread)
    return value


def packed_reference():
    """Place each image row into every owning interval; no reverse-roll code."""
    packed = bytearray(11 * 8 * 64)
    duplicate_destinations = 0
    for y in range(168):
        owners = [block for block in range(11) if 16 * block <= y <= 16 * block + 20]
        duplicate_destinations += max(0, len(owners) - 1) * 24
        for block in owners:
            for x_byte in range(24):
                offset = 64 * (8 * block + x_byte // 3) + 3 * (y % 21) + x_byte % 3
                packed[offset] = image_byte(x_byte, y)
    return packed, duplicate_destinations


def checkpoint(response):
    return int(re.search(r"(?:BREAK|TRACE):\s*(\d+)", response)[1])


def events(response):
    return [{"address": int(address, 16), "raster": int(raster), "pc": int(pc, 16),
             "value": int(a if opcode.upper() == "STA" else x, 16)}
            for address, raster, pc, opcode, a, x in TRACE.findall(response)]


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("shared_native_monitor", ROOT / "verify.py")
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    labels = shared.read_labels(HERE / "build/main.sym")
    palette = [tuple(int(part, 16) for part in line.split())
               for line in (ROOT / "palettes/colodore.vpl").read_text().splitlines()
               if line and not line.startswith("#")]
    patch = Image.new("RGB", (192, 168))
    patch.putdata([palette[COLORS[x // 24]] if image_byte(x // 8, y) & (0x80 >> (x % 8))
                   else palette[0] for y in range(168) for x in range(192)])
    patch.save(OUTPUT / "expected-carpet.png")
    packed, duplicate_destinations = packed_reference()
    (OUTPUT / "expected-sprite-data.bin").write_bytes(packed)
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
                monitor.run(f"break {labels['framePresented']:04x}")
                monitor.run("x")
                captures, samples, clocks = [], [], []
                pointer_count = y_count = 0
                pointer_offsets, y_lead_times = [], []
                for index in range(33):
                    response = monitor.run("x") if index else ""
                    pc, raster, clock = monitor.registers()
                    clocks.append(clock)
                    monitor.run("bank ram")
                    ram = monitor.memory(OUTPUT / f"ram-{index:02d}.bin", 0, 0xFFFF)
                    monitor.run("bank cpu")
                    phase = index % 32
                    assert int.from_bytes(ram[labels["frameCounter"]:labels["frameCounter"] + 2], "little") == index + 1
                    assert ram[labels["phaseUsed"]] == phase
                    assert ram[0x2000:0x3600] == packed
                    assert ram[0x0400:0x07E8] == bytes(1000)
                    assert ram[0x3800:0x3808] == bytes(8)
                    assert ram[0x07F8:0x0800] == bytes(range(0xD0, 0xD8))
                    vic = monitor.memory(OUTPUT / "vic.bin", 0xD000, 0xD03F)
                    assert vic[0x15] == 255 and vic[0x18] & 0xFE == 0x1E
                    assert vic[0x11] & 0x7F == 0x1B and vic[0x16] & 0x1F == 8
                    assert all(vic[address] == 0 for address in (0x17, 0x1B, 0x1C, 0x1D))
                    assert vic[0x10] == (0xC0 if phase >= 24 else 0x80)
                    for sprite in range(8):
                        assert vic[2 * sprite] == (88 + 24 * sprite + phase) % 256
                        assert vic[2 * sprite + 1] == 211
                    if index:
                        traced = events(response)
                        pointer_events = [event for event in traced if 0x07F8 <= event["address"] <= 0x07FF]
                        y_events = [event for event in traced if 0xD001 <= event["address"] <= 0xD00F
                                    and event["address"] % 2]
                        assert [(event["address"], event["value"]) for event in pointer_events] == [
                            (0x07F8 + sprite, 0x80 + 8 * block + sprite)
                            for block in range(11) for sprite in range(8)]
                        assert [(event["address"], event["value"]) for event in y_events] == [
                            (0xD001 + 2 * sprite, 64 + 21 * restart)
                            for restart in range(8) for sprite in range(8)]
                        for event in pointer_events[8:]:
                            block = (event["value"] - 0x80) // 8
                            boundary = 64 + 16 * block
                            offset = event["raster"] - boundary
                            assert 0 <= offset <= 4, (index, event, boundary)
                            pointer_offsets.append(offset)
                        for event in y_events:
                            lead = event["value"] - event["raster"]
                            assert lead > 0, (index, event)
                            if event["value"] != 64:
                                y_lead_times.append(lead)
                        pointer_count += len(pointer_events)
                        y_count += len(y_events)
                    screenshot = OUTPUT / f"field-{index:02d}.png"
                    monitor.run(f'scrsh "{screenshot}" 2')
                    image = Image.open(screenshot).convert("RGB")
                    expected = Image.new("RGB", image.size, palette[0])
                    expected.paste(patch, (96 + phase, 49))
                    difference = ImageChops.difference(image, expected)
                    if difference.getbbox() is not None:
                        expected.save(OUTPUT / f"expected-field-{index:02d}.png")
                        difference.save(OUTPUT / f"difference-field-{index:02d}.png")
                        raise AssertionError(f"Full sprite DMA image mismatch in field {index}")
                    captures.append(image)
                    samples.append({"field": index + 1, "phase": phase, "raster": raster,
                                    "clock": clock, "screenshot": screenshot.name,
                                    "sprite_image_origin": [96 + phase, 49]})
                    if index == 0:
                        monitor.run("trace store 07f8 07ff")
                        monitor.run("trace store d001 d00f")
                captures[0].save(OUTPUT / "sprite-interleave.gif", save_all=True,
                                 append_images=captures[1:], duration=20, loop=0)
                receipt = {"pass": True, "fields": 33, "distinct_motion_phases": 32,
                           "sprite_image_dimensions": [192, 168],
                           "image_pixels_checked_per_field": 192 * 168,
                           "full_screenshot_pixels_checked_per_field": captures[0].width * captures[0].height,
                           "sprite_bytes_compared_per_field": len(packed),
                           "duplicate_overlap_byte_destinations": duplicate_destinations,
                           "pointer_stores_checked": pointer_count, "Y_stores_checked": y_count,
                           "pointer_completion_row_offsets_from_overlap_start": sorted(set(pointer_offsets)),
                           "Y_store_lead_lines_before_restart": sorted(set(y_lead_times)),
                           "mean_field_interval_PAL_clocks": (clocks[-1] - clocks[0]) / (len(clocks) - 1),
                           "field_interval_PAL_clocks": [b - a for a, b in zip(clocks, clocks[1:])],
                           "samples": samples, "command": command,
                           "program_sha256": hashlib.sha256((HERE / "build/example.prg").read_bytes()).hexdigest(),
                           "scope": "Independent interval-based row ownership, all5632 packed bytes, full actual sprite-DMA screenshots over32 motion phases pluswrap, pointer/Y store values and bounded monitor-reported line windows. No20-line variant, universal cycle proof or physical-hardware validation."}
                (OUTPUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
                print(json.dumps({key: value for key, value in receipt.items()
                                  if key not in ("samples", "command")}, indent=2))
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
