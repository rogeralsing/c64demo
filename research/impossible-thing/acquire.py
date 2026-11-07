#!/usr/bin/env python3
"""Acquire/recheck original Impossible Thing party files; never run a program."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'build/research/impossible-thing'
URLS = {
    'scene-party-pack.zip': 'https://files.scene.org/get/parties/2003/breakpoint03/c64/in4k/c64-4k.zip',
    'csdb-4Ks.zip': 'https://csdb.dk/getinternalfile.php/57487/4Ks.zip',
    'csdb-release.html': 'https://csdb.dk/release/?id=8615',
    'oxyron-releases.html': 'https://www.oxyron.de/html/demosc.html',
}
PINNED = {
    'scene-party-pack.zip': '0bb5d307ab10461ea46e3f289c436cf0b59549340bfe3e384936e674b98fd7ca',
    'csdb-4Ks.zip': '159339cb807c238de1bd74e33c02dca7c13550769873ad467a97e69b6f5334cf',
}
DISK_SHA = '8f40a954ef6bdbd28d8e5e9d81c920310169349242714a8611b0b8dabcaf5717'
PRG_SHA = 'a79f294f7a506bd489135dbf56515e939d8a14a6b16cafccea38673d09acca8d'


def sha(data): return hashlib.sha256(data).hexdigest()
def relative(path): return str(Path(path).resolve().relative_to(ROOT))
def record(path):
    data=Path(path).read_bytes()
    return dict(path=relative(path),bytes=len(data),sha256=sha(data))
def sectors(track):
    assert 1<=track<=35
    return 21 if track<=17 else 19 if track<=24 else 18 if track<=30 else 17
def sector(disk,track,index):
    assert 0<=index<sectors(track)
    first=256*(sum(sectors(t) for t in range(1,track))+index)
    return disk[first:first+256]
def extract(disk,track,index):
    output=bytearray();seen=set();chain=[]
    while track:
        assert (track,index) not in seen;seen.add((track,index))
        data=sector(disk,track,index)
        chain.append(dict(track=track,sector=index,link=list(data[:2]),sha256=sha(data)))
        assert data[0] or 1<=data[1]<=255
        output.extend(data[2:256 if data[0] else data[1]+1])
        track,index=data[:2]
    return bytes(output),chain
def directory(disk):
    result=[];seen=set();track,index=18,1
    while track:
        assert (track,index) not in seen;seen.add((track,index));data=sector(disk,track,index)
        for slot in range(8):
            entry=data[2+32*slot:32+32*slot]
            if entry[0]&7:
                result.append(dict(directory_track=track,directory_sector=index,slot=slot,
                    type=entry[0],first_track=entry[1],first_sector=entry[2],
                    name=entry[3:19].rstrip(b'\xa0').decode('latin1'),
                    raw_name_hex=entry[3:19].hex(),declared_blocks=int.from_bytes(entry[28:30],'little')))
        track,index=data[:2]
    return result
def basic_lines(prg):
    first=int.from_bytes(prg[:2],'little');data=prg[2:];address=first;seen=set();result=[]
    while True:
        assert address not in seen;seen.add(address);offset=address-first
        assert 0<=offset<=len(data)-2
        next_address=int.from_bytes(data[offset:offset+2],'little')
        if not next_address:break
        assert address+4<=next_address<=first+len(data)
        end=data.index(0,offset+4);body=data[offset+4:end]
        assert end+1==next_address-first
        result.append(dict(address=address,line=int.from_bytes(data[offset+2:offset+4],'little'),
            body_hex=body.hex(),text=body[1:].decode('latin1') if body[:1]==b'\x8f' else None))
        address=next_address
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch',action='store_true',help='Fetch bounded primary release routes; otherwise inspect saved bytes only')
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    responses=[]
    if args.fetch:
        for filename,url in URLS.items():
            try:
                request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 c64demo-research'})
                with urllib.request.urlopen(request,timeout=30) as response:
                    data=response.read()
                    if filename in PINNED:assert sha(data)==PINNED[filename]
                    (OUT/filename).write_bytes(data)
                    responses.append(dict(file=filename,url=url,final_url=response.url,status=response.status,
                        headers={k:v for k,v in response.headers.items() if k.lower()!='set-cookie'},
                        bytes=len(data),sha256=sha(data)))
            except Exception as error:
                responses.append(dict(file=filename,url=url,error=repr(error)))
        (OUT/'http-responses.json').write_text(json.dumps(responses,indent=2)+'\n')
    archives=[];disks=[]
    for name,digest in PINNED.items():
        blob=(OUT/name).read_bytes();assert sha(blob)==digest
        archive=zipfile.ZipFile(io.BytesIO(blob));members=[]
        for info in archive.infolist():
            data=archive.read(info)
            members.append(dict(name=info.filename,bytes=len(data),sha256=sha(data)))
            if info.filename.lower()=='c64-4k.d64':
                assert len(data)==174848 and sha(data)==DISK_SHA;disks.append(data)
        archives.append(dict(**record(OUT/name),source_url=URLS[name],members=members))
    assert len(disks)==2 and disks[0]==disks[1];disk=disks[0]
    (OUT/'c64-4k.d64').write_bytes(disk);entries=directory(disk)
    target=[e for e in entries if e['name']=='4K/AEG & AXIS'];assert len(target)==1
    entry=target[0];prg,chain=extract(disk,entry['first_track'],entry['first_sector'])
    assert len(prg)==3592 and sha(prg)==PRG_SHA and prg[:2]==b'\x01\x08'
    assert prg[2:12]==bytes.fromhex('0b 08 90 06 9e 32 30 34 39 00')
    (OUT/'impossible-thing.prg').write_bytes(prg)
    readme=[e for e in entries if e['name']=='READ ME'];assert len(readme)==1
    note,note_chain=extract(disk,readme[0]['first_track'],readme[0]['first_sector'])
    assert sha(note)=='4db2a452c02dee1bfd75af4001b256779853b1d29d5215efe02847081fd89e6c'
    lines=basic_lines(note);(OUT/'read-me.prg').write_bytes(note)
    (OUT/'read-me.txt').write_text('\n'.join(line['text'] or '' for line in lines)+'\n')
    pouet=ROOT/'build/research/second-reality/sources/impossible-thing-pouet.html'
    assert sha(pouet.read_bytes())=='dabcffc090830f85f84ea883e303492e1c9a52fa8cff28cfab8048befb45fe9e'
    pages=[dict(**record(p),source_url=URLS[p.name]) for p in (OUT/'csdb-release.html',OUT/'oxyron-releases.html') if p.exists()]
    report=dict(pass_=True,script=record(Path(__file__)),archives=archives,disk=record(OUT/'c64-4k.d64'),
        archives_have_identical_disk=True,directory=entries,
        target=dict(**record(OUT/'impossible-thing.prg'),entry=entry,chain=chain,load_address=0x801,
                    loaded_end_exclusive=0x1607,BASIC_SYS=2049,entry_signature=prg[2:29].hex(' ')),
        author_note=dict(**record(OUT/'read-me.prg'),chain=note_chain,lines=lines,
            scope='Original bundled author readme; its25FPS/fullscreen/historical-priority statements are claims, not native measurements.'),
        primary_pages=pages,pinned_pouet=dict(**record(pouet),source_url='https://www.pouet.net/prod.php?which=10607',
            posts=[81370,81849,81860]),
        scope='Original release acquisition and byte identity only. No host program, C64 code or emulator execution.')
    report['pass']=report.pop('pass_');target=OUT/'acquisition.json';target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(receipt=relative(target),sha256=sha(target.read_bytes()),PRG_sha256=PRG_SHA),indent=2))


if __name__=='__main__':main()
