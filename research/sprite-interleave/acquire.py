#!/usr/bin/env python3
"""Archive Raistlin's interleave sources and check their finite layout arithmetic.

Only our Python, HTML parsing and image decoding run. No downloaded host code,
assembler, CPU interpreter, emulator, original program or timing mock runs.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import urllib.error
import urllib.request
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'build/research/sprite-interleave'
COMMIT = '965807c511e2025b5c5e1ffb2a6235a4efd6ae5b'
TREE = '2a9bc04218fb7c60d744e8eb1b86ca4cda044eca'
REPO = 'RobertTroughton/C64Demo-PublicReleases'
ARTICLE_SHA = '13341d774dda1a23ae78aec3a21765e0fcf41fd4017d01c6a4d84777a59eafe8'
MM = 'MementoMori/6502/Parts/RotatingGP'
MM_CPP = 'MementoMori/PC/Parts/RotatingGP.cpp'
DIVE = 'TheDive/Build/Parts/VertBitmap'
DIVE_CPP = 'TheDive/VisualStudioProject/C64-RaistllinCodeGenerator/Source/DemoParts/VertBitmap.cpp'
FILES = [
    'README.md', MM + '/RotatingGP.asm', MM_CPP,
    'MementoMori/6502/Main/Main-CommonDefines.asm',
    MM + '/Data/RotatingGP-Base.png', MM + '/Data/RotatingGP.png',
    DIVE + '/ASM/VertBitmap.asm', DIVE_CPP, DIVE + '/Data/InitialSpriteLogos.map',
]
PAGES = [
    ('big-animating-sprite-logo.html', 'https://c64demo.com/big-animating-sprite-logo/'),
    ('sprite-interleave.md', 'https://c64demo.com/sprite-interleave/index.md'),
    ('big-animating-sprite-logo.md', 'https://c64demo.com/big-animating-sprite-logo/index.md'),
    ('the-dive-csdb.html', 'https://csdb.dk/release/?id=179128'),
    ('memento-mori-csdb.html', 'https://csdb.dk/release/?id=195841'),
    ('the-dive-pouet.html', 'https://www.pouet.net/prod.php?which=81677'),
    ('memento-mori-pouet.html', 'https://www.pouet.net/prod.php?which=86927'),
    ('source-announcement.html', 'https://csdb.dk/forums/index.php?roomid=11&showallposts=1&topicid=162980'),
    ('original-codebase64.html', 'https://codebase64.net/doku.php?id=base:sprite_interleave'),
    ('the-dive-original.d64', 'https://csdb.dk/release/download.php?id=222527'),
    ('memento-mori-original.zip', 'https://csdb.dk/release/download.php?id=241934'),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=sha(data))


def fetch(path, url):
    record = dict(requested_url=url, requested_utc=datetime.now(timezone.utc).isoformat())
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'c64demo-primary-source-research'})
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read(8 * 1024 * 1024 + 1)
            assert len(data) <= 8 * 1024 * 1024, ('Bounded acquisition limit', url)
            record.update(final_url=response.url, status=response.status,
                          content_type=response.headers.get('Content-Type'))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        record.update(success=True, artifact=artifact(path))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
        record.update(success=False, error=str(error))
    return record


class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.table = self.row = self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == 'table': self.table = []
        elif tag == 'tr' and self.table is not None: self.row = []
        elif tag in ('td', 'th') and self.row is not None: self.cell = []

    def handle_data(self, value):
        if self.cell is not None: self.cell.append(value)

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(''.join(self.cell).strip()); self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.table.append(self.row); self.row = None
        elif tag == 'table' and self.table is not None:
            self.tables.append(self.table); self.table = None


def line_owners(height, step):
    """Independent interval definition: block b owns image rows sb through sb+20."""
    count = (height + step - 1) // step
    owners = {y: [] for y in range(height)}
    for y in range(height):
        for block in range(count):
            if step * block <= y <= step * block + 20:
                owners[y].append((block, y % 21))
    return count, owners


def table_checks(article):
    parser = Tables(); parser.feed(article)
    result = []
    for step, columns in [(16, 13), (20, 10)]:
        grid = next(t for t in parser.tables if t[0] == ['Sprite line'] + [f'B{i}' for i in range(columns)])
        assert len(grid) == 22
        count, owners = line_owners(200, step)
        expected = {(block, row): y for y, slots in owners.items() for block, row in slots}
        for row, cells in enumerate(grid[1:]):
            assert cells[0] == str(row) and len(cells) == count + 1
            for block, value in enumerate(cells[1:]):
                actual = None if value == '-' else int(value.rstrip('*'))
                assert actual == expected.get((block, row)), (step, block, row, actual)
        result.append(dict(step=step, blocks=count, table_cells=21 * count,
                           repeated_image_rows=sum(len(x) - 1 for x in owners.values()), exact=True))
    return result


def packed_png(path):
    with Image.open(path) as source:
        image = source.convert('RGB')
    width, height = image.size
    assert width % 8 == 0
    # RGB nonblack is the published converter's one-bit sprite ownership rule.
    rows = []
    for y in range(height):
        rows.append(bytes(sum((image.getpixel((8 * x + bit, y)) != (0, 0, 0)) << (7 - bit)
                              for bit in range(8)) for x in range(width // 8)))
    return (width, height), rows


def independent_sprite_bytes(rows):
    """Pack ideal image rows into every block whose 21-row interval contains them."""
    height = len(rows)
    count, owners = line_owners(height, 20)
    result = bytearray(count * 8 * 64)
    for y, values in enumerate(rows):
        for block, hardware_row in owners[y]:
            for xbyte, value in enumerate(values):
                address = 64 * (8 * block + xbyte // 3) + 3 * hardware_row + xbyte % 3
                result[address] = value
    return result, owners


def memento_layout():
    base_size, base_rows = packed_png(OUT / 'source' / MM / 'Data/RotatingGP-Base.png')
    anim_size, wide_rows = packed_png(OUT / 'source' / MM / 'Data/RotatingGP.png')
    assert base_size == (192, 189) and anim_size == (16 * 192, 189)
    expected, owners = independent_sprite_bytes(base_rows)
    # Literal arithmetic in RotatingGP.cpp:56..94; this is not an executed converter.
    literal = bytearray(5120)
    lookup = {y: [] for y in range(189)}
    for packed_y in range(189 + 21):
        block = packed_y // 21
        image_y = packed_y
        if image_y > (block + 1) * 20: image_y -= 21
        if image_y >= 189: continue
        lookup[image_y].append(packed_y)
        for xbyte, value in enumerate(base_rows[image_y]):
            address = 64 * (8 * block + xbyte // 3) + 3 * (packed_y % 21) + xbyte % 3
            literal[address] = value
    assert literal == expected
    assert all(sorted(lookup[y]) == sorted(21 * b + h for b, h in owners[y]) for y in owners)
    vectors = {(y, x): tuple(wide_rows[y][24 * frame + x] for frame in range(16))
               for y in range(189) for x in range(24)}
    varying = {key: value for key, value in vectors.items() if len(set(value)) > 1}
    # The original reverse bottom-half loop omits source row 94. It is constant
    # in these published assets; no arbitrary odd-height animation claim follows.
    emitted_order = list(range(94)) + list(range(188, 94, -1))
    assert all(y in emitted_order for y, x in varying)
    assert all(base_rows[y][x] == value[0] for (y, x), value in vectors.items() if len(set(value)) == 1)
    counts = [0, 0]
    for y, x in varying:
        counts[int(y >= 94)] += len(lookup[y])
    images = []
    missing_duplicate_bytes = 0
    for frame in range(16):
        actual = bytearray(literal)
        omitted = bytearray(literal)
        for y in emitted_order:
            for x in range(24):
                if (y, x) not in varying: continue
                value = vectors[y, x][frame]
                for n, packed_y in enumerate(lookup[y]):
                    address = 64 * (8 * (packed_y // 21) + x // 3) + 3 * (packed_y % 21) + x % 3
                    actual[address] = value
                    if n == 0: omitted[address] = value
        oracle, _ = independent_sprite_bytes([row[24 * frame:24 * (frame + 1)] for row in wide_rows])
        assert actual == oracle, frame
        images.append(sha(bytes(actual)))
        missing_duplicate_bytes += sum(a != b for a, b in zip(omitted, oracle))
    assert missing_duplicate_bytes > 0, 'Negative control must expose omitted duplicate writes.'
    return dict(base_dimensions=list(base_size), animation_dimensions=list(anim_size), frames=16,
                physical_sprite_blocks=80, packed_bytes=5120, useful_base_bytes=189 * 24 + 9 * 24,
                duplicated_image_rows=[y for y, slots in owners.items() if len(slots) == 2],
                layout_bytes_exact=5120, all_frame_packed_bytes_exact=16 * 5120,
                varying_logical_byte_sites=len(varying), generated_store_sites_per_half=counts,
                generated_blitter_nominal_cycles=[8 * n + 6 for n in counts],
                generated_blitter_bytes=[6 * n + 1 for n in counts],
                frame_sha256=images, negative_control_omitted_duplicate_different_bytes=missing_duplicate_bytes,
                row94_varying_bytes=0,
                scope='Host translations of pinned source arithmetic versus independent row-interval/image ownership; original C++ and assembly were not executed.')


def dive_layout():
    source = (OUT / 'source' / DIVE / 'Data/InitialSpriteLogos.map').read_bytes()
    assert len(source) == 3 * 7 * 8 * 64
    literal = bytearray(len(source))
    oracle = bytearray(len(source))
    wrong_roll = bytearray(len(source))
    for set_index in range(3):
        for block in range(7):
            for sprite in range(8):
                first = ((set_index * 7 + block) * 8 + sprite) * 64
                # Literal VertBitmap.cpp:38..45, independently checked below.
                for k in range(21):
                    y = block * 20 + k
                    src = ((set_index * 7 + y // 21) * 8 + sprite) * 64 + 3 * (y % 21)
                    dst = first + 3 * ((k + 21 - block) % 21)
                    literal[dst:dst + 3] = source[src:src + 3]
                    bad = first + 3 * ((k + block) % 21)
                    wrong_roll[bad:bad + 3] = source[src:src + 3]
                for hardware_row in range(21):
                    y = next(y for y in range(20 * block, 20 * block + 21) if y % 21 == hardware_row)
                    src = ((set_index * 7 + y // 21) * 8 + sprite) * 64 + 3 * (y % 21)
                    dst = first + 3 * hardware_row
                    oracle[dst:dst + 3] = source[src:src + 3]
    assert literal == oracle
    different = sum(a != b for a, b in zip(wrong_roll, oracle))
    assert different > 0
    return dict(sets=3, block_rows=7, sprites_per_row=8, packed_bytes_exact=len(source),
                useful_bytes=3 * 7 * 8 * 63, padding_bytes_zero=3 * 7 * 8,
                woven_sha256=sha(bytes(literal)), negative_control_reversed_roll_different_bytes=different,
                scope='All original map bytes rearranged by a source-arithmetic translation, checked against independent image-row ownership; no emitted binary or native display comparison.')


def pointers():
    cases = []
    for base in range(0, 256, 8):
        actual = [None] * 8
        for index in range(4):
            x = base + 4 + index
            actual[index] = x & 0xfb
            actual[index + 4] = x
        assert actual == list(range(base, base + 8))
        cases.append(dict(base=base, pointers=actual))
    wrong = [(4 + 4 + i) & 0xfb for i in range(4)]
    assert wrong != list(range(4, 8))
    return dict(aligned_bases=32, pointer_values_checked=256,
                first_to_last_nominal_cycles=dict(plain=7 * 4 + 7 * 2, SAX=7 * 4 + 3 * 2),
                cost_scope='Instruction costs from the author listing; excludes setup, first store, IRQ overhead and VIC stalls, and is not measured bus timing.',
                misaligned_base4_negative_control=wrong,
                memento_pointer_table=[0xfbf8, 0xfc00], memento_sprite_memory=[0xe000, 0xf400],
                memento_Y_values=[0x3a + 21 * i for i in range(10)],
                memento_requested_IRQ_lines=[0, 77] + [96 + 20 * i for i in range(8)],
                memento_first_pointer_by_row=[0x80 + 8 * i for i in range(10)],
                scope='Exact eight-bit AND/address arithmetic, not a VIC fetch/timing or Y-restart emulator.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true', help='Acquire bounded primary pages and selected immutable source files.')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    metadata = [OUT / 'repository.json', OUT / 'commit.json', OUT / 'tree.json']
    commit = json.loads(metadata[1].read_text())
    tree = json.loads(metadata[2].read_text())
    assert commit['sha'] == COMMIT and commit['commit']['tree']['sha'] == TREE
    assert tree['sha'] == TREE and tree['truncated'] is False
    items = {x['path']: x for x in tree['tree']}
    prior = ROOT / 'build/research/frontier-2026/sprite-interleave.html'
    assert sha(prior.read_bytes()) == ARTICLE_SHA
    routes_path = OUT / 'acquisition.json'
    if args.fetch:
        old = {r['requested_url']: r for r in json.loads(routes_path.read_text())} if routes_path.exists() else {}
        requests = [(OUT / name, url) for name, url in PAGES]
        requests += [(OUT / 'source' / name,
                      f'https://raw.githubusercontent.com/{REPO}/{COMMIT}/{name}') for name in FILES]
        routes = []
        for path, url in requests:
            cached = old.get(url)
            if cached and cached['success']:
                assert artifact(ROOT / cached['artifact']['path']) == cached['artifact']
                routes.append(cached)
            else:
                routes.append(fetch(path, url))
        routes_path.write_text(json.dumps(routes, indent=2) + '\n')
    routes = json.loads(routes_path.read_text())
    for route in routes:
        if route['success']:
            item = route['artifact']
            assert artifact(ROOT / item['path']) == item
    source = []
    for name in FILES:
        path = OUT / 'source' / name
        data = path.read_bytes()
        git_sha = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        assert git_sha == items[name]['sha'] and len(data) == items[name]['size']
        source.append(dict(**artifact(path), repository_path=name, git_blob_sha1=git_sha,
                           url=f'https://github.com/{REPO}/blob/{COMMIT}/{name}'))
    releases = []
    for name in ['the-dive-original.d64', 'memento-mori-original.zip']:
        route = next(r for r in routes if r.get('artifact', {}).get('path') == str((OUT / name).relative_to(ROOT)))
        data = (OUT / name).read_bytes()
        assert route['success'], name
        if name.endswith('.d64'):
            assert len(data) == 174848 and route['content_type'] == 'application/x-d64'
            format_, members = '35-track D64', []
        else:
            assert zipfile.is_zipfile(io.BytesIO(data)), name
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                members = [dict(name=info.filename, bytes=info.file_size,
                                sha256=sha(archive.read(info))) for info in archive.infolist() if not info.is_dir()]
            format_ = 'ZIP'
        releases.append(dict(**artifact(OUT / name), source_url=route['requested_url'],
                             final_url=route['final_url'], format=format_, members=members,
                             scope='Linked original-release archive inventory only; no build or source-to-release/native equivalence.'))
    result = dict(script=artifact(Path(__file__).resolve()), author='Raistlin / Genesis Project',
                  article=dict(date='2026-10-12', url='https://c64demo.com/sprite-interleave/',
                               artifact=artifact(prior), reuse='Pinned earlier frontier-2026 acquisition, unchanged.'),
                  repo=dict(url=f'https://github.com/{REPO}', commit=COMMIT, tree=TREE,
                            metadata=[artifact(p) for p in metadata]),
                  browser_tool_observations=dict(
                      artifact=artifact(OUT / 'web-tool-observations.json'),
                      observations=json.loads((OUT / 'web-tool-observations.json').read_text())),
                  acquisition=routes, sources=source, original_release_artifacts=releases,
                  article_table_checks=table_checks(prior.read_text()),
                  memento_mori=memento_layout(), the_dive=dive_layout(), pointer_checks=pointers(),
                  scope='Primary author/source acquisition and finite host-only arithmetic/asset checks. No downloaded code, compilation, CPU execution, VICE or production implementation.',
                  pass_=True)
    result['pass'] = result.pop('pass_')
    target = OUT / 'source-proof.json'
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(passed=result['pass'], source_files=len(source),
                          acquisition_success=sum(x['success'] for x in routes),
                          acquisition_failed=[x['requested_url'] for x in routes if not x['success']],
                          memento=result['memento_mori'], dive=result['the_dive'],
                          receipt=str(target.relative_to(ROOT))), indent=2))


if __name__ == '__main__':
    main()
