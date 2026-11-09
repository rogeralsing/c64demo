#!/usr/bin/env python3
"""Accept one closed original EOD side-1a controller/loader observation."""
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
CASE = BASE/'native-02'
DISK = BASE/'release/EdgeOfDisgrace_1a.d64'
EXTRACT = BASE/'file-analysis/accepted-03'
# Filled only after the native owner closes and pins this case. A live case
# must never be accepted merely because its currently visible files parse.
CASE_SHA = '03b3a0faabf52736b3bb2cc176f4f98a12d4443f5a3d5395d636a91caae9b24c'
CASE_MANIFEST_SHA = '4c7662ac3499bd7b0addd8085c08e398dfa9953cc50ea4ab5a7cd0abba400283'
PINS = {
    'research/verify_vice_live.py': 'f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a',
    'research/vice_session_live.py': '4340d1b0394fa612f5e6a71edddcbc2daf947e59c4c3013ab3b850c886dc621c',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'research/eod/native_boot.py': 'f1c0c0eaa4be5380bec55b84b34461b43b0065689a0ab94342c411dffb53bb55',
    'research/eod/extract.py': '3d64cdd4ec2671a9b70126448a75db0802fcc84815558287f931fbea78284094',
    'build/research/eod/file-analysis/accepted-03/file-proof.json': 'fb8e819f854fd500acb34ea023508a9966f95914f38e1c6de0db77e3f2381db9',
    'build/research/eod/release/EdgeOfDisgrace_1a.d64': '0624697997c57209929fc36ff7121ec7c61760a88576edbf0768d63e77d28956',
    'build/research/eod/release/EdgeOfDisgrace_1b.d64': 'b348369ba5c7644019e4bf7f3cb8a5e81529b220e10b76dc5c0b7ad548310628',
    'build/research/eod/native-02-files.json': CASE_MANIFEST_SHA,
    'build/research/quondam/hardware-source/vice-3.10.tar.gz': '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prg(path):
    raw = path.read_bytes()
    accepted = json.loads((EXTRACT/'file-proof.json').read_text())
    relative = str(path.relative_to(EXTRACT))
    record = next(r for r in accepted['outputs'] if r['name'] == relative)
    assert len(raw) == record['bytes'] and sha(raw) == record['sha256']
    start = int.from_bytes(raw[:2], 'little')
    assert start+len(raw)-2 <= 65536
    return start, raw[2:]


def static_map(extractor):
    """Declared byte placements, not a CPU execution or prediction of drive state."""
    a_path = EXTRACT/'EdgeOfDisgrace_1a/dos-001.decoded.prg'
    b_path = EXTRACT/'EdgeOfDisgrace_1b/dos-001.decoded.prg'
    start, a = prg(a_path)
    b_start, b = prg(b_path)
    assert start == b_start == 0x900 and len(a) == len(b) == 800
    assert [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y] == [(0x4b, 0xb1, 0xb2)]
    view = bytes(0x900)+a
    assert view[0x91d:0x925] == bytes.fromhex('20570978a9358501')
    assert view[0x92d:0x94a] == bytes.fromhex('a200bd000a9d0002bd000b9d0003bd000c9d0004bd400c9d4004e8d0e5')
    assert view[0x94a:0x957] == bytes.fromhex('a9b1200002a9002000024c4004')
    command = view[0x983:0x9ac]
    assert command == bytes.fromhex('4d2d450d021212120f120c1209a207bd05029506ca10f8a203a9809500a901d500d0fcca10f34ce904')
    disk = DISK.read_bytes()
    drive = bytearray(0x700)
    jobs = []
    for slot, sector in enumerate((18, 15, 12, 9)):
        dest = 0x300+256*slot
        raw = extractor.block(disk, 18, sector)
        drive[dest:dest+256] = raw
        jobs.append(dict(job=slot, track=18, sector=sector, buffer=dest, sha256=sha(raw)))
    assert drive[0x4fe:0x50f] == bytes.fromhex('208c05302b0aaabdae058506bdaf058507')
    assert drive[0x52e:0x53a] == bytes.fromhex('297f8586a912a200850e860f')
    assert drive[0x542:0x54c] == bytes.fromhex('207d05adff07c586d0f6')
    assert drive[0x560:0x575] == bytes.fromhex('a206860f207d05a200bd00079dae05e8d0f74cf204')
    assert extractor.block(disk, 18, 0)[255] == 0x31
    assert extractor.block((BASE/'release/EdgeOfDisgrace_1b.d64').read_bytes(), 18, 0)[255] == 0x32
    loader = view[0xa00:0xc18]
    assert len(loader) == 536
    assert loader[:0x32] == bytes.fromhex('4820ff03681010a9088d00dd2c00dd10fba9008d00dd6020390338e90385d6a90085d784d486d5a002b1d499d1008810f818')
    controller_path = EXTRACT/'EdgeOfDisgrace_1a/trackmo-000.decoded.prg'
    c_start, controller = prg(controller_path)
    assert c_start == 0x440 and len(controller) == 872
    c = bytes(c_start)+controller
    assert c[0x440:0x446] == bytes.fromhex('4cb3044cca04')
    assert c[0x4b3:0x4d8] == bytes.fromhex('207804a901200002a902200002a903200002a904200002a90085fe85ffa9208d5a042000a0')
    late = c[0x6ee:0x722]
    assert late == bytes.fromhex('20000aa932200002200088a93320000220038820000fa934200002a93520000220030f20060f20090f200c0f200f0fa936200002')
    calls = [dict(request_PC=0x6f3, index=50, next_PC=0x6f6),
             dict(request_PC=0x6fb, index=51, next_PC=0x6fe),
             dict(request_PC=0x706, index=52, next_PC=0x709),
             dict(request_PC=0x70b, index=53, next_PC=0x70e)]
    return dict(boot_inputs=[artifact(a_path), artifact(b_path)],
        boot_only_side_difference=dict(address=0x94b, side1a=0xb1, side1b=0xb2),
        drive_init=dict(command_address=0x983, command_hex=command.hex(), device=8,
            secondary=0x6f, execute_drive_PC=0x20d, jobs=jobs, job_execution_order=[3, 2, 1, 0],
            post_jobs_drive_PC=0x4e9),
        API=dict(C64_entry=0x200, send_A=0x3ff, positive='A0..127 addresses pair index A; original index bounds still apply',
            disk_select='Negative A compares (A AND7F) with loaded BAM byte07FF, then loads indexT18S6',
            drive_receiver=0x58c, drive_index_base=0x5ae, index_copy_end_exclusive=0x6ae,
            disk_markers=[0x31, 0x32], compressed_payload_header='D1=first-bit byte; D2/D3=destination from three received data bytes',
            header_initialization_PC=[0x227, 0x231], original_end_RTS=0x323,
            register_limit='A/X/Y and flags are scratch; API does not generally preserve caller state.',
            handshake_limit='C64094F post-disk-select return precedes possible drive index read/copy; it is not an index-completion witness.'),
        loader_source=[0xa00, 0xc18], installed_code_range=[0x200, 0x418],
        controller=artifact(controller_path), controller_jump_entries=[0x440, 0x443],
        late_calls=calls, late_bytes=dict(start=0x6ee, end_exclusive=0x722, hex=late.hex()),
        navigation='Fresh original side1a emergency DOS boot can initialize its own drive/controller; no disk0 request in this path. Native execution remains separately checked.'), loader


def audit_wire():
    assert not CASE_SHA.startswith('PENDING'), 'Only accept an owner-closed, pinned case'
    wire = load('eod_controller_wire', 'research/verify_vice_live.py')
    wire.BASE, wire.CASE_PINS = BASE, {'native-02': CASE_SHA}
    source = (ROOT/'research/verify_vice_live.py').read_text()
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'audit_session')
    original = ast.get_source_segment(source, node)+'\n'
    old = 'assert session["startup_mode"] == "manual monitor load" and "-autostart" not in session["command"]'
    replacement = ('assert session["startup_mode"] == "autostart"\n'
                   '    assert session["program"] == '+repr(str(DISK))+'\n'
                   '    for flag in ("-autostart", "-8"):\n'
                   '        assert session["command"].count(flag) == 1\n'
                   '        assert session["command"][session["command"].index(flag)+1] == '+repr(str(DISK)))
    assert original.count(old) == 1
    adapted = original.replace(old, replacement)
    exec(compile(adapted, '<exact-original-eod-side1a-autostart>', 'exec'), wire.__dict__)
    case = wire.audit_session('native-02')
    assert not case['partial'] and not case['cancelled']
    responses = case['responses']
    assert sorted(responses) == list(range(1, 102))
    assert all(r['status'] == 'completed' for r in responses.values())
    assert all(r['purpose'] == 'ordinary' for r in case['requests'])
    commands = [responses[n]['command'] for n in range(1, 102)]
    assert sha(json.dumps(commands, separators=(',', ':')).encode()) == '6e7201877793c86d9e56e9793504fe41f5230b7af4cb30c27ea263d4de7b6045'
    assert not any(re.search(r'ERROR --|Syntax error|Unknown resource', r['response']) for r in responses.values())
    assert len(case['waits']) == 1 and case['waits'][0] == dict(
        utc='2026-11-08T18:01:23.181521+00:00', kind='observation_timeout', status='partial',
        waiting=True, elapsed_seconds=30.058, sequence=26, id='navigate-candidate-gouraud', command='x',
        internal=False, received_bytes=0, action='Still pending; send interrupt or close. No retry or restart.')
    assert not [e for e in case['events'] if e['kind'] in ('interrupt_requested', 'interrupt_rejected')]
    assert commands[24] == 'warp on' and commands[50:53] == ['warp off', 'warp', 'resourceget "Speed"']
    assert commands[99:101] == ['warp', 'resourceget "Speed"']
    for n in (52, 100):
        assert 'Warp mode is off.' in responses[n]['response']
    for n in (53, 101):
        assert re.search(r'Speed\s*=\s*100', responses[n]['response'])
    launch = case['session']['command']
    assert '-pal' in launch and launch[launch.index('-speed')+1] == '100'
    assert '+warp' in launch and '+autostart-warp' in launch
    assert launch[launch.index('-drive8type')+1] == '1541' and '-drive8truedrive' in launch
    manifest = json.loads((BASE/'native-02-files.json').read_text())
    listing = [dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
               for p in sorted(CASE.iterdir()) if p.is_file()]
    assert listing == manifest['files'] and len(listing) == manifest['file_count'] == 36
    assert sum(r['bytes'] for r in listing) == manifest['total_bytes'] == 3820648
    assert sha(json.dumps(listing, sort_keys=True, separators=(',', ':')).encode()) == manifest['listing_sha256'] == CASE_SHA
    return wire, case, dict(original_function_sha256=sha(original.encode()),
        adapted_function_sha256=sha(adapted.encode()), exact_startup_replacement=replacement)


def capture_pairs(reader, wire, case):
    """Same-stop wire/physical-RAM/snapshot checks for every saved pair."""
    responses, memories, records = case['responses'], {}, []
    pattern = re.compile(r'bsave "'+re.escape(str(CASE))+r'/([a-z0-9-]+)-ram\.bin" 0 0000 ffff')
    for save in sorted(responses):
        match = pattern.fullmatch(responses[save]['command'])
        if not match:
            continue
        stem = match[1]
        assert responses[save-1]['command'] == 'r'
        assert responses[save+1]['command'] == f'dump "{CASE}/{stem}.vsf"'
        regs = wire.registers(responses[save-1]['response'])
        stop = max(n for n in responses if n < save and responses[n]['command'] in ('x', 'exit'))
        stopped = list(re.finditer(r'^#\d+ \(Stop on\s+exec ([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\n'
            r'\.C:[^\n]+\s+(\d+)\n', responses[stop]['response'], re.M | re.I))[-1]
        assert int(stopped[1], 16) == regs['pc']
        assert tuple(map(int, stopped.groups()[1:])) == (regs['line'], regs['cycle'], regs['clock'])
        assert not any(responses[n]['command'] in ('x', 'exit') for n in range(stop+1, save+2))
        rawpath, vsfpath = CASE/f'{stem}-ram.bin', CASE/f'{stem}.vsf'
        raw = rawpath.read_bytes()
        mem, cpu = reader.module_payload(vsfpath, 'C64MEM'), reader.module_payload(vsfpath, 'MAINCPU')
        state = reader.read_snapshot(vsfpath)
        assert len(raw) == 65536 and raw == mem[4:65540]
        assert state['modules']['C64MEM']['version'] == [0, 1] and len(mem) == 65555
        assert mem[65543:] == bytes(12)
        assert mem[1] == mem[65542] == regs['port00'] == 0x2f
        assert mem[65541] == regs['port01'] and mem[0] & mem[1] == regs['port01'] & mem[1]
        expected = dict(clock=int.from_bytes(cpu[:8], 'little'), a=cpu[8], x=cpu[9], y=cpu[10], sp=cpu[11],
            pc=int.from_bytes(cpu[12:14], 'little'), flags=cpu[14])
        assert all(regs[k] == v for k, v in expected.items())
        assert (state['vicii']['raster_line'], state['vicii']['raster_cycle']) == (regs['line'], regs['cycle'])
        assert (regs['clock']//63 % 312, regs['clock'] % 63) == (regs['line'], regs['cycle'])
        memories[stem] = raw
        records.append(dict(stem=stem, stop_sequence=stop, register_sequence=save-1,
            save_sequence=save, snapshot_sequence=save+1, registers=regs, ram=artifact(rawpath),
            snapshot=artifact(vsfpath), all65536_physical_RAM_bytes_equal=True, CPU_clock_flags_and_beam_equal=True,
            ports=dict(latch=mem[0], DDR=mem[1], data_out=mem[65540], data_read=mem[65541], dir_read=mem[65542],
                monitor_readback_equal=True, driven_output_bits_equal=True, unused_state_zero=True)))
    assert len(records) == len(list(CASE.glob('*.vsf'))) == len(list(CASE.glob('*-ram.bin')))
    return memories, records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to((BASE/'controller-analysis').resolve())
    assert not out.exists(), 'Choose a fresh output directory'
    for name, pin in PINS.items():
        assert sha((ROOT/name).read_bytes()) == pin, name
    extractor = load('eod_pinned_extractor', 'research/eod/extract.py')
    static, installed_loader = static_map(extractor)
    wire, case, adapter = audit_wire()
    reader = load('eod_controller_snapshots', 'research/quondam/snapshot_state.py')
    boot = load('eod_frozen_boot_sources', 'research/eod/native_boot.py')
    memories, captures = capture_pairs(reader, wire, case)
    states = {r['stem']: r['registers'] for r in captures}
    expected = {
        'sys': (0x80d, 6976276), 'unpacked': (0x900, 7091534), 'controller': (0x440, 10194824),
        'rejected-candidate': (0x546a, 215921314), 'before51': (0x6fb, 398251001),
        'after51': (0x6fe, 401192343), 'after52': (0x709, 418848691),
        'gouraud-first': (0x546a, 468122687), 'gouraud-first-complete': (0x17db, 468169304),
        'stable-frame': (0x546a, 469164461), 'thin-line': (0x1856, 469182934),
        'thin-line-complete': (0x5e62, 469183449), 'stable-frame-complete': (0x17db, 469222679),
        'next-frame': (0x546a, 469262715),
    }
    assert set(states) == set(expected)
    assert all((states[k]['pc'], states[k]['clock']) == v for k, v in expected.items())
    source_files, payload_checks = [], []
    rawpath = EXTRACT/'EdgeOfDisgrace_1a/dos-001.raw.prg'
    start, data = prg(rawpath)
    assert start == 0x801 and len(data) == 874 and memories['sys'][start:start+len(data)] == data
    source_files.append(rawpath)
    payload_checks.append(dict(capture='sys', source=artifact(rawpath), start=start, bytes=len(data), all_bytes_equal=True))
    for stem, relative, length in (
            ('unpacked', 'EdgeOfDisgrace_1a/dos-001.decoded.prg', 800),
            ('controller', 'EdgeOfDisgrace_1a/trackmo-000.decoded.prg', 872),
            ('after51', 'EdgeOfDisgrace_1a/trackmo-051.decoded.prg', 10461),
            ('after52', 'EdgeOfDisgrace_1a/trackmo-052.decoded.prg', 13603)):
        path = EXTRACT/relative
        start, data = prg(path)
        assert len(data) == length and memories[stem][start:start+length] == data
        source_files.append(path)
        payload_checks.append(dict(capture=stem, source=artifact(path), start=start,
            end_exclusive=start+length, bytes=length, all_bytes_equal=True, mismatches=0))
    actual_loader = memories['controller'][0x200:0x418]
    patches = [dict(address=0x200+i, original=a, actual=b)
        for i, (a, b) in enumerate(zip(installed_loader, actual_loader)) if a != b]
    assert {p['address'] for p in patches} <= {0x364, 0x3eb, 0x3f8, 0x3fa, 0x3fb}
    assert states['before51']['a'] == 0x33
    for stem in ('after51', 'after52'):
        assert states[stem]['a'] == 0 and states[stem]['flags'] & 1 and not states[stem]['flags'] & 8
    _, engine = prg(EXTRACT/'EdgeOfDisgrace_1a/trackmo-051.decoded.prg')
    engine = bytes(0x800)+engine
    _, shader = prg(EXTRACT/'EdgeOfDisgrace_1a/trackmo-052.decoded.prg')
    shader = bytes(0x30dd)+shader
    assert engine[0x17d8:0x17e1] == bytes.fromhex('206a5490b2ee671760')
    assert shader[0x5467:0x546d] == bytes.fromhex('4c8554201555')
    assert memories['rejected-candidate'][0x546a:0x546c] == bytes.fromhex('7110')
    assert memories['rejected-candidate'][0x546a:0x546d] != shader[0x546a:0x546d]
    for stem in ('gouraud-first', 'gouraud-first-complete', 'stable-frame', 'thin-line',
                 'thin-line-complete', 'stable-frame-complete', 'next-frame'):
        m = memories[stem]
        assert m[0x1767] == 10 and m[0x17d8:0x17e1] == engine[0x17d8:0x17e1]
        assert m[0x5467:0x546d] == shader[0x5467:0x546d]
    for stem in ('stable-frame', 'thin-line', 'thin-line-complete', 'stable-frame-complete', 'next-frame'):
        assert memories[stem][0x5514] == 1
    thin = memories['thin-line']
    assert list(thin[0x10:0x14]) == [32, 40, 72, 60] and thin[0x15] == 4
    def continuation(stem):
        sp = states[stem]['sp']
        m = memories[stem]
        return ((m[0x100+((sp+1)&255)] | m[0x100+((sp+2)&255)] << 8)+1)&65535
    assert continuation('gouraud-first') == continuation('stable-frame') == 0x17db
    assert continuation('thin-line') == 0x5e62
    assert (states['thin-line-complete']['sp']-states['thin-line']['sp']) & 255 == 2
    assert (states['stable-frame-complete']['sp']-states['stable-frame']['sp']) & 255 == 2
    intervals = dict(first_body=states['gouraud-first-complete']['clock']-states['gouraud-first']['clock'],
        stable_body=states['stable-frame-complete']['clock']-states['stable-frame']['clock'],
        thin_line=states['thin-line-complete']['clock']-states['thin-line']['clock'],
        stable_begin_to_next_begin=states['next-frame']['clock']-states['stable-frame']['clock'])
    assert intervals == dict(first_body=46617, stable_body=58218, thin_line=515, stable_begin_to_next_begin=98254)
    assert engine[0x174b:0x1758] == bytes.fromhex('c60120731a20781ae601206817')
    assert engine[0x1a73:0x1a7d] == bytes.fromhex('a2004c00d8a9004c00c4')
    assert engine[0x125c:0x1262] == bytes.fromhex('4d00788d0070')
    ports = boot.primary_port_sources()
    out.mkdir(parents=True)
    outputs = []
    for name, raw in (('loader-0200-source.bin', installed_loader), ('controller.checked.py', Path(__file__).read_bytes())):
        (out/name).write_bytes(raw)
        outputs.append(dict(name=name, bytes=len(raw), sha256=sha(raw)))
    proof = dict(pass_=True, scope='Original side1a bootstrap/controller and complete native payload51/52 bindings plus guarded shader-entry/one-line boundaries; no shader arithmetic or full-pixel claim',
        producer=artifact(Path(__file__)), inputs=[artifact(ROOT/p) for p in PINS]+[artifact(p) for p in source_files],
        case_sha256=CASE_SHA, wire=wire.summary(case), exact_auditor_adaptation=adapter,
        captures=captures, primary_port_schema=ports, static_map=static,
        original_payload_checks=payload_checks, installed_loader=dict(bytes=536, documented_modified_operands=patches,
            unchanged_code_bytes=536-len(patches), no_other_differences=True),
        rejected_phase=dict(capture='rejected-candidate', PC=0x546a, wrong_prefix='7110',
            correct_prefix=shader[0x546a:0x546d].hex(), reason='Earlier overlay uses same PC; rejected before original51/52 load-return binding'),
        shader_witness=dict(state_address=0x1767, state=10, stable_ramp_address=0x5514, stable_ramp=1,
            frame_entry=0x546a, frame_caller=0x17d8, frame_continuation=0x17db,
            thin_entry=0x1856, thin_continuation=0x5e62, thin_input_XY=[32,40,72,60], thin_mask=4,
            actual_saved_stack_continuations_checked=True),
        elapsed_machine_cycles=intervals,
        cadence_limit=dict(outside_stable_body=98254-58218, begin_samples=1,
            source_work='Original IRQ174D prefix reconstruction through1A73/D800 and1750 marker clear through1A78/C400 precede the1768/17D8 shader dispatch.',
            residue_not_exclusively_attributed=True, delivered_FPS_claimed=False),
        limits=['Navigation warp is explicit; proof windows follow warp-off and Speed100 queries, rechecked at the endpoint.',
            'Original source/API placement is a byte map, not a drive CPU or IEC cycle simulation. C64094F proves handshake, not completed index-copy timing.',
            'This accepts complete payload51/52 bytes at their real load returns, not every decoded candidate or whole-demo execution.',
            'One-line/native boundary evidence is exposed for a separate independent shader model; complete output pixels are not reconstructed here.',
            'The98254-cycle begin-to-begin sample is one interval, not deliveredFPS or a full-animation cadence distribution.',
            'PNG is cosmetic context only; no screenshot-derived pixel or shading acceptance.',
            'No downloaded host code, CPU interpreter, emulator, subprocess, build or new native execution occurs in this producer.'], outputs=outputs)
    raw = (json.dumps(proof, indent=2)+'\n').encode()
    (out/'controller-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=True, receipt_bytes=len(raw), receipt_sha256=sha(raw), pairs=len(captures),
        native_payload_bytes=sum(r['bytes'] for r in payload_checks), elapsed_machine_cycles=intervals), indent=2))


if __name__ == '__main__':
    main()
