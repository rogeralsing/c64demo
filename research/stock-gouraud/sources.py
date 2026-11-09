#!/usr/bin/env python3
"""Replay retained primary author bodies; no network, archive program or CPU runs."""
import argparse
import hashlib
import html
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/stock-gouraud'
PRIMARY = BASE / 'primary'
OUTPUT_ROOT = BASE / 'analysis'
PINS = {
    'applause-release.body': '36ca885598013cafa52840014910800938b66b694f48e02c02e1c5b31587f8f8',
    'applause-release.json': '0e0dbcc81c49aadeec567544d34e80e04842f2d8226e137f8072ed6037ff55b4',
    'browar-interview.body': 'e281fd688d7b97f2515712e63c33184d7df3518e88978ffb34751990785ab65e',
    'browar-interview.json': '512777a1dbd5b6b483fbd83b0c2b15814f1b008a9b8b351cc2149785133e1b4c',
    'eod-author-note.json': 'e9e3b04cd22e588fd1fc9e1632096e18d8f0e65376255a1204cf8e9461135eb6',
    'eod-nfo-mirror.body': 'b8b52a2ba5ce98577d9047f69c1eb398d7e5d50c257537553b0c3faf629cb318',
    'eod-nfo-mirror.json': '883f2ce434e3d2e7b8972c65d8450f95ffcfaa0d01287d1ecda9cb4f8d16a679',
    'eod-release-zip.body': '21ec8560179a7ff4bf5c77b6102632f9a078aabddffea2f5534b304109ea353e',
    'eod-release-zip.json': '6df0182c8ab7b31896cdd50d05d4a16d67b660b025c3528e0c77791a4535174d',
    'eod-release.body': '2d67059b36131a0b60aecdaed7d7569c96f5c02d33202aa03cbe1d3c1c2b0d33',
    'eod-release.json': 'b799c4e3ff9b720a504c5bb4199329e2f4dd1184ed9d900996428b73c6f18daf',
    'mekanix-author-note.body': 'b0243bc21ecfa1f64f312108772a9e42b458c87f3f852746be91e94d944391ec',
    'mekanix-author-note.json': 'a3a1bb37796ff3a67d9cbf3df67e0881b67f8ad09a5ccc43af45b3527d9162ee',
}
URLS = {
    'eod-nfo-mirror': 'https://www.pouet.net/prod_nfo.php?which=51983',
    'eod-release': 'https://csdb.dk/release/?id=72550',
    'eod-release-zip': 'https://csdb.dk/getinternalfile.php/67631/EdgeOfDisgrace.zip',
    'eod-author-note': 'https://www.boozedesign.com/pub/eod_note.html',
    'mekanix-author-note': 'https://csdb.dk/release/?id=94438&show=notes',
    'browar-interview': 'https://attitude.triad.se/index.php?action=readtext&issue=3&which=7',
    'applause-release': 'https://csdb.dk/release/?id=4019',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def write(directory, name, data):
    raw = data.encode() if isinstance(data,str) else data
    (directory/name).write_bytes(raw)
    return dict(file=name,bytes=len(raw),sha256=sha(raw))


class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script','style'):
            self.hidden += 1
        if tag in ('br','p','div','tr','h1','h2','h3','li','pre'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script','style'):
            self.hidden -= 1
        if tag in ('p','div','tr','h1','h2','h3','li','pre'):
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)

    def text(self):
        return '\n'.join(line for part in ''.join(self.parts).splitlines()
                         if (line := re.sub(r'[ \t\r\f\v]+',' ',part).strip()))+'\n'


def page_text(body):
    parser = Text()
    parser.feed(body)
    assert parser.hidden == 0
    return parser.text()


def location(raw, text, needle, text_file):
    assert text.count(needle) == 1, needle
    at = text.index(needle)
    raw_at = raw.index(needle)
    return dict(needle=needle,text_file=text_file,text_line=text[:at].count('\n')+1,
                raw_body_line=raw[:raw_at].count('\n')+1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUTPUT_ROOT/'accepted-01')
    directory = parser.parse_args().output.expanduser().resolve()
    directory.relative_to(OUTPUT_ROOT.resolve())
    if directory.exists() and any(directory.iterdir()):
        raise SystemExit('Output must be fresh or empty; choose a new --output directory.')
    assert sorted(p.name for p in PRIMARY.iterdir()) == sorted(PINS)
    for name,pin in PINS.items():
        assert sha((PRIMARY/name).read_bytes()) == pin,name
    sources, bodies = [], {}
    for name,url in URLS.items():
        path = PRIMARY/(name+'.json')
        metadata = json.loads(path.read_text())
        assert metadata['name'] == name and metadata['requested_url'] == url and metadata['retrieved_utc']
        row = dict(name=name,url=url,metadata=artifact(path))
        if name == 'eod-author-note':
            assert metadata['transport_error'] == 'URLError' and 'status' not in metadata and 'body_file' not in metadata
            row.update(retrieved=False,transport_error=metadata['transport_error'],message=metadata['message'])
        else:
            body = PRIMARY/metadata['body_file']
            raw = body.read_bytes()
            assert body.name == name+'.body' and metadata['status'] == 200
            assert metadata['final_url'] == url and metadata['bytes'] == len(raw) and metadata['sha256'] == sha(raw)
            row.update(retrieved=True,status=200,final_url=metadata['final_url'],body=artifact(body))
            if name != 'eod-release-zip':
                # All claim anchors are ASCII; retained bodies remain exact.
                # Decode the actual advertised charset where present.
                content_type = next(v for k,v in metadata['headers'].items() if k.lower()=='content-type')
                charset = re.search(r'charset=([^;\s]+)',content_type,re.I)
                encoding = charset[1].strip('"') if charset else 'utf-8'
                bodies[name] = raw.decode(encoding)
                row['text_encoding'] = encoding
        sources.append(row)
    nfo_match = re.search(r'<pre[^>]*>(.*?)</pre>',bodies['eod-nfo-mirror'],re.I|re.S)
    assert nfo_match
    nfo = html.unescape(re.sub(r'<[^>]*>','',nfo_match[1])).replace('\r\n','\n')
    assert 'hcl on the keys..' in nfo and 'released at x-2008' in nfo
    dither_start = nfo.index('ditheredvector:')
    dither_end = nfo.index('ab-zoom:',dither_start)
    section = nfo[dither_start:dither_end]
    for phrase in ['gouraud-shader','16-bit calculations and perspective','tracing-line',
                   '13 dithered','three out of four iterations','plotting a zero']:
        assert phrase in section,phrase
    assert 'gouraud-styledtexture' in nfo[nfo.index('x-vector:'):nfo.index('x-vector-plasma:')]
    mekanix = page_text(bodies['mekanix-author-note'])
    browar = page_text(bodies['browar-interview'])
    eod_identity, applause_identity = page_text(bodies['eod-release']), page_text(bodies['applause-release'])
    assert 'C64 Demo' in eod_identity and 'Edge of Disgrace' in eod_identity
    assert 'Submitted by HCL on 6 December 2011' in mekanix and 'C64 Demo' in mekanix
    assert 'Gouraud: (HCL) Enhanced from EoD.' in mekanix
    assert 'BROWAR/ARISE:' in browar and 'Multicolour gouraud zbuffer from' in browar
    assert 'Applause' in applause_identity and 'Browar' in applause_identity and 'C64 Demo' in applause_identity
    members = []
    with zipfile.ZipFile(io.BytesIO((PRIMARY/'eod-release-zip.body').read_bytes())) as archive:
        assert len(archive.infolist()) == 3
        for entry in archive.infolist():
            assert Path(entry.filename).name == entry.filename and entry.file_size == 174848
            assert entry.filename.lower().endswith('.d64')
            raw = archive.read(entry)  # ZIP CRC validated; plain data only.
            members.append(dict(name=entry.filename,bytes=len(raw),sha256=sha(raw),ZIP_CRC32=f'{entry.CRC:08x}'))
    directory.mkdir(parents=True,exist_ok=True)
    outputs = [write(directory,'eod-nfo.txt',nfo),write(directory,'mekanix-author-note.txt',mekanix),
        write(directory,'browar-interview.txt',browar),write(directory,'eod-release.txt',eod_identity),
        write(directory,'applause-release.txt',applause_identity),write(directory,'sources.checked.py',Path(__file__).read_bytes())]
    anchors = {
        'author_identity': location(bodies['eod-nfo-mirror'],nfo,'hcl on the keys..','eod-nfo.txt'),
        'earlier_texture': location(bodies['eod-nfo-mirror'],nfo,'x-vector:','eod-nfo.txt'),
        'shader_section': location(bodies['eod-nfo-mirror'],nfo,'ditheredvector:','eod-nfo.txt'),
        'shader_next_section': location(bodies['eod-nfo-mirror'],nfo,'ab-zoom:','eod-nfo.txt'),
        'mekanix_lineage': location(bodies['mekanix-author-note'],mekanix,'Gouraud: (HCL) Enhanced from EoD.','mekanix-author-note.txt'),
        'browar_claim': location(bodies['browar-interview'],browar,'Multicolour gouraud zbuffer from','browar-interview.txt'),
    }
    result = dict(pass_=True,producer=artifact(Path(__file__).resolve()),sources=sources,
        all_primary_input_artifacts=[artifact(PRIMARY/name) for name in PINS],locations=anchors,
        EOD_release_archive=dict(members=members,plain_NFO_text_members=0,mirror_equals_original_payload_proved=False,
            limit='Archive has only three disk images. No disk-note program is depacked or executed; absence of a plain NFO ZIP member does not mean absence of an in-demo note.'),
        author_mechanism=dict(author='HCL/Booze Design',
            description='Author describes 16-bit perspective Gouraud using traced shade boundaries and 13 dither levels/four colors, contrasting an earlier Gouraud-styled texture with the later shader.',
            three_of_four_skip='Author claim for zero plots on thin lines between neighboring dither levels; no original shader code or independent algebra/pixel/timing verification here.',
            evidence_tier='Detailed primary author algorithm description, not independently verified original shader implementation.'),
        supporting_claims=[dict(production='Mekanix',author='HCL',evidence='Author says enhanced from EoD; lineage only, not a new source-code/interpolation proof.'),
            dict(production='Applause',author='Browar',evidence='Coder identifies his own multicolor Gouraud Z-buffer; this interview gives no interpolation algorithm or clock proof.')],
        stock_clock_limit='Release identities say C64 Demo. No explicit 1MHz qualification, accelerator exclusion, native CPU-clock measurement or performance acceptance is established by this lane.',
        original_shader_source_found=False,outputs=outputs,
        limits=['No timing, FPS, native pixels or general shading-correctness claims.',
            'The failed author-domain fetch is retained as a transport failure; its body/status is not invented.',
            'Primary HTTP bodies and metadata are pinned inputs. Replay performs no network request, archive executable, native run or build.',
            'No qualifying Crest source was found in this bounded discovery; these author claims do not substitute for shader code inspection.'])
    receipt = write(directory,'source-proof.json',json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(output=str(directory),receipt=receipt,locations=anchors,release_members=members),indent=2))


if __name__ == '__main__':
    main()
