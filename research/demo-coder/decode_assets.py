#!/usr/bin/env python3
"""Passively decode stream 46's stored bitmap candidates; never run a CPU/VIC.

The PNGs apply the documented ordinary multicolor bitmap addressing formula.
They are storage diagnostics, not reconstructions of the raster program's output.
Only the standard library and the repository's read-only VSF parser are used.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys
import urllib.request
import zlib

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/demo-coder'
sys.path.insert(0, str(ROOT / 'research/quondam'))
from snapshot_state import module_payload, read_snapshot

PAYLOAD_SHA = '3be2386eeb9c9f0d3bb274eab04fd7aa48f7df3b3a10199df3d49cecaabec31c'
STOPS = ('selector-entry', 'selector-initialized', 'selector-visible-c')
REFERENCE_URLS = {
    'c64gfx-rubicon.html': 'https://c64gfx.com/image/9993572',
    'c64gfx-rubicon.png': 'https://d2certfx9n6wgt.cloudfront.net/artwork/9993572.png?v=7103e964',
}
REFERENCE_PNG_SHA = '7018bb0f9df0160323771e70be287801da8100d64ea505cb9ecc8b36c4e4ae34'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rel(path):
    return str(Path(path).resolve().relative_to(ROOT))


def file_record(path):
    data = Path(path).read_bytes()
    return dict(path=rel(path), bytes=len(data), sha256=sha(data))


def palette(path):
    result = []
    for line in path.read_text().splitlines():
        fields = line.split('#', 1)[0].split()
        if fields:
            assert len(fields) == 3
            result.append(tuple(int(value, 16) for value in fields))
    assert len(result) == 16
    return result


def png(path, pixels, colors, description):
    """Encode color indices directly, without filtering or image transformations."""
    height, width = len(pixels), len(pixels[0])
    assert all(len(row) == width and max(row, default=0) < 16 for row in pixels)
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    raw = b''.join(b'\0' + bytes(row) for row in pixels)
    data = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 3, 0, 0, 0))
            + chunk(b'PLTE', bytes(value for color in colors for value in color))
            + chunk(b'tEXt', b'Description\0' + description.encode('ascii'))
            + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))
    path.write_bytes(data)
    return dict(**file_record(path), width=width, height=height,
                color_index_sha256=sha(b''.join(bytes(row) for row in pixels)),
                color_index_counts=dict(sorted(Counter(value for row in pixels for value in row).items())))


def multicolor(memory, bitmap, screen, color_ram, background, height=200):
    """320 physical pixels, 40 cells, ordinary 8-byte-per-cell bitmap layout."""
    result = []
    for y in range(height):
        row = []
        for column in range(40):
            cell = (y // 8) * 40 + column
            byte = memory[bitmap + cell * 8 + (y & 7)]
            attribute = memory[screen + cell]
            choices = (background, attribute >> 4, attribute & 15, color_ram[cell] & 15)
            for shift in (6, 4, 2, 0):
                row.extend((choices[(byte >> shift) & 3],) * 2)
        result.append(row)
    return result


def indexed_png(path):
    """Read bounded non-interlaced indexed PNGs, preserving exact color indices."""
    data = path.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    cursor, compressed, colors, header = 8, bytearray(), None, None
    while cursor < len(data):
        length = int.from_bytes(data[cursor:cursor+4], 'big')
        kind, body = data[cursor+4:cursor+8], data[cursor+8:cursor+8+length]
        assert len(body) == length
        assert zlib.crc32(kind+body) & 0xffffffff == int.from_bytes(data[cursor+8+length:cursor+12+length], 'big')
        if kind == b'IHDR':
            header = struct.unpack('>IIBBBBB', body)
        elif kind == b'PLTE':
            assert len(body) % 3 == 0
            colors = [tuple(body[i:i+3]) for i in range(0, len(body), 3)]
        elif kind == b'IDAT':
            compressed.extend(body)
        cursor += length+12
        if kind == b'IEND':
            break
    assert cursor == len(data) and header and colors
    width, height, depth, mode, compression, filtering, interlace = header
    assert 0 < width <= 512 and 0 < height <= 512 and depth in (1, 2, 4, 8)
    assert (mode, compression, filtering, interlace) == (3, 0, 0, 0)
    stride = (width * depth + 7) // 8
    raw = zlib.decompress(compressed)
    assert len(raw) == height * (stride+1)
    previous, pixels = bytearray(stride), []
    def paeth(a, b, c):
        p = a+b-c
        pa, pb, pc = abs(p-a), abs(p-b), abs(p-c)
        return a if pa <= pb and pa <= pc else b if pb <= pc else c
    for y in range(height):
        offset = y * (stride+1)
        method, row = raw[offset], bytearray(raw[offset+1:offset+1+stride])
        assert method <= 4
        for i in range(stride):
            left, above, corner = row[i-1] if i else 0, previous[i], previous[i-1] if i else 0
            predictor = (0, left, above, (left+above)//2, paeth(left, above, corner))[method]
            row[i] = (row[i]+predictor) & 255
        pixels.append([(row[(x*depth)//8] >> (8-depth-((x*depth)&7))) & ((1 << depth)-1) for x in range(width)])
        previous = row
    assert max(value for row in pixels for value in row) < len(colors)
    return pixels, colors


def reference_comparison(path, candidate):
    """Compare color equivalence at bounded screenshot offsets, not RGB palettes.

    A candidate index must map to exactly one gallery index. An exact bijection
    therefore checks every pixel's palette class despite differing RGB palettes.
    The offsets tested and every non-perfect trial remain in the receipt.
    """
    assert sha(path.read_bytes()) == REFERENCE_PNG_SHA
    pixels, colors = indexed_png(path)
    trials = []
    for top in range(32, 41):
        pairs = {}
        for y in range(176):
            for x in range(320):
                pairs.setdefault(candidate[y][x], Counter())[pixels[top+y][32+x]] += 1
        mapping = {key: counts.most_common(1)[0][0] for key, counts in pairs.items()}
        mismatch_rows = []
        for y in range(176):
            count = sum(mapping[candidate[y][x]] != pixels[top+y][32+x] for x in range(320))
            if count:
                mismatch_rows.append(dict(row=y, mismatch_pixels=count))
        trials.append(dict(left=32, top=top, width=320, height=176, pixel_count=320*176,
                           color_mapping=mapping, one_to_one=len(set(mapping.values())) == len(mapping),
                           mismatch_pixels=sum(row['mismatch_pixels'] for row in mismatch_rows), mismatch_rows=mismatch_rows))
    best = min(trials, key=lambda trial:trial['mismatch_pixels'])
    tail_mismatches = sum(best['color_mapping'][candidate[y][x]] != pixels[best['top']+y][32+x]
                          for y in range(176, 184) for x in range(128))
    full_height_rows = []
    for y in range(200):
        count = sum(best['color_mapping'][candidate[y][x]] != pixels[best['top']+y][32+x] for x in range(320))
        if count:
            full_height_rows.append(dict(row=y, mismatch_pixels=count))
    return dict(reference=file_record(path), reference_width=len(pixels[0]), reference_height=len(pixels),
                reference_palette_rgb=colors, tested_offsets=trials, best=best,
                exact=best['one_to_one'] and best['mismatch_pixels'] == 0,
                final_128_bitmap_bytes=dict(left=0, top=176, width=128, height=8, pixel_count=1024,
                                            mismatch_pixels=tail_mismatches,
                                            exact=best['one_to_one'] and tail_mismatches == 0,
                                            scope='The first 16 cells of character row 22, $3B80..$3BFF; completes the 7168-byte bitmap prefix.'),
                complete_200_line_trial=dict(left=32, top=best['top'], width=320, height=200,
                                            mismatch_pixels=sum(row['mismatch_pixels'] for row in full_height_rows),
                                            mismatch_rows=full_height_rows,
                                            scope='Same palette mapping, deliberately decoding screen bytes as the final 832 bitmap bytes; this is not a complete stored 200-line image.'),
                scope='Only the first 176 stored image lines; color-index equivalence, not RGB equality or a raster output oracle.')


def equal_check(label, actual, expected):
    assert len(actual) == len(expected)
    differences = [dict(offset=i, expected=b, actual=a) for i, (a, b) in enumerate(zip(actual, expected)) if a != b]
    return dict(label=label, bytes=len(actual), exact=not differences, actual_sha256=sha(bytes(actual)),
                expected_sha256=sha(bytes(expected)), differences=differences)


def capture(directory, name):
    vsf, ramfile = directory / (name + '.vsf'), directory / ('ram-' + name + '.bin')
    state = read_snapshot(vsf)
    meta = state['modules']['C64MEM']
    assert meta['version'] == [0, 1] and meta['payload_size'] == 65555
    ram = ramfile.read_bytes()
    assert len(ram) == 65536 and ram == module_payload(vsf, 'C64MEM')[4:65540]
    cpu = module_payload(vsf, 'MAINCPU')
    vic = state['vicii']
    return ram, vic, dict(name=name, ram=file_record(ramfile), snapshot=file_record(vsf),
                          ram_matches_snapshot=True, cpu_clock=int.from_bytes(cpu[:8], 'little'),
                          cpu_pc=int.from_bytes(cpu[12:14], 'little'),
                          vic_regs=vic['regs'], color_ram_sha256=sha(bytes(vic['color_ram'])),
                          cia2=state['cia']['CIA2'],
                          vic_observation={key: vic[key] for key in ('raster_line', 'raster_cycle', 'rc', 'vc', 'vcbase',
                                                                   'vmli', 'bad_line', 'idle_state', 'allow_bad_lines',
                                                                   'vborder', 'main_border')})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=BASE / 'asset-analysis')
    parser.add_argument('--fetch-reference', action='store_true', help='Archive the public gallery page and its linked PNG, at most 1 MiB each.')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    reference_dir = output / 'reference'
    if args.fetch_reference:
        from datetime import datetime, timezone
        reference_dir.mkdir(parents=True, exist_ok=True)
        acquisitions = []
        for name, url in REFERENCE_URLS.items():
            request = urllib.request.Request(url, headers={'User-Agent': 'C64 research archive (passive asset identification)'})
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read(1024*1024+1)
                assert len(data) <= 1024*1024
                target = reference_dir / name
                target.write_bytes(data)
                acquisitions.append(dict(url=url, final_url=response.url, status=response.status,
                                         headers=dict(response.headers), **file_record(target),
                                         retrieved_utc=datetime.now(timezone.utc).isoformat()))
        (reference_dir / 'acquisition.json').write_text(json.dumps(acquisitions, indent=2) + '\n')
    directory = BASE / 'native-01'
    session_path = directory / 'session.json'
    session = json.loads(session_path.read_text())
    assert session.get('closed_utc'), 'Read only a closed native session.'
    prg_path = BASE / 'streams/046-2000-unpacked.prg'
    prg = prg_path.read_bytes()
    assert len(prg) == 40963 and prg[:2] == b'\0 ' and sha(prg[2:]) == PAYLOAD_SHA
    original = bytearray(65536)
    original[0x2000:0xc001] = prg[2:]
    captures = {name: capture(directory, name) for name in STOPS}
    entry, entry_vic, _ = captures['selector-entry']
    initialized, init_vic, _ = captures['selector-initialized']
    visible, visible_vic, _ = captures['selector-visible-c']
    checks = [equal_check('Complete original image equals natural-entry RAM', entry[0x2000:0xc001], prg[2:]),
              equal_check('Initializer copies 1000 source low nibbles to physical Color RAM',
                          init_vic['color_ram'][:1000], [v & 15 for v in entry[0x4000:0x43e8]]),
              equal_check('Remaining 24 Color RAM cells retain entry', init_vic['color_ram'][1000:], entry_vic['color_ram'][1000:])]
    for name in ('selector-initialized', 'selector-visible-c'):
        ram, vic, _ = captures[name]
        checks.extend([
            equal_check(name + ': original 7168 bitmap-source bytes retained', ram[0x2000:0x3c00], entry[0x2000:0x3c00]),
            equal_check(name + ': +1 byte source copied to $4000', ram[0x4000:0x5c00], entry[0x2001:0x3c01]),
            equal_check(name + ': +2 byte source copied to $C000', ram[0xc000:0xdc00], entry[0x2002:0x3c02]),
            equal_check(name + ': $E000 7168-byte source cleared', ram[0xe000:0xfc00], bytes(0x1c00)),
            equal_check(name + ': all physical Color RAM unchanged since initializer', vic['color_ram'], init_vic['color_ram'])])
        for screen in (0x3c00, 0x5c00, 0xdc00, 0xfc00):
            checks.append(equal_check(f'{name}: screen ${screen:04X} equals original $3C00',
                                      ram[screen:screen+1000], entry[0x3c00:0x3fe8]))
    palette_path = ROOT / 'palettes/colodore.vpl'
    colors = palette(palette_path)
    background = init_vic['regs'][0x21] & 15
    assert background == visible_vic['regs'][0x21] & 15
    renders = []
    configs = [('original', original, 0x2000, 0x3c00, init_vic['color_ram']),
               ('initialized-bank0', initialized, 0x2000, 0x3c00, init_vic['color_ram']),
               ('initialized-plus1', initialized, 0x4000, 0x5c00, init_vic['color_ram']),
               ('initialized-plus2', initialized, 0xc000, 0xdc00, init_vic['color_ram']),
               ('initialized-clear', initialized, 0xe000, 0xfc00, init_vic['color_ram']),
               ('visible-c-bank0', visible, 0x2000, 0x3c00, visible_vic['color_ram']),
               ('visible-c-plus1', visible, 0x4000, 0x5c00, visible_vic['color_ram']),
               ('visible-c-plus2', visible, 0xc000, 0xdc00, visible_vic['color_ram'])]
    for name, ram, bitmap, screen, color in configs:
        pixels = multicolor(ram, bitmap, screen, color, background)
        record = png(output / (name + '-ordinary-mc.png'), pixels, colors,
                     f'Ordinary multicolor bitmap storage diagnostic: {name}; bitmap ${bitmap:04x}, screen ${screen:04x}, actual initialized Color RAM, background {background}. Not a raster output reconstruction.')
        record.update(name=name, bitmap=bitmap, screen=screen, background=background,
                      bitmap_sha256=sha(ram[bitmap:bitmap+8000]), screen_sha256=sha(ram[screen:screen+1000]),
                      color_ram_sha256=sha(bytes(color)))
        renders.append(record)
    # Complete character rows strictly below the screen-address overlap boundary.
    clean_pixels = multicolor(original, 0x2000, 0x3c00, init_vic['color_ram'], background, 176)
    renders.append(dict(name='original-first-176-lines', **png(output / 'original-first-176-lines.png', clean_pixels, colors,
                         'First 22 complete ordinary bitmap rows (176 lines), all before the $3c00 screen overlap. Storage diagnostic, not raster output.')))
    # A byte-level row-phase check avoids calling the shifted copies a normal
    # scrolling bitmap: +1/+2 wrap across adjacent cells at the eighth row.
    phase_checks = []
    for shift, target in ((1, 0x4000), (2, 0xc000)):
        ordinary_rows, cross_cell_rows = 0, 0
        for cell in range(896):
            for row in range(8):
                address = target + cell * 8 + row
                expected_address = 0x2000 + cell * 8 + row + shift
                assert initialized[address] == entry[expected_address]
                if row + shift < 8:
                    ordinary_rows += 1
                else:
                    cross_cell_rows += 1
        phase_checks.append(dict(shift_bytes=shift, target=target, bytes=7168,
                                 within_same_cell_row_bytes=ordinary_rows, crosses_into_next_cell_bytes=cross_cell_rows,
                                 source_end_exclusive=0x3c00+shift))
    report = dict(description=__doc__, scope='Passive byte reads and ordinary multicolor storage decoding; no CPU, emulator, raster rendering, or independent VIC pixel oracle.',
                  script=file_record(Path(__file__)), snapshot_reader=file_record(ROOT / 'research/quondam/snapshot_state.py'),
                  original_prg=file_record(prg_path), payload_bytes=len(prg)-2, payload_sha256=sha(prg[2:]),
                  session=file_record(session_path), session_closed_utc=session['closed_utc'],
                  palette=file_record(palette_path), captures=[captures[name][2] for name in STOPS],
                  checks=checks, checks_passed=all(check['exact'] for check in checks),
                  ordinary_bitmap=dict(width=320, height=200, bitmap_bytes=8000, screen_bytes=1000,
                                       source_bitmap_region=[0x2000, 0x3c00], source_bitmap_bytes=7168,
                                       screen_region=[0x3c00, 0x3fe8], overlapping_full_decode_bytes=832,
                                       complete_nonoverlapping_character_rows=22, complete_nonoverlapping_pixel_lines=176,
                                       color_selectors=['00: D021 background', '01: screen high nibble', '10: screen low nibble', '11: Color RAM low nibble']),
                  shifted_byte_phase_checks=phase_checks, renders=renders,
                  limitations=['Ordinary bitmap decode ignores changing VIC mode, fetch counters, borders and time-varying bank/screen selection.',
                               'The complete 200-line ordinary decode intentionally includes screen bytes in its final 832 bitmap bytes.',
                               'No image identity, MEGA/full-row phase assignment, or physical-VIC frame claim follows from byte equality.'])
    reference_path = reference_dir / 'c64gfx-rubicon.png'
    if reference_path.exists():
        report['gallery_comparison'] = reference_comparison(reference_path, multicolor(original, 0x2000, 0x3c00, init_vic['color_ram'], background))
        report['gallery_sources'] = [file_record(reference_dir / name) for name in (*REFERENCE_URLS, 'acquisition.json')]
    author_path = ROOT / 'build/research/frontier-followup/demo-coder-release.html'
    report['author_release_page'] = file_record(author_path)
    assert 'the fld-with-stretch effect uses an unreleased loading picture' in author_path.read_text()
    report_path = output / 'asset-evidence.json'
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(receipt=rel(report_path), sha256=sha(report_path.read_bytes()),
                          checks=len(checks), all_checks_passed=report['checks_passed'], renders=len(renders),
                          gallery_first_176_lines_exact=report.get('gallery_comparison', {}).get('exact')), indent=2))
    if not report['checks_passed']:
        raise SystemExit('Asset byte checks failed; complete differences were retained in the receipt.')


if __name__ == '__main__':
    main()
