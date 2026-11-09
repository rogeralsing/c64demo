#!/usr/bin/env python3
"""Audit the closed original Aloft run without starting VICE or a CPU model."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-20261109'
CASE = BASE / 'native-01'
DISK = BASE / 'disk-analysis/accepted-01/Aloft-Side1.d64'
CASE_SHA = '0164e695fa631e1789304a636381dcd4c460d11e61a89343b365d0d87844a187'
PINS = {
    'research/vice_session_live.py': '4340d1b0394fa612f5e6a71edddcbc2daf947e59c4c3013ab3b850c886dc621c',
    'research/verify_vice_live.py': 'f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'build/research/aloft-20261109/native-01-files.json': 'db333462f5b220f3eb987e13099de52e7c9bced440528182851dce9cfc93c65b',
    'build/research/aloft-20261109/disk-analysis/accepted-01/Aloft-Side1.d64': 'd13eae8daeada64bc61772a2dad2d3e62d1a0d30a34b29103119535610e4cfce',
    'build/research/quondam/hardware-source/vice-3.10.tar.gz': '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1',
    'build/research/aloft-20261109/native-analysis/beam-source-01/c64.c': '967a52413c31b43f0b51c793d608c171e34aa31728230b03391327bcca1a9352',
    'build/research/aloft-20261109/native-analysis/beam-source-01/vicii-cycle.c': '561876187fde8bfe8636e64593543aa77a5e0855ebbd9fe56d9da4fa6eb564ba',
    'build/research/aloft-20261109/native-analysis/beam-source-01/vicii-snapshot.c': 'de023a097745605ede9fba5a25c3cf66ea9a86030671133e8092c124566f83b7',
    'build/research/aloft-20261109/native-analysis/beam-source-01/viciitypes.h': 'c6178cc2e026dcd85640a3ab4b9cd6609713731560e0bbbe4b1a7d8764588493',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def meta(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=sha(data))


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    assert out.is_relative_to(BASE / 'native-analysis') and not out.exists()
    for name, pin in PINS.items():
        assert sha((ROOT / name).read_bytes()) == pin, name
    beam_source = BASE / 'native-analysis/beam-source-01'
    machine = (beam_source / 'c64.c').read_text()
    cycle_source = (beam_source / 'vicii-cycle.c').read_text()
    assert '*line = (unsigned int)((maincpu_clk) / machine_timing.cycles_per_line % machine_timing.screen_lines);' in machine
    assert '#define VICII_PAL_CYCLE(c) ((c) - 1)' in (beam_source / 'viciitypes.h').read_text()
    assert 'if (vicii.raster_line == vicii.screen_height - 1) {\n        vicii.start_of_frame = 1;' in cycle_source
    assert 'if (vicii.start_of_frame) {\n        if (vicii.raster_cycle == VICII_PAL_CYCLE(2)) {\n            vicii_cycle_start_of_frame();' in cycle_source
    listing = json.loads((BASE / 'native-01-files.json').read_text())
    actual = [dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
              for p in sorted(CASE.iterdir())]
    assert actual == listing['files'] and len(actual) == listing['file_count'] == 71
    assert sum(p['bytes'] for p in actual) == listing['bytes'] == 7001061
    assert sha(json.dumps(actual, sort_keys=True, separators=(',', ':')).encode()) == CASE_SHA

    # Reuse the pinned strict wire auditor. Only its old manual-start assertion
    # changes: this case autostarts the original disk instead of monitor-loading.
    wire = load('aloft_frozen_wire', 'research/verify_vice_live.py')
    wire.BASE, wire.CASE_PINS = BASE, {'native-01': CASE_SHA}
    text = (ROOT / 'research/verify_vice_live.py').read_text()
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == 'audit_session')
    original = ast.get_source_segment(text, node)
    old = 'assert session["startup_mode"] == "manual monitor load" and "-autostart" not in session["command"]'
    replacement = ('assert session["startup_mode"] == "autostart"\n'
        '    assert session["program"] == ' + repr(str(DISK)) + '\n'
        '    for flag in ("-autostart", "-8"):\n'
        '        assert session["command"].count(flag) == 1\n'
        '        assert session["command"][session["command"].index(flag)+1] == ' + repr(str(DISK)))
    assert original.count(old) == 1
    adapted = original.replace(old, replacement)
    exec(compile(adapted, '<Aloft-original-disk-startup-only-adapter>', 'exec'), wire.__dict__)
    case = wire.audit_session('native-01')
    rows = case['responses']
    assert sorted(rows) == list(range(1, 193)) and not case['partial'] and not case['cancelled']
    assert [n for n, row in rows.items() if row['status'] == 'interrupted'] == [4]
    assert len(case['waits']) == 1 and case['waits'][0]['sequence'] == 4
    assert sum(not row['internal'] for row in rows.values()) == 190
    assert len([r for r in case['requests'] if r['purpose'] == 'interrupt']) == 1
    permitted = re.compile(r'(?:r|x|bank ram|sidefx off|warp(?: on)?|resourceget "(?:Speed|VICIIModel|VICIIBorderMode)"|dummy|io|(?:enable|disable) \d+|ignore \d+ \$[0-9a-f]+|break(?: .+)?|bsave ".+" 0 0000 ffff|dump ".+"|screenshot ".+" 2|[dm] [\$0-9a-f ]+)')
    assert all(permitted.fullmatch(row['command']) for row in rows.values())
    assert not any(re.search(r'ERROR --|Syntax error|Unknown resource', row['response']) for row in rows.values())
    launch = case['session']['command']
    assert '-pal' in launch and '-drive8truedrive' in launch
    assert launch[launch.index('-drive8type') + 1] == '1541'
    assert rows[2]['command'] == 'sidefx off'
    rawwire = case['wire']['received']

    # Bind every natural stop to its actual, previously created checkpoint.
    points, stops = {}, {}
    for sequence, row in sorted(rows.items()):
        command, response = row['command'], row['response']
        if command.startswith('break '):
            match = re.search(r'BREAK: (\d+)  C:\$([0-9a-f]{4})  \(Stop on exec\)', response)
            assert match and int(match[1]) not in points
            points[int(match[1])] = dict(PC=int(match[2], 16), enabled=True, created_sequence=sequence,
                                        setup_command=command, setup_response_sha256=sha(rawwire[row['received_first']:row['received_end']]))
        elif command.startswith(('enable ', 'disable ')):
            action, number = command.split()
            assert int(number) in points
            points[int(number)]['enabled'] = action == 'enable'
        elif command == 'x' and row['status'] == 'completed':
            match = re.fullmatch(r'#(\d+) \(Stop on\s+exec ([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\n\.C:[^\n]+\s+(\d+)\n\(C:\$[0-9a-f]{4}\) ', response)
            assert match, sequence
            number = int(match[1])
            assert points[number]['enabled'] and points[number]['PC'] == int(match[2], 16)
            assert points[number]['created_sequence'] < sequence and number != 1
            stops[sequence] = dict(checkpoint=number, pc=int(match[2], 16), line=int(match[3]),
                                   cycle=int(match[4]), clock=int(match[5]), natural=True)

    reader = load('aloft_frozen_snapshots', 'research/quondam/snapshot_state.py')
    captures = []
    for sequence, row in sorted(rows.items()):
        match = re.fullmatch(r'bsave "' + re.escape(str(CASE)) + r'/([a-z0-9-]+)-ram.bin" 0 0000 ffff', row['command'])
        if not match:
            continue
        stem = match[1]
        stop = max(n for n in rows if n < sequence and rows[n]['command'] == 'x')
        latest = [n for n in rows if stop < n < sequence and rows[n]['command'] == 'r']
        register_sequence = max(latest) if latest else stop
        regs = wire.registers(rows[register_sequence]['response'])
        if stop == 4:
            assert stem == 'orientation' and register_sequence == 4
            assert rows[4]['interrupt']['command'] == 'r'
            origin = dict(natural=False, pc=regs['pc'], line=regs['line'], cycle=regs['cycle'], clock=regs['clock'])
        else:
            origin = stops[stop]
            assert all(origin[k] == regs[k] for k in ('pc', 'line', 'cycle', 'clock'))
        assert rows[sequence + 1]['command'] == f'dump "{CASE}/{stem}.vsf"'
        assert not any(rows[n]['command'] == 'x' for n in range(stop + 1, sequence + 2))
        ram, snapshot = CASE / f'{stem}-ram.bin', CASE / f'{stem}.vsf'
        data = ram.read_bytes()
        mem, cpu = reader.module_payload(snapshot, 'C64MEM'), reader.module_payload(snapshot, 'MAINCPU')
        state = reader.read_snapshot(snapshot)
        assert len(data) == 65536 and data == mem[4:65540] and len(mem) == 65555
        assert state['modules']['C64MEM']['version'] == [0, 1] and mem[65543:] == bytes(12)
        assert mem[1] == mem[65542] == regs['port00']
        assert mem[65541] == regs['port01'] and mem[0] & mem[1] == regs['port01'] & mem[1]
        expected = dict(clock=int.from_bytes(cpu[:8], 'little'), a=cpu[8], x=cpu[9], y=cpu[10], sp=cpu[11],
                        pc=int.from_bytes(cpu[12:14], 'little'), flags=cpu[14])
        assert all(regs[k] == v for k, v in expected.items())
        vic = state['vicii']
        core_beam = (vic['raster_line'], vic['raster_cycle'])
        monitor_beam = (regs['line'], regs['cycle'])
        if core_beam != monitor_beam:
            assert stem == 'orientation' and core_beam == (311, 0) and monitor_beam == (0, 0)
            assert vic['start_of_frame'] == 1 and vic['model'] == 1
        assert (regs['clock'] // 63 % 312, regs['clock'] % 63) == (regs['line'], regs['cycle'])
        captures.append(dict(stem=stem, stop_sequence=stop, register_sequence=register_sequence,
            save_sequence=sequence, snapshot_sequence=sequence + 1, registers=regs, stop=origin,
            ram=meta(ram), snapshot=meta(snapshot), all65536_physical_RAM_bytes_equal=True,
            CPU_clock_flags_and_ports_equal=True,
            beam=dict(monitor_CPU_derived=list(monitor_beam), VIC_core=list(core_beam),
                equal=core_beam == monitor_beam, start_of_frame=vic['start_of_frame'],
                frame_wrap_reset_deferred_to_zero_based_cycle1=core_beam != monitor_beam),
            wrapper_counter=data[0x88d],
            current_VIC_registers=vic['regs'], CIA2=state['cia']['CIA2'],
            limits='Current boundary state is not a full-field mode, independently composed pixels, or a resource identity.'))
    assert len(captures) == len(list(CASE.glob('*.vsf'))) == len(list(CASE.glob('*-ram.bin'))) == 25
    assert sum(c['stop']['natural'] for c in captures) == 24
    images = []
    for image in sorted(CASE.glob('*.png')):
        data = image.read_bytes()
        assert data[:8] == b'\x89PNG\r\n\x1a\n' and data[12:16] == b'IHDR'
        width, height = struct.unpack('>II', data[16:24])
        assert (width, height) == (384, 272)
        assert len([r for r in rows.values() if r['command'] == f'screenshot "{image}" 2']) == 1
        images.append(dict(artifact=meta(image), width=width, height=height))
    assert len(images) == 14
    for sequence, prefix in [(187, 'Warp mode is on.'), (188, 'Speed=100'), (189, 'VICIIModel=1'),
                             (190, 'VICIIBorderMode=0'), (191, 'Checkpoints will not trigger on dummy accesses.')]:
        assert rows[sequence]['response'].startswith(prefix + '\n')
    proof = dict(pass_=True, scope='Closed original Aloft side1 native custody and same-stop state only.',
        producer=meta(Path(__file__)), inputs=[meta(ROOT / n) for n in PINS],
        original_disk=meta(DISK), case_manifest=meta(BASE / 'native-01-files.json'),
        session=case['session'], case_files=case['files'], event_count=len(case['events']),
        wire={k: dict(bytes=len(v), sha256=sha(v)) for k, v in case['wire'].items()},
        response_count=192, public_commands=190, completed_responses=191, interrupted_responses=1,
        waits=case['waits'], natural_stops=stops, captures=captures, images=images,
        startup_adapter=dict(original_function_sha256=sha(original.encode()), adapted_function_sha256=sha(adapted.encode()),
            exact_old_assertion=old, exact_replacement=replacement, replacements=1),
        limits=['The initial guarded SYS0810 stop was not observed. Its cause is unresolved; no startup checkpoint/first-payload success is inferred.',
                'Orientation is an explicitly interrupted observation, not a natural requested source phase.',
                'Warp was enabled after orientation. No delivered FPS, animation duration or product optimization follows.',
                'No target CPU interpreter, emulator, process, network or downloaded host code runs in this passive audit.',
                'No PC/RAM write, snapshot restore, disk change or process restart appears on the original command wire.',
                'Images and full snapshot states are native observations, not independently predicted committed pixels.'])
    out.mkdir(parents=True)
    (out / 'native.checked.py').write_bytes(Path(__file__).read_bytes())
    path = out / 'native-proof.json'
    path.write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps(dict(pass_=True, captures=len(captures), natural_captures=24, original_case_reaped=True, proof=meta(path))))


if __name__ == '__main__':
    main()
