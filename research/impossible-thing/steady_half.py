#!/usr/bin/env python3
"""Replay one captured half-image up to, but never through, the next I/O store."""
from collections import Counter
import hashlib
import importlib.metadata
import json
from pathlib import Path

from py65.devices.mpu6502 import MPU

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'build/research/impossible-thing'


def sha(data):return hashlib.sha256(data).hexdigest()
def record(path):
    data=Path(path).read_bytes()
    return dict(path=str(Path(path).resolve().relative_to(ROOT)),bytes=len(data),sha256=sha(data))
def comparison(actual,expected,first,end,label):
    assert len(actual)==len(expected)==65536
    differences=[dict(address=a,expected=expected[a],actual=actual[a]) for a in range(first,end) if actual[a]!=expected[a]]
    return dict(label=label,first=first,end_exclusive=end,bytes=end-first,exact=not differences,
                matched_bytes=end-first-len(differences),differences=differences,
                actual_sha256=sha(actual[first:end]),expected_sha256=sha(expected[first:end]))
def ranges(addresses):
    result=[]
    for address in sorted(set(addresses)):
        if result and result[-1][1]==address:result[-1][1]+=1
        else:result.append([address,address+1])
    return result


class KnownMachineRam:
    def __init__(self,data,port,ddr):
        self.data=data;self.pins=(port&ddr)|(7&~ddr);self.pc=0
        self.reads=Counter();self.writes=Counter();self.graphic_stores=[]
    def mapped(self,address):
        if 0xd000<=address<0xe000 and self.pins&3:
            return 'I/O' if self.pins&4 else 'character ROM'
        if 0xa000<=address<0xc000 and self.pins&3==3:return 'BASIC ROM'
        if address>=0xe000 and self.pins&2:return 'KERNAL ROM'
    def __getitem__(self,address):
        assert address not in (0,1),('CPU port read',self.pc,address)
        assert not self.mapped(address),('Mapped read',self.pc,address,self.mapped(address))
        self.reads[address]+=1;return self.data[address]
    def __setitem__(self,address,value):
        assert address not in (0,1),('CPU port write',self.pc,address)
        assert self.mapped(address)!='I/O',('I/O write',self.pc,address,value)
        self.data[address]=value;self.writes[address]+=1
        if address>=0xe000:self.graphic_stores.append(dict(pc=self.pc,address=address,value=value))


def main():
    output=BASE/'steady-analysis';output.mkdir(parents=True,exist_ok=True)
    path=BASE/'native-analysis/native-evidence.json';proof=json.loads(path.read_text());assert proof['pass']
    captures={item['name']:item for item in proof['captures']};before,after=captures['select-01'],captures['select-02']
    before_path,after_path=ROOT/before['ram']['path'],ROOT/after['ram']['path']
    before_data,after_data=before_path.read_bytes(),after_path.read_bytes()
    assert sha(before_data)==before['ram']['sha256'] and sha(after_data)==after['ram']['sha256']
    start,end=before['registers'],after['registers'];assert start['pc']==end['pc']==0x227f
    assert start['a']==0xda and end['a']==0xc8
    data=bytearray(before_data);memory=KnownMachineRam(data,start['port01'],start['port00'])
    cpu=MPU(memory=memory,pc=0x227f)
    for key in ('a','x','y','sp'):setattr(cpu,key,start[key])
    cpu.p=start['flags'];counts=Counter();steps=0
    while cpu.pc!=0x227c:
        assert steps<1_000_000,('Instruction budget',cpu.pc)
        memory.pc=cpu.pc;op=memory[cpu.pc]
        assert cpu.instruct[op].__name__!='inst_not_implemented',(cpu.pc,op)
        counts[cpu.pc]+=1;cpu.step();steps+=1
    assert data[0x227c:0x227f]==bytes.fromhex('8d 18 d0')
    # The original next instruction is precisely the skipped D018 store.
    # It changes no CPU flags/registers, only advancing PC by3.
    cpu_checks=[dict(register=key,expected=getattr(cpu,key),actual=end[key],exact=getattr(cpu,key)==end[key])
                for key in ('a','x','y','sp')]
    cpu_checks.append(dict(register='flags',expected=cpu.p,actual=end['flags'],exact=cpu.p==end['flags']))
    domain=[]
    for first,last,label in [(0xe000,0x10000,'Entire8192-byte font/screen/hidden-plane range'),
                             (0x2000,0x2920,'Entire original renderer/program region including runtime SMC'),
                             (0x3800,0x4000,'All packed texture tables'),
                             (0x4000,0xb200,'All generated glyph-writer code')]:
        domain.append(comparison(after_data,data,first,last,label))
    zp=sorted(address for address in memory.writes if 2<=address<256)
    zp_diff=[dict(address=a,expected=data[a],actual=after_data[a]) for a in zp if data[a]!=after_data[a]]
    zp_check=dict(addresses=zp,bytes=len(zp),differences=zp_diff,exact=not zp_diff,
                  scope='Every zero-page byte written by the literal renderer, without selecting favorable subranges.')
    full=comparison(after_data,data,0,65536,'Unfiltered final RAM: literal IRQ-free replay versus native endpoint')
    assert len(memory.graphic_stores)==2048+1000,len(memory.graphic_stores)
    assert Counter(item['address'] for item in memory.graphic_stores)==Counter(range(0xe000,0xe800))+Counter(range(0xf000,0xf3e8))
    stores=output/'graphic-stores.json';stores.write_text(json.dumps(memory.graphic_stores,indent=2)+'\n')
    expected=output/'expected-endpoint.ram';expected.write_bytes(data)
    report=dict(script=record(Path(__file__)),py65_version=importlib.metadata.version('py65'),
        native_receipt=record(path),before=before,after=after,
        original_execution=dict(first_pc=0x227f,stop_pc=cpu.pc,completed_instructions=steps,
            nominal_cpu_cycles=cpu.processorCycles,instruction_counts=dict(sorted(counts.items())),
            read_ranges=ranges(memory.reads),written_ranges=ranges(memory.writes),
            graphic_stores=len(memory.graphic_stores),literal_font_stores=2048,literal_matrix_stores=1000,
            hardware_or_ROM_responses=0,IRQ_delivery=False),
        endpoint_alignment=dict(expected_PC=0x227c,native_PC=0x227f,
            skipped_instruction='STA D018,3 bytes/4 nominal cycles; no CPU register or flag changes.',
            scope='Expected state stops BEFORE I/O; native state is immediately AFTER that one original store.'),
        cpu_comparisons=cpu_checks,exact_domain_checks=domain,renderer_written_ZP=zp_check,
        full_RAM_observation=full,native_elapsed_clocks=end['clock']-start['clock'],
        graphic_store_receipt=record(stores),expected_endpoint=record(expected),
        scope='One native-prestate-conditional half-image. No hardware/IRQ response or timing model is supplied. Exact domains and all other full-RAM differences are separately retained; no whole-machine or independent pixel claim.',
        pass_=all(item['exact'] for item in domain+cpu_checks) and zp_check['exact'])
    report['pass']=report.pop('pass_');target=output/'half-proof.json';target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(target.relative_to(ROOT)),sha256=sha(target.read_bytes()),pass_=report['pass'],
        completed_instructions=steps,nominal_cycles=cpu.processorCycles,native_elapsed=report['native_elapsed_clocks'],
        full_RAM_differences=len(full['differences'])),indent=2))
    assert report['pass'],'Differences remain visible in half-proof.json'


if __name__=='__main__':main()
