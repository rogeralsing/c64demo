#!/usr/bin/env python3
"""Replay retained creator-content acquisitions; never fetch or execute source."""
import argparse
import base64
import hashlib
import json
import re
from collections import Counter
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'build/research/aloft-20261109/primary-source-analysis'
MANIFEST_SHA = 'f6a92c878040b59c4da2e29860a3903809f2c67a49e1315aca041ea23a11ffd5'
PINS = {
    'build/research/aloft-20261109/primary-source-analysis/acquire.py': '3a2ae4c90fc3e0280b0e04374f5dedb91620a647495d6918e4059c9d094e619a',
    'build/research/aloft-20261109/primary-source-analysis/discovery-notes.json': 'b5daf191f8af45d0a89c321434d952cee1213629d0e40ca3a6d19c2e6fe507cb',
    'docs/research/frontier-effects-followup.md': '58f87b5443e0ca44fdeb4103e8aad7634725ade6ed28076b5db6a163f2aea9c1',
}
SIDQUAKE_REVISION = '1d7dbb4b56547f2fcf816f528cb5cf46c9bcceba'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def meta(path):
    data = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(data), 'sha256': digest(data)}


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.href = None
        self.label = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.href = dict(attrs).get('href')
            self.label = []

    def handle_data(self, data):
        if self.href:
            self.label.append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self.href:
            self.links.append({'href': self.href, 'label': ' '.join(''.join(self.label).split())})
            self.href = None


def plain(data):
    return ' '.join(unescape(re.sub(r'<[^>]*>', ' ', data.decode('utf-8', errors='replace'))).split())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = ROOT / args.output
    assert not output.exists(), 'fresh output directory required'
    manifest = DATA / 'acquisition-manifest.json'
    assert digest(manifest.read_bytes()) == MANIFEST_SHA
    closed = json.loads(manifest.read_text())
    assert closed['file_count'] == len(closed['files']) == 97
    assert closed['bytes'] == sum(row['bytes'] for row in closed['files'])
    inputs = [meta(manifest)]
    for name, expected in PINS.items():
        path = ROOT / name
        assert digest(path.read_bytes()) == expected, name
        inputs.append(meta(path))
    for row in closed['files']:
        path = DATA / row['name']
        assert path.is_file() and path.is_relative_to(DATA)
        current = meta(path)
        assert (current['bytes'], current['sha256']) == (row['bytes'], row['sha256']), row['name']
        inputs.append(current)

    responses = {}
    http = []
    for path in sorted(DATA.glob('acquisition-*/*.response.json')):
        row = json.loads(path.read_text())
        request_path = path.with_name(path.name.replace('.response.json', '.request.json'))
        assert row['request'] == json.loads(request_path.read_text())
        request = row['request']
        assert request['method'] == 'GET' and request['url'].startswith('https://')
        assert request['purpose'] and request['discovery']
        assert row['transport_error'] is None
        body = path.parent / row['body']['name']
        data = body.read_bytes()
        assert len(data) == row['body']['bytes'] and digest(data) == row['body']['sha256']
        assert row['started_utc'] <= row['completed_utc']
        content_type = dict(row['response_headers']).get('Content-Type', '').lower()
        assert not content_type.startswith(('video/', 'audio/'))
        key = path.name.split('-', 1)[1].removesuffix('.response.json')
        assert key not in responses
        responses[key] = (row, data)
        http.append({'id': key, 'url': request['url'], 'final_url': row['final_url'],
                     'status': row['status'], 'body': meta(body), 'metadata': meta(path),
                     'request': meta(request_path), 'redirects': row['redirects']})
    assert len(http) == 30
    assert Counter(row['status'] for row in http) == Counter({200: 27, 401: 2, 404: 1})

    def body(name):
        return responses[name][1]

    def json_body(name):
        return json.loads(body(name))

    pages = {}
    for name in ['quiss-home', 'quiss-writings', 'quiss-blog', 'quiss-legacy',
                 'quiss-hacks', 'gp-home', 'gp-resources', 'gp-news', 'scrap-profile',
                 'sparta-profile', 'raistlin-search']:
        data = body(name)
        parser = Links()
        parser.feed(data.decode('utf-8', errors='replace'))
        text = plain(data)
        pages[name] = {'url': responses[name][0]['final_url'], 'links': parser.links,
                       'case_insensitive_Aloft_occurrences': len(re.findall('aloft', text, re.I))}
    blog_links = [row for row in pages['quiss-blog']['links'] if 'scribdtech.wordpress.com/' in row['href']]
    assert len(blog_links) == 5
    assert all(re.search(r'/201[02]/', row['href']) for row in blog_links)
    assert pages['quiss-blog']['case_insensitive_Aloft_occurrences'] == 0
    assert pages['quiss-legacy']['case_insensitive_Aloft_occurrences'] == 0
    assert pages['gp-resources']['case_insensitive_Aloft_occurrences'] == 0
    assert pages['gp-news']['case_insensitive_Aloft_occurrences'] == 0
    assert any(row['href'] == 'https://gp-64.com' for row in pages['scrap-profile']['links'])
    assert any(row['href'] == 'https://gp-64.com' for row in pages['sparta-profile']['links'])
    assert 'Scrap Writer 64' in plain(body('gp-resources'))

    search = {}
    for name in ['scrap-user-search', 'aloft-repo-search', 'quiss-commit-search', 'sparta-commit-search']:
        value = json_body(name)
        assert value == {'total_count': 0, 'incomplete_results': False, 'items': []}, name
        search[name] = {'returned_items': 0, 'incomplete_results': False,
                        'scope': responses[name][0]['request']['purpose']}
    for name in ['quiss-gists', 'sparta-gists']:
        assert json_body(name) == []
        assert not any(key.lower() == 'link' for key, value in responses[name][0]['response_headers'])
        search[name] = {'returned_items': 0, 'pagination_link_absent': True}
    for name in ['quiss-code-search', 'sparta-code-search']:
        assert responses[name][0]['status'] == 401
        assert json_body(name)['message'] == 'Requires authentication'
        search[name] = {'HTTP_status': 401, 'result': 'access boundary; no content search result inferred'}
    assert responses['raistlin-api-search'][0]['status'] == 404
    assert 'Page not found' in plain(body('raistlin-api-search'))
    # A static site ignoring ?s= is not a successful full-text site search.
    assert pages['raistlin-search']['case_insensitive_Aloft_occurrences'] == 0

    decoded = {}
    for name in ['soul-readme', 'sparkle-readme', 'sidquake-readme', 'scrap-text-0']:
        value = json_body(name)
        assert value['encoding'] == 'base64'
        data = base64.b64decode(value['content'])
        assert len(data) == value['size']
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == value['sha']
        decoded[name] = {'name': value['name'], 'git_blob_sha1': value['sha'],
                         'bytes': len(data), 'sha256': digest(data),
                         'Aloft_occurrences': len(re.findall(rb'aloft', data, re.I))}
        assert decoded[name]['Aloft_occurrences'] == 0
    soul = base64.b64decode(json_body('soul-readme')['content']).decode()
    assert '242826' in soul and 'X2024' in soul and 'rotating sprite vectors' in soul
    assert 'd094947170cbe18eee0e553bfa2dc59a7d474fd2' in responses['soul-readme'][0]['request']['url']
    sparkle = base64.b64decode(json_body('sparkle-readme')['content']).decode()
    assert 'IRQ loader' in sparkle
    assert json_body('sidquake-branch')['commit']['sha'] == SIDQUAKE_REVISION
    players = json_body('sidquake-players')
    columns = next(row for row in players if row['name'] == 'ScrapColumns')
    assert columns['sha'] == 'a33b9b53331005a3396656de3ed8b77269e96ad8'
    directory = json_body('scrap-source-route')
    source = next(row for row in directory if row['name'] == 'ScrapColumns.asm')
    assert source['sha'] == json_body('scrap-text-0')['sha'] == 'f8664351a4870755c74116d486b25023d7bbe38a'
    for name in ['sidquake-players', 'scrap-source-route', 'scrap-text-0']:
        assert f'ref={SIDQUAKE_REVISION}' in responses[name][0]['request']['url']
    scrap = base64.b64decode(json_body('scrap-text-0')['content']).decode()
    assert '3D Column Spectrum Visualizer by Scrap' in scrap and 'Adapted for SIDquake' in scrap
    assert '.const NUM_COLUMNS                  = 20' in scrap
    assert all(token in scrap for token in ['Screen 1 (double buffer)', 'CharSet (MC mode)', 'SID voice independently'])
    assert not re.search('aloft|kefrens', scrap, re.I)

    creator_note = plain(body('aloft-creator-input-note'))
    assert 'Submitted by Sparta on 1 February 2026' in creator_note
    assert 'Use a joystick to control the movement of the flipped Kefrens bars on Side 2.' in creator_note
    findings = {
        'pages': pages, 'targeted_search_results': search, 'decoded_content': decoded,
        'Scrap_source_route': {'revision': SIDQUAKE_REVISION,
            'path': 'SIDPlayers/ScrapColumns/ScrapColumns.asm',
            'identity': 'Scrap-credited SIDquake column-spectrum visualizer; not source-to-Aloft matched',
            'source_declares': {'columns': 20, 'sections': 3, 'rows_per_section': 8,
                                'multicolor_charset': True, 'double_buffered_screens': True},
            'Aloft_or_Kefrens_mentions': 0, 'executed': False},
        'scene_boundaries': {
            'moving_three_layer_pattern': 'No creator mechanism recovered in this acquired content set.',
            'bitmap_Kefrens': 'No creator mechanism recovered in this acquired content set.',
            'flipped_Kefrens': 'Creator note binds joystick movement on side2, not drawing algorithm or bitmap-scene identity.'},
        'access_limits': ['GitHub code search401 is not a no-source result.',
                          'Raistlin WordPress API route404 is not a content index.',
                          'A query URL returning the static landing page is not proof of a full-text search.',
                          'No private/deleted source, whole-web absence or implementation equivalence is claimed.']}
    output.mkdir(parents=True)
    checked = output / 'primary_sources.checked.py'
    checked.write_bytes(Path(__file__).read_bytes())
    found_path = output / 'creator-content-findings.json'
    found_path.write_text(json.dumps(findings, indent=2) + '\n')
    record = {'pass_': True, 'scope': 'Bounded public creator-content acquisition and offline parsing. Named Aloft effect mechanisms remain open.',
              'producer': meta(Path(__file__).resolve()), 'inputs': inputs, 'http': http,
              'HTTP_status_counts': dict(Counter(str(row['status']) for row in http)),
              'HTTP_bodies': len(http), 'body_bytes': sum(row['body']['bytes'] for row in http),
              'creator_content_checked': findings, 'limits': findings['access_limits'],
              'new_algorithm_or_source_to_original_match': False,
              'native_CPU_audio_video_download_or_downloaded_host_execution': False,
              'outputs': [{'name': path.name, 'bytes': path.stat().st_size, 'sha256': digest(path.read_bytes())}
                          for path in [checked, found_path]]}
    receipt = output / 'primary-source-proof.json'
    receipt.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'pass_': True, 'HTTP_bodies': len(http), 'outputs': [path.name for path in [checked, found_path, receipt]], 'receipt': meta(receipt)}))


if __name__ == '__main__':
    main()
