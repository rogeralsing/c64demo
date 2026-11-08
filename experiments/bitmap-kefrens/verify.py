#!/usr/bin/env python3
"""Verify native bitmap ribbons and joystick-driven movement/orientation changes."""

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import socket
import struct
import subprocess

from PIL import Image, ImageChops


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("cube_verification", ROOT / "verify.py")
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
INPUTS = ([0] * 4 + [1] * 4 + [0] * 2 + [8] * 3 + [4] * 3 + [2] * 4
          + [16] * 2 + [0] * 2 + [16] + [0] * 2 + [9] * 2 + [16]
          + [0] * 3 + [6] * 3 + [0] * 2 + [16] + [0] * 2)


class Joyport:
    """VICE's official binary monitor API drives real emulated port input lines."""

    def __init__(self, connection):
        self.connection = connection
        connection.settimeout(15)
        self.request = 0
        self.transcript = []

    def receive(self, size):
        value = b""
        while len(value) < size:
            chunk = self.connection.recv(size - len(value))
            if not chunk:
                raise RuntimeError("VICE binary monitor closed.")
            value += chunk
        return value

    def set(self, pressed):
        self.request += 1
        raw = 31 ^ pressed
        # JOYPORT_2 is zero-based port index 1 in VICE's monitor API.
        body = struct.pack("<HH", 1, raw)
        packet = struct.pack("<BBIIB", 2, 2, len(body), self.request, 0xa2) + body
        self.connection.sendall(packet)
        while True:
            header = self.receive(12)
            start, version, size, response, error, request = struct.unpack("<BBIBBI", header)
            response_body = self.receive(size)
            if start != 2 or version != 2:
                raise RuntimeError("Invalid binary monitor response header.")
            if request != self.request:
                continue
            if response != 0xa2 or error or response_body:
                raise RuntimeError(f"Joyport command failed: type={response:#x}, error={error:#x}.")
            self.transcript.append({"physical_port": 2, "api_port": 1, "pressed_bits": pressed,
                                    "active_low_lines": raw, "request_hex": packet.hex(),
                                    "response_header_hex": header.hex()})
            return raw


def sine_values(center, amplitude):
    return bytes(math.floor(center + amplitude * math.sin(index * math.tau / 256) + 0.5)
                 for index in range(256))


def apply_controls(state, pressed):
    state = dict(state)
    if pressed & 1:
        state["speed"] = min(4, state["speed"] + 1)
    if pressed & 2:
        state["speed"] = max(1, state["speed"] - 1)
    if pressed & 4:
        state["bend"] = max(1, state["bend"] - 1)
    if pressed & 8:
        state["bend"] = min(4, state["bend"] + 1)
    if pressed & 16 and not state["fireHeld"]:
        state["orientation"] ^= 1
    state["fireHeld"] = int(bool(pressed & 16))
    return state


def reference(state, palette):
    grid = [bytearray(128) for _ in range(64)]
    coverage = [bytearray(128) for _ in range(64)]
    if state["orientation"] == 0:
        profile = (1, 1, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 2, 2, 1, 1)
        for y in range(64):
            for bar in range(6):
                angle = (state["phase"] + y * state["bend"] + bar * 37) % 256
                x0 = math.floor(56 + 48 * math.sin(angle * math.tau / 256) + 0.5)
                for offset, color in enumerate(profile):
                    grid[y][x0 + offset] = color
                    coverage[y][x0 + offset] += 1
    else:
        profile = (1, 2, 3, 3, 3, 3, 2, 1)
        for column in range(32):
            for bar in range(6):
                angle = (state["phase"] + column * 4 * state["bend"] + bar * 37) % 256
                y0 = math.floor(28 + 24 * math.sin(angle * math.tau / 256) + 0.5)
                for offset, color in enumerate(profile):
                    for pixel in range(4):
                        grid[y0 + offset][column * 4 + pixel] = color
                        coverage[y0 + offset][column * 4 + pixel] += 1
    bitmap = bytearray(8000)
    image = Image.new("RGB", (320, 200), palette[0])
    pixels = image.load()
    counts = [0, 0, 0, 0]
    for row in range(64):
        y = 36 + 2 * row
        for column in range(32):
            value = 0
            for pixel in range(4):
                color = grid[row][column * 4 + pixel]
                counts[color] += 1
                value |= color << (6 - 2 * pixel)
                for py in (y, y + 1):
                    for px in (32 + column * 8 + pixel * 2, 33 + column * 8 + pixel * 2):
                        pixels[px, py] = palette[(0, 3, 4, 1)[color]]
            address = (y // 8) * 320 + (column + 4) * 8 + y % 8
            bitmap[address] = bitmap[address + 1] = value
    overlap = sum(value > 1 for row in coverage for value in row)
    return bytes(bitmap), image, counts, overlap


def crop_native(image, expected):
    origins = [(32, 35)] + [(x, y) for y in range(30, 41) for x in range(28, 37)
                           if (x, y) != (32, 35)]
    for x, y in origins:
        crop = image.crop((x, y, x + 320, y + 200))
        if ImageChops.difference(crop, expected).getbbox() is None:
            return crop, [x, y]
    raise AssertionError("Native VIC screenshot differs from independent ribbon composition.")


def main():
    labels = common.read_labels(HERE / "build/main.sym")
    program = HERE / "build/example.prg"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output = HERE / "build/verification" / stamp
    output.mkdir(parents=True)
    palette_path = ROOT / "palettes/colodore.vpl"
    palette = [tuple(int(value, 16) for value in line.split()[:3])
               for line in palette_path.read_text().splitlines()
               if line.strip() and not line.lstrip().startswith("#")]
    with socket.socket() as reserve_text, socket.socket() as reserve_binary:
        reserve_text.bind(("127.0.0.1", 0))
        reserve_binary.bind(("127.0.0.1", 0))
        text_port = reserve_text.getsockname()[1]
        binary_port = reserve_binary.getsockname()[1]
    command = common.vice_command(shutil.which("x64sc"), program, text_port, palette_path)
    command.extend(["-binarymonitor", "-binarymonitoraddress", f"ip4://127.0.0.1:{binary_port}",
                    "-controlport2device", "37"])
    report = {"pass": False, "program_sha256": hashlib.sha256(program.read_bytes()).hexdigest(),
              "input_method": "explicit synthetic port-2 input lines via VICE Joyport I/O simulation",
              "memory_or_pc_writes": False, "samples": []}
    state = {"phase": 0, "speed": 1, "bend": 2, "orientation": 0, "fireHeld": 0}
    process = monitor = joy = binary_connection = None
    clocks, captures, durations = [], [], []
    expected_wide, expected_narrow = sine_values(56, 48), sine_values(28, 24)
    try:
        with (output / "vice.log").open("w") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            with common.connect_monitor(process, text_port) as connection:
                monitor = common.Monitor(connection)
                monitor.run("r")
                monitor.run("sidefx off")
                monitor.run(f"break {labels['inputSample']:04x}")
                monitor.run(f"break {labels['displayComplete']:04x}")
                monitor.run("disable 2")
                monitor.run("x")
                if monitor.registers()[0] != labels["inputSample"]:
                    raise AssertionError("Normal startup did not reach its first hardware-input read.")
                binary_connection = socket.create_connection(("127.0.0.1", binary_port), timeout=15)
                joy = Joyport(binary_connection)
                monitor.run("disable 1")
                monitor.run("enable 2")
                for index, pressed in enumerate(INPUTS):
                    raw_input = joy.set(pressed)
                    if index:
                        state["phase"] = (state["phase"] + state["speed"]) % 256
                    state = apply_controls(state, pressed)
                    monitor.run("x")
                    pc, raster, clock = monitor.registers()
                    if pc != labels["displayComplete"] or not 256 <= raster <= 260:
                        raise AssertionError(f"Unexpected completed-image stop: ${pc:04x}, raster {raster}.")
                    monitor.run("bank ram")
                    ram = monitor.memory(output / f"ram-{index:03d}.bin", 0, 0xffff)
                    actual_state = {name: ram[labels[name]] for name in state}
                    if actual_state != state:
                        raise AssertionError(f"Input-driven state differs: {actual_state} != {state}.")
                    if ram[labels["lastJoystick"]] != raw_input or ram[labels["iteration"]] != index % 256:
                        raise AssertionError("Native code did not consume the injected hardware lines in order.")
                    for name, expected in (("widePositions", expected_wide), ("narrowPositions", expected_narrow)):
                        address = labels[name]
                        if ram[address:address + 256] != expected:
                            raise AssertionError("Reusable sine positions differ from the independent formula.")
                    bitmap_address = 0xa000 if index % 2 == 0 else 0x2000
                    if ram[labels["drawBitmapHi"]] << 8 != bitmap_address:
                        raise AssertionError("Completed bitmap buffers did not alternate.")
                    expected_bitmap, expected_image, counts, overlap = reference(state, palette)
                    actual = ram[bitmap_address:bitmap_address + 8000]
                    if actual != expected_bitmap:
                        differing = sum(a != b for a, b in zip(actual, expected_bitmap))
                        raise AssertionError(f"Full bitmap differs in {differing} of 8,000 bytes.")
                    if not all(counts) or overlap == 0:
                        raise AssertionError("Image must exercise colored shading, background and overlapping bars.")
                    for screen in (0x0400, 0x8400):
                        if ram[screen:screen + 1000] != bytes([0x34]) * 1000:
                            raise AssertionError("A bitmap screen color plane changed.")
                    monitor.run("bank io")
                    vic = monitor.memory(output / f"vic-{index:03d}.bin", 0xd000, 0xd03f)
                    cia1 = monitor.memory(output / f"cia1-{index:03d}.bin", 0xdc00, 0xdc03)
                    cia2 = monitor.memory(output / f"cia2-{index:03d}.bin", 0xdd00, 0xdd03)
                    colors = monitor.memory(output / f"colors-{index:03d}.bin", 0xd800, 0xdbe7)
                    if cia1[0] & 31 != raw_input or cia1[2] & 31:
                        raise AssertionError("Joystick input did not reach actual CIA1 port-A input pins.")
                    if cia2[0] & 3 != (1 if index % 2 == 0 else 3) or cia2[2] & 3 != 3:
                        raise AssertionError("CIA2 did not select the completed bitmap bank.")
                    if vic[0x11] & 0x7f != 0x3b or vic[0x16] & 0x3f != 0x18 or vic[0x18] & 0xfe != 0x18:
                        raise AssertionError("VIC multicolor bitmap configuration changed.")
                    if bytes(value & 15 for value in colors) != bytes([1]) * 1000:
                        raise AssertionError("Bitmap white shade changed in Color RAM.")
                    if vic[0x15] or vic[0x20] & 15 or vic[0x21] & 15:
                        raise AssertionError("Sprites or a nonblack backdrop alter the output.")
                    monitor.run("bank cpu")
                    screenshot = output / f"native-{index:03d}.png"
                    monitor.run(f'screenshot "{screenshot}" 2')
                    crop, origin = crop_native(Image.open(screenshot).convert("RGB"), expected_image)
                    crop.save(output / f"native-crop-{index:03d}.png")
                    expected_image.save(output / f"expected-{index:03d}.png")
                    captures.append(crop.resize((640, 400), Image.Resampling.NEAREST))
                    durations.append(160 if not clocks else round((clock - clocks[-1]) / 19656 * 20))
                    clocks.append(clock)
                    report["samples"].append({"update": index, "pressed_bits": pressed,
                                              "active_low_lines": raw_input, "state": dict(state),
                                              "bitmap": f"${bitmap_address:04x}",
                                              "bitmap_sha256": hashlib.sha256(actual).hexdigest(),
                                              "selector_counts": counts, "overlapping_logical_samples": overlap,
                                              "native_screenshot": screenshot.name, "screen_origin": origin,
                                              "clock": clock, "raster": raster})
                    print(f"Verified native Kefrens update {index + 1}/{len(INPUTS)}, orientation {state['orientation']}", flush=True)
                joy.set(0)
        intervals = [second - first for first, second in zip(clocks, clocks[1:])]
        cadence = {}
        for mode in (0, 1):
            selected = [interval for interval, sample in zip(intervals, report["samples"][1:])
                        if sample["state"]["orientation"] == mode]
            fields = [round(interval / 19656) for interval in selected]
            if not selected or any(abs(interval - count * 19656) > 63 for interval, count in zip(selected, fields)):
                raise AssertionError("Both orientations must publish at complete PAL-field intervals.")
            cadence[str(mode)] = {"interval_clocks": [min(selected), max(selected)],
                                  "pal_fields_per_update": sorted(set(fields))}
        captures[0].save(output / "animation.gif", save_all=True, append_images=captures[1:],
                         duration=durations, loop=0, optimize=False, disposal=2)
        report.update({"pass": True, "native_images": len(captures),
                       "full_bitmap_bytes_checked": 8000 * len(captures),
                       "native_pixels_checked": 64000 * len(captures),
                       "prepared_sine_bytes_checked": 512,
                       "cadence_by_orientation": cadence, "animation": "animation.gif",
                       "limits": ["original educational bitmap implementation; Aloft algorithm remains unknown",
                                  "bounded PAL VICE and synthetic input validation; no physical joystick claim"]})
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        if joy is not None:
            report["synthetic_inputs"] = joy.transcript
        if binary_connection is not None:
            binary_connection.close()
        if monitor is not None:
            (output / "monitor.log").write_text("\n".join(monitor.transcript))
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"Verification: {output / 'verification.json'}", flush=True)


if __name__ == "__main__":
    main()
