#!/usr/bin/env python3
"""Map stream 46 and optionally analyze its owner's frozen native captures.

This never executes a CPU or opens VICE. Default output is a static source
contract; --capture adds the bounded original native evidence. The existing
selector proof owns the 50-case/1,275-cell byte validation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parents[2]
IMAGE_SHA = '3be2386eeb9c9f0d3bb274eab04fd7aa48f7df3b3a10199df3d49cecaabec31c'
INDEX_SHA = '307b6de0dd9a5ca8fa81d095260768088bb29d49937a7b0a5772a068e4d3f709'
VICE_SHA = '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1'
MONITOR_PROOF_SHA = 'd0cebe1729be950fb09e3a04c74098b23ad0eb0c592ec37e12024c4b60f517ba'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def name_module_differences(comparison, first, second, module_payload):
    """Annotate every changed byte from the pinned writers; omit none."""
    layouts = {
        '1541VIA1D0': ([2, 2], ((6, 2, 'T1_counter'), (12, 2, 'T2_counter'),
                                  (22, 1, 'packed_CA2_CB2_CB1_levels')), 'src/core/viacore.c:1958-1977'),
        'VIA2D0': ([2, 2], ((6, 2, 'T1_counter'), (12, 2, 'T2_counter'),
                              (22, 1, 'packed_CA2_CB2_CB1_levels')), 'src/core/viacore.c:1958-1977'),
        'DRIVECPU0': ([1, 3], ((0, 8, 'drive_clock'), (8, 1, 'A'), (9, 1, 'X'),
                                (10, 1, 'Y'), (11, 1, 'SP'), (12, 2, 'PC'), (14, 1, 'status'),
                                (15, 4, 'last_opcode_info'), (19, 8, 'last_clk'),
                                (27, 8, 'cycle_accum'), (35, 8, 'last_exc_cycles'),
                                (43, 8, 'stop_clk'), (51, 1, 'cpu_last_data')), 'src/drive/drivecpu.c:543-572'),
        'SIDEXTENDED': ([1, 4], ((27, 1, 'register_1B_OSC3_readback'),), 'src/sid/sid-snapshot.c:663; src/resid/sid.cc:187-189,380-383'),
    }
    for difference in comparison['different_modules']:
        name = difference['module']
        assert name in layouts, f'Unclassified whole-snapshot difference: {name}'
        version, fields, source = layouts[name]
        assert difference['first_version'] == difference['second_version'] == version
        a, b = module_payload(first, name), module_payload(second, name)
        assert len(a) == len(b)
        changed = {item['payload_offset'] for item in difference['differences']}
        mapped, covered = [], set()
        for offset, length, field in fields:
            overlap = changed & set(range(offset, offset+length))
            if overlap:
                covered |= overlap
                mapped.append(dict(field=field, payload_offset=offset, bytes=length,
                                   first=int.from_bytes(a[offset:offset+length], 'little'),
                                   second=int.from_bytes(b[offset:offset+length], 'little')))
        assert covered == changed, (name, sorted(changed-covered))
        difference.update(named_fields=mapped, source=source, all_changed_bytes_named=True)
    comparison['scope_note'] = ('All bytes retained. VIA combinedCB1 packing has a writer/reader asymmetry; '
                                'drive clocks/status remain different. ReSID OSC3 is a derived readback '
                                'not restored as a writable SID register; the cause of its changed value '
                                'is not established here. This is not whole-machine or audio equivalence.')
    return comparison


TRACE = re.compile(
    r'^#(?P<checkpoint>\d+) \(Trace store (?P<target>[0-9a-f]{4})\)\s+'
    r'(?P<line>\d+)/\$[0-9a-f]+,\s+(?P<cycle>\d+)/\$[0-9a-f]+\n'
    r'\.C:(?P<pc>[0-9a-f]+)\s+[^\n]*?'
    r'- A:(?P<a>[0-9a-f]+) X:(?P<x>[0-9a-f]+) Y:(?P<y>[0-9a-f]+) '
    r'SP:(?P<sp>[0-9a-f]+) [^\n]*?\s+(?P<clock>\d+)\n', re.M | re.I)


def native_segment(directory, output, original, selector, allow_live):
    """Read frozen captures and literal store data; no CPU or hardware model."""
    # The sibling owns monitor-context and physical-RAM parsing. Pin the
    # readers in this receipt; do not duplicate its general initializer proof.
    import native_capture as readers
    from snapshot_state import compare_modules, module_payload, read_snapshot
    session = json.loads((directory / 'session.json').read_text())
    if not allow_live:
        assert session.get('closed_utc'), 'Final native evidence requires a closed owner session.'
    text = (directory / 'monitor.log').read_text(errors='replace')
    events = {e['filename']: e for e in readers.contexts(text)}

    def capture(stem, expected_pc):
        vsf = directory / f'{stem}.vsf'
        raw = directory / f'ram-{stem}.bin'
        event, raw_event = events[vsf.name], events[raw.name]
        reg = event['registers']
        assert event['command'] == 'dump' and reg == raw_event['registers']
        assert raw_event['bank'] == 'ram' and raw_event['first'] == 0 and raw_event['end_inclusive'] == 65535
        assert reg['pc'] == expected_pc
        state = read_snapshot(vsf)
        cpu = module_payload(vsf, 'MAINCPU')
        assert state['modules']['MAINCPU']['version'] == [1, 4]
        assert int.from_bytes(cpu[:8], 'little') == reg['clock']
        assert list(cpu[8:12]) == [reg[k] for k in ('a', 'x', 'y', 'sp')]
        assert int.from_bytes(cpu[12:14], 'little') == reg['pc']
        assert (state['vicii']['raster_line'], state['vicii']['raster_cycle']) == (reg['raster_line'], reg['raster_cycle'])
        ram = readers.physical_ram(vsf)
        assert len(raw.read_bytes()) == 65536 and raw.read_bytes() == ram
        assert ram[0x69c1:0xb50c] == original[0x69c1:0xb50c]
        assert ram[0xbb64:0xbbc8] == original[0xbb64:0xbbc8]
        cia = state['cia']['CIA2']
        assert cia['ddra'] & 3 == 3, 'Bank decode here requires both selector pins to be outputs.'
        vic = state['vicii']
        io = dict(d011=vic['regs'][0x11], d016=vic['regs'][0x16], d018=vic['regs'][0x18],
                  cia2_pra=cia['pra'], cia2_ddra=cia['ddra'],
                  vic_bank_from_output_pins=((~cia['pra']) & 3)*0x4000)
        record = dict(stem=stem, registers=reg, physical_RAM_sha256=sha(ram),
                      snapshot_sha256=sha(vsf.read_bytes()),
                      all65536_raw_RAM_bytes_equal_snapshot=True,
                      family19275_and_target100_bytes_original=True, io=io,
                      vic={k:vic[k] for k in ('raster_line', 'raster_cycle', 'rc', 'vcbase', 'vc',
                            'vmli', 'bad_line', 'allow_bad_lines', 'idle_state', 'reg11_delay',
                            'vbuf', 'cbuf', 'gbuf', 'vborder', 'main_border', 'sprite_dma')})
        return ram, state, reg, record

    before, before_state, first, a = capture('selector-segment-before', 0x68b9)
    after, after_state, last, b = capture('selector-segment-after-traced', 0x68bc)
    control, control_state, control_reg, c = capture('selector-segment-after-control', 0x68bc)
    assert last == control_reg
    assert before == after == control, 'The selected JMP/load/store/INX routine changes no physical RAM.'
    target = int.from_bytes(before[0x68ba:0x68bc], 'little')
    cases = [case for case in selector['cases'] if case['first'] == target]
    assert len(cases) == 1
    case = cases[0]
    count, x0 = case['cells'], first['x']
    expected = []
    for row, value in enumerate(case['selectors']):
        x = (x0+row) & 255
        pc = target+15*row
        for offset, port, v in ((3, 0xd011, before[0xb800+x]),
                                (8, 0xdd00, value), (11, 0xd018, value)):
            expected.append(dict(pc=pc+offset, target=port, a=v, x=x,
                                 y=first['y'], sp=first['sp'], row=row))
    actual = []
    for match in TRACE.finditer(text):
        f = match.groupdict()
        item = {k:int(v, 16 if k in ('target', 'pc', 'a', 'x', 'y', 'sp') else 10) for k, v in f.items()}
        if first['clock'] <= item['clock'] <= last['clock']:
            assert before[item['pc']] == 0x8d
            assert int.from_bytes(before[item['pc']+1:item['pc']+3], 'little') == item['target']
            actual.append(item)
    assert len(actual) == len(expected) == 3*count
    for expected_item, actual_item in zip(expected, actual):
        assert all(actual_item[k] == v for k, v in expected_item.items() if k != 'row'), (expected_item, actual_item)
        actual_item['row'] = expected_item['row']
    assert last['x'] == (x0+count) & 255 and last['a'] == case['selectors'][-1]
    assert all(last[k] == first[k] for k in ('y', 'sp', 'port00', 'port01'))
    expected_flags = (first['flags'] & ~0x82) | (0x80 if last['x'] & 128 else 0) | (2 if last['x'] == 0 else 0)
    assert last['flags'] == expected_flags
    d011 = actual[0::3]
    periods = [v['clock']-u['clock'] for u, v in zip(d011, d011[1:])]
    assert periods and set(periods) == {63}
    assert all(v['line'] == first['raster_line']+i for i, v in enumerate(d011))
    assert len({v['cycle'] for v in d011}) == 1
    assert all(y['clock']-x['clock'] == 6 and z['clock']-y['clock'] == 4
               for x, y, z in zip(actual[0::3], actual[1::3], actual[2::3]))
    # The pinned finite fixture is the owner's case14 trace; later cases
    # require separate evidence rather than silently inheriting these phases.
    assert target == 0x7012 and case['index'] == 14 and count == 15 and x0 == 0x50
    assert first['clock'] == 259896720 and last['clock'] == 259897628
    assert [v['cycle'] for v in actual[:3]] == [59, 2, 6]
    assert all(v['line'] == first['raster_line']+v['row']+(v['target'] != 0xd011) for v in actual)
    compare = compare_modules(directory/'selector-segment-after-traced.vsf', directory/'selector-segment-after-control.vsf')
    different = {item['module'] for item in compare['different_modules']}
    assert not different & {'MAINCPU', 'C64MEM', 'VIC-II'}, 'Trace changed a core result module.'
    sid = module_payload(directory/'selector-segment-after-traced.vsf', 'SID')
    assert before_state['modules']['SID']['version'] == [1, 5] and sid[:4] == bytes((0, 1, 1, 1))
    compare = name_module_differences(compare, directory/'selector-segment-after-traced.vsf',
                                      directory/'selector-segment-after-control.vsf', module_payload)
    micros = []
    for label, row in (('fb', 0), ('72', 3), ('70', 6), ('f8', 8)):
        pre, pre_state, pre_reg, pre_record = capture(f'micro-{label}-before-dma', target+15*row+14)
        post, post_state, post_reg, post_record = capture(f'micro-{label}-after-dma', target+15*(row+1)+3)
        assert pre == post == before
        v0, v1 = pre_state['vicii'], post_state['vicii']
        value = case['selectors'][row]
        assert value == int(label, 16)
        raster = first['raster_line']+row+1
        assert [v0['raster_line'], v0['raster_cycle'], v1['raster_line'], v1['raster_cycle']] == [raster, 6, raster, 55]
        assert post_reg['clock']-pre_reg['clock'] == 49
        assert pre_reg['x'] == x0+row and post_reg['x'] == x0+row+1
        assert pre_reg['a'] == value and post_reg['a'] == before[0xb800+x0+row+1]
        assert v0['rc'] == (7 if row == 0 else 1) and v1['rc'] == 0
        assert all(v[k] == expected for v in (v0, v1) for k, expected in
                   (('vcbase', 520), ('vmli', 40), ('bad_line', 1), ('allow_bad_lines', 1),
                    ('idle_state', 0), ('sprite_dma', 0), ('vborder', 0)))
        assert v0['vc'] == (520 if row == 0 else 560) and v1['vc'] == 560
        assert v0['main_border'] == 1 and v1['main_border'] == 0
        for state in (pre_state, post_state):
            v, cia = state['vicii'], state['cia']['CIA2']
            assert v['regs'][0x18] & 0xfe == value & 0xfe
            assert cia['pra'] == value and cia['ddra'] == 0x37
            assert v['regs'][0x11] == v['reg11_delay'] == before[0xb800+x0+row]
        bank = ((~value) & 3)*0x4000
        screen = bank+((value & 0xf0) << 6)
        expected_matrix = list(before[screen+520:screen+560])
        expected_color = post_state['vicii']['color_ram'][520:560]
        assert v1['vbuf'] == expected_matrix and v1['cbuf'] == expected_color
        if row == 0:
            assert v0['vbuf'] != expected_matrix and v0['cbuf'] != expected_color
        micros.append(dict(selector=value, selected_cell=row, snapshots=[pre_record, post_record],
                           all65536_RAM_bytes_equal_segment_start=True,
                           before_RC=v0['rc'], after_RC=v1['rc'], vcbase=520,
                           all40_fetched_matrix_and_color_bytes_exact=True,
                           matrix_address=screen+520,
                           before_matrix_differs_from_fetched_row=v0['vbuf'] != expected_matrix,
                           black_gated_ECM_BMM=True,
                           scope='Four exact beam-point pairs inside this case, not a full-raster pixel oracle.'))
    cont_after, cont_state, cont_last, cont_record = capture('selector-continuation-after-traced', 0x69be)
    cont_control, _, cont_control_reg, cont_control_record = capture('selector-continuation-after-control', 0x69be)
    assert cont_last == cont_control_reg and cont_after == cont_control
    assert before[0xb600:0xb800] == original[0xb600:0xb800]
    assert before[0xba00:0xbbc8] == original[0xba00:0xbbc8]
    phase0 = (after[0xb51d]+after[0xb51f]) & 255
    phase1 = (after[0xb51e]+after[0xb520]) & 255
    delta = ((after[0xb600+phase0]+after[0xb700+phase1]) - after[0xb514]) & 255
    half = 0 if delta & 128 else delta//2
    next_index = min(49, half)
    next_target = original[0xbb64+next_index]+256*original[0xbb96+next_index]
    next_selectors = [original[base+next_index] for base in (0xba00, 0xba32, 0xba64, 0xba96, 0xbac8, 0xbb00, 0xbb32)]
    expected_ram = bytearray(after)
    expected_ram[0xb51d:0xb51f] = bytes((phase0, phase1))
    expected_ram[0x68ba:0x68bc] = next_target.to_bytes(2, 'little')
    expected_ram[0xb50d:0xb514] = bytes(next_selectors)
    # Original helper-chain returns leave these literal JSR operands on the
    # hardware stack. They happen already to have these values in this pose.
    sp = last['sp']
    for relative, value in ((0, 0x69), (-1, 0xbc), (-2, 0x60), (-3, 0x41), (-4, 0x60), (-5, 0x3d)):
        expected_ram[0x100+((sp+relative) & 255)] = value
    assert cont_after == expected_ram, 'Continuation RAM differs from its independent finite arithmetic/JSR contract.'
    assert next_index == 17 and next_target == 0x72eb
    assert cont_last['x'] == (last['x']+7) & 255 and cont_last['y'] == next_index
    assert cont_last['a'] == next_selectors[-1]
    assert all(cont_last[k] == last[k] for k in ('sp', 'port00', 'port01'))
    cont_flags = ((last['flags'] & ~0xc3) | (after[0xea] & 0x40)
                  | (0x80 if cont_last['a'] & 128 else 0) | (2 if cont_last['a'] == 0 else 0)
                  | (1 if half >= 49 else 0))
    assert cont_last['flags'] == cont_flags
    cont_trace = []
    for match in TRACE.finditer(text):
        f = match.groupdict()
        item = {k:int(v, 16 if k in ('target', 'pc', 'a', 'x', 'y', 'sp') else 10) for k, v in f.items()}
        if last['clock'] <= item['clock'] <= cont_last['clock']:
            opcode = after[item['pc']]
            assert opcode in (0x8c, 0x8d)
            assert int.from_bytes(after[item['pc']+1:item['pc']+3], 'little') == item['target']
            item['value'] = item['y' if opcode == 0x8c else 'a']
            cont_trace.append(item)
    assert len(cont_trace) == 21
    starts = (0x68bc, 0x68e8, 0x691c, 0x6942, 0x6958, 0x696e, 0x6998)
    for row, pc in enumerate(starts):
        x = (last['x']+row) & 255
        values = (after[0xb900+x], after[0xb50d+row], after[0xb50d+row])
        for item, offset, port, value in zip(cont_trace[row*3:row*3+3], (3, 9, 12),
                                              (0xd011, 0xdd00, 0xd018), values):
            assert (item['pc'], item['target'], item['value'], item['x'], item['sp']) == (pc+offset, port, value, x, last['sp'])
    assert [v['cycle'] for v in cont_trace[0::3]] == [62, 61, 61, 61, 61, 61, 56]
    assert [v['line'] for v in cont_trace[0::3]] == list(range(95, 102))
    assert cont_last['clock']-last['clock'] == 475
    cont_compare = compare_modules(directory/'selector-continuation-after-traced.vsf', directory/'selector-continuation-after-control.vsf')
    assert cont_compare['all_module_payloads_equal'], 'Continuation trace/control differ; classify before expanding this proof.'
    cont_micros = []
    for stem, pc, raster, cycle, rc, vcbase in (
            ('micro-continuation-rc1', 0x68cb, 96, 11, 1, 520),
            ('micro-continuation-rc4', 0x6951, 99, 10, 4, 520),
            ('micro-continuation-rc7', 0x69a7, 102, 5, 7, 520),
            ('micro-next-row-before-dma', 0x72f9, 103, 6, 7, 560)):
        ram, state, reg, record = capture(stem, pc)
        v = state['vicii']
        assert (v['raster_line'], v['raster_cycle'], v['rc'], v['vcbase']) == (raster, cycle, rc, vcbase)
        assert v['idle_state'] == 0 and v['allow_bad_lines'] == 1 and v['sprite_dma'] == 0
        assert v['bad_line'] == (1 if stem == 'micro-next-row-before-dma' else 0)
        assert v['regs'][0x11] & 0x60 == 0x60
        record['RAM_changes_from_continuation_start'] = [dict(address=i, before=x, actual=y)
                                                         for i, (x, y) in enumerate(zip(after, ram)) if x != y]
        cont_micros.append(record)
    continuation_evidence = dict(
        snapshots=[cont_record, cont_control_record], observed_cycles=475,
        all21_store_PCs_values_X_SP_exact=True, trace_events=cont_trace,
        all65536_RAM_bytes_match_independent_finite_contract=True,
        derived_phase_values=[phase0, phase1], derived_index=next_index,
        derived_target=next_target, derived_next_selectors=next_selectors,
        RAM_net_changes=[dict(address=i, before=x, expected=y) for i, (x, y) in enumerate(zip(after, expected_ram)) if x != y],
        trace_control_all_module_comparison=cont_compare, micro_row_progression=cont_micros,
        scope='One following continuation. RC1/4/7 and nextVCBASE are sampled witnesses, not a complete image or all-eight-row scaling oracle.')
    rmw_before, rb_state, rb_reg, rb_record = capture('selector-rmw-before', 0x6763)
    rmw_mid, rm_state, rm_reg, rm_record = capture('selector-rmw-mid', 0x6766)
    rmw_after, ra_state, ra_reg, ra_record = capture('selector-rmw-after-traced', 0x6769)
    rmw_control, _, rac_reg, rac_record = capture('selector-rmw-after-control', 0x6769)
    clean, clean_state, clean_reg, clean_record = capture('selector-rmw-clean-return-after-traced', 0x631b)
    clean_control, _, clean_control_reg, clean_control_record = capture('selector-rmw-clean-return-after-untraced', 0x631b)
    assert rmw_before == rmw_mid == rmw_after == rmw_control == clean == clean_control
    assert ra_reg == rac_reg and clean_reg == clean_control_reg
    assert rm_reg['clock']-rb_reg['clock'] == 6
    assert ra_reg['clock']-rb_reg['clock'] == 52
    assert clean_reg['clock']-rb_reg['clock'] == 58
    assert rb_reg['clock'] == 265812191
    rmw_fields = ('raster_line', 'raster_cycle', 'rc', 'vcbase', 'vc', 'vmli', 'bad_line', 'idle_state')
    for state, expected in (
            (rb_state, (65, 8, 7, 400, 400, 40, 0, 1)),
            (rm_state, (65, 14, 7, 400, 400, 0, 1, 0)),
            (ra_state, (65, 60, 0, 440, 440, 40, 0, 0)),
            (clean_state, (66, 3, 0, 440, 440, 40, 1, 0))):
        assert tuple(state['vicii'][key] for key in rmw_fields) == expected
        assert state['vicii']['allow_bad_lines'] == 1 and state['vicii']['sprite_dma'] == 0
    assert [state['vicii']['regs'][0x11] for state in (rb_state, rm_state, ra_state, clean_state)] == [0x72, 0x71, 0x72, 0x72]
    for state, register, value in ((rm_state, rm_reg, 0x71), (ra_state, ra_reg, 0x72),
                                    (clean_state, clean_reg, 0x72)):
        assert all(register[k] == rb_reg[k] for k in ('a', 'x', 'y', 'port00', 'port01'))
        assert register['flags'] == ((rb_reg['flags'] & ~0x82) | (value & 0x80) | (2 if value == 0 else 0))
    assert rm_reg['sp'] == ra_reg['sp'] == rb_reg['sp'] == 0x56
    assert clean_reg['sp'] == 0x58
    assert int.from_bytes(rmw_before[0x157:0x159], 'little')+1 == clean_reg['pc']

    def replay_text(stem):
        """Select one named restore→capture trial, not all equal-clock replays."""
        lines = text.splitlines()
        end = events[f'{stem}.vsf']['transcript_line']
        starts = [i for i, line in enumerate(lines[:end])
                  if line.startswith('undump "') and line.split('"')[1].endswith('/selector-rmw-before.vsf')]
        assert starts, f'No source restore before {stem}'
        return '\n'.join(lines[starts[-1]:end])+'\n'

    clean_trace_text = replay_text('selector-rmw-clean-return-after-traced')
    clean_untraced_text = replay_text('selector-rmw-clean-return-after-untraced')
    assert not list(TRACE.finditer(clean_untraced_text)), 'Canonical no-trace control still contains trace events.'
    rmw_trace = []
    for match in TRACE.finditer(clean_trace_text):
        f = match.groupdict()
        item = {k:int(v, 16 if k in ('target', 'pc', 'a', 'x', 'y', 'sp') else 10) for k, v in f.items()}
        assert item['target'] == 0xd011
        assert all(item[k] == rb_reg[k] for k in ('a', 'x', 'y', 'sp'))
        rmw_trace.append(item)
    assert [(e['pc'], e['clock'], e['line'], e['cycle']) for e in rmw_trace] == [
        (0x6763, 265812197, 65, 14), (0x6763, 265812197, 65, 14),
        (0x6766, 265812243, 65, 60), (0x6766, 265812243, 65, 60)]
    rmw_compare = compare_modules(directory/'selector-rmw-clean-return-after-traced.vsf',
                                  directory/'selector-rmw-clean-return-after-untraced.vsf')
    pair_compare = compare_modules(directory/'selector-rmw-after-traced.vsf',
                                   directory/'selector-rmw-after-control.vsf')
    assert rmw_compare['all_module_payloads_equal'] and pair_compare['all_module_payloads_equal']
    monitor_proof_path = ROOT/'build/research/vice-trace-timing/source-proof.json'
    assert sha(monitor_proof_path.read_bytes()) == MONITOR_PROOF_SHA
    monitor_proof = json.loads(monitor_proof_path.read_text())
    assert monitor_proof['pass'] and monitor_proof['archive_sha256'] == VICE_SHA
    rmw_evidence = dict(
        snapshots=[rb_record, rm_record, ra_record, rac_record, clean_record, clean_control_record],
        all65536_RAM_bytes_unchanged=True, CPU_registers_flags_stack_return_exact=True,
        observed_pair_cycles=52, observed_pair_plus_RTS_cycles=58,
        returned_to_original_JSR_caller=True,
        source_derived_old_new_values=[0x72, 0x71, 0x71, 0x72],
        trace_does_not_log_RMW_store_values=True, clean_trace_events=rmw_trace,
        trace_window_has_no_prior_restore_records=True,
        canonical_untraced_window_has_no_trace_events=True,
        pair_endpoint_all_module_comparison=pair_compare,
        clean_return_all_module_comparison=rmw_compare,
        rejected_or_limited_trials=[
            dict(stem='selector-rmw-after-traced', reason='Stops at next instruction breakpoint before final queued INC records are drained; endpoint valid but trace incomplete.'),
            dict(stem='selector-rmw-return-after-traced', reason='Six records include two stale queued entries; excluded as a clean four-write trace.'),
            dict(stem='selector-rmw-clean-return-after-control', reason='Wrong delete ID left trace3 active with dummy off; retained but not accepted as an untraced control.')],
        monitor_timing_source_note='docs/research/vice-trace-timing.md',
        monitor_timing_source_proof=dict(path=str(monitor_proof_path.relative_to(ROOT)), sha256=MONITOR_PROOF_SHA),
        scope='Observed late-badline pulse advances VCBASE40 and wraps RC7→0 while restoring D011. Four queued monitor records are not four separately measured bus-write phases.')
    visual_observations = []
    first_visual_reg = None
    for suffix, phase, elapsed in (('a', 0x6401, 0), ('b', 0x6414, 100), ('c', 0x648d, 300)):
        stem = f'selector-visible-{suffix}'
        ram, state, reg, record = capture(stem, 0x6336)
        assert int.from_bytes(ram[0x64d7:0x64d9], 'little') == phase and ram[0x606d] == 0
        if suffix in ('b', 'c'):
            expected_pages = bytearray(original[0xb800:0xba00])
            for page in (0, 256):
                for index in range(0x50, 0xfc):
                    expected_pages[page+index] &= 0x3f
            assert ram[0xb800:0xba00] == expected_pages, 'Full reveal is not complete at this observation.'
        if first_visual_reg is None:
            first_visual_reg = reg
        assert reg['raster_line'] == first_visual_reg['raster_line'] == 251
        assert reg['clock']-first_visual_reg['clock'] == elapsed*19656+reg['raster_cycle']-first_visual_reg['raster_cycle']
        png = directory/f'{stem}.png'
        assert png.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        assert events[png.name]['registers'] == reg
        record.update(png=str(png.relative_to(ROOT)), png_sha256=sha(png.read_bytes()),
                      elapsed_PAL_periods=elapsed, choreography_continuation=phase,
                      full_reveal_verified=suffix in ('b', 'c'),
                      scope='Original output observation only. No pixel oracle or named-effect identity; viewed frames remain bands.')
        visual_observations.append(record)
    native = dict(
        pass_=True, provisional=not bool(session.get('closed_utc')), session=session,
        script_sha256=sha(Path(__file__).read_bytes()),
        image_payload_sha256=IMAGE_SHA, stream_index_sha256=INDEX_SHA,
        selector_proof_sha256=sha((ROOT/'build/research/demo-coder/selector-analysis/selector-proof.json').read_bytes()),
        hardware_source_archive_sha256=VICE_SHA,
        static_contract_sha256=sha((output/'raster-contract.json').read_bytes()),
        capture_directory=str(directory.relative_to(ROOT)),
        transcript_sha256=sha((directory/'monitor.log').read_bytes()),
        helper_sha256={str(ROOT/'research/demo-coder/native_capture.py'):sha(Path(readers.__file__).read_bytes()),
                       str(ROOT/'research/nine/native_capture.py'):sha((ROOT/'research/nine/native_capture.py').read_bytes()),
                       str(ROOT/'research/quondam/snapshot_state.py'):sha((ROOT/'research/quondam/snapshot_state.py').read_bytes())},
        snapshots=[a, b, c], target=target, table_index=case['index'], cells=count,
        all65536_physical_RAM_bytes_unchanged=True,
        all_expected_store_PCs_values_registers_match=True,
        selected_call_clocks=last['clock']-first['clock'],
        nominal_cpu_cycles_including_dispatch_and_end_jumps=3+20*count+3,
        excess_over_nominal_clocks=(last['clock']-first['clock'])-(3+20*count+3),
        d011_periods=periods, trace_events=actual,
        trace_control_all_module_comparison=compare,
        micro_badline_witnesses=micros,
        continuation=continuation_evidence,
        RMW_row_advance=rmw_evidence,
        visible_observations=visual_observations,
        core_CPU_RAM_full_VIC_equal=True,
        whole_machine_equal=compare['all_module_payloads_equal'], exclusions=[],
        scope='One original selected case14 call. Observed trace phases are retained as reported; no physical bus-phase calibration, complete effect pixel oracle, or FPS claim.')
    native['pass'] = native.pop('pass_')
    filename = 'native-raster-evidence-provisional.json' if native['provisional'] else 'native-raster-evidence.json'
    (output / filename).write_text(json.dumps(native, indent=2)+'\n')
    print(f'Native case 14: {count} cells / {len(actual)} exact stores / {last["clock"]-first["clock"]} observed clocks; all control module differences retained.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=ROOT / 'build/research/demo-coder/raster-analysis')
    parser.add_argument('--capture', type=Path, help='Analyze the owner\'s existing case14 trace/control captures.')
    parser.add_argument('--allow-live', action='store_true', help='Write explicitly provisional evidence from existing files only.')
    args = parser.parse_args()
    index_path = ROOT / 'build/research/demo-coder/streams/unpacked-index.json'
    assert sha(index_path.read_bytes()) == INDEX_SHA
    entry = json.loads(index_path.read_text())['files'][46]
    image_path = ROOT / entry['output_path']
    prg = image_path.read_bytes()
    assert prg[:2] == b'\x00\x20' and len(prg[2:]) == 0xa001
    assert sha(prg[2:]) == entry['output_sha256'] == IMAGE_SHA
    mem = bytearray(65536)
    mem[0x2000:0xc001] = prg[2:]
    selector_path = ROOT / 'build/research/demo-coder/selector-analysis/selector-proof.json'
    selector = json.loads(selector_path.read_text())
    assert selector['pass'] and selector['image_sha256'] == IMAGE_SHA
    assert selector['table_entries'] == 50 and selector['raster_cells'] == 1275

    signatures = []

    def original(pc, expected, purpose):
        expected = bytes.fromhex(expected)
        actual = bytes(mem[pc:pc+len(expected)])
        assert actual == expected, f'original-byte mismatch at ${pc:04x}'
        signatures.append(dict(pc=pc, bytes=actual.hex(), purpose=purpose))

    original(0x62b2, 'a9 fb 8d 18 d0 8d 00 dd', 'frame-start selector')
    original(0x62c4, 'ad 04 67 29 07 49 07 09 70 8d 11 d0',
             'initial ECM+BMM+DEN and complemented phase')
    original(0x62d0, 'ad 04 67 49 07 29 07 18 69 2e 8d 12 d0',
             'raster IRQ = 46 + complemented phase')
    original(0x6318, '20 06 67 a9 fb 8d 12 d0 ba 8e 35 63',
             'calibrate, arm raster251, save outer stack pointer')
    original(0x6324, 'a9 36 8d fe ff a9 63 8d ff ff ee 19 d0 58 4c aa 68',
             'nested IRQ escape while selector loop runs')
    original(0x6336, 'ae 35 63 9a 20 60 01 a9 1b 8d 11 d0',
             'discard display-loop stack and leave bitmap mode')
    original(0x6763, 'ce 11 d0 ee 11 d0 60', 'two NMOS read-modify-writes')
    original(0x64ef,
             'a0 07 bd 00 b9 29 3f 9d 00 b9 bd 00 b8 29 3f 9d 00 b8 ca 88 10 ec',
             'eight entries/page lose ECM, descending')
    original(0x6536, '8a 38 e9 08 aa e0 58 b0 ad a2 50 8e 6a 65 a0 07',
             'reveal descending-block limit and final ascending block')
    original(0x6546,
             'bd 00 b9 29 3f 9d 00 b9 bd 00 b8 29 3f 9d 00 b8 e8 88 10 ec',
             'final eight-entry ascending reveal block')
    original(0x6582,
             'a0 03 bd 00 b9 09 70 9d 00 b9 bd 00 b8 09 70 9d 00 b8 ca 88 10 ec',
             'four entries/page gain ECM/BMM/DEN, descending')
    original(0x65c9, '8a 38 e9 04 aa e0 58 b0 ad', 'rehide block limit')
    original(0x68b6, 'ae 12 d0 4c b9 68', 'sample actual raster once, then patched dispatch')
    original(0x69ba, '20 3a 60 ea 4c b9 68', 'repeat without resampling raster')

    continuation = []
    for i, pc in enumerate((0x68bc, 0x68e8, 0x691c, 0x6942, 0x6958, 0x696e, 0x6998)):
        reg = 'Y' if i < 2 else 'A'
        expected = ('bc 00 b9 8c 11 d0 ' if i < 2 else 'bd 00 b9 8d 11 d0 ')
        expected += ('ad 0d b5 8d 00 dd 8d 18 d0 e8' if i == 0 else
                     'ac 0e b5 8c 00 dd 8c 18 d0 e8' if i == 1 else
                     f'ad {0x0d+i:02x} b5 8d 00 dd 8d 18 d0 e8')
        original(pc, expected, f'continuation lane {i}: B900 then prepared selector')
        continuation.append(dict(index=i, pc=pc, d011_store_pc=pc+3,
                                 dd00_store_pc=pc+9, d018_store_pc=pc+12,
                                 d011_source_page=0xb900, d011_source_register=reg,
                                 selector_address=0xb50d+i))

    # These are finite consequences of the original block starts/limits,
    # not simulated native frame counts or a new replay of selector fixtures.
    reveal_starts = list(range(0xfb, 0x58-1, -8))
    reveal = sorted({x-j for x in reveal_starts for j in range(8)} | set(range(0x50, 0x58)))
    rehide_starts = list(range(0xfb, 0x58-1, -4))
    rehide = sorted({x-j for x in rehide_starts for j in range(4)})
    assert reveal == list(range(0x50, 0xfc))
    assert rehide == list(range(0x58, 0xfc))

    archive_path = ROOT / 'build/research/quondam/hardware-source/vice-3.10.tar.gz'
    assert sha(archive_path.read_bytes()) == VICE_SHA
    source_ranges = {
        'src/viciisc/vicii-cycle.c': [(51, 60), (523, 563), (594, 608)],
        'src/viciisc/vicii-fetch.c': [(158, 181), (236, 270)],
        'src/viciisc/vicii-draw-cycle.c': [(133, 142), (200, 210)],
        'src/viciisc/vicii-mem.c': [(145, 155)],
        'src/viciisc/viciitypes.h': [(44, 57)],
        'src/c64/c64cia2.c': [(140, 170), (207, 218)],
        'src/core/viacore.c': [(1952, 1979), (2149, 2153)],
        'src/drive/drivecpu.c': [(543, 572)],
        'src/sid/sid-snapshot.c': [(65, 74), (656, 669)],
        'src/sid/resid.cc': [(363, 378)],
        'src/resid/sid.cc': [(184, 194), (375, 383), (424, 436)],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    sources = []
    with tarfile.open(archive_path) as archive:
        for relative, ranges in source_ranges.items():
            member = 'vice-3.10/' + relative
            data = archive.extractfile(member).read()
            target = args.output / 'hardware-source' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            lines = data.decode().splitlines()
            sources.append(dict(member=member, sha256=sha(data),
                                excerpts=[dict(first=a, last=b,
                                               text='\n'.join(lines[a-1:b])) for a, b in ranges]))

    report = dict(
        pass_=True, evidence_level='original bytes and pinned hardware source; no native result',
        script_sha256=sha(Path(__file__).read_bytes()),
        image=dict(path=str(image_path.relative_to(ROOT)), payload_sha256=IMAGE_SHA,
                   load=0x2000, end_inclusive=0xc000),
        index_sha256=INDEX_SHA,
        reused_selector_proof=dict(path=str(selector_path.relative_to(ROOT)),
                                   sha256=sha(selector_path.read_bytes()),
                                   cases=50, cells=1275, rerun=False),
        vice_archive=dict(path=str(archive_path.relative_to(ROOT)), sha256=VICE_SHA,
                          url='https://downloads.sourceforge.net/project/vice-emu/releases/vice-3.10.tar.gz'),
        hardware_source=sources, original_signatures=signatures,
        continuation=continuation,
        generated_cell=dict(first=0x69c1, end_exclusive=0xb50c, bytes=15,
                            d011_store_offset=3, dd00_store_offset=8,
                            d018_store_offset=11, nominal_cycles=20,
                            endpoint_jump=0x68bc, physical_raster_period_unproved=True),
        reveal=dict(entry=0x64d9, mask=0x3f, descending_starts=reveal_starts,
                    final_ascending_start=0x50, indices=reveal,
                    unique_entries_per_page=len(reveal), polling_yield_count=2),
        rehide=dict(entry=0x656c, mask=0x70, descending_starts=rehide_starts,
                    indices=rehide, unique_entries_per_page=len(rehide), polling_yield_count=6),
        trace_ports=[0xd011, 0xdd00, 0xd018], optional_setup_ports=[0xd012, 0xd016],
        checkpoints=[
            dict(pc=0x6237, role='post-initializer before RTS'),
            dict(pc=0x62ea, role='phase-specific raster IRQ entry'),
            dict(pc=0x6763, role='before DEC D011 / INC D011 pair'),
            dict(pc=0x6769, role='after both RMW instructions, before RTS'),
            dict(pc=0x68b9, role='dispatch; reject self-loop as selected segment'),
            dict(pc=0x68bc, role='after selected routine, before seven continuation cells'),
            dict(pc=0x69be, role='after continuation, before redispatch'),
            dict(pc=0x6336, role='raster251 nested IRQ escape'),
            dict(pc=0x633f, role='before teardown STA D011')],
        snapshot_fields=['raster_line', 'raster_cycle', 'rc', 'vcbase', 'vc', 'vmli',
                         'bad_line', 'allow_bad_lines', 'idle_state', 'regs', 'reg11_delay',
                         'vbuf', 'cbuf', 'gbuf', 'vbank_phi1', 'vborder', 'main_border'],
        predictions=[
            'B800 and B900 YSCROLL equal (X+1)&7 and (X+2)&7 before table mutation; neither proves current raster equality.',
            'At PAL cycle14 (zero-based13), a true bad_line resets RC; at PAL58 (zero-based57), RC7 updates VCBASE before conditional RC increment.',
            'Early repeated badlines can reset RC every line; late badlines can leave the full RC sequence. Measure phases and fetch addresses.',
            'ECM+BMM is black in the pinned draw implementation and ECM also masks the graphics-fetch address with $39FF.',
            'Bitmap fetch is based on VC and RC, not directly the cached character code. Include the selected bank, D018 and shifted source data.',
            'DEC/INC D011 are NMOS RMW instructions; preserve dummy and final writes, and D011 readback raster bit7.',
            'The seven continuation writes and generated cells are interrupted at raster251; a $68BC hit alone is not a complete frame.'],
        scope='No CPU or VICE execution, no physical write-phase measurement, no pixel oracle, no MEGA identity or all-eight-row native proof.')
    report['pass'] = report.pop('pass_')
    (args.output / 'raster-contract.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Stream 46 static raster contract: 7 continuation cells, IRQ lifecycle, RMW pair, reveal/rehide ranges; no native claim.')
    if args.capture:
        native_segment(args.capture.resolve(), args.output.resolve(), mem, selector, args.allow_live)


if __name__ == '__main__':
    main()
