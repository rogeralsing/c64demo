#!/usr/bin/env python3
"""Host-only BRR research. Does not assemble or run the C64 renderer.

Author HTML/code is cached only in ignored build/, never vendored. The line,
scene, topology and cycle models below are our own mathematical comparisons.
"""

import argparse
import ast
import bisect
import hashlib
import html
import json
import math
import re
from collections import Counter
from fractions import Fraction
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "article.html": (
        "https://www.quiss.org/boo/",
        "21c8010b0058bc6e3337288cab1c1efc3c8d6a54e3a9fc1a2455ba6158fa4da6",
    ),
    "bitreverse.html": (
        "https://www.quiss.org/boo/bitreverse.html",
        "6a7cf15d26afe2fd2686494051200c7d7165f83a85c239384cbab5c88995c458",
    ),
}
BASE_PROGRAM = "d5baf50b922f23ace12c829e28ef8a6796dd3431b334aff660409334a173c792"
VERTICES = [
    (0, -21, -34), (0, -21, 34), (0, 21, -34), (0, 21, 34),
    (-21, -34, 0), (-21, 34, 0), (21, -34, 0), (21, 34, 0),
    (-34, 0, -21), (-34, 0, 21), (34, 0, -21), (34, 0, 21),
]
FACES = [
    (0, 2, 10), (0, 4, 8), (0, 6, 4), (0, 8, 2), (0, 10, 6),
    (1, 3, 9), (1, 4, 6), (1, 6, 11), (1, 9, 4), (1, 11, 3),
    (2, 5, 7), (2, 7, 10), (2, 8, 5), (3, 5, 9), (3, 7, 5),
    (3, 11, 7), (4, 9, 8), (5, 8, 9), (6, 10, 11), (7, 11, 10),
]
COLORS = [1, 1, 2, 2, 3, 1, 1, 2, 2, 3, 1, 2, 3, 2, 3, 1, 3, 1, 1, 3]
REVERSE = [int(f"{x:08b}"[::-1], 2) for x in range(256)]
SINE = [math.floor(64 * math.sin(i * math.tau / 256) + 0.5) for i in range(256)]


def source_cache(directory, fetch):
    result = {}
    for name, (url, expected) in SOURCES.items():
        path = directory / name
        if fetch or not path.exists():
            path.write_bytes(urlopen(url, timeout=30).read())
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != expected:
            raise ValueError(f"Primary source changed: {url}: {digest}; review before updating pin")
        result[name] = {"url": url, "sha256": digest, "bytes": len(raw)}
    return result


def author_functions(directory):
    raw = (directory / "bitreverse.html").read_text()
    pre = re.search(r"<pre[^>]*>(.*?)</pre>", raw, re.S).group(1)
    code = html.unescape(re.sub(r"<[^>]+>", "", pre))
    # This ignored extraction is not an independently licensed vendored module.
    (directory / "author-bitreverse.py").write_text(code)
    tree = ast.parse(code)
    if any(not isinstance(node, (ast.FunctionDef, ast.Assign)) for node in tree.body):
        raise ValueError("Unexpected top-level code in downloaded author example")
    namespace = {}
    exec(compile(tree, "downloaded-author-example", "exec"), namespace)
    return namespace["value_in_sorted_bitreverse_1"], namespace["value_in_sorted_bitreverse_2"]


def check_author(first, second, exhaustive):
    checks = different = 0
    starts = range(256) if exhaustive else range(0, 256, 17)
    for start in starts:
        for end in range(start + 1, 257):
            ordered = sorted(REVERSE[start:end])
            for rank, expected in enumerate(ordered):
                actual = first(start, end, rank)
                separator = second(start, end, rank)
                assert actual == expected, (start, end, rank, actual, expected)
                assert bisect.bisect_left(ordered, separator) == rank
                different += separator != expected
                checks += 1
    return {"exhaustive": exhaustive, "interval_rank_triples_per_implementation": checks,
            "implementation_1_order_statistic_failures": 0,
            "implementation_2_strict_rank_failures": 0,
            "implementation_2_nonidentical_separators": different}


def ceil_div(numerator, denominator):
    return -(-numerator // denominator)


def ordered_edge(a, b):
    return (a, b) if a[0] <= b[0] else (b, a)


def crossings(a, b, mode):
    """Return [left,right) crossings plus an exact endpoint check.

    BRR uses absolute horizontal coordinate for the permutation phase. A step
    at x adds floor(dy/dx), plus one if bitreverse[x] is below the rank separator.
    Starting at the left endpoint is a stated convention, not inferred drivecode.
    """
    a, b = ordered_edge(a, b)
    start, end = a[0], b[0]
    length, rise = end - start, b[1] - a[1]
    if not length:
        return [], {"dx": 0, "remainder": 0}
    quotient, remainder = divmod(rise, length)
    if mode == "ceil":
        values = [a[1] + ceil_div(k * rise, length) for k in range(length + 1)]
    elif mode == "nearest":
        # One conventional nearest-lattice/Bresenham tie rule: halves go +Y.
        values = [a[1] + (2 * k * rise + length) // (2 * length)
                  for k in range(length + 1)]
    elif mode == "brr":
        separator = sorted(REVERSE[start:end])[remainder]
        values = [a[1]]
        for x in range(start, end):
            values.append(values[-1] + quotient + (REVERSE[x] < separator))
        assert sum(REVERSE[x] < separator for x in range(start, end)) == remainder
        # A literal CPY/ADC implementation uses >=, so adjust strict separator.
        threshold = separator - 1 if remainder else 255
        adc_step = quotient if remainder else quotient - 1
        assert [adc_step + (threshold >= REVERSE[x]) for x in range(start, end)] == [
            values[i + 1] - values[i] for i in range(length)]
    else:
        raise ValueError(mode)
    assert values[0] == a[1] and values[-1] == b[1]
    assert all(min(a[1], b[1]) <= y <= max(a[1], b[1]) for y in values)
    return list(zip(range(start, end), values[:-1])), {
        "dx": length, "dy": rise, "quotient": quotient, "remainder": remainder,
        "endpoint": [end, values[-1]],
    }


def multiply(a, b):
    assert -128 <= a + b <= 127 and -128 <= a - b <= 127
    return (a + b) ** 2 // 256 - (a - b) ** 2 // 256


def scene(index):
    yaw, pitch = 3 * index % 256, (3 * index // 2) % 256
    sy, cy = SINE[yaw], SINE[(yaw + 64) % 256]
    sp, cp = SINE[pitch], SINE[(pitch + 64) % 256]
    points = []
    for x, y, z in VERTICES:
        xx = multiply(x, cy) + multiply(z, sy)
        zz = multiply(z, cy) - multiply(x, sy)
        yy = multiply(y, cp) - multiply(zz, sp)
        depth = 144 + multiply(y, sp) + multiply(zz, cp)
        factor = (16384 + depth) // (2 * depth)
        px = (29 * multiply(xx, factor) + 10) // 20
        py = (29 * multiply(yy, factor) + 10) // 20
        points.append(((64 + px) // 2, 64 - py))
    visible = []
    for face in FACES:
        a, b, c = (points[v] for v in face)
        area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        visible.append(int(area >= 0))
    return points, visible


def model_edges():
    adjacency = {}
    for face, triangle in enumerate(FACES):
        for a, b in zip(triangle, triangle[1:] + triangle[:1]):
            adjacency.setdefault(tuple(sorted((a, b))), []).append(face)
    assert len(adjacency) == 30 and all(len(v) == 2 for v in adjacency.values())
    return [(a, b, *faces) for (a, b), faces in sorted(adjacency.items())]


def canvas_from_edges(edges, mode, parity=None):
    height = 128 if parity is None else 64
    markers = [[0] * height for _ in range(64)]
    terminal = [0] * 64
    for a, b, color in edges:
        for x, y in crossings(a, b, mode)[0]:
            if parity is None:
                markers[x][y] ^= color
            else:
                q = ceil_div(y - parity, 2)
                if q < 64:
                    markers[x][q] ^= color
                else:
                    terminal[x] ^= color
    canvas = [[0] * height for _ in range(64)]
    for x in range(64):
        running = 0
        for y in range(height):
            running ^= markers[x][y]
            canvas[x][y] = running
        assert running ^ terminal[x] == 0
    return canvas, markers, terminal


def changed(a, b):
    return sum(x != y for ca, cb in zip(a, b) for x, y in zip(ca, cb))


def enclosed_black(canvas):
    """Black samples between the first and last colored sample of each column."""
    result = 0
    for column in canvas:
        occupied = [i for i, value in enumerate(column) if value]
        if occupied:
            result += sum(value == 0 for value in column[occupied[0]:occupied[-1] + 1])
    return result


def analyze_scenes(report_path):
    report = json.loads(report_path.read_text()) if report_path else None
    if report:
        assert report["program_sha256"] == BASE_PROGRAM
        assert len(report["samples"]) == 512
    totals, per_frame, shapes = Counter(), [], Counter()
    max_error = {"brr": Fraction(0), "nearest": Fraction(0), "ceil": Fraction(0)}
    witness = {}
    for index in range(512):
        points, visible = scene(index)
        if report:
            sample = report["samples"][index]
            assert points == [tuple(v) for v in sample["vertices"]]
            assert visible == sample["visible_faces"]
        edges = []
        for a, b, f, g in model_edges():
            color = (COLORS[f] if visible[f] else 0) ^ (COLORS[g] if visible[g] else 0)
            if not color:
                continue
            totals["visible_edges"] += 1
            aa, bb = ordered_edge(points[a], points[b])
            if aa[0] == bb[0]:
                totals["vertical_edges_skipped"] += 1
                continue
            edges.append((aa, bb, color))
            exact, info = crossings(aa, bb, "ceil")
            brr, _ = crossings(aa, bb, "brr")
            nearest, _ = crossings(aa, bb, "nearest")
            n, dy, r = info["dx"], info["dy"], info["remainder"]
            totals["nonvertical_edges"] += 1
            totals["markers"] += n
            totals["one_column_fast_path_edges"] += n == 1
            totals["generated_kernel_markers"] += n if n > 1 else 0
            totals["fraction_corrections"] += r
            totals["zero_fraction_edges"] += r == 0
            totals["brr_changed_crossings_vs_ceil"] += sum(a != b for a, b in zip(exact, brr))
            totals["nearest_changed_crossings_vs_ceil"] += sum(a != b for a, b in zip(exact, nearest))
            totals["brr_crossing_distance_from_ceil"] += sum(abs(a[1] - b[1]) for a, b in zip(exact, brr))
            shapes[(n, dy, aa[0])] += 1
            for mode, line in [("ceil", exact), ("brr", brr), ("nearest", nearest)]:
                for x, y in line:
                    error = abs(Fraction(y - aa[1]) - Fraction((x - aa[0]) * dy, n))
                    if error > max_error[mode]:
                        max_error[mode] = error
                        witness[mode] = {"presentation": index, "from": aa, "to": bb,
                                         "sample": [x, y], "error": str(error)}
        full = {mode: canvas_from_edges(edges, mode) for mode in ("ceil", "brr", "nearest")}
        parity = index // 2 & 1
        all_fields = {mode: [canvas_from_edges(edges, mode, p) for p in (0, 1)] for mode in full}
        fields = {mode: all_fields[mode][parity] for mode in full}
        # Mapping full-resolution crossings must equal selecting full-canvas rows.
        for mode in full:
            for p in (0, 1):
                assert all_fields[mode][p][0] == [column[p::2] for column in full[mode][0]]
        row = {"presentation": index, "parity": parity,
               "brr_full_changed_pixels": changed(full["ceil"][0], full["brr"][0]),
               "brr_field_changed_pixels": changed(fields["ceil"][0], fields["brr"][0]),
               "nearest_full_changed_pixels": changed(full["ceil"][0], full["nearest"][0]),
               "nearest_field_changed_pixels": changed(fields["ceil"][0], fields["nearest"][0]),
               "brr_full_enclosed_black_pixels": enclosed_black(full["brr"][0]),
               "ceil_full_enclosed_black_pixels": enclosed_black(full["ceil"][0]),
               "nearest_full_enclosed_black_pixels": enclosed_black(full["nearest"][0])}
        per_frame.append(row)
    summary = {}
    for key in per_frame[0]:
        if key not in ("presentation", "parity"):
            values = [row[key] for row in per_frame]
            summary[key] = {"mean": sum(values) / 512, "max": max(values), "total": sum(values)}
    # dx=1 already has a direct one-marker path and performs no DDA advance.
    n, r = totals["generated_kernel_markers"], totals["fraction_corrections"]
    return {
        "poses": 512, "clock": {"yaw": "3*k mod 256", "pitch": "floor(3*k/2) mod 256",
                                 "field_parity": "floor(k/2) mod 2", "buffers": "B,A,B,A"},
        "baseline_program_sha256": BASE_PROGRAM,
        "report_validation": {"path": str(report_path) if report_path else None,
                              "sha256": hashlib.sha256(report_path.read_bytes()).hexdigest() if report_path else None,
                              "matching_vertex_visibility_sets": 512 if report else None},
        "totals": dict(totals), "unique_edge_shapes_with_absolute_phase": len(shapes),
        "maximum_vertical_error_from_continuous_edge": {
            mode: {"exact_fraction": str(value), "rows": float(value), "witness": witness[mode]}
            for mode, value in max_error.items()},
        "pixel_changes": summary,
        "closure_and_selected_fullcanvas_mismatches": 0,
        "prefix_closure_checks": 512 * 3 * 3,
        "selected_field_equivalence_checks": 512 * 3 * 2,
        "cycle_model_excludes_setup_plot_dispatch_stalls": {
            "current_advance_cycles": 21 * n + 4 * r,
            "ideal_5_cycle_brr_saving_per_pose": (16 * n + 4 * r) / 512,
            "register_compatible_12_cycle_brr_saving_per_pose": (9 * n + 4 * r) / 512,
            "additional_threshold_setup_break_even_per_nonvertical_edge":
                (9 * n + 4 * r) / totals["nonvertical_edges"],
            "additional_setup_break_even_per_nonzero_fraction_edge":
                (9 * n + 4 * r) / (totals["nonvertical_edges"] - totals["zero_fraction_edges"]),
        },
        "per_frame": per_frame,
    }


def fixtures():
    polygons = {
        "rectangle": [(8, 8), (24, 8), (24, 28), (8, 28)],
        "diamond": [(16, 0), (31, 17), (16, 34), (1, 17)],
        "steep_triangle": [(5, 3), (8, 126), (26, 31)],
        "one_column": [(30, 2), (31, 127), (30, 126)],
        "terminal_127": [(4, 3), (29, 8), (28, 127), (5, 127)],
    }
    result = []
    for name, polygon in polygons.items():
        edges = [(a, b, 1) for a, b in zip(polygon, polygon[1:] + polygon[:1])]
        full = canvas_from_edges(edges, "brr")
        for parity in (0, 1):
            field = canvas_from_edges(edges, "brr", parity)
            assert field[0] == [column[parity::2] for column in full[0]]
        # Reversing winding must leave the same canonical shared-edge trace.
        reverse = [(b, a, color) for a, b, color in edges]
        assert canvas_from_edges(reverse, "brr") == full
        assert canvas_from_edges(edges + reverse, "brr")[0] == [[0] * 128 for _ in range(64)]
        result.append({"name": name, "points": polygon, "both_fields_and_reversal_and_xor_cancellation": True})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/research/boo-math")
    parser.add_argument("--fetch", action="store_true", help="Refresh ignored primary-source HTML (pinned SHA required)")
    parser.add_argument("--sample-author", action="store_true", help="Quicker smoke instead of all 2,829,056 interval/rank triples")
    parser.add_argument("--report", type=Path, help="Optionally cross-check old d5baf50b verification pose inputs")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    provenance = source_cache(args.output, args.fetch)
    first, second = author_functions(args.output)
    provenance["bitreverse.html"]["extracted_python_sha256"] = hashlib.sha256(
        (args.output / "author-bitreverse.py").read_bytes()).hexdigest()
    result = {"analysis_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "primary_sources": provenance,
              "author_selector_checks": check_author(first, second, not args.sample_author),
              "brr_contract": {"phase": "absolute horizontal x",
                               "quotient_remainder": "dy=q*dx+r, 0<=r<dx",
                               "step": "y(x+1)=y(x)+q+[bitreverse(x)<sorted(BR[left:right])[r]]",
                               "markers": "integer x in [left,right), starting exactly at leftY"},
              "fixtures": fixtures(), "scene": analyze_scenes(args.report)}
    (args.output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    compact = {k: v for k, v in result.items() if k != "scene"}
    compact["scene"] = {k: v for k, v in result["scene"].items() if k != "per_frame"}
    print(json.dumps(compact, indent=2))


if __name__ == "__main__":
    main()
