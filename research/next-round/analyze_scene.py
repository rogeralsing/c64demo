#!/usr/bin/env python3
"""Parse original Next Round side-3 polygon records and audit geometric overlap.

This analyzes supplied 2D polygons, not the renderer's integer pixel rules. Pair
overlap is exact rational geometry: interval order can change only at vertices
or edge intersections; sample every open Y slab delimited by those events.
"""
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path

ROOT = Path("build/research/next-round/boot-analysis")


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def subtract(a, b):
    return a[0] - b[0], a[1] - b[1]


def edges(points):
    return list(zip(points, points[1:] + points[:1]))


def intervals(points, y):
    xs = []
    for a, b in edges(points):
        if min(a[1], b[1]) < y < max(a[1], b[1]):
            xs.append(a[0] + Fraction(b[0] - a[0], b[1] - a[1]) * (y - a[1]))
    xs.sort()
    assert len(xs) % 2 == 0
    return [(a, b) for a, b in zip(xs[::2], xs[1::2]) if a < b]


def overlap(a, b):
    lo = max(min(p[1] for p in a), min(p[1] for p in b))
    hi = min(max(p[1] for p in a), max(p[1] for p in b))
    if lo >= hi:
        return None, 0
    if max(min(p[0] for p in a), min(p[0] for p in b)) >= min(max(p[0] for p in a), max(p[0] for p in b)):
        return None, 0
    events = {Fraction(lo), Fraction(hi)}
    events.update(Fraction(p[1]) for p in a + b if lo < p[1] < hi)
    for a0, a1 in edges(a):
        r = subtract(a1, a0)
        for b0, b1 in edges(b):
            s = subtract(b1, b0)
            denominator = cross(r, s)
            if not denominator:
                continue  # collinear changes are delimited by endpoints
            q = subtract(b0, a0)
            t = Fraction(cross(q, s), denominator)
            u = Fraction(cross(q, r), denominator)
            if 0 <= t <= 1 and 0 <= u <= 1:
                y = a0[1] + t * r[1]
                if lo < y < hi:
                    events.add(y)
    events = sorted(events)
    area = Fraction(0)
    max_width = Fraction(0)
    witness = None
    for y0, y1 in zip(events, events[1:]):
        y = (y0 + y1) / 2
        for x0, x1 in intervals(a, y):
            for u0, u1 in intervals(b, y):
                left, right = max(x0, u0), min(x1, u1)
                if left < right:
                    area += (right - left) * (y1 - y0)
                    max_width = max(max_width, right - left)
                    if witness is None:
                        witness = {"x": str((left + right) / 2), "y": str(y)}
    if witness is not None:
        witness.update(area=str(area), area_float=float(area),
                       largest_slab_midpoint_width=str(max_width),
                       largest_slab_midpoint_width_float=float(max_width))
    return witness, len(events) - 1


def parse(ram):
    start = 0x6CBD
    assert ram[0xE000] == ram[0xE005] == 0xA9
    end = ram[0xE001] | ram[0xE006] << 8
    cursor = start
    frames = []
    while cursor < end:
        frame = {"frame": len(frames), "address": cursor, "polygons": []}
        while cursor < end:
            descriptor = ram[cursor]
            cursor += 1
            if descriptor == 0:
                break
            count = (descriptor >> 4) + 3
            assert cursor + count * 2 <= end
            points = [(ram[cursor + 2*i + 1], ram[cursor + 2*i]) for i in range(count)]
            cursor += 2 * count
            left, right = points[:2], [points[0], points[2]]
            index = 3
            while index < count:
                if left[-1][1] == right[-1][1]:
                    left.append(points[index])
                    index += 1
                    if index < count:
                        right.append(points[index])
                        index += 1
                elif left[-1][1] > right[-1][1]:
                    left.append(points[index])
                    index += 1
                else:
                    right.append(points[index])
                    index += 1
            assert all(b[1] <= a[1] for chain in (left, right) for a, b in zip(chain, chain[1:]))
            outline = left + list(reversed(right[1:]))
            signs = set()
            for i in range(count):
                value = cross(subtract(outline[i-1], outline[i-2]), subtract(outline[i], outline[i-1]))
                if value:
                    signs.add(value > 0)
            frame["polygons"].append({"descriptor": descriptor, "pattern": descriptor & 15,
                                      "raw_yx": [(y, x) for x, y in points],
                                      "outline_xy": outline, "convex": len(signs) <= 1})
        frames.append(frame)
    assert cursor == end
    return start, end, frames


def main():
    ram = (ROOT / "depacked-round3/008-e000-ram.bin").read_bytes()
    start, end, frames = parse(ram)
    all_polygons = [p for f in frames for p in f["polygons"]]
    summary = {
        "start": start, "end": end, "frames": len(frames), "polygons": len(all_polygons),
        "polygons_per_frame": dict(Counter(len(f["polygons"]) for f in frames)),
        "patterns": dict(Counter(p["pattern"] for p in all_polygons)),
        "vertex_counts": dict(Counter(len(p["outline_xy"]) for p in all_polygons)),
        "nonconvex_polygons": sum(not p["convex"] for p in all_polygons),
        "chain_y_monotonicity_violations": 0,
        "coordinate_ranges": [(min(p[k] for q in all_polygons for p in q["outline_xy"]),
                               max(p[k] for q in all_polygons for p in q["outline_xy"])) for k in (0, 1)],
        "stream_sha256": hashlib.sha256(ram[start:end]).hexdigest(),
    }
    (ROOT / "original-scene.json").write_text(json.dumps({"summary": summary, "frames": frames}, indent=2) + "\n")
    pairs = slabs = 0
    overlaps = []
    for frame in frames:
        polygons = frame["polygons"]
        for i, a in enumerate(polygons):
            for j in range(i+1, len(polygons)):
                witness, count = overlap(a["outline_xy"], polygons[j]["outline_xy"])
                pairs += 1
                slabs += count
                if witness is not None:
                    overlaps.append({"frame": frame["frame"], "polygons": [i, j],
                                     "patterns": [a["pattern"], polygons[j]["pattern"]],
                                     "witness": witness})
        if frame["frame"] % 128 == 0:
            print(f"frame {frame['frame']}: {pairs} pairs, {len(overlaps)} positive-area overlaps", flush=True)
    result = {"scene": summary, "polygon_pairs": pairs, "y_slabs": slabs,
              "positive_area_overlaps": len(overlaps), "examples": overlaps[:100],
              "method": "Exact rational even-odd intervals; every vertex/edge-crossing Y event delimits tested slabs",
              "scope": "Continuous supplied polygon geometry, not C64 edge rounding or native pixel equivalence",
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (ROOT / "scene-overlap.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("examples", "scene")}, indent=2))


if __name__ == "__main__":
    main()
