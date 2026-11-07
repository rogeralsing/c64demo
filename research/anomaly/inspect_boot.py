#!/usr/bin/env python3
"""Inspect Anomaly's original Sparkle2.3 boot and decode its disk data offline.

The host decoder follows byte-bound original SL/SD/Packer data semantics. It
does not run the downloaded tool, drive/C64 loader, ROM or hardware. The only
CPU execution is six file-known boot instructions ending before JSR KERNAL.
"""
import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'build/research/anomaly'
OUT=BASE/'binary-analysis'
SOURCE=OUT/'source/sparkle-2.3.23.105'
COMMIT='427e8be5743e70e9ea206eeef49cb4c971b1cba3'
DISKS=('d452497845598cca8936fdf57c60fdc9c70cd7e64110e049fa6fc7d735f940cd',
       '3b537ade95fc1312d0c1b6ef2d042041e454ca3055c687fd8aaaf46a4a00a41e')


def sha(data):return hashlib.sha256(data).hexdigest()
def record(path):
    data=path.read_bytes();return dict(path=str(path.relative_to(ROOT)),bytes=len(data),sha256=sha(data))
def verify_primary_sources():
    receipts=[OUT/'source/acquisitions.json',OUT/'source/older-tool-comparisons.json',
              OUT/'source/first-bundle-acquisitions.json',SOURCE/'acquisitions.json']
    rows=[]
    for path in receipts:
        receipt=json.loads(path.read_text());files=receipt if isinstance(receipt,list) else receipt['files']
        for row in files:
            source=ROOT/row['path'];data=source.read_bytes()
            assert len(data)==row['bytes'] and sha(data)==row['sha256']
            blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            assert blob==row['git_blob_sha1']
            rows.append(dict(source_path=row['source_path'],git_blob_sha1=blob,**record(source)))
    return dict(acquisition_receipts=[record(path) for path in receipts],files=rows)
def sectors(track):
    assert 1<=track<=35
    return 21 if track<=17 else 19 if track<=24 else 18 if track<=30 else 17
def sector(disk,track,number):
    assert 0<=number<sectors(track)
    first=256*(sum(sectors(t) for t in range(1,track))+number)
    return disk[first:first+256]
def linked(disk,track,number):
    result=bytearray();chain=[]
    while track:
        assert (track,number) not in [(r['track'],r['sector']) for r in chain]
        block=sector(disk,track,number);chain.append(dict(track=track,sector=number,sha256=sha(block)))
        result+=block[2:256 if block[0] else block[1]+1];track,number=block[:2]
    return bytes(result),chain
def directory(disk):
    track,number=18,1;entries=[];seen=set()
    while track:
        assert (track,number) not in seen;seen.add((track,number));block=sector(disk,track,number)
        for slot in range(8):
            item=block[2+32*slot:32+32*slot]
            if item[0]:entries.append(dict(type=item[0],track=item[1],sector=item[2],name_hex=item[3:19].hex(),blocks=int.from_bytes(item[28:30],'little')))
        track,number=block[:2]
    return entries
def transform(value):return value^(0x7f if value&9 in (0,9) else 0x76)


def physical_order(interleaves):
    """Independent translation of the pinned builder's CalcTabs data layout."""
    result=[];start_sector=0
    for track in range(1,36):
        if track==18:start_sector+=2;continue
        size=sectors(track);zone=0 if track<18 else 1 if track<25 else 2 if track<31 else 3
        interleave=interleaves[zone]%size
        if start_sector>=size:
            start_sector-=size
            if track<18 and start_sector>0:start_sector-=1
        track_start=start_sector;used=set()
        while len(used)<size:
            if start_sector not in used:
                used.add(start_sector)
                result.append(dict(track=track,sector=start_sector,track_start=track_start,remaining=size-len(used)+1))
                start_sector+=interleave
                if start_sector>=size:
                    start_sector-=size
                    if track<18 and start_sector>0:start_sector-=1
            else:start_sector=(start_sector+1)%size
    assert len(result)==664 and len({(r['track'],r['sector']) for r in result})==664
    return result


def internal_directory(disk,order):
    raw=b''.join(bytes(sector(disk,18,s)[(-i)&255] for i in range(256)) for s in (17,18))
    result=[]
    for index in range(128):
        entry=raw[4*index:4*index+4];track,start,remaining=map(transform,entry[:3])
        found=[i for i,r in enumerate(order) if (r['track'],r['track_start'],r['remaining'])==(track,start,remaining)]
        assert len(found)==1,(index,track,start,remaining)
        result.append(dict(bundle=index,track=track,track_start=start,remaining_on_track=remaining,
                           bit_pointer=entry[3],block_index=found[0],sector=order[found[0]]['sector']))
    return result


class DecodeError(Exception):pass
class Decoder:
    def __init__(self,disk,order,transitional_blocks,memory=None,known=None):
        self.disk,self.order=disk,order
        self.transitional_blocks=set(transitional_blocks)
        self.memory=bytearray(65536) if memory is None else memory
        self.known=bytearray(65536) if known is None else known
    def load(self,index,pointer):
        assert 0<=index<len(self.order);self.block_index=index
        physical=self.order[index];self.buffer=bytearray(sector(self.disk,physical['track'],physical['sector']))
        self.blocks.append(dict(block_index=index,**physical,sha256=sha(self.buffer),
            transitional_block_count_removed=index in self.transitional_blocks,
            original_block_count_field=self.buffer[1] if index in self.transitional_blocks else None))
        # Original byte-bound SD ChkLastBlock saves this field as NBC then
        # writes7F to the transformed drive buffer: C64 receives zero here.
        # Only directory-identified transitional blocks carry that field.
        if index in self.transitional_blocks:self.buffer[1]=0
        self.bits=self.buffer[pointer];assert self.bits
        self.pointer=(pointer-1)&255;self.nibble=None;self.buffer[0]=0
    def byte(self):
        value=self.buffer[self.pointer];self.pointer=(self.pointer-1)&255;return value
    def bit(self):
        carry=self.bits>>7;self.bits=(self.bits<<1)&255
        if self.bits==0:
            value=self.byte();self.bits=((value<<1)|1)&255;carry=value>>7
        return carry
    def write(self,value):
        address=self.destination;self.memory[address]=value;self.known[address]=1
        self.writes[address]+=1;self.destination=(address-1)&65535
    def file(self):
        low=self.byte();high=self.byte();under_io=high==0
        if under_io:high=self.byte()
        self.destination=low+256*high
        self.headers.append(dict(block_index=self.block_index,address_last=self.destination,under_IO=under_io))
    def literal(self):
        length=1
        if self.bit():
            if self.nibble is None:
                value=self.byte();length=value&15;self.nibble=value>>4
            else:length=self.nibble;self.nibble=None
            if length==0:length=self.byte()
            length+=1
        self.tokens['literal']+=1
        for _ in range(length):self.write(self.byte())
    def decode(self,entry):
        self.blocks=[];self.headers=[];self.writes=Counter();self.reads=Counter();self.tokens=Counter()
        self.load(entry['block_index'],entry['bit_pointer']);self.file();mode='literal'
        for token in range(500_000):
            if mode=='literal':self.literal();mode='match';continue
            tag=self.byte();self.tokens['match_tag']+=1
            if tag==0:
                self.load(self.block_index+1,0);self.file();mode='literal';continue
            if tag&3:length=(tag&3)+1;offset=(tag>>2)+1
            elif tag==0x80:self.file();mode='literal';continue
            else:
                high=0 if tag&0x80 else self.byte()
                length=(tag&0x7c)>>2
                if length==1:
                    length=self.byte()
                    if length==0:
                        assert tag==0x84
                        return dict(bundle=entry['bundle'],entry=entry,blocks=self.blocks,headers=self.headers,
                            tokens=dict(self.tokens),written_bytes=len(self.writes),total_writes=sum(self.writes.values()),
                            written_ranges=intervals(self.writes),source_read_bytes=len(self.reads),
                            source_read_ranges=intervals(self.reads),next_bit_pointer=self.pointer,
                            end_block_index=self.block_index,scope='Offline original-disk data decoding, not CPU/IEC/drive execution.')
                assert 2<=length<=255,(tag,length)
                offset=high*256+self.byte()+1
            self.tokens['match']+=1
            for _ in range(length):
                source=(self.destination+offset)&65535
                if not self.known[source]:raise DecodeError(('Unknown match source',entry['bundle'],hex(source),hex(self.destination),length,offset,self.block_index,self.pointer))
                self.reads[source]+=1;self.write(self.memory[source])
            mode='match' if self.bit() else 'literal'
        raise DecodeError(('Token budget',entry['bundle']))


def intervals(values):
    result=[]
    for address in sorted(values):
        if result and result[-1][1]==address:result[-1][1]+=1
        else:result.append([address,address+1])
    return result


def boot_cpu(blob):
    from py65.devices.mpu6502 import MPU
    class Memory:
        def __init__(self):
            self.data=bytearray(65536);self.known=bytearray(65536)
            self.data[0x801:0xb41]=blob[2:];self.known[0x801:0xb41]=bytes([1])*0x340;self.pc=0;self.writes=[]
        def __getitem__(self,address):
            assert address not in (0,1) and address<0xa000 and self.known[address],('Unproved read',self.pc,address)
            return self.data[address]
        def __setitem__(self,address,value):
            assert address not in (0,1) and address<0xa000
            self.data[address]=value;self.known[address]=1;self.writes.append(dict(pc=self.pc,address=address,value=value))
    memory=Memory();cpu=MPU(memory=memory,pc=0x810);cpu.p=cpu.UNUSED;cpu.sp=255;instructions=[]
    for _ in range(6):
        memory.pc=cpu.pc;instructions.append(cpu.pc);cpu.step()
    assert cpu.pc==0x81c and memory.data[0x81c:0x81f]==bytes.fromhex('20 0c ed')
    return dict(instructions=instructions,count=6,nominal_CPU_cycles=cpu.processorCycles,stop_pc=cpu.pc,
                boundary='Before JSR $ED0C KERNAL; no ROM, drive, hardware or unknown data supplied.',
                initial_register_conditions='SP255, flags20; neither affects these six instructions. No initial port/RAM value invented.',
                writes=memory.writes)


def bind_drive(disk):
    original=b''.join(sector(disk,18,s) for s in range(11,17))
    blob=(SOURCE/'Resources/SD.prg').read_bytes();assert int.from_bytes(blob[:2],'little')==0x2300 and len(blob)==1337
    # Author builder explicitly zero-initializes six pages before copying SD.
    memory=bytearray(1536);memory[:len(blob)-2]=blob[2:]
    transformed=bytes(transform(memory[768+(-i&255)]) for i in range(256))
    memory[768:1024]=memory[1024:1280];memory[1024:1280]=memory[1280:1536];memory[1280:1536]=transformed
    before=[dict(offset=i,canonical=a,original=b) for i,(a,b) in enumerate(zip(memory,original)) if a!=b]
    assert [r['offset'] for r in before]==[27,28,29,91,92,93,95,867]
    bam=sector(disk,18,0);product=bytes(transform(bam[i]) for i in (0xf8,0xf7,0xf6))
    memory[0x1b:0x1e]=product
    # Literal matching-tool resource version2.3.23.105 and original drive BCD
    # version23/01/05. Exact host build uniqueness is not inferred.
    memory[0x5b:0x5e]=bytes.fromhex('23 01 05');memory[0x5f]=0x23
    for offset,bam_offset in ((0x360,0xfe),(0x361,0xfd),(0x362,0xfc),(0x363,0xfb),(0x364,0xfa)):
        memory[offset]=transform(bam[bam_offset])
    assert memory==original
    return dict(canonical_SD=record(SOURCE/'Resources/SD.prg'),raw_sectors=[[18,s] for s in range(11,17)],
        raw_bytes=1536,raw_sha256=sha(original),differences_before_documented_config=before,
        all1536_bytes_equal_after_config=True,product_id_hex=product.hex(),version_BCD_hex=original[0x5b:0x5e].hex(),
        version_major_minor_byte=original[0x5f],normalization='SD ChkLastBlock removes transitional block count: transformed7F becomes C64 zero at buffer[1].')


def payload_check(bundle,blob,first,label):
    ram=(ROOT/bundle['RAM']['path']).read_bytes();known=(ROOT/bundle['known_mask']['path']).read_bytes()
    end=first+len(blob);assert all(known[first:end]),('Unknown decoded payload byte',label)
    differences=[dict(address=first+i,decoded=a,expected=b) for i,(a,b) in enumerate(zip(ram[first:end],blob)) if a!=b]
    return dict(label=label,bundle=bundle['bundle'],first=first,end_exclusive=end,bytes=len(blob),all_bytes_file_known=True,
                decoded_sha256=sha(ram[first:end]),expected_sha256=sha(blob),exact=not differences,differences=differences)


def native_bindings(capture):
    """Passive source-byte joins only; independent lifecycle checker is separate."""
    sys.path.insert(0,str(ROOT/'research/quondam'))
    from snapshot_state import read_snapshot,module_payload
    source_path=OUT/'side1-binary-proof.json';source=json.loads(source_path.read_text());assert source['pass']
    assert source['script']['sha256']==sha(Path(__file__).read_bytes())
    session_path=capture/'session.json';session=json.loads(session_path.read_text());assert session.get('closed_utc')
    names=('boot-entry','resident-copied','first-return','entry-fade-return','base-music-return','fade-assets-return','fade-call-return','humanmade-entry')
    captures={};checks=[]
    for name in names:
        ram_path=capture/('ram-'+name+'.bin');vsf_path=capture/(name+'.vsf');ram=ram_path.read_bytes()
        state=read_snapshot(vsf_path);mem=module_payload(vsf_path,'C64MEM');cpu=module_payload(vsf_path,'MAINCPU')
        assert state['modules']['C64MEM']['version']==[0,1] and state['modules']['MAINCPU']['version']==[1,4]
        assert len(ram)==65536 and ram==mem[4:65540]
        captures[name]=dict(ram=ram,record=dict(name=name,ram=record(ram_path),snapshot=record(vsf_path),
            pc=int.from_bytes(cpu[12:14],'little'),clock=int.from_bytes(cpu[:8],'little')))
    def compare(name,expected,first,end,label):
        actual=captures[name]['ram'];different=[a for a in range(first,end) if actual[a]!=expected[a]]
        checks.append(dict(capture=name,label=label,first=first,end_exclusive=end,bytes=end-first,
            exact=not different,different_addresses=different,actual_sha256=sha(actual[first:end]),expected_sha256=sha(expected[first:end])))
    boot=(OUT/'side1-boot.prg').read_bytes();expected=bytearray(65536);expected[0x801:0xb41]=boot[2:]
    compare('boot-entry',expected,0x801,0xb41,'Every832 DOS-loaded boot byte before SYS entry')
    resident=captures['resident-copied']['ram'];expected[0x160:0x2fc]=resident[0x9a5:0xb41]
    expected[0x2fc:0x300]=resident[0xb41:0xb45]
    compare('resident-copied',expected,0x160,0x300,'All416 literal copied bytes, including4 actual native source-tail bytes')
    expected[0x160:0x2fc]=boot[0x9a5-0x801+2:]
    compare('resident-copied',expected,0x160,0x2fc,'All412 file-defined resident bytes versus original boot')
    for name,index in (('first-return',0),('entry-fade-return',1),('base-music-return',2),('fade-assets-return',3),('humanmade-entry',4)):
        bundle=source['bundles'][index];expected=(ROOT/bundle['RAM']['path']).read_bytes()
        for first,end in bundle['written_ranges']:
            compare(name,expected,first,end,'Every independently decoded original bundle'+str(index)+' range')
    pcs=[0x810,0x8b5,0xff40,0xff40,0xff54,0xff63,0xff66,0x2d00]
    assert [captures[name]['record']['pc'] for name in names]==pcs
    report=dict(script=record(Path(__file__)),source_proof=record(source_path),session=record(session_path),
        session_closed_utc=session['closed_utc'],captures=[captures[name]['record'] for name in names],checks=checks,
        scope='Passive original-source payload/relocation comparisons. Lifecycle/input/process provenance is checked separately; initialized effect is not rerun.',
        pass_=all(row['exact'] for row in checks))
    report['pass']=report.pop('pass_');target=OUT/'native-payload-comparisons.json';target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(target.relative_to(ROOT)),sha256=sha(target.read_bytes()),pass_=report['pass'],checks=len(checks)),indent=2))
    assert report['pass']


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--side',type=int,default=1,choices=(1,))
    parser.add_argument('--native-only',action='store_true');parser.add_argument('--capture',type=Path,default=BASE/'native-02')
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    if args.native_only:native_bindings(args.capture);return
    primary_sources=verify_primary_sources()
    path=BASE/'original'/f'WeAreTheAnomaly-Side{args.side}.d64';disk=path.read_bytes();assert len(disk)==174848 and sha(disk)==DISKS[args.side-1]
    entries=directory(disk);assert {(r['track'],r['sector']) for r in entries}=={(18,7)}
    boot,chain=linked(disk,18,7);assert len(boot)==834
    (OUT/f'side{args.side}-boot.prg').write_bytes(boot)
    canonical=(SOURCE/'Resources/Loader.prg').read_bytes();assert len(canonical)==834
    different=[dict(file_offset=i,canonical=a,original=b) for i,(a,b) in enumerate(zip(canonical,boot)) if a!=b]
    assert [r['file_offset'] for r in different]==[261,264]
    configured_entry=((boot[261]<<8)|boot[264])+1
    assert configured_entry==0xff40
    executable=OUT/'source/Extras/Sparkle/Sparkle2.exe';exe=executable.read_bytes();boot_array_offset=exe.find(canonical)
    assert boot_array_offset==0x11b520
    assert '2.3.23.105'.encode('utf-16le') in exe
    resident=boot[0x9a5-0x801+2:];assert len(resident)==412
    (OUT/'resident-file-defined.bin').write_bytes(resident)
    drive=bind_drive(disk)
    bam=sector(disk,18,0);interleaves=[(-transform(bam[position]))&255 for position in (0xfa,0xfc,0xfd,0xfe)]
    assert interleaves==[4,3,3,3]
    order=physical_order(interleaves);internal=internal_directory(disk,order)
    unique=[]
    for entry in internal:
        key=(entry['block_index'],entry['bit_pointer'])
        if key not in [(r['block_index'],r['bit_pointer']) for r in unique]:unique.append(entry)
    assert len(unique)==40 and unique[-1]['bundle']==39
    assert all((entry['block_index'],entry['bit_pointer'])==(unique[-1]['block_index'],unique[-1]['bit_pointer']) for entry in internal[39:])
    terminal=unique[-1];terminal_bytes=sector(disk,terminal['track'],terminal['sector']);pointer=terminal['bit_pointer']
    assert terminal['block_index']==663 and pointer==11 and terminal_bytes[7:12]==bytes.fromhex('00 00 03 08 41')
    terminal=dict(entry=terminal,first_destination=0x308,first_literal=0,next_tag=0,
        scope='Final self-overwriting buffer-reset dummy requests a next block/side, not another complete payload. No next-disk input supplied.')
    bundles=[];failure=None
    for entry in unique[:-1]:
        # Every bundle is independently file-known. No prior effect state or
        # previous bundle RAM is carried into its match-source dictionary.
        decoder=Decoder(disk,order,{entry['block_index'] for entry in unique})
        try:bundle=decoder.decode(entry)
        except (AssertionError,DecodeError) as error:failure=dict(bundle=entry['bundle'],type=type(error).__name__,error=str(error));break
        ram=OUT/f'side{args.side}-bundle{entry["bundle"]:03d}.ram';mask=ram.with_suffix('.known')
        ram.write_bytes(decoder.memory);mask.write_bytes(decoder.known)
        bundle.update(RAM=record(ram),known_mask=record(mask));bundles.append(bundle)
    assert failure is None and len(bundles)==39
    checks=[]
    for index,name in ((0,'CIADetect'),(1,'EntryWithBASICFade'),(2,'Main-BaseCode')):
        path_to_prg=OUT/'source/Link/Main'/(name+'.prg');prg=path_to_prg.read_bytes()
        checks.append(payload_check(bundles[index],prg[2:],int.from_bytes(prg[:2],'little'),'Original bundle versus published Link '+name))
    with zipfile.ZipFile(ROOT/'build/research/frontier-2026/anomaly-author.zip') as archive:
        sid=archive.read('Music/Exordium.sid');data_offset=int.from_bytes(sid[6:8],'big');address=int.from_bytes(sid[8:10],'big');data=sid[data_offset:]
        if address==0:address=int.from_bytes(data[:2],'little');data=data[2:]
        checks.append(payload_check(bundles[2],data,address,'Every Exordium payload byte from original author ZIP SID'))
    arcade_path=BASE/'Link/ArcadeScroller/ArcadeScroller.prg';arcade=arcade_path.read_bytes()
    assert sha(arcade)=='8ee85d5dad9035e205bb68391ab5b4e033c5c596a7e62f840db270f63b1fc16c'
    for address,offset,length in ((0x2800,2,0x972f),(0xe000,0xb802,2820)):
        checks.append(payload_check(bundles[36],arcade[offset:offset+length],address,'Original Arcade bundle36 versus production Link section'))
    assert bundles[36]['written_ranges']==[[0x2800,0xbf2f],[0xe000,0xeb04]] and bundles[36]['written_bytes']==41523
    driver=(ROOT/bundles[35]['RAM']['path']).read_bytes()
    assert driver[0x8ab:0x8c3]==bytes.fromhex('20 00 c0 20 09 08 ad 8f 08 f0 fb a9 00 8d 8f 08 20 00 3b ad 8f 08 f0 fb')
    report=dict(script=record(Path(__file__)),source_commit=COMMIT,primary_sources=primary_sources,primary_source_acquisitions=record(SOURCE/'acquisitions.json'),
        py65_version=importlib.metadata.version('py65'),disk=record(path),DOS_directory=entries,boot_chain=chain,boot_SHA256=sha(boot),
        canonical_loader=record(SOURCE/'Resources/Loader.prg'),canonical_differences=different,configured_RTS_entry=configured_entry,
        matching_tool=dict(file=record(executable),canonical_array_file_offset=boot_array_offset,resource_version='2.3.23.105',
            scope='Exact boot-image family; matching retained bytes do not prove one unique host executable build.'),
        file_known_boot_CPU=boot_cpu(boot),resident=dict(file_defined_source=[0x9a5,0xb41],file_defined_destination=[0x160,0x2fc],
            source_tail_outside_PRG=[0xb41,0xb45],destination_native_tail=[0x2fc,0x300],
            copied_bytes=416,overlap_bytes=96,file_defined_bytes=412,sha256=sha(resident),post_copy_checkpoint=0x8b5,
            symbols=dict(SendCmd=0x160,LoadA=0x182,LoadFetched=0x185,LoadNext=0x200,IRQ=0x2e2,IRQ_JSR=0x2f0,RTI=0x2fb)),
        byte_bound_drive_image=drive,interleaves_from_original_BAM=interleaves,internal_directory=internal,unique_entry_count=len(unique),
        independently_file_known_real_bundles=39,terminal_dummy=terminal,bundles=bundles,decoder_failure=failure,payload_checks=checks,
        arcade=dict(bundle=36,production_Link_PRG=record(arcade_path),matched_payload_bytes=41523,all_sections_exact=all(row['exact'] for row in checks[-2:]),
            source_holes_not_loaded=[[0xbf2f,0xe000]],native_execution_claim=False,
            incoming_original_driver_bundle=35,loader_call=0x8ae,return_pc=0x8b1,wait_flag=0x88f,actual_call=0x8bb,entry=0x3b00,
            entry_guard=arcade[0x3b00-0x2800+2:0x3b18-0x2800+2].hex()),
        limitations=['Offline data decoder, not CPU/IEC/1541/VIC timing or native execution.',
            'Four bytes copied beyond PRG are not synthesized.',
            'Each decoded bundle starts with unknown RAM and uses only bytes defined inside that bundle; no runtime-prestate backreference is synthesized.',
            'Published source is not rebuilt. Original Arcade section equality binds the bundled production Link artifact, not arbitrary later source builds.'],pass_=failure is None and all(row['exact'] for row in checks))
    report['pass']=report.pop('pass_')
    assert report['matching_tool']['canonical_array_file_offset']==0x11b520
    target=OUT/f'side{args.side}-binary-proof.json';target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(target.relative_to(ROOT)),sha256=sha(target.read_bytes()),pass_=report['pass'],
                          unique_entries=len(unique),decoded=len(bundles),failure=failure),indent=2))


if __name__=='__main__':main()
