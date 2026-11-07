#!/usr/bin/env python3
"""Analyze existing CA graphic stores without executing CPU or hardware.

Ordered byte ownership, clipping sinks and independent two-bit sample
arithmetic are derived from pinned artifacts. This is stored glyph memory,
not a reconstruction of time-varying VIC output.
"""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'build/research/second-reality'
CA_PROOF_SHA='36af2e866fc3421b0fe9652a0503866a4bc08b715e6f4c46a4587453f6c4f57c'
NATIVE_PROOF_SHA='fc9be5785818dd4febbd5f8a9837394956130f75582884516a562c45c140feb4'
sys.path.insert(0,str(ROOT/'research/quondam'))
from snapshot_state import read_snapshot


def sha(data):return hashlib.sha256(data).hexdigest()
def relative(path):return str(path.resolve().relative_to(ROOT))
def pinned(path,digest):
    data=path.read_bytes();assert sha(data)==digest,('Pinned artifact changed',path)
    return data
def category(address):
    if 0xe400<=address<0xe500:return 'vertical_sink_E4'
    if 0xe800<=address<0x10000:
        return 'left_column_sink' if address%256<8 else 'colored_atlas'
    raise AssertionError(('Unexpected graphic destination',address))
def samples(value):return {lane:(value>>(6-2*lane))&3 for lane in range(4) if (value>>(6-2*lane))&3}
def point(value):
    entries=list(samples(value).items());assert len(entries)==1,('Point value is not one nonzero two-bit lane',value)
    return entries[0]
def coordinates(address,lane):
    assert 0xe800<=address<0x10000 and 0<=lane<4
    index=address-0xe800;group,index=divmod(index,2048);glyph,row=divmod(index,8)
    charrow,column=divmod(glyph,32)
    return column*4+lane,group*64+charrow*8+row
def nonzero_atlas(memory):
    return {(address,lane):code for address in range(0xe800,0x10000)
            if category(address)=='colored_atlas' for lane,code in samples(memory[address]).items()}
def histogram(values):return {str(k):v for k,v in sorted(Counter(values).items())}
def domain_difference(actual,expected):
    addresses=[a for a in range(0xe800,0x10000) if category(a)=='colored_atlas']
    return dict(different_bytes=sum(actual[a]!=expected[a] for a in addresses),
                different_two_bit_samples=sum(((actual[a]>>s)&3)!=((expected[a]>>s)&3) for a in addresses for s in (0,2,4,6)))


def picture(path,requested,endpoint,missing):
    """A labelled data visualization; no native screenshot is consumed."""
    scale=3;top=60;gap=24;left=12;width=128*scale;height=192*scale
    image=Image.new('RGB',(2*width+gap+2*left,height+top+36),(30,30,35));draw=ImageDraw.Draw(image)
    draw.text((left,8),'Stored glyph-atlas ownership: not a beam frame',fill='white')
    draw.text((left,27),'Requested: latest color per pixel lane',fill='white')
    draw.text((left+width+gap,27),'Native B; missing requested lanes in red',fill='white')
    colors={1:(180,180,180),2:(95,95,95),3:(255,255,255)}
    for panel,data in enumerate((requested,endpoint)):
        x0=left+panel*(width+gap)
        draw.rectangle((x0,top,x0+width-1,top+height-1),fill=(0,0,0))
        draw.rectangle((x0,top,x0+4*scale-1,top+height-1),fill=(45,45,55))
        for (address,lane),code in data.items():
            x,y=coordinates(address,lane)
            draw.rectangle((x0+x*scale,top+y*scale,x0+(x+1)*scale-1,top+(y+1)*scale-1),fill=colors[code])
        if panel:
            for address,lane in missing:
                x,y=coordinates(address,lane)
                draw.rectangle((x0+x*scale,top+y*scale,x0+(x+1)*scale-1,top+(y+1)*scale-1),outline=(255,65,65))
    draw.text((left,top+height+10),'Gray left strip: black/clipping column. Logical samples; not native RGB output.',fill='white')
    image.save(path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=BASE/'ca-coverage')
    args=parser.parse_args();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    proof_path=BASE/'ca-analysis/ca-proof.json';proof=json.loads(pinned(proof_path,CA_PROOF_SHA));assert proof['pass'] is True
    native_path=BASE/'native-parts-analysis/native-parts-evidence.json'
    native=json.loads(pinned(native_path,NATIVE_PROOF_SHA));assert native['status']=='complete' and native['pass'] is True
    assert sha((ROOT/'research/quondam/snapshot_state.py').read_bytes())==native['snapshot_reader_sha256']
    ca_file=proof['files']['CA'];pinned(ROOT/ca_file['path'],ca_file['sha256'])
    store_record=proof['native_prestate_iteration']['plot_store_receipt'];store_path=ROOT/store_record['path']
    stores=json.loads(pinned(store_path,store_record['sha256']))
    assert len(stores)==1984 and Counter(s['kind'] for s in stores)=={'cached_clear':992,'point_plot':992}
    captures={row['name']:row for row in proof['captures']}
    before=pinned(ROOT/captures['ca-iteration-a']['ram']['path'],captures['ca-iteration-a']['ram']['sha256'])
    after=pinned(ROOT/captures['ca-iteration-b']['ram']['path'],captures['ca-iteration-b']['ram']['sha256'])
    assert len(before)==len(after)==65536
    states=[]
    for name in ('ca-iteration-a','ca-iteration-b'):
        row=captures[name];path=ROOT/row['snapshot']['path'];pinned(path,row['snapshot']['sha256'])
        states.append(read_snapshot(path))
    # Derive both lookup tables by finite integer binning, not CPU replay.
    expected_x=bytes(8*((x-64)//4) if 64<=x<192 else 0 for x in range(256))
    expected_y=bytes(0xe8+(y-32)//8 if 32<=y<224 else 0xe4 for y in range(256))
    for memory,state in zip((before,after),states):
        assert memory[0x400:0x500]==expected_x and memory[0x500:0x600]==expected_y
        expected_colors=[9 if r<24 and 5<=c<36 else 0 for r in range(25) for c in range(40)]+[0]*24
        assert state['vicii']['color_ram']==expected_colors
        for r in range(24):
            for c in range(4,36):assert memory[0xe000+r*40+c]==(r%8)*32+c-4
    for instance in range(1,32):
        block=stores[(instance-1)*64:instance*64]
        assert [s['kind'] for s in block]==['cached_clear']*32+['point_plot']*32
        for s in block:
            assert (s['pc']-0x2000)//1108==instance
            assert before[s['pc']]==(0x8d if s['kind']=='cached_clear' else 0x91)
            if s['kind']=='cached_clear':assert s['value']==0
            else:point(s['value'])
    state=bytearray(before);owners={};histories=defaultdict(list);kills=[];classified=[]
    requested={};plot_events=[]
    for index,store in enumerate(stores):
        address,value=store['address'],store['value'];kind=store['kind'];which=category(address)
        prior=owners.get(address);old=state[address]
        entry=dict(index=index,**store,category=which,instance=(store['pc']-0x2000)//1108)
        if kind=='point_plot':
            lane,code=point(value);entry.update(lane=lane,selector=code);plot_events.append(entry)
            if which=='colored_atlas':requested[address,lane]=code
        if old and prior is not None and stores[prior]['kind']=='point_plot':
            kills.append(dict(earlier_plot_index=prior,replacing_store_index=index,address=address,
                              old_byte=old,new_byte=value,replacement_kind=kind,category=which,
                              cleared_other_lanes=sorted(samples(old).keys()-samples(value).keys())))
        state[address]=value;owners[address]=index;histories[address].append(index);classified.append(entry)
    assert state[0xe000:0x10000]==after[0xe000:0x10000],'Ordered literal STA stores do not reconstruct native B graphic RAM.'
    endpoint=nonzero_atlas(after);missing=sorted(requested.keys()-endpoint.keys());extra=sorted(endpoint.keys()-requested.keys())
    wrong=[key for key in requested.keys()&endpoint.keys() if requested[key]!=endpoint[key]]
    point_addresses=Counter(s['address'] for s in plot_events)
    point_slots=Counter((s['address'],s['lane']) for s in plot_events)
    def traffic(kind):
        rows=[s for s in classified if s['kind']==kind]
        return {cat:dict(stores=sum(s['category']==cat for s in rows),
                         unique_addresses=len({s['address'] for s in rows if s['category']==cat}))
                for cat in ('colored_atlas','left_column_sink','vertical_sink_E4')}
    counters={}
    for name,operation in (('OR',lambda x,y:x|y),('XOR',lambda x,y:x^y)):
        same_clear=bytearray(before);fresh=bytearray(65536)
        for store in stores:
            a,v=store['address'],store['value']
            if store['kind']=='cached_clear':same_clear[a]=0
            else:same_clear[a]=operation(same_clear[a],v);fresh[a]=operation(fresh[a],v)
        counters[name]=dict(same_original_clear_order=domain_difference(after,same_clear),
                            fresh_current_point_combination=domain_difference(after,fresh))
    per_pixel=bytearray(65536)
    for (a,lane),code in requested.items():per_pixel[a]|=code<<(6-2*lane)
    eligible_plots=[s for s in plot_events if s['category']=='colored_atlas']
    eligible_addresses={s['address'] for s in eligible_plots}
    visible_lane_sets=defaultdict(set)
    for s in eligible_plots:visible_lane_sets[s['address']].add(s['lane'])
    witnesses={}
    for kill in kills:
        if kill['category']!='colored_atlas':continue
        if kill['replacement_kind']=='cached_clear':witnesses.setdefault('later_clear_erases_current_plot',kill)
        elif kill['cleared_other_lanes']:witnesses.setdefault('point_STA_erases_another_lane',kill)
    missing_rows=[]
    for address,lane in missing:
        index=owners[address];last=classified[index];x,y=coordinates(address,lane)
        missing_rows.append(dict(address=address,lane=lane,logical_x=x,logical_y=y,requested_selector=requested[address,lane],
                                 final_byte=after[address],last_store_index=index,last_store_kind=last['kind']))
    summary=dict(point_plots=992,cached_clears=992,traffic={k:traffic(k) for k in ('cached_clear','point_plot')},
                 point_byte_collisions=dict(unique_addresses=len(point_addresses),repeated_stores=992-len(point_addresses),
                     addresses_with_multiple_plots=sum(v>1 for v in point_addresses.values()),maximum_plots_per_address=max(point_addresses.values()),
                     multiplicity_histogram=histogram(point_addresses.values()),unique_two_bit_slots=len(point_slots),
                     repeated_same_slot_stores=992-len(point_slots)),
                 colored_atlas=dict(eligible_plot_stores=len(eligible_plots),unique_requested_byte_addresses=len(eligible_addresses),
                     unique_requested_pixel_lanes=len(requested),addresses_requesting_multiple_lanes=sum(len(v)>1 for v in visible_lane_sets.values()),
                     same_pixel_duplicate_stores=len(eligible_plots)-len(requested),native_A_nonzero_samples=len(nonzero_atlas(before)),
                     native_B_nonzero_samples=len(endpoint),missing_requested_samples=len(missing),extra_samples=len(extra),wrong_selector_samples=len(wrong),
                     last_pixel_color_wins_reference_difference=domain_difference(after,per_pixel)),
                 immediate_current_plot_replacements={cat:dict(Counter(k['replacement_kind'] for k in kills if k['category']==cat))
                     for cat in ('colored_atlas','left_column_sink','vertical_sink_E4')},
                 terminal_plot_byte_owners=dict(Counter(category(a) for a,index in owners.items() if stores[index]['kind']=='point_plot')),
                 missing_samples_by_final_writer=dict(Counter(row['last_store_kind'] for row in missing_rows)))
    assert summary['colored_atlas']['native_B_nonzero_samples']==len(requested)-len(missing)+len(extra)
    assert not extra and not wrong
    image_path=output/'stored-atlas-ownership.png';picture(image_path,requested,endpoint,missing)
    collisions=[dict(address=a,category=category(a),plot_count=point_addresses[a],
                     ordered_store_indices=histories[a],final_byte=after[a],final_owner=owners[a])
                for a in sorted(point_addresses) if point_addresses[a]>1]
    result=dict(pass_=True,script_sha256=sha(Path(__file__).read_bytes()),
                source_proof=dict(path=relative(proof_path),sha256=CA_PROOF_SHA),
                native_lifecycle_proof=dict(path=relative(native_path),sha256=NATIVE_PROOF_SHA),
                ordered_stores=dict(path=relative(store_path),sha256=store_record['sha256'],count=len(stores)),
                inputs={name:captures[name] for name in ('ca-iteration-a','ca-iteration-b')},
                mapping=dict(x_input_range=[64,192],y_input_range=[32,224],colored_columns_inclusive=[5,35],
                             colored_character_rows=[0,24],colored_atlas_byte_count=5952,logical_colored_samples=23808,
                             limitation='Left-column destinations conflate out-of-range X with valid first-bin X64..67; address traffic alone cannot separate them. Atlas mapping is not a beam-time reconstruction.'),
                ordered_STA_graphic_RAM_match=dict(range=[0xe000,0x10000],bytes=8192,exact=True,sha256=sha(state[0xe000:0x10000])),
                summary=summary,counterfactual_combining=counters,witnesses=witnesses,
                missing_requested_samples=missing_rows,extra_samples=[list(k) for k in extra],wrong_selector_samples=[list(k) for k in wrong],
                colliding_point_addresses=collisions,immediate_current_plot_replacement_events=kills,
                visualization=dict(path=relative(image_path),sha256=sha(image_path.read_bytes()),
                                   interpretation='Derived logical glyph-atlas visualization; not a native screenshot or coherent display frame.'),
                scope='One pinned A→B interval, independent byte/lane ownership arithmetic over existing ordered stores. No new CPU/native execution, hardware mock, actual-beam pixel oracle or claim that authored point loss is a demo bug.')
    result['pass']=result.pop('pass_');target=output/'coverage.json';target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(pass_=True,summary=summary,counterfactual_combining=counters,receipt=relative(target)),indent=2))


if __name__=='__main__':main()
