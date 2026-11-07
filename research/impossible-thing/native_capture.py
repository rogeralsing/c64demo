#!/usr/bin/env python3
"""Passively compare owner-captured original Impossible Thing RAM/VSFs."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'build/research/impossible-thing'
spec=importlib.util.spec_from_file_location('impossible_nine_reader',ROOT/'research/nine/native_capture.py')
reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)


def sha(data):return hashlib.sha256(data).hexdigest()
def record(path):
    data=Path(path).read_bytes()
    return dict(path=str(Path(path).resolve().relative_to(ROOT)),bytes=len(data),sha256=sha(data))
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,default=BASE/'native-01')
    parser.add_argument('--output',type=Path,default=BASE/'native-analysis')
    args=parser.parse_args();capture=args.capture.resolve();output=args.output.resolve()
    session_path=capture/'session.json';session=json.loads(session_path.read_text())
    assert session.get('closed_utc'),'Final evidence requires the capture owner to close the session.'
    transcript=capture/'monitor.log';events=reader.contexts(transcript.read_text(errors='replace'))
    by_file={}
    for event in events:by_file.setdefault(event['filename'],[]).append(event)
    captures=[];images={};registers={}
    for path in sorted(capture.glob('ram-*.bin')):
        name=path.stem[4:];snapshot=capture/(name+'.vsf');assert snapshot.exists()
        raw=path.read_bytes();assert len(raw)==65536 and raw==reader.physical_ram(snapshot)
        candidates=[event for event in by_file.get(path.name,[]) if event['command']=='bsave' and event['bank']=='ram']
        assert len(candidates)==1,(path,candidates)
        event=candidates[0];assert event['first']==0 and event['end_inclusive']==65535
        reg=event['registers'];payload=reader.module_payload(snapshot,'MAINCPU')
        native=dict(clock=int.from_bytes(payload[:8],'little'),a=payload[8],x=payload[9],y=payload[10],sp=payload[11],
                    pc=int.from_bytes(payload[12:14],'little'),flags=payload[14])
        assert all(native[key]==reg[key] for key in native),(name,native,reg)
        snap_events=[event for event in by_file.get(snapshot.name,[]) if event['command']=='dump']
        assert len(snap_events)==1 and snap_events[0]['registers']==reg
        state=reader.read_snapshot(snapshot)
        images[name]=raw;registers[name]=reg
        captures.append(dict(name=name,ram=record(path),snapshot=record(snapshot),registers=reg,
            physical_RAM_exact=True,MAINCPU_exact=True,
            snapshot_raster=[state['vicii']['raster_line'],state['vicii']['raster_cycle']],
            D018=state['vicii']['regs'][0x18],D011=state['vicii']['regs'][0x11],D016=state['vicii']['regs'][0x16]))
    comparisons=[]
    def compare(name,expected,first,end,label):
        assert name in images,name
        result=reader.comparison(images[name],expected,first,end,label)
        comparisons.append(dict(capture=name,**result));assert result['exact'],(name,label,result['differences'])
    prg=(BASE/'impossible-thing.prg').read_bytes();source=bytearray(65536)
    source[0x801:0x1607]=prg[2:]
    assert registers['sys-entry']['pc']==0x801
    compare('sys-entry',source,0x801,0x1607,'Entire original PRG body before the first instruction')
    assert registers['stub-entry']['pc']==0x340
    prefix=bytearray(65536);prefix[0x340:0x3b4]=source[0x1593:0x1607]
    compare('stub-entry',prefix,0x340,0x3b4,'116 file-established bytes in the first wrapper copy')
    full_copy=bytearray(65536);full_copy[0x340:0x440]=images['sys-entry'][0x1593:0x1693]
    compare('stub-entry',full_copy,0x340,0x440,'All256 bytes from actual native prestate, including140 file-unknown bytes')
    assert registers['decoder-entry']['pc']==0x100
    expected=bytearray(65536);expected[0xfa:0x1fa]=source[0x14d9:0x15d9]
    compare('decoder-entry',expected,0xfa,0x1fa,'Entire file-established decoder copy before execution')
    assert images['sys-entry'][0x12]==images['decoder-entry'][0x12]==0
    boot_path=BASE/'binary/boot-proof.json';boot=json.loads(boot_path.read_text())
    decoded=(BASE/'binary/conditional-unpacked.ram').read_bytes()
    first,end=boot['conditional_decoder']['output_first'],boot['conditional_decoder']['output_end_exclusive']
    assert sha(decoded[first:end])==boot['conditional_decoder']['output_sha256']
    assert registers['main-entry']['pc']==0x2000
    compare('main-entry',decoded,first,end,'Every decoded byte: native original program versus explicitly conditional reconstruction')
    increments=boot['conditional_decoder']['external_counter']['increments']
    counter=dict(initial=images['decoder-entry'][0x400],increments=increments,actual=images['main-entry'][0x400])
    counter['expected']=(counter['initial']+increments)&255;counter['exact']=counter['actual']==counter['expected'];assert counter['exact']
    renderer_path=BASE/'renderer/renderer-map.json';renderer=json.loads(renderer_path.read_text())
    assert renderer['pass'],'Independent renderer producer receipt did not pass'
    prepared_record=renderer['prepared_image'];prepared_path=ROOT/prepared_record['path']
    assert prepared_path.resolve()==(BASE/'renderer/prepared-conditional.ram').resolve()
    prepared=prepared_path.read_bytes()
    assert len(prepared)==prepared_record['bytes'] and sha(prepared)==prepared_record['sha256'],prepared_record
    initialized=[]
    for item in captures:
        name=item['name']
        if item['registers']['pc']==0x28da:
            compare(name,prepared,0x4000,0xb200,'All29184 generated glyph-writer bytes before the first image')
            compare(name,prepared,0x3800,0x4000,'All2048 packed texture-table bytes')
            compare(name,prepared,0x400,0x700,'All768 isolated-setup address/sine table bytes')
            duplicate=bytearray(65536);duplicate[0x700:0x800]=prepared[0x600:0x700]
            compare(name,duplicate,0x700,0x800,'Literal sine-page duplication inside the unexecuted Color RAM loop')
            compare(name,prepared,0x2606,0x26f6,'All40 original generated screen cells before runtime operand patching')
            initialized.append(name)
    flips=[]
    for item in captures:
        if item['registers']['pc']==0x227f:
            assert item['D018']==item['registers']['a'] and item['D018'] in (0xc8,0xda)
            flips.append(dict(name=item['name'],clock=item['registers']['clock'],D018=item['D018'],
                              raster=[item['registers']['raster_line'],item['registers']['raster_cycle']]))
    flips.sort(key=lambda item:item['clock'])
    intervals=[];lines=transcript.read_text(errors='replace').splitlines()
    for first,last in zip(flips,flips[1:]):
        before=by_file['ram-'+first['name']+'.bin'][0]['transcript_line']
        after=by_file['ram-'+last['name']+'.bin'][0]['transcript_line']
        between=[line.strip() for line in lines[before:after]]
        assert between.count('x')==1
        assert sum('Stop on  exec 227f' in line for line in between)==1
        assert not any(line.startswith(('ignore ','step ','undump ','load ','g ')) for line in between)
        intervals.append(dict(first=first['name'],last=last['name'],clocks=last['clock']-first['clock'],
            transcript_lines=[before,after],one_resume_one_next_break=True))
    pngs=[]
    for path in sorted(capture.glob('*.png')):
        png_events=[event for event in by_file.get(path.name,[]) if event['command'] in ('screenshot','scrsh')]
        assert len(png_events)==1
        pngs.append(dict(**record(path),registers=png_events[0]['registers'],scope='Original-output observation; no independent pixel oracle.'))
    report=dict(script=record(Path(__file__)),reader=record(ROOT/'research/nine/native_capture.py'),
        snapshot_reader=record(ROOT/'research/quondam/snapshot_state.py'),session=record(session_path),
        session_closed_utc=session['closed_utc'],transcript=record(transcript),
        boot_receipt=record(boot_path),renderer_receipt=record(renderer_path),captures=captures,
        full_RAM_pair_bytes=65536*len(captures),comparisons=comparisons,
        native_ZP12_at_SYS_and_decoder=0,actual_native_counter_transition=counter,
        native_initialization_captures=initialized,image_selection_stops=flips,
        image_selection_capture_intervals=intervals,
        screenshots=pngs,
        scope='Passive exact byte/capture evidence only. The selected native run establishes decoder input ZP12=0 and complete output identity; it does not erase conditional/file-only boundaries. Consecutive image-selection intervals are not coherent-frame FPS. No whole-machine, pixel, analog or general frame-rate proof.',pass_=True)
    report['pass']=report.pop('pass_');output.mkdir(parents=True,exist_ok=True)
    path=output/'native-evidence.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(path.relative_to(ROOT)),sha256=sha(path.read_bytes()),
                         pairs=len(captures),PNGs=len(pngs),comparisons=len(comparisons)),indent=2))


if __name__=='__main__':main()
