#!/usr/bin/env python3
"""Typed finite Aloft cell generator; source prediction before native byte oracles.

This recognizes fixed source macros and emits their mathematical result. It is
not a CPU interpreter and does not execute generated cells or C64 instructions.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-cells-20261109/cell-analysis'
COLOR = 'build/research/aloft-decode-20261109/color-analysis/accepted-01/color-stream-proof.json'
COLOR_SHA = '44bbc6a94b22db33d81dc9f15178f1303a2db19fb22484292e0c6f894f00f4b2'
NATIVE = 'build/research/aloft-20261109/native-analysis/accepted-01/native-proof.json'
NATIVE_SHA = '02243d0cbae68edad8aa5a51aec9e22e9cfa4c52f918f1ba30db9e5226b19eb4'
ASSOCIATION = 'build/research/aloft-decode-20261109/effect-analysis/accepted-01/effect-binding-proof.json'
ASSOCIATION_SHA = '882027ffe37e5651ec2c18ea7a3e511824d10f5d15da264c73b855fb6769c5ce'
READER = 'research/quondam/snapshot_state.py'
READER_SHA = 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a'
GUARDS = [
    (0xf000, 0xf02b, 'ecb358dacb400d3b9bd03031d417438736ffdd5ccde670e55f756c7334ca0c0d', 'init call order'),
    (0xf43d, 0xf47c, 'c84b1a042e5ec3895c205bc7a859ff290ebd68a66253a04f84f23bd170d0f513', 'predecessor store footprints and no SED/template mutation'),
    (0xf47c, 0xf55a, '091f6550bb93506a878fb2a300f00e4158cde7eeb1021a1b0e09ef6c1efa16b5', 'paired page emitter and boundary constants'),
    (0xf55a, 0xf626, '39dad338510ac3bad0aa6386b5139b76d84dcdc9eebc2cf231176e31ac35be5a', 'mask and operand update macros'),
    (0xf626, 0xf64e, 'd09e8cecd626860abd71974efd14eddceaab78a8ae0d726bd5274cce8b0d3c31', 'two20-byte operand tables'),
    (0xf64e, 0xf787, 'd1669c08c36c437abea62977935553f1422ce35c500e5577bcec4a1583930b22', 'subsequent generators, lookup and disjoint target bounds'),
    (0xf787, 0xf817, '1a401fef5d6c254e6c702d5aeab97c4cd3dba1fea9c48135aed4b3532d565d5f', 'two72-byte original cell templates'),
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def meta(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha(raw)}


def checked(ref):
    path = (ROOT / ref['path']).resolve()
    path.relative_to(ROOT)
    raw = path.read_bytes()
    assert len(raw) == ref['bytes'] and sha(raw) == ref['sha256'], ref['path']
    return raw


def pin(relative, digest):
    path = ROOT / relative
    raw = path.read_bytes()
    assert sha(raw) == digest, relative
    return json.loads(raw), meta(path)


def json_write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def output_meta(path):
    return {'name': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}


def source_input():
    proof, proof_meta = pin(COLOR, COLOR_SHA)
    assert proof['pass_'] is True and proof['native_values_never_inputs'] is True
    assert proof['all_initial_RAM_and_device_low_bits_unknown'] is True
    row = proof['completed_bundles'][31]
    assert row['bundle'] == 31 and row['packet_at_return'] == 495 and row['saved_LastX'] == 26
    folder = (ROOT / COLOR).parent
    refs = {ref['name'].removeprefix('bundle031-'): {
        'path': (folder / ref['name']).relative_to(ROOT).as_posix(),
        'bytes': ref['bytes'], 'sha256': ref['sha256']} for ref in row['files']}
    data = {name: checked(ref) for name, ref in refs.items()}
    assert sha(data['memory.bin']) == '95a344b261b1b28d229da9778df80bae06eff39470ff4515820ce4e1fa86869e'
    assert all(len(data[name]) == 65536 for name in (
        'memory.bin', 'known-mask.bin', 'cumulative-write-mask.bin', 'delta-write-mask.bin'))
    memory, known, written = (data[name] for name in (
        'memory.bin', 'known-mask.bin', 'cumulative-write-mask.bin'))
    assert set(known) <= {0, 1} and set(written) <= {0, 1}
    guards = []
    for first, end, digest, role in GUARDS:
        assert all(known[first:end]) and all(written[first:end]), ('unknown/nonpayload source', first, end)
        assert sha(memory[first:end]) == digest, (first, end)
        guards.append({'first': first, 'end_exclusive': end, 'bytes': end - first,
            'sha256': digest, 'role': role, 'all_full_bytes_known_and_physical_payload': True})
    return memory, {'receipt': proof_meta, 'generation': 31, 'state_files': list(refs.values()),
        'guards': guards, 'no_native_memory_values_or_device_color_values_used': True}


def constant_store_block(source, first, end):
    """Recognize one fixed LDA#constant + STAabs-list macro, then RTS.

    Only this finite source grammar is admitted; no instruction state machine,
    register execution, branch simulation or arbitrary opcode dispatch exists.
    """
    groups, cursor = [], first
    while cursor < end - 1:
        assert source[cursor] == 0xa9
        literal, literal_pc = source[cursor + 1], cursor
        cursor += 2
        stores = []
        while source[cursor] == 0x8d:
            stores.append({'source_PC': cursor,
                'address': int.from_bytes(source[cursor + 1:cursor + 3], 'little')})
            cursor += 3
        assert stores
        groups.append({'literal_PC': literal_pc, 'value': literal, 'stores': stores})
    assert cursor == end - 1 and source[cursor] == 0x60
    return groups


def predict(source):
    """Generate only source-defined output bytes; everything else stays unknown."""
    assert source[0xf47c:0xf48f] == bytes.fromhex('a9008510a9208511a9008512a9bb851320a8f5')
    assert source[0xf492:0xf498] == bytes.fromhex('a5112904d00e')
    assert source[0xf4b2:0xf4c5] == bytes.fromhex('e611c613a520c9ffd00320b9f5a511c970d0ca')
    assert source[0xf592:0xf5b9] == bytes.fromhex(
        '462066214620662138662266233866226623a520d010a9ff8520a9c08521a9808522a97f852360')
    template = bytearray(source[0xf787:0xf817])
    base = 0xf787
    mask_targets = [
        [0xf78a, 0xf7ad, 0xf7d2, 0xf7f5], [0xf791, 0xf7b4, 0xf7d9, 0xf7fc],
        [0xf78c, 0xf7af, 0xf7d4, 0xf7f7], [0xf793, 0xf7b6, 0xf7db, 0xf7fe]]
    first_zp_targets = [0xf788, 0xf7a1, 0xf7ab, 0xf7c4, 0xf7d0, 0xf7e9, 0xf7f3, 0xf80c]
    second_zp_targets = [0xf78f, 0xf7a3, 0xf7b2, 0xf7c6, 0xf7d7, 0xf7eb, 0xf7fa, 0xf80e]
    scratch_targets = [0xf79f, 0xf7c2, 0xf7e7, 0xf80a]
    screen_low_targets = [0xf799, 0xf7bc, 0xf7e1, 0xf804]
    screen_high_targets = [0xf79a, 0xf7bd, 0xf7e2, 0xf805]
    # The fixed F55A source directly supplies the four destination lists.
    cursor = 0xf55a
    for zp, targets in zip(range(0x20, 0x24), mask_targets):
        assert source[cursor:cursor + 2] == bytes([0xa5, zp])
        cursor += 2
        for target in targets:
            assert source[cursor:cursor + 3] == bytes([0x8d, target & 255, target >> 8])
            cursor += 3
    assert cursor == 0xf592
    reset = tuple(source[pc] for pc in (0xf5a9, 0xf5ad, 0xf5b1, 0xf5b5))
    assert reset == (0xff, 0xc0, 0x80, 0x7f)
    masks = reset
    memory, mask = bytearray(65536), bytearray(65536)
    patches, emits, last_page, mask_phases = [], [], {}, []
    logical_digest = hashlib.sha256()
    logical_count, overwritten, group_counter = 0, 0, source[0xf5f0]
    assert group_counter == 0

    def patch_templates(targets, value, reason, group):
        assert 0 <= value <= 255
        for target in targets:
            assert base <= target < base + len(template)
            template[target - base] = value
        patches.append({'group': group, 'targets': targets, 'value': value, 'reason': reason})

    def store(address, value, source_pc):
        nonlocal logical_count, overwritten
        assert 0 <= address <= 65535 and 0 <= value <= 255
        overwritten += bool(mask[address])
        memory[address], mask[address] = value, 1
        logical_count += 1
        logical_digest.update(address.to_bytes(2, 'little') + bytes([value]) + source_pc.to_bytes(2, 'little'))

    for index in range(80):
        forward, mirror = 0x20 + index, 0xbb - index
        for targets, value in zip(mask_targets, masks):
            patch_templates(targets, value, 'F55A inject before paired-page copy', index // 4)
        before = masks
        if index < 4:
            mask_phases.append(list(before))
        a, b, c, d = masks
        masks = (a >> 2, (b >> 2) | ((a & 3) << 6),
                 (c >> 2) | 0xc0, (d >> 2) | ((c & 3) << 6))
        if masks[0] == 0:
            masks = reset
        variant = 1 if forward & 4 else 0
        code = bytes(template[variant * 72:(variant + 1) * 72])
        forward_pc, mirror_pc = ((0xf4ab, 0xf4ad) if variant else (0xf49d, 0xf49f))
        for y in range(71, -1, -1):
            store((forward << 8) + y, code[y], forward_pc)
            store((mirror << 8) + y, code[y], mirror_pc)
        event = {'iteration': index, 'group': index // 4, 'phase': index % 4,
            'masks_20_21_22_23': list(before), 'variant': 'B' if variant else 'A',
            'template_first': base + variant * 72, 'template_bytes': 72,
            'forward_page': forward, 'mirror_page': mirror, 'copied_SHA256': sha(code),
            'write_order': 'Y71..0, forward store then mirror store at each Y'}
        emits.append(event)
        for page in (forward, mirror):
            last_page[page] = event
        if masks[0] == 0xff:
            group_counter += 1
            old_second = template[0xf78f - base]
            patch_templates(first_zp_targets, old_second, 'F5B9 previous second ZP becomes first', group_counter)
            patch_templates(second_zp_targets, (old_second + 8) & 255, 'F5D5 second ZP increases by8', group_counter)
            scratch = source[0xf63a + group_counter]
            low = source[0xf626 + group_counter]
            patch_templates(scratch_targets, scratch, 'F5F5 source scratch-operand table', group_counter)
            if low & 128:
                patch_templates(screen_high_targets, 0, 'F609 negative low-table value selects zero-page destination', group_counter)
            patch_templates(screen_low_targets, low | 128, 'F617 destination low byte OR80', group_counter)
    assert group_counter == 20 and masks == reset
    assert mask_phases == [[255, 192, 128, 127], [63, 240, 224, 31],
                           [15, 252, 248, 7], [3, 255, 254, 1]]
    assert sorted(last_page) == list(range(0x20, 0xbc))
    constant_groups = constant_store_block(source, 0xf4c5, 0xf55a)
    boundary = []
    for item in constant_groups:
        for row in item['stores']:
            assert 0x6c00 <= row['address'] < 0x7000 and mask[row['address']]
            record = row | {'value': item['value'], 'prior': memory[row['address']]}
            boundary.append(record)
            store(row['address'], item['value'], row['source_PC'])
    assert len(boundary) == 40 and logical_count == 11560
    assert sum(mask) == 11232 and overwritten == 328
    cells = []
    for page, event in sorted(last_page.items()):
        for offset, length, role in [(0, 35, 'normal'), (35, 37, 'row-end')]:
            pc = (page << 8) + offset
            cells.append({'pc': pc, 'bytes': length, 'role': role,
                'variant': event['variant'], 'last_emission_iteration': event['iteration'],
                'last_emission_group': event['group'], 'last_emission_mask_phase': event['phase'],
                'boundary_patch_page': 0x6c <= page <= 0x6f,
                'final_code_hex': bytes(memory[pc:pc + length]).hex()})
    # F676 rotates in all eight bits from X. After eight rotations every
    # previous0400-byte bit is discarded; initial table bytes are unnecessary.
    assert source[0xf676:0xf686] == bytes.fromhex('a2008aa0074a3e00048810f9e8d0f360')
    lookup = bytes(int(f'{index:08b}'[::-1], 2) for index in range(256))
    return {'memory': bytes(memory), 'mask': bytes(mask), 'lookup': lookup,
        'dense': b''.join(memory[(page << 8):(page << 8) + 72] for page in range(0x20, 0xbc)),
        'final_templates': bytes(template), 'final_F5F0': group_counter,
        'cells': cells, 'emissions': emits, 'template_patches': patches,
        'boundary_patches': boundary, 'mask_phases': mask_phases,
        'logical_store_count': logical_count, 'distinct_generated_bytes': sum(mask),
        'logical_overwrites': overwritten, 'logical_store_digest': logical_digest.hexdigest(),
        'initial_inputs': {'pointer10_11': 0x2000, 'pointer12_13': 0xbb00,
            'mask20_21_22_23': list(reset), 'template_F5F0_group_counter': source[0xf5f0],
            'decimal_flag_precondition': 'D=0 for F5D5 ADC08; declared before prediction, verified at native entry only afterwards.',
            'previous_generated_cell_memory': 'Unknown and never read',
            'native_ZP_or_lookup_or_generated_bytes': 'Never read during prediction'},
        'unused_final_template_update': {'group': 20, 'scratch_table_address': 0xf64e,
            'scratch_table_value': source[0xf64e], 'low_table_address': 0xf63a,
            'low_table_value': source[0xf63a], 'not_copied_to_any_generated_page': True}}


def surrounding_init_contract(source, generated_mask):
    """Fixed macro footprints around the cell generator, without CPU execution."""
    assert source[0xf43d:0xf47c] == bytes.fromhex(
        'a227a9209dc007a9089dc0dbca10f3a200a000989dc007c0189006e849e89dc007'
        'c8e8e028d0eca9ffa2009507cbf8d0faa0079d8707cbf88810f88dff3f60')
    # Explicit recognized instruction boundaries avoid treating the F8 operand
    # of AXS#F8 as a SED opcode. No source step is interpreted or executed.
    predecessor_opcodes = [
        (0xf43d, 0xa2), (0xf43f, 0xa9), (0xf441, 0x9d), (0xf444, 0xa9),
        (0xf446, 0x9d), (0xf449, 0xca), (0xf44a, 0x10), (0xf44c, 0xa2),
        (0xf44e, 0xa0), (0xf450, 0x98), (0xf451, 0x9d), (0xf454, 0xc0),
        (0xf456, 0x90), (0xf458, 0xe8), (0xf459, 0x49), (0xf45b, 0x9d),
        (0xf45e, 0xc8), (0xf45f, 0xe8), (0xf460, 0xe0), (0xf462, 0xd0),
        (0xf464, 0xa9), (0xf466, 0xa2), (0xf468, 0x95), (0xf46a, 0xcb),
        (0xf46c, 0xd0), (0xf46e, 0xa0), (0xf470, 0x9d), (0xf473, 0xcb),
        (0xf475, 0x88), (0xf476, 0x10), (0xf478, 0x8d), (0xf47b, 0x60)]
    assert all(source[pc] == opcode and opcode != 0xf8 for pc, opcode in predecessor_opcodes)
    predecessor = list(range(0x07c0, 0x07e8)) + list(range(0xdbc0, 0xdbe8))
    predecessor += list(range(7, 256, 8)) + list(range(0x0787, 0x07c0, 8)) + [0x3fff]
    assert len(predecessor) == 121
    assert not any(0xf787 <= address < 0xf817 or address == 0xf5f0 for address in predecessor)
    assert not any(generated_mask[address] for address in predecessor)
    assert source[0xf64e:0xf658] == bytes.fromhex('a9008510a9058511a218')
    assert source[0xf658:0xf65f] == bytes.fromhex('a018b917f89110')
    assert source[0xf662:0xf66b] == bytes.fromhex('a918206bf6ca10ee60')
    call_kernel = [0x0500, 0x0500 + 24 * 24 + 25]
    assert call_kernel == [0x0500, 0x0759]
    later_ranges = []
    for first, loop, advance, page in [
        (0xf686, 0xf690, 0xf6bd, 0xc0), (0xf6c5, 0xf6cf, 0xf6fc, 0xc8),
        (0xf706, 0xf710, 0xf73d, 0xd0), (0xf745, 0xf74f, 0xf77c, 0xd8)]:
        assert source[first:first + 10] == bytes.fromhex('a9008510a9') + bytes([page]) + bytes.fromhex('8511a2c8')
        assert source[loop:loop + 2] == bytes.fromhex('a009')
        assert source[loop + 2] == 0xb9 and source[loop + 5:loop + 7] == bytes.fromhex('9110')
        assert source[advance:advance + 8] == bytes.fromhex('a909206bf6cad0cb')
        destination = page << 8
        #200 overlapping10-byte copies at stride9 cover exactly1801addresses.
        later_ranges.append([destination, destination + 199 * 9 + 10])
    template_targets = [0xf831, 0xf834, 0xf837, 0xf838, 0xf83b, 0xf83e, 0xf841, 0xf842,
                        0xf845, 0xf848, 0xf84b, 0xf84c, 0xf84f, 0xf852, 0xf855, 0xf856]
    later = list(range(*call_kernel)) + list(range(0x0400, 0x0500))
    for first, end in later_ranges:
        later += list(range(first, end))
    later += template_targets + [0x10, 0x11, 0x01]
    assert not any(generated_mask[address] for address in later)
    assert not any(0xf787 <= address < 0xf817 or address == 0xf5f0 for address in later)
    return {'recognized_predecessor': [0xf43d, 0xf47c],
        'predecessor_instruction_opcodes': predecessor_opcodes,
        'predecessor_has_no_SED_at_instruction_boundary': True,
        'predecessor_nominal_store_footprints': [
            {'first': 0x07c0, 'end_exclusive': 0x07e8, 'role': 'screen fill and indexed overwrite'},
            {'first': 0xdbc0, 'end_exclusive': 0xdbe8, 'role': 'ColorRAM destination addresses'},
            {'first': 7, 'end_exclusive': 256, 'stride': 8, 'count': 32, 'value': 255},
            {'first': 0x0787, 'end_exclusive': 0x07c0, 'stride': 8, 'count': 8, 'value': 255},
            {'address': 0x3fff, 'value': 255}],
        'predecessor_does_not_mutate_original_cell_templates_or_group_operand': True,
        'predecessor_does_not_write_generated_cell_prefixes': True,
        'later_F64E_copy_footprint': {'range': call_kernel, 'copies': 25, 'bytes_per_copy': 25, 'stride': 24},
        'later_F686_copy_footprints': [{'range': row, 'copies': 200, 'bytes_per_copy': 10, 'stride': 9} for row in later_ranges],
        'later_F686_template_patch_addresses': template_targets,
        'later_other_addresses': [0x10, 0x11, 0x01],
        'tail_F676_lookup_footprint': [0x0400, 0x0500],
        'all_later_footprints_disjoint_from_generated_cell_mask_and_cell_templates': True,
        'scope': 'Finite nominal source-store addresses only; no bus mapping, IRQ interleaving or executed-store history claim.'}


def native_oracles(prediction):
    proof, proof_meta = pin(NATIVE, NATIVE_SHA)
    association, association_meta = pin(ASSOCIATION, ASSOCIATION_SHA)
    assert proof['pass_'] is True and association['pass_'] is True
    assert sha((ROOT / READER).read_bytes()) == READER_SHA
    spec = importlib.util.spec_from_file_location('aloft_cell_snapshot_reader', ROOT / READER)
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    captures, memories = [], {}
    by_stem = {item['stem']: item for item in proof['captures']}
    for stem, expected_pc in [('part08-entry', 0x0890), ('part08-body', 0xf02b)]:
        item = by_stem[stem]
        raw = checked(item['ram'])
        checked(item['snapshot'])
        path = ROOT / item['snapshot']['path']
        state = reader.read_snapshot(path)
        cpu, mem = reader.module_payload(path, 'MAINCPU'), reader.module_payload(path, 'C64MEM')
        assert state['modules']['MAINCPU']['version'] == [1, 4] and len(cpu) == 103
        assert state['modules']['C64MEM']['version'] == [0, 1] and len(mem) == 65555
        assert len(raw) == 65536 and raw == mem[4:65540]
        reg = item['registers']
        assert int.from_bytes(cpu[12:14], 'little') == reg['pc'] == expected_pc
        assert int.from_bytes(cpu[:8], 'little') == reg['clock']
        assert list(cpu[8:12]) == [reg['a'], reg['x'], reg['y'], reg['sp']]
        assert cpu[14] == reg['flags']
        assert (reg['line'], reg['cycle']) == (reg['clock'] // 63 % 312, reg['clock'] % 63)
        assert reg['port00'] == mem[1] == mem[65542] == 0x2f
        assert reg['port01'] == mem[65541]
        assert not (reg['port01'] & 2), 'source F000 must be RAM-visible, HIRAM clear'
        assert mem[0] & mem[1] == mem[65541] & mem[1]
        assert item['stop']['natural'] is True and item['all65536_physical_RAM_bytes_equal'] is True
        captures.append({'stem': stem, 'ram': item['ram'], 'snapshot': item['snapshot'],
            'registers': reg, 'stop_sequence': item['stop_sequence'], 'beam': item['beam'],
            'all65536_RAM_equal_snapshot': True,
            'wire_boot_checkpoint_custody': 'Delegated to pinned original native proof.'})
        memories[stem] = raw
    body = memories['part08-body']
    differences = [{'address': i, 'predicted': prediction['memory'][i], 'native': body[i]}
        for i, known in enumerate(prediction['mask']) if known and prediction['memory'][i] != body[i]]
    template_differences = [{'address': 0xf787 + i, 'predicted': byte, 'native': body[0xf787 + i]}
        for i, byte in enumerate(prediction['final_templates']) if body[0xf787 + i] != byte]
    results = {'all11232_generated_bytes_equal': not differences,
        'differences': differences, 'all144_final_template_bytes_equal': not template_differences,
        'template_differences': template_differences,
        'F5F0_counter_predicted': prediction['final_F5F0'], 'F5F0_native': body[0xf5f0],
        'all256_lookup0400_bytes_equal': prediction['lookup'] == body[0x0400:0x0500],
        'declared_decimal_clear_precondition_equal_native_entry':
            not (by_stem['part08-entry']['registers']['flags'] & 8),
        'decimal_clear_at_prebody': not (by_stem['part08-body']['registers']['flags'] & 8),
        'lookup_input_not_required': 'Eight fresh input bits replace all eight previous bits.',
        'all_oracles_opened_after_prediction_files_written': True}
    return results, captures, [proof_meta, association_meta, meta(ROOT / READER)], memories


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    out.relative_to(BASE.resolve())
    out.mkdir(parents=True, exist_ok=False)
    checked_path = out / 'cells.checked.py'
    checked_path.write_bytes(Path(__file__).read_bytes())
    try:
        source, contract = source_input()
        prediction = predict(source)
        surrounding = surrounding_init_contract(source, prediction['mask'])
        files = [checked_path]
        for name, raw in [('predicted-cell-memory.bin', prediction['memory']),
                          ('predicted-cell-mask.bin', prediction['mask']),
                          ('predicted-cell-bytes.bin', prediction['dense']),
                          ('predicted-final-templates.bin', prediction['final_templates']),
                          ('predicted-lookup0400.bin', prediction['lookup'])]:
            path = out / name
            path.write_bytes(raw)
            files.append(path)
        layout = out / 'cell-layout.json'
        json_write(layout, {'source': contract, 'cells': prediction['cells'],
            'page_first': 0x20, 'page_end_exclusive': 0xbc, 'normal_offset': 0,
            'normal_bytes': 35, 'row_end_offset': 35, 'row_end_bytes': 37,
            'every_page_first72_bytes_generated_rest_unclaimed': True})
        files.append(layout)
        ledger = out / 'generation-ledger.json'
        json_write(ledger, {key: prediction[key] for key in (
            'initial_inputs', 'emissions', 'mask_phases', 'template_patches', 'boundary_patches',
            'unused_final_template_update', 'logical_store_count', 'distinct_generated_bytes',
            'logical_overwrites', 'logical_store_digest', 'final_F5F0')} | {'surrounding_init_contract': surrounding})
        files.append(ledger)
        # Every source prediction artifact above exists before any native RAM opens.
        result, captures, native_inputs, memories = native_oracles(prediction)
        result['all_source_guard_bytes_equal_native_entry'] = all(
            source[first:end] == memories['part08-entry'][first:end] for first, end, digest, role in GUARDS)
        comparisons = out / 'native-comparisons.json'
        json_write(comparisons, result | {'captures': captures})
        files.append(comparisons)
        assert result['all11232_generated_bytes_equal'], 'generated cell mismatch'
        assert result['all144_final_template_bytes_equal'], 'final template mismatch'
        assert result['F5F0_native'] == result['F5F0_counter_predicted']
        assert result['all256_lookup0400_bytes_equal'], 'lookup mismatch'
        assert result['declared_decimal_clear_precondition_equal_native_entry']
        assert result['decimal_clear_at_prebody']
        assert result['all_source_guard_bytes_equal_native_entry'], 'source-entry generation mismatch'
        proof = {'pass_': True, 'scope': 'Finite source-only F47C paired-page generator, explicit template/boundary patches and bit-reversal lookup; late native comparisons only. No CPU or cell execution.',
            'producer': meta(Path(__file__).resolve()), 'source_contract': contract,
            'native_inputs_as_oracles_only': native_inputs, 'captures': captures,
            'prediction_written_before_native_oracles': True,
            'page_count': 156, 'cell_count': 312, 'generated_bytes': 11232,
            'full_generated_byte_equality': True, 'final_template_bytes': 144,
            'final_group_counter': 20, 'lookup_bytes': 256,
            'logical_generation_store_operations': 11560,
            'mask_phases': prediction['mask_phases'],
            'boundary_patch_write_count': 40, 'source_generation': 31,
            'surrounding_source_footprints': surrounding,
            'limits': ['Only the first72bytes of each page20..BB are generated-cell claims; other RAM bytes are unclaimed.',
                'Generated code, original templates and all init literals/tables are independent original-packet predictions; target code/ZP/device values never seed them.',
                'Binary ADC08 arithmetic requires D=0. This is declared before prediction and verified afterwards against genuine native entry CPU flags; no generated output chooses the precondition.',
                'This source macro model does not execute generated cells, the init CPU, IRQs, physical stores, dummy accesses or VIC fetches.',
                'The logical source-store count is not a native trace or hardware timing observation.',
                'F55A/F5B9 and the final40store block are generation-time SMC. Per-frame0500 target selection and motion-table evaluation remain separate questions.',
                'The final unused template group20 reads F64E code byte as source data; no generated page consumes that unused update.',
                'Bit reversal fully replaces the previous0400-byte bits; no old lookup table byte is used as input.',
                'Full wire/boot/checkpoint/process custody belongs to the pinned native proof; selected RAM/VSF/CPU identity is independently rechecked here.',
                'No named target-scene, committed-pixel, complete-animation, bus timing, FPS or optimization result.'],
            'outputs': [output_meta(path) for path in files]}
        receipt = out / 'cell-generator-proof.json'
        json_write(receipt, proof)
        print(json.dumps({'pass_': True, 'receipt': meta(receipt), 'generated_bytes': 11232, 'cells': 312}))
    except Exception as error:
        json_write(out / 'failure.json', {'pass_': False, 'error': type(error).__name__,
            'reason': str(error), 'scope': 'Failure retained; prediction files are not accepted output.',
            'no_native_oracle_values_seed_source_model': True})
        raise


if __name__ == '__main__':
    main()
