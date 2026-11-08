#!/usr/bin/env python3
"""Resolve original projected cube faces into disjoint vector fragments."""

from fractions import Fraction
import json
import math
from pathlib import Path


HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
PATTERNS = ((0, 0), (0x00, 0x33), (0xCC, 0x33), (0xCC, 0xFF),
            (0xFF, 0xFF), (0xFF, 0xEE), (0xBB, 0xEE), (0xBB, 0xAA),
            (0xAA, 0xAA), (0xAA, 0x99), (0x66, 0x99), (0x66, 0x55), (0x55, 0x55))


def area(poly):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1])) / 2


def normalize(poly):
    result = []
    for point in poly:
        point = tuple(Fraction(value) for value in point)
        if not result or point != result[-1]:
            result.append(point)
    if len(result) > 1 and result[0] == result[-1]:
        result.pop()
    changed = True
    while changed and len(result) >= 3:
        changed = False
        for index in range(len(result)):
            a, b, c = result[index - 1], result[index], result[(index + 1) % len(result)]
            if (b[0] - a[0]) * (c[1] - b[1]) == (b[1] - a[1]) * (c[0] - b[0]):
                result.pop(index)
                changed = True
                break
    if len(result) < 3 or area(result) == 0:
        return []
    return result if area(result) > 0 else result[::-1]


def side(point, a, b):
    return (b[0] - a[0]) * (point[1] - a[1]) - (b[1] - a[1]) * (point[0] - a[0])


def cut(poly, a, b, inside=True):
    if not poly:
        return []
    result = []
    previous = poly[-1]
    old_side = side(previous, a, b)
    old_inside = old_side >= 0 if inside else old_side <= 0
    for current in poly:
        new_side = side(current, a, b)
        new_inside = new_side >= 0 if inside else new_side <= 0
        if new_inside != old_inside:
            t = old_side / (old_side - new_side)
            result.append((previous[0] + t * (current[0] - previous[0]),
                           previous[1] + t * (current[1] - previous[1])))
        if new_inside:
            result.append(current)
        previous, old_side, old_inside = current, new_side, new_inside
    return normalize(result)


def intersection(subject, clip):
    result = subject
    for a, b in zip(clip, clip[1:] + clip[:1]):
        result = cut(result, a, b)
    return result


def subtract(subject, clip):
    remainder, result = subject, []
    for a, b in zip(clip, clip[1:] + clip[:1]):
        outside = cut(remainder, a, b, False)
        if outside:
            result.append(outside)
        remainder = cut(remainder, a, b)
        if not remainder:
            break
    return result


def cube(x, bottom):
    p, r, l = (x, bottom), (x + 24, bottom - 24), (x - 24, bottom - 24)
    t, tr, tl, back = (x, bottom - 64), (x + 24, bottom - 88), (x - 24, bottom - 88), (x, bottom - 112)
    return [normalize([t, tr, back, tl]), normalize([p, r, tr, t]), normalize([p, t, tl, l])]


def inside_sample(poly, x, y):
    # Pixel centers, with left-inclusive/right-exclusive edge ownership.
    for a, b in zip(poly, poly[1:] + poly[:1]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        value = dx * (2 * y + 1 - 2 * a[1]) - dy * (2 * x + 1 - 2 * a[0])
        if value < 0 or value == 0 and not (dy < 0 or dy == 0 and dx > 0):
            return False
    return True


def expected_material(face_a, face_b):
    if face_a is None:
        return (12, 4, 8)[face_b] if face_b is not None else 0
    if face_a != 1 or face_b is None:
        return (12, 3, 4)[face_a]
    return (7, 4, 5)[face_b]


def frame(phase):
    x = 82 + 2 * math.floor(3 * math.sin(phase * math.tau / 16) + 0.5)
    y = 132 + 2 * math.floor(2 * math.cos(phase * math.tau / 16) + 0.5)
    a_faces, b_faces = cube(44, 156), cube(x, y)
    fragments = []
    for face_a, original in enumerate(a_faces):
        pieces = [original]
        for b in b_faces:
            pieces = [part for piece in pieces for part in subtract(piece, b)]
        fragments.extend((expected_material(face_a, None), piece) for piece in pieces)
        for face_b, b in enumerate(b_faces):
            common = intersection(original, b)
            if common:
                fragments.append((expected_material(face_a, face_b), common))
    for face_b, original in enumerate(b_faces):
        pieces = [original]
        for a in a_faces:
            pieces = [part for piece in pieces for part in subtract(piece, a)]
        fragments.extend((expected_material(None, face_b), piece) for piece in pieces)
    fragments.sort(key=lambda part: (-max(point[0] for point in part[1]), min(point[1] for point in part[1]), part[0]))
    integers = []
    for material, poly in fragments:
        assert all(value.denominator == 1 for point in poly for value in point)
        vertices = [tuple(int(value) for value in point) for point in poly]
        assert all(0 <= px <= 128 and 0 <= py <= 160 for px, py in vertices)
        assert all(dx == 0 or dy == 0 or abs(dx) == abs(dy)
                   for (x0, y0), (x1, y1) in zip(vertices, vertices[1:] + vertices[:1])
                   for dx, dy in [(x1 - x0, y1 - y0)])
        integers.append((material, vertices))
    return a_faces, b_faces, integers


def main():
    BUILD.mkdir(parents=True, exist_ok=True)
    stream, offsets, records = bytearray(), [], []
    for phase in range(16):
        a_faces, b_faces, fragments = frame(phase)
        a_faces = [[tuple(map(int, point)) for point in poly] for poly in a_faces]
        b_faces = [[tuple(map(int, point)) for point in poly] for poly in b_faces]
        offsets.append(len(stream))
        stream.append(len(fragments))
        boundary_cells = {(28, 0)}
        masks = []
        for material, poly in fragments:
            stream.extend((material, len(poly)))
            for a, b in zip(poly, poly[1:] + poly[:1]):
                stream.extend((*a, *b))
            mask = {(x, y) for y in range(160) for x in range(128) if inside_sample(poly, x, y)}
            masks.append(mask)
            touched = {(x // 4, y // 8) for x, y in mask}
            for cx, cy in touched:
                if any((x, y) not in mask for y in range(cy * 8, cy * 8 + 8) for x in range(cx * 4, cx * 4 + 4)):
                    boundary_cells.add((cx, cy))
        for y in range(160):
            for x in range(128):
                aa = [i for i, poly in enumerate(a_faces) if inside_sample(poly, x, y)]
                bb = [i for i, poly in enumerate(b_faces) if inside_sample(poly, x, y)]
                actual = [material for (material, poly), mask in zip(fragments, masks) if (x, y) in mask]
                assert len(aa) <= 1 and len(bb) <= 1 and len(actual) <= 1
                expected = expected_material(aa[0] if aa else None, bb[0] if bb else None)
                assert actual == ([expected] if aa or bb else []), (phase, x, y, expected, actual)
        assert len(boundary_cells) <= 243, (phase, len(boundary_cells))
        records.append({"phase": phase, "fragment_count": len(fragments),
                        "private_boundary_cells": len(boundary_cells),
                        "cube_a": [[list(map(int, point)) for point in poly] for poly in a_faces],
                        "cube_b": [[list(map(int, point)) for point in poly] for poly in b_faces],
                        "fragments": [{"material": material, "vertices": poly} for material, poly in fragments]})
    assert len(stream) < 0x5000
    (BUILD / "scene.bin").write_bytes(stream)
    (BUILD / "scene-offsets.inc").write_text(
        "poseLow: .byte " + ",".join(f"<(sceneData+{offset})" for offset in offsets) + "\n"
        + "poseHigh: .byte " + ",".join(f">(sceneData+{offset})" for offset in offsets) + "\n")
    (BUILD / "geometry.json").write_text(json.dumps({"frames": records, "scene_bytes": len(stream),
                                                    "offsets": offsets, "patterns": PATTERNS}, indent=2) + "\n")
    print(json.dumps({"poses": 16, "scene_bytes": len(stream),
                      "fragment_counts": [record["fragment_count"] for record in records],
                      "private_boundary_cells": [record["private_boundary_cells"] for record in records]}))


if __name__ == "__main__":
    main()
