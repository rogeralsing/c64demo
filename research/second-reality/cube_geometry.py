#!/usr/bin/env python3
"""Bind the original cube's stored projected poses to its native RAM captures.

This passive check executes no demo code. It establishes which geometry inputs
are literal original-file data; edge interpolation and texture rendering have
their own analysis. Native capture/session validation remains separate.
"""

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "build/research/second-reality"
BB_SHA = "3b84919d607a072c1990f43be657017f1240be46a537a29b3046e05ecbe1d7ce"
BA_SHA = "fdc325fc558f9fe9e40fd909b166b98f1acec19de20c7f6ceb7af1c790fcb846"
FACES = ((0x01, (0, 1, 2, 3)), (0x10, (0, 1, 5, 4)),
         (0x08, (1, 2, 6, 5)), (0x20, (2, 3, 7, 6)),
         (0x04, (0, 3, 7, 4)))
DOMAINS = (("projected_vertex_poses", 0x3000, 0x800, 0),
           ("visibility_masks", 0x3800, 128, 0x800),
           ("scale_tables", 0x3B00, 550, 0xB00))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source(name, digest, load, size):
    path = BASE / "disk-map" / name
    raw = path.read_bytes()
    assert sha(raw) == digest, (path, "original-file identity")
    assert int.from_bytes(raw[:2], "little") == load and len(raw) == size + 2
    return raw[2:], {"path": str(path.relative_to(ROOT)), "sha256": digest,
                     "load_address": load, "payload_bytes": size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path,
                        default=BASE / "native-cube-20261108T123508Z")
    parser.add_argument("--output", type=Path, default=BASE / "cube-geometry")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / "proof.json"
    target.unlink(missing_ok=True)
    bb, bb_record = source("side2-entry06-BB.prg", BB_SHA, 0x7000, 12288)
    ba, ba_record = source("side2-entry05-BA.prg", BA_SHA, 0x4000, 4080)
    poses = []
    for phase in range(128):
        vertices = [(bb[256 * vertex + phase], bb[256 * vertex + 128 + phase])
                    for vertex in range(8)]
        assert all(0 <= value <= 48 for point in vertices for value in point)
        mask = bb[0x800 + phase]
        assert mask and not mask & ~0x3D
        poses.append({"phase": phase, "projected_vertices": vertices,
                      "visibility_mask": mask})
    assert bb[0xB00:0xB32] == bytes(range(50)), "Base scale lookup is identity"
    captures = []
    for path in sorted(args.capture.glob("ram-ba-*.bin")):
        ram = path.read_bytes()
        assert len(ram) == 65536, (path, "complete physical RAM")
        checks = {}
        for name, address, size, offset in DOMAINS:
            actual, expected = ram[address:address + size], bb[offset:offset + size]
            checks[name] = {"bytes": size, "sha256": sha(expected),
                            "exact": actual == expected}
            assert checks[name]["exact"], (path, name)
        if path.name == "ram-ba-entry.bin":
            assert ram[0x4000:0x4FF0] == ba, "All original BA bytes at its entry"
        captures.append({"path": str(path.relative_to(ROOT)), "sha256": sha(ram),
                         "checks": checks})
    assert captures, "No native cube RAM captures found"
    result = {"pass": True, "script_sha256": sha(Path(__file__).read_bytes()),
              "original_files": [ba_record, bb_record], "poses": poses,
              "face_mask_vertices": [{"bit": bit, "vertices": vertices}
                                     for bit, vertices in FACES],
              "stored_pose_bytes": 2048, "stored_visibility_bytes": 128,
              "stored_scale_bytes": 550, "native_captures": captures,
              "runtime_consumers": {"face_dispatch": 0x3880,
                                    "coordinate_scale_lookup": 0x3A00,
                                    "phase_update": "(phase - 1) & 127"},
              "scope": "Original projected coordinate, visibility and scale data identity. "
                       "No CPU execution, frame-rate claim or whole-machine equivalence."}
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"pass": True, "poses": 128, "geometry_bytes": 2726,
                      "native_captures": len(captures), "receipt": str(target)}, indent=2))


if __name__ == "__main__":
    main()
