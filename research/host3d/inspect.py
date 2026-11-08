#!/usr/bin/env python3
"""Passively decode a published HORS-V3 cartridge and its host-picture oracle.

Only data is read. No upstream Python, assembler, C64 CPU or emulator runs.
"""

import gzip
import hashlib
import json
from pathlib import Path
import re
import struct
import zlib

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/host3d'
INPUT = BASE / 'acquired'
SOURCE = INPUT / 'source'
OUT = BASE / 'analysis'
COMMIT = '079b6d8a907bea6242d94296701ad7aa9a11dc73'
INDEX_SHA = '9b53080d8512ddc60af5c4fe6e8dcaf8cb9b02a4ec840f904efcd0a44e66b238'
STEM = 'examples/stanford_dragon/cartridges/stanford_dragon-metallic-hors-v3'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=sha(data))


def inputs():
    index = INPUT / 'acquisition.json'
    assert sha(index.read_bytes()) == INDEX_SHA
    rows = json.loads(index.read_text())
    commit = json.loads((INPUT / 'commit.json').read_text())
    tree = json.loads((INPUT / 'tree.json').read_text())
    assert commit['sha'] == COMMIT and tree['sha'] == commit['commit']['tree']['sha']
    assert not tree['truncated']
    entries = {r['path']: r for r in tree['tree'] if r['type'] == 'blob'}
    records = []
    for row in rows:
        path = INPUT / row['name']
        data = path.read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256']
        assert row['status'] == 200
        record = dict(**artifact(path), url=row['url'])
        if row['name'].startswith('source/'):
            relative = row['name'][7:]
            git_blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            assert git_blob == entries[relative]['sha'] and len(data) == entries[relative]['size']
            assert row['url'] == f'https://raw.githubusercontent.com/FlyingFathead/c64-3d-toolkit/{COMMIT}/{relative}'
            record['git_blob_sha1'] = git_blob
        records.append(record)
    return dict(acquisition_index=artifact(index), commit=COMMIT,
                commit_utc=commit['commit']['committer']['date'], files=records)


def cartridge(data):
    assert data[:16] == b'C64 CARTRIDGE   '
    assert int.from_bytes(data[22:24], 'big') == 32  # EasyFlash hardware type.
    offset = int.from_bytes(data[16:20], 'big')
    chips = {}
    while offset < len(data):
        signature, length, chip_type, bank, address, size = struct.unpack('>4sI4H', data[offset:offset + 16])
        assert signature == b'CHIP' and chip_type == 2 and length == 16 + size and size == 8192
        assert address in (0x8000, 0xa000) and (bank, address) not in chips
        chips[bank, address] = data[offset + 16:offset + length]
        assert len(chips[bank, address]) == size
        offset += length
    assert offset == len(data)
    assert chips[0, 0xa000][0x5c:0x5e] == b'\xa2\x58'  # Published boot LDX #88 pages.
    ram = bytearray(65536)
    for bank in range(3):
        first, end = 0x800 + bank * 8192, min(0x800 + (bank + 1) * 8192, 0x6000)
        ram[first:end] = chips[bank, 0x8000][:end - first]
    assert chips[2, 0x8000][0x1800:] == bytes(0x800)  # Uncopied cartridge padding.
    return chips, ram


def logical_picture(frame, base_color):
    """Use prefix popcounts and absolute coordinates, not a replayed DDA loop."""
    bitmap = bytearray(7680)
    for record in frame['records']:
        low, high, count, control, *masks = record
        row, cell_bytes = divmod(low + 256 * high, 320)
        major_y, negative = bool(control & 64), bool(control & 128)
        x0, y0 = 8 * (cell_bytes // 8) + (control & 7), 8 * row + ((control >> 3) & 7)
        phase = (y0 if major_y else x0) & 7
        assert len(masks) == 1 + (phase + count - 1) // 8
        first_length = 8 - phase
        increments = []
        for transition in range(count - 1):
            byte, bit = ((0, transition) if transition < first_length else
                         (1 + (transition - first_length) // 8, (transition - first_length) % 8))
            increments.append((masks[byte] >> (7 - bit)) & 1)
        minor = 0
        for i in range(count):
            signed_minor = -minor if negative else minor
            x, y = (x0 + signed_minor, y0 + i) if major_y else (x0 + i, y0 + signed_minor)
            assert 0 <= x < 320 and 0 <= y < 192
            bitmap[(y // 8) * 320 + (x // 8) * 8 + y % 8] |= 128 >> (x % 8)
            if i < len(increments):
                minor += increments[i]
    colors = bytearray([base_color]) * 960
    for low, high, count, value in frame['color_spans']:
        start = low + 256 * high
        assert 0 <= start < start + count <= 960
        colors[start:start + count] = bytes([value]) * count
    assert sum(b.bit_count() for b in bitmap) == frame['unique_pixels']
    return bytes(bitmap + colors)


def clear_mask(block):
    count, mask, spans = block[0], bytearray(7680), []
    for i in range(count):
        low, high, length = block[1 + 3 * i:4 + 3 * i]
        first = low + ((high & 127) << 8)
        size = length * (1 if high & 128 else 8)
        assert 0 <= first < first + size <= 7680
        mask[first:first + size] = b'\1' * size
        spans.append([low, high, length])
    return 1 + count * 3, mask, spans


def decode(block, metadata, color_runs, base_color):
    position, clear, clear_spans = clear_mask(block)
    colors = bytearray([base_color]) * 960
    for first, count in color_runs:
        colors[first:first + count] = block[position:position + count]
        position += count
    assert position == metadata
    word = int.from_bytes(block[position:position + 2], 'little')
    assert word & 0x8000
    count, position = word & 0x7fff, position + 2
    bitmap, spans, zero_bytes, boundaries = bytearray(7680), [], 0, 0
    for _ in range(count):
        low, flags, size = block[position:position + 3]
        assert flags & 0x60 == 0 and size > 0
        first = low + ((flags & 31) << 8)
        position += 3
        data = block[position:position + size]
        assert len(data) == size and 0 <= first < first + size <= 7680
        bitmap[first:first + size] = data
        spans.append(dict(first=first, size=size, release=bool(flags & 128)))
        zero_bytes += data.count(0)
        boundaries += bool(flags & 128)
        position += size
    assert position == len(block) and spans[-1]['release']
    assert all(not value or clear[i] for i, value in enumerate(bitmap))
    return bytes(bitmap + colors), spans, clear_spans, dict(literal_bytes=sum(r['size'] for r in spans),
        stored_zero_bytes=zero_bytes, map_release_boundaries=boundaries,
        bitmap_copy_core_cycles_lower_bound=13 * sum(r['size'] for r in spans),
        clear_bytes=sum(clear), clear_covers_all_nonzero_bitmap_bytes=True)


def kernel_binding(ram, labels):
    """Bind two copy loops and the span-address mask to actual cartridge bytes."""
    cases = [('v3_color_copy', bytes.fromhex('b1f091f2c8c4ecd0f7')),
             ('v9_group', bytes.fromhex('b1f091f2c8') * 8 + bytes.fromhex('c4e2d0d4'))]
    result = []
    for name, expected in cases:
        address = labels[name]
        assert 0x800 <= address < address + len(expected) <= 0x6000
        assert ram[address:address + len(expected)] == expected
        result.append(dict(label=name, address=address, bytes=len(expected), machine_code=expected.hex()))
    flags = labels['hors_v2_span_flags']
    expected = b'\xa0\x00\xb1\xf0\x85\xf2\xc8\xb1\xf0\x8d' + flags.to_bytes(2, 'little') + b'\x29\x1f'
    address = labels['hors_v2_span_mapped']
    assert 0x800 <= address < address + len(expected) <= 0x6000
    assert ram[address:address + len(expected)] == expected
    result.append(dict(label='hors_v2_span_mapped', address=address, bytes=len(expected), machine_code=expected.hex()))
    return result


def png(picture):
    # An illustrative RGB palette; proof comparisons use original numeric indices.
    palette = [(0, 0, 0), (255, 255, 255), (136, 0, 0), (170, 255, 238),
               (204, 68, 204), (0, 204, 85), (0, 0, 170), (238, 238, 119),
               (221, 136, 85), (102, 68, 0), (255, 119, 119), (51, 51, 51),
               (119, 119, 119), (170, 255, 102), (0, 136, 255), (187, 187, 187)]
    pixels = bytearray()
    for y in range(192):
        for x in range(320):
            cell = (y // 8) * 40 + x // 8
            bit = picture[(y // 8) * 320 + (x // 8) * 8 + y % 8] & (128 >> (x % 8))
            colors = picture[7680 + cell]
            pixels.append(colors >> 4 if bit else colors & 15)
    raw = b''.join(b'\0' + bytes(pixels[y * 320:(y + 1) * 320]) for y in range(192))
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    data = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 320, 192, 8, 3, 0, 0, 0)) +
            chunk(b'PLTE', bytes(c for rgb in palette for c in rgb)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))
    path = OUT / 'dragon-frame-000.png'
    path.write_bytes(data)
    return dict(**artifact(path), scope='Reconstructed logical 320x192 image, illustrative RGB palette; no native scanout.')


def main():
    acquisition = inputs()
    manifest = json.loads((SOURCE / (STEM + '-manifest.json')).read_text())
    oracle = json.loads(gzip.decompress((SOURCE / (STEM + '-oracle.json.gz')).read_bytes()))
    chips, ram = cartridge((SOURCE / (STEM + '.crt')).read_bytes())
    labels = {m[2]: int(m[1], 16) for m in re.finditer(r'^al ([0-9a-fA-F]+) \.([^\s]+)$',
              (SOURCE / (STEM + '.lbl')).read_text(), re.M)}
    assert manifest['frames'] == len(oracle) == len(manifest['frame_data']) == 128
    assert manifest['wire_format'] == 'hors-v3-color-literals-v1'
    run_count = labels['v3_color_hi'] - labels['v3_color_lo']
    assert labels['v3_color_length'] - labels['v3_color_hi'] == run_count == 23
    color_runs = [(ram[labels['v3_color_lo'] + i] + 256 * ram[labels['v3_color_hi'] + i],
                   ram[labels['v3_color_length'] + i]) for i in range(run_count)]
    active = [j for start, count in color_runs for j in range(start, start + count)]
    assert active == sorted(set(active)) and len(active) == 437
    for name in ('cart_bank', 'cart_source_lo', 'cart_source_hi', 'cart_length_lo',
                 'cart_length_hi', 'cart_meta_lo', 'cart_meta_hi'):
        assert 0x800 <= labels[name] < labels[name] + 128 <= 0x6000
    assert 0x800 <= labels['v3_color_lo'] < labels['v3_color_length'] + run_count <= 0x6000
    OUT.mkdir(parents=True, exist_ok=True)
    decoded, expected, rows, all_spans = [], [], [], []
    for i, (entry, frame) in enumerate(zip(manifest['frame_data'], oracle)):
        def directory(name):
            return ram[labels[name] + i]
        bank = directory('cart_bank')
        address = directory('cart_source_lo') + 256 * directory('cart_source_hi')
        flagged_size = directory('cart_length_lo') + 256 * directory('cart_length_hi')
        metadata = directory('cart_meta_lo') + 256 * directory('cart_meta_hi')
        assert flagged_size & 0x8000
        size = flagged_size & 0x7fff
        assert (bank, address, size, metadata) == (entry['bank'], entry['address'], entry['bytes'], entry['metadata_bytes'])
        assert 0x8000 <= address < address + size <= 0xa000 and metadata <= 1024
        block = chips[bank, 0x8000][address - 0x8000:address - 0x8000 + size]
        assert sha(block) == entry['sha256']
        actual, spans, clears, stats = decode(block, metadata, color_runs, manifest['screen_color'])
        independent = logical_picture(frame, manifest['screen_color'])
        assert actual == independent, i
        assert clears == frame['clear_spans'] and len(frame['records']) == entry['runs']
        assert all(value == manifest['screen_color'] or cell in active for cell, value in enumerate(independent[7680:]))
        decoded.append(actual)
        expected.append(independent)
        all_spans.append(spans)
        rows.append(dict(frame=i, bank=bank, address=address, encoded_bytes=size, metadata_bytes=metadata,
                         literal_spans=len(spans), host_oracle_records=len(frame['records']),
                         bitmap_and_screen_sha256=sha(actual), **stats))
    # A concrete history control: copying the next picture without clearing leaves old pixels.
    control = None
    for i in range(1, len(decoded)):
        stale = bytearray(decoded[i - 1][:7680])
        for span in all_spans[i]:
            start, count = span['first'], span['size']
            stale[start:start + count] = decoded[i][start:start + count]
        errors = sum(a != b for a, b in zip(stale, decoded[i][:7680]))
        if errors:
            control = dict(previous_frame=i - 1, next_frame=i, uncleared_bitmap_byte_differences=errors)
            break
    assert control
    body = (SOURCE / 'examples/stanford_dragon/stanford_dragon.obj').read_text()
    vertices = [r for r in body.splitlines() if r.startswith('v ')]
    faces = [[int(v.split('/')[0]) for v in r.split()[1:]] for r in body.splitlines() if r.startswith('f ')]
    assert len(vertices) == manifest['vertices'] == 5205 and len(faces) == manifest['faces'] == 11102
    assert all(len(f) == 3 and all(1 <= v <= len(vertices) for v in f) for f in faces)
    edges = {tuple(sorted((f[j], f[(j + 1) % 3]))) for f in faces for j in range(3)}
    assert len(edges) == manifest['edges'] == 15796
    outputs = []
    for name, pictures in [('decoded-pictures.bin', decoded), ('independent-oracle-pictures.bin', expected)]:
        path = OUT / name
        path.write_bytes(b''.join(pictures))
        outputs.append(artifact(path))
    result = dict(pass_=True, producer=artifact(Path(__file__).resolve()), acquisition=acquisition,
        source_model=dict(vertices=len(vertices), triangles=len(faces), unique_edges=len(edges)),
        CRT=dict(hardware_type=32, chip_type=2, chip_packets=len(chips), payload_bytes=sum(map(len, chips.values())),
                 source=artifact(SOURCE / (STEM + '.crt')), bootstrap_pages=88,
                 boot_page_count_instruction=dict(ROMH_bank=0, offset=0x5c, bytes='a258'),
                 runtime_source='Only the 88-page bootstrap input, $0800..$5FFF; uncopied $6000..$67FF zero cartridge padding is excluded. No CPU execution is inferred.'),
        machine_code_binding=kernel_binding(ram, labels), color_plan=dict(runs=color_runs, cells=len(active),
            absolute_values_each_frame=True, all_nonbase_oracle_cells_covered=True),
        compared_frames=len(rows), bytes_per_picture=8640, compared_bytes=8640 * len(rows), differences=0,
        frames=rows, outputs=outputs, preview=png(decoded[0]), no_clear_control=control,
        every_frame_clear_covers_own_nonzero_bitmap=True,
        static_bitmap_copy_bound=dict(core_cycles_per_byte=13, instructions=['LDA (zp),Y: minimum 5', 'STA (zp),Y: 6', 'INY: 2'],
            maximum_picture_lower_bound=max(r['bitmap_copy_core_cycles_lower_bound'] for r in rows),
            conditional_on='Executing each published literal copy once on an ordinary 6510; excludes page crossings, branches, mapping/setup, clearing, colors, IRQs and VIC stalls.',
            measured_cycles=False, FPS_claim=False),
        upstream_benchmark_reproduced=False, native_execution=False,
        limits=['Compares published cartridge data to published host oracle, not native display output.',
                'Checks original OBJ topology counts, not its projection, visibility, lighting, or source-to-oracle pipeline.',
                'Selected HORS-V3 release asset only; current main also contains other backends and defaults.',
                'The 192-line logical viewport excludes the HUD, borders, VIC scheduling, IRQ behavior and frame timing.',
                'Literal pictures are independent; bitmap slots still require correct old-frame clear metadata and initialization.',
                'No upstream Python or assembler is imported, evaluated or executed; no cartridge is run.'])
    result['pass'] = result.pop('pass_')
    path = OUT / 'host3d-proof.json'
    path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(receipt=artifact(path), frames=len(rows), compared_bytes=result['compared_bytes'],
                         differences=0, preview=result['preview']), indent=2))


if __name__ == '__main__':
    main()
