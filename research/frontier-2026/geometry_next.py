#!/usr/bin/env python3
"""Verify retained SpriteFPP prepared strip data against its supplied C64 PRG."""

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "build/research/frontier-geometry-20261108"
PART = ARCHIVE / "NoBounds/Parts/SpriteFPP"
COMMIT = "965807c511e2025b5c5e1ffb2a6235a4efd6ae5b"
INDEX_SHA256 = "875dd5dfa0fdedc8992d6c82ad3c043b3a64ccdebd307a6127e8cbe52de962d9"
COLOR_TO_SELECTOR = {(0, 0, 0): 0, (187, 187, 187): 1, (119, 119, 119): 3, (51, 51, 51): 2}
SELECTOR_TO_COLOR = ((0, 0, 0), (187, 187, 187), (51, 51, 51), (119, 119, 119))


def check(value, message):
    if not value:
        raise AssertionError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def retained_inputs():
    index = (ARCHIVE / "acquisitions.json").read_bytes()
    check(sha256(index) == INDEX_SHA256, "Acquisition index changed")
    records = json.loads(index)
    commit = json.loads((ARCHIVE / "commit.json").read_text())
    tree = json.loads((ARCHIVE / "tree.json").read_text())
    check(commit["sha"] == COMMIT, "Wrong immutable commit")
    check(tree["sha"] == commit["tree"]["sha"] and not tree["truncated"], "Incomplete/wrong immutable tree")
    entries = {entry["path"]: entry for entry in tree["tree"]}
    blobs = []
    for row in records:
        body = (ARCHIVE / row["path"]).read_bytes()
        check(row["status"] == 200 and len(body) == row["bytes"] and sha256(body) == row["sha256"], row["path"])
        check(sha256((ARCHIVE / row["headers"]).read_bytes()) == row["headers_sha256"], row["headers"])
        if row["path"].startswith("NoBounds/"):
            oid = hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
            check(entries[row["path"]]["sha"] == oid, "Git blob identity: " + row["path"])
            blobs.append({"path": row["path"], "git_blob": oid, "bytes": len(body), "sha256": sha256(body)})
    return {"http_bodies_checked": len(records), "index_sha256": INDEX_SHA256,
            "commit": COMMIT, "tree": tree["sha"], "git_blobs": blobs}


def list_arguments(source, name):
    return [list(map(int, item.split(","))) for item in re.findall(re.escape(name) + r"\.add\(([-\d,]+)\)", source)]


def unpack_row(data):
    return [(value >> shift) & 3 for value in data for shift in (6, 4, 2, 0)]


def sprite_data(program, load):
    palette = (PART / "data/palette.asm").read_text()
    line_ids = [row[0] for row in list_arguments(palette, "PaletteLineIdList")]
    widths = [row[0] for row in list_arguments(palette, "PaletteWidthList")]
    check(len(line_ids) == len(widths) == 68, "Palette length changed")
    with Image.open(PART / "data/texture_gradient.png") as image:
        image = image.convert("RGB")
        check(image.size == (174, 4), "Texture size changed")
        colors = [image.getpixel((0, y)) for y in range(4)]
        check(all(image.getpixel((x, y)) == colors[y] for y in range(4) for x in range(174)), "Texture rows are not constant")
        check(set(colors) == set(COLOR_TO_SELECTOR), "Unexpected texture colors")
    atlas = bytearray(68 * 64)
    interval_rows = []
    bounds = []
    for index, (line_id, width) in enumerate(zip(line_ids, widths)):
        check(0 <= line_id < 4 and width in range(0, 191, 2), "Palette key escapes its checked domain")
        # Source-equivalent forward splat. No downloaded assembly is evaluated.
        pixels = [(0, 0, 0)] * 192
        if width:
            factor = width / 174
            padding = (192 - width) // 2
            for x in range(174):
                for repeat in range(math.ceil(factor)):
                    destination = padding + math.floor(x * factor + 0.5) + repeat
                    check(0 <= destination < 192, "Scale splat escaped its canvas")
                    pixels[destination] = colors[line_id]
        packed = bytes(sum(COLOR_TO_SELECTOR[pixels[8 * x + 2 * lane]] << (6 - 2 * lane)
                           for lane in range(4)) for x in range(24))
        atlas[64 * index + 3:64 * index + 27] = packed
        # Independent interval construction is valid specifically because the
        # original texture rows are constant. It does not replay each splat.
        if width:
            left = (192 - width) // 2
            last = left + math.floor(173 * width / 174 + 0.5) + math.ceil(width / 174) - 1
        else:
            left, last = 1, 0
        expected = [COLOR_TO_SELECTOR[colors[line_id]] if left <= 2 * x <= last else 0 for x in range(96)]
        check(unpack_row(packed) == expected, "Forward-splat row differs from the interval oracle")
        interval_rows.append(expected)
        bounds.append([left, last])
    actual = program[2 + 0x4000 - load:2 + 0x4000 - load + len(atlas)]
    check(actual == atlas, "Complete 68-slot sprite atlas differs from supplied PRG")
    wrong_offset = wrong_selectors = 0
    for index, expected in enumerate(interval_rows):
        slot = actual[index * 64:(index + 1) * 64]
        wrong_offset += sum(a != b for a, b in zip(unpack_row(slot[:24]), expected))
        swapped = [3 if value == 2 else 2 if value == 3 else value for value in unpack_row(slot[3:27])]
        wrong_selectors += sum(a != b for a, b in zip(swapped, expected))
    check(wrong_offset > 0 and wrong_selectors > 0, "Palette negative controls did not distinguish the layout")
    (ARCHIVE / "predicted-sprite-atlas.bin").write_bytes(atlas)
    return interval_rows, {"palette_entries": len(line_ids), "palette_keys": list(zip(line_ids, widths)),
                           "texture_size": [174, 4], "texture_rows_constant": True,
                           "sprite_slots": 68, "bytes_per_slot": 64, "first_data_byte_in_slot": 3,
                           "data_bytes_per_slot": 24, "packed_payload_bytes": 68 * 24,
                           "complete_atlas_bytes_checked": len(atlas), "loaded_atlas_address": 0x4000,
                           "atlas_sha256": sha256(atlas),
                           "independent_logical_row_samples_checked": 68 * 96,
                           "distinct_packed_rows": len({bytes(atlas[64 * i + 3:64 * i + 27]) for i in range(68)}),
                           "physical_interval_bounds": bounds,
                           "wrong_slot_offset_logical_mismatches": wrong_offset,
                           "swapped_10_11_selectors_logical_mismatches": wrong_selectors}


def frame_data(program, load, interval_rows):
    source = (PART / "data/frames_list.asm").read_text()
    frames = list_arguments(source, "LineIndexList")
    heights = [row[0] for row in list_arguments(source, "FramesHeightList")]
    check(len(frames) == len(heights) == 64 and {len(row) for row in frames} == {91}, "Prepared frame dimensions changed")
    check(min(min(row) for row in frames) == 0 and max(max(row) for row in frames) == 67, "Prepared palette range changed")
    packed = bytes(index for frame in frames for index in frame)
    offset = 2 + 0xab00 - load
    check(program[offset:offset + len(packed)] == packed, "All prepared frame rows differ from the PRG")
    check(program.find(packed) == offset and program.find(packed, offset + 1) == -1, "Frame block is not unique")
    addresses = [0xab00 + 91 * index for index in range(64)]
    tables = (bytes(address & 255 for address in addresses) + bytes(address >> 8 for address in addresses)
              + bytes(64) + bytes(91 - 2 * index for index in range(32)))
    pointer_offset = 2 + 0xc200 - load
    check(program[pointer_offset:pointer_offset + len(tables)] == tables, "Frame pointers/start/length tables differ")
    histogram = Counter()
    comparisons = 0
    sheet = Image.new("RGB", (4 * 192, 2 * 91))
    selected_frames = [0, 8, 16, 24, 32, 40, 48, 56]
    for frame_index, frame in enumerate(frames):
        image = Image.new("RGB", (192, 91)) if frame_index in selected_frames else None
        for y, palette_index in enumerate(frame):
            first = 2 + 0x4000 - load + 64 * palette_index + 3
            actual = unpack_row(program[first:first + 24])
            expected = interval_rows[palette_index]
            check(actual == expected, "Prepared frame differs from independent strip interval")
            comparisons += len(expected)
            histogram[palette_index] += 1
            if image is not None:
                for x, value in enumerate(actual):
                    image.putpixel((2 * x, y), SELECTOR_TO_COLOR[value])
                    image.putpixel((2 * x + 1, y), SELECTOR_TO_COLOR[value])
        if image is not None:
            slot = selected_frames.index(frame_index)
            sheet.paste(image, ((slot % 4) * 192, (slot // 4) * 91))
    sheet.save(ARCHIVE / "strip-sequence-contact.png")
    (ARCHIVE / "predicted-frame-lookup.bin").write_bytes(packed)
    return {"frames": len(frames), "fixed_rows_per_frame": 91, "lookup_bytes_checked": len(packed),
            "lookup_sha256": sha256(packed), "loaded_lookup_address": 0xab00,
            "frame_pointer_start_length_bytes_checked": len(tables), "loaded_pointer_address": 0xc200,
            "source_height_metadata_range": [min(heights), max(heights)],
            "source_height_metadata_used_as_address_stride": False,
            "prepared_logical_strip_samples_checked": comparisons,
            "palette_indices_used": len(histogram), "palette_use_counts": dict(sorted(histogram.items())),
            "preview": {"path": "strip-sequence-contact.png", "frames": selected_frames,
                        "scope": "prepared strip sequences in source gray values; not native scanout",
                        "sha256": sha256((ARCHIVE / "strip-sequence-contact.png").read_bytes())}}


def pointer_kernel(program, load):
    expected = bytearray()
    for row in range(133):
        address = 0x0700 + row
        expected.extend((0x8c, 0x17, 0xd0, 0xad, address & 255, address >> 8))
        for sprite in range(8):
            address = 0x43f8 + sprite
            expected.extend((0x8d, address & 255, address >> 8))
        expected.extend((0x8e, 0x17, 0xd0))
    offset = program.find(expected)
    check(offset == 30763 and program.find(expected, offset + 1) == -1, "Unrolled pointer kernel does not match uniquely")
    check(program[offset - 4:offset] == bytes((0xa0, 0xff, 0xa2, 0)), "Kernel's Y=FF/X=00 prefix differs")
    check(load + offset - 2 == 0x802a and len(expected) == 4389, "Kernel location or size changed")
    (ARCHIVE / "predicted-pointer-kernel.bin").write_bytes(expected)
    return {"cells": 133, "bytes_per_cell": 33, "matched_code_bytes": len(expected),
            "sha256": sha256(expected), "loaded_start": 0x802a, "register_prefix_bytes_checked": 4,
            "source_rows": [0x0700, 0x0784], "pointer_destinations": [0x43f8, 0x43ff],
            "schedule": "STY D017; LDA row; eight STA sprite pointers; STX D017",
            "scope": "literal generated bytes; no executed IRQ/DMA/timing proof"}


def main():
    inputs = retained_inputs()
    program = (PART / "SpriteFpp.prg").read_bytes()
    load = int.from_bytes(program[:2], "little")
    check(load == 0x0801 and len(program) == 48386, "Supplied PRG layout changed")
    rows, palette = sprite_data(program, load)
    frames = frame_data(program, load, rows)
    kernel = pointer_kernel(program, load)
    producer = Path(__file__).read_bytes()
    receipt = {"pass": True, "provenance": inputs, "program": {"bytes": len(program), "load": load,
               "sha256": sha256(program)}, "palette": palette, "frames": frames, "pointer_kernel": kernel,
               "unclaimed_acquisition": "PlasmaVector source/assets retained only as an independent next lead",
               "limits": ["source snapshot is not an original-disk or full source/build equivalence proof",
                          "Unity project and original assembler were not run; active export causality is unproved",
                          "matched frame/palette functions are prepared, not evidence of live C64 3D rotation",
                          "no original CPU, native/VICE, FPP MCBASE, DMA, whole-frame or timing proof"],
               "producer": {"path": str(Path(__file__).relative_to(ROOT)), "bytes": len(producer), "sha256": sha256(producer)}}
    output = ARCHIVE / "geometry-findings.json"
    output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"pass": True, "receipt": str(output.relative_to(ROOT)),
                      "matched_atlas_bytes": palette["complete_atlas_bytes_checked"],
                      "matched_frame_bytes": frames["lookup_bytes_checked"],
                      "prepared_strip_samples": frames["prepared_logical_strip_samples_checked"],
                      "matched_kernel_bytes": kernel["matched_code_bytes"],
                      "receipt_sha256": sha256(output.read_bytes())}, indent=2))


if __name__ == "__main__":
    main()
