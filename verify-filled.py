#!/usr/bin/env python3
"""Verify multicolor polygon boundaries and XOR filling on the emulated C64."""

import argparse
from contextlib import contextmanager
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import socket
import subprocess

from PIL import GifImagePlugin, Image

from verify import Monitor, connect_monitor, geometry_reference, read_labels, vice_command
from verify import visible_faces_reference


WIDTH, HEIGHT = 64, 128
HERE = Path(__file__).resolve().parent


def face_quads():
    """Generate the six outward face windings from binary cube coordinates."""
    for axis in range(3):
        u, v = 1 << ((axis + 1) % 3), 1 << ((axis + 2) % 3)
        for side in range(2):
            origin = side << axis
            first, second = (u, v) if side else (v, u)
            yield (origin, origin | first, origin | first | second, origin | second), axis + 1


def polygon_reference(polygons):
    """Direct odd-even polygon coverage at integer samples, using exact intersections.

    The X sample owns edges whose left endpoint is inclusive and right endpoint
    is exclusive. Integer Y samples own the lower intersection, not the upper.
    This computes face interiors directly; it never performs a prefix fill.
    """
    canvas = bytearray(WIDTH * HEIGHT)
    for polygon, color in polygons:
        for x in range(WIDTH):
            intersections = []
            for p, q in zip(polygon, polygon[1:] + polygon[:1]):
                if min(p[0], q[0]) <= x < max(p[0], q[0]):
                    intersections.append(Fraction(p[1]) + Fraction((q[1] - p[1]) * (x - p[0]),
                                                                   q[0] - p[0]))
            intersections.sort()
            if len(intersections) % 2:
                raise AssertionError("A closed polygon produced an odd number of intersections.")
            for lower, upper in zip(intersections[::2], intersections[1::2]):
                for y in range(max(0, math.ceil(lower)), min(HEIGHT, math.ceil(upper))):
                    canvas[y * WIDTH + x] ^= color
    return canvas


def cube_reference(vertices, visible_faces):
    return polygon_reference([(tuple(vertices[index] for index in quad), color)
                              for face, (quad, color) in enumerate(face_quads())
                              if visible_faces & (1 << face)])


def decode_charset(charset):
    return bytearray((charset[(x // 4) * HEIGHT + y] >> (6 - 2 * (x % 4))) & 3
                     for y in range(HEIGHT) for x in range(WIDTH))


def encode_canvas(canvas):
    charset = bytearray(2048)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            charset[(x // 4) * HEIGHT + y] |= canvas[y * WIDTH + x] << (6 - 2 * (x % 4))
    return charset


def marker_reference(canvas):
    """Invert the independently computed interiors to locate expected transitions."""
    packed = encode_canvas(canvas)
    return bytes(packed[column * HEIGHT + y] ^ (packed[column * HEIGHT + y - 1] if y else 0)
                 for column in range(16) for y in range(HEIGHT))


def closure_errors(markers):
    errors = {}
    for column in range(16):
        parity = 0
        for value in markers[column * HEIGHT:(column + 1) * HEIGHT]:
            parity ^= value
        if parity:
            errors[column] = parity
    return errors


def fixtures():
    """Hand-computable shapes exercise half-open edges, slopes, and shared colors."""
    rectangle = ((3, 5), (13, 5), (13, 12), (3, 12))
    triangle = ((2, 2), (8, 8), (2, 8))
    steep = ((4, 2), (6, 14), (10, 14))
    diamond = ((8, 2), (14, 8), (8, 14), (2, 8))
    upper = ((2, 2), (14, 2), (14, 14))
    lower = ((2, 2), (14, 14), (2, 14))
    cases = [
        ("flat rectangle", [(rectangle, 1)], {1: 70}),
        ("reversed rectangle", [(tuple(reversed(rectangle)), 2)], {2: 70}),
        ("diagonal triangle", [(triangle, 3)], {3: 21}),
        ("steep triangle", [(steep, 2)], {2: 24}),
        ("fractional downward slope", [(((3, 2), (10, 13), (3, 13)), 1)], {1: 41}),
        ("fractional upward slope", [(((3, 13), (10, 2), (3, 2)), 2)], {2: 47}),
        ("V corners", [(diamond, 1)], {1: 72}),
        ("shared sloped edge", [(upper, 1), (lower, 2)], {1: 66, 2: 78}),
        ("shared edge reversed", [(tuple(reversed(lower)), 2), (tuple(reversed(upper)), 1)],
         {1: 66, 2: 78}),
        ("last row and byte column", [(((60, 120), (63, 120), (63, 127), (60, 127)), 3)],
         {3: 21}),
    ]
    for index, width in enumerate((1, 2, 4, 8, 16, 32)):
        for remainder, height in enumerate((3 * width, 125)):
            lower, upper = 127 - height, 127
            upward = (index + remainder) % 2
            left, right = 63 - width, 63
            polygon = ((left, upper), (right, lower), (left, lower)) if upward else (
                (left, lower), (right, upper), (left, upper))
            if remainder:
                polygon = tuple(reversed(polygon))
            # Integer lattice counts follow from the standard floor-sum identity.
            # These closed forms do not call the rasterizer or its ceiling loop.
            area = ((height * width + height + width - math.gcd(width, height)) // 2 if upward else
                    ((height - 1) * width + height + math.gcd(width, height)) // 2)
            color = (index + remainder) % 3 + 1
            cases.append((f"division width{width} height{height}", [(polygon, color)], {color: area}))
    for name, polygons, counts in cases:
        expected = polygon_reference(polygons)
        if any(expected.count(color) != count for color, count in counts.items()):
            raise AssertionError(f"Reference disagrees with hand-computed fixture area: {name}.")
        if closure_errors(marker_reference(expected)):
            raise AssertionError(f"Reference fixture is not closed: {name}.")
        yield name, polygons, expected


def read_palette():
    palette_file = HERE / "palettes/colodore.vpl"
    palette = [tuple(int(value, 16) for value in line.split()[:3])
               for line in palette_file.read_text().splitlines()
               if line.strip() and not line.lstrip().startswith("#")]
    return palette_file, palette


@contextmanager
def machine(executable, program, output):
    output.mkdir(parents=True, exist_ok=True)
    palette_file, _ = read_palette()
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    monitor = None
    with (output / "vice.log").open("w") as log:
        process = subprocess.Popen(vice_command(executable, program, port, palette_file),
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            with connect_monitor(process, port) as connection:
                monitor = Monitor(connection)
                monitor.run("r")
                yield monitor
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


def write_memory(monitor, address, data):
    monitor.run(f"> {address:04x} " + " ".join(f"{value:02x}" for value in data))


def call(monitor, address, measure=False):
    # This stub uses the BASIC input buffer after the demo has disabled the ROMs.
    # It is ordinary debugger code, not a special entry point in the program.
    write_memory(monitor, 0x0200, [0x20, address & 255, address >> 8, 0x4c, 0x03, 0x02])
    before_cycles = monitor.registers()[2] if measure else None
    monitor.run("g 0200")
    pc, _, cycles = monitor.registers()
    if pc != 0x0203:
        raise AssertionError(f"Fixture routine did not return: ${pc:04x}.")
    return cycles - before_cycles if measure else None


def boundary_cases():
    """Cover specialized widths and nearby general-division controls systematically."""
    for width in (1, 2, 3, 4, 7, 8, 16, 31, 32):
        for slope_kind, height in (("horizontal", 0), ("exact", 3 * width), ("long", 125)):
            for upward in ((False,) if not height else (False, True)):
                left, right, lower, upper = 63 - width, 63, 127 - height, 127
                start = (left, upper if upward else lower)
                end = (right, lower if upward else upper)
                for reversed_endpoints in (False, True):
                    for color in (1, 2, 3):
                        yield {"width": width, "height": height, "slope_kind": slope_kind,
                               "upward": upward, "reversed": reversed_endpoints, "color": color,
                               "start": end if reversed_endpoints else start,
                               "end": start if reversed_endpoints else end}
    # The original matrix ends at X=63. Sweep every other reachable endpoint
    # without repeating every width, checking all color-specialized sentinels.
    for end_x in range(2, 63):
        upward = bool(end_x & 1)
        for color in (1, 2, 3):
            yield {"width": 2, "height": 3, "slope_kind": "x_lane_sentinel",
                   "upward": upward, "reversed": False, "color": color,
                   "start": (end_x - 2, 38 if upward else 35),
                   "end": (end_x, 35 if upward else 38)}
    # Full chains visit every X lane in both Y directions, including transitions
    # between byte columns and generated code pages, for all six color/bank sets.
    for upward in (False, True):
        start, end = (0, 114 if upward else 13), (63, 13 if upward else 114)
        for reversed_endpoints in (False, True):
            for color in (1, 2, 3):
                yield {"width": 63, "height": 101, "slope_kind": "x_lane_chain",
                       "upward": upward, "reversed": reversed_endpoints, "color": color,
                       "start": end if reversed_endpoints else start,
                       "end": start if reversed_endpoints else end}


def boundary_reference(start, end, color):
    """Evaluate the mathematical ceiling independently at every owned X sample."""
    if start[0] > end[0]:
        start, end = end, start
    canvas = bytearray(WIDTH * HEIGHT)
    for x in range(start[0], end[0]):
        y = math.ceil(Fraction(start[1]) + Fraction((end[1] - start[1]) * (x - start[0]),
                                                  end[0] - start[0]))
        canvas[y * WIDTH + x] = color
    return encode_canvas(canvas)


def boundary_kernel_image(original, labels):
    if "xorBoundaryKernelsStart" not in labels:
        return None
    start, end = labels["xorBoundaryKernelsStart"], labels["xorBoundaryKernelsEnd"]
    load = int.from_bytes(original[:2], "little")
    return start, end, original[2 + start - load:2 + end - load]


def verify_boundary_cases(monitor, labels, output, original):
    # Disable display DMA and the private raster clock for instruction-count
    # comparisons. Closed-polygon fixtures above exercise the normal live VIC.
    write_memory(monitor, 0xd011, [0x0b])
    write_memory(monitor, 0xd01a, [0])
    write_memory(monitor, 0xd019, [0x0f])
    # DEN can remain latched for the current frame. Execute a debugger-owned
    # JMP loop for more than one PAL frame before capturing or timing state.
    write_memory(monitor, 0x0200, [0x4c, 0x00, 0x02])
    monitor.run("r pc=$0200")
    settle_start = monitor.registers()[2]
    monitor.run("step $3000")
    settle_cycles = monitor.registers()[2] - settle_start
    if settle_cycles < 19656:
        raise AssertionError("Display DMA did not receive a full emulated PAL frame to settle.")
    allowed = [(0xd0, 0xe0), (labels["linePointer"], labels["squareSum"] + 1),
               (0x0100, 0x0206), (0x2000, 0x3000),
               (labels["drawBufferHi"], labels["drawBufferHi"] + 1),
               (labels["boundaryColor"], labels["boundaryColor"] + 1)]
    if "xorBoundaryDispatch" in labels:
        allowed.append((labels["xorBoundaryDispatch"] + 1, labels["xorBoundaryDispatch"] + 3))
    generated = boundary_kernel_image(original, labels)
    monitor.run("bank ram")
    stable_ram = bytearray(monitor.memory(output / "boundary-ram.bin", 0, 0xffff))
    monitor.run("bank cpu")
    for first, last in allowed:
        stable_ram[first:last] = bytes(last - first)
    results = []
    for high in (0x20, 0x28):
        write_memory(monitor, labels["drawBufferHi"], [high])
        opposite = 0x2800 if high == 0x20 else 0x2000
        for case in boundary_cases():
            monitor.run("f 2000 2fff 00")
            monitor.run(f"f {opposite:04x} {opposite + 2047:04x} a5")
            for name, value in zip(("lineX0", "lineY0", "lineX1", "lineY1"), (*case["start"], *case["end"])):
                write_memory(monitor, labels[name], [value])
            write_memory(monitor, labels["boundaryColor"], [case["color"]])
            cycles = call(monitor, labels["drawBoundary"], measure=True)
            monitor.run("bank ram")
            ram = monitor.memory(output / "boundary-ram.bin", 0, 0xffff)
            monitor.run("bank cpu")
            expected = boundary_reference(case["start"], case["end"], case["color"])
            if ram[high << 8:(high << 8) + 2048] != expected:
                raise AssertionError(f"Boundary fast-path case differs from exact ceilings: {case}, ${high:02x}00.")
            if ram[opposite:opposite + 2048] != bytes([0xa5]) * 2048:
                raise AssertionError(f"Boundary fast-path case changed the opposite buffer: {case}.")
            if generated is not None:
                first, last, image = generated
                if ram[first:last] != image:
                    raise AssertionError(f"Generated boundary sentinel was not restored: {case}.")
            stable = bytearray(ram)
            for first, last in allowed:
                stable[first:last] = bytes(last - first)
            if stable != stable_ram:
                address = next(i for i, (a, b) in enumerate(zip(stable, stable_ram)) if a != b)
                raise AssertionError(f"Boundary case wrote outside its workspace at ${address:04x}: {case}.")
            if case["width"] == 1 and not case["reversed"] and cycles > 150:
                raise AssertionError(f"Ordered dx=1 boundary took {cycles} cycles; budget is 150 including JSR/RTS.")
            results.append({**case, "charset": f"${high:02x}00", "cycles_with_call_return": cycles,
                            "pass": True})
    return results, settle_cycles


def verify_fixtures(program, labels, output, executable):
    boundary_ready = labels.get("boundariesReady", labels.get("boundaryReady"))
    if boundary_ready is None:
        raise ValueError("Missing natural boundary-completion debug label.")
    results = []
    original = program.read_bytes()
    kernel_start, kernel_end = labels["xorFillKernelsStart"], labels["xorFillKernelsEnd"]
    kernel_image = original[2 + kernel_start - 0x0801:2 + kernel_end - 0x0801]
    generated = boundary_kernel_image(original, labels)
    with machine(executable, program, output) as monitor:
        monitor.run(f"break {boundary_ready:04x}")
        monitor.run("x")
        monitor.run("delete 1")
        monitor.run("break 0203")
        for high in (0x20, 0x28):
            write_memory(monitor, labels["drawBufferHi"], [high])
            for name in ("dirtyMinColumn", "dirtyMinRow"):
                write_memory(monitor, labels[name], [0, 0])
            write_memory(monitor, labels["dirtyMaxColumn"], [15, 15])
            write_memory(monitor, labels["dirtyMaxRow"], [127, 127])
            for name, polygons, expected in fixtures():
                monitor.run("f 2000 2fff 00")
                opposite = 0x2800 if high == 0x20 else 0x2000
                monitor.run(f"f {opposite:04x} {opposite + 2047:04x} a5")
                for polygon, color in polygons:
                    write_memory(monitor, labels["boundaryColor"], [color])
                    for start, end in zip(polygon, polygon[1:] + polygon[:1]):
                        for field, value in zip(("lineX0", "lineY0", "lineX1", "lineY1"), (*start, *end)):
                            write_memory(monitor, labels[field], [value])
                        call(monitor, labels["drawBoundary"])
                raw = monitor.memory(output / "boundary.bin", high << 8, (high << 8) + 2047)
                if closure_errors(raw) or raw != marker_reference(expected):
                    raise AssertionError(f"CPU boundary markers differ from polygon fixture: {name}, ${high:02x}00.")
                call(monitor, labels["xorFill"])
                actual = monitor.memory(output / "filled.bin", high << 8, (high << 8) + 2047)
                if decode_charset(actual) != expected:
                    raise AssertionError(f"CPU prefix fill differs from polygon fixture: {name}, ${high:02x}00.")
                if monitor.memory(output / "opposite.bin", opposite, opposite + 2047) != bytes([0xa5]) * 2048:
                    raise AssertionError(f"Fixture wrote into the opposite buffer: {name}.")
                if monitor.memory(output / "kernels.bin", kernel_start, kernel_end - 1) != kernel_image:
                    raise AssertionError(f"Prefix kernels were not restored after fixture: {name}.")
                if generated is not None:
                    first, last, image = generated
                    if monitor.memory(output / "boundary-kernels.bin", first, last - 1) != image:
                        raise AssertionError(f"Generated boundary kernels were not restored after fixture: {name}.")
                results.append({"name": name, "charset": f"${high:02x}00", "pass": True})
        boundary_results, settle_cycles = verify_boundary_cases(monitor, labels, output, original)
    ordered_dx1 = [case["cycles_with_call_return"] for case in boundary_results
                   if case["width"] == 1 and not case["reversed"]]
    report = {"pass": True, "program_sha256": hashlib.sha256(original).hexdigest(),
              "fixture_cases": len(results), "boundary_cases": len(boundary_results),
              "ordered_dx1_budget_cycles": 150,
              "ordered_dx1_guard_evaluation": {"method": "active_assertion_during_fixture_run",
                                               "performed_during_emulator_run": True,
                                               "samples_checked": len(ordered_dx1), "limit_cycles": 150,
                                               "max_measured_cycles": max(ordered_dx1), "passed": True},
              "boundary_timing_setup": {"method": "12288 debugger JMP instructions after DEN and IRQ disable",
                                         "emulated_settle_cycles": settle_cycles,
                                         "minimum_required_cycles": 19656},
              "boundary_cycle_measurement": "CPU cycles including JSR/RTS; display DMA and raster IRQ disabled",
              "samples": results, "boundary_samples": boundary_results}
    (output / "fixtures.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ("samples", "boundary_samples")}, indent=2))


def mutable_ranges(labels):
    ranges = [(0x0100, 0x0200), (labels["linePointer"], labels["squareSum"] + 1),
            (labels["angleYaw"], labels["bitMasks"]), (0x2000, 0x3000),
            (0xd0, 0xe0), (labels["cullDX1"], labels["cullSumHi"] + 1),
            (labels["visibleFaces"], labels["visibleFaces"] + 1),
            (labels["clearPatchPointer"], labels["clearPatchPointer"] + 2),
            (labels["clearStateStart"], labels["clearStateEnd"]),
            (labels["clearEntry"] + 1, labels["clearEntry"] + 3),
            (labels["clearFirstRow"] + 1, labels["clearFirstRow"] + 2),
            (labels["clearLastRow"] + 1, labels["clearLastRow"] + 2),
            (labels["fillStateStart"], labels["fillStateEnd"]),
            (labels["xorFillEntry"] + 1, labels["xorFillEntry"] + 3)]
    if "xorBoundaryDispatch" in labels:
        ranges.append((labels["xorBoundaryDispatch"] + 1, labels["xorBoundaryDispatch"] + 3))
    return ranges


def screenshot_difference(image, canvas, colors):
    expected = [colors[canvas[y * WIDTH + x // 2]] for y in range(HEIGHT) for x in range(WIDTH * 2)]
    image = image.convert("RGB")
    candidates = []
    for top in range(28, 42):
        for left in range(28, 38):
            actual = list(image.crop((left + 96, top + 32, left + 224, top + 160)).get_flattened_data())
            candidates.append((sum(a != b for a, b in zip(actual, expected)), left, top))
    return min(candidates)


def preview(canvas, colors):
    palette = [component for color in colors for component in color] + [0] * (768 - 12)
    field = Image.frombytes("P", (WIDTH, HEIGHT), bytes(canvas))
    field.putpalette(palette)
    image = Image.new("P", (320, 200))
    image.putpalette(palette)
    image.paste(field.resize((128, 128), Image.Resampling.NEAREST), (96, 32))
    return image.resize((640, 400), Image.Resampling.NEAREST)


def save_animation(frames, path, duration):
    header, _ = GifImagePlugin.getheader(frames[0], info={"loop": 0, "optimize": False})
    with path.open("wb") as stream:
        for block in header:
            stream.write(block)
        for frame in frames:
            for block in GifImagePlugin.getdata(frame, duration=duration, disposal=1):
                stream.write(block)
        stream.write(b";")


def read_ram(monitor, output):
    monitor.run("bank ram")
    ram = monitor.memory(output / "ram.bin", 0, 0xffff)
    monitor.run("bank cpu")
    return ram


def verify(program, labels, output, executable, frames, ticks, raster_line):
    original = program.read_bytes()
    if original[:2] != b"\x01\x08":
        raise ValueError("Expected a runnable C64 PRG at $0801.")
    boundary_ready = labels.get("boundariesReady", labels.get("boundaryReady"))
    if boundary_ready is None:
        raise ValueError("Missing natural boundary-completion debug label.")
    _, palette = read_palette()
    colors = [palette[index] for index in (0, 6, 14, 3)]
    allowed = mutable_ranges(labels)
    kernel_start, kernel_end = labels["xorFillKernelsStart"], labels["xorFillKernelsEnd"]
    kernel_image = original[2 + kernel_start - 0x0801:2 + kernel_end - 0x0801]
    generated = boundary_kernel_image(original, labels)
    samples, animation, elapsed, hashes = [], [], [], set()
    previous_canvas = previous_angles = previous_cycles = previous_tick = stable_ram = None
    seen_buffers, captures = set(), 0
    output.mkdir(parents=True, exist_ok=True)
    (output / "verification.json").unlink(missing_ok=True)
    with machine(executable, program, output) as monitor:
        monitor.run(f"break {boundary_ready:04x}")
        monitor.run(f"break {labels['framePresented']:04x}")
        for index in range(frames):
            monitor.run("x")
            pc, _, _ = monitor.registers()
            if pc != boundary_ready:
                raise AssertionError("Program did not finish drawing boundary markers.")
            before = read_ram(monitor, output)
            if generated is not None:
                first, last, image = generated
                if before[first:last] != image:
                    raise AssertionError("Generated boundary kernels were not restored before prefix filling.")
            draw = before[labels["drawBufferHi"]] << 8
            if draw not in (0x2000, 0x2800):
                raise AssertionError("Boundary renderer selected an unexpected charset.")
            yaw, pitch = before[labels["angleYaw"]], before[labels["anglePitch"]]
            vertices = list(zip(before[labels["projectedX"]:labels["projectedX"] + 8],
                                before[labels["projectedY"]:labels["projectedY"] + 8]))
            if any(not (0 <= x < WIDTH and 0 <= y < HEIGHT) for x, y in vertices):
                raise AssertionError("A projected vertex escaped the multicolor canvas.")
            ideal = geometry_reference(yaw, pitch)
            # Dropping the physical X low bit deliberately selects a two-pixel
            # footprint. Measure distance to that footprint, not its left edge.
            error = max(max(2 * x - ref_x, ref_x - (2 * x + 1), 0, abs(y - ref_y))
                        for (x, y), (ref_x, ref_y) in zip(vertices, ideal))
            if error > 3:
                raise AssertionError(f"Projection differs from true geometry by {error:.3f} physical pixels.")
            visible = visible_faces_reference(vertices)
            if before[labels["visibleFaces"]] != visible:
                raise AssertionError("Face visibility differs from independent signed screen areas.")
            expected = cube_reference(vertices, visible)
            markers = before[draw:draw + 2048]
            parity = closure_errors(markers)
            if parity:
                raise AssertionError(f"Open boundary bitplanes in byte columns: {parity}.")
            expected_markers = marker_reference(expected)
            if markers != expected_markers:
                raise AssertionError(f"Boundary markers differ from independent polygon interiors in "
                                     f"{sum(a != b for a, b in zip(markers, expected_markers))} bytes.")
            monitor.run("x")
            pc, line, cycles = monitor.registers()
            if pc != labels["framePresented"]:
                raise AssertionError("Program did not present its filled buffer.")
            io = monitor.memory(output / "vic.bin", 0xd000, 0xd03f)
            if io[0x11] & 0x60 or io[0x16] & 0x1f != 0x18:
                raise AssertionError("VIC-II left standard multicolor character mode.")
            if [io[address] & 15 for address in (0x21, 0x22, 0x23)] != [0, 6, 14]:
                raise AssertionError("Multicolor palette registers changed.")
            if io[0x18] >> 4 != 1 or (io[0x18] & 14) * 1024 != draw:
                raise AssertionError("Displayed screen/charset does not match the completed buffer.")
            after = read_ram(monitor, output)
            actual = after[draw:draw + 2048]
            if decode_charset(actual) != expected:
                raise AssertionError("Filled charset differs from direct odd-even polygon coverage.")
            opposite = draw ^ 0x0800
            if after[opposite:opposite + 2048] != before[opposite:opposite + 2048]:
                raise AssertionError("Prefix filling changed the displayed opposite buffer.")
            if after[kernel_start:kernel_end] != kernel_image:
                raise AssertionError("Generated prefix kernels were not restored after filling.")
            stable = bytearray(after)
            for first, last in allowed:
                stable[first:last] = bytes(last - first)
            if stable_ram is not None and stable != stable_ram:
                address = next(i for i, (a, b) in enumerate(zip(stable, stable_ram)) if a != b)
                raise AssertionError(f"Unexpected write outside renderer workspaces at ${address:04x}.")
            stable_ram = stable
            if (line - raster_line) % 312 > 3:
                raise AssertionError(f"Presentation missed its raster window: line {line}.")
            if previous_cycles is not None:
                elapsed.append(cycles - previous_cycles)
                if abs(elapsed[-1] - ticks * 19656) > 63:
                    raise AssertionError(f"Presentation missed its {ticks}-frame cycle budget: {elapsed[-1]} cycles.")
            if previous_tick is not None and (after[labels["rasterTick"]] - previous_tick) % 256 != ticks:
                raise AssertionError("Raster clock did not advance at the required cadence.")
            if previous_angles is not None:
                expected_yaw = (previous_angles[0] + ticks) & 255
                expected_pitch = (previous_angles[1] + int(ticks == 2 or expected_yaw % 2 == 0)) & 255
                if (yaw, pitch) != (expected_yaw, expected_pitch):
                    raise AssertionError("Rotation speed changed between presentations.")
            if after[labels["drawBufferHi"]] << 8 != draw ^ 0x0800:
                raise AssertionError("Drawing and displayed charsets are not separate buffers.")
            if any(after[0x0400 + (row + 4) * 40 + column + 12] != column * 16 + row
                   for row in range(16) for column in range(16)):
                raise AssertionError("Column-major screen mapping changed.")
            if index == 0:
                color_ram = monitor.memory(output / "colors.bin", 0xd800, 0xdbe7)
                if any(color_ram[(row + 4) * 40 + column + 12] & 15 != 11
                       for row in range(16) for column in range(16)):
                    raise AssertionError("Canvas cells do not select multicolor and foreground color3.")
            sample = {"yaw": yaw, "pitch": pitch, "vertices": vertices, "visible_faces": visible,
                      "charset": f"${draw:04x}", "geometry_error_pixels": round(error, 4),
                      "colored_pixels": sum(value != 0 for value in expected),
                      "color_counts": [expected.count(color) for color in range(4)],
                      "boundary_parity_errors": 0, "cycles": cycles, "presentation_raster_line": line,
                      "marker_sha256": hashlib.sha256(markers).hexdigest(),
                      "charset_sha256": hashlib.sha256(actual).hexdigest()}
            if previous_canvas is not None and index % max(1, frames // 32) == 0:
                screenshot = output / f"vice-{index:03d}.png"
                monitor.run(f'scrsh "{screenshot}" 2')
                mismatch, left, top = screenshot_difference(Image.open(screenshot), previous_canvas, colors)
                if mismatch:
                    raise AssertionError(f"Native multicolor VICE capture differs in {mismatch} physical pixels.")
                sample.update({"screenshot": screenshot.name, "screenshot_mismatches": mismatch,
                               "screen_origin": [left, top]})
                captures += 1
            samples.append(sample)
            animation.append(preview(expected, colors))
            hashes.add(sample["charset_sha256"])
            seen_buffers.add(draw)
            previous_canvas, previous_angles, previous_cycles = expected, (yaw, pitch), cycles
            previous_tick = after[labels["rasterTick"]]
    if seen_buffers != {0x2000, 0x2800} or len(hashes) < 2:
        raise AssertionError("Both filled buffers must animate.")
    save_animation(animation, output / "filled-cube.gif", ticks * 20)
    report = {"pass": True, "program_sha256": hashlib.sha256(original).hexdigest(),
              "frames_verified": frames, "logical_canvas": [WIDTH, HEIGHT], "physical_canvas": [128, 128],
              "pal_frames_per_presentation": ticks, "raster_irq_line": raster_line,
              "boundary_parity_errors": 0, "distinct_canvases": len(hashes), "screenshots": captures,
              "max_geometry_error_pixels": max(sample["geometry_error_pixels"] for sample in samples),
              "cycles_per_presentation": {"min": min(elapsed), "max": max(elapsed)},
              "independent_checks": ["exact Fraction odd-even polygon interiors", "signed-area visibility",
                                     "boundary markers from independent interior differences",
                                     "closed color bitplanes in every byte column", "exact multicolor VIC pixels",
                                     "restored generated prefix kernels", "RAM writes restricted to owned workspaces",
                                     "strict PAL raster/cycle cadence", "unchanged angular speed"],
              "gif": {"file": "filled-cube.gif", "frames": frames, "frame_duration_ms": ticks * 20},
              "samples": samples}
    (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "samples"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", type=Path, nargs="?", default=HERE / "build/filled-cube.prg")
    parser.add_argument("--labels", type=Path, default=HERE / "build/filled.sym")
    parser.add_argument("--output", type=Path, default=HERE / "build/filled-verification")
    parser.add_argument("--vice", default=os.environ.get("VICE") or shutil.which("x64sc"))
    parser.add_argument("--ticks", type=int, choices=(1, 2), default=2,
                        help="Expected PAL frames per presentation (default: 2).")
    parser.add_argument("--raster-line", type=int, default=0)
    parser.add_argument("--frames", type=int)
    parser.add_argument("--fixtures", action="store_true", help="Run boundary/fill CPU fixtures in both buffers.")
    args = parser.parse_args()
    if not args.vice:
        parser.error("x64sc is missing; install VICE or pass --vice /path/to/x64sc.")
    frames = args.frames if args.frames is not None else 512 // args.ticks
    if frames < 2 or not 0 <= args.raster_line < 312:
        parser.error("Use at least 2 frames and a PAL raster line in 0..311.")
    if args.fixtures:
        verify_fixtures(args.program.resolve(), read_labels(args.labels), args.output.resolve(), args.vice)
    else:
        verify(args.program.resolve(), read_labels(args.labels), args.output.resolve(), args.vice,
               frames, args.ticks, args.raster_line)
