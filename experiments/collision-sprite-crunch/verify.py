#!/usr/bin/env python3
"""Native PAL proof of hardware collision packing, crunch timing and visible DMA.

The reference uses an authored row/geometry specification, not the generated
sprite bytes or CPU collision log, to predict the image and control decisions.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import shutil
import socket
import subprocess

from PIL import Image, ImageChops


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("c64_native", ROOT / "verify.py")
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
ROWS = (
    (53,56,59,62,21,24,27,30,33,37,40,43,46,49),
    (53,56,59,62,1,5,8,11,15,23,26,29,32,35,39,42,45),
    (53,56,59,62,1,4,7,10,13,21,24,27,30,33,37,40,43,46,49),
    (53,56,59,62,1,5,8,11,14,17,20,23,26,29,32,35,38,41,44,47,50),
)
COLORS = (3,4,5,14,8,10,7,1)
SAMPLE_PHASES = {0,1,9,17,31,47,55,63}
TIMING_PHASES = {0,1,17,31,47,63}
TIMING_LINES = (76,83,90,113,174,235)
FIELD_CLOCKS = 63 * 312


def holds(phase):
    return [math.floor(3.5 + 3.5 * math.sin((phase + i * 8) % 64 * math.tau / 64) + .5)
            for i in range(8)]


def row_index(column, fetch_line, offsets):
    age = fetch_line - 76 - offsets[column]
    return 0 if age < 0 else age % len(ROWS[column % 4])


def bases(fetch_line, offsets):
    if fetch_line == 75:
        return [45] * 8
    return [ROWS[i % 4][row_index(i, fetch_line, offsets)] for i in range(8)]


def is_crunch(column, row):
    rows = ROWS[column % 4]
    return int(rows[(row + 1) % len(rows)] != (rows[row] + 3) % 64)


def collision(line, offsets):
    # Display was fetched one line earlier; we read the preceding displayed row.
    return sum(is_crunch(i, (row_index(i, line - 2, offsets) + 2) % len(ROWS[i % 4])) << i
               for i in range(8))


def tile_points(column, row):
    """Own outlined tile and diagonal hatching, excluding the hidden 24th pixel."""
    height = len(ROWS[column % 4])
    if not row:
        return set()
    result = set()
    if 2 <= row <= height - 2:
        result.update((2, 20))
    if row in (2, height - 2):
        result.update(range(2, 21))
    if 3 <= row <= height - 3:
        first = (-(row + column * 3)) % 7
        result.update(x for x in range(first, 20, 7) if x >= 3)
    return result


def sprite_bytes():
    result = bytearray(512)
    for column in range(8):
        for row, base in enumerate(ROWS[column % 4]):
            points = tile_points(column, row)
            if is_crunch(column, (row + 2) % len(ROWS[column % 4])):
                points.add(23)
            for x in points:
                result[column * 64 + (base + x // 8) % 64] |= 128 >> (x % 8)
    return bytes(result)


def expected_image(phase, palette):
    image = Image.new("RGB", (320, 200), palette[0])
    offsets = holds(phase)
    for y in range(26, 186):
        for column in range(8):
            row = row_index(column, y + 50, offsets)
            for x in tile_points(column, row):
                image.putpixel((64 + column * 24 + x, y), palette[COLORS[column]])
    return image


def registers(monitor):
    text = monitor.run("r")
    match = re.search(r"^\.;([\da-fA-F]{4})\s+(.*)$", text, re.M)
    if not match:
        raise RuntimeError("No native registers returned.")
    fields = match[2].split()
    return {"pc": int(match[1],16), "a": int(fields[0],16), "x": int(fields[1],16),
            "y": int(fields[2],16), "raster": int(fields[-3]),
            "cycle_zero_based": int(fields[-2]), "clock": int(fields[-1])}


def vic_state(monitor):
    text = monitor.run("io d000")
    rows = re.findall(r">C:d0[0-3]0\s+((?:[\da-fA-F]{2}\s+){15}[\da-fA-F]{2})", text)
    if len(rows) != 4:
        raise RuntimeError("Could not decode native VIC registers.")
    values = bytes.fromhex(" ".join(rows))
    base_line = re.search(r"^MCBASE:\s+(.*)$", text, re.M)
    dma_line = re.search(r"^DMA/dis:\s+(.*)$", text, re.M)
    if not base_line or not dma_line:
        raise RuntimeError("Native VIC did not report its DMA counters.")
    return {"mcbase": [int(value,16) for value in re.findall(r"\$([\da-fA-F]{2})", base_line[1])],
            "dma": dma_line[1].split(), "d017": values[0x17], "d01f": values[0x1f]}


def stop(monitor, address):
    monitor.run("delete")
    monitor.run(f"break {address:04x}")
    monitor.run("x")
    state = registers(monitor)
    if state["pc"] != address:
        raise AssertionError("Stopped outside the requested native instruction.")
    return state


def capture(monitor, output, name, expected):
    path = output / (name + ".png")
    monitor.run(f'screenshot "{path}" 2')
    native = Image.open(path).convert("RGB").crop((32,35,352,235))
    expected.save(output / (name + "-expected.png"))
    difference = ImageChops.difference(native, expected)
    different = sum(a != b for a,b in zip(native.getdata(),expected.getdata()))
    if different:
        difference.save(output / (name + "-difference.png"))
    return different


def verify(args):
    labels = common.read_labels(HERE / "build/main.sym")
    program = HERE / "build/example.prg"
    data = program.read_bytes()
    base = int.from_bytes(data[:2], "little")
    def table(name):
        lo, hi = labels[name + "Lo"] - base + 2, labels[name + "Hi"] - base + 2
        return [data[lo + i] | data[hi + i] << 8 for i in range(176)]
    sites = {name:table(name) for name in ("crunch", "sampled", "applied")}
    for i, address in enumerate(sites["crunch"]):
        offset = address - base + 2
        if data[offset:offset + 6] != bytes.fromhex("9c17d0ad1fd0"):
            raise AssertionError(f"Row {61+i} does not clear $D017 and read actual $D01F.")
        if i >= 83 - 61 and data[offset+6:offset+9] != bytes.fromhex("8d17d0"):
            raise AssertionError("Body decision is not fed directly back to $D017.")
    if (HERE / "build/sprites.bin").read_bytes() != sprite_bytes():
        raise AssertionError("Generated artwork differs from its independent tile specification.")
    # Check every authored loop against the bit-level VIC crunch equation.
    for rows in ROWS:
        for first, following in zip(rows,rows[1:]+rows[:1]):
            normal = (first+3)%64
            glitched = sum((((first >> bit & 1) | (normal >> bit & 1)) if bit%2 == 0
                            else ((first >> bit & 1) & (normal >> bit & 1))) << bit
                           for bit in range(6))
            if following not in (normal,glitched):
                raise AssertionError("Authored loop violates the documented hardware equation.")
    palette_path = ROOT / "palettes/colodore.vpl"
    palette = [tuple(int(x,16) for x in line.split()[:3])
               for line in palette_path.read_text().splitlines()
               if line.strip() and not line.lstrip().startswith("#")]
    output = HERE / "build/verification" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output.mkdir(parents=True)
    receipt = {"passed":False, "program_sha256":hashlib.sha256(data).hexdigest(),
               "frames":[], "timing":[], "exact_pixels":0, "collision_bytes":0,
               "model":"Independent tile geometry, row loops and VIC boolean transition equation",
               "synthetic_input":"Negative control patches one live SHY destination, after the normal run"}
    monitor = None
    process = None
    log = (output / "vice.log").open("w")
    sock = socket.socket()
    sock.bind(("127.0.0.1",0))
    port = sock.getsockname()[1]
    sock.close()
    try:
        command = common.vice_command(args.vice,program,port,palette_path)
        command[command.index("+warp")] = "-warp"
        process = subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        monitor = common.Monitor(common.connect_monitor(process,port))
        monitor.run("r")  # Barrier against the asynchronous initial greeting.
        monitor.run("sidefx off")
        previous_field = None
        for phase in range(64):
            offsets = holds(phase)
            if phase in TIMING_PHASES:
                prelude = stop(monitor,labels["prelude"])
                if (prelude["raster"],prelude["cycle_zero_based"]) != (55,0):
                    raise AssertionError("Double IRQ did not align the raster prelude.")
                for line in TIMING_LINES:
                    start = stop(monitor,sites["crunch"][line-61])
                    before = vic_state(monitor)
                    if before["mcbase"] != bases(line-1,offsets):
                        raise AssertionError(f"Unexpected DMA base before crunch at phase{phase}/line{line}.")
                    if before["dma"] != ["D/d"] * 8:
                        raise AssertionError("The effect is not using eight active VIC DMA streams.")
                    monitor.run("z")
                    falling = registers(monitor)
                    if (falling["raster"],falling["cycle_zero_based"]) != (line,15):
                        raise AssertionError("The five-cycle falling write did not end on PAL cycle15.")
                    monitor.run("z")
                    sampled = registers(monitor)
                    after = vic_state(monitor)
                    if sampled["pc"] != sites["sampled"][line-61] or (sampled["raster"],sampled["cycle_zero_based"]) != (line,19):
                        raise AssertionError("Hardware collision read is outside cycles16..19.")
                    if after["mcbase"] != bases(line,offsets):
                        raise AssertionError(f"VIC did not perform the required crunch at phase{phase}/line{line}.")
                    if after["d01f"]:
                        raise AssertionError("CPU read did not reset the actual collision latch.")
                    record = {"phase":phase,"line":line,"before":before,"after":after,
                              "falling_write_finished":falling,"sampled":sampled}
                    if line >= 83:
                        expected = collision(line,offsets)
                        if sampled["a"] != expected:
                            raise AssertionError("Native $D01F did not pack the eight expected decisions.")
                        monitor.run("z")
                        applied = registers(monitor)
                        applied_vic = vic_state(monitor)
                        if applied["pc"] != sites["applied"][line-61] or (applied["raster"],applied["cycle_zero_based"]) != (line,23):
                            raise AssertionError("Direct decision write is outside cycles20..23.")
                        if applied_vic["d017"] != expected:
                            raise AssertionError("Hardware packed byte was not written to $D017.")
                        record["applied"] = applied
                        record["expected_collision"] = expected
                    receipt["timing"].append(record)
            state = stop(monitor,labels["framePresented"])
            field_start = state["clock"] - state["raster"]*63 - state["cycle_zero_based"]
            if previous_field is not None and field_start - previous_field != FIELD_CLOCKS:
                raise AssertionError("Animation missed or duplicated a PAL field.")
            previous_field = field_start
            monitor.run("bank ram")
            ram = monitor.memory(output / f"phase-{phase:02d}.bin",0,0xffff)
            monitor.run("bank cpu")
            if ram[labels["phase"]] != phase or list(ram[labels["holdOffsets"]:labels["holdOffsets"]+8]) != offsets:
                raise AssertionError("Native movement state differs from the sine reference.")
            if ram[0x4000:0x4200] != sprite_bytes():
                raise AssertionError("Sprite source patterns changed or came from another bank.")
            if list(ram[0x5ff8:0x6000]) != list(range(8)):
                raise AssertionError("VIC pointers do not address the specified source patterns.")
            for line in range(83,237):
                if ram[labels["collisionLog"] + line-61] != collision(line,offsets):
                    raise AssertionError(f"Hardware packing differs at phase{phase}/line{line}.")
                receipt["collision_bytes"] += 1
            if phase in SAMPLE_PHASES:
                wrong = capture(monitor,output,f"phase-{phase:02d}",expected_image(phase,palette))
                if wrong:
                    raise AssertionError(f"Native sprite DMA image has {wrong} wrong pixels in phase{phase}.")
                receipt["exact_pixels"] += 64000
            receipt["frames"].append({"phase":phase,"hold_offsets":offsets,**state,"field_start":field_start})
        # An equal-duration write to the border omits one actual $D017 falling edge.
        # The resulting wrong MCBASE and pixels prove the normal oracle is sensitive
        # to the required VIC mechanism, rather than only a CPU bookkeeping table.
        address = sites["crunch"][90-61]
        monitor.run(f"> {address+1:04x} 20")
        stop(monitor,sites["sampled"][90-61])
        negative = vic_state(monitor)
        expected = bases(90,holds(0))
        if negative["mcbase"] == expected:
            raise AssertionError("Omitting the crunch did not disturb actual VIC DMA bases.")
        stop(monitor,labels["framePresented"])
        wrong = capture(monitor,output,"negative-no-crunch",expected_image(0,palette))
        if not wrong:
            raise AssertionError("The missing crunch was invisible to the independent pixel oracle.")
        receipt["negative_control"] = {"line":90,"phase":0,"patched_ram_operand":address+1,
                                       "expected_mcbase":expected,"actual_mcbase":negative["mcbase"],
                                       "different_pixels":wrong,"rejected_as_expected":True}
        receipt["cadence"] = {"pal_fields_per_pose":1,"pal_clocks_per_pose":FIELD_CLOCKS,
                              "nominal_poses_per_second":50,"observed_consecutive_poses":64}
        receipt["passed"] = True
    except Exception as error:
        receipt["error"] = str(error)
        raise
    finally:
        if monitor:
            (output / "monitor.txt").write_text("\n".join(monitor.transcript))
            monitor.connection.close()
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        log.close()
        (output / "verification.json").write_text(json.dumps(receipt,indent=2)+"\n")
        print(output / "verification.json",flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vice",default=shutil.which("x64sc"))
    verify(parser.parse_args())
