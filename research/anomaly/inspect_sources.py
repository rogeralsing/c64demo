#!/usr/bin/env python3
"""Check pinned Arcade Scroller bytes and enumerate declared source arithmetic.

No assembler, downloaded script, CPU, emulator, native timing or Sparkle
decompression is run. Enumeration inputs and comparison baselines are explicit.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'build/research/anomaly'
SURVEY=ROOT/'build/research/frontier-2026'
COMMIT='4361d011f56f27014c0b6cd542718ca0b23666d8'


def sha(data):return hashlib.sha256(data).hexdigest()
def record(path):
    data=path.read_bytes();return dict(path=str(path.relative_to(ROOT)),bytes=len(data),sha256=sha(data))
def const(text,name):
    value=re.search(r'\.const\s+'+name+r'\s*=\s*(\$[0-9a-f]+|[0-9]+)',text,re.I)[1]
    return int(value[1:],16) if value.startswith('$') else int(value)


def schedule(rates,phases):
    accum=[0]*len(rates);fine=list(phases);rows=[];counts=[0]*len(rates)
    for update in range(1,2049):
        carry_lines=[];coarse=[]
        for line,rate in enumerate(rates):
            total=accum[line]+rate;accum[line]=total&255
            carry=total>=256
            if carry:
                carry_lines.append(line);fine[line]-=1
                if fine[line]<0:fine[line]=7;coarse.append(line);counts[line]+=1
            # Independent cumulative formulas, including initial phase.
            carries=update*rate//256
            assert accum[line]==update*rate%256 and fine[line]==(phases[line]-carries)%8
            assert counts[line]==(carries+7-phases[line])//8
        rows.append(dict(update=update,carry_lines=carry_lines,coarse_lines=coarse,
                         coarse_count=len(coarse),bitmap_read_bytes=40*len(coarse),bitmap_write_bytes=40*len(coarse)))
    assert accum==[0]*len(rates) and fine==phases and counts==rates
    histogram=Counter(row['coarse_count'] for row in rows)
    return dict(calls=2048,per_line_coarse_counts=counts,total_coarse_events=sum(counts),
                mean_coarse_lines=sum(counts)/2048,maximum_coarse_lines=max(histogram),
                minimum_coarse_lines=min(histogram),coarse_count_histogram=dict(sorted(histogram.items())),calls_detail=rows)


def main():
    BASE.mkdir(parents=True,exist_ok=True)
    tree_path=SURVEY/'anomaly-pinned-tree.json';tree=json.loads(tree_path.read_text());assert not tree['truncated']
    entries={row['path']:row for row in tree['tree'] if row['type']=='blob'}
    survey_path=SURVEY/'sources.json';survey=json.loads(survey_path.read_text());assert survey['pass']
    selected=[row for row in survey['source_bindings']['selected_sources'] if row['project']=='anomaly']
    additional_path=BASE/'additional-acquisitions.json';additional=json.loads(additional_path.read_text())
    assert additional['commit']==COMMIT and additional['tree_sha1']==tree['sha']
    sources={};provenance=[]
    for row in selected+additional['files']:
        path=ROOT/row.get('local_path',row.get('path'));data=path.read_bytes();source_path=row['source_path']
        blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        assert sha(data)==row['sha256'] and blob==entries[source_path]['sha'] and len(data)==entries[source_path]['size']
        sources[source_path]=data;provenance.append(dict(source_path=source_path,git_blob_sha1=blob,**record(path)))
    def source(name):return sources['Parts/ArcadeScroller/'+name].decode()
    main_source=source('ArcadeScroller.asm');settings=source('scene_settings.asm');scroll=source('scroll_logic.asm')
    upper=source('upper_scroll_logic.asm');macros=source('macros.asm');double=source('double_buffer_functions.asm')
    functions=source('functions.asm');raster=source('raster_irq.asm');variables=source('variables.asm')
    lines=const(settings,'bitmap_lines');factor=const(settings,'PERSPECTIVE_FACTOR');rows=const(settings,'UPPER_PART_ROWS')
    assert (lines,factor,rows,const(settings,'top_d016_delay_amt'))==(96,102,13,15)
    assert '.byte p+x' in main_source and '.var f = frame_line_offsets_list.get(x)' in main_source
    assert 'adc frame_line_offsets_table+x' in scroll and 'dcp d016_zp_table+x' in scroll
    assert 'lda #$bf' in scroll and 'ldx #$c7' in scroll and 'stx d016_zp_table+x' in scroll
    assert 'addr_list.size()-1' in macros and 'lda src,y' in macros and 'sta dst,y' in macros
    assert re.search(r'cmp #\$24\s*//[^\n]*\n\s*bmi',upper)
    rates=list(range(factor,factor+lines));phases=[(i+offset)%8 for offset in (6,0,2,0) for i in range(24)]
    actual=schedule(rates,phases)
    aligned0=schedule(rates,[0]*96);aligned7=schedule(rates,[7]*96)
    detail=BASE/'floor-schedule-2048.json';detail.write_text(json.dumps(actual['calls_detail'],indent=2)+'\n')
    def summary(result):return {key:value for key,value in result.items() if key!='calls_detail'}
    gates=[]
    for threshold in (0x24,0x40,0x60):
        accepted=[value for value in range(256) if (value-threshold)&0x80]
        rejected=[value for value in range(256) if value not in accepted]
        gates.append(dict(threshold=threshold,accepted_low_bytes=accepted,rejected_low_bytes=rejected,
                          predicate='bit7((D012_low-threshold)&255)==1 (CMP then BMI); D011 bit7 not read'))
    assert 'ldx #$40' in functions and 'ldx #$60' in functions and 'stx upper_scroll_threshold+1' in functions
    assert 'eor #$ff' in double and 'jsr handle_double_buffering' in raster
    assert 'lda #1' in raster and 'sta upper_scroll_status' in raster
    state_calls=[dict(call=i+1,state='copy_pixels',row=i,read_bytes=320,write_bytes=320) for i in range(rows)]
    state_calls += [dict(call=rows+i+1,state='copy_colours',row=i,read_bytes=40,write_bytes=40) for i in range(rows)]
    state_calls += [dict(call=27,state='copy_new_column',read_bytes=13,write_bytes=13),
                    dict(call=28,state='copy_new_pixels',read_bytes=104,write_bytes=104,next_status=0)]
    assert sum(row['write_bytes'] for row in state_calls)==4797
    sym=sources['Build/6502/ArcadeScroller/ArcadeScroller.sym'].decode()
    symbols={name:int(value,16) for name,value in re.findall(r'\.label (\w+)=\$([0-9a-f]+)',sym)}
    binaries={name:sources[name] for name in ('Parts/ArcadeScroller/ArcadeScroller.prg','Link/ArcadeScroller/ArcadeScroller.prg')}
    binary_checks=[]
    phase_bytes=bytes(0xc0|value for value in phases)
    for name,data in binaries.items():
        first=int.from_bytes(data[:2],'little');assert first==0x2800 and len(data)==49926
        at=lambda address,size:data[address-first+2:address-first+2+size]
        gate=at(symbols['scroll_upper_part'],8)
        assert gate==bytes.fromhex('ad 12 d0 c9 24 30 01 60')
        assert at(symbols['d016_table'],96)==phase_bytes
        binary_checks.append(dict(name=name,sha256=sha(data),bytes=len(data),header=first,
            offset_table=list(at(0x2800,96)),matches_current_source_rates=at(0x2800,96)==bytes(rates),
            matches_signed_gate=True,matches_initial_fine_phases=True,
            first_line_update_hex=at(0x2900,39).hex(),symbols_scope='Locations from bundled Build symbol file; selected literal guards checked, not source rebuilt.'))
    assert binary_checks[0]['offset_table']==list(range(94,190)) and binary_checks[1]['matches_current_source_rates']
    different=[i for i,(a,b) in enumerate(zip(*binaries.values())) if a!=b]
    assert len(different)==6992
    zip_path=SURVEY/'anomaly-author.zip';assert sha(zip_path.read_bytes())=='cc33d92f4b3ac732c340ecd65ce7389e6cd4d1e5a360d3cfc69e92210d882eb3'
    disks=[]
    with zipfile.ZipFile(zip_path) as archive:
        for side in (1,2):
            name=f'WeAreTheAnomaly-Side{side}.d64';original=archive.read(name);repo=sources['Release/'+name]
            assert original==repo and len(original)==174848
            disks.append(dict(member=name,bytes=len(original),sha256=sha(original),repository_Release_byte_identical=True))
    production=sources['Main/Sparkle/WeAreTheAnomalyA.sls'].decode()
    assert '..\\..\\Link\\ArcadeScroller\\ArcadeScroller.prg\t2800\t02\t972f' in production
    assert '..\\..\\Link\\ArcadeScroller\\ArcadeScroller.prg\te000\tb802' in production
    report=dict(script=record(Path(__file__)),commit=COMMIT,tree=record(tree_path),survey_receipt=record(survey_path),
        additional_acquisitions=record(additional_path),sources=provenance,original_zip=record(zip_path),original_disks=disks,
        arithmetic_inputs=dict(lines=96,rate_bytes=rates,initial_accumulators=[0]*96,initial_fine_phases=phases,
            perspective_factor=102,ignored_imported_list='frame_line_offsets_list values are bound to f but f is not emitted; p+x is emitted.',
            fine_register_high_bits=0xc0,coarse_trigger='DCP decrements C0 to BF; CMP BF sets Z; STX resets to C7.',
            pointer_initial=0x7800,pointer_line_stride=160,pointer_increment_per_coarse=1),
        floor_schedule=dict(actual=summary(actual),aligned_all_zero=summary(aligned0),aligned_all_seven=summary(aligned7),
            detail=record(detail),scope='Complete2048-call accumulator/fine-state period. Calls are abstract source updates, not measured frames.'),
        floor_copy=dict(shift_bytes_per_line=39,insert_bytes_per_line=1,pixel_shift=8,per_event_reads=40,per_event_writes=40,
            functions=12,bytes_per_function=235,total_function_bytes=2820,source_address=0xe000,relocation_address=0xf040,
            relocation_copy_bytes=13*256,bytes_beyond_function_end=508),
        upper_gate=gates,upper_state_machine=dict(eligible_calls=28,jobs=state_calls,read_bytes=4797,write_bytes=4797,
            publication_interval_source_calls=8*15,publication_checks_completion=False,
            transitions=['13 pixel rows→13 color rows→new color column→new pixel column→status0/copy_pixels'],
            destination_reset='At fine wrap, XOR FF publishes alternate bank, resets row pointers and asserts status1.',
            limitation='28 eligible calls must finish before unconditional120-IRQ publication; gate outcome/timing is not modeled.'),
        binary_correspondence=dict(binaries=binary_checks,different_byte_offsets=different,
            production_manifest='Main/Sparkle/WeAreTheAnomalyA.sls',manifest_target='Link/ArcadeScroller/ArcadeScroller.prg',
            sections=[dict(load=0x2800,file_offset=2,length=0x972f),dict(load=0xe000,file_offset=0xb802,length=2820)],
            whole_disk_identity=True,source_rebuilt=False,original_Sparkle_payload_decoded=False,
            scope='Repository release disks equal author disks; manifest names Link binary; selected byte guards agree. No source-build equality or decompressed-original-part equality.'),
        limitations=['No assembler, source/host script, CPU, emulator or Sparkle decompressor run.',
            'Author50fps and drive-stress statements remain attributed claims, not measurements.',
            'This is source arithmetic/workload enumeration with declared initial state, not raster timing or coherent-field verification.'],pass_=True)
    report['pass']=report.pop('pass_');target=BASE/'arcade-source-proof.json';target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(target.relative_to(ROOT)),sha256=sha(target.read_bytes()),script_sha256=report['script']['sha256'],
        pass_=report['pass'],staggered_maximum=actual['maximum_coarse_lines'],aligned0_maximum=aligned0['maximum_coarse_lines'],
        aligned7_maximum=aligned7['maximum_coarse_lines'],total_coarse_events=actual['total_coarse_events'],upper_eligible_calls=28),indent=2))


if __name__=='__main__':main()
