#!/usr/bin/env python3
"""Pin Relax24's wrapper/format and a strict startup boundary; no fake I/O."""
import hashlib
import importlib.metadata
import json
from pathlib import Path

from py65.devices.mpu6502 import MPU
from py65.disassembler import Disassembler

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'build/research/relax24'
ARCHIVE_SHA='0c68892c3a73cdeda0854eaa28db205672a9b02ed3f04ce185dbda72ad656fac'
SOURCE_SHA='ea9040469d211c87cdfd1aaa2a5eca04685be741d679bc1537cb7cc280810180'


def sha(data):return hashlib.sha256(data).hexdigest()
def record(path):
    data=Path(path).read_bytes()
    return dict(path=str(Path(path).resolve().relative_to(ROOT)),bytes=len(data),sha256=sha(data))
def checked(item):
    data=(ROOT/item['path']).read_bytes()
    assert len(data)==item['bytes'] and sha(data)==item['sha256'],item
    return data


class Boundary(Exception):pass
class StrictRam:
    def __init__(self,data,known):self.data,self.known=data,known;self.pc=0
    def __getitem__(self,address):
        if address in (0,1) or 0xd000<=address<0xe000:
            raise Boundary(('hardware-address read',self.pc,address))
        if not self.known[address]:raise Boundary(('unknown read',self.pc,address))
        return self.data[address]
    def __setitem__(self,address,value):
        if address in (0,1) or 0xd000<=address<0xe000:
            raise Boundary(('hardware-address write',self.pc,address,value))
        self.data[address]=value;self.known[address]=1


def main():
    output=BASE/'reader-analysis';output.mkdir(parents=True,exist_ok=True)
    archive_path=BASE/'archive-proof.json';assert sha(archive_path.read_bytes())==ARCHIVE_SHA
    archive=json.loads(archive_path.read_text());assert archive['pass']
    source=checked(archive['lynx']['extracted']);assert sha(source)==SOURCE_SHA
    assert len(source)==31211 and source[:2]==b'\x60\x07'
    data=bytearray(65536);known=bytearray(65536);data[0x760:0x8149]=source[2:];known[0x760:0x8149]=bytes([1])*31209
    assert data[0x801:0x80c]==bytes.fromhex('0c 08 c9 07 9e ff ac 36 35 36 00')
    basic_tokens=bytes(data[0x801:0x80c])
    assert data[0x80c:0x823]==bytes.fromhex('a0 00 78 ee 30 d0 4e 11 d0 e6 01 b9 52 7f 99 40 03 c8 d0 f7 4c 40 03')
    memory=StrictRam(bytearray(data),bytearray(known));cpu=MPU(memory=memory,pc=0x80c)
    steps=0;boundary=None
    try:
        while steps<16:
            memory.pc=cpu.pc;cpu.step();steps+=1
    except Boundary as error:boundary=list(error.args[0])
    assert boundary==['hardware-address read',0x80f,0xd030] and steps==2
    # Conditional literal copies only: never continue the CPU across its
    # hardware boundary or claim this is an initialized/depacked reader.
    copies=[]
    for first,end,target in ((0x7f52,0x8052,0x340),(0x8048,0x8148,0x723)):
        assert all(known[first:end]);data[target:target+end-first]=data[first:end];known[target:target+end-first]=bytes([1])*(end-first)
        copies.append(dict(source=[first,end],destination=[target,target+end-first],bytes=end-first,all_source_bytes_file_established=True))
    assert data[0x340:0x349]==bytes.fromhex('b9 48 80 99 23 07 c8 d0 f7')
    tables={name:list(data[first:end]) for name,first,end in [
        ('literal_bits',0x723,0x733),('literal_bases',0x733,0x743),
        ('match_bits',0x743,0x753),('match_bases',0x753,0x763),
        ('distance_bits',0x763,0x770),('distance_low_bases',0x770,0x77d),('distance_high_bases',0x77d,0x78a)]}
    d=Disassembler(MPU(memory=list(data)));pc=0x340;listing=[]
    while pc<0x436:
        length,text=d.instruction_at(pc);assert text!='???'
        listing.append(f'{pc:04X} {data[pc:pc+length].hex(" "):9} {text}');pc+=length
    assert pc==0x436
    listing_path=output/'file-derived-wrapper.txt';listing_path.write_text('\n'.join(listing)+'\n')
    articles=[]
    for item in archive['side2_files']:
        blob=checked(item['extracted']);name=item['directory_entry']['two_byte_name_prefix_ascii']
        articles.append(dict(name=name,source=item['extracted'],first_five_bytes=blob[:5].hex(' '),
            first_word_big_endian=int.from_bytes(blob[:2],'big'),file_bytes_minus_five=len(blob)-5,
            observed_count_relation=int.from_bytes(blob[:2],'big')==len(blob)-5))
    report=dict(script=record(Path(__file__)),py65_version=importlib.metadata.version('py65'),archive_proof=record(archive_path),
        source=archive['lynx']['extracted'],load_address=0x760,loaded_end_exclusive=0x8149,
        BASIC=dict(address=0x801,line=1993,tokens_hex=basic_tokens.hex(' '),
            expression='SYS pi*656',conventional_truncated_target=0x80c,
            scope='Token/static interpretation; no BASIC-ROM execution or native entry proof.'),
        strict_CPU=dict(assumed_entry=0x80c,completed_instructions=steps,nominal_cycles=cpu.processorCycles,boundary=boundary,
            hardware_responses=0,scope='Two original RAM instructions only; no execution beyond the first hardware-address read.'),
        conditional_literal_copies=copies,wrapper_listing=record(listing_path),tables=tables,
        source_derived_decoder=dict(bit_reader=0x3ca,buffer=0x78a,initial_buffer=data[0x78a],initial_remaining_bits=data[0x3d4],
            initial_source=int.from_bytes(data[0x3e8:0x3ea],'little'),refill='Decrement source first, then read MSB-first; first refill7F50.',
            initial_destination=int.from_bytes(data[0x40e:0x410],'little'),output='Store byte, then decrement destination.',
            literal_match_entry=0x352,length_entry=0x41c,hardware_cycle_wrapper=[0x349,0x352],hardware_exit=[0x3fe,0x40d],
            candidate_handoff=0x801,scope='Instruction-derived format description only; no decompression execution or recovered reader.'),
        side2_header_observations=articles,
        scope='Pinned wrapper/tables, strict startup boundary and raw file-header observations. No completed boot, recovered reader, decoded article, coding-review identity or native claim.',pass_=True)
    report['pass']=report.pop('pass_');path=output/'reader-proof.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(path.relative_to(ROOT)),sha256=sha(path.read_bytes()),strict_boundary=boundary,
        side2_files=len(articles),count_relation_matches=sum(item['observed_count_relation'] for item in articles)),indent=2))


if __name__=='__main__':main()
