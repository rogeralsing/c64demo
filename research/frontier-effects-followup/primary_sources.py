#!/usr/bin/env python3
"""Retain and passively inspect bounded original Hat/Aloft source routes."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'build/research/frontier-effects-followup'
ROUTES = [
    ('the-hat.html','https://csdb.dk/release/?id=259070'),
    ('the-hat-notes.html','https://csdb.dk/release/?id=259070&show=notes'),
    ('the-hat-hidden.html','https://csdb.dk/release/?id=259070&show=hidden'),
    ('alfatech.html','https://csdb.dk/scener/?id=305'),
    ('aloft.html','https://csdb.dk/release/?id=259056'),
    ('aloft-hidden.html','https://csdb.dk/release/?id=259056&show=hidden'),
    ('trident-home.html','https://trident64.github.io/'),
    ('trident-feed.xml','https://trident64.github.io/feed.xml'),
    ('trident-code-branches.json','https://api.github.com/repos/trident64/c64/branches?per_page=100'),
    ('trident-code-tags.json','https://api.github.com/repos/trident64/c64/tags?per_page=100'),
    ('trident-code-tree.json','https://api.github.com/repos/trident64/c64/git/trees/80d1027742815e55cda13a80cb4826744dd75c83?recursive=1'),
    ('trident-site-branches.json','https://api.github.com/repos/trident64/trident64.github.io/branches?per_page=100'),
    ('trident-site-tree.json','https://api.github.com/repos/trident64/trident64.github.io/git/trees/9c8bac3711136ca7d44b476bb8a962fa3bfab4d9?recursive=1'),
    ('filename-short-hash-search.json','https://api.github.com/search/commits?q=7a825b1&per_page=100'),
    ('quiss-home.html','https://www.quiss.org/'),
    ('quiss-repos.json','https://api.github.com/users/matthiaskramm/repos?per_page=100'),
    ('quiss-source-branches.json','https://api.github.com/repos/matthiaskramm/soul_on_fire/branches?per_page=100'),
    ('quiss-source-tags.json','https://api.github.com/repos/matthiaskramm/soul_on_fire/tags?per_page=100'),
    ('quiss-source-tree.json','https://api.github.com/repos/matthiaskramm/soul_on_fire/git/trees/d094947170cbe18eee0e553bfa2dc59a7d474fd2?recursive=1'),
    ('raistlin-branches.json','https://api.github.com/repos/RobertTroughton/C64Demo-PublicReleases/branches?per_page=100'),
    ('raistlin-tags.json','https://api.github.com/repos/RobertTroughton/C64Demo-PublicReleases/tags?per_page=100'),
    ('raistlin-tree.json','https://api.github.com/repos/RobertTroughton/C64Demo-PublicReleases/git/trees/965807c511e2025b5c5e1ffb2a6235a4efd6ae5b?recursive=1'),
    ('raistlin-articles.txt','https://c64demo.com/llms.txt'),
    ('sparta-repos.json','https://api.github.com/users/spartaomg/repos?per_page=100'),
    ('piper-watch.html','https://www.youtube.com/watch?v=Vfnyczaf1Ao'),
    ('piper-oembed.json','https://www.youtube.com/oembed?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DVfnyczaf1Ao&format=json'),
    ('piper-caption-list.xml','https://www.youtube.com/api/timedtext?type=list&v=Vfnyczaf1Ao'),
    ('trident-talk-watch.html','https://www.youtube.com/watch?v=tqX42YoncaA'),
    ('piper-repos.json','https://api.github.com/users/martinpiper/repos?per_page=100'),
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)),bytes=len(raw),sha256=sha(raw))


def fetch_route(directory, route):
    name,url = route
    row = dict(name=name,requested_url=url,requested_UTC=datetime.now(timezone.utc).isoformat())
    try:
        request = urllib.request.Request(url,headers={'User-Agent':'c64demo-read-only-primary-source-research','Accept':'application/vnd.github+json' if 'api.github.com' in url else '*/*'})
        try:
            response = urllib.request.urlopen(request,timeout=20)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            raw = response.read(4_000_001)
            row.update(status=response.status,final_url=response.url,
                content_type=response.headers.get('Content-Type'),etag=response.headers.get('ETag'),
                last_modified=response.headers.get('Last-Modified'),pagination_link=response.headers.get('Link'),
                github_rate_remaining=response.headers.get('X-RateLimit-Remaining'))
        complete = len(raw) <= 4_000_000
        (directory/name).write_bytes(raw)
        row.update(complete_response_body=complete,artifact=artifact(directory/name),success=row['status']==200 and complete)
    except (urllib.error.URLError,TimeoutError) as error:
        row.update(success=False,error=str(error))
    return row


def transcript_requests(acquisition, directory):
    """Normal read-only public transcript POST, with params from retained UI JSON."""
    assert not directory.exists(),'Choose a fresh transcript directory'
    directory.mkdir(parents=True)
    def request_transcript(pair):
        stem,video=pair
        watch=acquisition/('piper-watch.html' if stem=='piper' else 'trident-talk-watch.html')
        raw=watch.read_text();cfg={}
        for match in re.finditer(r'ytcfg\.set\(',raw):
            try:
                value,_=json.JSONDecoder().raw_decode(raw[match.end():])
                if isinstance(value,dict):cfg.update(value)
            except json.JSONDecodeError:pass
        initial=re.search(r'(?:var\s+)?ytInitialData\s*=\s*',raw)
        assert initial
        data,_=json.JSONDecoder().raw_decode(raw[initial.end():])
        endpoints=[]
        def collect(value):
            if isinstance(value,dict):
                if 'getTranscriptEndpoint' in value:endpoints.append(value['getTranscriptEndpoint'])
                for item in value.values():collect(item)
            elif isinstance(value,list):
                for item in value:collect(item)
        collect(data);assert len(endpoints)==1
        client=cfg['INNERTUBE_CONTEXT']['client']
        context={'client':{k:client[k] for k in ('hl','gl','clientName','clientVersion','visitorData') if k in client}}
        body=json.dumps(dict(context=context,params=endpoints[0]['params']),separators=(',',':')).encode()
        request_path=directory/(stem+'-request.json');request_path.write_bytes(body)
        url='https://www.youtube.com/youtubei/v1/get_transcript?prettyPrint=false'
        headers={'Content-Type':'application/json','User-Agent':'c64demo-read-only-primary-source-research',
                 'Origin':'https://www.youtube.com','Referer':'https://www.youtube.com/watch?v='+video}
        row=dict(name=stem,method='POST',requested_url=url,requested_UTC=datetime.now(timezone.utc).isoformat(),
                 source_watch=artifact(watch),request=artifact(request_path),request_headers=headers)
        try:
            request=urllib.request.Request(url,data=body,headers=headers,method='POST')
            try:response=urllib.request.urlopen(request,timeout=20)
            except urllib.error.HTTPError as error:response=error
            with response:
                reply=response.read(4_000_001)
                row.update(status=response.status,final_url=response.url,content_type=response.headers.get('Content-Type'))
            path=directory/(stem+'-response.json');path.write_bytes(reply)
            row.update(response=artifact(path),complete_response_body=len(reply)<=4_000_000)
        except (urllib.error.URLError,TimeoutError,OSError) as error:row['error']=str(error)
        return row
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows=list(pool.map(request_transcript,(('piper','Vfnyczaf1Ao'),('trident-talk','tqX42YoncaA'))))
    (directory/'acquisition.json').write_text(json.dumps(dict(routes=rows,read_only_public_transcript_request=True),indent=2)+'\n')
    return rows


class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.text=[]; self.links=[]; self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.skip+=1
        if tag=='a':
            href=dict(attrs).get('href')
            if href:self.links.append(href)
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip-=1
    def handle_data(self,data):
        if not self.skip:self.text.append(data)


def inspect(acquisition, supplementals):
    rows=json.loads((acquisition/'acquisition.json').read_text())['routes']
    indexed={row['name']:row for row in rows}
    bodies={}
    for row in rows:
        if 'artifact' in row:
            path=ROOT/row['artifact']['path'];assert artifact(path)==row['artifact']
            bodies[row['name']]=path.read_bytes()
    def parsed(name):
        if indexed[name]['success']:
            return json.loads(bodies[name])
        return None
    repositories=[]
    for prefix,owner,commit in (
        ('trident-code','trident64/c64','80d1027742815e55cda13a80cb4826744dd75c83'),
        ('trident-site','trident64/trident64.github.io','9c8bac3711136ca7d44b476bb8a962fa3bfab4d9'),
        ('quiss-source','matthiaskramm/soul_on_fire','d094947170cbe18eee0e553bfa2dc59a7d474fd2'),
        ('raistlin','RobertTroughton/C64Demo-PublicReleases','965807c511e2025b5c5e1ffb2a6235a4efd6ae5b')):
        branches=parsed(prefix+'-branches.json');tree=parsed(prefix+'-tree.json')
        row=dict(repository=owner,requested_commit=commit,branches=branches)
        if branches is not None and tree is not None:
            assert not tree['truncated']
            row.update(branch_listing_complete=not indexed[prefix+'-branches.json']['pagination_link'],
                requested_commit_is_current_branch=any(b['commit']['sha']==commit for b in branches),
                tree_entries=len(tree['tree']),tree_sha=tree['sha'],
                target_named_paths=[item['path'] for item in tree['tree'] if re.search(r'aloft|the[ _-]?hat',item['path'],re.I)],
                kefrens_paths=[item['path'] for item in tree['tree'] if 'kefrens' in item['path'].lower()])
        repositories.append(row)
    pages=[]
    for name in ('the-hat.html','the-hat-notes.html','the-hat-hidden.html','alfatech.html','aloft.html','aloft-hidden.html','trident-home.html','quiss-home.html'):
        if indexed[name]['success']:
            parser=Text();parser.feed(bodies[name].decode('utf-8',errors='replace'))
            text=' '.join(' '.join(parser.text).split())
            pages.append(dict(name=name,characters=len(text),links=parser.links,
                target_mentions=[dict(term=term,count=len(re.findall(re.escape(term),text,re.I))) for term in ('upscroll','kefrens','source','Aloft','The Hat')]))
    videos=[]
    for name in ('piper-watch.html','trident-talk-watch.html'):
        item=dict(name=name,HTTP_success=indexed[name]['success'],player_response_found=False)
        if indexed[name]['success']:
            raw=bodies[name].decode('utf-8',errors='replace')
            match=re.search(r'(?:var\s+)?ytInitialPlayerResponse\s*=\s*',raw)
            if match:
                try:
                    response,_=json.JSONDecoder().raw_decode(raw[match.end():])
                    captions=response.get('captions',{}).get('playerCaptionsTracklistRenderer',{}).get('captionTracks',[])
                    micro=response.get('microformat',{}).get('playerMicroformatRenderer',{})
                    item.update(player_response_found=True,playability=response.get('playabilityStatus'),
                        details=response.get('videoDetails'),caption_tracks=captions,
                        publish_date=micro.get('publishDate'),upload_date=micro.get('uploadDate'))
                except json.JSONDecodeError:item['parse_error']='No valid JSON at player-response assignment'
        videos.append(item)
    search=parsed('filename-short-hash-search.json')
    supplemental_rows=[]
    teardown_repositories=[]
    caption_results=[]
    def verify_metadata(value):
        if isinstance(value,dict):
            if isinstance(value.get('path'),str) and isinstance(value.get('bytes'),int) and isinstance(value.get('sha256'),str):
                assert artifact(ROOT/value['path']) == {key:value[key] for key in ('path','bytes','sha256')}
            for item in value.values():verify_metadata(item)
        elif isinstance(value,list):
            for item in value:verify_metadata(item)
    for directory in supplementals:
        path=directory/'acquisition.json';data=json.loads(path.read_text());verify_metadata(data)
        supplemental_rows.append(dict(manifest=artifact(path),data=data))
        for route in data['routes']:
            row=route.get('response',route.get('artifact'))
            if directory.name.startswith('captions-') or directory.name.startswith('transcript-endpoint-'):
                reply=(ROOT/row['path']).read_bytes() if row else b''
                status=None
                try:status=json.loads(reply).get('error',{}).get('status')
                except (json.JSONDecodeError,UnicodeDecodeError):pass
                assert (not reply and route.get('status')==200) or (route.get('status')==400 and status=='FAILED_PRECONDITION')
                caption_results.append(dict(route=route['name'],method=route.get('method','GET'),
                    HTTP_status=route.get('status'),response_bytes=len(reply),API_error_status=status,
                    transcript_text_recovered=False,
                    scope='Retained response is empty or an explicit API error; HTTP success alone does not provide transcript content.'))
        if directory.name.startswith('piper-source-'):
            for repository in ('C64Public','C64Docs','C64FindCode'):
                branch=json.loads((directory/(repository+'-branch.json')).read_text())
                tree=json.loads((directory/(repository+'-tree.json')).read_text())
                assert not tree['truncated']
                commit=branch['commit']['sha']
                tree_route=next(row for row in data['routes'] if row['name']==repository+'-tree.json')
                assert '/'+commit+'?' in tree_route['requested_url']
                targets=[row['path'] for row in tree['tree'] if re.search(r'the[ _-]?hat|upscroll|259070|7a825b1',row['path'],re.I)]
                teardown_repositories.append(dict(repository='martinpiper/'+repository,commit=commit,
                    tree_sha=tree['sha'],entries=len(tree['tree']),truncated=False,target_named_paths=targets,
                    scope='Uploader-owned tree-path inventory, not a search of every blob or original creator effect source.'))
    return dict(pass_=True,scope='Bounded primary-source retrieval and original public-tree/author-route refresh; no recovered target algorithm is implied by successful acquisition.',
        producer=artifact(Path(__file__)),acquisition=artifact(acquisition/'acquisition.json'),
        routes=rows,repositories=repositories,pages=pages,videos=videos,
        supplemental_acquisitions=supplemental_rows,caption_access_results=caption_results,
        teardown_repository_inventories=teardown_repositories,
        named_mechanism_recovered=dict(the_hat_end_upscroller=False,aloft_three_layer_pattern=False,aloft_bitmap_or_flipped_Kefrens=False),
        starting_note=artifact(ROOT/'docs/research/february-2026.md'),
        retained_helper_failures=[artifact(BASE/'failure-import-01/failure-note.json'),
            artifact(BASE/'failure-import-01/inspect.checked.py'),artifact(BASE/'transcript-endpoint-01/failure-note.json')],
        short_filename_hash_search=None if search is None else dict(total_count=search.get('total_count'),
            incomplete_results=search.get('incomplete_results'),returned_items=len(search.get('items',[])),
            matches=[dict(repository=item['repository']['full_name'],commit=item['sha']) for item in search.get('items',[])],
            scope='Seven-hex-prefix search results are ambiguous and do not identify the release source commit.'),
        limits=['Tree-path checks do not inspect every blob or establish private/deleted/history-wide source absence.',
            'A failed/blocked/empty caption request does not establish that no transcript exists.',
            'Video descriptions and metadata identify a technical lead; no spoken algorithm is inferred without its contents.',
            'Named mechanism statuses record the bounded manual source review, not a theorem that source or explanations are absent everywhere.',
            'Viewer/peer reactions remain separate from production-coder statements.',
            'No downloaded code execution, CPU interpreter, emulator, native/build/process action or product change.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acquisition',type=Path,required=True)
    parser.add_argument('--fetch',action='store_true')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--transcripts',type=Path)
    parser.add_argument('--supplemental',type=Path,nargs='*',default=[])
    args=parser.parse_args();directory=args.acquisition.resolve();directory.relative_to(BASE.resolve())
    if args.fetch:
        assert not directory.exists(),'Choose a fresh acquisition directory'
        directory.mkdir(parents=True)
        with ThreadPoolExecutor(max_workers=6) as pool:
            rows=list(pool.map(lambda route:fetch_route(directory,route),ROUTES))
        manifest=dict(routes=rows,downloaded_host_code_executed=False)
        (directory/'acquisition.json').write_text(json.dumps(manifest,indent=2)+'\n')
        print(json.dumps(dict(routes=len(rows),successful=sum(row['success'] for row in rows)),indent=2))
    if args.transcripts:
        transcripts=args.transcripts.resolve();transcripts.relative_to(BASE.resolve())
        rows=transcript_requests(directory,transcripts)
        print(json.dumps([dict(name=row['name'],status=row.get('status'),bytes=row.get('response',{}).get('bytes'),error=row.get('error')) for row in rows],indent=2))
    if args.output:
        out=args.output.resolve();out.relative_to(BASE.resolve());assert not out.exists(),'Choose a fresh output directory'
        supplementals=[path.resolve() for path in args.supplemental]
        for path in supplementals:path.relative_to(BASE.resolve())
        proof=inspect(directory,supplementals);out.mkdir(parents=True)
        (out/'inspect.checked.py').write_bytes(Path(__file__).read_bytes())
        raw=(json.dumps(proof,indent=2)+'\n').encode();(out/'source-proof.json').write_bytes(raw)
        print(json.dumps(dict(pass_=True,receipt_bytes=len(raw),receipt_sha256=sha(raw)),indent=2))


if __name__=='__main__':main()
