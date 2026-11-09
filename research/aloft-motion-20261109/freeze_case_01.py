#!/usr/bin/env python3
"""Freeze the owner's already closed original-disk motion observation.

Only retained files are read. The terminal handle, tool exit and owned-process
closure below are facts observed by the root owner, not inferred from a PID.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-motion-20261109'
CASE = BASE / 'native-01'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def ref(path):
    raw = path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=len(raw), sha256=sha(raw))


def write_new(path, value):
    assert not path.exists(), path
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    session = json.loads((CASE / 'session.json').read_bytes())
    assert session['pid'] == 92343 and session['port'] == 60831
    assert session['owned_process_reaped'] is True and session['exit_code'] == -15
    assert session['closed_utc'] == '2026-11-09T11:58:22.295820+00:00'
    events = [json.loads(line) for line in (CASE / 'events.jsonl').read_text().splitlines()]
    responses = [row for row in events if row['kind'] == 'response']
    assert len(responses) == 84
    assert all(row['status'] == 'completed' for row in responses)
    assert responses[-1]['sequence'] == 84
    assert responses[-1]['response'] == 'No breakpoints are set\n(C:$f11d) '
    assert not any('ERROR' in row['response'] for row in responses)
    rows = [dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
            for p in sorted(CASE.iterdir()) if p.is_file()]
    assert len(rows) == 23
    listing_sha = sha(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode())
    manifest = BASE / 'native-01-files.json'
    write_new(manifest, dict(case=CASE.relative_to(ROOT).as_posix(), files=rows,
                            file_count=len(rows), bytes=sum(r['bytes'] for r in rows),
                            canonical_listing_sha256=listing_sha))
    stems = ['sys', 'body', 'first-precall', 'first-postcall', 'first-postwrapper',
             'later-precall', 'later-postcall', 'later-postwrapper']
    pairs = []
    for stem in stems:
        ram, vsf = CASE / (stem + '-ram.bin'), CASE / (stem + '.vsf')
        saves = [r for r in responses if r['command'].startswith('bsave ') and str(ram) in r['command']]
        dumps = [r for r in responses if r['command'] == 'dump "' + str(vsf) + '"']
        assert len(saves) == len(dumps) == 1 and ram.stat().st_size == 65536
        pairs.append(dict(stem=stem, ram=ref(ram), vsf=ref(vsf),
                          ram_sequence=saves[0]['sequence'], snapshot_sequence=dumps[0]['sequence']))
    write_new(BASE / 'owner-closure-01.json', dict(
        scope='Root-owned terminal closure and capture map; arithmetic and timing acceptance are separate.',
        owner_closed=True, owned_process_reaped=True, unified_handle_terminal=True,
        unified_session_id=77394, observer_tool_exit_code=0, native_exit_code=-15,
        pid=92343, port=60831, session=ref(CASE / 'session.json'),
        case_relative=CASE.relative_to(ROOT).as_posix(), manifest=ref(manifest),
        file_count=len(rows), case_bytes=sum(r['bytes'] for r in rows),
        canonical_listing_sha256=listing_sha, response_count=len(responses),
        all_84_responses_completed=True, fresh_original_autostart=True,
        snapshot_restores=0, PC_or_RAM_mutations=0, disk_changes=0, restarts=0,
        interrupts=0, timeouts=0, pairs=pairs, syntax_errors=[],
        final_resource_queries=[dict(sequence=r['sequence'], command=r['command'], response=r['response'])
                                for r in responses if 74 <= r['sequence'] <= 79],
        fields=[
            dict(label='first', index=0, roles=dict(precall='first-precall', postcall='first-postcall',
                                                  postwrapper='first-postwrapper'),
                 pre_run_sequence=34, call_run_sequence=42, wrapper_run_sequence=49),
            dict(label='later', index=64, roles=dict(precall='later-precall', postcall='later-postcall',
                                                    postwrapper='later-postwrapper'),
                 pre_run_sequence=56, call_run_sequence=63, wrapper_run_sequence=70)],
        checkpoint_ids=dict(sys=1, body=2, input=3, output=4, wrapper=5, stores=6),
        motion_scope='F133 inputs precede the JSR C000 that builds the following display list. F136 precedes phase updates. F11D precedes INC05.',
        later_selection='After the first wrapper stop, checkpoint 3 ignored the next 63 entries. The following entry is invocation index 64.',
        warp_scope='Warp only between SYS and F02B; off before both motion observations.',
        limitations=['Monitor store clocks are instruction-completion hooks, not electrical bus timestamps.',
                     'Only two calls of the first of four source-defined motion programs were observed.',
                     'No scanout, full-field timing, frame rate or named visual-scene identity is accepted here.'],
        freeze_source=ref(Path(__file__))))
    print(json.dumps(dict(manifest=ref(manifest), owner_closure=ref(BASE / 'owner-closure-01.json'))))


if __name__ == '__main__':
    main()
