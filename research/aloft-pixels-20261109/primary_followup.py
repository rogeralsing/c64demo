#!/usr/bin/env python3
"""Primary-author reading, passive PRG header and finite WIZ offset arithmetic.

This does not execute the downloaded C64 program or reconstruct its bitmap,
snowflake coordinates, native display, sprite schedule or delivered FPS.
"""
import argparse
import hashlib
from html import unescape
from html.parser import HTMLParser
import json
from math import gcd
from pathlib import Path
import re
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-pixels-20261109/reading-analysis'
HTTP = BASE / 'acquisition-01/http-retention.json'
HTTP_SHA = '03a7764f22704b9b69eab73b894134fb2871370ea3ac48830065043d87d9c781'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def ref(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def checked(row):
    raw = (ROOT / row['path']).read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
    return raw


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.hrefs += [value for name, value in attrs if name == 'href']


def output(out, name, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    (out / name).write_bytes(raw)
    return dict(name=name, bytes=len(raw), sha256=sha(raw))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to(BASE)
    assert not out.exists()
    assert sha(HTTP.read_bytes()) == HTTP_SHA
    http = json.loads(HTTP.read_bytes())
    assert http['no_certificate_bypass'] is True
    rows = {row['name']: row for row in http['requests']}
    assert set(rows) == {'bauer', 'perpetual', 'perpetual-prg'}
    for row in rows.values():
        assert row['status'] == 200 and not row['certificate_verification_disabled']
        checked(row['body'])
    assert rows['bauer']['body']['sha256'] == 'ed558b2480638b153d0ead4726b8b675e4a0b945f2ab4d37c17a3d892cf00828'
    html = checked(rows['perpetual']['body']).decode('utf-8')
    first = html.index('<h1>Perpetual Fragility</h1>')
    last = html.index('Discuss this page', first)
    author = html[first:last]
    links = Links(); links.feed(author)
    assert rows['perpetual-prg']['url'] in [urljoin(rows['perpetual']['url'], href) for href in links.hrefs]
    text = unescape(re.sub('<[^>]+>', ' ', author))
    text = re.sub(r'\s+', ' ', text)
    anchors = [
        r'scroll offset increases by 595 \(modulo 1024\)',
        r'actual snowflake animation happens to contain 1496 frames',
        r'only need to prepare one row of video matrix data',
        r'generator runs at compile-time',
    ]
    assert all(re.search(pattern, text) for pattern in anchors)
    prg = checked(rows['perpetual-prg']['body'])
    assert len(prg) == 9469 and prg[:14] == bytes.fromhex('01080b081e009e32303631000000')
    header = dict(load_address=0x0801, BASIC_next_line=0x080b, BASIC_line_number=30,
                  BASIC_SYS_decimal=2061, SYS_address=0x080d,
                  retained_prefix_hex=prg[:16].hex(), bytes=len(prg),
                  C64_machine_code_executed=False, packed_payload_decoded=False)
    step, modulus = 595, 1024
    offsets = [(index * step) % modulus for index in range(modulus)]
    assert sorted(offsets) == list(range(modulus))
    assert (modulus * step) % modulus == 0 and gcd(step, modulus) == 1
    inverse = pow(step, -1, modulus)
    assert all((value * inverse) % modulus == index for index, value in enumerate(offsets))
    # The odd-step statement is a finite arithmetic claim, independent of a PRG.
    odd_cases = []
    for candidate in range(1, modulus, 2):
        cycle = {(index * candidate) % modulus for index in range(modulus)}
        assert len(cycle) == modulus
        odd_cases.append(dict(step=candidate, visited=modulus, period=modulus))
    # Bitmap coarse addressing wraps a 1024-cell ring; it is not a 40x25 torus.
    address_cases = []
    for offset in offsets:
        cells = [((offset + 40 * y + x) % modulus) for y in range(25) for x in range(40)]
        assert len(cells) == len(set(cells)) == 1000
        assert all(0 <= value * 8 + row < 8192 for value in cells for row in range(8))
        address_cases.append(dict(offset=offset, cells=1000, distinct_cells=1000,
                                  unobserved_cells=24))
    out.mkdir(parents=True)
    source = out / 'primary_followup.checked.py'; source.write_bytes(Path(__file__).read_bytes())
    outputs = [dict(name=source.name, bytes=source.stat().st_size, sha256=sha(source.read_bytes())),
        output(out, 'author-and-passive-program.json', dict(
            HTTP=ref(HTTP), source_bodies=[row['body'] for row in rows.values()],
            author_fragment_character_range=[first, last], author_fragment_sha256=sha(author.encode()),
            required_author_patterns=anchors, anonymous_comments_used=False,
            author_claims_not_native_binary_validation=True, passive_PRG_header=header)),
        output(out, 'WIZ-offset-arithmetic.json', dict(
            declared_author_step=step, modulus=modulus, modular_inverse=inverse,
            full_offset_order=offsets, all512_odd_steps=odd_cases,
            coarse_address_formula='(offset + 40*y_char + x_char) mod1024',
            bitmap_byte_formula='8*coarse_address + pixel_row_in_character',
            all1024_viewport_cases=address_cases,
            actual1496_snowflake_coordinates_or_final_bitmap_inputs=False,
            actual_snowflake_count_or_image_match_claim=False))]
    output(out, 'primary-followup-proof.json', dict(pass_=True, producer=ref(Path(__file__)),
        inputs=[ref(HTTP)] + [row['body'] for row in rows.values()], outputs=outputs,
        scope='Primary-author mechanism reading, official linked C64 PRG header and finite offset/address arithmetic; no native demo execution or pixel/coordinate reconstruction.',
        HTTP200_bodies=3, retained_HTTP_body_bytes=sum(row['body']['bytes'] for row in rows.values()),
        odd_step_cases=512, chosen_step_offset_states=1024, viewport_coarse_cases=1024,
        author_comments_excluded=True, downloaded_host_or_C64_code_executed=False,
        actual_PRG_offset_update_or_snowflake_data_reverse_engineered=False,
        no_native_6502_or_VIC_execution=True))


if __name__ == '__main__':
    main()
