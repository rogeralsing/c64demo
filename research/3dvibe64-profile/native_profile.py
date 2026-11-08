#!/usr/bin/env python3
"""Accept closed native profiling traces; no CPU, build tool or emulator runs."""
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

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/3dvibe64-profile'
CASE = BASE / 'native-01'
PROGRAM = ROOT / 'build/research/3dvibe64-native/build-01/products/3Dvibe64.prg'
CASE_SHA = '13bfd23f30bf0b7a2db7a9e8dc4ceb8dc69e77d81c76862fe9b372a1f23ef714'
PINS = {
    'research/verify_vice_live.py': 'f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a',
    'research/vice_session_live.py': '4340d1b0394fa612f5e6a71edddcbc2daf947e59c4c3013ab3b850c886dc621c',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'research/3dvibe64-profile/anchors.py': '34c3ee2bed850f80dfaa51e1ad989ad2f9c1c141c33f470904a6c2a971c8544f',
    'research/3dvibe64-profile/native-plan.json': 'b7eecbadea670f5441d41b455f2d9da5400a9f77ecb4c87408443a16ef60d307',
    'build/research/3dvibe64-profile/native-01-pin.json': '35abf1d4b0f02aad49e08cb38337b80be108bc60fa315161b573490331d6a246',
    'build/research/3dvibe64-profile/source-analysis/accepted-02/anchors.json': 'f61a80d70d90fe58b48c3f3f7109d58f62551d6d81aff4f71fde6f3aeb3c5937',
    'build/research/3dvibe64-native/build-01/products/3Dvibe64.prg': '69b0d86f79106b2bf9654d85bd631bc68c12f4efd708454a0048560b3c1bfdeb',
    'build/research/quondam/hardware-source/vice-3.10.tar.gz': '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1',
}
TRACE = re.compile(
    r'^#(?P<id>\d+) \(Trace\s+exec\s+(?P<target>[0-9a-f]{4})\)\s+'
    r'(?P<line>\d+)/\$[0-9a-f]+,\s+(?P<cycle>\d+)/\$[0-9a-f]+\n'
    r'\.C:(?P<pc>[0-9a-f]{4}) +(?P<bytes>(?:[0-9a-f]{2} +){1,3})[^\n]*?'
    r'- A:(?P<a>[0-9a-f]{2}) X:(?P<x>[0-9a-f]{2}) Y:(?P<y>[0-9a-f]{2}) '
    r'SP:(?P<sp>[0-9a-f]{2}) [^\n]*? +(?P<clock>\d+)\n', re.M | re.I)
MEMORY = re.compile(r'^>C:([0-9a-f]{4})  ([0-9a-f]{2}(?: [0-9a-f]{2}){0,3})(?=\s{2,}|$)', re.M | re.I)
FRAMES = [('first', [85, 98]), ('second', [112, 119]), ('third', [133, 140])]
BUCKET = {
    'light_intensity': 'lighting', 'object_light': 'lighting', 'vertex_shades': 'lighting',
    'reflectivity': 'lighting', 'dirty_clear': 'clearing',
    'matrix_angles': 'rotation_and_projection', 'rotation_depth': 'rotation_and_projection',
    'lazy_project_vertex': 'rotation_and_projection',
    'xyq2_bounds': 'geometry_and_shade_edges', 'shade_edges': 'geometry_and_shade_edges',
    'shade_span': 'span_drawing', 'material_span_a': 'material', 'material_span_b': 'material',
    'load_material': 'material', 'fill_bounds': 'row_setup_and_dirty_tracking',
    'collect_faces': 'culling_and_bucketing',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def load(name, rel):
    assert sha((ROOT / rel).read_bytes()) == PINS[rel]
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wire_case():
    wire = load('profile_wire', 'research/verify_vice_live.py')
    wire.BASE, wire.CASE_PINS = BASE, {'native-01': CASE_SHA}
    source = (ROOT / 'research/verify_vice_live.py').read_text()
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'audit_session')
    original = ast.get_source_segment(source, node) + '\n'
    before = 'assert session["startup_mode"] == "manual monitor load" and "-autostart" not in session["command"]'
    after = ('assert session["startup_mode"] == "autostart"\n'
             '    assert session["command"].count("-autostart") == 1\n'
             f'    assert session["command"][session["command"].index("-autostart") + 1] == {str(PROGRAM)!r}')
    assert original.count(before) == 1
    adapted = original.replace(before, after)
    exec(compile(adapted, '<pinned-profile-PRG-autostart-contract>', 'exec'), wire.__dict__)
    case = wire.audit_session('native-01')
    assert not case['partial'] and not case['cancelled'] and not case['waits']
    launch = case['session']['command']
    assert case['session']['program'] == str(PROGRAM) and '-pal' in launch
    assert launch[launch.index('-speed')+1] == '100'
    assert '+warp' in launch and '+autostart-warp' in launch
    assert launch[launch.index('-autostartprgmode')+1] == '1'
    manifest = json.loads((BASE / 'native-01-pin.json').read_text())
    expected = [dict(name=Path(f['path']).name, bytes=f['bytes'], sha256=f['sha256']) for f in case['files']]
    assert manifest['case_sha256'] == CASE_SHA and manifest['entries'] == expected
    assert len(expected) == 29 and sum(f['bytes'] for f in expected) == 14444407
    return wire, case, dict(original_function_sha256=sha(original.encode()), adapted_function_sha256=sha(adapted.encode()),
                           replaced_assertion=before, replacement=after,
                           scope='Only exact generated-PRG autostart metadata replaces manual-load metadata.')


def command_audit(wire, case, plan):
    rows = list(case['responses'].values())
    assert [r['sequence'] for r in rows] == list(range(1, 154))
    assert all(r['status'] == 'completed' for r in rows)
    points = {p['id']: p for p in plan['points']}
    armed, attached, contexts, rejected, last = {}, {}, {}, [], None
    for index, row in enumerate(rows):
        command, text, seq = row['command'], row['response'], row['sequence']
        if seq in (4, 5, 10):
            expected = {4: 'resourceget Speed', 5: 'resourceget WarpMode', 10: 'resourceget "WarpMode"'}[seq]
            assert command == expected
            assert ('ERROR -- Wrong syntax:' in text if seq != 10 else 'Unknown resource "WarpMode".' in text)
            rejected.append(dict(sequence=seq, command=command, response=text))
            continue
        assert not re.search(r'ERROR --|Unknown resource|Syntax error|[Mm]onitor observation failed', text)
        allowed = command in ('r', 'sidefx off', 'help resourceget', 'bank ram', 'x',
                              'resourceget "Speed"', 'resourceget "InitialWarpMode"')
        if command == 'r':
            last = wire.registers(text)
        if command == 'x':
            last = None
        match = re.fullmatch(r'trace exec ([0-9a-f]{4})', command)
        if match:
            response = re.search(r'TRACE: (\d+)  C:\$([0-9a-f]{4})  \(Trace exec\)', text)
            assert response
            checkpoint, pc = int(response[1]), response[2]
            assert pc == match[1] == points[checkpoint]['pc'] and checkpoint not in armed
            armed[checkpoint] = seq
            allowed = True
        match = re.fullmatch(r'command (\d+) "([^"\n]+)"', command)
        if match:
            checkpoint = int(match[1])
            assert checkpoint in armed and match[2] == points[checkpoint]['command']
            assert checkpoint not in attached and text.startswith(f'Setting checkpoint {checkpoint} command to: {match[2]}\n')
            attached[checkpoint] = seq
            allowed = True
        if re.fullmatch(r'break [0-9a-f]{4}', command):
            assert re.search(r'BREAK: \d+  C:\$' + command[6:] + r'  \(Stop on exec\)', text)
            allowed = True
        match = re.fullmatch(r'delete (\d+)', command)
        if match:
            # All deleted IDs are stops, not any of the still-armed plan IDs.
            assert int(match[1]) not in armed
            allowed = True
        match = re.fullmatch(r'(bsave|dump) "([^"\n]+)"( 0 0000 ffff)?', command)
        if match:
            kind, filename, suffix = match.groups()
            path = Path(filename)
            assert path.parent == CASE and last is not None and rows[index-1]['command'] == 'r'
            assert (kind == 'bsave') == (suffix is not None) and path.name not in contexts
            contexts[path.name] = dict(registers=last, sequence=seq)
            allowed = True
        assert allowed, ('Unclassified or mutating command', seq, command)
    assert set(armed) == set(points)
    assert set(attached) == {p['id'] for p in points.values() if p['kind'] == 'entry'}
    assert len(contexts) == 22
    for seq in (9, 148):
        assert case['responses'][seq]['response'].startswith('Speed=100\n')
    for seq in (18, 149):
        assert case['responses'][seq]['response'].startswith('InitialWarpMode=0\n')
    return contexts, armed, attached, dict(
        ordinary_commands=153, serialized_completed_commands=153, attached_read_only_entry_commands=len(attached),
        retained_read_only_query_errors=rejected, no_manual_CPU_RAM_or_register_writes=True,
        no_snapshot_restore=True, declared_PRG_autostart_mode1_loader_injection=True,
        runtime_Speed_100_queries=[9, 148], InitialWarpMode_zero_queries=[18, 149],
        current_runtime_warp_observed=False,
        limitation='Launch +warp/+autostart-warp disables warp. InitialWarpMode is a launch resource, not current warp; rejected WarpMode reads do not establish current mode.')


def captures(reader, contexts):
    result = {}
    for path in sorted(CASE.glob('*.vsf')):
        raw_path = path.with_suffix('.bin')
        regs = contexts[path.name]['registers']
        assert regs == contexts[raw_path.name]['registers']
        ram = raw_path.read_bytes()
        memory = reader.module_payload(path, 'C64MEM')
        assert len(ram) == 65536 and ram == memory[4:65540]
        assert (memory[1], memory[0]) == (regs['port00'], regs['port01'])
        cpu = reader.module_payload(path, 'MAINCPU')
        fields = dict(clock=int.from_bytes(cpu[:8], 'little'), a=cpu[8], x=cpu[9], y=cpu[10], sp=cpu[11],
                      pc=int.from_bytes(cpu[12:14], 'little'), flags=cpu[14])
        assert all(regs[k] == v for k, v in fields.items())
        state = reader.read_snapshot(path)
        assert (state['vicii']['raster_line'], state['vicii']['raster_cycle']) == (regs['line'], regs['cycle'])
        assert (regs['clock']//63 % 312, regs['clock'] % 63) == (regs['line'], regs['cycle'])
        result[path.stem] = dict(ram=ram, regs=regs, record=dict(
            stem=path.stem, RAM=artifact(raw_path), snapshot=artifact(path), registers=regs,
            paired_RAM_CPU_ports_clock_and_beam_equal=True, drawbuf=ram[11]))
    assert len(result) == 11
    program = PROGRAM.read_bytes()
    load_address = int.from_bytes(program[:2], 'little')
    assert result['start']['regs']['pc'] == 0x080d
    assert result['start']['ram'][load_address:load_address+len(program)-2] == program[2:]
    return result


def trace_events(case, sequences, points, armed, attached, initial_memory):
    events = []
    for sequence in sequences:
        response = case['responses'][sequence]
        assert response['command'] == 'x' and response['status'] == 'completed'
        text = response['response'].replace('\r\n', '\n')
        matches = list(TRACE.finditer(text))
        assert len(matches) == len(re.findall(r'^#\d+ \(Trace\s+exec ', text, re.M))
        for index, match in enumerate(matches):
            values = match.groupdict()
            checkpoint = int(values['id'])
            point = points[checkpoint]
            pc = int(values['pc'], 16)
            assert pc == int(values['target'], 16) == int(point['pc'], 16)
            assert armed[checkpoint] < sequence
            chunk = text[match.end():matches[index+1].start() if index+1 < len(matches) else len(text)]
            dumped = {}
            for line in MEMORY.finditer(chunk):
                address = int(line[1], 16)
                for offset, byte in enumerate(bytes.fromhex(line[2])):
                    assert address+offset not in dumped
                    dumped[address+offset] = byte
            if point['kind'] == 'entry':
                assert attached[checkpoint] < sequence and chunk.startswith('Executing: ' + point['command'] + '\n')
                expected = set(range(0x100, 0x200))
                if pc == 0xa000:
                    expected |= set(range(0x0b, 0x30)) | set(range(0xb43b, 0xb442))
                assert set(dumped) == expected
            else:
                assert not dumped and not chunk.startswith('Executing: ')
            raw = bytes.fromhex(values['bytes'])
            if pc == 0xa053:
                assert len(raw) == 3 and raw[0] == 0xb9
                assert int.from_bytes(raw[1:], 'little') in (0xb526, 0xb547, 0xb568, 0xb589)
            else:
                assert raw == initial_memory[pc:pc+len(raw)], (hex(pc), raw.hex())
            event = {name: int(values[name], 16 if name in ('pc', 'a', 'x', 'y', 'sp') else 10)
                     for name in ('pc', 'a', 'x', 'y', 'sp', 'line', 'cycle', 'clock')}
            assert (event['clock']//63 % 312, event['clock'] % 63) == (event['line'], event['cycle'])
            event.update(checkpoint=checkpoint, kind=point['kind'], name=point['name'],
                         response_sequence=sequence, machine_bytes=raw.hex(), dumped=dumped)
            events.append(event)
    assert events and all(a['clock'] < b['clock'] for a, b in zip(events, events[1:]))
    return events


def bayer_pattern(shade, row):
    ranks = ((0,8,2,10), (12,4,14,6), (3,11,1,9), (15,7,13,5))[row & 3]
    return sum((1 + (shade > rank) + (shade > rank+16)) << (6-2*x) for x, rank in enumerate(ranks))


def span_input(event, drawbuf):
    memory = event['dumped']
    x0, x1, delta, direction_raw, error, extent, shade0 = [memory[a] for a in range(0xb43b, 0xb442)]
    assert direction_raw in (1, 255)
    direction = 1 if direction_raw == 1 else -1
    shade1 = shade0 + direction*delta
    y, draw = memory[0x2f], memory[0x0b]
    assert 0 <= x0 <= x1 < 160 and 0 <= y < 100 and error == 0 and extent == x1-x0
    assert 0 <= shade0 <= 32 and 0 <= shade1 <= 32 and draw == drawbuf
    assert (memory[0x29], memory[0x2a]) == (x0, x1)
    row0 = memory[0x25] + 256*memory[0x26]
    row1 = memory[0x27] + 256*memory[0x28]
    base = 0x6000 if draw == 0 else 0x2000
    assert row0 == base + (y//4)*320 + 2*(y%4) and row1 == row0+1
    route = 'span_uniform_bulk' if extent >= 7 and bayer_pattern(shade0,y) == bayer_pattern(shade1,y) else 'span_general'
    prefix = min(4-x0%4, extent+1) if x0%4 else 0
    remaining = extent+1-prefix
    full = remaining//4
    partial = bool(prefix) + bool(remaining%4)
    return dict(clock=event['clock'], response_sequence=event['response_sequence'], y=y, x0=x0, x1=x1,
                delta=delta, direction=direction, error0=error, extent=extent, shade0=shade0, shade1=shade1,
                drawbuf=draw, row0=row0, row1=row1, expected_route=route,
                expected_general_full_bytes=full if route == 'span_general' else 0,
                expected_general_partial_bytes=partial if route == 'span_general' else 0,
                zero_page_dump=bytes(memory[a] for a in range(0x0b,0x30)).hex(),
                span_ABI_dump=bytes(memory[a] for a in range(0xb43b,0xb442)).hex())


def pair_frame(name, events, captured, anchors):
    begin, done = captured[name+'-begin'], captured[name+'-complete']
    first, last = begin['regs'], done['regs']
    assert first['pc'] == 0x08cb and last['pc'] == 0x08d4 and first['sp'] == last['sp']
    root = dict(index=0, name='render', pc=0x08cb, start=first['clock'], entry_sp=first['sp'],
                continuation=0x08d4, parent=None, children=[], expected_return_sp=first['sp'])
    nodes, active, span_rows, records, unmatched = [root], [root], [], [], Counter()
    direct = {}
    for row in anchors['selected_calls']:
        direct.setdefault(row['entry'], set()).add(row['continuation'])
    direct[0xac96] = {0x9226}
    direct[0x9455] = {0x4030}
    for event in events + [dict(kind='boundary', name='render_end', pc=last['pc'], sp=last['sp'], clock=last['clock'])]:
        assert first['clock'] < event['clock'] <= last['clock']
        compact = {k:v for k,v in event.items() if k != 'dumped'}
        if event['kind'] == 'entry':
            memory, sp, pc = event['dumped'], event['sp'], event['pc']
            stack = bytes(memory[a] for a in range(0x100,0x200))
            saved = memory[0x100+((sp+1)&255)] + 256*memory[0x100+((sp+2)&255)]
            continuation = (saved+1)&65535
            assert continuation in direct[pc], (event['name'], hex(continuation))
            node = dict(index=len(nodes), name=event['name'], pc=pc, start=event['clock'],
                        entry_sp=sp, continuation=continuation, expected_return_sp=(sp+2)&255,
                        parent=active[-1]['index'], children=[])
            if pc == 0x9455:
                assert active[-1]['name'] == 'draw_face'
                assert (sp, continuation) == (active[-1]['entry_sp'], active[-1]['continuation'])
                node['tail_entry'] = True
            else:
                # Lazy projection has one untraced load_face_visible JSR frame.
                expected_depth = 4 if pc == 0x9051 else 2
                assert sp == (active[-1]['entry_sp']-expected_depth)&255
                if pc == 0x9051:
                    assert active[-1]['name'] == 'collect_faces'
            active[-1]['children'].append(node['index'])
            nodes.append(node)
            active.append(node)
            compact.update(stacked_return_word=saved, continuation=continuation,
                           stack_page_sha256=sha(stack), node=node['index'])
            if pc == 0xa000:
                row = span_input(event, begin['ram'][11])
                row.update(frame=name, index=len(span_rows), node=node['index'], route_markers=[], full_byte_markers=0, partial_byte_markers=0)
                span_rows.append(row)
                node['span_index'] = row['index']
        elif event['kind'] == 'marker':
            assert active[-1]['name'] == 'shade_span'
            row = span_rows[active[-1]['span_index']]
            if event['name'] in ('span_general', 'span_uniform_bulk'):
                row['route_markers'].append(event['name'])
            elif event['name'] == 'full_byte':
                row['full_byte_markers'] += 1
                operand = int.from_bytes(bytes.fromhex(event['machine_bytes'])[1:], 'little')
                assert operand == (0xb526,0xb547,0xb568,0xb589)[row['y']&3]
            else:
                assert event['name'] == 'partial_byte'
                row['partial_byte_markers'] += 1
            compact['span_index'] = row['index']
        else:
            closed = []
            while active and (event['pc'], event['sp']) == (active[-1]['continuation'], active[-1]['expected_return_sp']):
                node = active.pop()
                node['end'] = event['clock']
                node['inclusive_cycles'] = node['end'] - node['start']
                assert node['inclusive_cycles'] > 0
                closed.append(node['index'])
            compact['closed_nodes'] = closed
            if not closed:
                unmatched[event['name']] += 1
        records.append(compact)
    assert not active, [(n['name'],hex(n['continuation'])) for n in active]
    assert len(nodes) > 1
    for row in span_rows:
        assert row['route_markers'] == [row['expected_route']]
        assert row['full_byte_markers'] == row['expected_general_full_bytes']
        assert row['partial_byte_markers'] == row['expected_general_partial_bytes']
    buckets, functions = Counter(), {}
    for node in nodes:
        children = [nodes[i] for i in node['children']]
        assert all(node['start'] <= c['start'] < c['end'] <= node['end'] for c in children)
        assert all(a['end'] <= b['start'] for a,b in zip(children,children[1:]))
        node['exclusive_cycles'] = node['inclusive_cycles'] - sum(c['inclusive_cycles'] for c in children)
        assert node['exclusive_cycles'] >= 0
        bucket = BUCKET.get(node['name'], 'other_setup_traversal_and_call_overhead')
        node['bucket'] = bucket
        buckets[bucket] += node['exclusive_cycles']
        stats = functions.setdefault(node['name'],dict(calls=0,inclusive_cycles=0,exclusive_cycles=0))
        stats['calls'] += 1
        stats['inclusive_cycles'] += node['inclusive_cycles']
        stats['exclusive_cycles'] += node['exclusive_cycles']
    total = last['clock']-first['clock']
    assert sum(buckets.values()) == total == root['inclusive_cycles']
    assert all(row['clock'] == nodes[row['node']]['start'] for row in span_rows)
    paths = Counter(row['expected_route'] for row in span_rows)
    summary = dict(frame=name, drawbuf=begin['ram'][11], begin_clock=first['clock'], end_clock=last['clock'],
                   render_elapsed_cycles=total, PAL_frame_cycles=19656, PAL_frame_equivalents=total/19656,
                   exclusive_buckets=dict(buckets), inclusive_functions=functions,
                   spans=len(span_rows), inclusive_logical_pixels=sum(r['extent']+1 for r in span_rows),
                   paths=dict(paths), general_full_byte_groups=sum(r['full_byte_markers'] for r in span_rows),
                   general_partial_byte_groups=sum(r['partial_byte_markers'] for r in span_rows),
                   unpaired_continuation_flow_hits=dict(unmatched),
                   all_entries_closed_by_actual_continuation_PC_and_SP=True,
                   normal_return_instruction_and_intervening_stalls_included=True)
    return summary, nodes, span_rows, records


def source_contract():
    archive = ROOT / 'build/research/quondam/hardware-source/vice-3.10.tar.gz'
    members = {
        'src/6510dtvcore.c': [('if (monitor_mask[CALLER] & (MI_BREAK))',437),
                              ('DO_INTERRUPT(pending_interrupt);',1763), ('SET_LAST_ADDR(reg_pc);',1792), ('FETCH_OPCODE(opcode);',1804)],
        'src/monitor/mon_breakpoint.c': [('mon_interfaces[mem]->get_line_cycle(&line, &cycle, &half_cycle);',573),
                                         ('mon_disassemble_with_regdump(mem, instpc);',596),
                                         ('parse_and_execute_line(cp->command);',602)],
        'src/monitor/mon_disassemble.c': [('void mon_disassemble_with_regdump(MEMSPACE mem, unsigned int addr)',1633)],
        'src/vsync.c': [('static int warp_enabled;',153), ('static int initial_warp_mode_resource;',156),
                        ('int vsync_get_warp_mode(void)',191)],
    }
    result = []
    with tarfile.open(archive) as tar:
        for member, references in members.items():
            raw = tar.extractfile('vice-3.10/'+member).read()
            lines = raw.decode().splitlines()
            for text, line in references:
                assert text in lines[line-1], (member,line)
            result.append(dict(member='vice-3.10/'+member, bytes=len(raw), sha256=sha(raw),
                               references=[dict(line=n,text=t) for t,n in references]))
    return dict(archive_sha256=PINS['build/research/quondam/hardware-source/vice-3.10.tar.gz'], members=result,
                interpretation='Exec checkpoints observe current PC/registers before its instruction fetch; printed raster/clock and attached memory dumps share the stopped instruction boundary. Runtime warp state and InitialWarpMode are separate.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=BASE / 'profile-analysis')
    args = parser.parse_args()
    out = args.output.resolve()
    inputs = []
    for rel,pin in PINS.items():
        item = artifact(ROOT/rel)
        assert item['sha256'] == pin, rel
        inputs.append(item)
    anchors = json.loads((BASE/'source-analysis/accepted-02/anchors.json').read_text())
    plan = json.loads((ROOT/'research/3dvibe64-profile/native-plan.json').read_text())
    wire,case,adaptation = wire_case()
    contexts,armed,attached,commands = command_audit(wire,case,plan)
    reader = load('profile_snapshot','research/quondam/snapshot_state.py')
    captured = captures(reader,contexts)
    memory = captured['start']['ram']
    points = {p['id']:p for p in plan['points']}
    summaries,intervals,spans,events = [],[],[],[]
    for name,sequences in FRAMES:
        parsed = trace_events(case,sequences,points,armed,attached,memory)
        summary,nodes,rows,records = pair_frame(name,parsed,captured,anchors)
        summaries.append(summary)
        intervals.append(dict(frame=name,nodes=nodes))
        spans.extend(rows)
        events.append(dict(frame=name,events=records))
    assert [r['render_elapsed_cycles'] for r in summaries] == [590499,543692,676134]
    assert [r['drawbuf'] for r in summaries] == [1,0,1]
    starts = [captured[name+'-begin']['regs']['clock'] for name in ('first','second','third','fourth')]
    periods = [b-a for a,b in zip(starts,starts[1:])]
    assert periods == [612884,549791,688964]
    assert all(summaries[i]['render_elapsed_cycles'] < periods[i] for i in range(3))
    out.mkdir(parents=True,exist_ok=False)
    outputs = []
    for filename,value in [('intervals.json',intervals),('span-records.json',spans),('trace-events.json',events)]:
        raw = (json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
        (out/filename).write_bytes(raw)
        outputs.append(dict(name=filename,bytes=len(raw),sha256=sha(raw)))
    proof = dict(pass_=True, scope='Three completed stock PAL Mode6 renders, exact elapsed emulated machine-clock partition; not retired CPU cycles, full-rotation performance or native pixel acceptance',
                 inputs=inputs,case_sha256=CASE_SHA,case_files=case['files'],wire_adaptation=adaptation,
                 command_audit=commands,source_contract=source_contract(),
                 captures=[v['record'] for v in captured.values()],frames=summaries,
                 begin_to_next_begin_cycles=periods,
                 post_render_to_next_begin_cycles=[p-s['render_elapsed_cycles'] for p,s in zip(periods,summaries)],
                 output_files=outputs,
                 limitations=[
                     'Entry-to-continuation includes normal RTS/VIC/IRQ time and excludes initiating JSR. Caller JSRs stay in the parent residual.',
                     'Exclusive buckets partition elapsed cycles exactly; inclusive helper totals overlap and are not additive.',
                     'XYQ2 interval begins after two wrapper JMPs; their elapsed cycles remain in draw_face residual.',
                     'Tail fill shares its caller return and SP; it and draw_face close on the same actual continuation.',
                     'Light intensity/setup, visibility, material loading and byte kernels retain their runtime costs even for this static light and single mesh.',
                     'IRQ time is included where it occurs; no separate IRQ-only timeline was captured, so no pure6510-only budget is claimed.',
                     'First two clears target initially clean buffers; third render reuses B and measures its dirty clear.',
                     'Speed=100 and InitialWarpMode=0 reads are retained. Actual current warp was not successfully queried; launch disables warp, and machine-clock differences do not establish wall-time FPS.',
                     'Span markers classify executed routes/groups; they do not reconstruct geometry or establish displayed pixels.',
                     'Only three poses/frames are measured. No best/worst/full-rotation or physical-hardware claim.',
                 ])
    raw = (json.dumps(proof,indent=2,sort_keys=True)+'\n').encode()
    (out/'profile-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=True,output=str(out.relative_to(ROOT)),proof_sha256=sha(raw),
                         frames=[dict(frame=r['frame'],cycles=r['render_elapsed_cycles'],spans=r['spans'],buckets=r['exclusive_buckets']) for r in summaries]),sort_keys=True))


if __name__ == '__main__':
    main()
