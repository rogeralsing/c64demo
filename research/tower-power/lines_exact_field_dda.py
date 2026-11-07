#!/usr/bin/env python3
"""Exhaustive host proof of true-denominator, negative-error row/field DDA.

Models 8-bit binary ADC/SBC carry operationally, independently comparing every
sample to integer rational ceilings. No proposed ASM, VICE or production write.
NumPy only accelerates exhaustive enumeration of all legal Y endpoint pairs.
"""

import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np


REPOSITORY = Path(__file__).resolve().parents[2]
OUTPUT = REPOSITORY / "build/research/tower-power/static/lines/exact-field-dda.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def advance(error, coordinate, height, sign, denominator):
    # Binary ADC with incoming C=0. A's encoded negative byte plus h overflows
    # iff the signed error+h is nonnegative, since -126 <= error < 0, h <= 127.
    total = (error & 255) + height
    carry = total >= 256
    accumulator = total & 255
    updates = np.zeros_like(error)
    while np.any(carry):
        coordinate = coordinate + np.where(carry, sign, 0)
        updates += carry
        # INX/DEX does not change C. Each SBC runs with C=1, so no extra borrow.
        difference = accumulator - denominator
        accumulator = np.where(carry, difference & 255, accumulator)
        carry = carry & (difference >= 0)
    assert np.all(accumulator >= 128)
    error = accumulator - 256
    assert np.all((-denominator <= error) & (error < 0))
    return error, coordinate, updates


def exhaust():
    y0 = np.repeat(np.arange(128, dtype=np.int32), 128)
    y1 = np.tile(np.arange(128, dtype=np.int32), 128)
    delta = y1 - y0
    height = np.abs(delta)
    negative = delta < 0
    sign = np.where(negative, -1, 1)
    samples, transitions, maximum = Counter(), Counter(), Counter()
    terminal_samples = 0
    for width in range(1, 64):
        full = y0.copy()
        full_error = np.where(negative, -width, -1)
        fields, errors = [], []
        for parity in (0, 1):
            odd = ((y0 - parity) & 1) != 0
            fields.append((y0 - parity + 1) // 2)
            errors.append(np.where(negative,
                                   np.where(odd, -width, -2 * width),
                                   np.where(odd, -width - 1, -1)))
        for index in range(width + 1):  # Include the unused final endpoint too.
            expected_y = (y0 * width + delta * index + width - 1) // width
            assert np.array_equal(full, expected_y)
            assert np.all((-width <= full_error) & (full_error < 0))
            samples["full_y"] += len(y0)
            for parity in (0, 1):
                expected_q = ((y0 - parity) * width + delta * index + 2 * width - 1) // (2 * width)
                nested_q = (expected_y - parity + 1) // 2
                assert np.array_equal(fields[parity], expected_q)
                assert np.array_equal(fields[parity], nested_q)
                assert np.all((-2 * width <= errors[parity]) & (errors[parity] < 0))
                assert np.all((0 <= fields[parity]) & (fields[parity] <= 64))
                terminal = fields[parity] == 64
                assert np.array_equal(terminal, (expected_y == 127) if parity == 0 else np.zeros_like(terminal))
                terminal_samples += int(np.count_nonzero(terminal))
                samples[f"field_{parity}"] += len(y0)
            if index == width:
                continue
            full_error, full, count = advance(full_error, full, height, sign, width)
            maximum["full_y"] = max(maximum["full_y"], int(count.max()))
            transitions["full_y"] += len(y0)
            for parity in (0, 1):
                errors[parity], fields[parity], count = advance(errors[parity], fields[parity], height, sign, width * 2)
                maximum[f"field_{parity}"] = max(maximum[f"field_{parity}"], int(count.max()))
                transitions[f"field_{parity}"] += len(y0)
        if width % 16 == 0:
            print(f"widths 1..{width}: all Y endpoints and both field parities pass", flush=True)
    return {"endpoint_pairs_per_width": 16384, "widths": [1, 63],
            "x_start_translation_invariant": True, "samples_including_right_endpoint": dict(samples),
            "transitions": dict(transitions), "maximum_row_updates_in_one_advance": dict(maximum),
            "field64_terminal_samples_including_endpoint": terminal_samples,
            "all_exact_rational_ceilings_match": True, "all_8bit_negative_error_invariants_pass": True}


def scalar_advance(error, row, height, sign, denominator):
    total = (error & 255) + height
    carry, accumulator = total >= 256, total & 255
    count = 0
    while carry:
        row += sign
        count += 1
        difference = accumulator - denominator
        carry, accumulator = difference >= 0, difference & 255
    return accumulator - 256, row, count


def workload():
    sys.path.insert(0, str(REPOSITORY))
    from verify import read_labels
    spec = importlib.util.spec_from_file_location("filled_reference", REPOSITORY / "verify-filled.py")
    filled = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(filled)
    base = REPOSITORY / "build/z-culling-after"
    report_path = base / "verification/verification.json"
    report = json.loads(report_path.read_text())
    program = (base / "icosahedron-interlaced.prg").read_bytes()
    assert report["pass"] and report["frames_verified"] == 512
    assert digest(program) == report["program_sha256"] == "d5baf50b922f23ace12c829e28ef8a6796dd3431b334aff660409334a173c792"
    model = filled.ReferenceModel("icosahedron", program, read_labels(base / "icosahedron-interlaced.sym"))
    adjacency = {}
    for face_id, face in enumerate(model.faces):
        for a, b in zip(face, face[1:] + face[:1]):
            adjacency.setdefault(tuple(sorted((a, b))), []).append(face_id)
    frames = []
    all_updates = Counter()
    for index, sample in enumerate(report["samples"]):
        parity, vertices, visible = sample["field_parity"], sample["vertices"], sample["visible_faces"]
        frame = Counter()
        for (a, b), (face_a, face_b) in adjacency.items():
            color = (model.colors[face_a] if visible[face_a] else 0) ^ (model.colors[face_b] if visible[face_b] else 0)
            if not color:
                continue
            x0, y0 = vertices[a]
            x1, y1 = vertices[b]
            if x0 > x1:
                x0, x1, y0, y1 = x1, x0, y1, y0
            width, delta = x1 - x0, y1 - y0
            frame["drawn_edges"] += 1
            if width == 0:
                frame["vertical_edges"] += 1
                continue
            if width == 1:
                frame["single_width_fast_edges"] += 1
                continue
            height, denominator = abs(delta), width * 2
            eligible = height <= denominator
            frame["hybrid_edges" if eligible else "steep_retained_edges"] += 1
            row = (y0 - parity + 1) // 2
            odd = (y0 - parity) & 1
            error = (-width if odd else -denominator) if delta < 0 else (-width - 1 if odd else -1)
            old_error, old_remainder = -1, delta % width
            pending = None
            for j in range(width):
                expected = ((y0 - parity) * width + delta * j + denominator - 1) // denominator
                assert row == expected
                frame["kernel_x_samples"] += 1
                key = ((x0 + j) // 4, row)
                if key != pending:
                    frame["packed_row_runs"] += 1
                pending = key
                error, row, updates = scalar_advance(error, row, height, -1 if delta < 0 else 1, denominator)
                old_error += old_remainder
                old_cycles = 48
                if old_error >= 0:
                    old_error -= width
                    old_cycles += 4
                new_cycles = 39 if updates == 0 else 37 + 8 * updates
                # 27-cycle current plot + ZP error/step path: 12 or 10+8*n.
                frame["old_kernel_cycles"] += old_cycles
                frame["all_dda_kernel_cycles"] += new_cycles
                frame["hybrid_kernel_cycles"] += new_cycles if eligible else old_cycles
                if eligible:
                    assert updates <= 1
                    frame["hybrid_x_samples"] += 1
                    frame["hybrid_saved_cycles"] += old_cycles - new_cycles
                all_updates[updates] += 1
        frame["frame"] = index
        frames.append(dict(frame))
    keys = sorted({key for frame in frames for key in frame} - {"frame"})
    summaries = {key: {"total": sum(frame.get(key, 0) for frame in frames),
                       "mean": sum(frame.get(key, 0) for frame in frames) / len(frames),
                       "min": min(frame.get(key, 0) for frame in frames),
                       "max": max(frame.get(key, 0) for frame in frames)} for key in keys}
    return {"baseline_report_sha256": digest(report_path.read_bytes()), "baseline_program_sha256": report["program_sha256"],
            "frames": 512, "summary": summaries, "field_advance_histogram": dict(sorted(all_updates.items())),
            "scope": "Hot-kernel instruction estimate from verified geometry; old/new setup, new dispatch, LUT changes and VIC stalls not estimated",
            "all_dda_is_hypothetical": True, "hybrid_rule": "Retain current kernel for abs(dy)>2*dx; preserve width1 fastpath",
            "packed_runs_are_capacity_count_only": True}


def main():
    exhaustive = exhaust()
    measurements = workload()
    result = {"pass": True, "scope": "Host arithmetic proof and static cost model only; no proposed ASM or native timing proof",
              "script_sha256": digest(Path(__file__).read_bytes()), "numpy_version": np.__version__,
              "exhaustive": exhaustive, "baseline_workload": measurements,
              "cost_model_current_plot27_zp_steps": {"no_field_advance": 39, "one": 45, "two": 53, "three": 61},
              "limitations": ["Direct-q LUT and q64 sentinel mapping would require implementation work",
                              "Packed-run collector has not been implemented or benchmarked",
                              "No production renderer, emulator, raster, memory-layout or binary changes"]}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"pass": True, "exhaustive": exhaustive,
                      "workload_summary": measurements["summary"]}, indent=2))


if __name__ == "__main__":
    main()
