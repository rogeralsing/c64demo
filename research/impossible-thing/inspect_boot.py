#!/usr/bin/env python3
"""Bounded original Impossible Thing decoder execution; no hardware responses."""
from collections import Counter
import hashlib
import importlib.metadata
import json
from pathlib import Path

from py65.devices.mpu6502 import MPU
from py65.disassembler import Disassembler

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'build/research/impossible-thing'
PRG_SHA='a79f294f7a506bd489135dbf56515e939d8a14a6b16cafccea38673d09acca8d'


def sha(data):return hashlib.sha256(data).hexdigest()
def record(path):
    data=Path(path).read_bytes()
    return dict(path=str(Path(path).resolve().relative_to(ROOT)),bytes=len(data),sha256=sha(data))
def ranges(addresses):
    result=[]
    for address in sorted(set(addresses)):
        if result and result[-1][1]==address:result[-1][1]+=1
        else:result.append([address,address+1])
    return result


class Boundary(Exception):pass
class KnownRam:
    def __init__(self,data,known,io_visible=False):
        self.data,self.known=data,known;self.pc=0;self.reads=Counter();self.writes=Counter();self.output=[]
        self.counter_reads=[];self.counter_writes=[]
        self.io_visible=io_visible
    def __getitem__(self,address):
        if address in (0,1):raise Boundary(('CPU port read',self.pc,address))
        if self.io_visible and 0xd000<=address<0xe000:raise Boundary(('I/O read',self.pc,address))
        if not self.known[address]:raise Boundary(('unknown read',self.pc,address))
        self.reads[address]+=1
        if address==0x400:self.counter_reads.append(self.pc)
        return self.data[address]
    def __setitem__(self,address,value):
        if address in (0,1):raise Boundary(('CPU port write',self.pc,address,value))
        if self.io_visible and 0xd000<=address<0xe000:raise Boundary(('I/O write',self.pc,address,value))
        self.data[address]=value;self.known[address]=1;self.writes[address]+=1
        if address==0x400:self.counter_writes.append(self.pc)
        if self.pc==0x7b5:self.output.append(dict(address=address,value=value))


class Core(MPU):
    def step(self):
        # Only the pinned entry's ANC immediate extension is interpreted.
        # Formula agrees with VICE's original 6510core.c ANC macro. Every
        # other unimplemented opcode remains an error, never a NOP.
        if self.pc==0x801 and self.memory[self.pc]==0x0b:
            self.a &= self.memory[self.pc+1]
            self.p &= ~(self.NEGATIVE|self.ZERO|self.CARRY)
            if self.a==0:self.p|=self.ZERO
            if self.a&0x80:self.p|=self.NEGATIVE|self.CARRY
            self.pc+=2;self.processorCycles+=2
            return self
        return super().step()


def execute(data,known,entry,stop=None,limit=1_000_000,core=MPU,io_visible=False):
    memory=KnownRam(data,known,io_visible);cpu=core(memory=memory,pc=entry)
    cpu.a=cpu.x=cpu.y=0;cpu.sp=255;cpu.p=cpu.UNUSED|cpu.INTERRUPT
    steps=0;counts=Counter();boundary=None
    while cpu.pc!=stop:
        assert steps<limit,('instruction limit',cpu.pc)
        memory.pc=cpu.pc
        try:
            op=memory[cpu.pc]
            assert core is Core and cpu.pc==0x801 and op==0x0b or cpu.instruct[op].__name__!='inst_not_implemented',(cpu.pc,op)
            pc=cpu.pc;cpu.step();counts[pc]+=1;steps+=1
        except Boundary as error:
            boundary=list(error.args[0]);break
    return memory,dict(entry=entry,stop_pc=cpu.pc,boundary=boundary,completed_instructions=steps,
        nominal_cpu_cycles=cpu.processorCycles,registers=dict(a=cpu.a,x=cpu.x,y=cpu.y,sp=cpu.sp,flags=cpu.p),
        instruction_counts=dict(sorted(counts.items())),read_ranges=ranges(memory.reads),
        written_ranges=ranges(memory.writes),total_writes=sum(memory.writes.values()))


def main():
    out=BASE/'binary';out.mkdir(parents=True,exist_ok=True)
    path=BASE/'impossible-thing.prg';prg=path.read_bytes();assert sha(prg)==PRG_SHA
    initial=bytearray(65536);initial[0x801:0x1607]=prg[2:]
    known=bytearray(65536);known[0x801:0x1607]=bytes([1])*len(prg[2:])
    _,strict=execute(bytearray(initial),bytearray(known),0x801,core=Core)
    assert strict['boundary']==['CPU port read',0x80e,1]
    # The first256-byte copy spans unknown startup padding. Record that
    # boundary, without supplying a byte or continuing its whole boot.
    assert initial[0x810:0x81c]==bytes.fromhex('b9 93 15 99 40 03 c8 d0 f7 4c 40 03')
    # Separately reconstruct only file-established bytes for the later
    # decoder copy. The original source is entirely inside this PRG.
    decoder=bytearray(initial);mask=bytearray(known)
    decoder[0x340:0x3b4]=initial[0x1593:0x1607];mask[0x340:0x3b4]=bytes([1])*116
    decoder[0xfa:0x1fa]=initial[0x14d9:0x15d9];mask[0xfa:0x1fa]=bytes([1])*256
    # Starting at0100 is conditional on the ordinary copy's finalY=0,
    # binary arithmetic and all-RAM visibility. It neither executes nor
    # fabricates the preceding CPU-port/raster/optional KERNAL branch.
    _,strict_decoder=execute(bytearray(decoder),bytearray(mask),0x100)
    assert strict_decoder['boundary']==['unknown read',0x13f,0x400]
    decoder[0x400]=0;mask[0x400]=1
    _,counter_only=execute(bytearray(decoder),bytearray(mask),0x100)
    assert counter_only['boundary']==['unknown read',0x7b9,0x12]
    decoder[0x12]=0;mask[0x12]=1
    memory,result=execute(decoder,mask,0x100)
    assert result['boundary'] and result['boundary'][0]=='CPU port write',result
    events=memory.output;assert events
    addresses=[event['address'] for event in events]
    first,end=min(addresses),max(addresses)+1
    assert len(addresses)==len(set(addresses))==end-first
    assert addresses==list(range(end-1,first-1,-1))
    assert memory.counter_reads and set(memory.counter_reads)==set(memory.counter_writes)=={0x13f}
    # INC affects only its counter and N/Z. The next flag setter is LDX at
    # 0145, before any condition reads N/Z; A and carry are untouched by INC.
    assert decoder[0x13f:0x149]==bytes.fromhex('ee 00 04 ea 85 11 a6 fe a5 ff')
    output=bytes(decoder[first:end]);(out/'conditional-unpacked.ram').write_bytes(decoder)
    (out/'conditional-known-mask.bin').write_bytes(mask)
    (out/'unpacked-output.prg').write_bytes(first.to_bytes(2,'little')+output)
    (out/'output-stores.json').write_text(json.dumps(events,indent=2)+'\n')
    # Only actual instruction intervals at the handoff are disassembled.
    dis=Disassembler(MPU(memory=list(decoder)));pc=0x2000;lines=[]
    while pc<0x2080:
        length,text=dis.instruction_at(pc)
        lines.append(f'{pc:04X}  {decoder[pc:pc+length].hex(" "):9} {text}');pc+=length
    (out/'entry-instructions.txt').write_text('\n'.join(lines)+'\n')
    report=dict(script=record(Path(__file__)),py65_version=importlib.metadata.version('py65'),source=record(path),
        strict_entry=strict,
        first_copy=dict(source=[0x1593,0x1693],destination=[0x340,0x440],
            file_known_source=[0x1593,0x1607],unknown_source=[0x1607,0x1693],unknown_bytes=140,
            scope='Static literal-copy contract only; strict entry already stops at CPU-port access.'),
        skipped_bootstrap=dict(first=0x340,unresolved_reads=[0x01,0xa2,0xd012],optional_KERNAL_vectors=[0xffba,0xffbd,0xffc0,0xffe7],
            scope='Not executed or mocked. The optional branch and KERNAL behavior are unresolved by file bytes.'),
        strict_isolated_decoder=strict_decoder,
        counter_only_conditional_decoder=counter_only,
        conditional_decoder=dict(source=[0x14d9,0x15d9],destination=[0xfa,0x1fa],
            preconditions=['All-RAM visibility; no IRQs or hardware/ROM delivery.',
                           'Y=0 from the completed original 256-byte copy; decimal flag clear; SP=FF for this isolated run.',
                           'Initial A/X/C are overwritten before they affect decoded bytes.',
                           'External screen counter0400 is explicitly seeded0, not established by the file.',
                           'Caller zero-page12 is explicitly seeded0; this affects length control and is not file-established or proved independent.'],
            external_counter=dict(address=0x400,chosen_initial=0,read_pcs=sorted(set(memory.counter_reads)),
                write_pcs=sorted(set(memory.counter_writes)),increments=len(memory.counter_writes),
                independence_argument='Only INC0400 at013F accesses this byte. Its value is never loaded into A/X/Y or used as an address. INC changes only N/Z, which LDX at0145 overwrites before any conditional use; carry and decoded length in A are unaffected.'),
            execution=result,output_first=first,output_end_exclusive=end,output_bytes=len(output),
            output_sha256=sha(output),output_stores=len(events),unique_consecutive_reverse_stores=True,
            handoff_after_port_restore=0x2000,handoff_signature=decoder[0x2000:0x2020].hex(' ')),
        artifacts=[record(out/name) for name in ('conditional-unpacked.ram','conditional-known-mask.bin','unpacked-output.prg','output-stores.json','entry-instructions.txt')],
        scope='Bounded conditional RAM decoder with an explicit independent screen-counter seed and caller ZP12=0 assumption. All three strict boundaries retained. No fully file-established decode, full-bootstrap, native output, renderer, refresh-rate, VIC or music proof.',pass_=True)
    report['pass']=report.pop('pass_');target=out/'boot-proof.json';target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(target.relative_to(ROOT)),sha256=sha(target.read_bytes()),
        decoder_instructions=result['completed_instructions'],boundary=result['boundary'],
        output_first=hex(first),output_end_exclusive=hex(end),output_bytes=len(output),output_sha256=sha(output)),indent=2))


if __name__=='__main__':main()
