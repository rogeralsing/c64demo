#!/usr/bin/env python3
"""Classify captured camera-space triangles and replay selected native spans.

Passive data analysis only. No SDK, generated CPU code, build or emulator runs.
"""

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = ROOT / 'build/research/3dvibe64-camera/analysis'
OLD_PROOF = 'build/research/3dvibe64-profile/pixel-analysis/profile-pixels-proof.json'
UNITS_PROOF = 'build/research/3dvibe64-camera/source-analysis/units-proof.json'
BASE = ROOT / 'build/research/3dvibe64-camera'
CASE = BASE / 'native-01'
CASE_SHA = '4b320fcca0330ff3f11338a810340ec8cde71fd80ec082080be0325118c69463'
PROGRAM = ROOT / 'build/research/3dvibe64-native/build-01/products/3Dvibe64.prg'
DUMPS = 'm 0100 01ff; m 000b 002f; m b43b b441'
PINS = {
    'research/3dvibe64-native/pixels.py': '859e1ece975ea57c283cf0c4dcef47be95cf91c72d8d9eba29cd4765da8e16a2',
    'research/3dvibe64-overdraw/omit_groups.py': '3683d59029dbb251e56a33536d83837ae22b799407ff54501c0c694c777accb4',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    OLD_PROOF: 'a564dc770db6b02afc66607b259cd71971b9ef2810200c642fd5c4cae1cb2710',
    UNITS_PROOF: '665e9233aafe5cc3e25e82b497549117a04f64f2a14fa5f0c335290970284551',
    'research/3dvibe64-profile/check_pixels.py': 'c6c4d9e4d72b2c31f2a29a69f60f127555c5ab4a5c4aa9b70f8f75f81bbb3f94',
    'research/verify_vice_live.py': 'f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a',
    'research/vice_session_live.py': '4340d1b0394fa612f5e6a71edddcbc2daf947e59c4c3013ab3b850c886dc621c',
    'research/anomaly/scanout.py': 'c5e63a07f3060614710518aaf9b9e6c9365c297619af4e19719a4b5f8b62198f',
    'build/research/3dvibe64-camera/native-01-pin.json': 'ac6999155804945682533e35bcdfad8286c11bcd213a43e96da865fa024e4637',
    'build/research/3dvibe64-camera/capture-records.json': 'feda3215a3b75290991d277acd951660599ea871769f346c4305b8ac25b89ec4',
    'research/3dvibe64-camera/capture-plan.json': '9b33193e3d6ed460a48c33b3c0f71d9ae7eba58f7c27796ad76abf0d44aa3dd7',
    'research/3dvibe64-native/scene.json': '2dc0c5d4a8bab84ae522a31da6b7e998e346cce1dd0ffe6693ab01990ca6f72a',
    'build/research/3dvibe64-native/build-01/products/3Dvibe64.asm': '22008b3a92b7896c699543b12f9036704797262aa3558cd9116d8a09c85b796f',
    'build/research/3dvibe64-native/build-01/products/3Dvibe64.prg': '69b0d86f79106b2bf9654d85bd631bc68c12f4efd708454a0048560b3c1bfdeb',
    'build/research/3dvibe64-native/symbols-01/3Dvibe64.labels': '265a1770fe7a605139f0cdfd9d2983f6ddb314a1cf234a6f3a14d6f3b344e847',
    'palettes/colodore.vpl': 'cfc740890e811b94a73bbbe9f38c400f6714d37c6b6167935adf4f892422b972',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def load(name, path):
    assert sha((ROOT / path).read_bytes()) == PINS[path], path
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def signed(value, bits):
    return value if value < (1 << (bits - 1)) else value - (1 << bits)


def minus(a, b):
    return tuple(x - y for x, y in zip(a, b))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def plane(points, triangle, eye=(0, 0, 0)):
    a, b, c = [points[i] for i in triangle]
    normal = cross(minus(b, a), minus(c, a))
    value = dot(normal, minus(eye, a))
    return dict(vertices=triangle, anchor=a, normal=normal, signed_eye_side=value,
                front_facing=value > 0, tangent=value == 0, degenerate=normal == (0, 0, 0))


def algebra_controls(points, triangles):
    offset = (37, -19, 211)
    translated = [tuple(p[i] + offset[i] for i in range(3)) for p in points]
    scaled = [tuple(2 * value for value in p) for p in points]
    for triangle in triangles:
        a, b, c = triangle
        value = plane(points, triangle)['signed_eye_side']
        assert value == -dot(points[a], cross(points[b], points[c]))
        assert plane(points, [b, c, a])['signed_eye_side'] == value
        assert plane(points, [a, c, b])['signed_eye_side'] == -value
        assert plane(translated, triangle, offset)['signed_eye_side'] == value
        assert plane(scaled, triangle)['signed_eye_side'] == 8 * value
    return dict(exact_integer_determinant_identity=True, cyclic_winding_preserves_side=True,
        reversed_winding_negates_side=True, common_vertex_and_eye_translation_preserves_side=True,
        uniform_positive_scale_two_multiplies_side_by_eight=True,
        arithmetic='Python unbounded signed integers, no fixed-width overflow or division.')


def linked_mesh():
    labels = {name: int(address, 16) for address, name in re.findall(
        r'(?m)^al ([0-9a-f]+) \.([^\s]+)$',
        (ROOT / 'build/research/3dvibe64-native/symbols-01/3Dvibe64.labels').read_text())}
    raw = (ROOT / 'build/research/3dvibe64-native/build-01/products/3Dvibe64.prg').read_bytes()
    start = int.from_bytes(raw[:2], 'little')
    memory = bytearray(65536)
    memory[start:start + len(raw) - 2] = raw[2:]
    def table(name, size):
        return list(memory[labels[name]:labels[name] + size])
    triangles = [list(values) for values in zip(*(table('face' + str(i), 8) for i in range(3)))]
    assert table('face_vertex_count', 8) == [3] * 8
    coords = [table(c + 'coord', 3) for c in 'xyz']
    indices = [table('vert_' + c + 'i', 6) for c in 'xyz']
    original = [tuple(signed(coords[axis][indices[axis][i]], 8) for axis in range(3)) for i in range(6)]
    assert set(original) == {(28, 0, 0), (-28, 0, 0), (0, 28, 0), (0, -28, 0), (0, 0, 28), (0, 0, -28)}
    # Outward winding follows from local plane side, not captured image fits.
    # The object origin is strictly inside every linked triangle plane.
    winding = [plane(original, triangle) for triangle in triangles]
    assert all(face['signed_eye_side'] < 0 and not face['degenerate'] for face in winding)
    return triangles, dict(original_vertices=original, linked_triangles=triangles,
        original_origin_strictly_inside_all_outward_planes=True, original_planes=winding,
        original_algebra_controls=algebra_controls(original, triangles),
        mathematical_rule='N=(P1-P0)x(P2-P0); S=N dot (E-P0); keep strictly S>0; E=(0,0,0).',
        zero_policy='S=0 is tangent or degenerate and is excluded, without an empirical tolerance.')


def captured_points(ram):
    return [(signed(ram[0x8036 + i], 8), signed(ram[0x803c + i], 8),
             signed(ram[0x802a + i] + 256 * ram[0x8030 + i], 16)) for i in range(6)]


def native_wire():
    """Use the frozen raw-wire auditor with only its loader metadata adapted."""
    wire = load('camera_native_wire', 'research/verify_vice_live.py')
    wire.BASE, wire.CASE_PINS = BASE, {'native-01': CASE_SHA}
    text = (ROOT / 'research/verify_vice_live.py').read_text()
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == 'audit_session')
    original = ast.get_source_segment(text, node) + '\n'
    old = 'assert session["startup_mode"] == "manual monitor load" and "-autostart" not in session["command"]'
    new = ('assert session["startup_mode"] == "autostart"\n'
           '    assert session["command"].count("-autostart") == 1\n'
           f'    assert session["command"][session["command"].index("-autostart") + 1] == {str(PROGRAM)!r}')
    assert original.count(old) == 1
    adapted = original.replace(old, new)
    exec(compile(adapted, '<camera-autostart-metadata-only>', 'exec'), wire.__dict__)
    case = wire.audit_session('native-01')
    assert not case['partial'] and not case['cancelled'] and not case['waits']
    launch = case['session']['command']
    assert case['session']['program'] == str(PROGRAM)
    assert launch[launch.index('-autostartprgmode') + 1] == '1'
    assert '-pal' in launch and launch[launch.index('-speed') + 1] == '100'
    assert '+warp' in launch and '+autostart-warp' in launch
    pin = json.loads((BASE / 'native-01-pin.json').read_text())
    items = [dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
             for p in sorted(CASE.iterdir()) if p.is_file()]
    assert pin['entries'] == items and len(items) == 81
    assert pin['case_sha256'] == CASE_SHA == sha(json.dumps(items, sort_keys=True, separators=(',', ':')).encode())
    return wire, case, dict(original_function_sha256=sha(original.encode()),
        adapted_function_sha256=sha(adapted.encode()), replaced_assertion=old, replacement=new,
        scope='Only exact generated-PRG autostart metadata is adapted; all wire/custody/closure checks remain frozen.')


def natural_stop(response, expected_pc, expected_id, following):
    raw = response['response'].replace('\r\n', '\n')
    beam = re.findall(r'(?m)^#(\d+) \(Stop on\s+exec ([0-9a-f]{4})\)\s+(\d+)/\$([0-9a-f]+),\s+(\d+)/\$([0-9a-f]+)', raw)
    assert len(beam) == 1 and response['command'] == 'x' and response['status'] == 'completed'
    checkpoint, pc, line, line_hex, cycle, cycle_hex = beam[0]
    assert int(checkpoint) == expected_id and int(pc, 16) == expected_pc
    assert int(line) == int(line_hex, 16) and int(cycle) == int(cycle_hex, 16)
    cpu = re.findall(r'(?m)^\.C:' + pc + r'\s+[^\n]*?- A:([0-9a-f]{2}) X:([0-9a-f]{2}) Y:([0-9a-f]{2}) '
                     r'SP:([0-9a-f]{2}) ([NV\-BDIZC.]{8})\s+(\d+)\s*$', raw, re.I)
    assert len(cpu) == 1
    a, x, y, sp, flags, clock = cpu[0]
    expected = dict(pc=expected_pc, a=int(a, 16), x=int(x, 16), y=int(y, 16), sp=int(sp, 16),
        flags=sum(128 >> i for i, flag in enumerate(flags) if flag != '.'), clock=int(clock),
        line=int(line), cycle=int(cycle))
    assert all(following[key] == value for key, value in expected.items())
    return dict(sequence=response['sequence'], checkpoint=expected_id, actual_stop=expected,
                stop_equals_following_explicit_registers=True)


def native_commands(wire, case):
    rows = [row for _, row in sorted(case['responses'].items())]
    assert [row['sequence'] for row in rows] == list(range(1, 269))
    contexts, last = {}, None
    for index, row in enumerate(rows):
        command, response = row['command'], row['response']
        assert row['status'] == 'completed' and not re.search(r'ERROR --|Syntax error|Unknown resource|[Mm]onitor observation failed', response)
        allowed = command in ('r', 'sidefx off', 'bank ram', 'x', 'trace exec a000',
            'command 1 "' + DUMPS + '"', 'resourceget "Speed"', 'resourceget "InitialWarpMode"')
        allowed |= bool(re.fullmatch(r'break (?:080d|1153|1441|08d4)', command))
        allowed |= bool(re.fullmatch(r'delete \d+', command))
        if command == 'r':
            last = wire.registers(response)
        if command == 'x':
            last = None
        match = re.fullmatch(r'(bsave|dump) "([^"\n]+)"( 0 0000 ffff)?', command)
        if match:
            kind, filename, suffix = match.groups()
            path = Path(filename)
            assert path.parent == CASE and last is not None and rows[index - 1]['command'] == 'r'
            assert (kind == 'bsave') == (suffix is not None) and path.name not in contexts
            contexts[path.name] = dict(registers=last, sequence=row['sequence'])
            allowed = True
        assert allowed, command
    assert len(contexts) == 74
    for sequences, command, value in [((3, 266), 'resourceget "Speed"', 'Speed=100'),
                                       ((4, 267), 'resourceget "InitialWarpMode"', 'InitialWarpMode=0')]:
        assert [r['sequence'] for r in rows if r['command'] == command] == list(sequences)
        assert all(case['responses'][n]['response'].split('(C:')[0].strip() == value for n in sequences)
    assert case['responses'][13]['command'] == 'trace exec a000'
    assert case['responses'][14]['command'] == 'command 1 "' + DUMPS + '"'
    return contexts, dict(ordinary_commands=268, capture_file_commands=74, errors=[], interrupted_resumes=[],
        waits=[], restores=[], later_manual_CPU_RAM_register_patches=[],
        Speed_query_sequences=[3, 266], InitialWarpMode_query_sequences=[4, 267],
        runtime_warp_query=False, InitialWarpMode_scope='Startup resource, not proof of current runtime warp.',
        startup='Declared generated-PRG autostart mode1 loader injection; original disk boot is not claimed.')


def native_captures(reader, contexts):
    captures = {}
    for path in sorted(CASE.glob('*.vsf')):
        ram_path = path.with_suffix('.bin')
        registers = contexts[path.name]['registers']
        assert registers == contexts[ram_path.name]['registers']
        ram, memory = ram_path.read_bytes(), reader.module_payload(path, 'C64MEM')
        assert len(ram) == 65536 and memory[4:65540] == ram
        assert (memory[1], memory[0]) == (registers['port00'], registers['port01'])
        cpu = reader.module_payload(path, 'MAINCPU')
        actual = dict(clock=int.from_bytes(cpu[:8], 'little'), a=cpu[8], x=cpu[9], y=cpu[10], sp=cpu[11],
                      pc=int.from_bytes(cpu[12:14], 'little'), flags=cpu[14])
        assert all(registers[key] == value for key, value in actual.items())
        state = reader.read_snapshot(path)
        assert (state['vicii']['raster_line'], state['vicii']['raster_cycle']) == (registers['line'], registers['cycle'])
        captures[path.stem] = dict(ram=ram, state=state, entry=dict(stem=path.stem,
            ram=artifact(ram_path), snapshot=artifact(path), registers=registers,
            RAM_CPU_ports_clock_beam_pair_equal=True,
            file_command_sequences=[contexts[ram_path.name]['sequence'], contexts[path.name]['sequence']]))
    assert len(captures) == 37
    program = PROGRAM.read_bytes()
    assert captures['start']['entry']['registers']['pc'] == 0x080d
    assert captures['start']['ram'][0x0801:0x0801 + len(program) - 2] == program[2:]
    return captures


def new_samples(directory, omit, reference, reader):
    wire, case, adapter = native_wire()
    contexts, audit = native_commands(wire, case)
    captures = native_captures(reader, contexts)
    layout = load('camera_trace_layout', 'research/anomaly/scanout.py')
    parser = load('camera_frozen_span_parser', 'research/3dvibe64-profile/check_pixels.py')
    guide = json.loads((BASE / 'capture-records.json').read_text())
    plan = json.loads((ROOT / 'research/3dvibe64-camera/capture-plan.json').read_text())
    assert guide['pose_count'] == plan['pose_count'] == 12 and len(guide['records']) == 36
    assert plan['span_trace'] == dict(pc='a000', command=DUMPS)
    natural = [natural_stop(case['responses'][7], 0x080d, 1, captures['start']['entry']['registers'])]
    samples = []
    for pose in range(1, 13):
        name = f'pose-{pose:02}'
        parts = {stage: captures[name + '-' + stage] for stage in ('shades', 'geometry', 'complete')}
        for stage_index, (stage, pc) in enumerate([('shades', 0x1153), ('geometry', 0x1441), ('complete', 0x08d4)]):
            record = guide['records'][(pose - 1) * 3 + stage_index]
            sequence, checkpoint = 16 + 21 * (pose - 1) + 7 * stage_index, 2 + 3 * (pose - 1) + stage_index
            assert record == dict(pose=pose, stage=stage, pc=f'{pc:04x}', break_id=checkpoint, resume_sequence=sequence)
            setup = case['responses'][sequence - 1]
            assert setup['command'] == f'break {pc:04x}'
            assert re.search(rf'BREAK: {checkpoint}  C:\${pc:04x}  \(Stop on exec\)', setup['response'])
            assert contexts[name + '-' + stage + '.bin']['sequence'] == sequence + 2
            assert contexts[name + '-' + stage + '.vsf']['sequence'] == sequence + 4
            natural.append(natural_stop(case['responses'][sequence], pc, checkpoint, parts[stage]['entry']['registers']))
        before, geometry, complete = [parts[stage] for stage in ('shades', 'geometry', 'complete')]
        assert before['entry']['registers']['clock'] < geometry['entry']['registers']['clock'] < complete['entry']['registers']['clock']
        assert geometry['ram'][0x8042:0x8048] == bytes(6)
        assert captured_points(geometry['ram']) == captured_points(complete['ram'])
        assert before['ram'][11] == geometry['ram'][11] == complete['ram'][11] == (pose & 1)
        sequence = 30 + 21 * (pose - 1)
        spans = parser.spans_from_raw(case, reference, layout, sequence, before, complete)
        assert all(span['clock'] > geometry['entry']['registers']['clock'] for span in spans)
        name_spans = name + '-spans.json'
        omit.output_json(directory, name_spans, spans)
        # Output-independent in-proof reference: the generated span artifact is
        # an output-local filename, not an absolute --output-dependent path.
        samples.append(dict(name=name, baseline=before['entry'], completed=complete['entry'],
            geometry=geometry['entry'], spans=spans, spans_output=name_spans,
            geometry_fresh_before_projection=True, geometry_points_unchanged_to_completion=True))
    span_sequences = {30 + 21 * i for i in range(12)}
    for sequence, response in case['responses'].items():
        if sequence not in span_sequences:
            assert not layout.TRACE.search(response['response']), sequence
    return samples, dict(case_sha256=CASE_SHA, wire=wire.summary(case), startup_adapter=adapter,
        command_audit=audit, capture_pairs=[capture['entry'] for capture in captures.values()],
        capture_pairs_count=37, full_RAM_bytes_compared=37 * 65536,
        natural_stops=natural, spans_resume_sequences=sorted(span_sequences),
        generated_PRG_loaded_payload_bytes_exact=len(PROGRAM.read_bytes()) - 2,
        fresh_geometry_points_unchanged_through_completion_for_all_12=True,
        projdone_zero_at_all_12_geometry_stops=True)


def inspect_frame(directory, omit, reference, reader, sample, triangles, dataset):
    name = dataset + '-' + sample['name']
    before = omit.load_capture(reader, sample['baseline'])
    complete = omit.load_capture(reader, sample['completed'])
    if isinstance(sample['spans'], dict):
        spans = json.loads(omit.checked(sample['spans']))
        span_reference = sample['spans']
    else:
        spans = sample['spans']
        raw = (directory / sample['spans_output']).read_bytes()
        span_reference = dict(file=sample['spans_output'], bytes=len(raw), sha256=sha(raw))
    groups = omit.group_spans(name, spans)
    points = captured_points(complete['ram'])
    face_planes = [dict(face_id=i, **plane(points, triangle)) for i, triangle in enumerate(triangles)]
    center_sum = tuple(sum(p[axis] for p in points) for axis in range(3))
    for face in face_planes:
        face['six_times_center_plane_side'] = dot(face['normal'], minus(center_sum, tuple(6 * x for x in face['anchor'])))
        face['nonface_vertex_plane_sides'] = [dict(vertex=i, signed_plane_side=dot(face['normal'], minus(p, face['anchor'])))
            for i, p in enumerate(points) if i not in face['vertices']]
        face['outward_convex_supporting_plane'] = (face['six_times_center_plane_side'] < 0 and
            all(point['signed_plane_side'] < 0 for point in face['nonface_vertex_plane_sides']))
        indices = face['vertices']
        projected = all(complete['ram'][0x8042 + i] == 1 for i in indices)
        face['all_three_projected'] = projected
        if projected:
            xy = [(complete['ram'][0x8000 + i], complete['ram'][0x800c + i] + 256 * complete['ram'][0x8012 + i]) for i in indices]
            (x0, y0), (x1, y1), (x2, y2) = xy
            face['captured_projected_sx_syQ2'] = xy
            face['captured_projected_area_Q2'] = (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)
    front = {face['face_id'] for face in face_planes if face['front_facing']}
    selected = [span for span in spans if span['observed_face_id_latch'] in front]
    assert [s['index'] for s in selected] == sorted(s['index'] for s in selected)
    full = reference.scalar(before, spans)
    assert full['bitmap'] == complete['ram'][full['base']:full['base'] + 8000]
    assert full['attributes'] == complete['ram'][full['screen']:full['screen'] + 1024]
    assert full['color_ram'] == bytearray(complete['state']['vicii']['color_ram'])
    background = complete['state']['vicii']['regs'][0x21] & 15
    full_image = omit.display_indices(full, background)
    model = reference.scalar(before, selected)
    image = omit.display_indices(model, background)
    comparison = omit.compare_model(model, full, image, full_image, background)
    outputs = [omit.output_file(directory, name + '-selected-bitmap.bin', model['bitmap']),
               omit.output_file(directory, name + '-selected-screen.bin', model['attributes']),
               omit.output_file(directory, name + '-selected-color-RAM.bin', model['color_ram']),
               omit.output_file(directory, name + '-selected-display-indices.bin', image),
               omit.output_file(directory, name + '-full.png', omit.png_indices(full_image)),
               omit.output_file(directory, name + '-selected.png', omit.png_indices(image))]
    if not comparison['decoded_display_equal']:
        difference = bytes(2 if a != b else 0 for a, b in zip(image, full_image))
        outputs.append(omit.output_file(directory, name + '-difference.png', omit.png_indices(difference)))
    # A reversed inequality is a genuine wrong camera-side control, not a new
    # candidate calibrated against the result. Retain failure data as observed.
    reversed_ids = {face['face_id'] for face in face_planes if face['signed_eye_side'] < 0}
    reverse = reference.scalar(before, [s for s in spans if s['observed_face_id_latch'] in reversed_ids])
    reverse_image = omit.display_indices(reverse, background)
    reverse_comparison = omit.compare_model(reverse, full, reverse_image, full_image, background)
    orthographic_ids = {face['face_id'] for face in face_planes if face['normal'][2] < 0}
    return dict(dataset=dataset, frame=sample['name'], points=points, eye=[0, 0, 0], face_planes=face_planes,
        captured_algebra_controls=algebra_controls(points, triangles),
        all_eight_actual_windings_are_strict_outward_supporting_planes=all(f['outward_convex_supporting_plane'] for f in face_planes),
        observed_groups=[omit.public_group(group) for group in groups],
        mathematical_front_ids=sorted(front), front_ids_without_observed_span_group=sorted(front - {g['face_id'] for g in groups}),
        retained_observed_face_order=[g['face_id'] for g in groups if g['face_id'] in front],
        omitted_observed_face_order=[g['face_id'] for g in groups if g['face_id'] not in front],
        full_span_count=len(spans), selected_span_count=len(selected),
        full_input_pixel_writes=sum(s['extent'] + 1 for s in spans),
        selected_input_pixel_writes=sum(s['extent'] + 1 for s in selected),
        full_scalar_equals_native_completed_bitmap_and_palettes=True,
        full_decoded_display_sha256=sha(full_image), selected_comparison=comparison,
        wrong_reversed_side_control=dict(selected_front_ids=sorted(reversed_ids), comparison=reverse_comparison),
        orthographic_diagnostic=dict(normal_z_negative_ids=sorted(orthographic_ids),
            differs_from_camera_plane=orthographic_ids != front,
            interpretation='N.z sign omits the plane anchor term and is not the perspective camera-plane classifier.'),
        fresh_geometry=sample.get('geometry'), span_records=span_reference,
        inputs=[sample['baseline']['ram'], sample['baseline']['snapshot'],
                sample['completed']['ram'], sample['completed']['snapshot']], outputs=outputs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT_ROOT / 'accepted-01')
    args = parser.parse_args()
    directory = args.output.expanduser().resolve()
    directory.relative_to(OUTPUT_ROOT.resolve())
    if directory.exists() and any(directory.iterdir()):
        raise SystemExit('Output must be fresh or empty; choose a new --output directory.')
    for relative, pin in PINS.items():
        assert sha((ROOT / relative).read_bytes()) == pin, relative
    omit = load('camera_frozen_omission_helpers', 'research/3dvibe64-overdraw/omit_groups.py')
    reference = load('camera_frozen_scalar', 'research/3dvibe64-native/pixels.py')
    reader = load('camera_frozen_snapshot', 'research/quondam/snapshot_state.py')
    triangles, geometry = linked_mesh()
    units = json.loads((ROOT / UNITS_PROOF).read_text())
    assert units['pass_'] and units['unit_contract']['eye'] == [0, 0, 0]
    geometry['coordinate_unit_contract'] = units['unit_contract']
    accepted = json.loads((ROOT / OLD_PROOF).read_text())
    assert accepted['pass']
    directory.mkdir(parents=True, exist_ok=True)
    frames = [inspect_frame(directory, omit, reference, reader, sample, triangles, 'old')
              for sample in accepted['accepted_samples']]
    for frame, unit_frame in zip(frames, units['frames']):
        assert frame['frame'] == unit_frame['frame']
        assert [list(point) for point in frame['points']] == unit_frame['camera_vertices']
    samples, native = new_samples(directory, omit, reference, reader)
    frames.extend(inspect_frame(directory, omit, reference, reader, sample, triangles, 'new') for sample in samples)
    assert len(frames) == 15
    counterexamples = [dict(dataset=f['dataset'], frame=f['frame'], comparison=f['selected_comparison'])
                       for f in frames if not f['selected_comparison']['all_memory_equal']]
    reverse_fails = all(f['wrong_reversed_side_control']['comparison']['bitmap_different_bytes'] > 0 and
        f['wrong_reversed_side_control']['comparison']['decoded_display_different_pixels'] > 0 for f in frames)
    assert reverse_fails
    result = dict(producer=artifact(Path(__file__).resolve()),
        pinned_inputs=[artifact(ROOT / path) for path in PINS],
        geometry=geometry, frames=frames, frame_count=len(frames),
        closed_new_native_case=native,
        input_and_full_scalar_integrity_pass=True,
        classifier_all_full_memory_preserved=not counterexamples,
        classifier_all_decoded_images_preserved=all(f['selected_comparison']['decoded_display_equal'] for f in frames),
        all_captured_triangle_windings_are_strict_outward_supporting_planes=all(f['all_eight_actual_windings_are_strict_outward_supporting_planes'] for f in frames),
        reversed_side_negative_control_differs_for_every_frame=reverse_fails,
        counterexamples=counterexamples,
        limitations=['The classifier uses the actual quantized camera-space vertex cloud, not unquantized continuous animation.',
            'Only captured native span groups can be retained or omitted; no absent face span is synthesized.',
            'Source triangle winding fixes the sign independently of captured images. Face IDs only join actual ABI groups to triangle inputs.',
            'No empirical area band, selected IDs, fitted threshold, SDK/product patch, CPU execution or measured speedup is introduced.',
            'Decoded completed images are not new committed VIC or physical-hardware observations; finite image preservation is not a general culling theorem.'])
    omit.output_file(directory, 'classify.checked.py', Path(__file__).read_bytes())
    receipt = omit.output_json(directory, 'camera-proof.json', result)
    print(json.dumps(dict(output=str(directory), receipt=receipt,
        integrity_pass=True, classification_all_memory_preserved=not counterexamples,
        frames=[dict(dataset=f['dataset'], frame=f['frame'], front=f['mathematical_front_ids'],
            retained=f['retained_observed_face_order'],
            bitmap_difference_bytes=f['selected_comparison']['bitmap_different_bytes'],
            display_difference_pixels=f['selected_comparison']['decoded_display_different_pixels']) for f in frames]), indent=2))


if __name__ == '__main__':
    main()
