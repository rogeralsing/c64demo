#!/usr/bin/env python3
"""Passively bind released One-Der, native state, shade tables and one byte plot."""
import argparse
import ast
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/one-der'
CASE = BASE / 'native-01'
CASE_SHA = '3264e764ff72ae0744de5c0a3b55beabd7641ac370c79744a8fb3ba0f4b361a9'
PINS = {
    'research/verify_vice_live.py': 'f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a',
    'research/vice_session_live.py': '4340d1b0394fa612f5e6a71edddcbc2daf947e59c4c3013ab3b850c886dc621c',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'build/research/quondam/hardware-source/vice-3.10.tar.gz': '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1',
    'build/research/one-der/one-der.t64.gz': 'd77324f0ca6232285def5bb328a20d98fcb1a3e83a8f557b38cc86df3e84ec7e',
    'build/research/one-der/one-der.t64': 'b2896a7814a711b6603c4a8caf96a8e4e26141c82589c975702d64a722040671',
    'build/research/one-der/one-der.prg': 'a4d719d1ef0d65b287225f466ca068f742d7d7d98e6f667045065da2ce056053',
    'build/research/one-der/release.html': 'f03605748d4a85608916fc70fe366f10dfe4618beb1a612f7e70c2c634116848',
}
PCS = dict(sys=0xcf9d, sfx=0x080e, unpacked=0x013f, main=0x14be,
           production=0x1000, part2=0x2432, **{'gouraud-init':0x2000,
           'frame-start':0x09cd, 'shade-start':0x09cd, 'kernel-start':0x133b,
           'kernel-end':0x1344, 'later-frame':0x09cd, 'draw-end':0x09d6, 'cosmetic':0x0b29})


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def audit_wire():
    wire = load('one_der_wire', 'research/verify_vice_live.py')
    wire.BASE, wire.CASE_PINS = BASE, {'native-01':CASE_SHA}
    source = (ROOT / 'research/verify_vice_live.py').read_text()
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'audit_session')
    original = ast.get_source_segment(source, node) + '\n'
    old = 'assert session["startup_mode"] == "manual monitor load" and "-autostart" not in session["command"]'
    new = ('assert session["startup_mode"] == "autostart"\n'
           '    assert session["command"].count("-autostart") == 1\n'
           f'    assert session["command"][session["command"].index("-autostart")+1] == {str(BASE / "one-der.prg")!r}\n'
           '    assert "-8" not in session["command"]')
    assert original.count(old) == 1
    adapted = original.replace(old, new)
    exec(compile(adapted, '<one-der-extracted-original-autostart>', 'exec'), wire.__dict__)
    case = wire.audit_session('native-01')
    assert not case['partial'] and not case['cancelled'] and not case['waits']
    assert list(sorted(case['responses'])) == list(range(1, 125))
    assert [n for n,r in case['responses'].items() if r['status'] == 'interrupted'] == [87]
    assert case['responses'][87]['interrupt']['command'] == 'r'
    assert case['responses'][81]['response'] == '#1 not a valid checkpoint\n(C:$09cd) '
    assert case['responses'][14]['command'] == 'keybuf "D"'
    assert case['responses'][16]['response'].find('A:22 ') >= 0
    allowed = re.compile(r'^(?:r|sidefx off|bank ram|warp (?:on|off)|resourceget "Speed"|x|z 3|help keybuf|'
                         r'd [0-9a-f]{4} [0-9a-f]{4}|delete [1-6]|disable 1|keybuf "D"|'
                         r'break (?:[0-9a-f]{4}|exec 12cf 1512|exec 0000 ffff if RL == \$fc)|'
                         r'trace exec 0e5[36]|command [34] "m 0010 0027(?:; m 0072 0079)?")$')
    contexts, latest = {}, None
    for sequence,row in sorted(case['responses'].items()):
        command = row['command']
        if command in ('x','z 3'):
            latest = None
        if command == 'r':
            latest = wire.registers(row['response'])
        capture = re.fullmatch(r'(bsave|dump|screenshot) "([^"\n]+)"( 0 0000 ffff| 2)?', command)
        if capture:
            kind, name, suffix = capture.groups()
            path = Path(name)
            assert path.parent == CASE and latest is not None and path.name not in contexts
            assert suffix == (' 0 0000 ffff' if kind == 'bsave' else ' 2' if kind == 'screenshot' else None)
            contexts[path.name] = latest
        else:
            assert allowed.fullmatch(command), command
        assert not re.search(r'ERROR --|Syntax error|Unknown resource', row['response'])
        if 'not a valid checkpoint' in row['response']:
            assert sequence == 81
    launch = case['session']['command']
    assert '-pal' in launch and launch[launch.index('-speed')+1] == '100'
    assert '+warp' in launch and '+autostart-warp' in launch
    assert [n for n,r in case['responses'].items() if r['command'] == 'warp on'] == [52,57,66]
    assert [n for n,r in case['responses'].items() if r['command'] == 'warp off'] == [54,59,68]
    assert case['responses'][69]['response'].startswith('Speed=100\n')
    assert case['responses'][124]['response'].startswith('Speed=100\n')
    return wire,case,contexts,dict(original_function_sha256=sha(original.encode()), adapted_function_sha256=sha(adapted.encode()),
        exact_startup_replacement=new, keyboard_observation='Literal monitor keybuf command included quotes; native A22 is the first key. Original non-N branch selected demo. No claim that A44 selected it.',
        retained_error='Sequence81 deletes nonexistent checkpoint1. shade-start captures a second09CD frame boundary, not0A24. Corrected by deleting checkpoint5; attempt87 then interrupted read-only.',
        native_instruction_step='Sequence96 z3 executes original LDA/ORA/STA; no manual CPU/RAM/register patch or snapshot restore.')


def captures(reader, contexts):
    result, records = {}, []
    assert len(list(CASE.glob('*.vsf'))) == len(PCS) == 14
    for stem,pc in PCS.items():
        vsf, raw = CASE / f'{stem}.vsf', CASE / f'{stem}-ram.bin'
        regs = contexts[vsf.name]
        assert regs == contexts[raw.name] and regs['pc'] == pc
        ram = raw.read_bytes()
        mem, cpu = reader.module_payload(vsf,'C64MEM'), reader.module_payload(vsf,'MAINCPU')
        assert len(ram) == 65536 and ram == mem[4:65540]
        # VICE3.10 c64memsnapshot.c:217-230 saves both latch and readback.
        # Guard zero unused-bit/decay state before comparing monitor reads.
        assert len(mem) == 65555 and mem[65543:] == bytes(12)
        assert mem[1] == mem[65542] == regs['port00'] == 0x2f
        assert mem[65541] == regs['port01']
        assert (mem[0]&mem[1]) == (regs['port01']&mem[1])
        observed_inputs = regs['port01']&(~mem[1]&255)
        assert observed_inputs == 0x10
        expected = dict(clock=int.from_bytes(cpu[:8],'little'),a=cpu[8],x=cpu[9],y=cpu[10],sp=cpu[11],
                        pc=int.from_bytes(cpu[12:14],'little'),flags=cpu[14])
        assert all(regs[k] == v for k,v in expected.items())
        state = reader.read_snapshot(vsf)
        assert state['modules']['C64MEM']['version'] == [0,1]
        assert (state['vicii']['raster_line'],state['vicii']['raster_cycle']) == (regs['line'],regs['cycle'])
        assert (regs['clock']//63%312,regs['clock']%63) == (regs['line'],regs['cycle'])
        result[stem] = dict(ram=ram,regs=regs)
        records.append(dict(stem=stem,registers=regs,ram=artifact(raw),snapshot=artifact(vsf),all_RAM_CPU_registers_clock_and_beam_equal=True,
                            port=dict(snapshot_data_latch=mem[0],snapshot_DDR=mem[1],snapshot_data_out=mem[65540],
                                      snapshot_data_read=mem[65541],snapshot_dir_read=mem[65542],monitor_readback=regs['port01'],
                                      output_bits_equal=True,serialized_readback_equals_monitor=True,observed_input_bits=observed_inputs,
                                      unused_bit_and_decay_state_zero=True,source='VICE3.10 c64memsnapshot.c:217-230; c64mem.c:267-335. Raw latch and external-input readback are different fields.')))
    return result,records


def original_file(c):
    tape = (BASE/'one-der.t64').read_bytes()
    assert gzip.decompress((BASE/'one-der.t64.gz').read_bytes()) == tape
    assert tape[:19] == b'C64 tape image file' and tuple(int.from_bytes(tape[i:i+2],'little') for i in (32,34,36)) == (256,1,1)
    entry = tape[64:96]
    assert entry[:2] == b'\x01\x81'
    start,end,offset = int.from_bytes(entry[2:4],'little'),int.from_bytes(entry[4:6],'little'),int.from_bytes(entry[8:12],'little')
    assert (start,end,offset) == (0x0801,0xd000,96) and len(tape)-offset == end-start
    program = (BASE/'one-der.prg').read_bytes()
    assert program == start.to_bytes(2,'little') + tape[offset:]
    assert c['sys']['ram'][start:end] == program[2:]
    return dict(T64_version=256,active_entries=1,entry_name=entry[16:32].decode('ascii'),load_address=start,end_exclusive=end,
                payload_bytes=end-start,all_loaded_payload_bytes_match=True,BASIC_SYS=53149,entry_PC=0xcf9d)


def shade_tables(c):
    source = c['part2']['ram']
    assert source[0x1d74:0x1d7d] == bytes.fromhex('a2d8a0fba90d20240a')
    palette = bytes.fromhex('ffeeaa99554400')
    assert source[0xa72:0xa79] == palette
    assert source[0xa24:0xa2d] == bytes.fromhex('86368438853aa20018')
    tables, accumulator = [bytearray(256) for _ in range(8)], 0xfbd8
    samples = []
    for x in range(256):
        accumulator = (accumulator+13)&65535
        high = accumulator>>8
        level = 0 if high&128 else min(6,high)
        p = palette[level]
        values = [p&240,p&240,p&15,p&15,(p<<2)&240,(p<<2)&240,(p>>2)&15,(p>>2)&15]
        for table,value in zip(tables,values):table[x]=value
        samples.append(dict(index=x,accumulator=accumulator,level=level,packed=p))
    packed = b''.join(tables)
    stems = ('frame-start','shade-start','kernel-start','later-frame','draw-end')
    assert all(c[s]['ram'][0x3000:0x3800] == packed for s in stems)
    return dict(address=0x3000,bytes_per_capture=2048,captures=list(stems),matching_bytes=2048*len(stems),
                seed_fraction=216,seed_integer_signed=-5,unsigned_increment=13,preincrement_sample=True,
                pattern_codes=list(palette),sha256=sha(packed),samples=samples),packed


def kernel(c):
    before,after = c['kernel-start'],c['kernel-end']
    m,n,r,s = before['ram'],after['ram'],before['regs'],after['regs']
    assert r['pc'] == 0x133b and s['pc'] == 0x1344 and m[0x133b:0x1344] == bytes.fromhex('bd4e301d4632990026')
    first,second,target = 0x304e+r['x'],0x3246+r['x'],0x2600+r['y']
    value = m[first] | m[second]
    assert m[first]&15 == 0 and m[second]&240 == 0
    assert (first,second,target,m[first],m[second],value) == (0x308f,0x3287,0x2620,0x90,0x0a,0x9a)
    assert s['a'] == n[target] == value
    assert all(r[k] == s[k] for k in ('x','y','sp','port00','port01'))
    expected_flags = (r['flags']&~0x82)|(value&0x80)|(2 if value==0 else 0)
    assert s['flags'] == expected_flags
    differences = [i for i,(a,b) in enumerate(zip(m,n)) if a!=b]
    assert differences == [target] and m[target] == 0xff
    assert s['clock']-r['clock'] == 13
    source = c['part2']['ram']
    groups=[]
    for entry,base in ((0x12cf,0x2000),(0x1360,0x2000),(0x13f1,0x2800),(0x1482,0x2800)):
        table_a,table_b = (0x3000,0x3200) if entry in (0x12cf,0x13f1) else (0x3400,0x3600)
        for i in range(16):
            expected = b'\xbd'+table_a.to_bytes(2,'little')+b'\x1d'+table_b.to_bytes(2,'little')+b'\x99'+(base+128*i).to_bytes(2,'little')
            assert source[entry+9*i:entry+9*i+9] == expected
        assert source[entry+144] == 0x60
        groups.append(dict(entry=entry,groups=16,bytes=145,destination_base=base,table_pair=[table_a,table_b]))
    return dict(executed_bytes=m[0x133b:0x1344].hex(),input_addresses=[first,second],input_values=[m[first],m[second]],
                destination=target,before=m[target],after=n[target],all_RAM_differences=differences,
                observed_elapsed_cycles=13,CPU_registers_and_NZ_checked=True,static_unrolled_routines=groups,
                limitation='One original three-instruction byte plot. Two independent nibble contributions; physical pixel footprint and whole-image equivalence are separate.')


def gradient_trace(case,c):
    for stem in ('part2','later-frame','draw-end'):
        memory=c[stem]['ram']
        assert memory[0xe53:0xe58] == bytes.fromhex('207017a200')
        assert memory[0x1770:0x1777] == bytes.fromhex('a51738e5148520')
        assert memory[0x17b9] == 0x60
    raw = case['responses'][111]['response']
    pattern = re.compile(r'^\.C:(0e53|0e56)[^\n]* SP:([0-9a-f]{2}) [NV.BDIZC-]{8}\s+(\d+)\n',re.M|re.I)
    matches = list(pattern.finditer(raw)); assert len(matches)==8
    rows=[]
    for i in range(0,8,2):
        a,b=matches[i:i+2]
        assert a[1].lower()=='0e53' and b[1].lower()=='0e56' and int(a[2],16)==int(b[2],16)==0xf4
        def memory(match,next_match):
            chunk=raw[match.end():next_match.start() if next_match else len(raw)]
            values={}
            for line in re.finditer(r'^>C:([0-9a-f]{4})  ([0-9a-f]{2}(?: [0-9a-f]{2}){0,3})(?=\s{2,}|$)',chunk,re.M|re.I):
                address=int(line[1],16)
                for j,value in enumerate(bytes.fromhex(line[2])):values[address+j]=value
            return values
        entry=memory(a,b); end=memory(b,matches[i+2] if i+2<len(matches) else None)
        assert set(entry)==set(range(0x10,0x28))|set(range(0x72,0x7a)) and set(end)==set(range(0x10,0x28))
        triples=[list(entry[j] for j in range(start,start+3)) for start in (0x10,0x13,0x16)]
        assert len({row[2] for row in triples})>1
        assert all(entry[j]==end[j] for j in range(0x10,0x19))
        rows.append(dict(vertex_triples=triples,third_vertex_array=list(entry[j] for j in range(0x72,0x7a)),
                         elapsed_cycles=int(b[3])-int(a[3]),SP=244,result_20_to_27=list(end[j] for j in range(0x20,0x28))))
    return dict(executed_runtime_gradient_calls=4,entry_PC=0xe53,return_PC=0xe56,callee=0x1770,triangles=rows,
                limitation='Execution and varying third attributes are bound. This does not independently reproduce full signed gradient arithmetic or establish a separate light/normal model.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    out=parser.parse_args().output.resolve();out.relative_to((BASE/'analysis').resolve())
    assert not out.exists(), 'Choose a fresh output directory'
    for name,pin in PINS.items():assert sha((ROOT/name).read_bytes())==pin,name
    wire,case,contexts,adapter=audit_wire()
    reader=load('one_der_snapshot','research/quondam/snapshot_state.py')
    c,records=captures(reader,contexts)
    origin=original_file(c); tables,packed=shade_tables(c); plot=kernel(c); gradients=gradient_trace(case,c)
    assert c['frame-start']['ram'][0x9ca:0x9cd]==bytes.fromhex('20741d')
    assert c['later-frame']['ram'][0x9d3:0x9d6]==bytes.fromhex('201d1b')
    elapsed=c['draw-end']['regs']['clock']-c['later-frame']['regs']['clock']
    assert elapsed==132724
    out.mkdir(parents=True)
    outputs=[]
    for name,data in [('shade-tables.bin',packed),('analyze.checked.py',Path(__file__).read_bytes())]:
        (out/name).write_bytes(data);outputs.append(dict(name=name,bytes=len(data),sha256=sha(data)))
    tables.pop('samples')
    proof=dict(pass_=True,scope='Original released One-Der native startup,14 state pairs, packed shade LUT identity and one exact byte plot; not full animation/pixel/FPS acceptance',
               producer=artifact(Path(__file__)),inputs=[artifact(ROOT/p) for p in PINS],case_sha256=CASE_SHA,
               wire=wire.summary(case),startup_adapter=adapter,captures=records,release_identity=origin,
               shade_tables=tables,kernel=plot,gradient_trace=gradients,
               one_observed_render=dict(begin_PC=0x9cd,end_PC=0x9d6,elapsed_PAL_cycles=elapsed,PAL_fields=elapsed/19656,
                   includes='Original rotation, buffer clear, draw and IRQ/VIC time; excludes following wait/presentation. One pose, not whole-scene FPS.'),
               cosmetic_png=artifact(CASE/'gouraud.png'),outputs=outputs,
               next_work='Reproduce rotated-coordinate-to-intensity and signed gradient/edge math, then verify complete span pixels and actual raster display geometry; HCL tracing-line algorithm is separate.')
    raw=(json.dumps(proof,indent=2)+'\n').encode();(out/'one-der-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=True,output=str(out),proof_bytes=len(raw),proof_sha256=sha(raw),pairs=len(records),LUT_matching_bytes=tables['matching_bytes'],kernel=plot,render_cycles=elapsed),indent=2))


if __name__=='__main__':main()
