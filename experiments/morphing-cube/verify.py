#!/usr/bin/env python3
"""Check live morph geometry, convex coverage and complete native PAL output."""
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess

from PIL import Image, ImageChops

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT = HERE / 'build/verification'
QUADS = ((0, 4, 6, 2), (1, 3, 7, 5), (0, 1, 5, 4),
         (2, 6, 7, 3), (0, 2, 3, 1), (4, 5, 7, 6))
COLORS = (1, 1, 2, 2, 3, 3, 1, 2, 3, 1, 2, 3, 1, 2)
MARK_COLORS = (2, 2, 3, 3, 1, 1)


def topology():
    faces = []
    for corners in QUADS:
        face = []
        for index, corner in enumerate(corners):
            incoming = (corner ^ corners[index - 1]).bit_length() - 1
            outgoing = (corner ^ corners[(index + 1) % 4]).bit_length() - 1
            face.extend((corner * 3 + incoming, corner * 3 + outgoing))
        faces.append(face)
    for corner in range(8):
        order = (0, 1, 2) if corner.bit_count() % 2 else (0, 2, 1)
        faces.append([corner * 3 + axis for axis in order])
    return faces


FACES = topology()
BODY_EDGES = {}
for _face in FACES:
    for _a, _b in zip(_face, _face[1:] + _face[:1]):
        _edge = tuple(sorted((_a, _b)))
        BODY_EDGES[_edge] = BODY_EDGES.get(_edge, 0) + 1
assert len(BODY_EDGES) == 36 and set(BODY_EDGES.values()) == {2}
assert 24 - len(BODY_EDGES) + len(FACES) == 2


def rounded(value):
    return math.floor(value + 0.5)


def scaled(a, b):
    assert abs(a + b) <= 128 and abs(a - b) <= 128
    return (a + b) ** 2 // 256 - (a - b) ** 2 // 256


def coverage(polygon):
    """Direct rational crossing ceilings; no incremental line sampler replay."""
    pixels = set()
    for x in range(min(p[0] for p in polygon), max(p[0] for p in polygon)):
        crossings = []
        for p, q in zip(polygon, polygon[1:] + polygon[:1]):
            if p[0] > q[0]:
                p, q = q, p
            if p[0] <= x < q[0]:
                denominator = q[0] - p[0]
                numerator = p[1] * denominator + (q[1] - p[1]) * (x - p[0])
                crossings.append(-(-numerator // denominator))
        crossings.sort()
        assert len(crossings) % 2 == 0
        for first, last in zip(crossings[::2], crossings[1::2]):
            pixels.update((x, y) for y in range(first, last))
    return pixels


def reference(phase):
    cut = 9 + rounded(5 * math.sin(phase * math.tau / 64))
    yaw = 4 * phase + 1
    pitch = rounded(24 * math.sin(phase * math.tau / 64 + 0.4))
    sy, cy = (rounded(64 * math.sin((yaw + offset) * math.tau / 256)) for offset in (0, 64))
    sp, cp = (rounded(64 * math.sin((pitch + offset) * math.tau / 256)) for offset in (0, 64))
    model = []
    for corner in range(8):
        for edge_axis in range(3):
            model.append(tuple((1 if corner & (1 << axis) else -1)
                               * (24 - cut if axis == edge_axis else 24)
                               for axis in range(3)))
    for face in range(6):
        axis, sign = face // 2, 1 if face % 2 else -1
        u, v = (axis + 1) % 3, (axis + 2) % 3
        for first, second in ((-7, -7), (9, -7), (0, 10)):
            point = [0, 0, 0]
            point[axis], point[u], point[v] = sign * 24, first, second
            model.append(tuple(point))
    # Exact supporting-plane contracts for the live truncated-cube body.
    for point in model[:24]:
        assert all(abs(value) <= 24 for value in point)
        for corner in range(8):
            assert sum(value * (1 if corner & (1 << axis) else -1)
                       for axis, value in enumerate(point)) <= 72 - cut
    rotated, projected = [], []
    max_error = 0
    for x, y, z in model:
        xx = scaled(x, cy) + scaled(z, sy)
        zz = scaled(z, cy) - scaled(x, sy)
        yy = scaled(y, cp) - scaled(zz, sp)
        zz = scaled(zz, cp) + scaled(y, sp)
        rotated.append((xx, yy, zz))
        factor = rounded(96 * 64 / (144 + zz))
        pixel = (32 + scaled(xx, factor), 64 - 2 * scaled(yy, factor))
        assert 0 <= pixel[0] < 64 and 0 <= pixel[1] < 128
        projected.append(pixel)
        angle_yaw, angle_pitch = yaw * math.tau / 256, pitch * math.tau / 256
        fx = x * math.cos(angle_yaw) + z * math.sin(angle_yaw)
        fz = z * math.cos(angle_yaw) - x * math.sin(angle_yaw)
        fy = y * math.cos(angle_pitch) - fz * math.sin(angle_pitch)
        fz = fz * math.cos(angle_pitch) + y * math.sin(angle_pitch)
        ideal = (32 + 96 * fx / (144 + fz), 64 - 192 * fy / (144 + fz))
        max_error = max(max_error, math.hypot(2 * (pixel[0] - ideal[0]), pixel[1] - ideal[1]))
    assert max_error < 8
    polygons = [[projected[index] for index in face] for face in FACES]
    areas = [sum(p[0] * q[1] - p[1] * q[0]
                 for p, q in zip(poly, poly[1:] + poly[:1])) for poly in polygons]
    visible = [int(area > 0) for area in areas]
    pixel_colors, parent_pixels = {}, {}
    for face, polygon in enumerate(polygons):
        if not visible[face]:
            continue
        pixels = coverage(polygon)
        assert not pixels.intersection(pixel_colors), (phase, 'overlapping body faces', face)
        parent_pixels[face] = pixels
        pixel_colors.update((pixel, COLORS[face]) for pixel in pixels)
    normal_z = (-scaled(sy, cp), sp, scaled(cy, cp))
    mark_visible = []
    for face in range(6):
        normal = normal_z[face // 2] * (1 if face % 2 else -1)
        on = int(visible[face] and normal <= -32)
        mark_visible.append(on)
        if on:
            pixels = coverage(projected[24 + face * 3:27 + face * 3])
            assert pixels <= parent_pixels[face], (phase, 'stencil outside parent', face)
            pixel_colors.update((pixel, MARK_COLORS[face]) for pixel in pixels)
    assert any(mark_visible)
    charset = bytearray(2048)
    for (x, y), color in pixel_colors.items():
        charset[(x // 4) * 128 + y] |= color << (6 - 2 * (x % 4))
    markers = bytearray(2048)
    for column in range(16):
        previous = 0
        for y in range(128):
            current = charset[column * 128 + y]
            markers[column * 128 + y] = previous ^ current
            previous = current
    return {'cut': cut, 'yaw': yaw, 'pitch': pitch, 'model': model, 'rotated': rotated,
            'projected': projected, 'visible': visible, 'marks': mark_visible,
            'normal_z': normal_z, 'charset': bytes(charset), 'markers': bytes(markers),
            'max_ideal_error_physical_pixels': max_error}


def expected_image(record, palette):
    patch = Image.new('RGB', (128, 128))
    colors = (0, 6, 3, 1)
    pixels = []
    for y in range(128):
        for x in range(128):
            logical = x // 2
            byte = record['charset'][(logical // 4) * 128 + y]
            selector = (byte >> (6 - 2 * (logical % 4))) & 3
            pixels.append(palette[colors[selector]])
    patch.putdata(pixels)
    return patch


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'proof.json').unlink(missing_ok=True)
    references = [reference(phase) for phase in range(64)]
    assert {row['cut'] for row in references} == set(range(4, 15))
    spec = importlib.util.spec_from_file_location('morph_monitor', ROOT / 'verify.py')
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    labels = shared.read_labels(HERE / 'build/main.sym')
    palette = [tuple(int(value, 16) for value in line.split()[:3])
               for line in (ROOT / 'palettes/colodore.vpl').read_text().splitlines()
               if line and not line.startswith('#')]
    with socket.socket() as reserve:
        reserve.bind(('127.0.0.1', 0))
        port = reserve.getsockname()[1]
    program = HERE / 'build/example.prg'
    command = shared.vice_command(os.environ.get('VICE', 'x64sc'), program, port,
                                  ROOT / 'palettes/colodore.vpl')
    process = monitor = None
    observations, images, clocks = [], [], []
    with (OUTPUT / 'vice.log').open('w') as log:
        try:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            monitor = shared.Monitor(shared.connect_monitor(process, port))
            monitor.run('r')
            monitor.run(f'break ${labels["framePresented"]:04x}')
            for index in range(66):
                monitor.run('x')
                registers = monitor.run('r')
                monitor.run('bank ram')
                ram = monitor.memory(OUTPUT / f'pose-{index:02d}.ram', 0, 65535)
                phase = index % 64
                row = references[phase]
                assert ram[labels['shownPhase']] == phase
                assert int.from_bytes(ram[labels['presentationCount']:labels['presentationCount'] + 2], 'little') == index + 1
                assert ram[labels['cutValue']] == row['cut']
                for name, values in (('modelX', row['model']), ('rotatedX', row['rotated'])):
                    for axis in range(3):
                        address = labels[name] + axis * 42
                        expected = bytes(point[axis] & 255 for point in values)
                        assert ram[address:address + 42] == expected, (index, name, axis)
                for axis, name in enumerate(('projectedX', 'projectedY')):
                    assert ram[labels[name]:labels[name] + 42] == bytes(point[axis] for point in row['projected']), (index, name)
                assert ram[labels['faceVisible']:labels['faceVisible'] + 14] == bytes(row['visible'])
                assert ram[labels['markVisible']:labels['markVisible'] + 6] == bytes(row['marks'])
                assert ram[labels['normalZ']:labels['normalZ'] + 3] == bytes(value & 255 for value in row['normal_z'])
                base = 0x2800 if index % 2 == 0 else 0x2000
                assert ram[base:base + 2048] == row['charset'], (index, 'complete charset')
                assert ram[0x4000:0x4800] == row['markers'], (index, 'boundary parity')
                cpu = re.search(r'^\.;[0-9a-fA-F]{4}\s+(.*)$', registers, re.M)[1].split()
                line, cycle, clock = map(int, cpu[-3:])
                assert 0 <= line < 48, (index, 'charset publication after top border', line, cycle)
                clocks.append(clock)
                observation = {'presentation': index + 1, 'phase': phase, 'cut': row['cut'],
                               'yaw': row['yaw'], 'pitch': row['pitch'], 'visible_faces': sum(row['visible']),
                               'visible_stencils': sum(row['marks']), 'front_charset': base,
                               'clock': clock, 'raster': [line, cycle]}
                if index in (1, 9, 17, 25, 33, 41, 49, 57, 65):
                    name = f'visible-phase-{(phase - 1) % 64:02d}-{index:02d}.png'
                    monitor.run(f'screenshot "{OUTPUT / name}" 2')
                    image = Image.open(OUTPUT / name).convert('RGB')
                    expected = Image.new('RGB', image.size, palette[0])
                    expected.paste(expected_image(references[(phase - 1) % 64], palette), (128, 67))
                    difference = ImageChops.difference(image, expected)
                    if difference.getbbox() is not None:
                        expected.save(OUTPUT / 'expected-failed.png')
                        difference.save(OUTPUT / 'difference-failed.png')
                        raise AssertionError((index, 'complete native image'))
                    images.append(image)
                    observation['screenshot'] = name
                observations.append(observation)
            monitor.connection.sendall(b'quit\n')
            process.wait(timeout=5)
        finally:
            if process is not None and process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            if monitor is not None:
                (OUTPUT / 'monitor.log').write_text('\n'.join(monitor.transcript))
                monitor.connection.close()
    images[0].save(OUTPUT / 'morphing-cube.gif', save_all=True, append_images=images[1:], duration=250, loop=0)
    intervals = [b - a for a, b in zip(clocks, clocks[1:])]
    field_intervals = []
    for a, b in zip(observations, observations[1:]):
        phase_delta = 63 * (b['raster'][0] - a['raster'][0]) + b['raster'][1] - a['raster'][1]
        elapsed = b['clock'] - a['clock'] - phase_delta
        assert elapsed > 0 and elapsed % 19656 == 0
        field_intervals.append(elapsed // 19656)
    report = {'pass': True, 'program_sha256': hashlib.sha256(program.read_bytes()).hexdigest(),
              'moving_poses': 64, 'presentations': len(observations), 'cut_range': [4, 14],
              'body_vertices': 24, 'body_faces': 14, 'stencil_vertices': 18,
              'body_edges': len(BODY_EDGES), 'convex_disjoint_coverage_poses': 64,
              'contained_stencil_coverage_poses': 64,
              'shared_edge_sampler_sha256': hashlib.sha256((HERE.parent / 'lib/polygon-edges.asm').read_bytes()).hexdigest(),
              'complete_charsets_compared': len(observations), 'bytes_per_charset': 2048,
              'complete_marker_planes_compared': len(observations), 'native_images': len(images),
              'pixels_per_native_image': images[0].width * images[0].height,
              'max_ideal_geometry_error_physical_pixels': max(row['max_ideal_error_physical_pixels'] for row in references),
              'publication_interval_pal_clocks': [min(intervals), max(intervals)],
              'mean_publication_interval_pal_clocks': sum(intervals) / len(intervals),
              'pal_fields_per_publication': field_intervals,
              'observations': observations, 'command': command, 'owned_process_returncode': process.returncode,
              'limits': ['Own 24-vertex truncation and18 stencil vertices, not Tower Power\'s original24+15 model.',
                         'All64 authored moving poses checked; arbitrary angles/camera settings and physical hardware are not covered.']}
    (OUTPUT / 'proof.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key not in ('observations', 'command')}, indent=2))


if __name__ == '__main__':
    main()
