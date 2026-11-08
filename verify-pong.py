#!/usr/bin/env python3
"""Verify the self-playing Pong cube against independent game and pixel rules."""

import argparse
from collections import Counter
from dataclasses import asdict, dataclass, replace
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import sys


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("filled_verifier", HERE / "verify-filled.py")
filled = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = filled
SPEC.loader.exec_module(filled)


@dataclass(frozen=True)
class Game:
    ball_x: int = 0
    ball_y: int = 0
    velocity_x: int = 1
    velocity_y: int = 1
    left_y: int = 0
    right_y: int = 0
    phase: int = 0
    misses: int = 0


STATE_LABELS = {"ball_x": "pongBallX", "ball_y": "pongBallY", "velocity_x": "pongBallVX",
                "velocity_y": "pongBallVY", "left_y": "pongLeftY", "right_y": "pongRightY",
                "phase": "pongPhase", "misses": "pongMisses"}


def chase(position, target):
    return max(-17, min(17, position + (target > position) - (target < position)))


def game_step(previous):
    """Paddle pursuit precedes motion; wall reflection precedes paddle contact."""
    left = chase(previous.left_y, previous.ball_y if previous.velocity_x < 0 else 0)
    right = chase(previous.right_y, previous.ball_y if previous.velocity_x > 0 else 0)
    x, y = previous.ball_x + previous.velocity_x, previous.ball_y + previous.velocity_y
    vx, vy, misses = previous.velocity_x, previous.velocity_y, previous.misses
    events = []
    if y >= 22 or y <= -22:
        y = max(-22, min(22, y))
        vy = -vy
        events.append("bottom_wall" if y > 0 else "top_wall")
    if x >= 16 or x <= -16:
        side = "right" if x > 0 else "left"
        paddle = right if x > 0 else left
        if abs(y - paddle) <= 10:
            vx = -vx
            events.append(side + "_paddle")
        else:
            x, y, vy = 0, 0, -vy
            misses = (misses + 1) & 255
            events.append(side + "_miss")
    return Game(x, y, vx, vy, left, right, (previous.phase + 4) & 255, misses), events


def motion_reference(game):
    return ((16 + filled.q6_product(filled.Q6_SINE[game.phase], 4)) & 255,
            (-14 + filled.q6_product(filled.Q6_SINE[(game.phase + 64) & 255], 3)) & 255)


def game_from_ram(ram, labels):
    values = {}
    for field, label in STATE_LABELS.items():
        value = ram[labels[label]]
        values[field] = value - 256 if field not in ("phase", "misses") and value >= 128 else value
    return Game(**values)


def rectangles_reference(game):
    """Face-local court and three white rectangles; V increases screen-down."""
    return (("court", (-27, -27, 27, 27), 0),
            ("left_paddle", (-24, game.left_y - 6, -20, game.left_y + 6), 3),
            ("right_paddle", (20, game.right_y - 6, 24, game.right_y + 6), 3),
            ("ball", (game.ball_x - 2, game.ball_y - 2, game.ball_x + 2, game.ball_y + 2), 3))


def point_reference(axes, u, v):
    """Transform face-local (u,-v,-32) with the original signed Q6 products."""
    result = tuple(filled.q6_product(u, 2 * axes[0][coordinate]) -
                   filled.q6_product(v, 2 * axes[1][coordinate]) - axes[2][coordinate]
                   for coordinate in range(3))
    if any(not -128 <= coordinate < 128 for coordinate in result):
        raise AssertionError("A Pong surface point escaped signed coordinate storage.")
    return result


def axes_reference(yaw, pitch):
    # Recover the three transformed model basis vectors from opposite corners.
    # This is independent of the renderer's cached axis addresses and scratch.
    body = filled.glenz_rotation_reference(yaw, pitch)
    return tuple(tuple((body[1 << axis][coordinate] - body[0][coordinate]) // 2
                       for coordinate in range(3)) for axis in range(3))


def scene_geometry(game):
    yaw, pitch = motion_reference(game)
    body = filled.glenz_rotation_reference(yaw, pitch)
    vertices = filled.glenz_projection_reference(body)
    axes = axes_reference(yaw, pitch)
    shapes = []
    for name, (u0, v0, u1, v1), color in rectangles_reference(game):
        local = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
        rotated = tuple(point_reference(axes, u, v) for u, v in local)
        if any(not (-41 <= x <= 41 and -41 <= y <= 41 and -48 <= z <= 0) for x, y, z in rotated):
            raise AssertionError(f"Pong shape {name} escaped the projection lookup domain.")
        shapes.append({"name": name, "local": local, "rotated_xyz": rotated,
                       "projected": filled.glenz_projection_reference(rotated), "color": color})
    return yaw, pitch, body, vertices, shapes


def pixel_reference(base_colors, vertices, active, shapes, entity_areas=None):
    """Opaque assignment oracle; it never constructs expected XOR deltas."""
    faces = [quad for quad, _ in filled.face_quads()]
    visible = filled.visible_faces_reference(vertices)
    base = filled.polygon_reference([(tuple(vertices[index] for index in face), color)
                                     for parent, (face, color) in enumerate(zip(faces, base_colors))
                                     if visible & (1 << parent)])
    result = bytearray(base)
    if not active:
        return result
    face = tuple(vertices[index] for index in faces[4])
    parent = filled.polygon_reference([(face, 1)])
    court = filled.polygon_reference([(tuple(shapes[0]["projected"]), 1)])
    ink = bytearray(filled.WIDTH * filled.HEIGHT)
    for shape in shapes:
        coverage = filled.polygon_reference([(tuple(shape["projected"]), 1)])
        count = sum(coverage)
        if not count:
            raise AssertionError(f"Pong rectangle {shape['name']} collapsed to zero projected pixels.")
        if entity_areas is not None and shape["name"] != "court":
            area = entity_areas.setdefault(shape["name"], {"min": filled.WIDTH * filled.HEIGHT, "max": 0})
            area["min"], area["max"] = min(area["min"], count), max(area["max"], count)
        for index, covered in enumerate(coverage):
            if not covered:
                continue
            if not parent[index] or base[index] != base_colors[4]:
                raise AssertionError("Pong pixels left their owning opaque cube face.")
            if shape["name"] != "court":
                if not court[index]:
                    raise AssertionError("A Pong entity escaped the black court.")
                if ink[index]:
                    raise AssertionError("Projected Pong entities overlap and would cancel under XOR.")
                ink[index] = 1
            result[index] = shape["color"]
    return result


class PongModel(filled.ReferenceModel):
    def __init__(self, original, labels):
        super().__init__("cube", original, labels)
        self.name = "pong"
        self.colors = [2, 2, 3, 3, 1, 1]
        self.geometry_tolerance = 4.4
        load = int.from_bytes(original[:2], "little")

        def data(label, count):
            first = labels[label]
            value = original[2 + first - load:2 + first - load + count]
            if len(value) != count:
                raise AssertionError(f"Pong data {label} lies outside the assembled program.")
            self.immutable.append((first, value))
            return value

        constants = {"pongHalfSize": 32, "pongCourtHalfSize": 27, "pongPaddleInner": 20,
                     "pongPaddleOuter": 24, "pongPaddleHalfHeight": 6, "pongPaddleLimit": 17,
                     "pongBallHalfSize": 2, "pongCollisionRadius": 4, "pongPaddleContact": 16,
                     "pongWallContact": 22, "pongPaddleHitHalfHeight": 10,
                     "pongYawBias": 16, "pongYawAmplitude": 4, "pongPitchAmplitude": 3, "pongPhaseStep": 4}
        if any(labels.get(label) != expected for label, expected in constants.items()):
            raise AssertionError("Pong model/game constants differ from the independent game contract.")
        if labels.get("pongPitchBias", 0) & 255 != (-14 & 255):
            raise AssertionError("Pong pitch bias differs from the visible three-face view.")
        if [tuple(row) for row in zip(*(data("pongFace" + axis, 6) for axis in "ABCD"))] != list(self.faces):
            raise AssertionError("Pong body faces differ from the independent outward cube quads.")
        if data("pongFaceColor", 6) != bytes(self.colors) or data("pongFaceBits", 6) != bytes(1 << i for i in range(6)):
            raise AssertionError("Pong body colors or parent visibility masks changed.")
        adjacency = {}
        for parent, face in enumerate(self.faces):
            for first, last in zip(face, face[1:] + face[:1]):
                adjacency.setdefault(tuple(sorted((first, last))), set()).add(parent)
        seen = set()
        for first, last, a, b in zip(*(data("pongEdge" + field, 12) for field in ("A", "B", "FaceA", "FaceB"))):
            edge = tuple(sorted((first, last)))
            if edge in seen or edge not in adjacency or {a, b} != adjacency[edge]:
                raise AssertionError("Pong body edge tables differ from independent cube adjacency.")
            seen.add(edge)
        for label, expected in filled.half32_arithmetic_tables_reference():
            if data(label, len(expected)) != expected:
                raise AssertionError(f"Pong arithmetic table {label} differs from the original Q6 contract.")
        for prefix in ("pongTables", "pongPrepareCode", "pongDrawCode", "pongRuntimeCode"):
            data(prefix + "Start", labels[prefix + "End"] - labels[prefix + "Start"])
        if data("pongPaddleDirections", 2) != bytes((255, 1)):
            raise AssertionError("Pong paddle direction mapping changed.")
        if labels["pongStateEnd"] - labels["pongStateStart"] != 8 or any(
                not labels["pongStateStart"] <= labels[label] < labels["pongStateEnd"] for label in STATE_LABELS.values()):
            raise AssertionError("Pong game state escaped its declared eight-byte ownership.")
        addresses = {"pongProjectionTablesStart": 0xe000, "pongProjectionOffsets": 0xe000,
                     "pongProjectionOffsetsEnd": 0xefe3, "pongProjectionRowLo": 0xfb00,
                     "pongProjectionRowHi": 0xfb80, "pongProjectionTablesEnd": 0xfc00}
        if any(labels.get(label) != value for label, value in addresses.items()):
            raise AssertionError("Pong projection lookup ownership or dimensions changed.")
        lookup = bytearray(0x1c00)
        for z in range(-48, 1):
            row = 0xe000 + (z + 48) * 83
            lookup[0x1b00 + z + 48], lookup[0x1b80 + z + 48] = row & 255, row >> 8
            depth = math.floor(8192 / (144 + z) + 0.5)
            for coordinate in range(-41, 42):
                lookup[row - 0xe000 + coordinate + 41] = (filled.q6_product(coordinate, depth) + 64) & 255
        self.runtime_immutable.append((0xe000, bytes(lookup)))

    def geometry(self, yaw, pitch):
        return filled.glenz_geometry_reference(yaw, pitch)

    def visibility(self, vertices):
        mask = filled.visible_faces_reference(vertices)
        return [bool(mask & (1 << parent)) for parent in range(6)]


class PongScene:
    palette_indices = (0, 6, 3, 1)
    gif_name = "pong-cube.gif"

    def __init__(self, original, labels):
        self.model = PongModel(original, labels)
        self.labels = labels
        self.owned_ranges = [(labels["pongStateStart"], labels["pongStateEnd"])]
        self.state = Game()
        self.events = Counter()
        self.frames = 0

    def pending(self, index, ram, vertices, rotated, yaw, pitch):
        if index != self.frames:
            raise AssertionError("Pong verification lost its consecutive game-step lifecycle.")
        events = []
        if index:
            self.state, events = game_step(self.state)
            self.events.update(events)
        if game_from_ram(ram, self.labels) != self.state:
            raise AssertionError(f"Live Pong state differs from independent game rules at update{index}.")
        if (yaw, pitch) != motion_reference(self.state):
            raise AssertionError("Pong cube motion differs from the live phase oscillator.")
        _, _, expected_rotated, expected_vertices, shapes = scene_geometry(self.state)
        if rotated != expected_rotated or vertices != expected_vertices:
            raise AssertionError("Pong body geometry differs from the independent Q6 cube transform.")
        mask = filled.visible_faces_reference(vertices)
        if not mask & (1 << 4):
            raise AssertionError("Bounded Pong motion hid its playing face.")
        materials = [color if mask & (1 << face) else 0 for face, color in enumerate(self.model.colors)]
        if list(ram[self.labels["xorFaceColors"]:self.labels["xorFaceColors"] + 6]) != materials:
            raise AssertionError("Pong body materials differ from independent parent visibility.")
        scratch = list(zip(*(tuple(value - 256 if value >= 128 else value for value in
                                  ram[self.labels["rotated" + axis] + 8:self.labels["rotated" + axis] + 12])
                            for axis in "XYZ")))
        projected = list(zip(ram[self.labels["projectedX"] + 8:self.labels["projectedX"] + 12],
                             ram[self.labels["projectedY"] + 8:self.labels["projectedY"] + 12]))
        matches = [shape["name"] for shape in shapes if list(shape["rotated_xyz"]) == scratch and
                   shape["projected"] == projected]
        if not matches:
            raise AssertionError("Pong scratch geometry/projection differs from all independently transformed quads.")
        expected = pixel_reference(self.model.colors, vertices, True, shapes)
        self.frames += 1
        return expected, {"game": asdict(self.state), "events": events, "shapes": shapes,
                          "native_scratch_matches": matches}

    def presented(self, index, ram):
        if game_from_ram(ram, self.labels) != self.state:
            raise AssertionError("Rendering modified Pong state before the scheduled game update.")

    def report(self):
        if self.frames >= 128 and any(not self.events[event] for event in
                                      ("left_paddle", "right_paddle", "top_wall", "bottom_wall")):
            raise AssertionError("The native Pong run did not exercise both paddles and both walls.")
        return {"game": "live signed-unit Pong; pursuit AI then ball motion, walls and paddle decisions",
                "updates_checked": max(0, self.frames - 1), "events_checked": dict(self.events),
                "motion": "phase+=4, yaw=16+M(sin,4), pitch=-14+M(cos,3)",
                "pixel_oracle": "independent opaque court/entity assignment, not XOR of renderer deltas",
                "projection_lookup_entries_checked": 4067, "projection_pointer_slots_checked": 128,
                "unused_pointer_slots_zero": 79, "projection_gap_zero_bytes_checked": 2845,
                "game_update_cost_included_in_presentation_cadence": True}


def audit_domain():
    minimum, maximum = [127, 127, 127], [-128, -128, -128]
    maximum_index, checked = 0, 0
    front = list(filled.face_quads())[4][0]
    for phase in range(0, 256, 4):
        yaw, pitch = motion_reference(Game(phase=phase))
        axes = axes_reference(yaw, pitch)
        body = filled.glenz_projection_reference(filled.glenz_rotation_reference(yaw, pitch))
        if not filled.visible_faces_reference(body) & (1 << 4):
            raise AssertionError("The bounded motion hides the Pong face.")
        if filled.visible_faces_reference(body).bit_count() != 3:
            raise AssertionError("The Pong view no longer exposes three cube faces.")
        quad = [body[index] for index in front]
        for u in range(-27, 28):
            for v in range(-27, 28):
                point = point_reference(axes, u, v)
                if not (-41 <= point[0] <= 41 and -41 <= point[1] <= 41 and -48 <= point[2] <= 0):
                    raise AssertionError("A legal court point escaped the projection lookup.")
                projected = filled.glenz_projection_reference([point])[0]
                for a, b in zip(quad, quad[1:] + quad[:1]):
                    if (b[0] - a[0]) * (projected[1] - a[1]) - (b[1] - a[1]) * (projected[0] - a[0]) < 0:
                        raise AssertionError("A legal court point escaped the projected front face.")
                for axis, value in enumerate(point):
                    minimum[axis], maximum[axis] = min(minimum[axis], value), max(maximum[axis], value)
                depth = math.floor(8192 / (144 + point[2]) + 0.5)
                maximum_index = max(maximum_index, *(abs(value + sign * depth) for value in point[:2] for sign in (-1, 1)))
                checked += 1
    return {"pass": True, "motion_phases": 64, "visible_body_faces_per_pose": 3,
            "integer_uv_points_checked": checked,
            "coordinate_minimum": minimum, "coordinate_maximum": maximum,
            "maximum_projection_product_index": maximum_index, "outside_parent_points": 0}


def audit_game(model, limit=4096):
    game, seen, events = Game(), {}, Counter()
    entity_areas = {}
    for frame in range(limit):
        if game in seen:
            return {"pass": True, "states_checked": frame, "cycle_start": seen[game],
                    "cycle_length": frame - seen[game], "events": dict(events),
                    "opaque_xor_mismatches": 0, "projected_entity_overlap_pixels": 0,
                    "entity_pixel_areas": entity_areas}
        seen[game] = frame
        if not (-16 <= game.ball_x <= 16 and -22 <= game.ball_y <= 22 and
                abs(game.velocity_x) == abs(game.velocity_y) == 1 and
                -17 <= game.left_y <= 17 and -17 <= game.right_y <= 17):
            raise AssertionError("Pong simulation escaped its signed-unit game bounds.")
        _, _, _, vertices, shapes = scene_geometry(game)
        expected = pixel_reference(model.colors, vertices, True, shapes, entity_areas)
        visible = filled.visible_faces_reference(vertices)
        encoded = filled.polygon_reference([
            (tuple(vertices[index] for index in face), color)
            for parent, (face, color) in enumerate(zip(model.faces, model.colors)) if visible & (1 << parent)] +
            [(tuple(shape["projected"]), 1 if shape["name"] == "court" else 3) for shape in shapes])
        if encoded != expected:
            raise AssertionError("Pong XOR encoding differs from opaque court/entity assignment.")
        game, happened = game_step(game)
        events.update(happened)
    raise AssertionError("Pong host audit did not reach a complete deterministic game/motion cycle.")


def game_fixture_cases():
    initial = Game()
    return [("old-ball-ai", replace(initial, ball_y=10, right_y=10), []),
            ("bottom-wall", replace(initial, ball_y=21), ["bottom_wall"]),
            ("top-wall", replace(initial, ball_y=-21, velocity_y=-1), ["top_wall"]),
            ("right-paddle", replace(initial, ball_x=15), ["right_paddle"]),
            ("left-paddle", replace(initial, ball_x=-15, velocity_x=-1), ["left_paddle"]),
            ("inclusive-hit-radius", replace(initial, ball_x=15, ball_y=10), ["right_paddle"]),
            ("outside-hit-radius", replace(initial, ball_x=15, ball_y=11), ["right_miss"]),
            ("left-miss", replace(initial, ball_x=-15, ball_y=-20, velocity_x=-1,
                                  velocity_y=-1, left_y=17), ["left_miss"]),
            ("wall-before-miss", replace(initial, ball_x=15, ball_y=21, right_y=-17),
             ["bottom_wall", "right_miss"]),
            ("miss-counter-wrap", replace(initial, ball_x=15, ball_y=20, right_y=-17, misses=255), ["right_miss"]),
            ("phase-wrap", replace(initial, phase=252), []),
            ("paddle-clamp", replace(initial, ball_y=22, right_y=17), ["bottom_wall"])]


def verify_game_fixtures(program, labels, output, executable):
    model = PongModel(program.read_bytes(), labels)
    results = []
    with filled.machine(executable, program, output) as monitor:
        ready = labels.get("boundariesReady", labels.get("boundaryReady"))
        monitor.run(f"break {ready:04x}")
        monitor.run("x")
        monitor.run("delete 1")
        filled.write_memory(monitor, 0xd011, [0x0b])
        filled.write_memory(monitor, 0xd01a, [0])
        filled.write_memory(monitor, 0xd019, [0x0f])
        filled.write_memory(monitor, 0x0200, [0x4c, 0x00, 0x02])
        monitor.run("r pc=$0200")
        monitor.run("step $3000")
        monitor.run("break 0203")
        allowed = [(0x0100, 0x0206), (0xc0, 0xca), (labels["linePointer"], labels["squareSum"] + 1),
                   (labels["pongStateStart"], labels["pongStateEnd"]), (labels["angleYaw"], labels["anglePitch"] + 1)]
        baseline = bytearray(filled.read_ram(monitor, output))
        for first, last in allowed:
            baseline[first:last] = bytes(last - first)
        for name, state, required_events in game_fixture_cases():
            expected, events = game_step(state)
            if events != required_events:
                raise AssertionError(f"Game fixture {name} does not exercise its intended collision path.")
            for field, label in STATE_LABELS.items():
                filled.write_memory(monitor, labels[label], [getattr(state, field) & 255])
            cycles = filled.call(monitor, labels["pongUpdate"], measure=True)
            ram = filled.read_ram(monitor, output)
            if game_from_ram(ram, labels) != expected:
                raise AssertionError(f"Real Pong update failed fixture {name}.")
            if (ram[labels["angleYaw"]], ram[labels["anglePitch"]]) != motion_reference(expected):
                raise AssertionError(f"Real Pong motion failed fixture {name}.")
            model.check_immutable(ram)
            stable = bytearray(ram)
            for first, last in allowed:
                stable[first:last] = bytes(last - first)
            if stable != baseline:
                raise AssertionError(f"Pong game update wrote outside its owned state in fixture {name}.")
            results.append({"name": name, "input": asdict(state), "expected": asdict(expected),
                            "events": events, "cycles_with_call_return": cycles, "pass": True})
    report = {"pass": True, "program_sha256": hashlib.sha256(program.read_bytes()).hexdigest(),
              "fixture_cases": len(results), "maximum_game_update_cycles": max(row["cycles_with_call_return"] for row in results),
              "timing_scope": "real update including JSR/RTS, display DMA and raster IRQ disabled", "samples": results}
    (output / "game-fixtures.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "samples"}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", type=Path, nargs="?", default=HERE / "build/pong-cube.prg")
    parser.add_argument("--labels", type=Path, default=HERE / "build/pong.sym")
    parser.add_argument("--output", type=Path, default=HERE / "build/pong/verification")
    parser.add_argument("--vice", default=os.environ.get("VICE") or shutil.which("x64sc"))
    parser.add_argument("--frames", type=int, default=706)
    parser.add_argument("--ticks", type=int, default=2)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--audit", action="store_true", help="Host-only full court domain and complete game/motion cycle.")
    modes.add_argument("--fixtures", action="store_true", help="Real boundary/fill and controlled game-update fixtures.")
    args = parser.parse_args()
    program, output = args.program.resolve(), args.output.resolve()
    labels = filled.read_labels(args.labels)
    model = PongModel(program.read_bytes(), labels)
    if args.audit:
        report = {"pass": True, "program_sha256": hashlib.sha256(program.read_bytes()).hexdigest(),
                  "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "domain": audit_domain(), "game_and_pixels": audit_game(model)}
        output.mkdir(parents=True, exist_ok=True)
        (output / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
    elif args.fixtures:
        if not args.vice:
            parser.error("VICE is required for native fixtures.")
        filled.verify_fixtures(program, labels, output / "boundaries", args.vice, model_name="pong",
                               reference_model=model, cached_boundary=True)
        verify_game_fixtures(program, labels, output / "game", args.vice)
    else:
        if not args.vice or args.frames < 2 or not 1 <= args.ticks <= 255:
            parser.error("Use VICE, at least two frames, and a positive PAL-tick cadence.")
        filled.verify(program, labels, output, args.vice, args.frames, args.ticks, 0,
                      model_name="pong", scene_factory=PongScene)


if __name__ == "__main__":
    main()
