#!/usr/bin/env python3
"""Measure a closed original Next Round trace; no emulator or CPU code runs."""
import argparse
import ast
from collections import Counter
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import statistics
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/next-round-timing'
CASE = BASE / 'native-01'
OUTPUT_ROOT = BASE / 'analysis'
CASE_SHA = '766e62fa105c35fc722de5e540343265a2a825bec8970a677b57ed06cf2ff507'
PROGRAM = ROOT / 'build/research/next-round/boot-analysis/round3-bootstrap.prg'
DISK = ROOT / 'build/research/next-round/release/round3.d64'
PAL = 312 * 63
PINS = {
    'research/verify_vice_live.py': 'f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a',
    'research/vice_session_live.py': '4340d1b0394fa612f5e6a71edddcbc2daf947e59c4c3013ab3b850c886dc621c',
    'build/research/next-round-timing/native-01-pin.json': 'dd11fe82b1dc19edae5487611af12b40dbcd20faa558829e33d41334be4630b0',
    'build/research/next-round-timing/capture-validation.json': '99f07e26e99d0f2345e6f1ecfb4f7b225f1c5bd08d0689062c6cdb8f2e1cb3dc',
    'research/next-round-timing/validate_capture.py': '30131085455c577f408a32a136e7113e883da904574302dc308e47b5d5ffc5bf',
    'research/next-round-timing/capture-plan.json': 'bbd121d4d72941ee1773ed4539bcb24a364f82a3449f358dc394c1196e42f0a1',
    'build/research/next-round/boot-analysis/original-scene.json': '5f4fa37f2ad743f330b5e1fb86a73e9566a4fc3db774001e4fcc14573e2ff4f0',
    'build/research/next-round/full-source/full/full.asm': '980757e07b9c2447f77ad83fb87696fe5fd4589e1a1a671b21e46222bf1ef5dd',
    'build/research/next-round/boot-analysis/round3-bootstrap.prg': 'a5441eea42eab6f7bbe9566403cf5eae9b86e2e17dbdadeca7813ad6ae6682ec',
    'build/research/next-round/release/round3.d64': 'e1991a76fa7968743e81efd7fd46bd1c4f81cc831512f02b33fb8eef563a4179',
}
EVENT = re.compile(
    r'^#(?P<checkpoint>\d+) \((?P<category>Trace|Stop on)\s+exec (?P<target>[0-9a-f]{4})\)\s+'
    r'(?P<line>\d+)/\$(?P<linehex>[0-9a-f]+),\s+(?P<cycle>\d+)/\$(?P<cyclehex>[0-9a-f]+)\n'
    r'\.C:(?P<pc>[0-9a-f]{4})\s+(?P<opcode>[0-9a-f]{2}(?: [0-9a-f]{2}){0,2})\s+[^\n]*?- '
    r'A:(?P<a>[0-9a-f]{2}) X:(?P<x>[0-9a-f]{2}) Y:(?P<y>[0-9a-f]{2}) '
    r'SP:(?P<sp>[0-9a-f]{2}) (?P<flags>[^ ]{8})\s+(?P<clock>\d+)\n', re.M | re.I)
MEMORY = re.compile(r'^>C:([0-9a-f]{4})  ([0-9a-f]{2}(?: [0-9a-f]{2}){0,3})(?=\s{2,}|$)', re.M | re.I)
MAIN, RETURN, COPY, REQUEST = [0x600, 0x6a5, 0x74a], [0x603, 0x6a8, 0x74d], [0x65e, 0x703, 0x7a8], [0x669, 0x70e, 0x7b3]
BANKS = [0xc6, 0xd8, 0xea]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def load_wire():
    spec = importlib.util.spec_from_file_location('next_round_frozen_wire', ROOT / 'research/verify_vice_live.py')
    wire = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wire)
    wire.BASE, wire.CASE_PINS = BASE, {'native-01': CASE_SHA}
    text = (ROOT / 'research/verify_vice_live.py').read_text()
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == 'audit_session')
    original = ast.get_source_segment(text, node) + '\n'
    old = 'assert session["startup_mode"] == "manual monitor load" and "-autostart" not in session["command"]'
    new = ('assert session["startup_mode"] == "autostart"\n'
           '    assert session["command"].count("-autostart") == 1\n'
           f'    assert session["command"][session["command"].index("-autostart") + 1] == {str(PROGRAM)!r}\n'
           '    assert session["command"].count("-8") == 1\n'
           f'    assert session["command"][session["command"].index("-8") + 1] == {str(DISK)!r}')
    assert original.count(old) == 1
    adapted = original.replace(old, new)
    exec(compile(adapted, '<original-bootstrap-autostart-metadata>', 'exec'), wire.__dict__)
    case = wire.audit_session('native-01')
    assert not case['partial'] and not case['cancelled']
    assert len(case['waits']) == 1 and case['waits'][0]['sequence'] == 59
    assert all(row['status'] == 'completed' for row in case['responses'].values())
    launch = case['session']['command']
    assert case['session']['program'] == str(PROGRAM) and '-pal' in launch
    assert launch[launch.index('-autostartprgmode') + 1] == '1'
    assert launch[launch.index('-speed') + 1] == '100' and '+warp' in launch and '+autostart-warp' in launch
    return wire, case, dict(original_function_sha256=sha(original.encode()), adapted_function_sha256=sha(adapted.encode()),
        replaced_assertion=old, replacement=new, scope='Exact original bootstrap and disk argv only; frozen wire/closure checks unchanged.')


def commands(wire, case, validation):
    rows = [row for _, row in sorted(case['responses'].items())]
    assert [r['sequence'] for r in rows] == list(range(1, 65))
    allowed = {'r', 'sidefx off', 'resourceget "Speed"', 'break 0800', 'break e000', 'x', 'delete 1', 'delete 2',
               'warp on', 'warp off', 'bank ram', 'break 0600', 'd 0600 07f1', 'd ff00 ff96', 'd 5d02 5d47',
               'help trace', 'help command', 'break 5d44'}
    captures, latest = {}, None
    for row in rows:
        command, response = row['command'], row['response']
        assert not re.search(r'ERROR --|Syntax error|Unknown resource|[Mm]onitor observation failed', response)
        accepted = command in allowed
        accepted |= bool(re.fullmatch(r'trace exec (?:0600|06a5|074a|5d02|5d32|0603|06a8|074d|065e|0703|07a8|0669|070e|07b3|ff40)', command))
        accepted |= bool(re.fullmatch(r'command (?:[1-9]|1[0-5]) "m 0017 0022(?:; m 0100 01ff)?"', command))
        if command == 'r':
            latest = wire.registers(response)
        if command == 'x':
            latest = None
        match = re.fullmatch(r'(bsave|dump|screenshot) "([^"\n]+)"( 0 0000 ffff| 2)?', command)
        if match:
            kind, name, suffix = match.groups()
            path = Path(name)
            assert path.parent == CASE and latest is not None and path.name not in captures
            assert suffix == (' 0 0000 ffff' if kind == 'bsave' else ' 2' if kind == 'screenshot' else None)
            captures[path.name] = latest
            accepted = True
        assert accepted, command
    assert [r['sequence'] for r in rows if r['command'] == 'warp on'] == [8]
    assert [r['sequence'] for r in rows if r['command'] == 'warp off'] == [10]
    assert [r['sequence'] for r in rows if r['command'] == 'resourceget "Speed"'] == [3, 11, 63]
    assert all(case['responses'][n]['response'].split('(C:')[0].strip() == 'Speed=100' for n in [3, 11, 63])
    for pair in validation['paired_captures']:
        assert captures[Path(pair['ram']['path']).name] == captures[Path(pair['snapshot']['path']).name] == pair['registers']
    plan = json.loads((ROOT / 'research/next-round-timing/capture-plan.json').read_text())
    for row, planned in zip(rows[26:59], plan['commands']):
        assert row['command'] == planned['command']
    assert len(plan['commands']) == 33 and case['responses'][59]['command'] == 'x'
    return dict(ordinary_commands=64, completed=64, errors=[], interrupted=[], restored_or_manually_patched=[],
        waiting_notices=case['waits'], same_sequence_completed_after_wait=59,
        navigation_warp_on_sequence=8, proof_warp_off_sequence=10, Speed_100_sequences=[3, 11, 63],
        startup='Original extracted DOS bootstrap through declared PRG autostart mode1, with original disk attached; no later PC/RAM/register patch.')


def source_and_scene(loop, end, entry):
    scene = json.loads((ROOT / 'build/research/next-round/boot-analysis/original-scene.json').read_text())
    cursor, polygons = 0x6cbd, 0
    for index, frame in enumerate(scene['frames']):
        assert frame['frame'] == index and frame['address'] == cursor
        for poly in frame['polygons']:
            descriptor = entry[cursor]
            assert descriptor == poly['descriptor'] and 1 <= descriptor & 15 <= 12
            count = (descriptor >> 4) + 3
            cursor += 1
            yx = [list(entry[cursor + 2*i:cursor + 2*i + 2]) for i in range(count)]
            assert yx == poly['raw_yx'] and len(poly['outline_xy']) == count
            cursor += 2 * count
            polygons += 1
        assert entry[cursor] == 0
        frame['terminator_address'] = cursor
        cursor += 1
    assert len(scene['frames']) == 536 and polygons == 2402 and cursor == 0xc571
    assert sha(entry[0x6cbd:cursor]) == scene['summary']['stream_sha256']
    assert loop[0x6cbd:cursor] == end[0x6cbd:cursor] == entry[0x6cbd:cursor]
    expected = {0x600:'202023', 0x6a5:'207023', 0x74a:'207766', 0x5d02:'841c851da000b318f026',
        0x5d32:'e618d002e619a518', 0x5d3a:'c971d009a519c9c5', 0x5d44:'4c180460',
        0x65e:'a9eac522d0fca9008d39ff', 0x703:'a9c6c522d0fca9018d39ff', 0x7a8:'a9d8c522d0fca9028d39ff',
        0xff38:'a2', 0xff3a:'bd74ff8d18d08522', 0xff74:'c6d8ea',
        0x496:'a9ec8d6a068d0f078db407a9ce8d6affa9198d6bffa9d08d6cff'}
    for pc, value in expected.items():
        raw = bytes.fromhex(value)
        assert loop[pc:pc + len(raw)] == end[pc:pc + len(raw)] == raw, hex(pc)
    assert loop[0xff39] == 2 and loop[0x22] == 0 and end[0xff39] == 0
    assert loop[0x18]+256*loop[0x19] == 0x6cbd and end[0x18]+256*end[0x19] == cursor
    assert loop[0xff6a:0xff6d] == bytes.fromhex('20 32 04')
    assert end[0xff6a:0xff6d] == bytes.fromhex('ce 19 d0')
    return scene['frames'], dict(frame_count=536, polygon_count=polygons, stream_start=0x6cbd, stream_end=cursor,
        stream_sha256=scene['summary']['stream_sha256'], stream_identical_at_entry_loop_end=True,
        code_guards=[dict(pc=pc, bytes=value) for pc, value in expected.items()],
        IRQ_integration_patch=dict(initial_ff6a='203204', final_ff6a='ce19d0',
            interpretation='Original startup/fade integration selfmodifies to IRQ acknowledgement; early IRQ costs may differ.'),
        source_lines=dict(loop=[1821,1836], render_macro=[1625,1662], frame=[2983,3032], switch=[1605,1613], sprite_copy=[1739,1788]),
        data_contract='Prepared 2D polygon coordinates/patterns; runtime rasterization, allocation, cleanup and scheduling; not runtime3D transform proof.')


def parse_trace(case, loop, points):
    response = case['responses'][59]
    raw = response['response'].replace('\r\n', '\n')
    headers = list(EVENT.finditer(raw))
    assert len(headers) == len(re.findall(r'^#\d+ \(', raw, re.M)) == 4841
    events = []
    for index, match in enumerate(headers):
        event = {key:int(match[key], 16 if key in ('pc','target','a','x','y','sp') else 10)
                 for key in ('checkpoint','pc','target','line','cycle','a','x','y','sp','clock')}
        assert event['line'] == int(match['linehex'],16) and event['cycle'] == int(match['cyclehex'],16)
        assert event['pc'] == event['target'] and 0 <= event['line'] < 312 and 0 <= event['cycle'] < 63
        assert (event['clock'] - event['line']*63 - event['cycle']) % PAL == 0
        event['field'] = (event['clock'] - event['line']*63 - event['cycle']) // PAL
        opcode = bytes.fromhex(match['opcode'])
        event['opcode'] = opcode.hex()
        if event['pc'] in REQUEST:
            # clr_logo immediate is patched by the original0432 integration,
            # then reset to00 by setup_char_del after its one use.
            assert opcode in (bytes.fromhex('a200'),bytes.fromhex('a2ec'))
        else:
            assert loop[event['pc']:event['pc'] + len(opcode)] == opcode
        chunk = raw[match.end():headers[index + 1].start() if index + 1 < len(headers) else len(raw)]
        if match['category'].lower() == 'stop on':
            assert event['pc'] == 0x5d44 and event['checkpoint'] == 16 and index == len(headers) - 1
            event.update(kind='scene-end', zp=None)
        else:
            assert event['checkpoint'] in points and event['pc'] == int(points[event['checkpoint']]['pc'],16)
            required_command = 'm 0017 0022' + ('; m 0100 01ff' if event['pc'] == 0x5d02 else '')
            assert chunk.startswith('Executing: ' + required_command + '\n')
            memory = {}
            for line in MEMORY.finditer(chunk):
                address = int(line[1],16)
                for offset, byte in enumerate(bytes.fromhex(line[2])):
                    assert address + offset not in memory
                    memory[address + offset] = byte
            required = set(range(0x17,0x23)) | (set(range(0x100,0x200)) if event['pc'] == 0x5d02 else set())
            assert set(memory) == required
            event.update(kind=points[event['checkpoint']]['name'], zp=bytes(memory[i] for i in range(0x17,0x23)),
                         data=memory[0x18]+256*memory[0x19], ack=memory[0x22], allocated=memory[0x17])
            if event['pc'] == 0x5d02:
                assert event['sp'] == 0xfd
                event['saved_return'] = memory[0x100+((event['sp']+1)&255)] + 256*memory[0x100+((event['sp']+2)&255)]
        events.append(event)
    assert all(a['clock'] < b['clock'] for a,b in zip(events,events[1:]))
    return events


def stats(values):
    return dict(count=len(values), total_cycles=sum(values), min_cycles=min(values), median_cycles=statistics.median(values),
                max_cycles=max(values))


def measure(events, frames, loop, seed, endpoint):
    current = dict(frame=0, buffer_index=0, main=dict(seed, kind='main-1', data=loop[0x18]+256*loop[0x19], ack=loop[0x22], allocated=loop[0x17]))
    results, publications, pending, front, requested_index, ack = [], [], None, None, loop[0xff39], loop[0x22]
    current['main']['field'] = (seed['clock'] - seed['line']*63 - seed['cycle']) // PAL
    for event in events:
        pc = event['pc']
        if pc == 0x5d44:
            assert current['frame'] == 535 and 'draw-end' in current and 'return' not in current
            assert all(event[k] == endpoint[k] for k in ('pc','a','x','y','sp','clock','line','cycle'))
            current['scene-end'] = event
            results.append(current)
            continue
        assert event['ack'] == ack
        if pc == 0xff40:
            assert event['x'] == requested_index and event['a'] == BANKS[event['x']]
            category = 'baseline' if front is None else 'repeat' if front == event['a'] else 'changed'
            row = dict(clock=event['clock'], field=event['field'], line=event['line'], raw_cycle=event['cycle'],
                       bank=event['a'], buffer_index=event['x'], prior_ack=event['ack'], category=category, frame=None)
            if pending is not None:
                assert category == 'changed' and pending['buffer_index'] == event['x']
                pending['publication'] = event
                row['frame'] = pending['frame']
                pending = None
            else:
                assert category in ('baseline','repeat')
            publications.append(row)
            front = ack = event['a']  # Next original instruction STA22, with IRQs masked.
            continue
        if pc in MAIN:
            assert 'requested' in current
            current['next-main'] = event
            results.append(current)
            current = dict(frame=len(results), buffer_index=len(results)%3, main=event)
        number, buffer_index = current['frame'], current['buffer_index']
        expected_start = frames[number]['address']
        expected_next = frames[number]['terminator_address'] + 1
        if pc in MAIN:
            assert pc == MAIN[buffer_index] and event['sp'] == 0xff and event['data'] == expected_start
        elif pc == 0x5d02:
            assert 'draw-entry' not in current and event['data'] == expected_start
            assert event['saved_return'] + 1 == RETURN[buffer_index]
            current['draw-entry'] = event
        elif pc == 0x5d32:
            assert 'draw-entry' in current and 'draw-end' not in current
            assert event['data'] == expected_next - 1 and event['sp'] == 0xfd
            current['draw-end'] = event
        elif pc in RETURN:
            assert 'draw-end' in current and pc == RETURN[buffer_index] and event['data'] == expected_next and event['sp'] == 0xff
            current['return'] = event
        elif pc in COPY:
            assert 'return' in current and pc == COPY[buffer_index] and event['data'] == expected_next and event['sp'] == 0xff
            current['copy-end'] = event
        elif pc in REQUEST:
            assert 'copy-end' in current and pc == REQUEST[buffer_index] and event['data'] == expected_next and event['sp'] == 0xff
            assert pending is None and event['a'] == buffer_index and event['ack'] == BANKS[(buffer_index-1)%3]
            requested_index = buffer_index
            current['requested'] = event
            pending = current
        else:
            raise AssertionError(hex(pc))
    assert len(results) == 536 and pending is None and len(publications) == 1628
    assert sum(r['category']=='changed' for r in publications) == 535
    assert all('publication' in frame for frame in results[:-1]) and 'publication' not in results[-1]
    rows = []
    phases = [('prepare_clear','main','draw-entry'),('polygon_body','draw-entry','draw-end'),
              ('frame_epilogue','draw-end','return'),('sprite_copy','return','copy-end'),
              ('wait_and_request','copy-end','requested'),('post_request_metadata','requested','next-main')]
    for frame in results:
        row = dict(frame=frame['frame'], buffer_index=frame['buffer_index'], scene_address=frames[frame['frame']]['address'],
                   terminator_address=frames[frame['frame']]['terminator_address'], polygons=len(frames[frame['frame']]['polygons']))
        for name in ('main','draw-entry','draw-end','return','copy-end','requested','next-main','publication','scene-end'):
            event = frame.get(name)
            for field in ('clock','pc','sp','line','cycle','data','allocated'):
                row[name.replace('-','_')+'_'+field] = event.get(field) if event else None
        row['actual_saved_return_word'] = frame['draw-entry']['saved_return']
        for name, start, end in phases:
            row[name+'_cycles'] = frame[end]['clock'] - frame[start]['clock'] if end in frame else None
        row['main_to_next_main_cycles'] = frame['next-main']['clock'] - frame['main']['clock'] if 'next-main' in frame else None
        row['request_to_publication_cycles'] = frame['publication']['clock'] - frame['requested']['clock'] if 'publication' in frame else None
        row['censored'] = 'return' not in frame
        if not row['censored']:
            assert sum(row[name+'_cycles'] for name,_,_ in phases) == row['main_to_next_main_cycles']
        rows.append(row)
    complete = rows[:-1]
    summaries = {name:stats([r[name+'_cycles'] for r in complete]) for name,_,_ in phases}
    summaries['main_to_next_main'] = stats([r['main_to_next_main_cycles'] for r in complete])
    assert sum(s['total_cycles'] for name,s in summaries.items() if name!='main_to_next_main') == summaries['main_to_next_main']['total_cycles']
    changed = [row for row in publications if row['category']=='changed']
    observed_banks = [row for row in publications if row['category']!='repeat']
    intervals = [b['clock']-a['clock'] for a,b in zip(observed_banks,observed_banks[1:])]
    gaps = Counter(b['field']-a['field'] for a,b in zip(observed_banks,observed_banks[1:]))
    changed_intervals = [b['clock']-a['clock'] for a,b in zip(changed,changed[1:])]
    changed_gaps = Counter(b['field']-a['field'] for a,b in zip(changed,changed[1:]))
    return rows, publications, dict(complete_535_phase_summaries=summaries,
        polygon_body_all_536=stats([r['polygon_body_cycles'] for r in rows]),
        prepare_clear_all_536=stats([r['prepare_clear_cycles'] for r in rows]),
        request_to_publication_535=stats([r['request_to_publication_cycles'] for r in complete]),
        loop_to_scene_end_cycles=endpoint['clock']-seed['clock'],
        final_censor=dict(frame=535, main_clock=rows[-1]['main_clock'], draw_entry_clock=rows[-1]['draw_entry_clock'],
            body_end_clock=rows[-1]['draw_end_clock'], scene_end_clock=endpoint['clock'],
            body_end_to_scene_handoff_cycles=endpoint['clock']-rows[-1]['draw_end_clock'],
            absent=['normal_return','sprite_copy','request','publication','next_main']),
        publication=dict(IRQ_samples=len(publications), initial_baseline_records=1, changed_queued_publications=len(changed),
            repeated_same_bank_samples=sum(p['category']=='repeat' for p in publications),
            baseline_to_changed_and_changed_to_changed_periods=stats(intervals),
            exact_PAL_field_gap_histogram=dict(sorted(gaps.items())),
            changed_to_changed_periods=stats(changed_intervals),
            changed_to_changed_exact_PAL_field_gap_histogram=dict(sorted(changed_gaps.items())),
            interpretation='D018 bank-publication cadence only. Baseline is not a new queued frame; no pixel scanout or delivered FPS is proved.'))


def write(directory, name, raw):
    (directory/name).write_bytes(raw)
    return dict(file=name,bytes=len(raw),sha256=sha(raw))


def csv_output(directory, name, rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return write(directory,name,stream.getvalue().encode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUTPUT_ROOT/'accepted-01')
    directory = parser.parse_args().output.expanduser().resolve()
    directory.relative_to(OUTPUT_ROOT.resolve())
    if directory.exists() and any(directory.iterdir()):
        raise SystemExit('Output must be fresh or empty; choose a new --output directory.')
    for relative,pin in PINS.items():
        assert sha((ROOT/relative).read_bytes()) == pin,relative
    validation = json.loads((BASE/'capture-validation.json').read_text())
    assert validation['pass_'] and validation['case_sha256'] == CASE_SHA and validation['total_original_payload_bytes'] == 44525
    wire,case,adapter = load_wire()
    audit = commands(wire,case,validation)
    captures = {r['stem']:r for r in validation['paired_captures']}
    loop,end,entry = [(ROOT/captures[name]['ram']['path']).read_bytes() for name in ('loop','end','entry')]
    frames,source = source_and_scene(loop,end,entry)
    plan = json.loads((ROOT/'research/next-round-timing/capture-plan.json').read_text())
    points = {row['checkpoint']:row for row in plan['points']}
    events = parse_trace(case,loop,points)
    rows,publications,summary = measure(events,frames,loop,captures['loop']['registers'],captures['end']['registers'])
    assert case['responses'][59]['received_first'] == 13227 and case['responses'][59]['received_end'] == 2082039
    directory.mkdir(parents=True,exist_ok=True)
    outputs = [csv_output(directory,'frames.csv',rows),csv_output(directory,'publications.csv',publications),
               write(directory,'analyze.checked.py',Path(__file__).read_bytes())]
    result = dict(pass_=True,producer=artifact(Path(__file__).resolve()),inputs=[artifact(ROOT/p) for p in PINS],
        case_sha256=CASE_SHA,wire=wire.summary(case),startup_adapter=adapter,command_audit=audit,
        capture_identity_receipt=artifact(BASE/'capture-validation.json'),source_and_scene=source,
        trace=dict(response_sequence=59,received_first=13227,received_end=2082039,execution_rows=4841,trace_rows=4840,
            counter=dict(Counter(e['kind'] for e in events)),seeded_initial_main=dict(captures['loop']['registers']),
            initial_main_absent_from_trace='Execution was already stopped at0600 when trace was armed; exact loop registers/RAM seed frame0.',
            all_scene_pointers_checked=True,all_536_parent_stack_continuations_checked=True,
            exact_memory_payloads='12bytes0017..0022; do_frame additionally256bytes0100..01ff.',
            original_logo_count_LDX_variants=dict(Counter(e['opcode'] for e in events if e['pc'] in REQUEST)),
            PAL_cycles_per_field=PAL,all_beam_coordinates_match_cpu_clock_modulo_PAL=True),
        summary=summary,outputs=outputs,
        limits=['Original prepared2D stream and runtime rasterizer are timed; no runtime3D geometry/lighting pipeline is established.',
            'All phase durations are elapsed emulated PAL cycles, including IRQ execution, VIC bus stalls and phase effects; not exclusive CPU instruction costs.',
            'The536th body reaches its terminator and scene handoff but has no normal return, sprite copy, request or publication in this window.',
            'FF40 proves original D018 store reached; repeat bank samples and queued changed publications are separate. No full scanout or delivered-frame FPS is claimed.',
            'Original startup integration selfmodifies later; no later manual CPU/RAM/register patch, emulator, build, SDK or downloaded host executable runs in this analysis.'])
    receipt = write(directory,'timing-proof.json',(json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps(dict(output=str(directory),receipt=receipt,summary=summary),indent=2))


if __name__ == '__main__':
    main()
