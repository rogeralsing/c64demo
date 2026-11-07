#!/usr/bin/env python3
"""Archive bounded primary 2025–2026 C64 frontier-source leads.

Only public bytes/metadata and ZIP inventories are inspected. No CPU,
emulator, downloaded host code or process-control action is performed.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib
from html import unescape
import io
import json
from pathlib import Path
import re
import urllib.error
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'build/research/frontier-2026'
ANOMALY_COMMIT='4361d011f56f27014c0b6cd542718ca0b23666d8'
CARRION_COMMIT='84207a9fcd4c1268e4f5515699403ae9cc1fb8b3'
SOURCE_FILES=(
 ('anomaly','readme.md'),
 ('anomaly','Parts/ArcadeScroller/ArcadeScroller.asm'),
 ('anomaly','Parts/ArcadeScroller/scroll_logic.asm'),
 ('anomaly','Parts/ArcadeScroller/upper_scroll_logic.asm'),
 ('anomaly','Parts/ArcadeScroller/raster_irq.asm'),
 ('anomaly','Parts/ArcadeScroller/scene_settings.asm'),
 ('anomaly','Parts/ArcadeScroller/data/frame_line_offsets.asm'),
 ('carrion','censor_intro/main.c'),
 ('carrion','censor_intro/mem.h'),
 ('carrion','censor_intro/readme.md'),
 ('carrion','censor_intro/data/anim/png2spr.py'),
 ('carrion','censor_intro/data/anim/README.md'),
 ('carrion','censor_intro/release/censor_intro_icc26.prg'),
)
def source_name(project,path):return project+'--'+path.replace('/','--')
def source_url(project,path):
    repo,commit=('elder0010/WeAreTheAnomaly',ANOMALY_COMMIT) if project=='anomaly' else ('c64portal/c64_code',CARRION_COMMIT)
    return f'https://raw.githubusercontent.com/{repo}/{commit}/{path}'
PAGES=(
 ('anomaly-author.html','https://www.elder0010.com/projects/we-are-the-anomaly/'),
 ('anomaly-author.zip','https://www.elder0010.com/uploads/we_are_the_anomaly/we_are_the_anomaly_gp_ext.zip'),
 ('anomaly-csdb.html','https://csdb.dk/release/?id=257561'),
 ('anomaly-pouet.html','https://www.pouet.net/prod.php?which=105332'),
 ('codeboys-csdb.html','https://csdb.dk/release/?id=249805'),
 ('codeboys-forum.html','https://csdb.dk/forums/?roomid=12&topicid=170065'),
 ('codeboys-forum-all.html','https://csdb.dk/forums/?roomid=12&showallposts=1&topicid=170065'),
 ('sprite-interleave.html','https://c64demo.com/sprite-interleave/'),
 ('hires-bubbles-author.html','https://c64portal.pl/2026/05/23/kod-w-c-grafika-w-blenderze-jak-napisalem-intro-na-c64/'),
 ('hires-bubbles-csdb.html','https://csdb.dk/release/?id=259782'),
 ('hires-bubbles.prg','https://csdb.dk/getinternalfile.php/277735/censor_intro_icc26.prg'),
 ('c64-code-repo.json','https://api.github.com/repos/c64portal/c64_code'),
 ('carrion-repositories.json','https://api.github.com/users/c64portal/repos?per_page=100'),
 ('elder-repositories.json','https://api.github.com/users/elder0010/repos?per_page=100'),
 ('anomaly-head.json','https://api.github.com/repos/elder0010/WeAreTheAnomaly/commits/master'),
 ('anomaly-tree.json','https://api.github.com/repos/elder0010/WeAreTheAnomaly/git/trees/master?recursive=1'),
 ('c64-code-head.json','https://api.github.com/repos/c64portal/c64_code/commits/main'),
 ('c64-code-tree.json','https://api.github.com/repos/c64portal/c64_code/git/trees/main?recursive=1'),
 ('anomaly-pinned-tree.json','https://api.github.com/repos/elder0010/WeAreTheAnomaly/git/trees/1bf46c72fc177d18c89eb812fcc307fe4b2e5edd?recursive=1'),
 ('carrion-pinned-tree.json','https://api.github.com/repos/c64portal/c64_code/git/trees/f6542073b5911a0630532c80b1c4e42cef1b66c0?recursive=1'),
)+tuple((source_name(project,path),source_url(project,path)) for project,path in SOURCE_FILES)


def sha(data):return hashlib.sha256(data).hexdigest()
def relative(path):return str(path.resolve().relative_to(ROOT))
def preserve(path,data):
    if path.exists() and path.read_bytes()!=data:
        old=path.with_name(path.name+'.previous-'+sha(path.read_bytes())[:12])
        if not old.exists():old.write_bytes(path.read_bytes())
    path.write_bytes(data)
def fetch(pair):
    name,url=pair;result=dict(name=name,requested_url=url,requested_utc=datetime.now(timezone.utc).isoformat())
    try:
        request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 bounded C64 primary-source research','Accept':'*/*'})
        try:response=urllib.request.urlopen(request,timeout=25)
        except urllib.error.HTTPError as error:response=error
        with response:
            data=response.read(12_000_001);assert len(data)<=12_000_000,'Response exceeded bounded acquisition size.'
            result.update(final_url=response.geturl(),status=response.status,success=200<=response.status<300,
                          headers={k:response.headers[k] for k in ('Content-Type','Content-Length','ETag','Last-Modified','X-RateLimit-Remaining') if k in response.headers},
                          bytes=len(data),sha256=sha(data),path=relative(OUT/name))
        preserve(OUT/name,data)
    except (OSError,urllib.error.URLError,AssertionError) as error:
        result.update(success=False,error_type=type(error).__name__,error=str(error),path=None)
    return result
def plain(text):
    text=re.sub(r'<(script|style)\b[^>]*>.*?</\1>','',text,flags=re.I|re.S)
    return re.sub(r'\s+',' ',unescape(re.sub(r'<[^>]*>',' ',text))).strip()


def source_bindings():
    trees={};bindings=[]
    for project,head_name,commit in (('anomaly','anomaly',ANOMALY_COMMIT),('carrion','c64-code',CARRION_COMMIT)):
        head=json.loads((OUT/(head_name+'-head.json')).read_text())
        tree=json.loads((OUT/(project+'-pinned-tree.json')).read_text())
        assert head['sha']==commit and tree['sha']==head['commit']['tree']['sha'] and not tree['truncated']
        trees[project]={item['path']:item for item in tree['tree'] if item['type']=='blob'}
        bindings.append(dict(project=project,commit=commit,tree=tree['sha'],committed_utc=head['commit']['committer']['date']))
    checked=[]
    for project,path in SOURCE_FILES:
        file=OUT/source_name(project,path);data=file.read_bytes();entry=trees[project][path]
        blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        assert len(data)==entry['size'] and blob==entry['sha'],('Source/tree identity mismatch',project,path)
        checked.append(dict(project=project,source_path=path,download_url=source_url(project,path),
                            local_path=relative(file),bytes=len(data),sha256=sha(data),git_blob_sha1=blob))
    published=(OUT/'hires-bubbles.prg').read_bytes()
    repo_release=(OUT/source_name('carrion','censor_intro/release/censor_intro_icc26.prg')).read_bytes()
    assert published==repo_release and len(published)==13497
    frames=[trees['carrion'][f'censor_intro/data/anim/{index:04d}.bin'] for index in range(25)]
    assert all(entry['size']==512 for entry in frames)
    forum=(OUT/'codeboys-forum-all.html').read_text()
    first=forum.index('<a name="170074"');last=forum.index('<a name="',first+1)
    post=plain(forum[first:last])
    assert '2025-02-05' in post and '08:50' in post and 'Pex Mahoney Tufvesson' in post
    assert '/scener/?id=3701' in forum[first:last]
    assert 'The coordinates of the lines are pre-calculated.' in post and 'lost three horizontal lines' in post
    assert '<a href="/scener/?id=3701">Mahoney</a>' in (OUT/'codeboys-csdb.html').read_text()
    post_path=OUT/'mahoney-post-170074.txt';preserve(post_path,(post+'\n').encode())
    return dict(pinned_revisions=bindings,selected_sources=checked,
                hires_release_identity=dict(repo_and_CSDb_PRG_identical=True,bytes=len(published),sha256=sha(published),
                    scope='Published PRG is identical to the source repository release file. Source was not rebuilt or executed.'),
                hires_animation_inventory=dict(frames=25,bytes_per_raw_frame=512,
                    scope='Pinned source-tree file inventory only; Blender, converter, compiler and C64 code were not executed.'),
                mahoney_primary_post=dict(url='https://csdb.dk/forums/?roomid=12&showallposts=1&topicid=170065#170074',
                    post_id=170074,date='2025-02-05 08:50 CET',scener_id=3701,
                    profile_identity='Same account 3701 is credited as Mahoney on the release and signs the post as Pex Mahoney Tufvesson.',
                    text=relative(post_path),sha256=sha(post_path.read_bytes()),
                    scope='Direct effect-author explanation and claimed design choices, not reproduced measurements.'),
                limitations=['No source assembled, compiled, executed or matched natively.',
                    'Anomaly source revision is post-release; its build is not proven identical to the archived production disks.',
                    'Author performance, hardware and historical claims remain attributed claims.',
                    'HCL explicitly says he did not code the separate Pernod character-explosion effect.',
                    'Raistlin 2026 article discusses 2019/2020 productions; it is not a 2026 demo release.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fetch',action='store_true')
    parser.add_argument('--fetch-new',action='store_true',help='Fetch only newly added routes; retain existing acquisitions.')
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True);ledger=OUT/'acquisitions.json'
    if args.fetch or args.fetch_new:
        existing={row['name']:row for row in json.loads(ledger.read_text())} if ledger.exists() else {}
        pending=[pair for pair in PAGES if args.fetch or pair[0] not in existing]
        with ThreadPoolExecutor(max_workers=4) as pool:received=list(pool.map(fetch,pending))
        existing.update({row['name']:row for row in received})
        requests=[existing[name] for name,url in PAGES]
        preserve(ledger,(json.dumps(requests,indent=2)+'\n').encode())
    else:requests=json.loads(ledger.read_text())
    analyses=[]
    for row in requests:
        result=dict(acquisition=row)
        if row.get('path'):
            data=(ROOT/row['path']).read_bytes();assert sha(data)==row['sha256']
            if row['success'] and row['name'].endswith('.html'):
                decoded=data.decode('utf-8',errors='replace');body=plain(decoded)
                title=re.search(r'<title[^>]*>(.*?)</title>',decoded,re.S|re.I)
                result.update(title=plain(title[1]) if title else None,
                              relevant_windows=[body[max(0,m.start()-160):m.end()+600] for m in re.finditer(
                                  r'Arcade Scroller|Stretcher|7 unique|7 chars|Pernod|25 klatek|25 frames|LZO|source|github|2026|2025',body,re.I)][:20],
                              artifact_links=sorted(set(unescape(u) for u in re.findall(r'href=[\"\']([^\"\']+)[\"\']',decoded,re.I)
                                                        if any(s in u.lower() for s in ('github','getinternalfile','.zip','.prg','.d64')))))
                text_path=OUT/(row['name']+'.txt');preserve(text_path,(body+'\n').encode())
                result['plain_text']=dict(path=relative(text_path),sha256=sha(text_path.read_bytes()))
            elif row['success'] and row['name'].endswith('.zip'):
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    assert sum(item.file_size for item in archive.infolist())<=32_000_000
                    assert all(item.file_size<=16_000_000 for item in archive.infolist())
                    result['members']=[dict(name=item.filename,bytes=item.file_size,sha256=sha(archive.read(item))) for item in archive.infolist()]
                result['scope']='ZIP byte inventory only; no packed file, C64 code or host code is executed.'
            elif row['success'] and row['name'].endswith('.json'):
                metadata=json.loads(data)
                if isinstance(metadata,list):result['repositories']=[dict(name=x.get('name'),url=x.get('html_url'),description=x.get('description'),default_branch=x.get('default_branch')) for x in metadata]
                elif 'commit' in metadata:
                    result['commit']=dict(sha=metadata['sha'],tree_sha=metadata['commit']['tree']['sha'],
                                          authored_date=metadata['commit']['author']['date'],committed_date=metadata['commit']['committer']['date'],
                                          message=metadata['commit']['message'])
                elif 'tree' in metadata:
                    result['source_tree']=dict(sha=metadata['sha'],truncated=metadata['truncated'],entries=metadata['tree'])
                else:result['repository']={k:metadata.get(k) for k in ('full_name','html_url','description','default_branch','pushed_at')}
        analyses.append(result)
    readmap=ROOT/'docs/research/README.md'
    observations=OUT/'web-tool-observations.json'
    result=dict(pass_=True,script_sha256=sha(Path(__file__).read_bytes()),readmap=dict(path=relative(readmap),sha256=sha(readmap.read_bytes())),
                source_bindings=source_bindings(),
                web_tool_observations=(dict(path=relative(observations),sha256=sha(observations.read_bytes())) if observations.exists() else None),
                routes=analyses,scope='Bounded source discovery/acquisition and artifact inventories. Author claims, contributor explanations, old-production writeups and source/release identity must be classified separately; no implementation or performance reproduced.')
    result['pass']=result.pop('pass_');preserve(OUT/'sources.json',(json.dumps(result,indent=2)+'\n').encode())
    print(f'{sum(row["success"] for row in requests)}/{len(requests)} bounded routes acquired; failures retained.')


if __name__=='__main__':main()
