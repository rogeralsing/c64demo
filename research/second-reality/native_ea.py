#!/usr/bin/env python3
"""Passively validate closed native-04, resumed from the saved DB iteration D.

No CPU interpreter, emulator, process, input injection or disk parser is run.
Capture identity, the approved restore and the independent EA/EC source proof
are separate gates. Logical render checkpoints are not whole-frame timings.
"""
import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/second-reality'
PARENT_SHA = '89b12a2aa1c506653e3924b0e8ac24970cc575005ec321d6690f709b247bd825'
SOURCE_SHA = '3d0b9fac1f2ceb6926b55b9dfea86bcf9caafe2050c717137449f57e0584301e'
DISK_SHA = '05aa03c00be26cab0618f8802477d0bc7226af029c003a253a34bd32c630acf2'
HELPER = ROOT / 'research/second-reality/native_capture.py'
spec = importlib.util.spec_from_file_location('native_ea_helpers', HELPER)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
sha, relative = native.sha, native.relative

EXPECTED_PCS = {
    'restored-db': 0xc200, 'ea-entry': 0x2e00, 'eb-bridge': 0x3f50,
    'ea-restored': 0x6c00, 'ec-load-call': 0x6de1, 'ec-load-return': 0x6de4,
    'eb-restored': 0x6de7, 'ec-entry': 0xc000, 'ec-prepared': 0xca80,
    'ec-iteration-a': 0xca88, 'ec-half-a': 0x9c02,
    'ec-iteration-b': 0xca88, 'ec-iteration-c': 0xca88,
    'ec-iteration-d': 0xca88, 'ec-visible-end': 0xcabc,
}
EXPECTED_IMAGES = {
    'ec-prepared', 'ec-half-a', 'ec-iteration-b', 'ec-iteration-d', 'ec-visible-end',
}


def commands(text):
    """Read commands following standalone monitor prompts, retaining line numbers."""
    ready = True
    result = []
    for number, line in enumerate(text.splitlines(), 1):
        value = line.strip()
        if re.fullmatch(r'\(C:\$[0-9a-f]{4}\)', value, re.I):
            ready = True
        elif ready and value:
            result.append(dict(transcript_line=number, command=value))
            ready = False
    return result


def observer_audit(text, source):
    """Reject unapproved monitor operations rather than only searching for CB writes."""
    result = commands(text)
    restores = []
    for row in result:
        command = row['command']
        if command.startswith('undump '):
            match = re.fullmatch(r'undump "([^"\n]+)"', command)
            assert match and Path(match[1]).resolve() == source.resolve(), row
            restores.append(row)
            continue
        safe = (
            command in ('r', 'sidefx off', 'bank ram', 'x')
            or re.fullmatch(r'(?:break|delete) [0-9a-f]{1,4}', command, re.I)
            or re.fullmatch(r'bsave "[^"\n]+" 0 0000 ffff', command)
            or re.fullmatch(r'dump "[^"\n]+"', command)
            or re.fullmatch(r'screenshot "[^"\n]+" 2', command)
        )
        assert safe, ('Unclassified monitor operation', row)
    assert len(restores) == 1, ('Expected exactly one approved restore', restores)
    clean = '\n'.join(row['command'] for row in result if row not in restores)
    assert native.interventions(clean) == []
    assert '[Monitor observation failed:' not in text, 'Unclassified failed observation.'
    return dict(
        commands=result, command_counts=dict(Counter(x['command'].split()[0] for x in result)),
        approved_snapshot_restores=restores, synthetic_inputs=[], direct_RAM_writes=[],
        code_writes=[], register_or_PC_writes=[], rejected_or_missing_observations=[],
        scope='Audit of the archived monitor command transcript, not an external OS activity audit.',
    )


def verify_artifacts(value):
    """Bind every path/SHA pair exposed by the pinned source receipt."""
    if isinstance(value, dict):
        if isinstance(value.get('path'), str) and 'sha256' in value:
            data = (ROOT / value['path']).read_bytes()
            assert sha(data) == value['sha256'], ('Source artifact drift', value['path'])
            if isinstance(value.get('bytes'), int):
                assert len(data) == value['bytes'], value['path']
        for item in value.values():
            verify_artifacts(item)
    elif isinstance(value, list):
        for item in value:
            verify_artifacts(item)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, default=BASE / 'native-04')
    parser.add_argument('--output', type=Path, default=BASE / 'native-ea-analysis')
    args = parser.parse_args()
    directory, output = args.capture.resolve(), args.output.resolve()
    session_path = directory / 'session.json'
    session = json.loads(session_path.read_text())
    assert session.get('closed_utc') and session.get('exit_code') == -15, 'Expected owner-closed capture session.'
    parent_path = BASE / 'native-next-analysis/native-next-evidence.json'
    parent_bytes = parent_path.read_bytes()
    assert sha(parent_bytes) == PARENT_SHA
    parent = json.loads(parent_bytes)
    assert parent['status'] == 'complete' and parent['pass'] is True
    assert sha(HELPER.read_bytes()) == parent['helper_sha256']
    reader = ROOT / 'research/quondam/snapshot_state.py'
    assert sha(reader.read_bytes()) == parent['snapshot_reader_sha256']
    inherited = next(row for row in parent['checkpoints'] if row['stem'] == 'db-iteration-d')
    source, source_ram = ROOT / inherited['snapshot'], ROOT / inherited['file']
    assert sha(source.read_bytes()) == inherited['snapshot_sha256']
    assert sha(source_ram.read_bytes()) == inherited['sha256']
    text_path = directory / 'monitor.log'
    text = text_path.read_text(errors='strict')
    audit = observer_audit(text, source)

    events = native.contexts(text)
    by_name = {}
    for event in events:
        assert event['filename'] not in by_name, ('Capture filename reused', event['filename'])
        by_name[event['filename']] = event
    snapshots, records, images = {}, [], []
    for event in events:
        if event['command'] != 'dump':
            continue
        path = directory / event['filename']
        state = native.read_snapshot(path)
        cpu = native.cpu_state(path)
        assert all(cpu[k] == event['registers'][k] for k in cpu), ('Snapshot CPU versus recorded stop', path)
        assert [state['vicii']['raster_line'], state['vicii']['raster_cycle']] == [
            event['registers']['raster_line'], event['registers']['raster_cycle']], ('Snapshot beam versus recorded stop', path)
        snapshots[path.stem] = (path, state)
    for event in events:
        if event['command'] != 'bsave':
            continue
        assert event['bank'] == 'ram' and (event['first'], event['end_inclusive']) == (0, 65535)
        path = directory / event['filename']
        assert path.name.startswith('ram-')
        stem = path.stem[4:]
        snapshot, state = snapshots[stem]
        assert by_name[snapshot.name]['registers'] == event['registers'], ('RAM/VSF stops differ', path)
        actual = path.read_bytes()
        assert len(actual) == 65536
        check = native.comparison(actual, native.physical_ram(snapshot), 0, 65536,
                                  'Every raw physical RAM byte versus the same-stop snapshot')
        records.append(dict(stem=stem, file=relative(path), sha256=sha(actual),
                            snapshot=relative(snapshot), snapshot_sha256=state['file_sha256'],
                            registers=event['registers'], transcript_line=event['transcript_line'],
                            checks=[check], exact=check['exact']))
    for event in events:
        if event['command'] not in ('screenshot', 'scrsh'):
            continue
        path = directory / event['filename']
        snapshot, _ = snapshots[path.stem]
        assert by_name[snapshot.name]['registers'] == event['registers']
        with Image.open(path) as image:
            image.load()
            size = list(image.size)
        images.append(dict(file=relative(path), sha256=sha(path.read_bytes()), pixels=size,
                           snapshot=relative(snapshot), registers=event['registers'],
                           interpretation='Original output observation; no independent full-image or coherent-frame oracle.'))
    named = {row['stem']: row for row in records}
    assert len(records) == len(EXPECTED_PCS) and set(named) == set(EXPECTED_PCS)
    assert set(snapshots) == set(named)
    assert {p.stem for p in directory.glob('*.vsf')} == set(named)
    assert {p.stem[4:] for p in directory.glob('ram-*.bin')} == set(named)
    assert len(images) == len(EXPECTED_IMAGES)
    assert {Path(x['file']).stem for x in images} == EXPECTED_IMAGES
    assert {p.stem for p in directory.glob('*.png')} == EXPECTED_IMAGES
    for stem, pc in EXPECTED_PCS.items():
        assert named[stem]['registers']['pc'] == pc, (stem, named[stem]['registers'])
    clocks = [row['registers']['clock'] for row in records]
    assert all(a < b for a, b in zip(clocks, clocks[1:])), 'Unexpected restore or nonmonotonic capture chronology.'
    restored = named['restored-db']
    restore_check = native.comparison((ROOT / restored['file']).read_bytes(), source_ram.read_bytes(),
                                     0, 65536, 'Whole RAM identity at the one approved native-03 restore')
    assert restored['registers'] == inherited['registers'], 'Restore CPU/ports/beam differ from the parent stop.'
    restore_cpu = native.module_payload(ROOT / restored['snapshot'], 'MAINCPU') == native.module_payload(source, 'MAINCPU')
    assert restore_cpu, 'Complete MAINCPU snapshot payload differs after restore.'
    # The first register query after undump must already have this same state.
    restore_line = audit['approved_snapshot_restores'][0]['transcript_line']
    first = next(m for line in text.splitlines()[restore_line:]
                 if (m := native.helpers.REGISTER.match(line.strip())))
    first_cpu = dict(pc=int(first[1], 16), a=int(first[2], 16), x=int(first[3], 16),
                     y=int(first[4], 16), sp=int(first[5], 16), flags=int(first[8], 2), clock=int(first[11]))
    assert first_cpu == native.cpu_state(source)

    source_path = BASE / 'ea-analysis/ea-proof.json'
    source_bytes = source_path.read_bytes()
    assert sha(source_bytes) == SOURCE_SHA
    oracle = json.loads(source_bytes)
    assert oracle['pass'] is True and all(c['exact'] for c in oracle['checks'])
    assert oracle['session']['path'] == relative(session_path)
    assert oracle['session']['sha256'] == sha(session_path.read_bytes())
    assert oracle['session_closed_utc'] == session['closed_utc']
    verify_artifacts(oracle)
    assert {c['name'] for c in oracle['captures']} == set(named)
    for capture in oracle['captures']:
        row = named[capture['name']]
        assert (row['file'], row['sha256']) == (capture['ram']['path'], capture['ram']['sha256'])
        assert (row['snapshot'], row['snapshot_sha256']) == (capture['snapshot']['path'], capture['snapshot']['sha256'])
        assert all(row['registers'][k] == v for k, v in capture['cpu'].items())
    disk = Path(session['program'])
    assert sha(disk.read_bytes()) == DISK_SHA == parent['independent_payload_proof']['configured_disk']['sha256']
    call = named['ec-load-call']['registers']
    assert [call['a'], call['x'], call['y']] == [8, 0x45, 0x43]
    passed = restore_check['exact'] and restore_cpu and all(row['exact'] for row in records)
    result = dict(
        status='complete', capture_checks_pass=passed, script_sha256=sha(Path(__file__).read_bytes()),
        helper_sha256=sha(HELPER.read_bytes()), snapshot_reader_sha256=sha(reader.read_bytes()),
        parent_native03_receipt=dict(file=relative(parent_path), sha256=PARENT_SHA),
        session=session, session_metadata_sha256=sha(session_path.read_bytes()),
        transcript=dict(file=relative(text_path), sha256=sha(text_path.read_bytes())), observer_audit=audit,
        restore_source=dict(file=relative(source), sha256=inherited['snapshot_sha256'],
                            RAM_file=relative(source_ram), RAM_sha256=inherited['sha256'],
                            check=restore_check, CPU_ports_beam_equal=True,
                            complete_MAINCPU_payload_equal=restore_cpu, first_observed_cpu=first_cpu,
                            interpretation='One explicit native-03 snapshot continuation, not a new cold boot.'),
        checkpoints=records, screenshots=images, RAM_snapshot_bytes=len(records) * 65536,
        configured_disk=dict(file=str(disk), sha256=DISK_SHA),
        independent_source_proof=dict(file=relative(source_path), sha256=SOURCE_SHA,
            captures_joined=len(oracle['captures']), checks=len(oracle['checks']),
            script=oracle['script'], files=oracle['files'], checks_summary=oracle['checks'],
            limitations=oracle['limitations']),
        scope='Closed native-04 lifecycle, exact approved restore, every RAM/VSF/CPU/beam pair, zero recorded data/code/PC/input edits, and a pinned independent source-proof join. No full image, sound, drive timing, whole-machine equivalence or coherent-frame FPS claim.',
    )
    result['pass'] = passed
    output.mkdir(parents=True, exist_ok=True)
    path = output / 'native-ea-evidence.json'
    path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status=result['status'], passed=passed, RAM_snapshot_pairs=len(records),
                          screenshots=len(images), source_checks=len(oracle['checks']), receipt=relative(path)), indent=2))
    assert passed, 'Native-04 comparison failed; differences retained.'


if __name__ == '__main__':
    main()
