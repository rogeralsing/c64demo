#!/usr/bin/env python3
"""Explain pinned conservative culling and correlate observed draw subtrees.

Reads only retained source, PRG, captures and accepted passive receipts. No
upstream script, build tool, CPU model, emulator or live connection executes.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
NATIVE = ROOT / 'build/research/3dvibe64-native'
PROFILE = ROOT / 'build/research/3dvibe64-profile'
ACCEPTED = PROFILE / 'profile-analysis/accepted-02'
PINS = {
    'build/research/3dvibe64-native/build-01/products/3Dvibe64.asm': '22008b3a92b7896c699543b12f9036704797262aa3558cd9116d8a09c85b796f',
    'build/research/3dvibe64-native/build-01/products/3Dvibe64.prg': '69b0d86f79106b2bf9654d85bd631bc68c12f4efd708454a0048560b3c1bfdeb',
    'build/research/3dvibe64-native/symbols-01/3Dvibe64.labels': '265a1770fe7a605139f0cdfd9d2983f6ddb314a1cf234a6f3a14d6f3b344e847',
    'research/3dvibe64-profile/native_profile.py': '2362c360bb2b99714d6c03bbba88e08dbf3d1b677d287b6bb945dc3b4d06d1ca',
    'build/research/3dvibe64-profile/native-01-pin.json': '35abf1d4b0f02aad49e08cb38337b80be108bc60fa315161b573490331d6a246',
    'build/research/3dvibe64-profile/profile-analysis/accepted-02/profile-proof.json': 'ebf994a2f7ed0a211cf98a2a112ea2d2b055de04a493484d238717736c42942a',
    'build/research/3dvibe64-profile/profile-analysis/accepted-02/span-records.json': '9dc2145badd95d98401b68938c437448160ff3ed8a80a20bce40b4c5cd79c18b',
    'build/research/3dvibe64-profile/profile-analysis/accepted-02/intervals.json': 'a85f51572e824a88fade3fb20a0289dbc349772a6f97e6bd2b94083d935c6119',
}
CASE_SHA = '13bfd23f30bf0b7a2db7a9e8dc4ceb8dc69e77d81c76862fe9b372a1f23ef714'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def signed(n, bits):
    return n if n < 1 << (bits-1) else n-(1 << bits)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'build/research/3dvibe64-overdraw/cull-analysis')
    args = parser.parse_args()
    output = args.output.resolve()
    inputs = []
    for rel,pin in PINS.items():
        item = artifact(ROOT/rel)
        assert item['sha256'] == pin, rel
        inputs.append(item)
    asm = (NATIVE/'build-01/products/3Dvibe64.asm').read_text()
    lines = asm.splitlines()
    labels = {n:int(v,16) for v,n in re.findall(r'(?m)^al ([0-9a-f]+) \.([^\s]+)$',
                                                (NATIVE/'symbols-01/3Dvibe64.labels').read_text())}
    prg = (NATIVE/'build-01/products/3Dvibe64.prg').read_bytes()
    load = int.from_bytes(prg[:2], 'little')
    ram0 = bytearray(65536)
    ram0[load:load+len(prg)-2] = prg[2:]

    def const(name):
        if name == 'CAMERA_FACE_MIN_DEPTH':
            assert 'CAMERA_FACE_MIN_DEPTH = PROJ_CAMERA_FACE_MIN_DEPTH' in asm
            return const('PROJ_CAMERA_FACE_MIN_DEPTH')
        values = re.findall(r'(?m)^'+re.escape(name)+r' = (\$[0-9a-fA-F]+|\d+)\s*(?:;[^\n]*)?$',asm)
        assert values and len(set(values)) == 1, name
        return int(values[0][1:],16) if values[0].startswith('$') else int(values[0])

    expected_flags = dict(CONSERVATIVE_FACE_CULL=1,CONSERVATIVE_SLIVER_CULL=1,
        CONSERVATIVE_CULL_NEG_AREA=32,CONSERVATIVE_EDGE_CULL_NEG_AREA=96,
        CONSERVATIVE_SLIVER_THIN_SPAN=3,CONSERVATIVE_SLIVER_LONG_SPAN=6,
        FACE_CULL_PREP=1,FORCE_FACE_RENDER=0,STABLE_FACE_CULL_PROFILE=0,
        CAMERA_SPACE_FACE_CULL_SUPPORT=0,CAMERA_MOVABLE=0,CAMERA_PLANE_CLIP_PROFILE=0,
        EXPLORER_NEAR_POLY=0,EXPLORER_SCREEN_CLIP_POLY=0,MESH_SOURCE_SHARING_RUNTIME=0,
        MODE4_FACE_ID_LATCH=1,SOLID_SUBPIXEL_XYQ2_LEGACY_DIRECT_Y=1,
        HAS_TRI_FACES=1,SCENE_OBJECT_COUNT=1,FACE_COUNT=8,VERT_COUNT=6,
        MIN_FACE_AREA=10,SCREEN_MIN_SPAN=3,CAMERA_FACE_MIN_DEPTH=8)
    flags = {name:const(name) for name in expected_flags}
    assert flags == expected_flags
    assert const('mode4_current_face_id') == 12 and const('faceidx') == 13
    assert labels['face_visible'] == 0x9000 and labels['load_face_visible'] == 0x42a9
    assert labels['mode4_latch_current_face_id'] == 0xca1d
    assert labels['face_conservative_sliver'] == 0x4366
    guards = []

    def guard(pc, expected):
        raw = bytes.fromhex(expected)
        assert bytes(ram0[pc:pc+len(raw)]) == raw, hex(pc)
        guards.append(dict(pc=pc,bytes=raw.hex()))

    guard(0x9039,'a5 44 30 03 4c 4d 90 c9 ff d0 0b a5 43 c9 e0 b0 03 4c 4f 90 38 60 18 60')
    guard(0x42a9,'a4 0d b9 b4 b4 aa bd 36 80 85 10 bd 3c 80 49 ff 18 69 01 85 11')
    guard(0x42e4,'20 00 90 90 44 20 87 43 f0 3f a4 0d be b4 b4 20 51 90')
    guard(0x4317,'a4 0d 84 51 20 ec 40 90 0d 20 2f 43 d0 05 20 66 43 f0 03 4c 85 14')
    guard(0x4366,'a5 60 c9 04 b0 09 a5 5f c9 06 b0 12 a9 00 60 a5 5f c9 04 b0 09 a5 60 c9 06 b0 03 a9 00 60 a9 01 60')
    guard(0x423a,'38 a5 42 e5 41 85 5f 4c 56 42')
    guard(0x428c,'38 a5 42 e5 41 85 60 4c a5 42')
    guard(0xca1d,'85 51 85 0c c9 08 90 04 78 4c 26 ca a4 0c 4c 19 40')
    guard(0x4015,'4c 1d ca ea a4 0c a4 0c 20 ad 91 20 ec 40')

    # The signed multiplier uses Q(a+b)-Q(|a-b|), then restores the sign.
    # Bind all linked quarter-square bytes independently; no 6502 execution.
    quarters = [n*n//4 for n in range(256)]
    for name,shift in [('sqlo',0),('sqhi',8)]:
        address = labels[name]
        assert bytes(ram0[address:address+256]) == bytes((n >> shift)&255 for n in quarters)
    mul_start,mul_end = labels['mul_s8_16'],labels['ms8_done']+1
    mul_source = asm[asm.index('mul_s8_16:'):asm.index('solid_subpixel_yq2_store:')]
    for text in ['lda sqlo,x','lda sqhi,x','sbc sqlo,x','sbc sqhi,x','eor #$80']:
        assert text in mul_source

    manifest = json.loads((PROFILE/'native-01-pin.json').read_text())
    actual = [dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
              for p in sorted((PROFILE/'native-01').iterdir()) if p.is_file()]
    assert manifest['entries'] == actual
    assert sha(json.dumps(actual,sort_keys=True,separators=(',',':')).encode()) == manifest['case_sha256'] == CASE_SHA
    profile = json.loads((ACCEPTED/'profile-proof.json').read_text())
    assert profile['pass_'] and profile['case_sha256'] == CASE_SHA
    intervals = json.loads((ACCEPTED/'intervals.json').read_text())
    spans = json.loads((ACCEPTED/'span-records.json').read_text())
    faces = [list(face) for face in zip(*[ram0[labels['face'+str(i)]:labels['face'+str(i)]+8] for i in range(3)])]
    assert faces == [[0,5,2],[2,5,1],[1,5,3],[3,5,0],[0,2,4],[2,1,4],[1,3,4],[3,0,4]]
    assert bytes(ram0[labels['face_vertex_count']:labels['face_vertex_count']+8]) == b'\x03'*8
    source_refs = []
    for name in ['load_face_visible','face_visible','load_face_y','screen_face_drawable',
                 'face_far_depth','face_conservative_sliver','mode4_latch_current_face_id','mul_s8_16']:
        line = next(i+1 for i,text in enumerate(lines) if text == name+':')
        source_refs.append(dict(label=name,line=line,pc=labels[name]))
    frames,groups,used_products = [],[],0

    def product(a,b):
        nonlocal used_products
        assert -128 <= a <= 127 and -128 <= b <= 127
        assert abs(a)+abs(b) < 256  # Guard the linked 8-bit sum index.
        value = quarters[abs(a)+abs(b)]-quarters[abs(abs(a)-abs(b))]
        value = -value if (a < 0) != (b < 0) else value
        assert value == a*b
        used_products += 1
        return value

    for frame_intervals,frame_profile in zip(intervals,profile['frames']):
        name,nodes = frame_intervals['frame'],frame_intervals['nodes']
        assert name == frame_profile['frame']
        complete = PROFILE/'native-01'/f'{name}-complete.bin'
        captured = complete.read_bytes()
        rx = [signed(v,8) for v in captured[0x8036:0x803c]]
        ry = [signed(v,8) for v in captured[0x803c:0x8042]]
        sx,sy = list(captured[0x8000:0x8006]),list(captured[0x8006:0x800c])
        syq2 = [captured[0x800c+i]+256*captured[0x8012+i] for i in range(6)]
        depth = [captured[0x802a+i]+256*captured[0x8030+i] for i in range(6)]
        projdone = list(captured[0x8042:0x8048])
        face_results = []
        for face_id,vertices in enumerate(faces):
            xy = [(rx[i],signed((-ry[i])&255,8)) for i in vertices]
            (x0,y0),(x1,y1),(x2,y2) = xy
            dx1,dy1,dx2,dy2 = [signed(v&255,8) for v in (x1-x0,y1-y0,x2-x0,y2-y0)]
            raw_cross = (product(dx1,dy2)-product(dy1,dx2))&65535
            cross = signed(raw_cross,16)
            accepted_area = cross >= -32
            depth_safe = all(signed(depth[i],16) >= 8 for i in vertices)
            valid_projection = all(projdone[i] == 1 for i in vertices)
            result = dict(face=face_id,vertices=vertices,rotated_xy=xy,signed_cross=cross,
                          conservative_area_accepts=accepted_area,depth_safe=depth_safe,
                          all_three_projected=valid_projection)
            if accepted_area:
                assert depth_safe and valid_projection
                px = [sx[i] for i in vertices]
                py = [(syq2[i]+2)//4 for i in vertices]
                width,height = max(px)-min(px),max(py)-min(py)
                far = all(0 < captured[0x8030+i] < 128 for i in vertices)
                sliver_keep = width >= 6 if height <= 3 else width >= 4 or height >= 6
                assert far or sliver_keep
                result.update(loaded_projected_xy=list(zip(px,py)),spanw=width,spanh=height,
                              far_depth_skip_sliver=far,sliver_retains=sliver_keep)
            face_results.append(result)
        frame_spans = [row for row in spans if row['frame'] == name]
        by_ancestor = {}
        for row in frame_spans:
            node = nodes[row['node']]
            while node['name'] != 'draw_face':
                assert node['parent'] is not None
                node = nodes[node['parent']]
            by_ancestor.setdefault(node['index'],[]).append(row)
        assert set(by_ancestor) == {n['index'] for n in nodes if n['name'] == 'draw_face'}
        frame_groups = []
        for node_index,rows in by_ancestor.items():
            node = nodes[node_index]
            latch = {bytes.fromhex(row['zero_page_dump'])[1] for row in rows}
            collector = {bytes.fromhex(row['zero_page_dump'])[2] for row in rows}
            assert len(latch) == 1 and collector == {8}
            face_id = next(iter(latch))
            assert 0 <= face_id < 8
            assert all(a['index']+1 == b['index'] for a,b in zip(rows,rows[1:]))
            todo,subtree = [node_index],[]
            while todo:
                current = nodes[todo.pop()]
                subtree.append(current)
                todo.extend(current['children'])
            costs = Counter()
            for current in subtree:
                costs[current['name']] += current['exclusive_cycles']
            assert sum(costs.values()) == node['inclusive_cycles']
            group = dict(frame=name,face=face_id,draw_face_node=node_index,
                first_span_index=rows[0]['index'],first_span_clock=rows[0]['clock'],last_span_index=rows[-1]['index'],
                spans=len(rows),logical_pixel_visits=sum(r['extent']+1 for r in rows),
                span_width_min=min(r['extent']+1 for r in rows),span_width_max=max(r['extent']+1 for r in rows),
                start_clock=node['start'],end_clock=node['end'],observed_draw_subtree_cycles=node['inclusive_cycles'],
                observed_frame_cycle_share=node['inclusive_cycles']/frame_profile['render_elapsed_cycles'],
                exclusive_subtree_costs=dict(costs),collector_faceidx_value=8)
            groups.append(group)
            frame_groups.append(group)
        observed = [g['face'] for g in frame_groups]
        modeled = [f['face'] for f in face_results if f['conservative_area_accepts']]
        assert len(observed) == len(set(observed)) and set(observed) == set(modeled)
        frames.append(dict(frame=name,captured_complete=artifact(complete),rotated_rx=rx,rotated_ry=ry,
            raw_projected_workspace=dict(sx=sx,sy=sy,syQ2=syq2,projdone=projdone,depth=depth),
            faces=face_results,modeled_area_accepted_ids=modeled,observed_draw_order=observed,
            observed_span_group_counts=[g['spans'] for g in frame_groups]))
    assert used_products == 48
    assert [f['observed_draw_order'] for f in frames] == [[3,2,1,0],[1,2,0,3],[1,7,2,0,3]]
    extra = next(g for g in groups if g['frame'] == 'third' and g['face'] == 7)
    assert (extra['spans'],extra['logical_pixel_visits'],extra['observed_draw_subtree_cycles']) == (45,203,90751)
    assert frames[2]['faces'][7]['signed_cross'] == -17
    report = dict(pass_=True,scope='Pinned source/data culling reconstruction and attribution of already observed elapsed draw subtrees; no independent projection, geometry visibility theorem, pixel omission proof or measured optimization',
        inputs=inputs,case_sha256=CASE_SHA,flags=flags,code_guards=guards,source_references=source_refs,
        multiplier=dict(entry=mul_start,end=mul_end,code_sha256=sha(bytes(ram0[mul_start:mul_end])),
                        independently_bound_quarter_square_bytes=512,captured_operand_products_checked=used_products,
                        formula='sign * (floor((abs(a)+abs(b))^2/4)-floor(abs(abs(a)-abs(b))^2/4)), sumindex<256'),
        frames=frames,group_costs=groups,third_face7=extra,
        interpretations=[
            'Actual culling uses rxbuf and negated rybuf before perspective projection; the -32 tolerance is not a projected-pixel-area threshold.',
            'Nonnegative cross, including zero, is accepted. MIN_FACE_AREA10 is bypassed by the conservative path; the optional -96 clipped-quad branch is compiled out here.',
            'Screen bounds are computed from captured sx and rounded syQ2. The direct XYQ2 profile bypasses integer SCREEN_MIN_SPAN rejection but retains the conservative sliver filter.',
            'Third face7 cross=-17 lies inside the actual -32 tolerance. It passes safe depth and sliver checks, explaining submission under this policy, not proving physical visibility.',
            'Frame1/2 unprojected workspace entries may be stale. Screen-space reasoning here uses only area-accepted faces whose three projdone entries are1.',
            'Face IDs come from source-latched0C in each actual span ABI. Collector0D is8 and is not a draw ID.',
            'Observed draw subtree starts at9223 and ends at actual4030 continuation, including bounds, shade edges, row setup, span stores and material spans. Its initiating JSR, prior face load/material/reflectivity, collection and buckets lie outside it.',
            'The 90751-cycle third-face7 subtree is an observed cost, not a speedup. Removing it can change setup, projection/bucket work, VIC phase and IRQ incidence; no native candidate was run.',
            'Integer policy reconstruction agrees with observed submitted ID sets for these three captured poses only. No full-rotation or culling-correctness claim.',
        ])
    output.mkdir(parents=True,exist_ok=False)
    raw = (json.dumps(report,indent=2,sort_keys=True)+'\n').encode()
    (output/'cull-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=True,bytes=len(raw),sha256=sha(raw),group_count=len(groups),third_face7=extra),sort_keys=True))


if __name__ == '__main__':
    main()
