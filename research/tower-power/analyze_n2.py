#!/usr/bin/env python3
"""Record N2's literal coordinate rings and count operands without execution."""

import hashlib
import json
import math
from pathlib import Path


def main():
    root = Path("build/research/tower-power/static")
    prefix = root / "unpacked/side2-n2"
    memory = prefix.with_suffix(".memory.bin").read_bytes()
    known = prefix.with_suffix(".known.bin").read_bytes()
    tables = [0x4600, 0x4650, 0x46a0]
    if not all(known[address + i] for address in tables for i in range(40)):
        raise AssertionError("Coordinate bytes must be established output")
    points = [tuple(memory[address + i] - 128 for address in tables) for i in range(40)]
    radii = [math.sqrt(sum(value * value for value in point)) for point in points]
    report = {"source": "side2/n2.00%-100%-100%",
              "memory_sha256": hashlib.sha256(memory).hexdigest(),
              "coordinate_tables": tables, "center_bias": 128,
              "upper_points": points,
              "ring_y": [points[i][1] for i in (0, 10, 20, 30)],
              "radius_min": min(radii), "radius_max": max(radii),
              "face_count_operand_22cb": memory[0x22cb],
              "edge_count_operand_22ca": memory[0x22ca],
              "interpretation": "Four 10-point latitude rings; runtime mirrors output. Sphere candidate, not native visual identification."}
    target = root / "n2-geometry-candidate.json"
    target.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "upper_points"}, indent=2))


if __name__ == "__main__":
    main()
