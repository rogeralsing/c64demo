#!/usr/bin/env python3
"""Verify multicolor polygon boundaries and XOR filling on the emulated C64."""

import argparse
from contextlib import contextmanager
from fractions import Fraction
from itertools import combinations
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import socket
import subprocess

from PIL import GifImagePlugin, Image

from verify import Monitor, connect_monitor, geometry_reference, read_labels, vice_command
from verify import visible_faces_reference


WIDTH, HEIGHT = 64, 128
HERE = Path(__file__).resolve().parent
DITHER_PATTERNS = ((0x00, 0x66, 0xbb, 0xdd), (0x00, 0x99, 0xee, 0x77))
BAYER_RANKS = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))
GOURAUD_RANKS = ((0, 4, 1, 5), (6, 2, 7, 3))
Q6_SINE = tuple(math.floor(64 * math.sin(angle * math.tau / 256) + 0.5) for angle in range(256))


def face_quads():
    """Generate the six outward face windings from binary cube coordinates."""
    for axis in range(3):
        u, v = 1 << ((axis + 1) % 3), 1 << ((axis + 2) % 3)
        for side in range(2):
            origin = side << axis
            first, second = (u, v) if side else (v, u)
            yield (origin, origin | first, origin | first | second, origin | second), axis + 1


class ReferenceModel:
    """Validate model inputs against an independently derived convex hull."""

    def __init__(self, name, original, labels, dither=False, tonal=False, gouraud=False, fast_solid=False):
        self.name = name
        self.dither = dither
        self.tonal = tonal
        self.gouraud = gouraud
        self.fast_solid = fast_solid
        self.immutable = []
        self.runtime_immutable = []
        self.shader = None
        self.shader_buffer = None
        if name == "cube":
            self.vertex_count = 8
            self.faces, self.colors = zip(*face_quads())
            self.edge_count = 12
            self.geometry_tolerance = 3
            return
        self.vertex_count, self.edge_count = 12, 30
        # The 29/20 post-projection zoom has a separately audited all-angle
        # physical pixel-footprint error bound of 4.726370 pixels.
        self.geometry_tolerance = 4.8
        load = int.from_bytes(original[:2], "little")

        def data(label, count, immutable=True):
            first = labels[label]
            image = original[2 + first - load:2 + first - load + count]
            if len(image) != count:
                raise AssertionError(f"Model data {label} lies outside the PRG image.")
            if immutable:
                self.immutable.append((first, image))
            return image

        if dither:
            for parity, name in enumerate(("ditherPatternEven", "ditherPatternOdd")):
                if data(name, 4) != bytes(DITHER_PATTERNS[parity]):
                    raise AssertionError(f"{name} differs from the fixed material contract.")
            if data("ditherPairMasks", 4) != bytes((0xc0, 0x30, 0x0c, 0x03)):
                raise AssertionError("Dither pair masks differ from four physical multicolor lanes.")
        if tonal:
            if data("tonalGradientMask", HEIGHT) != tonal_masks_reference():
                raise AssertionError("Tonal masks differ from the physical-Y Bayer density contract.")
            start, end = labels["tonalShaderCodeStart"], labels["tonalShaderCodeEnd"]
            image = data("tonalShaderCodeStart", end - start, immutable=False)
            cells = labels["tonalShadeCells"]
            if labels["tonalShadeCellsEnd"] - cells != 16 * 8 or not start <= cells < cells + 128 <= end:
                raise AssertionError("Tonal cells lie outside their fixed shader code range.")
            operands = []
            for column in range(16):
                pc = cells + 8 * column
                cell = image[pc - start:pc - start + 8]
                expected_low = (column & 1) * 128
                if (len(cell) != 8 or (cell[0], cell[3], cell[4], cell[5]) != (0xb9, 0x25, 0xd3, 0x99)
                        or cell[1] != expected_low or cell[6] != expected_low
                        or cell[2] != cell[7] or cell[2] != 0x20 + column // 2):
                    raise AssertionError(f"Tonal cell {column} is not a matching charset read/mask/store.")
                operands.extend(((pc + 2, column), (pc + 7, column)))
            self.shader = start, image, operands
            for low_start, low_end in (("tonalLowCodeStart", "tonalLowCodeEnd"),):
                if low_start in labels and low_end in labels:
                    data(low_start, labels[low_end] - labels[low_start])
        if gouraud:
            expected_light = bytes(gouraud_intensity(value if value < 128 else value - 256)
                                   for value in range(256))
            if data("gouraudLightTable", 256) != expected_light:
                raise AssertionError("Gouraud light table differs from the radial-normal/light dot contract.")
            data("gouraudCodeStart", labels["gouraudCodeEnd"] - labels["gouraudCodeStart"])
            data("gouraudTablesStart", labels["gouraudTablesEnd"] - labels["gouraudTablesStart"])
            data("gouraudFillFrame", labels["gouraudFrameFilled"] + 1 - labels["gouraudFillFrame"])
        if fast_solid:
            sine = reference_sine()
            if data("sineUnit", 256) != bytes(value & 255 for value in sine):
                raise AssertionError("Fast rotation coefficients differ from the original Q6 sine table.")
            expected_quarters = bytes((value if value < 128 else value - 256) ** 2 // 256
                                      for value in range(256))
            if data("quarterSquares", 256) != expected_quarters:
                raise AssertionError("Original Q6 quarter-square rounding table changed.")
            expected_depth = bytes(math.floor(8192 / (80 + index) + 0.5) for index in range(128))
            if data("depthFactors", 128) != expected_depth:
                raise AssertionError("Original reciprocal-depth rounding table changed.")
            for prefix in ("fastRotation", "fastProjection"):
                data(prefix + "CodeStart", labels[prefix + "CodeEnd"] - labels[prefix + "CodeStart"])
            products = b''.join(bytes(q6_product(coordinate, coefficient) & 255 for coefficient in sine)
                                for coordinate in (21, 34))
            if (labels["fastRotationTablesStart"], labels["fastRotationTablesEnd"],
                    labels["fastProduct21"], labels["fastProduct34"]) != (0xe000, 0xe200, 0xe000, 0xe100):
                raise AssertionError("Unexpected fast rotation table ownership.")
            self.runtime_immutable.append((0xe000, products))
            if (labels["fastProjectionTablesStart"], labels["fastProjectionTablesEnd"],
                    labels["fastProjectionOffsets"], labels["fastProjectionRowLo"], labels["fastProjectionRowHi"]) != (
                    0xe200, 0xfe00, 0xe200, 0xfc00, 0xfd00):
                raise AssertionError("Unexpected fast projection table ownership.")
            projection = bytearray(0x1c00)  # Includes the zero gap and all pointer slots.
            for z in range(-40, 41):
                row = 0xe200 + (z + 40) * 81
                projection[0x1a00 + (z & 255)] = row & 255
                projection[0x1b00 + (z & 255)] = row >> 8
                for coordinate in range(-40, 41):
                    depth = math.floor(8192 / (144 + z) + 0.5)
                    offset = (29 * q6_product(coordinate, depth) + 10) // 20
                    projection[row - 0xe200 + coordinate + 40] = (offset + 64) & 255
            self.runtime_immutable.append((0xe200, bytes(projection)))
            if labels["fastProjectionStateEnd"] - labels["fastProjectionStateStart"] != 1:
                raise AssertionError("Unexpected projection initializer state ownership.")
            self.runtime_immutable.append((labels["fastProjectionStateStart"], bytes((41,))))

        zoom = data("icosahedronZoom", 256)
        expected_zoom = bytes(((29 * (value if value < 128 else value - 256) + 10) // 20) & 255
                              for value in range(256))
        if zoom != expected_zoom:
            raise AssertionError("Signed 29/20 projection zoom differs from floor((29*v+10)/20).")
        # Floor division includes the asymmetric half cases: -10 maps to -14,
        # while +10 maps to +15. The full byte table is also immutable at runtime.

        coordinates = [data(f"model{axis}", 12) for axis in "XYZ"]
        self.coordinates = [tuple(value if value < 128 else value - 256 for value in vertex)
                            for vertex in zip(*coordinates)]
        expected = {(0, a, b) for a in (-21, 21) for b in (-34, 34)}
        expected |= {(a, b, 0) for a in (-21, 21) for b in (-34, 34)}
        expected |= {(b, 0, a) for a in (-21, 21) for b in (-34, 34)}
        if len(set(self.coordinates)) != 12 or set(self.coordinates) != expected:
            raise AssertionError("Icosahedron inputs differ from the specified integer vertex set.")

        def subtract(a, b):
            return tuple(x - y for x, y in zip(a, b))

        def cross(a, b):
            return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
                    a[0] * b[1] - a[1] * b[0])

        def dot(a, b):
            return sum(x * y for x, y in zip(a, b))

        def canonical(face):
            return min(face[index:] + face[:index] for index in range(3))

        hull = set()
        for face in combinations(range(12), 3):
            p, q, r = (self.coordinates[index] for index in face)
            normal = cross(subtract(q, p), subtract(r, p))
            sides = [dot(normal, subtract(point, p)) for point in self.coordinates]
            if all(side <= 0 for side in sides):
                hull.add(canonical(face))
            elif all(side >= 0 for side in sides):
                hull.add(canonical((face[0], face[2], face[1])))
        face_indices = [data(f"modelFace{axis}", 20) for axis in "ABC"]
        self.faces = [tuple(face) for face in zip(*face_indices)]
        if len(hull) != 20 or {canonical(face) for face in self.faces} != hull:
            raise AssertionError("Model faces differ from the independently derived outward convex hull.")
        self.colors = list(data("modelFaceColor", 20))
        if any(color not in (1, 2, 3) for color in self.colors):
            raise AssertionError("Every model face must select a visible multicolor code.")
        adjacency = {}
        for index, face in enumerate(self.faces):
            for first, last in zip(face, face[1:] + face[:1]):
                adjacency.setdefault(tuple(sorted((first, last))), []).append((index, first, last))
        if len(adjacency) != 30 or 12 - len(adjacency) + len(hull) != 2:
            raise AssertionError("Icosahedron topology violates its edge count or Euler characteristic.")
        for entries in adjacency.values():
            if len(entries) != 2 or entries[0][1:] != entries[1][1:][::-1]:
                raise AssertionError("A model edge must have two oppositely oriented adjacent faces.")
            if self.colors[entries[0][0]] == self.colors[entries[1][0]]:
                raise AssertionError("Adjacent faces need distinct colors to retain every shared edge.")
        edge_indices = [data(f"modelEdge{field}", 30) for field in ("A", "B", "FaceA", "FaceB")]
        seen = set()
        for first, last, face_a, face_b in zip(*edge_indices):
            edge = tuple(sorted((first, last)))
            if edge in seen or edge not in adjacency or {face_a, face_b} != {item[0] for item in adjacency[edge]}:
                raise AssertionError("Runtime edge/face adjacency differs from the independent hull.")
            seen.add(edge)
        for name in ("cullDepthCode", "xorEdgeDispatch", "fastCullCode", "fastBoundsCode"):
            if name + "Start" in labels:
                data(name + "Start", labels[name + "End"] - labels[name + "Start"])

    def check_immutable(self, ram):
        for first, image in self.immutable:
            if ram[first:first + len(image)] != image:
                raise AssertionError(f"Immutable model data or renderer code changed at ${first:04x}.")
        for first, image in self.runtime_immutable:
            if ram[first:first + len(image)] != image:
                raise AssertionError(f"Generated arithmetic table differs from original Q6 math at ${first:04x}.")
        if self.shader is not None:
            first, image, operands = self.shader
            expected = bytearray(image)
            if self.shader_buffer is not None:
                for address, column in operands:
                    expected[address - first] = (self.shader_buffer >> 8) + column // 2
            if ram[first:first + len(image)] != expected:
                raise AssertionError("Tonal shader code or exact charset high operands changed unexpectedly.")

    def expect_shaded(self, draw):
        if not self.tonal or draw not in (0x2000, 0x2800):
            raise AssertionError("Unexpected tonal shader buffer.")
        self.shader_buffer = draw

    def geometry(self, yaw, pitch):
        if self.name == "cube":
            return geometry_reference(yaw, pitch)
        yaw, pitch = yaw * math.tau / 256, pitch * math.tau / 256
        cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
        result = []
        for x, y, z in self.coordinates:
            x, z = cy * x + sy * z, -sy * x + cy * z
            y, z = cp * y - sp * z, sp * y + cp * z
            result.append((64 + (128 * 29 / 20) * x / (144 + z),
                           64 - (128 * 29 / 20) * y / (144 + z)))
        return result

    def visibility(self, vertices):
        if self.name == "cube":
            mask = visible_faces_reference(vertices)
            return [bool(mask & (1 << face)) for face in range(6)]
        result = []
        for face in self.faces:
            p, q, r = (vertices[index] for index in face[:3])
            result.append((q[0] - p[0]) * (r[1] - p[1]) -
                          (q[1] - p[1]) * (r[0] - p[0]) >= 0)
        return result

    def materials(self, vertices, visible, face_materials=None):
        colors = self.colors if face_materials is None else face_materials
        return polygon_reference([(tuple(vertices[index] for index in face), color)
                                  for face, color, shown in zip(self.faces, colors, visible) if shown])

    def canvas(self, vertices, visible):
        material_ids = self.materials(vertices, visible)
        return (dither_reference(material_ids) if self.dither else
                tonal_reference(material_ids) if self.tonal else material_ids)


def dither_reference(material_ids, row_parity=None):
    """Paint direct face interiors using fixed physical-row/X-lane materials.

    This reads neither runtime pattern tables nor edge/prefix state. An optional
    fixed parity is used only to evaluate an ignored even-field terminal across
    rows126/127 without introducing an unrelated odd-row pattern transition.
    """
    return bytearray((DITHER_PATTERNS[(y & 1) if row_parity is None else row_parity]
                                   [material_ids[y * WIDTH + x]] >> (6 - 2 * (x & 3))) & 3
                     for y in range(HEIGHT) for x in range(WIDTH))


def tonal_density(y):
    return max(0, min(16, 16 - ((y - 8) * 17 // 112)))


def tonal_reference(material_ids):
    """Tone direct face interiors; one Bayer cell owns one two-pixel MC sample."""
    return bytearray(material_ids[y * WIDTH + x] if BAYER_RANKS[y & 3][x & 3] < tonal_density(y) else 0
                     for y in range(HEIGHT) for x in range(WIDTH))


def tonal_masks_reference():
    return bytes(sum(3 << (6 - 2 * lane) for lane in range(4)
                     if BAYER_RANKS[y & 3][lane] < tonal_density(y)) for y in range(HEIGHT))


def gouraud_intensity(normal_dot_numerator):
    """Quantized radial normal dotted with camera-space light (0,1,-1)/sqrt2."""
    diffuse = math.floor(7 * max(0, normal_dot_numerator) / math.sqrt(3194) + 0.5)
    return max(1, min(8, 1 + diffuse))


def gouraud_polygons_reference(polygons):
    """Direct exact-coverage triangles and barycentric intensity, no clip/DDA.

    Each input is (three projected points, their shared vertex intensities,
    material). The existing XOR composition is retained for any quantized face
    overlap. X is a logical two-pixel multicolor sample; Y is a physical row.
    """
    canvas = bytearray(WIDTH * HEIGHT)
    for polygon, intensities, material in polygons:
        a, b, c = polygon
        area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if not area:
            continue
        coverage = polygon_reference([(polygon, 1)])
        for index, covered in enumerate(coverage):
            if not covered:
                continue
            y, x = divmod(index, WIDTH)
            wa = (b[0] - x) * (c[1] - y) - (b[1] - y) * (c[0] - x)
            wb = (c[0] - x) * (a[1] - y) - (c[1] - y) * (a[0] - x)
            wc = area - wa - wb
            numerator = wa * intensities[0] + wb * intensities[1] + wc * intensities[2]
            # I >= rank+1, retaining exact equality without a rounded quotient.
            if (numerator >= (GOURAUD_RANKS[y & 1][x & 3] + 1) * area if area > 0 else
                    numerator <= (GOURAUD_RANKS[y & 1][x & 3] + 1) * area):
                canvas[index] ^= material
    return canvas


def gouraud_reference(model, vertices, visible, vertex_intensities):
    return gouraud_polygons_reference([
        (tuple(vertices[index] for index in face), tuple(vertex_intensities[index] for index in face), material)
        for face, material, shown in zip(model.faces, model.colors, visible) if shown])


def reference_sine():
    return Q6_SINE


def q6_product(first, second):
    """Original signed quarter-square difference, not generic shifted multiply."""
    if not (-128 <= first + second < 128 and -128 <= first - second < 128):
        raise AssertionError("Original Q6 product exceeds its signed table-index domain.")
    return (first + second) ** 2 // 256 - (first - second) ** 2 // 256


def direct_rotation_reference(coordinates, yaw, pitch):
    """Original eight-product path independently evaluated for every vertex."""
    sy, cy = Q6_SINE[yaw], Q6_SINE[(yaw + 64) & 255]
    sp, cp = Q6_SINE[pitch], Q6_SINE[(pitch + 64) & 255]
    result = []
    for x, y, z in coordinates:
        rx = q6_product(x, cy) + q6_product(z, sy)
        intermediate_z = q6_product(z, cy) - q6_product(x, sy)
        ry = q6_product(y, cp) - q6_product(intermediate_z, sp)
        rz = q6_product(y, sp) + q6_product(intermediate_z, cp)
        result.append((rx, ry, rz))
    return result


def direct_projection_reference(rotated):
    """Original reciprocal depth, Q6 multiply and signed29/20 zoom order."""
    result = []
    for x, y, z in rotated:
        factor = math.floor(8192 / (144 + z) + 0.5)
        dx = (29 * q6_product(x, factor) + 10) // 20
        dy = (29 * q6_product(y, factor) + 10) // 20
        result.append((((dx + 64) & 255) >> 1, (64 - dy) & 255))
    return result


def fast_face_materials(rotated, faces, visible, fixed_materials):
    """Fixed model materials; independent original geometry supplies diagnostics."""
    depths = [sum(rotated[vertex][2] for vertex in face) for face in faces]
    colors = [material if shown else 0 for material, shown in zip(fixed_materials, visible)]
    return depths, colors


def fast_rotation_candidate(yaw, pitch, product21, product34):
    """Candidate algebra for the host identity audit; never the native oracle."""
    a, b = product21[(yaw + 64) & 255], product34[(yaw + 64) & 255]
    c, d = product21[yaw], product34[yaw]
    e, f = product21[(pitch + 64) & 255], product21[pitch]
    g, h = product34[(pitch + 64) & 255], product34[pitch]
    sp, cp = Q6_SINE[pitch], Q6_SINE[(pitch + 64) & 255]
    sb, cb = q6_product(b, sp), q6_product(b, cp)
    sc, cc = q6_product(c, sp), q6_product(c, cp)
    splus, cplus = q6_product(a + d, sp), q6_product(a + d, cp)
    sminus, cminus = q6_product(a - d, sp), q6_product(a - d, cp)
    result = [None] * 12
    for first, opposite, value in ((3, 0, (d, e - sb, f + cb)), (2, 1, (-d, e + sb, f - cb)),
                                   (7, 4, (a, g + sc, h - cc)), (5, 6, (-a, g - sc, h + cc)),
                                   (11, 8, (b + c, -sminus, cminus)), (9, 10, (c - b, -splus, cplus))):
        result[first] = value
        result[opposite] = tuple(-component for component in value)
    return result


def verify_rotation_audit(program, labels, output):
    original = program.read_bytes()
    model = ReferenceModel("icosahedron", original, labels, fast_solid=True)
    p21 = tuple(q6_product(21, coefficient) for coefficient in Q6_SINE)
    p34 = tuple(q6_product(34, coefficient) for coefficient in Q6_SINE)
    digest = hashlib.sha256()
    maximum = [0, 0, 0]
    for yaw in range(256):
        for pitch in range(256):
            expected = direct_rotation_reference(model.coordinates, yaw, pitch)
            candidate = fast_rotation_candidate(yaw, pitch, p21, p34)
            if candidate != expected:
                raise AssertionError(f"Fixed-model algebra changes original rotation at {yaw},{pitch}.")
            for vertex in expected:
                for axis, value in enumerate(vertex):
                    maximum[axis] = max(maximum[axis], abs(value))
            digest.update(bytes(value & 255 for vertex in expected for value in vertex))
    if any(value > 40 for value in maximum):
        raise AssertionError("The full-angle original rotation exceeds the fast projection table domain.")
    report = {"pass": True, "program_sha256": hashlib.sha256(original).hexdigest(),
              "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "yaw_pitch_pairs": 65536, "vertex_comparisons": 65536 * 12,
              "coordinate_comparisons": 65536 * 12 * 3, "maximum_absolute_rotated_xyz": maximum,
              "ordered_original_coordinates_sha256": digest.hexdigest(),
              "reference": "original eight independent Q6 products per vertex",
              "candidate": "four yaw-Z bases, eight dynamic pitch products, exact antipodal pairs",
              "scope": "Host arithmetic identity across all angle pairs; no assembled CPU/native execution of all poses. "
                       "Actual generated RAM tables and native XYZ/projection are checked by the native verifier."}
    output.mkdir(parents=True, exist_ok=True)
    (output / "rotation-audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


def selected_field(full_canvas, retained_canvas, parity):
    mixed = bytearray(retained_canvas)
    for row in range(parity, HEIGHT, 2):
        mixed[row * WIDTH:(row + 1) * WIDTH] = full_canvas[row * WIDTH:(row + 1) * WIDTH]
    return mixed


def polygon_reference(polygons):
    """Direct odd-even polygon coverage at integer samples, using exact intersections.

    The X sample owns edges whose left endpoint is inclusive and right endpoint
    is exclusive. Integer Y samples own the lower intersection, not the upper.
    This computes face interiors directly; it never performs a prefix fill.
    """
    canvas = bytearray(WIDTH * HEIGHT)
    for polygon, color in polygons:
        for x in range(WIDTH):
            intersections = []
            for p, q in zip(polygon, polygon[1:] + polygon[:1]):
                if min(p[0], q[0]) <= x < max(p[0], q[0]):
                    intersections.append(Fraction(p[1]) + Fraction((q[1] - p[1]) * (x - p[0]),
                                                                   q[0] - p[0]))
            intersections.sort()
            if len(intersections) % 2:
                raise AssertionError("A closed polygon produced an odd number of intersections.")
            for lower, upper in zip(intersections[::2], intersections[1::2]):
                for y in range(max(0, math.ceil(lower)), min(HEIGHT, math.ceil(upper))):
                    canvas[y * WIDTH + x] ^= color
    return canvas


def cube_reference(vertices, visible_faces):
    return polygon_reference([(tuple(vertices[index] for index in quad), color)
                              for face, (quad, color) in enumerate(face_quads())
                              if visible_faces & (1 << face)])


def decode_charset(charset):
    return bytearray((charset[(x // 4) * HEIGHT + y] >> (6 - 2 * (x % 4))) & 3
                     for y in range(HEIGHT) for x in range(WIDTH))


def encode_canvas(canvas):
    charset = bytearray(2048)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            charset[(x // 4) * HEIGHT + y] |= canvas[y * WIDTH + x] << (6 - 2 * (x % 4))
    return charset


def marker_reference(canvas):
    """Invert the independently computed interiors to locate expected transitions."""
    packed = encode_canvas(canvas)
    return bytes(packed[column * HEIGHT + y] ^ (packed[column * HEIGHT + y - 1] if y else 0)
                 for column in range(16) for y in range(HEIGHT))


def closure_errors(markers):
    errors = {}
    for column in range(16):
        parity = 0
        for value in markers[column * HEIGHT:(column + 1) * HEIGHT]:
            parity ^= value
        if parity:
            errors[column] = parity
    return errors


def interlaced_reference(full_canvas, retained_canvas, parity, terminal_canvas=None, virtual_terminal=False):
    """Select rows from full interiors, then derive this field's transitions.

    The terminal sink is derived from the full-resolution transition at row127.
    It is independent of the runtime crossing-to-field address lookup tables.
    """
    mixed = selected_field(full_canvas, retained_canvas, parity)
    packed = encode_canvas(full_canvas)
    terminal_packed = packed if terminal_canvas is None else encode_canvas(terminal_canvas)
    markers = bytearray(2048)
    last_colors, sink = [], 0
    for column in range(16):
        previous = 0
        for row in range(parity, HEIGHT, 2):
            current = packed[column * HEIGHT + row]
            markers[column * HEIGHT + row] = current ^ previous
            previous = current
        last_colors.append(previous)
        if virtual_terminal:
            sink ^= previous
        elif parity == 0:
            sink ^= terminal_packed[column * HEIGHT + 127] ^ terminal_packed[column * HEIGHT + 126]
    return mixed, bytes(markers), sink, last_colors


def coherent_field_reference(full_canvas):
    """Both internal field-marker sets describe the same complete pose."""
    fields = [interlaced_reference(full_canvas, bytes(WIDTH * HEIGHT), parity, virtual_terminal=True)
              for parity in (0, 1)]
    markers = bytes(even ^ odd for even, odd in zip(fields[0][1], fields[1][1]))
    return markers, fields[0][2] ^ fields[1][2], fields


def interlaced_closure_errors(markers, last_colors, parity):
    # An ignored transition below the final selected row is a virtual terminal.
    # XOR of stored markers alone need not be zero when that row is colored.
    errors = {}
    for column in range(16):
        value = last_colors[column]
        for row in range(parity, HEIGHT, 2):
            value ^= markers[column * HEIGHT + row]
        if value:
            errors[column] = value
    return errors


def dirty_bounds(ram, labels, slot):
    return tuple(ram[labels[name] + slot] for name in (
        "dirtyMinColumn", "dirtyMinRow", "dirtyMaxColumn", "dirtyMaxRow"))


def union_bounds_reference(current, previous):
    if previous is None:
        return current
    return (min(current[0], previous[0]), min(current[1], previous[1]),
            max(current[2], previous[2]), max(current[3], previous[3]))


def interlaced_q_bounds(bounds, parity):
    # Include the closing marker even when its physical row is just beyond maxY.
    return (bounds[1] + 1 - parity) // 2, min(63, (bounds[3] + 1 - parity) // 2)


def check_interlaced_fill(ram, labels, bounds, parity, terminal=0):
    expected = interlaced_q_bounds(bounds, parity)
    actual = ram[labels["interlaceMinQ"]], ram[labels["interlaceMaxQ"]]
    if actual != expected:
        raise AssertionError(f"Field cleanup rows {actual} differ from closing-marker bounds {expected}.")
    if ram[labels["interlaceTerminalMarker"]] != terminal:
        raise AssertionError("The ignored terminal-marker sink differs from the expected fill-stage value.")
    return expected


def fixtures():
    """Hand-computable shapes exercise half-open edges, slopes, and shared colors."""
    rectangle = ((3, 5), (13, 5), (13, 12), (3, 12))
    triangle = ((2, 2), (8, 8), (2, 8))
    steep = ((4, 2), (6, 14), (10, 14))
    diamond = ((8, 2), (14, 8), (8, 14), (2, 8))
    upper = ((2, 2), (14, 2), (14, 14))
    lower = ((2, 2), (14, 14), (2, 14))
    cases = [
        ("flat rectangle", [(rectangle, 1)], {1: 70}),
        ("reversed rectangle", [(tuple(reversed(rectangle)), 2)], {2: 70}),
        ("diagonal triangle", [(triangle, 3)], {3: 21}),
        ("steep triangle", [(steep, 2)], {2: 24}),
        ("fractional downward slope", [(((3, 2), (10, 13), (3, 13)), 1)], {1: 41}),
        ("fractional upward slope", [(((3, 13), (10, 2), (3, 2)), 2)], {2: 47}),
        ("V corners", [(diamond, 1)], {1: 72}),
        ("shared sloped edge", [(upper, 1), (lower, 2)], {1: 66, 2: 78}),
        ("shared edge reversed", [(tuple(reversed(lower)), 2), (tuple(reversed(upper)), 1)],
         {1: 66, 2: 78}),
        ("last row and byte column", [(((60, 120), (63, 120), (63, 127), (60, 127)), 3)],
         {3: 21}),
    ]
    for index, width in enumerate((1, 2, 4, 8, 16, 32)):
        for remainder, height in enumerate((3 * width, 125)):
            lower, upper = 127 - height, 127
            upward = (index + remainder) % 2
            left, right = 63 - width, 63
            polygon = ((left, upper), (right, lower), (left, lower)) if upward else (
                (left, lower), (right, upper), (left, upper))
            if remainder:
                polygon = tuple(reversed(polygon))
            # Integer lattice counts follow from the standard floor-sum identity.
            # These closed forms do not call the rasterizer or its ceiling loop.
            area = ((height * width + height + width - math.gcd(width, height)) // 2 if upward else
                    ((height - 1) * width + height + math.gcd(width, height)) // 2)
            color = (index + remainder) % 3 + 1
            cases.append((f"division width{width} height{height}", [(polygon, color)], {color: area}))
    for name, polygons, counts in cases:
        expected = polygon_reference(polygons)
        if any(expected.count(color) != count for color, count in counts.items()):
            raise AssertionError(f"Reference disagrees with hand-computed fixture area: {name}.")
        if closure_errors(marker_reference(expected)):
            raise AssertionError(f"Reference fixture is not closed: {name}.")
        yield name, polygons, expected


def read_palette():
    palette_file = HERE / "palettes/colodore.vpl"
    palette = [tuple(int(value, 16) for value in line.split()[:3])
               for line in palette_file.read_text().splitlines()
               if line.strip() and not line.lstrip().startswith("#")]
    return palette_file, palette


@contextmanager
def machine(executable, program, output):
    output.mkdir(parents=True, exist_ok=True)
    palette_file, _ = read_palette()
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    monitor = None
    with (output / "vice.log").open("w") as log:
        process = subprocess.Popen(vice_command(executable, program, port, palette_file),
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            with connect_monitor(process, port) as connection:
                monitor = Monitor(connection)
                monitor.run("r")
                yield monitor
        finally:
            if monitor:
                (output / "monitor.log").write_text("\n".join(monitor.transcript))
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


def write_memory(monitor, address, data):
    monitor.run(f"> {address:04x} " + " ".join(f"{value:02x}" for value in data))


def prepare_fast_boundary_fixture(monitor, labels, high):
    """Declared FAST primitive prerequisites normally supplied by its caller.

    Tests choose a buffer directly, so supply its immutable dispatch-table
    address and fill-bank high byte, and the documented zero pointer-low byte.
    These are controlled routine inputs, not expected marker/output bytes.
    """
    suffix = "A" if high == 0x20 else "B"
    table = labels["xorBoundaryTable" + suffix]
    bank = labels["xorFillKernels" + suffix] >> 8
    write_memory(monitor, labels["fastBoundaryStateStart"], [table & 255, table >> 8, bank])
    write_memory(monitor, labels["xorPointer"], [0])


def call(monitor, address, measure=False, checkpoints=None):
    # This stub uses the BASIC input buffer after the demo has disabled the ROMs.
    # It is ordinary debugger code, not a special entry point in the program.
    write_memory(monitor, 0x0200, [0x20, address & 255, address >> 8, 0x4c, 0x03, 0x02])
    before_cycles = monitor.registers()[2] if measure else None
    monitor.run("g 0200")
    pc, _, cycles = monitor.registers()
    while checkpoints and pc in checkpoints:
        checkpoints[pc]()
        monitor.run("x")
        pc, _, cycles = monitor.registers()
    if pc != 0x0203:
        raise AssertionError(f"Fixture routine did not return: ${pc:04x}.")
    return cycles - before_cycles if measure else None


def boundary_cases():
    """Cover specialized widths and nearby general-division controls systematically."""
    for width in (1, 2, 3, 4, 7, 8, 16, 31, 32):
        for slope_kind, height in (("horizontal", 0), ("exact", 3 * width), ("long", 125)):
            for upward in ((False,) if not height else (False, True)):
                left, right, lower, upper = 63 - width, 63, 127 - height, 127
                start = (left, upper if upward else lower)
                end = (right, lower if upward else upper)
                for reversed_endpoints in (False, True):
                    for color in (1, 2, 3):
                        yield {"width": width, "height": height, "slope_kind": slope_kind,
                               "upward": upward, "reversed": reversed_endpoints, "color": color,
                               "start": end if reversed_endpoints else start,
                               "end": start if reversed_endpoints else end}
    # The original matrix ends at X=63. Sweep every other reachable endpoint
    # without repeating every width, checking all color-specialized sentinels.
    for end_x in range(2, 63):
        upward = bool(end_x & 1)
        for color in (1, 2, 3):
            yield {"width": 2, "height": 3, "slope_kind": "x_lane_sentinel",
                   "upward": upward, "reversed": False, "color": color,
                   "start": (end_x - 2, 38 if upward else 35),
                   "end": (end_x, 35 if upward else 38)}
    # Full chains visit every X lane in both Y directions, including transitions
    # between byte columns and generated code pages, for all six color/bank sets.
    for upward in (False, True):
        start, end = (0, 114 if upward else 13), (63, 13 if upward else 114)
        for reversed_endpoints in (False, True):
            for color in (1, 2, 3):
                yield {"width": 63, "height": 101, "slope_kind": "x_lane_chain",
                       "upward": upward, "reversed": reversed_endpoints, "color": color,
                       "start": end if reversed_endpoints else start,
                       "end": start if reversed_endpoints else end}


def boundary_reference(start, end, color):
    """Evaluate the mathematical ceiling independently at every owned X sample."""
    if start[0] > end[0]:
        start, end = end, start
    canvas = bytearray(WIDTH * HEIGHT)
    for x in range(start[0], end[0]):
        y = math.ceil(Fraction(start[1]) + Fraction((end[1] - start[1]) * (x - start[0]),
                                                  end[0] - start[0]))
        canvas[y * WIDTH + x] = color
    return encode_canvas(canvas)


class PrefixImage:
    """Decode marker ownership from literal output stores in the loaded program.

    Immediate operands may change while edges are pending. Every other code byte
    remains checked, including each reset store's address and temporary sentinel.
    """

    def __init__(self, original, labels, interlaced=False):
        self.first, self.last = labels["xorFillKernelsStart"], labels["xorFillKernelsEnd"]
        load = int.from_bytes(original[:2], "little")
        self.image = original[2 + self.first - load:2 + self.last - load]
        self.operands = {}
        self.tables = []
        if self.image[0] != 0x49:  # The earlier implementation stores markers in the charset.
            return
        for high, label in ((0x20, "xorFillKernelsA"), (0x28, "xorFillKernelsB")):
            addresses = [None] * 2048
            start = labels[label]
            for offset in range(2048):
                pc = start + offset * 8
                cell = self.image[pc - self.first:pc - self.first + 8]
                if len(cell) != 8 or (cell[0], cell[2], cell[5]) != (0x49, 0x8d, 0x8e):
                    raise AssertionError(f"Invalid EOR/store/reset cell at ${pc:04x}.")
                target = int.from_bytes(cell[3:5], "little") - (high << 8)
                reset = int.from_bytes(cell[6:8], "little")
                if cell[1] or not 0 <= target < 2048 or addresses[target] is not None or reset != pc + 1:
                    raise AssertionError(f"Invalid marker ownership/reset target at ${pc:04x}.")
                addresses[target] = pc + 1
            self.operands[high] = addresses
        if interlaced:
            lows, pages = [], []
            for parity in (0, 1):
                for crossing in range(128):
                    row = (crossing + 1 - parity) // 2
                    if row == 64:
                        low, page = 1, 255
                    else:
                        address = self.operands[0x20][2 * row + parity] - labels["xorFillKernelsA"]
                        low, page = address & 255, address >> 8
                    lows.append(low)
                    pages.append(page)
            for name, expected in (("xorOperandLo", lows), ("xorOperandPage", pages)):
                first = labels[name]
                image = original[2 + first - load:2 + first - load + 256]
                if image != bytes(expected):
                    raise AssertionError(f"{name} disagrees with independently decoded field destinations.")
                self.tables.append((first, image))

    def check_tables(self, ram):
        for first, image in self.tables:
            if ram[first:first + len(image)] != image:
                raise AssertionError("Immutable interlaced crossing/address tables changed.")

    def markers(self, ram, high):
        if self.operands:
            return bytes(ram[address] for address in self.operands[high])
        return ram[high << 8:(high << 8) + 2048]

    def check_pending(self, ram, high, expected):
        self.check_tables(ram)
        if self.markers(ram, high) != expected:
            raise AssertionError("Boundary markers differ from the independent ceiling/interior oracle.")
        if self.operands:
            fixed = bytearray(ram[self.first:self.last])
            for bank, addresses in self.operands.items():
                for address in addresses:
                    if bank != high and ram[address]:
                        raise AssertionError("Boundary drawing changed the opposite marker bank.")
                    fixed[address - self.first] = 0
            if fixed != self.image:
                raise AssertionError("Boundary drawing changed fixed prefix opcodes or store/reset addresses.")

    def check_restored(self, ram):
        self.check_tables(ram)
        if ram[self.first:self.last] != self.image:
            raise AssertionError("Prefix filling did not restore all marker operands and sentinels.")

    def normalize_pending(self, ram):
        for addresses in self.operands.values():
            for address in addresses:
                ram[address] = 0


def full_fixture_bounds(monitor, labels):
    for name in ("dirtyMinColumn", "dirtyMinRow"):
        write_memory(monitor, labels[name], [0, 0])
    write_memory(monitor, labels["dirtyMaxColumn"], [15, 15])
    write_memory(monitor, labels["dirtyMaxRow"], [127, 127])


def boundary_kernel_image(original, labels):
    if "xorBoundaryKernelsStart" not in labels:
        return None
    start, end = labels["xorBoundaryKernelsStart"], labels["xorBoundaryKernelsEnd"]
    load = int.from_bytes(original[:2], "little")
    return start, end, original[2 + start - load:2 + end - load]


def verify_boundary_cases(monitor, labels, output, original, fast_solid=False):
    # Disable display DMA and the private raster clock for instruction-count
    # comparisons. Closed-polygon fixtures above exercise the normal live VIC.
    write_memory(monitor, 0xd011, [0x0b])
    write_memory(monitor, 0xd01a, [0])
    write_memory(monitor, 0xd019, [0x0f])
    # DEN can remain latched for the current frame. Execute a debugger-owned
    # JMP loop for more than one PAL frame before capturing or timing state.
    write_memory(monitor, 0x0200, [0x4c, 0x00, 0x02])
    monitor.run("r pc=$0200")
    settle_start = monitor.registers()[2]
    monitor.run("step $3000")
    settle_cycles = monitor.registers()[2] - settle_start
    if settle_cycles < 19656:
        raise AssertionError("Display DMA did not receive a full emulated PAL frame to settle.")
    allowed = [(0xd0, 0xe0), (labels["linePointer"], labels["squareSum"] + 1),
               (0x0100, 0x0206), (0x2000, 0x3000),
               (labels["drawBufferHi"], labels["drawBufferHi"] + 1),
               (labels["boundaryColor"], labels["boundaryColor"] + 1)]
    if "xorBoundaryDispatch" in labels:
        allowed.append((labels["xorBoundaryDispatch"] + 1, labels["xorBoundaryDispatch"] + 3))
    generated = boundary_kernel_image(original, labels)
    prefix = PrefixImage(original, labels)
    allowed.extend([(labels["fillStateStart"], labels["fillStateEnd"]),
                    (labels["xorFillEntry"] + 1, labels["xorFillEntry"] + 3)])
    if "fastFillEntry" in labels:
        allowed.append((labels["fastFillEntry"] + 1, labels["fastFillEntry"] + 3))
    if fast_solid:
        allowed.append((labels["fastBoundaryStateStart"], labels["fastBoundaryStateEnd"]))
    full_fixture_bounds(monitor, labels)
    monitor.run("bank ram")
    stable_ram = bytearray(monitor.memory(output / "boundary-ram.bin", 0, 0xffff))
    monitor.run("bank cpu")
    for first, last in allowed:
        stable_ram[first:last] = bytes(last - first)
    results = []
    for high in (0x20, 0x28):
        write_memory(monitor, labels["drawBufferHi"], [high])
        opposite = 0x2800 if high == 0x20 else 0x2000
        for case in boundary_cases():
            if fast_solid:
                prepare_fast_boundary_fixture(monitor, labels, high)
            monitor.run("f 2000 2fff 00")
            monitor.run(f"f {opposite:04x} {opposite + 2047:04x} a5")
            for name, value in zip(("lineX0", "lineY0", "lineX1", "lineY1"), (*case["start"], *case["end"])):
                write_memory(monitor, labels[name], [value])
            write_memory(monitor, labels["boundaryColor"], [case["color"]])
            cycles = call(monitor, labels["drawBoundary"], measure=True)
            monitor.run("bank ram")
            ram = monitor.memory(output / "boundary-ram.bin", 0, 0xffff)
            monitor.run("bank cpu")
            expected = boundary_reference(case["start"], case["end"], case["color"])
            prefix.check_pending(ram, high, expected)
            if prefix.operands and any(ram[high << 8:(high << 8) + 2048]):
                raise AssertionError(f"Boundary drawing modified charset output before filling: {case}.")
            if ram[opposite:opposite + 2048] != bytes([0xa5]) * 2048:
                raise AssertionError(f"Boundary fast-path case changed the opposite buffer: {case}.")
            if generated is not None:
                first, last, image = generated
                if ram[first:last] != image:
                    raise AssertionError(f"Generated boundary sentinel was not restored: {case}.")
            stable = bytearray(ram)
            prefix.normalize_pending(stable)  # Exact operands and all fixed bytes were checked above.
            for first, last in allowed:
                stable[first:last] = bytes(last - first)
            if stable != stable_ram:
                address = next(i for i, (a, b) in enumerate(zip(stable, stable_ram)) if a != b)
                raise AssertionError(f"Boundary case wrote outside its workspace at ${address:04x}: {case}.")
            if case["width"] == 1 and not case["reversed"] and cycles > 150:
                raise AssertionError(f"Ordered dx=1 boundary took {cycles} cycles; budget is 150 including JSR/RTS.")
            call(monitor, labels["xorFill"])
            consumed = read_ram(monitor, output)
            prefix.check_restored(consumed)
            if consumed[opposite:opposite + 2048] != bytes([0xa5]) * 2048:
                raise AssertionError(f"Consuming edge markers changed the opposite buffer: {case}.")
            stable = bytearray(consumed)
            for first, last in allowed:
                stable[first:last] = bytes(last - first)
            if stable != stable_ram:
                address = next(i for i, (a, b) in enumerate(zip(stable, stable_ram)) if a != b)
                raise AssertionError(f"Consuming edge markers wrote outside its workspace at ${address:04x}: {case}.")
            results.append({**case, "charset": f"${high:02x}00", "cycles_with_call_return": cycles,
                            "pass": True})
    return results, settle_cycles


def verify_fixtures(program, labels, output, executable, model_name="cube", fast_solid=False):
    boundary_ready = labels.get("boundariesReady", labels.get("boundaryReady"))
    if boundary_ready is None:
        raise ValueError("Missing natural boundary-completion debug label.")
    results = []
    original = program.read_bytes()
    model = ReferenceModel(model_name, original, labels, fast_solid=fast_solid)
    prefix = PrefixImage(original, labels)
    generated = boundary_kernel_image(original, labels)
    with machine(executable, program, output) as monitor:
        monitor.run(f"break {boundary_ready:04x}")
        monitor.run("x")
        monitor.run("delete 1")
        monitor.run("break 0203")
        model.check_immutable(read_ram(monitor, output))
        full_fixture_bounds(monitor, labels)
        # Consume the natural startup frame through the real API. No host writes
        # erase markers or patch generated code between independent cases.
        if prefix.operands:
            for high in (0x20, 0x28):
                write_memory(monitor, labels["drawBufferHi"], [high])
                call(monitor, labels["xorFill"])
            prefix.check_restored(read_ram(monitor, output))
        for high in (0x20, 0x28):
            write_memory(monitor, labels["drawBufferHi"], [high])
            for name, polygons, expected in fixtures():
                if fast_solid:
                    prepare_fast_boundary_fixture(monitor, labels, high)
                monitor.run("f 2000 2fff 00")
                opposite = 0x2800 if high == 0x20 else 0x2000
                monitor.run(f"f {opposite:04x} {opposite + 2047:04x} a5")
                for polygon, color in polygons:
                    write_memory(monitor, labels["boundaryColor"], [color])
                    for start, end in zip(polygon, polygon[1:] + polygon[:1]):
                        for field, value in zip(("lineX0", "lineY0", "lineX1", "lineY1"), (*start, *end)):
                            write_memory(monitor, labels[field], [value])
                        call(monitor, labels["drawBoundary"])
                pending = read_ram(monitor, output)
                model.check_immutable(pending)
                raw = prefix.markers(pending, high)
                prefix.check_pending(pending, high, marker_reference(expected))
                if closure_errors(raw):
                    raise AssertionError(f"CPU polygon markers are not closed: {name}, ${high:02x}00.")
                if prefix.operands and any(pending[high << 8:(high << 8) + 2048]):
                    raise AssertionError(f"Boundary drawing modified charset output before filling: {name}.")
                call(monitor, labels["xorFill"])
                actual = monitor.memory(output / "filled.bin", high << 8, (high << 8) + 2047)
                if decode_charset(actual) != expected:
                    raise AssertionError(f"CPU prefix fill differs from polygon fixture: {name}, ${high:02x}00.")
                if monitor.memory(output / "opposite.bin", opposite, opposite + 2047) != bytes([0xa5]) * 2048:
                    raise AssertionError(f"Fixture wrote into the opposite buffer: {name}.")
                restored = read_ram(monitor, output)
                prefix.check_restored(restored)
                model.check_immutable(restored)
                if generated is not None:
                    first, last, image = generated
                    if monitor.memory(output / "boundary-kernels.bin", first, last - 1) != image:
                        raise AssertionError(f"Generated boundary kernels were not restored after fixture: {name}.")
                results.append({"name": name, "charset": f"${high:02x}00", "pass": True})
        boundary_results, settle_cycles = verify_boundary_cases(monitor, labels, output, original, fast_solid)
    ordered_dx1 = [case["cycles_with_call_return"] for case in boundary_results
                   if case["width"] == 1 and not case["reversed"]]
    report = {"pass": True, "program_sha256": hashlib.sha256(original).hexdigest(),
              "fixture_cases": len(results), "boundary_cases": len(boundary_results), "model": model_name,
              "fast_solid": fast_solid,
              "marker_storage": "decoded immediate operands" if prefix.operands else "charset RAM",
              "decoded_marker_operands": sum(map(len, prefix.operands.values())),
              "ordered_dx1_budget_cycles": 150,
              "ordered_dx1_guard_evaluation": {"method": "active_assertion_during_fixture_run",
                                               "performed_during_emulator_run": True,
                                               "samples_checked": len(ordered_dx1), "limit_cycles": 150,
                                               "max_measured_cycles": max(ordered_dx1), "passed": True},
              "boundary_timing_setup": {"method": "12288 debugger JMP instructions after DEN and IRQ disable",
                                         "emulated_settle_cycles": settle_cycles,
                                         "minimum_required_cycles": 19656},
              "boundary_cycle_measurement": "CPU cycles including JSR/RTS; display DMA and raster IRQ disabled",
              "samples": results, "boundary_samples": boundary_results}
    (output / "fixtures.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ("samples", "boundary_samples")}, indent=2))


def interlaced_fixture_cases(material=1, dither=False, tonal=False):
    # The first edge has no selected even-row sample. Its ignored terminal must
    # still be reset on the empty-fill path; odd fields contain physical row127.
    yield "terminal127 empty-path", (((60, 127), (63, 127), material),), (
        (((60, 127), (63, 127), (63, 128), (60, 128)), material),), (15, 127, 15, 127)
    rectangles = [
        ("first row", (0, 0, 5, 1)),
        ("opposite-parity closing row", (5, 115, 13, 119)),
        ("smaller reuse", (6, 116, 10, 118)),
        ("empty reuse", None),
        ("odd-field collision", (3, 10, 9, 11)),
        ("even-field collision", (3, 11, 9, 12)),
    ]
    if dither or tonal:
        rectangles.extend([
            ("all-lane pattern span", (0, 1, 63, 126)),
            ("pattern dirty shrink", (5, 60, 6, 62)),
            ("pattern dirty empty reuse", None),
        ])
    for name, rectangle in rectangles:
        if rectangle is None:
            yield name, (), (), (2, 117, 2, 117)
            continue
        left, top, right, bottom = rectangle
        polygon = ((left, top), (right, top), (right, bottom), (left, bottom))
        edges = tuple((start, end, material) for start, end in zip(polygon, polygon[1:] + polygon[:1]))
        yield name, edges, ((polygon, material),), (
            left // 4, top, right // 4, bottom)
    if dither or tonal:
        other = material % 3 + 1
        # The shared horizontal edge receives one full-byte material XOR.
        # Width1 forces xorBoundarySingle; width4 spans all lanes in one byte;
        # the unaligned span crosses a packed-byte boundary.
        for name, left, right in (("single-sample material transition", 5, 6),
                                  ("full-byte material transition", 4, 8),
                                  ("cross-byte material transition", 3, 7)):
            top = ((left, 8), (right, 8), (right, 10), (left, 10))
            bottom = ((left, 10), (right, 10), (right, 12), (left, 12))
            edges = (((left, 8), (right, 8), material),
                     ((left, 10), (right, 10), material ^ other),
                     ((left, 12), (right, 12), other))
            yield name, edges, ((top, material), (bottom, other)), (left // 4, 8, right // 4, 12)


def gouraud_fixture_cases(material):
    """Triangle API fixtures with independent coverage/affine-light contracts."""
    triangle = ((4, 8), (28, 8), (4, 40))
    cases = [("same triangle B positive", triangle, (1, 4, 8)),
             ("same triangle B negative", triangle, (8, 4, 1)),
             ("same triangle B zero", triangle, (1, 8, 1))]
    cases.extend((f"exact threshold intensity{value}", triangle, (value, value, value))
                 for value in range(1, 9))
    cases.extend([
        ("reversed winding", tuple(reversed(triangle)), (8, 4, 1)),
        ("zero-area triangle", ((4, 8), (12, 16), (20, 24)), (1, 4, 8)),
        ("single-sample column", ((5, 8), (6, 8), (5, 14)), (1, 8, 8)),
        ("last packed byte", ((60, 120), (63, 120), (60, 126)), (8, 1, 4)),
        ("wide affine light", ((0, 1), (63, 1), (0, 126)), (1, 8, 4)),
        ("small dirty reuse", ((6, 60), (8, 60), (6, 62)), (8, 8, 8)),
        ("empty dirty reuse", None, None),
        ("both-field q64 closure", ((60, 126), (63, 128), (60, 128)), (8, 8, 8)),
        ("even-empty odd-row127", ((60, 127), (63, 127), (60, 128)), (8, 8, 8)),
    ])
    for name, polygon, intensities in cases:
        if polygon is None:
            yield name, (), (), (2, 117, 2, 117)
            continue
        if any(not 0 <= x <= 63 or not 0 <= y <= 128 for x, y in polygon):
            raise AssertionError("Gouraud fixture exceeds the declared coordinate domain.")
        if any(abs(p[1] - q[1]) > 127 for p, q in zip(polygon, polygon[1:] + polygon[:1])):
            raise AssertionError("Gouraud fixture exceeds the declared edge-delta domain.")
        bounds = (min(x for x, _ in polygon) // 4, min(y for _, y in polygon),
                  max(x for x, _ in polygon) // 4, max(y for _, y in polygon))
        yield name, (), ((polygon, intensities, material),), bounds


def verify_interlaced_fixtures(program, labels, output, executable, model_name, dither=False, tonal=False,
                               gouraud=False):
    original = program.read_bytes()
    model = ReferenceModel(model_name, original, labels, dither, tonal, gouraud)
    prefix = PrefixImage(original, labels, True)
    generated = boundary_kernel_image(original, labels)
    allowed = mutable_ranges(labels, model_name, True, tonal, gouraud) + [(0x0200, 0x0206)]
    images = {0x2000: bytes(2048), 0x2800: bytes(2048)}
    history, next_parities, samples = {}, [0, 0], []
    used_fields = [0, 0, 0, 0]

    def normalized(ram, pending=False):
        stable = bytearray(ram)
        if pending:
            prefix.normalize_pending(stable)  # Every marker value was independently checked.
        for first, last in allowed:
            stable[first:last] = bytes(last - first)
        return stable

    with machine(executable, program, output) as monitor:
        monitor.run(f"break {labels['nextFrame']:04x}")
        monitor.run("x")
        monitor.run("delete 1")
        monitor.run("break 0203")
        if gouraud:
            monitor.run(f"break {labels['gouraudEvenFilled']:04x}")
        initial = read_ram(monitor, output)
        prefix.check_restored(initial)
        model.check_immutable(initial)
        if any(initial[labels["filledBufferUsed"]:labels["filledBufferUsed"] + 4]) or any(
                initial[labels["interlaceNextParity"]:labels["interlaceNextParity"] + 2]):
            raise AssertionError("Interlaced fixture did not begin at fresh field initialization.")
        stable_ram = normalized(initial)
        for color in (1, 2, 3):
            cases = (gouraud_fixture_cases(color) if gouraud else
                     interlaced_fixture_cases(color, dither, tonal))
            for name, edges, polygons, current in cases:
                if gouraud:
                    full = gouraud_polygons_reference(polygons)
                else:
                    materials = polygon_reference(polygons)
                    full = dither_reference(materials) if dither else materials
                terminal_canvas = dither_reference(materials, 0) if dither else None
                for field in range(2 if gouraud else 4):
                    draw = 0x2800 if field % 2 == 0 else 0x2000
                    parity = 0 if gouraud else field // 2
                    slot = 2 * int(draw == 0x2800) + parity
                    key = draw if gouraud else (draw, parity)
                    union = union_bounds_reference(current, history.get(key))
                    write_memory(monitor, labels["drawBufferHi"], [draw >> 8])
                    call(monitor, labels["prepareFilledFrame"])
                    if gouraud:
                        # The real second-fill path calls rememberBounds again.
                        # Repeating the three corners gives the production
                        # 12-vertex bounds routine the exact fixture rectangle.
                        corners = polygons[0][0] if polygons else ((8, 117),) * 3
                        write_memory(monitor, labels["projectedX"], [point[0] for point in corners] * 4)
                        write_memory(monitor, labels["projectedY"], [point[1] for point in corners] * 4)
                        call(monitor, labels["rememberBounds"])
                        for polygon, intensities, material in polygons:
                            write_memory(monitor, labels["gouraudInputX"], [point[0] for point in polygon])
                            write_memory(monitor, labels["gouraudInputY"], [point[1] for point in polygon])
                            write_memory(monitor, labels["gouraudInputI"], intensities)
                            write_memory(monitor, labels["gouraudMaterial"], [material])
                            call(monitor, labels["gouraudTriangle"])
                    else:
                        for label, value in zip(("dirtyMinColumn", "dirtyMinRow", "dirtyMaxColumn", "dirtyMaxRow"), current):
                            write_memory(monitor, labels[label] + slot, [value])
                    for start, end, transition in edges:
                        packed_transition = DITHER_PATTERNS[parity][transition] if dither else transition
                        write_memory(monitor, labels["boundaryColor"], [packed_transition])
                        for label, value in zip(("lineX0", "lineY0", "lineX1", "lineY1"), (*start, *end)):
                            write_memory(monitor, labels[label], [value])
                        call(monitor, labels["drawBoundary"])
                    pending = read_ram(monitor, output)
                    fields = None
                    if gouraud:
                        expected = full
                        markers, sink, fields = coherent_field_reference(full)
                    else:
                        expected, markers, sink, terminal = interlaced_reference(
                            full, decode_charset(images[draw]), parity, terminal_canvas)
                    raw_expected = expected
                    if tonal:
                        expected = selected_field(tonal_reference(materials), decode_charset(images[draw]), parity)
                    if pending[labels["interlaceFieldParity"]] != parity or pending[labels["interlaceDirtyIndex"]] != slot:
                        raise AssertionError("Focused fixture selected the wrong field or dirty slot.")
                    next_parities[int(draw == 0x2800)] ^= 1
                    if list(pending[labels["interlaceNextParity"]:labels["interlaceNextParity"] + 2]) != next_parities:
                        raise AssertionError("Focused field lifecycle did not toggle the selected buffer's parity.")
                    if gouraud:
                        used_fields[slot] = 1
                        if list(pending[labels["filledBufferUsed"]:labels["filledBufferUsed"] + 4]) != used_fields:
                            raise AssertionError("Coherent fixture prepared a field before its production stage.")
                    prefix.check_pending(pending, draw >> 8, markers)
                    if pending[labels["interlaceTerminalMarker"]] != sink:
                        raise AssertionError(f"Terminal sink differs from direct full-resolution transition: {name}.")
                    for selected in ((0, 1) if gouraud else (parity,)):
                        last = fields[selected][3] if gouraud else terminal
                        if interlaced_closure_errors(prefix.markers(pending, draw >> 8), last, selected):
                            raise AssertionError("Focused field fails closure with its virtual terminal.")
                    model.check_immutable(pending)
                    if any(pending[bank:bank + 2048] != image for bank, image in images.items()):
                        raise AssertionError("Focused boundary drawing changed existing field pixels.")
                    if normalized(pending, True) != stable_ram:
                        address = next(i for i, (a, b) in enumerate(zip(normalized(pending, True), stable_ram)) if a != b)
                        raise AssertionError(f"Focused boundary wrote outside its workspace at ${address:04x}.")
                    middle = {}
                    if gouraud:
                        def check_even_fill():
                            mid = read_ram(monitor, output)
                            model.check_immutable(mid)
                            prefix.check_pending(mid, draw >> 8, fields[1][1])
                            if decode_charset(mid[draw:draw + 2048]) != selected_field(
                                    full, decode_charset(images[draw]), 0):
                                raise AssertionError("First fill does not contain current even/prior odd rows.")
                            if mid[draw ^ 0x0800:(draw ^ 0x0800) + 2048] != images[draw ^ 0x0800]:
                                raise AssertionError("First coherent fill changed the other physical buffer.")
                            if mid[labels["interlaceFieldParity"]] != 0 or mid[labels["interlaceDirtyIndex"]] != slot:
                                raise AssertionError("First coherent fill changed its active metadata too early.")
                            middle["q_bounds"] = check_interlaced_fill(mid, labels, union, 0, sink)
                            if normalized(mid, True) != stable_ram:
                                raise AssertionError("First coherent fill wrote outside its workspace.")
                        call(monitor, labels["gouraudFillFrame"],
                             checkpoints={labels["gouraudEvenFilled"]: check_even_fill})
                    else:
                        call(monitor, labels["xorFill"])
                    if tonal:
                        raw = read_ram(monitor, output)
                        prefix.check_restored(raw)
                        model.check_immutable(raw)
                        if decode_charset(raw[draw:draw + 2048]) != raw_expected:
                            raise AssertionError(f"Focused raw material fill differs before tonal shading: {name}.")
                        if normalized(raw) != stable_ram:
                            raise AssertionError("Raw tonal fill wrote outside its owned workspaces.")
                        call(monitor, labels["tonalShade"])
                        model.expect_shaded(draw)
                    after = read_ram(monitor, output)
                    prefix.check_restored(after)
                    if gouraud:
                        q_bounds = {"even": middle["q_bounds"],
                                    "odd": check_interlaced_fill(after, labels, union, 1)}
                        next_parities[int(draw == 0x2800)] ^= 1
                        used_fields[slot + 1] = 1
                        if (after[labels["interlaceFieldParity"]] != 1 or
                                after[labels["interlaceDirtyIndex"]] != slot + 1 or
                                list(after[labels["interlaceNextParity"]:labels["interlaceNextParity"] + 2]) != next_parities or
                                list(after[labels["filledBufferUsed"]:labels["filledBufferUsed"] + 4]) != used_fields):
                            raise AssertionError("Coherent fixture did not finish both field lifecycles.")
                        if any(dirty_bounds(after, labels, slot + selected) != current for selected in (0, 1)):
                            raise AssertionError("Coherent fixture field bounds describe different poses.")
                    else:
                        q_bounds = check_interlaced_fill(after, labels, union, parity)
                    model.check_immutable(after)
                    actual = after[draw:draw + 2048]
                    if decode_charset(actual) != expected:
                        raise AssertionError(f"Focused field differs from selected full-resolution pixels: {name}.")
                    opposite = draw ^ 0x0800
                    if after[opposite:opposite + 2048] != images[opposite]:
                        raise AssertionError("Focused field changed the other physical buffer.")
                    if not gouraud and any(actual[column * HEIGHT + row] != images[draw][column * HEIGHT + row]
                           for column in range(16) for row in range(1 - parity, HEIGHT, 2)):
                        raise AssertionError("Focused field changed opposite-parity rows.")
                    actual_union = tuple(after[labels[label]] for label in (
                        "filledMinColumn", "filledMinRow", "filledMaxColumn", "filledMaxRow"))
                    if actual_union != union:
                        raise AssertionError("Focused field did not reuse its own previous dirty rectangle.")
                    if generated is not None:
                        first, last, image = generated
                        if after[first:last] != image:
                            raise AssertionError("Focused boundary sentinel was not restored.")
                    if normalized(after) != stable_ram:
                        address = next(i for i, (a, b) in enumerate(zip(normalized(after), stable_ram)) if a != b)
                        raise AssertionError(f"Focused fill wrote outside its workspace at ${address:04x}.")
                    images[draw], history[key] = bytes(actual), current
                    samples.append({"name": name, "color": color, "charset": f"${draw:04x}",
                                    "packed_transitions": [DITHER_PATTERNS[parity][item[2]] if dither else item[2]
                                                           for item in edges],
                                    "gouraud_triangles": polygons if gouraud else None,
                                    "parity": None if gouraud else parity,
                                    "parities": [0, 1] if gouraud else [parity],
                                    "dirty_slot": slot, "union": union,
                                    "raw_material_fill_checked": tonal,
                                    "cleanup_q_bounds": q_bounds, "terminal_before": sink,
                                    "terminal_after": 0, "pass": True})
    report = {"pass": True, "program_sha256": hashlib.sha256(original).hexdigest(),
              "model": model_name, "interlaced": not gouraud, "visual_interlaced": not gouraud,
              "field_layout": True, "dither": dither, "tonal": tonal,
              "gouraud": gouraud,
              "fixture_fields": len(samples) * (2 if gouraud else 1),
              "coherent_fixture_images": len(samples) if gouraud else None,
              "material_patterns": {"even": list(DITHER_PATTERNS[0]), "odd": list(DITHER_PATTERNS[1])}
                                   if dither else None,
              "field_sequence": ["B-both", "A-both"] if gouraud else ["B-even", "A-even", "B-odd", "A-odd"],
              "tonal_masks_checked": HEIGHT if tonal else 0,
              "tonal_smc_high_bytes_checked": 32 if tonal else 0,
              "gouraud_light_table_bytes_checked": 256 if gouraud else 0,
              "gouraud_pixel_oracle": "direct Fraction coverage and exact affine barycentric I>=rank+1"
                                      if gouraud else None,
              "terminal_nonzero_cases": sum(sample["terminal_before"] != 0 for sample in samples),
              "empty_cleanup_cases": sum(bounds[0] > bounds[1] for sample in samples
                                          for bounds in (sample["cleanup_q_bounds"].values() if gouraud else
                                                         (sample["cleanup_q_bounds"],))), "samples": samples}
    (output / "fixtures.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "samples"}, indent=2))


def mutable_ranges(labels, model_name="cube", interlaced=False, tonal=False, gouraud=False, fast_solid=False):
    ranges = [(0x0100, 0x0200), (labels["linePointer"], labels["squareSum"] + 1),
            (labels["angleYaw"], labels["bitMasks"]), (0x2000, 0x3000),
            (0xd0, 0xe0), (labels["cullDX1"], labels["cullSumHi"] + 1),
            (labels["visibleFaces"], labels["visibleFaces"] + (20 if model_name == "icosahedron" else 1)),
            (labels["clearStateStart"], labels["clearStateEnd"]),
            (labels["fillStateStart"], labels["fillStateEnd"]),
            (labels["xorFillEntry"] + 1, labels["xorFillEntry"] + 3)]
    if "clearEntry" in labels:
        ranges.extend(((labels["clearPatchPointer"], labels["clearPatchPointer"] + 2),
                       (labels["clearEntry"] + 1, labels["clearEntry"] + 3),
                       (labels["clearFirstRow"] + 1, labels["clearFirstRow"] + 2),
                       (labels["clearLastRow"] + 1, labels["clearLastRow"] + 2)))
    if "xorBoundaryDispatch" in labels:
        ranges.append((labels["xorBoundaryDispatch"] + 1, labels["xorBoundaryDispatch"] + 3))
    if "fastFillEntry" in labels:
        ranges.append((labels["fastFillEntry"] + 1, labels["fastFillEntry"] + 3))
    if interlaced:
        ranges.append((labels["interlaceTerminalMarker"], labels["interlaceTerminalMarker"] + 1))
    if tonal:
        cells = labels["tonalShadeCells"]
        ranges.extend((cells + column * 8 + offset, cells + column * 8 + offset + 1)
                      for column in range(16) for offset in (2, 7))
    if gouraud:
        ranges.append((0xc0, 0xca))
        ranges.append((labels["gouraudStateStart"], labels["gouraudStateEnd"]))
    if fast_solid:
        ranges.append((labels["fastRotationStateStart"], labels["fastRotationStateEnd"]))
        ranges.append((labels["fastBoundsStateStart"], labels["fastBoundsStateEnd"]))
        ranges.append((labels["fastBoundaryStateStart"], labels["fastBoundaryStateEnd"]))
    return ranges


def screenshot_difference(image, canvas, colors):
    expected = [colors[canvas[y * WIDTH + x // 2]] for y in range(HEIGHT) for x in range(WIDTH * 2)]
    image = image.convert("RGB")
    candidates = []
    for top in range(28, 42):
        for left in range(28, 38):
            actual = list(image.crop((left + 96, top + 32, left + 224, top + 160)).get_flattened_data())
            candidates.append((sum(a != b for a, b in zip(actual, expected)), left, top))
    return min(candidates)


def preview(canvas, colors):
    palette = [component for color in colors for component in color] + [0] * (768 - 12)
    field = Image.frombytes("P", (WIDTH, HEIGHT), bytes(canvas))
    field.putpalette(palette)
    image = Image.new("P", (320, 200))
    image.putpalette(palette)
    image.paste(field.resize((128, 128), Image.Resampling.NEAREST), (96, 32))
    return image.resize((640, 400), Image.Resampling.NEAREST)


def save_animation(frames, path, duration):
    header, _ = GifImagePlugin.getheader(frames[0], info={"loop": 0, "optimize": False})
    with path.open("wb") as stream:
        for block in header:
            stream.write(block)
        for frame in frames:
            for block in GifImagePlugin.getdata(frame, duration=duration, disposal=1):
                stream.write(block)
        stream.write(b";")


def read_ram(monitor, output):
    monitor.run("bank ram")
    ram = monitor.memory(output / "ram.bin", 0, 0xffff)
    monitor.run("bank cpu")
    return ram


def verify(program, labels, output, executable, frames, ticks, raster_line, model_name="cube", interlaced=False,
           dither=False, tonal=False, gouraud=False, fast_solid=False):
    field_layout = interlaced or gouraud
    visual_interlaced = interlaced and not gouraud
    modern_palette = field_layout or fast_solid
    original = program.read_bytes()
    if original[:2] != b"\x01\x08":
        raise ValueError("Expected a runnable C64 PRG at $0801.")
    boundary_ready = labels.get("boundariesReady", labels.get("boundaryReady"))
    if boundary_ready is None:
        raise ValueError("Missing natural boundary-completion debug label.")
    _, palette = read_palette()
    colors = [palette[index] for index in ((0, 6, 5, 4) if modern_palette else (0, 6, 14, 3))]
    model = ReferenceModel(model_name, original, labels, dither, tonal, gouraud, fast_solid)
    allowed = mutable_ranges(labels, model_name, field_layout, tonal, gouraud, fast_solid)
    prefix = PrefixImage(original, labels, field_layout)
    generated = boundary_kernel_image(original, labels)
    samples, animation, elapsed, hashes = [], [], [], set()
    previous_canvas = previous_angles = previous_cycles = previous_tick = stable_ram = None
    seen_buffers, captures = set(), 0
    capture_stride = max(1, min(16, frames // 32)) if gouraud else max(1, frames // 32)
    buffer_images = {0x2000: bytes(2048), 0x2800: bytes(2048)}
    buffer_bounds = {}
    next_parities, used_fields = [0, 0], [0, 0, 0, 0]
    seen_fields = set()
    output.mkdir(parents=True, exist_ok=True)
    (output / "verification.json").unlink(missing_ok=True)
    with machine(executable, program, output) as monitor:
        monitor.run(f"break {boundary_ready:04x}")
        monitor.run(f"break {labels['framePresented']:04x}")
        if gouraud:
            monitor.run(f"break {labels['gouraudEvenFilled']:04x}")
        if tonal:
            monitor.run(f"break {labels['tonalRawReady']:04x}")
        for index in range(frames):
            monitor.run("x")
            pc, _, _ = monitor.registers()
            if pc != boundary_ready:
                raise AssertionError("Program did not finish drawing boundary markers.")
            before = read_ram(monitor, output)
            if modern_palette and monitor.memory(output / "border.bin", 0xd020, 0xd020)[0] & 15:
                raise AssertionError("The border is not black while rendering is pending.")
            model.check_immutable(before)
            if generated is not None:
                first, last, image = generated
                if before[first:last] != image:
                    raise AssertionError("Generated boundary kernels were not restored before prefix filling.")
            draw = before[labels["drawBufferHi"]] << 8
            if draw not in (0x2000, 0x2800):
                raise AssertionError("Boundary renderer selected an unexpected charset.")
            field_parity = None
            slot = int(draw == 0x2800)
            field_key = draw
            if field_layout:
                field_parity = before[labels["interlaceFieldParity"]]
                expected_draw = 0x2800 if index % 2 == 0 else 0x2000
                expected_parity = 0 if gouraud else (index // 2) & 1
                if (draw, field_parity) != (expected_draw, expected_parity):
                    raise AssertionError("Drawing buffer or first selected field differs from the presentation lifecycle.")
                buffer_index = slot
                slot = 2 * buffer_index + field_parity
                field_key = draw, field_parity
                if before[labels["interlaceDirtyIndex"]] != slot:
                    raise AssertionError("Field dirty bounds belong to the wrong buffer/parity.")
                next_parities[buffer_index] ^= 1
                if list(before[labels["interlaceNextParity"]:labels["interlaceNextParity"] + 2]) != next_parities:
                    raise AssertionError("Per-buffer next field parity did not toggle on reuse.")
                used_fields[slot] = 1
                if list(before[labels["filledBufferUsed"]:labels["filledBufferUsed"] + 4]) != used_fields:
                    raise AssertionError("First-use state does not belong to four independent fields.")
                seen_fields.add(field_key)
            yaw, pitch = before[labels["angleYaw"]], before[labels["anglePitch"]]
            vertices = list(zip(before[labels["projectedX"]:labels["projectedX"] + model.vertex_count],
                                before[labels["projectedY"]:labels["projectedY"] + model.vertex_count]))
            original_rotated = None
            if fast_solid:
                original_rotated = direct_rotation_reference(model.coordinates, yaw, pitch)
                actual_rotated = list(zip(*[tuple(value if value < 128 else value - 256
                                                   for value in before[labels["rotated" + axis]:
                                                                       labels["rotated" + axis] + model.vertex_count])
                                           for axis in "XYZ"]))
                if actual_rotated != original_rotated:
                    raise AssertionError("Fast rotation XYZ differ from the original per-vertex Q6 path.")
                if vertices != direct_projection_reference(original_rotated):
                    raise AssertionError("Fast projection differs from the original depth/Q6/zoom operation order.")
            if any(not (0 <= x < WIDTH and 0 <= y < HEIGHT) for x, y in vertices):
                raise AssertionError("A projected vertex escaped the multicolor canvas.")
            if model_name == "icosahedron" and any(not (4 <= x <= 59 and 9 <= y <= 119)
                                                    for x, y in vertices):
                raise AssertionError("The enlarged model escaped its audited canvas margins.")
            ideal = model.geometry(yaw, pitch)
            # Dropping the physical X low bit deliberately selects a two-pixel
            # footprint. Measure distance to that footprint, not its left edge.
            error = max(max(2 * x - ref_x, ref_x - (2 * x + 1), 0, abs(y - ref_y))
                        for (x, y), (ref_x, ref_y) in zip(vertices, ideal))
            if error > model.geometry_tolerance:
                raise AssertionError(f"Projection differs from true geometry by {error:.3f} physical pixels.")
            shown = model.visibility(vertices)
            visible = (sum(int(value) << face for face, value in enumerate(shown)) if model_name == "cube"
                       else [int(value) for value in shown])
            actual_visibility = (before[labels["visibleFaces"]] if model_name == "cube" else
                                 list(before[labels["visibleFaces"]:labels["visibleFaces"] + len(shown)]))
            if actual_visibility != visible:
                raise AssertionError("Face visibility differs from independent signed screen areas.")
            fast_depths = fast_materials = None
            if fast_solid:
                fast_depths, fast_materials = fast_face_materials(original_rotated, model.faces, shown, model.colors)
                if "fastFaceDepth" in labels:
                    recorded = list(before[labels["fastFaceDepth"]:labels["fastFaceDepth"] + len(model.faces)])
                    if recorded != [value & 255 for value in fast_depths]:
                        raise AssertionError("Recorded face depths differ from original direct Q6 geometry.")
                if list(before[labels["xorFaceColors"]:labels["xorFaceColors"] + len(model.faces)]) != fast_materials:
                    raise AssertionError("FAST face materials differ from fixed model colors and independent visibility.")
            vertex_intensities = light_dots = None
            if gouraud:
                signed_y = [value if value < 128 else value - 256
                            for value in before[labels["rotatedY"]:labels["rotatedY"] + model.vertex_count]]
                signed_z = [value if value < 128 else value - 256
                            for value in before[labels["rotatedZ"]:labels["rotatedZ"] + model.vertex_count]]
                light_dots = [y - z for y, z in zip(signed_y, signed_z)]
                if any(not -128 <= value < 128 for value in light_dots):
                    raise AssertionError("A rotated-normal/light dot does not fit the declared signed byte.")
                vertex_intensities = [gouraud_intensity(value) for value in light_dots]
                if list(before[labels["gouraudVertexI"]:labels["gouraudVertexI"] + model.vertex_count]) != vertex_intensities:
                    raise AssertionError("Vertex intensities differ from the independent rotated-normal/light dot.")
                full_reference = gouraud_reference(model, vertices, shown, vertex_intensities)
            else:
                materials = model.materials(vertices, shown, fast_materials)
                full_reference = dither_reference(materials) if dither else materials
            expected = full_reference
            fields = None
            if gouraud:
                expected = full_reference
                expected_markers, expected_sink, fields = coherent_field_reference(full_reference)
                if before[labels["interlaceTerminalMarker"]] != expected_sink:
                    raise AssertionError("Aggregate virtual terminal differs from both coherent field closures.")
            elif visual_interlaced:
                terminal_canvas = dither_reference(materials, 0) if dither else None
                expected, expected_markers, expected_sink, last_colors = interlaced_reference(
                    full_reference, decode_charset(buffer_images[draw]), field_parity, terminal_canvas, gouraud)
                if before[labels["interlaceTerminalMarker"]] != expected_sink:
                    raise AssertionError("Ignored terminal markers differ from the full-resolution transition.")
            raw_expected = expected
            if tonal:
                full_reference = tonal_reference(materials)
                expected = selected_field(full_reference, decode_charset(buffer_images[draw]), field_parity)
            if prefix.operands:
                for bank, image in buffer_images.items():
                    if before[bank:bank + 2048] != image:
                        raise AssertionError("Boundary drawing changed charset output before prefix filling.")
            markers = prefix.markers(before, draw >> 8)
            if gouraud:
                parity = {selected: errors for selected in (0, 1)
                          if (errors := interlaced_closure_errors(markers, fields[selected][3], selected))}
            else:
                parity = (interlaced_closure_errors(markers, last_colors, field_parity) if visual_interlaced else
                          closure_errors(markers))
            if parity:
                raise AssertionError(f"Open boundary bitplanes in byte columns: {parity}.")
            if not field_layout:
                expected_markers = marker_reference(expected)
            prefix.check_pending(before, draw >> 8, expected_markers)
            current_bounds = (min(x for x, _ in vertices) // 4, min(y for _, y in vertices),
                              max(x for x, _ in vertices) // 4, max(y for _, y in vertices))
            old_bounds = buffer_bounds.get(field_key)
            union_bounds = union_bounds_reference(current_bounds, old_bounds)
            if prefix.operands:
                actual_bounds = dirty_bounds(before, labels, slot)
                if actual_bounds != current_bounds:
                    raise AssertionError("Dirty metadata does not describe the current projected model.")
            raw_hash = None
            even_q_bounds = None
            if gouraud:
                monitor.run("x")
                if monitor.registers()[0] != labels["gouraudEvenFilled"]:
                    raise AssertionError("Program did not reach its natural between-fill checkpoint.")
                mid = read_ram(monitor, output)
                model.check_immutable(mid)
                prefix.check_pending(mid, draw >> 8, fields[1][1])
                if decode_charset(mid[draw:draw + 2048]) != selected_field(
                        full_reference, decode_charset(buffer_images[draw]), 0):
                    raise AssertionError("Intermediate draw buffer mixes unexpected poses or parities.")
                opposite = draw ^ 0x0800
                if mid[opposite:opposite + 2048] != before[opposite:opposite + 2048]:
                    raise AssertionError("Intermediate fill changed the displayed physical buffer.")
                if mid[labels["interlaceFieldParity"]] != 0 or mid[labels["interlaceDirtyIndex"]] != slot:
                    raise AssertionError("Second field metadata was prepared before its production stage.")
                even_q_bounds = check_interlaced_fill(mid, labels, union_bounds, 0, expected_sink)
                displayed = monitor.memory(output / "between-fill-vic.bin", 0xd018, 0xd018)[0]
                if (displayed & 14) * 1024 != opposite:
                    raise AssertionError("A partially filled Gouraud buffer was displayed before both fields completed.")
            if tonal:
                monitor.run("x")
                if monitor.registers()[0] != labels["tonalRawReady"]:
                    raise AssertionError("Program did not reach its natural pre-shader checkpoint.")
                raw = read_ram(monitor, output)
                model.check_immutable(raw)
                prefix.check_restored(raw)
                if decode_charset(raw[draw:draw + 2048]) != raw_expected:
                    raise AssertionError("Raw material fill differs before tonal shading.")
                if raw[draw ^ 0x0800:(draw ^ 0x0800) + 2048] != before[draw ^ 0x0800:(draw ^ 0x0800) + 2048]:
                    raise AssertionError("Raw tonal fill changed the opposite physical buffer.")
                check_interlaced_fill(raw, labels, union_bounds, field_parity)
                raw_hash = hashlib.sha256(raw[draw:draw + 2048]).hexdigest()
            monitor.run("x")
            pc, line, cycles = monitor.registers()
            if pc != labels["framePresented"]:
                raise AssertionError("Program did not present its filled buffer.")
            io = monitor.memory(output / "vic.bin", 0xd000, 0xd03f)
            if modern_palette and io[0x20] & 15:
                raise AssertionError("The border is not black at presentation.")
            if io[0x11] & 0x60 or io[0x16] & 0x1f != 0x18:
                raise AssertionError("VIC-II left standard multicolor character mode.")
            if [io[address] & 15 for address in (0x21, 0x22, 0x23)] != [0, 6, 5 if modern_palette else 14]:
                raise AssertionError("Multicolor palette registers changed.")
            if io[0x18] >> 4 != 1 or (io[0x18] & 14) * 1024 != draw:
                raise AssertionError("Displayed screen/charset does not match the completed buffer.")
            after = read_ram(monitor, output)
            if tonal:
                model.expect_shaded(draw)
            model.check_immutable(after)
            actual = after[draw:draw + 2048]
            if decode_charset(actual) != expected:
                raise AssertionError("Filled charset differs from direct odd-even polygon coverage.")
            opposite = draw ^ 0x0800
            if after[opposite:opposite + 2048] != before[opposite:opposite + 2048]:
                raise AssertionError("Prefix filling changed the displayed opposite buffer.")
            prefix.check_restored(after)
            q_bounds = None
            if gouraud:
                q_bounds = {"even": even_q_bounds, "odd": check_interlaced_fill(after, labels, union_bounds, 1)}
                next_parities[int(draw == 0x2800)] ^= 1
                used_fields[slot + 1] = 1
                if (after[labels["interlaceFieldParity"]] != 1 or
                        after[labels["interlaceDirtyIndex"]] != slot + 1 or
                        list(after[labels["interlaceNextParity"]:labels["interlaceNextParity"] + 2]) != next_parities or
                        list(after[labels["filledBufferUsed"]:labels["filledBufferUsed"] + 4]) != used_fields):
                    raise AssertionError("Gouraud presentation did not complete both internal field lifecycles.")
                seen_fields.add((draw, 1))
            elif visual_interlaced:
                q_bounds = check_interlaced_fill(after, labels, union_bounds, field_parity)
                if any(after[draw + column * HEIGHT + row] != before[draw + column * HEIGHT + row]
                       for column in range(16) for row in range(1 - field_parity, HEIGHT, 2)):
                    raise AssertionError("Filling changed an untouched row of the same physical buffer.")
            if prefix.operands:
                actual_union = tuple(after[labels[name]] for name in (
                    "filledMinColumn", "filledMinRow", "filledMaxColumn", "filledMaxRow"))
                if actual_union != union_bounds:
                    raise AssertionError(f"Fill bounds {actual_union} differ from old/new buffer union {union_bounds}.")
            buffer_images[draw] = bytes(actual)
            buffer_bounds[field_key] = current_bounds
            if gouraud:
                buffer_bounds[(draw, 1)] = current_bounds
            if field_layout:
                for (bank, selected_parity), bounds in buffer_bounds.items():
                    saved_slot = 2 * int(bank == 0x2800) + selected_parity
                    if dirty_bounds(after, labels, saved_slot) != bounds:
                        raise AssertionError("A field changed another buffer/parity's saved bounds.")
            stable = bytearray(after)
            for first, last in allowed:
                stable[first:last] = bytes(last - first)
            if stable_ram is not None and stable != stable_ram:
                address = next(i for i, (a, b) in enumerate(zip(stable, stable_ram)) if a != b)
                raise AssertionError(f"Unexpected write outside renderer workspaces at ${address:04x}.")
            stable_ram = stable
            if (line - raster_line) % 312 > 3:
                raise AssertionError(f"Presentation missed its raster window: line {line}.")
            if previous_cycles is not None:
                elapsed.append(cycles - previous_cycles)
                if abs(elapsed[-1] - ticks * 19656) > 63:
                    raise AssertionError(f"Presentation missed its {ticks}-frame cycle budget: {elapsed[-1]} cycles.")
            if previous_tick is not None and (after[labels["rasterTick"]] - previous_tick) % 256 != ticks:
                raise AssertionError("Raster clock did not advance at the required cadence.")
            if previous_angles is not None:
                expected_yaw = (previous_angles[0] + ticks) & 255
                expected_pitch = (previous_angles[1] + (ticks + (previous_angles[0] & 1)) // 2) & 255
                if (yaw, pitch) != (expected_yaw, expected_pitch):
                    raise AssertionError("Rotation speed changed between presentations.")
            if after[labels["drawBufferHi"]] << 8 != draw ^ 0x0800:
                raise AssertionError("Drawing and displayed charsets are not separate buffers.")
            if any(after[0x0400 + (row + 4) * 40 + column + 12] != column * 16 + row
                   for row in range(16) for column in range(16)):
                raise AssertionError("Column-major screen mapping changed.")
            if index == 0:
                color_ram = monitor.memory(output / "colors.bin", 0xd800, 0xdbe7)
                if any(color_ram[(row + 4) * 40 + column + 12] & 15 != (12 if modern_palette else 11)
                       for row in range(16) for column in range(16)):
                    raise AssertionError("Canvas cells do not select multicolor and foreground color3.")
            sample = {"yaw": yaw, "pitch": pitch, "vertices": vertices, "visible_faces": visible,
                      "charset": f"${draw:04x}", "geometry_error_pixels": round(error, 4),
                      "visible_face_count": sum(shown), "field_parity": None if gouraud else field_parity,
                      "internal_fields": [0, 1] if gouraud else [field_parity] if field_layout else None,
                      "field_dirty_slot": slot if field_layout else None,
                      "field_cleanup_q_bounds": q_bounds,
                      "full_reference_charset_sha256": hashlib.sha256(encode_canvas(full_reference)).hexdigest(),
                      "raw_material_charset_sha256": raw_hash,
                      "original_direct_q6_rotated_xyz": original_rotated,
                      "fast_face_depth_sums": fast_depths, "fast_face_materials": fast_materials,
                      "vertex_intensities": vertex_intensities, "normal_light_dot_numerators": light_dots,
                      "colored_pixels": sum(value != 0 for value in expected),
                      "color_counts": [expected.count(color) for color in range(4)],
                      "boundary_parity_errors": 0, "cycles": cycles, "presentation_raster_line": line,
                      "marker_sha256": hashlib.sha256(markers).hexdigest(),
                      "charset_sha256": hashlib.sha256(actual).hexdigest(),
                      "current_bounds": current_bounds, "previous_buffer_bounds": old_bounds,
                      "required_clear_union": union_bounds,
                      "fill_union_bytes": ((union_bounds[2] - union_bounds[0] + 1) *
                                           (sum(max(0, bounds[1] - bounds[0] + 1) for bounds in q_bounds.values())
                                            if gouraud else max(0, q_bounds[1] - q_bounds[0] + 1)
                                            if field_layout else union_bounds[3] - union_bounds[1] + 1))}
            if previous_canvas is not None and index % capture_stride == 0:
                screenshot = output / f"vice-{index:03d}.png"
                monitor.run(f'scrsh "{screenshot}" 2')
                mismatch, left, top = screenshot_difference(Image.open(screenshot), previous_canvas, colors)
                if mismatch:
                    raise AssertionError(f"Native multicolor VICE capture differs in {mismatch} physical pixels.")
                sample.update({"screenshot": screenshot.name, "screenshot_mismatches": mismatch,
                               "screen_origin": [left, top]})
                captures += 1
            samples.append(sample)
            animation.append(preview(expected, colors))
            hashes.add(sample["charset_sha256"])
            seen_buffers.add(draw)
            previous_canvas, previous_angles, previous_cycles = expected, (yaw, pitch), cycles
            previous_tick = after[labels["rasterTick"]]
    if seen_buffers != {0x2000, 0x2800} or len(hashes) < 2:
        raise AssertionError("Both filled buffers must animate.")
    if field_layout and seen_fields != {(bank, parity) for bank in (0x2000, 0x2800) for parity in (0, 1)}:
        raise AssertionError("All four independent buffer/parity fields must animate.")
    gif_name = ("icosahedron-fast-solid.gif" if fast_solid else "icosahedron-gouraud.gif" if gouraud else
                "icosahedron-tonal.gif" if tonal else
                "icosahedron-dither.gif" if dither else
                "icosahedron-interlaced.gif" if interlaced else
                "filled-cube.gif" if model_name == "cube" else "icosahedron.gif")
    save_animation(animation, output / gif_name, ticks * 20)
    report = {"pass": True, "program_sha256": hashlib.sha256(original).hexdigest(),
              "frames_verified": frames, "logical_canvas": [WIDTH, HEIGHT], "physical_canvas": [128, 128],
              "coherent_poses_verified": frames if gouraud else None,
              "model": model_name, "interlaced": visual_interlaced, "visual_interlaced": visual_interlaced,
              "field_layout": field_layout, "dither": dither, "tonal": tonal,
              "gouraud": gouraud,
              "fast_solid": fast_solid,
              "material_patterns": {"even": list(DITHER_PATTERNS[0]), "odd": list(DITHER_PATTERNS[1])}
                                   if dither else None,
              "field_sequence": (["B-both", "A-both"] if gouraud else
                                 ["B-even", "A-even", "B-odd", "A-odd"] if visual_interlaced else None),
              "tonal_contract": {"density": "clamp(16-floor((physicalY-8)*17/112),0,16)",
                                  "bayer_ranks": BAYER_RANKS, "x_coordinate": "logical multicolor X sample (two physical pixels)",
                                  "keep_material_when": "rank[physicalY&3][logicalX&3] < density",
                                  "mask_bytes_checked": HEIGHT, "smc_high_bytes_checked": 32,
                                  "raw_material_fill_checked_each_presentation": True} if tonal else None,
              "gouraud_contract": {"normal": "shared radial vertex normal; radius sqrt1597",
                                     "light": "camera/view fixed (0,1,-1)/sqrt2",
                                     "vertex_intensity": "clamp(1+floor(7*max(0,signedY-signedZ)/sqrt3194+0.5),1,8)",
                                     "interpolation": "exact affine barycentric intensity at integer logicalX/physicalY",
                                     "bayer_ranks": GOURAUD_RANKS, "keep_material_when": "I >= rank[y&1][x&3]+1",
                                     "light_table_bytes_checked": 256,
                                     "shared_vertex_intensities_checked_per_presentation": model.vertex_count,
                                     "coherent_pose": "both fields from this one yaw/pitch before display flip",
                                     "between_fill_display_remains_opposite_buffer": True,
                                     "terminal": "q64 closing XOR of selected last-row bytes, both parities"}
                                    if gouraud else None,
              "vertex_count": model.vertex_count, "face_count": len(model.faces),
              "edge_count": model.edge_count, "geometry_tolerance_pixels": model.geometry_tolerance,
              "projection_zoom": [29, 20] if model_name == "icosahedron" else [1, 1],
              "zoom_table_entries_checked": 256 if model_name == "icosahedron" else 0,
              "projected_range": {
                  "logical_x": [min(x for sample in samples for x, _ in sample["vertices"]),
                                max(x for sample in samples for x, _ in sample["vertices"])],
                  "y": [min(y for sample in samples for _, y in sample["vertices"]),
                        max(y for sample in samples for _, y in sample["vertices"])]},
              "marker_storage": "decoded immediate operands" if prefix.operands else "charset RAM",
              "decoded_marker_operands": sum(map(len, prefix.operands.values())),
              "crossing_address_entries_checked": 256 if field_layout else 0,
              "black_border_checked_pending_and_presented": modern_palette,
              "fast_arithmetic_contract": {"rotation_product_bytes_checked": 512,
                                            "projection_entries_checked": 6561,
                                            "projection_valid_pointer_rows_checked": 81,
                                            "projection_pointer_slots_checked": 256,
                                            "projection_zero_gap_bytes_checked": 95,
                                            "projection_table_encoding": "(old signed zoom offset+64) modulo256",
                                            "runtime_xyz_oracle": "original8products independently for each vertex",
                                            "runtime_projection_oracle": "original reciprocal-depth/Q6/signed29over20 order",
                                            "table_kind": "reusable arithmetic, not prepared poses"} if fast_solid else None,
              "fast_material_contract": {"visible_selectors": "immutable modelFaceColor, one fixed material per face",
                                         "hidden_selector": 0,
                                         "depth_diagnostic": "sum of three original-Q6 rotated vertexZ coordinates",
                                         "recorded_depth_bytes_checked": 20 if "fastFaceDepth" in labels else 0,
                                         "shading": "fixed proper3color assignment; no orientation or per-pixel tone change"}
                                        if fast_solid else None,
              "pal_frames_per_presentation": ticks, "raster_irq_line": raster_line,
              "boundary_parity_errors": 0, "distinct_canvases": len(hashes), "screenshots": captures,
              "native_capture_stride": capture_stride,
              "max_geometry_error_pixels": max(sample["geometry_error_pixels"] for sample in samples),
              "fill_union_bytes": {"max": max(sample["fill_union_bytes"] for sample in samples),
                                   "mean": sum(sample["fill_union_bytes"] for sample in samples) / frames},
              "cycles_per_presentation": {"min": min(elapsed), "max": max(elapsed)},
              "independent_checks": ["exact Fraction odd-even polygon interiors", "signed-area visibility",
                                     "boundary markers from independent interior differences",
                                     "field closure including virtual terminal" if field_layout else
                                     "closed color bitplanes in every byte column", "exact multicolor VIC pixels",
                                     "restored generated prefix kernels", "RAM writes restricted to owned workspaces",
                                     "both dirty-field histories and one complete pose per buffer" if gouraud else
                                     "per-buffer/parity dirty bounds and retained opposite rows" if visual_interlaced else
                                     "per-buffer old/new dirty-region lifecycle",
                                     "strict PAL raster/cycle cadence", "unchanged angular speed"] +
                                    (["physical-row/X-lane fixed materials on direct polygon interiors",
                                      "immutable even/odd material and lane-mask tables"] if dither else []) +
                                    (["raw material markers and natural pre-shader fill",
                                      "independent physical-Y Bayer density on direct face interiors",
                                      "immutable tonal masks/code and exact32 charset high operands"] if tonal else []) +
                                    (["shared rotated-normal/light vertex intensities independent of light LUT",
                                      "direct Fraction interiors and exact affine barycentric light threshold",
                                      "virtual q64 closure for both fields"] if gouraud else []) +
                                    (["exact original direct Q6 rotation XYZ and projection coordinates",
                                      "all startup-generated arithmetic products/pointers/gap checked and immutable"]
                                     if fast_solid else []),
              "gif": {"file": gif_name, "frames": frames, "frame_duration_ms": ticks * 20},
              "samples": samples}
    (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "samples"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", type=Path, nargs="?", default=HERE / "build/filled-cube.prg")
    parser.add_argument("--labels", type=Path, default=HERE / "build/filled.sym")
    parser.add_argument("--output", type=Path, default=HERE / "build/filled-verification")
    parser.add_argument("--vice", default=os.environ.get("VICE") or shutil.which("x64sc"))
    parser.add_argument("--ticks", type=int, default=2,
                        help="Expected PAL frames per presentation (default: 2).")
    parser.add_argument("--raster-line", type=int, default=0)
    parser.add_argument("--frames", type=int)
    parser.add_argument("--model", choices=("cube", "icosahedron"), default="cube")
    parser.add_argument("--interlaced", action="store_true", help="Verify alternating fields and retained opposite rows.")
    materials = parser.add_mutually_exclusive_group()
    materials.add_argument("--dither", action="store_true", help="Verify fixed even/odd material patterns; requires icosahedron/interlaced.")
    materials.add_argument("--tonal", action="store_true", help="Verify within-face Bayer light-to-dark toning; requires icosahedron/interlaced.")
    materials.add_argument("--gouraud", action="store_true", help="Verify coherent full-pose Gouraud images; requires icosahedron and implies internal field storage.")
    materials.add_argument("--fast-solid", action="store_true", help="Verify full-row solid icosahedron with exact runtime arithmetic tables.")
    parser.add_argument("--rotation-audit", action="store_true", help="Host-only all-angle fixed-rotation identity audit; requires --fast-solid.")
    parser.add_argument("--fixtures", action="store_true", help="Run boundary/fill CPU fixtures in both buffers.")
    args = parser.parse_args()
    if not args.vice and not args.rotation_audit:
        parser.error("x64sc is missing; install VICE or pass --vice /path/to/x64sc.")
    if args.interlaced and args.model != "icosahedron":
        parser.error("Use --interlaced with --model icosahedron.")
    if args.dither and (args.model != "icosahedron" or not args.interlaced):
        parser.error("Use --dither with --model icosahedron --interlaced.")
    if args.tonal and (args.model != "icosahedron" or not args.interlaced):
        parser.error("Use --tonal with --model icosahedron --interlaced.")
    if args.gouraud and args.model != "icosahedron":
        parser.error("Use --gouraud with --model icosahedron.")
    if args.fast_solid and (args.model != "icosahedron" or args.interlaced):
        parser.error("Use --fast-solid with --model icosahedron and full-row storage.")
    if args.rotation_audit and (not args.fast_solid or args.fixtures):
        parser.error("Use --rotation-audit with --fast-solid and without --fixtures.")
    frames = args.frames if args.frames is not None else 512 // math.gcd(512, args.ticks)
    if frames < 2 or not 0 <= args.raster_line < 312 or not 1 <= args.ticks <= 255:
        parser.error("Use at least 2 frames, a PAL raster line in 0..311 and expected ticks in 1..255.")
    if args.rotation_audit:
        verify_rotation_audit(args.program.resolve(), read_labels(args.labels), args.output.resolve())
    elif args.fixtures:
        fixture_runner = verify_interlaced_fixtures if args.interlaced or args.gouraud else verify_fixtures
        fixture_args = (args.program.resolve(), read_labels(args.labels), args.output.resolve(), args.vice, args.model)
        if args.interlaced or args.gouraud:
            fixture_runner(*fixture_args, dither=args.dither, tonal=args.tonal, gouraud=args.gouraud)
        else:
            fixture_runner(*fixture_args, fast_solid=args.fast_solid)
    else:
        verify(args.program.resolve(), read_labels(args.labels), args.output.resolve(), args.vice,
               frames, args.ticks, args.raster_line, args.model, args.interlaced, args.dither, args.tonal, args.gouraud,
               args.fast_solid)
