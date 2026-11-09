#!/usr/bin/env python3
"""Bind One-Der's column-major software canvas to retained VIC text states."""
import argparse
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'build/research/one-der'
PINS={
    'research/one-der/analyze.py':'8b46d13c021f2d691bacfd87c2194e77450459b8d5c1b3ea24da0e71ed6338f4',
    'build/research/one-der/analysis/accepted-02/one-der-proof.json':'e5eaaa1c454462e84de564b0984b8d587a37993b2b42457cc504bff0925f1532',
    'research/quondam/snapshot_state.py':'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw=path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)),bytes=len(raw),sha256=sha(raw))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    out=p.parse_args().output.resolve();out.relative_to((BASE/'display-analysis').resolve())
    assert not out.exists(),'Choose a fresh output directory'
    for name,pin in PINS.items():assert sha((ROOT/name).read_bytes())==pin,name
    spec=importlib.util.spec_from_file_location('one_der_display_snapshot',ROOT/'research/quondam/snapshot_state.py')
    reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    accepted=json.loads((BASE/'analysis/accepted-02/one-der-proof.json').read_text())
    captures={}
    for row in accepted['captures']:
        for field in ('ram','snapshot'):
            path=ROOT/row[field]['path'];raw=path.read_bytes()
            assert len(raw)==row[field]['bytes'] and sha(raw)==row[field]['sha256']
        captures[row['stem']]=dict(ram=(ROOT/row['ram']['path']).read_bytes(),snapshot=ROOT/row['snapshot']['path'])
    source=captures['part2']['ram']
    expected=bytes.fromhex('a2008a18')
    for r in range(16):expected+=b'\x9d'+(0x40c+40*r).to_bytes(2,'little')+bytes.fromhex('6901')
    expected+=bytes.fromhex('e8e010d0aa')
    assert source[0x206b:0x206b+len(expected)]==expected
    # BNE20C2 targets206E, retaining A after the preceding16 increments.
    assert 0x20c4+int.from_bytes(source[0x20c3:0x20c4],'little',signed=True)==0x206e
    grid=[dict(row=r,column=c,screen_address=0x40c+40*r+c,code=16*c+r,
               glyph_2000=0x2000+8*(16*c+r),glyph_2800=0x2800+8*(16*c+r))
          for r in range(16) for c in range(16)]
    stems=('frame-start','shade-start','kernel-start','kernel-end','later-frame','draw-end','cosmetic')
    states={}
    for stem in stems:
        capture=captures[stem];ram=capture['ram'];state=reader.read_snapshot(capture['snapshot'])
        colors=state['vicii']['color_ram']
        for cell in grid:
            assert ram[cell['screen_address']]==cell['code']
            assert colors[cell['screen_address']-0x400]==8
        states[stem]=state
    addresses={}
    for c in range(16):
        for y in range(128):
            r,rc=divmod(y,8)
            offset=128*c+y
            assert offset==8*(16*c+r)+rc and offset not in addresses
            addresses[offset]=(c,y)
    assert set(addresses)==set(range(2048))
    observations=[]
    for stem,r in [('shade-start',2),('kernel-start',3)]:
        state=states[stem];v=state['vicii'];regs=v['regs'];cia=state['cia']['CIA2'];ram=captures[stem]['ram']
        assert (regs[0x11]&0x60)==0 and regs[0x16]&0x10
        assert cia['ddra']&3==3
        bank=((~cia['pra'])&3)*0x4000
        screen=bank+((regs[0x18]&0xf0)<<6)
        charset=bank+((regs[0x18]&14)<<10)
        assert bank==0 and screen==0x400 and charset==0x2800
        assert v['vcbase']==40*r
        assert v['vbuf'][12:28]==[16*c+r for c in range(16)]
        assert v['cbuf'][12:28]==[8]*16
        rc=v['rc'];assert 0<=rc<8
        sample_addresses=[charset+8*(16*c+r)+rc for c in range(16)]
        assert sample_addresses==[charset+128*c+8*r+rc for c in range(16)]
        observations.append(dict(capture=stem,beam=[v['raster_line'],v['raster_cycle']],mode='multicolor text',
            bank=bank,screen=screen,charset=charset,cached_matrix_row=r,RC=rc,cached_codes=v['vbuf'][12:28],
            cached_colors=v['cbuf'][12:28],potential_row_fetch_addresses=sample_addresses,
            potential_row_bytes=[ram[a] for a in sample_addresses],
            limitation='Addresses follow the cached row and current RC. This is not proof that all16 glyph bytes/pixels were already fetched or committed when stopped.'))
    kernel_state=states['kernel-start']['vicii'];regs=kernel_state['regs']
    palette=[regs[0x21]&15,regs[0x22]&15,regs[0x23]&15,0]
    byte=accepted['kernel']['after'];selectors=[(byte>>shift)&3 for shift in (6,4,2,0)]
    assert byte==0x9a and selectors==[2,1,2,2] and palette==[3,14,6,0]
    rows=io.StringIO(newline='');writer=csv.DictWriter(rows,fieldnames=list(grid[0]),lineterminator='\n');writer.writeheader();writer.writerows(grid)
    out.mkdir(parents=True)
    outputs=[]
    for name,raw in [('matrix.csv',rows.getvalue().encode()),('display_map.checked.py',Path(__file__).read_bytes())]:
        (out/name).write_bytes(raw);outputs.append(dict(name=name,bytes=len(raw),sha256=sha(raw)))
    proof=dict(pass_=True,scope='Source-defined canvas and retained interior cached text rows; not complete raster/pixel acceptance',
        producer=artifact(Path(__file__)),inputs=[artifact(ROOT/p) for p in PINS],capture_acceptance_reused=True,
        source_matrix_generator=dict(start=0x206b,end_exclusive=0x20c4,bytes=expected.hex(),branch_target=0x206e),
        canvas=dict(screen=0x400,first_screen_column=12,character_columns=16,character_rows=16,
                    code_formula='16*column+character_row',byte_formula='charset+128*column+Y',
                    all2048_offsets_bijective=True,nominal_multicolor_samples=[64,128],nominal_display_pixels=[128,128],
                    sampled_matrix_bytes=256*len(stems),sampled_Color_RAM_bytes=256*len(stems),captures=list(stems)),
        interior_observations=observations,
        nibble_interpretation=dict(packed_byte=byte,nibbles=[byte>>4,byte&15],multicolor_selectors=selectors,
            physical_selector_replication=[v for s in selectors for v in (s,s)],sampled_palette_indices=palette,
            hypothetical_palette_indices_if_displayed=[palette[s] for s in selectors],
            each_nibble_nominal_physical_width=4,
            outside=dict(cleared_byte=255,selector=3,Color_RAM=8,palette_index=0),
            limitation='The byte probe wrote the draw buffer, while sampled VIC displayed the other charset. Palette interpretation is conditional, not a committed-pixel comparison.'),
        limits=['The nominal128-row canvas follows source/matrix layout; lower IRQ at raster178 changes to the portrait bitmap. Exact boundary-pixel scanout remains open.',
                'Current VIC/CIA states and cached rows bind ordinary multicolor text inside the canvas; this does not establish another production uses the same mode.',
                'A nibble supplies two VIC multicolor selectors/four nominal physical pixels. Per-vertex intensity, dither phase and coverage are separate quantities.',
                'No new native execution, CPU emulation, timing or product changes.'],outputs=outputs)
    raw=(json.dumps(proof,indent=2)+'\n').encode();(out/'display-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=True,output=str(out),receipt_bytes=len(raw),receipt_sha256=sha(raw),matrix_checks=256*len(stems),interior_rows=len(observations))))


if __name__=='__main__':main()
