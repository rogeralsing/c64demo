#!/usr/bin/env python3
"""Typed cell-data composition with externally bound VIC-read inputs.

This is not a CPU interpreter or raster scheduler. Native custody/oracle
integration remains fail-closed until the new original case is frozen.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEMANTICS = 'research/aloft-cells-20261109/cell_semantics.py'
SEMANTICS_SHA = 'cace07aa398eabc901cd29c5d1b3018504e3f9167e0b21e357a72114bf36676d'
PRIMARY = 'research/aloft-cells-20261109/primary_reading.py'
PRIMARY_SHA = '4c8b3e1ae3968fff3bc90af9527fda0a6489c6853ba68f32bf17f4a1c4e74dda'
SEM_PROOF = 'build/research/aloft-cells-20261109/semantic-analysis/accepted-01/cell-semantics-proof.json'
SEM_PROOF_SHA = '88e8f06afaa9d066a0587d54b95d8f4a6e8c354eb14908dc09da0e924d5da3ed'
CUSTODY = 'build/research/aloft-execution-20261109/native-analysis/accepted-02'
CUSTODY_SHA = '5db9694db276541a5fd2b5cb386e92639e6da2c0d6cd644caf758eb113cc2326'
INPUTS_SHA = 'bf50bdafeb7b18b737397bbf24f78f67390e2b883e32ed02a7011013d6b16f81'
ORACLES_SHA = 'dd9d74c80242510f2271010d6ccbd0071dadba5a5ca7c2dfe9356171c4904647'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pinned(path, digest):
    raw = (ROOT / path).read_bytes()
    if sha(raw) != digest:
        raise ValueError('changed pinned input: ' + path)
    return raw


def identity(path):
    raw = (ROOT / path).read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}


def output_json(out, name, value):
    raw = (json.dumps(value, indent=2) + '\n').encode()
    (out / name).write_bytes(raw)
    return {'name': name, 'bytes': len(raw), 'sha256': sha(raw)}


def passive_module(path, digest, name):
    pinned(path, digest)
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frozen_contract():
    sem = passive_module(SEMANTICS, SEMANTICS_SHA, 'frozen_execution_cell_algebra')
    primary = passive_module(PRIMARY, PRIMARY_SHA, 'frozen_execution_VIC_values')
    proof = json.loads(pinned(SEM_PROOF, SEM_PROOF_SHA))
    ref = next(r for r in proof['outputs'] if r['name'] == 'cell-descriptors.json')
    path = str(Path(SEM_PROOF).parent / ref['name'])
    raw = pinned(path, ref['sha256'])
    if len(raw) != ref['bytes']:
        raise ValueError('descriptor size changed')
    rows = json.loads(raw)['cells']
    # Re-recognize the bytes rather than admitting an arbitrary JSON dataflow.
    by_pc = {}
    for row in rows:
        checked = sem.recognize({
            'pc': row['pc'], 'role': row['role'], 'variant': row['variant'],
            'bytes': len(bytes.fromhex(row['source_generated_bytes'])),
            'final_code_hex': row['source_generated_bytes'],
            'boundary_patch_page': row['lookup_writes_suppressed'],
        })
        if checked != row or row['pc'] in by_pc:
            raise ValueError('descriptor does not match frozen source recognizer')
        by_pc[row['pc']] = checked
    if len(by_pc) != 312:
        raise ValueError('incomplete cell source domain')
    return sem, primary, by_pc


def read_msb(sample, instruction_pc):
    """An independent input supplies the possible actual read-time beam(s).

    The caller/custody proof must establish the clock convention. A monitor
    end-of-instruction sample must not silently become a bus-read timestamp.
    Multiple possible lines are accepted only if their raster-MSB agrees.
    """
    if sample['instruction_PC'] != instruction_pc:
        raise ValueError('external read source-PC mismatch')
    if sample['scope'] != 'independently_bound_actual_operand_read_beam':
        raise ValueError('operand read beam provenance is unresolved')
    lines = sample['possible_read_raster_lines']
    if not lines or any(type(line) is not int or not 0 <= line < 312 for line in lines):
        raise ValueError('invalid PAL operand-read beam domain')
    msbs = {(line & 0x100) >> 1 for line in lines}
    if len(msbs) != 1:
        raise ValueError('unresolved D011 raster-MSB crossing')
    if not sample.get('rawref') or not sample.get('clock_provenance'):
        raise ValueError('missing read-clock custody reference')
    return msbs.pop()


def source_closure(dispatcher_bytes, call_targets, initial_flags, descriptors):
    """Finite straight-line dispatcher/cell write-footprint argument.

    This establishes a source closure under stated machine assumptions, not
    a complete instruction trace or an assertion that endpoint equality alone
    proves an unchanged executable throughout the interval.
    """
    if len(call_targets) != 200 or not initial_flags & 4:
        raise ValueError('complete200call dispatcher with IRQ disabled required')
    expected = bytearray()
    for i, row in enumerate(call_targets):
        if row['index'] != i or row['call_PC'] != 0x500 + i * 3:
            raise ValueError('dispatcher call sequence changed')
        desc = descriptors[row['target']]
        if desc['role'] != ('row-end' if i % 8 == 7 else 'normal'):
            raise ValueError('dispatcher role sequence changed')
        expected.extend((0x20, row['target'] & 255, row['target'] >> 8))
    expected.append(0x60)
    if bytes(expected) != dispatcher_bytes or len(dispatcher_bytes) != 601:
        raise ValueError('genuine dispatcher is not exactly200JSRs plusRTS')
    writes = set()
    executable = set(range(0x500, 0x759))
    for row in descriptors.values():
        executable.update(range(row['pc'], row['pc'] + len(bytes.fromhex(row['source_generated_bytes']))))
        writes.update((row['zp_x'], row['zp_y']))
        if not row['lookup_writes_suppressed']:
            writes.update((row['screen_address'], row['scratch_zp']))
    glyphs = {7 + 8 * i for i in range(32)} | {0x787 + 8 * i for i in range(8)}
    if writes != glyphs or not writes.isdisjoint(executable):
        raise ValueError('cell stores can modify admitted executable')
    if not writes.isdisjoint(range(0x400, 0x500)) or not writes.isdisjoint(range(0x100, 0x200)):
        raise ValueError('cell stores can modify lookup or return stack')
    return {'dispatcher_bytes': 601, 'calls': 200, 'all_cells_strictly_source_recognized': True,
            'data_store_address_union': sorted(writes),
            'data_stores_disjoint_dispatcher_cells_lookup_and_return_stack': True,
            'other_cell_store_is_D011_IO': True, 'IRQ_disabled_at_entry': True,
            'read_only_CMP_and_NOP_values_flags_and_side_effects_not_replayed': True,
            'machine_assumptions': [
                'No intervening external NMI handler or other CPU control diversion.',
                'No external RAM-writing DMA actor modifies code/data/return stack.',
                'VIC reads and CPU bus stalls may occur; independently bounded read inputs handle their phase.',
                'CPU memory mapping for the admitted code/IO remains the captured mapping.'],
            'endpoint_code_equality_alone_is_not_the_lifetime_argument': True}


def predict(initial_cpu_zp, lookup, call_targets, initial_d011, read_samples,
            *, initial_glyph_bytes, semantics=None, primary=None, descriptors=None):
    """Predict data effects using pre-call state and independent reads only.

    Inputs deliberately have no expected store values/addresses/counts or
    endpoint RAM. Call-target state is a declared live motion input, not a
    prediction of the motion generator. CMP values/flags remain opaque.
    """
    if semantics is None or primary is None or descriptors is None:
        semantics, primary, descriptors = frozen_contract()
    if len(initial_cpu_zp) != 256 or len(lookup) != 256:
        raise ValueError('complete genuine CPU-view ZP and lookup required')
    if any(type(v) is not int or not 0 <= v <= 255 for v in list(initial_cpu_zp) + list(lookup)):
        raise ValueError('unknown/nonbyte data input')
    if not 1 <= len(call_targets) <= 200 or not 0 <= initial_d011 <= 255:
        raise ValueError('bounded source-call input required')
    glyph_domain = {7 + 8 * i for i in range(32)} | {0x787 + 8 * i for i in range(8)}
    if set(initial_glyph_bytes) != glyph_domain:
        raise ValueError('all40 genuine initial glyph values required')
    if any(type(v) is not int or not 0 <= v <= 255 for v in initial_glyph_bytes.values()):
        raise ValueError('unknown/nonbyte initial glyph input')
    if any(initial_glyph_bytes[a] != initial_cpu_zp[a] for a in glyph_domain if a < 256):
        raise ValueError('genuine glyph/ZP input aliases disagree')
    glyph_state = dict(initial_glyph_bytes)
    zp, d011, used = list(initial_cpu_zp), initial_d011, 0
    cells, glyph_writes, d011_accesses, ordered_writes, ordered_accesses = [], [], [], [], []
    for index, target in enumerate(call_targets):
        if target['index'] != index or target['call_PC'] != 0x500 + 3 * index:
            raise ValueError('source call-site sequence changed')
        desc = descriptors[target['target']]
        if desc['role'] != ('row-end' if index % 8 == 7 else 'normal'):
            raise ValueError('source normal/row-end call selection changed')
        result = semantics.cell_data(desc, zp, lookup, d011 & 127, primary)
        effects = []
        for event in result['events']:
            kind = event['kind']
            if kind.startswith('write_'):
                address = event['address']
                if not 0 <= address < 0x800 or address & 7 != 7:
                    raise ValueError('write escaped source glyph-row contract')
                write = {'instruction_PC': event['pc'],
                    'address': address, 'value': event['value'], 'operation': 'store',
                    'dummy': False, 'call_index': index, 'kind': kind}
                glyph_writes.append(write)
                ordered_writes.append(write)
                ordered_accesses.append(write)
                glyph_state[address] = event['value']
            if kind == 'D011_RMW_alternatives_unbound_raster_MSB':
                if used == len(read_samples):
                    raise ValueError('independent operand-read input exhausted')
                sample = read_samples[used]
                read = (d011 & 127) | read_msb(sample, event['pc'])
                used += 1
                triple = primary.d011_inc_read(read)
                if triple not in event['choices']:
                    raise ValueError('actual read violates source alternative domain')
                d011 = triple['final_write']
                for operation, dummy, value in [('load', False, triple['read']),
                                               ('store', True, triple['dummy_write']),
                                               ('store', False, triple['final_write'])]:
                    access = {'instruction_PC': event['pc'], 'address': 0xd011,
                        'operation': operation, 'dummy': dummy, 'value': value,
                        'call_index': index}
                    d011_accesses.append(access)
                    ordered_accesses.append(access)
                    if operation == 'store':
                        ordered_writes.append(access)
                effects.append({'kind': 'bound_D011_RMW', 'instruction_PC': event['pc'],
                    'data': triple, 'independent_read_sample_index': used - 1})
            else:
                effects.append(event)
                if kind == 'D011_literal_store':
                    d011 = event['value']
                    access = {'instruction_PC': event['pc'],
                        'address': 0xd011, 'operation': 'store', 'dummy': False,
                        'value': d011, 'call_index': index}
                    d011_accesses.append(access)
                    ordered_writes.append(access)
                    ordered_accesses.append(access)
        cells.append({**{k: v for k, v in result.items() if k != 'events'},
                      'call_index': index, 'call_PC': target['call_PC'], 'events': effects})
    if used != len(read_samples):
        raise ValueError('unconsumed independent read samples')
    return {'cells': cells, 'predicted_CPU_view_ZP': zp, 'predicted_D011_stored': d011,
            'predicted_glyph_bytes': [{'address': a, 'value': glyph_state[a]}
                                      for a in sorted(glyph_state)],
            'predicted_glyph_writes': glyph_writes, 'predicted_D011_accesses': d011_accesses,
            'predicted_ordered_writes': ordered_writes,
            'predicted_ordered_accesses': ordered_accesses,
            'opaque_CMP_values_and_final_CNZ': True,
            'independent_read_samples_consumed': used,
            'native_expected_store_or_endpoint_values_consumed': False}


def prepare_predictions(out):
    """Write predictions before any oracle artifact is opened or parsed."""
    out.resolve().relative_to(ROOT / 'build/research/aloft-execution-20261109/cell-analysis')
    out.mkdir(parents=True, exist_ok=False)
    source_raw = Path(__file__).read_bytes()
    (out / 'cell_execution.checked.py').write_bytes(source_raw)
    pinned(CUSTODY + '/native-proof.json', CUSTODY_SHA)  # Identity gate, not data input.
    raw = pinned(CUSTODY + '/independent-inputs.json', INPUTS_SHA)
    inputs = json.loads(raw)
    if inputs['no_post_state_or_store_values_as_model_inputs'] is not True:
        raise ValueError('input/oracle separation contract changed')
    if [f['label'] for f in inputs['fields']] != ['first', 'later']:
        raise ValueError('unexpected closed-case profiles')
    semantics, primary, descriptors = frozen_contract()
    source_cells_sha = sha(b''.join(bytes.fromhex(d['source_generated_bytes'])
                                   for _, d in sorted(descriptors.items())))
    predictions = {}
    files = [{'name': 'cell_execution.checked.py', 'bytes': len(source_raw), 'sha256': sha(source_raw)}]
    for field in inputs['fields']:
        label, data = field['label'], field['input']
        cpu = data['initial_CPU']
        if cpu['pc'] != 0x500 or data['capture']['registers'] != cpu:
            raise ValueError('genuine pre0500 capture identity changed')
        if data['CPU_view_ZP'][:2] != [data['CPU_port_readbacks']['dir_read'],
                                     data['CPU_port_readbacks']['data_read']]:
            raise ValueError('CPU-view port inputs disagree')
        if data['CPU_view_ZP'][2:] != data['physical_ZP_aliases'][2:]:
            raise ValueError('ZP CPU/RAM alias inputs disagree')
        if data['read_domains_do_not_use_post_INC_flags_or_values'] is not True:
            raise ValueError('read domain consumes results')
        calls = []
        for r in data['actual_calls']:
            encoded = bytes([0x20, r['target'] & 255, r['target'] >> 8]).hex()
            if r['instruction_hex'] != encoded:
                raise ValueError('live call bytes are not JSR target')
            calls.append({'index': r['ordinal'], 'call_PC': r['instruction_PC'], 'target': r['target']})
        dispatch = bytes(data['dispatcher_0500_bytes'])
        if data['final_dispatcher_RTS'] != {'PC': 0x758, 'byte': 0x60}:
            raise ValueError('dispatcher return byte changed')
        closure = source_closure(dispatch, calls, cpu['flags'], descriptors)
        for lifetime in data['actual_code_lifetimes']:
            if not lifetime['all_actual_bytes_unchanged_from_genuine_dispatcher']:
                raise ValueError('captured executable bytes changed')
            if lifetime['cell_code_11232_sha256'] != source_cells_sha:
                raise ValueError('live generated bytes differ from source cells')
            if lifetime['call_kernel_601_sha256'] != sha(dispatch):
                raise ValueError('captured dispatcher generation changed')
        samples = []
        for i, r in enumerate(data['independent_D011_read_domains']):
            first, end = r['clock_interval_inclusive']
            if not cpu['clock'] <= first <= end or end - first > 19656:
                raise ValueError('invalid bounded operand-read interval')
            lines = sorted({clock // 63 % 312 for clock in range(first, end + 1)})
            if r['ordinal'] != i or r['read_address'] != 0xd011 or lines != r['possible_read_raster_lines']:
                raise ValueError('custody raster interval computation changed')
            inc, sty = r['INC_load_rawref'], r['preceding_STY_rawref']
            if inc['instruction_PC'] != r['instruction_PC'] or inc['instruction_hex'] != 'ee11d0':
                raise ValueError('INC read source bytes changed')
            desc = descriptors[r['instruction_PC'] - 29]
            if sty['instruction_PC'] != desc['pc'] + 27 or sty['instruction_hex'] != bytes([0x84, desc['zp_y']]).hex():
                raise ValueError('preceding STY source does not lead directly into INC')
            if r['post_INC_A_flags_result_and_store_values_excluded'] is not True:
                raise ValueError('result seeded operand-read interval')
            sample = {'instruction_PC': r['instruction_PC'],
                'scope': 'independently_bound_actual_operand_read_beam',
                'possible_read_raster_lines': lines,
                'rawref': {'preceding_STY': sty, 'INC_load': inc},
                'clock_provenance': {'interval_inclusive': [first, end],
                    'lower_bound': r['lower_bound'], 'upper_bound': r['upper_bound'],
                    'not_actual_bus_timestamps': data['not_actual_bus_timestamps']}}
            read_msb(sample, r['instruction_PC'])
            samples.append(sample)
        glyphs = {r['address']: r['value'] for r in data['all40_initial_glyph_values']}
        for part, count in [('first-cell', 1), ('full-chain', 200)]:
            selected = calls[:count]
            nreads = sum(descriptors[c['target']]['role'] == 'normal' for c in selected)
            result = predict(data['CPU_view_ZP'], data['lookup0400'], selected,
                data['initial_stored_D011'], samples[:nreads], initial_glyph_bytes=glyphs,
                semantics=semantics, primary=primary, descriptors=descriptors)
            physical = list(data['physical_ZP_aliases'])
            physical[2:] = result['predicted_CPU_view_ZP'][2:]
            last = result['cells'][-1]
            result.update({'label': label, 'part': part, 'source_closure': closure,
                'input_capture': data['capture'],
                'independent_D011_read_domains': samples[:nreads],
                'predicted_physical_ZP_aliases': physical,
                'predicted_return_CPU': {'pc': 0x503 if count == 1 else 0xf0b1,
                    'sp': cpu['sp'] if count == 1 else (cpu['sp'] + 2) & 255,
                    'a': last['A_at_return'], 'x': last['X'], 'y': last['Y'],
                    'preserved_flags_mask': 0x4c, 'preserved_flags_value': cpu['flags'] & 0x4c},
                'unique_call_targets': len({c['target'] for c in selected}),
                'predicted_before_oracle_artifact_open': True})
            name = f'{label}-{part}-prediction.json'
            files.append(output_json(out, name, result))
            predictions[(label, part)] = result
    return inputs, predictions, files


def compare_endpoint(prediction, endpoint):
    expected, cpu = prediction['predicted_return_CPU'], endpoint['capture']['registers']
    for key in ('pc', 'sp', 'a', 'x', 'y'):
        if cpu[key] != expected[key]:
            raise ValueError(('return CPU mismatch', key, cpu[key], expected[key]))
    if cpu['flags'] & expected['preserved_flags_mask'] != expected['preserved_flags_value']:
        raise ValueError('preserved I/D/V flags changed')
    for key, actual_key in [('predicted_CPU_view_ZP', 'CPU_view_ZP'),
                            ('predicted_physical_ZP_aliases', 'physical_ZP_aliases')]:
        if prediction[key] != endpoint[actual_key]:
            raise ValueError('endpoint mismatch: ' + actual_key)
    if prediction['predicted_glyph_bytes'] != endpoint['all40_glyph_values']:
        raise ValueError('glyph endpoint differs')
    if prediction['predicted_D011_stored'] != endpoint['stored_D011']:
        raise ValueError('stored D011 endpoint differs')
    return {'capture': endpoint['capture'], 'AXY_PC_SP_equal': True,
        'preserved_IDV_flags_equal': True, 'CMP_CNZ_not_compared': True,
        'all256_CPU_view_ZP_equal': True, 'all256_physical_ZP_aliases_equal': True,
        'all40_glyph_values_equal': True, 'raw_stored_D011_equal': True}


def compare_hooks(prediction, hooks, first_clock, end_clock, descriptors):
    """Consume every reported hook in the interval; RMW data stay unobserved."""
    glyphs = {r['address'] for r in prediction['predicted_glyph_bytes']}
    observed = [h for h in hooks if first_clock <= h['registers']['clock'] <= end_clock]
    expected = prediction['predicted_ordered_accesses']
    if len(expected) != len(observed):
        raise ValueError(('hook count differs', len(expected), len(observed)))
    code = {pc + i: value for pc, desc in descriptors.items()
            for i, value in enumerate(bytes.fromhex(desc['source_generated_bytes']))}
    glyph_count = literal_count = 0
    inc_completions, raw_projection, glyph_projection = set(), [], []
    for exp, actual in zip(expected, observed):
        structure = (actual['operation'], actual['instruction_PC'], actual['monitored_address'])
        if structure != (exp['operation'], exp['instruction_PC'], exp['address']):
            raise ValueError(('ordered access differs', structure, exp))
        encoded = bytes.fromhex(actual['instruction_hex'])
        pc, regs = actual['instruction_PC'], actual['registers']
        if encoded != bytes(code[pc + i] for i in range(len(encoded))):
            raise ValueError('observed instruction bytes disagree with source generation')
        if regs['pc'] != pc + len(encoded):
            raise ValueError('hook registers are not at source instruction fallthrough')
        raw_projection.append(structure)
        if encoded[0] in (0x85, 0x8d, 0x86, 0x84):
            if actual['operation'] != 'store':
                raise ValueError('direct-store instruction reported as load')
            register = {0x85: 'a', 0x8d: 'a', 0x86: 'x', 0x84: 'y'}[encoded[0]]
            value = regs[register]
            if value != actual['post_register_direct_store_operand'] or value != exp['value']:
                raise ValueError('direct store value differs')
            if int.from_bytes(encoded[1:], 'little') != exp['address']:
                raise ValueError('direct store operand address differs')
            if exp['address'] in glyphs:
                glyph_count += 1
                glyph_projection.append((pc, exp['address'], value))
            else:
                literal_count += 1
        elif encoded == bytes.fromhex('ee11d0'):
            if actual['post_register_direct_store_operand'] is not None:
                raise ValueError('INC hook falsely exposes a direct bus value')
            cell = prediction['cells'][exp['call_index']]
            rmw = next(e for e in cell['events'] if e['kind'] == 'bound_D011_RMW')
            result = rmw['data']['final_write']
            expected_nz = (result & 0x80) | (2 if result == 0 else 0)
            if regs['flags'] & 0x82 != expected_nz:
                raise ValueError('independent postINC N/Z disagrees')
            if (regs['a'], regs['x'], regs['y']) != (cell['A_at_return'], cell['X'], cell['Y']):
                raise ValueError('INC-preserved A/X/Y disagrees')
            inc_completions.add((pc, regs['clock']))
        else:
            raise ValueError('unsupported hook instruction in admitted source closure')
    def digest_projection(rows):
        return sha(json.dumps(rows, separators=(',', ':')).encode())
    return {'ordered_hook_operations_PCs_addresses_equal': True,
        'every_reported_hook_in_interval_consumed': True,
        'predicted_address_set_not_used_to_filter_oracle': True,
        'watched_hook_records': len(observed), 'direct_glyph_store_values_equal': glyph_count,
        'direct_D011_literal_STA_values_equal': literal_count,
        'independent_INC_postNZ_and_preserved_AXY_completions_equal': len(inc_completions),
        'ordered_structure_projection_sha256': digest_projection(raw_projection),
        'direct_glyph_value_projection_sha256': digest_projection(glyph_projection),
        'INC_read_dummy_final_values_derived_not_directly_observed': True,
        'reported_hook_clocks_not_bus_access_clocks': True,
        'observed_dummy_final_roles_not_separate_bus_value_measurements': True}


def produce(out, prediction_only=False):
    inputs, predictions, files = prepare_predictions(out)
    if prediction_only:
        output_json(out, 'prediction-only.json', {
            'status': 'Predictions emitted; comparison oracles never opened in this invocation.',
            'native_acceptance_claim': False, 'outputs': files})
        return
    # No oracle/endpoint artifact has been opened before the four predictions exist.
    oracle = json.loads(pinned(CUSTODY + '/hook-oracles.json', ORACLES_SHA))
    custody = json.loads(pinned(CUSTODY + '/native-proof.json', CUSTODY_SHA))
    if custody['pass_'] is not True or oracle['input_use_forbidden'] is not True:
        raise ValueError('custody/oracle scope changed')
    if not oracle['hook_clock_is_instruction_completion_not_bus_clock'] or not oracle['RMW_hook_values_not_bus_data']:
        raise ValueError('observer limitations changed')
    facts = custody['observer_source_contract']['facts']
    for key in ('queued_duplicates_preserved', 'FIFO_within_load_and_store_queue', 'loads_flushed_before_stores'):
        if facts[key] is not True:
            raise ValueError('collector ordering proof changed')
    _, _, descriptors = frozen_contract()
    fields, comparisons = [], []
    captures = {r['stem']: r for r in custody['captures']}
    for field in oracle['fields']:
        label = field['label']
        entry = next(f['input'] for f in inputs['fields'] if f['label'] == label)
        record = {'label': label, 'source_closure': predictions[(label, 'full-chain')]['source_closure'],
            'unique_call_targets': predictions[(label, 'full-chain')]['unique_call_targets'],
            'input_capture': entry['capture'], 'comparisons': {}}
        for part, endpoint_role in [('first-cell', 'first_return'), ('full-chain', 'post_all')]:
            pred, endpoint = predictions[(label, part)], field['endpoints'][endpoint_role]
            ep = compare_endpoint(pred, endpoint)
            hk = compare_hooks(pred, oracle['all_hooks'], entry['initial_CPU']['clock'],
                endpoint['capture']['registers']['clock'], descriptors)
            comparison = {'label': label, 'part': part, 'endpoint': ep, 'hooks': hk}
            comparisons.append(comparison)
            record['comparisons'][part] = comparison
            output_ref = next(f for f in files if f['name'] == f'{label}-{part}-prediction.json')
            record['first_prediction' if part == 'first-cell' else 'full_prediction'] = output_ref
        pre = captures[field['roles']['precall']]['registers']
        first_target = captures[field['roles']['first_target']]['registers']
        first_return = field['endpoints']['first_return']['capture']['registers']
        post = field['endpoints']['post_all']['capture']['registers']
        record['observed_elapsed_PAL_cycles'] = {
            'F0AE_to_F0B1': post['clock'] - pre['clock'],
            '0500_to_F0B1': post['clock'] - entry['initial_CPU']['clock'],
            'first_cell_entry_to_0503': first_return['clock'] - first_target['clock'],
            '0500_to_0503': first_return['clock'] - entry['initial_CPU']['clock'],
            'not_an_animation_FPS_or_wall_time_measurement': True}
        initial = {r['address']: r['value'] for r in entry['all40_initial_glyph_values']}
        record['changed_glyph_slots_from_genuine_entry'] = {
            part: sum(r['value'] != initial[r['address']] for r in predictions[(label, part)]['predicted_glyph_bytes'])
            for part in ('first-cell', 'full-chain')}
        fields.append(record)
    files.append(output_json(out, 'execution-comparisons.json', {'pass_': True, 'fields': comparisons}))
    proof_inputs = [identity(p) for p in (CUSTODY + '/native-proof.json', CUSTODY + '/independent-inputs.json',
                    CUSTODY + '/hook-oracles.json', SEMANTICS, PRIMARY, SEM_PROOF)]
    output_json(out, 'cell-execution-proof.json', {
        'pass_': True, 'producer': identity(str(Path(__file__).resolve().relative_to(ROOT))),
        'inputs': proof_inputs, 'predictions_written_before_oracle_artifact_open': True,
        'no_CPU_interpreter_native_or_build_execution': True, 'fields': fields, 'outputs': files,
        'limits': ['Two captured source-admitted200call chains; not all312cell paths or every motion pose.',
            'D011 bus data are source-derived using independent raster domains, not present in RMW hooks.',
            'PostINC N/Z and A/X/Y, direct-store values and rawstored endpoints are distinct observations.',
            'CMP target values and final C/N/Z remain opaque; their read side effects are not simulated.',
            'Continuous executable lifetime relies on the finite source closure and stated NMI/DMA/mapping assumptions.',
            'No complete field fetch, committed pixels, animation FPS or author-intent claim.']})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--prediction-only', action='store_true')
    args = parser.parse_args()
    produce(args.output, args.prediction_only)
