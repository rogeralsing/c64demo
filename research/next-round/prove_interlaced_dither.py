#!/usr/bin/env python3
"""Host feasibility proof; no C64 program or emulator is run or changed.

Compare per-face rational interiors (opaque assignment) to per-mesh-edge byte
markers and prefix XOR, using previously native-verified projected vertices.
The negative control keeps the existing two-bit color lane-shift recipe while
feeding it an eight-bit pattern; it must disagree with the opaque reference.
"""
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from verify import read_labels

spec = importlib.util.spec_from_file_location("filled_reference", REPO/"verify-filled.py")
filled = importlib.util.module_from_spec(spec)
spec.loader.exec_module(filled)

BASE = REPO/"build/z-culling-after"
OUT = REPO/"build/research/interlaced-dither"
MASKS = (0xC0, 0x30, 0x0C, 0x03)


def direct_interiors(vertices, faces, visible, patterns):
    """Opaque direct face interiors, no marker generation or prefix step."""
    packed = bytearray(2048)
    owners = bytearray(64*128)
    for face_id, (face, shown) in enumerate(zip(faces, visible)):
        if not shown:
            continue
        contour = [vertices[index] for index in face]
        for x in range(64):
            hits = []
            for a, b in zip(contour, contour[1:]+contour[:1]):
                if min(a[0], b[0]) <= x < max(a[0], b[0]):
                    hits.append(Fraction(a[1]) + Fraction((b[1]-a[1])*(x-a[0]), b[0]-a[0]))
            hits.sort()
            assert len(hits) in (0, 2)
            if not hits:
                continue
            for y in range(max(0, math.ceil(hits[0])), min(128, math.ceil(hits[1]))):
                assert not owners[y*64+x], ("visible faces overlap", x, y, face_id)
                owners[y*64+x] = face_id+1
                index, mask = (x//4)*128+y, MASKS[x&3]
                packed[index] = (packed[index] & (255^mask)) | (patterns[face_id] & mask)
    return packed, sum(bool(v) for v in owners)


def edge_prefix(vertices, faces, visible, patterns, parity, wrong_lanes=False):
    adjacency = {}
    for face_id, face in enumerate(faces):
        for a, b in zip(face, face[1:]+face[:1]):
            adjacency.setdefault(tuple(sorted((a, b))), []).append(face_id)
    markers = bytearray(2048)
    sink = 0
    for (a, b), (first, last) in adjacency.items():
        delta = (patterns[first] if visible[first] else 0) ^ (patterns[last] if visible[last] else 0)
        a, b = vertices[a], vertices[b]
        if a[0] > b[0]:
            a, b = b, a
        dx, dy = b[0]-a[0], b[1]-a[1]
        for x in range(a[0], b[0]):
            crossing = -(-(a[1]*dx+dy*(x-a[0]))//dx)
            q = (crossing+1-parity)//2
            assert 0 <= q <= 64
            lane = ((delta << (6-2*(x&3))) & 255) if wrong_lanes else delta & MASKS[x&3]
            if q == 64:
                sink ^= lane
            else:
                markers[(x//4)*128+2*q+parity] ^= lane
    packed = bytearray(2048)
    for column in range(16):
        running = 0
        for row in range(parity, 128, 2):
            running ^= markers[column*128+row]
            packed[column*128+row] = running
    return packed, markers, sink


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = BASE/"verification/verification.json"
    report = json.loads(report_path.read_text())
    program = (BASE/"icosahedron-interlaced.prg").read_bytes()
    assert report["pass"] and report["frames_verified"] == 512
    assert hashlib.sha256(program).hexdigest() == report["program_sha256"]
    model = filled.ReferenceModel("icosahedron", program, read_labels(BASE/"icosahedron-interlaced.sym"))
    table_path = REPO/"build/research/next-round/patterns.json"
    table = json.loads(table_path.read_text())
    even = [int(p["even_hex"], 16) for p in table["patterns"]]
    odd = [int(p["odd_hex"], 16) for p in table["patterns"]]
    history = {0x2000: bytearray(2048), 0x2800: bytearray(2048)}
    output_digest = hashlib.sha256()
    covered_samples, negative_control = 0, None
    patterns_seen = set()
    for index, sample in enumerate(report["samples"]):
        parity = sample["field_parity"]
        bank = int(sample["charset"][1:], 16)
        assert bank == (0x2800 if index%2 == 0 else 0x2000)
        assert parity == (index//2)&1
        vertices = sample["vertices"]
        visible = model.visibility(vertices)
        assert list(map(int, visible)) == sample["visible_faces"]
        ids = [(face*5+index//4)%12 for face in range(20)]
        patterns = [(odd if parity else even)[i] for i in ids]
        patterns_seen.update((parity, i+1) for i, shown in zip(ids, visible) if shown)
        direct, pixels = direct_interiors(vertices, model.faces, visible, patterns)
        actual, markers, sink = edge_prefix(vertices, model.faces, visible, patterns, parity)
        mixed = bytearray(history[bank])
        for column in range(16):
            for row in range(parity, 128, 2):
                address = column*128+row
                assert direct[address] == actual[address], (index, column, row)
                mixed[address] = actual[address]
        history[bank] = mixed
        covered_samples += pixels
        output_digest.update(mixed)
        if negative_control is None:
            wrong, _, _ = edge_prefix(vertices, model.faces, visible, patterns, parity, wrong_lanes=True)
            differences = sum(wrong[c*128+y] != direct[c*128+y] for c in range(16) for y in range(parity, 128, 2))
            if differences:
                negative_control = {"frame": index, "wrong_selected_bytes": differences,
                                    "fault": "Use the existing 2-bit ASL lane recipe on 8-bit deltas"}
        if index%128 == 0:
            print(f"{index}: geometry/opaque-pattern/edge-prefix agreement", flush=True)
    assert len(patterns_seen) == 24 and negative_control is not None
    result = {
        "pass": True, "scope": "Host feasibility proof only; no proposed ASM/native/raster/timing validation",
        "baseline_program_sha256": report["program_sha256"],
        "baseline_report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        "model_validation_helper_sha256": hashlib.sha256((REPO/"verify-filled.py").read_bytes()).hexdigest(),
        "assessed_source_sha256": {str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest()
                                   for path in (REPO/"src/xor-fill.asm", REPO/"src/engine.asm")},
        "pattern_table_sha256": hashlib.sha256(table_path.read_bytes()).hexdigest(),
        "frames": len(report["samples"]), "pattern_id_and_parity_combinations": len(patterns_seen),
        "selected_packed_bytes_compared": len(report["samples"])*1024,
        "full_resolution_covered_integer_samples": covered_samples,
        "integer_samples_covered_by_multiple_visible_faces": 0,
        "mixed_buffer_output_sha256": output_digest.hexdigest(),
        "negative_control": negative_control,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    (OUT/"host-proof.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
