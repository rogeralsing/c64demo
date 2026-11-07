#!/usr/bin/env python3
"""Independent exact-rational topology/order audit of decoded 2D scene inputs."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from analyze_scene import cross, subtract, edges, intervals

ROOT = Path("build/research/next-round/boot-analysis")


def intersection(a0, a1, b0, b1):
    r, s = subtract(a1, a0), subtract(b1, b0)
    denominator = cross(r, s)
    if not denominator:
        return None
    q = subtract(b0, a0)
    t = Fraction(cross(q, s), denominator)
    u = Fraction(cross(q, r), denominator)
    return t, u, a0[1] + t*r[1]


def pair_order(a, b):
    lo = max(min(p[1] for p in a), min(p[1] for p in b))
    hi = min(max(p[1] for p in a), max(p[1] for p in b))
    if lo >= hi:
        return None
    events = {Fraction(lo), Fraction(hi)}
    events.update(Fraction(p[1]) for p in a+b if lo < p[1] < hi)
    for a0, a1 in edges(a):
        for b0, b1 in edges(b):
            hit = intersection(a0, a1, b0, b1)
            if hit is not None and 0 <= hit[0] <= 1 and 0 <= hit[1] <= 1 and lo < hit[2] < hi:
                events.add(hit[2])
    events = sorted(events)
    for y0, y1 in zip(events, events[1:]):
        y = (y0+y1)/2
        aa, bb = intervals(a, y), intervals(b, y)
        if aa and bb and aa[0][0] < bb[-1][1]:
            return {"y": str(y), "earlier_left": str(aa[0][0]), "later_right": str(bb[-1][1]),
                    "wrong_order_without_overlap": aa[-1][1] <= bb[0][0]}
    return None


def main():
    scene = json.loads((ROOT/"original-scene.json").read_text())
    proper_crossings, multiple_intervals, order_violations = [], [], []
    for frame in scene["frames"]:
        polygons = frame["polygons"]
        for i, polygon in enumerate(polygons):
            contour = polygon["outline_xy"]
            ee = edges(contour)
            for k, (a0, a1) in enumerate(ee):
                for j in range(k+1, len(ee)):
                    hit = intersection(a0, a1, *ee[j])
                    if hit is not None and 0 < hit[0] < 1 and 0 < hit[1] < 1:
                        proper_crossings.append([frame["frame"], i, k, j])
            yy = sorted(set(p[1] for p in contour))
            for low, high in zip(yy, yy[1:]):
                if len(intervals(contour, Fraction(low+high, 2))) > 1:
                    multiple_intervals.append([frame["frame"], i, low, high])
            for j in range(i+1, len(polygons)):
                witness = pair_order(contour, polygons[j]["outline_xy"])
                if witness is not None:
                    order_violations.append({"frame": frame["frame"], "polygons": [i, j], "witness": witness})
    result = {
        "scene_stream_sha256": scene["summary"]["stream_sha256"],
        "proper_self_crossings": proper_crossings,
        "multiple_even_odd_intervals_in_open_y_slab": multiple_intervals,
        "earlier_polygon_not_wholly_right_of_later": order_violations,
        "scope": "Continuous supplied polygon geometry; vertex-touching/pinches allowed, native integer edges not modeled",
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    (ROOT/"fragment-order.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({k: len(v) if isinstance(v, list) else v for k, v in result.items()}, indent=2))


if __name__ == "__main__":
    main()
