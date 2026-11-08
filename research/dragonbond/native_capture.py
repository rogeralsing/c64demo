#!/usr/bin/env python3
"""Audit retained original Dragonbond captures without starting an emulator."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/dragonbond'
OUTPUT = BASE / 'native-analysis'
DISK_SHA = '37854b4e3426349ee03bc759f5bed8ad9a6c7f0404a469f1ae5163918cf50300'
PARENT_SHA = '96f34d4beaec41de6f997aac42f8dcbc5e758fe3564c11c6c323c6a954bc1a3e'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


boot = load('dragon_native_helpers', 'research/anomaly/native_capture.py')
reader = load('dragon_native_commands', 'research/anomaly/native_arcade.py')
arcade = load('dragon_trace_reader', 'research/anomaly/inspect_arcade.py')
native = boot.native


def artifact(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest())


def capture_pairs(directory, transcript, expected):
    # The frozen C64 context reader accepts plain C64 address operands only.
    # Keep the original drive-space command in the real transcript, but omit
    # that one command from this reader input. Its payload is checked separately.
    drive_command = re.compile(r'^bsave "[^"\n]+/drive-ram-first-load.bin" 0 8:0000 8:07ff$')
    skipped = [line for line in transcript.splitlines() if drive_command.fullmatch(line)]
    cleaned = '\n'.join(line for line in transcript.splitlines() if not drive_command.fullmatch(line))
    events = native.contexts(cleaned)
    by_name = {event['filename']: event for event in events}
    assert len(events) == len(by_name)
    result = []
    for stem, (pc, clock, line, cycle) in expected.items():
        ram, snapshot = directory / f'ram-{stem}.bin', directory / f'{stem}.vsf'
        a, b = by_name[ram.name], by_name[snapshot.name]
        assert a['registers'] == b['registers']
        assert a['bank'] == 'ram' and (a['first'], a['end_inclusive']) == (0, 65535)
        cpu, state = native.cpu_state(snapshot), native.read_snapshot(snapshot)
        assert all(cpu[key] == a['registers'][key] for key in cpu)
        assert (cpu['pc'], cpu['clock'], state['vicii']['raster_line'], state['vicii']['raster_cycle']) == (pc, clock, line, cycle)
        assert ram.read_bytes() == native.physical_ram(snapshot)
        memory = native.module_payload(snapshot, 'C64MEM')
        assert (memory[1], memory[0]) == (a['registers']['port00'], a['registers']['port01'])
        result.append(dict(stem=stem, ram=artifact(ram), snapshot=artifact(snapshot), registers=a['registers'],
                           scene_label_accepted=stem != 'scene-42-entry'))
    return result, by_name, skipped


def audit_commands(transcript, session_number, parent):
    rows = reader.commands(transcript)
    resumes, restores, failures, warp = [], [], [], None
    for index, row in enumerate(rows):
        command = row['command']
        response = '\n'.join(row['response'])
        allowed = command in ('r', 'sidefx off', 'bank ram', 'warp', 'warp on', 'warp off',
                              'x', 'resourceget "Speed"', 'device c:')
        allowed |= bool(re.fullmatch(r'(?:break|delete) [0-9a-f]{1,4}(?: if (?:Y == \$[0-9a-f]{2}|RL == \$10b))?', command))
        allowed |= command == 'trace exec 06bb'
        allowed |= bool(re.fullmatch(r'trace store (?:d000 d02e|dd00 dd03|43f8 43ff|83f8 83ff)', command))
        allowed |= bool(re.fullmatch(r'bsave "[^"\n]+" 0 (?:0000 ffff|8:0000 8:07ff)', command))
        allowed |= bool(re.fullmatch(r'(?:dump|screenshot) "[^"\n]+"(?: 2)?', command))
        if command.startswith('undump '):
            assert session_number == 2 and command == f'undump "{parent}"'
            restores.append(row)
            allowed = True
        assert allowed, row
        assert '[Monitor observation failed:' not in response
        if 'not a valid checkpoint' in response:
            assert session_number == 1 and command == 'delete 3'
            failures.append(row)
        if command == 'warp':
            assert response.strip() == 'Warp mode is off.'
            warp = False
        elif command in ('warp on', 'warp off'):
            warp = command.endswith('on')
        if command == 'resourceget "Speed"':
            assert response.strip() == 'Speed=100'
        if command == 'x':
            assert warp is not None
            if not warp:
                assert [r['command'] for r in rows[index-2:index]] == ['warp', 'resourceget "Speed"']
            resumes.append(dict(command_index=index, warp=warp,
                                scope='Navigation only; not a timing claim' if warp else 'Unwarped original execution',
                                response_stop=re.findall(r'\.C:([0-9a-f]{4})[^\n]*\s(\d+)\s*$', response, re.M)[-1:]))
    return dict(command_count=len(rows), completed_resumes=resumes, restores=len(restores),
                rejected_checkpoint_commands=failures, writes_to_code_RAM_or_PC=[])


def main():
    for path, digest in boot.HELPER_PINS.items():
        assert artifact(ROOT / path)['sha256'] == digest
    disk = ROOT / 'build/research/frontier-20261108/dragonbond.d64'
    assert artifact(disk)['sha256'] == DISK_SHA
    parent = BASE / 'native-01/scene-41-entry.vsf'
    assert artifact(parent)['sha256'] == PARENT_SHA
    expected1 = {
        'boot-entry': (0x081e, 9665267, 224, 59),
        'depacker-entry': (0x0020, 9701167, 170, 49),
        'loader-entry': (0x2000, 9880008, 201, 33),
        'first-load-entry': (0x06bb, 10802022, 172, 42),
        'intro-entry': (0x0400, 11276186, 211, 5),
        'scene-3e-entry': (0x2800, 13071620, 6, 2),
        'scene-3e-ready': (0x28cc, 13084705, 213, 46),
        'scene-3f-entry': (0x2800, 28324176, 310, 6),
        'scene-3f-ready': (0x2832, 28324240, 311, 7),
        'scene-42-entry': (0x2832, 28324243, 311, 10),
        'scene-42-entry-valid': (0x2800, 38520350, 226, 8),
        'scene-42-ready': (0x28d6, 38545461, 0, 45),
        'scene-40-entry': (0x2800, 49637206, 92, 10),
        'scene-40-ready': (0x2832, 49637270, 93, 11),
        'scene-41-entry': (0x2800, 139667377, 182, 31),
    }
    expected2 = {
        'restored-scene41': (0x2800, 139667377, 182, 31),
        'scene41-ready': (0x2808, 139667473, 184, 1),
        'first-picture-irq': (0x28f6, 148997405, 78, 11),
        'before-intermediate': (0x3239, 149001185, 138, 11),
        'after-intermediate': (0x3258, 149001250, 139, 13),
        'before-full-new': (0x3239, 149001780, 147, 39),
        'after-full-new': (0x3258, 149001844, 148, 40),
        'before-next-intermediate': (0x3239, 149002445, 158, 11),
        'picture-field-01-end': (0x28f6, 149017061, 78, 11),
        'bank80-after-intermediate': (0x3278, 149027395, 242, 13),
        'bank80-before-full-new': (0x3259, 149028173, 254, 35),
        'bank80-after-full-new': (0x3278, 149028238, 255, 37),
    }
    sessions, all_pairs = [], []
    for number, expected in ((1, expected1), (2, expected2)):
        directory = BASE / f'native-0{number}'
        metadata = directory / 'session.json'
        session = json.loads(metadata.read_text())
        assert session['command'][session['command'].index('-8') + 1] == str(disk)
        assert '-pal' in session['command'] and '+saveres' in session['command']
        if number == 1:
            assert '-autostart' in session['command']
            assert session['closed_utc'] and session['exit_code'] == -15
        else:
            assert '-autostart' not in session['command']
            assert 'closed_utc' not in session  # Original incomplete helper metadata stays untouched.
        transcript = (directory / 'monitor.log').read_text()
        commands = audit_commands(transcript, number, parent)
        assert commands['restores'] == (number == 2)
        assert len(commands['completed_resumes']) == (15 if number == 1 else 11)
        pairs, contexts, drive_commands = capture_pairs(directory, transcript, expected)
        assert len(contexts) == (30 if number == 1 else 25)
        assert len(drive_commands) == (number == 1)
        all_pairs.extend(pairs)
        result = dict(session_metadata=artifact(metadata), session=session,
                      transcript=artifact(directory / 'monitor.log'), command_audit=commands,
                      checkpoints=pairs, drive_command_excluded_only_from_C64_context_reader=drive_commands)
        if number == 1:
            requests = re.findall(r'(?m)^#\d+ \(Trace\s+exec 06bb\)[^\n]*\n\.C:06bb[^\n]*A:([0-9a-fA-F]{2})', transcript)
            assert [int(value, 16) for value in requests] == [0x3e, 0x3f, 0x42, 0x40, 0x41]
            assert pairs[3]['registers']['a'] == 0
            drive = directory / 'drive-ram-first-load.bin'
            assert drive.stat().st_size == 2048
            result.update(actual_subsequent_file_requests_hex=requests, drive_RAM=artifact(drive),
                          rejected_label=artifact(directory / 'rejected-scene42-label.json'))
        else:
            cleanup_path = directory / 'owner-cleanup.json'
            cleanup = json.loads(cleanup_path.read_text())
            assert cleanup['session_sha256'] == artifact(metadata)['sha256']
            assert str(session['pid']) in cleanup['observed_owned_process']
            assert f"ip4://127.0.0.1:{session['port']}" in cleanup['observed_owned_process']
            assert cleanup['signal_requested'] == 'SIGTERM' and cleanup['owned_process_observed_absent']
            incomplete_path = directory / 'uncompleted-tail-observation.json'
            incomplete = json.loads(incomplete_path.read_text())
            assert incomplete['last_completed_capture_sha256'] == artifact(directory / 'bank80-after-full-new.vsf')['sha256']
            assert not (directory / 'bank80-new-tail.vsf').exists()
            assert not (directory / 'ram-bank80-new-tail.bin').exists()
            stores = arcade.traces(transcript)
            assert len(stores) == len(re.findall(r'^#\d+ \(Trace store ', transcript, re.M))
            screenshot = directory / 'picture-field-01-end.png'
            assert contexts[screenshot.name]['registers'] == contexts['picture-field-01-end.vsf']['registers']
            result.update(external_owner_cleanup=artifact(cleanup_path), cleanup=cleanup,
                          uncompleted_extra_observation=artifact(incomplete_path),
                          original_store_observations=stores,
                          store_target_histogram={f'{address:04x}': count for address, count in Counter(r['target'] for r in stores).items()},
                          screenshot=dict(**artifact(screenshot), scope='Initial transition observation, not complete-picture pixel proof.'),
                          completed_field_anchor_delta=149017061-148997405)
        sessions.append(result)
    restored = BASE / 'native-02/restored-scene41.vsf'
    for module in ('C64MEM', 'MAINCPU', 'CIA1', 'CIA2', 'VIC-II'):
        assert native.module_payload(parent, module) == native.module_payload(restored, module)
    assert sum(row['warp'] for row in sessions[0]['command_audit']['completed_resumes']) == 5
    assert not any(row['warp'] for row in sessions[1]['command_audit']['completed_resumes'])
    result = dict(pass_=True, script=artifact(Path(__file__).resolve()),
                  original_disk=artifact(disk), restore_parent=artifact(parent), sessions=sessions,
                  RAM_snapshot_pairs=len(all_pairs), RAM_snapshot_bytes=65536*len(all_pairs),
                  restore=dict(complete_C64MEM_MAINCPU_CIA1_CIA2_VICII_equal=True),
                  completed_resumes=26, uncompleted_optional_resumes=1,
                  data_or_PC_writes=[],
                  scope='Original boot/loader/scene lineage and same-stop full-RAM/snapshot ownership; completed native02 DMA interpretation belongs to inspect_original.py.',
                  limits=['Native01 contains five explicitly warped navigation intervals, not timing proofs.',
                          'A misleading scene42 filename is retained and rejected by actualPC.',
                          'The final native02 optional raster observation did not complete; wrapper interruption bypassed finally.',
                          'External owner cleanup is verified separately; no helper exit code or final machine state is invented.',
                          'Trace coordinates are instruction observer positions, not individual physical bus phases.',
                          'No complete-picture pixel reconstruction, physical-hardware equivalence or whole-demo FPS claim.'])
    result['pass'] = result.pop('pass_')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'native-evidence.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: result[key] for key in ('pass', 'RAM_snapshot_pairs', 'RAM_snapshot_bytes', 'completed_resumes', 'uncompleted_optional_resumes')}, indent=2))


if __name__ == '__main__':
    main()
