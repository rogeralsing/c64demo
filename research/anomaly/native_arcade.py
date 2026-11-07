#!/usr/bin/env python3
"""Passively check the closed, bounded native-03 Arcade continuation.

No CPU, emulator, process or source runtime model executes. Original native
state, explicit warp transit and the closed observation scope stay distinct.
"""
import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/anomaly'
PARENT_SHA = '25d9ef6cac9705f37999ab70af2b423dbdeff901e2192c1095a9e873272d9714'
RUNTIME_SHA = '17ed1c6adafb0b33f0a0ca0b9830bfcfa5ff913818a8ad4bd18bcd5c53f7b2fb'
RUNTIME_FILE = 'runtime-analysis/runtime-proof.json'
BOOT_HELPER = ROOT / 'research/anomaly/native_capture.py'
spec = importlib.util.spec_from_file_location('arcade_boot_helpers', BOOT_HELPER)
boot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boot)
native, sha, relative, artifact = boot.native, boot.sha, boot.relative, boot.artifact
EXPECTED = {
    'restored-humanmade': 0x2d00, 'arcade-load-call': 0x08ae,
    'arcade-load-return': 0x08b1, 'arcade-entry': 0x3b00, 'arcade-ready': 0x3b88,
    'floor-a-pre': 0x3d83, 'floor-a-post': 0x3d86,
    'floor-b-pre': 0x3d83, 'floor-b-post': 0x3d86,
    'upper-gate-rejected': 0x36e6, 'upper-rejected-post': 0x3d89,
}
EXPECTED_IMAGES = {'arcade-ready', 'upper-rejected-post'}


def commands(text):
    """Retain each command and response; help/error echoes are response text."""
    result, current, ready = [], None, True
    for number, line in enumerate(text.splitlines(), 1):
        value = line.strip()
        if re.fullmatch(r'\(C:\$[0-9a-f]{4}\)', value, re.I):
            ready, current = True, None
        elif ready and value:
            current = dict(line=number, command=value, response=[])
            result.append(current)
            ready = False
        elif current is not None:
            current['response'].append(line)
    return result


def checkpoint(command):
    if re.fullmatch(r'break [0-9a-f]{1,4}', command, re.I): return True
    if re.fullmatch(r'break exec \$[0-9a-f]{4}', command, re.I): return True
    match = re.fullmatch(r'break exec \$[0-9a-f]{4} if (.+)', command, re.I)
    return bool(match and all(re.fullmatch(r'\(@ram:\$[0-9a-f]{4} == \$[0-9a-f]{2}\)',
                                          term.strip(), re.I) for term in match[1].split('&&')))


def audit(text, restore_source):
    rows = commands(text)
    restores, warp_changes, warp_queries, failed_queries, resumes, traces = [], [], [], [], [], []
    mode = None
    for row in rows:
        command, response = row['command'], '\n'.join(row['response'])
        safe = (command in ('r', 'sidefx off', 'bank ram', 'x') or checkpoint(command)
                or re.fullmatch(r'delete [0-9a-f]{1,4}', command, re.I)
                or re.fullmatch(r'bsave "[^"\n]+" 0 0000 ffff', command)
                or re.fullmatch(r'dump "[^"\n]+"', command)
                or re.fullmatch(r'screenshot "[^"\n]+" 2', command))
        if command.startswith('undump '):
            match = re.fullmatch(r'undump "([^"\n]+)"', command)
            assert match and Path(match[1]).resolve() == restore_source.resolve(), row
            restores.append(row); safe = True
        elif command.startswith('help '):
            assert command in ('help resourceset', 'help resourceget', 'help warp'), row
            safe = True
        elif command.startswith('resourceget '):
            if command == 'resourceget "WarpMode"':
                assert response.strip() == 'Unknown resource "WarpMode".'
                failed_queries.append(dict(**row, kind='Unknown resource; read-only query.'))
            elif command == 'resourceget WarpMode':
                assert 'ERROR -- Wrong syntax:' in response and 'resourceget WarpMode' in response
                failed_queries.append(dict(**row, kind='Wrong syntax; read-only query.'))
            elif command == 'resourceget "Speed"':
                assert response.strip() == 'Speed=100'
            elif command == 'resourceget "SoundEmulateOnWarp"':
                assert response.strip() == 'SoundEmulateOnWarp=1'
            else:
                raise AssertionError(('Unclassified resource query', row))
            safe = True
        elif command in ('warp on', 'warp off'):
            mode = command.split()[1]
            warp_changes.append(row); safe = True
        elif command == 'warp':
            assert response.strip() in ('Warp mode is on.', 'Warp mode is off.'), row
            queried = 'on' if response.strip() == 'Warp mode is on.' else 'off'
            assert mode is None or mode == queried, ('Warp command/query disagreement', row)
            mode = queried
            warp_queries.append(dict(**row, observed_mode=mode)); safe = True
        elif command.startswith('trace '):
            match = re.fullmatch(r'trace exec \$([0-9a-f]{4})', command, re.I)
            assert match, ('Only the four recorded job-entry tracepoints belong to this batch', row)
            traces.append(dict(**row, target=int(match[1], 16))); safe = True
        assert safe, ('Unclassified monitor operation', row)
        if command == 'x':
            assert mode in ('off', 'on'), 'Resume without an observed warp state.'
            resumes.append(dict(line=row['line'], warp_mode=mode))
    assert len(restores) == 1
    assert [r['command'] for r in warp_changes] == ['warp on', 'warp off']
    assert [r['observed_mode'] for r in warp_queries] == ['off', 'on', 'off']
    assert len(failed_queries) == 2
    assert [r['command'] for r in rows if r['command'].startswith('resourceget ')] == [
        'resourceget "WarpMode"', 'resourceget WarpMode', 'resourceget "Speed"', 'resourceget "SoundEmulateOnWarp"']
    assert len([r for r in resumes if r['warp_mode'] == 'on']) == 1
    assert all(r['warp_mode'] == 'off' for r in resumes[1:])
    assert [r['target'] for r in traces] == [0x36f3, 0x38bb, 0x39b1, 0x39ca]
    trace_hits = [dict(line=i, text=line) for i, line in enumerate(text.splitlines(), 1)
                  if re.match(r'^#\d+ \(Trace\s+', line)]
    assert not trace_hits, 'This bounded batch has no observed job-entry trace hit.'
    assert '[Monitor observation failed:' not in text
    # Use the shared write checker after removing only the approved restore.
    assert native.interventions('\n'.join(r['command'] for r in rows if r not in restores)) == []
    return dict(commands=rows, counts=dict(Counter(r['command'].split()[0] for r in rows)),
                approved_restore=restores[0], warp_changes=warp_changes, warp_queries=warp_queries,
                resume_modes=resumes, failed_read_only_queries=failed_queries,
                job_tracepoints=traces, actual_job_trace_hits=trace_hits, D016_store_trace_captured=False,
                inputs=[], RAM_or_code_writes=[], register_or_PC_writes=[], resource_writes=[],
                rejected_capture_observations=[],
                trace_limits='Installed exec tracepoints and zero recorded hits are bounded to this archived interval. Monitor trace clocks, if present in a later batch, are observer timestamps, not automatically physical write-bus phases.',
                scope='Archived monitor command audit; the explicit warp transit is an intervention and is not hidden among read-only observations.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, default=BASE / 'native-03')
    parser.add_argument('--output', type=Path, default=BASE / 'native-arcade-analysis')
    args = parser.parse_args()
    directory, output = args.capture.resolve(), args.output.resolve()
    session_path = directory / 'session.json'
    session = json.loads(session_path.read_text())
    assert session.get('closed_utc') and session.get('exit_code') == -15, 'Final proof requires the owner-closed batch.'
    parent_path = BASE / 'native-analysis/native-evidence.json'
    assert sha(parent_path.read_bytes()) == PARENT_SHA
    parent = json.loads(parent_path.read_text())
    assert parent['pass'] is True and parent['status'] == 'complete'
    assert artifact(BOOT_HELPER) == parent['script']
    for path, expected in parent['helpers'].items(): assert sha((ROOT / path).read_bytes()) == expected
    inherited = next(row for row in parent['checkpoints'] if row['stem'] == 'humanmade-entry')
    restore_source = ROOT / inherited['snapshot']['path']
    assert artifact(restore_source) == inherited['snapshot']
    assert artifact(ROOT / inherited['ram']['path']) == inherited['ram']
    assert sha(Path(session['program']).read_bytes()) == parent['configured_disk']['sha256']
    text_path = directory / 'monitor.log'
    text = text_path.read_text(errors='strict')
    observation = audit(text, restore_source)
    events, by_name, snapshots = native.contexts(text), {}, {}
    for event in events:
        assert event['filename'] not in by_name
        by_name[event['filename']] = event
        if event['command'] != 'dump': continue
        path = directory / event['filename']
        state, cpu = native.read_snapshot(path), native.cpu_state(path)
        assert all(cpu[k] == event['registers'][k] for k in cpu), ('Snapshot CPU/clock versus transcript', path)
        assert [state['vicii']['raster_line'], state['vicii']['raster_cycle']] == [
            event['registers']['raster_line'], event['registers']['raster_cycle']], ('Snapshot beam versus transcript', path)
        snapshots[path.stem] = (path, state)
    records, images = [], []
    for event in events:
        if event['command'] != 'bsave': continue
        assert event['bank'] == 'ram' and (event['first'], event['end_inclusive']) == (0, 65535)
        path = directory / event['filename']
        assert path.name.startswith('ram-')
        stem = path.stem[4:]
        snapshot, _ = snapshots[stem]
        assert by_name[snapshot.name]['registers'] == event['registers']
        data = path.read_bytes(); assert len(data) == 65536
        check = native.comparison(data, native.physical_ram(snapshot), 0, 65536,
                                  'All physical RAM bytes versus the same-stop snapshot')
        records.append(dict(stem=stem, ram=artifact(path), snapshot=artifact(snapshot),
                            registers=event['registers'], transcript_line=event['transcript_line'], check=check, exact=check['exact']))
    for event in events:
        if event['command'] != 'screenshot': continue
        path = directory / event['filename']; snapshot, _ = snapshots[path.stem]
        assert by_name[snapshot.name]['registers'] == event['registers']
        with Image.open(path) as image:
            image.load(); dimensions = list(image.size)
        images.append(dict(**artifact(path), dimensions=dimensions, registers=event['registers'],
                           snapshot=relative(snapshot), scope='Original output observation, not an independently reconstructed complete field.'))
    named = {r['stem']: r for r in records}
    assert len(records) == len(EXPECTED) and set(named) == set(snapshots) == set(EXPECTED)
    assert {p.stem[4:] for p in directory.glob('ram-*.bin')} == set(EXPECTED)
    assert {p.stem for p in directory.glob('*.vsf')} == set(EXPECTED)
    assert len(images) == 2 and {Path(r['path']).stem for r in images} == EXPECTED_IMAGES
    assert {p.stem for p in directory.glob('*.png')} == EXPECTED_IMAGES
    for stem, pc in EXPECTED.items(): assert named[stem]['registers']['pc'] == pc, stem
    assert all(a['registers']['clock'] < b['registers']['clock'] for a, b in zip(records, records[1:]))
    restored = named['restored-humanmade']
    restore_check = native.comparison((ROOT / restored['ram']['path']).read_bytes(), (ROOT / inherited['ram']['path']).read_bytes(),
                                     0, 65536, 'Every restored RAM byte versus the parent HumanMade entry')
    assert restored['registers'] == inherited['registers']
    cpu_equal = native.module_payload(ROOT / restored['snapshot']['path'], 'MAINCPU') == native.module_payload(restore_source, 'MAINCPU')
    assert cpu_equal
    warp_off_line = observation['warp_changes'][-1]['line']
    assert warp_off_line < named['arcade-load-call']['transcript_line']
    assert all(r['line'] < named['arcade-load-call']['transcript_line'] for r in observation['warp_changes'])
    assert all(named['arcade-ready']['transcript_line'] < r['line'] < named['floor-a-pre']['transcript_line']
               for r in observation['job_tracepoints'])
    assert not any(r['command'] == 'x' and named['arcade-ready']['transcript_line'] < r['line'] < observation['job_tracepoints'][-1]['line']
                   for r in observation['commands'])
    runtime_path = BASE / RUNTIME_FILE
    assert sha(runtime_path.read_bytes()) == RUNTIME_SHA
    runtime = json.loads(runtime_path.read_text())
    assert runtime['pass'] is True
    assert runtime['session'] == artifact(session_path) and runtime['session_closed_utc'] == session['closed_utc']
    assert runtime['runtime_witness_complete'] is False
    assert len(runtime['checks']) == 20 and all(row['exact'] for row in runtime['checks'])
    assert runtime['upper_job_trace']['window_first_clock'] == named['arcade-ready']['registers']['clock']
    assert runtime['upper_job_trace']['window_last_clock'] == named['upper-rejected-post']['registers']['clock']
    assert runtime['upper_job_trace']['observed_hits'] == observation['actual_job_trace_hits'] == []
    boot.verify_artifacts(runtime)
    captures = runtime['captures']
    assert {r['name'] for r in captures} == set(named)
    for capture in captures:
        row = named[capture['name']]
        assert row['ram'] == capture['ram'] and row['snapshot'] == capture['snapshot']
        assert all(row['registers'][k] == v for k, v in capture['registers'].items())
    passed = restore_check['exact'] and cpu_equal and all(r['exact'] for r in records)
    result = dict(status='complete', script=artifact(Path(__file__).resolve()), session=session,
        session_metadata=artifact(session_path), transcript=artifact(text_path), parent=artifact(parent_path),
        helper=artifact(BOOT_HELPER), helper_dependencies=parent['helpers'], configured_disk=parent['configured_disk'],
        observation_audit=observation,
        job_trace_window=dict(first_clock=named['arcade-ready']['registers']['clock'],
                              last_clock=named['upper-rejected-post']['registers']['clock'],
                              scope='Four job entry traces installed at the paused ready state, through the final captured rejected return only.'),
        restore=dict(source=inherited, check=restore_check, complete_MAINCPU_payload_equal=cpu_equal,
                     recorded_registers_ports_beam_equal=True, scope='One explicit snapshot continuation, not a new cold boot.'),
        warp_transit=dict(first_clock=restored['registers']['clock'], last_clock=named['arcade-load-call']['registers']['clock'],
                         exit_PC=0x08ae, runtime_warp_off_before_capture=True, Speed_query=100, SoundEmulateOnWarp_query=1),
        checkpoints=records, RAM_snapshot_bytes=65536 * len(records), screenshots=images,
        source_runtime_proof=artifact(runtime_path), source_runtime_capture_identities_joined=len(captures),
        source_runtime_status=runtime['status'], source_runtime_scope=runtime['scope'],
        source_runtime_checks=runtime['checks'], runtime_witness_complete=False,
        not_observed=runtime['not_observed'],
        limits=['No CPU or loader runtime model is executed by this checker.',
                'Runtime capture begins only after warp is disabled at the guarded original loader call.',
                'The captured rejected upper gate and zero recorded job-entry hits do not establish an accepted job, completed publication or a full render deadline.',
                'No D016 store trace, independently reconstructed complete field, sound or FPS proof belongs to this batch.'])
    result['pass'] = passed
    output.mkdir(parents=True, exist_ok=True)
    path = output / 'native-arcade-evidence.json'; path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(passed=passed, RAM_snapshot_pairs=len(records), screenshots=len(images), receipt=relative(path)), indent=2))
    assert passed, 'RAM/restore comparison failed; differences retained.'


if __name__ == '__main__':
    main()
