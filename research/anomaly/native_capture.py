#!/usr/bin/env python3
"""Passively validate Anomaly's closed original-disk boot capture batch.

No emulator, CPU interpreter, disk decoder, downloaded code or process runs.
The closed setup-only first attempt is separate from native-02 boot evidence.
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
DISK_SHA = 'd452497845598cca8936fdf57c60fdc9c70cd7e64110e049fa6fc7d735f940cd'
BINARY_SHA = 'b8744b0184128330a069a7366c4f843193306074f4a55a03d10f092a6fa8800c'
JOIN_SHA = 'a6d48ec5123ca1ee9f621dfc52de8317a75e362feb0d8019384e6da21ec504e5'
HELPER_PINS = {
    'research/second-reality/native_capture.py': 'a3b80b719e3d38bd983a192d14bbf3dbdd16ac5fa76edf3c12cac33d32e755f2',
    'research/nine/native_capture.py': 'eeed7d330086c456ecc1e4b5071e8b474fc5b8a61ddc45f7a4e978983451e546',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
}
spec = importlib.util.spec_from_file_location('anomaly_native_helpers', ROOT / next(iter(HELPER_PINS)))
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
sha, relative = native.sha, native.relative
EXPECTED = {
    'boot-entry': 0x0810, 'resident-copied': 0x08b5, 'first-return': 0xff40,
    'entry-fade-return': 0xff40, 'base-music-return': 0xff54,
    'fade-assets-return': 0xff63, 'fade-call-return': 0xff66, 'humanmade-entry': 0x2d00,
}
IMAGES = {'first-return', 'entry-fade-return', 'fade-assets-return', 'fade-call-return', 'humanmade-entry'}


def artifact(path):
    data = path.read_bytes()
    return dict(path=relative(path), bytes=len(data), sha256=sha(data))


def audit(text, setup_only=False):
    commands, ready = [], True
    for number, line in enumerate(text.splitlines(), 1):
        value = line.strip()
        if re.fullmatch(r'\(C:\$[0-9a-f]{4}\)', value, re.I):
            ready = True
        elif ready and value:
            commands.append(dict(line=number, command=value))
            ready = False
    for row in commands:
        command = row['command']
        safe = command in ('r', 'sidefx off')
        if not setup_only:
            safe = safe or (
                command in ('bank ram', 'x')
                or re.fullmatch(r'(?:break|delete) [0-9a-f]{1,4}', command, re.I)
                or re.fullmatch(r'bsave "[^"\n]+" 0 0000 ffff', command)
                or re.fullmatch(r'dump "[^"\n]+"', command)
                or re.fullmatch(r'screenshot "[^"\n]+" 2', command)
            )
        assert safe, ('Unclassified monitor command', row)
    assert not native.interventions('\n'.join(row['command'] for row in commands))
    assert '[Monitor observation failed:' not in text
    return dict(commands=commands, counts=dict(Counter(row['command'].split()[0] for row in commands)),
                inputs=[], snapshot_restores=[], RAM_or_code_writes=[], register_or_PC_writes=[],
                resource_or_speed_changes=[], rejected_observations=[],
                scope='Archived monitor commands only; no external host-activity or keyboard-hardware audit.')


def verify_artifacts(value):
    if isinstance(value, dict):
        if isinstance(value.get('path'), str) and 'sha256' in value:
            actual = artifact(ROOT / value['path'])
            assert all(actual[k] == value[k] for k in ('path', 'bytes', 'sha256')), ('Pinned artifact drift', value['path'])
        for item in value.values(): verify_artifacts(item)
    elif isinstance(value, list):
        for item in value: verify_artifacts(item)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, default=BASE / 'native-02')
    parser.add_argument('--output', type=Path, default=BASE / 'native-analysis')
    args = parser.parse_args()
    directory, output = args.capture.resolve(), args.output.resolve()
    for path, expected_sha in HELPER_PINS.items():
        assert sha((ROOT / path).read_bytes()) == expected_sha, ('Helper drift', path)
    session_path = directory / 'session.json'
    session = json.loads(session_path.read_text())
    assert session.get('closed_utc') and session.get('exit_code') == -15
    assert session['startup_mode'] == 'autostart'
    command = session['command']
    assert '-autostart' in command and command[command.index('-autostart') + 1] == session['program']
    assert '-pal' in command and command[command.index('-speed') + 1] == '100' and '+warp' in command
    assert command[command.index('-sounddev') + 1] == 'dummy'
    assert sha(Path(session['program']).read_bytes()) == DISK_SHA
    transcript_path = directory / 'monitor.log'
    text = transcript_path.read_text(errors='strict')
    command_audit = audit(text)
    events, by_name, snapshots = native.contexts(text), {}, {}
    for event in events:
        assert event['filename'] not in by_name, ('Capture filename reused', event['filename'])
        by_name[event['filename']] = event
    for event in events:
        if event['command'] != 'dump': continue
        path = directory / event['filename']
        state, cpu = native.read_snapshot(path), native.cpu_state(path)
        assert all(cpu[k] == event['registers'][k] for k in cpu), ('CPU/clock versus transcript', path)
        assert [state['vicii']['raster_line'], state['vicii']['raster_cycle']] == [
            event['registers']['raster_line'], event['registers']['raster_cycle']], ('Beam versus transcript', path)
        snapshots[path.stem] = (path, state)
    records, images = [], []
    for event in events:
        if event['command'] != 'bsave': continue
        assert event['bank'] == 'ram' and (event['first'], event['end_inclusive']) == (0, 65535)
        path = directory / event['filename']
        assert path.name.startswith('ram-')
        stem = path.stem[4:]
        snapshot, state = snapshots[stem]
        assert by_name[snapshot.name]['registers'] == event['registers']
        actual = path.read_bytes()
        assert len(actual) == 65536
        check = native.comparison(actual, native.physical_ram(snapshot), 0, 65536,
                                  'All physical RAM bytes versus the same-stop snapshot')
        records.append(dict(stem=stem, ram=artifact(path), snapshot=artifact(snapshot),
                            registers=event['registers'], transcript_line=event['transcript_line'],
                            check=check, exact=check['exact']))
    for event in events:
        if event['command'] != 'screenshot': continue
        path = directory / event['filename']
        snapshot, _ = snapshots[path.stem]
        assert by_name[snapshot.name]['registers'] == event['registers']
        with Image.open(path) as image:
            image.load(); size = list(image.size)
        images.append(dict(**artifact(path), pixels=size, snapshot=relative(snapshot),
                           registers=event['registers'], interpretation='Observed original output at this stop, not a pixel or coherent-field oracle.'))
    named = {row['stem']: row for row in records}
    assert len(records) == len(EXPECTED) and set(named) == set(EXPECTED) == set(snapshots)
    assert {p.stem for p in directory.glob('*.vsf')} == set(EXPECTED)
    assert {p.stem[4:] for p in directory.glob('ram-*.bin')} == set(EXPECTED)
    assert len(images) == len(IMAGES) and {Path(p['path']).stem for p in images} == IMAGES
    assert {p.stem for p in directory.glob('*.png')} == IMAGES
    for stem, pc in EXPECTED.items(): assert named[stem]['registers']['pc'] == pc, stem
    clocks = [row['registers']['clock'] for row in records]
    assert all(a < b for a, b in zip(clocks, clocks[1:])), 'Nonmonotonic boot chronology.'

    binary_path = BASE / 'binary-analysis/side1-binary-proof.json'
    join_path = BASE / 'binary-analysis/native-payload-comparisons.json'
    assert sha(binary_path.read_bytes()) == BINARY_SHA and sha(join_path.read_bytes()) == JOIN_SHA
    binary, join = json.loads(binary_path.read_text()), json.loads(join_path.read_text())
    assert binary['pass'] is True and join['pass'] is True
    assert binary['independently_file_known_real_bundles'] == len(binary['bundles']) == 39
    assert binary['decoder_failure'] is None and binary['terminal_dummy']['entry']['bundle'] == 39
    assert binary['disk']['sha256'] == DISK_SHA
    assert all(c['exact'] and c['all_bytes_file_known'] for c in binary['payload_checks'])
    assert join['session'] == artifact(session_path) and join['session_closed_utc'] == session['closed_utc']
    assert join['source_proof'] == artifact(binary_path)
    verify_artifacts(binary)
    verify_artifacts(join)
    assert {c['name'] for c in join['captures']} == set(EXPECTED)
    for capture in join['captures']:
        row = named[capture['name']]
        assert row['ram'] == capture['ram'] and row['snapshot'] == capture['snapshot']
        assert row['registers']['pc'] == capture['pc'] and row['registers']['clock'] == capture['clock']
    assert len(join['checks']) == 15
    for check in join['checks']:
        row = named[check['capture']]
        actual = (ROOT / row['ram']['path']).read_bytes()[check['first']:check['end_exclusive']]
        assert len(actual) == check['bytes'] and check['exact'] and check['different_addresses'] == []
        assert sha(actual) == check['actual_sha256'] == check['expected_sha256']
        row.setdefault('independent_source_domains', []).append(check)

    setup_dir = BASE / 'native-01'
    setup_session_path = setup_dir / 'session.json'
    setup_session = json.loads(setup_session_path.read_text())
    assert setup_session.get('closed_utc') and setup_session.get('exit_code') == -15
    setup_text = (setup_dir / 'monitor.log').read_text(errors='strict')
    setup_audit = audit(setup_text, setup_only=True)
    assert not native.contexts(setup_text)
    assert not any(p.suffix in ('.bin', '.vsf', '.png') for p in setup_dir.iterdir())
    passed = all(row['exact'] for row in records)
    result = dict(
        status='complete', script=artifact(Path(__file__).resolve()), helpers=HELPER_PINS,
        session=session, session_metadata=artifact(session_path), transcript=artifact(transcript_path),
        observer_audit=command_audit, configured_disk=binary['disk'],
        checkpoints=records, RAM_snapshot_bytes=len(records) * 65536, screenshots=images,
        independent_source_proof=dict(artifact=artifact(binary_path), script=binary['script'],
            real_bundles=39, terminal_dummy=binary['terminal_dummy'], payload_checks=binary['payload_checks'],
            configured_RTS_entry=binary['configured_RTS_entry'], resident=binary['resident'],
            arcade=binary['arcade'], limitations=binary['limitations']),
        independent_native_domains=dict(artifact=artifact(join_path), joined_captures=len(join['captures']),
                                        domain_checks=15, scope=join['scope']),
        setup_only_attempt=dict(session=setup_session, metadata=artifact(setup_session_path),
            transcript=artifact(setup_dir / 'monitor.log'), audit=setup_audit, capture_count=0,
            interpretation='Closed helper/setup attempt with only r and sidefx off recorded, no monitor resume or capture. Not a boot/execution proof; owner reported closed stdin.'),
        scope='Closed native-02 original-disk autostart chronology, all RAM/VSF/CPU/beam pairs, zero recorded inputs/restores/data/code/PC/resource changes, and pinned independent early payload domains. No continuous loader/ROM/drive CPU model, source rebuild, native Arcade execution, whole-machine equivalence, full-image or frame-rate claim.',
    )
    result['pass'] = passed
    output.mkdir(parents=True, exist_ok=True)
    path = output / 'native-evidence.json'
    path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(passed=passed, RAM_snapshot_pairs=len(records), screenshots=len(images),
                          source_domains=15, receipt=relative(path)), indent=2))
    assert passed, 'RAM/snapshot mismatch; all differences retained.'


if __name__ == '__main__':
    main()
