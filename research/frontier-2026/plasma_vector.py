#!/usr/bin/env python3
"""Check PlasmaVector's prepared poses, live boundaries and color-page routing."""

from collections import Counter
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "build/research/frontier-geometry-20261108"
OUTPUT = ROOT / "build/research/no-bounds/plasma-vector-analysis"
PART = INPUT / "NoBounds/Parts/PlasmaVector"
EXTRA = OUTPUT / "extra/NoBounds/Parts/PlasmaVector/Data"
COMMIT = "965807c511e2025b5c5e1ffb2a6235a4efd6ae5b"
OLD_INDEX = "875dd5dfa0fdedc8992d6c82ad3c043b3a64ccdebd307a6127e8cbe52de962d9"
EXTRA_INDEX = "d8de64648606334e2eb601412fbbc5a900b22c402e905ebbbc06a589ecf9b4e1"
ROW_LENGTHS = [32,31,31,30,30,30,29,27,25,25,26,26,25,25,25,26,24,23,25,25,26,26,26,36,37]
XMIN = [0,0,8,6,5,3,3,2,2,1,1,1,1,1,1,1,1,1,2,2,3,4,5,7]
XLEN = [0,0,8,12,14,18,18,20,20,22,22,22,22,22,22,22,22,22,20,20,19,15,13,9,0]
PATTERN = bytes.fromhex("3098ec47b8dc2003b8dc20033098ec47")
COL = bytes.fromhex("00060e030e060b050d050902080a0802")
COL2 = bytes([value for color in (0,6,4,14,3,14,4,6,0,11,12,15,7,15,11,0) for value in [color] * 4])
FACES = [(0,1,2,3), (4,5,6,7), (0,6,7,1), (2,4,5,3), (1,7,4,2), (0,3,5,6)]
FACE_COLORS = [3,3,2,2,1,1]
EDGES = [(0,1,0,2),(1,2,0,4),(2,3,0,3),(0,3,0,5),(0,6,2,5),(1,7,2,4),
         (2,4,3,4),(3,5,3,5),(4,5,1,3),(5,6,1,5),(6,7,1,2),(4,7,1,4)]


def check(value, message):
    if not value:
        raise AssertionError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    path = Path(path)
    raw = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(raw), "sha256": sha256(raw)}


def save_json(name, value):
    path = OUTPUT / name
    path.write_text(json.dumps(value, indent=2) + "\n")
    return artifact(path)


def provenance():
    tree = json.loads((INPUT / "tree.json").read_text())
    commit = json.loads((INPUT / "commit.json").read_text())
    check(commit["sha"] == COMMIT and tree["sha"] == commit["tree"]["sha"] and not tree["truncated"], "Wrong/incomplete source tree")
    entries = {entry["path"]: entry for entry in tree["tree"]}
    selected = []
    body_count = 0
    for base, index_name, expected in [(INPUT, "acquisitions.json", OLD_INDEX), (OUTPUT, "extra-acquisitions.json", EXTRA_INDEX)]:
        raw = (base / index_name).read_bytes()
        check(sha256(raw) == expected, "Changed acquisition index")
        for row in json.loads(raw):
            path = base / row["path"]
            body = path.read_bytes()
            check(row["status"] == 200 and len(body) == row["bytes"] and sha256(body) == row["sha256"], str(path))
            check(sha256((base / row["headers"]).read_bytes()) == row["headers_sha256"], row["headers"])
            body_count += 1
            git_path = row.get("git_path", row["path"])
            if "/PlasmaVector/" in git_path:
                oid = hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
                check(entries[git_path]["sha"] == oid, "Git blob mismatch: " + git_path)
                selected.append({"git_path": git_path, "git_blob": oid, **artifact(path)})
    check(len(selected) == 15, "Unexpected selected source/asset count")
    return {"commit": COMMIT, "tree": tree["sha"], "http_bodies_checked": body_count,
            "selected_git_blobs_checked": len(selected), "selected": selected,
            "old_acquisition_index": artifact(INPUT / "acquisitions.json"),
            "new_acquisition_index": artifact(OUTPUT / "extra-acquisitions.json")}


def unique_block(program, raw, expected_offset, label):
    first = program.find(raw)
    check(first == expected_offset and program.find(raw, first + 1) == -1, "Missing/nonunique PRG block: " + label)
    return {"name": label, "file_offset": first, "loaded_address": 0xe000 + first - 2,
            "bytes": len(raw), "sha256": sha256(raw)}


def bind_prg():
    path = INPUT / "NoBounds/Link/PlasmaVector/PlasmaVector.prg"
    program = path.read_bytes()
    check(program[:2] == b"\x00\xe0" and len(program) == 5865, "Wrong supplied PRG")
    sine = bytes(int(64 + 64 * math.sin((index + .5) * 2 * math.pi / 128)) & 255 for index in range(256))
    small = [int(8 * math.sin((index + .5) * 2 * math.pi / 64)) for index in range(256)]
    cosine = bytes(int(12 + 12 * math.cos((index + .5) * 2 * math.pi / 112)) for index in range(224))
    tables = sine + bytes(value & 255 for value in small) + cosine + COL + COL2 + bytes((0,64,128,192)) + bytes(ROW_LENGTHS) + PATTERN
    blocks = [unique_block(program, tables, 3330, "complete sine/color/row-length/pattern table block"),
              unique_block(program, bytes(XMIN + XLEN), 3254, "fill clip minima/lengths")]
    templates = {
        "LineBase": (2349, "a52065229005c8e521b0fb8520be00cebd01c045239d01c060"),
        "FillBase": (3244, "a9048d038060"), "DelBase": (3250, "8d01c060"),
        "ColorRAM cell": (2055, "b310bd00048d00d8c8"),
        "screen high-nibble routing cell": (2064, "b1108d5ca3c8"),
        "screen low-nibble/OR cell": (2070, "b310bd000405008d0060c8"),
    }
    for name, (offset, encoded) in templates.items():
        blocks.append(unique_block(program, bytes.fromhex(encoded), offset, name))
    return small, {"program": artifact(path), "bound_blocks": blocks,
                   "bytes_bound": sum(block["bytes"] for block in blocks),
                   "scope": "literal original templates/tables; generated runtime RAM not observed"}


def assets():
    mask = (EXTRA / "PlasmaMask.map").read_bytes()
    original = (EXTRA / "razorbackunbound.map").read_bytes()
    supplied = (EXTRA / "CombinedBitmap.map").read_bytes()
    check(len(mask) == len(original) == len(supplied) == 8000, "Bitmap asset length changed")
    direct = bytes((PATTERN[index & 15] & mask[index]) | value for index, value in enumerate(original))
    direct_differences = sum(a != b for a, b in zip(direct, supplied))
    check(direct_differences == 5434, "Disabled MkPattern hypothesis outcome changed")
    failed_prediction = OUTPUT / "rejected-combined-regeneration/predicted-from-disabled-MkPattern.bin"
    check(failed_prediction.read_bytes() == direct, "Retained rejected prediction changed")
    reversed_groups = b"".join(PATTERN[index:index + 4][::-1] for index in range(0,16,4))
    expected = bytes((reversed_groups[index & 15] & mask[index]) | value for index, value in enumerate(original))
    check(expected == supplied, "Four-byte reversed pattern does not reconstruct supplied bitmap")
    independent_mask_zero = sum(a != b for a, b, m in zip(original, supplied, mask) if m == 0)
    check(independent_mask_zero == 0, "Mask-zero artwork changed")
    ancillary_rows = (PART / "Data/RowLength.bin").read_bytes()
    crops = []
    for label, extension in [("Scr", "scr"), ("Col", "col")]:
        source = (EXTRA / ("razorbackunbound." + extension)).read_bytes()
        predicted = bytes(source[row * 40 + 22 + column] if 22 + column >= ancillary_rows[row] else 0
                          for row in range(25) for column in range(18))
        actual = OUTPUT / ("extra/NoBounds/Link/PlasmaVector/RazorbackUnbound" + label + ".bin")
        check(predicted == actual.read_bytes(), "Original picture attribute crop differs: " + label)
        crops.append(artifact(actual))
    return {"combined_bitmap_bytes_checked": 8000, "combined_sha256": sha256(supplied),
            "actual_pattern": reversed_groups.hex(), "template_pattern": PATTERN.hex(),
            "direct_disabled_template_differences": direct_differences,
            "retained_rejected_prediction": artifact(failed_prediction),
            "retained_rejected_observation": artifact(OUTPUT / "rejected-combined-regeneration/observations.json"),
            "mask_zero_artwork_differences": independent_mask_zero, "cropped_attributes": crops,
            "ancillary_RowLength_sum": sum(ancillary_rows), "runtime_RowLenTab_sum": sum(ROW_LENGTHS),
            "limit": "Group reversal matches assets; no claim about the historical generator/edit that introduced it"}


def color_layout():
    high, ora, cells = {}, {}, []
    offset = 0
    for row, length in enumerate(ROW_LENGTHS):
        for column in range(length):
            high[row, column] = 0x8000 + 8 * offset + row + 4
            ora[row, column] = 0xa356 + 10 * offset + row + 6
            cells.append({"row": row, "column": column, "color_high_operand": high[row, column],
                          "screen_high_index_operand": ora[row, column],
                          "ColorRAM": 0xd800 + 40 * row + column, "screen": 0x6000 + 40 * row + column})
            offset += 1
    code_images = []
    for layer, (start, stride) in enumerate(((0x8000,8),(0x95b9,5),(0xa356,10))):
        code = bytearray()
        for row, length in enumerate(ROW_LENGTHS):
            for column in range(length):
                pair = 0x10 + 2 * column
                if layer == 0:
                    dest = 0xd800 + 40 * row + column
                    code.extend((0xb3,pair,0xbd,0,4,0x8d,dest & 255,dest >> 8))
                elif layer == 1:
                    dest = ora[row,column]
                    code.extend((0xb1,pair,0x8d,dest & 255,dest >> 8))
                else:
                    dest = 0x6000 + 40 * row + column
                    code.extend((0xb3,pair,0xbd,0,4,5,0,0x8d,dest & 255,dest >> 8))
            code.append(0xc8 if row < 24 else 0x60)
        check(len(code) == 691 * stride + 25, "Source-generated kernel size changed")
        path = OUTPUT / ("predicted-layer-" + str(layer + 1) + ".bin")
        path.write_bytes(code)
        code_images.append({"layer": layer + 1, "loaded_start": start, "reserved_gap_to_next": stride,
                            "scope": "source-defined prediction, not captured generated RAM", **artifact(path)})
    fill, clear, fill_cells = bytearray(), bytearray(), []
    for row in range(23):
        table_row = 24 - row
        if not XLEN[table_row]:
            continue
        first = XMIN[table_row]
        for column in range(first, first + XLEN[table_row] + 1):
            target = high[row,column]
            marker = 0xc000 + len(fill) + 1
            fill.extend((0xa9 if column == first else 0x49, 4 if column == first else 0,
                         0x8d, target & 255, target >> 8))
            clear.extend((0x8d if column == first else 0x8e, marker & 255, marker >> 8))
            fill_cells.append({"row": row, "column": column, "marker": marker,
                               "target": target, "row_start": column == first})
    clear.append(0x60)
    check(len(fill_cells) == 426 and len(fill) == 2130 and len(clear) == 1279, "Generated fill/clear size changed")
    path = OUTPUT / "predicted-fill-clear.bin"
    path.write_bytes(fill + clear)
    layout = save_json("generated-layout.json", {"color_cells": cells, "fill_cells": fill_cells})
    return fill_cells, {"color_cells": len(cells), "fill_cells": len(fill_cells), "fill_rows": 22,
                        "row_lengths": ROW_LENGTHS, "generated_color_kernels": code_images,
                        "fill_start": 0xc000, "clear_fallthrough": 0xc852,
                        "fill_bytes": len(fill), "clear_bytes": len(clear),
                        "fill_clear_prediction": artifact(path), "layout": layout,
                        "unknown_line_cell_indices": [23,24],
                        "unknown_line_scope": "Unused final chain operand cells depend on uninitialized TmpLnTab slots; no values invented"}


def crossing(first, last, formula=True, unbiased=False):
    x0, y0 = first
    x1, y1 = last
    if x0 == x1:
        return []
    if x0 > x1:
        x0, x1, y0, y1 = x1, x0, y1, y0
    width, height = x1 - x0, abs(y1 - y0)
    sign = 1 if y1 >= y0 else -1
    if formula:
        return [(row, y0 + sign * (((row - x0 + 1) * height - (0 if unbiased else height // 2) + width - 1) // width))
                for row in range(x0,x1)]
    error, column, result = (~(height // 2)) & 255, y0, []
    for row in range(x0,x1):
        value = error + height
        carry, error = value >= 256, value & 255
        if carry:
            while True:
                column += sign
                value = error - width
                carry, error = value >= 0, value & 255
                if not carry:
                    break
        result.append((row,column))
    return result


def prefix(markers):
    result = []
    for row in markers:
        accumulator = 0
        for value in row:
            accumulator ^= value
            result.append(accumulator)
        check(accumulator == 0, "Boundary row fails to close")
    return result


def geometry(fill_cells):
    data = (PART / "Data/Cube.bin").read_bytes()
    visibility = (PART / "Data/FaceVis.bin").read_bytes()
    check(len(data) == 4096 and len(visibility) == 256, "Pose/visibility asset size changed")
    coverage, markers_out, controls = bytearray(), bytearray(), Counter()
    draws = samples = skipped = overlap = 0
    face_count = false_area_bits = wrong_area_poses = 0
    seed = [4 if cell["row_start"] else 0 for cell in fill_cells]
    for phase in range(256):
        points = [(data[256 * vertex + phase],data[256 * (8 + vertex) + phase]) for vertex in range(8)]
        colors = [color if visibility[phase] & (1 << face) else 0 for face,color in enumerate(FACE_COLORS)]
        markers = [[0] * 25 for _ in range(25)]
        wrong_or = [[0] * 25 for _ in range(25)]
        wrong_bias = [[0] * 25 for _ in range(25)]
        for a,b,first_face,last_face in EDGES:
            color = colors[first_face] ^ colors[last_face]
            if not color:
                continue
            actual = crossing(points[a],points[b],False)
            check(actual == crossing(points[a],points[b]), "DDA/formula crossing differs")
            draws += bool(actual)
            skipped += not actual
            samples += len(actual)
            for row,column in actual:
                table_row = 24 - row
                check(1 <= row <= 22 and XMIN[table_row] <= column <= XMIN[table_row] + XLEN[table_row], "A marker escapes the fixed fill footprint")
                markers[row][column] ^= color
                wrong_or[row][column] |= color
            for row,column in crossing(points[a],points[b],unbiased=True):
                wrong_bias[row][column] ^= color
        actual_image = prefix(markers)
        expected, owners = [0] * 625, [None] * 625
        area_mask = 0
        for face,vertices in enumerate(FACES):
            polygon = [points[vertex] for vertex in vertices]
            area = sum(a[0] * b[1] - b[0] * a[1] for a,b in zip(polygon,polygon[1:] + polygon[:1]))
            shown_by_area = area > 0 if face == 1 else area < 0
            if shown_by_area:
                area_mask |= 1 << face
            if not colors[face]:
                continue
            face_count += 1
            check(shown_by_area, "A prepared visible face has inconsistent/zero projected area")
            local = [[0] * 25 for _ in range(25)]
            for a,b in zip(vertices,vertices[1:] + vertices[:1]):
                for row,column in crossing(points[a],points[b]):
                    local[row][column] ^= 1
            for index,value in enumerate(prefix(local)):
                if value:
                    overlap += owners[index] is not None
                    owners[index] = face
                    expected[index] = colors[face]
        false_area_bits += (area_mask ^ visibility[phase]).bit_count()
        wrong_area_poses += area_mask != visibility[phase]
        check(actual_image == expected, "Shared-edge fill differs from opaque face assignment")
        # A clear may leave an invalid open prefix. Compare its literal XOR
        # result without treating closure as a prerequisite for the control.
        for name,alternative in [("OR_markers",wrong_or),("omit_half_dY_bias",wrong_bias)]:
            flat = []
            for row in alternative:
                value = 0
                for marker in row:
                    value ^= marker
                    flat.append(value)
            controls[name] += sum(a != b for a,b in zip(flat,expected))
        operands = list(seed)
        for index,cell in enumerate(fill_cells):
            operands[index] ^= markers[cell["row"]][cell["column"]]
        accumulator = 0
        for index,cell in enumerate(fill_cells):
            accumulator = operands[index] if cell["row_start"] else accumulator ^ operands[index]
            check(accumulator == 4 ^ expected[cell["row"] * 25 + cell["column"]], "Generated page selection differs")
        check(accumulator == 4, "Clear's retained A is not the outside page")
        for index,cell in enumerate(fill_cells):
            operands[index] = accumulator if cell["row_start"] else 0
        check(operands == seed, "Fused clear does not restore every operand")
        coverage.extend(expected)
        markers_out.extend(value for row in markers for value in row)
    check(overlap == 0 and draws == 1732 and skipped == 62 and samples == 12844, "Pose/coverage enumeration changed")
    check(sum(value != 0 for value in coverage) == 62242 and all(controls.values()), "Coverage or negative controls changed")
    (OUTPUT / "all-256-face-selectors.bin").write_bytes(coverage)
    (OUTPUT / "all-256-boundary-markers.bin").write_bytes(markers_out)
    return {"prepared_poses": 256, "prepared_visible_faces": face_count,
            "drawn_edges": draws, "zero_row_width_edges_skipped": skipped, "exact_boundary_markers": samples,
            "grid_cells_compared": len(coverage), "generated_page_stores_checked": 426 * 256,
            "nonzero_face_cells": 62242, "opaque_face_overlap_cells": overlap,
            "operand_reset_passes_checked": 256, "negative_control_cell_differences": dict(controls),
            "integer_area_mask_different_bits": false_area_bits, "integer_area_mask_different_poses": wrong_area_poses,
            "area_limit": "Prepared visibility is accepted input; projected integer area alone does not regenerate its hidden bits",
            "selector_images": artifact(OUTPUT / "all-256-face-selectors.bin"),
            "marker_images": artifact(OUTPUT / "all-256-boundary-markers.bin")}


def warped_pointers(small):
    deltas = [0xc0 + small[index] - small[index - 1] for index in range(256)]
    check(deltas[0] == 0xc0 and set(deltas) == {191,192,193}, "Warp delta domain changed")
    compared, minimum, maximum, flat_differences = 0, 65536, 0, 0
    for phase in range(128):
        for start in range(24):
            address = 0x2000 + 64 * start
            for column in range(37):
                reference = 0x2000 + 64 * (start + column) - (small[(phase + column - 1) & 255] - small[(phase - 1) & 255])
                check(address == reference, "AXS warp differs from telescoping sine formula")
                minimum, maximum = min(minimum,address), max(maximum,address)
                flat_differences += address != 0x2000 + 64 * (start + column)
                compared += 1
                immediate = deltas[phase + column]
                low, high = address & 255, address >> 8
                carry = low >= immediate
                low = (low - immediate) & 255
                high += carry
                address = 256 * high + low
    check(0x2000 <= minimum and maximum + 61 < 0x3000 and flat_differences > 0, "Runtime texture pointer domain escaped")
    texture = (PART / "Data/Pattern80-BF.bin").read_bytes()
    check(len(texture) == 4096 and min(texture) == 128 and max(texture) == 191, "Plasma map's palette-index domain changed")
    return {"horizontal_phases": 128, "starting_columns": 24, "source_pointers_checked": compared,
            "minimum_address": minimum, "maximum_pointer_address": maximum,
            "maximum_pointer_plus_61": maximum + 61, "lookup_map": artifact(PART / "Data/Pattern80-BF.bin"),
            "map_index_range": [128,191], "AXS_immediates": sorted(set(deltas)),
            "flat_unwarped_pointer_differences": flat_differences,
            "scope": "source-defined pointer recurrence and domain; not a native sampler trace or measured plasma output"}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    pins = provenance()
    small, program = bind_prg()
    asset_result = assets()
    fill_cells, layout = color_layout()
    geometry_result = geometry(fill_cells)
    pointers = warped_pointers(small)
    source = Path(__file__).read_bytes()
    receipt = {"pass": True, "provenance": pins, "program": program, "assets": asset_result,
               "generated_layout": layout, "geometry": geometry_result, "warped_plasma_pointers": pointers,
               "limits": ["256 projected poses and visibility bytes are prepared input; host 3D producer not recovered",
                          "Only literal template/table PRG domains match; predicted generated RAM has no native binding",
                          "CombinedBitmap matches a four-byte-group-reversed pattern, not the disabled template formula",
                          "No original disk, CPU, emulator, live process, generated display scanout or timing proof"],
               "producer": {"path": str(Path(__file__).relative_to(ROOT)), "bytes": len(source), "sha256": sha256(source)}}
    result = save_json("plasma-vector-proof.json",receipt)
    print(json.dumps({"pass": True, "receipt": result, "poses": 256,
                      "face_cells": geometry_result["grid_cells_compared"],
                      "page_stores": geometry_result["generated_page_stores_checked"],
                      "source_pointer_cases": pointers["source_pointers_checked"]},indent=2))


if __name__ == "__main__":
    main()
