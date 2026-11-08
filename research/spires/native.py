#!/usr/bin/env python3
"""Passively bind closed original Spires captures to source and stripe data.

No native process, original CPU, assembler, host executable, network request or
subprocess is run. Prior frozen evidence is read, never regenerated here.
"""

from collections import Counter
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tarfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/spires'
OUT = BASE / 'native-analysis'
DISK = BASE / 'release/Spires_-_Onslaught.d64'
CASES = {'native-02': 'e65433c6938a120d8a62f6d0571dd938f6e2d460dd1edf9ce7356db2ac0eb9af',
         'native-03': 'b72fb9b7a73e3bbfda3b62def4fdb42d8f6784f636db28b2fa88d64c4cbd586b'}
FAILED = '9eaa979ea65241ae1bd3913d7738185a545cda2490efc2316e229bc9cfb89d59'
PINS = {
    'research/verify_vice_live.py': 'f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a',
    'research/vice_session_live.py': '4340d1b0394fa612f5e6a71edddcbc2daf947e59c4c3013ab3b850c886dc621c',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'research/spires/inspect.py': 'f5081155ffb43a02db87499a43dd71fad12eec60bf384fa9fc03577da47c084c',
    'build/research/spires/analysis/spires-proof.json': '4408d4819dcb1ab8c30b239dea03a7e15006923628c3a594d548aea06cdb11f3',
    'build/research/spires/source/fppinc.asm': 'c0e029ad277a2d462059c35cd400ae42ca73132ddafc82539c6d94362f720cf8',
    'build/research/spires/source/spires.asm': '0a7a4450ee4d747e37d6ee9f4e462e6b6802454e6c5d2234a7eda38a9ce3d037',
    'build/research/spires/source/spires_first_scene.asm': 'f40bc1f7c84c443c54d687e640e2bc0af9b0931130a69927246ff2b6f0ad1e4c',
    'build/research/spires/analysis/fpp-source-patterns.bin': 'c98021590a158a3d6b5203c7371245e5304e7ad393faa089cdc07ce8b6a463ff',
    'build/research/spires/analysis/fpp-source-patterns.known': '7751fbcd3becab08f84e7d5ee4a3ee3f1aa349e84f453841415fea54de57d90d',
    'build/research/spires/dos-files/11.prg': 'bf41f4736d09408b30671e0c622fd6922032f9b14820d355403040c45adef791',
    'build/research/spires/release/Spires_-_Onslaught.d64': '2e7299b1cd0bfc8dac4aa7886a472255be4f1ca9429964d526ba9c84e8d2175d',
    'build/research/quondam/hardware-source/vice-3.10.tar.gz': '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1',
}
TRACE = re.compile(
    r'^#(?P<checkpoint>\d+) \(Trace\s+(?P<kind>store|exec)\s+(?P<target>[0-9a-f]{4})\)\s+'
    r'(?P<line>\d+)/\$[0-9a-f]+,\s+(?P<cycle>\d+)/\$[0-9a-f]+\n'
    r'\.C:(?P<pc>[0-9a-f]+)\s+[^\n]*?'
    r'- A:(?P<a>[0-9a-f]+) X:(?P<x>[0-9a-f]+) Y:(?P<y>[0-9a-f]+) '
    r'SP:(?P<sp>[0-9a-f]+) [^\n]*?\s+(?P<clock>\d+)\n', re.M | re.I)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=sha(data))


def load(name, relative):
    assert sha((ROOT / relative).read_bytes()) == PINS[relative]
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save(name, value):
    path = OUT / name
    path.write_text(json.dumps(value, indent=2) + '\n')
    return artifact(path)


def wire_reader():
    wire = load('spires_wire', 'research/verify_vice_live.py')
    wire.BASE, wire.CASE_PINS = BASE, {**CASES, 'native-01': FAILED}
    auditor_text = (ROOT / 'research/verify_vice_live.py').read_text()
    function = next(node for node in ast.parse(auditor_text).body
                    if isinstance(node, ast.FunctionDef) and node.name == 'audit_session')
    original = ast.get_source_segment(auditor_text, function) + '\n'
    before = 'assert session["startup_mode"] == "manual monitor load" and "-autostart" not in session["command"]'
    after = ('assert session["startup_mode"] == "autostart"\n'
             '    assert session["command"].count("-autostart") == 1\n'
             f'    assert session["command"][session["command"].index("-autostart") + 1] == {str(DISK)!r}')
    assert original.count(before) == 1
    adapted = original.replace(before, after)
    exec(compile(adapted, '<pinned-wire-autostart-metadata>', 'exec'), wire.__dict__)
    return wire, dict(original_function_sha256=sha(original.encode()), adapted_function_sha256=sha(adapted.encode()),
                      replaced_assertion=before, replacement=after,
                      scope='Only manual-start metadata is replaced with the exact original-disk autostart contract.')


def startup_failure(wire):
    files = wire.pinned_case('native-01')
    directory = BASE / 'native-01'
    session = json.loads((directory / 'session.json').read_text())
    events = [json.loads(line) for line in (directory / 'events.jsonl').read_text().splitlines()]
    assert len(files) == 7 and [row['kind'] for row in events] == [
        'owned_process_started', 'observer_error', 'owned_terminate_requested', 'closed']
    assert session['observer_error'] == "OSError(22, 'Invalid argument')"
    assert session['exit_code'] == -15 and session['owned_process_reaped']
    assert events[0]['pid'] == events[2]['pid'] == session['pid'] == 91443
    assert all((directory / name).read_bytes() == b'' for name in ('input.bin', 'sent.bin', 'received.bin', 'monitor.log', 'vice.log'))
    assert not list(directory.glob('*.vsf'))
    return dict(directory_sha256=FAILED, files=files, session=session,
                observed_error=session['observer_error'], native_monitor_or_capture_evidence=False,
                interpretation='Retained observer-startup failure; distinct from the later original boot. No response timeout, monitor retry or recovered capture is asserted.')


def command_audit(wire, case, name):
    directory = BASE / name
    commands = [row for _, row in sorted(case['responses'].items())]
    assert not case['partial'] and not case['cancelled'] and not case['waits']
    contexts, resumes, last = {}, [], None
    for index, row in enumerate(commands):
        command, response = row['command'], row['response']
        assert row['status'] == 'completed'
        assert not re.search(r'Unknown resource|ERROR --|Syntax error|[Mm]onitor observation failed', response)
        allowed = command in ('r', 'sidefx off', 'bank ram', 'bank cpu', 'warp', 'warp on', 'warp off',
                              'resourceget "Speed"', 'x')
        allowed |= bool(re.fullmatch(r'break (?:exec )?[0-9a-f]{1,4}(?: if [^;\n]+)?', command))
        allowed |= bool(re.fullmatch(r'delete [0-9a-f]{1,4}', command))
        allowed |= command in ('trace store d000 d02e', 'trace store dd00 dd03', 'trace store aff8 afff')
        if command == 'r':
            last = wire.registers(response)
        if command == 'x':
            warp = next(r for r in reversed(commands[:index]) if r['command'] == 'warp')
            speed = next(r for r in reversed(commands[:index]) if r['command'] == 'resourceget "Speed"')
            warp_text = warp['response'].split('(C:')[0].strip()
            assert warp_text in ('Warp mode is on.', 'Warp mode is off.')
            assert speed['response'].split('(C:')[0].strip() == 'Speed=100'
            assert not any(r['command'] in ('warp on', 'warp off')
                           for r in commands if warp['sequence'] < r['sequence'] < row['sequence'])
            resumes.append(dict(sequence=row['sequence'], warp=warp_text == 'Warp mode is on.', Speed=100,
                                warp_query_sequence=warp['sequence'], speed_query_sequence=speed['sequence']))
            last = None
        match = re.fullmatch(r'(bsave|dump) "([^"\n]+)"( 0 0000 ffff)?', command)
        if match:
            kind, filename, suffix = match.groups()
            path = Path(filename)
            assert path.parent == directory and last is not None and commands[index - 1]['command'] == 'r'
            assert (kind == 'bsave') == (suffix is not None) and path.name not in contexts
            contexts[path.name] = dict(registers=last, command_sequence=row['sequence'])
            allowed = True
        screenshot = re.fullmatch(r'scrsh "([^"\n]+)" 2', command)
        if screenshot:
            assert Path(screenshot[1]).parent == directory and commands[index - 1]['command'] == 'r'
            allowed = True
        assert allowed, ('Unclassified monitor command', command)
    assert len(contexts) == 2 * len(list(directory.glob('*.vsf')))
    assert all(not row['warp'] for row in resumes if name == 'native-02' and row['sequence'] >= 28)
    if name == 'native-03':
        proof_start = contexts['colored64-preclear.vsf']['command_sequence']
        assert len([row for row in resumes if row['sequence'] > proof_start]) == 2
        assert all(not row['warp'] for row in resumes if row['sequence'] > proof_start)
    return contexts, dict(command_count=len(commands), counts=dict(Counter(row['command'].split()[0] for row in commands)),
                          resumes=resumes, CPU_RAM_PC_register_writes=[], snapshot_restores=[],
                          rejected_commands=[], interrupted_or_timed_out_resumes=[])


def captures(reader, contexts, name):
    directory, result = BASE / name, {}
    for path in sorted(directory.glob('*.vsf')):
        ram_path = directory / ('ram-' + path.stem + '.bin')
        registers = contexts[path.name]['registers']
        assert registers == contexts[ram_path.name]['registers']
        ram = ram_path.read_bytes()
        memory = reader.module_payload(path, 'C64MEM')
        assert len(ram) == 65536 and ram == memory[4:65540]
        assert (memory[1], memory[0]) == (registers['port00'], registers['port01'])
        cpu = reader.module_payload(path, 'MAINCPU')
        cpu_values = dict(clock=int.from_bytes(cpu[:8], 'little'), a=cpu[8], x=cpu[9], y=cpu[10], sp=cpu[11],
                          pc=int.from_bytes(cpu[12:14], 'little'), flags=cpu[14])
        assert all(registers[key] == value for key, value in cpu_values.items())
        state = reader.read_snapshot(path)
        assert (state['vicii']['raster_line'], state['vicii']['raster_cycle']) == (registers['line'], registers['cycle'])
        result[path.stem] = dict(ram=ram, state=state, entry=dict(stem=path.stem, ram=artifact(ram_path),
            snapshot=artifact(path), registers=registers, RAM_pair_CPU_ports_and_beam_equal=True))
    return result


def constants():
    source = (BASE / 'source/fppinc.asm').read_text()
    equ = {label: int(re.search(r'(?m)^' + label + r'\s+equ\s+\$([0-9a-f]+)', source, re.I)[1], 16)
           for label in ('base', 'scnpage', 'fstraster', 'based011')}
    pointers = [equ['base'] + equ['scnpage'] + 0x3f9 + index for index in range(7)]
    prior = json.loads((BASE / 'analysis/spires-proof.json').read_text())['FPP_source_math']['pointer_slots']
    assert prior == list(range(0xacf9, 0xad00)) and pointers == list(range(0xaff9, 0xb000))
    return equ, dict(previous_frozen_pointer_slots=prior, corrected_pointer_slots=pointers,
        arithmetic='$8000 + $2C00 + $03F9 = $AFF9; the $AC00 screen has its pointer table at $AFF8.',
        error_scope='The earlier receipt and note stated literal pointer addresses incorrectly. Source arithmetic, generated patterns and TechTech evidence remain separately retained; no frozen file is edited.')


def code_binding(decoded, equ, entry_stem='fpp-entry'):
    ram = decoded[entry_stem]['ram']
    table = ram[0x9000:0x9018]
    assert table[::3] == bytes([0x4c]) * 8
    targets = [int.from_bytes(table[index + 1:index + 3], 'little') for index in range(0, 24, 3)]
    start = targets[0]
    init_prefix = bytes.fromhex('a227a90b9d00aca9089d28ac989d00d89d28d8ca30034c') + (start + 2).to_bytes(2, 'little') + bytes.fromhex('a217a909e000f003')
    assert ram[start:start + len(init_prefix)] == init_prefix
    assert ram[targets[4]:targets[4] + 5] == bytes.fromhex('862d842e60')
    assert ram[targets[7]:targets[7] + 4] == bytes.fromhex('a5234a60')
    setgraph = bytes.fromhex('a9ba8d18d0ad00dd29fc09018d00dda5234a60')
    assert ram[0xa666:0xa666 + len(setgraph)] == setgraph
    call_prefix = bytes.fromhex('a008200090a000a200200c90a000a200200f90200390')
    call_hits = [index for index in range(len(ram)) if ram[index:index + len(call_prefix)] == call_prefix]
    assert len(call_hits) == 1
    pointers = [equ['base'] + equ['scnpage'] + 0x3f9 + i for i in range(7)]
    expected = bytearray()
    wrong = bytearray()
    for row in range(1, 131):
        def macro(addresses):
            code = bytearray([0xad]) + (0xa87d + row).to_bytes(2, 'little') + bytes.fromhex('8c17d0')
            for address in addresses[:6]:
                code += bytes([0x8d]) + address.to_bytes(2, 'little')
            code += bytes.fromhex('8e17d0') + bytes([0x8d]) + addresses[6].to_bytes(2, 'little')
            return code + bytes([0xa9, equ['based011'] | ((row + equ['fstraster'] + 1) & 7)]) + bytes.fromhex('8d11d0')
        expected += macro(pointers)
        wrong += macro([p - 0x300 for p in pointers])
    assert len(expected) == 4550 and ram[0x90e9:0x90e9 + len(expected)] == expected
    for capture in decoded.values():
        if capture['entry']['stem'] != 'original-boot':
            assert capture['ram'][0x90e9:0x90e9 + len(expected)] == expected
    return dict(eight_JMP_service_bytes=table.hex(), decoded_targets=targets,
                initscreen_prefix=init_prefix.hex(), initscreen_address=start,
                source_main_call_prefix=call_prefix.hex(), main_call_address=call_hits[0],
                setgraph_address=0xa666, setgraph_bytes=setgraph.hex(),
                macro_first_address=0x90e9, pointer_row_table=0xa87d, macro_rows=130,
                macro_bytes=4550, expanded_source_sha256=sha(expected), corrected_pointer_addresses=pointers,
                old_wrong_pointer_address_control_changed_bytes=sum(a != b for a, b in zip(expected, wrong)),
                full_source_build_or_missing_freshzoom_binary_identity_proven=False)


def patterns(decoded):
    expected = (BASE / 'analysis/fpp-source-patterns.bin').read_bytes()
    known = (BASE / 'analysis/fpp-source-patterns.known').read_bytes()
    ids = [index for index, value in enumerate(known) if value]
    assert len(ids) == 4032 and len(expected) == len(known) == 4096
    entry, prepared = (decoded[key]['ram'][0x8000:0x9000] for key in ('fpp-entry', 'fpp-prepared'))
    assert all(prepared[index] == expected[index] for index in ids)
    return dict(known_generated_bytes_compared=len(ids), differences=0,
                entry_to_prepared_changed_known_bytes=sum(entry[i] != prepared[i] for i in ids),
                stale_entry_control_differences=sum(entry[i] != expected[i] for i in ids),
                full_prepared_region_sha256=sha(prepared),
                ungenerated_byte63_offsets=[i for i, value in enumerate(known) if not value],
                ungenerated_endpoint_values=sorted({prepared[i] for i, value in enumerate(known) if not value}),
                unwritten_byte_values_are_endpoint_observations_only=True,
                absence_of_transient_or_redundant_writes_proven=False)


def capture_observations(decoded):
    rows = []
    for stem, capture in decoded.items():
        if stem in ('original-boot', 'fpp-entry', 'fpp-prepared'):
            continue
        vic, ram = capture['state']['vicii'], capture['ram']
        cia = capture['state']['cia']['CIA2']
        bank = (~((cia['pra'] | (~cia['ddra'] & 255)) & 3) & 3) * 0x4000
        screen = bank + ((vic['regs'][0x18] >> 4) * 1024)
        sprite_rows = []
        for index in range(1, 8):
            sprite = vic['sprites'][index]
            offset = bank + sprite['pointer'] * 64 + sprite['mcbase']
            expected_data = int.from_bytes(ram[offset:offset + 3], 'big')
            assert expected_data == sprite['data']
            sprite_rows.append(dict(sprite=index, **sprite, data_address=offset, expected_data_from_RAM=expected_data))
        rows.append(dict(stem=stem, clock=capture['entry']['registers']['clock'],
                         line=vic['raster_line'], raw_cycle=vic['raster_cycle'], D017=vic['regs'][0x17],
                         D010=vic['regs'][0x10], D015=vic['regs'][0x15], D018=vic['regs'][0x18],
                         D01B=vic['regs'][0x1b], D01C=vic['regs'][0x1c], D01D=vic['regs'][0x1d],
                         source_staggered_Y=[vic['regs'][2 * i + 1] for i in range(1, 8)], bank=bank, screen=screen,
                         sprite_palette_low_nibbles=[vic['regs'][0x27 + i] & 15 for i in range(1, 8)],
                         sprites=sprite_rows))
    return rows


def observations(decoded):
    rows = capture_observations(decoded)
    lookup = {row['stem']: row for row in rows}
    for stem in ('first-preclear', 'first-postclear', 'first-preset', 'first-postset', 'first-published',
                 'mature64-preclear', 'mature64-postclear', 'mature65-preclear'):
        assert [s['mcbase'] for s in lookup[stem]['sprites']] == list(range(0, 21, 3))
    assert [s['exp_flop'] for s in lookup['first-preclear']['sprites']] == [0] * 7
    assert [s['exp_flop'] for s in lookup['first-postclear']['sprites']] == [1] * 7
    assert [lookup[s]['D017'] for s in ('first-preclear', 'first-postclear', 'first-preset', 'first-postset')] == [255, 0, 0, 255]
    before, after = lookup['mature64-preclear'], lookup['mature65-preclear']
    assert after['clock'] - before['clock'] == 63 and after['line'] == before['line'] + 1
    assert [s['pointer'] for s in before['sprites']] == [0x1b] * 7
    assert [s['mcbase'] for s in before['sprites']] == [s['mcbase'] for s in after['sprites']]
    assert all(palette == 0 for row in rows for palette in row['sprite_palette_low_nibbles'])
    return dict(checkpoints=rows, band0_offsets_observed=list(range(0, 21, 3)),
                later_width=28, later_source_pointer=0x1b, same_counter_offsets_across_one_63_cycle_line=True,
                initial_X=[s['x'] for s in lookup['first-preclear']['sprites']],
                later_X=[s['x'] for s in before['sprites']],
                actual_nonblack_sprite_palette_observed=False,
                misleading_mature_filename_is_only_a_label=True,
                wrong_unmasked_color_guard='@io:$d028 != $00 can pass because unused read bits are high; use (@io:$d028 & $0f) != 0.',
                committed_output_pixels_composed_or_verified=False,
                all_three_bands_observed=False)


def traces(case, decoded, name='native-02'):
    rows = []
    for sequence, response in sorted(case['responses'].items()):
        for match in TRACE.finditer(response['response'].replace('\r\n', '\n')):
            row = match.groupdict()
            for key in ('checkpoint', 'line', 'cycle', 'clock'):
                row[key] = int(row[key])
            for key in ('target', 'pc', 'a', 'x', 'y', 'sp'):
                row[key] = int(row[key], 16)
            row['response_sequence'] = sequence
            rows.append(row)
    assert len(rows) == sum(len(re.findall(r'(?m)^#\d+ \(Trace store ', r['response'])) for r in case['responses'].values())
    assert all(a['clock'] <= b['clock'] for a, b in zip(rows, rows[1:]))
    if name == 'native-02':
        expected_first = [(0x90ec, 0xd017, 75247092), *[(0x90ef + i * 3, 0xaff9 + i, 75247096 + i * 4) for i in range(6)],
                          (0x9101, 0xd017, 75247120), (0x9104, 0xafff, 75247124), (0x9109, 0xd011, 75247130)]
        assert [(r['pc'], r['target'], r['clock']) for r in rows[:10]] == expected_first
        assert rows[0]['response_sequence'] == 60 and rows[6]['response_sequence'] == 71
        assert rows[7]['response_sequence'] == 82 and rows[8]['response_sequence'] == 93
        windows = [('first-preclear', 1, 130, 'first-window-complete'),
                   ('mature64-preclear', 64, 130, 'mature-window-complete')]
    else:
        windows = [('colored64-preclear', 64, 130, 'colored-window-complete')]
    receipt_windows = verify_trace_windows(rows, decoded, windows)
    artifact_row = save(name + '-trace-stores.json', rows)
    return dict(records=artifact_row, count=len(rows), first_macro=rows[:10], complete_macro_windows=receipt_windows,
                delayed_stop_boundary_delivery_observed=name == 'native-02',
                interpretation='Embedded checkpoint clocks are retained separately from response delivery. Several stores flush on a later resume, including the final pointer write. Bank switches are not assigned as a cause.',
                physical_bus_write_phase_certified=False)


def verify_trace_windows(rows, decoded, windows):
    cursor, result = 0, []
    offsets = [3, 6, 9, 12, 15, 18, 21, 24, 27, 32]
    targets = [0xd017, *range(0xaff9, 0xafff), 0xd017, 0xafff, 0xd011]
    cycles = [18, 22, 26, 30, 34, 38, 42, 46, 50, 56]
    for start_stem, first_row, last_row, end_stem in windows:
        capture, terminal = decoded[start_stem], decoded[end_stem]
        registers = capture['entry']['registers']
        assert registers['cycle'] == 14
        first = cursor
        for row_number in range(first_row, last_row + 1):
            pointer = capture['ram'][0xa87d + row_number]
            values = [0, *([pointer] * 6), 255, pointer, 0x18 | ((row_number + 61) & 7)]
            base_pc = 0x90e9 + (row_number - 1) * 35
            for offset, target, cycle, value in zip(offsets, targets, cycles, values):
                actual = rows[cursor]
                line = registers['line'] + row_number - first_row
                clock = registers['clock'] + (row_number - first_row) * 63 + cycle - 14
                assert (actual['pc'], actual['target'], actual['line'], actual['cycle'], actual['clock']) == (
                    base_pc + offset, target, line, cycle, clock)
                store_value = actual['y'] if target == 0xd017 and offset == 3 else actual['x'] if target == 0xd017 else actual['a']
                assert store_value == value
                cursor += 1
        assert rows[cursor - 1]['clock'] < terminal['entry']['registers']['clock']
        assert (terminal['entry']['registers']['pc'], terminal['entry']['registers']['line'],
                terminal['entry']['registers']['cycle']) == (0xa2b1, 192, 12)
        result.append(dict(first_macro_row=first_row, last_macro_row=last_row, records=cursor - first,
                           first_checkpoint=start_stem, terminal_checkpoint=end_stem,
                           final_store=rows[cursor - 1], terminal_clock=terminal['entry']['registers']['clock'],
                           all_PC_target_line_rawcycle_clock_values_exact=True,
                           terminal_store_delivered_in_retained_stream=True))
    assert cursor == len(rows)
    return result


def color_read_rule():
    archive = ROOT / 'build/research/quondam/hardware-source/vice-3.10.tar.gz'
    member = 'vice-3.10/src/viciisc/vicii-mem.c'
    with tarfile.open(archive, 'r:gz') as container:
        data = container.extractfile(member).read()
    source = data.decode()
    table = source.split('unused_bits_in_registers[0x40]', 1)[1].split('};', 1)[0]
    unused = [int(value, 16) for value in re.findall(r'0x([0-9a-f]+)\s*/\*\s*\$D[0-9A-F]+', table, re.I)]
    assert len(unused) == 64 and unused[0x28] == 0xf0
    peek = source.split('uint8_t vicii_peek(uint16_t addr)', 1)[1]
    assert 'return vicii.regs[addr] | unused_bits_in_registers[addr];' in peek
    assert bool(0 | unused[0x28]) and not ((0 | unused[0x28]) & 15)
    return dict(archive=artifact(archive), source_member=member, source_member_sha256=sha(data),
                x64sc_unused_read_mask_D028=unused[0x28], black_color_read_value=0xf0,
                unmasked_black_guard_passes=True, masked_black_guard_passes=False,
                interpretation='The color low nibble must be tested. The unused read bits do not indicate visible sprite color.')


def colored_case(wire, reader, equ):
    case = wire.audit_session('native-03')
    contexts, commands = command_audit(wire, case, 'native-03')
    decoded = captures(reader, contexts, 'native-03')
    assert len(decoded) == 4 and commands['command_count'] == 52
    original = (BASE / 'dos-files/11.prg').read_bytes()
    boot = decoded['original-boot']
    assert boot['entry']['registers']['pc'] == 0x080d
    assert boot['ram'][0x0801:0x0801 + len(original) - 2] == original[2:]
    expected = (BASE / 'analysis/fpp-source-patterns.bin').read_bytes()
    known = (BASE / 'analysis/fpp-source-patterns.known').read_bytes()
    rows = capture_observations(decoded)
    lookup = {row['stem']: row for row in rows}
    for row in rows:
        ram = decoded[row['stem']]['ram']
        assert all(ram[0x8000 + i] == expected[i] for i, value in enumerate(known) if value)
        assert row['sprite_palette_low_nibbles'] == [6] * 7
        assert row['D010'] == 0 and row['D01B'] == 255 and row['D018'] == 0xba
        assert row['bank'] == 0x8000 and row['screen'] == 0xac00
        assert [sprite['mcbase'] for sprite in row['sprites']] == list(range(0, 21, 3))
        assert row['source_staggered_Y'] == list(range(61, 54, -1))
    before, after = lookup['colored64-preclear'], lookup['colored65-preclear']
    assert after['clock'] - before['clock'] == 63 and after['line'] == before['line'] + 1
    assert [sprite['pointer'] for sprite in before['sprites']] == [0x1b] * 7
    assert [sprite['mcbase'] for sprite in before['sprites']] == [sprite['mcbase'] for sprite in after['sprites']]
    command = case['session']['command']
    assert case['session']['program'] == str(DISK) and command[command.index('-8') + 1] == str(DISK)
    assert '-pal' in command and '-drive8truedrive' in command and '+autostart-warp' in command
    return dict(native_case_directory_sha256=CASES['native-03'], wire=wire.summary(case), commands=commands,
                fresh_original_disk_autostart=True, no_native02_snapshot_parent=True,
                original_boot_payload_bytes=12425, original_boot_payload_exact=True,
                checkpoints=[capture['entry'] for capture in decoded.values()],
                source_code_binding=code_binding(decoded, equ, 'colored64-preclear'),
                known_pattern_bytes_equal_at_each_active_checkpoint=4032,
                generator_entry_or_writes_observed_in_this_case=False,
                actual_sprite_state=rows, nonblack_sprite_palette_observed=True,
                palette_low_nibble=6, palette_name='blue', source_width=28,
                same_band0_counter_offsets_across_one_63_cycle_line=True,
                trace=traces(case, decoded, 'native-03'),
                screenshot=artifact(BASE / 'native-03/colored-window.png'),
                screenshot_scope='Retained visible blue checkerboard observation. Character masking clips the left edge; seven fetched sprites are not seven fully visible sprites.',
                committed_palette_index_pixels_composed_or_verified=False,
                final_continuation=decoded['colored-window-complete']['entry'])


def main():
    for relative, digest in PINS.items():
        assert sha((ROOT / relative).read_bytes()) == digest, relative
    OUT.mkdir(parents=True, exist_ok=True)
    wire, adaptation = wire_reader()
    failure = startup_failure(wire)
    reader = load('spires_snapshot_reader', 'research/quondam/snapshot_state.py')
    case = wire.audit_session('native-02')
    command = case['session']['command']
    assert case['session']['program'] == str(DISK) and command[command.index('-8') + 1] == str(DISK)
    assert '-pal' in command and '-drive8truedrive' in command and '+autostart-warp' in command
    contexts, commands = command_audit(wire, case, 'native-02')
    decoded = captures(reader, contexts, 'native-02')
    assert len(decoded) == 13 and commands['command_count'] == 150
    assert decoded['fpp-entry']['entry']['registers']['pc'] == 0x9000
    assert decoded['fpp-prepared']['entry']['registers']['pc'] == 0x9003
    boot = decoded['original-boot']
    original = (BASE / 'dos-files/11.prg').read_bytes()
    assert boot['entry']['registers']['pc'] == 0x080d
    assert boot['ram'][0x0801:0x0801 + len(original) - 2] == original[2:]
    equ, correction = constants()
    blue = colored_case(wire, reader, equ)
    result = dict(pass_=True, script=artifact(Path(__file__).resolve()),
        input_pins=[artifact(ROOT / name) for name in PINS], startup_failure=failure,
        native_case_directory_sha256=CASES['native-02'], wire=wire.summary(case),
        original_disk_autostart_adapter=adaptation, commands=commands,
        original_boot=dict(checkpoint=boot['entry'], original_loaded_payload_bytes=len(original) - 2,
                           original_PRG_payload_exact=True, no_restore_or_CPU_state_injection=True),
        checkpoints=[capture['entry'] for capture in decoded.values()],
        earlier_frozen_pointer_arithmetic_correction=correction,
        original_source_code_binding=code_binding(decoded, equ), prepared_patterns=patterns(decoded),
        actual_sprite_state=observations(decoded), store_trace=traces(case, decoded),
        screenshots=[artifact(path) for path in sorted((BASE / 'native-02').glob('*.png'))],
        native02_continuation=decoded['mature-window-complete']['entry'],
        final_continuation=blue['final_continuation'], total_RAM_snapshot_pairs=17,
        total_compared_RAM_bytes=17 * 65536,
        masked_color_read_rule=color_read_rule(), fresh_masked_color_case=blue,
        fresh_masked_color_capture_pending=False,
        scope='Original native runtime code, pattern RAM, first-band row latches, one-line counter hold and a separate blue-palette observation; no committed-pixel oracle.',
        limits=['Observer clocks are not physical bus phases. No physical-chip, whole-frame, full-animation or FPS result is claimed.',
                'Native02 fields have black sprite color low nibbles. Mature filenames do not establish visible fill. Native03 independently observes blue low nibbles and a retained visible screenshot.',
                'Only first-band MCBASE offsets are observed; the source math for bands1/2 is not substituted for native counter evidence.',
                'Known generated bytes match independently retained source math. All64 ungenerated byte63 positions remain endpoint observations.',
                'Source code fragments and130 macro rows bind the original FPP mechanism; no full source rebuild or missing-binary identity is claimed.',
                'No committed VIC pixel compositor is run; window-complete labels are not full raster-frame proof.'])
    result['pass'] = result.pop('pass_')
    receipt = save('native-proof.json', result)
    (OUT / 'native.checked.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(pass_=True, original_boot_bytes=12425, source_macro_bytes=4550,
                         generated_known_bytes=4032, nonblack_color=True, receipt=receipt), indent=2))


if __name__ == '__main__':
    main()
