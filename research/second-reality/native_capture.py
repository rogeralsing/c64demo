#!/usr/bin/env python3
"""Passively validate archived original Second Reality native captures.

No emulator, process, CPU interpreter, input injection or download is started.
Final evidence requires a closed capture session. File-derived byte contracts
and a native-prestate loader-copy contract are labelled separately.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'build/research/second-reality'
BINARY = BASE/'binary'
BOOT_SHA = 'c62598561f3bb6d74e9c399385df6e1dd21890c9fc0abbd952a2a61548a286f5'
PROOF_SHA = '92f272cd978c594467c72a9be0536b29685fbbe0e68e1b18a71d8b9c2718cdfd'
OUTPUT_SHA = '7599810d51826909c19a4ffd9d2a739b4b45ec1a52ef7a8d36f1ecbe5179f6cd'
HELPER = ROOT/'research/nine/native_capture.py'
REJECTED_TIMEOUTS = {
    'first-load-call':dict(pc=0xc404,clock=440589240,intended_pc=0xcf00),
    'first-load-ready':dict(pc=0xc409,clock=747576649,intended_pc=0xce0e),
}
spec = importlib.util.spec_from_file_location('nine_native_helpers',HELPER)
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
contexts,physical_ram,comparison = helpers.contexts,helpers.physical_ram,helpers.comparison
sys.path.insert(0,str(ROOT/'research/quondam'))
from snapshot_state import read_snapshot,module_payload


def sha(data):
    return hashlib.sha256(data).hexdigest()


def relative(path):
    return str(path.resolve().relative_to(ROOT))


def cpu_state(snapshot):
    metadata = read_snapshot(snapshot)['modules']['MAINCPU']
    assert metadata['version']==[1,4] and metadata['payload_size']==103,metadata
    data = module_payload(snapshot,'MAINCPU')
    return dict(clock=int.from_bytes(data[:8],'little'),a=data[8],x=data[9],y=data[10],
                sp=data[11],pc=int.from_bytes(data[12:14],'little'),flags=data[14])


def interventions(text):
    """Retain explicit monitor writes and the latest observed stop, not keys."""
    result=[]; observed=None; last_raster=None
    for number,line in enumerate(text.splitlines(),1):
        line=line.strip()
        register=helpers.REGISTER.match(line)
        if register:
            values=register.groups()
            observed=dict(pc=int(values[0],16),clock=int(values[10]),
                          raster_line=int(values[8]),raster_cycle=int(values[9]))
        hit=re.match(r'#\d+ \(Stop on .*?\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+',line,re.I)
        if hit:
            last_raster=(int(hit[1]),int(hit[2]))
        stop=re.match(r'\.C:([0-9a-f]{4}).* - A:[0-9a-f]{2} X:[0-9a-f]{2} Y:[0-9a-f]{2} SP:[0-9a-f]{2}.*?\s(\d+)$',line,re.I)
        if stop and last_raster:
            observed=dict(pc=int(stop[1],16),clock=int(stop[2]),
                          raster_line=last_raster[0],raster_cycle=last_raster[1])
        write=re.fullmatch(r'>\s+([0-9a-f]{1,4})\s+((?:[0-9a-f]{1,2}\s*)+)',line,re.I)
        if write:
            address=int(write[1],16); data=[int(v,16) for v in write[2].split()]
            assert address==0xcb and len(data)==1,('Unclassified monitor RAM write',number,line)
            assert observed is not None,('Input write lacks observed stop',number)
            result.append(dict(transcript_line=number,command=line,address=address,values=data,
                               observed_stop=dict(observed),
                               interpretation='Synthetic raw scan-result RAM input, not keyboard hardware or a code/PC patch.'))
        assert not re.match(r'(?:undump|goto|g)\s',line,re.I),('Unexpected execution-state intervention',number,line)
        assert not re.match(r'r\s+\w+\s*=',line,re.I),('Unexpected register mutation',number,line)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,default=BASE/'native-01')
    parser.add_argument('--output',type=Path,default=BASE/'native-analysis')
    parser.add_argument('--allow-open-session',action='store_true',help='Emit explicitly provisional evidence while captures grow.')
    args=parser.parse_args(); directory=args.capture.resolve(); output=args.output.resolve()
    session=json.loads((directory/'session.json').read_text())
    closed=bool(session.get('closed_utc'))
    assert closed or args.allow_open_session,'Final receipt requires a closed session.'
    program=(BINARY/'side1-boot.prg').read_bytes()
    assert len(program)==42890 and sha(program)==BOOT_SHA
    proof_path=BINARY/'boot-proof.json'; proof_bytes=proof_path.read_bytes()
    assert sha(proof_bytes)==PROOF_SHA,'Independent binary reference changed; review before repinning.'
    proof=json.loads(proof_bytes); assert proof['pass'] and proof['boot_sha256']==BOOT_SHA
    unpacked=(BINARY/'file-derived-unpacked.ram').read_bytes()
    conditional=(BINARY/'conditional-SFX-copy-prefix.ram').read_bytes()
    assert len(unpacked)==len(conditional)==65536
    assert sha(conditional)==proof['conditional_SFX_pager']['RAM_sha256'],'Conditional SFX reference drifted from the pinned file-only proof.'
    assert sha(unpacked[0x7e8:0xf2e0])==OUTPUT_SHA
    assert proof['RAM_only_decompressor']['output_sha256']==OUTPUT_SHA
    original=bytearray(65536); original[0x801:0xaf89]=program[2:]
    relocated=bytearray(original); relocated[0x801:0xa901]=original[0xa00:0xab00]
    text=(directory/'monitor.log').read_text(errors='replace')
    events=contexts(text); by_name={}; pending=[]
    for event in events:
        assert event['filename'] not in by_name,('Capture filename reused',event['filename'])
        by_name[event['filename']]=event
    snapshots={}
    for event in events:
        if event['command']!='dump': continue
        path=directory/event['filename']
        if not path.exists():
            pending.append(event['filename']); continue
        state=read_snapshot(path); cpu=cpu_state(path)
        assert all(cpu[key]==event['registers'][key] for key in cpu),('VSF versus recorded CPU stop',path,cpu,event['registers'])
        beam_match=[state['vicii']['raster_line'],state['vicii']['raster_cycle']]==[
            event['registers']['raster_line'],event['registers']['raster_cycle']]
        if path.stem in REJECTED_TIMEOUTS:
            rejected=REJECTED_TIMEOUTS[path.stem]
            assert cpu['pc']==rejected['pc'] and cpu['clock']==rejected['clock'],('Rejected timeout identity changed',path)
        else:
            assert beam_match,('VSF versus recorded beam',path)
        snapshots[path.stem]=(path,state)
    records=[]; actual_by_stem={}; images=[]
    for event in events:
        if event['command']!='bsave': continue
        assert event['bank']=='ram' and (event['first'],event['end_inclusive'])==(0,65535),event
        file=directory/event['filename']; assert file.name.startswith('ram-')
        stem=file.stem[4:]
        if not file.exists() or stem not in snapshots:
            pending.append(event['filename']); continue
        snapshot,state=snapshots[stem]; actual=file.read_bytes(); assert len(actual)==65536
        snapshot_event=by_name[snapshot.name]
        assert snapshot_event['registers']==event['registers'],('RAM/VSF capture stops differ',file)
        checks=[comparison(actual,physical_ram(snapshot),0,65536,'All 65,536 raw physical RAM bytes versus same-stop VSF')]
        established=True; stage=stem
        if stem=='boot-entry':
            assert event['registers']['pc']==0x900
            checks.append(comparison(actual,original,0x801,0xaf89,'All 42,888 original loaded file bytes'))
        elif stem=='copied-entry':
            assert event['registers']['pc']==0xc000
            expected=bytearray(65536); expected[0xc000:0xc100]=original[0x980:0xa80]
            expected[0x5e0:0x608]=original[0x8c0:0x8e8]
            checks.extend([comparison(actual,expected,0xc000,0xc100,'File-derived 256-byte outer wrapper'),
                           comparison(actual,expected,0x5e0,0x608,'File-derived 40-byte text copy')])
        elif stem=='loader-call':
            assert event['registers']['pc']==0xc028
            before=(directory/'ram-copied-entry.bin').read_bytes(); assert len(before)==65536
            expected=bytearray(65536); expected[0xca00:0xcf00]=before[0xab00:0xb000]
            check=comparison(actual,expected,0xca00,0xcf00,'Native pre-state five-page loader-copy transition')
            check.update(source_native_file='ram-copied-entry.bin',source_sha256=sha(before),
                         source_range=[0xab00,0xb000],file_defined_source=[0xab00,0xaf89],
                         non_file_source=[0xaf89,0xb000],non_file_bytes=119,
                         interpretation='The 119 padding bytes come only from captured native pre-RAM, not invented file contents.')
            checks.append(check)
        elif stem=='packed-entry':
            assert event['registers']['pc']==0x80d
            checks.append(comparison(actual,relocated,0x801,0xa901,'All 41,216 file-derived 161-page relocation bytes'))
        elif stem=='depack-entry':
            assert event['registers']['pc']==0x40b
            checks.extend([comparison(actual,conditional,0x400,0x478,'All 120 file-derived decompressor code bytes'),
                           comparison(actual,conditional,0x6053,0x10000,'All 40,877 file-derived compressed-reader input bytes')])
        elif stem=='first-entry':
            assert event['registers']['pc']==0x9400
            checks.append(comparison(actual,unpacked,0x7e8,0xf2e0,'All 60,152 independently reconstructed SFX output bytes'))
        else:
            established=False
        records.append(dict(file=relative(file),sha256=sha(actual),snapshot=relative(snapshot),
                            snapshot_sha256=state['file_sha256'],registers=event['registers'],
                            stage=stage,established_byte_checkpoint=established,checks=checks,
                            exact=all(c['exact'] for c in checks),
                            interpretation=('Byte contract above; no general later-machine equivalence.' if established else
                                            'Observed original-program stop; only same-stop raw-RAM/VSF equality is asserted.')))
        if stem in REJECTED_TIMEOUTS:
            records[-1].update(rejected_timeout_observation=dict(
                **REJECTED_TIMEOUTS[stem],monitor_beam=[event['registers']['raster_line'],event['registers']['raster_cycle']],
                snapshot_beam=[state['vicii']['raster_line'],state['vicii']['raster_cycle']],
                reason='Capture owner explicitly rejected this async timeout stop: intended handoff was not reached. No beam-equality or successful-loader-checkpoint claim.'),
                interpretation='Rejected timeout observation. RAM/VSF and CPU identity checks remain; timing and intended-handoff claims are excluded.')
        actual_by_stem[stem]=(actual,snapshot,event['registers'])
    for event in events:
        if event['command'] not in ('screenshot','scrsh'): continue
        file=directory/event['filename']; stem=file.stem
        if not file.exists() or stem not in snapshots:
            pending.append(event['filename']); continue
        snapshot,state=snapshots[stem]
        assert by_name[snapshot.name]['registers']==event['registers']
        with Image.open(file) as image:
            image.load(); dimensions=list(image.size)
        images.append(dict(file=relative(file),sha256=sha(file.read_bytes()),pixels=dimensions,
                           snapshot=relative(snapshot),registers=event['registers'],
                           interpretation='Original output observation; no independent full-image oracle or keyboard-hardware proof.'))
    inputs=interventions(text)
    assert inputs and inputs[0]['values']==[0x3b]
    before,before_vsf,before_reg=actual_by_stem['startup-menu']
    after,after_vsf,after_reg=actual_by_stem['menu-key-injected']
    input_delta=[dict(address=a,before=before[a],after=after[a]) for a in range(65536) if before[a]!=after[a]]
    assert input_delta==[dict(address=0xcb,before=0x40,after=0x3b)],input_delta
    assert before_reg==after_reg and before_reg['pc']==0x9767 and before_reg['clock']==124281759
    cpu_equal=module_payload(before_vsf,'MAINCPU')==module_payload(after_vsf,'MAINCPU')
    assert cpu_equal,'Paused synthetic menu write changed CPU snapshot state.'
    if not args.allow_open_session:
        assert not pending,('Unpaired or incomplete captures',pending)
    required={'boot-entry','copied-entry','loader-call','packed-entry','depack-entry','first-entry'}
    assert required.issubset(actual_by_stem),('Missing required byte checkpoint',required-set(actual_by_stem))
    checks_pass=all(row['exact'] for row in records)
    result=dict(status='complete' if closed and not pending else 'provisional',pass_=checks_pass if closed and not pending else None,
                checks_pass=checks_pass,session=session,script_sha256=sha(Path(__file__).read_bytes()),
                reused_helper_sha256=sha(HELPER.read_bytes()),
                snapshot_reader_sha256=sha((ROOT/'research/quondam/snapshot_state.py').read_bytes()),
                reference_proof_sha256=PROOF_SHA,program_sha256=BOOT_SHA,output_sha256=OUTPUT_SHA,
                transcript_sha256=sha((directory/'monitor.log').read_bytes()),checkpoints=records,screenshots=images,
                rejected_timeout_observations=[r['stage'] for r in records if 'rejected_timeout_observation' in r],
                pending_capture_files=pending,synthetic_inputs=inputs,
                menu_input_transition=dict(before='startup-menu',after='menu-key-injected',
                                           full_64K_differences=input_delta,recorded_cpu_registers_equal=before_reg==after_reg,
                                           complete_MAINCPU_payload_equal=cpu_equal,
                                           interpretation='One paused raw scan-result write, not a physical key event.'),
                scope='Passive original-file/SFX byte identity, explicitly separate native-prestate copy transition, same-stop RAM/VSF equality, and recorded synthetic inputs. No independent renderer, full-image, keyboard hardware, sound, drive-timing or frame-rate proof.')
    result['pass']=result.pop('pass_'); output.mkdir(parents=True,exist_ok=True)
    target=output/'native-evidence.json'; target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],checks_pass=checks_pass,pass_=result['pass'],
                          RAM_snapshot_pairs=len(records),screenshots=len(images),synthetic_input_writes=len(inputs),
                          receipt=relative(target)),indent=2))
    assert checks_pass,'Capture comparison mismatch; exact differences are retained.'


if __name__=='__main__':
    main()
