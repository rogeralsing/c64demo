#!/usr/bin/env python3
"""Passive typed Lab attribute mathematics; no CPU interpreter or renderer.

The record transform preserves the original sign-dependent endpoint,
shift/carry and last-cell correction rules. True pre-edge state custody
is required before a complete native acceptance is produced.
"""
import argparse
import hashlib
import json
from pathlib import Path
import traceback

ROOT=Path(__file__).resolve().parents[2]
LAB=ROOT/'build/research/the-lab'
BASE=ROOT/'build/research/lab-polygons-20261109/attribute-analysis'
ORIGINAL20=LAB/'side2-analysis/depacked/20.ram.bin'
ORIGINAL22=LAB/'side2-analysis/depacked/22.ram.bin'
ORIGINAL20_SHA='f866f5a03713f91979dc4ad8421f95b4a9da6b405faea55804112e9993e90ef8'
ORIGINAL22_SHA='e95132427dc660f13e611bcb886636374d4f86e533b22a3dd286dc59896b5229'
CASE_PROOF=ROOT/'build/research/lab-polygons-20261109/native-analysis/accepted-01/ball-native-proof.json'
CASE_SHA='123732a8293916ffc9648b51686eeff314f1d0a9b371756efaab975976d968e5'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def meta(path):
    raw=path.read_bytes()
    return dict(path=str(path.resolve().relative_to(ROOT)),bytes=len(raw),sha256=sha(raw))


def original_sources():
    files={
        ORIGINAL20:ORIGINAL20_SHA, ORIGINAL22:ORIGINAL22_SHA,
        ORIGINAL20.with_name('20.written.bin'):'69666deef45da83279aadf998f467010be230b6adc32f80e3c8e099f2247c95a',
        ORIGINAL22.with_name('22.written.bin'):'5587e7baad4ec3f50c62876eed85e7304fa1b66b176948a28ced28913ad12502',
        ORIGINAL20.with_name('20-2000-902f.prg'):'1a9f16d936f515093ce403d19d63203b87a907904997f033052fd3c830dad9e8',
        ORIGINAL22.with_name('22-8c00-c34b.prg'):'e0eb89a8c11d6b1f1055c84573f4bd4c0a6cb9cbe0194930be1bce8801ec493f',
    }
    for path,pin in files.items():
        assert sha(path.read_bytes())==pin,path
    original20,original22=ORIGINAL20.read_bytes(),ORIGINAL22.read_bytes()
    for memory,index,first,end in ((original20,'20',0x2000,0x9030),
                                   (original22,'22',0x8c00,0xc34c)):
        written=(ORIGINAL20.parent/(index+'.written.bin')).read_bytes()
        expected=bytearray(65536);expected[first:end]=bytes([1])*(end-first)
        assert written==expected
        prg=(ORIGINAL20.parent/(index+('-2000-902f.prg' if index=='20' else '-8c00-c34b.prg'))).read_bytes()
        assert int.from_bytes(prg[:2],'little')==first and prg[2:]==memory[first:end]
    # Every consumed code, mask, crop-table and stream byte belongs to a
    # release-written range. Padded high-memory zeros are not source data.
    roles=[(0x2360,0x23fe,'Sign-specific character-boundary fixed-point setup'),
           (0x23fe,0x247a,'Palette lookup and Color-RAM-shadow event traversal'),
           (0x247a,0x2514,'Screen-nibble merge and event traversal'),
           (0x3f00,0x4000,'Independent nibble-event mask truth table'),
           (0x69d8,0x6f66,'Both screen propagators and their wrappers'),
           (0x876c,0x8994,'Fixed event/crop/code-pointer tables')]
    contract=[dict(first=a,end_exclusive=z,role=role,sha256=sha(original20[a:z]))
              for a,z,role in roles]
    for address,expected in [
        (0x2374,'A537A84A69004A69008537A5350A9044'),
        (0x23b2,'A5350A66356634A53965348539A53865358538'),
        (0x23c8,'A900853BA5384A4A4A853A8A2903F0124903A8'),
        (0x247a,'A647D013A2F0C910D019A53C0A0A0A0A853CA20F4C9D24'),
        (0x2491,'A200A53C0A0A0A0A053C853C'),
        (0x24d4,'AAA5350A66356634A5350A66356634A539E534853998E535A8'),
    ]:
        assert original20[address:address+len(expected)//2]==bytes.fromhex(expected),hex(address)
    for address in (0x2423,0x2462,0x246b,0x24b3,0x24f6,0x2503):
        assert original20[address:address+2]==bytes.fromhex('9145')
    frames=[];cursor=0x9026
    while cursor<0xc34c:
        start=cursor;records=[]
        while original22[cursor]!=255:
            record=list(original22[cursor:cursor+6]);assert len(record)==6
            assert 0<=(record[0]&127)<(record[1]&127)<96 and record[4]<192
            records.append(record);cursor+=6
        cursor+=1
        if not records:break
        frames.append((start,records))
    assert cursor==0xc34c and len(frames)==56 and sum(len(r) for _,r in frames)==2173
    assert frames[52][0]==0xbfe8 and len(frames[52][1])==34
    return original20,original22,frames,contract,[meta(p) for p in files]


def engine_generation(memory,original):
    mutable={code+27*row+10 for code in (0x69d8,0x6c60) for row in range(24)}
    mutable|={0x6f19,0x6f1a,0x6f58,0x6f59}
    regions=((0x2360,0x2514),(0x3f00,0x4000),(0x69d8,0x6f66),(0x876c,0x8994))
    differences=[]
    for first,end in regions:
        for address in range(first,end):
            if memory[address]!=original[address]:
                assert address in mutable,('wrong attribute engine generation',hex(address))
                differences.append(dict(address=address,original=original[address],actual=memory[address]))
    return differences


def adc(a,b,carry):
    total=a+b+carry
    return total&255,total>>8


def sbc(a,b,carry):
    total=a-b-(1-carry)
    return total&255,int(total>=0)


def position_divide8(row,fraction):
    """Three logical row-LSR/fraction-ROR pairs; retain the outgoing bit."""
    packed=(row<<8)|fraction
    result=packed>>3
    return result>>8,result&255,(fraction>>2)&1


def signed_slope_half(integer,fraction):
    """ASL integer into carry, ROR integer, ROR fraction."""
    packed=(integer<<8)|fraction
    signed=packed-65536 if integer&128 else packed
    result=(signed//2)&65535
    return result>>8,result&255,fraction&1


def crop_contract(original):
    """Recover fixed source row windows and verify both unrolled propagators."""
    assert len(original)==65536
    crop=[]
    for column in range(24):
        pointer=original[0x876c+column]|original[0x8784+column]<<8
        top=pointer-(0xc380+24*column)
        first=original[0x8934+column]|original[0x894c+column]<<8
        end=original[0x8964+column]|original[0x897c+column]<<8
        assert first==0x6c60+27*top
        assert (end-0x6c60+1)%27==0
        bottom=(end-0x6c60+1)//27
        assert 0<=top<bottom<=24
        assert original[0x88d4+column]|original[0x88ec+column]<<8==0x69d8+27*top
        assert original[0x8904+column]|original[0x891c+column]<<8==0x69d8+27*bottom-1
        crop.append((top,bottom))
    assert sum(bottom-top for top,bottom in crop)==484
    for code,screen in ((0x69d8,0xdc00),(0x6c60,0x6000)):
        for row in range(24):
            pc=code+27*row;operand=pc+10;target=screen+8+40*row
            word=lambda x:bytes((x&255,x>>8))
            expected=(b'\xb1\x45\xf0\x11\x8d'+word(operand)+b'\xa5\x68\x2d'+
                      bytes((original[operand],0x3f))+b'\x0d'+word(operand)+
                      b'\x85\x68\xa9\x00\x91\x45\xa5\x68\x9d'+word(target)+b'\xc8')
            assert original[pc:pc+27]==expected
    masks=bytes(((0xf0 if value&15 else 255)&(0x0f if value&240 else 255))
                for value in range(256))
    assert original[0x3f00:0x4000]==masks
    return crop,masks


def edge_sites(record,xmap,ymap,offset_x=0,offset_y=0):
    """Attribute boundary cells from original $2367..$2479/$250F.

    This is a record-level fixed-point construction, not an opcode machine.
    The source deliberately differs from an ideal line/cell intersection.
    """
    x0,x1,slope_lo,slope_hi,y0,attribute=record
    # Source translations are byte ADCs (carry cleared by LSR/CLC), including
    # wrapped two's-complement offsets. Domain checks follow the byte sum.
    left=(xmap[x0&127]+offset_x)&255
    right=(xmap[x1&127]+offset_x)&255
    row=(ymap[y0]+offset_y)&255
    assert 0<=left<=right<96 and 0<=row<192
    if left==right or attribute==0:
        return [],dict(skipped=True,left=left,right=right)
    first_column,end_column=left//4,(right+3)//4
    fraction=0
    negative=bool(slope_hi&128)
    if negative:
        # $2381 ASL leaves carry1 throughout the remainder setup.
        carry=1
        align_count=3-(left&3)
        last_remainder=3-((right-1)&3)
        for _ in range(align_count):
            fraction,carry=adc(fraction,slope_lo,carry)
            row,carry=adc(row,slope_hi,carry)
        row,fraction,carry=position_divide8(row,fraction)
        first_row=row
        slope_hi,slope_lo,carry=signed_slope_half(slope_hi,slope_lo)
        # Source $23B9 adds the first full-column increment before traversal.
        fraction,carry=adc(fraction,slope_lo,carry)
        row,carry=adc(row,slope_hi,carry)
    else:
        first_row=row>>3
        # $23CE..$23D0 leave row bit2 in carry before the alignment additions.
        carry=(row>>2)&1
        align_count=0 if left&3==0 else 4-(left&3)
        last_remainder=0
        for _ in range(align_count):
            fraction,carry=adc(fraction,slope_lo,carry)
            row,carry=adc(row,slope_hi,carry)
        row,fraction,carry=position_divide8(row,fraction)
        slope_hi,slope_lo,carry=signed_slope_half(slope_hi,slope_lo)
    sites=[(first_column,first_row)]
    for column in range(first_column+1,end_column):
        last=column==end_column-1
        if last and last_remainder:
            # Two extra source arithmetic shifts, then SBC without a new SEC.
            slope_hi,slope_lo,carry=signed_slope_half(slope_hi,slope_lo)
            slope_hi,slope_lo,carry=signed_slope_half(slope_hi,slope_lo)
            for _ in range(last_remainder):
                fraction,carry=sbc(fraction,slope_lo,carry)
                row,carry=sbc(row,slope_hi,carry)
        sites.append((column,row))
        if not last:
            # CPX against the exclusive column end establishes carry0 here.
            fraction,carry=adc(fraction,slope_lo,0)
            row,carry=adc(row,slope_hi,carry)
    assert all(0<=column<24 and 0<=row<24 for column,row in sites)
    return sites,dict(skipped=False,left=left,right=right,negative=negative,
                     align_steps=align_count,last_remainder=last_remainder,
                     first_column=first_column,end_column=end_column,first_row=first_row)


def build_attributes(records,xmap,ymap,palette,initial_events,initial_shadow,
                     initial_screen,crop,masks,alias_nibbles=0,screen_base=0x6000,
                     offset_x=0,offset_y=0):
    assert len(xmap)==96 and len(ymap)==192 and len(palette)==16
    assert all(0<=color<16 for color in palette)
    assert len(initial_events)==len(initial_shadow)==576 and len(initial_screen)==1000
    events,shadow,screen=bytearray(initial_events),bytearray(initial_shadow),bytearray(initial_screen)
    event_writes,shadow_writes,records_info=[],[],[]
    for number,record in enumerate(records):
        sites,description=edge_sites(record,xmap,ymap,offset_x,offset_y)
        attribute=record[5]
        if description['skipped']:
            records_info.append(dict(record=number,attribute=attribute,description=description,sites=[]))
            continue
        color=palette[attribute&15];style=attribute&0x30
        for ordinal,(column,row) in enumerate(sites):
            assert crop[column][0]<=row<crop[column][1],('outside source crop',number,column,row)
            offset=24*column+row
            if style==0x30:
                old=shadow[offset];shadow[offset]=color
                shadow_writes.append(dict(record=number,column=column,row=row,
                                          pc=0x2423 if ordinal==0 else (0x2462 if ordinal==len(sites)-1 else 0x246b),
                                          address=0xc5c0+offset,old=old,value=color))
            else:
                if alias_nibbles:
                    keep,value=0,(color<<4)|color
                elif style==0x10:
                    keep,value=0x0f,color<<4
                else:
                    keep,value=0xf0,color
                old=events[offset];events[offset]=(old&keep)|value
                event_writes.append(dict(record=number,column=column,row=row,
                                         pc=0x24b3 if ordinal==0 else (0x24f6 if ordinal==len(sites)-1 else 0x2503),
                                         address=0xc380+offset,old=old,value=events[offset]))
        records_info.append(dict(record=number,attribute=attribute,color=color,
                                 description=description,sites=[list(s) for s in sites]))
    before_propagation=bytes(events)
    screen_writes,clears,operand_writes=[],[],[]
    code_base=0x6c60 if screen_base==0x6000 else 0x69d8
    assert screen_base in (0x6000,0xdc00)
    for column in reversed(range(24)):
        value=0
        for row in range(*crop[column]):
            offset=24*column+row;event=events[offset]
            if event:
                value=(value&masks[event])|event
                events[offset]=0
                clears.append(0xc380+offset)
                operand_writes.append(dict(address=code_base+27*row+10,value=event))
            index=8+40*row+column;old=screen[index];screen[index]=value
            screen_writes.append(dict(address=screen_base+index,column=column,row=row,old=old,value=value))
    assert len(screen_writes)==484
    return dict(screen=bytes(screen),screen_events_after=bytes(events),
                screen_events_before_propagation=before_propagation,shadow=bytes(shadow),
                screen_boundary_writes=event_writes,shadow_boundary_writes=shadow_writes,
                screen_writes=screen_writes,screen_event_clears=clears,
                mask_operand_writes=operand_writes,records=records_info)


def ordered_event_writes(result,screen_base=0x6000):
    boundaries=sorted(result['screen_boundary_writes']+result['shadow_boundary_writes'],
                      key=lambda row:row['record'])  # stable within each record
    code=0x6c60 if screen_base==0x6000 else 0x69d8
    clears=[dict(pc=code+27*((address-0xc380)%24)+19,address=address,value=0)
            for address in result['screen_event_clears']]
    return [dict(pc=r['pc'],address=r['address'],value=r['value']) for r in boundaries]+clears


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();out=args.output.resolve()
    assert out.is_relative_to(BASE) and not out.exists()
    out.mkdir(parents=True)
    source=Path(__file__).resolve();(out/'ball_attributes.checked.py').write_bytes(source.read_bytes())
    try:
        assert sha(CASE_PROOF.read_bytes())==CASE_SHA
        case=json.loads(CASE_PROOF.read_text());assert case['pass_']
        for record in case['outputs']:
            raw=(CASE_PROOF.parent/record['name']).read_bytes()
            assert len(raw)==record['bytes'] and sha(raw)==record['sha256']
        captures={r['stem']:r for r in case['captures']}
        names={'ball52-body-entry':0x21bd,'ball52-edge-entry':0x2209,'ball52-render-done':0x2265}
        memories={}
        for name,pc in names.items():
            capture=captures[name]
            assert capture['accepted_natural_phase'] and capture['stop_kind']=='natural exec checkpoint'
            assert capture['registers']['pc']==pc and capture['CPU_clock_flags_and_beam_equal']
            assert capture['all65536_physical_RAM_bytes_equal'] and not capture['registers']['flags']&8
            for key in ('ram','snapshot'):
                record=capture[key];path=ROOT/record['path'];assert meta(path)==record
            memories[name]=(ROOT/capture['ram']['path']).read_bytes()
        entry=memories['ball52-edge-entry'];target=memories['ball52-render-done'];body=memories['ball52-body-entry']
        original20,original22,frames,roles,inputs=original_sources();crop,masks=crop_contract(original20)
        generations={name:engine_generation(memory,original20) for name,memory in memories.items()}
        assert entry[0x3e:0x40]==bytes.fromhex('E8BF') and target[0x3e:0x40]==entry[0x3e:0x40]
        assert [entry[p] for p in (0x43,0x44,0x47,0x4b,0x4c,0x4e,0x4f,0x50)]==[0,0,0,20,20,0,0,20]
        assert entry[0x48:0x4a]==bytes.fromhex('1690')
        assert entry[0x9026:0xc34c]==original22[0x9026:0xc34c]
        assert entry[0xc380:0xc800]==bytes(1152)
        assert body[0xc380:0xc800]==entry[0xc380:0xc800]
        for first,end in ((0x6000,0x63e8),(0x8a74,0x8b94),(0x9016,0x9026),(0x51,0x53)):
            assert body[first:end]==entry[first:end]
        assert target[0x8a74:0x8b94]==entry[0x8a74:0x8b94]
        assert target[0x9016:0x9026]==entry[0x9016:0x9026]
        # Entry data only: no target/event/store/readback byte enters this call.
        result=build_attributes(frames[52][1],entry[0x8b34:0x8b94],entry[0x8a74:0x8b34],
            entry[0x9016:0x9026],entry[0xc380:0xc5c0],entry[0xc5c0:0xc800],
            entry[0x6000:0x63e8],crop,masks,alias_nibbles=entry[0x47],
            offset_x=entry[0x51],offset_y=entry[0x52])
        assert result['screen']==target[0x6000:0x63e8]
        assert result['shadow']==target[0xc5c0:0xc800]
        assert result['screen_events_after']==target[0xc380:0xc5c0]
        operand_after={r['address']:r['value'] for r in result['mask_operand_writes']}
        assert all(target[address]==value for address,value in operand_after.items())
        final_call=0x6c60+27*crop[0][0]
        assert int.from_bytes(target[0x6f58:0x6f5a],'little')==final_call
        # Apply only source-derived persistent mutations to the genuine prior
        # code generation. Temporary endpoint RTS patches must be restored.
        code_after=bytearray(entry[0x69d8:0x6f66])
        for address,value in operand_after.items():code_after[address-0x69d8]=value
        code_after[0x6f58-0x69d8:0x6f5a-0x69d8]=final_call.to_bytes(2,'little')
        assert code_after==target[0x69d8:0x6f66]
        records=json.loads((CASE_PROOF.parent/'trace-hits.json').read_text())
        low=captures['ball52-edge-entry']['registers']['clock'];high=captures['ball52-render-done']['registers']['clock']
        cutoff_sequence=captures['ball52-render-done']['stop_sequence']
        event_oracle=[r for r in records if r['operation']=='store' and 0xc380<=r['monitored_address']<0xc800
                      and low<=r['registers']['clock']<=high and r['sequence']<=cutoff_sequence]
        ordered=ordered_event_writes(result)
        assert len(ordered)==len(event_oracle)
        for n,(model,observed) in enumerate(zip(ordered,event_oracle)):
            assert model['pc']==observed['instruction_PC'] and model['address']==observed['monitored_address'],n
            assert observed['instruction'].startswith('STA ')
            assert model['value']==observed['registers']['a']==observed['raw_source_store_value'],n
        palette_stores=[r for r in records if r['operation']=='store' and 0x9016<=r['monitored_address']<0x9026
                        and low<=r['registers']['clock']<=high and r['sequence']<=cutoff_sequence]
        assert not palette_stores
        for name,data in [('predicted-back-screen-6000.bin',result['screen']),
                          ('predicted-color-shadow-c5c0.bin',result['shadow']),
                          ('predicted-screen-events-before.bin',result['screen_events_before_propagation']),
                          ('predicted-screen-events-after.bin',result['screen_events_after']),
                          ('predicted-attribute-code-69d8.bin',code_after)]:
            (out/name).write_bytes(data)
        ledger={k:result[k] for k in ('screen_boundary_writes','shadow_boundary_writes','screen_writes',
                                    'screen_event_clears','mask_operand_writes','records')}
        (out/'attribute-mutations.json').write_text(json.dumps(ledger,indent=2)+'\n')
        event_addresses={r['address'] for r in result['screen_boundary_writes']}
        shadow_addresses={r['address'] for r in result['shadow_boundary_writes']}
        outputs=[dict(name=p.name,bytes=len(p.read_bytes()),sha256=sha(p.read_bytes())) for p in sorted(out.iterdir())]
        proof=dict(pass_=True,scope='Independent typed screen-nibble and Color-RAM-shadow mathematics for one original Lab pose at genuine pre-edge state; no CPU interpreter/pixel/FPS proof',
            producer=meta(source),inputs=[meta(CASE_PROOF)]+inputs,
            source_roles=roles,actual_attribute_engine_differences=generations,
            release_source_ranges=[dict(file=20,first=0x2000,end_exclusive=0x9030),dict(file=22,first=0x8c00,end_exclusive=0xc34c)],
            input_state=dict(captures=[captures[n] for n in ('ball52-body-entry','ball52-edge-entry')],frame_index=52,frame_pointer=0xbfe8,
                records=34,scale_mode=20,translation_bytes=list(entry[0x51:0x53]),
                translation_signed=[v if v<128 else v-256 for v in entry[0x51:0x53]],
                palette=list(entry[0x9016:0x9026]),alias_nibbles=0,screen_base=0x6000,
                both_preedge_576_event_buffers_observed_zero=True,
                scale_and_palette_are_declared_entry_inputs=True),
            comparison_oracles=dict(render_done_capture=captures['ball52-render-done'],
                                    store_hooks=meta(CASE_PROOF.parent/'trace-hits.json')),
            crop=dict(columns=[list(r) for r in crop],cells=484,source_fixed_not_current_dirty_bounds=True),
            mathematical_mask_table_all256_equal_source=True,
            comparisons=dict(backscreen1000_equal=True,screen_cells_computed=484,screen_cells_preserved=516,
                shadow576_equal=True,shadow_boundary_store_count=len(result['shadow_boundary_writes']),
                shadow_cells_written=len(shadow_addresses),shadow_cells_preserved=576-len(shadow_addresses),
                screen_events576_equal=True,screen_boundary_store_count=len(result['screen_boundary_writes']),
                screen_boundary_cells_written=len(event_addresses),screen_event_clears=len(result['screen_event_clears']),
                ordered_event_hook_PC_address_value_checks=len(ordered),event_hook_scope='Comparison only, after source prediction; addresses/counts did not control the math.',
                changed_mask_operands_equal=len(operand_after),final_wrapper_JSR_target_equal=True,
                full1422_byte_attribute_code_generation_equal=True,
                palette_store_hooks_during_body=0),
            exact_modeled_mutated_regions=[dict(first=0x6000,end_exclusive=0x63e8,computed_cells=484,preserved_cells=516),
                dict(first=0xc380,end_exclusive=0xc5c0,kind='screen-boundary event merge and consumed-event clearing'),
                dict(first=0xc5c0,end_exclusive=0xc800,kind='pending Color-RAM boundary events, not published Color RAM'),
                dict(addresses=sorted(operand_after),kind='nonzero-event source mask-operand updates')],
            outputs=outputs,
            limits=['No current-frame target attributes, event buffers or observed store values seed prediction.',
                'The genuine native02 palette is partial and translations areFD/EC. The old identity/zero-translation study remains separate and conditional.',
                'Only frame52attributes are native-checked; parsing all56released frames does not prove all56attribute results or arbitrary transforms.',
                'Color-shadow events remain pending at2265beforeINC44; actualColorRAM publication, fullcolors/scanout and timing are separate consumers.',
                'Original decoded RAM images are padded. Only PRG/written-mask-proven release ranges are treated as source data.',
                'No native process, CPU interpreter, build, downloaded host program or shared-index change occurs.'])
        raw=(json.dumps(proof,indent=2)+'\n').encode();(out/'ball-attribute-proof.json').write_bytes(raw)
        print(json.dumps(dict(pass_=True,receipt_bytes=len(raw),receipt_sha256=sha(raw),
            event_hooks=len(ordered),screen_computed=484,shadow_store_count=len(result['shadow_boundary_writes'])),indent=2))
    except Exception as error:
        (out/'failure.json').write_text(json.dumps(dict(pass_=False,error=str(error),traceback=traceback.format_exc(),producer=meta(source)),indent=2)+'\n')
        raise


if __name__=='__main__':
    main()
