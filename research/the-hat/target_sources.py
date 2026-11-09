#!/usr/bin/env python3
"""Passive, bounded content audit for The Hat ending source identifiers.

Downloads are data only. No caption/media route, native process or host tool.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import quote
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[2]
PRIOR = ROOT / 'build/research/frontier-effects-followup'
COMMIT = 'f5f36e1fb0b68bd8337a4b3cb44849b19d8ea17d'
TREE = PRIOR / 'piper-source-01/C64FindCode-tree.json'
TREE_SHA = '8a87db4cec2c97f89d6b40ce262267af4c614cefc62317aa4e6564f3b860b910'
NEEDLES = {
    'title': r'(?i)\bthe[ _-]+hat\b',
    'upscroll': r'(?i)up[ _-]?scroll',
    'all_border': r'(?i)all[ _-]?border',
    'short_hash': r'7a825b1',
    'release_id': r'259070|105678',
    'credited_coders': r'(?i)\b(?:trident|alfatech)\b',
    'party': r'(?i)fj[aä]lldata',
}
RETAINED = {
    'acquisition-01/the-hat.html': 'f0d64773d116898f84ed952302c22821edb78851c5214243b5443b3496a819b3',
    'acquisition-01/the-hat-notes.html': '419c85b2e0e8848caf135a3ccc836f8b2c8a04a7d38c12c29b6e83e2c828d952',
    'acquisition-01/the-hat-hidden.html': 'e21985d2962e382c16404c398e802239e682748982a20bf88280353c8eea6ae6',
    'acquisition-01/piper-watch.html': '59e8ebd0a22f197a35e96c3819e2591c0a9ca9babcd83c990f08d3d986564864',
    'accepted-02/source-proof.json': '60316a193f14f0989e81a35e6aab020c77efa19607d4ab83d11a66541e1af41d',
}


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_ld = False
        self.ld = []
        self.links = []
        self.visible = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag == 'script' and a.get('type') == 'application/ld+json':
            self.in_ld = True
        if tag == 'a' and 'href' in a:
            self.links.append(a['href'])

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden -= 1
        if tag == 'script':
            self.in_ld = False

    def handle_data(self, s):
        if self.in_ld:
            self.ld.append(s)
        if not self.hidden:
            self.visible.append(s)

    def text(self):
        return ' '.join(' '.join(self.visible).split())


def digest(b):
    return hashlib.sha256(b).hexdigest()


def meta(p):
    p = p.resolve()
    b = p.read_bytes()
    return {'path': str(p.relative_to(ROOT)), 'bytes': len(b), 'sha256': digest(b)}


def load_tree():
    assert digest(TREE.read_bytes()) == TREE_SHA
    t = json.loads(TREE.read_text())
    assert t['sha'] == COMMIT and t['truncated'] is False
    return [r for r in t['tree'] if r['type'] == 'blob']


def fetch(folder):
    folder.mkdir(parents=True, exist_ok=False)
    rows = []
    for n, row in enumerate(load_tree()):
        url = 'https://raw.githubusercontent.com/martinpiper/C64FindCode/' + COMMIT + '/' + quote(row['path'])
        req = Request(url, headers={'User-Agent': 'C64-research-passive-source-audit/1.0'})
        stamp = datetime.now(timezone.utc).isoformat()
        with urlopen(req, timeout=30) as r:
            body = r.read()
            status = r.status
            actual_url = r.url
            headers = {k: r.headers.get(k) for k in ['Content-Type', 'ETag', 'Last-Modified']}
        p = folder / ('%02d.blob' % n)
        p.write_bytes(body)
        rows.append({'repository_path': row['path'], 'git_blob_sha1': row['sha'],
                     'requested_url': url, 'final_url': actual_url,
                     'requested_UTC': stamp, 'status': status, 'headers': headers,
                     'artifact': meta(p)})
        (folder / 'retrieval.json').write_text(json.dumps({'commit': COMMIT, 'routes': rows}, indent=2) + '\n')


def artwork_sources(folder):
    a = json.loads((folder / 'retrieval.json').read_text())
    assert len(a['routes']) == 2
    result = []
    wanted = {'9985253': ('The Hat - Shifted Font', ['Trident', 'redcrab']),
              '9985254': ('The Hat - Shifted Ghost Font', ['redcrab'])}
    for row in a['routes']:
        identity = row['requested_url'].rsplit('/', 1)[-1]
        assert identity in wanted
        assert row['requested_url'] == 'https://c64gfx.com/image/' + identity
        p = ROOT / row['artifact']['path']
        assert meta(p) == row['artifact'] and row['status'] == 200
        page = Page()
        page.feed(p.read_text())
        records = [json.loads(s) for s in page.ld]
        o = next(r for r in records if r.get('@type') == 'ImageObject')
        name, artists = wanted.pop(identity)
        assert o['name'] == name and o['sameAs'] == 'https://csdb.dk/release/?id=259070'
        creators = o['creator'] if isinstance(o['creator'], list) else [o['creator']]
        assert [c['name'] for c in creators] == artists
        assert o['width'] == 384 and o['height'] == 272
        assert 'Format Hi-res bitmap , 2 colours per 8 x 8 block' in page.text()
        # This HTML offers an image and a converter, not the original charset.
        candidates = [u for u in page.links if re.search(r'(?i)\.(prg|bin|64c|chr|d64)(?:$|[?])', u)]
        result.append({'page': row['artifact'], 'requested_url': row['requested_url'],
                       'identity': identity, 'name': name, 'creators': artists,
                       'source_metadata': o, 'direct_original_binary_links': candidates,
                       'ending_consumer_established': False})
    assert not wanted
    return {'retrieval': meta(folder / 'retrieval.json'), 'fonts': result}


def analyze(folder, artwork, output):
    output.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).resolve()
    (output / 'target_sources.checked.py').write_bytes(source.read_bytes())
    acquisition = json.loads((folder / 'retrieval.json').read_text())
    assert acquisition['commit'] == COMMIT
    expected = {r['path']: r for r in load_tree()}
    assert len(acquisition['routes']) == len(expected) == 12
    files = []
    for row in acquisition['routes']:
        r = expected.pop(row['repository_path'])
        p = ROOT / row['artifact']['path']
        b = p.read_bytes()
        assert meta(p) == row['artifact'] and row['status'] == 200
        assert len(b) == r['size']
        assert row['git_blob_sha1'] == r['sha']
        assert hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest() == r['sha']
        assert row['requested_url'] == 'https://raw.githubusercontent.com/martinpiper/C64FindCode/' + COMMIT + '/' + quote(r['path'])
        text = b.decode('utf-8-sig')
        hits = []
        for line, s in enumerate(text.splitlines(), 1):
            names = [k for k, pat in NEEDLES.items() if re.search(pat, s)]
            if names:
                hits.append({'line': line, 'needles': names, 'text': s})
        files.append({'repository_path': r['path'], 'source': row['artifact'],
                      'git_blob_sha1': r['sha'], 'lines': len(text.splitlines()),
                      'identifier_hits': hits})
    assert not expected
    inputs = []
    pages = {}
    for name, sha in RETAINED.items():
        p = PRIOR / name
        assert digest(p.read_bytes()) == sha
        inputs.append(meta(p))
        if p.suffix == '.html':
            page = Page()
            page.feed(p.read_text())
            pages[p.name] = page
    release = pages['the-hat.html'].text()
    notes = pages['the-hat-notes.html'].text()
    hidden = pages['the-hat-hidden.html'].text()
    assert 'Code .... Alfatech' in release and 'Trident of' in release
    assert 'Production Info Submitted by redcrab on 23 March 2026' in notes
    assert '500 frames of petscii animation as .GIFs' in notes
    assert 'Hidden Part Submitted by' not in hidden
    assert 'https://c64gfx.com/release/259070' in notes
    watch = (PRIOR / 'acquisition-01/piper-watch.html').read_text()
    marker = re.search(r'(?:var\s+)?ytInitialPlayerResponse\s*=\s*', watch)
    assert marker
    player, _ = json.JSONDecoder().raw_decode(watch[marker.end():])
    video = player['videoDetails']
    assert video['videoId'] == 'Vfnyczaf1Ao'
    assert video['title'] == 'C64 Demos peek - The Hat - The end scroller part'
    assert video['channelId'] == 'UChH8yUKRIeekkJFufk9QuMA'
    # Not a statement that the released demo is 674 seconds long.
    assert video['lengthSeconds'] == '674'
    collection = ROOT / 'build/research/frontier-2026/february-analysis/the-hat-art.html'
    assert digest(collection.read_bytes()) == 'dd73582d78c15df4ce27701a39547ed12184361808dd310354498469c81c38a5'
    collection_page = Page()
    collection_page.feed(collection.read_text())
    for identity in ('9985253', '9985254'):
        assert '/image/' + identity in collection_page.links
    proof = {
        'schema': 'the-hat-target-content-1', 'producer': meta(source),
        'tree': meta(TREE), 'acquisition': meta(folder / 'retrieval.json'),
        'repository': 'https://github.com/martinpiper/C64FindCode', 'commit': COMMIT,
        'all_tree_blobs_checked': len(files), 'source_files': files,
        'retained_release_inputs': inputs,
        'creator_linked_collection': meta(collection),
        'font_candidates': artwork_sources(artwork),
        'uploader_target_description': {
            'title': video['title'], 'description': video['shortDescription'],
            'videoId': video['videoId'], 'channelId': video['channelId'],
            'video_length_seconds_not_production_timing': int(video['lengthSeconds']),
        },
        'reviewed_primary_boundary': {
            'retained_hidden_page_has_no_submitted_hidden_entry': True,
            'creator_note_is_artwork_not_skip_instructions': True,
            'ending_pc_skip_key_production_timestamp_established': False,
        },
        'case_sensitive_source_bytes_hashed': True,
        'downloaded_source_executed': False,
        'limits': [
            'Content check is restricted to twelve blobs in this pinned repository.',
            'No title hit is not proof that unrelated generic code cannot be reused.',
            'A source fragment is not tied to the ending without original-release binding.',
            'No caption, transcript, video or media endpoint was requested.',
            'No native execution, CPU interpreter, runtime address or skip-key proof.'
        ]
    }
    (output / 'target-proof.json').write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'files': len(files), 'bytes': sum(r['source']['bytes'] for r in files),
                      'hits': sum(len(r['identifier_hits']) for r in files),
                      'proof': meta(output / 'target-proof.json')}))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--acquisition', type=Path, required=True)
    p.add_argument('--fetch', action='store_true')
    p.add_argument('--artwork', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.fetch:
        fetch(a.acquisition)
    analyze(a.acquisition, a.artwork, a.output)


if __name__ == '__main__':
    main()
