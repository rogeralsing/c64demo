#!/usr/bin/env python3
"""Passive custody and bounded source bindings for closed original Hat native02.

This reads retained wire, snapshots and source bytes. It starts no machine,
subprocess, interpreter, socket or native process.
"""
import argparse
import ast
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tarfile
import traceback
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/the-hat'
CASE = BASE / 'native-02'
SOURCE = BASE / 'dali-analysis/neighbor-probe-02/accepted-01'
DISK = BASE / 'release/the-hat-7a825b1-b.d64'
CASE_SHA = '6c1d2df597cbf1751a2f5e8bbffb5afb020f06eac27991841ed3a73bdf987454'
COMMANDS_SHA = '0f34b0cbd778182801bd4f688b1de1266c6be3f56cf132e52432c6b61be5f8d5'
PINS = {
    'research/verify_vice_live.py': 'f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a',
    'research/vice_session_live.py': '4340d1b0394fa612f5e6a71edddcbc2daf947e59c4c3013ab3b850c886dc621c',
    'research/eod/controller.py': '033bafb6ac6e97283175ac6713af0eef60cb7991b653ee1c98c47a1a4afa83c9',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'build/research/the-hat/native-analysis/interrupt-framing-source.py': '0223c67fafd2a3e4ac72b0a6bc3c911655a88da2f4cc42041ed6e3089e464047',
    'build/research/quondam/hardware-source/vice-3.10.tar.gz': '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1',
    'build/research/frontier-2026/february-analysis/the-hat-original.zip': 'ab15a74ba10a71264ccad74cd1d3a394b8f442a2acd33fd363b671bf293b081f',
    'build/research/the-hat/release/the-hat-7a825b1-b.d64': '1527038ebebca1a3d3d3379b91dd1a77dffb6d6d89a4dbfc32bf3f6908eb5b21',
    'build/research/the-hat/native-02-files.json': 'dd06be2ba97ed9255cd922938b41bd0aec84daa21448454361128c2b49692d2d',
    'build/research/the-hat/disk-analysis/accepted-02/disk-proof.json': 'a23fa100137fe60f929af25b6596584089cd93cacd891fe02e7ebc85d47635a3',
    'build/research/the-hat/disk-analysis/early-01/original-bootstrap.prg': '32189d1101a947c3ecc02ae3e9493756dbc063008582d09c62f939068f1049cd',
    'build/research/the-hat/dali-analysis/accepted-03/dali-proof.json': '1687a5b2323ec86881b53b226a5361ac88c6408720498cfd34cf7032b3ad940e',
    'build/research/the-hat/dali-analysis/accepted-03/b00-0f00.bin': '61a9573334039fbd8b812c5378c4eefb820f96cf52d570dd1b1b3aa7ed23bbf9',
    'build/research/the-hat/dali-analysis/neighbor-probe-02/accepted-01/source-classification.json': '838ed0bd5534acce676b06528f4c311adbccc8f1fc62462d5b68abfe628dcb8f',
    'build/research/the-hat/dali-analysis/neighbor-probe-02/accepted-01/b07.bin': '5f2a0a0b960dfdd1f8c31b5be9ef5e60fbe2db177a446db5eb51462e57b5d150',
    'build/research/the-hat/dali-analysis/neighbor-probe-02/accepted-01/b08.bin': '5c8150c48068c62f8a77d8c97b18de33360dcb03046e0f5e9ffcb01ca6704ba6',
    'build/research/the-hat/dali-analysis/neighbor-probe-02/accepted-01/b09.bin': '9d0f80b7bc33c981a7befe2274ac98f30bf00c77916702016588b5e028e9a578',
}
EXPECTED = {
    'sys': (0x080d, 11358745), 'depacked': (0x0a00, 12267239),
    'first-loaded': (0x0f00, 13862168), 'b7-loaded': (0x2043, 124579026),
    'b8-controller': (0x8000, 127682762), 'b8-init': (0x8042, 127702618),
    'first-motion': (0xe152, 127722127), 'first-written': (0xe15c, 127722145),
    'mature-motion': (0xe152, 145414284), 'mature-written': (0xe15c, 145414302),
    'raster-selector': (0x8516, 145415945), 'cutoff': (0x828c, 145432586),
    'stack-restored': (0x8298, 145432621),
    'rejected-raster-request': (0x8048, 146240643),
    'complete-field': (0x81b2, 146259540), 'odd-selector': (0x8516, 146261279),
    'odd-program': (0xa8df, 146261354), 'odd-cutoff': (0x828c, 146277792),
    'odd-stack': (0x8298, 146277827),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def function_source(relative, name):
    source = (ROOT / relative).read_text()
    node = next(node for node in ast.parse(source).body
                if isinstance(node, ast.FunctionDef) and node.name == name)
    return ast.get_source_segment(source, node) + '\n'


def response_reference(row):
    raw = row['response'].encode()
    return dict(sequence=row['sequence'], id=row['id'], command=row['command'],
                received_first=row['received_first'], received_end=row['received_end'],
                response_bytes=len(raw), response_sha256=sha(raw),
                received_stream=str((CASE / 'received.bin').relative_to(ROOT)))


def closed_inventory():
    path = BASE / 'native-02-files.json'
    manifest = json.loads(path.read_text())
    rows = [dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
            for p in sorted(CASE.iterdir()) if p.is_file()]
    assert rows == manifest['files'] and len(rows) == manifest['file_count'] == 46
    assert sum(row['bytes'] for row in rows) == manifest['total_bytes'] == 61778341
    assert sha(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()) == manifest['listing_sha256'] == CASE_SHA
    with zipfile.ZipFile(ROOT / 'build/research/frontier-2026/february-analysis/the-hat-original.zip') as archive:
        names = [name for name in archive.namelist() if Path(name).name == DISK.name]
        assert len(names) == 1 and archive.read(names[0]) == DISK.read_bytes()
    return dict(manifest=artifact(path), files=46, bytes=61778341,
                canonical_listing_sha256=CASE_SHA,
                original_ZIP_member=names[0], all_B_disk_bytes_equal=True)


def interrupt_framing(row,wire):
    """Bind the final explicit interrupt-r frame without discarding late traces."""
    assert row['status']=='interrupted'
    text=row['response'];metadata=row['interrupt'];first=metadata['response_first']
    assert text.isascii() and metadata['register_response']==text[first:]
    pattern=re.compile(r'(?m)^\(C:\$([0-9a-f]{4})\) +ADDR A  X  Y  SP 00 01 NV-BDIZC LIN CYC  STOPWATCH\n'
        r'\.;[^\n]+\n\(C:\$\1\) \Z')
    match=pattern.search(text);assert match and match.start()>=first
    frame=match[0];registers=wire.registers(frame)
    assert registers['pc']==int(match[1],16) and wire.PROMPT.search(frame.encode())
    suffix=text[first:]
    return dict(registers=registers,frame_response_first=match.start(),
        frame_received_first=row['received_first']+match.start(),frame_received_end=row['received_end'],
        frame_bytes=len(frame),frame_sha256=sha(frame.encode()),
        complete_retained_interrupt_suffix_bytes=len(suffix),complete_retained_interrupt_suffix_sha256=sha(suffix.encode()),
        explicit_register_rows_in_complete_suffix=len(wire.REGISTERS.findall(suffix)),
        late_trace_headers_in_complete_suffix=len(re.findall(r'#\d+ \(Trace\s+(?:exec|store) ',suffix)),
        no_raw_suffix_or_late_trace_filtering=True)


def audit_wire():
    wire = load('hat_upscroll_wire', 'research/verify_vice_live.py')
    wire.BASE, wire.CASE_PINS = BASE, {'native-02': CASE_SHA}
    original = function_source('research/verify_vice_live.py', 'audit_session')
    old = 'assert session["startup_mode"] == "manual monitor load" and "-autostart" not in session["command"]'
    replacement = ('assert session["startup_mode"] == "autostart"\n'
                   '    assert session["program"] == ' + repr(str(DISK)) + '\n'
                   '    for flag in ("-autostart", "-8"):\n'
                   '        assert session["command"].count(flag) == 1\n'
                   '        assert session["command"][session["command"].index(flag)+1] == ' + repr(str(DISK)))
    assert original.count(old) == 1
    adapted = original.replace(old, replacement)
    interrupt_old = 'registers(interrupt["register_response"])'
    interrupt_replacement = 'hat_interrupt_registers(event)'
    assert adapted.count(interrupt_old) == 1
    adapted = adapted.replace(interrupt_old, interrupt_replacement)
    helper_source = function_source('research/the-hat/upscroll_native.py', 'interrupt_framing')
    assert helper_source.encode() == (BASE / 'native-analysis/interrupt-framing-source.py').read_bytes()
    wire.hat_interrupt_registers = lambda row: interrupt_framing(row, wire)['registers']
    exec(compile(adapted, '<original-Hat-sideB-autostart-and-exact-interrupt-frame>', 'exec'), wire.__dict__)
    case = wire.audit_session('native-02')
    responses = case['responses']
    assert not case['partial'] and not case['cancelled']
    assert sorted(responses) == list(range(1, 152))
    assert Counter(row['status'] for row in responses.values()) == {'completed': 150, 'interrupted': 1}
    assert [n for n, row in responses.items() if row['status'] == 'interrupted'] == [100]
    assert Counter(row['purpose'] for row in case['requests']) == {'ordinary': 151, 'interrupt': 1}
    commands = [responses[n]['command'] for n in range(1, 152)]
    assert sha(json.dumps(commands, separators=(',', ':')).encode()) == COMMANDS_SHA
    assert not any(re.search(r'ERROR --|Syntax error|Unknown resource', row['response']) for row in responses.values())
    assert case['waits'] == [dict(utc='2026-11-08T21:24:09.270372+00:00', kind='observation_timeout',
        status='partial', waiting=True, elapsed_seconds=30.181, sequence=29, id='natural-b7-loaded',
        command='x', internal=False, received_bytes=0,
        action='Still pending; send interrupt or close. No retry or restart.')]
    launch = case['session']['command']
    assert '-pal' in launch and launch[launch.index('-speed') + 1] == '100'
    assert '+warp' in launch and '+autostart-warp' in launch
    assert '-drive8truedrive' in launch and launch[launch.index('-drive8type') + 1] == '1541'
    for n in (9, 36, 115, 150):
        assert responses[n]['command'] == 'warp' and 'Warp mode is off.' in responses[n]['response']
    for n in (10, 37, 116, 151):
        assert responses[n]['command'] == 'resourceget "Speed"' and re.search(r'Speed\s*=\s*100', responses[n]['response'])
    assert commands[22] == 'warp on' and commands[34] == 'warp off'
    frame = interrupt_framing(responses[100], wire)
    assert frame['late_trace_headers_in_complete_suffix'] == 7364
    assert frame['explicit_register_rows_in_complete_suffix'] == 7366
    case['_strict_or_final_registers'] = lambda text: (
        wire.hat_interrupt_registers(responses[100])
        if text == responses[100]['interrupt']['register_response'] else wire.registers(text))
    return wire, case, dict(original_function_sha256=sha(original.encode()),
        adapted_function_sha256=sha(adapted.encode()), exact_startup_replacement=replacement,
        exact_interrupt_old=interrupt_old, exact_interrupt_replacement=interrupt_replacement,
        final_interrupt_frame_helper_sha256=sha(helper_source.encode()),
        only_two_declared_auditor_replacements=True, ordinary_register_reader_unchanged=True,
        no_event_or_raw_byte_change=True, interrupted_frame=frame)


def capture_pairs(reader, wire, case):
    helper = load('hat_upscroll_pairs', 'research/eod/controller.py')
    helper.CASE = CASE
    original = function_source('research/eod/controller.py', 'capture_pairs')
    old = "assert mem[1] == mem[65542] == regs['port00'] == 0x2f"
    replacement = "assert mem[1] == mem[65542] == regs['port00']"
    assert original.count(old) == 1
    adapted = original.replace(old, replacement)
    first = original.index('        stopped = list(re.finditer(')
    last = original.index('        assert not any(responses[n]', first)
    block = original[first:last]
    interrupt = ("        if responses[stop]['status'] == 'interrupted':\n"
                 "            assert stop == 100\n"
                 "            assert wire.hat_interrupt_registers(responses[stop]) == regs\n"
                 "        else:\n" + ''.join('    ' + line for line in block.splitlines(keepends=True)))
    assert adapted.count(block) == 1
    adapted = adapted.replace(block, interrupt)
    exec(compile(adapted, '<actual-DDR-and-declared-native02-interruption>', 'exec'), helper.__dict__)
    memories, captures = helper.capture_pairs(reader, wire, case)
    assert len(captures) == 19 and {row['stem'] for row in captures} == set(EXPECTED)
    for row in captures:
        assert (row['registers']['pc'], row['registers']['clock']) == EXPECTED[row['stem']]
        rejected = row['stem'] == 'rejected-raster-request'
        assert (case['responses'][row['stop_sequence']]['status'] == 'interrupted') == rejected
        row['stop_kind'] = 'read-only interrupted observer failure' if rejected else 'natural exec breakpoint'
        row['not_a_natural_requested_phase'] = rejected
    return memories, captures, dict(original_function_sha256=sha(original.encode()),
        adapted_function_sha256=sha(adapted.encode()), exact_DDR_replacement=replacement,
        exact_original_stop_block=block, exact_interrupted_stop_replacement=interrupt,
        only_two_pair_source_replacements=True,
        retained_checks='All65536physicalRAM, C64MEM schema/latch/DDR/readback, CPU registers/clock/flags, beam and same stopped interval remain checked.')


def checkpoints(case, captures):
    active, setups, stops = {}, [], {}
    generations = Counter()
    responses = case['responses']
    for sequence, row in sorted(responses.items()):
        command = row['command']
        if command.startswith(('break ', 'trace exec ', 'trace store ')):
            match = re.search(r'^(BREAK|TRACE): ([0-9]+)  C:\$([0-9a-f]{4})(?:-\$([0-9a-f]{4}))?  \((Stop on exec|Trace exec|Trace store)\)', row['response'])
            assert match, (sequence, row['response'])
            kind, number, first = match[1], int(match[2]), int(match[3], 16)
            last = int(match[4], 16) if match[4] else first
            assert number not in active
            generations[number] += 1
            operation = 'store' if match[5] == 'Trace store' else 'exec'
            if kind == 'TRACE':
                assert command == f'trace {operation} {first:04x}' + (f' {last:04x}' if last != first else '')
            else:
                declared = re.fullmatch(r'break (?:exec )?\$?([0-9a-f]{4})(?: \$?([0-9a-f]{4}))?(?: if (.+))?', command)
                assert declared and first == int(declared[1], 16)
                assert last == int(declared[2], 16) if declared[2] else last == first
            record = dict(number=number, generation=generations[number], kind=kind,
                operation=operation, first=first, last=last, setup=response_reference(row),
                condition=command.split(' if ', 1)[1] if ' if ' in command else None)
            active[number] = record
            setups.append(record)
        elif command.startswith('condition '):
            match = re.fullmatch(r'condition ([0-9]+) if (.+)', command)
            assert match and int(match[1]) in active
            assert row['response'].startswith(f'Setting checkpoint {match[1]} condition to:')
            active[int(match[1])]['condition'] = match[2]
            active[int(match[1])]['condition_response'] = response_reference(row)
        elif command.startswith('command '):
            match = re.fullmatch(r'command ([0-9]+) "r"', command)
            assert match and int(match[1]) in active
            assert row['response'].startswith(f'Setting checkpoint {match[1]} command to: r')
            active[int(match[1])]['attached_r'] = response_reference(row)
        elif command.startswith('delete '):
            number = int(command.split()[1]); assert number in active
            active[number]['deleted_sequence'] = sequence
            del active[number]
        elif command == 'x':
            if row['status'] == 'interrupted':
                assert sequence == 100
                stops[sequence] = dict(interrupted=True, active=[record.copy() for record in active.values()],
                    actual=wire_registers_final(case, sequence), response=response_reference(row))
                continue
            hits = list(re.finditer(r'^#([0-9]+) \(Stop on\s+exec ([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+', row['response'], re.M))
            assert len(hits) == 1, sequence
            hit = hits[0]; number, pc = int(hit[1]), int(hit[2], 16)
            assert number in active and active[number]['kind'] == 'BREAK'
            assert active[number]['first'] <= pc <= active[number]['last']
            stops[sequence] = dict(interrupted=False, checkpoint=active[number].copy(), PC=pc,
                beam=[int(hit[3]), int(hit[4])], response=response_reference(row))
    assert not active
    bindings = []
    for capture in captures:
        stop = stops[capture['stop_sequence']]
        if stop['interrupted']:
            assert stop['actual'] == capture['registers']
            stop['condition_evaluations_at_actual_interrupted_point'] = [
                dict(checkpoint=record['number'], generation=record['generation'],
                     predicates=evaluate_condition(record['condition'], capture['registers'],
                         (CASE / (capture['stem'] + '-ram.bin')).read_bytes()))
                for record in stop['active'] if record['kind'] == 'BREAK']
            assert len(stop['condition_evaluations_at_actual_interrupted_point']) == 1
            assert stop['condition_evaluations_at_actual_interrupted_point'][0]['predicates'][0]['equal'] is False
        else:
            assert stop['PC'] == capture['registers']['pc']
            assert stop['beam'] == [capture['registers']['line'], capture['registers']['cycle']]
            stop['evaluated_predicates'] = evaluate_condition(stop['checkpoint']['condition'],
                capture['registers'], (CASE / (capture['stem'] + '-ram.bin')).read_bytes())
            assert all(predicate['equal'] for predicate in stop['evaluated_predicates'])
        bindings.append(dict(stem=capture['stem'], **stop))
    bad, good = next(r for r in setups if r['setup']['sequence'] == 98), next(r for r in setups if r['setup']['sequence'] == 108)
    assert bad['number'] == 17 and bad['condition'] == 'RL == 300'
    assert good['number'] == 1 and good['generation'] == 2 and good['condition'] == 'RL == $012c'
    assert 'RL == $300' in responses[98]['response'] and 'RL == $12c' in responses[108]['response']
    completed = next(row for row in captures if row['stem'] == 'complete-field')
    assert completed['stop_sequence'] == 109
    assert (completed['registers']['line'], completed['registers']['cycle']) == (300, 0)
    return dict(setups=setups, capture_stops=bindings,
        rejected_request=dict(setup_sequence=98, pending_sequence=100, condition_literal='RL == 300',
            actual_normalized_condition='RL == $300', requested_numeric_value=768,
            valid_PAL_raster_lines=[0, 311], capture='rejected-raster-request',
            actual_not_requested_phase=True, no_retry_or_event_discard=True),
        corrected_request=dict(setup_sequence=108, reused_checkpoint=1, generation=2,
            condition='RL == $012c', actual_line=300, actual_cycle=0, stop_sequence=109))


def wire_registers_final(case, sequence):
    return case['_strict_or_final_registers'](case['responses'][sequence]['interrupt']['register_response'])


def evaluate_condition(condition, registers, memory):
    """Every predicate in the retained case must belong to this exact grammar."""
    predicates = []
    if not condition:
        return predicates
    for raw in re.split(r'\s*&&\s*', condition):
        term = raw.strip()
        if term.startswith('(') and term.endswith(')'):
            term = term[1:-1].strip()
        match = re.fullmatch(r'@ram:\$([0-9a-f]+) == \$([0-9a-f]+)', term)
        if match:
            address, expected = int(match[1], 16), int(match[2], 16)
            assert 0 <= address < 65536 and 0 <= expected <= 255
            actual = memory[address]
            predicates.append(dict(expression=raw, kind='RAM', address=address,
                                   expected=expected, actual=actual, equal=actual == expected))
            continue
        match = re.fullmatch(r'RL == (\$?[0-9a-f]+)', term)
        assert match, ('Unparsed original condition predicate', raw)
        expected = int(match[1].lstrip('$'), 16)
        actual = registers['line']
        predicates.append(dict(expression=raw, kind='raster_line', expected=expected,
                               actual=actual, equal=actual == expected))
    return predicates


def source_bindings(memories, captures):
    states = {row['stem']: row['registers'] for row in captures}
    original = []
    boot_path = BASE / 'disk-analysis/early-01/original-bootstrap.prg'
    boot = boot_path.read_bytes(); assert len(boot) == 2710 and boot[:2] == bytes.fromhex('0108')
    assert memories['sys'][0x0801:0x1295] == boot[2:]
    assert re.fullmatch(rb'\x9e\s*2061', boot[6:boot.index(0, 6)])
    original.append(dict(capture='sys', source=artifact(boot_path), destination=0x0801,
        bytes=2708, all_bytes_equal=True, BASIC_SYS=0x080d))
    b0path = BASE / 'dali-analysis/accepted-03/b00-0f00.bin'
    b0 = b0path.read_bytes(); assert len(b0) == 263
    assert memories['first-loaded'][0x0f00:0x0f00 + len(b0)] == b0
    dali = json.loads((BASE / 'dali-analysis/accepted-03/dali-proof.json').read_text())
    b0case = next(row for row in dali['cases'] if row['output']['name'] == b0path.name)
    assert dali['pass'] and b0case['unknown_bytes'] == b0case['prior_memory_reads'] == 0
    original.append(dict(capture='first-loaded', source=artifact(b0path), destination=0x0f00,
        bytes=len(b0), all_bytes_equal=True, prior_memory_reads=0))
    neighbor = json.loads((SOURCE / 'source-classification.json').read_text())
    raw_source = {}
    for name, destination, size in [('b07', 0x2000, 5065), ('b08', 0x4000, 36864), ('b09', 0xe000, 6144)]:
        row = next(r for r in neighbor['new_streams'] if r['name'] == name)
        path = SOURCE / row['output']['name']; raw = path.read_bytes()
        assert row['destination'] == destination and row['bytes'] == len(raw) == size
        assert row['end_exclusive'] == destination + size and row['unknown_bytes'] == 0
        assert sha(raw) == row['output']['sha256']
        assert artifact(ROOT / row['raw']['path']) == row['raw']
        raw_source[name] = (destination, raw)
        if name == 'b07':
            assert raw[0x3a:0x4b] == bytes.fromhex('204e2020d20220d202ad4c20f0fb4c0080')
            for stem in ('b7-loaded', 'b8-controller'):
                assert memories[stem][0x203a:0x204b] == raw[0x3a:0x4b]
                original.append(dict(capture=stem, source=artifact(path), source_offset=0x3a,
                    destination=0x203a, bytes=17, all_bytes_equal=True,
                    role='Original two-load, wait and JMP8000 controller bytes'))
        else:
            for stem in ('b7-loaded', 'b8-controller'):
                assert memories[stem][destination:destination + size] == raw
                original.append(dict(capture=stem, source=artifact(path), destination=destination,
                    bytes=size, all_bytes_equal=True, unknown_source_bytes=0))
    b8, b9 = raw_source['b08'][1], raw_source['b09'][1]
    code = lambda address, length: b8[address - 0x4000:address - 0x4000 + length]
    guards = []
    for address, h, role in [
        (0x803f, '204f80', 'Original initialization call returns8042'),
        (0x819d, 'ad7d818d01d08d03d08d05d08d07d08d09d08d0bd08d0dd08d0fd0', 'Copy current shared Y before motion update'),
        (0x81b8, 'ad7e81186920aa8ef843', 'Current pointer phase plus20 before motion update'),
        (0x81f3, '2000e0', 'Original subsequent motion-controller call'),
        (0x821c, 'ad01d038e9028d12d0aabdcc828d06dcbdcc838d07dc', 'Use current hardwareY minus2 for CIA1TimerB latch tables'),
        (0x8267, 'a9198d0fdc', 'Start/force-load one-shot CIA1TimerB'),
        (0x828c, 'a9fe8d18d1ad0ddcae8b829a', 'D018mirror, CIA1 acknowledge, saved-SP restore'),
        (0x8516, 'adf8432908f0034caaa8', 'Pointer bit3 selects original raster variant'),
    ]:
        expected = bytes.fromhex(h); assert code(address, len(expected)) == expected
        for stem in ('b8-controller', 'raster-selector', 'odd-selector'):
            assert memories[stem][address:address + len(expected)] == expected, (stem, hex(address))
        guards.append(dict(address=address, hex=h, role=role,
            captures=['b8-controller', 'raster-selector', 'odd-selector'], all_bytes_equal=True))
    assert b9[0x152:0x15c] == bytes.fromhex('b1028d7d81b1048d7e81')
    motions = []
    for before, after, expected_index, pair in [('first-motion', 'first-written', 0, [206, 0]),
                                               ('mature-motion', 'mature-written', 900, [13, 16])]:
        a, b = memories[before], memories[after]
        assert a[2:6] == b[2:6] and states[before]['y'] == states[after]['y'] == 0
        yp, pp = int.from_bytes(a[2:4], 'little'), int.from_bytes(a[4:6], 'little')
        index = yp - 0xe1ae
        assert index == pp - 0xe97e == expected_index and 0 <= index < 2000
        expected = [b9[yp - 0xe000], b9[pp - 0xe000]]
        assert expected == pair == list(b[0x817d:0x817f])
        assert states[after]['clock'] - states[before]['clock'] == 18
        assert a[0xe152:0xe15c] == b[0xe152:0xe15c] == b9[0x152:0x15c]
        differences = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
        assert set(differences) <= {0x817d, 0x817e}
        motions.append(dict(before=before, after=after, table_index=index,
            source_addresses=[yp, pp], predicted_pair=expected, observed_pair=pair,
            elapsed_cycles=18, all_RAM_changes=differences, all_predictions_equal=True,
            limit='This writes the next state after the current VIC Y/pointer consumer; it is not a current-field Y inference.'))
    return dict(original_loaded_ranges=original, full_B8_B9_bytes_per_capture=43008,
        whole_range_captures=['b7-loaded', 'b8-controller'], code_guards=guards,
        motion_updates=motions, raw_source=raw_source)


def machine_context(reader, memories, captures, sources):
    snapshots = {row['stem']: reader.read_snapshot(CASE / (row['stem'] + '.vsf')) for row in captures}
    states = {row['stem']: row['registers'] for row in captures}
    b8 = sources['raw_source']['b08'][1]
    fields = []
    for selector, cutoff, restored, bit, current_y, latch, interrupted_pc in [
        ('raster-selector', 'cutoff', 'stack-restored', 0, 14, 16667, 0x97ff),
        ('odd-selector', 'odd-cutoff', 'odd-stack', 8, 16, 16541, 0xb6e5),
    ]:
        initial, ending, final = [snapshots[name] for name in (selector, cutoff, restored)]
        cia, end_cia, final_cia = [x['cia']['CIA1'] for x in (initial, ending, final)]
        vic = initial['vicii']; cia2 = initial['cia']['CIA2']
        assert memories[selector][0x43f8] & 8 == bit
        assert (vic['regs'][1::2][:8]) == [current_y] * 8
        assert [cia2[k] for k in ('pra', 'ddra')] == [2, 0x3f]
        effective_pins = (cia2['pra'] & cia2['ddra']) | ((~cia2['ddra']) & 255)
        bank = ((~effective_pins) & 3) * 0x4000
        assert bank == 0x4000
        x = current_y - 2
        table_latch = b8[0x82cc + x - 0x4000] | b8[0x83cc + x - 0x4000] << 8
        assert table_latch == 0x440f - 63 * x == latch == cia['timer_b_latch']
        assert cia['timer_b'] == latch - 37
        assert cia['icr_mask'] == 2 and cia['icr_pending'] == 1 and cia['irq_enabled'] == 0
        assert cia['timer_b_state'] == 0x196b
        assert end_cia['icr_mask'] == 2 and end_cia['icr_pending'] == 0x83 and end_cia['irq_enabled'] == 1
        assert end_cia['timer_b'] == end_cia['timer_b_latch'] == latch and end_cia['timer_b_state'] == 0x1128
        assert final_cia['icr_pending'] == final_cia['irq_enabled'] == 0
        assert final_cia['timer_b_state'] == 0x1128
        assert cia['crb'] == end_cia['crb'] == final_cia['crb'] == 9
        assert all(x['vicii']['irq_status'] == 0 and x['vicii']['raster_irq_line'] == 511 for x in (initial, ending, final))
        saved_sp = memories[selector][0x828b]
        assert saved_sp == states[selector]['sp'] == states[restored]['sp'] == 0x59
        sp = states[cutoff]['sp']; assert sp == 0x56 and (saved_sp - sp) & 255 == 3
        raw = memories[cutoff]
        status = raw[0x100 + ((sp + 1) & 255)]
        pc = raw[0x100 + ((sp + 2) & 255)] | raw[0x100 + ((sp + 3) & 255)] << 8
        assert pc == interrupted_pc
        assert memories[cutoff] == memories[restored]
        assert states[restored]['clock'] - states[cutoff]['clock'] == 35
        assert states[restored]['a'] == 0x83
        fields.append(dict(selector=selector, cutoff=cutoff, restored=restored,
            selector_pointer=memories[selector][0x43f8], pointer_bit3=bit,
            selected_variant='odd' if bit else 'even',
            next_motion_pair=list(memories[selector][0x817d:0x817f]),
            current_all_eight_VIC_Y=current_y,
            CIA2=dict(pra=cia2['pra'], ddra=cia2['ddra'], effective_bank_low_pins=effective_pins & 3, VIC_bank=bank),
            source_timer_index=x, source_latch=table_latch,
            selector_timer_counter=cia['timer_b'], selector_timer_state=cia['timer_b_state'],
            cutoff_timer_counter=end_cia['timer_b'], cutoff_timer_state=end_cia['timer_b_state'],
            pending_mask_selector_cutoff_restored=[cia['icr_pending'], end_cia['icr_pending'], final_cia['icr_pending']],
            CIA1_interrupt_mask=2, VIC_interrupt_status=0, VIC_raster_compare=511,
            saved_SP=saved_sp, cutoff_SP=sp, restored_SP=states[restored]['sp'],
            interrupted_PC=pc, stacked_status=status, acknowledgement_A=states[restored]['a'],
            cutoff_to_restored_cycles=35, all65536_RAM_equal_across_LDX_TXS_interval=True,
            mechanism='CIA1TimerB enabled and pending; original handler acknowledges CIA1 and abandons the interrupted raster stack.',
            deadline_hardware_validation=False,
            limit='No DCxx trace captures the timer start/write deadline. This source/snapshot binding is not a complete timer scheduling or physical scanout validation.'))
    assert list(memories['raster-selector'][0x43f8:0x4400]) == list(range(0x30, 0x38))
    assert list(memories['odd-selector'][0x43f8:0x4400]) == list(range(0x38, 0x40))
    assert states['odd-program']['clock'] - states['odd-selector']['clock'] == 75
    rejected = states['rejected-raster-request']
    assert (rejected['pc'], rejected['line'], rejected['cycle']) == (0x8048, 0, 3)
    assert (states['complete-field']['line'], states['complete-field']['cycle']) == (300, 0)
    return snapshots, dict(fields=fields,
        current_VIC_consumers_precede_next_motion_state_write=True,
        odd_branch_PC_observed=0xa8df, selector_to_odd_program_cycles=75,
        rejected_requested_phase=dict(capture='rejected-raster-request', actual_registers=rejected,
            excluded_from_requested_line300_and_full_field_acceptance=True),
        corrected_line300=dict(capture='complete-field', actual_registers=states['complete-field'],
            scope='A natural any-PC beam observation; it is not a same-field pixel or complete output-model comparison.'),
        screenshot=dict(artifact=artifact(CASE / 'complete-field.png'), cosmetic_only=True,
            not_independent_native_pixel_oracle=True))


def trace_events(case, wire, points, memories, sources, captures):
    """Check every raw hit, compacting only the long interrupted100 response."""
    setups = [row for row in points['setups'] if row['kind'] == 'TRACE']
    header = re.compile(r'#([0-9]+) \(Trace\s+(exec|store) ([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\n')
    instruction = re.compile(r'^\.C:([0-9a-f]{4})\s+([0-9A-F]{2}(?: [0-9A-F]{2}){0,2})\s+(.+?)\s+- A:([0-9A-F]{2}) X:([0-9A-F]{2}) Y:([0-9A-F]{2}) SP:([0-9a-f]{2}) ([NV\-BDIZC.]{8})\s+(\d+)\n', re.M)
    states = {row['stem']: row['registers'] for row in captures}
    register_keys = ('pc', 'a', 'x', 'y', 'sp', 'port00', 'port01', 'flags', 'line', 'cycle', 'clock')
    records, windows, totals = [], [], Counter()
    for sequence, row in sorted(case['responses'].items()):
        if row['command'] != 'x':
            continue
        text = row['response']; assert text.isascii()
        headers = list(header.finditer(text)); assert text.count('(Trace') == len(headers)
        if not headers:
            continue
        compact = sequence == 100
        if compact:
            assert row['status'] == 'interrupted'
            terminal = interrupt_framing(row, wire)['frame_response_first']
            assert sum(match.start() >= row['interrupt']['response_first'] for match in headers) == 7364
        else:
            stop = re.search(r'^#[0-9]+ \(Stop on', text, re.M); assert stop
            terminal = stop.start()
        assert headers[-1].start() < terminal
        context_digest, framing_digest = hashlib.sha256(), hashlib.sha256()
        counts, ports, targets, opcodes, refs = [Counter() for _ in range(5)]
        first_record = last_record = None
        unmatched = []
        previous_clock = None
        for index, match in enumerate(headers):
            number, operation, address = int(match[1]), match[2], int(match[3], 16)
            candidates = [setup for setup in setups if setup['number'] == number
                and setup['setup']['sequence'] < sequence < setup.get('deleted_sequence', 152)]
            assert len(candidates) == 1, (sequence, number)
            setup = candidates[0]
            assert setup['operation'] == operation and setup['first'] <= address <= setup['last']
            assert setup['attached_r']['sequence'] < sequence
            end = headers[index + 1].start() if index + 1 < len(headers) else terminal
            segment = text[match.end():end]
            ins = instruction.search(segment)
            assert ins and segment.count('Executing: r') == 1
            pc, raw = int(ins[1], 16), bytes.fromhex(ins[2])
            regs = wire.registers(segment)
            assert regs['clock'] == int(ins[9])
            assert previous_clock is None or regs['clock'] >= previous_clock
            previous_clock = regs['clock']
            assert (regs['line'], regs['cycle']) == (int(match[4]), int(match[5]))
            assert (regs['clock'] // 63 % 312, regs['clock'] % 63) == (regs['line'], regs['cycle'])
            assert [regs[k] for k in ('a', 'x', 'y', 'sp')] == [int(ins[k], 16) for k in (4, 5, 6, 7)]
            if operation == 'exec':
                assert regs['pc'] == pc == address
            reference = 'not_equal_to_declared_code_references'
            for name in ('b08', 'b09'):
                base, original = sources['raw_source'][name]
                if base <= pc and pc + len(raw) <= base + len(original) and original[pc - base:pc - base + len(raw)] == raw:
                    reference = 'independent_original_' + name + '_bytes'
                    break
            if reference.startswith('not_equal') and states['b8-init']['clock'] <= regs['clock'] and memories['b8-init'][pc:pc + len(raw)] == raw:
                reference = 'earlier_natural_B8_initialized_RAM_bytes'
            record = dict(sequence=sequence, checkpoint=number, checkpoint_generation=setup['generation'],
                operation=operation, monitored_address=address,
                instruction_PC=pc, instruction_hex=raw.hex(), instruction=ins[3], registers=regs,
                setup_sequence=setup['setup']['sequence'], attached_r_sequence=setup['attached_r']['sequence'],
                received_first=row['received_first'] + match.start(), received_end=row['received_first'] + end,
                raw_block_bytes=end - match.start(), raw_block_sha256=sha(text[match.start():end].encode()),
                instruction_byte_reference=reference)
            canonical = [number, setup['generation'], operation, address, pc, raw.hex(),
                         [regs[key] for key in register_keys], record['received_first'], record['received_end'], reference]
            context_digest.update(json.dumps(canonical, separators=(',', ':')).encode() + b'\n')
            framing_digest.update(json.dumps([record['received_first'], record['received_end'], record['raw_block_sha256']], separators=(',', ':')).encode() + b'\n')
            counts[operation] += 1; totals[operation] += 1
            ports[(regs['port00'], regs['port01'])] += 1
            targets[(operation, address)] += 1
            opcodes[(operation, pc, raw.hex())] += 1
            refs[reference] += 1
            first_record = record if first_record is None else first_record
            last_record = record
            if reference.startswith('not_equal') and len(unmatched) < 8:
                unmatched.append(record)
            if not compact:
                records.append(record)
        windows.append(dict(response=response_reference(row), terminal_kind=row['status'],
            trace_hits=len(headers), compact_long_window=compact,
            late_hits_after_interrupt_request=7364 if compact else 0,
            terminal_response_offset=terminal,
            operation_counts=dict(sorted(counts.items())),
            ports=[dict(DDR=key[0], read01=key[1], hits=value) for key, value in sorted(ports.items())],
            targets=[dict(operation=key[0], address=key[1], hits=value) for key, value in sorted(targets.items())],
            instruction_codes=[dict(operation=key[0], PC=key[1], hex=key[2], hits=value) for key, value in sorted(opcodes.items())],
            instruction_byte_reference_counts=dict(sorted(refs.items())),
            all_hit_context_sha256=context_digest.hexdigest(), all_hit_raw_framing_sha256=framing_digest.hexdigest(),
            first_hit=first_record, last_hit=last_record, unmatched_reference_examples=unmatched,
            every_raw_header_instruction_clock_beam_AXYSP_and_attached_r_checked=True,
            retention='all-hit aggregates/digests plus first/last; complete original response pinned' if compact else 'every hit serialized in trace-hits.json'))
        print(json.dumps(dict(trace_window=sequence, hits=len(headers), compact=compact)), flush=True)
    assert [row['response']['sequence'] for row in windows] == [82, 88, 94, 100, 130, 136, 142]
    assert all(not 0xdc00 <= address <= 0xdcff for window in windows for address in [r['address'] for r in window['targets']])
    deferred = [record for record in records if record['sequence'] == 94 and record['instruction_PC'] == 0x97fc]
    assert len(deferred) == 1
    deferred = deferred[0]
    assert deferred['registers']['pc'] == 0x828c and deferred['registers']['clock'] == states['cutoff']['clock']
    assert deferred['monitored_address'] == 0xd000
    return dict(windows=windows, short_hits=records, operation_totals=dict(totals),
        all_raw_trace_headers_parsed=True, deferred_pre_cutoff_store_hook=deferred,
        DCxx_store_trace_configured=False, hardware_timer_deadline_validated=False,
        physical_bus_write_counts_inferred=False,
        digest_schema='CanonicalJSONline:[checkpoint,generation,operation,address,instructionPC,hex,[PC,A,X,Y,SP,DDR,read01,flags,line,cycle,clock],absoluteFirst,absoluteEnd,codeReference]. FramingJSONline:[absoluteFirst,absoluteEnd,rawBlockSHA256].',
        scope='All hits including late interrupt-drain traces are checked in retained order. A store hook reports observed post-step context, possibly after IRQ entry; it is not required to have PC=instructionPC+3. RMW hooks are not counted as all physical dummy/final bus writes. No timer or pixel interpreter is used.')


def primary_schema():
    archive_path = ROOT / 'build/research/quondam/hardware-source/vice-3.10.tar.gz'
    checks = {
        'vice-3.10/src/monitor/monitor.c': ['default_radix = e_hexadecimal;'],
        'vice-3.10/src/monitor/mon_parse.y': ['if (default_radix == e_hexadecimal)'],
        'vice-3.10/src/core/ciatimer.h': ['CIAT_CR_START'],
        'vice-3.10/src/core/ciacore.c': ['case CIA_CRB:           /* Control Register B */',
            '| ciat_is_running(cia_context->tb, rclk);'],
        'vice-3.10/src/c64/c64memsnapshot.c': ['pport.dir'],
    }
    members = []
    with tarfile.open(archive_path) as archive:
        for name, needles in checks.items():
            raw = archive.extractfile(name).read()
            text = raw.decode(); lines = text.splitlines()
            anchors = []
            for needle in needles:
                hits = [i + 1 for i, line in enumerate(lines) if needle in line]
                assert hits, (name, needle)
                anchors.append(dict(needle=needle, lines=hits))
            members.append(dict(member=name, bytes=len(raw), sha256=sha(raw), anchors=anchors))
    return dict(archive=artifact(archive_path), members=members,
        interpretation='Pinned VICE source plus the frozen snapshot reader schema. Timer running is timer_b_state bit0; raw serialized CRB09 alone is not a running proof. Monitor startup default is hexadecimal; actual normalized checkpoint responses also preserve $300/$12c.')


def command_audit(case):
    grammar = [r'r', r'sidefx off', r'bank ram', r'warp(?: on| off)?', r'resourceget "Speed"',
        r'break (?:exec )?\$?[0-9a-f]{4}(?: \$?[0-9a-f]{4})?(?: if .+)?',
        r'condition [0-9]+ if .+', r'trace store [0-9a-f]{4}(?: [0-9a-f]{4})?',
        r'command [0-9]+ "r"', r'delete [0-9]+', r'x', r'd [0-9a-f]{4} [0-9a-f]{4}',
        r'bsave "' + re.escape(str(CASE)) + r'/[a-z0-9-]+-ram\.bin" 0 0000 ffff',
        r'dump "' + re.escape(str(CASE)) + r'/[a-z0-9-]+\.vsf"',
        r'screenshot "' + re.escape(str(CASE)) + r'/[a-z0-9-]+\.png" 2']
    for row in case['responses'].values():
        assert any(re.fullmatch(pattern, row['command']) for pattern in grammar), row['command']
    return dict(all151ordinary_commands_classified=True, RAM_PC_register_patch_or_restore_commands=0,
        disk_or_keyboard_or_joystick_commands=0, actual_warp_queries=[response_reference(row)
            for row in case['responses'].values() if row['command'] in ('warp', 'resourceget "Speed"')],
        scope='Observation/checkpoint/trace/export commands plus explicit warp controls only; original sideB was attached at startup.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to((BASE / 'upscroll-native-analysis').resolve())
    out.mkdir(parents=True, exist_ok=False)
    checked = Path(__file__).read_bytes()
    (out / 'upscroll_native.checked.py').write_bytes(checked)
    try:
        for name, expected in PINS.items():
            assert sha((ROOT / name).read_bytes()) == expected, name
        inventory = closed_inventory()
        wire, case, adapter = audit_wire()
        reader = load('hat_upscroll_snapshot', 'research/quondam/snapshot_state.py')
        memories, captures, pair_adapter = capture_pairs(reader, wire, case)
        sources = source_bindings(memories, captures)
        points = checkpoints(case, captures)
        commands = command_audit(case)
        snapshots, context = machine_context(reader, memories, captures, sources)
        traces = trace_events(case, wire, points, memories, sources, captures)
        schema = primary_schema()
        sources.pop('raw_source')
        raw_hits = (json.dumps(traces.pop('short_hits'), indent=2) + '\n').encode()
        raw_snapshots = (json.dumps(snapshots, indent=2) + '\n').encode()
        outputs = [dict(name='upscroll_native.checked.py', bytes=len(checked), sha256=sha(checked)),
            dict(name='trace-hits.json', bytes=len(raw_hits), sha256=sha(raw_hits)),
            dict(name='capture-machine-context.json', bytes=len(raw_snapshots), sha256=sha(raw_snapshots))]
        proof = dict(pass_=True,
            scope='Closed original Hat sideB native02 custody, complete B8/B9 loaded-source byte binding, two bounded prepared-motion writes and two observed CIA1 cutoff/stack paths; no complete native pixel or timer-deadline model.',
            producer=artifact(Path(__file__)), inputs=[artifact(ROOT / p) for p in PINS],
            inventory=inventory, wire=wire.summary(case), wire_adapter=adapter, pair_adapter=pair_adapter,
            captures=captures, checkpoint_bindings=points, source_bindings=sources,
            bounded_machine_context=context, monitor_traces=traces, primary_schema=schema,
            command_audit=commands, waiting_notices=case['waits'], outputs=outputs,
            limits=[
                'All original wire bytes/events, pending handle, late trace hits, explicit read-only interruption and rejected phase pair remain pinned; there is no retry, RAM/PC patch or snapshot restore.',
                'The failed RL == 300 observer requested hexadecimal768. Its interrupted8048/line0 pair is custody evidence only, excluded from requested-line300/full-field acceptance. The corrected explicit$012c request naturally stops81B2 atline300/cycle0.',
                'Original B8/B9 source data is a separate strict Dali/source-classification result, not recovered from native RAM. The two complete43008-byte comparisons bind it to real loaded generations.',
                'Motion-pair writes update next consumer state. Current VIC Y/pointers are read separately; their source consumers precede the B9 call.',
                'The active cutoff is CIA1TimerB, not the B17 raster-IRQ mechanism. Snapshots and original code bind the source and stack transition; DCxx start/deadline writes were not traced, so hardware timer scheduling remains unvalidated.',
                'Elapsed observation clocks, store hooks and one cosmetic PNG do not establish delivered FPS, physical bus-write counts, full-field pixel equivalence, animation completeness or performance portability.',
                'This passive producer starts no emulator, CPU interpreter, subprocess, native process, socket, build or downloaded host program.'
            ])
        raw = (json.dumps(proof, indent=2) + '\n').encode()
        (out / 'trace-hits.json').write_bytes(raw_hits)
        (out / 'capture-machine-context.json').write_bytes(raw_snapshots)
        (out / 'upscroll-native-proof.json').write_bytes(raw)
        print(json.dumps(dict(pass_=True, pairs=len(captures), receipt_bytes=len(raw), receipt_sha256=sha(raw))))
    except Exception as error:
        (out / 'failure.json').write_text(json.dumps(dict(pass_=False, stage='passive-candidate',
            error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc(),
            producer=artifact(Path(__file__)), no_native_or_CPU_execution=True), indent=2) + '\n')
        raise


if __name__ == '__main__':
    main()
