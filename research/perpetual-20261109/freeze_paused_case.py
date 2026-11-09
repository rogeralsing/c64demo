#!/usr/bin/env python3
"""Preserve the root-owned case closed when the research goal was paused.

This reads retained files only. It neither runs an emulator nor upgrades the
unfinished native-custody reader into an accepted proof.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/perpetual-20261109'
CASE = BASE / 'native-01'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def ref(path):
    raw = path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=len(raw), sha256=sha(raw))


def write_new(path, value):
    assert not path.exists(), path
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    session = json.loads((CASE / 'session.json').read_bytes())
    assert session['pid'] == 13008 and session['port'] == 63952
    assert session['exit_code'] == -15 and session['owned_process_reaped'] is True
    assert session['closed_utc'] == '2026-11-09T12:39:26.241789+00:00'
    events = [json.loads(line) for line in (CASE / 'events.jsonl').read_text().splitlines()]
    responses = [row for row in events if row['kind'] == 'response']
    assert len(responses) == 36
    assert [row['sequence'] for row in responses] == list(range(1, 37))
    assert all(row['status'] == 'completed' for row in responses[:35])
    final = responses[-1]
    assert final['status'] == 'interrupted' and final['sequence'] == 36
    assert final['interrupt']['reason'] == 'close'
    assert final['interrupt']['drained_registers_and_prompt'] is True
    waits = [row for row in events if row['kind'] == 'observation_timeout']
    assert len(waits) == 1 and waits[0]['sequence'] == 36
    rows = [dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
            for p in sorted(CASE.iterdir()) if p.is_file()]
    assert len(rows) == 15
    manifest = BASE / 'native-01-files.json'
    write_new(manifest, dict(case=CASE.relative_to(ROOT).as_posix(), files=rows,
                            file_count=len(rows), bytes=sum(r['bytes'] for r in rows),
                            canonical_listing_sha256=sha(json.dumps(
                                rows, sort_keys=True, separators=(',', ':')).encode())))
    pairs = []
    for stem, save, snapshot in [('packed-sys', 14, 15), ('unpacked-entry', 20, 21),
                                  ('installed-init', 26, 27), ('menu-entry', 32, 33)]:
        pairs.append(dict(stem=stem, ram=ref(CASE / (stem + '-ram.bin')),
                          snapshot=ref(CASE / (stem + '.vsf')),
                          save_sequence=save, snapshot_sequence=snapshot))
    closure = BASE / 'paused-owner-closure.json'
    write_new(closure, dict(
        status='paused_work_in_progress', accepted_native_proof=False,
        owner_closed=True, owned_process_reaped=True, unified_handle_terminal=True,
        unified_session_id=70913, observer_tool_exit_code=0, native_exit_code=-15,
        pid=13008, port=63952, session=ref(CASE / 'session.json'),
        manifest=ref(manifest), pairs=pairs,
        completed_responses=35, interrupted_responses=1,
        observation_timeout_notices=waits, final_interrupted_response=final,
        final_RAM_snapshot_pair_captured=False,
        snapshot_restores=0, restarts=0, disk_changes=0, PC_or_RAM_patches=0,
        external_keyboard_attempt=dict(
            interface='macOS System Events, targeted process PID 13008',
            physical_key_code=49, requested_key='SPACE', command_exit_code=0,
            ordering='After sequence 36 was accepted; before user pause and owner closure.',
            exact_input_timestamp_not_recorded=True,
            delivery_to_emulated_CIA_unproved=True,
            guarded_1944_exit_not_observed=True),
        native_UI_discovery='CUA native-app service startup failed; browser discovery was not used for emulator input.',
        preliminary_byte_check=ref(BASE / 'root-unpack-precheck.json'),
        limitations=[
            'The source-native custody reader remains fail-closed and unfinished.',
            'Raw equality of 9467 packed and 17403 unpacked bytes is a preliminary check, not a selected native receipt.',
            'No natural menu exit, first effect IRQ, WIZ update, completed effect pixels or FPS was captured.',
            'The final stop is an interrupted menu register response, not another natural RAM/snapshot pair.'],
        freeze_source=ref(Path(__file__))))
    print(json.dumps(dict(manifest=ref(manifest), closure=ref(closure))))


if __name__ == '__main__':
    main()
