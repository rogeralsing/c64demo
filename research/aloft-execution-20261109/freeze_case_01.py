#!/usr/bin/env python3
"""Freeze the root-owned, already closed original-disk observation case.

This reads retained files only. It cannot start or control a native process.
The terminal-handle facts below are the owner's observed tool result.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-execution-20261109'
CASE = BASE / 'native-01'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def ref(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw),
            'sha256': digest(raw)}


def write_new(path, value):
    assert not path.exists(), path
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    session = json.loads((CASE / 'session.json').read_bytes())
    assert session['pid'] == 93687 and session['port'] == 63808
    assert session['owned_process_reaped'] is True and session['exit_code'] == -15
    assert session['closed_utc'] == '2026-11-09T10:23:27.122071+00:00'
    events = [json.loads(line) for line in (CASE / 'events.jsonl').read_text().splitlines()]
    responses = [row for row in events if row['kind'] == 'response']
    assert len(responses) == 202
    assert all(row['status'] == 'completed' for row in responses)
    assert responses[-1]['sequence'] == 202
    assert responses[-1]['response'].startswith('No breakpoints are set\n')
    rows = [{'name': path.name, 'bytes': path.stat().st_size,
             'sha256': digest(path.read_bytes())}
            for path in sorted(CASE.iterdir()) if path.is_file()]
    listing_sha = digest(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode())
    manifest = BASE / 'native-01-files.json'
    write_new(manifest, {'case': CASE.relative_to(ROOT).as_posix(), 'files': rows,
                        'file_count': len(rows), 'bytes': sum(row['bytes'] for row in rows),
                        'canonical_listing_sha256': listing_sha})
    stems = ['sys', 'body', 'precall', 'dispatcher', 'cell-entry', 'inc-entry',
             'inc-after', 'first-return', 'chain-return', 'after-line',
             'later-precall', 'later-dispatcher', 'later-cell-entry',
             'later-first-return', 'later-chain-return', 'later-after-line',
             'later-wrap-zero', 'later-wrap-one']
    pairs = []
    for stem in stems:
        ram, vsf = CASE / (stem + '-ram.bin'), CASE / (stem + '.vsf')
        matches = [row for row in responses if row['command'].startswith('bsave ')
                   and str(ram) in row['command']]
        snapshots = [row for row in responses if row['command'] == 'dump "' + str(vsf) + '"']
        assert len(matches) == len(snapshots) == 1
        assert ram.stat().st_size == 65536
        pairs.append({'stem': stem, 'ram': ref(ram), 'vsf': ref(vsf),
                      'ram_sequence': matches[0]['sequence'],
                      'snapshot_sequence': snapshots[0]['sequence']})
    write_new(BASE / 'owner-closure-01.json', {
        'scope': 'Root-owned terminal closure facts and raw capture map; no semantic, pixel or FPS acceptance.',
        'owner_closed': True, 'owned_process_reaped': True,
        'unified_handle_terminal': True, 'unified_session_id': 26020,
        'observer_tool_exit_code': 0, 'native_exit_code': -15,
        'pid': 93687, 'port': 63808, 'session': ref(CASE / 'session.json'),
        'case_relative': CASE.relative_to(ROOT).as_posix(), 'manifest': ref(manifest),
        'file_count': len(rows), 'case_bytes': sum(row['bytes'] for row in rows),
        'canonical_listing_sha256': listing_sha,
        'response_count': len(responses), 'all_202_responses_completed': True,
        'fresh_original_autostart': True, 'snapshot_restores': 0,
        'PC_or_RAM_mutations': 0, 'disk_changes': 0, 'restarts': 0,
        'interrupts': 0, 'timeouts': 0, 'pairs': pairs,
        'syntax_errors': [dict(sequence=row['sequence'], command=row['command'],
                               response=row['response'],
                               explanation='Read-only resource query omitted required quotes; corrected below without resuming.')
                          for row in responses if 177 <= row['sequence'] <= 181],
        'corrected_final_resource_queries': [dict(sequence=row['sequence'], command=row['command'],
                                                 response=row['response'])
                                            for row in responses if 183 <= row['sequence'] <= 187],
        'wrap_scope': 'Row0/cycle2 and row1/cycle2 are 63 cycles apart in the same field; they retain the same preceding field viewport, not two displayed generations.',
        'limitations': ['No fresh capture of resident-copy return at $08B5.',
                        'Monitor hook clocks are instruction completion clocks, not physical bus timestamps.',
                        'No native scanout, FPS or cell-model acceptance is supplied by this owner record.'],
        'freeze_source': ref(Path(__file__))})
    print(json.dumps({'manifest': ref(manifest), 'owner_closure': ref(BASE / 'owner-closure-01.json')}))


if __name__ == '__main__':
    main()
