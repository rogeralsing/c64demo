#!/usr/bin/env python3
"""Passively bind CA's exit/CB bridge to the DA, DB, EA and EB transfers.

Headers, actual bytes, source instructions and native boundaries remain separate.
No CPU, loader, hardware, drive, emulator or new web request is executed here.
"""
import argparse
import json
from pathlib import Path

from inspect_ca import BASE, ROOT, comparison, native, record, sha

FILES = {
    'CA': ('side1-entry14-CA.prg',0x6000,6144,'b795d4bd191a6dd6a153fa827a3c3e0175fb720c3266a38ae09e441df13b7554'),
    'CB': ('side1-entry15-CB.prg',0x8000,4096,'7ae9c9ad3040539c4659b4b370f161ccfd1b99677f2a8db042b21d8de9201955'),
    'DA': ('side1-entry16-DA.prg',0x4000,2048,'e3cb254ab2362ec54cca87386dd388658736953c163f89b607cb7781af65c137'),
    'DB': ('side1-entry17-DB.prg',0xc000,3072,'1c820bd4bc9d47a78f4c3c291be3a2ef7fd4f7a6754843632cfaf8410a48a8f2'),
    'EA': ('side1-entry18-EA.prg',0x6000,3817,'2444dd10effe58b3bc96decaf0199f75433aa74f03a5815bb4445512943ca8ce'),
    'EB': ('side1-entry19-EB.prg',0x7000,3976,'9c0758f571f5ba71b3224a9d1ed1084d07b1adc7e50374e68f07fbcec548f887'),
}


def load_inputs():
    images, records = {}, {}
    for name,(filename,target,size,digest) in FILES.items():
        path=BASE/'disk-map'/filename; blob=path.read_bytes()
        assert len(blob)==size+2 and int.from_bytes(blob[:2],'little')==target and sha(blob)==digest
        memory=bytearray(65536); memory[target:target+size]=blob[2:]
        images[name]=memory; records[name]=dict(**record(path),load_header=target,payload_bytes=size,
                                              payload_end_exclusive=target+size,payload_sha256=sha(blob[2:]))
    return images,records


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,default=BASE/'native-03')
    parser.add_argument('--output',type=Path,default=BASE/'da-analysis')
    args=parser.parse_args(); output=args.output.resolve(); output.mkdir(parents=True,exist_ok=True)
    session_path=args.capture/'session.json'; session=json.loads(session_path.read_text())
    assert session.get('closed_utc'),'Final transition binding requires the owner-closed session.'
    images,files=load_inputs()
    ca=images['CA']; bridge=bytearray(65536)
    bridge[0x800:0xc00]=images['CB'][0x8c00:0x9000]
    # Literal guards establish the actual path and request bytes, not names
    # inferred from archive ordering or PRG headers.
    assert ca[0x6ae2:0x6ae5]==bytes.fromhex('4c 00 09')
    assert bridge[0x90e:0x911]==bytes.fromhex('4c 78 09')
    assert bridge[0x9b3:0x9b9]==bytes.fromhex('20 1a 0a 4c 11 09')
    assert bridge[0xb50:0xb58]==bytes.fromhex('a9 01 8d c0 02 4c 80 08')
    assert bridge[0x880:0x883]==bytes.fromhex('20 00 08')
    calls=[('DA',0x83a,0x840,0x843),('DB',0x843,0x849,0x84c),('EA',0x84c,0x852,0x855),('EB',0x855,0x85b,0x85e)]
    for name,setup,call,ret in calls:
        assert bridge[setup:ret]==bytes([0xa2,ord(name[0]),0xa0,ord(name[1]),0xa9,0,0x20,0,0xcf])
    assert bridge[0x85e:0x878]==bytes.fromhex('a2 00 bd 00 cf 9d 00 6f a9 00 9d 00 cc 9d 00 cd 9d 00 ce 9d 00 cf e8 d0 e9 60')
    assert bridge[0x8c6:0x8c9]==bytes.fromhex('4c 00 c0')
    captures={name:native(args.capture,name) for name in ('da-call','da-return','db-return','ea-return','eb-return','db-entry','db-prepared')}
    call_cpu=captures['da-call'][2]
    assert (call_cpu['pc'],call_cpu['a'],call_cpu['x'],call_cpu['y'])==(0xcf00,0,ord('D'),ord('A'))
    transfers=[]; checks=[]
    for name,setup,call,ret in calls:
        capture_name=name.lower()+'-return'; actual,state,cpu,metadata=captures[capture_name]
        assert cpu['pc']==ret
        first=files[name]['load_header']; end=files[name]['payload_end_exclusive']
        check=comparison(actual,images[name],first,end,f'Every original {name} payload byte at its actual return')
        loader_end=int.from_bytes(actual[0xcf3b:0xcf3d],'little')
        assert loader_end==end
        checks.append(check)
        transfers.append(dict(prefix=name,setup_pc=setup,call_pc=call,return_pc=ret,source_argument_a=0,
                              source_argument_x=ord(name[0]),source_argument_y=ord(name[1]),capture=capture_name,
                              payload_check=check,actual_loader_end_pointer=loader_end,
                              end_pointer_location=[0xcf3b,0xcf3d],capture_cpu=cpu))
    da_call=captures['da-call'][0]; db_entry=captures['db-entry'][0]; prepared=captures['db-prepared'][0]
    # The bridge is code carried in the last1KiB of CB's already loaded data.
    # Its three color-table bytes are self-modified during this bridge display;
    # retain the entire difference list as well as the exact code intervals.
    cb_observation=comparison(da_call,bridge,0x800,0xc00,'Full restored CB tail after its initialization/IRQ color updates')
    checks.extend([comparison(da_call,bridge,0x800,0xb88,'Restored CB instruction/data bytes before three named color cells'),
                   comparison(da_call,bridge,0xb8b,0xc00,'Restored CB instruction/data bytes after three named color cells'),
                   comparison(da_call,images['CB'],0x8000,0x8c00,'All3072 CB graphic bytes restored from RAM under I/O')])
    previous=BASE/'native-02/ram-ca-iteration-d.bin'; previous_ram=previous.read_bytes(); assert len(previous_ram)==65536
    under_io=bytearray(65536); under_io[0xd000:0xe000]=images['CB'][0x8000:0x9000]
    checks.append(comparison(previous_ram,under_io,0xd000,0xe000,'All4096 original CB bytes parked under I/O before CA exit'))
    checks.append(comparison(da_call,previous_ram,0xd000,0xe000,'Parked CB bytes retain exact identity through bridge entry'))
    zero=bytearray(65536)
    loader_expected=bytearray(65536); loader_expected[0x6f00:0x7000]=captures['eb-return'][0][0xcf00:0xd000]
    checks.extend([comparison(db_entry,loader_expected,0x6f00,0x7000,'All256 current loader bytes explicitly backed up inside EA staging tail'),
                   comparison(db_entry,zero,0xcc00,0xd000,'All1024 retired screen/loader-page bytes cleared before DB entry')])
    gaps=[comparison(captures['ea-return'][0],captures['db-return'][0],0x6ee9,0x7000,'EA loader transfer preserves279 bytes after actual payload end'),
          comparison(captures['eb-return'][0],captures['ea-return'][0],0x7f88,0x8000,'EB loader transfer preserves120 bytes after actual payload end'),
          comparison(db_entry,captures['eb-return'][0],0x6ee9,0x6f00,'The23-byte stale tail before loader backup remains unchanged'),
          comparison(db_entry,captures['eb-return'][0],0x7f88,0x8000,'The120-byte EB stale tail remains unchanged at DB entry')]
    checks.extend(gaps)
    stage_expected=bytearray(65536); stage_expected[0x2000:0x4000]=db_entry[0x6000:0x8000]
    staged=comparison(prepared,stage_expected,0x2000,0x4000,'Full8192-byte DB staging copy conditional on actual entry RAM, including every non-file byte')
    checks.append(staged)
    stage_file_checks=[]
    for name,target in (('EA',0x2000),('EB',0x3000)):
        first=files[name]['load_header']; size=files[name]['payload_bytes']; expected=bytearray(65536)
        expected[target:target+size]=images[name][first:first+size]
        stage_file_checks.append(comparison(prepared,expected,target,target+size,f'Every original {name} file byte at its later staging location'))
    checks.extend(stage_file_checks)
    assert captures['db-entry'][2]['pc']==0xc000 and db_entry[0xc000:0xc020]==images['DB'][0xc000:0xc020]
    assert images['DB'][0xc039:0xc05a]==bytes.fromhex('a9 00 85 50 85 52 a9 60 85 51 a9 20 85 53 a0 00 b1 50 91 52 c8 d0 f9 e6 51 e6 53 a5 51 c9 80 d0 ed')
    report=dict(script=record(Path(__file__)),passive_helper=record(ROOT/'research/second-reality/inspect_ca.py'),
                files=files,session=record(session_path),session_closed_utc=session['closed_utc'],
                captures=[captures[name][3] for name in captures],previous_CA_prestate=record(previous),
                source_path=dict(CA_exit_jump=0xcae2,CB_entry=0x900,CB_tail_original=[0x8c00,0x9000],
                                 CB_tail_restored=[0x800,0xc00],CB_loader_subroutine=0x800,CB_main_call=0x880,
                                 loader_backup_pc=0x85e,next_execution_entry=0xc000,next_execution_file='DB'),
                transfers=transfers,checks=checks,full_CB_tail_observation=cb_observation,
                staging_copy=dict(check=staged,first=0x2000,end_exclusive=0x4000,
                    file_defined=[dict(prefix='EA',first=0x2000,end_exclusive=0x2ee9),dict(prefix='EB',first=0x3000,end_exclusive=0x3f88)],
                    stale_native_prestate_ranges=[[0x2ee9,0x2f00],[0x3f88,0x4000]],stale_bytes=143,
                    copied_native_loader_range=[0x2f00,0x3000],copied_loader_bytes=256,
                    non_EA_EB_file_bytes=399,
                    scope='The399 bytes outside EA/EB bodies are separately143 preserved pre-RAM bytes plus256 explicitly copied loader bytes. None is synthesized.'),
                pass_=all(check['exact'] for check in checks),
                limitations=['DA is a data preload; the next observed execution entry belongs to DB.',
                             'EA/EB headers are transfer addresses. Their future code/part roles are not inferred from those headers.',
                             'This binds bytes and reachable control flow, not hardware timing, frame composition or a named renderer.',
                             'The complete CB-tail differences remain observational; three exact source-written color bytes are not treated as pristine source.'])
    report['pass']=report.pop('pass_'); target=output/'da-transition-proof.json'; target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(target.relative_to(ROOT)),sha256=sha(target.read_bytes()),pass_=report['pass'],
                          transfers=len(transfers),exact_checks=len(checks),non_EA_EB_file_bytes=399),indent=2))
    assert report['pass'],'Transition mismatch retained in receipt.'


if __name__=='__main__': main()
