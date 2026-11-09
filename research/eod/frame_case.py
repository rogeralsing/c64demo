#!/usr/bin/env python3
"""Accept the closed original EOD stage-capture case; start no processes."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'build/research/eod'
CASE = BASE/'native-03'
DISK = BASE/'release/EdgeOfDisgrace_1a.d64'
CASE_SHA = 'b5218a5a088bb0343970327b8ddfc03ea3c177f6bf471db5a739f4bd00817af9'
PINS = {
    'research/eod/controller.py': '033bafb6ac6e97283175ac6713af0eef60cb7991b653ee1c98c47a1a4afa83c9',
    'research/eod/native_boot.py': 'f1c0c0eaa4be5380bec55b84b34461b43b0065689a0ab94342c411dffb53bb55',
    'research/verify_vice_live.py': 'f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a',
    'research/vice_session_live.py': '4340d1b0394fa612f5e6a71edddcbc2daf947e59c4c3013ab3b850c886dc621c',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'build/research/eod/native-03-files.json': '0b98f49bf80efdb114080753047a26cdb4260d7980aded32d78b43d4690e624c',
    'build/research/eod/release/EdgeOfDisgrace_1a.d64': '0624697997c57209929fc36ff7121ec7c61760a88576edbf0768d63e77d28956',
    'build/research/eod/file-analysis/accepted-03/file-proof.json': 'fb8e819f854fd500acb34ea023508a9966f95914f38e1c6de0db77e3f2381db9',
    'build/research/eod/controller-analysis/accepted-01/controller-proof.json': '256828263de51e95cb374db0c177e146e948752f61cc6651ff5371fe956532f6',
    'build/research/quondam/hardware-source/vice-3.10.tar.gz': '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1',
}
STAGES = [
    ('sys', 0x080d, 6979380), ('after52', 0x0709, 418848691),
    ('begin', 0x546a, 469164461), ('ramp', 0x546d, 469164493),
    ('coefficients', 0x5470, 469166308), ('vertices', 0x5473, 469168060),
    ('visibility', 0x5476, 469169677), ('edges', 0x5479, 469182577),
    ('internal', 0x547c, 469200758), ('outer', 0x547f, 469222667),
    ('body-complete', 0x17db, 469222679),
    ('prefix-before', 0x1a73, 469240212),
    ('prefix-filled', 0x1750, 469255307),
    ('prefix-cleared', 0x1753, 469262659),
    ('next-frame', 0x546a, 469262715),
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT/relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to((BASE/'frame-analysis').resolve())
    assert not out.exists(), 'Choose a fresh output directory'
    for name, expected in PINS.items():
        assert sha((ROOT/name).read_bytes()) == expected, name
    wire = load('eod_frame_wire', 'research/verify_vice_live.py')
    wire.BASE, wire.CASE_PINS = BASE, {'native-03': CASE_SHA}
    source = (ROOT/'research/verify_vice_live.py').read_text()
    node = next(n for n in ast.parse(source).body
                if isinstance(n, ast.FunctionDef) and n.name == 'audit_session')
    original = ast.get_source_segment(source, node)+'\n'
    old = 'assert session["startup_mode"] == "manual monitor load" and "-autostart" not in session["command"]'
    replacement = ('assert session["startup_mode"] == "autostart"\n'
        '    assert session["program"] == '+repr(str(DISK))+'\n'
        '    for flag in ("-autostart", "-8"):\n'
        '        assert session["command"].count(flag) == 1\n'
        '        assert session["command"][session["command"].index(flag)+1] == '+repr(str(DISK)))
    assert original.count(old) == 1
    adapted = original.replace(old, replacement)
    exec(compile(adapted, '<exact-EOD-side1a-frame-startup>', 'exec'), wire.__dict__)
    case = wire.audit_session('native-03')
    assert not case['partial'] and not case['cancelled']
    responses = case['responses']
    assert sorted(responses) == list(range(1, 100))
    assert all(r['status'] == 'completed' for r in responses.values())
    assert all(r['purpose'] == 'ordinary' for r in case['requests'])
    commands = [responses[n]['command'] for n in range(1, 100)]
    assert sha(json.dumps(commands, separators=(',', ':')).encode()) == 'f7ecec28d0bdae55e38f80e8036601b8d023385fb6c837b7a7c35dd90963b419'
    assert len(case['waits']) == 1 and case['waits'][0]['sequence'] == 12
    assert case['waits'][0]['received_bytes'] == 0 and responses[12]['command'] == 'x'
    assert not any(e['kind'].startswith('interrupt_') for e in case['events'])
    assert not any(re.search(r'ERROR --|Syntax error|Unknown resource', r['response']) for r in responses.values())
    assert commands[8] == 'warp on' and commands[19:22] == ['warp off', 'warp', 'resourceget "Speed"']
    for n in (21, 98):
        assert 'Warp mode is off.' in responses[n]['response']
    for n in (22, 99):
        assert re.search(r'Speed\s*=\s*100', responses[n]['response'])
    launch = case['session']['command']
    assert '-pal' in launch and launch[launch.index('-speed')+1] == '100'
    assert '+warp' in launch and '+autostart-warp' in launch
    assert '-drive8truedrive' in launch and launch[launch.index('-drive8type')+1] == '1541'
    manifest = json.loads((BASE/'native-03-files.json').read_text())
    listing = [dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
               for p in sorted(CASE.iterdir()) if p.is_file()]
    assert listing == manifest['files'] and len(listing) == manifest['file_count'] == 37
    assert sum(r['bytes'] for r in listing) == manifest['total_bytes'] == 4048269
    controller = load('eod_frame_capture_reader', 'research/eod/controller.py')
    controller.CASE = CASE
    reader = load('eod_frame_snapshot', 'research/quondam/snapshot_state.py')
    memories, captures = controller.capture_pairs(reader, wire, case)
    states = {r['stem']: r['registers'] for r in captures}
    assert set(states) == {s for s, _, _ in STAGES}
    for stem, pc, clock in STAGES:
        assert (states[stem]['pc'], states[stem]['clock']) == (pc, clock)
    for stem, _, _ in STAGES[2:]:
        assert memories[stem][0x1767] == 10 and memories[stem][0x5514] == 1
        assert memories[stem][0x546a:0x547f] == bytes.fromhex('20155520865520595720a95920565b20505d20655e')
        assert memories[stem][0x17d8:0x17e1] == bytes.fromhex('206a5490b2ee671760')
    assert all(states[s]['sp'] == 0xe9 for s, _, _ in STAGES[2:10])
    assert states['body-complete']['sp'] == 0xeb
    m, sp = memories['prefix-before'], states['prefix-before']['sp']
    continuation = ((m[0x101+sp] | m[0x102+sp] << 8)+1)&65535
    assert continuation == 0x1750
    assert states['prefix-filled']['sp'] == sp+2 == states['prefix-cleared']['sp']
    expected_files = [
        ('sys', 'EdgeOfDisgrace_1a/dos-001.raw.prg', 874),
        ('after52', 'EdgeOfDisgrace_1a/trackmo-052.decoded.prg', 13603),
    ]
    payloads = []
    for stem, name, length in expected_files:
        path = BASE/'file-analysis/accepted-03'/name
        start, data = controller.prg(path)
        assert len(data) == length and memories[stem][start:start+length] == data
        payloads.append(dict(source=artifact(path), start=start, bytes=length, all_equal=True))
    previous = json.loads((BASE/'controller-analysis/accepted-01/controller-proof.json').read_text())
    old = next(r for r in previous['captures'] if r['stem'] == 'stable-frame')['ram']
    oldpath = ROOT/old['path']
    oldram = oldpath.read_bytes()
    assert sha(oldram) == old['sha256']
    diffs = [dict(address=i, previous=b, current=a)
             for i, (a, b) in enumerate(zip(memories['begin'], oldram)) if a != b]
    assert diffs == [dict(address=0x146, previous=128, current=0)]
    intervals = [dict(begin=a, end=b, cycles=states[b]['clock']-states[a]['clock'])
                 for (a, _, _), (b, _, _) in zip(STAGES[2:], STAGES[3:])]
    boot = load('eod_frame_port_sources', 'research/eod/native_boot.py')
    ports = boot.primary_port_sources()
    out.mkdir(parents=True)
    checked = Path(__file__).read_bytes()
    (out/'frame_case.checked.py').write_bytes(checked)
    proof = dict(pass_=True, scope='Fresh original EOD side1a stage captures and full state-pair custody; no independent shader arithmetic or displayed-image acceptance',
        producer=artifact(Path(__file__)), inputs=[artifact(ROOT/p) for p in PINS],
        original_payloads=payloads, case_sha256=CASE_SHA, wire=wire.summary(case), captures=captures,
        adapter=dict(original_function_sha256=sha(original.encode()), adapted_function_sha256=sha(adapted.encode()),
                     exact_startup_replacement=replacement), primary_port_schema=ports,
        previous_case_input=artifact(oldpath), previous_begin_RAM_differences=diffs,
        consecutive_intervals=intervals,
        limits=['Fresh disk boot; no restore, manual RAM/register/PC patch, interrupt, retry or dropped wait event.',
                'Only the startup assertion is adapted; the frozen wire/capture readers remain unchanged.',
                'Warp is declared for navigation; actual off/Speed100 queries bound stage observations.',
                'All15RAM/VSFpairs agree; single old stack byte0146 prevents a whole-RAM cross-case equality claim.',
                'Code/stage/caller boundaries and elapsed cycles do not themselves prove correct 3D math, all output pixels, publication, FPS or speedups.'],
        outputs=[dict(name='frame_case.checked.py', bytes=len(checked), sha256=sha(checked))])
    raw = (json.dumps(proof, indent=2)+'\n').encode()
    (out/'frame-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=True, pairs=len(captures), receipt_bytes=len(raw), receipt_sha256=sha(raw))))


if __name__ == '__main__':
    main()
