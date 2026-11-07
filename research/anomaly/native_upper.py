#!/usr/bin/env python3
"""Audit closed native-04 captures, upper-job traces and three floor fields.

Passive files only: no emulator, CPU model, process control or bus-phase claim.
The separate inspect_upper.py checker owns the upper-copy/publication model.
"""
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/anomaly'
CAPTURE = BASE / 'native-04'
OUTPUT = BASE / 'native-upper-analysis'
PARENT_SHA = 'dad0640279b4637d086e212e016cc92c0e0342461cd3bdb82759c54f7195c117'
RESTORE_SHA = 'db7c7cae5e97a0f0c90229fde26767d162ff3f2dd28f5d2d44e18147644a7449'
HELPERS = {
    'research/anomaly/native_arcade.py': '24b832b8582eca051edc39d8055e974991e8d4cedded2c05c749b89900970df2',
    'research/anomaly/native_capture.py': 'c3ed26e8948b018e3e1c1967cda5613058ce32c783f72447de5fc08543522b1e',
    'research/anomaly/inspect_arcade.py': 'c016696ab829fec52b9b10830af2b8111806cc629f734d40b3c7cbc5a392b978',
}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


arcade = load('upper_native_helpers', 'research/anomaly/native_arcade.py')
model = load('upper_source_helpers', 'research/anomaly/inspect_arcade.py')
native, boot = arcade.native, arcade.boot
artifact, sha = arcade.artifact, arcade.sha


def audit(text, restore_source):
    rows = arcade.commands(text)
    restores, resumes, tracepoints = [], [], []
    warp_off = speed_100 = False
    gate = 'break exec $36e6 if (((A - @ram:$36e7) & $80) != $00) && (@ram:$0007 != $00)'
    execution_addresses = {0x36f3, 0x38bb, 0x39b1, 0x39ca, 0x3d89,
                           0xb84b, 0xb864, 0xb400, 0xb828}
    for row in rows:
        command, response = row['command'], '\n'.join(row['response']).strip()
        safe = (command in ('r', 'sidefx off', 'bank ram', 'break', 'x')
                or re.fullmatch(r'(?:delete|enable|disable) [0-9]+', command)
                or re.fullmatch(r'bsave "[^"\n]+" 0 0000 ffff', command)
                or re.fullmatch(r'dump "[^"\n]+"', command)
                or re.fullmatch(r'screenshot "[^"\n]+" 2', command))
        if command.startswith('undump '):
            assert command == f'undump "{restore_source}"'
            restores.append(row)
            safe = True
        elif command == 'warp':
            assert response == 'Warp mode is off.'
            warp_off, safe = True, True
        elif command == 'resourceget "Speed"':
            assert response == 'Speed=100'
            speed_100, safe = True, True
        elif command.startswith('break exec '):
            match = re.fullmatch(r'break exec \$([0-9a-f]{4})', command)
            assert command == gate or match and int(match[1], 16) in execution_addresses
            safe = True
        elif command.startswith('trace '):
            assert command in ('trace exec $36f3', 'trace exec $38bb',
                               'trace exec $39b1', 'trace exec $39ca', 'trace store $d016')
            tracepoints.append(row)
            safe = True
        assert safe, ('Unclassified command', row)
        assert 'ERROR --' not in response and 'Unknown resource' not in response
        if command == 'x':
            assert warp_off and speed_100, 'Resume before normal-speed observations.'
            resumes.append(row['line'])
    assert len(restores) == 1
    assert [row['command'] for row in tracepoints] == [
        'trace exec $36f3', 'trace exec $38bb', 'trace exec $39b1',
        'trace exec $39ca', 'trace store $d016']
    assert not native.interventions('\n'.join(row['command'] for row in rows if row not in restores))
    assert '[Monitor observation failed:' not in text
    return dict(commands=rows, counts=dict(Counter(row['command'].split()[0] for row in rows)),
                restore=restores[0], tracepoints=tracepoints, normal_speed_resume_lines=resumes,
                inputs=[], RAM_or_code_writes=[], register_or_PC_writes=[], resource_writes=[],
                scope='Recorded monitor operations, not an external audit of all host activity.')


def expected_captures():
    result = {'restored-arcade': 0x3d89, 'gate-pixel-pre': 0x36e6}
    for number in range(1, 29):
        stem = 'pixel-row' if number == 1 else f'job-{number:02d}'
        pc = 0x36f3 if number <= 13 else 0x38bb if number <= 26 else 0x39b1 if number == 27 else 0x39ca
        result[stem + '-pre'], result[stem + '-post'] = pc, 0x3d89
    result.update({'publication-pre': 0xb84b, 'publication-post': 0xb864,
                   'field-pre': 0xb400, 'field-post': 0xb828,
                   'field-02-pre': 0xb400, 'field-02-post': 0xb828,
                   'field-03-pre': 0xb400, 'field-03-post': 0xb828,
                   'field-04-pre': 0xb400})
    return result


def main():
    for path, expected in HELPERS.items():
        assert sha((ROOT / path).read_bytes()) == expected, ('Helper drift', path)
    for path, expected in boot.HELPER_PINS.items():
        assert sha((ROOT / path).read_bytes()) == expected, ('Nested helper drift', path)
    session_path, text_path = CAPTURE / 'session.json', CAPTURE / 'monitor.log'
    session, text = json.loads(session_path.read_text()), text_path.read_text()
    assert session.get('closed_utc') and session['exit_code'] == -15
    assert session['startup_mode'] == 'manual monitor load'
    command = session['command']
    assert '-autostart' not in command and '-pal' in command and '+warp' in command
    assert command[command.index('-speed') + 1] == '100'
    assert command[command.index('-8') + 1] == session['program']
    assert sha(Path(session['program']).read_bytes()) == boot.DISK_SHA
    parent_path = BASE / 'native-arcade-analysis/native-arcade-evidence.json'
    assert sha(parent_path.read_bytes()) == PARENT_SHA
    parent = json.loads(parent_path.read_text())
    assert parent['pass'] is True
    inherited = next(row for row in parent['checkpoints'] if row['stem'] == 'upper-rejected-post')
    restore_source = ROOT / inherited['snapshot']['path']
    assert artifact(restore_source) == inherited['snapshot'] and sha(restore_source.read_bytes()) == RESTORE_SHA
    assert artifact(ROOT / inherited['ram']['path']) == inherited['ram']
    observation = audit(text, restore_source)
    events = native.contexts(text)
    by_name, snapshots = {}, {}
    for event in events:
        assert event['filename'] not in by_name
        by_name[event['filename']] = event
        if event['command'] != 'dump':
            continue
        path = CAPTURE / event['filename']
        state, cpu = native.read_snapshot(path), native.cpu_state(path)
        assert all(cpu[key] == event['registers'][key] for key in cpu)
        assert [state['vicii']['raster_line'], state['vicii']['raster_cycle']] == [
            event['registers']['raster_line'], event['registers']['raster_cycle']]
        snapshots[path.stem] = (path, state)
    records, images = [], []
    for event in events:
        path = CAPTURE / event['filename']
        if event['command'] == 'bsave':
            assert event['bank'] == 'ram' and (event['first'], event['end_inclusive']) == (0, 65535)
            assert path.name.startswith('ram-')
            stem = path.stem[4:]
            snapshot, _ = snapshots[stem]
            assert by_name[snapshot.name]['registers'] == event['registers']
            data = path.read_bytes()
            assert len(data) == 65536 and data == native.physical_ram(snapshot)
            records.append(dict(stem=stem, ram=artifact(path), snapshot=artifact(snapshot),
                                registers=event['registers'], transcript_line=event['transcript_line']))
        elif event['command'] == 'screenshot':
            snapshot, _ = snapshots[path.stem]
            assert by_name[snapshot.name]['registers'] == event['registers']
            with Image.open(path) as image:
                image.load()
                dimensions = list(image.size)
            images.append(dict(**artifact(path), dimensions=dimensions, snapshot=artifact(snapshot),
                               scope='Output observation; no independent complete-field pixel comparison here.'))
    named = {row['stem']: row for row in records}
    expected = expected_captures()
    assert len(records) == len(expected) == 67 and set(named) == set(snapshots) == set(expected)
    assert {p.stem[4:] for p in CAPTURE.glob('ram-*.bin')} == set(expected)
    assert {p.stem for p in CAPTURE.glob('*.vsf')} == set(expected)
    assert {p.stem for p in CAPTURE.glob('*.png')} == {'publication-pre', 'publication-post', 'field-post'}
    assert len(images) == 3
    assert all(named[stem]['registers']['pc'] == pc for stem, pc in expected.items())
    assert all(a['registers']['clock'] < b['registers']['clock'] for a, b in zip(records, records[1:]))
    restored = named['restored-arcade']
    assert (ROOT / restored['ram']['path']).read_bytes() == (ROOT / inherited['ram']['path']).read_bytes()
    assert restored['registers'] == inherited['registers']
    assert native.module_payload(ROOT / restored['snapshot']['path'], 'MAINCPU') == native.module_payload(restore_source, 'MAINCPU')
    first_ram = (ROOT / named['gate-pixel-pre']['ram']['path']).read_bytes()
    assert ((named['gate-pixel-pre']['registers']['a'] - first_ram[0x36e7]) & 0x80) and first_ram[7]
    assert first_ram == (ROOT / named['pixel-row-pre']['ram']['path']).read_bytes()
    traces = model.traces(text)
    publication_clock = named['publication-pre']['registers']['clock']
    jobs = [row for row in traces if row['kind'] == 'exec' and row['clock'] < publication_clock]
    entries = [named[('pixel-row' if n == 1 else f'job-{n:02d}') + '-pre']['registers'] for n in range(1, 29)]
    assert len(jobs) == 28
    assert all((row['pc'], row['clock']) == (pre['pc'], pre['clock']) for row, pre in zip(jobs, entries))
    assert Counter(row['pc'] for row in jobs) == {0x36f3: 13, 0x38bb: 13, 0x39b1: 1, 0x39ca: 1}
    source, _, _, source_pin = model.original()
    schedule = model.D016_schedule(source)
    fields = []
    for n in range(1, 4):
        stem = 'field' if n == 1 else f'field-{n:02d}'
        pre, post = named[stem + '-pre'], named[stem + '-post']
        memory = (ROOT / pre['ram']['path']).read_bytes()
        rows = [row for row in traces if row['kind'] == 'store' and pre['registers']['clock'] <= row['clock'] < post['registers']['clock']]
        assert len(rows) == 96
        for row, planned in zip(rows, schedule):
            assert row['target'] == 0xd016 and row['pc'] == planned['pc']
            assert memory[row['pc']:row['pc'] + 3] == source[row['pc']:row['pc'] + 3] == bytes.fromhex('8d 16 d0')
            assert row['x'] == planned['line'] and row['a'] == memory[planned['table_address']]
        deltas = [b['clock'] - a['clock'] for a, b in zip(rows, rows[1:])]
        assert all(delta > 0 for delta in deltas)
        assert [row['line'] for row in rows] == list(range(155, 251))
        if fields:
            previous = fields[-1]['writes']
            assert [row['clock'] - old['clock'] for row, old in zip(rows, previous)] == [19656] * 96
            assert [(row['line'], row['cycle']) for row in rows] == [(row['line'], row['cycle']) for row in previous]
        fields.append(dict(number=n, pre=pre['stem'], post=post['stem'], writes=rows,
                           observer_clock_deltas=deltas, observer_delta_histogram=dict(Counter(deltas)),
                           sampled_values_match_prestate=True))
    stores = [row for row in traces if row['kind'] == 'store']
    floor_clocks = {row['clock'] for field in fields for row in field['writes']}
    upper_stores = [row for row in stores if row['clock'] not in floor_clocks]
    assert len(stores) == 291 and len(upper_stores) == 3 and all(row['pc'] == 0xb857 for row in upper_stores)
    boundaries = [named[stem]['registers'] for stem in ('field-pre', 'field-02-pre', 'field-03-pre', 'field-04-pre')]
    boundary_deltas = [b['clock'] - a['clock'] for a, b in zip(boundaries, boundaries[1:])]
    assert boundary_deltas == [19656, 19659, 19656]
    result = dict(status='complete', pass_=True, script=artifact(Path(__file__).resolve()),
                  session=session, session_metadata=artifact(session_path), transcript=artifact(text_path),
                  parent=artifact(parent_path), helpers=HELPERS, nested_helpers=boot.HELPER_PINS,
                  original_source_proof=source_pin, configured_disk=artifact(Path(session['program'])),
                  observation_audit=observation, restore=dict(source=inherited, all_RAM_equal=True,
                  complete_MAINCPU_payload_equal=True, registers_ports_beam_equal=True),
                  checkpoints=records, RAM_snapshot_bytes=65536 * len(records), screenshots=images,
                  jobs_before_first_publication=jobs, additional_job_traces_after_publication=[row for row in traces if row['kind'] == 'exec' and row['clock'] >= publication_clock],
                  floor_fields=fields, separate_upper_D016_stores=upper_stores,
                  consecutive_B400_boundaries=boundaries, boundary_clock_deltas=boundary_deltas,
                  scope='Closed capture/provenance, 28-job entry trace and three 96-write observer sequences. Upper RAM/publication modelling is separate.',
                  limits=['No whole-demo FPS, renderer worst-case deadline, sound or independent full-field pixel proof.',
                          'Monitor store trace clocks/cycles are observer coordinates, not certified physical bus phases.',
                          'B400 entry jitter differs from the exactly repeated field trace vector; within-field observer deltas are not uniformly63 clocks.'],
                  rejected_assumption=artifact(OUTPUT / 'rejected-all63-assumption.json'))
    result['pass'] = result.pop('pass_')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'native-upper-evidence.json').write_text(json.dumps(result, indent=2) + '\n')
    (OUTPUT / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(passed=True, RAM_pairs=len(records), bytes=result['RAM_snapshot_bytes'],
                          jobs=len(jobs), floor_fields=len(fields), floor_stores=288,
                          boundary_clock_deltas=boundary_deltas), indent=2))


if __name__ == '__main__':
    main()
