#!/usr/bin/env python3
"""Time-ordered glyph bytes from source stores, not a CPU or pixel replay."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from collections import Counter
import re
import traceback

ROOT = Path(__file__).resolve().parents[2]
NATIVE_SOURCE = 'research/aloft-execution-20261109/native.py'
NATIVE_SOURCE_SHA = '99bea080d4e2fa74f4c3656dfd6084af752e0747247c1ef67e7688c1ec92d967'
PROFILE = 'build/research/aloft-execution-20261109/native-analysis/closed-profile-01.json'
PROFILE_SHA = 'cb077129b7206a748cbc0e562c63ffe7dc0e66778a0cfd3d79cd55b384472fb6'
NATIVE = 'build/research/aloft-execution-20261109/native-analysis/accepted-02'
MATH = 'build/research/aloft-execution-20261109/cell-analysis/accepted-01'
LOGICAL = 'build/research/aloft-execution-20261109/fetch-analysis/binding-accepted-01'
FETCH = 'build/research/aloft-execution-20261109/fetch-analysis/accepted-01'
TAIL = 'build/research/aloft-pixels-20261109/tail-analysis/accepted-01'
STORE_ROUTE = 'build/research/aloft-pixels-20261109/display-analysis/store_route.py'
STORE_ROUTE_SHA = 'bc91e10b48cf7d7228e161b3bd5bb21292b1c592d8e6bcdd802d0a4c2fb43199'
STORE_PROOF = 'build/research/aloft-pixels-20261109/display-analysis/source-route-01/store-route-proof.json'
PHYSICAL = 'build/research/aloft-pixels-20261109/physical-analysis/accepted-01'
PHYSICAL_SOURCE = 'research/aloft-pixels-20261109/physical_fetch.py'
PHYSICAL_SOURCE_SHA = '5dddabd2356cd93698528e14d51090cbc3518c74eee2891b03a8bdb9fefbd433'
FETCH_G_MASK_SOURCE = 'build/research/aloft-execution-20261109/fetch-analysis/source-01/src__viciisc__vicii-chip-model.h'
PINS = {
    NATIVE + '/native-proof.json': '5db9694db276541a5fd2b5cb386e92639e6da2c0d6cd644caf758eb113cc2326',
    MATH + '/cell-execution-proof.json': 'b3bf0ae5e74059bc17b29717174587bb679bfe3701a388dad0f9a3d88b8ebdf5',
    LOGICAL + '/fetch-binding-proof.json': '31efa766ff16b02d04c834ba107c40c868d0124fb4c0ea2e499e5b6f6644916c',
    FETCH + '/fetch-contract-proof.json': '8bdb1a96436f66b2ea690b6812c8ef78974923dfb7cd66efa6e4a2d4a20fb565',
    TAIL + '/tail-guard-proof.json': 'f88ec772bd11d0c6e4669b0541578319cd6c1500e57a4ae8d66e57116c130029',
    STORE_PROOF: '2e7acf05f320399b27759d8811a0c0c074ba47511ac0466418740d65dfbf483a',
    PHYSICAL + '/physical-fetch-proof.json': 'e4e815d4b793cbeb85c693ba6b963d5f0c3e41f7641ab5e36ec0c00a1d805678',
    FETCH_G_MASK_SOURCE: '3aec194e53fcfdc4392d109379d0aa37e6b1404836eb6dc07bf2c73ad3e203ce',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pinned(path, digest):
    raw = (ROOT / path).read_bytes()
    if sha(raw) != digest:
        raise ValueError('changed pinned input: ' + path)
    return raw


def passive_module(path, digest, name):
    pinned(path, digest)
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def identity(path):
    raw = (ROOT / path).read_bytes()
    return {'path': path, 'bytes': len(raw), 'sha256': sha(raw)}


def exported(folder, proof, name):
    row = next(r for r in proof['outputs'] if r['name'] == name)
    path = folder + '/' + name
    raw = pinned(path, row['sha256'])
    if len(raw) != row['bytes']:
        raise ValueError('changed receipt output size')
    return raw


def emit_json(out, name, obj):
    raw = (json.dumps(obj, indent=2) + '\n').encode()
    (out / name).write_bytes(raw)
    return {'name': name, 'bytes': len(raw), 'sha256': sha(raw)}


def timing_only_raw_projection():
    """Reuse the frozen raw-wire parser without its snapshot/oracle stages.

    No RAM/VSF state decoder is called. Raw hook registers are reduced to PC
    and completion clock; A/X/Y, values and monitored addresses are discarded.
    Thus target endpoint GBUF/framebuffers are never opened for this projection.
    """
    native = passive_module(NATIVE_SOURCE, NATIVE_SOURCE_SHA, 'frozen_glyph_raw_custody')
    profile = json.loads(pinned(PROFILE, PROFILE_SHA))
    path = ROOT / profile['case_relative']
    wire, case, adapter = native.audit_wire(profile, path)
    generations = native.checkpoint_generations(case)
    hits = native.trace_hooks(case, wire, generations, captures=[])
    selected = [g for g in generations if g['kind'] == 'TRACE'
                and g['operation'].lower() == 'trace store'
                and (g['first'], g['last']) in ((0, 255), (0x787, 0x7bf))]
    if len(selected) != 2:
        raise ValueError('declared glyph-watch generations changed')
    keys = {(g['id'], g['created_sequence']) for g in selected}
    rows = []
    for hit in hits:
        if (hit['checkpoint'], hit['checkpoint_created_sequence']) not in keys:
            continue
        if hit['operation'] != 'store':
            raise ValueError('unexpected operation in data-store watch')
        rows.append({'instruction_PC': hit['instruction_PC'],
            'instruction_hex': hit['instruction_hex'], 'postPC': hit['registers']['pc'],
            'completion_clock': hit['registers']['clock'],
            'rawref': {key: hit[key] for key in ('sequence', 'checkpoint',
                'checkpoint_created_sequence', 'received_first', 'received_end',
                'raw_block_sha256', 'received_stream')}})
    return {'glyph_store_completion_records': rows,
        'source_watch_generations': [{k: g[k] for k in ('id', 'created_sequence', 'first', 'last')}
                                     for g in selected],
        'wire_startup_adapter': adapter,
        'target_RAM_VSF_GBUF_or_framebuffer_decoded': False,
        'A_X_Y_monitored_address_and_store_values_excluded': True}


def bind_store_bounds(initial, model, logical, raw_timing, store_route):
    start, end = initial['initial_CPU']['clock'], logical['last_g_clock']
    timings = [r for r in raw_timing['glyph_store_completion_records']
               if start <= r['completion_clock'] <= end]
    source = model['predicted_glyph_writes']
    if len(source) != len(timings):
        raise ValueError('all reported data-watch stores do not match source coverage')
    opcode = {'write_screen': 0x8d, 'write_scratch': 0x85,
              'write_state_X': 0x86, 'write_state_Y': 0x84}
    result = []
    for index, (write, time) in enumerate(zip(source, timings)):
        op = opcode[write['kind']]
        address = write['address']
        encoded = bytes([op, address & 255] + ([address >> 8] if op == 0x8d else []))
        if time['instruction_PC'] != write['instruction_PC'] or time['instruction_hex'] != encoded.hex():
            raise ValueError('source-generated store does not match raw instruction/timing order')
        if time['postPC'] != write['instruction_PC'] + len(encoded):
            raise ValueError('raw timing registers are not at instruction completion')
        interval = store_route.direct_store_interval(time['completion_clock'], op, no_clock_diversion=True)
        result.append({**time, 'source_write_ordinal': index,
            'visibility_clock_interval': interval,
            'visibility_convention': 'Conservative x64sc macro interval, not an electrical bus timestamp.'})
    return result


def stage_rows(initial_glyphs, source_stores, timed_stores, logical, fetch_slots,
               mapping, resolve_phi1):
    """Join independent time bounds to source-predicted byte assignments.

    Stores can affect a request only if their full visibility interval precedes
    it. Any overlapping store/fetch interval rejects rather than guessing order.
    Address resolution is an independently source-bound physical ABI.
    """
    if len(source_stores) != len(timed_stores):
        raise ValueError('source-store and timing-record counts differ')
    if fetch_slots != list(range(15, 55)) or len(logical['lines']) != 200:
        raise ValueError('unsupported source-bound fetch schedule')
    state = dict(initial_glyphs)
    latest_source_write = {address: None for address in state}
    if len(state) != 40:
        raise ValueError('complete genuine forty-byte glyph prestate required')
    previous_end = None
    for source, time in zip(source_stores, timed_stores):
        if source['instruction_PC'] != time['instruction_PC']:
            raise ValueError('source/timing program order disagrees')
        lo, hi = time['visibility_clock_interval']
        if not lo <= hi or previous_end is not None and lo <= previous_end:
            raise ValueError('ambiguous/out-of-order store visibility intervals')
        previous_end = hi
        if source['address'] not in state:
            raise ValueError('source store escapes initial physical glyph domain')
    cursor, rows, byte_stream = 0, [], bytearray()
    for line in logical['lines']:
        index = line['call_index']
        line_base = line['conservative_change_clock_interval'][1] // 63 * 63
        if line_base // 63 % 312 != line['line'] or line['RC_in_g_window'] != 7:
            raise ValueError('logical row/phase domain changed')
        if line['idle_in_g_window'] != 0 or line['graphics_requests'] != 40 or line['matrix_fetch_calls'] != 0:
            raise ValueError('unproved active graphics/cache lifetime')
        addresses = line['logical_row7_addresses']
        if len(addresses) != 40 or len(set(addresses)) != 40:
            raise ValueError('unsupported cached-code alias domain')
        values, physical, clocks, counts, provenance = [], [], [], [], []
        for slot, address in zip(fetch_slots, addresses):
            clock = line_base + slot
            while cursor < len(source_stores) and timed_stores[cursor]['visibility_clock_interval'][1] < clock:
                write = source_stores[cursor]
                state[write['address']] = write['value']
                latest_source_write[write['address']] = cursor
                cursor += 1
            if cursor < len(timed_stores):
                lo, hi = timed_stores[cursor]['visibility_clock_interval']
                if lo <= clock <= hi:
                    raise ValueError('store/fetch order is not independently fixed')
            result = resolve_phi1(address, mapping)
            if result['region'] != 'mainRAM' or result['cpu_port_overlay'] is not False:
                raise ValueError('logical request is not source-bound ordinary VIC RAM')
            resolved = result['physical_address']
            if resolved not in state:
                raise ValueError('physical fetched byte lacks genuine initial/source-written provenance')
            clocks.append(clock); physical.append(resolved); values.append(state[resolved]); counts.append(cursor)
            provenance.append(latest_source_write[resolved])
        if len(set(counts)) != 1:
            raise ValueError('stores interleave the forty-request row')
        this_stores = [{**source, **time} for source, time in zip(source_stores, timed_stores)
                       if source['call_index'] == index]
        next_time = timed_stores[cursor]['visibility_clock_interval'][0] if cursor < len(timed_stores) else None
        if next_time is not None and next_time <= clocks[-1]:
            raise ValueError('next source store can overlap the current row')
        rows.append({'call_index': index, 'raster_line': line['line'],
            'absolute_line_number': line_base // 63, 'fetch_clocks': clocks,
            'logical_glyph_addresses': addresses, 'physical_addresses': physical,
            'fetched_bytes': values, 'latest_source_write_ordinals': provenance,
            'current_cell_store_bounds': this_stores,
            'applied_source_store_count_first': counts[0], 'applied_source_store_count_last': counts[-1],
            'next_store_earliest_clock': next_time,
            'every_possible_store_fetch_order_fixed': True})
        byte_stream.extend(values)
    if cursor != len(source_stores) or len(byte_stream) != 8000:
        raise ValueError('incomplete source-store or fetched-byte coverage')
    return rows, bytes(byte_stream)


def prepare(out):
    """Produce both complete streams before opening any fetched-byte oracle."""
    out.resolve().relative_to(ROOT / 'build/research/aloft-pixels-20261109/glyph-analysis')
    out.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).read_bytes()
    (out / 'glyph_stream.checked.py').write_bytes(source)
    files = [{'name': 'glyph_stream.checked.py', 'bytes': len(source), 'sha256': sha(source)}]
    inputs, receipts = [], {}
    for path, digest in PINS.items():
        raw = pinned(path, digest)
        inputs.append(identity(path))
        if path.endswith('.json'):
            receipts[path] = json.loads(raw)
            if receipts[path]['pass_'] is not True:
                raise ValueError('failed dependency receipt')
    native = receipts[NATIVE + '/native-proof.json']
    math = receipts[MATH + '/cell-execution-proof.json']
    fetch = receipts[FETCH + '/fetch-contract-proof.json']
    logical_receipt = receipts[LOGICAL + '/fetch-binding-proof.json']
    tail = receipts[TAIL + '/tail-guard-proof.json']
    physical = receipts[PHYSICAL + '/physical-fetch-proof.json']
    schedule = json.loads(exported(FETCH, fetch, 'pal-fetch-schedule.json'))
    if (schedule['model_number'], schedule['color_latency'], schedule['cycles_per_line'], schedule['lines_per_frame']) != (1, 0, 63, 312):
        raise ValueError('unadmitted hardware scheduling model')
    slots = [r['snapshot_zero_based_cycle'] for r in schedule['rows'] if r['phi1_fetch_graphics_slot']]
    initial = json.loads(exported(NATIVE, native, 'independent-inputs.json'))
    if initial['no_post_state_or_store_values_as_model_inputs'] is not True:
        raise ValueError('initial-state separation changed')
    tail_prediction = json.loads(exported(TAIL, tail, 'tail-predictions.json'))
    mapping = json.loads(exported(PHYSICAL, physical, 'mapping-abi.json'))
    route = passive_module(STORE_ROUTE, STORE_ROUTE_SHA, 'frozen_glyph_store_visibility')
    resolver = passive_module(PHYSICAL_SOURCE, PHYSICAL_SOURCE_SHA, 'frozen_glyph_physical_mapping')
    inputs.extend([identity(STORE_ROUTE), identity(PHYSICAL_SOURCE), identity(NATIVE_SOURCE), identity(PROFILE)])
    timing = timing_only_raw_projection()
    files.append(emit_json(out, 'timing-only-source-inputs.json', timing))
    fields = []
    for field in initial['fields']:
        label, entry = field['label'], field['input']
        model = json.loads(exported(MATH, math, label + '-full-chain-prediction.json'))
        logical = json.loads(exported(LOGICAL, logical_receipt, label + '-logical-fetch-prediction.json'))
        mapfield = next(f for f in mapping['fields'] if f['label'] == label)
        tailfield = next(f for f in tail_prediction['fields'] if f['label'] == label)
        tailcheck = next(f for f in tail['comparisons'] if f['label'] == label)
        if tailfield['last_logical_graphics_clock'] != logical['last_g_clock']:
            raise ValueError('tail protection does not cover this fetch schedule')
        if not tailcheck['last_graphics_precedes_wait_fallthrough'] or not tailcheck['no_reported_hook_during_wait']:
            raise ValueError('final row lacks write-free tail protection')
        if not mapfield['native_final_RAM_bytes_not_used'] or mapfield['mapping_changes_in_interval']:
            raise ValueError('physical mapping is not a continuous source-bound input')
        if not mapfield['admitted_glyph_CPU_stores_alias_same_mem_ram']:
            raise ValueError('CPU glyph store and VIC phi1 RAM objects differ')
        low, high = mapfield['valid_clock_interval']
        if not low <= logical['first_g_clock'] <= logical['last_g_clock'] <= high:
            raise ValueError('physical mapping lifetime misses g-fetch requests')
        if model['source_closure'] != logical['source_closure']:
            raise ValueError('logical request proof assumes a different executable closure')
        times = bind_store_bounds(entry, model, logical, timing, route)
        glyphs = {r['address']: r['value'] for r in entry['all40_initial_glyph_values']}
        rows, raw = stage_rows(glyphs, model['predicted_glyph_writes'], times,
            logical, slots, mapfield['mapping'], resolver.resolve_phi1)
        if [r['raster_line'] for r in rows] != list(range(48, 248)):
            raise ValueError('bounded row domain changed')
        patterns = Counter(tuple(s['completion_clock'] - row['absolute_line_number'] * 63
                                  for s in row['current_cell_store_bounds']) for row in rows)
        if any(len(r['current_cell_store_bounds']) != 4 for r in rows):
            raise ValueError('source chain is not four-store per row')
        gaps_before = [r['fetch_clocks'][0] - max(s['visibility_clock_interval'][1]
                       for s in r['current_cell_store_bounds']) for r in rows]
        gaps_after = [r['next_store_earliest_clock'] - r['fetch_clocks'][-1]
                      for r in rows if r['next_store_earliest_clock'] is not None]
        first_boundary = times[0]['visibility_clock_interval']
        partial = {'raster_line': entry['initial_CPU']['line'],
            'genuine_initial_clock': entry['initial_CPU']['clock'],
            'genuine_initial_cycle': entry['initial_CPU']['cycle'],
            'genuine_initial_idle_state': entry['initial_VIC_context']['idle_state'],
            'included_in_200_row_glyph_prediction': False,
            'earlier_phi1_reads_and_pixels_not_reconstructed': True,
            'first_glyph_store_visibility_interval': first_boundary,
            'first_glyph_store_after_previous_scheduled_g_window':
                first_boundary[0] > entry['initial_CPU']['clock'] // 63 * 63 + slots[-1]}
        prediction = {'label': label, 'scope': 'Two source-bound200row temporal glyph streams, not a stored8000byte bitmap.',
            'input_capture': entry['capture'], 'source_closure': model['source_closure'],
            'mapping': mapfield, 'store_clock_contract': identity(STORE_PROOF),
            'first_g_clock': logical['first_g_clock'], 'last_g_clock': logical['last_g_clock'],
            'initial_partial_line_boundary': partial,
            'completion_offsets_relative_to_fetch_line': [
                {'offsets': list(pattern), 'rows': count} for pattern, count in sorted(patterns.items())],
            'minimum_store_completion_before_first_fetch_cycles': min(gaps_before),
            'minimum_next_store_visibility_after_last_fetch_cycles': min(gaps_after),
            'final_row_tail_guard': tailfield,
            'all8000_store_fetch_orders_fixed': True, 'rows': rows,
            'no_native_store_values_fetched_bytes_or_framebuffer_inputs': True}
        rowref = emit_json(out, label + '-glyph-rows.json', prediction)
        name = label + '-glyph-fetch-bytes.bin'
        (out / name).write_bytes(raw)
        byteref = {'name': name, 'bytes': len(raw), 'sha256': sha(raw)}
        files.extend([rowref, byteref])
        fields.append({'label': label, 'row_prediction': rowref, 'byte_stream': byteref,
            'prediction': prediction, 'roles': field['roles']})
    return native, fields, files, inputs


def produce(out):
    native, fields, files, inputs = prepare(out)
    # Both complete8000byte predictions exist before fetched-byte oracles open.
    contexts = json.loads(exported(NATIVE, native, 'machine-context.json'))['captures']
    captures = {c['stem']: c for c in native['captures']}
    header = pinned(FETCH_G_MASK_SOURCE, PINS[FETCH_G_MASK_SOURCE]).decode()
    if not re.search(r'#define\s+PHI1_TYPE_M\s+0x00000e00\b', header, re.I) or not re.search(r'#define\s+PHI1_FETCH_G\s+0x00000400\b', header, re.I):
        raise ValueError('source graphics-phase mask missing')
    comparisons, summaries = [], []
    for field in fields:
        prediction, rows = field['prediction'], field['prediction']['rows']
        for role in ('first_return', 'post_all'):
            stem = field['roles'][role]
            context = contexts[stem]
            cpu, vic = context['registers'], context['VIC']
            if (cpu['line'], cpu['cycle']) != (vic['raster_line'], vic['raster_cycle']):
                raise ValueError('sample CPU/VIC beam phases disagree')
            if cpu['clock'] // 63 % 312 != cpu['line'] or cpu['clock'] % 63 != cpu['cycle']:
                raise ValueError('sample clock/beam relation changed')
            if vic['cycle_flags'] & 0xe00 != 0x400 or vic['idle_state'] != 0 or vic['rc'] != 7:
                raise ValueError('GBUF sample is not independently phase-bound active FetchG')
            index, slot = cpu['line'] - rows[0]['raster_line'], cpu['cycle'] - 15
            if not 0 <= index < 200 or not 0 <= slot < 40:
                raise ValueError('sample outside predicted glyph stream')
            row = rows[index]
            if row['fetch_clocks'][slot] != cpu['clock']:
                raise ValueError('latest GBUF slot does not share the sample phase')
            base = 40 * index & 1023
            if (vic['vcbase'], vic['vc'], vic['vmli']) != (base, (base + slot + 1) & 1023, slot + 1):
                raise ValueError('source fetch-slot counter sample differs')
            expected = row['fetched_bytes'][slot]
            if (vic['gbuf'], vic['last_read_phi1']) != (expected, expected):
                raise ValueError('native GBUF/lastphi1 differs from independently staged byte')
            comparisons.append({'label': field['label'], 'role': role, 'capture': captures[stem],
                'raster_line': cpu['line'], 'zero_cycle': cpu['cycle'], 'slot': slot,
                'logical_address': row['logical_glyph_addresses'][slot],
                'physical_address': row['physical_addresses'][slot],
                'predicted_byte': expected, 'native_GBUF': vic['gbuf'],
                'native_last_read_phi1': vic['last_read_phi1'], 'equal': True,
                'oracle_opened_only_after_both_complete_stream_predictions': True})
        summaries.append({'label': field['label'], 'row_prediction': field['row_prediction'],
            'byte_stream': field['byte_stream'], 'rows': 200, 'requests': 8000,
            'completion_offsets_relative_to_fetch_line': prediction['completion_offsets_relative_to_fetch_line'],
            'minimum_store_completion_before_first_fetch_cycles': prediction['minimum_store_completion_before_first_fetch_cycles'],
            'minimum_next_store_visibility_after_last_fetch_cycles': prediction['minimum_next_store_visibility_after_last_fetch_cycles'],
            'partial_initial_line_excluded': True, 'final_row_tail_guard_pinned': True})
    files.append(emit_json(out, 'phase-bound-byte-comparisons.json', {'pass_': True, 'samples': comparisons}))
    emit_json(out, 'glyph-stream-proof.json', {'pass_': True,
        'producer': identity(str(Path(__file__).resolve().relative_to(ROOT))),
        'inputs': inputs, 'outputs': files, 'fields': summaries,
        'both_streams_written_before_fetched_byte_oracle_open': True,
        'source_store_data_from_frozen_independent_math_only': True,
        'raw_timing_projection_excludes_register_values_and_monitored_addresses': True,
        'native_GBUF_samples_compared': len(comparisons),
        'native_last_phi1_samples_compared': len(comparisons),
        'no_CPU_VIC_interpreter_native_process_build_or_downloaded_host_execution': True,
        'limits': ['8000source-derived byte requests perfield; onlyfourGBUF/lastphi1 phases sampled, not16000direct byteobservations.',
            'Initial partial raster47 is excluded, and postrow247 reset/music/frame tail are not reconstructed.',
            'C64SC macro visibility bounds are not electrical bus timestamps.',
            'External NMI/DMA/control/mapping closure and official-source implementation assumptions remain.',
            'No pixels, completeframebuffer, animationFPS or author-intent claim.']})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        produce(args.output)
    except Exception:
        if args.output.is_dir():
            (args.output / 'failure.txt').write_text(traceback.format_exc())
        raise
