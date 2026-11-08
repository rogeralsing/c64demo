#!/usr/bin/env python3
"""Prepare projected detached cube panels, not filled animation frames."""

from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path


HERE = Path(__file__).resolve().parent
POSES = 64
HALF_PANEL = 25
CAMERA = 180
FOCAL = 180
WIDTH, HEIGHT = 96, 128


def rotate(point, phase):
    theta = phase * math.tau / POSES
    yaw = theta + 0.55
    pitch = 0.32 + 0.2 * math.sin(2 * theta)
    roll = 0.12 * math.sin(theta)
    x, y, z = point
    x, z = x * math.cos(yaw) + z * math.sin(yaw), -x * math.sin(yaw) + z * math.cos(yaw)
    y, z = y * math.cos(pitch) - z * math.sin(pitch), y * math.sin(pitch) + z * math.cos(pitch)
    x, y = x * math.cos(roll) - y * math.sin(roll), x * math.sin(roll) + y * math.cos(roll)
    return x, y, z


def panels_for(phase):
    radius = 38 + 3 * math.sin(phase * math.tau / POSES)
    size = HALF_PANEL
    panels = []
    for axis in range(3):
        other = [coordinate for coordinate in range(3) if coordinate != axis]
        for sign in (-1, 1):
            normal = [0, 0, 0]
            normal[axis] = sign
            normal = rotate(normal, phase)
            points = []
            for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                point = [0, 0, 0]
                point[axis] = sign * radius
                point[other[0]] = u * size
                point[other[1]] = v * size
                x, y, z = rotate(point, phase)
                points.append([math.floor(48 + FOCAL * x / (2 * (CAMERA + z)) + 0.5),
                               math.floor(64 - FOCAL * y / (CAMERA + z) + 0.5)])
            layer = "A" if -CAMERA * normal[2] > radius else "B"
            panels.append({"axis": axis, "side": sign, "normal": normal,
                           "radius": radius, "layer": layer, "points": points})
    return panels


def coverage(points):
    result = set()
    for x in range(WIDTH):
        crossings = []
        for first, last in zip(points, points[1:] + points[:1]):
            if first[0] > last[0]:
                first, last = last, first
            if first[0] <= x < last[0]:
                crossings.append(Fraction(first[1]) + Fraction((x - first[0]) * (last[1] - first[1]), last[0] - first[0]))
        crossings.sort()
        if len(crossings) not in (0, 2):
            raise ValueError("Projected convex panel has an invalid crossing count.")
        if crossings:
            first, last = (-(-value.numerator // value.denominator) for value in crossings)
            result.update((x, y) for y in range(first, last))
    return result


def audit(panels):
    layers = {"A": {}, "B": {}}
    for panel in panels:
        for x, y in panel["points"]:
            if not 0 <= x < WIDTH or not 0 <= y < HEIGHT:
                raise ValueError(f"Projected vertex escaped the canvas at {(x, y)}.")
        for pixel in coverage(panel["points"]):
            if pixel in layers[panel["layer"]]:
                raise ValueError("Two panels overlap within one XOR layer.")
            layers[panel["layer"]][pixel] = panel
    overlap = layers["A"].keys() & layers["B"].keys()
    for x, y in overlap:
        depths = []
        ray = (2 * x - 96, 64 - y, FOCAL)
        for layer in ("A", "B"):
            panel = layers[layer][(x, y)]
            normal = panel["normal"]
            denominator = sum(a * b for a, b in zip(normal, ray))
            depths.append((panel["radius"] + CAMERA * normal[2]) / denominator)
        if not 0 < depths[0] < depths[1]:
            raise ValueError("A priority is not justified by the supporting-box depth order.")
    return {"a_only": len(layers["A"].keys() - layers["B"].keys()),
            "b_only": len(layers["B"].keys() - layers["A"].keys()),
            "overlap": len(overlap), "same_layer_overlaps": 0}


def main():
    output = HERE / "build"
    output.mkdir(exist_ok=True)
    commands, poses = bytearray(), []
    for phase in range(POSES):
        panels = panels_for(phase)
        counts = audit(panels)
        for panel in panels:
            commands.append(1 if panel["layer"] == "A" else 3)
            commands.extend(coordinate for point in panel["points"] for coordinate in point)
        poses.append({"phase": phase, "panels": panels, "coverage": counts})
    (output / "commands.bin").write_bytes(commands)
    result = {"poses": POSES, "panels_per_pose": 6, "command_bytes_per_panel": 9,
              "command_bytes": len(commands), "sha256": hashlib.sha256(commands).hexdigest(),
              "canvas": [WIDTH, HEIGHT], "physical_viewport": [192, 128],
              "panel_half_size": HALF_PANEL, "camera": CAMERA, "focal": FOCAL,
              "prepared_work": "projected endpoints and entry/exit layer labels; no filled frames",
              "frames": poses}
    (output / "geometry.json").write_text(json.dumps(result, indent=2) + "\n")
    points = [point for frame in poses for panel in frame["panels"] for point in panel["points"]]
    print(f"Prepared {POSES} poses / {len(commands)} command bytes; "
          f"bounds x={min(p[0] for p in points)}..{max(p[0] for p in points)}, "
          f"y={min(p[1] for p in points)}..{max(p[1] for p in points)}; "
          f"overlap={min(p['coverage']['overlap'] for p in poses)}..{max(p['coverage']['overlap'] for p in poses)}.")


if __name__ == "__main__":
    main()
