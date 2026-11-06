#!/usr/bin/env python3
"""Verify the assembled cube on a PAL C64 in VICE, then save emulator captures."""

import argparse
import hashlib
from itertools import chain
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time

from PIL import GifImagePlugin, Image


PROMPT = re.compile(rb"\(C:\$[0-9a-fA-F]{4}\) $")
EDGES = [(i, i ^ bit) for i in range(8) for bit in (1, 2, 4) if not i & bit]


def read_labels(path):
    """Read the assembler's normal debug symbols; no special test build is needed."""
    return {name: int(address, 16) for name, address in
            re.findall(r"\.label\s+(\w+)\s*=\s*\$([0-9a-fA-F]+)", path.read_text())}


class Monitor:
    def __init__(self, connection):
        self.connection = connection
        self.transcript = []
        # VICE may greet a new client before its first command. Consume that
        # unsolicited prompt so it cannot be mistaken for a command response.
        connection.settimeout(0.1)
        try:
            while connection.recv(65536):
                pass
        except socket.timeout:
            pass
        connection.settimeout(15)

    def run(self, command):
        self.connection.sendall((command + "\n").encode())
        response = b""
        while not PROMPT.search(response) or (command == "r" and not re.search(rb"^\.;", response, re.M)):
            part = self.connection.recv(65536)
            if not part:
                raise RuntimeError("VICE closed its monitor connection.")
            response += part
        text = response.decode(errors="replace")
        self.transcript.append(command + "\n" + text)
        if re.search(r"ERROR|Unknown command|Unknown resource|Syntax error", text):
            raise RuntimeError(f"VICE rejected {command!r}:\n{text}")
        return text

    def memory(self, path, first, last):
        self.run(f'bsave "{path.resolve()}" 0 {first:04x} {last:04x}')
        data = path.read_bytes()
        if len(data) != last - first + 1:
            raise RuntimeError("VICE wrote an incomplete memory dump.")
        return data

    def registers(self):
        response = self.run("r")
        match = re.search(r"^\.;([0-9a-fA-F]{4})\s+(.*)$", response, re.M)
        if not match:
            raise RuntimeError(f"Could not read VICE registers:\n{response}")
        fields = match[2].split()
        return int(match[1], 16), int(fields[-3]), int(fields[-1])


def line_pixels(x0, y0, x1, y1):
    """Rasterize with rational interpolation, rounding exact ties toward the start."""
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx, sy = 1 if x0 < x1 else -1, 1 if y0 < y1 else -1
    major, minor = max(dx, dy), min(dx, dy)
    if major == 0:
        yield x0, y0
        return
    for step in range(major + 1):
        offset = (step * minor + (major - 1) // 2) // major
        yield ((x0 + step * sx, y0 + offset * sy) if dx >= dy else
               (x0 + offset * sx, y0 + step * sy))


def visible_faces_reference(vertices):
    """Derive outward triangles from cube axes, then test their signed screen areas."""
    mask = 0
    for axis in range(3):
        u, v = 1 << ((axis + 1) % 3), 1 << ((axis + 2) % 3)
        for side in range(2):
            origin = side << axis
            first, second = (u, v) if side else (v, u)
            p, q, r = vertices[origin], vertices[origin | first], vertices[origin | second]
            area = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
            if area >= 0:
                mask |= 1 << (2 * axis + side)
    return mask


def reference_edges(visible_faces=None):
    for first, last in EDGES:
        # A cube edge belongs to the two planes whose coordinate is unchanged.
        adjacent_faces = [2 * axis + bool(first & (1 << axis)) for axis in range(3)
                          if not (first ^ last) & (1 << axis)]
        if visible_faces is None or any(visible_faces & (1 << face) for face in adjacent_faces):
            yield first, last


def raster_reference(vertices, visible_faces=None):
    pixels = set()
    for first, last in reference_edges(visible_faces):
        start, end = vertices[first], vertices[last]
        if start[1] > end[1]:
            start, end = end, start
        pixels.update(line_pixels(*start, *end))
    return pixels


def charset_pixels(charset):
    return {(column * 8 + bit, y)
            for column in range(16) for y in range(128) for bit in range(8)
            if charset[column * 128 + y] & (0x80 >> bit)}


def geometry_reference(yaw, pitch):
    """Project the mathematical cube using float math, independently of its tables."""
    yaw, pitch = yaw * math.tau / 256, pitch * math.tau / 256
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    vertices = []
    for vertex in range(8):
        x, y, z = (24 if vertex & bit else -24 for bit in (1, 2, 4))
        x, z = cy * x + sy * z, -sy * x + cy * z
        y, z = cp * y - sp * z, sp * y + cp * z
        vertices.append((64 + 128 * x / (144 + z), 64 - 128 * y / (144 + z)))
    return vertices


def screenshot_difference(image, pixels, color):
    """Find the native VIC screen origin, then compare every matrix pixel."""
    expected = [color if (x, y) in pixels else (0, 0, 0)
                for y in range(128) for x in range(128)]
    image = image.convert("RGB")
    candidates = []
    for top in range(28, 42):
        for left in range(28, 38):
            actual = list(image.crop((left + 96, top + 32, left + 224, top + 160)).get_flattened_data())
            candidates.append((sum(a != b for a, b in zip(actual, expected)), left, top))
    return min(candidates)


def save_animation(frames, path, duration):
    """Encode each presentation, including identical adjacent quantized images."""
    frames = iter(frames)
    first = next(frames)
    palette = first.convert("P", palette=Image.Palette.ADAPTIVE, colors=2)
    header, _ = GifImagePlugin.getheader(palette, info={"loop": 0, "optimize": False})
    with path.open("wb") as stream:
        for block in header:
            stream.write(block)
        for frame in chain([first], frames):
            indexed = frame.quantize(palette=palette, dither=Image.Dither.NONE)
            for block in GifImagePlugin.getdata(indexed, duration=duration, disposal=1):
                stream.write(block)
        stream.write(b";")


def vice_command(executable, program, port, palette):
    return [executable, "-default", "+saveres", "-minimized", "-pal",
            "-speed", "100", "+warp", "+autostart-warp", "+confirmonexit",
            "-sounddev", "dummy", "+refreshonbreak", "+binarymonitor",
            "-autostartprgmode", "1", "-autostart", str(program.resolve()),
            "-VICIIfilter", "0", "-VICIIextpal", "-VICIIpalette", str(palette),
            "-VICIIsaturation", "1000", "-VICIIcontrast", "1000",
            "-VICIIbrightness", "1000", "-VICIIgamma", "1000",
            "-remotemonitor", "-remotemonitoraddress", f"ip4://127.0.0.1:{port}"]


def connect_monitor(process, port):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("VICE exited during startup; inspect vice.log.")
        try:
            return socket.create_connection(("127.0.0.1", port), timeout=1)
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("VICE did not open its remote monitor within 15 seconds.")


def verify(program, labels_file, output, executable, frames, ticks=1, raster_irq_line=0):
    labels = read_labels(labels_file)
    required = {"framePresented", "projectedX", "projectedY", "angleYaw", "anglePitch",
                "drawBufferHi", "rasterTick", "bitMasks", "linePointer", "squareSum"}
    if required - labels.keys():
        raise ValueError(f"Missing debug symbols: {sorted(required - labels.keys())}")
    mutable_ranges = [(labels["linePointer"], labels["squareSum"] + 1),
                      (0x0100, 0x0200), (labels["angleYaw"], labels["bitMasks"]),
                      (0x2000, 0x3000)]
    if "clearEntry" in labels:
        # The fast clear temporarily modifies its store chain, then restores
        # it before returning. Only these four operand bytes remain dynamic
        # at the presentation boundary where this verifier samples RAM.
        mutable_ranges.extend([(labels["clearPatchPointer"], labels["clearPatchPointer"] + 2),
                               (labels["clearStateStart"], labels["clearStateEnd"]),
                               (labels["clearEntry"] + 1, labels["clearEntry"] + 3),
                               (labels["clearFirstRow"] + 1, labels["clearFirstRow"] + 2),
                               (labels["clearLastRow"] + 1, labels["clearLastRow"] + 2)])
    if "fastLineDispatch" in labels:
        # Generated pixel kernels restore their temporary endpoint patch before
        # returning. Only the dispatch and common tail operands stay dynamic.
        mutable_ranges.append((labels["fastLineTable"], labels["fastLineError"] + 1))
        for name, size in [("fastLineDispatch", 2), ("fastLineTailMask", 1),
                           ("fastLineTailRead", 2), ("fastLineTailWrite", 2),
                           ("fastLineTailEnd", 1)]:
            mutable_ranges.append((labels[name] + 1, labels[name] + 1 + size))
    culling = "visibleFaces" in labels
    if culling:
        mutable_ranges.extend([(labels["cullDX1"], labels["cullSumHi"] + 1),
                               (labels["visibleFaces"], labels["visibleFaces"] + 1)])
    original = program.read_bytes()
    if original[:2] != b"\x01\x08":
        raise ValueError("Expected a runnable C64 PRG loaded at $0801.")
    output.mkdir(parents=True, exist_ok=True)
    (output / "verification.json").unlink(missing_ok=True)
    palette_file = Path(__file__).resolve().parent / "palettes/colodore.vpl"
    palette = [tuple(int(value, 16) for value in line.split()[:3])
               for line in palette_file.read_text().splitlines()
               if line.strip() and not line.lstrip().startswith("#")]
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    monitor, samples, captures, animation = None, [], [], []
    previous_pixels, previous_angles = None, None
    shown_charsets, hashes, elapsed = set(), set(), []
    stable_ram = None
    with (output / "vice.log").open("w") as log:
        process = subprocess.Popen(vice_command(executable, program, port, palette_file),
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            with connect_monitor(process, port) as connection:
                monitor = Monitor(connection)
                monitor.run("r")
                monitor.run(f"break {labels['framePresented']:04x}")
                monitor.run("x")
                # The initial autostart is also covered: its first presentation
                # must reach the same normal rendering boundary as later frames.
                colors = monitor.memory(output / "colors.bin", 0xd800, 0xdbe7)
                matrix_colors = {colors[(4 + row) * 40 + 12 + column] & 15
                                 for row in range(16) for column in range(16)}
                if len(matrix_colors) != 1 or 0 in matrix_colors:
                    raise AssertionError("The cube's character matrix has inconsistent or invisible colors.")
                color = palette[next(iter(matrix_colors))]
                previous_cycles, previous_tick = None, None
                for index in range(frames):
                    if index:
                        monitor.run("x")
                    pc, raster_line, cycles = monitor.registers()
                    if pc != labels["framePresented"]:
                        raise AssertionError(f"Execution stopped outside the frame boundary: ${pc:04x}.")
                    if (raster_line - raster_irq_line) % 312 > 3:
                        raise AssertionError(f"Charset swapped outside the scheduled raster window at line {raster_line}.")
                    if previous_cycles is not None:
                        elapsed.append(cycles - previous_cycles)
                        if abs(elapsed[-1] - ticks * 63 * 312) > 63:
                            raise AssertionError(f"Presentation interval was {elapsed[-1]} cycles, not {ticks} PAL frames.")
                    previous_cycles = cycles
                    io = monitor.memory(output / "vic.bin", 0xd000, 0xd03f)
                    if io[0x11] & 0x60 or io[0x16] & 0x10:
                        raise AssertionError("VIC-II left standard hires character mode.")
                    if io[0x18] >> 4 != 1:
                        raise AssertionError("VIC-II screen RAM moved away from $0400.")
                    visible = (io[0x18] & 0x0e) * 1024
                    if visible not in (0x2000, 0x2800):
                        raise AssertionError(f"Unexpected displayed charset: ${visible:04x}.")
                    shown_charsets.add(visible)
                    monitor.run("bank ram")
                    ram = monitor.memory(output / "ram.bin", 0, 0xffff)
                    monitor.run("bank cpu")
                    stable = bytearray(ram)
                    for first, last in mutable_ranges:
                        stable[first:last] = bytes(last - first)
                    if stable_ram is not None and stable != stable_ram:
                        address = next(i for i, (a, b) in enumerate(zip(stable, stable_ram)) if a != b)
                        raise AssertionError(f"Renderer wrote outside its buffers, variables, stack, or workspace at ${address:04x}.")
                    stable_ram = stable
                    tick = ram[labels["rasterTick"]]
                    if previous_tick is not None and (tick - previous_tick) % 256 != ticks:
                        raise AssertionError(f"Presentation did not occur every {ticks} PAL raster interrupts.")
                    previous_tick = tick
                    if ram[labels["drawBufferHi"]] << 8 != visible ^ 0x0800:
                        raise AssertionError("Drawing and displayed charsets are not separate buffers.")
                    yaw, pitch = ram[labels["angleYaw"]], ram[labels["anglePitch"]]
                    if previous_angles is not None:
                        expected_yaw = (previous_angles[0] + ticks) & 255
                        pitch_step = int(ticks == 2 or expected_yaw % 2 == 0)
                        expected_pitch = (previous_angles[1] + pitch_step) & 255
                        if (yaw, pitch) != (expected_yaw, expected_pitch):
                            raise AssertionError("Rotation angles did not preserve their PAL-frame angular speed.")
                    previous_angles = yaw, pitch
                    vertices = list(zip(ram[labels["projectedX"]:labels["projectedX"] + 8],
                                        ram[labels["projectedY"]:labels["projectedY"] + 8]))
                    if any(not (0 <= x < 128 and 0 <= y < 128) for x, y in vertices):
                        raise AssertionError("A projected vertex escaped the character canvas.")
                    ideal = geometry_reference(yaw, pitch)
                    error = max(abs(actual - expected) for vertex, reference in zip(vertices, ideal)
                                for actual, expected in zip(vertex, reference))
                    if error > 3:
                        raise AssertionError(f"Projection differs from true 3D geometry by {error:.3f} pixels.")
                    visible_faces = visible_faces_reference(vertices) if culling else None
                    if culling and ram[labels["visibleFaces"]] != visible_faces:
                        raise AssertionError("Face visibility differs from independent projected signed areas.")
                    expected_pixels = raster_reference(vertices, visible_faces)
                    charset = ram[visible:visible + 2048]
                    actual_pixels = charset_pixels(charset)
                    if actual_pixels != expected_pixels:
                        raise AssertionError(f"Canvas differs from independently rasterized cube: "
                                             f"{len(actual_pixels ^ expected_pixels)} wrong pixels.")
                    if any(ram[0x0400 + (row + 4) * 40 + column + 12] != column * 16 + row
                           for row in range(16) for column in range(16)):
                        raise AssertionError("The column-major character matrix was corrupted.")
                    hashes.add(hashlib.sha256(charset).hexdigest())
                    sample = {"yaw": yaw, "pitch": pitch, "charset": f"${visible:04x}",
                              "lit_pixels": len(actual_pixels), "geometry_error_pixels": round(error, 4),
                              "vertices": vertices, "cycles": cycles, "presentation_raster_line": raster_line}
                    if culling:
                        sample.update({"visible_faces": visible_faces,
                                       "drawn_edges": len(list(reference_edges(visible_faces)))})
                    # Keep every verified canvas at the actual presentation cadence.
                    # VICE PNG captures below independently prove its display.
                    preview = Image.new("RGB", (320, 200))
                    for x, y in actual_pixels:
                        preview.putpixel((x + 96, y + 32), color)
                    animation.append(preview.resize((640, 400), Image.Resampling.NEAREST))
                    # At the lower-border presentation breakpoint, the VIC has
                    # completed scanning the previously presented charset.
                    if previous_pixels is not None and index % max(1, frames // 32) == 0:
                        screenshot = output / f"vice-{index:03d}.png"
                        monitor.run(f'scrsh "{screenshot}" 2')
                        image = Image.open(screenshot).convert("RGB")
                        mismatch, left, top = screenshot_difference(image, previous_pixels, color)
                        sample.update({"screenshot": screenshot.name, "screenshot_mismatches": mismatch,
                                       "screen_origin": [left, top]})
                        if mismatch:
                            raise AssertionError(f"VIC-II capture has {mismatch} incorrect canvas pixels.")
                        captures.append(image)
                    samples.append(sample)
                    previous_pixels = actual_pixels
            if shown_charsets != {0x2000, 0x2800} or len(hashes) < 2:
                raise AssertionError("Both buffers must show changing cube images.")
            save_animation(animation, output / "cube.gif", ticks * 20)
            report = {"pass": True, "pal": True, "frames_verified": frames,
                      "pal_frames_per_presentation": ticks, "raster_irq_line": raster_irq_line,
                      "program_sha256": hashlib.sha256(original).hexdigest(),
                      "independent_checks": ["floating-point 3D geometry within 3 pixels",
                                             "exact rational raster of independently visible cube edges" if culling
                                             else "exact rational raster of all twelve edges",
                                             "both 2 KB charset buffers", "VIC-II screenshot pixels",
                                             "column-major screen mapping", "rotation progression",
                                             f"presentation every {ticks} PAL raster interrupts",
                                             "buffer swap at the scheduled raster boundary",
                                             "unchanged RAM outside renderer-owned workspaces"],
                      "max_geometry_error_pixels": max(s["geometry_error_pixels"] for s in samples),
                      "cycles_per_presentation": {"min": min(elapsed), "max": max(elapsed)},
                      "max_pal_frames_per_presentation": max(elapsed) / (63 * 312),
                      "distinct_canvases": len(hashes), "screenshots": len(captures),
                      "gif": {"source": "verified C64 charset RAM", "frames": len(animation),
                              "frame_duration_ms": ticks * 20, "file": "cube.gif"}, "samples": samples}
            (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps({key: value for key, value in report.items() if key != "samples"}, indent=2))
        finally:
            if monitor:
                (output / "monitor.log").write_text("\n".join(monitor.transcript))
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", type=Path, nargs="?", default=here / "build/vector-cube.prg")
    parser.add_argument("--labels", type=Path, default=here / "build/cube.sym")
    parser.add_argument("--output", type=Path, default=here / "build/verification")
    parser.add_argument("--vice", default=os.environ.get("VICE") or shutil.which("x64sc"))
    parser.add_argument("--frames", type=int,
                        help="Presentations to verify (default: one full 10.24-second rotation period).")
    parser.add_argument("--ticks", type=int, choices=(1, 2), default=1,
                        help="Expected PAL frames per presentation (default: 1).")
    parser.add_argument("--raster-line", type=int, default=0,
                        help="Expected raster IRQ line for buffer presentation (default: 0).")
    args = parser.parse_args()
    if not args.vice:
        parser.error("x64sc is missing; install VICE or pass --vice /path/to/x64sc.")
    if args.frames is None:
        args.frames = 512 // args.ticks
    if args.frames < 2:
        parser.error("--frames must be at least 2.")
    if not 0 <= args.raster_line < 312:
        parser.error("--raster-line must be in the PAL range 0..311.")
    verify(args.program.resolve(), args.labels.resolve(), args.output.resolve(), args.vice, args.frames,
           args.ticks, args.raster_line)
