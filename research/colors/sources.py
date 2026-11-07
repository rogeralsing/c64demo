#!/usr/bin/env python3
"""Acquire a bounded set of Colors author-source leads; never run C64 code.

Default analysis is offline. --fetch preserves responses and failure metadata
under this lane's ignored output directory. It does not touch the release,
disk acquisition, depacker or native checker owned by other agents.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html import unescape
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'build/research/colors/source-analysis'
PAGES = (
    ('group.html', 'https://csdb.dk/group/?id=612'),
    ('coder-dev0.html', 'https://csdb.dk/scener/?id=35906'),
    ('coder-ego.html', 'https://csdb.dk/scener/?id=19196'),
    ('coder-schedar.html', 'https://csdb.dk/scener/?id=34619'),
    ('coder-strepto.html', 'https://csdb.dk/scener/?id=13717'),
    ('musician-vincenzo.html', 'https://csdb.dk/scener/?id=4559'),
    ('group-http.html', 'http://lethargy.hu/'),
    ('group-https.html', 'https://lethargy.hu/'),
    ('publication.html', 'https://medium.com/c64-dev'),
    ('publication-feed.xml', 'https://medium.com/feed/c64-dev'),
    ('pouet.html', 'https://m.pouet.net/prod.php?which=106373'),
    ('group-releases.html', 'http://lethargy.hu/releases'),
    ('group-members.html', 'http://lethargy.hu/members'),
    ('group-social.html', 'http://lethargy.hu/elerhetoseg'),
    ('group-search-colors.html', 'http://lethargy.hu/?s=Colors'),
    ('linked-video.html', 'https://www.youtube.com/watch?v=9LWkHRAvNyA'),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def plain(text):
    text = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', '', text, flags=re.S | re.I)
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]*>', ' ', text))).strip()


def links(text, base):
    result = []
    for match in re.finditer(r'<a\b[^>]*href\s*=\s*[\"\']([^\"\']+)[\"\'][^>]*>(.*?)</a>', text, re.S | re.I):
        url = urllib.parse.urljoin(base, unescape(match[1]))
        if urllib.parse.urlsplit(url).scheme not in ('http', 'https'):
            continue
        item = dict(url=url, label=plain(match[2]))
        if item not in result:
            result.append(item)
    return result


def fetch(pair):
    name, url = pair
    record = dict(name=name, requested_url=url, requested_utc=datetime.now(timezone.utc).isoformat())
    request = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 C64 author-source research'})
    try:
        try:
            response = urllib.request.urlopen(request, timeout=15)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            data = response.read(3_000_001)
            assert len(data) <= 3_000_000, 'Source-page response exceeded the bounded text limit'
            record.update(final_url=response.geturl(), http_status=response.status,
                          headers={key:response.headers[key] for key in ('Content-Type', 'Content-Length', 'ETag', 'Last-Modified') if key in response.headers},
                          success=200 <= response.status < 300, bytes=len(data), sha256=sha(data))
        target = OUT/name
        if target.exists() and target.read_bytes() != data:
            old = OUT/(name+'.previous-'+sha(target.read_bytes())[:12])
            if not old.exists():
                old.write_bytes(target.read_bytes())
        target.write_bytes(data)
        record['path'] = str(target.relative_to(ROOT))
    except (OSError, urllib.error.URLError, AssertionError) as error:
        record.update(success=False, error_type=type(error).__name__, error=str(error),
                      http_status=None, path=None, bytes=None, sha256=None)
    return record


def comments(text):
    pattern = re.compile(r'<b>User Comment</b><br>Submitted by <b><a href="/scener/\?id=(\d+)">(.*?)</a></b> on ([^<]+)<br\s*/?>', re.S)
    result = []
    for match in pattern.finditer(text):
        end = text.find('</font></td></tr></table>', match.end())
        assert end != -1
        result.append(dict(scener_id=int(match[1]), handle=plain(match[2]), date=plain(match[3]),
                           text=plain(text[match.end():end])))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true', help='Fetch only the listed public text endpoints.')
    parser.add_argument('--fetch-missing', action='store_true', help='Fetch newly listed routes while preserving previous response receipts.')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    ledger = OUT/'acquired-pages.json'
    if args.fetch or args.fetch_missing:
        previous = json.loads(ledger.read_text()) if args.fetch_missing and ledger.exists() else []
        previous_names = {row['name'] for row in previous}
        with ThreadPoolExecutor(max_workers=4) as pool:
            acquisitions = previous+list(pool.map(fetch, [pair for pair in PAGES if pair[0] not in previous_names]))
        if ledger.exists():
            old_ledger = OUT/('acquired-pages.previous-'+sha(ledger.read_bytes())[:12]+'.json')
            if not old_ledger.exists():
                old_ledger.write_bytes(ledger.read_bytes())
        ledger.write_text(json.dumps(acquisitions, indent=2)+'\n')
    else:
        acquisitions = json.loads(ledger.read_text())
    # Reuse the other lane's original preserved release; do not refetch or
    # rewrite the archive, release page, acquisition receipt or D64 files.
    original_receipt = ROOT/'build/research/colors/acquisition.json'
    acquisition = json.loads(original_receipt.read_text())
    release_path = ROOT/'build/research/colors/release.html'
    release = release_path.read_bytes()
    expected = next(row for row in acquisition['acquisitions'] if row['path'].endswith('/release.html'))
    assert sha(release) == expected['sha256']
    release_text = release.decode()
    credits_section = release_text.split('<b>Credits :</b><br>', 1)[1].split('SIDs used', 1)[0]
    credited = {int(value) for value in re.findall(r'/scener/\?id=(\d+)', credits_section)}
    coders = {35906, 19196, 34619, 13717}
    review = comments(release_text)
    assert len(review) == 36, 'Pinned release comment parser no longer matches the preserved body'
    for item in review:
        item['credited_participant'] = item['scener_id'] in credited
        item['credited_coder'] = item['scener_id'] in coders
        item['scope'] = ('Credited participant statement; content still determines what it supports.'
                         if item['credited_participant'] else 'Viewer/commenter statement; not identified here as an author explanation.')
    (OUT/'release-comments.json').write_text(json.dumps(review, indent=2, ensure_ascii=False)+'\n')
    page_analysis = []
    for record in acquisitions:
        item = dict(acquisition=record)
        if record['path']:
            path = ROOT/record['path']
            data = path.read_bytes()
            assert sha(data) == record['sha256']
            if record['success']:
                decoded = data.decode('utf-8', errors='replace')
                title = re.search(r'<title[^>]*>(.*?)</title>', decoded, re.S | re.I)
                all_links = links(decoded, record['final_url'])
                external = [link for link in all_links if urllib.parse.urlsplit(link['url']).netloc != urllib.parse.urlsplit(record['final_url']).netloc]
                item.update(title=plain(title[1]) if title else None, external_links=external,
                            repository_links=[link for link in all_links if urllib.parse.urlsplit(link['url']).netloc in ('github.com','gitlab.com','bitbucket.org')],
                            relevant_text_mentions=[plain(decoded[max(0,m.start()-120):m.end()+180]) for m in re.finditer(r'Colors|github|source code', decoded, re.I)][:30])
                if record['name'].endswith('.xml'):
                    try:
                        tree = ET.fromstring(data)
                        item['feed_items'] = [dict(title=node.findtext('title'), url=node.findtext('link'), date=node.findtext('pubDate')) for node in tree.findall('.//item')]
                    except ET.ParseError as error:
                        item['feed_parse_error'] = str(error)
                if record['name'] == 'linked-video.html':
                    marker = re.search(r'(?:var\s+)?ytInitialPlayerResponse\s*=\s*', decoded)
                    if marker:
                        player, _ = json.JSONDecoder().raw_decode(decoded[marker.end():])
                        details = player.get('videoDetails', {})
                        item['video_text_metadata'] = {key:details.get(key) for key in ('videoId','title','author','channelId','shortDescription')}
                        item['video_playability'] = player.get('playabilityStatus')
                        captions = player.get('captions', {}).get('playerCaptionsTracklistRenderer', {}).get('captionTracks', [])
                        item['caption_track_metadata'] = [dict(language=track.get('languageCode'),
                                                                kind=track.get('kind'),
                                                                name=track.get('name')) for track in captions]
                        item['caption_scope'] = 'Metadata only. Automatic speech recognition is not an author technical explanation; no captions or media are downloaded.'
                    else:
                        item['video_text_metadata_available'] = False
        page_analysis.append(item)
    by_name = {row['acquisition']['name']:row for row in page_analysis}
    video = by_name.get('linked-video.html', {}).get('video_text_metadata')
    official_chain = None
    if video:
        channel = 'https://www.youtube.com/channel/'+video['channelId']
        social_links = by_name['group-social.html']['external_links']
        assert any(link['url'] == channel for link in social_links)
        official_chain = dict(group_site_social_page='http://lethargy.hu/elerhetoseg',
                              linked_channel=channel, linked_release_video='https://www.youtube.com/watch?v=9LWkHRAvNyA',
                              actual_video_channel=video['channelId'], author=video['author'],
                              exact_channel_match=True,
                              scope='Primary group publication chain; the original-hardware statement is an uploader claim, not an independently checked hardware capture.')
    result = dict(pass_=True, research_utc=datetime.now(timezone.utc).isoformat(),
                  script_sha256=sha(Path(__file__).read_bytes()),
                  reused_acquisition_sha256=sha(original_receipt.read_bytes()),
                  preserved_release_sha256=sha(release),
                  search_ledger_sha256=sha((OUT/'search-ledger.json').read_bytes()) if (OUT/'search-ledger.json').exists() else None,
                  release_comment_count=len(review), credited_coder_comments=[r for r in review if r['credited_coder']],
                  credited_participant_comments=[r for r in review if r['credited_participant']],
                  official_video_publication_chain=official_chain, pages=page_analysis,
                  scope='Bounded public-text acquisition and comment/profile provenance. No C64, CPU, emulator, process or display reconstruction; a failed route or no hit is not proof that no public source exists.')
    result['pass'] = result.pop('pass_')
    (OUT/'sources.json').write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
    print(f'{len(review)} preserved release comments; {len(result["credited_coder_comments"])} credited-coder comments; {sum(r["success"] for r in acquisitions)}/{len(acquisitions)} public text routes succeeded.')


if __name__ == '__main__':
    main()
