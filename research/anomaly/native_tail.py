#!/usr/bin/env python3
"""Passively audit the closed five-cycle native-06 floor continuation."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/anomaly'
CAPTURE = BASE / 'native-06'
OUTPUT = BASE / 'native-tail-analysis'
PARENT_SHA = '2185b4f932c49c900223c9e5c3598fc66c6fd8b1e04704158699659aa574b28a'
OWNER_SHA = '70fe556b8c80bf6a73721b4f51852e30bc9f6b103f1e3bff06e4e2e1b1e7dfa2'
DISK_SHA = 'd452497845598cca8936fdf57c60fdc9c70cd7e64110e049fa6fc7d735f940cd'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


boot = load('tail_native_helpers', 'research/anomaly/native_capture.py')
reader = load('tail_native_commands', 'research/anomaly/native_arcade.py')
native = boot.native


def artifact(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest())


def main():
    for name, digest in boot.HELPER_PINS.items():
        assert artifact(ROOT / name)['sha256'] == digest
    parent = BASE / 'native-05/field-post.vsf'
    owner = BASE / 'native-scanout-analysis/native-scanout-evidence.json'
    disk = BASE / 'original/WeAreTheAnomaly-Side1.d64'
    assert artifact(parent)['sha256'] == PARENT_SHA
    assert artifact(owner)['sha256'] == OWNER_SHA
    assert artifact(disk)['sha256'] == DISK_SHA
    assert json.loads(owner.read_text())['pass']
    session = json.loads((CAPTURE / 'session.json').read_text())
    assert session['closed_utc'] and session['exit_code'] == -15
    assert '-autostart' not in session['command']
    assert session['command'][session['command'].index('-8') + 1] == str(disk)
    transcript = (CAPTURE / 'monitor.log').read_text()
    commands = reader.commands(transcript)
    restores, resumes = [], []
    for index, row in enumerate(commands):
        command = row['command']
        allowed = command in ('r', 'sidefx off', 'bank ram', 'warp', 'x',
                              'resourceget "Speed"', 'break b82a')
        allowed |= bool(re.fullmatch(r'bsave "[^"\n]+" 0 0000 ffff', command))
        allowed |= bool(re.fullmatch(r'dump "[^"\n]+"', command))
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
            assert [r['command'] for r in commands[index-2:index]] == ['warp', 'resourceget "Speed"']
            resumes.append(row)
    assert len(restores) == len(resumes) == 1
    contexts = native.contexts(transcript)
    by_name = {event['filename']: event for event in contexts}
    assert len(contexts) == len(by_name) == 4
    checkpoints = []
    expected = {'restored-floor-post': (0xb828, 250, 57, 167013183),
                'floor-line-drawn': (0xb82a, 250, 62, 167013188)}
    for stem, stop in expected.items():
        ram, snapshot = CAPTURE / f'ram-{stem}.bin', CAPTURE / f'{stem}.vsf'
        a, b = by_name[ram.name], by_name[snapshot.name]
        assert a['registers'] == b['registers']
        assert a['bank'] == 'ram' and (a['first'], a['end_inclusive']) == (0, 65535)
        cpu, state = native.cpu_state(snapshot), native.read_snapshot(snapshot)
        assert all(cpu[k] == a['registers'][k] for k in cpu)
        assert (cpu['pc'], state['vicii']['raster_line'], state['vicii']['raster_cycle'], cpu['clock']) == stop
        assert ram.read_bytes() == native.physical_ram(snapshot)
        memory = native.module_payload(snapshot, 'C64MEM')
        assert (memory[1], memory[0]) == (a['registers']['port00'], a['registers']['port01'])
        checkpoints.append(dict(stem=stem, ram=artifact(ram), snapshot=artifact(snapshot), registers=a['registers']))
    restored = CAPTURE / 'restored-floor-post.vsf'
    final = CAPTURE / 'floor-line-drawn.vsf'
    for module in ('C64MEM', 'MAINCPU'):
        assert native.module_payload(parent, module) == native.module_payload(restored, module)
    before, after = native.physical_ram(restored), native.physical_ram(final)
    assert before[0xb828:0xb82a] == bytes.fromhex('e6 d9')
    assert [i for i in range(65536) if before[i] != after[i]] == [0xd9]
    assert after[0xd9] == (before[0xd9] + 1) & 255
    cpu0, cpu1 = native.cpu_state(restored), native.cpu_state(final)
    assert all(cpu0[k] == cpu1[k] for k in ('a', 'x', 'y', 'sp'))
    flags = (cpu0['flags'] & ~0x82) | (after[0xd9] & 0x80) | (2 if after[0xd9] == 0 else 0)
    assert cpu1['flags'] == flags
    mem0, mem1 = native.module_payload(restored, 'C64MEM'), native.module_payload(final, 'C64MEM')
    assert [i for i in range(len(mem0)) if mem0[i] != mem1[i]] == [4 + 0xd9]
    first_state, final_state = native.read_snapshot(restored), native.read_snapshot(final)
    assert all(first_state['vicii'][key] == final_state['vicii'][key] for key in ('regs',))
    parent_state = native.read_snapshot(parent)
    assert parent_state['cia'] == first_state['cia']
    assert all(parent_state['vicii'][key] == first_state['vicii'][key]
               for key in ('regs', 'raster_line', 'raster_cycle'))
    cia_deltas = {f'{chip}.{key}': [old, final_state['cia'][chip][key]]
                  for chip, values in first_state['cia'].items()
                  for key, old in values.items() if old != final_state['cia'][chip][key]}
    assert cia_deltas == {'CIA1.relative_tod_alarm_cycles': [13312, 13307],
                          'CIA2.timer_b': [60, 55],
                          'CIA2.relative_tod_alarm_cycles': [12808, 12803]}
    assert first_state['vicii']['dbuf_offset'] == 456
    assert final_state['vicii']['dbuf_offset'] == 496
    assert len(final_state['vicii']['dbuf']) >= 488
    result = dict(pass_=True, script=artifact(Path(__file__).resolve()),
                  parent=artifact(parent), parent_owner_receipt=artifact(owner),
                  original_disk=artifact(disk), session_metadata=artifact(CAPTURE / 'session.json'),
                  session=session, transcript=artifact(CAPTURE / 'monitor.log'),
                  restore=dict(complete_C64MEM_equal=True, complete_MAINCPU_equal=True,
                               ports_equal=True, registers_and_beam_equal=True),
                  checkpoints=checkpoints, RAM_snapshot_bytes=131072,
                  restores=1, observation_resumes=1, elapsed_cycles=5,
                  warp_off_before_each_resume=True, observed_speed=100,
                  executed_instruction=dict(pc=0xb828, bytes='e6 d9', mnemonic='INC $D9'),
                  final_RAM_delta=[dict(address=0xd9, before=before[0xd9], after=after[0xd9])],
                  CPU_registers_and_INC_flags_checked=True, CIA_ports_and_configuration_unchanged=True,
                  CIA_elapsed_timer_deltas=cia_deltas,
                  VIC_registers_unchanged=True, DBUF_offsets=[456, 496],
                  data_or_PC_writes=[],
                  scope='Closed original five-cycle continuation; DBUF now covers all384 displayed pixels of line250.',
                  limits=['Final RAM delta does not enumerate individual RMW bus writes.',
                          'Pixel composition belongs to the separate independent sprite checker.',
                          'No upper-wall scanout or whole-demo timing claim.'])
    result['pass'] = result.pop('pass_')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'native-tail-evidence.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('pass', 'elapsed_cycles', 'RAM_snapshot_bytes', 'DBUF_offsets', 'scope')}, indent=2))


if __name__ == '__main__':
    main()
