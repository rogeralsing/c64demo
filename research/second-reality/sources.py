#!/usr/bin/env python3
"""Preserve bounded author/interview/review leads for C64 Second Reality.

Only public text is fetched. No CPU, emulator, downloaded program, media,
application, or people-messaging action is performed. Failed routes stay in
the ledger; a related author's other production is not silently relabelled.
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
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'build/research/second-reality/sources'
PAGES = (
    ('recollection-germany.html', 'https://www.atlantis-prophecy.org/recollection/?country=germany&load=demo_map'),
    ('relax24-raw.txt', 'https://c64mags.untergrund.net/wiki/index.php?title=Relax_24&action=raw'),
    ('relax24-edit.html', 'https://c64mags.untergrund.net/wiki/index.php?action=edit&title=Relax_24'),
    ('relax24-http.html', 'http://c64mags.untergrund.net/wiki/index.php?title=Relax_24'),
    ('second-reality-pouet.html', 'https://www.pouet.net/prod.php?which=1216'),
    ('impossible-thing-pouet.html', 'https://www.pouet.net/prod.php?which=10607'),
    ('deutschlandfunk-2005.html', 'https://www.deutschlandfunk.de/der-brotkasten-lebt-100.html'),
    ('aeg-profile.html', 'https://www.c64-wiki.de/wiki/Andr%C3%A9_B%C3%BCrger'),
    ('aeg-interview.html', 'https://tell-the-world.com/interview-mit-spieleentwickler-und-geschaeftsfuehrer-andre-buerger-der-firma-visgames/'),
    ('future-crew-PC-readme.md', 'https://raw.githubusercontent.com/mtuomi/SecondReality/master/README.md'),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def plain(text):
    text = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', '', text, flags=re.S|re.I)
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]*>', ' ', text))).strip()


def fetch(pair):
    name,url = pair
    record = dict(name=name,requested_url=url,requested_utc=datetime.now(timezone.utc).isoformat())
    try:
        request = urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 C64 primary-source research'})
        try:
            response = urllib.request.urlopen(request,timeout=20)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            data = response.read(4_000_001)
            assert len(data) <= 4_000_000
            record.update(final_url=response.geturl(),http_status=response.status,success=200<=response.status<300,
                          headers={k:response.headers[k] for k in ('Content-Type','Content-Length','ETag','Last-Modified') if k in response.headers},
                          bytes=len(data),sha256=sha(data))
        target = OUT/name
        if target.exists() and target.read_bytes()!=data:
            backup = OUT/(name+'.previous-'+sha(target.read_bytes())[:12])
            if not backup.exists():
                backup.write_bytes(target.read_bytes())
        target.write_bytes(data)
        record['path'] = str(target.relative_to(ROOT))
    except (OSError,urllib.error.URLError,AssertionError) as error:
        record.update(success=False,http_status=None,error_type=type(error).__name__,error=str(error),path=None)
    return record


def decode(data):
    try:
        return data.decode('utf-8'),'UTF8'
    except UnicodeDecodeError:
        return data.decode('latin1'),'Latin1 byte-preserving fallback'


def pouet_comment(source, comment_id, account, date):
    """Locate one preserved post by its explicit ID, author link and date."""
    pattern = (rf"<div class='comment[^']*' id='c{comment_id}'>\s*"
               r"<div class='content'>(.*?)</div>\s*<div class='foot'>(.*?)</div>\s*</div>")
    match = re.search(pattern,source,re.S)
    assert match is not None, comment_id
    assert f"user.php?who={account}" in match[2]
    assert date in plain(match[2])
    return dict(comment_id=comment_id,account=account,date=date,body=plain(match[1]),
                source_character_range=[match.start(),match.end()])


def classified_evidence():
    """Keep identity checks and evidence classes separate from keyword hits."""
    impossible = (OUT/'impossible-thing-pouet.html').read_text()
    second = (OUT/'second-reality-pouet.html').read_text()
    for page in (impossible,second):
        credits = re.search(r"<td id='credits'.*?</td>",page,re.S)
        assert credits and "user.php?who=4909" in credits[0]
    posts = [pouet_comment(impossible,*row) for row in (
        (81370,4909,'2003-08-25 18:39:17'),
        (81849,417,'2003-08-27 22:23:37'),
        (81850,417,'2003-08-27 22:24:39'),
        (81860,4909,'2003-08-27 23:08:44'))]
    assert '16x16 pixel texture' in posts[0]['body']
    assert '40x25' in posts[1]['body']
    assert 'explanation of the effect ist quite correct' in posts[3]['body']
    author_posts = re.findall(r"<div class='comment cite-4909(?: [^']*)?' id='c(\d+)'>",second)
    result = dict(
        related_production=dict(
            title='The Impossible Thing',release_year=2003,pouet=10607,
            source='impossible-thing-pouet.html',source_sha256=sha((OUT/'impossible-thing-pouet.html').read_bytes()),
            identity='Account 4909 is credited on both pages; author posts are explicitly attached to the 2003 production.',
            posts=posts,
            classification='Direct author technical explanation of a DIFFERENT production, not the 1997 C64 Second Reality routine.'),
        second_reality_pouet=dict(source='second-reality-pouet.html',
                                  aeg_account_4909_comment_ids=author_posts,
                                  scope='No author post by this credited account found in the acquired page; this is not a global absence claim.'),
        pc_source=dict(source='future-crew-PC-readme.md',
                       classification='Future Crew 1993 PC source; excluded as evidence for Smash Designs C64 renderer.'),
        interview=dict(source='deutschlandfunk-2005.html',
                       classification='Direct AEG voice, but no Second Reality per-effect implementation explanation located.'),
        recollection=dict(source='recollection-germany.html',
                          classification='Editorial history containing an attributed AEG design recollection; not per-effect renderer source.'))
    cached = OUT/'relax24-web-cache-response.txt'
    if cached.exists():
        body = cached.read_text()
        start = body.index('Clarence about the coding:')
        end = body.index('RRR about the artwork:',start)
        review = plain(body[start:end])
        target = OUT/'relax24-cached-coding-review.txt'
        target.write_text(review+'\n')
        result['contemporary_review'] = dict(
            source=str(cached.relative_to(ROOT)),sha256=sha(cached.read_bytes()),
            coding_section=str(target.relative_to(ROOT)),coding_section_sha256=sha(target.read_bytes()),
            character_range_in_cache=[start,end],
            url='https://c64mags.untergrund.net/wiki/index.php?action=edit&title=Relax_24',
            acquisition='Search-engine cached/indexed response, not a successful direct HTTP acquisition.',
            classification='Clarence coding review. Secondary implementation impressions; no C64 author provenance or runtime proof.',
            excluded_neighbouring_sections='RRR artwork and unrelated productions, compo rules and interviews are not renderer evidence.')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch',action='store_true')
    args = parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    ledger = OUT/'acquired-pages.json'
    if args.fetch:
        with ThreadPoolExecutor(max_workers=4) as pool:
            acquisitions = list(pool.map(fetch,PAGES))
        if ledger.exists():
            backup = OUT/('acquired-pages.previous-'+sha(ledger.read_bytes())[:12]+'.json')
            if not backup.exists():
                backup.write_bytes(ledger.read_bytes())
        ledger.write_text(json.dumps(acquisitions,indent=2)+'\n')
    else:
        acquisitions = json.loads(ledger.read_text())
    reused = []
    for name in ('author-home.html','author-c64-releases.html','csdb-release.html'):
        path = ROOT/'build/research/second-reality'/name
        reused.append(dict(path=str(path.relative_to(ROOT)),bytes=path.stat().st_size,sha256=sha(path.read_bytes()),
                           scope='Existing acquisition reused without refetch or mutation.'))
    analyses = []
    for item in acquisitions:
        row = dict(acquisition=item)
        if item['path']:
            data = (ROOT/item['path']).read_bytes()
            assert sha(data)==item['sha256']
            decoded,encoding = decode(data)
            if item['success']:
                body = plain(decoded)
                title = re.search(r'<title[^>]*>(.*?)</title>',decoded,re.S|re.I)
                row.update(decoding=encoding,title=plain(title[1]) if title else None,
                           relevant_windows=[body[max(0,m.start()-180):m.end()+500] for m in re.finditer(r'Second Reality|Second Rea- lity|2nd Reality|precalcul|rotozoom|textur|AEG recalls',body,re.I)][:24])
                if item['name'].startswith('relax24'):
                    start = body.find('Clarence about the coding:')
                    end = body.find('RRR about the artwork:',start)
                    if start!=-1 and end>start:
                        coding = body[start:end]
                        output = OUT/(item['name']+'.second-reality-coding.txt')
                        output.write_text(coding+'\n')
                        row.update(coding_review=dict(path=str(output.relative_to(ROOT)),sha256=sha(output.read_bytes()),
                                                      author='Clarence, coding reviewer; not credited C64 demo author',
                                                      scope='Magazine transcription, not checked against an original magazine image or executed code in this lane.'))
        analyses.append(row)
    result = dict(pass_=True,script_sha256=sha(Path(__file__).read_bytes()),reused_artifacts=reused,pages=analyses,
                  classified_evidence=classified_evidence(),
                  research_utc=datetime.now(timezone.utc).isoformat(),
                  scope='Bounded source acquisition and text location only. Primary quotations, contemporary reviews, hearsay, other productions, and PC1993 code require separate classification; no C64 algorithm is proved by a keyword hit.')
    result['pass']=result.pop('pass_')
    (OUT/'sources.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'{sum(item["success"] for item in acquisitions)}/{len(acquisitions)} bounded text routes succeeded; failures and original bodies retained.')


if __name__=='__main__':
    main()
