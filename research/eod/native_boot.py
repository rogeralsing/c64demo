#!/usr/bin/env python3
"""Passively accept EOD's original disk-0 SFX and complete native unpacked payload."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tarfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'build/research/eod'
CASE = BASE/'native-01'
DISK = BASE/'release/EdgeOfDisgrace_0.d64'
CASE_SHA = '0acb6d27127338b7634e4cb1a68e5c62f60f88f5f458fcc191ea91b0f057dd0c'
EXTRACT = BASE/'file-analysis/accepted-02'
REJECTED = dict(utc='2026-11-08T17:39:53.630686+00:00', kind='interrupt_rejected',
                reason='No pending x/exit', requested_by='input')
WAIT = dict(utc='2026-11-08T17:38:25.459209+00:00', kind='observation_timeout', status='partial',
            waiting=True, elapsed_seconds=30.15, sequence=5, id='natural-disk-boot', command='x',
            internal=False, received_bytes=0,
            action='Still pending; send interrupt or close. No retry or restart.')
PINS = {
    'research/verify_vice_live.py': 'f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a',
    'research/vice_session_live.py': '4340d1b0394fa612f5e6a71edddcbc2daf947e59c4c3013ab3b850c886dc621c',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'build/research/eod/file-analysis/accepted-02/extract.checked.py': '365143c8a013b1c6a0cb9724c8cbb14baafcf6456f0c88f07324847ef7010097',
    'build/research/eod/file-analysis/accepted-02/file-proof.json': '12f6dd050f3d42d6a9b672475906211704e820d414d7ca26c959b22dd184a608',
    'build/research/eod/file-analysis/accepted-02/EdgeOfDisgrace_0/dos-001.raw.prg': 'd45e1474288f537841351bbf95cafbc6df2ecf50f3f86b0547352d7c67c9e724',
    'build/research/eod/file-analysis/accepted-02/EdgeOfDisgrace_0/dos-001.decoded.prg': '3087048a4b95171955f57adcc455be06b858fa29e72cf7550ea3aae5c638795a',
    'build/research/eod/release/EdgeOfDisgrace_0.d64': 'ee9570df68c3ddd1fda60ea3360dd5880c2ac95ed110bbe1bd60fdb91dec3f61',
    'build/research/eod/native-01-files.json': '1e302512b86046699f2f417f5c57193ba1dd71a7f679a5768009ff1568ac5cdf',
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


def audit_wire():
    wire = load('eod_native_wire', 'research/verify_vice_live.py')
    wire.BASE, wire.CASE_PINS = BASE, {'native-01': CASE_SHA}
    source = (ROOT/'research/verify_vice_live.py').read_text()
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'audit_session')
    original = ast.get_source_segment(source, node)+'\n'
    old = 'assert session["startup_mode"] == "manual monitor load" and "-autostart" not in session["command"]'
    startup = ('assert session["startup_mode"] == "autostart"\n'
               '    assert session["program"] == '+repr(str(DISK))+'\n'
               '    for flag in ("-autostart", "-8"):\n'
               '        assert session["command"].count(flag) == 1\n'
               '        assert session["command"][session["command"].index(flag)+1] == '+repr(str(DISK)))
    anchor = '        elif kind == "partial_response":'
    rejection = ('        elif kind == "interrupt_rejected":\n'
                 '            assert event == '+repr(REJECTED)+'\n'
                 '            assert active is None and sending is None\n'
                 '            assert max(responses) == 5 and responses[5]["status"] == "completed"\n'
                 '            assert ordinary[5]["command"] == "x"\n'+anchor)
    assert original.count(old) == original.count(anchor) == 1
    adapted = original.replace(old, startup).replace(anchor, rejection)
    exec(compile(adapted, '<eod-exact-autostart-and-inactive-rejection>', 'exec'), wire.__dict__)
    case = wire.audit_session('native-01')
    responses = case['responses']
    assert sorted(responses) == list(range(1, 23))
    assert not case['partial'] and not case['cancelled']
    assert case['waits'] == [WAIT]
    assert all(row['status'] == 'completed' for row in responses.values())
    assert all(row['purpose'] == 'ordinary' for row in case['requests'])
    assert [e for e in case['events'] if e['kind'] == 'interrupt_rejected'] == [REJECTED]
    command = case['session']['command']
    assert '-pal' in command and command[command.index('-speed')+1] == '100'
    assert '+warp' in command and '+autostart-warp' in command
    assert command[command.index('-drive8type')+1] == '1541' and '-drive8truedrive' in command
    expected = ['r', 'sidefx off', 'break 080d', 'break 0334', 'x', 'bank ram', 'r',
                f'bsave "{CASE}/sys-ram.bin" 0 0000 ffff', f'dump "{CASE}/sys.vsf"', 'delete 1', 'x', 'r',
                f'bsave "{CASE}/sfx-ram.bin" 0 0000 ffff', f'dump "{CASE}/sfx.vsf"', 'd 0334 03f3',
                'break 0900', 'delete 2', 'x', 'r', f'bsave "{CASE}/unpacked-ram.bin" 0 0000 ffff',
                f'dump "{CASE}/unpacked.vsf"', 'd 0900 09b0']
    assert [responses[n]['command'] for n in range(1, 23)] == expected
    assert not any(re.search(r'ERROR --|Syntax error|Unknown resource', row['response']) for row in responses.values())
    manifest = json.loads((BASE/'native-01-files.json').read_text())
    listing = [dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
               for p in sorted(CASE.iterdir()) if p.is_file()]
    assert listing == manifest['files'] and manifest['file_count'] == len(listing) == 13
    assert sum(r['bytes'] for r in listing) == manifest['total_bytes'] == 834331
    assert sha(json.dumps(listing, sort_keys=True, separators=(',', ':')).encode()) == manifest['listing_sha256'] == CASE_SHA
    return wire, case, dict(original_function_sha256=sha(original.encode()), adapted_function_sha256=sha(adapted.encode()),
        startup_replacement=startup, retained_rejection_branch=rejection,
        rejected_request=REJECTED, no_active_command_at_rejection=True, no_interrupt_r_sent=True,
        retained_waiting_notice=WAIT, same_seq5_later_completes_naturally=True,
        launch_contract='Exact original D64 is both -autostart and -8; PAL, speed100, +warp, +autostart-warp, true1541.',
        limitation='Launch configuration is checked; no runtime speed/warp resource query was made.')


def capture_pairs(reader, wire, case):
    memories, records = {}, []
    for stem, pc, stop, reg, save, snap, clock in (
            ('sys', 0x080d, 5, 7, 8, 9, 85514861),
            ('sfx', 0x0334, 11, 12, 13, 14, 86019674),
            ('unpacked', 0x0900, 18, 19, 20, 21, 90297558)):
        responses = case['responses']
        regs = wire.registers(responses[reg]['response'])
        assert regs['pc'] == pc and regs['clock'] == clock
        natural = re.search(r'^#\d+ \(Stop on\s+exec ([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\n'
                            r'\.C:[^\n]+\s+(\d+)\n', responses[stop]['response'], re.M | re.I)
        assert natural and tuple(map(int, natural.groups()[1:])) == (regs['line'], regs['cycle'], clock)
        assert int(natural[1], 16) == pc
        assert all(responses[n]['command'] not in ('x', 'exit', 'z 3') for n in range(reg, snap+1))
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
        assert (clock//63 % 312, clock % 63) == (regs['line'], regs['cycle'])
        memories[stem] = raw
        records.append(dict(stem=stem, stop_sequence=stop, register_sequence=reg, save_sequence=save,
            snapshot_sequence=snap, registers=regs, ram=artifact(rawpath), snapshot=artifact(vsfpath),
            all65536_physical_RAM_bytes_equal=True, CPU_clock_flags_and_beam_equal=True,
            ports=dict(latch=mem[0], DDR=mem[1], data_out=mem[65540], data_read=mem[65541], dir_read=mem[65542],
                       monitor_readback_equal=True, driven_output_bits_equal=True,
                       observed_input_bits=regs['port01'] & (~mem[1] & 255), unused_state_zero=True)))
    return memories, records


def primary_port_sources():
    pins = {
        'vice-3.10/src/c64/c64memsnapshot.c': ('12058072799a1b0c8d46df7d978a8051bf4d6ef5e7fb26921ac82cd94ed2e149', [217, 230]),
        'vice-3.10/src/c64/c64mem.c': ('4ee45952cac4a572d57f3bbea7ea0d52f5d303499167228b6eea24d7ec5ebf95', [267, 338]),
        'vice-3.10/src/c64/c64pla.c': ('21574c654d7feaaf9b860cada61c74bee1b3d0eba1f2cdb3ff814d9f940e3737', [53, 75]),
    }
    records = []
    with tarfile.open(ROOT/'build/research/quondam/hardware-source/vice-3.10.tar.gz') as archive:
        for member, (pin, lines) in pins.items():
            raw = archive.extractfile(member).read()
            assert sha(raw) == pin
            records.append(dict(member=member, bytes=len(raw), sha256=pin, lines=lines))
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to((BASE/'native-analysis').resolve())
    assert not out.exists(), 'Choose a fresh output directory'
    for name, pin in PINS.items():
        assert sha((ROOT/name).read_bytes()) == pin, name
    wire, case, adapter = audit_wire()
    reader = load('eod_native_snapshot', 'research/quondam/snapshot_state.py')
    memories, records = capture_pairs(reader, wire, case)
    raw = (EXTRACT/'EdgeOfDisgrace_0/dos-001.raw.prg').read_bytes()
    decoded = (EXTRACT/'EdgeOfDisgrace_0/dos-001.decoded.prg').read_bytes()
    file_proof = json.loads((EXTRACT/'file-proof.json').read_text())
    file_record = file_proof['disks'][0]['files'][0]
    assert file_proof['pass_'] and file_proof['disks'][0]['name'] == 'EdgeOfDisgrace_0.d64'
    assert file_record['family'] == 'dos' and file_record['number'] == 1 and file_record['start'] == [1, 0]
    assert file_record['raw']['sha256'] == sha(raw) and file_record['decoded']['sha256'] == sha(decoded)
    assert raw[:2] == decoded[:2] == bytes.fromhex('0108') and len(raw) == 32864 and len(decoded) == 63233
    assert memories['sys'][0x801:0x885f] == raw[2:]
    assert memories['unpacked'][0x801:0xff00] == decoded[2:]
    assert memories['sys'][0x801:0x80d] == bytes.fromhex('0b0800009e32303631000000')
    assert memories['sys'][0x80d:0x81f] == bytes.fromhex('78a9348501a23bbd1f089506ca10f84c0800')
    decoder = memories['sys'][0x85b:0x91b]
    assert memories['sfx'][0x334:0x3f4] == decoder
    assert decoder[:3] == bytes.fromhex('20b803')
    assert memories['sfx'][0x3b0:0x3b8] == bytes.fromhex('a9378501584c0009')
    assert memories['unpacked'][0x900:0x90a] == bytes.fromhex('2c11d010fb2c11d030fb')
    sources = primary_port_sources()
    out.mkdir(parents=True)
    outputs = []
    for name, data in (('decoder-0334.bin', decoder), ('native_boot.checked.py', Path(__file__).read_bytes())):
        (out/name).write_bytes(data)
        outputs.append(dict(name=name, bytes=len(data), sha256=sha(data)))
    proof = dict(pass_=True, scope='Original disk0 DOS bootstrap, SFX decoder and complete decoded payload through natural0900; no Gouraud-part or whole-demo claim',
        producer=artifact(Path(__file__)), inputs=[artifact(ROOT/p) for p in PINS], case_sha256=CASE_SHA,
        wire=wire.summary(case), exact_auditor_adaptations=adapter, captures=records,
        primary_port_schema=sources, original_file=dict(track=1, sector=0, raw_PRG_bytes=32864,
            load=0x801, loaded_end_exclusive=0x885f, loaded_payload_bytes=32862, all_loaded_bytes_equal=True),
        decoder=dict(source=[0x85b, 0x91b], destination=[0x334, 0x3f4], compared_bytes=192, all_bytes_equal=True,
                     exit_PC=0x3b0, exit_bytes='a9378501584c0009', natural_handoff_PC=0x900),
        decoded_payload=dict(source='Pinned passive extractor BB1 result', load=0x801, end_exclusive=0xff00,
            bytes=63231, all_bytes_equal=True, mismatches=0, sha256=sha(decoded[2:])),
        limits=['This validates the main disk0 decoder result; it does not validate every hidden indexed file or decoder corner case.',
                'The original program is stopped before0900 executes; no content-side load, shader, Gouraud speed or complete animation is accepted.',
                'The rejected interrupt request occurred after natural seq5 completion; it did not interrupt execution and sent no monitor r.',
                'Processor-port reads are checked against serialized readback with unused-state guards; no tape-state inference.',
                'No downloaded source execution, emulator, CPU interpreter, subprocess, build or new native action in this producer.'], outputs=outputs)
    result = (json.dumps(proof, indent=2)+'\n').encode()
    (out/'native-boot-proof.json').write_bytes(result)
    print(json.dumps(dict(pass_=True, receipt_bytes=len(result), receipt_sha256=sha(result), pairs=3,
                         loaded_bytes=32862, decoded_bytes=63231, decoder_bytes=192), indent=2))


if __name__ == '__main__':
    main()
