#!/usr/bin/env python3
"""Retain/parse Perpetual Fragility's actual author article and layout data.

Replay is passive: no network, downloaded host execution, CPU interpreter,
assembler, native process, bitmap simulation, or repeated offset-orbit proof.
"""
import argparse
import hashlib
import json
import re
import struct
import zlib
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[2]
ACQUISITION = 'build/research/perpetual-20261109/primary-analysis/acquisition-01/'
MANIFEST_SHA = 'f5aad291d53fc6bc511d5254f20931a89aad072d9331bc8bf88f4c5159989c66'
ARTICLE_URL = 'https://www.linusakesson.net/scene/perpetual-fragility/index.php'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def ref(path):
    path = Path(path)
    data = path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=len(data), sha256=sha(data))


def output(out, name, value):
    data = json.dumps(value, indent=2, ensure_ascii=False)+'\n'
    (out/name).write_text(data)


class ArticleHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text, self.links, self.images, self.frames, self.pre = [], [], [], [], []
        self.pre_data, self.in_pre = [], False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a':
            assert 'href' in attrs
            self.links.append(attrs['href'])
        if tag == 'img':
            self.images.append(attrs['src'])
        if tag == 'iframe':
            self.frames.append(attrs['src'])
        if tag == 'pre':
            assert not self.in_pre
            self.pre_data, self.in_pre = [], True

    def handle_endtag(self, tag):
        if tag == 'pre':
            assert self.in_pre
            self.pre.append(''.join(self.pre_data))
            self.in_pre = False

    def handle_data(self, text):
        self.text.append(text)
        if self.in_pre:
            self.pre_data.append(text)


def parse(fragment):
    parser = ArticleHTML()
    parser.feed(fragment)
    assert not parser.in_pre
    return parser, ' '.join(' '.join(parser.text).split())


def png(data):
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    cursor, chunks = 8, []
    while cursor < len(data):
        count = struct.unpack('>I', data[cursor:cursor+4])[0]
        kind = data[cursor+4:cursor+8]
        value = data[cursor+8:cursor+8+count]
        check = struct.unpack('>I', data[cursor+8+count:cursor+12+count])[0]
        assert check == zlib.crc32(kind+value)
        chunks.append(dict(type=kind.decode('ascii'), bytes=count))
        if kind == b'IHDR':
            width, height, depth, colour, compression, filter_, interlace = struct.unpack('>IIBBBBB', value)
            assert compression == filter_ == 0 and interlace in (0, 1)
        cursor += count+12
        if kind == b'IEND':
            break
    assert cursor == len(data) and chunks[-1] == dict(type='IEND', bytes=0)
    return dict(width=width, height=height, depth=depth, colour_type=colour,
                interlace=interlace, all_chunk_CRCs_match=True, chunks=chunks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = ROOT/args.output
    out.mkdir(parents=True, exist_ok=False)
    (out/'primary.checked.py').write_bytes(Path(__file__).read_bytes())
    manifest_path = ROOT/ACQUISITION/'http-retention.json'
    assert sha(manifest_path.read_bytes()) == MANIFEST_SHA
    manifest = json.loads(manifest_path.read_bytes())
    assert len(manifest['attempts']) == 6
    bodies = {}
    for row in manifest['attempts']:
        assert row['status'] == 200 and row['TLS_verification_bypassed'] is False
        assert ref(ROOT/row['body']['path']) == row['body']
        bodies[row['label']] = row
    assert set(bodies) == {'author-article'} | {f'diagram{i}' for i in range(1, 6)}
    body_path = ROOT/bodies['author-article']['body']['path']
    raw = body_path.read_bytes()
    start = raw.index(b'<h1>Perpetual Fragility</h1>')
    forum = re.search(br'<h3[^>]*>Discuss this page</h3>', raw)
    assert forum and start < forum.start()
    end = forum.start()
    article = raw[start:end]
    page, text = parse(article.decode('utf-8'))
    (out/'author-content.html').write_bytes(article)
    sections = list(re.finditer(br'<h2>([^<]+)</h2>', article))
    assert len(sections) == 11
    sources = {}
    for index, match in enumerate(sections):
        last = sections[index+1].start() if index+1 < len(sections) else len(article)
        fragment = article[match.start():last]
        _, words = parse(fragment.decode('utf-8'))
        heading = match[1].decode('utf-8')
        sources[heading] = dict(heading=heading, byte_first=start+match.start(),
                               byte_end_exclusive=start+last,
                               fragment_sha256=sha(fragment), text=words)
    required = {
        'Main graphics': ['linecrunch', 'VSP', 'AGSP', 'bitmap'],
        'Sprites': ['high-resolution', 'X-expanded'],
        'Let it snow!': ['list of coordinates', 'animation order', '595', '1024'],
        'Through the looking-glass': ['40 bytes', 'first two and last two', 'middle 36',
                                    'sprite-pointer area', 'inhibit', 'bank switch'],
        'A busy schedule': ['compile-time', 'code snippets', 'greedy algorithm'],
        'Rounding it off': ['1156', '1496', 'misdirection']}
    # These claims are article authority, not evidence that released code has
    # already passed a corresponding data/timing/native check.
    for heading, terms in required.items():
        assert all(term in sources[heading]['text'] for term in terms), heading
    output(out, 'author-claims.json', dict(
        pass_=True, article_source=ref(body_path), author_content_range=[start, end],
        author_content_sha256=sha(article), sections=list(sources.values()),
        article_claims_are_not_new_native_or_machine_code_proofs=True,
        code_binding_requirements=[
            dict(claim='Coordinate-list deposition', require='Identify actual list boundary, producer/consumer and each bitmap read/modify/write from released bytes'),
            dict(claim='Repeated 40-cell colour stencil', require='Independently derive its destination/values and establish actual VIC c-buffer fetching and retained lifetime'),
            dict(claim='Matrix versus sprite-pointer bank separation', require='Bind real memory selection writes, pointer fetch domains and actual timing'),
            dict(claim='Compiled timing schedule', require='Inspect released schedule and its observed execution; the author assertion alone does not recover compiler source or deadlines'),
            dict(claim='Sprites versus snowfall', require='Identify actual sprite data/positions/modes and bitmap payload; do not equate diagram coordinates with VIC X/Y without a mapping')]))
    downloads = [urljoin(ARTICLE_URL, link) for link in page.links if '/files/' in link]
    assert len(downloads) == 4 and sum(url.endswith('.prg') for url in downloads) == 3
    assert sum(url.endswith('.mp3') for url in downloads) == 1
    assert not [link for link in page.links if re.search(r'\.(zip|tar|gz|asm|s|c|h|py|js|txt)(?:$|[?#])', link, re.I)]
    figure_urls = sorted({urljoin(ARTICLE_URL, link) for link in page.images+page.links
                          if re.fullmatch(r'diagram[1-5]\.png', link)})
    assert figure_urls == [urljoin(ARTICLE_URL, f'diagram{i}.png') for i in range(1, 6)]
    comments = []
    for header, message in re.findall(br'<div class="forum1">(.*?)</div><div class="forum2">(.*?)</div>', raw[end:], re.S):
        _, author = parse(header.decode('utf-8'))
        _, message = parse(message.decode('utf-8'))
        comments.append(dict(header=author, message_sha256=sha(message.encode()),
                             authenticated_author_reply=('Linus Åkesson' in author and 'lft' in author)))
    assert len(comments) == 3 and not any(row['authenticated_author_reply'] for row in comments)
    output(out, 'article-link-inventory.json', dict(
        pass_=True, article_source=ref(body_path), links=page.links,
        resolved_links=[urljoin(ARTICLE_URL, link) for link in page.links],
        downloadable_file_links=downloads, author_figure_urls=figure_urls,
        embedded_video_links=page.frames, embedded_videos_not_requested=True,
        explicit_linked_source_or_readme_downloads=[], comments=comments,
        no_author_reply_in_current_comment_headers=True,
        negative_scope='Explicit links in the author article and acquired comment headers only; not a proof about unpublished/private/site-wide source'))
    assert len(page.pre) == 1
    rows = []
    for line in page.pre[0].splitlines():
        if line:
            match = re.fullmatch(r'([0-9a-f]+) (.*)', line)
            assert match and len(match[2]) == 207
            value = match[2]
            assert set(value) <= set(' -=*#')
            rows.append(dict(label_hex=match[1], label_integer=int(match[1], 16),
                             characters=value,
                             normal_width_markers=[i for i, c in enumerate(value) if c == '-'],
                             expanded_width_markers=[i for i, c in enumerate(value) if c == '='],
                             opaque_art_positions=[i for i, c in enumerate(value) if c in '*#']))
    assert len(rows) == 149 and rows[0]['label_integer'] == 0x1f and rows[-1]['label_integer'] == 0xb3
    assert all(b['label_integer'] == a['label_integer']+1 for a, b in zip(rows, rows[1:]))
    counts = Counter(''.join(row['characters'] for row in rows))
    assert sum(counts.values()) == 149*207
    (out/'author-tree-ascii.txt').write_text(page.pre[0])
    output(out, 'author-tree-layout.json', dict(
        pass_=True, source=ref(body_path), rows=rows, row_count=149, column_count=207,
        character_counts=dict(counts),
        source_interpretation='Author describes - as normal-width/hires strips and = as X-expanded strips; */# retain their literal artwork labels',
        actual_VIC_coordinate_origin_or_DMA_schedule_proved=False,
        mapping_into_original_sprite_memory_proved=False,
        pixels_or_palette_reconstructed=False))
    figures = []
    for i in range(1, 6):
        path = ROOT/bodies[f'diagram{i}']['body']['path']
        detail = png(path.read_bytes())
        assert (detail['width'], detail['height']) == ((600, 350) if i < 5 else (1800, 1050))
        figures.append(dict(source=ref(path), requested_url=bodies[f'diagram{i}']['requested_url'], **detail))
    output(out, 'author-figure-metadata.json', dict(
        pass_=True, figures=figures,
        role='Actual author diagrams of illustrative animation phases and nonrectangular address layout',
        diagram_labels_not_treated_as_original_snowflake_coordinates=True,
        no_new_offset_orbit_or_synthetic_fixture=True))
    outputs = [dict(name=path.name, bytes=path.stat().st_size, sha256=sha(path.read_bytes()))
               for path in sorted(out.iterdir())]
    proof = dict(pass_=True, schema='perpetual-primary-source-and-author-layout-v1',
                 producer=ref(Path(__file__).resolve()), HTTP_manifest=ref(manifest_path),
                 HTTP_attempts=6, HTTP200_bodies=6,
                 retained_HTTP_body_bytes=sum(row['body']['bytes'] for row in bodies.values()),
                 author_source=ref(body_path), outputs=outputs,
                 actual_author_tree_rows=149, actual_author_tree_columns=207,
                 source_code_download_link_recovered=False,
                 real_released_payload_or_native_outputs_used_as_inputs=False,
                 prior_595_or_odd_step_result_not_recounted_as_new=True,
                 no_CPU_native_build_or_downloaded_host_execution=True,
                 limits=['This is primary author evidence and exact layout extraction, not a source-to-binary timing or pixel proof',
                         'The displayed abstract WIZ phase diagrams are not actual snowflake coordinate tables',
                         'Current article comments provide no authenticated lft reply and are not technical authority'])
    output(out, 'primary-proof.json', proof)
    print(json.dumps(dict(pass_=True, output=args.output, files=len(outputs)+1,
                          tree_rows=149, tree_columns=207,
                          explicit_source_download_found=False)))


if __name__ == '__main__':
    main()
