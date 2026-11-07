#!/usr/bin/env python3
"""Inspect original CA point-plotting code, with strict RAM-only CPU contracts.

No VIC, IRQ, SID, drive, ROM or unknown-memory response is supplied. Native
captures are read-only inputs. Pure file-derived preparation and conditional
native-prestate draw/update proofs are recorded separately.
"""
import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

from py65.devices.mpu6502 import MPU
from py65.disassembler import Disassembler

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'build/research/second-reality'
sys.path.insert(0,str(ROOT/'research/quondam'))
from snapshot_state import read_snapshot, module_payload

FILES = {
    'CA': ('side1-entry14-CA.prg',0x6000,0x1800,'b795d4bd191a6dd6a153fa827a3c3e0175fb720c3266a38ae09e441df13b7554'),
    'BD': ('side1-entry13-BD.prg',0xc000,0x900,'99fae6d7d0b108be8f14a0ce067d96bc3aa661620d34b6493f7a1a76a4e7a49a'),
    'BC': ('side1-entry12-BC.prg',0x8600,0x3940,'25f2ec9af774fc49eba9ce0d1048722c73640ed23043fb23f45ce6d2aad581dc'),
}
STRIDE, GENERATED_FIRST, GENERATED_END = 1108, 0x2000, 0xaa80


def sha(data): return hashlib.sha256(data).hexdigest()
def relative(path): return str(Path(path).resolve().relative_to(ROOT))
def record(path):
    data=Path(path).read_bytes()
    return dict(path=relative(path),bytes=len(data),sha256=sha(data))
def ranges(values):
    result=[]
    for a in sorted(values):
        if result and result[-1][1]==a: result[-1][1]+=1
        else: result.append([a,a+1])
    return result
def comparison(actual,expected,first,end,label):
    differences=[dict(address=a,expected=expected[a],actual=actual[a]) for a in range(first,end) if actual[a]!=expected[a]]
    return dict(label=label,first=first,end_exclusive=end,bytes=end-first,
                matched_bytes=end-first-len(differences),exact=not differences,
                actual_sha256=sha(actual[first:end]),expected_sha256=sha(expected[first:end]),differences=differences)


class Boundary(Exception): pass
class KnownRam:
    def __init__(self,data,known,port=0x36,ddr=0x2f):
        self.data,self.known,self.port,self.ddr=data,known,port,ddr
        self.pc=0; self.writes=Counter(); self.reads=Counter(); self.graphic_stores=[]
    def mapping(self,a):
        pins=(self.port&self.ddr)|(7&~self.ddr)
        if 0xd000<=a<0xe000 and pins&3: return 'I/O' if pins&4 else 'character ROM'
        if 0xa000<=a<0xc000 and pins&3==3: return 'BASIC ROM'
        if a>=0xe000 and pins&2: return 'KERNAL ROM'
    def __getitem__(self,a):
        if a in (0,1): raise Boundary(('CPU-port access',self.pc,a))
        if self.mapping(a): raise Boundary(('Mapped read',self.pc,a,self.mapping(a)))
        if not self.known[a]: raise Boundary(('Unknown read',self.pc,a))
        self.reads[a]+=1
        return self.data[a]
    def __setitem__(self,a,value):
        if a in (0,1) or self.mapping(a)=='I/O': raise Boundary(('Hardware write',self.pc,a))
        self.data[a]=value; self.known[a]=1; self.writes[a]+=1
        if GENERATED_FIRST<=self.pc<GENERATED_END and a>=0xe000:
            offset=(self.pc-GENERATED_FIRST)%STRIDE
            self.graphic_stores.append(dict(pc=self.pc,address=a,value=value,
                                           kind='cached_clear' if offset<99 else 'point_plot'))


def run(data,known,entry,stop,registers=None,port=0x36,ddr=0x2f,limit=2_000_000):
    ram=KnownRam(data,known,port,ddr); cpu=MPU(memory=ram,pc=entry)
    cpu.p=cpu.UNUSED; cpu.sp=255
    if registers:
        for key in ('a','x','y','sp'): setattr(cpu,key,registers[key])
        cpu.p=registers['flags']
    counts=Counter(); steps=0
    while not (steps and cpu.pc==stop):
        if steps>=limit: raise AssertionError(('Instruction budget',cpu.pc,entry,stop))
        ram.pc=cpu.pc
        opcode=ram[cpu.pc]
        assert cpu.instruct[opcode].__name__!='inst_not_implemented',(cpu.pc,opcode)
        counts[cpu.pc]+=1; cpu.step(); steps+=1
    result=dict(entry=entry,stop_pc=cpu.pc,completed_instructions=steps,nominal_cpu_cycles=cpu.processorCycles,
                final_cpu=dict(pc=cpu.pc,a=cpu.a,x=cpu.x,y=cpu.y,sp=cpu.sp,flags=cpu.p),
                instruction_counts=dict(sorted(counts.items())),read_ranges=ranges(ram.reads),written_ranges=ranges(ram.writes),
                distinct_written_bytes=len(ram.writes),total_writes=sum(ram.writes.values()),RAM_sha256=sha(data),
                known_mask_sha256=sha(known),hardware_or_unknown_accesses=0,
                scope='Literal original instructions on known RAM only; no interrupts or hardware/ROM/unknown responses.')
    return ram,result


def native(directory,name):
    ram_path,vsf_path=directory/('ram-'+name+'.bin'),directory/(name+'.vsf')
    raw=ram_path.read_bytes(); state=read_snapshot(vsf_path)
    assert len(raw)==65536 and state['modules']['C64MEM']['version']==[0,1]
    mem=module_payload(vsf_path,'C64MEM'); assert raw==mem[4:65540]
    cpu=module_payload(vsf_path,'MAINCPU'); assert state['modules']['MAINCPU']['version']==[1,4]
    regs=dict(clock=int.from_bytes(cpu[:8],'little'),a=cpu[8],x=cpu[9],y=cpu[10],sp=cpu[11],
              pc=int.from_bytes(cpu[12:14],'little'),flags=cpu[14])
    return bytearray(raw),state,regs,dict(name=name,ram=record(ram_path),snapshot=record(vsf_path),cpu=regs,
                                         port_latch=mem[0],port_ddr=mem[1],
                                         vic={key:state['vicii'][key] for key in ('regs','color_ram','raster_line','raster_cycle','rc','vc','vcbase','idle_state','bad_line')},
                                         physical_ram_exact=True)


def emit_disassembly(memory,first,end):
    dis=Disassembler(MPU(memory=list(memory))); result=[]; pc=first
    while pc<end:
        length,text=dis.instruction_at(pc)
        result.append(f'{pc:04X}  {memory[pc:pc+length].hex(" "):9} {text}')
        pc+=length
    assert pc==end,(first,end,pc)
    return '\n'.join(result)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,default=BASE/'native-02')
    parser.add_argument('--output',type=Path,default=BASE/'ca-analysis')
    args=parser.parse_args(); output=args.output.resolve(); output.mkdir(parents=True,exist_ok=True)
    directory=args.capture.resolve(); session_path=directory/'session.json'; session=json.loads(session_path.read_text())
    assert session.get('closed_utc'),'Final CA evidence requires the owner-closed session.'
    source={}; file_records={}
    for name,(filename,target,size,digest) in FILES.items():
        path=BASE/'disk-map'/filename; data=path.read_bytes()
        assert len(data)==size+2 and int.from_bytes(data[:2],'little')==target and sha(data)==digest
        memory=bytearray(65536); memory[target:target+size]=data[2:]
        source[name]=memory; file_records[name]=record(path)
    ca=source['CA']; rebased=bytearray(ca); known=bytearray(65536)
    known[0x6000:0x7800]=bytes([1])*0x1800
    for first,end,target in ((0x6000,0x6c00,0xc000),(0x6c00,0x6d00,0xcf00),(0x7000,0x7800,0x9000)):
        rebased[target:target+end-first]=ca[first:end]; known[target:target+end-first]=bytes([1])*(end-first)
    assert ca[0x6d12:0x6d20]==bytes.fromhex('a9 00 85 50 85 52 a9 60 85 51 a9 c0 85 53')
    assert ca[0x6d5f:0x6d62]==bytes.fromhex('4c 00 c0') and source['BD'][0xc8ab:0xc8ae]==bytes.fromhex('4c 00 6d')
    captures={name:native(directory,name) for name in ('ca-gate','ca-relocator','ca-entry','ca-prepared',
                                                       'ca-iteration-a','ca-iteration-b','ca-iteration-c','ca-iteration-d')}
    entry=captures['ca-entry'][0]; prepared=captures['ca-prepared'][0]
    entry_checks=[comparison(entry,rebased,first,end,label) for first,end,label in (
        (0xc000,0xcc00,'All 3072 relocated CA code/table bytes'),
        (0xcf00,0xd000,'All 256 relocated loader-page bytes'),
        (0x9000,0x9800,'All 2048 relocated prepared-data bytes'))]
    assert all(check['exact'] for check in entry_checks)
    # Start at the actual original JSR site, so return stack bytes are created
    # by original instructions rather than supplying a synthetic RTS target.
    preparation_ram,table_run=run(rebased,known,0xc085,0xc088)
    assert rebased[0xc085:0xc088]==bytes.fromhex('20 00 c5')
    assert all(known[0xb000:0xc000])
    expected_expansion=bytearray(65536)
    for n in range(32):
        quarter=ca[0x7000+n*64:0x7040+n*64]
        expected_expansion[0xb000+n*128:0xb080+n*128]=quarter+quarter[::-1]
    expanded_check=comparison(rebased,expected_expansion,0xb000,0xc000,'All 4096 mirrored motion-table bytes from32 original64-byte quarters')
    assert expanded_check['exact']
    generated_ram,generation_run=run(rebased,known,0xc0b3,0xc840)
    assert generated_ram.data[0xc0b3:0xc0b6]==bytes.fromhex('4c 00 c2')
    pointer_checks=[]
    for index in range(32):
        stored=rebased[0xc800+index]+256*rebased[0xc820+index]
        assert stored==GENERATED_FIRST+STRIDE*index
        pointer_checks.append(dict(index=index,entry=stored,end_exclusive=stored+STRIDE))
    prep_checks=[expanded_check,comparison(prepared,rebased,0xb000,0xc000,'Native full mirrored motion-table preparation'),
                 comparison(prepared,rebased,GENERATED_FIRST,GENERATED_END,'Every one of35,456 original-generated kernel bytes before first draw'),
                 comparison(prepared,rebased,0x400,0x600,'All512 coordinate-address lookup bytes'),
                 comparison(prepared,rebased,0xb00,0xc00,'All256 initialized style/state bytes')]
    assert all(check['exact'] for check in prep_checks)
    (output/'file-derived-generated.ram').write_bytes(rebased)
    # Bind one complete steady iteration to an actual native prestate. This
    # executes neither entry/IRQ code nor any monitor intervention.
    before,before_state,before_cpu,before_record=captures['ca-iteration-a']
    after,after_state,after_cpu,after_record=captures['ca-iteration-b']
    assert before_cpu['pc']==after_cpu['pc']==0xc85f
    interval_ram,interval_run=run(bytearray(before),bytearray([1])*65536,0xc85f,0xc85f,before_cpu,
                                  before_record['port_latch'],before_record['port_ddr'])
    expected=interval_ram.data
    full_difference=comparison(after,expected,0,65536,'All final native RAM versus IRQ-free literal native-prestate iteration; every difference retained')
    interval_checks=[comparison(after,expected,first,end,label) for first,end,label in (
        (0x2000,0xaa80,'All35,456 generated code/cache bytes after literal draw'),
        (0xe000,0x10000,'All8192 screen/character/hidden-plane RAM bytes after literal draw'),
        (0xa00,0xa41,'All65 next-position bytes including literal duplicate end stores'),
        (0xb00,0xb23,'All35 shifted style/state bytes'),
        (0x2c0,0x2c5,'Five phase/instance counters'))]
    cpu_comparison=[dict(register=key,expected=interval_run['final_cpu'][key],actual=after_cpu[key],
                         exact=interval_run['final_cpu'][key]==after_cpu[key]) for key in ('pc','a','x','y','sp','flags')]
    assert all(check['exact'] for check in interval_checks)
    plots=interval_ram.graphic_stores
    assert Counter(item['kind'] for item in plots)==dict(cached_clear=992,point_plot=992)
    plot_path=output/'iteration-a-to-b-plot-stores.json'; plot_path.write_text(json.dumps(plots,indent=2)+'\n')
    (output/'iteration-a-to-b-ram-only-expected.bin').write_bytes(expected)
    # Curated reachable instruction intervals only. Adjacent coordinate/profile
    # tables remain bytes and are never disassembled as renderer code.
    disassembly=[]
    for first,end in ((0xc000,0xc0b6),(0xc0b9,0xc12a),(0xc200,0xc252),(0xc280,0xc38b),
                      (0xc390,0xc3f3),(0xc440,0xc496),(0xc500,0xc53f),(0xc540,0xc565),
                      (0xc580,0xc5fd),(0xc840,0xc8ad),(0xc900,0xc94b)):
        disassembly.append(emit_disassembly(rebased,first,end))
    dis_path=output/'ca-reachable-instructions.txt'; dis_path.write_text('\n'.join(disassembly))
    elapsed=[dict(first=first,last=last,clocks=captures[last][2]['clock']-captures[first][2]['clock'])
             for first,last in zip(('ca-iteration-a','ca-iteration-b','ca-iteration-c'),('ca-iteration-b','ca-iteration-c','ca-iteration-d'))]
    report=dict(script=record(Path(__file__)),py65_version=importlib.metadata.version('py65'),
                files=file_records,session=record(session_path),session_closed_utc=session['closed_utc'],
                snapshot_reader=record(ROOT/'research/quondam/snapshot_state.py'),captures=[captures[name][3] for name in captures],
                relocation_checks=entry_checks,file_derived_table_execution=table_run,file_derived_generation_execution=generation_run,
                prepared_checks=prep_checks,generated_kernels=dict(first=GENERATED_FIRST,end_exclusive=GENERATED_END,
                    bytes=GENERATED_END-GENERATED_FIRST,count=32,bytes_per_kernel=STRIDE,clear_prefix_bytes=99,
                    point_pair_template_bytes=63,point_pairs_per_kernel=16,trailing_rts_bytes=1,pointers=pointer_checks,
                    draw_instances=list(range(1,32))),
                native_prestate_iteration=dict(first=before_record['name'],last=after_record['name'],execution=interval_run,
                    exact_domain_checks=interval_checks,cpu_comparison=cpu_comparison,full_RAM_observation=full_difference,
                    original_native_elapsed_clocks=after_cpu['clock']-before_cpu['clock'],
                    cached_clear_stores=992,point_plot_stores=992,plot_store_receipt=record(plot_path),
                    scope='Conditional on captured pre-RAM/CPU/port state; no IRQ delivery or hardware response. Exact semantic domains and complete unfiltered RAM differences are separate.'),
                observed_native_intervals=elapsed,reachable_disassembly=record(dis_path),
                pass_=all(check['exact'] for check in entry_checks+prep_checks+interval_checks) and all(item['exact'] for item in cpu_comparison),
                limitations=['Logical draw/update boundaries are not coherent frame or PAL-period boundaries.',
                             'RAM-only CPU cycle totals exclude VIC stalls, IRQ/music, ROM, drive and other hardware.',
                             'Every full-RAM mismatch from concurrent native execution is retained; no whole-machine equality is claimed.',
                             'Native PNGs are original-output observations, without an independent pixel/composition oracle.',
                             'No named author phase, vector geometry pipeline, polygon-fill or historical-priority claim.'])
    report['pass']=report.pop('pass_'); target=output/'ca-proof.json'; target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(receipt=relative(target),sha256=sha(target.read_bytes()),pass_=report['pass'],
                         generated_bytes=GENERATED_END-GENERATED_FIRST,pure_iteration_cycles=interval_run['nominal_cpu_cycles'],
                         native_interval_clocks=after_cpu['clock']-before_cpu['clock'],full_RAM_mismatches=len(full_difference['differences']),
                         CPU_exact=all(item['exact'] for item in cpu_comparison)),indent=2))
    assert report['pass'],'Contract mismatch; CPU and byte comparison details are retained in the receipt.'


if __name__=='__main__': main()
