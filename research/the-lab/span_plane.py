#!/usr/bin/env python3
"""Check The Lab's expanded-sprite plane and prepared span/triangle inputs.

Consumes native RAM already captured by the separate owned VICE run. Executes
only pointer-table setup and RAM-only compressed-span APIs in py65; no VICE,
timer/IRQ simulation, process control, or production renderer changes.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RAM_SHA = "8504f35ee08086d534ac2ef8644d0e31dcdc73e1b7ba35d77ed1a45c94ca4fa4"
POSE74_SHA = "f63a4f22e68df183eb49648e21f8c8dc6d2a405f43c60338580149f281537757"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pointer_proof(image, cpu_class, execute):
    # Start after the genuine raster handshake. No wait/IRQ is fabricated.
    results = []
    for entry, first in ((0x8BF8, 0x80), (0x8D3D, 0xC0)):
        ram, instructions = execute(cpu_class, image, entry)
        tables = []
        for band in range(7):
            address = 0xC3F8 + band * 0x400
            row = band if band < 4 else 0x20 + band - 4
            wanted = bytes(first + 4 * sprite + row for sprite in range(8))
            assert ram.data[address:address + 8] == wanted
            tables.append({"band": band, "table": address, "values": list(wanted),
                           "physical_start_raster": 15 + 42 * band})
        # Compare every displayed byte's sprite fetch address to the independently
        # established span-storage formula, for both 84-row slices.
        compared = 0
        for column in range(24):
            for y in range(147):
                band, within = divmod(y, 21)
                pointer = ram.data[0xC3F8 + band * 0x400 + column // 3]
                fetched = 0xC000 + pointer * 64 + within * 3 + column % 3
                local = y % 84
                drawn = (0xC000 + first * 64 + (0x800 if y >= 84 else 0)
                         + (column // 3) * 256 + column % 3
                         + 64 * (local // 21) + 3 * (local % 21))
                assert fetched == drawn
                compared += 1
        results.append({"setup_entry_after_wait": entry, "first_pointer": first,
                        "original_instructions": instructions,
                        "tables": tables, "displayed_byte_addresses_compared": compared})
    # Validate the source immediates that establish the seven Y/selector bands.
    y_operands = [0x2F5B, 0x2D32, 0x2D69, 0x2DA0, 0x3022, 0x2E32, 0x3136]
    d018_operands = [0x2F8C, 0x2D56, 0x2D83, 0x2DBA, 0x303C, 0x2E4C, 0x3172]
    assert [image[p] for p in y_operands] == [15, 57, 99, 141, 183, 225, 11]
    assert all(image[p - 1] == 0xA9 for p in y_operands + d018_operands)
    assert [image[p] for p in d018_operands] == [6 + 16 * i for i in range(7)]
    # The last low-Y=11 band occurs at raster267, not at raster11: it is armed
    # by the raster248 handler; bit8+D0120A next selects raster266 to setD01866.
    assert image[0x3120:0x312A] == bytes.fromhex("48 a9 83 8d 11 d0 a9 0a 8d 12")
    assert image[0x3154:0x315E] == bytes.fromhex("48 a9 8b 8d 11 d0 a9 1e 8d 12")
    return {"pass": True, "buffers": results,
            "logical_display": [192, 147], "expanded_physical_display": [384, 294],
            "physical_rasters_inclusive": [15, 308],
            "allocated_logical_capacity": [192, 168],
            "first_slice_displayed_rows": 84, "second_slice_displayed_rows": 63,
            "undisplayed_last_slice_rows": 21,
            "interpretation": "Contiguous vertical slices, double buffered; not odd/even row fields"}


def prepared_inputs(image):
    count = image[0x9EA0]
    special = {image[0x9EA1 + i]: image[0x9ECF + i] + 256 * image[0x9EFD + i]
               for i in range(count)}
    assert count == len(special) == 46
    cursor, default, triangles = 0x9041, [], [0, 0]
    ys = [[], []]
    for pose in range(164):
        if pose in special:
            continue
        start, header = cursor, image[cursor]
        cursor += 1
        counts = [header & 15, header >> 4]
        for half, number in enumerate(counts):
            triangles[half] += number
            for _ in range(number):
                record = image[cursor:cursor + 7]
                assert all(record[i] < 192 for i in (0, 2, 4))
                assert all(record[i] < 84 for i in (1, 3, 5))
                ys[half].extend(record[i] for i in (1, 3, 5))
                cursor += 7
        default.append({"pose": pose, "address": start, "counts": counts})
    assert cursor == 0x99F5
    packets = []
    for pose, address in special.items():
        cursor, halves = address, []
        for half in range(2):
            number = image[cursor]
            cursor += 1
            runs = []
            for _ in range(number):
                material, height, y = image[cursor:cursor + 3]
                left, right = image[cursor + 3:cursor + 5]
                cursor += 5
                assert material < 16 and 0 < height <= 84 and y + height <= 84
                rows = []
                for row in range(height):
                    assert 0 <= left <= right < 192
                    rows.append([y + row, left, right])
                    if row + 1 < height:
                        token = image[cursor]
                        cursor += 1
                        if token == 255:
                            left, right = image[cursor:cursor + 2]
                            cursor += 2
                        else:
                            assert token < 16
                            left = (left + image[0x9E80 + token]) & 255
                            right = (right + image[0x9E90 + token]) & 255
                runs.append({"material": material, "rows": rows})
            halves.append(runs)
        packets.append({"pose": pose, "address": address, "end": cursor, "halves": halves})
    for here, following in zip(packets, packets[1:]):
        assert here["end"] == following["address"]
    assert packets[-1]["end"] == 0xBFC2
    return {"poses": 164, "triangle_poses": len(default), "run_poses": len(packets),
            "triangle_packets_end": 0x99F5, "triangles_by_half": triangles,
            "triangle_max_local_y_by_half": [max(v) for v in ys],
            "run_max_local_y_by_half": [max(row[0] for p in packets
                                           for run in p["halves"][h] for row in run["rows"])
                                        for h in range(2)],
            "default_poses": default, "run_packets": packets}


def run_reference(image, packet):
    wanted = bytearray(4096)
    for half, runs in enumerate(packet["halves"]):
        for run in runs:
            material = run["material"]
            pattern = 0x8400 + (material // 2) * 256 + (material % 2) * 88 + 4 * half
            for row, left, right in run["rows"]:
                first, last = left // 8, right // 8
                for column in range(first, last + 1):
                    address = (half * 2048 + (column // 3) * 256 + column % 3
                               + 64 * (row // 21) + 3 * (row % 21))
                    mask = 255
                    if column == first:
                        mask &= 255 >> (left % 8)
                    if column == last:
                        mask &= (255 << (7 - right % 8)) & 255
                    value = image[pattern + row]
                    if first < column < last:
                        wanted[address] = value
                    else:
                        wanted[address] |= value & mask
    return wanted


def run_cpu_proof(image, packets, cpu_class, execute):
    results = []
    for packet in packets:
        memory = bytearray(image)
        memory[0xE000:0xF000] = bytes(4096)
        memory[0x6F:0x71] = bytes((0xE0, 0xE8))
        memory[0x73:0x75] = packet["address"].to_bytes(2, "little")
        memory[0x75] = 255
        ram, instructions = execute(cpu_class, memory, 0x7F8A, limit=1000000)
        wanted = run_reference(image, packet)
        assert ram.data[0xE000:0xF000] == wanted, packet["pose"]
        results.append({"pose": packet["pose"], "original_instructions": instructions,
                        "buffer_sha256": sha(wanted)})
    return {"pass": True, "packets": len(results),
            "original_instructions": sum(x["original_instructions"] for x in results),
            "scope": "Original compressed-run renderer including its cached fast span paths; isolated zeroed4KBbuffer and original supplied packets, no raster/IRQ timing",
            "results": results}


def area_ranking(image, inputs):
    scores = []
    for packet in inputs["default_poses"]:
        cursor, area, checker = packet["address"] + 1, 0, 0
        for half, number in enumerate(packet["counts"]):
            for _ in range(number):
                record = image[cursor:cursor + 7]
                cursor += 7
                points = [(record[i], record[i + 1] + half * 84) for i in (0, 2, 4)]
                value = abs(sum(points[i][0] * points[(i + 1) % 3][1]
                                - points[(i + 1) % 3][0] * points[i][1]
                                for i in range(3))) / 2
                area += value
                checker += value * ((record[6] & 127) == 8)
        scores.append({"pose": packet["pose"], "kind": "triangles",
                       "draw_area": area, "checker8_area": checker})
    for packet in inputs["run_packets"]:
        area, checker = 0, 0
        for half, runs in enumerate(packet["halves"]):
            for run in runs:
                for row, left, right in run["rows"]:
                    if row + half * 84 < 147:
                        area += right - left + 1
                        checker += (right - left + 1) * (run["material"] == 8)
        scores.append({"pose": packet["pose"], "kind": "runs",
                       "draw_area": area, "checker8_area": checker})
    return {"largest_draw": sorted(scores, key=lambda v: v["draw_area"], reverse=True)[:12],
            "largest_checker8": sorted(scores, key=lambda v: v["checker8_area"], reverse=True)[:12],
            "scope": "Sum of triangle geometric areas or visible scanline widths; includes overlapping and clearing material0, not final opaque pixel union",
            "initial_controller_display_lag": "At counter78=N after N updates, most recently completed back poseN-1 and displayed front poseN-2; restoreinitialized then74updates targets frontpose72"}


def native_pose_proof(source, inputs, path):
    native = path.read_bytes()
    assert sha(native) == POSE74_SHA
    assert [native[p] for p in (0x60, 0x6F, 0x70, 0x78)] == [0, 0xE0, 0xE8, 74]
    packets = {p["pose"]: p for p in inputs["run_packets"]}
    comparisons = []
    for pose, base in ((72, 0xF000), (73, 0xE000)):
        packet = packets[pose]
        start, end = packet["address"], packet["end"]
        assert native[start:end] == source[start:end]
        wanted = run_reference(source, packet)
        compared = 0
        for column in range(24):
            for y in range(147):
                half, local = divmod(y, 84)
                offset = (half * 2048 + (column // 3) * 256 + column % 3
                          + 64 * (local // 21) + 3 * (local % 21))
                assert native[base + offset] == wanted[offset], (pose, column, y)
                compared += 1
        comparisons.append({"pose": pose, "buffer": base,
                            "display_role": "front" if pose == 72 else "back",
                            "displayed_bytes_compared": compared})
    return {"pass": True, "native_ram_path": str(path), "native_ram_sha256": sha(native),
            "controller_updates": 74, "comparisons": comparisons,
            "total_displayed_bytes_compared": sum(v["displayed_bytes_compared"] for v in comparisons),
            "scope": "Every displayed pixel byte, including zeros, for two native poses; only sprite padding and undisplayed allocation rows are outside the display-map comparison"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "build/research/the-lab")
    args = parser.parse_args()
    root = args.root.resolve()
    image_path = root / "side2-targeted-02/ram-span-032.bin"
    image = image_path.read_bytes()
    assert sha(image) == RAM_SHA
    cpu = load(ROOT / "research/the-lab/inspect_side2.py", "span_original_cpu")
    runner = load(ROOT / "research/the-lab/mms_inventory.py", "span_cpu_runner")
    inputs = prepared_inputs(image)
    result = {"script_sha256": sha(Path(__file__).read_bytes()),
              "native_ram_path": str(image_path), "native_ram_sha256": sha(image),
              "pointer_plane": pointer_proof(image, cpu.Cpu, runner.execute),
              "prepared_inputs": inputs,
              "pose_area_ranking": area_ranking(image, inputs),
              "native_poses": native_pose_proof(image, inputs, root / "side2-targeted-02/ram-span-update074.bin"),
              "run_cpu": run_cpu_proof(image, inputs["run_packets"], cpu.Cpu, runner.execute)}
    output = root / "span-plane-analysis"
    output.mkdir(exist_ok=True)
    (output / "plane.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"pass": True, "logical_display": [192, 147],
                      "physical_display": [384, 294],
                      "prepared_triangle_poses": inputs["triangle_poses"],
                      "prepared_run_poses": inputs["run_poses"],
                      "run_max_local_y": inputs["run_max_local_y_by_half"],
                      "run_cpu_instructions": result["run_cpu"]["original_instructions"]}, indent=2))


if __name__ == "__main__":
    main()
