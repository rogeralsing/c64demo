#!/usr/bin/env python3
"""Inspect original Second Reality side1 bootstrap with strict known RAM.

Outer boot stops on unknown file padding. A separately labelled, file-derived
relocation feeds the SFX pager, which also stops on unknown padding. Only its
already-established decompressor/code/input are then run as a RAM-only routine.
No unknown byte, KERNAL, I/O, drive or interrupt response is supplied.
"""
import argparse
from collections import Counter,deque
import hashlib
import importlib.metadata
import json
from pathlib import Path
from py65.devices.mpu6502 import MPU

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'build/research/second-reality'
DISK_SHA='05aa03c00be26cab0618f8802477d0bc7226af029c003a253a34bd32c630acf2'
BOOT_SHA='c62598561f3bb6d74e9c399385df6e1dd21890c9fc0abbd952a2a61548a286f5'


def sha(data):return hashlib.sha256(data).hexdigest()
def count(t):
    assert 1<=t<=35
    return 21 if t<=17 else 19 if t<=24 else 18 if t<=30 else 17
def sector(d,t,s):
    assert 0<=s<count(t)
    offset=256*(sum(count(i) for i in range(1,t))+s)
    return d[offset:offset+256]
def extract(d):
    data,chain,seen=bytearray(),[],set();t,s=17,0
    while t:
        assert (t,s) not in seen;seen.add((t,s));block=sector(d,t,s)
        chain.append(dict(track=t,sector=s,sha256=sha(block),link=list(block[:2])))
        data.extend(block[2:256 if block[0] else block[1]+1]);t,s=block[:2]
    return bytes(data),chain


class Boundary(Exception):
    def __init__(self,kind,pc,address,mapping=None):
        self.detail=dict(kind=kind,instruction_pc=pc,address=address,mapping=mapping)
class Ram:
    def __init__(self,data,known):
        self.data,self.known=data,known;self.pc=0;self.writes=Counter();self.output=[]
    def mapping(self,a):
        pins=(self.data[1]&self.data[0])|(7&~self.data[0])
        if 0xd000<=a<0xe000 and pins&3:return 'I/O' if pins&4 else 'character ROM'
        if 0xa000<=a<0xc000 and pins&3==3:return 'BASIC ROM'
        if a>=0xe000 and pins&2:return 'KERNAL ROM'
    def __getitem__(self,a):
        mapping=self.mapping(a)
        if mapping:raise Boundary('mapped_read',self.pc,a,mapping)
        if not self.known[a]:raise Boundary('unknown_read',self.pc,a)
        return self.data[a]
    def __setitem__(self,a,v):
        if self.mapping(a)=='I/O':raise Boundary('I/O_write',self.pc,a,'I/O')
        self.data[a]=v;self.known[a]=1;self.writes[a]+=1
        if self.pc==0x426:self.output.append((a,v))


def initial(blob):
    data,known=bytearray(65536),bytearray(65536)
    data[0x801:0xaf89]=blob[2:];known[0x801:0xaf89]=bytes([1])*(len(blob)-2)
    data[:2]=b'\x2f\x37';known[:2]=b'\x01\x01'
    return data,known
def ranges(addresses):
    result=[]
    for a in sorted(addresses):
        if result and result[-1][1]==a:result[-1][1]+=1
        else:result.append([a,a+1])
    return result


def run(data,known,entry,stop=None,x=0,y=0,limit=2_000_000):
    ram=Ram(data,known);cpu=MPU(memory=ram,pc=entry);cpu.p=cpu.UNUSED;cpu.sp=255;cpu.x=x;cpu.y=y
    history,counts,first_bytes=deque(maxlen=16),Counter(),{}
    completed=0;boundary=None
    for _ in range(limit):
        if cpu.pc==stop:break
        ram.pc=cpu.pc
        before=dict(pc=cpu.pc,a=cpu.a,x=cpu.x,y=cpu.y,p=cpu.p,sp=cpu.sp)
        try:
            opcode=ram[cpu.pc]
            assert cpu.instruct[opcode].__name__!='inst_not_implemented',(cpu.pc,opcode)
            first_bytes.setdefault(cpu.pc,bytes(data[cpu.pc:cpu.pc+3]).hex(' '))
            history.append(before);counts[cpu.pc]+=1;cpu.step();completed+=1
        except Boundary as error:
            boundary=error.detail;break
    else:raise AssertionError(('Instruction limit',cpu.pc))
    return ram,dict(entry=entry,stop_pc=boundary['instruction_pc'] if boundary else cpu.pc,
                    status='boundary' if boundary else 'reached_handoff',boundary=boundary,
                    completed_instructions=completed,nominal_cpu_cycles=cpu.processorCycles,
                    last_pre_instruction_states=list(history),instruction_counts=dict(sorted(counts.items())),
                    first_instruction_bytes=dict(sorted(first_bytes.items())),
                    written_ranges=ranges(ram.writes),known_ranges=ranges(a for a,k in enumerate(known) if k),
                    RAM_sha256=sha(data),known_mask_sha256=sha(known),
                    isolated_execution='No IRQ delivery; no mapped reads or unknown RAM values supplied')


def native_compare(native,expected,first,end,label):
    actual=native.read_bytes();assert len(actual)==65536
    differences=[dict(address=a,expected=expected[a],actual=actual[a]) for a in range(first,end) if actual[a]!=expected[a]]
    return dict(file=str(native.relative_to(ROOT)),sha256=sha(actual),label=label,first=first,end_exclusive=end,
                bytes=end-first,matched_bytes=end-first-len(differences),exact=not differences,differences=differences)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--disk',type=Path,default=BASE/'author-http-members/2ndReality_S1.D64')
    parser.add_argument('--output',type=Path,default=BASE/'binary')
    args=parser.parse_args();disk=args.disk.read_bytes()
    assert len(disk)==174848 and sha(disk)==DISK_SHA
    blob,chain=extract(disk);assert len(blob)==42890 and sha(blob)==BOOT_SHA and len(chain)==169
    assert blob[:12]==bytes.fromhex('01 08 0b 08 01 00 9e 32 33 30 34 00')
    args.output.mkdir(parents=True,exist_ok=True);(args.output/'side1-boot.prg').write_bytes(blob)
    data,known=initial(blob);original=bytes(data)
    assert data[0x900:0x91b]==bytes.fromhex('a2 00 bd 80 09 9d 00 c0 e8 d0 f7 a2 00 bd c0 08 9d e0 05 e8 e0 28 d0 f5 4c 00 c0')
    outer,outer_result=run(data,known,0x900)
    assert outer_result['boundary']['kind']=='unknown_read' and outer_result['boundary']['address']==0xaf89
    (args.output/'file-only-prefix.ram').write_bytes(data)
    data,known=initial(blob)
    # Original post-uploader forward relocation; input is original file bytes,
    # not native RAM and not a fictitious successful KERNAL/drive execution.
    data[0x801:0xa901]=original[0xa00:0xab00]
    known[0x801:0xa901]=bytes([1])*0xa100
    assert data[0x80d:0x81d]==bytes.fromhex('78 a2 a1 a0 78 84 01 b9 31 08 99 ff 03 88 d0 f7')
    packed_reference=bytes(data)
    pager,pager_result=run(data,known,0x80d)
    assert pager_result['boundary']['kind']=='unknown_read' and pager_result['boundary']['address']==0x739
    (args.output/'conditional-SFX-copy-prefix.ram').write_bytes(data)
    input_reference=bytes(data)
    # Last page reads $0739..$0838 into $5f00..$5fff. Its unknown padding
    # never becomes a decoder input: the established reader starts $6053.
    # X=Y=0 follows from fixed page-loop counters, independent of data values.
    # Initial A is unused before the original reader overwrites it.
    assert all(known[a] for a in range(0x400,0x478))
    assert all(known[a] for a in range(0x6053,0x10000))
    assert data[0x40b:0x410]==bytes.fromhex('e8 c8 20 4e 04')
    assert data[0x44e:0x451]==bytes.fromhex('ad 53 60')
    # At the strict stop this page retains old file data, but a completed
    # pager would overwrite it with partly unknown source bytes. Invalidate
    # the entire excluded page so stale known values cannot pass as inputs.
    known[0x5f00:0x6000]=bytes(0x100)
    core,core_result=run(data,known,0x40b,stop=0x9400,x=0,y=0)
    assert core_result['status']=='reached_handoff'
    assert core.output and core.output[0][0]==0x7e8
    assert all(a==0x7e8+i for i,(a,_) in enumerate(core.output))
    end=0x7e8+len(core.output)
    output=bytes(v for _,v in core.output)
    assert output==data[0x7e8:end]
    (args.output/'file-derived-unpacked.ram').write_bytes(data)
    (args.output/'file-derived-known-mask.bin').write_bytes(known)
    (args.output/'unpacked-output.prg').write_bytes(b'\xe8\x07'+output)
    core_result.update(output_first=0x7e8,output_end_exclusive=end,output_bytes=len(output),output_sha256=sha(output),
                       output_store_pc=0x426,output_event_sha256=sha(b''.join(a.to_bytes(2,'little')+bytes([v]) for a,v in core.output)),
                       entry_preconditions=dict(x=0,y=0,decimal=False,initial_A='overwritten before use'),
                       excluded_unknown_page=dict(source=[0x739,0x839],destination=[0x5f00,0x6000],
                                                  rule='No padding value is supplied or read by this routine-only proof'))
    comparisons=[];native=BASE/'native-01'
    for name,expected,first,last,label in [
        ('ram-packed-entry.bin',packed_reference,0x801,0xa901,'All literal161-page relocation bytes'),
        ('ram-depack-entry.bin',input_reference,0x400,0x478,'All established decompressor code bytes'),
        ('ram-depack-entry.bin',input_reference,0x6053,0x10000,'All established actual compressed-reader input bytes'),
        ('ram-first-entry.bin',data,0x7e8,end,'Every independently decompressed output byte')]:
        if (native/name).exists():comparisons.append(native_compare(native/name,expected,first,last,label))
    result=dict(pass_=True,disk_sha256=DISK_SHA,boot_sha256=BOOT_SHA,boot_bytes=len(blob),DOS_chain=chain,
                BASIC_SYS=2304,entry=0x900,load=0x801,file_end_exclusive=0xaf89,
                script_sha256=sha(Path(__file__).read_bytes()),py65_version=importlib.metadata.version('py65'),
                file_only_boot=outer_result,conditional_SFX_pager=pager_result,RAM_only_decompressor=core_result,
                native_comparisons=comparisons,
                scope='Known-file-only outer boundary and separately labelled conditional relocation/SFX routine proof. Native RAM is comparison-only, never an input. No drive, ROM, I/O, IRQ or first-display execution.')
    result['pass']=result.pop('pass_') and all(c['exact'] for c in comparisons)
    (args.output/'boot-proof.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(pass_=result['pass'],outer_boundary=outer_result['boundary'],pager_boundary=pager_result['boundary'],
                         output_bytes=len(output),output_range=[0x7e8,end],core_instructions=core_result['completed_instructions']),indent=2))
    assert result['pass'],'Native comparison mismatches retained in boot-proof.json'


if __name__=='__main__':main()
