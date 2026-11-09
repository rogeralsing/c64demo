#!/usr/bin/env python3
"""Bounded source-generation/localization models; no CPU or emulator execution."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-20261109/part-analysis'
PROFILE = BASE / 'capture-profile-01.json'
PROFILE_SHA = '78190eee4afff50a5d8c85248524c30ed05929a6a4d50f68f1617b2f128bc9e0'
PINS = {
    'research/tower-power/static_loader.py': '21da904962fa53ab7fa3c72caf0bc5a21fa4eb0a94f2be6155ef06a6994b4ce4',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'research/eod/controller.py': '033bafb6ac6e97283175ac6713af0eef60cb7991b653ee1c98c47a1a4afa83c9',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def meta(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha(raw)}


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def guard(memory, pc, code):
    raw = bytes.fromhex(code)
    assert memory[pc:pc + len(raw)] == raw, hex(pc)


def predict_relocation(source):
    """Source-bound31 full pages plus254-byte tail; not an instruction interpreter."""
    assert len(source) == 65536
    return source[0x6000:0x7ffe]


def predict_screens(source):
    """836E: eleven40-column windows into genuine52-column source rows."""
    records = []
    for shift in range(11):
        target = source[0x83cc + shift] | source[0x83d7 + shift] << 8
        data = bytes(source[0x9000 + row * 52 + shift + column]
                     for row in range(25) for column in range(40))
        records.append((target, data))
    return records


def predict_text(source):
    """Four53-character streams: eight lookup rows plus a spacing row per glyph."""
    records = []
    for text, target in [(0x3db5, 0x9000), (0x3e21, 0xa000),
                         (0x3deb, 0xb000), (0x3e57, 0xc000)]:
        cursor, data = text, bytearray()
        while source[cursor] < 128:
            index = (source[cursor] << 3) & 255
            data.extend(source[0x8800 + source[0x8a00 + index + row]] for row in range(8))
            data.append(source[0x8800])
            cursor += 1
            assert cursor - text <= 256
        data.append(255)
        records.append((text, target, cursor - text, bytes(data)))
    return records


def predict_call_kernel(source):
    """F64E copies25-byte template at24-byte stride,25 times; last byte is RTS."""
    result = bytearray(601)
    for index in range(25):
        result[24 * index:24 * index + 25] = source[0xf817:0xf830]
    return bytes(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    out.relative_to(BASE.resolve())
    assert not out.exists(), 'fresh output required'
    assert sha(PROFILE.read_bytes()) == PROFILE_SHA
    for name, expected in PINS.items():
        assert sha((ROOT / name).read_bytes()) == expected, name
    decoder = load('aloft_part_static', 'research/tower-power/static_loader.py')
    reader = load('aloft_part_snapshot', 'research/quondam/snapshot_state.py')
    profile = json.loads(PROFILE.read_text())
    assert len(profile['captures']) == 21
    memories, captures = {}, []
    inputs = [meta(PROFILE)] + [meta(ROOT / name) for name in PINS]
    for item in profile['captures']:
        stem = item['stem']
        rawpath, vsfpath = ROOT / item['ram']['path'], ROOT / item['snapshot']['path']
        assert meta(rawpath) == item['ram'] and meta(vsfpath) == item['snapshot']
        raw = rawpath.read_bytes()
        state = reader.read_snapshot(vsfpath)
        cpu = reader.module_payload(vsfpath, 'MAINCPU')
        mem = reader.module_payload(vsfpath, 'C64MEM')
        assert state['modules']['MAINCPU']['version'] == [1, 4] and len(cpu) == 103
        assert state['modules']['C64MEM']['version'] == [0, 1] and len(mem) == 65555
        assert len(raw) == 65536 and raw == mem[4:65540]
        pc, clock = int.from_bytes(cpu[12:14], 'little'), int.from_bytes(cpu[:8], 'little')
        assert (pc, clock) == (item['pc'], item['clock'])
        beam = [state['vicii']['raster_line'], state['vicii']['raster_cycle']]
        assert beam == [clock // 63 % 312, clock % 63]
        assert mem[1] == mem[65542] == 0x2f
        assert mem[0] & mem[1] == mem[65541] & mem[1]
        guard(raw, 0x0809, 'ee8d084c1c02')
        guard(raw, 0x080f, '8d8d084c9c01')
        captures.append({'stem': stem, 'ram': item['ram'], 'snapshot': item['snapshot'],
            'pc': pc, 'clock': clock, 'sp': cpu[11], 'beam': beam,
            'counter_088D': raw[0x088d], 'clock_increment_ZP_operands': [raw[0x0801], raw[0x0805]],
            'ports': {'latch': mem[0], 'DDR': mem[1], 'data_read': mem[65541]},
            'all65536_RAM_bytes_equal_snapshot': True,
            'full_wire_boot_checkpoint_custody': 'Delegated to the root-owned native-case producer; not audited here.'})
        memories[stem] = raw
        inputs += [item['ram'], item['snapshot']]

    p1, p2, p5, p6, p7, p8 = [memories[f'part{i:02d}-entry'] for i in [1, 2, 5, 6, 7, 8]]
    for index, counter in [(1, 0x14), (2, 0x15), (3, 0x16), (4, 0x17),
                           (5, 0x18), (6, 0x19), (7, 0x1d), (8, 0x1f), (9, 0x21)]:
        assert memories[f'part{index:02d}-entry'][0x088d] == counter
    assert memories['part06-precopy'][0x088d] == 0x1c
    guard(p1, 0x0890, '20002c20302ca90848a98f484c0908')
    guard(p2, 0x0890, 'a90f2c20d0d0fb2009082000662009082000e0')
    guard(p5, 0x0890, 'a20f8a4a4bfe69f2dd0030d005ca10f230032000e0')
    guard(p6, 0x0890, '200048200908e611200908e611a512f0fc200908')
    guard(p6, 0x08a4, 'a01fa200bd00609d00e0e8d0f7eeaa08eead0888d0eea2febdff7e9dfffecad0f7')
    guard(p6, 0x08cb, 'a900a020a2009d0060e8d0faeed30888d0f4')
    guard(p7, 0x0890, 'a9008dfe082000802c11d010fba5fec902a5ffe91590f1201780200020')
    guard(p8, 0x0890, '2000f0a5fac9c2a5fbe91690f6202bf0')
    assert memories['part02-entry'][0xe000:0xe020] == bytes(32)
    guard(memories['part04-entry'], 0xe000, 'a00cab009d00209d00219d8021e8d0f4')
    expected_table = bytes(0xf2 + (index // 4) for index in range(16))
    assert p5[0x3000:0x3010] == expected_table

    # Predictions are completed from earlier source/input generations before target comparisons.
    pre = memories['part06-precopy']
    moved = predict_relocation(pre)
    screens = predict_screens(p7)
    texts = predict_text(p7)
    call_kernel = predict_call_kernel(p8)
    assert len(moved) == 8190 and len(screens) == 11
    assert all(len(data) == 1000 for target, data in screens)
    assert all(chars == 53 and len(data) == 478 for text, target, chars, data in texts)
    assert p8[0xf817:0xf830] == bytes.fromhex('200020' * 7 + '20232060')
    guard(p8, 0xf64e, 'a9008510a9058511a218a018b917f891108810f8a918206bf6ca10ee60')
    post, cleared = memories['part06-postcopy'], memories['part06-afterclear']
    assert moved == post[0xe000:0xfffe] == cleared[0xe000:0xfffe]
    assert pre[0x6000:0x7ffe] == post[0x6000:0x7ffe]
    assert pre[0xfffe:] == post[0xfffe:]
    assert cleared[0x6000:0x8000] == bytes(8192)
    armed, generated = memories['part07-armed'], memories['part07-generated']
    for target, data in screens:
        assert data == armed[target:target + len(data)], hex(target)
    for text, target, chars, data in texts:
        assert data == generated[target:target + len(data)], hex(target)
    assert call_kernel == memories['part08-body'][0x0500:0x0759]
    assert [memories['part08-body'][0x0801], memories['part08-body'][0x0805]] == [0xfa, 0xfb]
    assert [p8[0x0801], p8[0x0805]] == [0xfe, 0xff]

    routes = [
        {'part': '01', 'counter': 0x14, 'classification': '2C00 init and2C30 IRQ arming; sprite pointer/position and raster-color routes, not a proven target-scene identity.'},
        {'part': '02-04', 'counters': [0x15, 0x16, 0x17], 'classification': 'Changed0890 wrapper waits onD020, loads then6600, loads thenE000. E000 iszero before its own load; generations stay separate.'},
        {'part': '05', 'counter': 0x18, 'classification': '3000 table guard may skip E000 init; FE/FF threshold0DFA thenE021. E149 IRQ jumps into generated0590. No full engine reconstruction.'},
        {'part': '06', 'counters': [0x19, 0x1c], 'classification': '4800 renderer setup; threeLoadNext calls and11/12/13 handshakes;8190-byte relocation and later8192-byte source clear. Renderer mechanism belongs to separate lane.'},
        {'part': '07', 'counter': 0x1d, 'classification': '8000 copies11 background screens before2000 text expansion overwrites9000. 8017 configures paired hi-res Y-expanded sprites and IRQ chain. Scene label remains separate from this source analysis.'},
        {'part': '08', 'counter': 0x1f, 'classification': 'F000 redirects clock increment operands toFA/FB. F02B installsF080 IRQ; F080 calls generated0500.25 groups of8 calls select generated2000/2023 cell variants. Vertical ribbon image association is owner observation; no complete image/timing proof.'},
        {'part': '09', 'counter': 0x21, 'classification': 'Wrapper/source pin only; no renderer analysis in this lane.'},
    ]
    source_sites = {'part01-entry': [0x0800, 0x0809, 0x080f, 0x0890, 0x0893, 0x2c00, 0x2c30, 0x2c89, 0x2e21],
        'part02-entry': [0x0890, 0x0892, 0x0897, 0x089a, 0x089d, 0x08a0],
        'part05-entry': [0x0890, 0x0894, 0x0898, 0x08a2, 0x08aa, 0x08b4],
        'part06-entry': [0x0890, 0x0893, 0x0898, 0x089d, 0x08a1, 0x08a4, 0x08a8, 0x08bc, 0x08c5, 0x08cb, 0x08dd],
        'part07-entry': [0x0895, 0x08a7, 0x08aa, 0x08ad, 0x8000, 0x8017, 0x8057, 0x805c, 0x8061, 0x80a5, 0x80bc, 0x816e, 0x81cf, 0x8239, 0x828e, 0x82c6, 0x836e, 0x2000, 0x2018, 0x206f, 0x20c6, 0x211d],
        'part08-entry': [0x0890, 0x0893, 0x089d, 0x08ae, 0xf000, 0xf012, 0xf017, 0xf02b, 0xf080, 0xf0ae, 0xf43d, 0xf47c, 0xf64e],
        'part09-entry': [0x0890]}
    listings = {stem: [decoder.decode(memories[stem], pc) for pc in sites] for stem, sites in source_sites.items()}
    out.mkdir(parents=True)
    files = [out / 'part_localization.checked.py', out / 'part06-relocated-8190.bin',
             out / 'part07-predicted-screens-11000.bin', out / 'part07-predicted-text-1912.bin',
             out / 'part08-predicted-kernel-601.bin', out / 'source-sites.json']
    for path, data in zip(files[:5], [Path(__file__).read_bytes(), moved,
            b''.join(data for target, data in screens), b''.join(data for text, target, chars, data in texts), call_kernel]):
        path.write_bytes(data)
    files[5].write_text(json.dumps(listings, indent=2) + '\n')
    proof = {'pass_': True, 'scope': 'Finite native-observed source generations, wrapper localization and pure copy/table/template models. No CPU execution or complete native custody audit.',
        'producer': meta(Path(__file__).resolve()), 'inputs': inputs, 'captures': captures,
        'routes': routes, 'source_sites': {'name': files[5].name,
            'bytes': files[5].stat().st_size, 'sha256': sha(files[5].read_bytes())},
        'part06_relocation': {'source': [0x6000, 0x7ffe], 'destination': [0xe000, 0xfffe], 'bytes': 8190,
            'full_pages': 31, 'tail_bytes': 254, 'all_bytes_equal': True, 'FFFE_FFFF_preserved': True,
            'later_source_clear': [0x6000, 0x8000], 'all8192_zero': True, 'relocated_bytes_unchanged_after_clear': True},
        'part07_screens': [{'target': target, 'bytes': len(data), 'sha256': sha(data), 'all_equal_armed': True}
                            for target, data in screens],
        'part07_text': [{'source_text': text, 'target': target, 'characters': chars, 'bytes': len(data),
                         'sha256': sha(data), 'all_equal_generated': True} for text, target, chars, data in texts],
        'part08_generated_calls': {'first': 0x0500, 'bytes': 601, 'generator': 0xf64e, 'template': [0xf817, 0xf830],
            'copies': 25, 'stride': 24, 'calls': 200, 'normal_target': 0x2000, 'row_end_target': 0x2023,
            'all601_bytes_equal_body': True, 'clock_operands_redirected': [0xfa, 0xfb]},
        'limits': ['Inputs are pinned observed RAM/VSF source generations, not independent original stream decompression.',
                   'Snapshot/RAM/CPU/beam are decoded, but full wire/boot/checkpoint custody is delegated to the separate root producer.',
                   'All copy/screen/text/kernel predictions precede target comparisons; target bytes never seed those models.',
                   'No complete renderer execution, store trace, image composition, timing or FPS claim.',
                   'No named three-layer-pattern association established by these part numbers or source similarities.'],
        'outputs': [{'name': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())} for path in files]}
    receipt = out / 'part-localization-proof.json'
    receipt.write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps({'pass_': True, 'captures': len(captures), 'receipt': meta(receipt)}))


if __name__ == '__main__':
    main()
