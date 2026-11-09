#!/usr/bin/env python3
"""Passive custody and bounded source bindings for closed original Hat native03.

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
CASE = BASE / 'native-03'
SOURCE = BASE / 'dali-analysis/neighbor-probe-02/accepted-01'
DISK = BASE / 'release/the-hat-7a825b1-b.d64'
CASE_SHA = 'a421461d4718ac2d52a1f83f130bde75ea495d4ada207bd826a6deb3821b83c4'
COMMANDS_SHA = '0018d3bd683b535f6d38063f230e51f6713adad36415b1ba2aa7879ddd962a7f'
PROFILE = {'manifest_name': 'native-03-files.json', 'manifest_sha256': '825eb76a391ed0f03a3d7c8b19fca871309c716fbb0f89b659afe195b89cb909', 'file_count': 91, 'total_bytes': 21779310, 'command_count': 386, 'status_counts': {'completed': 386}, 'interrupt_sequences': [], 'waits': [{'utc': '2026-11-08T22:09:15.406674+00:00', 'kind': 'observation_timeout', 'status': 'partial', 'waiting': True, 'elapsed_seconds': 30.008, 'sequence': 23, 'id': 'natural-b7-loaded', 'command': 'x', 'internal': False, 'received_bytes': 0, 'action': 'Still pending; send interrupt or close. No retry or restart.'}], 'rejected_captures': [], 'compact_sequences': [], 'whole_loaded_stems': ['b7-loaded', 'b8-controller'], 'raster_stems': ['even-consumer', 'even-copied', 'even-latch', 'even-before-start', 'even-started', 'even-selector', 'even-cutoff', 'even-restored', 'even-field-end', 'odd-consumer', 'odd-copied', 'odd-latch', 'odd-before-start', 'odd-started', 'odd-selector', 'odd-cutoff', 'odd-restored', 'odd-field-end', 'even-readback-consumer', 'even-readback-copied', 'even-readback-latch', 'even-readback-before-start', 'even-readback-started', 'even-readback-selector', 'even-readback-cutoff', 'even-readback-restored', 'even-readback-field-end', 'odd-readback-consumer', 'odd-readback-copied', 'odd-readback-latch', 'odd-readback-before-start', 'odd-readback-started', 'odd-readback-selector', 'odd-readback-cutoff', 'odd-readback-restored', 'odd-readback-field-end'], 'fields': [{'label': 'even', 'stages': {'before': 'even-consumer', 'copied': 'even-copied', 'latch': 'even-latch', 'before_start': 'even-before-start', 'started': 'even-started', 'selector': 'even-selector', 'cutoff': 'even-cutoff', 'restored': 'even-restored', 'completed': 'even-field-end'}, 'cursor_index': 899, 'current_pair': [14, 16], 'next_index': 900, 'next_pair': [13, 16], 'attached_command': 'r'}, {'label': 'odd', 'stages': {'before': 'odd-consumer', 'copied': 'odd-copied', 'latch': 'odd-latch', 'before_start': 'odd-before-start', 'started': 'odd-started', 'selector': 'odd-selector', 'cutoff': 'odd-cutoff', 'restored': 'odd-restored', 'completed': 'odd-field-end'}, 'cursor_index': 942, 'current_pair': [16, 24], 'next_index': 943, 'next_pair': [16, 24], 'attached_command': 'r'}, {'label': 'even-readback', 'stages': {'before': 'even-readback-consumer', 'copied': 'even-readback-copied', 'latch': 'even-readback-latch', 'before_start': 'even-readback-before-start', 'started': 'even-readback-started', 'selector': 'even-readback-selector', 'cutoff': 'even-readback-cutoff', 'restored': 'even-readback-restored', 'completed': 'even-readback-field-end'}, 'cursor_index': 975, 'current_pair': [23, 32], 'next_index': 976, 'next_pair': [22, 32], 'attached_command': 'r; bank io; m d000 d03f; bank ram'}, {'label': 'odd-readback', 'stages': {'before': 'odd-readback-consumer', 'copied': 'odd-readback-copied', 'latch': 'odd-readback-latch', 'before_start': 'odd-readback-before-start', 'started': 'odd-readback-started', 'selector': 'odd-readback-selector', 'cutoff': 'odd-readback-cutoff', 'restored': 'odd-readback-restored', 'completed': 'odd-readback-field-end'}, 'cursor_index': 1015, 'current_pair': [26, 40], 'next_index': 1016, 'next_pair': [26, 40], 'attached_command': 'r; bank io; m d000 d03f; bank ram'}]}
RECEIVED_RAW = None
ATTACHED_COMMANDS = ('r', 'r; bank io; m d000 d03f; bank ram')

PINS = {'research/verify_vice_live.py': 'f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a', 'research/vice_session_live.py': '4340d1b0394fa612f5e6a71edddcbc2daf947e59c4c3013ab3b850c886dc621c', 'research/eod/controller.py': '033bafb6ac6e97283175ac6713af0eef60cb7991b653ee1c98c47a1a4afa83c9', 'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a', 'build/research/the-hat/native-analysis/interrupt-framing-source.py': '0223c67fafd2a3e4ac72b0a6bc3c911655a88da2f4cc42041ed6e3089e464047', 'build/research/quondam/hardware-source/vice-3.10.tar.gz': '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1', 'build/research/frontier-2026/february-analysis/the-hat-original.zip': 'ab15a74ba10a71264ccad74cd1d3a394b8f442a2acd33fd363b671bf293b081f', 'build/research/the-hat/release/the-hat-7a825b1-b.d64': '1527038ebebca1a3d3d3379b91dd1a77dffb6d6d89a4dbfc32bf3f6908eb5b21', 'research/the-hat/upscroll_native.py': '3edd29533e90036c596949d030928ac36da76c7ac4dacb7af62b95420defdfbf', 'build/research/the-hat/disk-analysis/accepted-02/disk-proof.json': 'a23fa100137fe60f929af25b6596584089cd93cacd891fe02e7ebc85d47635a3', 'build/research/the-hat/disk-analysis/early-01/original-bootstrap.prg': '32189d1101a947c3ecc02ae3e9493756dbc063008582d09c62f939068f1049cd', 'build/research/the-hat/dali-analysis/accepted-03/dali-proof.json': '1687a5b2323ec86881b53b226a5361ac88c6408720498cfd34cf7032b3ad940e', 'build/research/the-hat/dali-analysis/accepted-03/b00-0f00.bin': '61a9573334039fbd8b812c5378c4eefb820f96cf52d570dd1b1b3aa7ed23bbf9', 'build/research/the-hat/dali-analysis/neighbor-probe-02/accepted-01/source-classification.json': '838ed0bd5534acce676b06528f4c311adbccc8f1fc62462d5b68abfe628dcb8f', 'build/research/the-hat/dali-analysis/neighbor-probe-02/accepted-01/b07.bin': '5f2a0a0b960dfdd1f8c31b5be9ef5e60fbe2db177a446db5eb51462e57b5d150', 'build/research/the-hat/dali-analysis/neighbor-probe-02/accepted-01/b08.bin': '5c8150c48068c62f8a77d8c97b18de33360dcb03046e0f5e9ffcb01ca6704ba6', 'build/research/the-hat/dali-analysis/neighbor-probe-02/accepted-01/b09.bin': '9d0f80b7bc33c981a7befe2274ac98f30bf00c77916702016588b5e028e9a578', 'build/research/the-hat/raster-source-analysis/accepted-02/raster-source-proof.json': '6c3e831d481b58ca3d297cd13d2f21a95256a1edeb806cc46c4b5ce60d8491cb', 'build/research/the-hat/raster-source-analysis/accepted-02/raster-read-anchors.json': 'caf8d7c8396cf34f83296f9e3b38b0def511311b87b4216d9a71da151efb44e9'}
EXPECTED = {'sys': (2061, 11336568), 'first-loaded': (3840, 14029108), 'b7-loaded': (8259, 124735855), 'b8-controller': (32768, 127840084), 'even-consumer': (33181, 145571401), 'even-copied': (33267, 145571523), 'even-latch': (33308, 145572956), 'even-before-start': (33383, 145573148), 'even-started': (33388, 145573154), 'even-selector': (34070, 145573193), 'even-cutoff': (33420, 145589834), 'even-restored': (33432, 145589869), 'even-field-end': (32840, 145591995), 'odd-consumer': (33181, 146416616), 'odd-copied': (33267, 146416738), 'odd-latch': (33308, 146418293), 'odd-before-start': (33383, 146418482), 'odd-started': (33388, 146418488), 'odd-selector': (34070, 146418527), 'odd-cutoff': (33420, 146435040), 'odd-restored': (33432, 146435075), 'odd-field-end': (32837, 146437201), 'even-readback-consumer': (33181, 147065462), 'even-readback-copied': (33267, 147065584), 'even-readback-latch': (33308, 147067380), 'even-readback-before-start': (33383, 147067571), 'even-readback-started': (33388, 147067577), 'even-readback-selector': (34070, 147067616), 'even-readback-cutoff': (33420, 147083688), 'even-readback-restored': (33432, 147083723), 'even-readback-field-end': (32840, 147085849), 'odd-readback-consumer': (33181, 147851316), 'odd-readback-copied': (33267, 147851438), 'odd-readback-latch': (33308, 147853808), 'odd-readback-before-start': (33383, 147854000), 'odd-readback-started': (33388, 147854006), 'odd-readback-selector': (34070, 147854045), 'odd-readback-cutoff': (33420, 147869930), 'odd-readback-restored': (33432, 147869965), 'odd-readback-field-end': (32840, 147872090)}


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


def retained_response(row):
    global RECEIVED_RAW
    if RECEIVED_RAW is None:RECEIVED_RAW=(CASE/'received.bin').read_bytes()
    raw=RECEIVED_RAW[row['received_first']:row['received_end']]
    assert raw.decode(errors='replace')==row['response']
    return raw


def response_reference(row):
    raw=retained_response(row)
    return dict(sequence=row['sequence'],id=row['id'],command=row['command'],received_first=row['received_first'],received_end=row['received_end'],response_bytes=len(raw),response_sha256=sha(raw),received_stream=str((CASE/'received.bin').relative_to(ROOT)),identity_basis='Original raw received bytes; event text is its UTF8 replacement decode')


def closed_inventory():
    assert PROFILE is not None and not CASE_SHA.startswith('PENDING')
    path=BASE/PROFILE['manifest_name'];assert sha(path.read_bytes())==PROFILE['manifest_sha256']
    manifest=json.loads(path.read_text())
    rows=[dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(CASE.iterdir()) if p.is_file()]
    assert rows==manifest['files'] and len(rows)==manifest['file_count']==PROFILE['file_count']
    assert sum(r['bytes'] for r in rows)==manifest['total_bytes']==PROFILE['total_bytes']
    assert sha(json.dumps(rows,sort_keys=True,separators=(',',':')).encode())==manifest['listing_sha256']==CASE_SHA
    with zipfile.ZipFile(ROOT/'build/research/frontier-2026/february-analysis/the-hat-original.zip') as archive:
        names=[name for name in archive.namelist() if Path(name).name==DISK.name]
        assert len(names)==1 and archive.read(names[0])==DISK.read_bytes()
    return dict(manifest=artifact(path),files=len(rows),bytes=sum(r['bytes'] for r in rows),canonical_listing_sha256=CASE_SHA,original_ZIP_member=names[0],all_B_disk_bytes_equal=True)


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


def interrupt_trace_context(row,wire):
    original=function_source('research/the-hat/raster_case.py','interrupt_framing')
    assert original.encode()==(BASE/'native-analysis/interrupt-framing-source.py').read_bytes()
    replacements=[
        ("text=row['response'];metadata=row['interrupt'];first=metadata['response_first']", "text=retained_response(row).decode('latin1');metadata=row['interrupt'];first=metadata['response_first']"),
        ("assert text.isascii() and metadata['register_response']==text[first:]", "assert metadata['register_response']==retained_response(row)[first:].decode(errors='replace')"),
        ("assert registers['pc']==int(match[1],16) and wire.PROMPT.search(frame.encode())", "assert wire.PROMPT.search(frame.encode())"),
        ('.encode()', ".encode('latin1')"),
        ('(?:exec|store)', '(?:exec|store|load)')]
    adapted=original
    for old,new in replacements:
        assert old in adapted,old
        adapted=adapted.replace(old,new)
    namespace=dict(globals());exec(compile(adapted,'<native03-raw-byte-final-interrupt-frame-and-monitor-dot>','exec'),namespace)
    frame=namespace['interrupt_framing'](row,wire)
    raw=retained_response(row);dot=re.match(rb'\(C:\$([0-9a-f]{4})\)',raw[frame['frame_response_first']:]);assert dot
    frame['monitor_dot_address']=int(dot[1],16)
    frame['monitor_dot_not_assumed_CPU_PC']=True
    frame['original_helper_sha256']=sha(original.encode());frame['adapted_helper_sha256']=sha(adapted.encode());frame['exact_raw_byte_adapter_replacements']=replacements
    return frame


def audit_wire():
    wire=load('hat_raster_wire','research/verify_vice_live.py')
    wire.BASE,wire.CASE_PINS=BASE,{'native-03':CASE_SHA}
    original=function_source('research/verify_vice_live.py','audit_session')
    old='assert session["startup_mode"] == "manual monitor load" and "-autostart" not in session["command"]'
    replacement=('assert session["startup_mode"] == "autostart"\n'
        '    assert session["program"] == '+repr(str(DISK))+'\n'
        '    for flag in ("-autostart", "-8"):\n'
        '        assert session["command"].count(flag) == 1\n'
        '        assert session["command"][session["command"].index(flag)+1] == '+repr(str(DISK)))
    assert original.count(old)==1;adapted=original.replace(old,replacement)
    interrupt_old='registers(interrupt["register_response"])';interrupt_replacement='hat_interrupt_registers(event)'
    assert adapted.count(interrupt_old)==1;adapted=adapted.replace(interrupt_old,interrupt_replacement)
    helper=function_source('research/the-hat/raster_case.py','interrupt_framing')
    assert helper.encode()==(BASE/'native-analysis/interrupt-framing-source.py').read_bytes()
    wire.hat_interrupt_registers=lambda row:interrupt_trace_context(row,wire)['registers']
    exec(compile(adapted,'<native03-original-B-and-final-interrupt-frame>','exec'),wire.__dict__)
    case=wire.audit_session('native-03');responses=case['responses'];count=PROFILE['command_count']
    assert not case['partial'] and not case['cancelled'] and sorted(responses)==list(range(1,count+1))
    assert Counter(r['status'] for r in responses.values())==PROFILE['status_counts']
    assert [n for n,r in responses.items() if r['status']=='interrupted']==PROFILE['interrupt_sequences']
    assert Counter(r['purpose'] for r in case['requests'])==dict(ordinary=count,**({'interrupt':len(PROFILE['interrupt_sequences'])} if PROFILE['interrupt_sequences'] else {}))
    assert sha(json.dumps([responses[n]['command'] for n in range(1,count+1)],separators=(',',':')).encode())==COMMANDS_SHA
    assert case['waits']==PROFILE['waits']
    assert all(responses[w['sequence']]['status'] in ('completed','interrupted') for w in case['waits'])
    assert not any(re.search(r'ERROR --|Syntax error|Unknown resource',r['response']) for r in responses.values())
    launch=case['session']['command'];assert '-pal' in launch and launch[launch.index('-speed')+1]=='100'
    assert '+warp' in launch and '+autostart-warp' in launch and '-drive8truedrive' in launch and launch[launch.index('-drive8type')+1]=='1541'
    frames={n:interrupt_trace_context(responses[n],wire) for n in PROFILE['interrupt_sequences']}
    def strict_or_final(text):
        candidates=[n for n in PROFILE['interrupt_sequences'] if text==responses[n]['interrupt']['register_response']]
        assert len(candidates)<=1
        return frames[candidates[0]]['registers'] if candidates else wire.registers(text)
    case['_strict_or_final_registers']=strict_or_final
    return wire,case,dict(original_function_sha256=sha(original.encode()),adapted_function_sha256=sha(adapted.encode()),exact_startup_replacement=replacement,exact_interrupt_old=interrupt_old,exact_interrupt_replacement=interrupt_replacement,final_interrupt_frame_helper_sha256=sha(helper.encode()),only_two_declared_auditor_replacements=True,ordinary_register_reader_unchanged=True,no_event_or_raw_byte_change=True,raw_response_identity='Original received bytes; Latin1 trace framing, original UTF8-replacement event decode checked unchanged',raw_interrupt_adapter_function_sha256=sha(function_source('research/the-hat/raster_case.py','interrupt_trace_context').encode()),interrupted_frames=frames)


def capture_pairs(reader, wire, case):
    helper = load('hat_upscroll_pairs', 'research/eod/controller.py')
    helper.CASE = CASE
    helper.DECLARED_INTERRUPTS = PROFILE["interrupt_sequences"]
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
                 "            assert wire.hat_interrupt_registers(responses[stop]) == regs\n"
                 "        else:\n" + ''.join('    ' + line for line in block.splitlines(keepends=True)))
    assert adapted.count(block) == 1
    adapted = adapted.replace(block, interrupt)
    exec(compile(adapted, '<actual-DDR-and-declared-native03-interruption>', 'exec'), helper.__dict__)
    memories, captures = helper.capture_pairs(reader, wire, case)
    assert len(captures) == len(EXPECTED) and {row['stem'] for row in captures} == set(EXPECTED)
    for row in captures:
        assert (row['registers']['pc'], row['registers']['clock']) == EXPECTED[row['stem']]
        rejected = row['stem'] in PROFILE['rejected_captures']
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
        if command.startswith(('break ', 'trace exec ', 'trace store ', 'trace load ')):
            match = re.search(r'^(BREAK|TRACE): ([0-9]+)  C:\$([0-9a-f]{4})(?:-\$([0-9a-f]{4}))?  \((Stop on exec|Trace exec|Trace store|Trace load)\)', row['response'])
            assert match, (sequence, row['response'])
            kind, number, first = match[1], int(match[2]), int(match[3], 16)
            last = int(match[4], 16) if match[4] else first
            assert number not in active
            generations[number] += 1
            operation = 'store' if match[5] == 'Trace store' else 'load' if match[5] == 'Trace load' else 'exec'
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
            match = re.fullmatch(r'command ([0-9]+) "(.+)"', command)
            assert match and int(match[1]) in active and match[2] in ATTACHED_COMMANDS
            assert row['response'].startswith(f'Setting checkpoint {match[1]} command to: {match[2]}')
            active[int(match[1])]['attached_r'] = response_reference(row)
            active[int(match[1])]['attached_command_text'] = match[2]
        elif command.startswith('delete '):
            number = int(command.split()[1]); assert number in active
            active[number]['deleted_sequence'] = sequence
            del active[number]
        elif command == 'x':
            if row['status'] == 'interrupted':
                assert sequence in PROFILE['interrupt_sequences']
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
            assert capture['stem'] in PROFILE['rejected_captures']
        else:
            assert stop['PC'] == capture['registers']['pc']
            assert stop['beam'] == [capture['registers']['line'], capture['registers']['cycle']]
            stop['evaluated_predicates'] = evaluate_condition(stop['checkpoint']['condition'],
                capture['registers'], (CASE / (capture['stem'] + '-ram.bin')).read_bytes())
            assert all(predicate['equal'] for predicate in stop['evaluated_predicates'])
        bindings.append(dict(stem=capture['stem'], **stop))
    return dict(setups=setups,capture_stops=bindings,all_checkpoint_generations_deleted_before_close=True)


def wire_registers_final(case, sequence):
    return case['_strict_or_final_registers'](case['responses'][sequence]['interrupt']['register_response'])


def evaluate_condition(condition,registers,memory):
    result=[]
    if not condition:return result
    for raw in re.split(r'\s*&&\s*',condition):
        term=raw.strip()
        if term.startswith('(') and term.endswith(')'):term=term[1:-1].strip()
        match=re.fullmatch(r'(@ram:\$[0-9a-f]+|RL|CY|A|X|Y|SP|PC)\s*(==|>=|<=)\s*(\$?[0-9a-f]+)',term);assert match,('Unsupported condition',raw)
        name,op,value=match[1],match[2],int(match[3].lstrip('$'),16)
        if name.startswith('@ram:'):
            address=int(name.split('$')[1],16);assert 0<=address<65536 and 0<=value<256;actual=memory[address];kind='RAM'
        else:address=None;actual=registers[{'RL':'line','CY':'cycle'}.get(name,name.lower())];kind='register_or_beam'
        passed={'==':actual==value,'>=':actual>=value,'<=':actual<=value}[op]
        result.append(dict(expression=raw,kind=kind,address=address,actual=actual,expected=value,operation=op,equal=passed))
    return result


def source_bindings(memories,captures):
    states={r['stem']:r['registers'] for r in captures};original=[]
    bootpath=BASE/'disk-analysis/early-01/original-bootstrap.prg';boot=bootpath.read_bytes()
    assert len(boot)==2710 and boot[:2]==bytes.fromhex('0108') and memories['sys'][0x801:0x1295]==boot[2:]
    assert re.fullmatch(rb'\x9e\s*2061',boot[6:boot.index(0,6)])
    original.append(dict(capture='sys',source=artifact(bootpath),destination=0x801,bytes=2708,all_bytes_equal=True))
    b0path=BASE/'dali-analysis/accepted-03/b00-0f00.bin';b0=b0path.read_bytes();assert len(b0)==263 and memories['first-loaded'][0xf00:0xf00+len(b0)]==b0
    original.append(dict(capture='first-loaded',source=artifact(b0path),destination=0xf00,bytes=len(b0),all_bytes_equal=True))
    proof=json.loads((SOURCE/'source-classification.json').read_text());raw_source={};guards=[]
    for name,destination,size in [('b07',0x2000,5065),('b08',0x4000,36864),('b09',0xe000,6144)]:
        row=next(r for r in proof['new_streams'] if r['name']==name);path=SOURCE/row['output']['name'];raw=path.read_bytes()
        assert row['destination']==destination and row['bytes']==len(raw)==size and row['end_exclusive']==destination+size and row['unknown_bytes']==0
        assert sha(raw)==row['output']['sha256'] and artifact(ROOT/row['raw']['path'])==row['raw'];raw_source[name]=(destination,raw)
        for stem in PROFILE['whole_loaded_stems']:
            offset,length=(0x3a,17) if name=='b07' else (0,size)
            assert memories[stem][destination+offset:destination+offset+length]==raw[offset:offset+length]
            original.append(dict(capture=stem,source=artifact(path),source_offset=offset,destination=destination+offset,bytes=length,all_bytes_equal=True))
    b8,b9=raw_source['b08'][1],raw_source['b09'][1]
    for first,end in [(0x819d,0x81de),(0x821c,0x8234),(0x8267,0x826c),(0x828c,0x8298),(0x8516,0x8520)]:
        expected=b8[first-0x4000:end-0x4000]
        for stem in PROFILE['raster_stems']:
            assert memories[stem][first:end]==expected,(stem,hex(first))
        guards.append(dict(source=artifact(SOURCE/'b08.bin'),source_first=first-0x4000,RAM_first=first,end_exclusive=end,hex=expected.hex(),captures=PROFILE['raster_stems'],all_bytes_equal=True))
    motions=[]
    for field in PROFILE['fields']:
        before,copied,latch=[field['stages'][name] for name in ('before','copied','latch')]
        index=field['cursor_index'];nxt=field['next_index'];expected=[b9[0x1ae+index],b9[0x97e+index]];nextpair=[b9[0x1ae+nxt],b9[0x97e+nxt]]
        assert expected==field['current_pair'] and nextpair==field['next_pair']
        for stem in (before,copied):
            m=memories[stem];assert int.from_bytes(m[2:4],'little')==0xe1ae+index and int.from_bytes(m[4:6],'little')==0xe97e+index
            assert list(m[0x817d:0x817f])==expected
        m=memories[latch];assert int.from_bytes(m[2:4],'little')==0xe1ae+nxt and int.from_bytes(m[4:6],'little')==0xe97e+nxt and list(m[0x817d:0x817f])==nextpair
        assert states[before]['pc']==0x819d and states[copied]['pc']==0x81f3 and states[latch]['pc']==0x821c
        motions.append(dict(before=before,after_current_copy=copied,after_next_motion=latch,current_cursor=index,current_source_addresses=[0xe1ae+index,0xe97e+index],current_pair=expected,next_cursor=nxt,next_pair=nextpair,source=artifact(SOURCE/'b09.bin'),current_consumer_precedes_next_coroutine_state=True))
    return dict(original_loaded_ranges=original,full_B8_B9_bytes_per_capture=43008,whole_range_captures=PROFILE['whole_loaded_stems'],code_guards=guards,motion_generations=motions,raw_source=raw_source)


def machine_context(reader,memories,captures,sources):
    snapshots={r['stem']:reader.read_snapshot(CASE/(r['stem']+'.vsf')) for r in captures}
    states={r['stem']:r['registers'] for r in captures};fields=[];b8=sources['raw_source']['b08'][1]
    for field in PROFILE['fields']:
        stages=field['stages'];observed={}
        for role,stem in stages.items():
            snapshot=snapshots[stem];observed[role]=dict(stem=stem,registers=states[stem],CIA1=snapshot['cia']['CIA1'],CIA2=snapshot['cia']['CIA2'],VIC=snapshot['vicii'],pointers43F8=list(memories[stem][0x43f8:0x4400]),pointers47F8=list(memories[stem][0x47f8:0x4800]),motion_pair=list(memories[stem][0x817d:0x817f]),cursor_bytes=list(memories[stem][2:6]))
        copied=observed['copied'];selector=observed['selector'];cutoff=observed['cutoff'];restored=observed['restored'];y=field['current_pair'][0]
        assert copied['VIC']['regs'][1:16:2]==[y]*8
        assert copied['pointers43F8']==list(range(field['current_pair'][1]+0x20,field['current_pair'][1]+0x28))
        x=y-2;latch=b8[0x42cc+x]|b8[0x43cc+x]<<8;assert latch==0x440f-63*x
        assert observed['before_start']['CIA1']['timer_b_latch']==observed['started']['CIA1']['timer_b_latch']==latch
        saved=memories[stages['selector']][0x828b];sp=states[stages['cutoff']]['sp'];m=memories[stages['cutoff']]
        pc=m[0x100+((sp+2)&255)]|m[0x100+((sp+3)&255)]<<8
        assert sp==0x56 and saved==states[stages['restored']]['sp']==0x59
        assert memories[stages['cutoff']]==memories[stages['restored']]
        assert states[stages['restored']]['a']==0x83
        assert cutoff['CIA1']['icr_mask']==2 and cutoff['CIA1']['icr_pending']&0x82==0x82 and cutoff['CIA1']['irq_enabled']==1
        assert restored['CIA1']['icr_pending']==restored['CIA1']['irq_enabled']==0
        for stage in observed.values():
            cia2=stage['CIA2'];pins=(cia2['pra']&cia2['ddra'])|((~cia2['ddra'])&255);bank=((~pins)&3)*0x4000
            assert bank==0x4000
            stage['effective_VIC_bank']=bank
        fields.append(dict(label=field['label'],stages=observed,current_pair=field['current_pair'],next_pair=field['next_pair'],timer_source_index=x,timer_source_latch=latch,stacked_interrupted_PC=pc,cutoff_clock=states[stages['cutoff']]['clock'],cutoff_SP=sp,restored_SP=saved,all65536_RAM_equal_across_handler_interval=True,source_IRQ_mechanism='CIA1 TimerB; guarded source handler reads DC0D and restores saved SP',timer_deadline_or_pixel_model_claimed=False))
    return snapshots,dict(fields=fields,complete_renderbuffer_interpretation_delegated=True,current_and_next_motion_generations_distinct=True,no_full_pixel_FPS_or_physical_hardware_claim=True)


def visible_io_readback(segment,absolute_first):
    rows=list(re.finditer(r'^>C:([0-9a-f]{4})[ \t]+((?:[0-9a-f]{2}[ \t]+){15}[0-9a-f]{2})[^\n]*\n',segment,re.M|re.I))
    assert len(rows)==4 and segment.count('>C:')==4
    values=[];references=[]
    for index,row in enumerate(rows):
        assert int(row[1],16)==0xd000+16*index
        raw=bytes.fromhex(row[2]);assert len(raw)==16;values.extend(raw)
        block=row[0].encode('latin1');references.append(dict(first_address=int(row[1],16),received_first=absolute_first+row.start(),received_end=absolute_first+row.end(),bytes=len(block),sha256=sha(block)))
    assert len(values)==64
    return dict(first=0xd000,end_exclusive=0xd040,visible_bytes=values,raw_rows=references,scope='Side-effect-free bank-io visible readback after this hook; unused/read-only bits are CPU-visible readback, not an observation of all stored raw bits. Oracle only, excluded from external read inputs.',bank_ram_restored_by_exact_attached_command=True)


def trace_events(case, wire, points, memories, sources, captures):
    """Check all exec/store/load hooks; compact only explicitly pinned windows."""
    setups = [row for row in points['setups'] if row['kind'] == 'TRACE']
    header = re.compile(r'#([0-9]+) \(Trace\s+(exec|store|load) ([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\n')
    instruction = re.compile(r'^\.C:([0-9a-f]{4})\s+([0-9A-F]{2}(?: [0-9A-F]{2}){0,2})\s+(.+?)\s+- A:([0-9A-F]{2}) X:([0-9A-F]{2}) Y:([0-9A-F]{2}) SP:([0-9a-f]{2}) ([NV\-BDIZC.]{8})\s+(\d+)\n', re.M)
    states = {row['stem']: row['registers'] for row in captures}
    register_keys = ('pc', 'a', 'x', 'y', 'sp', 'port00', 'port01', 'flags', 'line', 'cycle', 'clock')
    records, windows, totals = [], [], Counter()
    read_records = []
    for sequence, row in sorted(case['responses'].items()):
        if row['command'] != 'x':
            continue
        raw_response=retained_response(row);text=raw_response.decode('latin1')
        headers = list(header.finditer(text)); assert text.count('(Trace') == len(headers)
        if not headers:
            continue
        compact = sequence in PROFILE['compact_sequences']
        late = 0
        if row['status'] == 'interrupted':
            terminal = interrupt_trace_context(row, wire)['frame_response_first']
            late = sum(match.start() >= row['interrupt']['response_first'] for match in headers)
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
                and setup['setup']['sequence'] < sequence < setup.get('deleted_sequence', PROFILE['command_count']+1)]
            assert len(candidates) == 1, (sequence, number)
            setup = candidates[0]
            assert setup['operation'] == operation and setup['first'] <= address <= setup['last']
            assert setup['attached_r']['sequence'] < sequence
            end = headers[index + 1].start() if index + 1 < len(headers) else terminal
            segment = text[match.end():end]
            ins = instruction.search(segment)
            assert ins and segment.count('Executing: '+setup['attached_command_text']) == 1
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
            if reference.startswith('not_equal') and 'b8-init' in states and states['b8-init']['clock'] <= regs['clock'] and memories['b8-init'][pc:pc + len(raw)] == raw:
                reference = 'earlier_natural_B8_initialized_RAM_bytes'
            record = dict(sequence=sequence, checkpoint=number, checkpoint_generation=setup['generation'],
                operation=operation, monitored_address=address,
                instruction_PC=pc, instruction_hex=raw.hex(), instruction=ins[3], registers=regs,
                setup_sequence=setup['setup']['sequence'], attached_r_sequence=setup['attached_r']['sequence'],
                received_first=row['received_first'] + match.start(), received_end=row['received_first'] + end,
                raw_block_bytes=end - match.start(), raw_block_sha256=sha(raw_response[match.start():end]),
                instruction_byte_reference=reference,attached_command=setup['attached_command_text'])
            if setup['attached_command_text']!= 'r':
                record['visible_IO_readback']=visible_io_readback(segment,row['received_first']+match.end())
            else:
                assert '>C:' not in segment
            canonical = [number, setup['generation'], operation, address, pc, raw.hex(),
                         [regs[key] for key in register_keys], record['received_first'], record['received_end'], reference]
            context_digest.update(json.dumps(canonical, separators=(',', ':')).encode() + b'\n')
            framing_digest.update(json.dumps([record['received_first'], record['received_end'], record['raw_block_sha256']], separators=(',', ':')).encode() + b'\n')
            if operation == 'load' and address in (0xd012,0xd112,0xdc04):
                read_records.append(record)
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
            late_hits_after_interrupt_request=late,
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
    assert sum(row['trace_hits'] for row in windows)==sum(len(re.findall(rb'#\d+ \(Trace\s+(?:exec|store|load) ',retained_response(row))) for row in case['responses'].values())
    return dict(windows=windows,short_hits=records,read_records=read_records,operation_totals=dict(totals),all_raw_trace_headers_parsed=True,
        source_and_snapshot_contexts_retained=True,physical_bus_write_counts_inferred=False,
        digest_schema='CanonicalJSONline:[checkpoint,generation,operation,address,instructionPC,hex,[PC,A,X,Y,SP,DDR,read01,flags,line,cycle,clock],absoluteFirst,absoluteEnd,codeReference]. FramingJSONline:[absoluteFirst,absoluteEnd,rawBlockSHA256].',
        scope='Every exec/store/load hook and attached-r context remains in original order, including late interrupt-drain records. Store/load hooks expose observed post-step context; IRQ dispatch can change PC before the hook is reported. No PC=instructionPC+length, physical RMW bus-write, timer-deadline, executed-source-model or pixel claim is inferred here.')


def primary_schema():
    archive_path = ROOT / 'build/research/quondam/hardware-source/vice-3.10.tar.gz'
    checks = {
        'vice-3.10/src/monitor/monitor.c': ['default_radix = e_hexadecimal;'],
        'vice-3.10/src/monitor/mon_lex.l': ['CMD_SEP'],
        'vice-3.10/src/monitor/mon_parse.y': ['if (default_radix == e_hexadecimal)', 'end_cmd'],
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
    grammar = [r'r', r'sidefx off', r'bank ram', r'bank', r'r; bank io; m d000 d03f; bank ram', r'warp(?: on| off)?', r'resourceget "(?:Speed|VICIIBorderMode|VICIIModel)"', r'dummy',
        r'break (?:exec )?\$?[0-9a-f]{4}(?: \$?[0-9a-f]{4})?(?: if .+)?',
        r'condition [0-9]+ if .+', r'trace (?:store|load|exec) [0-9a-f]{4}(?: [0-9a-f]{4})?',
        r'command [0-9]+ "(?:r|r; bank io; m d000 d03f; bank ram)"', r'delete [0-9]+', r'x', r'help [a-z]+', r'[dm] [0-9a-f]{4} [0-9a-f]{4}',
        r'bsave "' + re.escape(str(CASE)) + r'/[a-z0-9-]+-ram\.bin" 0 0000 ffff',
        r'dump "' + re.escape(str(CASE)) + r'/[a-z0-9-]+\.vsf"',
        r'screenshot "' + re.escape(str(CASE)) + r'/[a-z0-9-]+\.png" 2']
    for row in case['responses'].values():
        assert any(re.fullmatch(pattern, row['command']) for pattern in grammar), row['command']
    return dict(all_ordinary_commands_classified=True, RAM_PC_register_patch_or_restore_commands=0,
        disk_or_keyboard_or_joystick_commands=0, actual_warp_queries=[response_reference(row)
            for row in case['responses'].values() if row['command'] in ('warp', 'resourceget "Speed"', 'resourceget "VICIIBorderMode"', 'resourceget "VICIIModel"', 'dummy')],
        scope='Observation/checkpoint/trace/export commands plus explicit warp controls only; original sideB was attached at startup.')


def watched_lifetimes(case,captures,points):
    by_stem={row['stem']:row for row in captures}
    required=[('store',0xd000,0xd3ff),('store',0xdc00,0xdc0f),('store',0xdd00,0xdd03),('store',0x43f8,0x43ff),('store',0x47f8,0x47ff),('load',0xd012,0xd012),('load',0xd112,0xd112),('load',0xdc04,0xdc04)]
    fields=[]
    for field in PROFILE['fields']:
        stages=field['stages'];before=by_stem[stages['before']];first=by_stem[stages['copied']];end=by_stem[stages['completed']]
        assert (end['registers']['line'])==0
        watches=[]
        for operation,low,high in required:
            matches=[row for row in points['setups'] if row['kind']=='TRACE' and row['operation']==operation and row['first']==low and row['last']==high and row['setup']['sequence']<first['stop_sequence']<row.get('deleted_sequence',PROFILE['command_count']+1)]
            assert len(matches)==1,(field['label'],operation,hex(low),hex(high))
            watch=matches[0];assert watch['attached_r']['sequence']<first['stop_sequence']
            assert watch['attached_command_text']==field['attached_command']
            assert watch.get('deleted_sequence',0)>end['snapshot_sequence']
            watches.append(watch)
        fields.append(dict(label=field['label'],before_consumer=before['stem'],first_continuation_stop=first['stop_sequence'],completed_boundary=end['stem'],completed_stop_sequence=end['stop_sequence'],start_clock=before['registers']['clock'],end_clock=end['registers']['clock'],elapsed_cycles=end['registers']['clock']-before['registers']['clock'],watches=watches,attached_command=field['attached_command'],visible_IO_oracles_expected=field['attached_command']!= 'r',all_required_watches_active_before_first_consumer_store_and_through_completed_pair=True,full312_current_framebuffer_rows_not_implied=True))
    return dict(fields=fields,required_ranges=[dict(operation=op,first=lo,last=hi) for op,lo,hi in required])


def entry_generations(memories,captures,sources):
    by_stem={row['stem']:row for row in captures};reference=sources['raw_source']['b08'][1];b9=sources['raw_source']['b09'][1]
    proof=json.loads((BASE/'raster-source-analysis/accepted-02/raster-source-proof.json').read_text());domain=proof['source_range'];first,end=domain['first'],domain['end_exclusive']
    expected=reference[first-0x4000:end-0x4000];assert len(expected)==17060 and sha(expected)==domain['sha256']
    fields=[]
    for field in PROFILE['fields']:
        stem=field['stages']['selector'];memory=memories[stem];state=by_stem[stem]['registers'];assert state['flags']&8==0
        actual=memory[first:end];differences=[dict(address=first+i,original=a,actual=b) for i,(a,b) in enumerate(zip(expected,actual)) if a!=b]
        tables=[]
        for page in range(0xf200,0xf800,0x100):
            raw=memory[page:page+256];original=b9[page-0xe000:page-0xe000+256]
            tables.append(dict(first=page,end_exclusive=page+256,bytes=len(raw),sha256=sha(raw),original_sha256=sha(original),original_equal=raw==original,all_differences=[dict(address=page+i,original=a,actual=b) for i,(a,b) in enumerate(zip(original,raw)) if a!=b]))
        helpers=memory[0x19f:0x1ac];early=memories['first-loaded'][0x19f:0x1ac]
        fields.append(dict(label=field['label'],selector_capture=stem,selector_RAM=by_stem[stem]['ram'],decimal_flag_clear=True,source_code_range=dict(first=first,end_exclusive=end,bytes=len(expected),independent_original_sha256=sha(expected),actual_sha256=sha(actual),all_observed_differences=differences,no_difference_silently_normalized=True),actual_table_generations=tables,delay_helper_generation=dict(first=0x19f,end_exclusive=0x1ac,bytes=len(helpers),hex=helpers.hex(),sha256=sha(helpers),earlier_natural_first_loaded_equal=helpers==early,earlier_natural_hex=early.hex(),scope='Actual helper context. Equality to earlier execution is not independent static SFX decoding; the typed consumer must prove its required value/carry semantics.'),initial_tables_and_VIC_are_declared_inputs_not_expected_store_oracles=True))
    return dict(fields=fields,scope='Selector-time source/helper/table generation identities and all code differences are explicit. Mutable dispatch operands are not broadly normalized or adopted as predicted control-flow targets.')


def external_read_inputs(traces,captures):
    path=BASE/'raster-source-analysis/accepted-02/raster-read-anchors.json'
    anchors=json.loads(path.read_text())['points'];assert len(anchors)==106
    by_pc={row['first']:row for row in anchors};assert len(by_pc)==106
    by_stem={row['stem']:row for row in captures};fields=[]
    for field in PROFILE['fields']:
        stages=field['stages'];selector=by_stem[stages['selector']];cutoff=by_stem[stages['cutoff']];completed=by_stem[stages['completed']]
        low,high=selector['registers']['clock'],cutoff['registers']['clock'];variant=(field['current_pair'][1]>>3)&1;samples=[];calibration=[]
        for hit in traces['read_records']:
            if hit['sequence']>completed['stop_sequence']:continue
            if hit['instruction_PC'] in by_pc and low<=hit['registers']['clock']<=high:
                anchor=by_pc[hit['instruction_PC']];assert anchor['variant']==variant and hit['monitored_address']==anchor['source_address']
                assert hit['instruction_hex']==bytes([0xac,anchor['source_address']&255,anchor['source_address']>>8]).hex()
                assert hit['instruction_byte_reference']=='independent_original_b08_bytes'
                samples.append(dict(instruction_PC=hit['instruction_PC'],postPC=hit['registers']['pc'],loaded_Y=hit['registers']['y'],clock=hit['registers']['clock'],beam=[hit['registers']['line'],hit['registers']['cycle']],source_fallthrough_PC=anchor['post_pc'],block=anchor['block'],sample=anchor['sample'],variant=variant,read_address=hit['monitored_address'],rawref={key:hit[key] for key in ('sequence','received_first','received_end','raw_block_bytes','raw_block_sha256')}))
            if hit['monitored_address']==0xdc04 and by_stem[stages['before']]['registers']['clock']<=hit['registers']['clock']<=low:
                calibration.append({key:hit[key] for key in ('sequence','instruction_PC','instruction_hex','registers','received_first','received_end','raw_block_bytes','raw_block_sha256')})
        assert samples and all(a['clock']<=b['clock'] for a,b in zip(samples,samples[1:]))
        fields.append(dict(label=field['label'],variant=variant,selector_clock=low,cutoff_clock=high,raster_read_samples=samples,timer_A_calibration_load_contexts=calibration,cutoff_capture=stages['cutoff'],record_selection_by_hook_clock_not_only_wire_response_sequence=True,read_context_scope='External observed post-LDY Y at independent source anchors; actual postPC is retained even when IRQ dispatch differs from source fallthrough. No expected stores, write counts, or native target memory seed this input stream.'))
    return dict(source_anchor_artifact=artifact(path),fields=fields,input_contract='Observed raster reads and calibration contexts only. Expected store hooks remain in the separate trace-hits oracle; DC04 SBC post-register context is not relabelled an independently observed timer-read byte.')


def actual_queries(case,snapshots):
    result=[];models=[]
    for row in case['responses'].values():
        command=row['command']
        if command=='warp':
            match=re.search(r'Warp mode is (on|off)\.',row['response']);assert match
            result.append(dict(**response_reference(row),kind='warp',observed=match[1]))
        elif command.startswith('resourceget '):
            name=re.fullmatch(r'resourceget "(Speed|VICIIBorderMode|VICIIModel)"',command)[1]
            match=re.search(r'\b'+name+r'\s*=\s*([0-9]+)',row['response']);assert match
            value=int(match[1]);result.append(dict(**response_reference(row),kind=name,observed=value))
            if name=='Speed':assert value==100
            if name=='VICIIBorderMode':assert value==0
            if name=='VICIIModel':models.append(value)
        elif command=='dummy':
            assert row['response'].startswith('Checkpoints will not trigger on dummy accesses.\n')
            result.append(dict(**response_reference(row),kind='dummy_accesses',observed='off'))
    assert models and all(snapshot['vicii']['model']==models[0] for snapshot in snapshots.values()) and set(models)=={models[0]}
    assert all(any(row['kind']==kind for row in result) for kind in ('warp','Speed','VICIIBorderMode','VICIIModel','dummy_accesses'))
    return dict(queries=result,snapshot_VIC_model_enum=models[0],query_snapshot_model_equal=True,interpretation='VIC model is the actual resource/snapshot enum; no6569 subtype is assumed. Query instants alone establish resource values; dummy tracing coverage is not changed. Normal viewport row lifetime requires the separate draw-tail consumer.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    out=parser.parse_args().output.resolve();out.relative_to((BASE/'raster-case-analysis').resolve())
    assert PROFILE is not None and EXPECTED is not None and not CASE_SHA.startswith('PENDING'),'Owner-closed native03 profile required; this is not live acceptance'
    out.mkdir(parents=True,exist_ok=False);checked=Path(__file__).read_bytes();(out/'raster_case.checked.py').write_bytes(checked)
    try:
        for name,pin in PINS.items():assert sha((ROOT/name).read_bytes())==pin,name
        inventory=closed_inventory();wire,case,adapter=audit_wire();reader=load('hat_raster_snapshot','research/quondam/snapshot_state.py')
        memories,captures,pair_adapter=capture_pairs(reader,wire,case);sources=source_bindings(memories,captures)
        points=checkpoints(case,captures);lifetimes=watched_lifetimes(case,captures,points);commands=command_audit(case);snapshots,context=machine_context(reader,memories,captures,sources)
        traces=trace_events(case,wire,points,memories,sources,captures);reads=external_read_inputs(traces,captures);traces.pop('read_records');queries=actual_queries(case,snapshots);generations=entry_generations(memories,captures,sources);sources.pop('raw_source')
        raw_hits=(json.dumps(traces.pop('short_hits'),indent=2)+'\n').encode();raw_snapshots=(json.dumps(snapshots,indent=2)+'\n').encode();raw_reads=(json.dumps(reads,indent=2)+'\n').encode()
        outputs=[dict(name='raster_case.checked.py',bytes=len(checked),sha256=sha(checked)),dict(name='trace-hits.json',bytes=len(raw_hits),sha256=sha(raw_hits)),dict(name='capture-machine-context.json',bytes=len(raw_snapshots),sha256=sha(raw_snapshots)),dict(name='raster-read-inputs.json',bytes=len(raw_reads),sha256=sha(raw_reads))]
        proof=dict(pass_=True,scope='Closed fresh original-B native03 raster-window custody with complete watched VIC/CIA/pointer-table store and selected raster/calibration load hooks. Independent executed-write and draw-tail/pixel interpretation are separate consumers.',producer=artifact(Path(__file__)),inputs=[artifact(ROOT/p) for p in PINS],inventory=inventory,wire=wire.summary(case),wire_adapter=adapter,pair_adapter=pair_adapter,captures=captures,checkpoint_bindings=points,watched_lifetimes=lifetimes,source_bindings=sources,bounded_machine_context=context,entry_generations=generations,monitor_traces=traces,primary_schema=primary_schema(),command_audit=commands,actual_mode_queries=queries,external_read_input_output=outputs[-1],store_hook_oracle_output=dict(**outputs[1],selection="operation==store; hook contexts only, no physical-RMW bus-write claim"),waiting_notices=case['waits'],outputs=outputs,limits=['All original wire/events/waits, complete suffixes and all exec/store/load hooks remain. A read-only interrupt is not a natural phase stop.','Current copied VIC Y/pointers and subsequently updated B9 motion state remain separate source generations.','Every full RAM/VSF pair has identical physical RAM, CPU/flags/clock/ports and beam; runtime snapshots never seed an independent source decoder.','Source timer configuration, acknowledged CIA state and restored SP are bounded custody context. Independent timer deadlines, full executed write sequence and VIC draw-tail interpretation belong to separate new consumers.','No physical RMW bus-write, complete pixels, full animation/FPS, optimization, hardware-portability or product claim follows from this custody proof.','The passive producer starts no native process, emulator, socket, CPU interpreter, subprocess, build or downloaded host program.'])
        raw=(json.dumps(proof,indent=2)+'\n').encode();(out/'trace-hits.json').write_bytes(raw_hits);(out/'capture-machine-context.json').write_bytes(raw_snapshots);(out/'raster-read-inputs.json').write_bytes(raw_reads);(out/'raster-case-proof.json').write_bytes(raw)
        print(json.dumps(dict(pass_=True,pairs=len(captures),receipt_bytes=len(raw),receipt_sha256=sha(raw))))
    except Exception as error:
        (out/'failure.json').write_text(json.dumps(dict(pass_=False,stage='passive-candidate',error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc(),producer=artifact(Path(__file__)),no_native_or_CPU_execution=True),indent=2)+'\n');raise


if __name__ == '__main__':
    main()
