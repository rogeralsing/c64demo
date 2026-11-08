#!/usr/bin/env python3
"""Passively audit the closed native-05 scanout captures; run no emulator."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/anomaly'
CAPTURE = BASE / 'native-05'
OUTPUT = BASE / 'native-scanout-analysis'
PARENT_SHA = '70fbfcde49a6c1b9a1b18ad538d7e0684cc1c7fdaf2ec6a42b40ad734bbf1b5b'
DISK_SHA = 'd452497845598cca8936fdf57c60fdc9c70cd7e64110e049fa6fc7d735f940cd'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


boot = load('scanout_native_helpers', 'research/anomaly/native_capture.py')
arcade = load('scanout_original_code', 'research/anomaly/inspect_arcade.py')
command_reader = load('scanout_commands', 'research/anomaly/native_arcade.py')
native = boot.native


def artifact(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest())


def main():
    for name, digest in boot.HELPER_PINS.items():
        assert artifact(ROOT / name)['sha256'] == digest
    parent = BASE / 'native-04/field-04-pre.vsf'
    disk = BASE / 'original/WeAreTheAnomaly-Side1.d64'
    assert artifact(parent)['sha256'] == PARENT_SHA
    assert artifact(disk)['sha256'] == DISK_SHA
    session = json.loads((CAPTURE / 'session.json').read_text())
    assert session['closed_utc'] and session['exit_code'] == -15
    assert '-autostart' not in session['command']
    assert session['command'][session['command'].index('-8') + 1] == str(disk)
    text = (CAPTURE / 'monitor.log').read_text()
    commands = command_reader.commands(text)
    resumes, restores = [], []
    for index, row in enumerate(commands):
        command = row['command']
        allowed = command in ('r', 'sidefx off', 'bank ram', 'warp', 'x', 'resourceget "Speed"')
        allowed |= bool(re.fullmatch(r'(?:break|delete) [0-9a-f]{1,4}', command))
        allowed |= bool(re.fullmatch(r'trace store (?:d000 d02e|dd00 dd03|63f8 63ff)', command))
        allowed |= bool(re.fullmatch(r'disass (?:b400 b440|b530 b55a|b441 b4a0)', command))
        allowed |= bool(re.fullmatch(r'bsave "[^"\n]+" 0 0000 ffff', command))
        allowed |= bool(re.fullmatch(r'(?:dump|screenshot) "[^"\n]+"(?: 2)?', command))
        if command.startswith('undump '):
            assert command == f'undump "{parent}"'
            restores.append(row)
            allowed = True
        assert allowed, row
        response = '\n'.join(row['response'])
        assert '[Monitor observation failed:' not in response
        if command == 'warp':
            assert response.strip() == 'Warp mode is off.'
        if command == 'resourceget "Speed"':
            assert response.strip() == 'Speed=100'
        if command == 'x':
            assert [r['command'] for r in commands[index - 2:index]] == ['warp', 'resourceget "Speed"']
            resumes.append(row)
    assert len(restores) == 1 and len(resumes) == 4
    expected = {'restored-arcade': (0xb400, 152, 13),
                'first-row-fetched': (0xb47b, 155, 59),
                'floor-strip-complete': (0xb54a, 178, 53),
                'floor-strip-drawn': (0xb54d, 178, 59),
                'field-post': (0xb828, 250, 57)}
    events = native.contexts(text)
    by_name = {r['filename']: r for r in events}
    assert len(events) == len(by_name) == 11
    checkpoints = []
    for stem, stop in expected.items():
        ram_path, snapshot = CAPTURE / f'ram-{stem}.bin', CAPTURE / f'{stem}.vsf'
        a, b = by_name[ram_path.name], by_name[snapshot.name]
        assert a['registers'] == b['registers']
        assert a['bank'] == 'ram' and (a['first'], a['end_inclusive']) == (0, 65535)
        state, cpu = native.read_snapshot(snapshot), native.cpu_state(snapshot)
        assert all(cpu[k] == a['registers'][k] for k in cpu)
        assert (cpu['pc'], state['vicii']['raster_line'], state['vicii']['raster_cycle']) == stop
        assert ram_path.read_bytes() == native.physical_ram(snapshot)
        mem = native.module_payload(snapshot, 'C64MEM')
        assert (mem[1], mem[0]) == (a['registers']['port00'], a['registers']['port01'])
        checkpoints.append(dict(stem=stem, ram=artifact(ram_path), snapshot=artifact(snapshot),
                                registers=a['registers']))
    restored = CAPTURE / 'restored-arcade.vsf'
    for module in ('C64MEM', 'MAINCPU'):
        assert native.module_payload(parent, module) == native.module_payload(restored, module)
    assert native.physical_ram(CAPTURE / 'floor-strip-complete.vsf') == native.physical_ram(CAPTURE / 'floor-strip-drawn.vsf')
    source, _, _, source_receipt = arcade.original()
    schedule, stores = arcade.D016_schedule(source), arcade.traces(text)
    assert len(stores) == len(re.findall(r'^#\d+ \(Trace store ', text, re.M))
    floor = [r for r in stores if r['target'] == 0xd016]
    memory = native.physical_ram(parent)
    assert len(floor) == len(schedule) == 96
    for observed, planned in zip(floor, schedule):
        assert observed['pc'] == planned['pc'] and observed['x'] == planned['line']
        assert observed['a'] == memory[planned['table_address']]
        assert memory[observed['pc']:observed['pc'] + 3] == bytes.fromhex('8d 16 d0')
    assert [r['line'] for r in floor] == list(range(155, 251))
    screenshot = CAPTURE / 'field-post.png'
    assert by_name[screenshot.name]['registers'] == checkpoints[-1]['registers']
    result = dict(pass_=True, script=artifact(Path(__file__).resolve()),
                  session_metadata=artifact(CAPTURE / 'session.json'), session=session,
                  transcript=artifact(CAPTURE / 'monitor.log'), parent=artifact(parent),
                  original_disk=artifact(disk), original_source_receipt=source_receipt,
                  restore=dict(complete_C64MEM_equal=True, complete_MAINCPU_equal=True,
                               ports_equal=True, registers_and_beam_equal=True),
                  checkpoints=checkpoints, RAM_snapshot_bytes=65536 * len(checkpoints),
                  screenshot=dict(**artifact(screenshot), scope='Output observation, not full-screen pixel proof.'),
                  register_observations=stores, floor_D016_observations=floor,
                  target_histogram={f'{a:04x}': count for a, count in Counter(r['target'] for r in stores).items()},
                  observation_resumes=4, restores=1, warp_off_before_each_resume=True,
                  observed_speed=100, data_or_PC_writes=[],
                  rejected_observer_assumptions=[
                      'Physical RAM offsets0/1 are not the6510ports; corrected using complete C64MEM equality and transcript2F/35.',
                      'Capture floor-strip-complete is actually B54A at178/53, before the final graphics fetches. Its filename is historical; floor-strip-drawn178/59 is the late-row capture.'],
                  scope='Closed capture lineage and source-matched96 floor stores. Pixel/fetch interpretation belongs to the independent scanout model.',
                  limits=['Trace clocks are observer coordinates, not physical bus phases.',
                          'RMW trace events are not a complete list of individual dummy/final bus writes.',
                          'No whole-screen compositor, maximum workload or whole-demo FPS proof.'])
    result['pass'] = result.pop('pass_')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'native-scanout-evidence.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('pass', 'RAM_snapshot_bytes', 'observation_resumes', 'restores', 'scope')}, indent=2))


if __name__ == '__main__':
    main()
