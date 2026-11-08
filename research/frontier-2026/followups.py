#!/usr/bin/env python3
"""Check retained Star Wars scroller source/assets without running downloaded code."""

import ast
from collections import Counter
import hashlib
import itertools
import json
import math
from pathlib import Path
import re

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "build/research/frontier-followups-20261108"
COMMIT = "965807c511e2025b5c5e1ffb2a6235a4efd6ae5b"
INDEX_SHA256 = "578c9a257fb33fa4a814ed2b6ab87ac09380f6d38c12bcd7d600d00a858958c6"
GIT_PATHS = {
    "no-bounds-starwars.cpp": "NoBounds/Parts/StarWars/StarWars.cpp",
    "no-bounds-starwars.asm": "NoBounds/Parts/StarWars/StarWars.asm",
    "no-bounds-starwars.sls": "NoBounds/Parts/StarWars/StarWars.sls",
    "no-bounds-font.bmp": "NoBounds/Parts/StarWars/Data/Raistlin-16x16.bmp",
    "no-bounds-font.map": "NoBounds/Parts/StarWars/Data/Raistlin-16x16.map",
    "no-bounds-font.bin": "NoBounds/Link/StarWars/SW-RemappedFont.bin",
    "no-bounds-scroll.bin": "NoBounds/Link/StarWars/SW-ScrollText.bin",
    "no-bounds-starwars.prg": "NoBounds/Link/StarWars/StarWars.prg",
    "dive-starwars.cpp": "TheDive/VisualStudioProject/C64-RaistllinCodeGenerator/Source/DemoParts/StarWars.cpp",
    "dive-starwars.asm": "TheDive/Build/Parts/StarWars/ASM/StarWars.asm",
    "dive-font.bmp": "TheDive/Build/Parts/StarWars/Data/Ksubi-16x16.bmp",
    "dive-font.map": "TheDive/Build/Parts/StarWars/Data/Ksubi-16x16.map",
    "dive-starwars-layout.txt": "TheDive/Build/Parts/StarWars/SpindleLayout-StarWars.txt",
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def check(condition, explanation):
    if not condition:
        raise AssertionError(explanation)


def identities():
    raw = (ARCHIVE / "acquisitions.json").read_bytes()
    check(sha256(raw) == INDEX_SHA256, "Acquisition index changed")
    records = json.loads(raw)
    for row in records:
        body = (ARCHIVE / row["path"]).read_bytes()
        check(len(body) == row["bytes"] and sha256(body) == row["sha256"], row["path"])
        check(sha256((ARCHIVE / row["headers"]).read_bytes()) == row["headers_sha256"], row["headers"])
        check(row["status"] == 200, "Non-successful body in the acquisition index")
    commit = json.loads((ARCHIVE / "commit.json").read_text())
    tree = json.loads((ARCHIVE / "tree.json").read_text())
    check(commit["sha"] == COMMIT, "Wrong commit")
    check(tree["sha"] == commit["tree"]["sha"] and not tree["truncated"], "Incomplete or wrong tree")
    paths = {row["path"]: row for row in tree["tree"]}
    blobs = []
    for local, remote in GIT_PATHS.items():
        body = (ARCHIVE / local).read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
        check(actual == paths[remote]["sha"], "Git blob mismatch: " + remote)
        blobs.append({"path": remote, "bytes": len(body), "git_blob": actual, "sha256": sha256(body)})
    return {"http_bodies_checked": len(records), "index_sha256": INDEX_SHA256,
            "commit": COMMIT, "tree": tree["sha"], "git_blobs_checked": blobs}


def font_rows(prefix):
    """Read visible 16-pixel rows; compare their independently repacked CharPad map."""
    with Image.open(ARCHIVE / (prefix + "-font.bmp")) as image:
        image = image.convert("RGB")
        check(image.size == (512, 16), "Unexpected font geometry")
        check({color for _, color in image.getcolors()} == {(0, 0, 0), (255, 255, 255)}, "Not a two-color font")
        rows = [[sum((image.getpixel((16 * char + x, y)) == (255, 255, 255)) << (15 - x)
                     for x in range(16)) for y in range(16)] for char in range(32)]
    packed = bytes((rows[char][8 * half_y + y] >> (8 * (1 - half_x))) & 255
                   for half_y in range(2) for char in range(32)
                   for half_x in range(2) for y in range(8))
    check(packed == (ARCHIVE / (prefix + "-font.map")).read_bytes(), "BMP/MAP disagreement")
    return rows


def no_bounds_text():
    source = (ARCHIVE / "no-bounds-starwars.cpp").read_text()
    start = source.index("unsigned char ScrollText[]")
    # Stop before the alternate, commented-out text. literal_eval reads only
    # string constants; no downloaded source is imported, compiled or executed.
    literals = re.findall(r'"([^"\n]*)"', source[start:source.index("/*", start)])
    text = bytearray("".join(ast.literal_eval('"' + part + '"') for part in literals).encode("latin1"))
    check(len(text) == 497 and text[-1] == 255, "Unexpected bounded scroll text")
    for first in range(0, 496, 16):
        line = text[first:first + 16]
        if all(char == 32 for char in line):
            text[first:first + 16] = bytes((128,)) * 16
        else:
            text[first:first + 16] = bytes({46: 28, 33: 29, 45: 27, 44: 30}.get(
                char, char & 31 if (char & 31) <= 26 else 0) for char in line)
    used = sorted({char for char in text[:-1] if char < 64})
    dense = {char: index for index, char in enumerate(used)}
    encoded = bytes(dense[char] if char < 64 else char for char in text)
    check(encoded == (ARCHIVE / "no-bounds-scroll.bin").read_bytes(), "Published text mismatch")
    return used, encoded


def horizontal_samples():
    """The source's fixed waisted plane, with -1 outside its horizontal span."""
    result = [[-1] * 256 for _ in range(120)]
    for y in range(120):
        half_width = min(256, (0.5 + 0.5 * math.sin(y * math.pi / 120)) * 257) / 2
        for x in range(math.ceil(half_width)):
            result[119 - y][128 + x] = math.floor(128 + x / half_width * 127)
            result[119 - y][127 - x] = math.floor(127 - x / half_width * 127)
    return result


def tables_and_pixels(rows, used):
    unique_rows = []
    for char in used:
        for value in rows[char]:
            if value not in unique_rows:
                unique_rows.append(value)
    check(len(unique_rows) == 20, "Font-row dictionary changed")
    remapped = bytes(unique_rows.index(rows[char][y]) for y in range(16) for char in used)
    check(remapped == (ARCHIVE / "no-bounds-font.bin").read_bytes(), "Published remapped font mismatch")
    samples = horizontal_samples()
    byte_sets, addresses, packed, cells = [], [], bytearray(), []
    for y, line in enumerate(samples):
        for x_byte in range(32):
            groups = {}
            for bit in range(8):
                source_x = line[x_byte * 8 + bit]
                if source_x >= 0 and source_x % 16 not in (0, 15):
                    groups.setdefault(source_x // 16, []).append((bit, source_x % 16))
            check(len(groups) <= 2, "More than two text columns affect a target byte")
            cell = []
            for column, bits in groups.items():
                values = bytes(255 - sum(((value >> (15 - source_bit)) & 1) << (7 - bit)
                                        for bit, source_bit in bits) for value in unique_rows)
                if values not in byte_sets:
                    byte_sets.append(values)
                    if 256 - len(packed) % 256 < 24:
                        packed.extend(bytes(256 - len(packed) % 256))
                    addresses.append(len(packed))
                    # The source emits 24 slots. Only 20 are live; unfilled
                    # slots remain FF, rather than invented font patterns.
                    packed.extend(values + b"\xff" * 4)
                cell.append((column, byte_sets.index(values)))
            cells.append((y, x_byte, cell))
    check(len(byte_sets) == 295 and len(packed) == 7544, "Derived table count/size changed")
    program = (ARCHIVE / "no-bounds-starwars.prg").read_bytes()
    offset = program.find(packed)
    check(offset == 105 and program.find(packed, offset + 1) == -1, "Complete table block is not unique at the expected position")
    base = int.from_bytes(program[:2], "little")
    check(base == 0x2000, "Wrong PRG load address")
    low = bytes((0xfd00 + 15 * row) & 255 for row in range(16))
    high = bytes((0xfd00 + 15 * row) >> 8 for row in range(16))
    check(program[offset - 32:offset] == low + high, "Font-row pointer prefix differs")
    # Both outside source columns and the omitted boundary bits are zero in
    # every input glyph. Check that prerequisite directly, not by assumption.
    check(all(value & 0x8001 == 0 for char in rows for value in char), "An omitted glyph edge contains ink")
    checks = mismatches = or_control_errors = 0
    histogram = Counter()
    for y, x_byte, contributors in cells:
        histogram[len(contributors)] += 1
        for selection in itertools.product(range(20), repeat=len(contributors)):
            chosen = {column: unique_rows[row] for (column, _), row in zip(contributors, selection)}
            table_value = 255
            wrong_or = 0
            for (_, table), row in zip(contributors, selection):
                actual = program[offset + addresses[table] + row]
                table_value &= actual
                wrong_or |= actual
            # Independent direct sampler: visit target pixels, select their
            # source glyph row, and form the inverse bitmap byte from ink.
            ink = 0
            for bit in range(8):
                source_x = samples[y][8 * x_byte + bit]
                if source_x >= 0:
                    value = chosen.get(source_x // 16, 0)
                    ink |= ((value >> (15 - source_x % 16)) & 1) << (7 - bit)
            expected = ink ^ 255
            checks += 1
            mismatches += table_value != expected
            if len(contributors) == 2:
                or_control_errors += wrong_or != expected
    check(mismatches == 0 and or_control_errors > 0, "Pixel oracle or negative control failed")
    (ARCHIVE / "predicted-font-tables.bin").write_bytes(packed)
    # A source-level lazy copy is valid only when the old next row samples
    # exactly the same column/table function at the new frame's source index.
    virtual, total = [], 0.0
    for y in range(120):
        total += 0.5 + 1.2 * abs(60 - y) / 60
        virtual.append(math.floor(total))
    skipped = {0, 1, 3, 5, 8, 11, 14, 118, 116, 114, 111, 108, 105}
    by_position = {(y, xb): cell for y, xb, cell in cells}
    lazy, rejected = [], []
    for y, xb, cell in cells:
        if not cell or y in skipped or y == 119 or y + 1 in skipped or virtual[y + 1] - virtual[y] != 1:
            continue
        following = by_position[y + 1, xb]
        # This is the comparison emitted by the original generator. The
        # stronger independent check below also compares source columns.
        candidate = all(table == (following[index][1] if index < len(following) else 0)
                        for index, (_, table) in enumerate(cell))
        if candidate:
            if cell == following:
                lazy.append((y, xb))
            else:
                rejected.append((y, xb, cell, following))
    # Preserve real limitations in this source rather than weakening the
    # oracle: one comparison omits a second contributor; another matches an
    # unused zero-initialized FontMapping slot in an otherwise empty cell.
    check([(y, xb) for y, xb, _, _ in rejected] == [(79, 19), (92, 2)], "Lazy-copy exception set changed")
    exceptions = []
    for y, xb, first, following in rejected:
        columns = sorted({column for column, _ in first + following})
        differences, witness = 0, None
        for choice in itertools.product(range(20), repeat=len(columns)):
            selected = dict(zip(columns, choice))
            current_value, copied_value = 255, 255
            for column, table in first:
                current_value &= byte_sets[table][selected[column]]
            for column, table in following:
                copied_value &= byte_sets[table][selected[column]]
            if current_value != copied_value:
                differences += 1
                if witness is None:
                    witness = {"row_indices_by_column": selected, "direct": current_value, "copied": copied_value}
        def bitmap_address(row, column):
            return 0xe000 + (row // 8) * 320 + column * 8 + row % 8
        source_address = bitmap_address(y + 40, xb + 4)
        target_address = bitmap_address(y + 39, xb + 4)
        instruction = bytes((0xad, source_address & 255, source_address >> 8,
                             0x8d, target_address & 255, target_address >> 8))
        positions = [position for position in range(len(program)) if program.startswith(instruction, position)]
        expected_offset = {(79, 19): 24673, (92, 2): 27824}[y, xb]
        check(positions == [expected_offset] and differences > 0, "Lazy-copy byte witness or counterexample changed")
        exceptions.append({"generated_y": y, "generated_byte_x": xb, "first": first, "next": following,
                           "dictionary_combinations_checked": 20 ** len(columns),
                           "different_dictionary_combinations": differences, "counterexample": witness,
                           "prg_copy_file_offset": positions[0], "loaded_instruction_address": base + positions[0] - 2,
                           "instruction_hex": instruction.hex(), "source_address": source_address,
                           "target_address": target_address,
                           "scope": "source and literal PRG instructions; not observed execution or visible error"})
    return {"font_characters_used": used, "font_rows": len(unique_rows), "remapped_font_bytes_checked": len(remapped),
            "scroll_bytes_checked": 497, "generated_tables": len(byte_sets), "slots_per_table": 24,
            "live_slots_per_table": 20, "unused_slots_value": 255,
            "packed_table_bytes_checked": len(packed), "packed_table_sha256": sha256(packed),
            "prg_file_offset": offset, "loaded_table_address": base + offset - 2,
            "table_pointer_prefix_bytes_checked": 32, "target_byte_contributors": dict(sorted(histogram.items())),
            "byte_truth_cases_checked": checks, "byte_truth_mismatches": mismatches,
            "incorrect_or_composition_errors": or_control_errors,
            "lazy_copy_cells_checked": len(lazy), "lazy_copy_source_column_mismatches": len(rejected),
            "lazy_copy_exceptions": exceptions,
            "virtual_row_offsets": [value - virtual[0] for value in virtual],
            "skipped_rows": sorted(skipped),
            "actual_table_bases_allowing_live_index_page_cross": sum(
                ((base + offset - 2 + address) & 255) + 19 > 255 for address in addresses)}


def ring_contract(offsets):
    check(min(offsets) == 0 and max(offsets) < 255, "Virtual scroll span escapes one page")
    checks = 0
    for phase in range(256):
        write = (phase + offsets[-1] + 1) & 255
        check(all(write != ((phase + row) & 255) for row in offsets), "New tail overwrites a current sample")
        check(write == ((phase + 1 + offsets[-1]) & 255), "Tail is not the next frame's last sample")
        for row in offsets:
            check((phase + 1 + row) & 255 == ((phase + row) + 1) & 255, "Ring wrap disagrees")
            checks += 1
    return {"phase_values_checked": 256, "row_index_relations_checked": checks,
            "sample_span": [min(offsets), max(offsets)], "future_tail_overwrites_current_samples": 0,
            "scope": "uint8 indexing contract; not original instruction execution or buffer initialization"}


def main():
    provenance = identities()
    rows = font_rows("no-bounds")
    dive = font_rows("dive")
    used, _ = no_bounds_text()
    result = tables_and_pixels(rows, used)
    report = {"pass": True, "provenance": provenance, "no_bounds": result,
              "ring_contract": ring_contract(result["virtual_row_offsets"]),
              "the_dive_font": {"bmp_map_bytes_checked": 1024,
                                 "distinct_rows_across_all_32_input_glyphs": len({v for char in dive for v in char}),
                                 "scope": "all input glyphs; not the article's selected/reduced 28-row runtime alphabet"},
              "limits": ["source snapshot is not an original-disk source/build proof",
                         "no downloaded code, C64 instructions, native/VICE execution or timing measurements",
                         "pixel truth cases use independently selectable dictionary rows, not observed text state",
                         "lazy-copy checks retain two source-selected non-equivalent cells; no native visible-error claim",
                         "The Hat/Aloft algorithm source gaps remain open"],
              "producer": {"path": str(Path(__file__).relative_to(ROOT)),
                           "bytes": len(Path(__file__).read_bytes()), "sha256": sha256(Path(__file__).read_bytes())}}
    path = ARCHIVE / "followup-findings.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"pass": True, "receipt": str(path.relative_to(ROOT)),
                      "tables": result["generated_tables"], "packed_bytes": result["packed_table_bytes_checked"],
                      "truth_cases": result["byte_truth_cases_checked"], "lazy_cells": result["lazy_copy_cells_checked"],
                      "receipt_sha256": sha256(path.read_bytes())}, indent=2))


if __name__ == "__main__":
    main()
