#!/usr/bin/env python3
"""Passively check native-03, restored from original CA iteration D.

No CPU, emulator, input action, disk parsing or process is run. Closed-session
capture identity and independent file payload identity are separate gates.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re

from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'build/research/second-reality'
PARENT_SHA='fc9be5785818dd4febbd5f8a9837394956130f75582884516a562c45c140feb4'
SOURCE_SHA='eb75376e089794a6d1468090274b8a27259e3550b91f3139566e95e87beffe2c'
HELPER=ROOT/'research/second-reality/native_capture.py'
spec=importlib.util.spec_from_file_location('native_next_helpers',HELPER)
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
sha,relative=native.sha,native.relative


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,default=BASE/'native-03')
    parser.add_argument('--output',type=Path,default=BASE/'native-next-analysis')
    args=parser.parse_args();directory=args.capture.resolve();output=args.output.resolve()
    session=json.loads((directory/'session.json').read_text());assert session.get('closed_utc'),'Final capture gate requires a closed session.'
    parent_path=BASE/'native-parts-analysis/native-parts-evidence.json';data=parent_path.read_bytes()
    assert sha(data)==PARENT_SHA;parent=json.loads(data);assert parent['status']=='complete' and parent['pass'] is True
    assert sha(HELPER.read_bytes())==parent['helper_sha256']
    assert sha((ROOT/'research/quondam/snapshot_state.py').read_bytes())==parent['snapshot_reader_sha256']
    inherited=next(row for row in parent['checkpoints'] if row['stem']=='ca-iteration-d')
    source=ROOT/inherited['snapshot'];assert sha(source.read_bytes())==inherited['snapshot_sha256']
    text=(directory/'monitor.log').read_text(errors='replace')
    restores=list(re.finditer(r'^undump "([^"\n]+)"[ \t]*$',text,re.M))
    assert len(restores)==1 and Path(restores[0][1]).resolve()==source.resolve(),'Unexpected native-03 restore lineage.'
    restore=restores[0];clean=text[:restore.start()]+text[restore.end():]
    assert not native.interventions(clean),'Native-03 must have no synthetic input or direct monitor RAM write.'
    assert '[Monitor observation failed:' not in text,'Unclassified timeout in native-03.'
    observed=next((m for line in text[restore.end():].splitlines() if (m:=native.helpers.REGISTER.match(line.strip()))),None)
    assert observed is not None
    cpu=dict(pc=int(observed[1],16),a=int(observed[2],16),x=int(observed[3],16),y=int(observed[4],16),
             sp=int(observed[5],16),flags=int(observed[8],2),clock=int(observed[11]))
    assert cpu==native.cpu_state(source),'First observed CPU after restore does not match source.'
    events=native.contexts(text);by_name={};snapshots={}
    for event in events:
        assert event['filename'] not in by_name,('Capture filename reused',event['filename'])
        by_name[event['filename']]=event
        if event['command']!='dump':continue
        path=directory/event['filename'];state=native.read_snapshot(path);state_cpu=native.cpu_state(path)
        assert all(state_cpu[k]==event['registers'][k] for k in state_cpu),('Snapshot CPU versus recorded stop',path)
        assert [state['vicii']['raster_line'],state['vicii']['raster_cycle']]==[
            event['registers']['raster_line'],event['registers']['raster_cycle']],('Snapshot beam versus recorded stop',path)
        snapshots[path.stem]=(path,state)
    records=[];images=[]
    for event in events:
        if event['command']!='bsave':continue
        assert event['bank']=='ram' and (event['first'],event['end_inclusive'])==(0,65535)
        path=directory/event['filename'];assert path.name.startswith('ram-');stem=path.stem[4:]
        snapshot,state=snapshots[stem];assert by_name[snapshot.name]['registers']==event['registers']
        actual=path.read_bytes();assert len(actual)==65536
        check=native.comparison(actual,native.physical_ram(snapshot),0,65536,'All 65,536 raw physical RAM bytes versus same-stop VSF')
        records.append(dict(stem=stem,file=relative(path),sha256=sha(actual),snapshot=relative(snapshot),
                            snapshot_sha256=state['file_sha256'],registers=event['registers'],
                            transcript_line=event['transcript_line'],checks=[check],exact=check['exact']))
    for event in events:
        if event['command'] not in ('screenshot','scrsh'):continue
        path=directory/event['filename'];snapshot,state=snapshots[path.stem]
        assert by_name[snapshot.name]['registers']==event['registers']
        with Image.open(path) as image:image.load();size=list(image.size)
        images.append(dict(file=relative(path),sha256=sha(path.read_bytes()),pixels=size,
                           snapshot=relative(snapshot),registers=event['registers'],
                           interpretation='Original-program output observation, not an independent pixel oracle or whole-frame checkpoint.'))
    named={row['stem']:row for row in records}
    expected={'da-call':0xcf00,'da-return':0x0843,'db-return':0x084c,'ea-return':0x0855,
              'eb-return':0x085e,'db-entry':0xc000,'db-prepared':0xc620,
              **{f'db-iteration-{i}':0xc200 for i in 'abcd'}}
    assert set(named)==set(expected),('Unexpected or missing native-03 capture',set(named)^set(expected))
    for stem,pc in expected.items():assert named[stem]['registers']['pc']==pc,(stem,named[stem]['registers'])
    call=named['da-call']['registers'];assert [call['a'],call['x'],call['y']]==[0,0x44,0x41]
    oracle_path=BASE/'da-analysis/da-transition-proof.json';oracle_bytes=oracle_path.read_bytes()
    assert sha(oracle_bytes)==SOURCE_SHA,'Independent DA/DB/EA/EB source proof changed; review before repinning.'
    oracle=json.loads(oracle_bytes);assert oracle['pass'] is True and all(c['exact'] for c in oracle['checks'])
    for artifact in (oracle['script'],oracle['passive_helper']):
        assert sha((ROOT/artifact['path']).read_bytes())==artifact['sha256']
    for artifact in oracle['files'].values():
        data=(ROOT/artifact['path']).read_bytes()
        assert len(data)==artifact['bytes'] and sha(data)==artifact['sha256']
        assert int.from_bytes(data[:2],'little')==artifact['load_header']
        assert len(data)-2==artifact['payload_bytes'] and sha(data[2:])==artifact['payload_sha256']
    for capture in oracle['captures']:
        row=named[capture['name']]
        assert row['file']==capture['ram']['path'] and row['sha256']==capture['ram']['sha256']
        assert row['snapshot']==capture['snapshot']['path'] and row['snapshot_sha256']==capture['snapshot']['sha256']
    joined=[]
    for transfer in oracle['transfers']:
        prefix=transfer['prefix'];assert prefix in ('DA','DB','EA','EB')
        row=named[transfer['capture']];check=transfer['payload_check'];file=oracle['files'][prefix]
        assert all(row['registers'][k]==v for k,v in transfer['capture_cpu'].items())
        assert [check['first'],check['end_exclusive'],check['bytes']]==[
            file['load_header'],file['payload_end_exclusive'],file['payload_bytes']]
        assert check['exact'] is True and check['differences']==[] and check['matched_bytes']==check['bytes']
        assert check['actual_sha256']==check['expected_sha256']==file['payload_sha256']
        raw=(ROOT/row['file']).read_bytes()
        end_pointer=int.from_bytes(raw[0xcf3b:0xcf3d],'little')
        assert end_pointer==transfer['actual_loader_end_pointer']==file['payload_end_exclusive']
        contract=dict(prefix=prefix,source_file=file,comparison=check,loader_end_pointer=end_pointer,
                      interpretation='Pinned independent original-file comparison joined to the exact native return capture.')
        row['original_file_payload']=contract;joined.append(contract)
    assert len(joined)==4 and {x['prefix'] for x in joined}=={'DA','DB','EA','EB'}
    disk=Path(session['program']);disk_sha=parent['original_file_payload_proof']['configured_disk']['sha256']
    assert sha(disk.read_bytes())==disk_sha
    checks_pass=all(row['exact'] for row in records)
    result=dict(status='complete',pass_=checks_pass,capture_checks_pass=checks_pass,
                script_sha256=sha(Path(__file__).read_bytes()),helper_sha256=sha(HELPER.read_bytes()),
                snapshot_reader_sha256=sha((ROOT/'research/quondam/snapshot_state.py').read_bytes()),
                parent_native02_receipt_sha256=PARENT_SHA,session=session,
                restore_source=dict(file=relative(source),sha256=sha(source.read_bytes()),
                                    transcript_line=text[:restore.start()].count('\n')+1,first_observed_cpu=cpu,
                                    interpretation='Explicit continuation from native-02 CA iteration D, not another cold boot.'),
                transcript_sha256=sha((directory/'monitor.log').read_bytes()),synthetic_inputs=[],
                loader_call=dict(filename='DA',registers=call),checkpoints=records,screenshots=images,
                independent_payload_proof=dict(file=relative(oracle_path),sha256=SOURCE_SHA,
                    file_comparisons=len(joined),payload_bytes=sum(x['comparison']['bytes'] for x in joined),
                    source_transition_checks=len(oracle['checks']),configured_disk=dict(file=str(disk),sha256=disk_sha),
                    staging_copy=oracle['staging_copy']),independent_payload_proof_pending=False,
                scope='Closed native-03 lifecycle, restore and full RAM/VSF/CPU/beam identity with pinned independent original-file/transition evidence. DB logical iteration stops do not establish whole-frame or physical-VIC output.')
    result['pass']=result.pop('pass_');output.mkdir(parents=True,exist_ok=True)
    path=output/'native-next-evidence.json';path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],capture_checks_pass=checks_pass,RAM_snapshot_pairs=len(records),
                          screenshots=len(images),receipt=relative(path)),indent=2))
    assert checks_pass,'Native-03 RAM/VSF comparison failed; differences retained.'


if __name__=='__main__':main()
