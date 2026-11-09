#!/usr/bin/env python3
"""Finite source-bound VIC counter/address contracts; no CPU or pixel execution."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parents[2]
BASE = Path('build/research/aloft-execution-20261109/fetch-analysis')
SOURCE = BASE / 'source-01/source.json'
SOURCE_SHA = '5019d2a77259490e839756a55b94274b0e651a93524824d72faaf85e008e3471'
GLYPH = Path('build/research/aloft-cells-20261109/glyph-analysis/accepted-01/glyph-mapping-proof.json')
GLYPH_SHA = '64d053eefd919df04025e2300efc4630860d6b9fb1b332b78960367b43ed3fc0'
CONTEXT = Path('build/research/aloft-cells-20261109/context-analysis/accepted-01/context-proof.json')
CONTEXT_SHA = '3610d8f46d722667f8d25f4f8976b363afc2c3c632c450f39d8d88d751d7e95e'
PRIMARY = Path('build/research/aloft-cells-20261109/primary-analysis/accepted-01/primary-reading-proof.json')
PRIMARY_SHA = '4fd7cedb1ce4325a6adc0c406406f4a2f6a2cc65ccb7c8ef735d21c02344ed04'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def meta(path):
    raw = (ROOT / path).read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=sha(raw))


def checked(path, digest):
    raw = (ROOT / path).read_bytes()
    assert sha(raw) == digest, path
    return raw


def write(output, name, obj):
    raw = (json.dumps(obj, indent=2, sort_keys=True) + '\n').encode()
    (output / name).write_bytes(raw)
    return dict(name=name, bytes=len(raw), sha256=sha(raw))


def fields(line):
    """Split a guarded C initializer at top-level commas, never evaluate C."""
    line = line.strip().removeprefix('{').removesuffix(',').removesuffix('}')
    parts, depth, first = [], 0, 0
    for i, char in enumerate(line):
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
            assert depth >= 0
        elif char == ',' and depth == 0:
            parts.append(line[first:i].strip())
            first = i + 1
    assert depth == 0
    parts.append(line[first:].strip())
    assert len(parts) == 6, parts
    return parts


def pal_schedule(text):
    block = text.split('static const struct ViciiCycle cycle_tab_pal[] = {', 1)[1].split('};', 1)[0]
    halves = {}
    for line in block.splitlines():
        if not line.strip():
            continue
        values = fields(line)
        match = re.fullmatch(r'Phi([12])\((\d+)\)', values[0])
        assert match
        phase, cycle = map(int, match.groups())
        assert (cycle, phase) not in halves
        halves[(cycle, phase)] = values
    assert len(halves) == 126
    rows = []
    for cycle in range(1, 64):
        first, second = halves[(cycle, 1)], halves[(cycle, 2)]
        rows.append(dict(hardware_cycle=cycle, snapshot_zero_based_cycle=cycle - 1,
            phi1=first, phi2=second,
            phi1_fetch_graphics_slot=(first[3] == 'FetchG'),
            phi2_matrix_opportunity=(second[3] == 'FetchC'),
            update_VC=('UpdateVc' in first[5] or 'UpdateVc' in second[5]),
            update_RC=('UpdateRc' in first[5] or 'UpdateRc' in second[5])))
    assert [r['hardware_cycle'] for r in rows if r['phi1_fetch_graphics_slot']] == list(range(16, 56))
    assert [r['hardware_cycle'] for r in rows if r['phi2_matrix_opportunity']] == list(range(15, 55))
    assert [r['hardware_cycle'] for r in rows if r['update_VC']] == [14]
    assert [r['hardware_cycle'] for r in rows if r['update_RC']] == [58]
    return rows


def phi1_request_8565(state, schedule, code):
    """Address/counter fragment at phi1; physical bank/data/pixels are external."""
    result = dict(state)
    if not schedule['phi1_fetch_graphics_slot']:
        return result, None
    mode = state['reg11_delay']
    if state['idle_state']:
        return result, dict(kind='idle_graphics', logical_phi1_address=0x39ff if mode & 0x40 else 0x3fff)
    assert 0 <= state['vmli'] < 40 and 0 <= code <= 255
    assert 0 <= state['rc'] < 8 and 0 <= state['vc'] < 1024
    if mode & 0x20:
        address = (state['vc'] << 3) | state['rc']
        address |= (state['d018'] & 8) << 10
    else:
        address = (code << 3) | state['rc']
        address |= (state['d018'] & 14) << 10
    if mode & 0x40:
        address &= 0x39ff
    result['vmli'] += 1
    result['vc'] = (result['vc'] + 1) & 1023
    return result, dict(kind='graphics', logical_phi1_address=address,
                        cache_index=state['vmli'], cached_code=code, row=state['rc'])


def graphics_control_fragment(state, schedule, raster_line):
    """Only cycle.c521..564+matrix gate; caller binds phase and line handling."""
    result = dict(state)
    assert 0 <= raster_line <= 511
    assert state['ysmooth'] == (state['d011'] & 7)
    vsp_may_crash = not state['bad_line'] and bool(state['idle_state'])
    if raster_line == 0x30 and not result['allow_bad_lines']:
        result['allow_bad_lines'] = int(bool(state['d011'] & 0x10))
    if result['allow_bad_lines']:
        result['bad_line'] = int((raster_line & 7) == state['ysmooth'])
        if result['bad_line']:
            result['idle_state'] = 0
    vsp_candidate = bool(result['bad_line'] and vsp_may_crash
        and 16 <= schedule['hardware_cycle'] < 55)
    if schedule['update_VC']:
        result['vc'] = result['vcbase']
        result['vmli'] = 0
        if result['bad_line']:
            result['rc'] = 0
    if schedule['update_RC']:
        if result['rc'] == 7:
            result['idle_state'] = 1
            result['vcbase'] = result['vc']
        if not result['idle_state'] or result['bad_line']:
            result['rc'] = (result['rc'] + 1) & 7
            result['idle_state'] = 0
    return result, dict(matrix_fetch_function_called=bool(
        result['bad_line'] and schedule['phi2_matrix_opportunity']),
        VSP_corruption_handler_condition=vsp_candidate)


def early_cancel_example(seed, schedule, codes, cancel_visible_stage):
    """Visibility at a VIC logic stage is declared; no CPU write clock is inferred."""
    state = dict(seed)
    trace, requests, matrix_calls = [], [], 0
    for slot in schedule:
        code = codes[state['vmli']] if state['vmli'] < 40 else 0
        state, request = phi1_request_8565(state, slot, code)
        if slot['hardware_cycle'] == cancel_visible_stage:
            state['d011'] = 0x19
            state['ysmooth'] = 1
        state, event = graphics_control_fragment(state, slot, 0x60)
        matrix_calls += int(event['matrix_fetch_function_called'])
        assert not event['VSP_corruption_handler_condition']
        # End-of-graphics-logic one-cycle mode latch, cycle.c608; not a CPU action.
        state['reg11_delay'] = state['d011']
        if request and request['kind'] == 'graphics':
            requests.append(request)
        trace.append(dict(hardware_cycle=slot['hardware_cycle'], phi1_request=request,
                          after_graphics_control=state, events=event))
    return dict(cancel_visible_to_graphics_control_at_hardware=cancel_visible_stage,
                CPU_write_clock_not_specified=True, phase_rows=trace,
                graphics_requests=requests, matrix_fetch_calls=matrix_calls, final_state=state)


def anchor(text, first, last, required):
    fragment = ''.join(text.splitlines(keepends=True)[first - 1:last])
    assert all(term in fragment for term in required), (first, required)
    return dict(first_line=first, last_line=last, sha256=sha(fragment.encode()),
                required_fragments=required)


def produce(output):
    output.relative_to(ROOT / BASE)
    assert not output.exists()
    source = json.loads(checked(SOURCE, SOURCE_SHA))
    archive = source['archive']
    checked(Path(archive['path']), archive['sha256'])
    texts, sources = {}, [meta(SOURCE), archive]
    # Byte comparison to original tar members is independent of copied-file metadata.
    with tarfile.open(ROOT / archive['path']) as tar:
        for row in source['members']:
            raw = checked(Path(row['path']), row['sha256'])
            assert len(raw) == row['bytes']
            assert tar.extractfile(row['member']).read() == raw
            texts[Path(row['member']).name] = raw.decode()
            sources.append(meta(Path(row['path'])))
    glyph = json.loads(checked(GLYPH, GLYPH_SHA))
    context = json.loads(checked(CONTEXT, CONTEXT_SHA))
    primary = json.loads(checked(PRIMARY, PRIMARY_SHA))
    assert glyph['pass_'] and context['pass_'] and primary['pass_']
    assert glyph['mode_and_RAM_charset_interpretation_is_conditional']
    sources += [meta(GLYPH), meta(CONTEXT), meta(PRIMARY)]
    matrix_row = next(row for row in glyph['outputs'] if row['name'] == 'predicted-matrix-row24.bin')
    matrix_path = GLYPH.parent / matrix_row['name']
    codes = list(checked(matrix_path, matrix_row['sha256']))
    assert len(codes) == 40 and len(set(codes)) == 40
    assert set(codes) == set(range(32)) | set(range(0xf0, 0xf8))
    sources.append(meta(matrix_path))
    color_row = next(row for row in glyph['outputs'] if row['name'] == 'predicted-color-row24.bin')
    color_path = GLYPH.parent / color_row['name']
    colors = list(checked(color_path, color_row['sha256']))
    assert colors == [8] * 40
    sources.append(meta(color_path))
    model_text = texts['vicii-chip-model.c']
    anchors = {
        'vicii.h': [anchor(texts['vicii.h'], 57, 63, ['VICII_MODEL_8565    1'])],
        'vicii-chip-model.c': [anchor(model_text, 250, 267,
            ['chip_model_mos8565', '0,               /* color latency */']),
            anchor(model_text, 815, 824, ['case VICII_MODEL_8565:', '&chip_model_mos8565'])],
        'vicii-cycle.c': [anchor(texts['vicii-cycle.c'], 51, 60, ['vicii.idle_state = 0;']),
            anchor(texts['vicii-cycle.c'], 130, 141, ['if (!vicii.idle_state)', 'vicii_fetch_idle_gfx()']),
            anchor(texts['vicii-cycle.c'], 202, 218, ['vicii.allow_bad_lines = 0;', 'vicii.vcbase = 0;']),
            anchor(texts['vicii-cycle.c'], 228, 241, ['vicii.bad_line = 0;']),
            anchor(texts['vicii-cycle.c'], 382, 411, ['next_vicii_cycle();', 'cycle_phi1_fetch', 'vicii_draw_cycle();']),
            anchor(texts['vicii-cycle.c'], 521, 564, ['vsp_may_crash', 'check_badline();', 'vicii.rc = 0;', 'vicii.vcbase = vicii.vc;']),
            anchor(texts['vicii-cycle.c'], 594, 608, ['vicii_fetch_matrix();', 'vicii.reg11_delay = vicii.regs[0x11];'])],
        'vicii-fetch.c': [anchor(texts['vicii-fetch.c'], 50, 100, ['vicii.vbank_phi1', 'vicii.vaddr_mask_phi1', 'export.ultimax_phi1']),
            anchor(texts['vicii-fetch.c'], 158, 201, ['vicii.vbuf[vicii.vmli] << 3', 'vicii.cbuf[vicii.vmli] = mem_color_ram_vicii[vicii.vc]']),
            anchor(texts['vicii-fetch.c'], 213, 272, ['reg11 = vicii.reg11_delay;', 'g_fetch_addr(vicii.reg11_delay)', 'vicii.vmli++;'])],
        'vicii-snapshot.c': [anchor(texts['vicii-snapshot.c'], 83, 127,
            ['ram_base_phi[12] and vaddr_* updated from elsewhere', 'vbank_phi[12] updated from elsewhere', 'vicii.reg11_delay'])],
        'vicii-resources.c': [anchor(texts['vicii-resources.c'], 165, 167, ['"VICIIVSPBug"'])],
    }
    schedule = pal_schedule(model_text)
    seed = dict(rc=7, idle_state=1, vc=0, vcbase=0, vmli=0, bad_line=0,
                allow_bad_lines=1, d011=0x18, ysmooth=0, reg11_delay=0x18, d018=0x10)
    rc_cases = []
    for rc in range(8):
        for idle in range(2):
            for bad in range(2):
                # lineLSB0 equals ysmooth0 iff explicitly allowed; preserve bad when disallowed.
                state = dict(seed, rc=rc, idle_state=idle, bad_line=bad, allow_bad_lines=0, vc=1023)
                after, events = graphics_control_fragment(state, schedule[57], 0x61)
                expected_rc = (rc + 1) & 7 if bad or (not idle and rc != 7) else rc
                assert after['rc'] == expected_rc
                assert after['idle_state'] == (1 if rc == 7 and not bad else idle if idle and not bad else 0)
                assert after['vcbase'] == (1023 if rc == 7 else 0)
                rc_cases.append(dict(before=state, after=after, events=events))
    # A declared sufficient schedule, not an execution trace or fitted native state.
    state, activation = graphics_control_fragment(seed, schedule[58], 0x60)
    assert state['rc'] == 7 and state['idle_state'] == 0
    assert not activation['matrix_fetch_function_called'] and not activation['VSP_corruption_handler_condition']
    state['bad_line'] = 0  # start-of-line helper, before the next line's graphics fragment.
    trace, requests, matrix_calls = [], [], 0
    for slot in schedule:
        code = codes[state['vmli']] if state['vmli'] < 40 else 0
        state, request = phi1_request_8565(state, slot, code)
        state, event = graphics_control_fragment(state, slot, 0x61)
        matrix_calls += int(event['matrix_fetch_function_called'])
        assert not event['VSP_corruption_handler_condition']
        if request and request['kind'] == 'graphics':
            requests.append(request)
        trace.append(dict(hardware_cycle=slot['hardware_cycle'], phi1_request=request,
                          after_graphics_control=state, events=event))
    assert len(requests) == 40 and matrix_calls == 0
    assert [r['logical_phi1_address'] for r in requests] == [(c << 3) | 7 for c in codes]
    assert (state['rc'], state['idle_state'], state['vcbase'], state['vc']) == (7, 1, 40, 40)
    assert len({r['logical_phi1_address'] for r in requests}) == 40
    early_cases = []
    for visibility in range(2, 15):
        example = early_cancel_example(seed, schedule, codes, visibility)
        assert example['matrix_fetch_calls'] == 0
        assert [r['row'] for r in example['graphics_requests']] == [7] * 40
        assert [r['logical_phi1_address'] for r in example['graphics_requests']] == [(c << 3) | 7 for c in codes]
        early_cases.append(dict(visibility_stage=visibility, graphics_requests=40,
            all_rows7=True, matrix_fetch_calls=0))
    early = early_cancel_example(seed, schedule, codes, 14)
    never_active = early_cancel_example(seed, schedule, codes, 1)
    too_late = early_cancel_example(seed, schedule, codes, 15)
    assert never_active['graphics_requests'] == []
    assert [r['row'] for r in too_late['graphics_requests']] == [0] * 40
    address_cases = []
    for code in range(256):
        for rc in range(8):
            active = dict(seed, idle_state=0, rc=rc)
            result, request = phi1_request_8565(active, schedule[15], code)
            assert request['logical_phi1_address'] == (code << 3) | rc
            assert result['vc'] == 1 and result['vmli'] == 1
            address_cases.append(request['logical_phi1_address'])
    idle_result, idle_request = phi1_request_8565(seed, schedule[15], codes[0])
    assert idle_request['logical_phi1_address'] == 0x3fff and idle_result == seed
    required_fields = ['model', 'raster_line', 'raster_cycle', 'cycle_flags', 'start_of_frame',
        'regs', 'ysmooth', 'allow_bad_lines', 'bad_line', 'idle_state', 'rc', 'vc', 'vcbase', 'vmli',
        'vbuf', 'cbuf', 'gbuf', 'last_read_phi1', 'last_bus_phi2', 'reg11_delay', 'prefetch_cycles',
        'sprite_dma', 'vborder', 'set_vborder', 'main_border']
    output.mkdir(parents=True)
    outputs = [write(output, 'primary-fetch-source.json', dict(sources=sources, anchors=anchors)),
        write(output, 'pal-fetch-schedule.json', dict(model_number=1, model='MOS8565',
            cycles_per_line=63, lines_per_frame=312, color_latency=0, rows=schedule)),
        write(output, 'finite-counter-rules.json', dict(RC58_cases=rc_cases,
            normal_charset_base0_address_cases=2048,
            normal_charset_base0_address_order_sha256=sha(bytes(v >> 8 for v in address_cases) + bytes(v & 255 for v in address_cases)),
            idle_RC7_example=dict(before=seed, request=idle_request, after=idle_result))),
        write(output, 'conditional-row7-schedule.json', dict(
            scope='Hypothetical afterRC58 activation schedule; no native input or timing observation.',
            seed_before_hardware59_on_line60=seed,
            activation_after_hardware58=activation, next_line=0x61,
            source_predicted_cached_codes=codes, cached_colors_assumed=colors,
            phase_rows=trace, graphics_requests=requests,
            matrix_fetch_calls=0, cache_content_unchanged_if_no_other_cache_writer=True,
            physical_RAM_bank0_charset0_interpretation_conditional=True)),
        write(output, 'conditional-early-cancel.json', dict(
            scope='Hypothetical equality-then-cancel schedule, not an Aloft bus-time or effect label.',
            source_predicted_cached_codes=codes, seed_before_first_line_logic=seed,
            sufficient_visibility_cases=early_cases, last_sufficient_stage_example=early,
            negative_boundaries=dict(cancel_before_activation=never_active,
                                     cancel_after_RC_reset=too_late),
            visibility_stage_is_not_CPU_bus_write_cycle=True,
            actual_native_snapshots_or_hook_values_not_inputs=True)),
        write(output, 'capture-contract.json', dict(required_snapshot_core_fields=required_fields,
            useful_natural_CPU_boundaries=['genuine pre0500 before JSR', 'first actual cell entry',
                'first cell return0503', 'post0500 F0B1'],
            useful_VIC_boundaries=dict(VC_reload=dict(hardware=14, zero_based=13),
                first_g_slot=dict(hardware=16, zero_based=15),
                last_matrix_opportunity=dict(hardware=54, zero_based=53),
                RC_update=dict(hardware=58, zero_based=57)),
            observer_requirements=['Bind actual CPU read-raster-MSB domain independently of postINC store values.',
                'Order D011 read/dummy/final accesses and glyph writes with clocks; distinguish monitor post-instruction state.',
                'Watch CPU ports, D018 and CIA2 bank/DDRA changes; bind VICIIVSPBug resource.',
                'Do not call a nearest CPU boundary an exact half-cycle snapshot.'],
            omitted_VSF_mapping_fields=['vbank_phi1', 'vbank_phi2', 'ram_base_phi1/2',
                'vaddr_mask_phi1/2', 'vaddr_offset_phi1/2', 'vaddr_chargen_mask/value', 'export.ultimax_phi1/2'],
            physical_fetch_requires='Independently bound mapping/cartridge/bank history in addition to logical addresses.',
            cache_endpoint_equality_is_not_origin_or_lifetime_proof=True,
            current_tick_phi1_precedes_badline_RC_and_matrix_logic=True))]
    proof = dict(pass_=True, producer=meta(Path(__file__).resolve().relative_to(ROOT)), inputs=sources,
        scope='Pinned MOS8565 PAL fetch/counter/address fragments and two hypothetical sufficient row7/cache schedules, not a CPU/VIC renderer or actual Aloft timing proof.',
        model_enum_source_bound=1, model_name='MOS8565', color_latency=0,
        source_archive_members_equal_retained_copies=True,
        PAL_phi1_g_slots=40, PAL_phi2_matrix_opportunities=40, RC58_finite_cases=32,
        normal_charset_base0_address_cases=2048, conditional_glyph_row7_addresses=40,
        early_cancel_sufficient_visibility_stage_cases=13,
        early_cancel_negative_activation_and_RC_reset_boundaries=2,
        hypothetical_matrix_fetch_calls=0,
        actual_native_input_or_endpoint_values_used_for_prediction=False,
        actual_native_g_fetch_or_cache_lifetime_match_claim=False,
        FLD_linecrunch_or_named_scene_identity_established=False,
        no_CPU_native_or_downloaded_host_execution=True,
        limits=['Graphics fragment starts after phi1; line/frame handling, BA/prefetch, sprite execution and corruption are not simulated.',
            'The hypothetical schedule uses declared conditions, not inferred instruction timing or fitted native outputs.',
            'Model1 uses delayed mode for fetch addressing; software D011 read and current YSCROLL remain separate.',
            'Logical addresses alone do not bind RAM/ROM, cartridge, GLUE bank transitions or returned bytes.',
            'IdleRC7 requests idle graphics, not the cached-code row7; an endpoint counter does not prove active fetching.',
            'No pixels, framebuffer lifetime, deliveredFPS or whole-field output is modeled.'], outputs=outputs)
    write(output, 'fetch-contract-proof.json', proof)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    produce(args.output.resolve())
