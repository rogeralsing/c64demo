#!/usr/bin/env python3
"""Bind actual Second Reality part requests to original side1 DOS bytes.

No CPU, loader stub, hardware response, emulator or process is run. Native
files are optional comparison/observation targets, never payload inputs.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'build/research/second-reality'
DISK_SHA='05aa03c00be26cab0618f8802477d0bc7226af029c003a253a34bd32c630acf2'
EXPECTED={
    'AA':('956d4cbf6ce051b88f36abf9e36f9b8dcec1e0c5a7739b6643a49440ee57793e',0x9000,320),
    'BC':('25f2ec9af774fc49eba9ce0d1048722c73640ed23043fb23f45ce6d2aad581dc',0x8600,14656),
    'BA':('a7290cbe7cc5d032457c10ef4ed63a6e60cc5cc32e4637dd65093014d9acda35',0x0c00,5120),
    'BB':('4c345d0e3c1771fdfd28365c20d6db1940ded3d55728beb088818894d6bf328a',0x3000,12288),
    'BD':('99fae6d7d0b108be8f14a0ce067d96bc3aa661620d34b6493f7a1a76a4e7a49a',0xc000,2304),
    'CA':('b795d4bd191a6dd6a153fa827a3c3e0175fb720c3266a38ae09e441df13b7554',0x6000,6144),
}
def sha(b):return hashlib.sha256(b).hexdigest()
def count(t):
    assert 1<=t<=35
    return 21 if t<=17 else 19 if t<=24 else 18 if t<=30 else 17
def sector(d,t,s):
    assert 0<=s<count(t)
    offset=256*(sum(count(i) for i in range(1,t))+s)
    return d[offset:offset+256]
def directory(d):
    entries=[];seen=set();t,s=18,1
    while t:
        assert (t,s) not in seen;seen.add((t,s));block=sector(d,t,s)
        for i in range(8):
            raw=block[2+32*i:32+32*i]
            if raw[0]&7==2:
                entries.append(dict(directory_track=t,directory_sector=s,slot=i,type=raw[0],
                    raw_name_hex=raw[3:19].hex(),prefix=raw[3:5].decode('latin1'),
                    first_track=raw[1],first_sector=raw[2],declared_blocks=int.from_bytes(raw[28:30],'little')))
        t,s=block[:2]
    return entries
def extract(d,t,s):
    data=bytearray();chain=[];seen=set()
    while t:
        assert (t,s) not in seen;seen.add((t,s));block=sector(d,t,s)
        chain.append(dict(track=t,sector=s,link=list(block[:2]),sha256=sha(block)))
        data.extend(block[2:256 if block[0] else block[1]+1]);t,s=block[:2]
    return bytes(data),chain


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--disk',type=Path,default=BASE/'author-http-members/2ndReality_S1.D64')
    parser.add_argument('--capture',type=Path,default=BASE/'native-02')
    parser.add_argument('--output',type=Path,default=BASE/'parts')
    args=parser.parse_args();disk=args.disk.read_bytes()
    assert len(disk)==174848 and sha(disk)==DISK_SHA
    entries=directory(disk);args.output.mkdir(parents=True,exist_ok=True)
    records=[];images={}
    for name,(expected_sha,load,size) in EXPECTED.items():
        selected=[e for e in entries if e['prefix']==name];assert len(selected)==1
        entry=selected[0];blob,chain=extract(disk,entry['first_track'],entry['first_sector'])
        assert sha(blob)==expected_sha and len(blob)==size+2
        assert int.from_bytes(blob[:2],'little')==load and load+size<=65536
        path=args.output/f'side1-{name}.prg';path.write_bytes(blob)
        memory=bytearray(65536);memory[load:load+size]=blob[2:];images[name]=memory
        records.append(dict(name=name,side=1,entry=entry,DOS_chain=chain,
            file_path=str(path.relative_to(ROOT)),file_bytes=len(blob),file_sha256=sha(blob),
            payload_first=load,payload_end_exclusive=load+size,payload_bytes=size,payload_sha256=sha(blob[2:]),
            first32_payload_bytes=blob[2:34].hex(' ')))
    frozen=(BASE/'binary/file-derived-unpacked.ram').read_bytes()
    boot_proof=json.loads((BASE/'binary/boot-proof.json').read_text())
    core=boot_proof['RAM_only_decompressor']
    assert sha(frozen[core['output_first']:core['output_end_exclusive']])==core['output_sha256']
    assert bytes.fromhex('8a 20 94 cf 98 20 94 cf') in frozen[0xcf74:0xcf94]
    assert frozen[0xcf24:0xcf35]==bytes.fromhex('20 c0 cf b0 1f 8d 3b cf 20 c0 cf 8d 3c cf ee 01 cf')
    assert frozen[0xcf35:0xcf48]==bytes.fromhex('20 c0 cf b0 0e 8d ff ff ee 3b cf d0 03 ee 3c cf 4c 35 cf')
    assert images['AA'][0x9100:0x9116]==bytes.fromhex('a2 42 a0 43 a9 00 20 00 cf a2 00 a9 00 9d 00 cb e8 d0 fa 4c 00 90')
    assert images['BC'][0x97c0:0x97e4]==bytes.fromhex('20 00 cf a2 42 a0 42 a9 08 20 00 cf a2 42 a0 44 a9 08 20 00 cf a9 00 20 00 0c a2 43 a0 41 a9 00 20 00 cf 60')
    comparisons=[]
    targets=[('AA','ram-first-loader-return.bin'),('AA','ram-first-part-entry.bin'),
             ('BC','ram-bc-entry.bin'),('BA','ram-fourth-loader-call.bin'),
             ('BB','ram-bb-return.bin'),('BD','ram-bd-return.bin'),('CA','ram-ca-return.bin')]
    absent=[]
    for name,filename in targets:
        path=args.capture/filename
        if not path.exists():absent.append(dict(name=name,file=filename));continue
        actual=path.read_bytes();assert len(actual)==65536
        _,load,size=EXPECTED[name];expected=images[name]
        differences=[dict(address=a,expected=expected[a],actual=actual[a]) for a in range(load,load+size) if actual[a]!=expected[a]]
        comparisons.append(dict(name=name,file=str(path.relative_to(ROOT)),native_RAM_sha256=sha(actual),
            first=load,end_exclusive=load+size,bytes=size,exact=not differences,
            matched_bytes=size-len(differences),differences=differences,
            scope='Payload-only byte comparison. Native context/RAM-VSF lifecycle belongs to the native checker.'))
    observed_calls=[];configuration=[]
    log=args.capture/'monitor.log'
    if log.exists():
        spec=importlib.util.spec_from_file_location('second_parts_nine_reader',ROOT/'research/nine/native_capture.py')
        reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
        for event in reader.contexts(log.read_text(errors='replace')):
            if event['command']!='bsave' or event['bank']!='ram':continue
            reg=event['registers'];path=args.capture/event['filename']
            if not path.exists():continue
            actual=path.read_bytes();assert len(actual)==65536
            if reg['pc']==0xcf00:
                request=bytes((reg['x'],reg['y'])).decode('latin1')
                assert actual[0xcf00]==0x24 and actual[0xcf02:0xcf15]==frozen[0xcf02:0xcf15]
                observed_calls.append(dict(file=str(path.relative_to(ROOT)),registers=reg,
                    requested_prefix=request,mode_before_AND=reg['a'],mode_after_AND=reg['a']&0xef,
                    CF01_operand=actual[0xcf01],
                    RTS_target=(int.from_bytes(bytes((actual[0x100+((reg['sp']+1)&255)],actual[0x100+((reg['sp']+2)&255)])),'little')+1)&65535,
                    mapped_file=request if request in EXPECTED else None))
        for filename in ('ram-configuration-default.bin','ram-configuration-sid.bin'):
            path=args.capture/filename
            if path.exists():
                actual=path.read_bytes();configuration.append(dict(file=str(path.relative_to(ROOT)),
                    options_at_this_capture={f'{a:04x}':actual[a] for a in (0x50,0x51,0x52)},
                    scope='These option addresses are reused later; this is not persistent configuration state.'))
    report=dict(pass_=True,script_sha256=sha(Path(__file__).read_bytes()),disk_sha256=DISK_SHA,files=records,
        frozen_boot_proof_sha256=sha((BASE/'binary/boot-proof.json').read_bytes()),
        protocol=dict(command_send_order=['X','Y'],header_order=['destination_low','destination_high'],
                      header_store_pcs=[0xcf29,0xcf2f],payload_store_pc=0xcf3a,
                      destination_increment_pcs=[0xcf3d,0xcf42],header_counter_increment=0xcf32,
                      CF01_scope='BIT zero-page operand increments per received header; separate from fixed code signature'),
        AA_projection=dict(source=[0x9100,0x9200],destination=[0xce00,0xcf00],
            file_known_source=[0x9100,0x9140],file_known_destination=[0xce00,0xce40],
            additional_source_not_established_by_AA=[0x9140,0x9200],additional_bytes=192,
            head_requests=dict(call_pc=0xce06,mode=0,x=0x42,y=0x43,name='BC'),
            after_return='Clear CB00..CBFF, then JMP9000; no entry decompressor'),
        BC_requests=[dict(call_pc=0x97c0,mode='from caller',name='BA observed natively'),
                     dict(call_pc=0x97c9,mode=8,name='BB'),dict(call_pc=0x97d2,mode=8,name='BD'),
                     dict(call_pc=0x97e0,mode=0,name='CA')],
        BC_music_call=dict(pc=0x97d7,target=0x0c00),
        CA_staging=dict(first=0x6000,end_exclusive=0x7800,
            first24_bytes=images['CA'][0x6000:0x6018].hex(' '),
            first_JSR_operand=0xc390,
            scope='6000 is the file load destination, not an established execution entry. '
                  'The staged bytes contain C000-space absolute targets; relocation and execution '
                  'are a separate analysis. C390 also lies within the previously loaded BD range, '
                  'which alone does not establish an executed dependency.'),
        native_payload_comparisons=comparisons,optional_absent_comparisons=absent,
        observed_native_calls=observed_calls,configuration_observations=configuration,
        scope='Original side1 DOS extraction, AA/BC request mapping, and optional raw native payload comparisons only. No CPU, hardware stub, native actions, CA execution-entry, general depacker, renderer role or timing claim.')
    report['pass']=report.pop('pass_') and all(c['exact'] for c in comparisons)
    (args.output/'parts.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(pass_=report['pass'],files=len(records),native_payload_comparisons=len(comparisons),
                         all_payloads_exact=all(c['exact'] for c in comparisons)),indent=2))
    assert report['pass'],'Payload mismatches retained in parts.json'


if __name__=='__main__':main()
