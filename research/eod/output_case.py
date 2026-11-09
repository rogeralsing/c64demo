#!/usr/bin/env python3
"""Passively accept the closed original EOD output/display/multi-pose case."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'build/research/eod'
CASE = BASE/'native-04'
DISK = BASE/'release/EdgeOfDisgrace_1a.d64'
EXTRACT = BASE/'file-analysis/accepted-03'
# Only the native owner may close/pin a case. None of its live file contents
# are acceptance authority while these constants remain pending.
CASE_SHA = 'c52bb838d493b5d6261b1b55f931df74b358136748ceb9f9de201b8ea499540c'
MANIFEST_SHA = '68e8bd5cc27781048f9e80655e3cfa9b3c946ac78ea0b58bae3ab4170ecdfb0e'
COMMANDS_SHA = '485b5a0d26109169bfb294552d56daf507aba714fdbbc059d7d5291531cbdf71'
FILE_COUNT, TOTAL_BYTES, COMMAND_COUNT = 80, 9764629, 270
EXPECTED_STATES = {
    'sys': (0x080d, 7040755),
    'after52': (0x0709, 418907659),
    'baseline-begin': (0x546a, 469223429),
    'baseline-body': (0x17db, 469281647),
    'baseline-prefix-before': (0x1a73, 469299180),
    'baseline-filled': (0x1750, 469314275),
    'baseline-cleared': (0x1753, 469321627),
    'baseline-next-frame': (0x546a, 469321683),
    'display-setup': (0x16bb, 469329631),
    'display-mid': (0x5cdb, 469334533),
    'display-complete': (0x5ddc, 469340208),
    'p110-begin': (0x546a, 470049369),
    'p110-body': (0x17db, 470090682),
    'p110-prefix-before': (0x1a73, 470105076),
    'p110-filled': (0x1750, 470120211),
    'p110-cleared': (0x1753, 470127563),
    'p096-begin': (0x546a, 471306999),
    'p096-body': (0x17db, 471368861),
    'p096-prefix-before': (0x1a73, 471382716),
    'p096-filled': (0x1750, 471397996),
    'p096-cleared': (0x1753, 471405305),
    'p072-begin': (0x546a, 473508691),
    'p072-body': (0x17db, 473551084),
    'p072-prefix-before': (0x1a73, 473564532),
    'p072-filled': (0x1750, 473579718),
    'p072-cleared': (0x1753, 473587069),
    'p024-begin': (0x546a, 477341379),
    'p024-body': (0x17db, 477358183),
    'p024-prefix-before': (0x1a73, 477377799),
    'p024-filled': (0x1750, 477393140),
    'p024-cleared': (0x1753, 477400449),
    'p206-begin': (0x546a, 479896685),
    'p206-body': (0x17db, 479954975),
    'p206-prefix-before': (0x1a73, 479972391),
    'p206-filled': (0x1750, 479987769),
    'p206-cleared': (0x1753, 479995079),
}
PINS = {
    'research/eod/controller.py': '033bafb6ac6e97283175ac6713af0eef60cb7991b653ee1c98c47a1a4afa83c9',
    'research/eod/frame_case.py': 'dccc4527a0a12f4df9f190dfcbd504a9b20c2747611e54fc20a404e062b886de',
    'research/eod/native_boot.py': 'f1c0c0eaa4be5380bec55b84b34461b43b0065689a0ab94342c411dffb53bb55',
    'research/verify_vice_live.py': 'f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a',
    'research/vice_session_live.py': '4340d1b0394fa612f5e6a71edddcbc2daf947e59c4c3013ab3b850c886dc621c',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'build/research/eod/release/EdgeOfDisgrace_1a.d64': '0624697997c57209929fc36ff7121ec7c61760a88576edbf0768d63e77d28956',
    'build/research/eod/file-analysis/accepted-03/file-proof.json': 'fb8e819f854fd500acb34ea023508a9966f95914f38e1c6de0db77e3f2381db9',
    'build/research/eod/file-analysis/accepted-03/EdgeOfDisgrace_1a/trackmo-051.decoded.prg': 'e4899712681147b233a960d675aab369feebac4ba149073f1051d45f78b5312c',
    'build/research/eod/file-analysis/accepted-03/EdgeOfDisgrace_1a/trackmo-052.decoded.prg': '3adc5e1b6990cf41b3d93954de9d92bd3da62b4b562fc636cbd827cf94d67c04',
    'build/research/quondam/hardware-source/vice-3.10.tar.gz': '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1',
}
TARGETS = (('baseline', 1, 120), ('p110', 1, 110), ('p096', 1, 96),
           ('p072', 1, 72), ('p024', 1, 24), ('p206', 2, 6))
STAGES = {'begin': 0x546a, 'body': 0x17db, 'prefix-before': 0x1a73,
          'filled': 0x1750, 'cleared': 0x1753}
TRACE_RANGES = ((0xd000, 0xd02e), (0xdd00, 0xdd03), (0x6c00, 0x6fff),
                (0x7000, 0x77ff), (0xd800, 0xdbff))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT/relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def response_reference(row):
    raw = row['response'].encode()
    return dict(sequence=row['sequence'], id=row['id'], command=row['command'],
        received_first=row['received_first'], received_end=row['received_end'],
        response_bytes=len(raw), response_sha256=sha(raw),
        received_stream=str((CASE/'received.bin').relative_to(ROOT)))


def audit_wire():
    assert all(not value.startswith('PENDING') for value in
               (CASE_SHA, MANIFEST_SHA, COMMANDS_SHA)), 'Only accept an owner-closed, pinned case'
    assert FILE_COUNT and TOTAL_BYTES and COMMAND_COUNT and EXPECTED_STATES
    assert sha((BASE/'native-04-files.json').read_bytes()) == MANIFEST_SHA
    wire = load('eod_output_wire', 'research/verify_vice_live.py')
    wire.BASE, wire.CASE_PINS = BASE, {'native-04': CASE_SHA}
    source = (ROOT/'research/verify_vice_live.py').read_text()
    node = next(n for n in ast.parse(source).body
                if isinstance(n, ast.FunctionDef) and n.name == 'audit_session')
    original = ast.get_source_segment(source, node)+'\n'
    old = 'assert session["startup_mode"] == "manual monitor load" and "-autostart" not in session["command"]'
    replacement = ('assert session["startup_mode"] == "autostart"\n'
        '    assert session["program"] == '+repr(str(DISK))+'\n'
        '    for flag in ("-autostart", "-8"):\n'
        '        assert session["command"].count(flag) == 1\n'
        '        assert session["command"][session["command"].index(flag)+1] == '+repr(str(DISK)))
    assert original.count(old) == 1
    adapted = original.replace(old, replacement)
    exec(compile(adapted, '<exact-EOD-side1a-output-startup>', 'exec'), wire.__dict__)
    case = wire.audit_session('native-04')
    assert not case['partial'] and not case['cancelled']
    responses = case['responses']
    assert sorted(responses) == list(range(1, COMMAND_COUNT+1))
    assert all(row['status'] == 'completed' for row in responses.values())
    assert all(row['purpose'] == 'ordinary' for row in case['requests'])
    commands = [responses[n]['command'] for n in range(1, COMMAND_COUNT+1)]
    assert sha(json.dumps(commands, separators=(',', ':')).encode()) == COMMANDS_SHA
    assert not any(event['kind'].startswith('interrupt_') for event in case['events'])
    assert not any(re.search(r'ERROR --|Syntax error|Unknown resource', row['response'])
                   for row in responses.values())
    # Both real observation notices remain in the unmodified journal, including
    # the internal startup r. The frozen auditor reconciles their full streams.
    assert len(case['waits']) == 2
    assert [(row['sequence'], row['command'], row['internal'], row['elapsed_seconds'])
            for row in case['waits']] == [(1, 'r', True, 30.051), (13, 'x', False, 30.003)]
    assert all(row['received_bytes'] == 0 for row in case['waits'])
    assert [responses[row['sequence']]['status'] for row in case['waits']] == ['completed']*2
    assert responses[13]['id'] == 'natural-load52'
    launch = case['session']['command']
    assert '-pal' in launch and launch[launch.index('-speed')+1] == '100'
    assert '+warp' in launch and '+autostart-warp' in launch
    assert '-drive8truedrive' in launch and launch[launch.index('-drive8type')+1] == '1541'
    manifest = json.loads((BASE/'native-04-files.json').read_text())
    listing = [dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
               for p in sorted(CASE.iterdir()) if p.is_file()]
    assert listing == manifest['files'] and len(listing) == manifest['file_count'] == FILE_COUNT
    assert sum(row['bytes'] for row in listing) == manifest['total_bytes'] == TOTAL_BYTES
    assert sha(json.dumps(listing, sort_keys=True, separators=(',', ':')).encode()) == CASE_SHA
    return wire, case, dict(original_function_sha256=sha(original.encode()),
        adapted_function_sha256=sha(adapted.encode()), exact_startup_replacement=replacement,
        no_event_filter_or_other_auditor_change=True)


def source_memory(controller):
    original = bytearray(65536)
    payloads = []
    for number in (51, 52):
        path = EXTRACT/f'EdgeOfDisgrace_1a/trackmo-{number:03}.decoded.prg'
        start, raw = controller.prg(path)
        original[start:start+len(raw)] = raw
        payloads.append(artifact(path))
    return bytes(original), payloads


def continuation(memory, sp):
    return ((memory[0x100+((sp+1)&255)] |
             memory[0x100+((sp+2)&255)] << 8)+1)&65535


def source_guards(memories, original):
    # These exact original ranges bind the scene dispatch, current shader
    # generation and common reconstruction entry. Numeric PCs alone are unsafe.
    ranges = ((0x1643,0x1646), (0x1667,0x1671), (0x16aa,0x16ad),
              (0x16b8,0x16d0), (0x174b,0x1758), (0x1768,0x17e1),
              (0x1a73,0x1a7d), (0x5467,0x5513), (0x5515,0x556d))
    result = []
    for stem, memory in memories.items():
        if stem in ('sys','after52'):
            continue
        checked = []
        for start, end in ranges:
            actual = memory[start:end]
            assert actual == original[start:end], (stem, hex(start), hex(end))
            checked.append(dict(start=start, end_exclusive=end, bytes=end-start,
                                sha256=sha(actual)))
        assert memory[0x1767] == 10
        result.append(dict(stem=stem, dispatcher_state_address=0x1767,
            dispatcher_state=10, exact_original_ranges=checked))
    return result


def check_states(memories, captures):
    states = {row['stem']: row['registers'] for row in captures}
    assert set(states) == set(EXPECTED_STATES)
    for stem, (pc, clock) in EXPECTED_STATES.items():
        assert (states[stem]['pc'], states[stem]['clock']) == (pc, clock), stem
    targets = []
    for name, phase, counter in TARGETS:
        stage_names = {stage: name+'-'+stage for stage in STAGES}
        for stage, stem in stage_names.items():
            assert states[stem]['pc'] == STAGES[stage]
        begin = stage_names['begin']; body = stage_names['body']
        before = stage_names['prefix-before']; filled = stage_names['filled']; cleared = stage_names['cleared']
        assert list(memories[begin][0x5513:0x5515]) == [counter, phase]
        assert continuation(memories[begin], states[begin]['sp']) == 0x17db
        assert (states[body]['sp']-states[begin]['sp']) & 255 == 2
        assert continuation(memories[before], states[before]['sp']) == 0x1750
        assert (states[filled]['sp']-states[before]['sp']) & 255 == 2
        assert states[filled]['sp'] == states[cleared]['sp']
        targets.append(dict(name=name, entry_phase=phase, entry_counter=counter,
            phase_address=0x5514, counter_address=0x5513, captures=stage_names,
            natural_saved_continuations_checked=True,
            intervals=[dict(begin=stage_names[a], end=stage_names[b],
                            cycles=states[stage_names[b]]['clock']-states[stage_names[a]]['clock'])
                       for a,b in zip(STAGES, list(STAGES)[1:])]))
    assert states['display-setup']['pc'] == 0x16bb
    for stem, line, low, high in (('display-mid',130,31,35), ('display-complete',220,35,45)):
        assert states[stem]['line'] == line and low <= states[stem]['cycle'] <= high
    assert states['display-mid']['clock']//19656 == states['display-complete']['clock']//19656
    return targets


def audit_commands(case):
    """Accept only observing/control commands; no RAM/PC/register mutation."""
    grammar = [r'r', r'sidefx off', r'bank ram', r'help (?:break|trace|command)',
        r'warp(?: on| off)?', r'resourceget "Speed"', r'delete [0-9]+',
        r'break [0-9a-f]{4}',
        r'break exec 0000 ffff if \(RL == \$[0-9a-f]+\) && \(CY >= \$[0-9a-f]+\) && \(CY <= \$[0-9a-f]+\)',
        r'condition [0-9]+ if \(@ram:\$1767 == \$0a\) && \(@ram:\$5514 == \$0[12]\) && \(@ram:\$5513 == \$[0-9a-f]{2}\)',
        r'trace store [0-9a-f]{4} [0-9a-f]{4}', r'command [0-9]+ "r"', r'x',
        r'bsave "'+re.escape(str(CASE))+r'/[a-z0-9-]+-ram\.bin" 0 0000 ffff',
        r'dump "'+re.escape(str(CASE))+r'/[a-z0-9-]+\.vsf"',
        r'screenshot "'+re.escape(str(CASE))+r'/display\.png" 2']
    for row in case['responses'].values():
        assert any(re.fullmatch(pattern, row['command']) for pattern in grammar), row['command']
    return dict(all_commands_match_observation_grammar=True,
        manual_RAM_PC_register_write_or_restore_commands=0,
        pinned_ordered_commands_sha256=COMMANDS_SHA)


def mode_queries(case, captures):
    responses = case['responses']
    queries = []
    for row in responses.values():
        if row['command'] == 'warp':
            assert 'Warp mode is off.' in row['response']
            queries.append(response_reference(row))
        elif row['command'] == 'resourceget "Speed"':
            assert re.search(r'Speed\s*=\s*100', row['response'])
            queries.append(response_reference(row))
    assert responses[10]['command'] == 'warp on'
    assert responses[21]['command'] == 'warp off'
    assert responses[22]['command'] == 'warp' and responses[23]['command'] == 'resourceget "Speed"'
    assert [responses[n]['command'] for n in (COMMAND_COUNT-1,COMMAND_COUNT)] == ['warp','resourceget "Speed"']
    scopes = []
    for capture in captures:
        if capture['stem'] in ('sys','after52'):
            continue
        last_change = max(n for n in responses if n < capture['register_sequence'] and responses[n]['command'] in ('warp on','warp off'))
        assert responses[last_change]['command'] == 'warp off'
        warp = max(n for n in responses if last_change < n < capture['register_sequence'] and responses[n]['command']=='warp')
        speed = max(n for n in responses if last_change < n < capture['register_sequence'] and responses[n]['command']=='resourceget "Speed"')
        scopes.append(dict(stem=capture['stem'], warp_off_sequence=last_change,
            actual_warp_query_sequence=warp, actual_speed_query_sequence=speed))
    return dict(actual_query_responses=queries, capture_query_bindings=scopes,
        navigation_warp_declared=True, endpoint_queries_repeated=True)


def checkpoint_bindings(case, captures):
    """Bind each actual natural stop to its live setup and optional predicate."""
    active, stops, setups = {}, {}, []
    for seq,row in sorted(case['responses'].items()):
        command = row['command']
        if command.startswith(('break ', 'trace ')):
            match = re.search(r'^(BREAK|TRACE): ([0-9]+)  C:\$([0-9a-f]{4})(?:-\$([0-9a-f]{4}))?  \((Stop on exec|Trace store)\)', row['response'])
            assert match, row
            kind, number, first, end, operation = match.groups()
            number, first = int(number), int(first,16)
            end = int(end,16) if end else first
            assert number not in active
            if re.fullmatch(r'break [0-9a-f]{4}',command):
                assert first==end==int(command.split()[1],16) and kind=='BREAK'
            elif command.startswith('break exec '):
                assert (first,end,kind)==(0,65535,'BREAK')
            else:
                assert command==f'trace store {first:04x} {end:04x}' and kind=='TRACE'
            conditional = command.split(' if ',1)[1] if ' if ' in command else None
            record = dict(number=number, kind=kind, first=first, last=end,
                operation=operation, setup=response_reference(row),
                condition=conditional, condition_response=response_reference(row) if conditional else None)
            active[number] = record
            setups.append(record)
        elif command.startswith('condition '):
            match = re.fullmatch(r'condition ([0-9]+) if (.+)',command)
            assert match and int(match[1]) in active
            assert row['response'].startswith(f'Setting checkpoint {match[1]} condition to:')
            active[int(match[1])]['condition'] = match[2]
            active[int(match[1])]['condition_response'] = response_reference(row)
        elif command.startswith('command '):
            match=re.fullmatch(r'command ([0-9]+) \"r\"',command)
            assert match and int(match[1]) in active
            active[int(match[1])]['attached_command_response']=response_reference(row)
        elif command.startswith('delete '):
            number = int(command.split()[1]); assert number in active
            active.pop(number)
        elif command == 'x':
            for hit in re.finditer(r'^#([0-9]+) \(Trace store ([0-9a-f]{4})\)',row['response'],re.M):
                number,address=int(hit[1]),int(hit[2],16)
                assert number in active and active[number]['kind']=='TRACE'
                assert active[number]['first']<=address<=active[number]['last']
                assert 'attached_command_response' in active[number]
            natural = list(re.finditer(r'^#([0-9]+) \(Stop on\s+exec ([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+',row['response'],re.M))
            assert len(natural) == 1, (seq, row['response'])
            hit = natural[0]; number,pc = int(hit[1]),int(hit[2],16)
            assert number in active and active[number]['kind']=='BREAK'
            assert active[number]['first'] <= pc <= active[number]['last']
            stops[seq] = dict(checkpoint=active[number].copy(), actual_PC=pc,
                actual_beam=[int(hit[3]),int(hit[4])], stop=response_reference(row))
    bindings=[]
    for capture in captures:
        assert capture['stop_sequence'] in stops
        record = dict(stem=capture['stem'], **stops[capture['stop_sequence']])
        assert record['actual_PC']==capture['registers']['pc']
        assert record['actual_beam']==[capture['registers']['line'],capture['registers']['cycle']]
        if capture['stem'].endswith('-begin'):
            target=next(t for t in TARGETS if capture['stem']==t[0]+'-begin')
            _,phase,counter=target
            expression = record['checkpoint']['condition']
            assert expression == f'(@ram:$1767 == $0a) && (@ram:$5514 == ${phase:02x}) && (@ram:$5513 == ${counter:02x})', expression
        bindings.append(record)
    return dict(setups=setups, natural_capture_stops=bindings,
        numeric_PC_without_source_guard_not_accepted=True)


def display_trace(case, captures, original, wire):
    responses=case['responses']
    arming=[]
    for i,(first,last) in enumerate(TRACE_RANGES):
        sequence=65+2*i; number=10+i
        setup,context=responses[sequence],responses[sequence+1]
        assert setup['command']==f'trace store {first:04x} {last:04x}'
        assert setup['response'].startswith(f'TRACE: {number}  C:${first:04x}-${last:04x}  (Trace store)')
        assert context['command']==f'command {number} "r"'
        assert context['response'].startswith(f'Setting checkpoint {number} command to: r')
        arming.append(dict(number=number, first=first, last=last,
            setup=response_reference(setup), attached_r=response_reference(context)))
    assert responses[75]['command']=='break exec 0000 ffff if (RL == $82) && (CY >= $1f) && (CY <= $23)'
    assert responses[81]['command']=='break exec 0000 ffff if (RL == $dc) && (CY >= $23) && (CY <= $2d)'
    hits=[]; windows=[]
    trace_header=re.compile(r'^#([0-9]+) \(Trace store ([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\n',re.M)
    instruction=re.compile(r'^\.C:([0-9a-f]{4})\s+([0-9A-F]{2}(?: [0-9A-F]{2}){0,2})\s+(.+?)\s+- A:([0-9A-F]{2}) X:([0-9A-F]{2}) Y:([0-9A-F]{2}) SP:([0-9a-f]{2}) ([NV\-BDIZC.]{8})\s+(\d+)\n',re.M)
    expected=[(77,10,0xd012,0x16bd,0x16c0,469329637),
              (77,10,0xd019,0x16c5,0x16c8,469329649),
              (83,10,0xd012,0x1732,0x1735,469338451),
              (83,10,0xd019,0x173a,0x173d,469338463)]
    for seq in (77,83):
        row=responses[seq];assert row['command']=='x'
        text=row['response'];assert text.isascii()
        matches=list(trace_header.finditer(text))
        assert text.count('(Trace store ')==len(matches)
        windows.append(dict(response=response_reference(row), instruction_hits=len(matches)))
        for index,match in enumerate(matches):
            natural=re.search(r'^#[0-9]+ \(Stop on',text[match.end():],re.M)
            assert natural
            last=matches[index+1].start() if index+1<len(matches) else match.end()+natural.start()
            segment=text[match.end():last]
            ins=instruction.search(segment);assert ins and segment.count('Executing: r')==1
            regs=wire.registers(segment)
            number,address,line,cycle=int(match[1]),int(match[2],16),int(match[3]),int(match[4])
            pc=int(ins[1],16);raw=bytes.fromhex(ins[2])
            assert original[pc:pc+len(raw)]==raw
            assert 10<=number<=14 and TRACE_RANGES[number-10][0]<=address<=TRACE_RANGES[number-10][1]
            assert regs['clock']==int(ins[9]) and (regs['line'],regs['cycle'])==(line,cycle)
            assert regs['port00']==0x2f and regs['port01']==0x35
            assert regs['pc']==pc+len(raw)
            assert [regs[key] for key in ('a','x','y','sp')]==[int(ins[k],16) for k in (4,5,6,7)]
            hits.append(dict(sequence=seq, checkpoint=number, monitored_address=address,
                monitor_instruction_PC=pc, instruction_hex=raw.hex(), instruction=ins[3],
                attached_post_instruction_registers=regs, original_source_range=[pc,pc+len(raw)],
                received_first=row['received_first']+match.start(),
                received_end=row['received_first']+last,
                trace_block_bytes=last-match.start(),
                trace_block_sha256=sha(text[match.start():last].encode()),
                response=response_reference(row), physical_bus_write_count_inferred=False))
    assert [(h['sequence'],h['checkpoint'],h['monitored_address'],h['monitor_instruction_PC'],
             h['attached_post_instruction_registers']['pc'],h['attached_post_instruction_registers']['clock'])
            for h in hits]==expected
    capturemap={c['stem']:c for c in captures}
    assert capturemap['display-setup']['stop_sequence']==59
    assert capturemap['display-mid']['stop_sequence']==77 and capturemap['display-complete']['stop_sequence']==83
    return dict(arming=arming, raw_windows=windows, observed_instruction_hits=hits,
        instruction_hits=4, no_other_monitor_trace_hits_in_watched_ranges=True,
        RMW_limit='INC D019 is a monitored RMW instruction hit; no one-hit/one-physical-bus-write equivalence is assumed.',
        CPU_port_context='All four attached post-instruction r rows read CPU01=35; addressed-device classification belongs to display proof.',
        source_ranges=[dict(start=h['monitor_instruction_PC'],end_exclusive=h['monitor_instruction_PC']+len(bytes.fromhex(h['instruction_hex'])),
                            sha256=sha(bytes.fromhex(h['instruction_hex']))) for h in hits])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to((BASE/'output-case-analysis').resolve())
    assert not out.exists(), 'Choose a fresh output directory'
    # Fail before inspecting a live case, importing readers, or creating outputs.
    assert not CASE_SHA.startswith('PENDING'), 'Only accept an owner-closed, pinned case'
    for name, expected in PINS.items():
        assert sha((ROOT/name).read_bytes()) == expected, name
    wire, case, adapter = audit_wire()
    controller = load('eod_output_capture_reader', 'research/eod/controller.py')
    controller.CASE = CASE
    reader = load('eod_output_snapshot', 'research/quondam/snapshot_state.py')
    memories, captures = controller.capture_pairs(reader, wire, case)
    original, original_inputs = source_memory(controller)
    guards = source_guards(memories, original)
    targets = check_states(memories, captures)
    command_audit=audit_commands(case)
    modes=mode_queries(case,captures)
    checkpoints=checkpoint_bindings(case,captures)
    trace=display_trace(case,captures,original,wire)
    payloads=[]
    for stem,name,length in (('sys','dos-001.raw.prg',874),
                             ('after52','trackmo-052.decoded.prg',13603)):
        path=EXTRACT/'EdgeOfDisgrace_1a'/name
        start,data=controller.prg(path)
        assert len(data)==length and memories[stem][start:start+length]==data
        payloads.append(dict(capture=stem,source=artifact(path),start=start,bytes=length,all_equal=True))
    after52=next(row for row in captures if row['stem']=='after52')['registers']
    assert after52['a']==0 and after52['flags']&1 and not after52['flags']&8
    boot=load('eod_output_port_sources','research/eod/native_boot.py')
    ports=boot.primary_port_sources()
    checked=Path(__file__).read_bytes()
    proof=dict(pass_=True,
        scope='Closed original EOD side1a output/display/multi-pose capture custody; independent arithmetic and displayed-pixel results belong to separate producers',
        producer=artifact(Path(__file__)), inputs=[artifact(ROOT/p) for p in PINS]+original_inputs,
        case_sha256=CASE_SHA,case_manifest=artifact(BASE/'native-04-files.json'),
        wire=wire.summary(case),adapter=adapter,command_audit=command_audit,
        waiting_notices=case['waits'],captures=captures,primary_port_schema=ports,
        original_payloads=payloads,original_source_generation_guards=guards,
        phase_counter_targets=targets,actual_modes=modes,checkpoint_bindings=checkpoints,
        display_trace=trace,
        limits=['Fresh original disk boot; no manual RAM, register or PC mutation, restore, interrupt, retry or event filtering.',
            'Only the frozen auditor startup assertion is adapted in memory; controller.capture_pairs remains unchanged.',
            'Observed trace hits retain their raw byte ranges and attached register context; RMW bus writes are not counted from monitor hits.',
            'Complete state-pair and source/checkpoint custody do not independently prove arithmetic, correct pixels, publication, all poses, full-field scanout, delivered FPS or a speedup.',
            'No emulator, socket, subprocess, CPU interpreter, build or downloaded host execution occurs in this passive producer.'],
        outputs=[dict(name='output_case.checked.py',bytes=len(checked),sha256=sha(checked))])
    raw=(json.dumps(proof,indent=2)+'\n').encode()
    out.mkdir(parents=True)
    (out/'output_case.checked.py').write_bytes(checked)
    (out/'output-case-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=True,pairs=len(captures),receipt_bytes=len(raw),receipt_sha256=sha(raw),trace_instruction_hits=4)))


if __name__ == '__main__':
    main()
