#!/usr/bin/env python3
"""Bind root-owned completed build products, without running any build/native tool."""
import hashlib
import json
import re
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/3dvibe64-native'
OUT = BASE / 'build-analysis'
PINS = {
    'build-01/products/3Dvibe64.asm': '22008b3a92b7896c699543b12f9036704797262aa3558cd9116d8a09c85b796f',
    'build-01/products/3Dvibe64.prg': '69b0d86f79106b2bf9654d85bd631bc68c12f4efd708454a0048560b3c1bfdeb',
    'build-01/command.json': '1bc228ddc3a8300bc652f25940f4d0266067c5f83906a5cfc2c1c9265fee463c',
    'build-01/result.json': '303512ac2300e69cd0d06066464a00286b06fc665d756c547a956a13353a233d',
    'build-01/stdout.bin': '3e03ff5d2051b62432e42ff089befefb8cfae2786d1d39afc8f364e56713fe4c',
    'build-01/stderr.bin': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    'build-01/sdk-delta.json': 'e206c86915a19ea5f24ca3f417368e4162a49c356458163d87d623be98dc052a',
    'sdk-before.json': '8ffa73f2a81a49b4459fb67c6b270add873233bc087b7b743c564d2a2c143da7',
    'symbols-01/command.json': '75a60ca5324ea2eb7cf2e8a86cad3027df1a9adfae00fb8a2f18713147d16736',
    'symbols-01/result.json': 'e44d21b2c54da08bdfa8856d442ba4e9b414a80676e9dca462c26dcac6f596d8',
    'symbols-01/stdout.bin': 'a5f63de81153bdec6d68364a1cf67b3b09a3dab4641549d328f708590d1e3124',
    'symbols-01/stderr.bin': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    'symbols-01/3Dvibe64.labels': '265a1770fe7a605139f0cdfd9d2983f6ddb314a1cf234a6f3a14d6f3b344e847',
    'symbols-01/3Dvibe64.prg': '69b0d86f79106b2bf9654d85bd631bc68c12f4efd708454a0048560b3c1bfdeb',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path, pin=None):
    data = path.read_bytes()
    if pin:
        assert sha(data) == pin, path
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=sha(data))


def source_custody():
    archive = ROOT / 'build/research/3dvibe64/upstream.tar.gz'
    pin = artifact(archive, 'fbccc522110b1fe4beb85ba1378183f70b5d8fc76227c2482306cd5354b4c998')
    before = json.loads((BASE / 'sdk-before.json').read_text())
    delta = json.loads((BASE / 'build-01/sdk-delta.json').read_text())
    assert not delta['changed'] and not delta['removed']
    assert set(delta['added']) == {'work/3Dvibe64.asm', 'work/3Dvibe64.prg', 'work/build/3Dvibe64.prg'}
    with tarfile.open(archive) as tar:
        prefix = '3Dvibe64-b19df459b7efe50d514b59fe876c0bc7c326c5b4/'
        originals = {m.name[len(prefix):]: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
    assert len(before) == len(originals) == 387
    for row in before:
        data = originals[row['name']]
        assert row['bytes'] == len(data) and row['sha256'] == sha(data)
    after = {row['name']: row for row in delta['after']}
    assert all(after[row['name']] == row for row in before)
    assert len(after) == 390
    assert sha(originals['work/build-3Dvibe64.ps1']) == 'b03d5d7ce6e9e5af85d47c04950841da96f1f3e6dc7b50f5c26a1f97c5bb7e70'
    return dict(archive=pin, original_files_compared=387, modified_or_removed_originals=0,
                added_files=delta['added'], source_builder_sha256=sha(originals['work/build-3Dvibe64.ps1']))


def main():
    inputs = [artifact(BASE / name, pin) for name, pin in PINS.items()]
    scene_path = ROOT / 'research/3dvibe64-native/scene.json'
    inputs.append(artifact(scene_path, '2dc0c5d4a8bab84ae522a31da6b7e998e346cce1dd0ffe6693ab01990ca6f72a'))
    custody = source_custody()
    for step in ('build-01', 'symbols-01'):
        command = json.loads((BASE / step / 'command.json').read_text())
        result = json.loads((BASE / step / 'result.json').read_text())
        assert result['exit_code'] == 0 and not result['shell'] and result['command'] == command['command']
        for stream in ('stdout', 'stderr'):
            raw = (BASE / step / (stream + '.bin')).read_bytes()
            assert result[stream] == dict(bytes=len(raw), sha256=sha(raw))
    asm = (BASE / 'build-01/products/3Dvibe64.asm').read_text()
    prg = (BASE / 'build-01/products/3Dvibe64.prg').read_bytes()
    assert prg == (BASE / 'symbols-01/3Dvibe64.prg').read_bytes()
    labels = {name: int(value, 16) for value, name in re.findall(
        r'(?m)^al ([0-9a-f]+) \.([^\s]+)$', (BASE / 'symbols-01/3Dvibe64.labels').read_text())}
    assert len(labels) == 968
    load = int.from_bytes(prg[:2], 'little')
    end = load + len(prg) - 2
    assert (load, end, len(prg)) == (0x0801, 0xca2e, 49711)

    def memory(address, count):
        assert load <= address <= address + count <= end
        return prg[2 + address - load:2 + address - load + count]

    def const(name):
        matches = re.findall(r'(?m)^' + re.escape(name) + r' = (\$[0-9a-fA-F]+|\d+)\s*(?:;[^\n]*)?$', asm)
        assert matches and len(set(matches)) == 1, (name, matches)
        return int(matches[0][1:], 16) if matches[0].startswith('$') else int(matches[0])

    def source_bytes(name):
        match = re.search(r'(?m)^' + re.escape(name) + r':\s*\n((?: \.byte [^\n]+\n)+)', asm)
        assert match, name
        tokens = ','.join(line.strip()[6:] for line in match[1].splitlines()).split(',')
        assert all(re.fullmatch(r'\$[0-9a-fA-F]+|\d+', token) for token in tokens), name
        return bytes(int(token[1:], 16) if token.startswith('$') else int(token) for token in tokens)

    tables = []

    def table(name, expected):
        expected = bytes(expected)
        assert source_bytes(name) == expected, ('assembly table', name)
        address = labels[name]
        assert memory(address, len(expected)) == expected, ('PRG table', name)
        tables.append(dict(name=name, address=address, bytes=len(expected), sha256=sha(expected)))

    bayer = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5]
    packed = bytes(sum((1 + int(s > bayer[4*y+x]) + int(s > bayer[4*y+x] + 16)) << (6-2*x)
                       for x in range(4)) for y in range(4) for s in range(33))
    levels = bytes(min(32, (2*d*i + 7)//15) for i in range(11) for d in range(64))
    assert sha(packed) == '08fb32589e23f8fe20c88beff0b2dad16510ff21581c1442bf0467b3f7ee84a9'
    assert sha(levels) == '4f8ef9b43a3cde7bab67e55b2cbb61aa215ce6a2e08126bd4a23c1d1fe00b912'
    for y in range(4):
        table('gouraud_bayer_code_lut_y' + str(y), packed[y*33:(y+1)*33])
    for i in range(11):
        table('gouraud_level_' + str(i), levels[i*64:(i+1)*64])
    for base, count in [('gouraud_bayer_code_lut', 4), ('gouraud_level', 11)]:
        addresses = [labels[base + ('_y' if count == 4 else '_') + str(i)] for i in range(count)]
        for suffix, shift in [('lo', 0), ('hi', 8)]:
            name = ('gouraud_bayer_code_lut_row_' if count == 4 else 'gouraud_level_ptr_') + suffix
            # The assembly expressions are not evaluated; compare linked bytes
            # directly to independently resolved symbol addresses.
            assert memory(labels[name], count) == bytes((v >> shift) & 255 for v in addresses)

    scene = json.loads(scene_path.read_text())
    assert scene['schema'] == 1 and scene['graphicsMode'] == 6 and scene['axisConvention'] == 'engine-y-up'
    assert len(scene['objects']) == len(scene['lights']) == 1
    obj, light = scene['objects'][0], scene['lights'][0]
    vertices, faces = obj['vertices'], obj['faces']
    assert vertices == [[28,0,0],[-28,0,0],[0,28,0],[0,-28,0],[0,0,28],[0,0,-28]]
    assert obj['gouraud']['creaseAngle'] == 180 and obj['scale'] == 1
    order = list(dict.fromkeys(v for f in faces for v in f))
    assert order == [0,5,2,1,3,4]
    normal_by_geom = [[63 if v > 0 else -63 if v < 0 else 0 for v in xyz] for xyz in vertices]
    for axis in range(3):
        coords = sorted(set(xyz[axis] for xyz in vertices))
        table('xyz'[axis] + 'coord', [v & 255 for v in coords])
        table('vert_' + 'xyz'[axis] + 'i', [coords.index(v[axis]) for v in vertices])
        table('gouraud_normal_' + 'xyz'[axis], [normal_by_geom[g][axis] & 255 for g in order])
    table('gouraud_geom_vertex', order)
    centers = [sum(normal_by_geom[g][a] * (vertices[g][a]//2) for a in range(3)) for g in order]
    assert centers == [882] * 6
    table('gouraud_center_dot_lo', [n & 255 for n in centers])
    table('gouraud_center_dot_hi', [n >> 8 for n in centers])
    table('gouraud_shade_value', [255] * 6)
    for axis in range(3):
        table('face' + str(axis), [f[axis] for f in faces])
    table('face3', [0] * 8)  # Unused triangle corner, not a fourth vertex.
    table('face_vertex_count', [3] * 8)
    for corner in range(4):
        table('gouraud_face_shade' + str(corner), [order.index(f[min(corner,2)]) for f in faces])
    for axis in range(3):
        fixed = round(obj['position'][axis] * 256)
        for suffix, shift in [('lo',0),('hi',8)]:
            table('object_pos_' + 'xyz'[axis] + '_' + suffix, [(fixed >> shift) & 255])
        velocity = round(obj['angularVelocity'][axis] * 256)
        for suffix, shift in [('lo',0),('hi',8)]:
            table('object_angvel_' + 'xyz'[axis] + '_' + suffix, [(velocity >> shift) & 255])
        table('light_pos_' + 'xyz'[axis], [light['position'][axis] & 255])
    table('object_pos_z_ext', [0])
    table('object_scale', [64])
    table('light_intensity_table', [10])
    table('face_material', [0] * 8)
    table('face_reflect_offset', [10] * 8)
    assert memory(labels['material_screen_bytes'] + 10, 1) == b'\xbf'
    assert memory(labels['material_color_bytes'] + 10, 1) == b'\x01'

    flags = {name: const(name) for name in ['VERT_COUNT','FACE_COUNT','SHADE_VERT_COUNT','GOURAUD_MODE6',
        'CAMERA_MOVABLE','EXPLORER_SCREEN_RAW','EXPLORER_NEAR_POLY','EXPLORER_SCREEN_CLIP_POLY',
        'CAMERA_PLANE_CLIP_PROFILE','STANDARD_PROJECT_VERTEX','XCOORD_COUNT','YCOORD_COUNT','ZCOORD_COUNT',
        'VIEWPORT_ROW_CAPACITY','FPS_OVERLAY_ENABLE','FPS_COUNTER_ENABLE','VIDEO_STANDARD_FORCE_PAL']}
    assert [flags[n] for n in ['EXPLORER_SCREEN_RAW','EXPLORER_NEAR_POLY','EXPLORER_SCREEN_CLIP_POLY','CAMERA_PLANE_CLIP_PROFILE']] == [0]*4
    assert flags['STANDARD_PROJECT_VERTEX'] == 1 and flags['GOURAUD_MODE6'] == 1
    aliases = dict(sx=0x8000,sy=0x8006,syq2_lo=0x800c,syq2_hi=0x8012,sx_prev=0x8018,
                   sy_prev=0x801e,smooth_ready=0x8024,sz=0x802a,szhi=0x8030,rxbuf=0x8036,
                   rybuf=0x803c,projdone=0x8042,x_m00=0x8048,x_m10=0x804b,x_m20=0x804e,
                   y_m01=0x8051,y_m11=0x8054,y_m21=0x8057,z_m02=0x805a,z_m12=0x805d,z_m22=0x8060,
                   leftb=0x8063,rightb=0x80c7,leftshade=0x812b,rightshade=0x818f)
    assert const('RUNTIME_BUFFER_BASE') == aliases['sx']
    # Bounded hand-derived active alias chain; no general assembler evaluator.
    for name, expression in [('sy','sx + VERT_COUNT'),('syq2_lo','sy + VERT_COUNT'),
        ('syq2_hi','syq2_lo + VERT_COUNT'),('sx_prev','RUNTIME_AFTER_CLIP'),
        ('sz','RUNTIME_AFTER_SMOOTH'),('leftb','z_m22 + ZCOORD_COUNT'),
        ('rightb','leftb + VIEWPORT_ROW_CAPACITY'),('leftshade','rightb + VIEWPORT_ROW_CAPACITY'),
        ('rightshade','leftshade + VIEWPORT_ROW_CAPACITY')]:
        assert name + ' = ' + expression in asm
    assert memory(labels['gfb_row'], 9) == b'\xbd\x63\x80\x85\x29\xbd\xc7\x80\x85'
    zp = {name: const(name) for name in ['drawbuf','yrow','faceidx','objidx','face_ymin','face_ymax',
                                        'ptr0lo','ptr0hi','ptr1lo','ptr1hi','row0lo','row0hi','row1lo','row1hi',
                                        'sh_nx','sh_ny','sh_nz','leftval','rightval']}
    scan = [labels['gouraud_scan_' + name] for name in ['x','end','delta','dir','err','span','shade']]
    assert scan == list(range(0xb43b,0xb442))

    def word(n):
        return n.to_bytes(2,'little')

    code_guards = {}

    def code(label, expected):
        address = labels[label]
        assert memory(address,len(expected)) == expected, label
        code_guards[label] = dict(address=address, bytes=expected.hex())

    basic = re.search(b'\x9e([0-9]+)\x00', memory(load, 12))
    assert basic and int(basic[1]) == labels['start'] == 0x080d
    code('start', bytes.fromhex('78 d8 ad 02 dd 09 03 8d 02 dd a9 36 85 01'))
    code('render_frame_end', b'\x20'+word(labels['wait_raster'])+b'\x20'+word(labels['show_buffer'])+
         b'\x20'+word(labels['fps_frame_done'])+b'\x4c'+word(labels['main_loop']))
    code('show_buffer', bytes.fromhex('a5 0b 49 01 85 0b 60'))
    code('raster_irq', bytes.fromhex('a9 01 8d 19 d0 20')+word(labels['set_bitmap_body_mode']))
    code('sbb_show_a', bytes.fromhex('ad 00 dd 29 fc 09 02 8d 00 dd a9 78 8d 18 d0 60'))
    code('sbb_show_b', bytes.fromhex('ad 00 dd 29 fc 09 03 8d 00 dd a9 18 8d 18 d0 60'))
    assert memory(labels['wait_raster'],14) == bytes.fromhex('ad 12 d0 c9 fc d0 f9 ad 12 d0 c9 fc f0 f9')
    for phase, mask in enumerate((192,48,12,3)):
        code('gdsb_lut_phase'+str(phase),b'\xb9'+word(labels['gouraud_bayer_code_lut_y0'])+bytes([0x29,mask]))
    shade_code = memory(labels['gouraud_update_object_shades'],labels['gous_done']-labels['gouraud_update_object_shades'])
    for axis in 'xyz':
        assert b'\xb9'+word(labels['gouraud_normal_'+axis])+bytes([0xa6,zp['sh_n'+axis]]) in shade_code
    assert b'\xf9'+word(labels['gouraud_center_dot_hi']) in shade_code
    capture_names = ['start','main_loop','render_frame_begin','render_frame_end','show_buffer','raster_irq',
        'set_bitmap_body_mode','sbb_show_a','sbb_show_b','gouraud_update_object_shades','gous_done',
        'rotate_project_vertices','rso_next_object','gouraud_fill_bounds','gfb_row','gfb_next_restore',
        'gfb_done','gouraud_draw_scan_span_bytes','gdsb_pointer_init','gouraud_shade_value']
    captures = {name:labels[name] for name in capture_names}
    captures['irq_after_bitmap_body_call'] = labels['raster_irq'] + 8
    assert captures['irq_after_bitmap_body_call'] == 0x09b1
    segments = []
    stdout = (BASE / 'build-01/stdout.bin').read_text()
    for kind, count, first, last in re.findall(r'(?m)^(Data|Gap):\s+(\d+)\s+\$([0-9a-f]+)-\$([0-9a-f]+)',stdout):
        first,last,count=int(first,16),int(last,16),int(count)
        assert last-first+1==count
        if kind=='Gap':assert memory(first,count)==bytes(count)
        segments.append(dict(kind=kind,start=first,end_exclusive=last+1,bytes=count))
    assert sum(s['bytes'] for s in segments) == len(prg)-2
    assert 'runtimeEnd=849C runtimeMargin=2916' in stdout
    proof = dict(passive=True, inputs=inputs, source_custody=custody, full_build_exit_code=0,
        symbol_reassembly_identical=True, symbols=len(labels), load=load,end_exclusive=end,
        loaded_payload_bytes=len(prg)-2, segments=segments, tables=tables,
        Bayer_bytes_compared=132, light_level_bytes_compared=704, shade_geom_order=order,
        shade_normals=[normal_by_geom[g] for g in order], center_dot_terms=centers,
        scene_flags=flags, zero_page=zp, active_runtime_aliases=aliases, scan_state=scan,
        scan_arrays=dict(first=0x8063,last_inclusive=0x81f2,bytes=400,per_array=100),
        material=dict(bootstrap_screen=const('MATERIAL_SCREEN_BYTE'),bootstrap_color=const('MATERIAL_COLOR_RAM'),
                      face_gray_reflectivity1_screen=191,face_gray_reflectivity1_color=1),
        code_guards=code_guards,capture_anchors=captures,
        lifecycle=dict(initial_drawbuf=1,initial_draw_bitmap=0x2000,initial_front_bitmap=0x6000,
                       toggle_is_not_VIC_publication=True,publication='raster IRQ applies drawbuf to DD00/D018 before09B1',
                       front_B_committed_capture='After firstB publication09B1/drawbuf0, stop naturally at raster252; current completed visible rows51..250 precede nextlogicaltoggle at253'),
        limitations=['No build/assembler/PowerShell/native process run by this producer',
                     'Root-owned build receipts and selected byte checks; not an independent whole-program compiler proof',
                     'Runtime alias chain is bounded to these emitted flags, corroborated by indexed load bytes',
                     'Live Bayer operands self-modify by logical row; do not expect all runtime code bytes immutable',
                     'No dynamic shade, geometry, framebuffer, FPS or hardware claim from build bytes'])
    OUT.mkdir(parents=True,exist_ok=True)
    target=OUT/'build-proof.json'
    target.write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(proof=artifact(target),tables=len(tables),Bayer132=True,lighting704=True,
                          source_files387=True,PRG_reassembly_identical=True,native_execution=False),indent=2))


if __name__ == '__main__':
    main()
