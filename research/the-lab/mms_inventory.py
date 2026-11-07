#!/usr/bin/env python3
"""Audit the native speech-balloon vector stage without running VICE.

The original release's decoded file22 supplies projected edge records. Compare
their unchanged native bytes, execute original RAM-only edge/generator/fill
routines in py65, and compare independent marker/prefix arithmetic. Disk, VIC,
IRQ and wall-clock behavior belong to the separate native capture.
"""

import argparse
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
NATIVE_SHA = "d8aac0f083581c4c616d9c85fd2f3d4b12107e9ec2942dd1b7ffc19136150bbc"
STREAM_START, STREAM_END = 0x9026, 0xC34C
MARKERS, MARKER_BYTES = 0xC800, 24 * 192
FILL_START, FILL_END = 0x7A46, 0x8346


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class TraceRam:
    def __init__(self, blob):
        self.data = bytearray(blob)
        self.pc = 0
        self.writes = []

    def __getitem__(self, address):
        return self.data[address]

    def __setitem__(self, address, value):
        self.data[address] = value
        self.writes.append((self.pc, address, value))


def execute(cpu_class, image, entry, registers=None, limit=100000):
    ram = TraceRam(image)
    # These isolated APIs are called in all-RAM context by the native program.
    ram.data[0:2] = bytes((0x2F, 0x34))
    cpu = cpu_class(memory=ram, pc=entry)
    cpu.p, cpu.sp = 0x20, 255
    for key, value in (registers or {}).items():
        setattr(cpu, key, value)
    cpu.stPushWord(0x1FFE)
    ram.writes.clear()
    instructions = 0
    while cpu.pc != 0x1FFF:
        assert instructions < limit, f"Instruction limit at ${cpu.pc:04x}"
        assert cpu.instruct[ram.data[cpu.pc]].__name__ != "inst_not_implemented"
        ram.pc = cpu.pc
        cpu.step()
        instructions += 1
    return ram, instructions


def frames_from_stream(image, start=STREAM_START, end=STREAM_END, expected_count=56):
    frames, cursor = [], start
    while cursor < end:
        address, records = cursor, []
        while image[cursor] != 255:
            assert cursor + 6 <= end
            record = bytes(image[cursor:cursor + 6])
            assert 0 <= (record[0] & 127) < (record[1] & 127) < 96
            assert record[4] < 192
            records.append(record)
            cursor += 6
        cursor += 1
        if not records:
            break
        frames.append((address, records))
    assert cursor == end and len(frames) == expected_count
    return frames


def other_assets(decoded):
    specifications = [(21, 0x8D32, 0x98B3, 64), (21, 0x98B3, 0x9AF8, 4),
                      (21, 0x9AF8, 0xBEFD, 64), (23, 0x8D02, 0xC327, 48)]
    result = []
    for number, start, end, count in specifications:
        image = (decoded / f"{number:02}.ram.bin").read_bytes()
        frames = frames_from_stream(image, start, end, count)
        result.append({"file": number, "range": [start, end], "frames": len(frames),
                       "records": sum(len(es) for _, es in frames),
                       "minimum_records": min(len(es) for _, es in frames),
                       "maximum_records": max(len(es) for _, es in frames),
                       "sha256": sha(image[start:end])})
    image21 = (decoded / "21.ram.bin").read_bytes()
    assert image21[0x8CB9:0x8CC5] == bytes((0, 1, 14, 4, 32, 14, 15, 23, 32, 63, 255, 255))
    return {"streams": result,
            "exact_user_speech_lead": {"file": 21, "inline_address": 0x8CB9,
                                        "text": "AND NOW ?",
                                        "call_before_inline": 0x8CB6,
                                        "edge_stream_selected": 0x9AF8},
            "native_routes": {"file21_call": 0x2109, "file22_call": 0x2118,
                               "file23_call": 0x2127},
            "file21_entry_first24": image21[0x8C00:0x8C18].hex(" "),
            "file23_entry_first24": (decoded / "23.ram.bin").read_bytes()[0x8C00:0x8C18].hex(" "),
            "in_place_tail_note": "File23 stream uses7 bytes already in the packed tail after last observed depacker store; packed logical endC327, observed stores endC320"}


def marker_reference(image, records, offset_x=0, offset_y=0):
    """Integer ADC-chain oracle; no code/table-derived slope raster sequence.

    The release supplies unsigned 16-bit slope bytes. Keep the high-byte carry
    into the next low-byte addition, as the original kernel does. This matters
    for negative slopes; silently replacing it with ordinary signed16 addition
    changes their samples.
    """
    markers = bytearray(MARKER_BYTES)
    samples = 0
    for record in records:
        left = image[0x8B34 + (record[0] & 127)] + offset_x
        right = image[0x8B34 + (record[1] & 127)] + offset_x
        row = image[0x8A74 + record[4]] + offset_y
        fraction, carry = 0, 0
        code = 2 * (record[0] >> 7) + (record[1] >> 7)
        for x in range(left, right):
            assert 0 <= x < 96 and 0 <= row < 192
            markers[(x // 4) * 192 + row] ^= code << (6 - 2 * (x % 4))
            samples += 1
            total = fraction + record[2] + carry
            fraction, carry = total & 255, total >> 8
            total = row + record[3] + carry
            row, carry = total & 255, total >> 8
    return markers, samples


def generator_proof(cpu_class, decoded, native):
    ram, instructions = execute(cpu_class, decoded, 0x8FE8)
    wanted = bytearray()
    for bank in (0xE000, 0x4000):
        for row in range(192):
            address = bank + 0x40 + (row // 8) * 320 + row % 8
            wanted.extend((0x51, 0x45, 0x9D, address & 255, address >> 8, 0xC8))
    assert ram.data[FILL_START:FILL_END] == wanted
    differences = [(address, ram.data[address], native[address])
                   for address in range(FILL_START, FILL_END)
                   if ram.data[address] != native[address]]
    assert differences == []
    return {"entry": 0x8FE8, "original_instructions": instructions,
            "generated_range": [FILL_START, FILL_END], "cells": 384,
            "cell_bytes": "51 45 9D lo hi C8",
            "cell_instructions": "EOR ($45),Y / STA absolute,X / INY",
            "banks": [0xE000, 0x4000], "rows_per_bank": 192,
            "destination_formula": "bank+0x40+(row//8)*320+(row%8)+X",
            "native_differences": differences,
            "native_difference_meaning": "Complete pass restored the temporary endpoint RTS; every generated byte matches",
            "pass": True}


def edge_proof(cpu_class, native, frames):
    results = []
    for index, (address, records) in enumerate(frames):
        image = bytearray(native)
        image[0xC380:0xDA00] = bytes(0x1680)
        image[0x3E:0x40] = address.to_bytes(2, "little")
        image[0x44] = 0
        image[0x51:0x53] = bytes(2)
        image[0x53:0x56] = bytes((0x60, 0, 0xC0))
        ram, instructions = execute(cpu_class, image, 0x2287, {"y": 0}, 500000)
        wanted, samples = marker_reference(native, records)
        assert ram.data[MARKERS:MARKERS + MARKER_BYTES] == wanted, index
        results.append({"frame": index, "address": address, "edges": len(records),
                        "samples": samples, "original_instructions": instructions,
                        "markers_sha256": sha(wanted)})
    return {"pass": True, "entry": 0x2287, "frames": len(results),
            "original_instructions": sum(x["original_instructions"] for x in results),
            "sampled_x_positions": sum(x["samples"] for x in results),
            "scale_state": native[0x50], "translation": [0, 0],
            "scope": "All56 released edge frames at the captured scale tables, zero translation; marker bytes only, not color attributes or complete frame timing",
            "frames_checked": results}


def completed_native_proof(cpu_class, native, frames):
    pointer = int.from_bytes(native[0x3E:0x40], "little")
    index, (_, records) = next((i, frame) for i, frame in enumerate(frames) if frame[0] == pointer)
    markers, samples = marker_reference(native, records, native[0x51], native[0x52])
    assert native[MARKERS:MARKERS + MARKER_BYTES] == markers
    bank = 0xE000 if native[0x43] else 0x4000
    entry = 0x260B if native[0x43] else 0x2662
    ram, instructions = execute(cpu_class, native, entry)
    stores = [(pc, address, value) for pc, address, value in ram.writes
              if FILL_START <= pc < FILL_END]
    assert len(stores) == 3040
    for _, address, value in stores:
        offset = address - bank - 0x40
        row, column = (offset // 320) * 8 + offset % 8, (offset % 320) // 8
        assert 0 <= row < 192 and 0 <= column < 24
        wanted = 0
        for y in range(row + 1):
            wanted ^= markers[column * 192 + y]
        assert value == wanted == native[address]
    return {"pass": True, "input_frame": index, "input_pointer": pointer,
            "commands": len(records), "sampled_x_positions": samples,
            "native_marker_bytes_compared": len(markers),
            "original_fill_entry": entry, "original_instructions": instructions,
            "native_bitmap_stores_compared": len(stores), "render_bank": bank,
            "column_store_counts": dict(sorted(Counter((a - bank - 0x40) % 320 // 8
                                                       for _, a, _ in stores).items())),
            "scope": "Complete captured backbuffer pass; all actual bitmap stores compared, untouched scene background outside dirty ranges excluded by the original write trace"}


def listings(output, utility, native, original20):
    ranges = [("mms-frame-consumer", native, 0x21BD, 0x2287),
              ("mms-edge-and-color-consumer", native, 0x2287, 0x2514),
              ("mms-erase-edges", native, 0x2514, 0x259F),
              ("mms-bitmap-fill-wrapper", native, 0x260B, 0x26B9),
              ("mms-example-edge-kernel", native, 0x6F66, 0x6FA6),
              ("mms-example-color-propagation", native, 0x6A74, 0x6AE6),
              ("mms-original-generator", original20, 0x8FE8, 0x903B)]
    for name, image, start, end in ranges:
        rows, pc = [], start
        while pc < end:
            item = utility.decode(image, pc)
            rows.append(f"{pc:04x}: {item['bytes']:<8} {item['mnemonic']} {item['text']}")
            pc = item["next"]
        (output / (name + ".asm")).write_text("\n".join(rows) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "build/research/the-lab")
    args = parser.parse_args()
    root = args.root.resolve()
    output = root / "mms-analysis"
    output.mkdir(exist_ok=True)
    native_path = root / "side2-live-01/ram-mms-frame-complete.bin"
    native = native_path.read_bytes()
    assert len(native) == 65536 and sha(native) == NATIVE_SHA
    decoded = root / "side2-analysis/depacked"
    original20 = (decoded / "20.ram.bin").read_bytes()
    original22 = (decoded / "22.ram.bin").read_bytes()
    assert native[STREAM_START:STREAM_END] == original22[STREAM_START:STREAM_END]
    frames = frames_from_stream(original22)
    helper = load_module(ROOT / "research/the-lab/inspect_side2.py", "the_lab_cpu")
    utility = load_module(ROOT / "research/tower-power/static_loader.py", "nmos_decoder")
    comparisons = []
    for number in range(25):
        image = (decoded / f"{number:02}.ram.bin").read_bytes()
        mask = (decoded / f"{number:02}.written.bin").read_bytes()
        addresses = [i for i, value in enumerate(mask) if value]
        matches = sum(native[i] == image[i] for i in addresses)
        comparisons.append({"file": number, "output_bytes": len(addresses), "matching": matches})
    result = {"script_sha256": sha(Path(__file__).read_bytes()),
              "native_path": str(native_path), "native_sha256": sha(native),
              "original20_snapshot_sha256": sha(original20),
              "original22_snapshot_sha256": sha(original22),
              "original_cpu_scope": "Flat RAM NMOS6502 APIs, no VICE/drive/VIC/IRQ emulation",
              "payload_comparisons": comparisons,
              "stream": {"range": [STREAM_START, STREAM_END], "bytes": STREAM_END - STREAM_START,
                         "sha256": sha(original22[STREAM_START:STREAM_END]),
                         "unchanged_in_native": True, "frames": len(frames),
                         "records": sum(len(es) for _, es in frames),
                         "minimum_records": min(len(es) for _, es in frames),
                         "maximum_records": max(len(es) for _, es in frames),
                         "record_format": "x0/codeBit1,x1/codeBit0,slopeLo,slopeHi,yStart,attributeStyle/paletteIndex",
                         "frame_terminator": 255, "stream_terminator": "Empty FF frame after last frame"},
              "runtime_palette": list(native[0x9016:0x9026]),
              "other_asset_streams": other_assets(decoded),
              "generator": generator_proof(helper.Cpu, original20, native),
              "all_frame_markers": edge_proof(helper.Cpu, native, frames),
              "completed_native_frame": completed_native_proof(helper.Cpu, native, frames)}
    listings(output, utility, native, original20)
    (output / "inventory.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"pass": True, "stream": result["stream"],
                      "generator_instructions": result["generator"]["original_instructions"],
                      "edge_instructions": result["all_frame_markers"]["original_instructions"],
                      "completed_native_frame": result["completed_native_frame"]}, indent=2))


if __name__ == "__main__":
    main()
