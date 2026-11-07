#!/usr/bin/env python3
"""Prove DB's DA-pattern preparation and literal two-source OR bitmap kernel.

File-only preparation stops before the CPU-port write. A separate host scatter
oracle checks the following pure data loop. One native-prestate steady update
runs original instructions on known RAM with no IRQ/hardware/ROM responses.
"""
import argparse
from collections import Counter
import importlib.metadata
import json
from pathlib import Path

from py65.devices.mpu6502 import MPU
from inspect_ca import BASE, ROOT, KnownRam, comparison, native, ranges, record, sha
from inspect_da import load_inputs

TRANSITION_SHA='eb75376e089794a6d1468090274b8a27259e3550b91f3139566e95e87beffe2c'


class DbRam(KnownRam):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs); self.bitmap_stores=[]
    def __setitem__(self,address,value):
        super().__setitem__(address,value)
        if 0xc7c0<=self.pc<0xcbee and address>=0xe000:
            self.bitmap_stores.append(dict(pc=self.pc,address=address,value=value))


def run(data,known,entry,stop,registers=None,port=0x36,ddr=0x2f,limit=2_000_000):
    ram=DbRam(data,known,port,ddr); cpu=MPU(memory=ram,pc=entry)
    cpu.p=cpu.UNUSED; cpu.sp=255
    if registers:
        for key in ('a','x','y','sp'):setattr(cpu,key,registers[key])
        cpu.p=registers['flags']
    counts=Counter(); steps=0
    while not (steps and cpu.pc==stop):
        assert steps<limit,('Instruction budget',entry,stop,cpu.pc)
        ram.pc=cpu.pc; opcode=ram[cpu.pc]
        assert cpu.instruct[opcode].__name__!='inst_not_implemented',(cpu.pc,opcode)
        counts[cpu.pc]+=1;cpu.step();steps+=1
    result=dict(entry=entry,stop_pc=cpu.pc,completed_instructions=steps,nominal_cpu_cycles=cpu.processorCycles,
                final_cpu=dict(pc=cpu.pc,a=cpu.a,x=cpu.x,y=cpu.y,sp=cpu.sp,flags=cpu.p),
                instruction_counts=dict(sorted(counts.items())),read_ranges=ranges(ram.reads),written_ranges=ranges(ram.writes),
                RAM_sha256=sha(data),known_mask_sha256=sha(known),hardware_or_unknown_accesses=0,
                scope='Known RAM only; CPU-port/hardware writes, mapped ROM reads and unknown reads are rejected. No IRQ delivery.')
    return ram,result


def scatter_oracle(phase_memory):
    """Literal $C4D8..$C54A data layout, independently expressed as indices."""
    result=bytearray(phase_memory)
    for block in range(32):
        for row in range(8):
            for column in range(32):
                source=0x8000+block*512+row*64+column
                target=0x4000+block*512+column*8+row
                result[target]=(phase_memory[source]*2)&255
                result[target+256]=(phase_memory[source+32]*2)&255
    return result


def lookup_oracle(db):
    result=bytearray(65536)
    for row in range(64):
        result[0x400+2*row]=row&7
        result[0x401+2*row]=0x40+((row>>2)&0xfe)
        result[0x700+2*row]=(row<<6)&0xc0
        result[0x701+2*row]=0x80+(row>>2)
    for row in range(64):
        result[0x400+2*(127-row):0x402+2*(127-row)]=result[0x400+2*row:0x402+2*row]
        result[0x700+2*(127-row):0x702+2*(127-row)]=result[0x700+2*row:0x702+2*row]
    result[0x500:0x580]=db[0xc300:0xc380]
    result[0x580:0x600]=db[0xc300:0xc380]
    result[0x600:0x680]=db[0xc380:0xc400]
    result[0x680:0x700]=db[0xc380:0xc400]
    return result


def kernel_oracle(memory,y_start):
    """Independent OR values/addresses from prepared operands, no CPU steps."""
    result=bytearray(memory); events=[]; source_rows=[]
    for row in range(96):
        pc=0xc7c2+11*row; zp=0x28+2*row
        assert memory[pc:pc+3]==bytes([0xb1,zp,0x1d])
        assert memory[pc+5]==memory[pc+8]==0x9d
        pointer=memory[zp]+256*memory[(zp+1)&255]
        or_base=int.from_bytes(memory[pc+3:pc+5],'little')
        dst1=int.from_bytes(memory[pc+6:pc+8],'little')
        dst2=int.from_bytes(memory[pc+9:pc+11],'little')
        assert dst2==dst1+1
        source_rows.append(dict(row=row,indirect_zp=zp,indirect_base=pointer,or_base=or_base,
                                bitmap_destination=dst1,duplicate_destination=dst2))
    for column in range(32):
        x=column*8;y=(y_start+column)&255
        for row,source in enumerate(source_rows):
            address1=(source['indirect_base']+y)&65535
            address2=(source['or_base']+x)&65535
            assert 0x8000<=address1<0xc000 and 0x4000<=address2<0x8000
            value=memory[address1]|memory[address2]
            pc=0xc7c2+11*row
            for offset,target in ((5,source['bitmap_destination']+x),(8,source['duplicate_destination']+x)):
                result[target]=value;events.append(dict(pc=pc+offset,address=target,value=value))
    assert len(events)==6144
    return result,events,source_rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,default=BASE/'native-03')
    parser.add_argument('--output',type=Path,default=BASE/'db-analysis')
    args=parser.parse_args(); output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    session_path=args.capture/'session.json';session=json.loads(session_path.read_text())
    assert session.get('closed_utc'),'Final DB proof requires the owner-closed session.'
    transition_path=BASE/'da-analysis/da-transition-proof.json'
    assert sha(transition_path.read_bytes())==TRANSITION_SHA
    transition=json.loads(transition_path.read_text());assert transition['pass']
    images,files=load_inputs();db=images['DB']
    captures={name:native(args.capture,name) for name in ('db-entry','db-prepared','db-iteration-a','db-iteration-b','db-iteration-c','db-iteration-d')}
    prepared=captures['db-prepared'][0]
    # Only DA/DB file bytes are initial inputs. The full table generator stops
    # before its literal STA $01=$36; no bank-register response is invented.
    memory=bytearray(65536);known=bytearray(65536)
    for name in ('DA','DB'):
        first=files[name]['load_header'];end=files[name]['payload_end_exclusive']
        memory[first:end]=images[name][first:end];known[first:end]=bytes([1])*(end-first)
    assert memory[0xc05a:0xc05d]==bytes.fromhex('20 00 c4')
    assert memory[0xc4d4:0xc4d8]==bytes.fromhex('a9 36 85 01')
    phase_ram,phase_execution=run(memory,known,0xc05a,0xc4d4)
    assert all(known[0x8000:0xc000])
    scatter=scatter_oracle(memory);lookups=lookup_oracle(db)
    da_payload=images['DA'][0x4000:0x4800]
    bitplanes=dict(original_DA_bytes=len(da_payload),original_DA_unique_values=sorted(set(da_payload)),
                   original_DA_uses_low_pair_bits_only=all((value&0xaa)==0 for value in da_payload),
                   first_source_bytes=0x4000,first_source_uses_low_pair_bits_only=all((value&0xaa)==0 for value in memory[0x8000:0xc000]),
                   second_source_bytes=0x4000,second_source_uses_high_pair_bits_only=all((value&0x55)==0 for value in scatter[0x4000:0x8000]),
                   interpretation='Two one-bit masks in complementary multicolor pair bits; OR yields00 background,01 first layer,10 second layer,11 overlap.')
    assert all(bitplanes[key] for key in ('original_DA_uses_low_pair_bits_only','first_source_uses_low_pair_bits_only','second_source_uses_high_pair_bits_only'))
    prep_checks=[comparison(prepared,memory,0x8000,0xc000,'All16384 file-only mirrored/shifted DA-pattern bytes'),
                 comparison(prepared,scatter,0x4000,0x8000,'All16384 independently indexed transposed/scaled DA-pattern bytes'),
                 comparison(prepared,lookups,0x400,0x800,'All1024 row-pointer/motion lookup bytes')]
    assert all(c['exact'] for c in prep_checks)
    (output/'file-derived-phase-planes.bin').write_bytes(memory[0x8000:0xc000])
    (output/'file-derived-transposed-planes.bin').write_bytes(scatter[0x4000:0x8000])
    # Preserve the original prestate; source selection/setup runs to the actual
    # original JSR kernel entry, with its own stack. No return address is faked.
    before,before_state,before_cpu,before_record=captures['db-iteration-a']
    after,after_state,after_cpu,after_record=captures['db-iteration-b']
    assert before_cpu['pc']==after_cpu['pc']==0xc200
    prefix_ram,prefix_run=run(bytearray(before),bytearray([1])*65536,0xc200,0xc7c0,before_cpu,
                              before_record['port_latch'],before_record['port_ddr'])
    model,expected_events,source_rows=kernel_oracle(prefix_ram.data,prefix_run['final_cpu']['y'])
    suffix_ram,suffix_run=run(prefix_ram.data,prefix_ram.known,0xc7c0,0xc200,prefix_run['final_cpu'],
                              before_record['port_latch'],before_record['port_ddr'])
    assert suffix_ram.bitmap_stores==expected_events
    expected=suffix_ram.data
    event_path=output/'iteration-a-to-b-bitmap-stores.json';event_path.write_text(json.dumps(expected_events,indent=2)+'\n')
    interval_checks=[comparison(after,expected,first,end,label) for first,end,label in (
        (0xc000,0xcc00,'All3072 DB code bytes including96 self-modified source operands'),
        (0xe000,0x10000,'All8192 bitmap RAM bytes after literal iteration'),
        (0x28,0xe8,'All192 prepared source-pointer bytes'),
        (0x2c0,0x2c8,'All8 global phase bytes'),
        (0x2d0,0x2d1,'Literal steady iteration counter'))]
    model_check=comparison(after,model,0xe000,0x10000,'Independent indexed OR/scatter bitmap oracle versus native result')
    interval_checks.append(model_check)
    cpu_checks=[dict(register=key,expected=suffix_run['final_cpu'][key],actual=after_cpu[key],
                     exact=suffix_run['final_cpu'][key]==after_cpu[key]) for key in ('pc','a','x','y','sp','flags')]
    full_difference=comparison(after,expected,0,65536,'Unfiltered whole-RAM observation outside the exact domains remains visible')
    (output/'iteration-a-to-b-ram-only-expected.bin').write_bytes(expected)
    report=dict(script=record(Path(__file__)),helpers=[record(ROOT/'research/second-reality/inspect_ca.py'),record(ROOT/'research/second-reality/inspect_da.py')],
                py65_version=importlib.metadata.version('py65'),session=record(session_path),session_closed_utc=session['closed_utc'],
                transition_receipt=record(transition_path),files=files,captures=[captures[name][3] for name in captures],
                source_only_phase_preparation=phase_execution,prepared_checks=prep_checks,
                complementary_bitplane_contract=bitplanes,
                prep_scope='DA/DB file bytes only for executed prefix. Stop atC4D4 before LDA/STA CPU-port sequence; suffix scatter and row-lookup loops are independent host data oracles, not skipped hardware execution.',
                kernel=dict(first=0xc7c0,row_block_first=0xc7c2,row_block_bytes=11,unrolled_rows=96,
                            horizontal_iterations=32,x_step=8,duplicate_vertical_stores=2,total_bitmap_stores=6144,
                            layer1_range=[0x8000,0xc000],layer2_range=[0x4000,0x8000],combine='bitwise OR',
                            source_rows=source_rows,store_receipt=record(event_path),all_CPU_stores_equal_independent_oracle=True),
                native_prestate_iteration=dict(prefix_execution=prefix_run,suffix_execution=suffix_run,
                    nominal_cpu_cycles=prefix_run['nominal_cpu_cycles']+suffix_run['nominal_cpu_cycles'],
                    instructions=prefix_run['completed_instructions']+suffix_run['completed_instructions'],
                    native_elapsed_clocks=after_cpu['clock']-before_cpu['clock'],checks=interval_checks,cpu_checks=cpu_checks,
                    full_RAM_observation=full_difference,
                    scope='Original instruction replay conditional on native A pre-RAM/CPU/ports, split only at the original kernel call. No IRQ/hardware/ROM/unknown responses.'),
                native_intervals=[dict(first=first,last=last,clocks=captures[last][2]['clock']-captures[first][2]['clock'])
                    for first,last in zip(('db-iteration-a','db-iteration-b','db-iteration-c'),('db-iteration-b','db-iteration-c','db-iteration-d'))],
                pass_=all(c['exact'] for c in prep_checks+interval_checks+cpu_checks),
                limitations=['No independent pixel/VIC-frame or analog composition oracle.',
                             'Nominal CPU totals omit IRQ/music, VIC stalls and all hardware; logical updates are not display frames.',
                             'Every whole-RAM mismatch is retained, with no whole-machine equivalence claim.',
                             'No author-specific effect name, polygon geometry/fill, historical priority or whole-demo behavior claim.'])
    report['pass']=report.pop('pass_');target=output/'db-proof.json';target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(target.relative_to(ROOT)),sha256=sha(target.read_bytes()),pass_=report['pass'],
                          prep_exact=all(c['exact'] for c in prep_checks),bitmap_stores=len(expected_events),
                          CPU_exact=all(c['exact'] for c in cpu_checks),nominal_cpu_cycles=report['native_prestate_iteration']['nominal_cpu_cycles'],
                          native_clocks=after_cpu['clock']-before_cpu['clock'],full_RAM_mismatches=len(full_difference['differences'])),indent=2))
    assert report['pass'],'DB contract mismatch retained in receipt.'


if __name__=='__main__':main()
