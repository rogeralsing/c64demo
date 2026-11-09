#!/usr/bin/env python3
"""Bind frozen VIC rules to completion deadlines, without executing a CPU."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-execution-20261109/fetch-analysis'
NATIVE = ROOT / 'build/research/aloft-execution-20261109/native-analysis/accepted-02/native-proof.json'
MATH = ROOT / 'build/research/aloft-execution-20261109/cell-analysis/accepted-01/cell-execution-proof.json'
CONTRACT = BASE / 'accepted-01/fetch-contract-proof.json'
CONTRACT_SHA = '8bdb1a96436f66b2ea690b6812c8ef78974923dfb7cd66efa6e4a2d4a20fb565'
FETCH = ROOT / 'research/aloft-execution-20261109/fetch_contract.py'
FETCH_SHA = 'b3f77c3f46e12686e51be148419e996bca6faabff3d255aee5e31a2665fffa1b'
GLYPH = ROOT / 'build/research/aloft-cells-20261109/glyph-analysis/accepted-01/glyph-mapping-proof.json'
GLYPH_SHA = '64d053eefd919df04025e2300efc4630860d6b9fb1b332b78960367b43ed3fc0'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def meta(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def pinned(path, digest):
    raw = path.read_bytes()
    assert sha(raw) == digest, path
    return json.loads(raw)


def export(proof, folder, name):
    rows = [row for row in proof['outputs'] if row.get('name', Path(row.get('path', '')).name) == name]
    assert len(rows) == 1, name
    raw = (folder / name).read_bytes()
    assert len(raw) == rows[0]['bytes'] and sha(raw) == rows[0]['sha256'], name
    return raw


def fieldmap(doc):
    data = doc['fields']
    result = data if isinstance(data, dict) else {row['label']: row for row in data}
    assert set(result) == {'first', 'later'}
    return result


def write(out, name, obj):
    raw = (json.dumps(obj, indent=2, sort_keys=True) + '\n').encode()
    (out / name).write_bytes(raw)
    return dict(name=name, bytes=len(raw), sha256=sha(raw))


def hook_ref(hit):
    return {k: hit[k] for k in ['sequence', 'checkpoint', 'instruction_PC',
        'instruction_hex', 'received_first', 'received_end', 'raw_block_sha256', 'received_stream']}


def derive(initial, model, hooks, codes):
    start = initial['initial_CPU']['clock']
    vic = initial['initial_VIC_context']
    assert (initial['initial_CPU']['pc'], initial['initial_CPU']['line'], initial['initial_CPU']['cycle']) == (0x500, 47, 24)
    assert initial['initial_CPU']['flags'] & 4
    assert vic['model'] == 1 and vic['sprite_dma'] == 0 and vic['regs'][0x15] == 0
    assert (vic['rc'], vic['idle_state'], vic['vc'], vic['vcbase'], vic['vmli']) == (7, 1, 0, 0, 0)
    assert vic['allow_bad_lines'] == vic['bad_line'] == 0
    assert vic['regs'][17] == vic['reg11_delay'] == 0x18 and vic['regs'][24] == 0x10
    assert vic['vbuf'] == codes and vic['cbuf'] == [8] * 40
    assert initial['CPU_port_readbacks']['data_read'] & 4 and initial['CPU_port_readbacks']['data_read'] & 3
    glyph_addresses = {(c << 3) | 7 for c in codes}
    assert len(glyph_addresses) == 40 and len(model['cells']) == 200
    assert all(w['address'] in glyph_addresses | {0xd011} for w in model['predicted_ordered_writes'])
    assert model['native_expected_store_or_endpoint_values_consumed'] is False
    closure = model['source_closure']
    assert closure['all_cells_strictly_source_recognized']
    assert closure['data_stores_disjoint_dispatcher_cells_lookup_and_return_stack']
    assert closure['other_cell_store_is_D011_IO'] and closure['IRQ_disabled_at_entry']
    assert set(closure['data_store_address_union']) == glyph_addresses
    assert model['predicted_before_oracle_artifact_open']
    selected = [h for h in hooks if start <= h['registers']['clock'] <= start + 12606]
    assert all(h['monitored_address'] == 0xd011 for h in selected
        if h['operation'] == 'store' and 0xd000 <= h['monitored_address'] <= 0xd03f)
    assert not any(h['operation'] == 'store' and 0xdd00 <= h['monitored_address'] <= 0xdd03 for h in selected)
    groups = []
    for h in selected:
        if h['monitored_address'] != 0xd011 or h['instruction_hex'] not in ('ee11d0', '8d11d0'):
            continue
        key = h['registers']['clock'], h['instruction_PC']
        if not groups or groups[-1]['key'] != key:
            groups.append(dict(key=key, hooks=[]))
        groups[-1]['hooks'].append(h)
    assert len(groups) == 200
    accesses = model['predicted_D011_accesses']
    domains = initial['independent_D011_read_domains']
    assert len(accesses) == 550 and len(domains) == 175
    used, stored, rows = 0, initial['initial_stored_D011'], []
    for index, group in enumerate(groups):
        predicted = [a for a in accesses if a['call_index'] == index]
        upper, pc = group['key']
        assert len(predicted) in (1, 3)
        assert [(h['operation'], h['instruction_PC']) for h in group['hooks']] == [
            (p['operation'], p['instruction_PC']) for p in predicted]
        if len(predicted) == 3:
            domain = domains[used]
            used += 1
            assert domain['instruction_PC'] == pc and domain['unique_raster_MSB'] == 0
            lower, final_clock = domain['clock_interval_inclusive']
            assert final_clock == upper and domain['post_INC_A_flags_result_and_store_values_excluded']
            assert [p['value'] for p in predicted] == [stored & 127, stored & 127, ((stored & 127) + 1) & 255]
            lower_ref = domain['preceding_STY_rawref']
        else:
            assert predicted[0]['value'] == 0x18 and group['hooks'][0]['instruction_hex'] == '8d11d0'
            previous = next(h for h in reversed(selected) if h['registers']['clock'] < upper and h['instruction_PC'] != pc)
            assert previous['operation'] == 'store' and previous['instruction_hex'].startswith('84')
            assert previous['instruction_PC'] + 4 == pc and previous['registers']['pc'] == pc - 2
            lower, lower_ref = previous['registers']['clock'], hook_ref(previous)
        line, final = upper // 63 % 312, predicted[-1]['value']
        assert lower // 63 == upper // 63 and (lower % 63, upper % 63) == (6, 12)
        assert line == 48 + index and upper == start + 51 + 63 * index
        assert stored & 7 == line & 7 and final & 7 == (line + 1) & 7
        assert stored & 0xf8 == final & 0xf8 == 0x18
        rows.append(dict(call_index=index, line=line, source_old_D011=stored, source_final_D011=final,
            conservative_change_clock_interval=[lower, upper], lower_rawref=lower_ref,
            instruction_hooks=[hook_ref(h) for h in group['hooks']],
            activation_before_any_change=True, final_inequality_before_hardware14_recheck=True,
            exact_physical_bus_clock_not_inferred=True,
            VCBASE_start=(40 * index) & 1023, RC_in_g_window=7, idle_in_g_window=0,
            graphics_requests=40, matrix_fetch_calls=0,
            logical_row7_addresses=[(c << 3) | 7 for c in codes]))
        stored = final
    assert used == 175 and stored == 0x18
    return dict(source_closure=model['source_closure'], lines=rows,
        declared_initial_hardware_input=initial['capture'], expected_cache_codes=codes, expected_cache_colors=[8] * 40,
        total_logical_graphics_requests=8000, total_matrix_fetch_calls=0,
        logical_address_set=sorted(glyph_addresses), logical_g_window_lines=[48, 247],
        first_g_clock=(groups[0]['key'][0] // 63) * 63 + 15,
        last_g_clock=(groups[-1]['key'][0] // 63) * 63 + 54,
        physical_RAM_ROM_mapping_proved=False,
        closure='Typed source footprint plus no unmodeled external NMI/reset/restore/RAM-writing DMA. Completion bounds are not physical bus timestamps.')


def expected_counters(prediction, clock):
    index = clock // 63 - prediction['first_g_clock'] // 63
    hardware = clock % 63 + 1
    assert 0 <= index < 200 and 16 <= hardware <= 55
    count, base = hardware - 15, (40 * index) & 1023
    return dict(rc=7, idle_state=0, vcbase=base, vc=(base + count) & 1023, vmli=count)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-sha', required=True)
    parser.add_argument('--math-sha', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.relative_to(BASE)
    assert not out.exists()
    native, math = pinned(NATIVE, args.native_sha), pinned(MATH, args.math_sha)
    contract, glyph = pinned(CONTRACT, CONTRACT_SHA), pinned(GLYPH, GLYPH_SHA)
    assert all(p['pass_'] for p in [native, math, contract, glyph])
    assert sha(FETCH.read_bytes()) == FETCH_SHA
    schedule = json.loads(export(contract, CONTRACT.parent, 'pal-fetch-schedule.json'))
    assert schedule['model_number'] == 1 and schedule['color_latency'] == 0
    assert sum(r['phi1_fetch_graphics_slot'] for r in schedule['rows']) == 40
    codes = list(export(glyph, GLYPH.parent, 'predicted-matrix-row24.bin'))
    inputs = fieldmap(json.loads(export(native, NATIVE.parent, 'independent-inputs.json')))
    oracle_doc = json.loads(export(native, NATIVE.parent, 'hook-oracles.json'))
    assert oracle_doc['hook_clock_is_instruction_completion_not_bus_clock']
    vsp_queries = [q for q in native['command_audit']['queries'] if q['command'] == 'resourceget "VICIIVSPBug"']
    assert vsp_queries and all('VICIIVSPBug=0' in q['response'] for q in vsp_queries)
    predictions, outputs = {}, []
    out.mkdir(parents=True)
    for label in ['first', 'later']:
        model = json.loads(export(math, MATH.parent, label + '-full-chain-prediction.json'))
        predictions[label] = derive(inputs[label]['input'], model, oracle_doc['all_hooks'], codes)
        outputs.append(write(out, label + '-logical-fetch-prediction.json', predictions[label]))
    # Expected state files exist before reading target VIC counters or cache values.
    contexts = json.loads(export(native, NATIVE.parent, 'machine-context.json'))['captures']
    captures = {c['stem']: c for c in native['captures']}
    comparisons = []
    for label in ['first', 'later']:
        roles, prediction = inputs[label]['roles'], predictions[label]
        for role in ['first_return', 'post_all']:
            stem = roles[role]
            ctx = contexts[stem]
            expected = expected_counters(prediction, ctx['registers']['clock'])
            actual = {key: ctx['VIC'][key] for key in expected}
            assert actual == expected
            assert ctx['VIC']['vbuf'] == codes and ctx['VIC']['cbuf'] == [8] * 40
            comparisons.append(dict(label=label, role=role, capture=captures[stem],
                expected_counters=expected, actual_counters=actual, all40_cache_codes_and_colors_equal=True,
                evaluation_clock_observed_not_independently_CPU_predicted=True))
        assert contexts[roles['after_line']]['registers']['clock'] > prediction['last_g_clock']
    outputs.append(write(out, 'fetch-state-comparisons.json', comparisons))
    first = inputs['first']['roles']
    before, after = [contexts[first[k]] for k in ['pre_inc', 'post_inc']]
    assert (before['VIC']['bad_line'], before['VIC']['idle_state'], before['VIC']['rc']) == (1, 0, 7)
    assert (after['VIC']['bad_line'], after['VIC']['idle_state'], after['VIC']['rc']) == (0, 0, 7)
    assert before['VIC']['regs'][17] == before['VIC']['reg11_delay'] == 0x18
    assert after['VIC']['regs'][17] == after['VIC']['reg11_delay'] == 0x19
    assert after['registers']['cycle'] == 12 < 13
    outputs.append(write(out, 'first-INC-phase-evidence.json', dict(
        before=captures[first['pre_inc']], after=captures[first['post_inc']],
        early_cancellation_before_RC_reset_source_and_phase_bound=True,
        exact_physical_read_dummy_final_bus_clocks_not_bound=True)))
    write(out, 'fetch-binding-proof.json', dict(pass_=True, producer=meta(Path(__file__)),
        inputs=[meta(p) for p in [NATIVE, MATH, CONTRACT, FETCH, GLYPH]], outputs=outputs,
        scope='Two native-bound intervals under source closure: completion deadlines and independent expected D011 values bind cached row7 logical-fetch invariants; no physical fetched-byte or pixel reconstruction.',
        expected_state_files_written_before_target_counter_cache_evaluation=True,
        endpoint_counters_and_actual_store_values_not_prediction_inputs=True,
        declared_inputs='Genuine initial hardware state, independently source-predicted D011 values, observed completion deadlines; endpoint clocks select evaluation phases only.',
        field_count=2, per_field_logical_graphics_requests=8000, per_field_matrix_fetch_calls=0,
        logical_row7_addresses=40, verified_return_counter_cache_states=4,
        first_INC_early_cancellation_bound=True, physical_RAM_mapping_proved=False,
        fetched_bytes_or_pixels_proved=False, cache_origin_or_all_frame_lifetime_proved=False,
        no_CPU_native_or_downloaded_host_execution=True,
        limits=['Declared source closure excludes unmodeled external NMI/reset/restore/RAM-writing DMA.',
            'Completion deadlines do not timestamp physical dummy/final writes.',
            'Only logical graphics requests over two line48..247 intervals are derived.',
            'Omitted bank/ROM/cartridge mapping and fetched data values are not reconstructed.',
            'No pixels, all-frame animation, deliveredFPS or separate named layered-scene identity.']))


if __name__ == '__main__':
    main()
