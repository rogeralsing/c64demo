#!/usr/bin/env python3
"""Passive linked-code profiling anchors; never execute the SDK or C64 code."""
import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / 'build/research/3dvibe64-native'
PINS = {
    'build-01/products/3Dvibe64.asm': '22008b3a92b7896c699543b12f9036704797262aa3558cd9116d8a09c85b796f',
    'build-01/products/3Dvibe64.prg': '69b0d86f79106b2bf9654d85bd631bc68c12f4efd708454a0048560b3c1bfdeb',
    'symbols-01/3Dvibe64.labels': '265a1770fe7a605139f0cdfd9d2983f6ddb314a1cf234a6f3a14d6f3b344e847',
}
DECODER = ROOT / 'research/tower-power/static_loader.py'
DECODER_PIN = '21da904962fa53ab7fa3c72caf0bc5a21fa4eb0a94f2be6155ef06a6994b4ce4'

# A named target, its natural call instruction, and post-JSR continuation.
# Branches/tail jumps are followed by static decoding; no JSR is executed.
CALLS = [
    ('update_light_intensity', 0x08cb, 0x08ce),
    ('clear_dirty', 0x08ce, 0x08d1),
    ('render_scene_objects', 0x08d1, 0x08d4),
    ('begin_depth_buckets', 0x142b, 0x142e),
    ('set_active_object', 0x1432, 0x1435),
    ('prepare_angles', 0x1435, 0x1438),
    ('prepare_object_light_for_shade', 0x1438, 0x143b),
    ('gouraud_update_object_shades', 0x143b, 0x143e),
    ('rotate_project_vertices', 0x143e, 0x1441),
    ('collect_active_mesh_faces', 0x1441, 0x1444),
    ('draw_depth_buckets', 0x144c, 0x144f),
    ('gouraud_load_face_raw_shades_y', 0x401d, 0x4020),
    ('load_face_y', 0x4020, 0x4023),
    ('load_face_material', 0x4027, 0x402a),
    ('gouraud_apply_face_reflectivity', 0x402a, 0x402d),
    ('draw_loaded_face_gouraud', 0x402d, 0x4030),
    ('build_loaded_face_bounds', 0x9223, 0x9226),
    ('gouraud_build_edge_shades', 0x922b, 0x922e),
    ('apply_material_span_a', 0x94b9, 0x94bc),
    ('apply_material_span_b', 0x94d5, 0x94d8),
    ('gouraud_draw_scan_span_bytes', 0x957a, 0x957d),
    ('project_vertex', 0x42f3, 0x42f6),
    ('project_vertex', 0x42fb, 0x42fe),
    ('project_vertex', 0x4303, 0x4306),
    ('project_vertex', 0x4314, 0x4317),
]
EXTRA_ENTRIES = ['gouraud_fill_bounds', 'build_loaded_face_bounds_xyq2']
BUCKETS = {
    'clear': ['clear_dirty'],
    'lighting': ['update_light_intensity', 'prepare_object_light_for_shade',
                 'gouraud_update_object_shades', 'gouraud_load_face_raw_shades_y',
                 'gouraud_apply_face_reflectivity'],
    'rotation_and_projection': ['prepare_angles', 'rotate_project_vertices', 'project_vertex'],
    'geometry_and_shade_edges': ['build_loaded_face_bounds', 'gouraud_build_edge_shades'],
    'span_drawing': ['gouraud_draw_scan_span_bytes'],
    'material': ['load_face_material', 'apply_material_span_a', 'apply_material_span_b'],
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=ROOT / 'build/research/3dvibe64-profile/source-analysis')
    parser.add_argument('--native-plan', type=Path,
                        default=ROOT / 'research/3dvibe64-profile/native-plan.json')
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.native_plan = args.native_plan.resolve()
    inputs = []
    data = {}
    for rel, pin in PINS.items():
        path = BUILD / rel
        raw = path.read_bytes()
        assert sha(raw) == pin, path
        inputs.append(dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=pin))
        data[rel] = raw
    assert sha(DECODER.read_bytes()) == DECODER_PIN
    inputs.append(dict(path=str(DECODER.relative_to(ROOT)), bytes=DECODER.stat().st_size,
                       sha256=DECODER_PIN))
    spec = importlib.util.spec_from_file_location('profile_static_decode', DECODER)
    decoder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(decoder)
    labels = {n: int(v, 16) for v, n in re.findall(
        r'(?m)^al ([0-9a-f]+) \.([^\s]+)$', data['symbols-01/3Dvibe64.labels'].decode())}
    assert len(labels) == 968
    asm = data['build-01/products/3Dvibe64.asm'].decode()
    source_lines = asm.splitlines()
    prg = data['build-01/products/3Dvibe64.prg']
    memory = bytearray(65536)
    load = int.from_bytes(prg[:2], 'little')
    end = load + len(prg) - 2
    memory[load:end] = prg[2:]
    assert (load, end) == (0x0801, 0xca2e)

    def at(address, count=8):
        assert load <= address < address + count <= end
        return bytes(memory[address:address+count])

    def flow(entry, stop=None):
        """Intra-procedure CFG, including absolute tail jumps; not a CPU run."""
        pending, decoded = [entry], {}
        while pending:
            pc = pending.pop()
            while pc not in decoded and pc != stop:
                assert load <= pc < end
                insn = decoder.decode(memory, pc)
                decoded[pc] = insn
                if insn['mode'] == 'r':
                    pending.append(insn['target'])
                if insn['mnemonic'] == 'JMP':
                    assert insn['target'] is not None, ('indirect control flow', hex(pc))
                    pending.append(insn['target'])
                    break
                if insn['mnemonic'] in ('RTS', 'RTI'):
                    break
                assert insn['mnemonic'] not in ('BRK', 'KIL'), insn
                pc = insn['next']
        return decoded

    frame = flow(labels['render_frame_begin'], labels['render_frame_end'])
    reachable, pending, callsites = {}, [labels['render_scene_objects'],
                                        labels['clear_dirty'], labels['update_light_intensity']], {}
    while pending:
        entry = pending.pop()
        if entry in reachable:
            continue
        decoded = flow(entry)
        reachable[entry] = decoded
        for insn in decoded.values():
            if insn['mnemonic'] == 'JSR':
                callsites[insn['address']] = insn
                pending.append(insn['target'])
    for insn in frame.values():
        if insn['mnemonic'] == 'JSR':
            callsites[insn['address']] = insn

    expected = []
    for name, pc, continuation in CALLS:
        insn = callsites[pc]
        target = labels[name]
        assert insn['mnemonic'] == 'JSR' and insn['target'] == target
        assert insn['next'] == continuation
        assert at(pc, 3) == b'\x20' + target.to_bytes(2, 'little')
        expected.append(dict(name=name, entry=target, call_pc=pc, continuation=continuation,
                             stacked_return_word=continuation-1, bytes=at(pc, 3).hex()))
    selected = list(dict.fromkeys([name for name, _, _ in CALLS] + EXTRA_ENTRIES))
    functions = []
    for name in selected:
        entry = labels[name]
        decoded = flow(entry)
        incoming = sorted((i for i in callsites.values() if i['target'] == entry),
                          key=lambda i: i['address'])
        line = next(i+1 for i, text in enumerate(source_lines) if text == name + ':')
        functions.append(dict(name=name, entry=entry, initial_entry_bytes=at(entry).hex(),
                              assembly_line=line,
                              direct_call_sites=[dict(pc=i['address'], continuation=i['next'],
                                                      bytes=i['bytes']) for i in incoming],
                              rts_sites=sorted(pc for pc, i in decoded.items() if i['mnemonic'] == 'RTS'),
                              reachable_instruction_count=len(decoded)))

    def guard(pc, hexbytes):
        raw = bytes.fromhex(hexbytes)
        assert at(pc, len(raw)) == raw, hex(pc)
        return dict(pc=pc, initial_bytes=raw.hex())

    guards = [
        guard(0x95dd, '4c e0 95 4c 96 ac'),
        guard(0x9223, '20 dd 95 ad 6d ac f0 06 20 32 92 4c 55 94 60'),
        guard(0xa000, 'ad 40 b4 c9 07 90 2e'),
        guard(0xa030, 'd0 03 4c 43 a1 20 8b 95'),
        guard(0xa053, 'b9 26 b5 29 c0'),
        guard(0xa0df, 'a9 00 85 41 a9 ff 85 2d'),
        guard(0xa142, '60 20 8b 95'),
        guard(0xa1a2, 'ad 3c b4 8d 3b b4 ad dd a1 8d 41 b4 60'),
        guard(0xb3fa, '78 4c fb b3'),
    ]
    assert labels['xyq2_walker_fault'] == 0xb3fa
    assert labels['xyq2_final_fault_halt'] == 0xb3fb
    assert labels['gfb_done'] == 0x958a
    assert all(memory[pc] == 0x60 for f in functions for pc in f['rts_sites'])
    # No JSR occurs in this named routine: projection is lazy in load_face_visible.
    assert not any(i['mnemonic'] == 'JSR' for i in flow(labels['rotate_project_vertices']).values())
    projection_calls = {i['address'] for i in callsites.values() if i['target'] == labels['project_vertex']}
    assert projection_calls == {0x42f3, 0x42fb, 0x4303, 0x4314}
    markers = [
        dict(name='general_route', pc=0xa035, meaning='short span or unequal endpoint Bayer patterns; not necessarily varying output'),
        dict(name='uniform_route', pc=0xa143, meaning='entire span selected for exact constant-pattern bulk fill; tail jump, not a new call'),
        dict(name='general_full_byte', pc=0xa053, meaning='one four-pixel full-byte DDA group; repeats within a span', mutable_operand=[0xa054, 0xa055]),
        dict(name='general_partial_byte', pc=0xa0df, meaning='one masked partial-byte aggregate; repeats within a span'),
    ]
    plan_raw = args.native_plan.read_bytes()
    plan = json.loads(plan_raw)
    assert plan['schema'] == 1 and plan['prg_sha256'] == PINS['build-01/products/3Dvibe64.prg']
    assert plan['program'] == 'build/research/3dvibe64-native/build-01/products/3Dvibe64.prg'
    entries = {f['entry']: f['name'] for f in functions}
    continuations = {row['continuation'] for row in expected} | {0x08cb}
    marker_pcs = {row['pc'] for row in markers}
    ids = [point['id'] for point in plan['points']]
    assert len(ids) == len(set(ids)) == 46
    bound_plan = []
    for point in plan['points']:
        pc = int(point['pc'], 16)
        if point['kind'] == 'entry':
            assert pc in entries
            command = ('m 0100 01ff; m 000b 002f; m b43b b441'
                       if pc == 0xa000 else 'm 0100 01ff')
            assert point['command'] == command
        elif point['kind'] == 'continuation':
            assert pc in continuations and point['command'] is None
        else:
            assert point['kind'] == 'marker' and pc in marker_pcs and point['command'] is None
        bound_plan.append(dict(id=point['id'], kind=point['kind'], name=point['name'], pc=pc))
    report = dict(
        scope='Static linked profiling plan, not measured cycles, CPU execution, native evidence or FPS',
        inputs=inputs,
        frame=dict(begin=0x08cb, end=0x08d4, code=at(0x08cb, 9).hex()),
        selected_calls=expected, functions=functions, code_guards=guards, markers=markers,
        static_recursive_function_entries=len(reachable),
        buckets=BUCKETS,
        tail_entries=[dict(entry=0xac96, enclosing_entry=0x95dd, continuation=0x9226),
                      dict(entry=0x9455, enclosing_entry=0x9223, continuation=0x4030),
                      dict(entry=0xa143, enclosing_entry=0xa000, continuation=0x957d)],
        native_plan=dict(path=str(args.native_plan.relative_to(ROOT)), bytes=len(plan_raw),
                         sha256=sha(plan_raw), points=bound_plan),
        stack_contract=dict(command='m 0100 01ff', span_command='m 0100 01ff; m 000b 002f; m b43b b441',
                            continuation='(stack[(SP+1)&255] | stack[(SP+2)&255]<<8) + 1, modulo65536',
                            returned_sp='entrySP + 2 modulo256',
                            wrap='stack indexes are in page0100 and wrap within that page'),
        method_limits=[
            'Entry to actual continuation includes RTS and intervening VIC stalls; do not add a nominal six cycles.',
            'Entry intervals exclude the initiating JSR. Its execution, IRQs outside child intervals, and parent loop/setup cost remain in the exclusive residual.',
            'Nested intervals overlap. Sum exclusive intervals only; subtract each immediate child once.',
            'Bounds95DD and AC96 are alternate boundaries of one bucket, never two nested chargeable intervals.',
            'A143 is a tail route of A000. Count/classify its parent span; do not push another stack frame.',
            'All four project_vertex callers are inside lazy visibility collection; the fourth is a compiled quad path, not proof of execution in this triangle scene.',
            'Monitored machine clocks are elapsed PAL cycles including VIC/IRQ time, not retired6510cycle totals or wall-time FPS.',
            'A complete second-render-onward case is required to profile dirty clearing; the first cleared bitmap is initially clean.',
            'Markers are alternatives/group counts, not instruction-complete gradient cost measurements.',
            'This source comment promises fault stack restoration, but actual linked final fault code is SEI/self-JMP; a fault terminates progress and cannot return normally.',
        ],
    )
    args.output.mkdir(parents=True, exist_ok=False)
    output = args.output / 'anchors.json'
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(pass_=True, output=str(output.relative_to(ROOT)), bytes=output.stat().st_size,
                          sha256=sha(output.read_bytes()), functions=len(functions),
                          selected_call_sites=len(expected)), sort_keys=True))


if __name__ == '__main__':
    main()
