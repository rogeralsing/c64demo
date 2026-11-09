#!/usr/bin/env python3
"""Passive closed-case custody for original Aloft cell execution observations.

No CPU model, native control, process, socket, build or downloaded host code.
The live case cannot be accepted before its owner supplies final closure pins.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-execution-20261109'
ANALYSIS = BASE / 'native-analysis'
PROFILE = ANALYSIS / 'closed-profile-01.json'
PROFILE_SHA = 'cb077129b7206a748cbc0e562c63ffe7dc0e66778a0cfd3d79cd55b384472fb6'
PINS = {
    'research/vice_session_live.py': '4340d1b0394fa612f5e6a71edddcbc2daf947e59c4c3013ab3b850c886dc621c',
    'research/verify_vice_live.py': 'f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a',
    'research/eod/controller.py': '033bafb6ac6e97283175ac6713af0eef60cb7991b653ee1c98c47a1a4afa83c9',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'research/aloft-decode-20261109/native_binding.py': '48510dcfd070f06db424fe91c2fe4e607c51ca8922340a26e1523d557d2406c0',
    'build/research/aloft-20261109/disk-analysis/accepted-01/Aloft-Side1.d64': 'd13eae8daeada64bc61772a2dad2d3e62d1a0d30a34b29103119535610e4cfce',
    'build/research/aloft-20261109/disk-analysis/accepted-01/bootstrap-side1.prg': '7e283e390a10c2b7784ac1885081234c21a754d161e938babd504a13da2ee2e5',
    'build/research/aloft-20261109/loader-analysis/accepted-01/resident-0160.bin': 'b09c13f9f60a28aa87cf1b157b4035df325eb60bf6d79fe8f176cf7aa606db48',
    'build/research/quondam/hardware-source/vice-3.10.tar.gz': '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1',
    'build/research/aloft-execution-20261109/native-analysis/observer-source-01/source-record.json': 'a144259a5c5c99bab466d5b967b9df606d71f935754ab48340acc93da8cbc1b7',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha(raw)}


def checked_ref(row):
    path = (ROOT / row['path']).resolve()
    path.relative_to(ROOT)
    raw = path.read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], row['path']
    return raw


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def function_source(relative, name):
    source = (ROOT / relative).read_text()
    node = next(node for node in ast.parse(source).body
                if isinstance(node, ast.FunctionDef) and node.name == name)
    return ast.get_source_segment(source, node)


def response_raw(case, row):
    raw = case['wire']['received'][row['received_first']:row['received_end']]
    assert raw.decode(errors='replace') == row['response']
    return raw


def response_reference(case, row):
    raw = response_raw(case, row)
    return {'sequence': row['sequence'], 'id': row['id'], 'command': row['command'],
        'received_first': row['received_first'], 'received_end': row['received_end'],
        'bytes': len(raw), 'sha256': sha(raw),
        'identity_basis': 'Original received bytes; event replacement decode checked unchanged.'}


def closed_inventory(profile):
    assert profile['owner_closed'] is True and profile['owned_process_reaped'] is True
    assert profile['unified_handle_terminal'] is True
    case = (ROOT / profile['case_relative']).resolve()
    case.relative_to(BASE)
    listing = json.loads(checked_ref(profile['manifest']))
    rows = [{'name': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}
            for path in sorted(case.iterdir()) if path.is_file()]
    assert rows == listing['files']
    assert len(rows) == listing['file_count'] == profile['file_count']
    assert sum(row['bytes'] for row in rows) == listing['bytes'] == profile['case_bytes']
    assert sha(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()) == profile['canonical_listing_sha256']
    return case, rows


def audit_wire(profile, case_path):
    """Retain the frozen auditor and change exactly its startup assertion."""
    wire = load('aloft_execution_frozen_wire', 'research/verify_vice_live.py')
    wire.BASE = case_path.parent
    wire.CASE_PINS = {case_path.name: profile['canonical_listing_sha256']}
    original = function_source('research/verify_vice_live.py', 'audit_session')
    old = 'assert session["startup_mode"] == "manual monitor load" and "-autostart" not in session["command"]'
    program = str((ROOT / profile['original_program']['path']).resolve())
    checked_ref(profile['original_program'])
    assert profile['original_program']['sha256'] == PINS['build/research/aloft-20261109/disk-analysis/accepted-01/Aloft-Side1.d64']
    replacement = ('assert session["startup_mode"] == "autostart"\n'
        '    assert session["program"] == ' + repr(program) + '\n'
        '    for flag in ("-autostart", "-8"):\n'
        '        assert session["command"].count(flag) == 1\n'
        '        assert session["command"][session["command"].index(flag)+1] == ' + repr(program))
    assert original.count(old) == 1
    adapted = original.replace(old, replacement)
    exec(compile(adapted, '<Aloft-execution-original-disk-startup-only-adapter>', 'exec'), wire.__dict__)
    case = wire.audit_session(case_path.name)
    return wire, case, {'original_function_sha256': sha(original.encode()),
        'adapted_function_sha256': sha(adapted.encode()), 'replacements': 1,
        'exact_old_assertion': old, 'exact_startup_replacement': replacement,
        'ordinary_register_reader_unchanged': True, 'events_and_wire_not_filtered': True}


def paired_captures(reader, wire, case, case_path):
    """Keep every frozen same-stop check; allow the original F080 DEC00 effect."""
    controller = load('aloft_execution_frozen_pairs', 'research/eod/controller.py')
    controller.CASE = case_path
    original = function_source('research/eod/controller.py', 'capture_pairs')
    old = "assert mem[1] == mem[65542] == regs['port00'] == 0x2f"
    replacement = "assert mem[1] == mem[65542] == regs['port00']"
    assert original.count(old) == 1
    adapted = original.replace(old, replacement)
    exec(compile(adapted, '<Aloft-execution-live-DDR-pair-adapter>', 'exec'), controller.__dict__)
    memories, captures = controller.capture_pairs(reader, wire, case)
    return memories, captures, {'original_function_sha256': sha(original.encode()),
        'adapted_function_sha256': sha(adapted.encode()), 'replacements': 1,
        'exact_old_assertion': old, 'exact_replacement': replacement,
        'reason': 'Original F080 DEC00 changes the live CPU DDR; wire/snapshot identity, port readbacks, driven bits, CPU and beam checks remain strict.'}


def checkpoint_generations(case):
    """Treat a reused monitor ID as a new creation sequence, never a global ID."""
    active, generations = {}, []
    for sequence, row in sorted(case['responses'].items()):
        command, response = row['command'], row['response']
        creation = re.search(r'(BREAK|TRACE): (\d+)  C:\$([0-9a-f]{4})(?:-\$([0-9a-f]{4}))?  \((Stop on exec|Trace exec|Trace store|Trace load)\)', response)
        if command.startswith(('break ', 'trace ')):
            assert creation, ('missing normalized setup', sequence)
            number = int(creation[2])
            assert number not in active, ('ID still live', sequence, number)
            record = {'id': number, 'created_sequence': sequence,
                'first': int(creation[3], 16), 'last': int(creation[4] or creation[3], 16),
                'kind': creation[1], 'operation': creation[5], 'enabled': True,
                'setup': response_reference(case, row), 'updates': []}
            active[number] = record
            generations.append(record)
        elif command.startswith('delete '):
            number = int(command.split()[1])
            record = active.pop(number)
            record['deleted_sequence'] = sequence
            record['delete_response'] = response_reference(case, row)
        elif command.startswith(('condition ', 'command ', 'enable ', 'disable ', 'ignore ')):
            verb, number, *_ = command.split()
            record = active[int(number)]
            record['updates'].append(response_reference(case, row))
            if verb in ('enable', 'disable'):
                record['enabled'] = verb == 'enable'
            if verb == 'command':
                attached = re.fullmatch(r'command \d+ "(.*)"', command)
                assert attached and attached[1] == 'r', ('undeclared attached command', sequence)
                record['attached_command'] = attached[1]
                record['attached_r_sequence'] = sequence
            if verb == 'condition':
                record['condition_command'] = command
    return generations


def generation_at(generations, identifier, sequence):
    matches = [row for row in generations if row['id'] == identifier
        and row['created_sequence'] < sequence
        and sequence < row.get('deleted_sequence', float('inf'))]
    assert len(matches) == 1, (identifier, sequence, len(matches))
    return matches[0]


def enabled_at(point, sequence):
    enabled = True
    for update in point['updates']:
        if update['sequence'] >= sequence:
            continue
        if update['command'].startswith('enable '):
            enabled = True
        elif update['command'].startswith('disable '):
            enabled = False
    return enabled


def source_observer_contract():
    record_path = ANALYSIS / 'observer-source-01/source-record.json'
    record = json.loads(record_path.read_text())
    checked_ref(record['archive'])
    with tarfile.open(ROOT / record['archive']['path']) as archive:
        for row in record['files']:
            raw = checked_ref(row)
            assert raw == archive.extractfile(row['member']).read(), row['member']
    checked_ref(record['excerpts'])
    return {'record': artifact(record_path), 'archive': record['archive'],
        'exact_members': record['files'], 'excerpts': record['excerpts'], 'facts': record['facts'],
        'interpretation': 'Conditional exact VICE3.10 implementation contract, with actual dummy mode and queue/stop behavior separately bound to this case. Hook clocks and load/store grouped order are not physical per-access bus timestamps/order.'}


def trace_hooks(case, wire, generations, captures):
    """Parse every original raw hook block, including next-response drains."""
    header = re.compile(r'#(\d+) \(Trace\s+(exec|store|load) ([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\n', re.I)
    stop = re.compile(r'#\d+ \(Stop on\s+exec ', re.I)
    instruction = re.compile(
        r'^\.C:([0-9a-f]{4})\s+([0-9A-F]{2}(?: [0-9A-F]{2}){0,2})\s+(.+?)\s+- A:([0-9A-F]{2}) X:([0-9A-F]{2}) Y:([0-9A-F]{2}) SP:([0-9a-f]{2}) ([NV\-BDIZC.]{8})\s+(\d+)\n', re.M | re.I)
    hits = []
    previous_clock = None
    for sequence, row in sorted(case['responses'].items()):
        raw = response_raw(case, row)
        text = raw.decode('latin1')
        headers = list(header.finditer(text))
        assert len(headers) == len(re.findall(r'#\d+ \(Trace', text))
        if not headers:
            continue
        assert row['command'] == 'x' and row['status'] == 'completed', ('undeclared trace response', sequence)
        terminal = stop.search(text)
        assert terminal and headers[-1].start() < terminal.start()
        for index, match in enumerate(headers):
            identifier, operation, address = int(match[1]), match[2].lower(), int(match[3], 16)
            point = generation_at(generations, identifier, sequence)
            assert enabled_at(point, sequence)
            assert ' if ' not in point['setup']['command']
            assert not any(update['command'].startswith('condition ') and update['sequence'] < sequence for update in point['updates'])
            assert point['kind'] == 'TRACE' and point['first'] <= address <= point['last']
            assert point['operation'].lower() == 'trace ' + operation
            assert point.get('attached_command') == 'r' and point['attached_r_sequence'] < sequence
            end = headers[index + 1].start() if index + 1 < len(headers) else terminal.start()
            segment = text[match.end():end]
            ins = instruction.search(segment)
            assert ins and segment.count('Executing: r') == 1
            regs = wire.registers(segment)
            pc, code = int(ins[1], 16), bytes.fromhex(ins[2])
            assert regs['clock'] == int(ins[9])
            assert previous_clock is None or regs['clock'] >= previous_clock
            previous_clock = regs['clock']
            assert (regs['line'], regs['cycle']) == (int(match[4]), int(match[5]))
            assert (regs['clock'] // 63 % 312, regs['clock'] % 63) == (regs['line'], regs['cycle'])
            assert [regs[key] for key in ('a', 'x', 'y', 'sp')] == [int(ins[n], 16) for n in (4, 5, 6, 7)]
            if operation == 'exec':
                assert regs['pc'] == pc == address
            mnemonic = ins[3].split()[0].upper()
            operand_value = {'STA': regs['a'], 'STX': regs['x'], 'STY': regs['y'],
                             'SAX': regs['a'] & regs['x']}.get(mnemonic) if operation == 'store' else None
            block = raw[match.start():end]
            prior_stops = [capture['stem'] for capture in captures
                if capture['stop_sequence'] < sequence and capture['registers']['clock'] == regs['clock']]
            hits.append({'sequence': sequence, 'response_id': row['id'],
                'checkpoint': identifier, 'checkpoint_created_sequence': point['created_sequence'],
                'operation': operation, 'monitored_address': address,
                'instruction_PC': pc, 'instruction_hex': code.hex(), 'instruction': ins[3],
                'registers': regs, 'instruction_disassembly_flags': ins[8],
                'post_register_direct_store_operand': operand_value,
                'RMW_bus_value_not_present_in_hook': operation == 'store' and mnemonic in ('INC', 'DEC', 'ASL', 'LSR', 'ROL', 'ROR'),
                'clock_convention': 'Current CPU instruction-completion clock when queued watchpoints are processed; not physical bus-access clock.',
                'completion_clock_equals_earlier_capture': prior_stops,
                'setup_sequence': point['created_sequence'], 'attached_r_sequence': point['attached_r_sequence'],
                'received_first': row['received_first'] + match.start(),
                'received_end': row['received_first'] + end,
                'raw_block_bytes': len(block), 'raw_block_sha256': sha(block),
                'received_stream': str((BASE / 'native-01/received.bin').relative_to(ROOT))})
    assert len(hits) == sum(len(re.findall(rb'#\d+ \(Trace', response_raw(case, row)))
                            for row in case['responses'].values())
    return hits


def machine_context(reader, memories, captures, case_path):
    """Use the frozen drive-reader schema; retain complete stopped VIC/CIA state."""
    binding = load('aloft_execution_frozen_drive_reader', 'research/aloft-decode-20261109/native_binding.py')
    binding.verify_snapshot_source()
    context = {}
    for capture in captures:
        stem = capture['stem']
        path = case_path / (stem + '.vsf')
        state = reader.read_snapshot(path)
        drive_ram, drive = binding.drive_snapshot(reader, path)
        assert len(drive_ram) == 2048
        context[stem] = {'registers': capture['registers'], 'ports': capture['ports'],
            'VIC': state['vicii'], 'CIA1': state['cia']['CIA1'], 'CIA2': state['cia']['CIA2'],
            'drive': drive, 'drive_RAM_reference': {'snapshot': capture['snapshot'],
                'module': 'DRIVECPU0', 'offset': 92, 'bytes': 2048, 'sha256': sha(drive_ram)},
            'physical_ZP': list(memories[stem][:256]),
            'CPU_view_ZP': [capture['ports']['dir_read'], capture['ports']['data_read']]
                + list(memories[stem][2:256])}
    return context


def hook_ref(hit):
    return {key: hit[key] for key in ('sequence', 'checkpoint', 'checkpoint_created_sequence',
        'instruction_PC', 'instruction_hex', 'received_first', 'received_end',
        'raw_block_bytes', 'raw_block_sha256', 'received_stream')}


def independent_inputs(profile, memories, captures, context, hits):
    """Separate genuine initial state/read domains from all output-value oracles."""
    roles = profile['roles']
    by_stem = {capture['stem']: capture for capture in captures}
    initial = by_stem[roles['dispatcher']]
    endpoint = by_stem[roles['post_all']]
    initial_ram = memories[initial['stem']]
    initial_context = context[initial['stem']]
    assert initial['registers']['pc'] == 0x0500 and endpoint['registers']['pc'] == 0xf0b1
    kernel = initial_ram[0x0500:0x0759]
    assert len(kernel) == 601 and kernel[-1] == 0x60
    calls = []
    for index in range(200):
        instruction_pc = 0x0500 + 3 * index
        code = kernel[3 * index:3 * index + 3]
        assert code[0] == 0x20
        target = int.from_bytes(code[1:], 'little')
        assert 0x20 <= target >> 8 <= 0xbb and target & 255 in (0, 0x23)
        calls.append({'ordinal': index, 'instruction_PC': instruction_pc,
            'instruction_hex': code.hex(), 'target': target})
    first_target = by_stem[roles['first_target']]
    assert first_target['registers']['pc'] == calls[0]['target']
    glyph_addresses = list(range(7, 256, 8)) + list(range(0x0787, 0x07c0, 8))
    assert len(glyph_addresses) == len(set(glyph_addresses)) == 40
    glyphs = [{'address': address, 'value': initial_ram[address]} for address in glyph_addresses]
    for row in glyphs:
        if row['address'] < 256:
            assert row['value'] == initial_context['CPU_view_ZP'][row['address']]
    code_mask_addresses = [page * 256 + offset for page in range(0x20, 0xbc) for offset in range(72)]
    cell_code = bytes(initial_ram[address] for address in code_mask_addresses)
    lifetimes = []
    for role in ('precall', 'dispatcher', 'first_target', 'pre_inc', 'post_inc', 'first_return', 'post_all'):
        if role not in roles:
            continue
        capture = by_stem[roles[role]]
        ram = memories[capture['stem']]
        assert bytes(ram[address] for address in code_mask_addresses) == cell_code
        assert ram[0x0500:0x0759] == kernel
        lifetimes.append({'role': role, 'stem': capture['stem'], 'ram': capture['ram'],
            'cell_code_11232_sha256': sha(cell_code), 'call_kernel_601_sha256': sha(kernel),
            'all_actual_bytes_unchanged_from_genuine_dispatcher': True})
    samples = []
    for index, hit in enumerate(hits):
        if not initial['registers']['clock'] <= hit['registers']['clock'] <= endpoint['registers']['clock']:
            continue
        if hit['operation'] != 'load' or hit['monitored_address'] != 0xd011:
            continue
        if hit['instruction_hex'] != 'ee11d0':
            continue  # Opaque other D011 reads remain in complete oracle hooks.
        pc, upper = hit['instruction_PC'], hit['registers']['clock']
        assert initial_ram[pc:pc + 3] == bytes.fromhex('ee11d0')
        previous = next((row for row in reversed(hits[:index])
            if row['instruction_PC'] != pc and row['registers']['clock'] < upper), None)
        assert previous is not None
        assert previous['operation'] == 'store' and previous['instruction_PC'] + 2 == pc
        assert bytes.fromhex(previous['instruction_hex'])[0] == 0x84
        assert previous['registers']['pc'] == pc
        assert initial_ram[previous['instruction_PC']:pc] == bytes.fromhex(previous['instruction_hex'])
        lower = previous['registers']['clock']
        assert lower >= initial['registers']['clock']
        lines = sorted(set(line % 312 for line in range(lower // 63, upper // 63 + 1)))
        possible_msbs = sorted(set((line & 256) >> 1 for line in lines))
        samples.append({'ordinal': len(samples), 'instruction_PC': pc, 'read_address': 0xd011,
            'clock_interval_inclusive': [lower, upper], 'possible_read_raster_lines': lines,
            'possible_raster_MSB_values': possible_msbs,
            'unique_raster_MSB': possible_msbs[0] if len(possible_msbs) == 1 else None,
            'lower_bound': 'Completion of immediately preceding watched STYzp whose next PC is this INC.',
            'upper_bound': 'Completion of this INC; actual operand read occurs during the bounded instruction.',
            'source_byte_lifetime': 'All11232 actual generated bytes remain unchanged across declared captures.',
            'preceding_STY_rawref': hook_ref(previous), 'INC_load_rawref': hook_ref(hit),
            'post_INC_A_flags_result_and_store_values_excluded': True})
    initial_input = {'scope': 'Genuine pre0500 state and independently bounded raster domains only; no output state or expected write values.',
        'capture': initial, 'initial_CPU': initial['registers'],
        'CPU_view_ZP': initial_context['CPU_view_ZP'], 'physical_ZP_aliases': initial_context['physical_ZP'],
        'CPU_port_readbacks': initial['ports'], 'lookup0400': list(initial_ram[0x0400:0x0500]),
        'all40_initial_glyph_values': glyphs, 'actual_calls': calls,
        'dispatcher_0500_bytes': list(kernel), 'final_dispatcher_RTS': {'PC': 0x0758, 'byte': 0x60},
        'initial_stored_D011': initial_context['VIC']['regs'][0x11],
        'initial_VIC_context': initial_context['VIC'], 'initial_CIA1': initial_context['CIA1'],
        'initial_CIA2': initial_context['CIA2'], 'independent_D011_read_domains': samples,
        'actual_code_lifetimes': lifetimes,
        'lifetime_scope': 'Equality at all declared captured states. Continuous executable lifetime additionally requires the consumer finite write-footprint and no unmodeled external NMI/RAM-writing DMA assumptions.',
        'not_actual_bus_timestamps': True, 'read_domains_do_not_use_post_INC_flags_or_values': True}
    endpoint_oracles = {}
    for role in ('first_return', 'post_all'):
        capture = by_stem[roles[role]]
        stem = capture['stem']
        endpoint_oracles[role] = {'capture': capture,
            'CPU_view_ZP': context[stem]['CPU_view_ZP'], 'physical_ZP_aliases': context[stem]['physical_ZP'],
            'all40_glyph_values': [{'address': address, 'value': memories[stem][address]} for address in glyph_addresses],
            'stored_D011': context[stem]['VIC']['regs'][0x11],
            'VIC_context': context[stem]['VIC']}
    return initial_input, {'scope': 'Comparison oracles only; never initial-state, motion, D011-read or expected-store inputs.',
        'all_hooks': hits, 'endpoints': endpoint_oracles,
        'hook_clock_is_instruction_completion_not_bus_cycle': True,
        'load_queue_before_store_queue_is_not_global_physical_access_order': True,
        'RMW_store_hooks_do_not_contain_bus_data_values': True}


def natural_bindings(case, generations, captures, memories):
    pattern = re.compile(r'#(\d+) \(Stop on\s+exec ([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\n\.C:[^\n]+\s+(\d+)\n', re.I)
    bindings = []
    for capture in captures:
        sequence = capture['stop_sequence']
        matches = list(pattern.finditer(response_raw(case, case['responses'][sequence]).decode('latin1')))
        assert len(matches) == 1
        match = matches[0]
        identifier, pc = int(match[1]), int(match[2], 16)
        point = generation_at(generations, identifier, sequence)
        assert point['kind'] == 'BREAK' and enabled_at(point, sequence)
        assert point['first'] <= pc <= point['last']
        assert (pc, int(match[3]), int(match[4]), int(match[5])) == tuple(
            capture['registers'][key] for key in ('pc', 'line', 'cycle', 'clock'))
        commands = [point['setup']['command']] + [update['command'] for update in point['updates'] if update['sequence'] < sequence]
        condition = next((command.split(' if ', 1)[1] for command in reversed(commands) if ' if ' in command), None)
        predicates = []
        if condition:
            leaf = re.compile(r'(@ram:\$[0-9a-f]+|RL|CY|A|X|Y|SP|PC)\s*==\s*\$([0-9a-f]+)', re.I)
            found = list(leaf.finditer(condition))
            assert found
            remainder = leaf.sub('', condition)
            assert not re.sub(r'[()&\s]', '', remainder)
            assert len(found) == 1 or condition.count('&&') == len(found) - 1
            for item in found:
                name, expected = item[1], int(item[2], 16)
                if name.lower().startswith('@ram:'):
                    address = int(name.split('$')[1], 16)
                    actual = memories[capture['stem']][address]
                else:
                    address = None
                    actual = capture['registers'][{'RL': 'line', 'CY': 'cycle'}.get(name.upper(), name.lower())]
                assert actual == expected, (capture['stem'], name, actual, expected)
                predicates.append({'operand': name, 'address': address, 'expected': expected, 'actual': actual})
        capture['natural_checkpoint'] = {'id': identifier, 'created_sequence': point['created_sequence'],
            'actual_PC': pc, 'condition_at_this_stop': condition, 'predicates': predicates}
        bindings.append({'stem': capture['stem'], 'stop_sequence': sequence,
            **capture['natural_checkpoint'], 'raw_response': response_reference(case, case['responses'][sequence])})
    assert len(bindings) == len([row for row in case['responses'].values() if row['command'] == 'x']) == 18
    return bindings


def command_audit(profile, case):
    rows = case['responses']
    assert sorted(rows) == list(range(1, 203))
    assert all(row['status'] == 'completed' for row in rows.values())
    assert not case['waits'] and not case['partial'] and not case['cancelled']
    assert [sequence for sequence, row in rows.items() if row['internal']] == [1, 2]
    permitted = re.compile(r'(?:r|x|bank (?:ram|io)|sidefx off|warp(?: on| off)?|dummy(?: on| off)?|resourceget "(?:Speed|VICIIModel|VICIIBorderMode|VICIIVSPBug)"|help (?:dummy|trace|command|ignore)|(?:enable|disable|delete) \d+|ignore \d+ \$[0-9a-f]+|command \d+ "r"|condition \d+ if [0-9a-z@$:() =&|!<>.]+|break(?: (?:exec )?[0-9a-f]{4}(?: [0-9a-f]{4})?(?: if [0-9a-z@$:() =&|!<>.]+)?)?|trace (?:load|store|exec) [0-9a-f]{4}(?: [0-9a-f]{4})?|bsave "[^"\n]+" 0 0000 ffff|dump "[^"\n]+"|m (?:d000 d03f|dd00 dd03|d011 d011))', re.I)
    errors = []
    declared_errors = {row['sequence']: row for row in profile['syntax_errors']}
    queries, peeks = [], []
    bank = None
    for sequence, row in sorted(rows.items()):
        command, response = row['command'], row['response']
        if re.search(r'ERROR --|Syntax error|Unknown resource', response):
            expected = declared_errors[sequence]
            assert command == expected['command'] and response == expected['response']
            assert re.fullmatch(r'resourceget (?:WarpMode|Speed|VICIIModel|VICIIBorderMode|VICIIVSPBug)', command)
            errors.append(response_reference(case, row) | {'classification': 'Rejected read-only resource query; transport response completed; no value accepted.'})
            continue
        assert permitted.fullmatch(command), (sequence, command)
        if command.startswith('bank '):
            bank = command[5:]
        if command.startswith('m '):
            assert bank == 'io'
            previous_resume = max(n for n, item in rows.items() if n < sequence and item['command'] == 'x')
            peeks.append(response_reference(case, row) | {'bank': 'io', 'source_sidefx_off': True,
                'preceding_resume_sequence': previous_resume,
                'raw_latin1_response': response_raw(case, row).decode('latin1'),
                'scope': 'Visible readback oracle only; live D011 rasterbit is not stored registerbit.'})
        if command in ('warp', 'dummy') or command.startswith('resourceget '):
            queries.append(response_reference(case, row) | {'response': response})
        if command.startswith('bsave '):
            assert bank == 'ram'
    assert [row['sequence'] for row in errors] == [177, 178, 179, 180, 181]
    assert rows[2]['command'] == 'sidefx off'
    assert rows[35]['response'].startswith('Checkpoints will trigger on dummy accesses.\n')
    for expected in profile['corrected_final_resource_queries']:
        row = rows[expected['sequence']]
        assert row['command'] == expected['command'] and row['response'] == expected['response']
    assert rows[202]['response'].startswith('No breakpoints are set\n')
    assert case['session']['exit_code'] == -15 and case['session']['owned_process_reaped'] is True
    launch = case['session']['command']
    assert '-pal' in launch and '-drive8truedrive' in launch
    assert launch[launch.index('-drive8type') + 1] == '1541'
    return {'responses': 202, 'public_commands': 200, 'completed_responses': 202,
        'interrupted_responses': 0, 'waits': [], 'queries': queries,
        'exact_five_rejected_resource_queries': errors, 'manual_IO_oracles': peeks,
        'no_PC_RAM_writes_restores_restart_or_disk_change_commands': True,
        'all_checkpoints_deleted_at_final_query': True}


def watched_windows(profile, case, generations, captures):
    by_stem = {row['stem']: row for row in captures}
    expected = [(3, 'store', 0xd000, 0xd03f), (4, 'store', 0xdd00, 0xdd03),
                (6, 'store', 0, 0xff), (7, 'store', 0x0787, 0x07bf), (8, 'load', 0xd011, 0xd011)]
    result = []
    for field in profile['fields']:
        first = by_stem[field['roles']['dispatcher']]
        last = by_stem[field['roles']['post_all']]
        mode_mutations = [(sequence, row['command']) for sequence, row in case['responses'].items()
                          if row['command'] in ('dummy on', 'dummy off')]
        assert max((item for item in mode_mutations if item[0] < first['stop_sequence']))[1] == 'dummy on'
        assert not any(first['stop_sequence'] < sequence < last['stop_sequence'] for sequence, command in mode_mutations)
        watches = []
        for number, operation, low, high in expected:
            point = generation_at(generations, number, first['stop_sequence'])
            assert point['kind'] == 'TRACE' and point['operation'].lower() == 'trace ' + operation
            assert ' if ' not in point['setup']['command']
            assert not any(update['command'].startswith('condition ') and update['sequence'] < last['stop_sequence'] for update in point['updates'])
            assert (point['first'], point['last']) == (low, high)
            assert point['attached_r_sequence'] < first['stop_sequence']
            assert enabled_at(point, first['stop_sequence']) and enabled_at(point, last['stop_sequence'])
            assert not any(update['command'].startswith('disable ') and first['stop_sequence'] < update['sequence'] < last['stop_sequence'] for update in point['updates'])
            assert point['deleted_sequence'] > last['snapshot_sequence']
            watches.append({'id': number, 'created_sequence': point['created_sequence'],
                'operation': operation, 'first': low, 'last': high,
                'attached_r_sequence': point['attached_r_sequence']})
        result.append({'label': field['label'], 'from_capture': first['stem'], 'through_capture': last['stem'],
            'start_clock': first['registers']['clock'], 'end_clock': last['registers']['clock'],
            'elapsed_cycles_between_captured_boundaries': last['registers']['clock'] - first['registers']['clock'],
            'watches': watches, 'dummy_enabled_query': response_reference(case, case['responses'][35]),
            'dummy_mode_unchanged_during_window': True})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    out.relative_to(ANALYSIS.resolve())
    assert not out.exists(), 'fresh output directory required'
    assert PROFILE_SHA is not None, 'Owner case is live/unpinned; closed-case acceptance is disabled.'
    assert sha(PROFILE.read_bytes()) == PROFILE_SHA
    for relative, digest in PINS.items():
        assert sha((ROOT / relative).read_bytes()) == digest, relative
    profile = json.loads(PROFILE.read_bytes())
    case_path, listing = closed_inventory(profile)
    wire, case, adapter = audit_wire(profile, case_path)
    reader = load('aloft_execution_snapshot_reader', 'research/quondam/snapshot_state.py')
    memories, captures, pair_adapter = paired_captures(reader, wire, case, case_path)
    points = checkpoint_generations(case)
    assert len(captures) == 18
    owner = json.loads(checked_ref(profile['owner_closure']))
    assert owner['all_202_responses_completed'] and owner['interrupts'] == owner['timeouts'] == 0
    assert owner['restarts'] == owner['snapshot_restores'] == owner['disk_changes'] == owner['PC_or_RAM_mutations'] == 0
    actual_pairs = {row['stem']: row for row in captures}
    for expected in profile['pairs']:
        actual = actual_pairs[expected['stem']]
        assert (actual['save_sequence'], actual['snapshot_sequence']) == (expected['ram_sequence'], expected['snapshot_sequence'])
        assert actual['ram'] == expected['ram'] and actual['snapshot'] == expected['vsf']
    bindings = natural_bindings(case, points, captures, memories)
    commands = command_audit(profile, case)
    hooks = trace_hooks(case, wire, points, captures)
    context = machine_context(reader, memories, captures, case_path)
    observer = source_observer_contract()
    lifetimes = watched_windows(profile, case, points, captures)
    input_fields, oracle_fields = [], []
    for field in profile['fields']:
        inputs, oracles = independent_inputs(field, memories, captures, context, hooks)
        input_fields.append({'label': field['label'], 'roles': field['roles'], 'input': inputs})
        oracle_fields.append({'label': field['label'], 'roles': field['roles'], 'endpoints': oracles['endpoints']})
    bootstrap = (ROOT / 'build/research/aloft-20261109/disk-analysis/accepted-01/bootstrap-side1.prg').read_bytes()
    assert bootstrap[:2] == bytes.fromhex('0108') and len(bootstrap) == 832
    assert memories['sys'][0x0801:0x0b3f] == bootstrap[2:]
    zero, one = actual_pairs['later-wrap-zero'], actual_pairs['later-wrap-one']
    assert (zero['registers']['line'], zero['registers']['cycle']) == (0, 2)
    assert (one['registers']['line'], one['registers']['cycle']) == (1, 2)
    assert one['registers']['clock'] - zero['registers']['clock'] == 63
    out.mkdir(parents=True)
    files = []
    checked_path = out / 'native.checked.py'; checked_path.write_bytes(Path(__file__).read_bytes()); files.append(checked_path)
    for name, value in [('machine-context.json', {'captures': context}),
        ('independent-inputs.json', {'fields': input_fields, 'no_post_state_or_store_values_as_model_inputs': True}),
        ('hook-oracles.json', {'all_hooks': hooks, 'fields': oracle_fields,
            'hook_clock_is_instruction_completion_not_bus_clock': True,
            'RMW_hook_values_not_bus_data': True, 'input_use_forbidden': True})]:
        path = out / name; path.write_text(json.dumps(value, indent=2) + '\n'); files.append(path)
    proof = {'pass_': True, 'scope': 'Closed original Aloft native execution custody, genuine pre0500 inputs, independently bounded INC read domains, and separate hook/endpoint oracles for two observed calls. No CPU/model/pixel execution.',
        'producer': artifact(Path(__file__).resolve()), 'profile': artifact(PROFILE),
        'inputs': [artifact(ROOT / name) for name in PINS] + [profile['owner_closure'], profile['manifest'], artifact(ROOT / profile['freeze_source']['path'])],
        'case_files': listing, 'owner_closure': owner, 'session': case['session'],
        'wire': {key: {'bytes': len(value), 'sha256': sha(value)} for key, value in case['wire'].items()},
        'event_count': len(case['events']), 'wire_adapter': adapter, 'pair_adapter': pair_adapter,
        'captures': captures, 'natural_stops': bindings, 'checkpoint_generations': points,
        'watched_windows': lifetimes, 'observer_source_contract': observer,
        'command_audit': commands, 'trace_hook_count': len(hooks),
        'bootstrap_binding': {'all830_payload_bytes_equal_SYS': True, 'SYS_PC': actual_pairs['sys']['registers']['pc'],
            'fresh_postcopy08B5_capture': False, 'later_resident_bytes_not_broadly_normalized': True},
        'fields': [{'label': row['label'], 'roles': row['roles'],
            'actual_call_count': len(row['input']['actual_calls']),
            'distinct_actual_targets': sorted(set(call['target'] for call in row['input']['actual_calls'])),
            'INC_read_domain_count': len(row['input']['independent_D011_read_domains']),
            'ambiguous_read_MSB_domains': sum(len(item['possible_raster_MSB_values']) != 1 for item in row['input']['independent_D011_read_domains'])} for row in input_fields],
        'wrap_scope': {'zero': zero['stem'], 'one': one['stem'], 'elapsed_cycles': 63,
            'same_preceding_field_not_two_displayed_generations': True},
        'limits': ['All raw events, completed responses and exact five rejected read-only query responses remain; corrected queries supply the resource bindings.',
            'Original same-handle autostart/SYS830byte binding; no fresh08B5 resident-copy pair and no full current resident equality claim.',
            'Watch hooks include duplicates and deferred next-response drains. Clocks are instruction completion times; load/store queues flush separately and are not a universal physical bus order.',
            'INC read raster domains use the preceding immediate STY completion and INC completion only; no postINC flags/A/results or expected store values seed read inputs.',
            'Captured code equality and the actual601byte dispatcher are supplied. Continuous execution additionally requires consumer finite write-footprint/no hidden external NMI or RAM-writing DMA assumptions.',
            'Raw stored D011 endpoints come from VSF; live I/Opeek bit7 is distinct. RMW hook records do not contain physical bus data values.',
            'Wrap row0/row1 captures are63cycles apart for the same preceding completed field; no two-field pixel or framebuffer lifetime claim.',
            'No new source-model acceptance, VIC fetch/pixel composition, complete animation/FPS/optimization or named three-layer scene identity follows from custody.',
            'No worker native process, monitor socket, CPU interpreter, emulator, build, restart, restore or downloaded host code execution.'],
        'outputs': [{'name': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())} for path in files]}
    receipt = out / 'native-proof.json'; receipt.write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps({'pass_': True, 'receipt': artifact(receipt), 'captures': len(captures), 'hooks': len(hooks), 'fields': proof['fields']}))


if __name__ == '__main__':
    main()
