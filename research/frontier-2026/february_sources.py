#!/usr/bin/env python3
"""Archive bounded primary-source leads for The Hat and Aloft (February 2026).

No C64 program, CPU interpreter, emulator, downloaded host code or process is
run. Artist/author notes, peer comments and unrecovered mechanism evidence
remain explicitly distinct.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'build/research/frontier-2026/february-analysis'
TRIDENT_CODE_COMMIT = '80d1027742815e55cda13a80cb4826744dd75c83'
TRIDENT_SITE_COMMIT = '9c8bac3711136ca7d44b476bb8a962fa3bfab4d9'
ROUTES = [
    ('the-hat.html', 'https://csdb.dk/release/?id=259070'),
    ('aloft.html', 'https://csdb.dk/release/?id=259056'),
    ('the-hat-notes.html', 'https://csdb.dk/release/?id=259070&show=notes'),
    ('aloft-notes.html', 'https://csdb.dk/release/?id=259056&show=notes'),
    ('the-hat-hidden.html', 'https://csdb.dk/release/?id=259070&show=hidden'),
    ('aloft-hidden.html', 'https://csdb.dk/release/?id=259056&show=hidden'),
    ('the-hat-original.zip', 'https://csdb.dk/getinternalfile.php/276889/the_hat-flt%26gp.zip'),
    ('aloft-original.zip', 'https://csdb.dk/getinternalfile.php/276871/Aloft.zip'),
    ('quiss-home.html', 'https://www.quiss.org/'),
    ('raistlin-index.md', 'https://c64demo.com/llms.txt'),
    ('trident-branches.json', 'https://api.github.com/repos/trident64/c64/branches?per_page=100'),
    ('sparta-repos.json', 'https://api.github.com/users/spartaomg/repos?per_page=100'),
    ('raistlin-branches.json', 'https://api.github.com/repos/RobertTroughton/C64Demo-PublicReleases/branches?per_page=100'),
    ('quiss-repos.json', 'https://api.github.com/users/matthiaskramm/repos?per_page=100'),
    ('trident-repos.json', 'https://api.github.com/users/trident64/repos?per_page=100'),
    ('raistlin-repos.json', 'https://api.github.com/users/RobertTroughton/repos?per_page=100'),
    ('trident-commit.json', f'https://api.github.com/repos/trident64/c64/commits/{TRIDENT_CODE_COMMIT}'),
    ('trident-tree.json', 'https://api.github.com/repos/trident64/c64/git/trees/7d1d2ccce83e1f61f5f0db434a988ca9d3af845f?recursive=1'),
    ('trident-site-commit.json', f'https://api.github.com/repos/trident64/trident64.github.io/commits/{TRIDENT_SITE_COMMIT}'),
    ('trident-site-tree.json', 'https://api.github.com/repos/trident64/trident64.github.io/git/trees/0101a59423bb948f52b6bf6375742c5504ce84cf?recursive=1'),
    ('the-hat-art.html', 'https://c64gfx.com/release/259070'),
    ('piper-end-scroller.json', 'https://www.youtube.com/oembed?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DVfnyczaf1Ao&format=json'),
    ('trident-talk.json', 'https://www.youtube.com/oembed?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DtqX42YoncaA&format=json'),
    ('overlapping-irq.html', 'https://trident64.github.io/overlapping-irq-handlers/'),
]
GIT_FILES = [
    ('trident64/c64', TRIDENT_CODE_COMMIT, 'trident-tree.json', 'README.md'),
    ('trident64/trident64.github.io', TRIDENT_SITE_COMMIT, 'trident-site-tree.json', 'index.html'),
    ('trident64/trident64.github.io', TRIDENT_SITE_COMMIT, 'trident-site-tree.json', 'feed.xml'),
    ('trident64/trident64.github.io', TRIDENT_SITE_COMMIT, 'trident-site-tree.json', 'overlapping-irq-handlers/index.html'),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=sha(data))


def fetch(name, url):
    row = dict(requested_url=url, requested_utc=datetime.now(timezone.utc).isoformat())
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'c64demo-primary-source-research'})
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read(4_000_001)
            assert len(data) <= 4_000_000, ('Bounded acquisition limit', url)
            row.update(status=response.status, final_url=response.url,
                       content_type=response.headers.get('Content-Type'),
                       pagination_link=response.headers.get('Link'))
        path = OUT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_bytes() != data:
            old = path.with_name(path.name + '.before-receipt-' + sha(path.read_bytes())[:12])
            if not old.exists(): old.write_bytes(path.read_bytes())
        path.write_bytes(data)
        row.update(success=True, artifact=record(path))
    except (urllib.error.URLError, TimeoutError) as error:
        row.update(success=False, error=str(error))
    return row


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.links, self.skip = [], [], 0
        self.code, self.codes = None, []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.skip += 1
        if tag == 'code': self.code = []
        if tag == 'a':
            target = dict(attrs).get('href')
            if target: self.links.append(target)

    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.skip -= 1
        if tag == 'code' and self.code is not None:
            self.codes.append(''.join(self.code)); self.code = None

    def handle_data(self, data):
        if not self.skip: self.parts.append(data)
        if self.code is not None: self.code.append(data)

    @property
    def text(self):
        return ' '.join(' '.join(self.parts).split())


def page(name):
    parser = Text(); parser.feed((OUT / name).read_text())
    return parser


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true', help='Acquire missing bounded routes, retaining successful cached receipts.')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    requests = list(ROUTES)
    requests += [(f'source/{repo}/{path}', f'https://raw.githubusercontent.com/{repo}/{commit}/{path}')
                 for repo, commit, tree, path in GIT_FILES]
    ledger_path = OUT / 'acquisitions.json'
    if args.fetch:
        prior = {r['requested_url']: r for r in json.loads(ledger_path.read_text())} if ledger_path.exists() else {}
        routes = []
        for name, url in requests:
            row = prior.get(url)
            if row and row['success']:
                assert record(ROOT / row['artifact']['path']) == row['artifact']
            else:
                row = fetch(name, url)
            routes.append(row)
        ledger_path.write_text(json.dumps(routes, indent=2) + '\n')
    routes = json.loads(ledger_path.read_text())
    assert [r['requested_url'] for r in routes] == [url for name, url in requests]
    for row in routes:
        if row['success']: assert record(ROOT / row['artifact']['path']) == row['artifact']
    source_bindings = []
    for repo, commit, tree_name, path in GIT_FILES:
        tree = json.loads((OUT / tree_name).read_text())
        commit_name = 'trident-commit.json' if repo == 'trident64/c64' else 'trident-site-commit.json'
        commit_object = json.loads((OUT / commit_name).read_text())
        assert commit_object['sha'] == commit and tree['sha'] == commit_object['commit']['tree']['sha']
        assert not tree['truncated']
        leaf = next(x for x in tree['tree'] if x['path'] == path and x['type'] == 'blob')
        local = OUT / 'source' / repo / path
        data = local.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        assert blob == leaf['sha'] and len(data) == leaf['size']
        source_bindings.append(dict(repo=repo, commit=commit, repository_path=path,
                                    git_blob_sha1=blob, artifact=record(local)))
    archives = []
    for name in ('the-hat-original.zip', 'aloft-original.zip'):
        path = OUT / name
        with zipfile.ZipFile(io.BytesIO(path.read_bytes())) as archive:
            members = [dict(name=i.filename, bytes=i.file_size, sha256=sha(archive.read(i)))
                       for i in archive.infolist() if not i.is_dir()]
        d64s = [m for m in members if m['name'].lower().endswith('.d64')]
        assert len(d64s) == (2 if name.startswith('the-hat') else 3)
        assert all(m['bytes'] == 174848 for m in d64s)
        archives.append(dict(artifact=record(path), members=members,
                             published_source_or_text_notes=[m['name'] for m in members
                                 if m['name'].lower().endswith(('.asm', '.s', '.c', '.cpp', '.nfo', '.diz', '.txt', '.md'))],
                             scope='Archive inventory only; D64 internals and executable code are not decoded.'))
    extracts = []
    for name, marker, classification in [
        ('the-hat-notes.html', 'Production Info Submitted by redcrab', 'Primary artist statement, not an upscroller algorithm.'),
        ('aloft-notes.html', 'Production Info Submitted by Mermaid', 'Primary artist workstages and concrete asset description.'),
        ('aloft-hidden.html', 'Hidden Parts Info Submitted by Sparta', 'Primary coder interaction claim, not a render mechanism.'),
        ('aloft-hidden.html', 'Hidden Parts Info Submitted by Quiss', 'Primary coder interaction claim, separate from Kefrens.'),
    ]:
        text = page(name).text
        found = [m.start() for m in re.finditer(re.escape(marker), text)]
        assert found, (name, marker)
        for position in found:
            tail = text[position:]
            stops = [tail.find(s, len(marker)) for s in ['Production Info Submitted by', 'Hidden Parts Info Submitted by', 'Search CSDb']]
            end = min(n for n in stops if n >= 0)
            extracts.append(dict(page=name, classification=classification, text=tail[:end].strip()))
    peers = []
    for name, author in [('the-hat.html', 'Quiss'), ('the-hat.html', 'HCL'),
                         ('the-hat.html', 'Clarence'), ('aloft.html', 'trident'), ('aloft.html', 'HCL')]:
        comments = re.split('User Comment', page(name).text)[1:]
        matched = next(c.strip() for c in comments if c.strip().startswith('Submitted by ' + author + ' on '))
        peers.append(dict(page=name, author=author, text=matched,
                          classification='Peer/viewer observation on this production, not a credited coder explanation of its mechanism.'))
    inventory = []
    for name in ['quiss-repos.json', 'trident-repos.json', 'sparta-repos.json', 'raistlin-repos.json']:
        repos = json.loads((OUT / name).read_text())
        assert len(repos) < 100
        route = next(r for r in routes if r.get('artifact', {}).get('path') == str((OUT / name).relative_to(ROOT)))
        assert not route['pagination_link'] or 'rel="next"' not in route['pagination_link']
        inventory.append(dict(artifact=record(OUT / name), repository_names=[r['name'] for r in repos],
                              scope='One complete public-repository listing at acquisition time; no assertion about private repositories or every file in unrelated projects.'))
    published = page('overlapping-irq.html')
    immutable = page('source/trident64/trident64.github.io/overlapping-irq-handlers/index.html')
    example = next(code for code in published.codes if 'BasicUpstart(start)' in code and 'irq_call_wait_rasterline' in code)
    assert example in immutable.codes, 'Live article example differs from the pinned immutable source.'
    example_path = OUT / 'source/overlapping-irq-full-example.asm'
    example_path.write_text(example)
    atom = ET.fromstring((OUT / 'source/trident64/trident64.github.io/feed.xml').read_bytes())
    ns = {'a': 'http://www.w3.org/2005/Atom'}
    entry = next(e for e in atom.findall('a:entry', ns) if e.find('a:id', ns).text == '/overlapping-irq-handlers')
    technique = dict(title=entry.find('a:title', ns).text, published=entry.find('a:published', ns).text,
                     author='Trident', url='https://trident64.github.io/overlapping-irq-handlers/',
                     complete_example=record(example_path), live_and_immutable_example_text_equal=True,
                     scope='Published generic nested-IRQ technique and full example, not a recovered Hat/Aloft effect implementation. No assembly, CPU or native timing check.')
    report = dict(script=record(Path(__file__).resolve()), acquisitions=routes,
                  publication_identity=[dict(title='The Hat', release_id=259070, release_page='https://csdb.dk/release/?id=259070',
                      CSDb_date='2026-02-01', groups=['Fairlight', 'Genesis Project'], coders=['Alfatech', 'Trident']),
                      dict(title='Aloft', release_id=259056, release_page='https://csdb.dk/release/?id=259056',
                      CSDb_date='2026-02-01', groups=['Quiss', 'Genesis Project'], coders=['Quiss', 'Raistlin', 'Scrap', 'Sparta'])],
                  primary_statements=extracts, peer_statements=peers, original_archives=archives,
                  published_repository_sources=source_bindings, public_repository_inventories=inventory,
                  separate_published_general_technique=technique,
                  mechanism_evidence=dict(the_hat_all_border_upscroll='No creator-authored explanation or full effect source recovered in this bounded pass.',
                      aloft_three_layer_pattern='No creator-authored explanation or full effect source recovered in this bounded pass.',
                      aloft_bitmap_kefrens='No creator-authored render explanation or full effect source recovered; joystick-control statement recovered.',
                      caveat='Not a claim that such material is absent from the Internet, private code or embedded disk notes.'),
                  scope='Bounded primary publication/credit/artist/coder-note inventory, repository/source provenance and original ZIP member hashes. No video-transcript, binary-mechanism, CPU/native, timing, visual or historical-first proof.',
                  pass_=True)
    report['pass'] = report.pop('pass_')
    output = OUT / 'source-findings.json'
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(passed=True, routes=len(routes), successful=sum(r['success'] for r in routes),
                          failed=[r['requested_url'] for r in routes if not r['success']],
                          primary_statements=len(extracts), archives=len(archives),
                          receipt=str(output.relative_to(ROOT))), indent=2))


if __name__ == '__main__':
    main()
