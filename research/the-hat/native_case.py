#!/usr/bin/env python3
"""Passively accept retained original The Hat native custody; start no processes."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tarfile
import zipfile

sys.dont_write_bytecode = True
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'build/research/the-hat'
CASE=BASE/'native-01'
DISK=BASE/'release/the-hat-7a825b1-a.d64'
BOOT=BASE/'disk-analysis/early-01/original-bootstrap.prg'
CASE_SHA='fac04fa90dbb6f499afe9e405fc565e2c7b99cb299e9ead4f02fcdde27f5a2e6'
MANIFEST_SHA='d36260529112029981bf746c08a89ff1dca177ab46b1bd51a07957990ee372ac'
COMMANDS_SHA='303864357f113a2de42f530cbf426c2b8c7a47ac2c26aa79de6de86d2760330e'
MANIFEST_NAME='native-01-files.json'
FILE_COUNT=47
TOTAL_BYTES=327423480
COMMAND_COUNT=159
EXPECTED_STATES={'sys': (2061, 11363840), 'depacked': (2560, 12272730), 'installed': (2570, 13602048), 'first-load-entry': (722, 13621989), 'first-loaded': (3840, 14398599), 'part01-load-return': (3902, 14421964), 'part01-entry': (2304, 14421967), 'part02-load-return': (2368, 15153526), 'part02-entry': (16384, 15153529), 'side-b-request': (524, 405643554), 'side-select-return': (34882, 405643828), 'side-b-file2-return': (34902, 409316362), 'b17-controller': (32768, 587004264), 'b17-init': (32829, 587033081), 'b17-raster': (8192, 590998150), 'b17-midfield': (32835, 602888834), 'b17-cutoff': (33563, 602905924), 'b17-stack-restored': (33567, 602905930), 'b17-complete': (32832, 602907732)}
EXPECTED_WAITS=[{'utc': '2026-11-08T20:22:56.142321+00:00', 'kind': 'observation_timeout', 'status': 'partial', 'waiting': True, 'elapsed_seconds': 30.073, 'sequence': 76, 'id': 'natural-side-b-request', 'command': 'x', 'internal': False, 'received_bytes': 2160, 'action': 'Still pending; send interrupt or close. No retry or restart.'}, {'utc': '2026-11-08T20:37:15.477021+00:00', 'kind': 'observation_timeout', 'status': 'partial', 'waiting': True, 'elapsed_seconds': 30.02, 'sequence': 100, 'id': 'natural-b17-controller', 'command': 'x', 'internal': False, 'received_bytes': 960, 'action': 'Still pending; send interrupt or close. No retry or restart.'}, {'utc': '2026-11-08T20:56:11.265640+00:00', 'kind': 'observation_timeout', 'status': 'partial', 'waiting': True, 'elapsed_seconds': 30.098, 'sequence': 129, 'id': 'natural-b17-midfield', 'command': 'x', 'internal': False, 'received_bytes': 33685364, 'action': 'Still pending; send interrupt or close. No retry or restart.'}]
EXPECTED_INTERRUPT_SEQUENCES=[76, 129]
SOURCE_BINDINGS=[{'capture': 'depacked', 'source': 'build/research/the-hat/disk-analysis/early-01/original-bootstrap.prg', 'source_first': 267, 'source_end': 270, 'RAM_first': 234, 'context': 'Original relocation tail JMP0A00; CPU00 was not copied'}, {'capture': 'first-loaded', 'source': 'build/research/the-hat/dali-analysis/accepted-03/a00-0f00.bin', 'source_first': 0, 'source_end': 4350, 'RAM_first': 3840, 'context': 'Full independent original A00 decode'}, {'capture': 'part01-load-return', 'source': 'build/research/the-hat/dali-analysis/accepted-03/a00-0f00.bin', 'source_first': 59, 'source_end': 65, 'RAM_first': 3899, 'context': 'Original A00 JSR02D2 and continuation JMP0900'}, {'capture': 'side-b-request', 'source': 'build/research/the-hat/dali-analysis/accepted-03/a41-5000.bin', 'source_first': 14394, 'source_end': 14402, 'RAM_first': 34874, 'context': 'Original A41 F1 request at883D, JSR020C at883F, continuation8842'}, {'capture': 'side-select-return', 'source': 'build/research/the-hat/dali-analysis/accepted-03/a41-5000.bin', 'source_first': 14394, 'source_end': 14402, 'RAM_first': 34874, 'context': 'Original A41 F1 request at883D, JSR020C at883F, continuation8842'}, {'capture': 'side-b-file2-return', 'source': 'build/research/the-hat/dali-analysis/accepted-03/a41-5000.bin', 'source_first': 14417, 'source_end': 14430, 'RAM_first': 34897, 'context': 'Original A41 selector2 JSR02D4 and wait/JMP range; mutable885E flag excluded explicitly'}, {'capture': 'b17-controller', 'source': 'build/research/the-hat/dali-analysis/accepted-03/b16-0800.bin', 'source_first': 58, 'source_end': 72, 'RAM_first': 2106, 'context': 'Original B16 JSR02D2 and flag-wait/JMP8000 control range'}, {'capture': 'b17-controller', 'source': 'build/research/the-hat/dali-analysis/accepted-03/b17-2000.bin', 'source_first': 0, 'source_end': 26402, 'RAM_first': 8192, 'context': 'Full independent B17 before initializer'}, {'capture': 'b17-init', 'source': 'build/research/the-hat/dali-analysis/accepted-03/b17-2000.bin', 'source_first': 24634, 'source_end': 24648, 'RAM_first': 32826, 'context': 'Original B17 initializer return, loader and controller range'}, {'capture': 'b17-raster', 'source': 'build/research/the-hat/dali-analysis/accepted-03/b17-2000.bin', 'source_first': 0, 'source_end': 8, 'RAM_first': 8192, 'context': 'Original B17 raster body generation'}, {'capture': 'b17-midfield', 'source': 'build/research/the-hat/dali-analysis/accepted-03/b17-2000.bin', 'source_first': 24640, 'source_end': 24648, 'RAM_first': 32832, 'context': 'Original B17 flag wait and later controller transfer'}, {'capture': 'b17-complete', 'source': 'build/research/the-hat/dali-analysis/accepted-03/b17-2000.bin', 'source_first': 24640, 'source_end': 24648, 'RAM_first': 32832, 'context': 'Original B17 flag wait and later controller transfer'}, {'capture': 'b17-cutoff', 'source': 'build/research/the-hat/dali-analysis/accepted-03/b17-2000.bin', 'source_first': 25371, 'source_end': 25385, 'RAM_first': 33563, 'context': 'Original B17 cutoff LDX831A/TXS and IRQ continuation'}, {'capture': 'b17-stack-restored', 'source': 'build/research/the-hat/dali-analysis/accepted-03/b17-2000.bin', 'source_first': 25371, 'source_end': 25385, 'RAM_first': 33563, 'context': 'Original B17 cutoff LDX831A/TXS and IRQ continuation'}]
RUNTIME_BINDINGS=[{'capture': 'installed', 'reference_capture': 'depacked', 'reference_first': 4794, 'reference_end': 5302, 'RAM_first': 512, 'expected_differences': [{'address': 523, 'reference': 0, 'actual': 7}], 'context': 'Two overlapping original installer copies, exact flag byte difference retained'}, {'capture': 'first-load-entry', 'reference_capture': 'depacked', 'reference_first': 4794, 'reference_end': 5302, 'RAM_first': 512, 'expected_differences': [{'address': 523, 'reference': 0, 'actual': 7}], 'context': 'Two overlapping original installer copies, exact flag byte difference retained'}, {'capture': 'installed', 'reference_capture': 'depacked', 'reference_first': 2560, 'reference_end': 2570, 'RAM_first': 2560, 'expected_differences': [], 'context': 'Original entry LDA18/SEI/CLD/LDX5F/TXS/JSR1000'}, {'capture': 'first-load-entry', 'reference_capture': 'depacked', 'reference_first': 2809, 'reference_end': 2818, 'RAM_first': 2809, 'expected_differences': [], 'context': 'Original pushes0E,FF and JMP02D2 active continuation0F00'}, {'capture': 'first-load-entry', 'reference_capture': 'depacked', 'reference_first': 2818, 'reference_end': 2894, 'RAM_first': 352, 'expected_differences': [], 'context': 'Original relocated callback/control stubs copied after installer return'}, {'capture': 'first-loaded', 'reference_capture': 'depacked', 'reference_first': 2818, 'reference_end': 2894, 'RAM_first': 352, 'expected_differences': [], 'context': 'Original relocated callback/control stubs copied after installer return'}, {'capture': 'part02-load-return', 'reference_capture': 'part01-entry', 'reference_first': 2365, 'reference_end': 2371, 'RAM_first': 2365, 'expected_differences': [], 'context': 'Earlier natural original JSR02D2 continuation JMP4000'}]
FLOW_BINDINGS=[{'context': 'Original bootstrap', 'scope': 'SYS080D relocates offsetsEC..01: source0821..090C to0001..00EC. Offset0 is not copied; CPU01 is a port write, not a physical RAM byte oracle. SFX expanded code at0A00 is observed from original execution, not independently decoded in this proof.'}, {'context': 'Installer', 'scope': 'The observed original0A00 entry includes LDA18 before SEI and explicitly resets SP with TXS. No generic SP+2 inference is made across installation. Installed resident508 bytes preserve the exact documented020B00-to07 flag difference; later resident SMC is not broadly normalized.'}, {'context': 'Original side selection', 'scope': 'Original A41 loads A=F1 and calls020C. Capture is before SEC executes, so original B is attached after an actual source-bound pending request, not a claimed visual prompt/drive acknowledgement. Explicit8842 return separately checks saved continuation.'}, {'context': 'B17 association', 'scope': 'Original B16 caller and entire26402-byte independently decoded B17 match the natural8000 entry. This is the closing-logo module; the requested all-border vertical UpScroll is a distinct target and is not identified by this case.'}]
STACK_BINDINGS=[{'entry_capture': 'first-load-entry', 'return_capture': 'first-loaded', 'continuation': 3840}, {'entry_capture': 'side-b-request', 'return_capture': 'side-select-return', 'continuation': 34882}]
PERIPHERAL_COMMANDS=[{'sequence': 84, 'command': 'attach "/Users/rogerjohansson/git/asynkron/c64demo/build/research/the-hat/release/the-hat-7a825b1-b.d64" 8', 'kind': 'media', 'context': 'Authentic pending original A41 F1 side-select request; before SEC at020C, no keyboard or RAM/PC patch', 'request_capture': 'side-b-request', 'request_PC': 524, 'request_A': 241}]

PINS={'research/verify_vice_live.py': 'f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a', 'research/vice_session_live.py': '4340d1b0394fa612f5e6a71edddcbc2daf947e59c4c3013ab3b850c886dc621c', 'research/eod/controller.py': '033bafb6ac6e97283175ac6713af0eef60cb7991b653ee1c98c47a1a4afa83c9', 'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a', 'build/research/quondam/hardware-source/vice-3.10.tar.gz': '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1', 'build/research/frontier-2026/february-analysis/the-hat-original.zip': 'ab15a74ba10a71264ccad74cd1d3a394b8f442a2acd33fd363b671bf293b081f', 'build/research/the-hat/release/the-hat-7a825b1-a.d64': 'ce09a1819a5dcec16342ebdc6515d20c377304db68e326ca2d86a499f0c9399d', 'build/research/the-hat/release/the-hat-7a825b1-b.d64': '1527038ebebca1a3d3d3379b91dd1a77dffb6d6d89a4dbfc32bf3f6908eb5b21', 'build/research/the-hat/disk-analysis/early-01/original-bootstrap.prg': '32189d1101a947c3ecc02ae3e9493756dbc063008582d09c62f939068f1049cd', 'research/the-hat/dali.py': '7195f31a85f0dcac032c10b53a6cefcd48d2832d4edf14da0c331dfcf7412ee0', 'build/research/the-hat/dali-analysis/accepted-03/dali-proof.json': '1687a5b2323ec86881b53b226a5361ac88c6408720498cfd34cf7032b3ad940e', 'build/research/the-hat/disk-analysis/accepted-02/disk-proof.json': 'a23fa100137fe60f929af25b6596584089cd93cacd891fe02e7ebc85d47635a3', 'build/research/the-hat/dali-analysis/accepted-03/a00-0f00.bin': '62b638c1de23c5361d099ecb490b82653a08729e813231520f6c6648e7091c7e', 'build/research/the-hat/dali-analysis/accepted-03/a40-2000.bin': 'c126478fc1f2cecd389367675aeea8e84c9e63b77db188f2ec2a3ecf1b3d1946', 'build/research/the-hat/dali-analysis/accepted-03/a41-5000.bin': 'fb76ffb83748a740039b95c5a3991889e4543a0d331192492dc6005ffae5ba0b', 'build/research/the-hat/dali-analysis/accepted-03/b00-0f00.bin': '61a9573334039fbd8b812c5378c4eefb820f96cf52d570dd1b1b3aa7ed23bbf9', 'build/research/the-hat/dali-analysis/accepted-03/b16-0800.bin': '082c9b848e804727f1cd5a98760ea57d723ef2a5637c638fbc74f1694ad8fd64', 'build/research/the-hat/dali-analysis/accepted-03/b17-2000.bin': 'fb41ff61943ba509b4cae952b50f48643006550633a0a181603565834aecaa72'}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw=path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)),bytes=len(raw),sha256=sha(raw))


def load(name,relative):
    spec=importlib.util.spec_from_file_location(name,ROOT/relative)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def function_source(path,name):
    source=path.read_text()
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==name)
    return ast.get_source_segment(source,node)+'\n'


def response_reference(row):
    raw=row['response'].encode()
    return dict(sequence=row['sequence'],id=row['id'],command=row['command'],
        received_first=row['received_first'],received_end=row['received_end'],
        response_bytes=len(raw),response_sha256=sha(raw),received_stream=str((CASE/'received.bin').relative_to(ROOT)))


def interrupt_framing(row,wire):
    """Bind the final explicit interrupt-r frame without discarding late traces."""
    assert row['status']=='interrupted'
    text=row['response'];metadata=row['interrupt'];first=metadata['response_first']
    assert text.isascii() and metadata['register_response']==text[first:]
    pattern=re.compile(r'(?m)^\(C:\$([0-9a-f]{4})\) +ADDR A  X  Y  SP 00 01 NV-BDIZC LIN CYC  STOPWATCH\n'
        r'\.;[^\n]+\n\(C:\$\1\) \Z')
    match=pattern.search(text);assert match and match.start()>=first
    frame=match[0];registers=wire.registers(frame)
    assert registers['pc']==int(match[1],16) and wire.PROMPT.search(frame.encode())
    suffix=text[first:]
    return dict(registers=registers,frame_response_first=match.start(),
        frame_received_first=row['received_first']+match.start(),frame_received_end=row['received_end'],
        frame_bytes=len(frame),frame_sha256=sha(frame.encode()),
        complete_retained_interrupt_suffix_bytes=len(suffix),complete_retained_interrupt_suffix_sha256=sha(suffix.encode()),
        explicit_register_rows_in_complete_suffix=len(wire.REGISTERS.findall(suffix)),
        late_trace_headers_in_complete_suffix=len(re.findall(r'#\d+ \(Trace\s+(?:exec|store) ',suffix)),
        no_raw_suffix_or_late_trace_filtering=True)


def original_disk_members():
    zip_path=ROOT/'build/research/frontier-2026/february-analysis/the-hat-original.zip'
    members=[]
    with zipfile.ZipFile(zip_path) as archive:
        for name,pin in (('the-hat-7a825b1-a.d64','ce09a1819a5dcec16342ebdc6515d20c377304db68e326ca2d86a499f0c9399d'),
                         ('the-hat-7a825b1-b.d64','1527038ebebca1a3d3d3379b91dd1a77dffb6d6d89a4dbfc32bf3f6908eb5b21')):
            matches=[info.filename for info in archive.infolist() if Path(info.filename).name==name]
            assert len(matches)==1
            raw=archive.read(matches[0])
            path=BASE/'release'/name
            assert len(raw)==174848 and sha(raw)==pin and path.read_bytes()==raw
            members.append(dict(member=matches[0],bytes=len(raw),sha256=pin,copy=artifact(path),all_bytes_equal=True))
    return dict(original_ZIP=artifact(zip_path),disk_members=members)


def audit_wire():
    assert all(not s.startswith('PENDING') for s in (CASE_SHA,MANIFEST_SHA,COMMANDS_SHA,MANIFEST_NAME)), 'Only accept an owner-closed pinned case'
    assert FILE_COUNT and TOTAL_BYTES and COMMAND_COUNT and EXPECTED_STATES
    assert all(v is not None for v in (EXPECTED_WAITS,EXPECTED_INTERRUPT_SEQUENCES,SOURCE_BINDINGS,RUNTIME_BINDINGS,FLOW_BINDINGS,STACK_BINDINGS,PERIPHERAL_COMMANDS))
    wire=load('hat_native_wire','research/verify_vice_live.py')
    wire.BASE,wire.CASE_PINS=BASE,{'native-01':CASE_SHA}
    original=function_source(ROOT/'research/verify_vice_live.py','audit_session')
    old='assert session["startup_mode"] == "manual monitor load" and "-autostart" not in session["command"]'
    replacement=('assert session["startup_mode"] == "autostart"\n'
        '    assert session["program"] == '+repr(str(DISK))+'\n'
        '    for flag in ("-autostart", "-8"):\n'
        '        assert session["command"].count(flag) == 1\n'
        '        assert session["command"][session["command"].index(flag)+1] == '+repr(str(DISK)))
    assert original.count(old)==1
    adapted=original.replace(old,replacement)
    interrupt_old='registers(interrupt["register_response"])'
    interrupt_replacement='hat_interrupt_registers(event)'
    assert adapted.count(interrupt_old)==1
    adapted=adapted.replace(interrupt_old,interrupt_replacement)
    wire.hat_interrupt_registers=lambda row:interrupt_framing(row,wire)['registers']
    exec(compile(adapted,'<exact-original-The-Hat-sideA-autostart>','exec'),wire.__dict__)
    case=wire.audit_session('native-01');responses=case['responses']
    assert not case['partial'] and not case['cancelled']
    assert sorted(responses)==list(range(1,COMMAND_COUNT+1))
    assert all(r['status'] in ('completed','interrupted') for r in responses.values())
    assert [n for n,r in sorted(responses.items()) if r['status']=='interrupted']==EXPECTED_INTERRUPT_SEQUENCES
    assert all(r['purpose'] in ('ordinary','interrupt') for r in case['requests'])
    commands=[responses[n]['command'] for n in range(1,COMMAND_COUNT+1)]
    assert sha(json.dumps(commands,separators=(',',':')).encode())==COMMANDS_SHA
    assert case['waits']==EXPECTED_WAITS
    assert all(responses[w['sequence']]['status'] in ('completed','interrupted') for w in case['waits'])
    assert not any(re.search(r'ERROR --|Syntax error|Unknown resource',r['response']) for r in responses.values())
    launch=case['session']['command']
    assert '-pal' in launch and launch[launch.index('-speed')+1]=='100'
    assert '+warp' in launch and '+autostart-warp' in launch
    assert '-drive8truedrive' in launch and launch[launch.index('-drive8type')+1]=='1541'
    path=BASE/MANIFEST_NAME;assert sha(path.read_bytes())==MANIFEST_SHA
    manifest=json.loads(path.read_text())
    listing=[dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(CASE.iterdir()) if p.is_file()]
    assert listing==manifest['files'] and len(listing)==manifest['file_count']==FILE_COUNT
    assert sum(r['bytes'] for r in listing)==manifest['total_bytes']==TOTAL_BYTES
    assert sha(json.dumps(listing,sort_keys=True,separators=(',',':')).encode())==CASE_SHA
    return wire,case,dict(original_function_sha256=sha(original.encode()),adapted_function_sha256=sha(adapted.encode()),
        exact_startup_replacement=replacement,exact_interrupt_old=interrupt_old,
        exact_interrupt_replacement=interrupt_replacement,
        final_interrupt_frame_helper_sha256=sha(function_source(Path(__file__),'interrupt_framing').encode()),
        only_two_declared_auditor_replacements=True,no_event_or_raw_byte_change=True)


def capture_pairs(reader,wire,case):
    """Frozen general state checks with its production-specific DDR constant removed."""
    helper=load('hat_frozen_pair_reader','research/eod/controller.py');helper.CASE=CASE
    original=function_source(ROOT/'research/eod/controller.py','capture_pairs')
    old="assert mem[1] == mem[65542] == regs['port00'] == 0x2f"
    replacement="assert mem[1] == mem[65542] == regs['port00']"
    assert original.count(old)==1
    adapted=original.replace(old,replacement)
    first=original.index('        stopped = list(re.finditer(')
    last=original.index('        assert not any(responses[n]',first)
    original_stop=original[first:last]
    replacement_stop=("        if responses[stop]['status'] == 'interrupted':\n"
        "            drained = wire.hat_interrupt_registers(responses[stop])\n"
        "            assert drained == regs\n"
        "        else:\n"+''.join('    '+line for line in original_stop.splitlines(keepends=True)))
    assert adapted.count(original_stop)==1
    adapted=adapted.replace(original_stop,replacement_stop)
    exec(compile(adapted,'<The-Hat-DDR-and-declared-interrupted-stop>','exec'),helper.__dict__)
    memories,captures=helper.capture_pairs(reader,wire,case)
    for capture in captures:
        row=case['responses'][capture['stop_sequence']]
        capture['observed_stop_kind']='read-only interruption' if row['status']=='interrupted' else 'natural exec breakpoint'
        capture['not_a_natural_phase_stop']=row['status']=='interrupted'
    return memories,captures,dict(original_function_sha256=sha(original.encode()),adapted_function_sha256=sha(adapted.encode()),
        exact_DDR_replacement=replacement,exact_original_stop_block=original_stop,exact_interrupted_stop_replacement=replacement_stop,
        reason='No inherited fixed DDR value. An interrupted same-stop pair compares the exact frozen-auditor drain registers with the explicit r, then runs every RAM/snapshot/CPU/clock/port/beam check. Natural stops retain the original regex and comparisons.',
        only_two_declared_source_replacements=True)


def port_schema():
    pins={
        'vice-3.10/src/c64/c64memsnapshot.c':('12058072799a1b0c8d46df7d978a8051bf4d6ef5e7fb26921ac82cd94ed2e149',[217,230]),
        'vice-3.10/src/c64/c64mem.c':('4ee45952cac4a572d57f3bbea7ea0d52f5d303499167228b6eea24d7ec5ebf95',[267,338]),
        'vice-3.10/src/c64/c64pla.c':('21574c654d7feaaf9b860cada61c74bee1b3d0eba1f2cdb3ff814d9f940e3737',[53,75])}
    result=[]
    with tarfile.open(ROOT/'build/research/quondam/hardware-source/vice-3.10.tar.gz') as archive:
        for member,(pin,lines) in pins.items():
            raw=archive.extractfile(member).read();assert sha(raw)==pin
            result.append(dict(member=member,bytes=len(raw),sha256=pin,lines=lines))
    return result


def independent_decoded_sources():
    path=BASE/'dali-analysis/accepted-03/dali-proof.json'
    proof=json.loads(path.read_text());assert proof['pass']
    models={}
    for case in proof['cases']:
        assert case['unknown_bytes']==case['prior_memory_reads']==0
        assert case['computed_bytes']+case['untouched_original_tail_bytes']==case['bytes']
        row=case['output'];file=path.parent/row['name'];actual=artifact(file)
        assert (actual['bytes'],actual['sha256'])==(row['bytes'],row['sha256'])
        models[str(file.relative_to(ROOT))]=dict(artifact=actual,destination=case['destination'],end_exclusive=case['end_exclusive'],
            prior_memory_reads=0,unknown_bytes=0,computed_bytes=case['computed_bytes'],
            preserved_original_raw_tail_bytes=case['untouched_original_tail_bytes'])
    return dict(proof=artifact(path),models=models,scope='Pinned strict original-stream predictions. Native target bytes are comparison oracles, never unknown-memory seeds; any untouched original packed-input tail remains explicit.')


def source_bindings(memories,captures,decoded):
    states={r['stem']:r['registers'] for r in captures};assert set(states)==set(EXPECTED_STATES)
    for stem,(pc,clock) in EXPECTED_STATES.items():assert (states[stem]['pc'],states[stem]['clock'])==(pc,clock),stem
    raw=BOOT.read_bytes();assert len(raw)==2710 and raw[:2]==bytes.fromhex('0108')
    payload=raw[2:];assert len(payload)==2708 and memories['sys'][0x801:0x1295]==payload
    basic_body=payload[4:payload.index(0,4)]
    basic_sys=re.fullmatch(rb'\x9e\s*([0-9]+)',basic_body);assert basic_sys and int(basic_sys[1])==0x080d
    original=[dict(capture='sys',source=artifact(BOOT),load_address=0x801,end_exclusive=0x1295,
                   payload_bytes=2708,all_bytes_equal=True,BASIC_SYS_target=int(basic_sys[1]),
                   BASIC_line_number=int.from_bytes(payload[2:4],'little'))]
    guards=[]
    for binding in SOURCE_BINDINGS:
        stem=binding['capture'];memory=memories[stem]
        path=ROOT/binding['source'];source=path.read_bytes()
        start,end=binding['source_first'],binding['source_end']
        target=binding['RAM_first'];expected=source[start:end]
        if binding['source'] in decoded['models']:
            model=decoded['models'][binding['source']]
            assert target==model['destination']+start and end<=model['artifact']['bytes']
        assert expected and target+len(expected)<=65536
        assert memory[target:target+len(expected)]==expected,(stem,binding)
        guards.append(dict(**binding,source_artifact=artifact(path),checked_bytes=len(expected),sha256=sha(expected),all_bytes_equal=True))
    runtime=[]
    for binding in RUNTIME_BINDINGS:
        stem,reference=binding['capture'],binding['reference_capture']
        first,end=binding['reference_first'],binding['reference_end']
        target=binding['RAM_first'];expected=memories[reference][first:end]
        assert states[reference]['clock']<=states[stem]['clock'] and expected and target+len(expected)<=65536
        actual=memories[stem][target:target+len(expected)]
        differences=[dict(address=target+i,reference=a,actual=b) for i,(a,b) in enumerate(zip(expected,actual)) if a!=b]
        assert differences==binding['expected_differences'],binding
        runtime.append(dict(**binding,checked_bytes=len(expected),reference_sha256=sha(expected),actual_sha256=sha(actual),
            all_bytes_equal=not differences,observed_differences=differences,
            provenance='Earlier natural original execution bytes; all differences retained explicitly, not an independent static decoded payload or a semantic proof of every modification'))
    stacks=[]
    for binding in STACK_BINDINGS:
        entry=binding['entry_capture'];returned=binding.get('return_capture')
        sp=states[entry]['sp'];memory=memories[entry]
        word=memory[0x100+((sp+1)&255)] | memory[0x100+((sp+2)&255)]<<8
        assert (word+1)&65535==binding['continuation']
        if returned is not None:
            assert binding['continuation']==states[returned]['pc'] and (states[returned]['sp']-sp)&255==2
        stacks.append(dict(**binding,entry_SP=sp,saved_word=word,returned_SP=states[returned]['sp'] if returned else None,
            actual_saved_continuation_equal=True,return_observed=returned is not None,
            scope='Active saved continuation; API completion is claimed only when an explicit return capture is also checked'))
    return dict(original_loaded_payloads=original,source_generation_guards=guards,runtime_generation_context=runtime,declared_source_flows=FLOW_BINDINGS,saved_continuations=stacks,
        limit='Only explicitly source-known ranges claim original-byte equality; natural runtime bytes without an independent disk decoder retain execution provenance only.')


def checkpoint_bindings(case,captures,wire,memories):
    active,stops,setups,interrupts={}, {}, [], []
    for sequence,row in sorted(case['responses'].items()):
        command=row['command']
        if command.startswith(('break ','trace exec ','trace store ')):
            match=re.search(r'^(BREAK|TRACE): ([0-9]+)  C:\$([0-9a-f]{4})(?:-\$([0-9a-f]{4}))?  \((Stop on exec|Trace exec|Trace store)\)',row['response']);assert match,row
            kind,number,first=match[1],int(match[2]),int(match[3],16);last=int(match[4],16) if match[4] else first
            assert number not in active
            if re.fullmatch(r'break [0-9a-f]{4}',command):assert first==last==int(command.split()[1],16)
            operation='store' if match[5]=='Trace store' else 'exec'
            if kind=='TRACE':
                expected=f'trace {operation} {first:04x}'+(f' {last:04x}' if last!=first else '')
                assert command==expected
            record=dict(number=number,kind=kind,operation=operation,first=first,last=last,setup=response_reference(row),condition=command.split(' if ',1)[1] if ' if ' in command else None)
            active[number]=record;setups.append(record)
        elif command.startswith('condition '):
            match=re.fullmatch(r'condition ([0-9]+) if (.+)',command);assert match and int(match[1]) in active
            assert row['response'].startswith(f'Setting checkpoint {match[1]} condition to:')
            active[int(match[1])]['condition']=match[2];active[int(match[1])]['condition_response']=response_reference(row)
        elif command.startswith('command '):
            match=re.fullmatch(r'command ([0-9]+) \"r\"',command);assert match and int(match[1]) in active
            assert row['response'].startswith(f'Setting checkpoint {match[1]} command to: r')
            active[int(match[1])]['attached_r']=response_reference(row)
        elif command.startswith('delete '):
            number=int(command.split()[1]);assert number in active;active.pop(number)
        elif command=='x':
            if row['status']=='interrupted':
                metadata=row['interrupt']
                interrupts.append(dict(sequence=sequence,response=response_reference(row),drain_metadata={key:value for key,value in metadata.items() if key!='register_response'},
                    drained_registers=wire.hat_interrupt_registers(row),
                    final_interrupt_frame=interrupt_framing(row,wire),
                    active_breakpoint_generations=[record.copy() for record in active.values() if record['kind']=='BREAK'],
                    scope='Explicit read-only interruption on the original pending handle. Any following RAM/VSF pair belongs to this actual interrupted point, not an unhit natural phase condition.'))
                continue
            found=list(re.finditer(r'^#([0-9]+) \(Stop on\s+exec ([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+',row['response'],re.M))
            assert len(found)==1,(sequence,row['response'])
            hit=found[0];number,pc=int(hit[1]),int(hit[2],16)
            assert number in active and active[number]['kind']=='BREAK' and active[number]['first']<=pc<=active[number]['last']
            stops[sequence]=dict(checkpoint=active[number].copy(),actual_PC=pc,actual_beam=[int(hit[3]),int(hit[4])],stop=response_reference(row))
    result=[]
    for capture in captures:
        sequence=capture['stop_sequence']
        if case['responses'][sequence]['status']=='interrupted':
            interruption=next(row for row in interrupts if row['sequence']==sequence)
            assert interruption['drained_registers']==capture['registers']
            result.append(dict(stem=capture['stem'],observed_stop_kind='read-only interruption',
                actual_PC=capture['registers']['pc'],actual_beam=[capture['registers']['line'],capture['registers']['cycle']],
                interruption=interruption,not_a_natural_phase_stop=True))
            continue
        row=stops[sequence]
        assert row['actual_PC']==capture['registers']['pc']
        assert row['actual_beam']==[capture['registers']['line'],capture['registers']['cycle']]
        condition=row['checkpoint']['condition'] or ''
        predicate=re.compile(r'(@ram:\$[0-9a-f]+|A|X|Y|SP|PC|RL|CY)\s*(==|>=|<=)\s*\$([0-9a-f]+)')
        checked=[]
        assert re.fullmatch(r'[()\s&]*',predicate.sub('',condition)),condition
        for match in predicate.finditer(condition):
            name,operation,value=match[1],match[2],int(match[3],16)
            if name.startswith('@ram:'):actual=memories[capture['stem']][int(name.split('$')[1],16)]
            else:actual=capture['registers'][{'RL':'line','CY':'cycle'}.get(name,name.lower())]
            assert {'==':actual==value,'>=':actual>=value,'<=':actual<=value}[operation]
            checked.append(dict(predicate=match[0],actual=actual,expected=value,passed=True))
        result.append(dict(stem=capture['stem'],observed_stop_kind='natural exec breakpoint',checked_condition_predicates=checked,**row))
    return dict(setups=setups,natural_capture_stops=result,declared_read_only_interruptions=interrupts,
        numeric_PC_without_provenance_not_a_scene_identity=True)


def trace_events(case,wire,checkpoints,memories,captures):
    """Check all hits; retain compact aggregates for the long interrupted129 window."""
    from collections import Counter
    setups=[row for row in checkpoints['setups'] if row['kind']=='TRACE']
    header=re.compile(r'#([0-9]+) \(Trace\s+(exec|store) ([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\n')
    instruction=re.compile(r'^\.C:([0-9a-f]{4})\s+([0-9A-F]{2}(?: [0-9A-F]{2}){0,2})\s+(.+?)\s+- A:([0-9A-F]{2}) X:([0-9A-F]{2}) Y:([0-9A-F]{2}) SP:([0-9a-f]{2}) ([NV\-BDIZC.]{8})\s+(\d+)\n',re.M)
    b17=(BASE/'dali-analysis/accepted-03/b17-2000.bin').read_bytes()
    states={row['stem']:row['registers'] for row in captures}
    records=[];windows=[];totals=Counter()
    register_keys=('pc','a','x','y','sp','port00','port01','flags','line','cycle','clock')
    for sequence,row in sorted(case['responses'].items()):
        if row['command']!='x':continue
        text=row['response'];assert text.isascii()
        headers=list(header.finditer(text));assert text.count('(Trace')==len(headers)
        if not headers:continue
        if row['status']=='interrupted':
            terminal=interrupt_framing(row,wire)['frame_response_first']
            assert row['interrupt']['drained_registers_and_prompt']
        else:
            stop=re.search(r'^#[0-9]+ \(Stop on',text,re.M);assert stop
            terminal=stop.start()
        compact=sequence==129
        context_digest=hashlib.sha256();framing_digest=hashlib.sha256()
        counts=Counter();ports=Counter();targets=Counter();opcodes=Counter();sources=Counter()
        first_record=last_record=None;unmatched=[]
        for index,match in enumerate(headers):
            number,operation,address=int(match[1]),match[2],int(match[3],16)
            candidates=[setup for setup in setups if setup['number']==number and setup['setup']['sequence']<sequence]
            assert candidates
            setup=max(candidates,key=lambda candidate:candidate['setup']['sequence'])
            assert setup['operation']==operation and setup['first']<=address<=setup['last'] and 'attached_r' in setup
            assert setup['attached_r']['sequence']<sequence
            assert not any(case['responses'][n]['command'] in (f'delete {number}',f'command {number} "r"')
                           for n in range(setup['attached_r']['sequence']+1,sequence))
            end=headers[index+1].start() if index+1<len(headers) else terminal
            segment=text[match.end():end];ins=instruction.search(segment)
            assert ins and segment.count('Executing: r')==1
            pc=int(ins[1],16);raw=bytes.fromhex(ins[2]);regs=wire.registers(segment)
            if operation=='exec':assert regs['pc']==pc==address
            assert regs['clock']==int(ins[9])
            assert (regs['line'],regs['cycle'])==(int(match[4]),int(match[5]))
            assert (regs['clock']//63%312,regs['clock']%63)==(regs['line'],regs['cycle'])
            assert [regs[k] for k in ('a','x','y','sp')]==[int(ins[k],16) for k in (4,5,6,7)]
            source='not_equal_to_retained_code_references'
            if regs['clock']>=states['b17-controller']['clock'] and 0x2000<=pc and pc+len(raw)<=0x8722 and b17[pc-0x2000:pc-0x2000+len(raw)]==raw:
                source='independent_original_B17_bytes'
            elif 0x200<=pc and pc+len(raw)<=0x3fc and memories['installed'][pc:pc+len(raw)]==raw:
                source='earlier_original_installed_resident_bytes'
            elif regs['clock']>=states['b17-init']['clock'] and memories['b17-init'][pc:pc+len(raw)]==raw:
                source='earlier_initialized_RAM_bytes'
            record=dict(sequence=sequence,checkpoint=number,operation=operation,monitored_address=address,
                instruction_PC=pc,instruction_hex=raw.hex(),instruction=ins[3],registers=regs,
                setup_sequence=setup['setup']['sequence'],attached_r_sequence=setup['attached_r']['sequence'],
                received_first=row['received_first']+match.start(),received_end=row['received_first']+end,
                trace_block_bytes=end-match.start(),trace_block_sha256=sha(text[match.start():end].encode()),
                instruction_byte_reference=source)
            canonical=[number,operation,address,pc,raw.hex(),[regs[key] for key in register_keys],record['received_first'],record['received_end'],source]
            context_digest.update(json.dumps(canonical,separators=(',',':')).encode()+b'\n')
            framing_digest.update(json.dumps([record['received_first'],record['received_end'],record['trace_block_sha256']],separators=(',',':')).encode()+b'\n')
            counts[operation]+=1;totals[operation]+=1;ports[(regs['port00'],regs['port01'])]+=1
            targets[(operation,address)]+=1;opcodes[(operation,pc,raw.hex())]+=1;sources[source]+=1
            if first_record is None:first_record=record
            last_record=record
            if source=='not_equal_to_retained_code_references' and len(unmatched)<8:unmatched.append(record)
            if not compact:records.append(record)
        windows.append(dict(response=response_reference(row),terminal_kind=row['status'],trace_hits=len(headers),
            retention='all-hit aggregate and framing/context digests plus first/last records' if compact else 'complete per-hit records in named trace output',
            compact_long_window=compact,operation_counts=dict(sorted(counts.items())),
            ports=[dict(DDR=key[0],read01=key[1],hits=value) for key,value in sorted(ports.items())],
            targets=[dict(operation=key[0],address=key[1],hits=value) for key,value in sorted(targets.items())],
            instruction_codes=[dict(operation=key[0],PC=key[1],hex=key[2],hits=value) for key,value in sorted(opcodes.items())],
            instruction_byte_reference_counts=dict(sorted(sources.items())),
            all_hit_context_sha256=context_digest.hexdigest(),all_hit_raw_framing_sha256=framing_digest.hexdigest(),
            first_hit=first_record,last_hit=last_record,unmatched_reference_examples=unmatched,
            every_header_instruction_clock_beam_AXYSP_and_attached_r_checked=True))
        print(json.dumps(dict(trace_window=sequence,hits=len(headers),compact=compact)),flush=True)
    return dict(raw_windows=windows,hits=records,exec_trace_hits=totals['exec'],store_trace_hits=totals['store'],
        all_raw_trace_headers_parsed=True,physical_bus_write_count_inferred=False,
        digest_schema='One canonical JSON line per hit: [checkpoint,operation,address,instructionPC,hex,[PC,A,X,Y,SP,DDR,read01,flags,line,cycle,clock],absoluteFirst,absoluteEnd,codeReference]. Framing digest lines are [absoluteFirst,absoluteEnd,rawBlockSHA256].',
        scope='Every configured hit and attached r is loop-checked in original order. Long response129 spans many fields and stays compact; its complete original raw response is retained/pinned without filtering. Only other short windows serialize per-hit records. Exec rows precede the instruction; store rows carry observed post-instruction context. Code-reference counts distinguish independent B17 bytes, earlier native resident/initialized bytes, and unmatched runtime changes; no semantic normalization or device/pixel/completed-call claim is made.')


def command_audit(case,captures):
    # Exact external keyboard/media commands, if any, are separately pinned and
    # classified. They cannot hide a RAM/register/PC write in this grammar.
    assert PERIPHERAL_COMMANDS is not None
    observing=[r'r',r'sidefx off',r'bank ram',r'warp(?: on| off)?',r'resourceget "Speed"',
        r'help [a-z]+',r'break [0-9a-f]{4}',r'break exec [0-9a-f]{4} [0-9a-f]{4}(?: if .+)?',
        r'condition [0-9]+ if .+',r'trace exec [0-9a-f]{4}',r'trace store [0-9a-f]{4}(?: [0-9a-f]{4})?',r'command [0-9]+ \"r\"',r'delete [0-9]+',r'x',r'm [0-9a-f]{4} [0-9a-f]{4}',r'd [0-9a-f]{4} [0-9a-f]{4}',
        r'bsave "'+re.escape(str(CASE))+r'/[a-z0-9-]+-ram\.bin" 0 0000 ffff',
        r'dump "'+re.escape(str(CASE))+r'/[a-z0-9-]+\.vsf"',r'screenshot "'+re.escape(str(CASE))+r'/[a-z0-9-]+\.png" 2']
    expected={row['sequence']:row for row in PERIPHERAL_COMMANDS};observed=[]
    for sequence,row in case['responses'].items():
        if any(re.fullmatch(pattern,row['command']) for pattern in observing):continue
        assert sequence in expected and row['command']==expected[sequence]['command'],row['command']
        operation=expected[sequence]
        assert operation['kind'] in ('keyboard','media','joystick') and operation['context']
        if operation['kind']=='keyboard':assert re.fullmatch(r'keybuf \".*\"',row['command'])
        elif operation['kind']=='media':
            request=next(capture for capture in captures if capture['stem']==operation['request_capture'])
            assert request['registers']['pc']==operation['request_PC'] and request['registers']['a']==operation['request_A']
            assert request['snapshot_sequence']<sequence
            assert row['command'] in (f'attach \"{BASE}/release/the-hat-7a825b1-a.d64\" 8',f'attach \"{BASE}/release/the-hat-7a825b1-b.d64\" 8')
        else:raise AssertionError('Declare the exact legitimate joystick-input command grammar before accepting it')
        observed.append(dict(**expected[sequence],response=response_reference(row)))
    assert set(expected)=={r['sequence'] for r in observed}
    return dict(all_commands_classified=True,manual_RAM_PC_register_write_or_restore_commands=0,
        peripheral_operations=observed,scope='Disk/keyboard/peripheral input is explicit when present; it is not classified as absent or as a manual RAM/PC patch.')


def mode_queries(case):
    rows=[]
    for row in case['responses'].values():
        if row['command']=='warp':
            match=re.search(r'Warp mode is (on|off)\.',row['response']);assert match
            rows.append(dict(**response_reference(row),observed_warp=match[1]))
        elif row['command']=='resourceget "Speed"':assert re.search(r'Speed\s*=\s*100',row['response']);rows.append(response_reference(row))
    assert rows
    return dict(actual_query_responses=rows,limit='Only the recorded actual query instants prove their on/off or Speed100 values; launch resources alone do not establish current warp throughout unqueried navigation.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    out=parser.parse_args().output.resolve();out.relative_to((BASE/'native-analysis').resolve())
    assert not out.exists(),'Choose a fresh output directory'
    assert not CASE_SHA.startswith('PENDING'),'Only accept an owner-closed pinned case'
    for name,pin in PINS.items():assert sha((ROOT/name).read_bytes())==pin,name
    disks=original_disk_members();wire,case,adapter=audit_wire()
    reader=load('hat_native_snapshot','research/quondam/snapshot_state.py')
    memories,captures,pair_adapter=capture_pairs(reader,wire,case)
    decoded=independent_decoded_sources();sources=source_bindings(memories,captures,decoded)
    checkpoints=checkpoint_bindings(case,captures,wire,memories);traces=trace_events(case,wire,checkpoints,memories,captures);commands=command_audit(case,captures);modes=mode_queries(case)
    checked=Path(__file__).read_bytes()
    trace_raw=(json.dumps(traces.pop('hits'),indent=2)+'\n').encode()
    trace_output=dict(name='trace-hits.json',bytes=len(trace_raw),sha256=sha(trace_raw))
    traces['parsed_hits_output']=trace_output
    proof=dict(pass_=True,scope='Original The Hat side-A boot, explicit authentic side-B attach, independent A00/B17 source equality, and bounded closing-logo native custody; requested all-border UpScroll remains separate',
        producer=artifact(Path(__file__)),inputs=[artifact(ROOT/p) for p in PINS],case_sha256=CASE_SHA,case_manifest=artifact(BASE/MANIFEST_NAME),
        original_disk_lineage=disks,wire=wire.summary(case),wire_startup_adapter=adapter,capture_pair_adapter=pair_adapter,
        captures=captures,primary_port_schema=port_schema(),independent_decoded_sources=decoded,source_bindings=sources,checkpoint_bindings=checkpoints,command_audit=commands,
        actual_mode_queries=modes,monitor_traces=traces,waiting_notices=case['waits'],
        limits=['All wire events/bytes, completed/interrupted original handles and exact drained read-only interruption metadata remain; no event filtering, manual RAM/register/PC patch or snapshot restore.',
            'Any declared keyboard/media/peripheral operation remains explicit and separately classified; its absence is claimed only when the recorded list is empty.',
            'The wire auditor changes its startup assertion and exactly one interrupted-suffix call to bind the final explicit interrupt-r frame; ordinary register parsing stays strict. Pair checking changes an inherited fixed-DDR constant and adds an explicit interrupted-stop drain comparison, preserving every physical/CPU/readback/clock/beam check.',
            'Only source-known byte ranges claim independent original-file equality; earlier natural runtime bytes provide generation context, not static decoded-source or scene identity.',
            'CPU clocks are factual observation boundaries, not delivered FPS or retired-instruction counts.',
            'No complete ending identification, all-border algorithm, effect pixels, full-field/animation, physical-hardware or optimization claim.',
            'No emulator, native process, socket, CPU interpreter, subprocess, build or downloaded host execution occurs in this passive producer.'],
        outputs=[dict(name='native_case.checked.py',bytes=len(checked),sha256=sha(checked)),trace_output])
    raw=(json.dumps(proof,indent=2)+'\n').encode()
    out.mkdir(parents=True);(out/'native_case.checked.py').write_bytes(checked);(out/'trace-hits.json').write_bytes(trace_raw);(out/'native-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=True,pairs=len(captures),receipt_bytes=len(raw),receipt_sha256=sha(raw),peripheral_operations=len(commands['peripheral_operations']))))


if __name__=='__main__':main()
