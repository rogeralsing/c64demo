#!/usr/bin/env python3
"""Original Arcade byte guards and conditional RAM arithmetic/copy witnesses.

Native RAM/VSF/transcripts are passive inputs. No CPU, emulator, hardware/ROM
response, pixel renderer or original downloaded program is run here.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'build/research/anomaly'
OUT=BASE/'runtime-analysis'
BINARY_SHA='b8744b0184128330a069a7366c4f843193306074f4a55a03d10f092a6fa8800c'
TRACE=re.compile(
    r'^#(?P<checkpoint>\d+) \(Trace\s+(?P<kind>store|exec)\s+(?P<target>[0-9a-f]{4})\)\s+'
    r'(?P<line>\d+)/\$[0-9a-f]+,\s+(?P<cycle>\d+)/\$[0-9a-f]+\n'
    r'\.C:(?P<pc>[0-9a-f]+)\s+[^\n]*?'
    r'- A:(?P<a>[0-9a-f]+) X:(?P<x>[0-9a-f]+) Y:(?P<y>[0-9a-f]+) '
    r'SP:(?P<sp>[0-9a-f]+) [^\n]*?\s+(?P<clock>\d+)\n',re.M|re.I)


def sha(data):return hashlib.sha256(data).hexdigest()
def record(path):
    data=path.read_bytes();return dict(path=str(path.relative_to(ROOT)),bytes=len(data),sha256=sha(data))
def checked(item):
    path=ROOT/item['path'];data=path.read_bytes();assert len(data)==item['bytes'] and sha(data)==item['sha256'];return data
def word(data,address):return int.from_bytes(data[address:address+2],'little')
def setword(data,address,value):data[address:address+2]=(value&65535).to_bytes(2,'little')
def comparison(actual,expected,first,end,label):
    differences=[dict(address=a,actual=actual[a],expected=expected[a]) for a in range(first,end) if actual[a]!=expected[a]]
    return dict(label=label,first=first,end_exclusive=end,bytes=end-first,exact=not differences,
                actual_sha256=sha(actual[first:end]),expected_sha256=sha(expected[first:end]),differences=differences)


def original():
    path=BASE/'binary-analysis/side1-binary-proof.json';assert sha(path.read_bytes())==BINARY_SHA
    proof=json.loads(path.read_text());assert proof['pass']
    for index in (35,36):
        assert proof['bundles'][index]['bundle']==index
        checked(proof['bundles'][index]['known_mask'])
    driver=checked(proof['bundles'][35]['RAM']);memory=checked(proof['bundles'][36]['RAM'])
    assert driver[0x8bb:0x8be]==bytes.fromhex('20 00 3b')
    assert driver[0x8ae:0x8b1]==bytes.fromhex('20 09 08')
    assert memory[0x3b00:0x3b18]==bytes.fromhex('a2 00 a9 01 95 e8 bd 87 3b 95 f0 bd e9 3a 95 e0 e8 e0 06 d0 ed a9 0f 85')
    assert memory[0x3d83:0x3d8c]==bytes.fromhex('20 00 29 20 e3 36 2c c2 66')
    assert memory[0x36e3:0x36f3]==bytes.fromhex('ad 12 d0 c9 24 30 01 60 a5 07 d0 01 60 4c f3 36')
    assert memory[0xb84b:0xb864]==bytes.fromhex('20 d4 67 20 00 67 a9 01 85 07 a9 c7 8d 16 d0 a5 d1 8d 18 d0 a5 d2 8d 02 dd')
    return memory,driver,proof,record(path)


def native(directory,name):
    sys.path.insert(0,str(ROOT/'research/quondam'))
    from snapshot_state import read_snapshot,module_payload
    ram_path=directory/('ram-'+name+'.bin');vsf=directory/(name+'.vsf');ram=ram_path.read_bytes()
    state=read_snapshot(vsf);mem=module_payload(vsf,'C64MEM');cpu=module_payload(vsf,'MAINCPU')
    assert state['modules']['C64MEM']['version']==[0,1] and state['modules']['MAINCPU']['version']==[1,4]
    assert len(ram)==65536 and ram==mem[4:65540]
    registers=dict(clock=int.from_bytes(cpu[:8],'little'),a=cpu[8],x=cpu[9],y=cpu[10],sp=cpu[11],
                   pc=int.from_bytes(cpu[12:14],'little'),flags=cpu[14])
    return bytearray(ram),dict(name=name,ram=record(ram_path),snapshot=record(vsf),registers=registers,
        port_latch=mem[0],port_ddr=mem[1],raster_line=state['vicii']['raster_line'],raster_cycle=state['vicii']['raster_cycle'],
        VIC_regs=state['vicii']['regs'])


def RAM_visible(metadata):
    pins=(metadata['port_latch']&metadata['port_ddr'])|(7&~metadata['port_ddr'])
    assert pins&2==0,'Modeled upper RAM must be visible, not mapped KERNAL/BASIC.'


def floor_layout(memory):
    assert memory[0x2900:0x2902]==bytes.fromhex('a2 c7')
    rows=[]
    for line in range(96):
        pc=0x2902+37*line;block=line//8;fine=line%8;target=0x5040+320*block+fine
        assert memory[pc:pc+8]==bytes([0x18,0xa5,0x68+line,0x6d,line,0x28,0x85,0x68+line])
        assert memory[pc+8:pc+23]==bytes([0x90,0x1b,0xa9,0xbf,0xc7,8+line,0xd0,0x15,0x86,8+line,0xa0,fine,0x20])+((0xf040+235*block)&65535).to_bytes(2,'little')
        assert memory[pc+23]==0xad and memory[pc+26]==0x8d
        assert word(memory,pc+27)==target+312
        assert memory[pc+29:pc+37]==bytes([0xee])+ (pc+24).to_bytes(2,'little')+bytes([0xd0,3,0xee])+(pc+25).to_bytes(2,'little')
        rows.append(dict(line=line,pc=pc,pointer_operand=pc+24,bitmap_first=target,bitmap_insert=target+312,
                         helper=0xf040+235*block))
    assert memory[0x36e2]==0x60 and list(memory[0x2800:0x2860])==list(range(102,198))
    return rows


def D016_schedule(source):
    """Expand original Y-controlled loops into96 indexed store sites."""
    sites=[pc+2 for pc in range(0xb46b,0xb828) if source[pc:pc+5]==bytes.fromhex('b5 08 8d 16 d0')]
    assert len(sites)==40
    assert source[0xb542:0xb54a]==bytes.fromhex('c8 c0 03 f0 03 4c 6b b4')
    assert source[0xb5fe:0xb606]==bytes.fromhex('c8 c0 05 f0 03 4c 4a b5')
    assert source[0xb820:0xb828]==bytes.fromhex('c8 c0 0a f0 03 4c 71 b7')
    result=sites[:8]*3+sites[8:16]*2+sites[16:24]+sites[24:32]+sites[32:40]*5
    assert len(result)==96
    return [dict(line=index,pc=pc,table_address=8+index) for index,pc in enumerate(result)]


def floor_model(before,source):
    """Independent line/cell indexing; no instruction or IRQ simulation."""
    memory=bytearray(before);rows=floor_layout(before);events=[];carries=[];coarse=[]
    assert memory[0xf040:0xfb44]==source[0xe000:0xeb04]
    for row in rows:
        line=row['line'];rate=source[0x2800+line];accumulator=before[0x68+line];fine=before[8+line]
        assert 0xc0<=fine<=0xc7
        total=accumulator+rate;memory[0x68+line]=total&255
        if total<256:continue
        carries.append(line);fine=(fine-1)&255;memory[8+line]=fine
        if fine!=0xbf:continue
        coarse.append(line);memory[8+line]=0xc7
        pointer=word(before,row['pointer_operand']);initial=0x7800+160*line
        assert initial<=pointer<initial+160
        for column in range(39):
            target=row['bitmap_first']+8*column;value=memory[target+8]
            memory[target]=value;events.append(dict(line=line,address=target,value=value,source=target+8))
        value=memory[pointer];memory[row['bitmap_insert']]=value
        events.append(dict(line=line,address=row['bitmap_insert'],value=value,source=pointer))
        setword(memory,row['pointer_operand'],pointer+1)
    assert len(events)==40*len(coarse)
    return memory,dict(carry_lines=carries,coarse_lines=coarse,bitmap_stores=len(events),stores=events,
        insertion_pointers=[dict(line=r['line'],operand=r['pointer_operand'],before=word(before,r['pointer_operand']),
                                 after=word(memory,r['pointer_operand'])) for r in rows])


def upper_model(before,sampled_low):
    """One original upper job from actual pre-CMP A and mutable RAM state."""
    memory=bytearray(before);threshold=before[0x36e7];accepted=bool((sampled_low-threshold)&0x80)
    events=[];target=word(before,0x36f1);job='gate-rejected' if not accepted else 'inactive'
    def copy(first,destination,size):
        assert not 0xd000<=destination<0xe000 and not 0xd000<=first<0xe000
        for offset in range(size):
            source=(first+offset)&65535
            assert source not in (0,1) and not 0xd000<=source<0xe000
            value=memory[source];address=(destination+offset)&65535
            assert address not in (0,1) and not 0xd000<=address<0xe000
            memory[address]=value;events.append(dict(address=address,value=value,source=(first+offset)&65535))
    if accepted and before[7]:
        if target==0x36f3:
            job='pixel-row';copy(word(memory,0xcc),word(memory,0xce),320)
            memory[0xcd]=(memory[0xcd]+1)&255;memory[0xcf]=(memory[0xcf]+1)&255
            memory[0xd4]=(memory[0xd4]+1)&255;row=memory[0xd4]
            for instruction,destination in ((0x3898,0xcc),(0x389d,0xcd),(0x38a2,0xce),(0x38a7,0xcf)):
                assert memory[instruction]==0xbd
                memory[destination]=memory[(word(memory,instruction+1)+row)&65535]
            if row==13:setword(memory,0x36f1,0x38bb)
        elif target==0x38bb:
            job='color-row';copy(word(memory,0xd5),word(memory,0xd7),40)
            total=memory[0xd5]+40;memory[0xd5]=total&255
            if total>=256:memory[0xd6]=(memory[0xd6]+1)&255;memory[0xd8]=(memory[0xd8]+1)&255
            memory[0xd7]=(memory[0xd7]+40)&255;memory[0x399c]=(memory[0x399c]+1)&255
            if memory[0x399c]==13:memory[0x399c]=0;setword(memory,0x36f1,0x39b1)
        elif target==0x39b1:
            job='new-color-column';routine=word(memory,0x39b2);assert routine in (0x6b82,0x6bd2)
            screen=0x6000 if routine==0x6b82 else 0xcc00;pointer=word(memory,0xdb)
            for row in range(13):copy(pointer+row,screen+40*row+39,1)
            setword(memory,0xdb,pointer+13);setword(memory,0x36f1,0x39ca)
        elif target==0x39ca:
            job='new-pixel-column';routine=word(memory,0x39cb);assert routine in (0x6c22,0x6f70)
            bitmap=0x4000 if routine==0x6c22 else 0xe000;pointer=word(memory,0xdd)
            for row in range(13):copy(pointer+8*row,bitmap+320*row+312,8)
            setword(memory,0xdd,pointer+104);memory[7]=0;setword(memory,0x36f1,0x36f3)
        else:raise AssertionError(('Unknown upper-job target',target))
    return memory,dict(sampled_D012_low=sampled_low,threshold=threshold,signed_gate_accepted=accepted,
        status_before=before[7],status_after=memory[7],dispatch_before=target,dispatch_after=word(memory,0x36f1),
        job=job,data_stores=len(events),stores=events)


def publication_model(before):
    memory=bytearray(before);old=memory[0xd0];assert old in (0,255);memory[0xd0]^=255
    memory[0xd3]=memory[0xd4]=0
    if memory[0xd0]:
        memory[0xd1]=0x38;memory[0xd2]=0x3f
        tables=(0x7568,0x7575,0x7582,0x758f,0x759c,0x75a9,0x75b6,0x75c3)
        color,pixels=0x6b82,0x6c22
    else:
        memory[0xd1]=0x80;memory[0xd2]=0x3d
        tables=(0x7500,0x750d,0x751a,0x7527,0x7534,0x7541,0x754e,0x755b)
        color,pixels=0x6bd2,0x6f70
    for pointer,table in zip((0xcc,0xcd,0xce,0xcf,0xd5,0xd6,0xd7,0xd8),tables):memory[pointer]=memory[table]
    for instruction,table in zip((0x3898,0x389d,0x38a2,0x38a7),tables[:4]):setword(memory,instruction+1,table)
    setword(memory,0x39b2,color);setword(memory,0x39cb,pixels);memory[7]=1
    return memory,dict(status_before=before[7],status_after=1,selection_before=old,selection_after=memory[0xd0],
        D018=memory[0xd1],DD02=memory[0xd2],previous_copy_completed=before[7]==0,
        scope='RAM state/pointer publication oracle; port stores and VIC output are separate native observations.')


def traces(text):
    rows=[]
    for match in TRACE.finditer(text):
        row=match.groupdict()
        for key in ('checkpoint','line','cycle','clock'):row[key]=int(row[key])
        for key in ('target','pc','a','x','y','sp'):row[key]=int(row[key],16)
        rows.append(row)
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--capture',type=Path,default=BASE/'native-03')
    args=parser.parse_args();source,driver,binary,binary_record=original();OUT.mkdir(parents=True,exist_ok=True)
    session_path=args.capture/'session.json';session=json.loads(session_path.read_text())
    assert session.get('closed_utc'),'Final runtime proof requires owner-closed capture session.'
    names=('restored-humanmade','arcade-load-call','arcade-load-return','arcade-entry','arcade-ready',
           'floor-a-pre','floor-a-post','floor-b-pre','floor-b-post','upper-gate-rejected','upper-rejected-post')
    captures={name:native(args.capture,name) for name in names};checks=[]
    expected_pcs=(0x2d00,0x8ae,0x8b1,0x3b00,0x3b88,0x3d83,0x3d86,0x3d83,0x3d86,0x36e6,0x3d89)
    assert [captures[name][1]['registers']['pc'] for name in names]==list(expected_pcs)
    parent,parent_record=native(BASE/'native-02','humanmade-entry')
    checks.append(comparison(captures['restored-humanmade'][0],parent,0,65536,'Full RAM identity versus the approved closed native02 HumanMade source'))
    restore_cpu=[dict(register=key,expected=parent_record['registers'][key],actual=captures['restored-humanmade'][1]['registers'][key],
                      exact=parent_record['registers'][key]==captures['restored-humanmade'][1]['registers'][key]) for key in parent_record['registers']]
    expected_driver=bytearray(driver);expected_driver[0x899]=0xb0;expected_driver[0x89c]=0xc8
    call=captures['arcade-load-call'][0]
    checks.append(comparison(call,expected_driver,0x88f,0x8cc,'All61 incoming-driver bytes after its original8-page-copy operand increments'))
    driver_differences=[dict(address=a,original=driver[a],native=call[a]) for a in range(0x88f,0x8cc) if driver[a]!=call[a]]
    assert [row['address'] for row in driver_differences]==[0x899,0x89c]
    for name in ('arcade-load-return','arcade-entry'):
        for first,end in ((0x2800,0xbf2f),(0xe000,0xeb04)):
            checks.append(comparison(captures[name][0],source,first,end,'Every original Arcade payload byte at '+name))
    assert captures['arcade-load-return'][0][0x2ff]==(call[0x2ff]+1)&255
    entry=captures['arcade-entry'][0];ready=captures['arcade-ready'][0]
    expected=bytearray(ready);expected[0xf040:0xfd40]=entry[0xe000:0xed00]
    checks.append(comparison(ready,expected,0xf040,0xfd40,'All3328 helper-relocation bytes conditional on actual entry RAM, including508 beyond original helper payload'))
    expected[0xf040:0xfb44]=source[0xe000:0xeb04]
    checks.append(comparison(ready,expected,0xf040,0xfb44,'All2820 original helper-code bytes at relocated execution addresses'))
    checks.append(comparison(ready,source,0x2900,0x36e3,'All3555 unmodified floor-update code/pointer bytes before first update'))
    expected[8:0x68]=source[0x72be:0x731e];expected[0x68:0xc8]=bytes(96)
    checks.append(comparison(ready,expected,8,0xc8,'All96 initial fine-scroll phases and96 zero accumulators'))
    expected[0xe000:0xe100]=entry[0x4000:0x4100]
    checks.append(comparison(ready,expected,0xe000,0xe100,'Only the literal256-byte initial upper-bitmap duplication is asserted'))
    assert (ready[7],ready[0xd0],ready[0xda],word(ready,0xdb),word(ready,0xdd),word(ready,0x36f1))==(1,0,15,0x6b00,0xb900,0x36f3)
    intervals=[]
    for label in ('a','b'):
        before,pre_record=captures['floor-'+label+'-pre'];after,post_record=captures['floor-'+label+'-post']
        RAM_visible(pre_record);model,result=floor_model(before,source)
        interval_checks=[comparison(after,model,first,end,description) for first,end,description in (
            (8,0x68,'All96 fine-scroll register bytes'),(0x68,0xc8,'All96 fractional accumulators'),
            (0x2900,0x36e3,'All floor code and96 insertion-pointer operands'),
            (0x5040,0x5f40,'All3840 floor bitmap bytes'))]
        checks+=interval_checks
        events_path=OUT/('floor-'+label+'-stores.json');events_path.write_text(json.dumps(result['stores'],indent=2)+'\n')
        result.pop('stores')
        result.update(name=label,before=pre_record,after=post_record,checks=interval_checks,
            store_receipt=record(events_path),observed_elapsed_clocks=post_record['registers']['clock']-pre_record['registers']['clock'],
            whole_RAM_observation=comparison(after,model,0,65536,'Unfiltered RAM observation; stack/IRQ/music/other differences remain visible'),
            scope='Independent native-prestate line/cell arithmetic. IRQ nesting and hardware are not simulated; no CPU-register or whole-machine equality claim.')
        intervals.append(result)
    assert intervals[0]['carry_lines']==intervals[0]['coarse_lines']==[]
    assert len(intervals[1]['carry_lines'])==70 and intervals[1]['coarse_lines']==[32,40,54,62,70,72,80,88]
    before,gate_record=captures['upper-gate-rejected'];after,gate_post_record=captures['upper-rejected-post']
    RAM_visible(gate_record);gate_model,gate=upper_model(before,gate_record['registers']['a'])
    assert gate['job']=='gate-rejected' and not gate['signed_gate_accepted'] and gate['data_stores']==0
    gate_check=comparison(after,gate_model,0,65536,'All65536 RAM bytes unchanged across the observed rejected upper gate')
    checks.append(gate_check);gate.pop('stores')
    gate.update(before=gate_record,after=gate_post_record,check=gate_check,
                observed_elapsed_clocks=gate_post_record['registers']['clock']-gate_record['registers']['clock'])
    transcript_path=args.capture/'monitor.log';text=transcript_path.read_text();events=traces(text)
    job_pcs={0x36f3:'pixel-row',0x38bb:'color-row',0x39b1:'new-color-column',0x39ca:'new-pixel-column'}
    first_clock=captures['arcade-ready'][1]['registers']['clock'];last_clock=gate_post_record['registers']['clock']
    jobs=[row for row in events if row['kind']=='exec' and row['pc'] in job_pcs and first_clock<=row['clock']<=last_clock]
    for pc in job_pcs:
        assert re.search(r'^trace\s+exec\s+\$?'+f'{pc:04x}'+r'\s*$',text,re.M|re.I),('Required job tracepoint not installed',pc)
    assert jobs==[],'This bounded checkpoint stops before an accepted upper job; retain and classify unexpected hits.'
    schedule=D016_schedule(source);schedule_path=OUT/'planned-D016-original-schedule.json'
    schedule_path.write_text(json.dumps(schedule,indent=2)+'\n')
    state=dict(pc=gate_post_record['registers']['pc'],clock=last_clock,raster_line=gate_post_record['raster_line'],raster_cycle=gate_post_record['raster_cycle'],
        upper_status=after[7],upper_row=after[0xd4],upper_dispatch=word(after,0x36f1),color_row_counter=after[0x399c],
        fine_delay=after[0xda],upper_fine=after[0xb856],buffer_selection=after[0xd0],source_pixels=word(after,0xcc),destination_pixels=word(after,0xce),
        source_colors=word(after,0xd5),destination_colors=word(after,0xd7),new_column_colors=word(after,0xdb),new_column_pixels=word(after,0xdd))
    not_observed=['An accepted upper gate or any completed upper row/new-column job.',
        'The first28-job update completion and unconditional upper-buffer publication.',
        'The96 per-line D016 STORE events in one B400→B828 interval.',
        'Complete subsequent fields, full image equivalence, display FPS or physical/analog output.']
    report=dict(script=record(Path(__file__)),source_binary_proof=binary_record,
        snapshot_helper=record(ROOT/'research/quondam/snapshot_state.py'),session=record(session_path),session_closed_utc=session['closed_utc'],
        captures=[captures[name][1] for name in names],approved_restore_source=parent_record,restore_CPU_checks=restore_cpu,
        incoming_driver=dict(original_bundle=35,bytes=61,unchanged_bytes=59,source_derived_selfmodifications=driver_differences,
            observed_counter_before=call[0x2ff],observed_counter_after=captures['arcade-load-return'][0][0x2ff],
            counter_limit='Software02FF index is not assumed equal to Sparkle bundle number; initial direct loads bypass increment.'),
        checks=checks,floor_updates=intervals,rejected_upper_gate=gate,
        upper_job_trace=dict(transcript=record(transcript_path),window_first_clock=first_clock,window_last_clock=last_clock,
                            installed_job_entry_PCs=sorted(job_pcs),observed_hits=jobs,observed_job_count=0),
        initialized_helper_copy=dict(bytes=3328,file_defined_bytes=2820,native_prestate_tail_bytes=508,
            source=[0xe000,0xed00],destination=[0xf040,0xfd40],tail_not_zero_padding=True),
        paused_followup_state=state,planned_D016_schedule=dict(artifact=record(schedule_path),stores=96,static_sites=40,
            basis='Original three Y-controlled loops:8sites×3,8×2,8,8,8×5; each STA follows LDA08,X.',native_observed=False),
        unexercised_models=['upper_model accepted-job branches and publication_model are plans only; no native success claim.'],
        not_observed=not_observed,runtime_witness_complete=False,
        status='PROVISIONAL Arcade-runtime investigation; closed bounded checkpoint',
        scope='Original payload/initialization bytes, two conditional floor-update arithmetic witnesses and one rejected upper gate. No CPU/VIC/hardware model or full50Hz demonstration.')
    report['pass']=all(row['exact'] for row in checks+restore_cpu)
    target=OUT/'runtime-proof.json';target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(target.relative_to(ROOT)),sha256=sha(target.read_bytes()),pass_=report['pass'],
        checks=len(checks),capture_pairs=len(names),floor_coarse=[len(row['coarse_lines']) for row in intervals],
        gate_A=gate['sampled_D012_low'],gate_threshold=gate['threshold'],job_hits=0,runtime_witness_complete=False),indent=2))
    assert report['pass'],'Mismatch retained in bounded runtime receipt.'


if __name__=='__main__':main()
