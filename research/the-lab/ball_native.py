#!/usr/bin/env python3
"""Passive, fail-closed custody for the original Lab side-two ball capture.

Reads closed wire, original release bytes and saved machine states only. It
starts no subprocess, socket, C64 CPU, emulator, downloaded code or process.
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
import traceback
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/lab-polygons-20261109'
CASE = BASE / 'native-02'
OLD = ROOT / 'build/research/the-lab'
DISK = OLD / 'release/side2.d64'
MANIFEST_SHA = '9c0db5a102cdf10682e52a139708572ef5b210714094b6362a58607a29687465'
CASE_SHA = '47bffc8f059b0b88437c1638430808845bcf40578a1da9cabde659bae474bc2e'
COMMANDS_SHA = '325d6ed22d9b64d5a8868ce4056668d7a6e644f648b2cdb63b276157f2e1a020'
PINS = {
    'research/verify_vice_live.py': 'f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a',
    'research/vice_session_live.py': '4340d1b0394fa612f5e6a71edddcbc2daf947e59c4c3013ab3b850c886dc621c',
    'research/eod/controller.py': '033bafb6ac6e97283175ac6713af0eef60cb7991b653ee1c98c47a1a4afa83c9',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'research/the-hat/raster_case.py': 'c73146a9d7b4b71b379a4b801c55bd27ef18282bd9fdd4280ae7eba2fc5c06be',
    'research/the-hat/raster_hardware.py': 'f9d15a6d26b877f63591b3c1ff7e31d3cf9430165783c89cb53b35ea6e32a12f',
    'build/research/quondam/hardware-source/vice-3.10.tar.gz': '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1',
    'build/research/the-lab/the-lab.zip': 'ea4ab6a4f3c8b10a412e80e3a4f46f240405cf2a820a526f222af2b5e0e48717',
    'build/research/the-lab/release/side2.d64': 'd34101d9b5852020ed56b3574aae854c7b16befff893df77a6d6ec08198cdf3b',
    'build/research/the-lab/side2-bootstrap.prg': 'a1d61674083c1c8f5b7e7532a0b6709ebdd897375ba26d23e0892042ebe25d78',
    'build/research/the-lab/side2-analysis/depacked/00-0400-1ff9.prg': 'd702ab9e3c0d2c5d56ebdf52d1996d0761e9c17028c1c8cbc73beb88e6ea442f',
    'build/research/the-lab/side2-analysis/packed/00-102b.prg': '4d7ca9376a5587f474bb9e6d1a3ca98826288a7cf31a2873f2863c694047709b',
    'build/research/the-lab/side2-analysis/depacked/20.ram.bin': 'f866f5a03713f91979dc4ad8421f95b4a9da6b405faea55804112e9993e90ef8',
    'build/research/the-lab/side2-analysis/depacked/20.written.bin': '69666deef45da83279aadf998f467010be230b6adc32f80e3c8e099f2247c95a',
    'build/research/the-lab/side2-analysis/depacked/22-8c00-c34b.prg': 'e0eb89a8c11d6b1f1055c84573f4bd4c0a6cb9cbe0194930be1bce8801ec493f',
    'build/research/lab-polygons-20261109/native-01-files.json': 'e92365e77f85ac2ea6f1d39178a57cbf24fd4135f4ccaa6589a0807b48745403',
    'build/research/lab-polygons-20261109/native-02-files.json': MANIFEST_SHA,
    'build/research/lab-polygons-20261109/display-source-analysis/accepted-01/display-source-proof.json': '30431ebfbef385a2b05a9983b2ef0094005053563ae3d60da95ef9ef980712ed',
}
EXPECTED = {
    'sys': (0x080d, 10780741), 'first-loaded': (0x0480, 13368416),
    'script-entry': (0x2118, 231623664),
    'ball52-body-entry': (0x21bd, 237344345), 'ball52-edge-entry': (0x2209, 237344381),
    'ball52-events-ready': (0x224e, 237370833), 'ball52-render-done': (0x2265, 237431554),
    'ball52-request-queued': (0x2267, 237431559),
    'ball52-bank-selected': (0x21a9, 237441570), 'ball52-color-copied': (0x21ac, 237447041),
    'ball52-request-cleared': (0x21ae, 237447046),
    'ball52-wrap-a': (0x23d0, 237464137), 'ball52-wrap-b': (0x7bf8, 237483796),
    'fullcolor52-body-entry': (0x7234, 599016604),
}
REJECTED = ['fullcolor52-body-entry']
RAW = None


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def artifact(path):
    path = Path(path)
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=sha(data))


def load(name, relative):
    path = ROOT / relative
    assert sha(path.read_bytes()) == PINS[relative], ('Changed helper', relative)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def function_source(relative, name):
    source = (ROOT / relative).read_text()
    tree = ast.parse(source)
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    assert len(nodes) == 1
    return ast.get_source_segment(source, nodes[0]) + '\n'


def retained_response(row):
    global RAW
    if RAW is None:
        RAW = (CASE / 'received.bin').read_bytes()
    data = RAW[row['received_first']:row['received_end']]
    assert data.decode(errors='replace') == row['response']
    return data


def response_reference(row):
    raw = retained_response(row)
    return dict(sequence=row['sequence'], command=row['command'], status=row['status'],
        received_first=row['received_first'], received_end=row['received_end'],
        raw_bytes=len(raw), raw_sha256=sha(raw))


def closed_inventory():
    inputs = []
    for relative, expected in PINS.items():
        item = artifact(ROOT / relative)
        assert item['sha256'] == expected, ('Changed input', relative, item)
        inputs.append(item)
    cases = []
    for name, expected_count, expected_bytes in [('native-01', 7, 3935), ('native-02', 48, 4782035)]:
        receipt = json.loads((BASE / (name + '-files.json')).read_text())
        directory = BASE / name
        items = [dict(name=path.name, bytes=path.stat().st_size, sha256=sha(path.read_bytes()))
            for path in sorted(directory.iterdir()) if path.is_file()]
        assert items == receipt['files'] and len(items) == receipt['file_count'] == expected_count
        assert sum(item['bytes'] for item in items) == receipt['total_bytes'] == expected_bytes
        assert sha(canonical(items)) == receipt['listing_sha256']
        assert receipt['session'] == json.loads((directory / 'session.json').read_text())
        session = receipt['session']
        assert session['owned_process_reaped'] and session['exit_code'] == -15
        assert session['closed_utc'] and session['program'] == str(DISK)
        cases.append(dict(manifest=artifact(BASE / (name + '-files.json')), **receipt))
    failed = cases[0]
    events = [json.loads(line) for line in (BASE / 'native-01/events.jsonl').read_text().splitlines()]
    assert [event['kind'] for event in events] == ['owned_process_started', 'observer_error', 'owned_terminate_requested', 'closed']
    assert events[1]['error'] == failed['session']['observer_error'] == "OSError(22, 'Invalid argument')"
    assert failed['response_count'] == 0 and not failed['all_other_requested_source_stops_natural']
    assert not list((BASE / 'native-01').glob('*.vsf'))
    assert all((BASE / 'native-01' / name).stat().st_size == 0 for name in ('input.bin', 'sent.bin', 'received.bin', 'monitor.log'))
    return dict(inputs=inputs, closed_cases=cases, failed_startup_is_host_observation_only=True,
        startup_diagnostic=artifact(BASE / 'native-launch-diagnostic.json'))


def audit_wire():
    wire = load('lab_ball_frozen_wire', 'research/verify_vice_live.py')
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
    exec(compile(adapted, '<Lab-original-side2-startup-only-adapter>', 'exec'), wire.__dict__)
    case = wire.audit_session('native-02')
    rows = case['responses']
    receipt = json.loads((BASE / 'native-02-files.json').read_text())
    assert not case['partial'] and not case['cancelled'] and sorted(rows) == list(range(1, 178))
    assert Counter(row['status'] for row in rows.values()) == {'completed': 176, 'interrupted': 1}
    assert [n for n, row in rows.items() if row['status'] == 'interrupted'] == [161]
    assert Counter(row['purpose'] for row in case['requests']) == {'ordinary': 177, 'interrupt': 1}
    assert sum(not row['internal'] for row in rows.values()) == 175
    assert sha(json.dumps([rows[n]['command'] for n in range(1, 178)], separators=(',', ':')).encode()) == COMMANDS_SHA
    assert case['waits'] == receipt['waits'] and len(case['waits']) == 1 and case['waits'][0]['sequence'] == 161
    assert case['waits'][0]['elapsed_seconds'] == 30.08 and case['waits'][0]['received_bytes'] == 0
    assert receipt['rejected_capture_stems'] == REJECTED and receipt['all_other_requested_source_stops_natural']
    rejection = receipt['syntax_rejections']
    assert len(rejection) == 1 and rejection[0]['sequence'] == 152
    assert rows[152]['command'] == rejection[0]['command']
    assert sha(retained_response(rows[152])) == rejection[0]['response_sha256'] == 'ea1c79d40998925f0b3e0aff5d6199eb8d8d139919c61aaa0c25d99b14195539'
    assert rows[152]['response'].count('ERROR --') == 2 and 'BREAK:' not in rows[152]['response']
    assert not any(re.search(r'ERROR --|Syntax error|Unknown resource', row['response']) for n, row in rows.items() if n != 152)
    assert rows[161]['interrupt']['response_first'] == 0 and rows[161]['interrupt']['received_first'] == rows[161]['received_first']
    assert wire.registers(rows[161]['response']) == wire.registers(rows[161]['interrupt']['register_response'])
    assert len(retained_response(rows[161])) == 126 and '(Trace' not in rows[161]['response']
    permitted = re.compile(r'(?:r|x|bank (?:ram|io)|sidefx off|warp(?: on| off)?|resourceget "(?:Speed|VICIIModel|VICIIBorderMode)"|dummy|delete \d+|trace store [0-9a-f]{4} [0-9a-f]{4}|command \d+ "r"|break .+|bsave ".+" 0 [0-9a-f]{4} [0-9a-f]{4}|dump ".+"|screenshot ".+" 2|m d000 d03f)')
    assert all(permitted.fullmatch(row['command']) for row in rows.values())
    assert rows[2]['command'] == 'sidefx off' and rows[2]['response'] == '(C:$fd75) '
    launch = case['session']['command']
    assert '-pal' in launch and launch[launch.index('-speed') + 1] == '100'
    assert '+warp' in launch and '+autostart-warp' in launch and '-drive8truedrive' in launch
    assert launch[launch.index('-drive8type') + 1] == '1541'
    return wire, case, dict(original_function_sha256=sha(original.encode()), adapted_function_sha256=sha(adapted.encode()),
        exact_old_startup_assertion=old, exact_startup_replacement=replacement,
        only_one_auditor_replacement=True, ordinary_and_interrupt_register_parsers_unchanged=True,
        syntax_rejection=response_reference(rows[152]), rejected_interrupted_stop=response_reference(rows[161]),
        no_retries_no_payload_or_PC_writes_no_restore_no_disk_replacement=True)


def capture_pairs(reader, wire, case):
    helper = load('lab_ball_frozen_pairs', 'research/eod/controller.py')
    helper.CASE = CASE
    helper.DECLARED_INTERRUPTS = [161]
    original = function_source('research/eod/controller.py', 'capture_pairs')
    old = "assert mem[1] == mem[65542] == regs['port00'] == 0x2f"
    replacement = "assert mem[1] == mem[65542] == regs['port00']"
    assert original.count(old) == 1
    adapted = original.replace(old, replacement)
    first = original.index('        stopped = list(re.finditer(')
    last = original.index('        assert not any(responses[n]', first)
    block = original[first:last]
    interrupt = ("        if responses[stop]['status'] == 'interrupted':\n"
        "            assert stop in DECLARED_INTERRUPTS\n"
        "            assert wire.registers(responses[stop]['interrupt']['register_response']) == regs\n"
        "        else:\n" + ''.join('    ' + line for line in block.splitlines(keepends=True)))
    assert adapted.count(block) == 1
    adapted = adapted.replace(block, interrupt)
    exec(compile(adapted, '<Lab-actual-DDR-and-one-rejected-interrupt>', 'exec'), helper.__dict__)
    memories, captures = helper.capture_pairs(reader, wire, case)
    assert len(captures) == 14 and {row['stem'] for row in captures} == set(EXPECTED)
    for row in captures:
        assert (row['registers']['pc'], row['registers']['clock']) == EXPECTED[row['stem']]
        rejected = row['stem'] in REJECTED
        assert (case['responses'][row['stop_sequence']]['status'] == 'interrupted') == rejected
        row['accepted_natural_phase'] = not rejected
        row['stop_kind'] = 'read-only interrupted observer failure; rejected source phase' if rejected else 'natural exec checkpoint'
    return memories, captures, dict(original_function_sha256=sha(original.encode()), adapted_function_sha256=sha(adapted.encode()),
        exact_DDR_replacement=replacement, exact_original_stop_block=block, exact_interrupted_stop_replacement=interrupt,
        only_two_pair_replacements=True, all65536_RAM_bytes_CPU_flags_clock_beam_and_port_consistency_preserved=True)


def checkpoints(case, captures):
    # Reuse the frozen strict grammar/predicate evaluator, adding only the exact
    # rejected command152 branch. It must not create a checkpoint generation.
    frozen = load('lab_ball_frozen_checkpoints', 'research/the-hat/raster_case.py')
    original = function_source('research/the-hat/raster_case.py', 'checkpoints')
    before = "        if command.startswith(('break ', 'trace exec ', 'trace store ', 'trace load ')):"
    after = ("        if sequence == 152:\n"
        "            assert command == REJECTED_COMMAND and sha(retained_response(row)) == REJECTED_RESPONSE_SHA\n"
        "            continue\n" + before)
    assert original.count(before) == 1
    adapted = original.replace(before, after)
    frozen.CASE, frozen.PROFILE, frozen.ATTACHED_COMMANDS = CASE, {'interrupt_sequences': [161], 'rejected_captures': REJECTED}, ['r']
    frozen.REJECTED_COMMAND = case['responses'][152]['command']
    frozen.REJECTED_RESPONSE_SHA = 'ea1c79d40998925f0b3e0aff5d6199eb8d8d139919c61aaa0c25d99b14195539'
    frozen.retained_response, frozen.response_reference = retained_response, response_reference
    frozen.wire_registers_final = lambda c, n: case['_wire'].registers(c['responses'][n]['interrupt']['register_response'])
    exec(compile(adapted, '<Lab-exact-rejected-break-does-not-create-checkpoint>', 'exec'), frozen.__dict__)
    points = frozen.checkpoints(case, captures)
    assert len(points['setups']) == 20 and all(item['setup']['sequence'] != 152 for item in points['setups'])
    rejected = next(row for row in points['capture_stops'] if row['stem'] in REJECTED)
    assert rejected['active'] == [] and rejected['condition_evaluations_at_actual_interrupted_point'] == []
    return points, dict(original_function_sha256=sha(original.encode()), adapted_function_sha256=sha(adapted.encode()),
        exact_rejection_branch=after, strict_unknown_condition_rejection_preserved=True,
        rejected_condition_was_never_an_active_breakpoint=True)


def original_bindings(memories, captures):
    archive = OLD / 'the-lab.zip'
    disk = DISK.read_bytes()
    with zipfile.ZipFile(archive) as bundle:
        names = [name for name in bundle.namelist() if name.split('/')[-1].lower() == 'side2.d64']
        assert len(names) == 1 and bundle.read(names[0]) == disk
        original_member = names[0]
    def sector(track, number):
        assert 1 <= track <= 40
        sectors = lambda t: 21 if t <= 17 else 19 if t <= 24 else 18 if t <= 30 else 17
        assert 0 <= number < sectors(track)
        first = (sum(sectors(t) for t in range(1, track)) + number) * 256
        return disk[first:first + 256]
    directory = sector(18, 1)
    entry = directory[2:32]
    assert entry[0] == 0x82 and entry[1:3] == bytes([18, 2])
    assert int.from_bytes(entry[28:30], 'little') == 1
    track, number, chunks, chain = 18, 2, [], []
    while track:
        assert [track, number] not in chain
        chain.append([track, number])
        raw = sector(track, number)
        chunks.append(raw[2:] if raw[0] else raw[2:raw[1] + 1])
        track, number = raw[0], raw[1]
    boot = b''.join(chunks)
    assert chain == [[18, n] for n in range(2, 12)] and number == 225
    assert boot == (OLD / 'side2-bootstrap.prg').read_bytes() and len(boot) == 2510
    assert boot[:2] == b'\x01\x08' and boot[6:13] == b'\x9e2061\x00\x00'
    assert memories['sys'][0x801:0x11cd] == boot[2:]
    file0 = (OLD / 'side2-analysis/depacked/00-0400-1ff9.prg').read_bytes()
    assert file0[:2] == b'\x00\x04' and len(file0) == 7164
    assert memories['first-loaded'][0x400:0x1ffa] == file0[2:]
    packed = (OLD / 'side2-analysis/packed/00-102b.prg').read_bytes()
    assert memories['first-loaded'][0x1ffa:0x1ffc] == packed[-2:] == b'\xdd\x00'
    file22 = (OLD / 'side2-analysis/depacked/22-8c00-c34b.prg').read_bytes()
    assert file22[:2] == b'\x00\x8c' and len(file22) == 14158
    assert memories['script-entry'][0x8c00:0xc34c] == file22[2:]
    proof_path = BASE / 'display-source-analysis/accepted-01/display-source-proof.json'
    display = json.loads(proof_path.read_text())
    assert display['pass_']
    source20 = (OLD / 'side2-analysis/depacked/20.ram.bin').read_bytes()
    mask20 = (OLD / 'side2-analysis/depacked/20.written.bin').read_bytes()
    assert len(source20) == len(mask20) == 65536
    guards = []
    for guard in display['publication']['guards']:
        first, end = guard['first'], guard['end_exclusive']
        raw = bytes.fromhex(guard['hex'])
        assert len(raw) == end - first and sha(raw) == guard['sha256']
        if first < 0x8c00:
            assert all(mask20[first:end]) and source20[first:end] == raw
        else:
            assert file22[2 + first - 0x8c00:2 + end - 0x8c00] == raw
        matched = []
        for capture in captures:
            stem = capture['stem']
            if not stem.startswith('ball52-'):
                continue
            assert memories[stem][first:end] == raw, (stem, guard['role'])
            matched.append(stem)
        guards.append(dict(**guard, matched_natural_captures=matched))
    loaded = []
    for capture in captures:
        stem = capture['stem']
        if not stem.startswith('ball52-'):
            continue
        raw = memories[stem]
        assert raw[0x8c00:0x9016] == file22[2:2 + 0x416]
        assert raw[0x9026:0xc34c] == file22[2 + 0x426:]
        loaded.append(dict(stem=stem, prefix_8C00_9016_equal=True, stream_9026_C34C_equal=True,
            mutable_runtime_palette_9016_9026=list(raw[0x9016:0x9026])))
    return dict(original_release=artifact(archive), disk=artifact(DISK), original_disk_member=original_member,
        DOS_first_PRG=dict(directory_declared_blocks=1, actual_sector_chain=chain, actual_bytes=len(boot),
            extracted_sha256=sha(boot), same_retained_PRG=True, load=0x801, SYS=0x80d,
            native_payload_bytes_equal=2508, not_custom_file_zero=True),
        file_zero=dict(source=artifact(OLD / 'side2-analysis/depacked/00-0400-1ff9.prg'),
            native_entry=0x480, decoded_output_first=0x400, decoded_output_end_exclusive=0x1ffa,
            native_output_bytes_equal=7162, legacy_decoded_original_prediction=True,
            untouched_packed_tail=dict(first=0x1ffa, end_exclusive=0x1ffc, hex='dd00')),
        file22=dict(source=artifact(OLD / 'side2-analysis/depacked/22-8c00-c34b.prg'),
            native_script_call=0x2118, first=0x8c00, end_exclusive=0xc34c,
            script_entry_bytes_equal=14156, stream_first=0x9026, stream_end_exclusive=0xc34c,
            stream_sha256=sha(file22[2 + 0x426:]), runtime_bindings=loaded),
        display_source_contract=artifact(proof_path), guarded_original_code=guards,
        limitation='No depacker/6502 is executed here. Frozen original decode bytes are compared with this untouched natural run; generated or self-modifying runtime bytes are a separate earlier native context.'), source20, mask20


def machine_contexts(reader, hardware, memories, captures, case, output):
    result = {}
    rows = case['responses']
    for capture in captures:
        stem = capture['stem']
        path = CASE / (stem + '.vsf')
        state = hardware.read_extended_snapshot(path, 0)
        vic, cia = state['vicii'], state['cia']['CIA2']
        assert vic['model'] == 1 and state['modules']['VIC-II']['version'] == [1, 3]
        assert state['raster_hardware_extension']['remaining_opaque_bytes'] == 0
        raw = memories[stem]
        mem = reader.module_payload(path, 'C64MEM')
        assert len(mem) == 65555
        glue = reader.module_payload(path, 'GLUE')
        assert state['modules']['GLUE']['version'] == [1, 0] and len(glue) == 3
        d018 = vic['regs'][0x18]
        pins = (cia['pra'] | (~cia['ddra'] & 255)) & 3
        bank = ((~pins) & 3) << 14
        summary = dict(registers=capture['registers'], accepted_natural_phase=capture['accepted_natural_phase'],
            CPU_memory_port=capture['ports'], EXROM=mem[2], GAME=mem[3],
            CIA2=dict(PRA=cia['pra'], DDRA=cia['ddra'], driven_low_two_bits=(cia['ddra'] & 3) == 3,
                effective_low_pins=pins, derived_VIC_bank=bank), GLUE_raw=glue.hex(),
            VIC=dict(D011=vic['regs'][0x11], D016=vic['regs'][0x16], D018_stored=d018,
                D015_sprite_enable=vic['regs'][0x15], D01A_IRQmask=vic['regs'][0x1a],
                D020=vic['regs'][0x20], D021=vic['regs'][0x21],
                derived_screen=bank + ((d018 & 0xf0) << 6), derived_bitmap=bank + ((d018 & 8) << 10),
                normal_multicolor_bitmap=(vic['regs'][0x11] & 0x60) == 0x20 and bool(vic['regs'][0x16] & 0x10)),
            selector43=raw[0x43], request44=raw[0x44], edge_pointer=int.from_bytes(raw[0x3e:0x40], 'little'),
            palette9016_9026=list(raw[0x9016:0x9026]),
            memory_slices=[dict(first=a, end_exclusive=b, sha256=sha(raw[a:b])) for a,b in
                [(0x4000,0x5f40),(0x6000,0x63e8),(0xdc00,0xdfe8),(0xe000,0xff40),(0xc380,0xc5c0),(0xc5c0,0xc800),(0xc800,0xda00)]])
        color_path = CASE / (stem + '-color.bin')
        if color_path.exists():
            color_seq = capture['snapshot_sequence'] + 2
            assert rows[color_seq - 1]['command'] == 'bank io'
            assert rows[color_seq]['command'] == f'bsave "{color_path}" 0 d800 dbff'
            assert rows[color_seq + 1]['command'] in ('bank ram', 'm d000 d03f')
            assert not any(rows[n]['command'] == 'x' for n in range(capture['stop_sequence'] + 1, color_seq + 1))
            color_raw = color_path.read_bytes()
            actual = bytes(vic['color_ram'])
            assert len(color_raw) == len(actual) == 1024
            assert bytes(value & 15 for value in color_raw) == actual
            summary['actual_ColorRAM'] = dict(artifact=artifact(color_path), io_bank_export_sequence=color_seq,
                all1024_low_nibbles_equal_snapshot_device=True, low_nibble_sha256=sha(actual),
                export_high_nibbles=sorted(set(value >> 4 for value in color_raw)),
                underlying_physical_D800_RAM_is_a_different_object=True)
        else:
            assert stem in ('sys', 'first-loaded')
        if stem.startswith('ball52-'):
            assert mem[1] == 0x37 and (mem[0] & 7) in (4,5)
            assert mem[2:4] == b'\x00\x00' and cia['ddra'] == 0x3f
            assert summary['VIC']['normal_multicolor_bitmap'] and vic['regs'][0x11] == 0x3b
            assert vic['regs'][0x16] == 0xd8 and vic['regs'][0x15] == 0
        if stem in ('ball52-wrap-a','ball52-wrap-b'):
            assert capture['registers']['line'] == state['raster_hardware_extension']['raster_store']['current_line'] == 0
            assert capture['registers']['cycle'] in (1,4)
            frame = hardware.framebuffer_bytes(path)
            assert len(frame) == 384 * 312
            viewport = frame[16*384:288*384]
            name = stem + '-retained-viewport-384x272.bin'
            (output / name).write_bytes(viewport)
            summary['retained_committed_viewport'] = dict(output_name=name, bytes=len(viewport), sha256=sha(viewport),
                rows=[16,287], width=384, height=272, origin='Unpadded framebuffer raster row16, physical pixel0',
                actual_stop_line=0, actual_stop_cycle=capture['registers']['cycle'],
                lifetime='Every normal displayed viewport row was committed in the preceding field; row0 is the current new-field line. This is a native pixel oracle, not an independently generated composition or a claim about all312rows.')
        result[stem] = dict(summary=summary, frozen_core_and_extended_state=state)
    queries = []
    expected = {9:'Warp mode is off.',10:'Speed=100',11:'VICIIModel=1',12:'VICIIBorderMode=0',
        13:'Checkpoints will not trigger on dummy accesses.',26:'Warp mode is off.',27:'Speed=100',
        28:'VICIIModel=1',29:'VICIIBorderMode=0',30:'Checkpoints will not trigger on dummy accesses.',
        44:'Warp mode is off.',45:'Speed=100',163:'Warp mode is off.',164:'Speed=100',
        173:'Warp mode is off.',174:'Speed=100',175:'VICIIModel=1',176:'VICIIBorderMode=0',
        177:'Checkpoints will not trigger on dummy accesses.'}
    for sequence, prefix in expected.items():
        assert rows[sequence]['response'].startswith(prefix + '\n')
        queries.append(dict(expected_value=prefix, **response_reference(rows[sequence])))
    return dict(captures=result, actual_resource_queries=queries,
        frozen_snapshot_reader=artifact(ROOT / 'research/quondam/snapshot_state.py'),
        extended_snapshot_reader=artifact(ROOT / 'research/the-hat/raster_hardware.py'),
        no_CPU_or_pipeline_advanced=True)


def trace_events(case, wire, points, memories, source20, mask20, captures):
    header = re.compile(r'#([0-9]+) \(Trace\s+(exec|store|load) ([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\n')
    instruction = re.compile(r'^\.C:([0-9a-f]{4})\s+([0-9A-F]{2}(?: [0-9A-F]{2}){0,2})\s+(.+?)\s+- A:([0-9A-F]{2}) X:([0-9A-F]{2}) Y:([0-9A-F]{2}) SP:([0-9a-f]{2}) ([NV\-BDIZC.]{8})\s+(\d+)\n', re.M)
    setups = [row for row in points['setups'] if row['kind'] == 'TRACE']
    assert [(r['number'], r['first'], r['last']) for r in setups] == [
        (5,0,1),(6,0xd000,0xd3ff),(7,0xd800,0xdbff),(8,0xdd00,0xdd03),
        (9,0x9016,0x9025),(10,0xc380,0xc7ff)]
    records, windows, last_clock = [], [], None
    for sequence,row in sorted(case['responses'].items()):
        if row['command'] != 'x':
            assert not header.search(retained_response(row).decode('latin1'))
            continue
        raw = retained_response(row)
        text = raw.decode('latin1')
        matches = list(header.finditer(text))
        assert text.count('(Trace') == len(matches)
        if not matches:
            continue
        assert row['status'] == 'completed'
        stop = re.search(r'^#[0-9]+ \(Stop on', text, re.M)
        assert stop and matches[-1].start() < stop.start()
        counts, targets, ports, refs = Counter(), Counter(), Counter(), Counter()
        first_record = len(records)
        for i,match in enumerate(matches):
            number, operation, address = int(match[1]), match[2], int(match[3],16)
            candidates = [r for r in setups if r['number']==number and r['setup']['sequence'] < sequence < r['deleted_sequence']]
            assert len(candidates)==1
            setup = candidates[0]
            assert setup['operation'] == operation == 'store' and setup['first'] <= address <= setup['last']
            assert setup['attached_command_text'] == 'r' and setup['attached_r']['sequence'] < sequence
            end = matches[i+1].start() if i+1<len(matches) else stop.start()
            segment = text[match.end():end]
            ins = instruction.search(segment)
            assert ins and len(instruction.findall(segment)) == 1 and segment.count('Executing: r') == 1
            assert '>C:' not in segment
            regs = wire.registers(segment)
            pc, code = int(ins[1],16), bytes.fromhex(ins[2])
            assert regs['clock'] == int(ins[9])
            assert (regs['line'],regs['cycle']) == (int(match[4]),int(match[5]))
            assert (regs['clock']//63%312,regs['clock']%63) == (regs['line'],regs['cycle'])
            assert [regs[k] for k in ('a','x','y','sp')] == [int(ins[k],16) for k in (4,5,6,7)]
            assert last_clock is None or regs['clock'] >= last_clock
            last_clock = regs['clock']
            if all(mask20[pc:pc+len(code)]) and source20[pc:pc+len(code)] == code:
                reference = 'frozen_original_file20_written_code_bytes'
            else:
                earlier = [c for c in captures if c['accepted_natural_phase'] and c['registers']['clock'] <= regs['clock']
                    and memories[c['stem']][pc:pc+len(code)] == code]
                assert earlier, ('No earlier original-run instruction-byte context', sequence,hex(pc),code.hex())
                reference = 'earlier_natural_native_context:' + earlier[-1]['stem']
            record = dict(sequence=sequence, checkpoint=number, checkpoint_generation=setup['generation'],
                operation=operation, monitored_address=address, instruction_PC=pc, instruction_hex=code.hex(),
                instruction=ins[3], registers=regs, instruction_byte_reference=reference,
                setup_sequence=setup['setup']['sequence'], attached_r_sequence=setup['attached_r']['sequence'],
                received_first=row['received_first']+match.start(), received_end=row['received_first']+end,
                raw_block_bytes=end-match.start(), raw_block_sha256=sha(raw[match.start():end]))
            # These are raw final source-store register values, not a CPU model.
            if code[0] in (0x85,0x95,0x8d,0x9d,0x99,0x81,0x91):
                record['raw_source_store_value'] = regs['a']
            elif code[0] in (0x86,0x96,0x8e):
                record['raw_source_store_value'] = regs['x']
            elif code[0] in (0x84,0x94,0x8c):
                record['raw_source_store_value'] = regs['y']
            records.append(record)
            counts[operation]+=1;targets[address]+=1;ports[(regs['port00'],regs['port01'])]+=1;refs[reference]+=1
        subset=records[first_record:]
        windows.append(dict(sequence=sequence, response=response_reference(row), first_record=first_record,
            record_count=len(subset), canonical_records_sha256=sha(canonical(subset)), operations=dict(counts),
            targets=[dict(address=a,count=n) for a,n in sorted(targets.items())],
            CPU_ports=[dict(DDR=d,readback=p,count=n) for (d,p),n in sorted(ports.items())],
            instruction_byte_references=dict(refs)))
    assert windows and records
    return dict(records=records, windows=windows, count=len(records),
        watched_ranges_complete_from_setup_to_delete=True,
        all_raw_trace_headers_and_attached_register_rows_consumed=True,
        source_store_values_are_observer_oracles_not_model_inputs=True,
        limitations=['Watch coverage is the six declared address ranges only; no bitmap/screen RAM-write history is claimed.',
            'Dummy accesses do not trigger checkpoints. This is a monitor hook history, not every physical NMOS bus transfer.',
            'D800-addressed hooks can target underlying RAM while CPU01=34. Device identity requires the captured CPU mapping.',
            'Attached-r PC is recorded as observed and is not forced to source-PC+instruction-length.'])


def publication_observations(contexts, memories, captures, traces):
    summaries={name:row['summary'] for name,row in contexts['captures'].items()}
    ordering=['ball52-body-entry','ball52-edge-entry','ball52-events-ready','ball52-render-done',
        'ball52-request-queued','ball52-bank-selected','ball52-color-copied','ball52-request-cleared','ball52-wrap-a','ball52-wrap-b']
    expected=[(0,0),(0,0),(0,0),(0,0),(0,1),(1,1),(1,1),(1,0),(1,0),(1,0)]
    for name,pair in zip(ordering,expected):
        row=summaries[name]
        assert (row['selector43'],row['request44'])==pair
        new=name in ordering[5:]
        assert (row['CIA2']['derived_VIC_bank'],row['VIC']['D018_stored'],row['VIC']['derived_screen'],row['VIC']['derived_bitmap']) == (
            (0x4000,0x80,0x6000,0x4000) if new else (0xc000,0x78,0xdc00,0xe000))
        assert row['GLUE_raw']==('010100' if new else '010300')
        if name in ordering[:8]:
            assert row['edge_pointer']==0xbfe8
    before='ball52-bank-selected';after='ball52-color-copied'
    assert summaries[before]['actual_ColorRAM']['low_nibble_sha256'] == summaries['ball52-render-done']['actual_ColorRAM']['low_nibble_sha256']
    a=bytes(contexts['captures'][before]['frozen_core_and_extended_state']['vicii']['color_ram'])
    b=bytes(contexts['captures'][after]['frozen_core_and_extended_state']['vicii']['color_ram'])
    changed=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y]
    assert changed
    copied=[r for r in traces['records'] if r['sequence']==113 and r['checkpoint']==7]
    assert len(copied)==484 and all(r['registers']['port01']==0x35 and 'raw_source_store_value' in r for r in copied)
    assert len({r['monitored_address'] for r in copied})==484
    replay=bytearray(a)
    for row in copied:
        replay[row['monitored_address']-0xd800]=row['raw_source_store_value']&15
    assert bytes(replay)==b
    # Pure replay of observed writes is an observation-consistency check only.
    # Independent source-derived attribute prediction belongs to a separate lane.
    first_completed=summaries['ball52-wrap-a']['registers']['clock']
    second_completed=summaries['ball52-wrap-b']['registers']['clock']
    assert second_completed-first_completed==19659 # one PAL frame plus three stop cycles
    assert summaries['ball52-wrap-a']['retained_committed_viewport']['sha256']==summaries['ball52-wrap-b']['retained_committed_viewport']['sha256']
    return dict(stages=[dict(stem=name,**summaries[name]) for name in ordering],
        hardware_ColorRAM_publication=dict(before=before,after=after,changed_cells=len(changed),
            changed_cell_offsets=changed,observed_store_count=len(copied),unique_destinations=484,
            replay_observed_low_nibble_stores_matches_all1024_device_cells=True,
            independent_source_attribute_prediction=False),
        post_publication_viewport_endpoints=['ball52-wrap-a','ball52-wrap-b'],
        limitations=['Native01 is host startup failure only.',
            'The later rejected fullcolor52-body-entry export is not any requested source phase and is excluded here.',
            'No FPS, real-time performance, original exporter topology, full pixel composition, full frame312rows or cycle-accurate hardware simulation is claimed.',
            'The front/pending bank facts and final ColorRAM observations do not themselves predict any polygon attribute values.'])


def write_json(path, data):
    path.write_text(json.dumps(data,indent=2)+'\n')


def run(output):
    output.mkdir(parents=True,exist_ok=False)
    source=Path(__file__).read_bytes()
    (output/'ball_native.checked.py').write_bytes(source)
    try:
        inventory=closed_inventory()
        wire,case,wire_adapter=audit_wire()
        case['_wire']=wire
        reader=load('lab_ball_frozen_snapshot','research/quondam/snapshot_state.py')
        hardware=load('lab_ball_extended_snapshot','research/the-hat/raster_hardware.py')
        memories,captures,pair_adapter=capture_pairs(reader,wire,case)
        points,checkpoint_adapter=checkpoints(case,captures)
        sources,source20,mask20=original_bindings(memories,captures)
        contexts=machine_contexts(reader,hardware,memories,captures,case,output)
        traces=trace_events(case,wire,points,memories,source20,mask20,captures)
        publication=publication_observations(contexts,memories,captures,traces)
        write_json(output/'capture-machine-context.json',contexts)
        write_json(output/'trace-hits.json',traces['records'])
        write_json(output/'publication-observations.json',publication)
        outputs=[dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(output.iterdir()) if p.is_file()]
        proof=dict(pass_=True,scope='Closed original side2 untouched natural run, stopped machine-state custody, original-byte bindings, declared watch history and publication observations only.',
            producer=dict(path=str(Path(__file__).relative_to(ROOT)),bytes=len(source),sha256=sha(source)),
            inputs=inventory['inputs'],closed_case_inventory=inventory,
            wire=dict(session=case['session'],responses=177,ordinary_public_commands=175,internal_responses=2,
                completed=176,interrupted=1,commands_sha256=COMMANDS_SHA,waits=case['waits'],
                response_references=[response_reference(row) for _,row in sorted(case['responses'].items())]),
            adapters=dict(wire=wire_adapter,pairs=pair_adapter,checkpoints=checkpoint_adapter),
            captures=captures,checkpoint_bindings=points,original_source_bindings=sources,
            monitor_traces={k:v for k,v in traces.items() if k!='records'},
            publication_summary=dict(post_publication_viewport_endpoints=publication['post_publication_viewport_endpoints'],
                ColorRAM_changed_cells=publication['hardware_ColorRAM_publication']['changed_cells']),
            rejected_capture_stems=REJECTED,accepted_natural_pairs=13,retained_rejected_pairs=1,
            outputs=outputs,limits=publication['limitations'])
        write_json(output/'ball-native-proof.json',proof)
        print(json.dumps(dict(pass_=True,proof=artifact(output/'ball-native-proof.json'),captures=len(captures),traces=traces['count'],outputs=len(outputs)+1)))
    except Exception as error:
        write_json(output/'failure.json',dict(pass_=False,error=repr(error),traceback=traceback.format_exc(),
            producer_sha256=sha(source),retained_checked_source=True))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    run(args.output.resolve())
