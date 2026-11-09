#!/usr/bin/env python3
"""Passively extract the original Hat DOS bootstrap and raw loader streams."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'build/research/the-hat'
ZIP = ROOT/'build/research/frontier-2026/february-analysis/the-hat-original.zip'
ZIP_SHA = 'ab15a74ba10a71264ccad74cd1d3a394b8f442a2acd33fd363b671bf293b081f'
DISKS = {
    'a': 'ce09a1819a5dcec16342ebdc6515d20c377304db68e326ca2d86a499f0c9399d',
    'b': '1527038ebebca1a3d3d3379b91dd1a77dffb6d6d89a4dbfc32bf3f6908eb5b21',
}
PINS = {
    'build/research/next-round/boot-analysis/bitfire-source/d64write/d64write.c': '78f3200efc32fdc4f92670bf7ac84a0dc016b4310b46396c0ab16fc720c8b5c1',
    'build/research/next-round/boot-analysis/bitfire-source/loader/resident.asm': '87d8f77d54f1c6dbee25a84cb3bc128e240f174cd1d25753cd7ad070a42708f1',
    'build/research/next-round/boot-analysis/bitfire-source/loader/drivecode.asm': 'bcea2c9703767b3e500b61fdf17e54d0dad71ab7f20d151f83ec24fa069deb4a',
    'build/research/next-round/boot-analysis/bitfire-source/loader/constants.inc': '3add7304b263e097de10889c9eb79a07e53bf0b890d40071bd77669674631a54',
    'build/research/next-round/boot-analysis/bitfire-source.json': 'ae970f06264ae255335516d20e3e04fff5670f1cfa11674e9f61965c6b01cff1',
}
BOOT_SHA = '32189d1101a947c3ecc02ae3e9493756dbc063008582d09c62f939068f1049cd'
SECTORS = [0]+[21]*17+[19]*7+[18]*6+[17]*5


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)),bytes=len(raw),sha256=sha(raw))


def sector_offset(track, sector):
    assert 1 <= track <= 35 and 0 <= sector < SECTORS[track]
    return 256*(sum(SECTORS[:track])+sector)


def sector(disk, track, number):
    offset=sector_offset(track,number)
    raw=disk[offset:offset+256]
    assert len(raw)==256
    return raw


def dos_entries(disk):
    assert sector(disk,18,0)[:2]==bytes((18,1))
    track,number=18,1
    entries,links,seen=[],[],set()
    while track:
        assert (track,number) not in seen
        seen.add((track,number))
        raw=sector(disk,track,number)
        links.append(dict(track=track,sector=number,next=list(raw[:2]),sha256=sha(raw)))
        for slot in range(8):
            offset=2+32*slot
            row=raw[offset:offset+30]
            if row[0]:
                entries.append(dict(index=len(entries),directory_track=track,directory_sector=number,slot=slot,
                    type=row[0],start=list(row[1:3]),name_hex=row[3:19].hex(),
                    declared_blocks=int.from_bytes(row[28:30],'little'),raw_entry_hex=row.hex()))
        track,number=raw[:2]
    return entries,links


def dos_chain(disk, start):
    track,number=start
    seen,raws,segments=set(),[],[]
    total=0
    while True:
        assert (track,number) not in seen
        seen.add((track,number))
        raw=sector(disk,track,number)
        next_track,next_number=raw[:2]
        count=254 if next_track else next_number-1
        assert 0 <= count <= 254
        chunk=raw[2:2+count]
        raws.append(chunk)
        segments.append(dict(track=track,sector=number,next_track=next_track,next_sector_or_length=next_number,
            disk_offset=sector_offset(track,number)+2,file_offset=total,bytes=count,sector_sha256=sha(raw)))
        total+=count
        if not next_track:
            break
        track,number=next_track,next_number
    return b''.join(raws),segments


def order(track):
    stride=4 if track<=17 else 3
    return [number for residue in range(stride) for number in range(residue,SECTORS[track],stride)]


def raw_streams(disk, side):
    directory=sector(disk,18,18)
    assert directory[:4]==bytes((1,0,0,0xf0+(side=='b')))
    fields=[tuple(directory[4+index+63*column] for column in range(4)) for index in range(63)]
    count=next((index for index,row in enumerate(fields) if not any(row)),63)
    assert 0 < count < 63 and not any(any(row) for row in fields[count:])
    track,slot,byte=directory[:3]
    records=[]
    # Independent global enumeration also checks each cursor-based extraction.
    physical_order=[(t,s) for t in range(1,36) if t!=18 for s in order(t)]
    joined=b''.join(sector(disk,t,s) for t,s in physical_order)
    global_cursor=0
    for index,(low,high_minus_one,len_low,len_high) in enumerate(fields[:count]):
        load=low|(((high_minus_one+1)&255)<<8)
        size=(len_low|(len_high<<8))+1
        result,segments=bytearray(),[]
        begin=[track,slot,byte]
        while len(result)<size:
            if slot==SECTORS[track]:
                track+=1
                if track==18:
                    track+=1
                assert track<=35
                slot=0
            number=order(track)[slot]
            take=min(256-byte,size-len(result))
            raw=sector(disk,track,number)
            segments.append(dict(track=track,sector=number,sector_byte=byte,
                disk_offset=sector_offset(track,number)+byte,file_offset=len(result),bytes=take))
            result.extend(raw[byte:byte+take])
            byte+=take
            if byte==256:
                slot+=1
                byte=0
        result=bytes(result)
        assert result==joined[global_cursor:global_cursor+size]
        global_cursor+=size
        records.append(dict(index=index,load=load,bytes=size,payload_sha256=sha(result),
            table_fields=list(fields[index]),begin_cursor=begin,end_cursor=[track,slot,byte],
            prospective_destination_word=int.from_bytes(result[:2],'little'),
            segments=segments,payload=result))
    assert sum(r['bytes'] for r in records)==global_cursor
    return records,dict(track=18,sector=18,sha256=sha(directory),header=list(directory[:4]),
        entry_count=count,zero_padding_entries=63-count,
        field_offsets='4+index+63*field; load high stored minus1, length stored minus1',
        global_stream_bytes=global_cursor,independent_global_order_slicing_equal=True)


def source_guards():
    path=ROOT/'build/research/next-round/boot-analysis/bitfire-source/d64write/d64write.c'
    lines=path.read_text().splitlines()
    fragments=[
        'dir[0x03] = (side - 1) | 0xf0;',
        'dir[4 + dir_pos + (0 * 0x3f)] = loadaddr & 0xff;',
        'dir[4 + dir_pos + (1 * 0x3f)] = ((loadaddr >> 8) & 0xff) - 1;',
        'dir[4 + dir_pos + (2 * 0x3f)] = (length - 1) & 0xff;',
        'dir[4 + dir_pos + (3 * 0x3f)] = ((length - 1) >> 8) & 0xff;',
        'dir[0x0] = track;', 'dir[0x1] = sectnum;', 'dir[0x2] = sectpos;',
        'case 1 ... 17:', 'interleave = 4;', 'interleave = 3;',
        'if(*track == D64_DIR_TRACK) (*track)++;',
        'if(*sector > sectors[*track]) {', '*sector = revs;',
    ]
    guards=[]
    for fragment in fragments:
        hits=[index+1 for index,line in enumerate(lines) if fragment in line]
        assert hits,fragment
        guards.append(dict(fragment=fragment,lines=hits))
    return dict(source=artifact(path),commit='5a3964b533656332c12cc0904f2ce92f44499c6f',
        guards=guards,scope='Pinned public writer describes this table/cursor format; no whole-loader binary equivalence follows from a format match.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    out=parser.parse_args().output.resolve()
    out.relative_to((BASE/'disk-analysis').resolve())
    assert not out.exists(),'Choose a fresh output directory'
    assert sha(ZIP.read_bytes())==ZIP_SHA
    for name,expected in PINS.items():
        assert sha((ROOT/name).read_bytes())==expected,name
    guards=source_guards()
    out.mkdir(parents=True)
    rows,outputs,members=[],[],[]
    def save(name,raw):
        path=out/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(raw)
        row=dict(name=name,bytes=len(raw),sha256=sha(raw))
        outputs.append(row)
        return row
    with zipfile.ZipFile(ZIP) as archive:
        for member in archive.infolist():
            raw=archive.read(member)
            members.append(dict(name=member.filename,bytes=len(raw),sha256=sha(raw),CRC32=member.CRC,directory=member.is_dir()))
        for side,expected in DISKS.items():
            member=next(n for n in archive.namelist() if n.endswith('-'+side+'.d64'))
            disk=archive.read(member)
            assert len(disk)==174848 and sha(disk)==expected
            released=BASE/'release'/Path(member).name
            assert released.read_bytes()==disk
            entries,directory_links=dos_entries(disk)
            assert len(entries)==48 and {tuple(row['start']) for row in entries}=={(18,2)}
            bootstrap,chain=dos_chain(disk,entries[0]['start'])
            assert len(bootstrap)==2710 and sha(bootstrap)==BOOT_SHA
            assert bootstrap[:14]==bytes.fromhex('01080b0842069e32303631000000')
            assert bootstrap[0x1f:0x22]==bytes.fromhex('4c0300')
            assert bootstrap[0x10b:0x10e]==bytes.fromhex('4c000a')
            if side=='a':save('original-bootstrap.prg',bootstrap)
            streams,index=raw_streams(disk,side)
            for row in streams:
                payload=row.pop('payload')
                record=save(f'raw-{side}/{row["index"]:03d}-{row["load"]:04x}.prg',row['load'].to_bytes(2,'little')+payload)
                row['output']=record['name']
            assert len(streams)==(43 if side=='a' else 19)
            rows.append(dict(side=side,disk=artifact(released),DOS_directory=entries,DOS_directory_links=directory_links,
                bootstrap=dict(bytes=len(bootstrap),sha256=sha(bootstrap),load=0x801,payload_bytes=len(bootstrap)-2,
                    payload_end_exclusive=0x1295,payload_sha256=sha(bootstrap[2:]),basic_SYS=2061,entry=0x80d,
                    source_relocation=dict(source=[0x821,0x90d],destination=[1,0xed],entry_JMP=[0x81e,0x0003],
                        source_final_JMP=0x90a,relocated_final_JMP=0xea,unpacked_entry=0xa00),chain=chain),
                raw_directory=index,raw_streams=streams))
    checked=Path(__file__).read_bytes()
    save('disk.checked.py',checked)
    proof=dict(pass_=True,scope='Original ZIP/DOS bootstrap and source-described Bitfire-compatible raw streams; no unpacked payload or native ending acceptance',
        producer=artifact(Path(__file__)),inputs=[artifact(ZIP)]+[artifact(ROOT/name) for name in PINS],
        archive_members=members,source_format=guards,disks=rows,total_raw_streams=sum(len(row['raw_streams']) for row in rows),outputs=outputs,
        limits=['Both original DOS directories alias one identical bootstrap. Identical boot bytes do not prove that sideB independently starts the ending.',
            'Raw stream PRGs add the loader address from the original table. They are compressed/input resources, not claimed standalone executables.',
            'The first payload word is recorded as a prospective destination only; decompression, transformed data and scene identities remain separate.',
            'The public writer/source format match is not an assembled binary or exact installed-loader version match.',
            'Static bootstrap source bytes establish relocation and the literal0A00 jump, not native execution or decompressed output correctness.',
            'No CPU interpreter, emulator, process, assembler/build, downloaded host entrypoint, network access or product/index edit occurs.'])
    raw=(json.dumps(proof,indent=2)+'\n').encode()
    (out/'disk-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=True,receipt_bytes=len(raw),receipt_sha256=sha(raw),raw_streams=proof['total_raw_streams']),indent=2))


if __name__=='__main__':main()
