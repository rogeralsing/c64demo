#!/usr/bin/env python3
"""Finite source motion-table arithmetic; not a CPU instruction interpreter."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import traceback

ROOT = Path(__file__).resolve().parents[2]
TABLE = 'build/research/aloft-motion-20261109/table-analysis/accepted-01'
TABLE_PROOF_SHA = 'b1c79ce00b3fa4694786ec6be8786b7c949b0b176514d8fcceb533441379a0fa'
ARCHIVE = 'build/research/quondam/hardware-source/vice-3.10.tar.gz'
ARCHIVE_SHA = '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1'
SOURCE = 'build/research/aloft-decode-20261109/color-analysis/accepted-01/bundle031-memory.bin'
SOURCE_SHA = '95a344b261b1b28d229da9778df80bae06eff39470ff4515820ce4e1fa86869e'
NATIVE = 'build/research/aloft-motion-20261109/native-analysis/accepted-01'
NATIVE_SHA = 'c478a2f2d620ed0b07f7e778df9cf14bb4bb85acadcac905cb630bdb7bb374ab'
INPUTS_SHA = 'afa80f3ba17872e0d464b6b84b7207b79ffd219ed6158cef97ec7a957ab9e780'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pinned(path, digest):
    raw = (ROOT / path).read_bytes()
    if sha(raw) != digest:
        raise ValueError('changed pinned input: ' + path)
    return raw


def identity(path):
    raw = (ROOT / path).read_bytes()
    return {'path': path, 'bytes': len(raw), 'sha256': sha(raw)}


def export(folder, proof, name):
    row = next(r for r in proof['outputs'] if r['name'] == name)
    raw = pinned(folder + '/' + name, row['sha256'])
    if len(raw) != row['bytes']:
        raise ValueError('changed export size')
    return raw


def abi_data(ref):
    raw = pinned(TABLE + '/' + ref['name'], ref['sha256'])
    if len(raw) != ref['bytes']:
        raise ValueError('changed table ABI file size')
    return raw


def write_json(out, name, value):
    raw = (json.dumps(value, indent=2) + '\n').encode()
    (out / name).write_bytes(raw)
    return {'name': name, 'bytes': len(raw), 'sha256': sha(raw)}


def recognize_program(raw, base):
    """Admit only 200 fixed LDA abs,X / ADC abs,Y / STA abs terms and one RTS."""
    if len(raw) != 1801 or raw[-1] != 0x60 or base not in (0xc000, 0xc800, 0xd000, 0xd800):
        raise ValueError('unsupported generated motion program')
    rows = []
    for i in range(200):
        term = raw[9 * i:9 * i + 9]
        if (term[0], term[3], term[6]) != (0xbd, 0x79, 0x8d):
            raise ValueError('motion term does not match fixed macro')
        a = int.from_bytes(term[1:3], 'little')
        b = int.from_bytes(term[4:6], 'little')
        destination = int.from_bytes(term[7:9], 'little')
        if destination != 0x502 + 3 * i:
            raise ValueError('motion term does not write the prescribed target high byte')
        rows.append({'index': i, 'source_PC': base + 9 * i,
            'LDA_base': a, 'ADC_base': b, 'store_address': destination})
    return rows


def load_source_contract():
    proof = json.loads(pinned(TABLE + '/motion-table-proof.json', TABLE_PROOF_SHA))
    if proof['pass_'] is not True:
        raise ValueError('table source proof failed')
    abi = json.loads(export(TABLE, proof, 'table-abi.json'))
    if abi['incoming_carry_unspecified'] is not True or abi['native_output_seeding']:
        raise ValueError('table ABI supplied a fictitious runtime carry/input')
    memory, assets, programs = {}, [], {}
    for row in abi['assets']:
        raw = abi_data(row['data'])
        if len(raw) != 512 or raw[:256] != raw[256:]:
            raise ValueError('original wave asset period contract changed')
        if (min(raw), max(raw)) != (row['minimum'], row['maximum']):
            raise ValueError('source asset bounds changed')
        for i, value in enumerate(raw):
            address = row['base'] + i
            if address in memory:
                raise ValueError('source wave assets overlap')
            memory[address] = value
        assets.append({'base': row['base'], 'minimum': min(raw), 'maximum': max(raw),
                       'source_data': row['data']})
    for row in abi['programs']:
        raw = abi_data(row['data'])
        terms = recognize_program(raw, row['base'])
        if any(t['LDA_base'] >> 8 != row['LDA_asset'] >> 8 or
               t['ADC_base'] >> 8 != row['ADC_asset'] >> 8 for t in terms):
            raise ValueError('generated table operand high byte changed')
        a = next(x for x in assets if x['base'] == row['LDA_asset'])
        b = next(x for x in assets if x['base'] == row['ADC_asset'])
        bound = a['maximum'] + b['maximum'] + 1
        if bound >= 256:
            raise ValueError('this source does not prove carry-out zero')
        programs[row['base']] = {'descriptor': row, 'terms': terms,
            'all_phase_input_sum_bound_including_carry1': bound,
            'carry_out_zero_for_every_admitted_source_value_pair': True}
    seed = abi_data(abi['dispatcher_data'])
    if len(seed) != 601 or seed[-1] != 0x60:
        raise ValueError('source dispatcher seed shape changed')
    for i in range(200):
        if seed[3 * i:3 * i + 3] != bytes([0x20, 0x23 if i % 8 == 7 else 0, 0x20]):
            raise ValueError('source initial dispatcher skeleton changed')
    return abi, memory, programs, seed, assets


def adc_binary(a, b, carry):
    """Exact admitted binary ADC value/flags, not a host sine approximation."""
    if any(type(v) is not int or not 0 <= v <= 255 for v in (a, b)) or carry not in (0, 1):
        raise ValueError('byte operands and carry bit required')
    total = a + b + carry
    result = total & 255
    return {'result': result, 'carry': int(total > 255),
        'negative': int(bool(result & 128)), 'zero': int(result == 0),
        'overflow': int(bool((~(a ^ b) & (a ^ result)) & 128))}


def evaluate(program, source_memory, dispatcher_seed, x, y, flags):
    """One source-defined 200-term transform from genuine phase/status inputs.

    Every A value is freshly loaded; only processor carry passes between terms.
    No byte of the previous runtime call list is read. All 200 high bytes are
    overwritten in the independently initialized dispatcher skeleton.
    """
    if any(type(v) is not int or not 0 <= v <= 255 for v in (x, y, flags)):
        raise ValueError('genuine byte X/Y/status inputs required')
    if flags & 8:
        raise ValueError('decimal ADC is outside the admitted binary motion contract')
    carry = flags & 1
    out, trace, read_addresses = bytearray(dispatcher_seed), [], set()
    lda_crosses = adc_crosses = 0
    for row in program['terms']:
        a_address, b_address = (row['LDA_base'] + x) & 65535, (row['ADC_base'] + y) & 65535
        if a_address not in source_memory or b_address not in source_memory:
            raise ValueError('motion read lacks original source-asset provenance')
        a, b = source_memory[a_address], source_memory[b_address]
        a_cross = int((row['LDA_base'] & 255) + x > 255)
        b_cross = int((row['ADC_base'] & 255) + y > 255)
        lda_crosses += a_cross
        adc_crosses += b_cross
        result = adc_binary(a, b, carry)
        offset = row['store_address'] - 0x500
        out[offset] = result['result']
        trace.append({**row, 'LDA_address': a_address, 'ADC_address': b_address,
            'LDA_value': a, 'ADC_value': b, 'carry_in': carry,
            'LDA_page_cross': bool(a_cross), 'ADC_page_cross': bool(b_cross), **result})
        read_addresses.update((a_address, b_address))
        carry = result['carry']
    if len(trace) != 200 or any(r['carry'] for r in trace):
        raise ValueError('source-derived carry-out bound disagrees with exact arithmetic')
    last = trace[-1]
    final_flags = (flags & 0x0c) | last['carry'] | (last['zero'] << 1) | (last['overflow'] << 6) | (last['negative'] << 7)
    targets = [out[3 * i + 1] | (out[3 * i + 2] << 8) for i in range(200)]
    if any(not 0x20 <= t >> 8 <= 0xbb for t in targets):
        raise ValueError('unclamped source result escapes generated cell-page library')
    return {'terms': trace, 'dispatcher_hex': out.hex(),
        'target_high_bytes': [r['result'] for r in trace], 'targets': targets,
        'return_CPU': {'a': last['result'], 'x': x, 'y': y,
                       'flags_mask': 0xcf, 'flags_value': final_flags},
        'all200_target_high_bytes_computed': True,
        'prior_runtime_dispatcher_high_bytes_not_inputs': True,
        'source_asset_read_addresses': sorted(read_addresses),
        'page_crosses': {'LDA_abs_X': lda_crosses, 'ADC_abs_Y': adc_crosses},
        'no_stall_JSR_program_RTS_cycles': 6 + 200 * 12 + lda_crosses + adc_crosses + 6,
        'cycle_scope': 'Algebraic source core cost; stalls, interrupts and whole-frame timing are not predicted.',
        'all_source_carry_outs_zero': True,
        'incoming_carry_dependency': 'First target high byte only; subsequent 199 carry inputs are zero by source value bounds.'}


def primary_source(out):
    pinned(ARCHIVE, ARCHIVE_SHA)
    with tarfile.open(ROOT / ARCHIVE) as archive:
        member = 'vice-3.10/src/6510dtvcore.c'
        raw = archive.extractfile(member).read()
    if sha(raw) != '40b9eea851ddb2853abf04c91ae16117a4a92789b18a5c2ae627ec90f9a454f8':
        raise ValueError('actual SC CPU core source changed')
    lines, anchors = raw.decode().splitlines(), []
    for first, end, needles in [
        (739, 771, ['LOCAL_DECIMAL()', 'tmp_value + reg_a_read + (reg_p & P_CARRY)', 'LOCAL_SET_CARRY(tmp > 0xff)']),
        (503, 516, ['INT_ABS_I_R(reg_x)', 'LOAD((p2) + reg_x)', 'INT_ABS_I_R(reg_y)', 'LOAD((p2) + reg_y)']),
        (1239, 1244, ['get_func(dest)', 'LOCAL_SET_NZ(dest)']),
        (1639, 1643, ['INC_PC(pc_inc)', 'set_func(value)']),
        (2314, 2316, ['ADC(GET_ABS_Y, 3)']),
        (2382, 2384, ['ST(reg_a_read, SET_ABS, 3)']),
        (2570, 2572, ['LD(reg_a_write, GET_ABS_X, 3)']),
    ]:
        text = '\n'.join(lines[first - 1:end]) + '\n'
        if any(needle not in text for needle in needles):
            raise ValueError('primary arithmetic/dataflow source anchor changed')
        anchors.append({'first_line': first, 'last_line': end, 'text': text, 'sha256': sha(text.encode())})
    return write_json(out, 'primary-motion-source.json', {'archive': identity(ARCHIVE),
        'member': member, 'member_sha256': sha(raw), 'anchors': anchors,
        'admitted_path': 'Binary D=0 ADC; source-prescribed indexed byte reads, not an analytical sine model.',
        'cycle_cost_scope': '200 fixed 12-cycle macro budgets plus indexed-read page crossings and outer JSR/RTS; no stall scheduler.'})


def prepare(out):
    out.resolve().relative_to(ROOT / 'build/research/aloft-motion-20261109/motion-analysis')
    out.mkdir(parents=True, exist_ok=False)
    source_raw = Path(__file__).read_bytes()
    (out / 'motion.checked.py').write_bytes(source_raw)
    files = [{'name': 'motion.checked.py', 'bytes': len(source_raw), 'sha256': sha(source_raw)}]
    pinned(NATIVE + '/native-proof.json', NATIVE_SHA)  # Identity only before predictions.
    source = pinned(SOURCE, SOURCE_SHA)
    abi, memory, programs, seed, assets = load_source_contract()
    inputs = json.loads(pinned(NATIVE + '/independent-inputs.json', INPUTS_SHA))
    if not inputs['no_post_state_or_store_values_as_model_inputs'] or not inputs['dispatcher_high_bytes_not_exported_as_inputs']:
        raise ValueError('native input/oracle separation changed')
    if source[0xf136:0xf141] != bytes.fromhex('cacaca8e30f1c8c88c32f1'):
        raise ValueError('phase-0 X/Y evolution source changed')
    files.append(primary_source(out))
    predictions = {}
    for witness in inputs['motion_witnesses']:
        label, entry = witness['label'], witness['input']
        cpu, context = entry['CPU'], entry['phase_context']
        if not entry['no_current_or_future_dispatcher_high_bytes_as_inputs']:
            raise ValueError('dispatcher outputs entered input projection')
        if bool(cpu['flags'] & 1) != entry['C'] or bool(cpu['flags'] & 8) != entry['D']:
            raise ValueError('genuine C/D readbacks disagree')
        if cpu['flags'] & 8 or not cpu['flags'] & 4:
            raise ValueError('native motion requires D clear and IRQ disabled')
        if cpu['port01'] & 2:
            raise ValueError('source wave assets are hidden by captured CPU mapping')
        address = entry['program_address']
        if address not in programs or address >= 0xd000 and cpu['port01'] & 3:
            raise ValueError('selected motion code is not visible in captured CPU mapping')
        program = programs[address]
        if entry['program_source'] != program['descriptor']['data']:
            raise ValueError('genuine program source binding changed')
        phase = next(p for p in abi['motion']['phases'] if p['program'] == address)
        current = next(p for p in context['phases'] if p['index'] == phase['index'])
        if context['active_controller'] != phase['entry'] or context['controller_operand_bytes'] != list(phase['entry'].to_bytes(2, 'little')):
            raise ValueError('active motion-controller generation differs')
        if (cpu['x'], cpu['y']) != (current['X'], current['Y']):
            raise ValueError('genuine phase immediates and loaded registers differ')
        if cpu['pc'] != phase['Y_operand'] + 1 or source[cpu['pc']:cpu['pc'] + 3] != bytes([0x20, address & 255, address >> 8]):
            raise ValueError('genuine input is not the source motion JSR boundary')
        result = evaluate(program, memory, seed, cpu['x'], cpu['y'], cpu['flags'])
        opposite = evaluate(program, memory, seed, cpu['x'], cpu['y'], cpu['flags'] ^ 1)
        changed = [i for i, (a, b) in enumerate(zip(bytes.fromhex(result['dispatcher_hex']), bytes.fromhex(opposite['dispatcher_hex']))) if a != b]
        if changed != [2]:
            raise ValueError('source carry sensitivity differs from proven first-term-only dependency')
        stores = {row['store_address'] for row in program['terms']}
        if len(stores) != 200 or stores & set(memory) or stores & set(range(address, address + 1801)) or stores & set(range(0x100, 0x200)):
            raise ValueError('motion writes escape finite dispatcher-only closure')
        result.update({'label': label, 'invocation_index': witness['invocation_index'],
            'input_capture': entry['capture'], 'genuine_X_Y_C_D': {
                'X': cpu['x'], 'Y': cpu['y'], 'C': entry['C'], 'D': entry['D']},
            'program_address': address, 'source_program_ref': program['descriptor']['data'],
            'source_assets': assets, 'expected_return_PC': cpu['pc'] + 3,
            'expected_return_SP': cpu['sp'],
            'source_closure': {'RAM_store_set': sorted(stores),
                'only_dispatcher_high_bytes_written': True,
                'program_tables_controller_and_return_stack_not_written': True,
                'IRQ_disabled': True, 'D_clear': True,
                'assumptions': ['No unmodeled external NMI/control diversion or RAM-writing DMA.',
                                'Captured CPU memory mapping remains in force.']},
            'counterfactual_opposite_C_changed_dispatcher_offsets': changed,
            'predicted_before_any_post_or_store_oracle_open': True})
        if phase['index'] == 0:
            result['phase_XY_after_wrapper'] = {
                'X_operand': phase['X_operand'], 'X': (cpu['x'] - 3) & 255,
                'Y_operand': phase['Y_operand'], 'Y': (cpu['y'] + 2) & 255,
                'source_guard': source[0xf136:0xf141].hex(),
                'palette_fade_and_wrapper_CPU_not_predicted': True,
                'caller_counter_05_06_updates_after_F11D': True}
        files.append(write_json(out, label + '-motion-prediction.json', result))
        raw = bytes.fromhex(result['dispatcher_hex'])
        name = label + '-dispatcher-0500.bin'; (out / name).write_bytes(raw)
        files.append({'name': name, 'bytes': len(raw), 'sha256': sha(raw)})
        predictions[label] = result
    return inputs, predictions, files


def compare_witness(witness, oracle, prediction, all_hooks):
    entry = witness['input']
    pre = entry['CPU']
    endpoints = {row['role']: row for row in oracle['endpoints']}
    post = endpoints['postcall']
    cpu = post['CPU']
    expected = prediction['return_CPU']
    for key in ('a', 'x', 'y'):
        if cpu[key] != expected[key]:
            raise ValueError('program return register differs: ' + key)
    if cpu['flags'] & expected['flags_mask'] != expected['flags_value']:
        raise ValueError('program return ADC/status flags differ')
    if cpu['pc'] != prediction['expected_return_PC'] or cpu['sp'] != prediction['expected_return_SP']:
        raise ValueError('natural program return PC/SP differs')
    if (cpu['port00'], cpu['port01']) != (pre['port00'], pre['port01']):
        raise ValueError('program CPU port mapping changed')
    raw = bytes.fromhex(prediction['dispatcher_hex'])
    if bytes(post['dispatcher_0500_bytes']) != raw:
        raise ValueError('complete 601-byte dispatcher output differs')
    if post['phase_context'] != entry['phase_context']:
        raise ValueError('program unexpectedly modified controller/counter/palette state')
    hooks = [h for h in all_hooks if pre['clock'] <= h['registers']['clock'] <= cpu['clock']]
    if len(hooks) != len(prediction['terms']):
        raise ValueError('reported store count differs from source terms')
    projection = []
    last_clock = pre['clock']
    for term, hit in zip(prediction['terms'], hooks):
        address, pc = term['store_address'], term['source_PC'] + 6
        encoded = bytes([0x8d, address & 255, address >> 8]).hex()
        regs = hit['registers']
        if (hit['operation'], hit['monitored_address'], hit['instruction_PC'], hit['instruction_hex']) != ('store', address, pc, encoded):
            raise ValueError('ordered direct-store source/address differs')
        if regs['pc'] != pc + 3 or regs['sp'] != (pre['sp'] - 2) & 255:
            raise ValueError('store hook is not the admitted source/stack fallthrough')
        if (regs['a'], regs['x'], regs['y']) != (term['result'], pre['x'], pre['y']):
            raise ValueError('observed STA value or invariant X/Y differs')
        if hit['post_register_direct_store_operand'] != term['result'] or hit['RMW_bus_value_not_present_in_hook']:
            raise ValueError('store is not a directly observed STA register operand')
        flags = (pre['flags'] & 0x0c) | term['carry'] | (term['zero'] << 1) | (term['overflow'] << 6) | (term['negative'] << 7)
        if regs['flags'] & 0xcf != flags:
            raise ValueError('observed per-term ADC/status flags differ')
        if regs['clock'] <= last_clock:
            raise ValueError('store completion order is not strictly increasing')
        last_clock = regs['clock']
        projection.append([pc, address, regs['a'], regs['flags'] & 0xcf])
    wrapper_result = {'compared': False, 'palette_fades_and_wrapper_CPU_not_predicted': True}
    if 'phase_XY_after_wrapper' in prediction:
        wrapper = endpoints['postwrapper']
        if wrapper['CPU']['pc'] != 0xf11d or wrapper['CPU']['sp'] != (pre['sp'] + 2) & 255:
            raise ValueError('wrapper boundary is not the natural return before caller counter update')
        if bytes(wrapper['dispatcher_0500_bytes']) != raw:
            raise ValueError('generated dispatcher changed before controller return')
        desired = prediction['phase_XY_after_wrapper']
        actual_phase = next(p for p in wrapper['phase_context']['phases'] if p['index'] == 0)
        if (actual_phase['X'], actual_phase['Y']) != (desired['X'], desired['Y']):
            raise ValueError('source phase X/Y evolution differs')
        if any(wrapper['phase_context'][key] != entry['phase_context'][key] for key in ('ZP05', 'ZP06')):
            raise ValueError('caller counter changed before F11D')
        wrapper_result = {'compared': True, 'capture': wrapper['capture'],
            'phase_XY_equal': True, 'dispatcher_still_equal': True,
            'caller_counter_not_advanced_before_F11D': True,
            'palette_fades_and_wrapper_CPU_not_predicted': True}
    elapsed = cpu['clock'] - pre['clock']
    return {'label': witness['label'], 'invocation_index': witness['invocation_index'],
        'pre_capture': entry['capture'], 'post_capture': post['capture'],
        'genuine_C': entry['C'], 'genuine_D': entry['D'],
        'complete_dispatcher_bytes_equal': 601, 'all200_direct_STA_values_and_order_equal': True,
        'all200_ADC_NZVC_and_preserved_DI_flags_equal': True,
        'all_reported_hooks_in_program_interval_consumed': True,
        'source_store_count': len(prediction['terms']),
        'return_AXY_PC_SP_and_flags_equal': True,
        'controller_counter_palette_unchanged_during_generated_program': True,
        'trace_projection_sha256': sha(json.dumps(projection, separators=(',', ':')).encode()),
        'page_crosses': prediction['page_crosses'],
        'algebraic_no_stall_call_cycles': prediction['no_stall_JSR_program_RTS_cycles'],
        'observed_call_cycles': elapsed,
        'observed_equals_algebraic_core_cost': elapsed == prediction['no_stall_JSR_program_RTS_cycles'],
        'timing_scope': 'Equality for these captured intervals only, not a whole-frame/FPS or general stall-free theorem.',
        'wrapper_phase_only': wrapper_result}


def produce(out, prediction_only=False):
    inputs, predictions, files = prepare(out)
    if prediction_only:
        write_json(out, 'prediction-only.json', {'native_acceptance_claim': False,
            'post_target_and_store_oracle_files_opened': False, 'outputs': files})
        return
    # Separate oracle data are opened only after both full predictions are saved.
    native = json.loads(pinned(NATIVE + '/native-proof.json', NATIVE_SHA))
    if native['pass_'] is not True:
        raise ValueError('native custody failed')
    oracles = json.loads(export(NATIVE, native, 'motion-oracles.json'))
    if oracles['input_use_forbidden'] is not True or oracles['all_raw_hits_retained'] is not True:
        raise ValueError('oracle separation/raw-history contract changed')
    records = []
    for witness in inputs['motion_witnesses']:
        oracle = next(row for row in oracles['motion_witnesses'] if row['label'] == witness['label'])
        if oracle['source_store_values_from_actual_A_are_oracles_only'] is not True:
            raise ValueError('direct-store oracle scope changed')
        record = compare_witness(witness, oracle, predictions[witness['label']], oracles['all_hooks'])
        record['prediction'] = next(f for f in files if f['name'] == witness['label'] + '-motion-prediction.json')
        record['dispatcher'] = next(f for f in files if f['name'] == witness['label'] + '-dispatcher-0500.bin')
        records.append(record)
    files.append(write_json(out, 'motion-comparisons.json', {'pass_': True, 'motion_witnesses': records}))
    write_json(out, 'motion-proof.json', {'pass_': True,
        'producer': identity(str(Path(__file__).resolve().relative_to(ROOT))),
        'inputs': [identity(p) for p in (TABLE + '/motion-table-proof.json',
            NATIVE + '/native-proof.json', NATIVE + '/independent-inputs.json',
            NATIVE + '/motion-oracles.json', SOURCE, ARCHIVE)],
        'outputs': files, 'motion_witnesses': records,
        'predictions_persisted_before_nativeproof_JSON_or_oracle_parse': True,
        'genuine_inputs_exclude_all_current_and_future_dispatcher_high_bytes': True,
        'source_initialized_scaffolding_has_all200_high_bytes_overwritten': True,
        'source_programs_recognized': 4, 'native_programs_exercised': [0xc000],
        'source_assets_bytes': 2560, 'native_ordered_target_stores_compared': 400,
        'no_CPU_interpreter_native_process_build_or_downloaded_host_execution': True,
        'limits': ['Only two genuine invocations of the first C000 controller are compared natively.',
            'Incoming carry comes from true pre-F133 flags; music is not interpreted and no carry default is supplied.',
            'D must be clear. Source-only other-controller cases do not expand native coverage.',
            'Controller wrapper comparison covers phase X/Y and unchanged counters/dispatcher, not palette fades or full wrapper CPU behavior.',
            'Reported hook clocks are completion contexts, not electrical bus timestamps.',
            'Source closure retains unmodeled external NMI/control diversion, RAM-writing DMA and captured-mapping assumptions.',
            'No complete-frame, future-rendered-field, pixel or animation-FPS claim.']})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--prediction-only', action='store_true')
    args = parser.parse_args()
    try:
        produce(args.output, args.prediction_only)
    except Exception:
        if args.output.is_dir():
            (args.output / 'failure.txt').write_text(traceback.format_exc())
        raise
