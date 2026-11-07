#!/usr/bin/env python3
"""Bind DB's EA/EB bridge and EC's generated two-source character renderer.

Native captures are passive inputs. File-known preparation stops before a bank
write; native-prestate drawing stops before a mapped-ROM read. No VIC,
IRQ, ROM, loader or unknown-memory response is supplied to the CPU checker.
"""
import argparse
from collections import Counter
import importlib.metadata
import json
from pathlib import Path

from py65.devices.mpu6502 import MPU
from inspect_ca import BASE, ROOT, KnownRam, comparison, native, ranges, record, sha
from inspect_da import load_inputs

EC = ('side1-entry20-EC.prg',0xc000,3231,'4a39c4a07db39e513af8ad0af2641a649d40fbb8224642808e52996f42523a82')
DA_PROOF = 'eb75376e089794a6d1468090274b8a27259e3550b91f3139566e95e87beffe2c'
DB_PROOF = '1db288eace0f8c241d9ee3578768bde2bca37fe34c50052fb7877a2a058642bf'


class EaRam(KnownRam):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.sample_stores=[]
    def __setitem__(self,address,value):
        super().__setitem__(address,value)
        if 0x9698<=self.pc<0x9c02 and 0xe000<=address<0xf800:
            self.sample_stores.append(dict(pc=self.pc,address=address,value=value))


def run(data,known,entry,stop,registers,port=0x36,ddr=0x2f,limit=2_000_000):
    ram=EaRam(data,known,port,ddr);cpu=MPU(memory=ram,pc=entry)
    for key in ('a','x','y','sp'):setattr(cpu,key,registers[key])
    cpu.p=registers['flags'];counts=Counter();steps=0
    while not (steps and cpu.pc==stop):
        assert steps<limit,('Instruction budget',entry,stop,cpu.pc)
        ram.pc=cpu.pc;opcode=ram[cpu.pc]
        assert cpu.instruct[opcode].__name__!='inst_not_implemented',(cpu.pc,opcode)
        counts[cpu.pc]+=1;cpu.step();steps+=1
    result=dict(entry=entry,stop_pc=cpu.pc,completed_instructions=steps,nominal_cpu_cycles=cpu.processorCycles,
                final_cpu=dict(pc=cpu.pc,a=cpu.a,x=cpu.x,y=cpu.y,sp=cpu.sp,flags=cpu.p),
                instruction_counts=dict(sorted(counts.items())),read_ranges=ranges(ram.reads),written_ranges=ranges(ram.writes),
                RAM_sha256=sha(data),known_mask_sha256=sha(known),hardware_or_unknown_accesses=0,
                scope='Known RAM only; CPU-port/hardware writes and mapped ROM/unknown reads rejected. No IRQ delivery.')
    return ram,result


def inputs():
    images,files=load_inputs();name,first,size,digest=EC
    path=BASE/'disk-map'/name;blob=path.read_bytes()
    assert len(blob)==size+2 and int.from_bytes(blob[:2],'little')==first and sha(blob)==digest
    memory=bytearray(65536);memory[first:first+size]=blob[2:];images['EC']=memory
    files['EC']=dict(**record(path),load_header=first,payload_bytes=size,payload_end_exclusive=first+size,
                     payload_sha256=sha(blob[2:]))
    return images,files


def texture_oracle(eb):
    """Independent indexed expansion of the authored run stream and row zero."""
    texture=bytearray(4096)
    values=[0xaa,0xa8,0xa0,0x80,0,2,0x0a,0x2a]
    for block,value in enumerate(values):texture[block*32:(block+1)*32]=bytes([value])*32
    source=0x7d00;target=256;runs=[]
    while eb[source]!=0x1c:
        value,count=eb[source:source+2]
        assert count<=128 and target+count<len(texture)
        texture[target:target+count+1]=bytes([value])*(count+1)
        runs.append(dict(source=source,value=value,count=count,first=target,end_inclusive=target+count))
        source+=2;target+=count
    assert len(runs)==111 and source==0x7dde and target==4095
    result=bytearray(65536)
    for row in range(16):
        original=texture[256*row:256*(row+1)];shifted=bytes(value>>1 for value in original)
        for repeat in range(2):
            first=0x2000+512*row+256*repeat;result[first:first+256]=original
            first+=0x2000;result[first:first+256]=shifted
    assert all(value&0x55==0 for value in result[0x2000:0x4000])
    assert all(value&0xaa==0 for value in result[0x4000:0x6000])
    return result,texture,runs


def masked_comparison(actual,expected,known,first,end,label):
    addresses=[a for a in range(first,end) if known[a]]
    differences=[dict(address=a,actual=actual[a],expected=expected[a]) for a in addresses if actual[a]!=expected[a]]
    return dict(label=label,first=first,end_exclusive=end,defined_bytes=len(addresses),
                undefined_bytes=end-first-len(addresses),undefined_ranges=ranges(a for a in range(first,end) if not known[a]),
                expected_defined_sha256=sha(bytes(expected[a] for a in addresses)),
                actual_defined_sha256=sha(bytes(actual[a] for a in addresses)),exact=not differences,differences=differences)


def screen_oracle():
    """C011..C07D and CC00/CC34's RAM writes, excluding all I/O writes."""
    result=bytearray(65536)
    for first in (0xb800,0xf800):result[first:first+0x400]=bytes([255])*0x400
    char=0
    for column in range(4,35):
        for row in range(8):result[0xb800+row*40+column]=char;char+=1
    for x in range(256):
        value=result[0xb800+x]
        for first in (0xb940,0xba80,0xf800,0xf940,0xfa80):result[first+x]=value
        value=result[0xb840+x]
        for first in (0xf840,0xb980,0xbac0,0xf980,0xfac0):result[first+x]=value
    for first in (0xa000,0xe000):result[first:first+0x1800]=bytes(0x1800)
    for first in (0xa7f8,0xaff8,0xb7f8,0xe7f8,0xeff8,0xf7f8):result[first:first+8]=bytes([255])*8
    return result


def sample_oracle(memory):
    """Independent 32x96 sampled OR/scatter from prepared source operands.

    This accepts the original prefix's affine-coordinate tables and operand
    bases. It does not independently derive motion or raster/field composition.
    """
    result=bytearray(memory);events=[];bases=[]
    for column in range(96):
        group=column//32
        first=0x969c+6*column+2*group;second=0x98e5+8*column+7*group
        assert memory[first]==0xbd and memory[first+3]==0x8d
        assert memory[second]==0xbd and memory[second+3]==0x09
        assert memory[second+5]==(0xad if column%32==31 else 0x99)
        base_a=int.from_bytes(memory[first+1:first+3],'little')
        base_b=int.from_bytes(memory[second+1:second+3],'little')
        destination=int.from_bytes(memory[second+6:second+8],'little')
        assert destination==0xe000+column*64
        bases.append(dict(column=column,first=base_a,second=base_b,destination=destination,second_pc=second,
                          stores=column%32!=31))
    for row in range(32):
        for column,base in enumerate(bases):
            group=column//32
            index_a=memory[0x40+32*group+row]
            index_b=memory[0xce80+32*group+row]
            first=(base['first']+index_a)&65535;second=(base['second']+index_b)&65535
            assert 0x2000<=first<0x4000 and 0x4000<=second<0x6000
            # The first pass patches every ORA immediate, including the unused
            # final column. Each patched AD absolute load then suppresses that
            # column's store; no mapped-ROM value is read or supplied here.
            result[base['second_pc']+4]=memory[first]
            if base['stores']:
                value=memory[first]|memory[second];target=base['destination']+2*row
                result[target]=value
                events.append(dict(pc=base['second_pc']+5,address=target,value=value,
                                   first_source=first,second_source=second))
    assert len(events)==2976
    return result,events,bases


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,default=BASE/'native-04')
    parser.add_argument('--output',type=Path,default=BASE/'ea-analysis')
    args=parser.parse_args();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    session_path=args.capture/'session.json';session=json.loads(session_path.read_text())
    assert session.get('closed_utc'),'Final EA/EC binding requires the owner-closed capture session.'
    dependencies=[]
    for path,digest in ((BASE/'da-analysis/da-transition-proof.json',DA_PROOF),(BASE/'db-analysis/db-proof.json',DB_PROOF)):
        assert sha(path.read_bytes())==digest and json.loads(path.read_text())['pass'];dependencies.append(record(path))
    images,files=inputs();ea,eb,ec=images['EA'],images['EB'],images['EC']
    assert images['DB'][0xc2cd:0xc2d5]==bytes.fromhex('a9 0f 8d d0 02 4c 00 2e')
    assert ea[0x6ee4:0x6ee7]==bytes.fromhex('4c 50 3f') and eb[0x7f71:0x7f74]==bytes.fromhex('4c 00 6c')
    assert ea[0x6ddb:0x6de7]==bytes.fromhex('a2 45 a0 43 a9 08 20 00 cf 20 60 3a')
    assert ea[0x6dca:0x6dcd]==bytes.fromhex('4c 00 c0')
    assert ec[0xc000:0xc011]==bytes.fromhex('a9 00 8d 11 d0 8d 20 d0 8d 21 d0 ad 00 0c 20 00 75')
    names=('restored-db','ea-entry','eb-bridge','ea-restored','ec-load-call','ec-load-return','eb-restored',
           'ec-entry','ec-prepared','ec-iteration-a','ec-half-a','ec-iteration-b','ec-iteration-c','ec-iteration-d','ec-visible-end')
    captures={name:native(args.capture,name) for name in names}
    previous=native(BASE/'native-03','db-iteration-d')
    checks=[comparison(captures['restored-db'][0],previous[0],0,65536,'Full RAM identity at the single approved native03 restore')]
    restore_cpu=[dict(register=key,actual=captures['restored-db'][2][key],expected=previous[2][key],
                      exact=captures['restored-db'][2][key]==previous[2][key]) for key in previous[2]]
    stages={name:captures[name][0] for name in names}
    for name,target in (('EA',0x2000),('EB',0x3000)):
        first=files[name]['load_header'];size=files[name]['payload_bytes'];expected=bytearray(65536)
        expected[target:target+size]=images[name][first:first+size]
        checks.append(comparison(stages['ea-entry'],expected,target,target+size,'All original '+name+' bytes at DB exit staging'))
    expected=bytearray(65536);expected[0x6000:0x7000]=stages['eb-bridge'][0x2000:0x3000]
    checks.append(comparison(stages['ea-restored'],expected,0x6000,0x7000,'Full4096-byte EA-region restoration, including23 stale plus256 loader bytes'))
    expected[0xcf00:0xd000]=stages['ea-restored'][0x2f00:0x3000]
    checks.append(comparison(stages['ec-load-call'],expected,0xcf00,0xd000,'Exact256-byte preserved loader restoration before EC call'))
    for name in ('ec-load-return','ec-entry'):
        checks.append(comparison(stages[name],ec,0xc000,0xcc9f,'Every3231 original EC payload byte at '+name))
    assert int.from_bytes(stages['ec-load-return'][0xcf3b:0xcf3d],'little')==0xcc9f
    assert (captures['ec-load-call'][2]['pc'],captures['ec-load-call'][2]['a'],captures['ec-load-call'][2]['x'],captures['ec-load-call'][2]['y'])==(0x6de1,8,69,67)
    expected[0x7000:0x8000]=stages['ec-load-return'][0x3000:0x4000]
    checks.append(comparison(stages['eb-restored'],expected,0x7000,0x8000,'Full4096-byte EB-region restoration, including120 non-file bytes'))
    checks.append(comparison(stages['eb-restored'],eb,0x7000,0x7f88,'Every3976 original EB payload byte restored for preparation'))
    expected_pcs=(0xc200,0x2e00,0x3f50,0x6c00,0x6de1,0x6de4,0x6de7,0xc000,0xca80,0xca88,0x9c02,0xca88,0xca88,0xca88,0xcabc)
    assert [captures[name][2]['pc'] for name in names]==list(expected_pcs)
    # The generator's arithmetic requires decimal mode clear. A/X/Y initial
    # values are overwritten before use; native entry SP supplies the JSR stack.
    registers=captures['ec-entry'][2];assert registers['flags']&8==0
    memory=bytearray(65536);known=bytearray(65536)
    for name in ('EB','EC'):
        first=files[name]['load_header'];end=files[name]['payload_end_exclusive']
        memory[first:end]=images[name][first:end];known[first:end]=bytes([1])*(end-first)
    prepared_ram,prep_run=run(memory,known,0xc00e,0xca14,registers)
    texture,logical_texture,runs=texture_oracle(eb)
    texture_checks=[comparison(memory,texture,0x2000,0x6000,'Independent run/duplicate/shift oracle against literal file-known CPU preparation'),
                    comparison(stages['ec-prepared'],texture,0x2000,0x6000,'All16384 independently expanded source-plane bytes versus native preparation')]
    # CC00 runs after the rejected bank write. These six literal opcode writes
    # are applied as a separate data oracle, never as skipped CPU execution.
    for address in (0x89e2,0x8ae9,0x8bf0,0x99e2,0x9ae9,0x9bf0):memory[address]=0xad;known[address]=1
    code_checks=[masked_comparison(stages['ec-prepared'],memory,known,first,end,'File-defined generated code/data at '+hex(first))
                 for first,end in ((0x8000,0x8c06),(0x9000,0x9c06))]
    screens=screen_oracle()
    screen_checks=[comparison(stages['ec-prepared'],screens,first,end,label) for first,end,label in (
        (0xb800,0xbc00,'All1024 screen bytes for bank8000'),(0xf800,0xfc00,'All1024 screen bytes for bankC000'),
        (0xa000,0xb800,'All6144 cleared first character-buffer bytes and six sprite pointers'),
        (0xe000,0xf800,'All6144 cleared second character-buffer bytes and six sprite pointers'))]
    checks+=texture_checks+code_checks+screen_checks
    (output/'file-derived-logical-texture.bin').write_bytes(logical_texture)
    (output/'file-derived-source-planes.bin').write_bytes(texture[0x2000:0x6000])
    (output/'file-derived-generated-code.bin').write_bytes(memory[0x8000:0xa000])
    (output/'file-derived-generated-code-known-mask.bin').write_bytes(known[0x8000:0xa000])
    before,before_state,before_cpu,before_record=captures['ec-iteration-a']
    after,after_state,after_cpu,after_record=captures['ec-half-a']
    prefix,prefix_run=run(bytearray(before),bytearray([1])*65536,0xca88,0x9698,before_cpu,before_record['port_latch'],before_record['port_ddr'])
    model,events,bases=sample_oracle(prefix.data)
    suffix,suffix_run=run(prefix.data,prefix.known,0x9698,0x99e2,prefix_run['final_cpu'],before_record['port_latch'],before_record['port_ddr'])
    assert suffix.sample_stores==[{key:event[key] for key in ('pc','address','value')} for event in events[:31]]
    # The original stores, independently re-indexed rather than replayed, must
    # match both the literal CPU result and its corresponding native endpoint.
    events_path=output/'half-a-sampled-stores.json';events_path.write_text(json.dumps(events,indent=2)+'\n')
    prefix_store_model=bytearray(before)
    for event in events[:31]:prefix_store_model[event['address']]=event['value']
    half_checks=[comparison(suffix.data,prefix_store_model,0xe000,0xf800,'Literal RAM-only CPU prefix versus first31 independently indexed OR stores'),
                 comparison(after,model,0xe000,0xf800,'All6144 second character-buffer bytes versus native half-draw'),
                 comparison(after,model,0x8000,0x9c06,'All generated code/operand bytes including the independently predicted final ORA immediates'),
                 comparison(after,prefix.data,0xc000,0xcc9f,'All3231 EC code/table bytes including motion self-modification'),
                 comparison(after,prefix.data,0x2c0,0x2c6,'All six motion/control bytes after native half-draw'),
                 comparison(after,prefix.data,0x40,0xa0,'All96 first-coordinate index lookup bytes'),
                 comparison(after,prefix.data,0xce80,0xcee0,'All96 second-coordinate index lookup bytes')]
    checks+=half_checks
    whole=comparison(after,model,0,65536,'Unfiltered whole-RAM observation against indexed-store model; registers/counters/IRQ state outside its scope remain visible')
    (output/'half-a-indexed-store-expected.bin').write_bytes(model)
    report=dict(script=record(Path(__file__)),helpers=[record(ROOT/'research/second-reality/inspect_ca.py'),record(ROOT/'research/second-reality/inspect_da.py')],
                py65_version=importlib.metadata.version('py65'),dependencies=dependencies,files=files,
                session=record(session_path),session_closed_utc=session['closed_utc'],captures=[captures[name][3] for name in names],
                previous_restore_capture=previous[3],restore_cpu_checks=restore_cpu,checks=checks,
                control_flow=dict(DB_exit=0xc2d2,staged_EA_entry=0x2e00,EA_copy_entry=0x3f50,restored_EA_entry=0x6c00,
                    EC_call=0x6de1,EC_return=0x6de4,EB_copy_call=0x6de4,EB_copy_return=0x6de7,EC_execution_entry=0xc000,
                    EC_prepared=0xca80,logical_pair_loop=0xca88,half_draw_bank_write=0x9c02),
                preparation=dict(file_known_execution=prep_run,source_files=['EB','EC'],conditional_decimal_mode_clear=True,
                    execution_stop='Before CA14 and the CA19 bank write; CC00/CC34 and screen initialization checked by separate host RAM oracles.',
                    texture=dict(logical_bytes=4096,rows=16,columns=256,runs=len(runs),run_stream=[0x7d00,0x7de0],
                        sentinel_address=0x7dde,semantics='Write count+1, advance count; adjacent runs overlap their shared endpoint.',
                        unique_values=sorted(set(logical_texture)),runs_detail=runs,
                        first_plane_range=[0x2000,0x4000],second_plane_range=[0x4000,0x6000],second_plane_operation='logical shift right one'),
                    generated_code_checks=code_checks,undefined_operands='Never synthesized; retained as unknown in file-known receipt/mask and checked only after the original runtime prefix defines them.'),
                half_draw=dict(prefix_execution=prefix_run,RAM_only_first_row_prefix=suffix_run,independent_oracle_scope='Conditional on the literal prefix-prepared source bases and coordinate index arrays.',
                    stores=len(events),store_receipt=record(events_path),source_bases=bases,
                    first31_ordered_CPU_sample_stores_equal_oracle=True,
                    ROM_boundary=dict(pc=0x99e2,original_instruction='LDA $E7C0',mapped_read='KERNAL ROM',
                        other_dead_reads=[0x9ae9,0x9bf0],continuous_half_draw_CPU_proof=False,
                        reason='Column31 stores are changed to absolute LDA; their A/N/Z results are overwritten before use. No ROM response is supplied or CPU instruction skipped.'),
                    bounded_prefix_nominal_CPU_cycles=prefix_run['nominal_cpu_cycles']+suffix_run['nominal_cpu_cycles'],
                    observed_native_elapsed_clocks=after_cpu['clock']-before_cpu['clock'],whole_RAM_observation=whole),
                limitations=['No hardware/ROM/IRQ response or loader emulation is used in either CPU check.',
                    'A half draw and a paired logical iteration are not coherent VIC frames or display FPS measurements.',
                    'Strict CPU drawing stops99E2 before its mapped KERNAL read. No continuous full-half CPU/native register comparison is claimed.',
                    'The full2976-store indexed oracle accepts prepared affine operands and coordinate tables; it is not an independent full motion or pixel/field oracle.',
                    'Texture-coordinate transformation is established; no polygon primitive or author-specific effect name is assigned.',
                    'Full-page bridge restores retain23 stale EA-tail bytes,256 saved loader bytes and120 stale EB-tail bytes; none is zero padding.'])
    report['pass']=all(check['exact'] for check in checks+restore_cpu)
    target=output/'ea-proof.json';target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(target.relative_to(ROOT)),sha256=sha(target.read_bytes()),pass_=report['pass'],
                          checks=len(checks),half_draw_stores=len(events),whole_RAM_differences=len(whole['differences'])),indent=2))
    assert report['pass'],'Mismatch retained in EA/EC receipt.'


if __name__=='__main__':main()
