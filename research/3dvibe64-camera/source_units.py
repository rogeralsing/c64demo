#!/usr/bin/env python3
"""Passively bind camera geometry units/signs to the unchanged linked product."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT/'build/research/3dvibe64-native'
PROFILE = ROOT/'build/research/3dvibe64-profile'
PINS = {
    'build/research/3dvibe64-native/build-01/products/3Dvibe64.asm': '22008b3a92b7896c699543b12f9036704797262aa3558cd9116d8a09c85b796f',
    'build/research/3dvibe64-native/build-01/products/3Dvibe64.prg': '69b0d86f79106b2bf9654d85bd631bc68c12f4efd708454a0048560b3c1bfdeb',
    'build/research/3dvibe64-native/symbols-01/3Dvibe64.labels': '265a1770fe7a605139f0cdfd9d2983f6ddb314a1cf234a6f3a14d6f3b344e847',
    'research/3dvibe64-native/scene.json': '2dc0c5d4a8bab84ae522a31da6b7e998e346cce1dd0ffe6693ab01990ca6f72a',
    'build/research/3dvibe64/source/work/build-3Dvibe64.ps1': 'b03d5d7ce6e9e5af85d47c04950841da96f1f3e6dc7b50f5c26a1f97c5bb7e70',
    'build/research/3dvibe64-profile/native-01-pin.json': '35abf1d4b0f02aad49e08cb38337b80be108bc60fa315161b573490331d6a246',
    'build/research/3dvibe64-profile/profile-analysis/accepted-02/profile-proof.json': 'ebf994a2f7ed0a211cf98a2a112ea2d2b055de04a493484d238717736c42942a',
}
CASE_SHA = '13bfd23f30bf0b7a2db7a9e8dc4ceb8dc69e77d81c76862fe9b372a1f23ef714'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)),bytes=len(raw),sha256=sha(raw))


def s8(n):
    return n if n < 128 else n-256


def s16(n):
    return n if n < 32768 else n-65536


def sub(a,b):
    return [x-y for x,y in zip(a,b)]


def cross(a,b):
    return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]


def dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'build/research/3dvibe64-camera/source-analysis')
    args = parser.parse_args()
    output = args.output.resolve()
    inputs = []
    for relative,pin in PINS.items():
        item = artifact(ROOT/relative)
        assert item['sha256'] == pin,relative
        inputs.append(item)
    asm = (BUILD/'build-01/products/3Dvibe64.asm').read_text()
    labels = {n:int(v,16) for v,n in re.findall(r'(?m)^al ([0-9a-f]+) \.([^\s]+)$',
                                                (BUILD/'symbols-01/3Dvibe64.labels').read_text())}
    prg = (BUILD/'build-01/products/3Dvibe64.prg').read_bytes()
    load = int.from_bytes(prg[:2],'little')
    memory = bytearray(65536)
    memory[load:load+len(prg)-2] = prg[2:]
    scene = json.loads((ROOT/'research/3dvibe64-native/scene.json').read_text())
    obj = scene['objects'][0]
    assert scene['axisConvention'] == 'engine-y-up'
    assert scene['camera']['position'] == scene['camera']['rotation'] == [0,0,0]
    assert obj['position'] == [0,0,128] and obj['scale'] == 1

    def const(name):
        values = re.findall(r'(?m)^'+re.escape(name)+r' = (\$[0-9a-fA-F]+|\d+)\s*(?:;[^\n]*)?$',asm)
        assert values and len(set(values)) == 1,name
        return int(values[0][1:],16) if values[0].startswith('$') else int(values[0])

    expected = dict(CAMERA_HAS_POS=0,CAMERA_HAS_ROT=0,CAMERA_MOVABLE=0,
        CAMERA_POS_X=0,CAMERA_POS_Y=0,CAMERA_POS_Z=0,SCENE_OBJECT_X_ACTIVE=0,
        SCENE_OBJECT_Y_ACTIVE=0,SCENE_OBJECT_SCALE_ACTIVE=0,SCENE_OBJECT_COUNT=1,
        MESH_SOURCE_SHARING_RUNTIME=0,MOTION_Z_START_FRAC=0,MOTION_Z_START_LO=0,
        MOTION_Z_START_HI=0,MOTION_Z_STEP_FRAC=0,MOTION_Z_STEP_LO=0,MOTION_Z_STEP_HI=0,
        PROJ_VIEW_DEPTH_BIAS=190,PROJ_VIEW_DEPTH_BIAS_HI=0,PROJ_FOCAL=170,
        PROJ_CAMERA_FACE_MIN_DEPTH=8,PROJ_CENTER_X=80,PROJ_CENTER_Y=50,
        REFERENCE_PROJECTION=0,EXTENDED_TABLE_PROJECTION=1,VERT_COUNT=6)
    flags = {name:const(name) for name in expected}
    assert flags == expected
    assert 'camera_depth_geometric_lo = sz' in asm and 'camera_depth_geometric_hi = szhi' in asm
    for name,address in dict(m00=0x56,motion_z_frac=0x76,motion_z_lo=0x77,motion_z_hi=0x7a,
                             obj_pos_x_cur=0x7c,obj_pos_y_cur=0x7d,obj_depth_lo=0x7e,
                             obj_scale_cur=0x7f,obj_depth_hi=0x80,obj_depth_frac=0x81).items():
        assert const(name) == address
    guards = []

    def guard(pc,expected_bytes):
        raw = bytes.fromhex(expected_bytes)
        assert bytes(memory[pc:pc+len(raw)]) == raw,hex(pc)
        guards.append(dict(pc=pc,bytes=raw.hex()))

    guard(0x0a61,'a6 7b bd 82 b4 85 65 a9 00 85 7c a9 00 85 7d bd 89 b4 85 81 bd 8a b4 85 7e bd 8b b4 85 80 a9 40')
    guard(0x13c4,'a5 3a 85 41 a9 00 85 42 a5 3a 10 04 a9 ff 85 42 18 a5 41 65 7e 85 41 a5 42 65 80 85 42 a5 35 99 36 80 a5 39 99 3c 80')
    guard(0x13eb,'18 a5 41 65 77 99 2a 80 a5 42 65 7a 90 02 a9 ff 99 30 80 a5 81 10 11')
    guard(0x1335,'a6 52 bd 2a 80 85 41 bd 30 80 85 42 4c 05 13')
    guard(0x1305,'a5 42 30 0e 18 a5 41 69 be 85 41 a5 42 69 00 85 42 60')
    guard(0x90a4,'20 35 13 a5 42 f0 09 c9 21 90 0e a9 01 85 3b 60 a5 41 aa bd 35 bb 85 3b 60 38 e9 01 0a 0a 0a 85 42 a5 41 4a 4a 4a 4a 4a 05 42 aa bd 35 bc 85 3b 60')
    guard(0x143e,'20 68 13 20 5c 14')
    guard(0x1413,'a9 00 99 42 80 c8 c4 62 f0 03 4c 6a 13 60')

    source = (ROOT/'build/research/3dvibe64/source/work/build-3Dvibe64.ps1').read_text()
    source_lines = source.splitlines()
    source_refs = []
    for text in ['$Mode4ProjectionMinDivisor = if ($Mode4LateNearRequested -or $Mode4CameraPlaneClipRequested) { 2 } else { 8 }',
                 '$cameraDepthGeometric = $projectionTableIndex - $ProjectionContract.ViewDepthProjectionIndexBias',
                 '$projectionTableIndexMidpoint = 256 + ($i * 32) + 16',
                 '$cameraDepthGeometricMidpoint = $projectionTableIndexMidpoint - $ProjectionContract.ViewDepthProjectionIndexBias',
                 '; PROJ_VIEW_DEPTH_BIAS is a projection-index origin only.  Camera geometry,']:
        indexes = [i+1 for i,line in enumerate(source_lines) if text in line]
        assert indexes
        source_refs.append(dict(builder_line=indexes[0],text=text))
    tables = []

    def table(name,values):
        raw = bytes(values)
        address = labels[name]
        assert bytes(memory[address:address+len(raw)]) == raw,name
        tables.append(dict(name=name,address=address,bytes=len(raw),sha256=sha(raw)))
        return raw

    # Exact rational nearest/even rounding matches Math.Round, with no host FP.
    scene_scales = table('scene_scale_tab',[max(18,min(255,round(Fraction(170*64,max(8,i-190))))) for i in range(256)])
    far_scales = table('scale_far_tab',[max(1,min(120,round(Fraction(170*64,256+32*i+16-190)))) for i in range(256)])
    table('projx',[max(0,min(159,80+s8(i))) for i in range(256)])
    table('projy',[max(0,min(99,50-s8(i))) for i in range(256)])
    quarters = [i*i//4 for i in range(256)]
    table('sqlo',[n&255 for n in quarters])
    table('sqhi',[n>>8 for n in quarters])
    coordinates = [list(map(s8,memory[labels[axis+'coord']:labels[axis+'coord']+3])) for axis in 'xyz']
    assert coordinates == [[-28,0,28]]*3
    indices = [list(memory[labels['vert_'+axis+'i']:labels['vert_'+axis+'i']+6]) for axis in 'xyz']
    local_vertices = [[coordinates[a][indices[a][i]] for a in range(3)] for i in range(6)]
    assert local_vertices == obj['vertices']
    faces = [[memory[labels['face'+str(c)]+f] for c in range(3)] for f in range(8)]
    assert faces == obj['faces']
    for face in faces:
        p0,p1,p2 = [local_vertices[i] for i in face]
        assert dot(cross(sub(p1,p0),sub(p2,p0)),p0) > 0  # Outward about local origin.
    pos = [memory[labels['object_pos_z_'+s]] for s in ('lo','hi','ext')]
    assert pos == [0,128,0] and Fraction(int.from_bytes(bytes(pos),'little'),256) == 128
    assert memory[labels['object_scale']] == 64

    manifest = json.loads((PROFILE/'native-01-pin.json').read_text())
    actual = [dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
              for p in sorted((PROFILE/'native-01').iterdir()) if p.is_file()]
    assert manifest['entries'] == actual
    assert sha(json.dumps(actual,sort_keys=True,separators=(',',':')).encode()) == manifest['case_sha256'] == CASE_SHA
    profile = json.loads((PROFILE/'profile-analysis/accepted-02/profile-proof.json').read_text())
    assert profile['pass_'] and profile['case_sha256'] == CASE_SHA
    frames,products,points_checked = [],0,0
    for name in ('first','second','third'):
        baseline_path = PROFILE/'native-01'/f'{name}-shades.bin'
        complete_path = PROFILE/'native-01'/f'{name}-complete.bin'
        baseline,completed = baseline_path.read_bytes(),complete_path.read_bytes()
        matrix = [s8(v) for v in baseline[0x56:0x5f]]
        term_bytes = baseline[0x8048:0x8063]
        assert completed[0x8048:0x8063] == term_bytes
        term_axes = []
        for axis in range(3):
            for out_axis in range(3):
                expected_terms = []
                for coordinate in coordinates[axis]:
                    coefficient = matrix[out_axis*3+axis]
                    assert abs(coordinate)+abs(coefficient) < 256
                    magnitude = quarters[abs(coordinate)+abs(coefficient)]-quarters[abs(abs(coordinate)-abs(coefficient))]
                    assert magnitude == abs(coordinate*coefficient)
                    value = magnitude//64
                    if (coordinate<0) != (coefficient<0):
                        value = -value
                    expected_terms.append(value)
                    products += 1
                offset = (axis*3+out_axis)*3
                assert bytes(v&255 for v in expected_terms) == term_bytes[offset:offset+3]
                term_axes.append(expected_terms)
        assert baseline[0x7c:0x82] == completed[0x7c:0x82] == bytes.fromhex('00 00 80 40 00 00')
        assert all(completed[a] == 0 for a in (0x76,0x77,0x7a))
        vertices,lookup = [],[]
        for vertex in range(6):
            rotated = [s8(sum(term_axes[axis*3+out_axis][indices[axis][vertex]] for axis in range(3))&255)
                       for out_axis in range(3)]
            depth = s16(completed[0x802a+vertex]+256*completed[0x8030+vertex])
            assert s8(completed[0x8036+vertex]) == rotated[0]
            assert s8(completed[0x803c+vertex]) == rotated[1]
            assert depth == rotated[2]+128
            vertices.append([rotated[0],rotated[1],depth])
            index = depth+190
            assert 256 <= index < 8448
            slot = (index-256)//32
            assert 0 <= slot < 256
            lookup.append(dict(vertex=vertex,geometric_depth=depth,physical_index=index,far_slot=slot,
                               geometric_bucket_midpoint=256+32*slot+16-190,scaleQ6=far_scales[slot],
                               actual_projdone=completed[0x8042+vertex]))
            points_checked += 1
        center = [sum(p[a] for p in vertices)//6 for a in range(3)]
        assert center == [0,0,128] and all(vertices[i][a]+vertices[j][a] == 2*center[a]
                                          for i,j in ((0,1),(2,3),(4,5)) for a in range(3))
        winding = []
        for face_id,face in enumerate(faces):
            p0,p1,p2 = [vertices[i] for i in face]
            normal = cross(sub(p1,p0),sub(p2,p0))
            outward = dot(normal,sub(p0,center))
            assert outward > 0
            eye_dot = dot(normal,[-v for v in p0])
            winding.append(dict(face=face_id,normal=normal,outward_dot_about_center=outward,
                                eye_minus_P_dot=eye_dot,strict_positive_plane_side=eye_dot>0))
        frames.append(dict(frame=name,baseline=artifact(baseline_path),complete=artifact(complete_path),
                           baseline_matrix_Q6=matrix,completed_matrix_bytes=list(completed[0x56:0x5f]),
                           completed_matrix_differs=baseline[0x56:0x5f] != completed[0x56:0x5f],
                           verified_coordinate_product_bytes=term_bytes.hex(),camera_vertices=vertices,
                           center=center,projection_lookup_if_requested=lookup,winding=winding))
    assert products == 81 and points_checked == 18
    report = dict(pass_=True,scope='Exact units/signs of this pinned fixed-camera product and three captured quantized vertex clouds; not independent projection, ideal continuous geometry, full-rotation classification or a new renderer',
        inputs=inputs,case_sha256=CASE_SHA,flags=flags,code_guards=guards,builder_source_references=source_refs,
        independently_bound_tables=tables,coordinate_products_checked=products,camera_vertices_checked=points_checked,
        scene_object_position_16_8_bytes=pos,frames=frames,
        unit_contract=dict(eye=[0,0,0],camera_vertex='(signed8 rxbuf, signed8 rybuf, signed16(sz|szhi<<8))',
            units='One integer geometric/world unit per stored integer; matrix coefficients use64 for1, not vertices.',
            Y='positive is up; linked projy maps50-signed_offset',Z='positive depth is away from the eye',
            object_translation='Z128 already included in depth; X/Y0 compiled out; no camera translation/rotation',
            projection_bias='190 changes only table index; table construction subtracts190 from its divisor',
            winding='N=(P1-P0) cross(P2-P0) is outward for the authored face order and all24 captured triangles',
            facing_sign='N dot(E-P0)>0 is the eye-facing side; reversing winding or reflectingY reverses the sign'),
        capture_plan=dict(pre_rotation=0x1368,after_rotation_before_collection=0x1441,
            completed_rotation_RTS=0x1420,caller_JSR=0x143e,
            compact_reads=['m 802a 8062','m 0056 0081'],
            guard='At1441 all six rotated/depth vertices are ready and projdone was reset. Prefer paired fullRAM/VSF. Snapshot08D4 matrix bytes are partly clobbered; use1153or1441 for matrix.'),
        limitations=[
            'Signed/unsigned overflow, saturating X/Y translation, fractional Z rounding and moving/rotated cameras are not exercised by these captures. Do not generalize the simplified P tuple to other profiles without inspecting their flags.',
            'Runtime local rotations are separately truncated Q6 coordinate products summed as bytes. They need not equal an ideal rigid rotation; actual stored vertices are the classifier inputs.',
            'Captured object Z fractional byte and motion depth are zero. This profile rounds object fraction>=128 upward, but no fractional geometry precision survives in sz/szhi.',
            'All81 coordinate terms match the baseline matrix and persist through completion; the completed matrix itself differs in every sample and is not valid reconstruction input.',
            'Lookup table values approximate perspective using32-index far buckets and clamps. This proves the190 origin compensation, not exact unquantized perspective.',
            'Projection lookups are derived if requested for all18 vertices. Actualprojdone0 denotes an unprojected/stale screen entry; sx/sy never enters this geometry proof.',
            'The source-backed plane-side sign is distinct from the conservative screen-style cross test. This audit makes no pixel-omission or new-policy benchmark claim.',
        ])
    output.mkdir(parents=True,exist_ok=False)
    raw = (json.dumps(report,indent=2,sort_keys=True)+'\n').encode()
    (output/'units-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=True,bytes=len(raw),sha256=sha(raw),products=products,vertices=points_checked,
                          plane_side_sets={f['frame']:[r['face'] for r in f['winding'] if r['strict_positive_plane_side']] for f in frames}),sort_keys=True))


if __name__ == '__main__':
    main()
