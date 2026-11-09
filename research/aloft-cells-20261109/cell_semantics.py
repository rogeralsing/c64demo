#!/usr/bin/env python3
"""Finite source-cell algebra, not a CPU, raster scheduler or native replay."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEN = 'build/research/aloft-cells-20261109/cell-analysis/accepted-02'
CTX = 'build/research/aloft-cells-20261109/context-analysis/accepted-01'
PRIMARY = 'research/aloft-cells-20261109/primary_reading.py'
PINS = {
    GEN + '/cell-generator-proof.json': '480428221ed84aed404dde3dfd8fcf9c378aab39f4e00390bfbe9d77aa399e4c',
    CTX + '/context-proof.json': '3610d8f46d722667f8d25f4f8976b363afc2c3c632c450f39d8d88d751d7e95e',
    PRIMARY: '4c8b3e1ae3968fff3bc90af9527fda0a6489c6853ba68f32bf17f4a1c4e74dda',
    'build/research/aloft-cells-20261109/primary-analysis/accepted-01/primary-reading-proof.json':
        '4fd7cedb1ce4325a6adc0c406406f4a2f6a2cc65ccb7c8ef735d21c02344ed04',
    'build/research/aloft-cells-20261109/primary-analysis/retained-vice-01/6510core.c':
        'd3e33633a64f4761d4073cd1744172dfcc3148c6a780cabad5759f381631f68f',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_pin(path, digest):
    raw = (ROOT / path).read_bytes()
    assert sha(raw) == digest, path
    return raw, {'path': path, 'bytes': len(raw), 'sha256': digest}


def receipt_output(folder, proof, name):
    ref = next(x for x in proof['outputs'] if x['name'] == name)
    raw, meta = read_pin(folder + '/' + name, ref['sha256'])
    assert len(raw) == ref['bytes']
    return raw, meta


def recognize(row):
    """Accept exactly the two fixed templates and their admitted patch sites."""
    b = bytes.fromhex(row['final_code_hex'])
    role, variant = row['role'], row['variant']
    assert len(b) == row['bytes'] == (35 if role == 'normal' else 37)
    assert role in ('normal', 'row-end') and variant in ('A', 'B')
    fixed = {0: 0xa5, 2: 0x09, 4: 0x29, 6: 0xaa, 7: 0xa5,
             9: 0x09, 11: 0x29, 13: 0xa8, 15: 0, 16: 4,
             21: 0, 22: 4, 25: 0x86, 27: 0x84}
    for offset, value in fixed.items():
        assert b[offset] == value, (row['pc'], offset)
    assert b[14] == (0xbd if variant == 'A' else 0xb9)
    assert b[20] == (0xb9 if variant == 'A' else 0xbd)
    assert b[26] == b[1] and b[28] == b[8]
    assert b[1] >= 2 and b[8] >= 2 and b[24] >= 2
    assert (b[17], b[23]) in ((0x8d, 0x85), (0x0c, 0x04))
    suppressed = b[17] == 0x0c
    assert suppressed == row['boundary_patch_page']
    assert suppressed == (0x6c <= row['pc'] >> 8 <= 0x6f)
    tail = bytes.fromhex('ee11d0c10060' if role == 'normal' else 'a9188d11d0c10060')
    assert b[29:] == tail
    return {
        'pc': row['pc'], 'role': role, 'variant': variant,
        'source_generated_bytes': b.hex(), 'zp_x': b[1], 'zp_y': b[8],
        'or_x': b[3], 'and_x': b[5], 'or_y': b[10], 'and_y': b[12],
        'first_lookup': 'X' if variant == 'A' else 'Y',
        'second_lookup': 'Y' if variant == 'A' else 'X',
        'screen_address': int.from_bytes(b[18:20], 'little'),
        'scratch_zp': b[24], 'lookup_writes_suppressed': suppressed,
        'd011': 'read/dummy/final INC' if role == 'normal' else 'literal STA18',
        'cmp_PC': row['pc'] + len(b) - 3,
        'CMP_value_and_final_CNZ_are_unbound': True,
    }


def reverse8(value):
    return int(f'{value:08b}'[::-1], 2)


def cell_data(desc, zp, lookup, d011_low7, primary):
    """Evaluate one admitted cell macro with explicit ordered effects.

    The dictionary is CPU-view ZP, not underlying RAM at port00/01. None is
    permitted only for an unbound device-port read. No CMP target byte is read:
    its address/dependency is retained, with flags and physical effects unknown.
    Unbound raster-MSB produces alternatives, never an invented beam sample.
    """
    zx, zy = desc['zp_x'], desc['zp_y']
    before = (zp[zx], zp[zy])
    assert all(isinstance(v, int) and 0 <= v <= 255 for v in before)
    x = (before[0] | desc['or_x']) & desc['and_x']
    y = (before[1] | desc['or_y']) & desc['and_y']
    indices = {'X': x, 'Y': y}
    first = lookup[indices[desc['first_lookup']]]
    second = lookup[indices[desc['second_lookup']]]
    events = [
        {'kind': 'read_ZP', 'pc': desc['pc'], 'address': zx, 'value': before[0]},
        {'kind': 'read_ZP', 'pc': desc['pc'] + 7, 'address': zy, 'value': before[1]},
        {'kind': 'read_lookup', 'pc': desc['pc'] + 14,
         'address': 0x400 + indices[desc['first_lookup']], 'value': first},
    ]

    def write(address, value, pc, kind):
        events.append({'kind': kind, 'pc': pc, 'address': address, 'value': value})
        if address < 256:
            assert address >= 2, 'device-port writes are outside this finite contract'
            zp[address] = value

    if desc['lookup_writes_suppressed']:
        events.append({'kind': 'NOP_absolute_read_unmodeled', 'pc': desc['pc'] + 17,
                       'address': desc['screen_address']})
    else:
        write(desc['screen_address'], first, desc['pc'] + 17, 'write_screen')
    events.append({'kind': 'read_lookup', 'pc': desc['pc'] + 20,
                   'address': 0x400 + indices[desc['second_lookup']], 'value': second})
    if desc['lookup_writes_suppressed']:
        events.append({'kind': 'NOP_ZP_operand_slot_physical_read_unmodeled',
                       'pc': desc['pc'] + 23, 'operand_address': desc['scratch_zp'],
                       'VICE_dispatch_has_no_explicit_target_LOAD': True})
    else:
        write(desc['scratch_zp'], second, desc['pc'] + 23, 'write_scratch')
    write(zx, x, desc['pc'] + 25, 'write_state_X')
    write(zy, y, desc['pc'] + 27, 'write_state_Y')
    if desc['role'] == 'normal':
        choices = [primary.d011_inc_read(d011_low7 | high) for high in (0, 128)]
        low_after = choices[0]['final_write'] & 127
        assert all(c['final_write'] & 127 == low_after for c in choices)
        events.append({'kind': 'D011_RMW_alternatives_unbound_raster_MSB',
                       'pc': desc['pc'] + 29, 'choices': choices})
        final_a = second
    else:
        low_after, final_a = 0x18, 0x18
        events.append({'kind': 'D011_literal_store', 'pc': desc['pc'] + 31,
                       'address': 0xd011, 'value': 0x18})
    lo, hi = zp[x], zp[(x + 1) & 255]
    cmp_address = None if lo is None or hi is None else lo | (hi << 8)
    events.append({'kind': 'CMP_indirect_X_unmodeled_value', 'pc': desc['cmp_PC'],
                   'dummy_ZP_read_address': 0, 'dummy_CPU_view_value': zp[0],
                   'pointer_ZP': [x, (x + 1) & 255], 'pointer_bytes': [lo, hi],
                   'address': cmp_address, 'unbound_flags': ['C', 'N', 'Z'],
                   'physical_read_side_effects_not_replayed': True})
    return {'pc': desc['pc'], 'incoming_state_bytes': list(before), 'X': x, 'Y': y,
            'A_at_return': final_a, 'd011_low7_after': low_after, 'events': events}


def produce(out):
    out.mkdir(parents=True, exist_ok=False)
    inputs, pinned, retained = [], {}, {}
    for path, digest in PINS.items():
        raw, ref = read_pin(path, digest)
        inputs.append(ref)
        retained[path] = raw
        if path.endswith('.json'):
            pinned[path] = json.loads(raw)
    gen, ctx = pinned[GEN + '/cell-generator-proof.json'], pinned[CTX + '/context-proof.json']
    assert gen['pass_'] and gen['prediction_written_before_native_oracles']
    assert ctx['pass_'] and ctx['scope'].startswith('Three retained native entry-state')
    raw, ref = receipt_output(GEN, gen, 'cell-layout.json'); inputs.append(ref)
    layout = json.loads(raw)
    descriptors = [recognize(row) for row in layout['cells']]
    assert len(descriptors) == 312 and len({d['pc'] for d in descriptors}) == 312
    by_pc = {d['pc']: d for d in descriptors}
    raw, ref = receipt_output(CTX, ctx, 'declared-entry-inputs.json'); inputs.append(ref)
    declared = json.loads(raw)
    assert declared['no_native_2000_or2023_cell_body_bytes_are_exposed_as_prediction_inputs']
    raw, ref = receipt_output(CTX, ctx, 'machine-context.json'); inputs.append(ref)
    contexts = json.loads(raw)
    source_ref = next(r for r in gen['source_contract']['state_files'] if r['path'].endswith('memory.bin'))
    source, ref = read_pin(source_ref['path'], source_ref['sha256']); inputs.append(ref)
    assert source[0xf676:0xf686].hex() == 'a2008aa0074a3e00048810f9e8d0f360'
    assert source[0xf080:0xf090].hex() == 'c6008d2bf1a91e38ed06dc8d8ff01000'
    assert source[0xf09d:0xf0b1].hex() == '8e29f18c27f1a9188d11d0486848684868200005'
    spec = importlib.util.spec_from_file_location('pinned_primary_cell_rules', ROOT / PRIMARY)
    primary = importlib.util.module_from_spec(spec); spec.loader.exec_module(primary)
    core_path = 'build/research/aloft-cells-20261109/primary-analysis/retained-vice-01/6510core.c'
    core = retained[core_path].decode().splitlines()
    anchors = []
    for first, last, fragments in [
        (583, 588, ['LOAD_ZERO_DUMMY(addr)', '(addr + reg_x_read) & 0xff', 'LOAD(tmpa)']),
        (1067, 1076, ['tmp = reg_a_read - (value)', 'LOCAL_SET_CARRY', 'LOCAL_SET_NZ']),
        (1447, 1456, ['#define NOOP(', '#define NOOP_ABS()', 'LOAD(p2)']),
        (2507, 2511, ['case 0x04:', 'NOOP(1, 2)']),
        (2549, 2551, ['case 0x0c:', 'NOOP_ABS()']),
        (3244, 3246, ['case 0xc1:', 'CMP(LOAD_IND_X(p1), 1, 2)']),
    ]:
        text = '\n'.join(core[first - 1:last])
        assert all(fragment in text for fragment in fragments)
        anchors.append({'first_line': first, 'last_line': last, 'text': text,
                        'sha256_UTF8_no_trailing_newline': sha(text.encode())})

    # Independent initializer proof: eight inserted bits discard any old byte.
    for index in range(256):
        for old in range(256):
            shifted = old
            for k in range(8):
                shifted = ((shifted << 1) | ((index >> k) & 1)) & 255
            assert shifted == reverse8(index)
    derived_lookup = [reverse8(i) for i in range(256)]
    for read in range(256):
        assert primary.d011_inc_read(read) == {
            'read': read, 'dummy_write': read, 'final_write': (read + 1) & 255}
    # Every byte-domain map is idempotent and independent of incoming carry.
    mask_checks = 0
    for desc in descriptors:
        for suffix in ('x', 'y'):
            for value in range(256):
                v = (value | desc['or_' + suffix]) & desc['and_' + suffix]
                assert ((v | desc['or_' + suffix]) & desc['and_' + suffix]) == v
                mask_checks += 1

    chosen = next(r for r in declared['captures'] if r['stem'] == 'part08-frame01')
    context = next(r for r in contexts['captures'] if r['stem'] == chosen['stem'])
    assert chosen['pc'] == context['registers']['pc'] == 0xf080
    assert chosen['CPU_read_ZP_at_same_stop'][:2] == [context['port']['DDR'], context['port']['read']]
    # Actual generation is checked, not silently restored to an old source image.
    prefix_changes = [r for r in context['source_window_changes'] if 0xf080 <= r['address'] < 0xf0b1]
    assert len(prefix_changes) == 1 and prefix_changes[0]['address'] == 0xf08f
    assert prefix_changes[0]['original'] == 0
    assert chosen['actual_RAM_lookup0400'] == derived_lookup
    isolated_boundaries = []
    for desc in descriptors:
        if not desc['lookup_writes_suppressed']:
            continue
        example = cell_data(desc, list(chosen['CPU_read_ZP_at_same_stop']), derived_lookup, 0x18, primary)
        kinds = [event['kind'] for event in example['events']]
        assert not any(k in kinds for k in ('write_screen', 'write_scratch'))
        assert kinds.count('write_state_X') == kinds.count('write_state_Y') == 1
        assert kinds.count('NOP_absolute_read_unmodeled') == 1
        assert kinds.count('NOP_ZP_operand_slot_physical_read_unmodeled') == 1
        isolated_boundaries.append(example)
    zp = list(chosen['CPU_read_ZP_at_same_stop'])
    assert len(zp) == 256
    # Conditional on source prefix reaching F0AE: DEC00 changes DDR; input pins
    # under the changed DDR are unobserved, so port01 is deliberately unknown.
    zp[0] = (zp[0] - 1) & 255
    zp[1] = None
    low, run = 0x18, []
    targets = chosen['actual_call_targets0500']
    assert len(targets) == 200
    for i, target in enumerate(targets):
        assert target['index'] == i and target['call_PC'] == 0x500 + 3 * i
        desc = by_pc[target['target']]
        assert desc['role'] == ('row-end' if i % 8 == 7 else 'normal')
        result = cell_data(desc, zp, derived_lookup, low, primary)
        result['call_index'], result['call_PC'] = i, target['call_PC']
        low = result['d011_low7_after']
        run.append(result)
    assert low == 0x18
    events = [e for r in run for e in r['events']]
    counts = {k: sum(e['kind'] == k for e in events) for k in sorted({e['kind'] for e in events})}
    summary = {
        'stem': chosen['stem'], 'input_clock': chosen['clock'], 'input_PC': chosen['pc'],
        'scope': 'Conditional arithmetic composition of declared200calltargets, not observed cell execution.',
        'source_prefix_assumptions': ['F080 prefix reaches F0AE',
            'DEC00 applied to CPU-view DDR; post-DDR port01 unbound',
            'F0A5 writes D01118 before calls', 'no intervening mutation of declared calltargets/ZP/lookup'],
        'runtime_prefix_changes': prefix_changes, 'calls': 200,
        'unique_declared_call_targets': len({r['target'] for r in targets}),
        'normal_calls': sum(r['call_index'] % 8 != 7 for r in run), 'row_end_calls': 25,
        'event_counts': counts, 'final_CPU_view_ZP_with_unknown_port01': zp,
        'D011_low7_after': low, 'CMP_CNZ_not_predicted': True,
        'native_post_cell_oracle_available': False,
    }
    outputs = []

    def emit(name, value):
        raw = (json.dumps(value, indent=2) + '\n').encode()
        (out / name).write_bytes(raw)
        outputs.append({'name': name, 'bytes': len(raw), 'sha256': sha(raw)})

    emit('cell-descriptors.json', {'cells': descriptors})
    emit('conditional-call-effects.json', {'input_stem': chosen['stem'], 'summary': summary, 'cells': run})
    emit('isolated-boundary-examples.json', {
        'scope': 'Eight independent cell evaluations using declared preIRQ ZP as explicit parameters; not observed execution.',
        'cells': isolated_boundaries})
    emit('primary-semantic-source.json', {
        'member': 'vice-3.10/src/6510core.c', 'retained_path': core_path,
        'retained_member_sha256': PINS[core_path], 'anchors': anchors,
        'NOP04_limit': 'This VICE dispatch has no explicit operand-target LOAD; physical target read is not asserted.',
        'generation31_byte_anchors': {
            'F676_lookup_initializer': source[0xf676:0xf686].hex(),
            'F080_prefix': source[0xf080:0xf090].hex(),
            'F09D_through_F0AE_JSR': source[0xf09d:0xf0b1].hex()}})
    emit('finite-domain-proof.json', {
        'bitreverse_initializer_index_oldbyte_cases': 65536,
        'per_cell_per_axis_byte_map_cases': mask_checks,
        'all_admitted_bitwise_maps_idempotent': True,
        'incoming_carry_not_read_by_cell_dataflow': True,
        'normal_D011_actual_read_byte_domain': 256,
        'boundary_suppressed_cells': [d['pc'] for d in descriptors if d['lookup_writes_suppressed']],
        'boundary_absolute_read_and_ZP_operand_slot_retained_without_writes': True,
    })
    raw = Path(__file__).read_bytes(); (out / 'cell_semantics.checked.py').write_bytes(raw)
    outputs.append({'name': 'cell_semantics.checked.py', 'bytes': len(raw), 'sha256': sha(raw)})
    emit('cell-semantics-proof.json', {
        'pass_': True, 'producer': {'path': Path(__file__).relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha(raw)},
        'inputs': inputs, 'source_predicted_descriptors': len(descriptors),
        'source_generated_cell_bytes': sum(len(bytes.fromhex(d['source_generated_bytes'])) for d in descriptors),
        'no_native_generated_cell_or_endpoint_bytes_read': True,
        'declared_runtime_input_summary': summary,
        'no_CPU_native_or_raster_execution': True,
        'limits': ['No cell-return/post0500 native witness exists in this retained case.',
            'CMP and absoluteNOP physical-read effects/flags are not replayed; ZPNOP target-read behavior is not established.',
            'D011 alternatives bind values only, not raster time, DMA, borders or pixels.',
            'Observed calltargets are a declared motion input; their evolution is not predicted.',
            'No complete renderer, animation, cadence or named scene identity is claimed.'],
        'outputs': list(outputs),
    })


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    produce(args.output)
