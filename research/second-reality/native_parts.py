#!/usr/bin/env python3
"""Passively check the recorded Second Reality snapshot continuation.

This is not another cold boot. No emulator, process, CPU interpreter, input
injection or download is started; final evidence requires a closed session.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re

from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'build/research/second-reality'
NATIVE01_PROOF_SHA='33c3b6c18acdc407d2f56337ecc4a279d78932cab05b8950bdbabea555821be9'
PARTS_PROOF_SHA='98a0b452a175de22fac8a3fedc51cdf1f2d6685d3d196e882e347434e4da528c'
HELPER=ROOT/'research/second-reality/native_capture.py'
spec=importlib.util.spec_from_file_location('second_reality_native_helpers',HELPER)
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
sha,relative=native.sha,native.relative


def delta(before,after):
    assert len(before)==len(after)==65536
    return [dict(address=a,before=before[a],after=after[a]) for a in range(65536) if before[a]!=after[a]]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,default=BASE/'native-02')
    parser.add_argument('--output',type=Path,default=BASE/'native-parts-analysis')
    parser.add_argument('--allow-open-session',action='store_true')
    args=parser.parse_args();directory=args.capture.resolve();output=args.output.resolve()
    session=json.loads((directory/'session.json').read_text())
    closed=bool(session.get('closed_utc'))
    assert closed or args.allow_open_session,'Final receipt requires a closed continuation session.'
    parent_path=BASE/'native-analysis/native-evidence.json';parent_bytes=parent_path.read_bytes()
    assert sha(parent_bytes)==NATIVE01_PROOF_SHA
    parent=json.loads(parent_bytes);assert parent['status']=='complete' and parent['pass'] is True
    assert sha(HELPER.read_bytes())==parent['script_sha256'],'Native helper drifted from frozen native-01 proof.'
    assert sha(native.HELPER.read_bytes())==parent['reused_helper_sha256'],'Capture-context helper drifted.'
    assert sha((ROOT/'research/quondam/snapshot_state.py').read_bytes())==parent['snapshot_reader_sha256'],'Snapshot reader drifted.'
    inherited=next(r for r in parent['checkpoints'] if r['stage']=='demo-entry')
    restore_path=ROOT/inherited['snapshot'];assert sha(restore_path.read_bytes())==inherited['snapshot_sha256']
    text=(directory/'monitor.log').read_text(errors='replace')
    restores=list(re.finditer(r'^undump "([^"\n]+)"[ \t]*$',text,re.M))
    assert restores and Path(restores[0][1]).resolve()==restore_path.resolve(),('Unexpected initial restore lineage',restores)
    assert len(restores)<=3,'Unreviewed continuation branch.'
    events=native.contexts(text);clean=text;restore_records=[]
    for index,restore in enumerate(restores):
        source=Path(restore[1]).resolve()
        line=text[:restore.start()].count('\n')+1
        if index:
            expected_branch_source=(directory/'ca-return.vsf',directory/'ca-entry.vsf')[index-1]
            assert source==expected_branch_source,('Unreviewed later restore source',source)
            prior=next((e for e in events if e['command']=='dump' and e['filename']==source.name),None)
            assert prior is not None and prior['transcript_line']<line,'Branch source was not captured earlier in this session.'
        following=text[restore.end():restores[index+1].start() if index+1<len(restores) else len(text)]
        match=next((m for value in following.splitlines() if (m:=native.helpers.REGISTER.match(value.strip()))),None)
        assert match is not None,'Restore lacks an explicit CPU observation.'
        values=match.groups()
        observed=dict(pc=int(values[0],16),a=int(values[1],16),x=int(values[2],16),y=int(values[3],16),
                      sp=int(values[4],16),flags=int(values[7],2),clock=int(values[10]))
        assert observed==native.cpu_state(source),('First observed CPU after restore differs',source,observed)
        restore_records.append(dict(file=relative(source),sha256=sha(source.read_bytes()),
                                    approved_undump_transcript_line=line,first_observed_cpu=observed,
                                    interpretation=('Initial original native-01 snapshot continuation, not a cold boot.' if not index else
                                                    'Explicit later branch from an earlier native-02 snapshot; clocks must not be treated as monotonic across restore.')))
    # Remove only approved commands, preserving transcript line numbering.
    for restore in reversed(restores):clean=clean[:restore.start()]+clean[restore.end():]
    def branch_at(line):
        return sum(r['approved_undump_transcript_line']<line for r in restore_records)-1
    inputs=native.interventions(clean)
    expected=[2,0x40,2,0x40,2,0x40,1]
    assert [item['values'][0] for item in inputs]==expected,('Unexpected raw scan-result sequence',inputs)
    assert all(item['observed_stop']['pc']==0x8207 for item in inputs)
    for item in inputs:item['restore_branch_index']=branch_at(item['transcript_line'])
    failures=[]
    for failure in re.finditer(r'^\[Monitor observation failed: (.*?)\][ \t]*$',text,re.M):
        match=next((m for line in text[failure.end():].splitlines() if (m:=native.helpers.REGISTER.match(line.strip()))),None)
        line=text[:failure.start()].count('\n')+1
        failures.append(dict(transcript_line=line,restore_branch_index=branch_at(line),error=failure[1],
                             next_observed_cpu=(dict(pc=int(match[1],16),clock=int(match[11])) if match else None),
                             interpretation='Rejected intended-stop attempt; intervening execution was not captured and does not establish the requested entry.'))
    by_name={};snapshots={};pending=[]
    for event in events:
        assert event['filename'] not in by_name,('Capture filename reused',event['filename'])
        by_name[event['filename']]=event
    for event in events:
        if event['command']!='dump':continue
        path=directory/event['filename']
        if not path.exists():pending.append(path.name);continue
        state=native.read_snapshot(path);cpu=native.cpu_state(path)
        assert all(cpu[k]==event['registers'][k] for k in cpu),('Snapshot CPU versus observed stop',path)
        assert [state['vicii']['raster_line'],state['vicii']['raster_cycle']]==[
            event['registers']['raster_line'],event['registers']['raster_cycle']],('Snapshot beam versus observed stop',path)
        snapshots[path.stem]=(path,state)
    records=[];images=[];ram={}
    for event in events:
        if event['command']!='bsave':continue
        assert event['bank']=='ram' and (event['first'],event['end_inclusive'])==(0,65535)
        path=directory/event['filename'];assert path.name.startswith('ram-');stem=path.stem[4:]
        if not path.exists() or stem not in snapshots:pending.append(path.name);continue
        snapshot,state=snapshots[stem];assert by_name[snapshot.name]['registers']==event['registers']
        data=path.read_bytes();assert len(data)==65536
        check=native.comparison(data,native.physical_ram(snapshot),0,65536,'All 65,536 raw RAM bytes versus same-stop VSF')
        records.append(dict(stem=stem,file=relative(path),sha256=sha(data),snapshot=relative(snapshot),
                            snapshot_sha256=state['file_sha256'],registers=event['registers'],
                            transcript_line=event['transcript_line'],restore_branch_index=branch_at(event['transcript_line']),
                            checks=[check],exact=check['exact'],
                            interpretation='Original continuation exec-stop; payload identity is separately attached from the parts worker.'))
        ram[stem]=data
    for event in events:
        if event['command'] not in ('screenshot','scrsh'):continue
        path=directory/event['filename'];stem=path.stem
        if not path.exists() or stem not in snapshots:pending.append(path.name);continue
        snapshot,state=snapshots[stem];assert by_name[snapshot.name]['registers']==event['registers']
        with Image.open(path) as image:image.load();dimensions=list(image.size)
        images.append(dict(file=relative(path),sha256=sha(path.read_bytes()),pixels=dimensions,
                           snapshot=relative(snapshot),registers=event['registers'],
                           transcript_line=event['transcript_line'],restore_branch_index=branch_at(event['transcript_line']),
                           interpretation='Original output observation, not an independent pixel oracle.'))
    for stem,expected_options in [('configuration-default',[0,0,0]),('configuration-sid',[3,0,0])]:
        assert stem in ram and list(ram[stem][0x50:0x53])==expected_options,(stem,list(ram.get(stem,b'')[0x50:0x53]))
    configuration=dict(option_addresses=[0x50,0x51,0x52],before=[0,0,0],after=[3,0,0],
                       all_64K_differences=delta(ram['configuration-default'],ram['configuration-sid']),
                       interpretation='Observed execution of the original handler after synthetic inputs; unrelated RAM changes are retained, not masked.')
    calls=[]
    for stem,name,expected_a in [('first-loader-call','AA',0),('second-loader-call','BC',0),
                                 ('third-loader-call','BA',0),('fourth-loader-call','BB',8)]:
        if stem not in ram:pending.append(stem);continue
        record=next(row for row in records if row['stem']==stem);regs=record['registers']
        assert regs['pc']==0xcf00 and chr(regs['x'])+chr(regs['y'])==name and regs['a']==expected_a,(stem,regs)
        calls.append(dict(stem=stem,filename_registers=name,a=expected_a,registers=regs,
                          restore_branch_index=record['restore_branch_index'],
                          interpretation='Literal loader-entry register contract; A differs for BB and is not assumed interchangeable.'))
    if not args.allow_open_session:assert not pending,('Incomplete continuation capture',pending)
    parts_path=BASE/'parts/parts.json';parts_bytes=parts_path.read_bytes()
    assert sha(parts_bytes)==PARTS_PROOF_SHA,'Independent part proof changed; review before repinning.'
    parts=json.loads(parts_bytes);assert parts['pass'] is True
    assert parts['frozen_boot_proof_sha256']==parent['reference_proof_sha256']
    assert sha((ROOT/'research/second-reality/parts.py').read_bytes())==parts['script_sha256']
    source_files={row['name']:row for row in parts['files']}
    assert set(source_files)=={'AA','BC','BA','BB','BD','CA'}
    for item in source_files.values():
        data=(ROOT/item['file_path']).read_bytes()
        assert sha(data)==item['file_sha256'] and len(data)==item['file_bytes']
        assert int.from_bytes(data[:2],'little')==item['payload_first']
        assert sha(data[2:])==item['payload_sha256']
    disk=Path(session['program']);assert sha(disk.read_bytes())==parts['disk_sha256']
    required={('AA','first-loader-return'),('AA','first-part-entry'),('BC','bc-entry'),
              ('BA','fourth-loader-call'),('BB','bb-return'),('BD','bd-return'),('CA','ca-return')}
    joined=[]
    for item in parts['native_payload_comparisons']:
        stem=Path(item['file']).stem[4:]
        assert (item['name'],stem) in required and stem in ram
        record=next(row for row in records if row['stem']==stem)
        assert record['file']==item['file'] and record['sha256']==item['native_RAM_sha256']
        source=source_files[item['name']]
        assert [item['first'],item['end_exclusive'],item['bytes']]==[
            source['payload_first'],source['payload_end_exclusive'],source['payload_bytes']]
        assert item['exact'] is True and item['differences']==[] and item['matched_bytes']==item['bytes']
        contract=dict(name=item['name'],first=item['first'],end_exclusive=item['end_exclusive'],bytes=item['bytes'],
                      source_file=source['file_path'],source_file_sha256=source['file_sha256'],
                      payload_sha256=source['payload_sha256'],native_RAM_sha256=item['native_RAM_sha256'],
                      exact=True,scope='Pinned independent original-DOS-file payload comparison, joined to this exact captured RAM.')
        record.setdefault('file_payload_contracts',[]).append(contract);joined.append((item['name'],stem))
    assert set(joined)==required and len(joined)==len(required) and not parts['optional_absent_comparisons']
    # AA's own helper copy occurs after first-part-entry and before the BC
    # loader call. Only64 source bytes belong to AA; retain native provenance
    # for the remaining192 instead of extending the file with invented data.
    projection=parts['AA_projection']
    assert projection['source']==[0x9100,0x9200] and projection['destination']==[0xce00,0xcf00]
    assert projection['file_known_source']==[0x9100,0x9140] and projection['additional_bytes']==192
    aa_blob=(ROOT/source_files['AA']['file_path']).read_bytes()
    before_copy=ram['first-part-entry'];after_copy=ram['second-loader-call']
    assert before_copy[0x9100:0x9140]==aa_blob[0x102:0x142]
    assert before_copy[0x9140:0x9200]==after_copy[0x9140:0x9200],'AA source padding changed during observed interval.'
    expected=bytearray(65536);expected[0xce00:0xce40]=aa_blob[0x102:0x142]
    expected[0xce40:0xcf00]=before_copy[0x9140:0x9200]
    aa_copy=native.comparison(after_copy,expected,0xce00,0xcf00,'AA helper copy:64 file-defined and192 native-prestate bytes')
    aa_copy.update(before='first-part-entry',after='second-loader-call',file_defined_source=[0x9100,0x9140],
                   native_prestate_source=[0x9140,0x9200],native_prestate_source_sha256=sha(before_copy[0x9140:0x9200]),
                   before_RAM_sha256=sha(before_copy),source_padding_preserved=True,
                   interpretation='Captured state transition, not a claim that AA defines all256 bytes or that source padding is boot-independent.')
    second_call=next(row for row in records if row['stem']=='second-loader-call')
    second_call['checks'].append(aa_copy);second_call['exact']=all(c['exact'] for c in second_call['checks'])
    checks_pass=all(row['exact'] for row in records)
    result=dict(status='complete' if closed and not pending else 'provisional',
                pass_=checks_pass if closed and not pending else None,checks_pass=checks_pass,session=session,
                script_sha256=sha(Path(__file__).read_bytes()),helper_sha256=sha(HELPER.read_bytes()),
                snapshot_reader_sha256=sha((ROOT/'research/quondam/snapshot_state.py').read_bytes()),
                parent_native01_receipt_sha256=NATIVE01_PROOF_SHA,
                original_file_payload_proof=dict(file=relative(parts_path),sha256=PARTS_PROOF_SHA,
                                                source_script_sha256=parts['script_sha256'],
                                                configured_disk=dict(file=str(disk),sha256=parts['disk_sha256']),
                                                native_comparisons=len(joined),compared_bytes=sum(item['bytes'] for item in parts['native_payload_comparisons']),
                                                exact=True),
                restore_branches=restore_records,rejected_intended_stop_attempts=failures,
                transcript_sha256=sha((directory/'monitor.log').read_bytes()),synthetic_inputs=inputs,
                AA_native_prestate_copy=aa_copy,
                configuration=configuration,loader_calls=calls,checkpoints=records,screenshots=images,
                pending_capture_files=pending,payload_proof_pending=False,
                scope='Passive snapshot lineage, full physical RAM/VSF and CPU/beam equality, original configuration handler observations and loader-call registers. No independent image, keyboard-hardware, physical-VIC, sound or performance proof.')
    result['pass']=result.pop('pass_');output.mkdir(parents=True,exist_ok=True)
    target=output/'native-parts-evidence.json';target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],checks_pass=checks_pass,RAM_snapshot_pairs=len(records),
                          screenshots=len(images),synthetic_inputs=len(inputs),session_closed=closed,
                          payload_proof_pending=False,receipt=relative(target)),indent=2))
    assert checks_pass,'RAM/VSF mismatch retained in continuation receipt.'


if __name__=='__main__':main()
