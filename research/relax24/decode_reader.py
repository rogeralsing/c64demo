#!/usr/bin/env python3
"""Known-memory, high-level Relax24 backward bit/LZ decoder.

This models the byte format. Port/border wrappers and the hardware exit are
explicitly outside the model; it is never called complete CPU execution.
"""
from collections import Counter
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'build/research/relax24'
ARCHIVE_SHA='0c68892c3a73cdeda0854eaa28db205672a9b02ed3f04ce185dbda72ad656fac'
READER_SHA='6879fffe4f8b4ceeb87730a5804e0976be725d897066f002f401f4ba32d5d226'


def sha(data):return hashlib.sha256(data).hexdigest()
def record(path):
    data=Path(path).read_bytes()
    return dict(path=str(Path(path).resolve().relative_to(ROOT)),bytes=len(data),sha256=sha(data))
def checked(item):
    data=(ROOT/item['path']).read_bytes();assert len(data)==item['bytes'] and sha(data)==item['sha256'],item
    return data
def ranges(addresses):
    result=[]
    for address in sorted(set(addresses)):
        if result and result[-1][1]==address:result[-1][1]+=1
        else:result.append([address,address+1])
    return result


class EndOfStream(Exception):pass
class KnownMemory:
    def __init__(self,data,known):
        self.data,self.known=data,known;self.reads=Counter();self.output_addresses=set()
        self.back_reference_provenance=Counter()
    def read(self,address,purpose):
        address&=65535
        assert self.known[address],('Unknown read',address,purpose)
        self.reads[address]+=1
        if purpose=='back-reference':
            self.back_reference_provenance['prior_output' if address in self.output_addresses else 'established_nonoutput']+=1
        return self.data[address]
    def state(self,address,value):self.data[address]=value&255;self.known[address]=1
    def word(self,address):return self.read(address,'state')+256*self.read(address+1,'state')
    def setword(self,address,value):self.state(address,value);self.state(address+1,value>>8)


class Decoder:
    def __init__(self,memory):
        self.memory=memory;self.events=[];self.refills=[];self.blocks=[];self.bits=0
    def bits_value(self,count):
        assert 0<=count<=16,count
        result=0
        for _ in range(count):
            remaining=self.memory.read(0x3d4,'remaining bits')
            if not remaining:
                pointer=(self.memory.word(0x3e8)-1)&65535
                self.memory.setword(0x3e8,pointer)
                value=self.memory.read(pointer,'compressed byte')
                self.memory.state(0x78a,value);remaining=8;self.refills.append(dict(address=pointer,value=value))
            buffer=self.memory.read(0x78a,'bit buffer');result=(result<<1)|(buffer>>7)
            self.memory.state(0x78a,buffer<<1);self.memory.state(0x3d4,remaining-1);self.bits+=1
        return result
    def length(self,match):
        selector=31 if match else 255
        for _ in range(256):
            selector=(selector+1)&255
            if self.bits_value(1):break
        else:raise AssertionError('Unbounded length prefix')
        if selector&16:raise EndOfStream(dict(stage='match' if match else 'literal',selector=selector))
        width=self.memory.read(0x723+selector,'length bit width')
        value=self.bits_value(width)
        return (value+self.memory.read(0x733+selector,'length base'))&255
    def put(self,value):
        destination=self.memory.word(0x40e)
        assert destination not in self.memory.output_addresses,('Repeated output store',destination)
        self.memory.state(destination,value);self.memory.output_addresses.add(destination)
        self.events.append(dict(address=destination,value=value))
        self.memory.setword(0x40e,(destination-1)&65535)
        assert len(self.events)<=65536
    def offset(self,length_byte):
        minus_one=(length_byte-1)&255
        if minus_one==0:return self.bits_value(4),None
        index=self.bits_value(2) if minus_one<2 else 4+self.bits_value(3)
        for _ in range(2):
            width=self.memory.read(0x763+index,'offset bit width')
            value=self.bits_value(width)
            base=self.memory.read(0x770+index,'offset low base')+256*self.memory.read(0x77d+index,'offset high base')
            value=(value+base)&65535
            if index>=4 and value==0:index=12
            else:return value,index
        raise AssertionError('Repeated offset escape')
    def decode(self):
        for block_index in range(65536):
            block=dict(index=block_index,output_first_event=len(self.events),input_pointer=self.memory.word(0x3e8))
            self.blocks.append(block)
            try:
                literal=self.length(False);block['literal_count']=literal
                for _ in range(literal):self.put(self.bits_value(8))
                match=self.length(True);offset,index=self.offset(match)
                block.update(match_length_byte=match,offset=offset,offset_class=index)
                minus_one=(match-1)&255;source=(self.memory.word(0x40e)+offset-minus_one)&65535
                y=(minus_one+1)&255;copies=0
                while True:
                    self.put(self.memory.read((source+y)&65535,'back-reference'));copies+=1
                    y=(y-1)&255
                    if not y:break
                block['match_stores']=copies
            except EndOfStream as end:
                block['end_marker']=end.args[0];self.finish_block(block);return
            self.finish_block(block)
        raise AssertionError('Block budget')
    def finish_block(self,block):
        block.update(output_end_event=len(self.events),input_end=self.memory.word(0x3e8),
                     remaining_end=self.memory.read(0x3d4,'remaining bits'),
                     buffer_end=self.memory.read(0x78a,'bit buffer'),destination_end=self.memory.word(0x40e))


def initial_state():
    archive_path=BASE/'archive-proof.json';reader_path=BASE/'reader-analysis/reader-proof.json'
    assert sha(archive_path.read_bytes())==ARCHIVE_SHA and sha(reader_path.read_bytes())==READER_SHA
    archive=json.loads(archive_path.read_text());reader=json.loads(reader_path.read_text())
    assert archive['pass'] and reader['pass'];prg=checked(archive['lynx']['extracted'])
    data=bytearray(65536);known=bytearray(65536)
    data[0x760:0x8149]=prg[2:];known[0x760:0x8149]=bytes([1])*len(prg[2:])
    for first,end,target in ((0x7f52,0x8052,0x340),(0x8048,0x8148,0x723)):
        assert all(known[first:end]);data[target:target+end-first]=data[first:end];known[target:target+end-first]=bytes([1])*(end-first)
    return data,known,archive,reader


class CpuMemory:
    def __init__(self,data,known):
        self.data,self.known=data,known;self.pc=0;self.events=[];self.refills=[]
        self.reads=Counter();self.writes=Counter();self.backrefs=Counter();self.output_addresses=set()
    def __getitem__(self,address):
        assert address not in (0,1) and not 0xd000<=address<0xe000,('Hardware address read',self.pc,address)
        assert self.known[address],('Unknown CPU read',self.pc,address)
        self.reads[address]+=1
        if self.pc==0x3bf and address>=0x801:
            self.backrefs['prior_output' if address in self.output_addresses else 'established_nonoutput']+=1
        if self.pc==0x3e7 and address>=0x78b:self.refills.append(dict(address=address,value=self.data[address]))
        return self.data[address]
    def __setitem__(self,address,value):
        assert address not in (0,1) and not 0xd000<=address<0xe000,('Hardware address write',self.pc,address)
        self.data[address]=value;self.known[address]=1;self.writes[address]+=1
        if self.pc==0x40d:
            self.events.append(dict(address=address,value=value));self.output_addresses.add(address)


def validate_original_fragments(decoder):
    from py65.devices.mpu6502 import MPU
    data,known,_,_=initial_state();memory=CpuMemory(data,known);cpu=MPU(memory=memory,pc=0x352)
    cpu.a=cpu.x=cpu.y=0;cpu.sp=255;cpu.p=cpu.UNUSED|cpu.INTERRUPT
    steps=0;counts=Counter();fragments=[]
    for index,block in enumerate(decoder.blocks):
        assert cpu.pc==0x352
        first_steps=steps;first_event=len(memory.events)
        while cpu.pc not in (0x349,0x3fe):
            assert steps<10_000_000,('Instruction budget',cpu.pc)
            assert 0x352<=cpu.pc<0x3fe or 0x40d<=cpu.pc<0x436,('Unexpected execution address',cpu.pc)
            memory.pc=cpu.pc;opcode=memory[cpu.pc]
            assert cpu.instruct[opcode].__name__!='inst_not_implemented',(cpu.pc,opcode)
            counts[cpu.pc]+=1;cpu.step();steps+=1
        assert memory.events[first_event:]==decoder.events[block['output_first_event']:block['output_end_event']],index
        state=dict(input_end=data[0x3e8]+256*data[0x3e9],remaining_end=data[0x3d4],
                   buffer_end=data[0x78a],destination_end=data[0x40e]+256*data[0x40f])
        assert all(state[key]==block[key] for key in state),(index,state,block)
        fragments.append(dict(index=index,entry=0x352,exit=cpu.pc,completed_instructions=steps-first_steps,
                              output_stores=len(memory.events)-first_event,format_state=state))
        if cpu.pc==0x3fe:
            assert index==len(decoder.blocks)-1 and 'end_marker' in block;break
        assert cpu.y==0 and cpu.sp==255,(index,cpu.y,cpu.sp)
        # This is the NEXT isolated fragment invocation, not an executed
        # branch over the port/border wrapper. Only PC is selected by the
        # harness; no RAM, output, I/O or ROM byte is supplied here.
        cpu.pc=0x352
    assert memory.events==decoder.events and memory.refills==decoder.refills
    assert memory.backrefs==decoder.memory.back_reference_provenance
    differences=[dict(address=a,format_model=decoder.memory.data[a],CPU=data[a])
                 for a in range(65536) if decoder.memory.data[a]!=data[a]]
    return data,dict(py65_version=importlib.metadata.version('py65'),fragment_count=len(fragments),
        completed_instructions=steps,nominal_executed_CPU_cycles=cpu.processorCycles,
        entry=0x352,final_stop=cpu.pc,all_output_events_exact=True,all_refills_exact=True,
        all_per_fragment_bit_destination_states_exact=True,output_stores=len(memory.events),
        refills=len(memory.refills),back_reference_provenance=dict(memory.backrefs),
        read_ranges=ranges(memory.reads),written_ranges=ranges(memory.writes),instruction_counts=dict(sorted(counts.items())),
        full_RAM_model_vs_CPU_differences=differences,fragments=fragments,
        preconditions=['File-established literal wrapper/table copies, with unknown RAM retained as unknown.',
                       'RAM visibility throughout the isolated block; no interrupts or hardware/ROM delivery.',
                       'First fragment Y=0, decimal clear, SP=FF; incoming A/X/carry are overwritten before format use.',
                       'Each completed fragment returns Y=0/SP=FF. The next invocation selects0352 explicitly.'],
        omitted_instructions_per_transition=[0x349,0x34b,0x34d,0x350],
        scope='Separately invoked original pure decoder fragments, not contiguous bootstrap execution. Port/border instructions and hardware exit are never executed or mocked. Format and CPU RAM differences outside the decoded range remain recorded.')


def outer_main():
    output=BASE/'decoder-analysis';output.mkdir(parents=True,exist_ok=True)
    data,known,archive,reader=initial_state();memory=KnownMemory(data,known);decoder=Decoder(memory)
    decoder.decode();addresses=[event['address'] for event in decoder.events]
    first,end=min(addresses),max(addresses)+1
    assert addresses==list(range(end-1,first-1,-1))
    payload=bytes(data[first:end])
    cpu_data,cpu=validate_original_fragments(decoder)
    assert cpu_data[first:end]==payload
    fragment_path=output/'CPU-fragments.json';fragment_path.write_text(json.dumps(cpu.pop('fragments'),indent=2)+'\n')
    (output/'CPU-fragment-final.ram').write_bytes(cpu_data)
    for name,blob in [('decoded-reader.ram',data),('decoded-known-mask.bin',known),
                      ('decoded-output.prg',first.to_bytes(2,'little')+payload)]:
        (output/name).write_bytes(blob)
    for name,value in [('output-events.json',decoder.events),('blocks.json',decoder.blocks),('refills.json',decoder.refills)]:
        (output/name).write_text(json.dumps(value,indent=2)+'\n')
    report=dict(script=record(Path(__file__)),archive_proof=record(BASE/'archive-proof.json'),
        static_reader_proof=record(BASE/'reader-analysis/reader-proof.json'),source=archive['lynx']['extracted'],
        high_level_decode=dict(output_first=first,output_end_exclusive=end,output_bytes=len(payload),output_sha256=sha(payload),
            output_stores=len(decoder.events),unique_reverse_consecutive_stores=True,blocks=len(decoder.blocks),
            input_bits=decoder.bits,refills=len(decoder.refills),input_read_ranges=ranges(item['address'] for item in decoder.refills),
            final_input_pointer=memory.word(0x3e8),final_remaining_bits=memory.read(0x3d4,'remaining'),
            final_output_pointer=memory.word(0x40e),end_marker=decoder.blocks[-1]['end_marker'],
            zero_match_length_blocks=[block['index'] for block in decoder.blocks if block.get('match_length_byte')==0],
            back_reference_provenance=dict(memory.back_reference_provenance)),
        original_CPU_fragment_validation=cpu,CPU_fragment_receipt=record(fragment_path),
        omitted_hardware=dict(per_block=[0x349,0x352],exit=[0x3fe,0x40d],
            scope='Explicit format abstraction only. No omitted instruction is represented as executed; startup and hardware behavior are not modeled.'),
        artifacts=[record(output/name) for name in ('decoded-reader.ram','decoded-known-mask.bin','decoded-output.prg','output-events.json','blocks.json','refills.json','CPU-fragment-final.ram')],
        scope='High-level known-memory format decode independently matched by original pure CPU fragments. No contiguous bootstrap, hardware response, native or article-format claim.',pass_=True)
    report['pass']=report.pop('pass_');target=output/'decoder-proof.json';target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(target.relative_to(ROOT)),sha256=sha(target.read_bytes()),
        CPU_instructions=cpu['completed_instructions'],**report['high_level_decode']),indent=2))


def inner_initial_state():
    path=BASE/'decoder-analysis/decoder-proof.json';proof=json.loads(path.read_text());assert proof['pass']
    cpu=proof['original_CPU_fragment_validation']
    assert cpu['all_output_events_exact'] and cpu['all_refills_exact'] and cpu['all_per_fragment_bit_destination_states_exact']
    producer=Path(__file__)
    if sha(producer.read_bytes())!=proof['script']['sha256']:producer=BASE/'decoder-analysis/outer-producer.py'
    assert sha(producer.read_bytes())==proof['script']['sha256'],'Outer producer source identity unavailable'
    item=next(item for item in proof['artifacts'] if item['path'].endswith('/decoded-reader.ram'))
    original=checked(item);stage=proof['high_level_decode'];first,end=stage['output_first'],stage['output_end_exclusive']
    assert (first,end)==(0x801,0xa0e0) and sha(original[first:end])==stage['output_sha256']
    data=bytearray(65536);known=bytearray(65536);data[first:end]=original[first:end];known[first:end]=bytes([1])*(end-first)
    assert data[0x801:0x814]==bytes.fromhex('a2 00 78 a9 34 85 01 bd 14 08 9d e8 00 e8 d0 f7 4c 00 01')
    data[0xe8:0x1e8]=data[0x814:0x914];known[0xe8:0x1e8]=bytes([1])*256
    return data,known,proof,record(path),record(producer)


class ByteRLE:
    def __init__(self,memory):self.memory=memory;self.events=[];self.reads=[];self.records=[];self.last_source_low=0
    def get(self):
        old=self.memory.word(0xfd);self.last_source_low=old&255;pointer=(old-1)&65535
        self.memory.setword(0xfd,pointer);value=self.memory.read(pointer,'inner compressed byte')
        self.reads.append(dict(address=pointer,value=value));return value
    def put(self,value):
        pointer=(self.memory.word(0xf1)-1)&65535;self.memory.setword(0xf1,pointer)
        assert pointer not in self.memory.output_addresses,('Repeated inner output',pointer)
        self.memory.state(pointer,value);self.memory.output_addresses.add(pointer)
        self.events.append(dict(address=pointer,value=value));assert len(self.events)<=65536
    def repeat(self,value,count):
        for _ in range(count or 256):self.put(value)
    def packed(self):
        packed=self.get();value=self.memory.read(0x1a2+(packed>>3),'RLE dictionary')
        assert value,'Original BNE would fall through; preserve before generalizing'
        self.repeat(value,(packed&7)+3)
    def decode(self):
        markers=bytes(self.memory.read(0x188+i,'marker table') for i in range(13));assert len(set(markers))==13
        for index in range(65536):
            value=self.get();self.memory.state(0x350+self.last_source_low,value)
            item=dict(index=index,tag=value,output_first_event=len(self.events));self.records.append(item)
            if value not in markers:self.put(value);item['kind']='literal'
            else:
                marker=markers.index(value);displacement=self.memory.read(0x195+marker,'marker dispatch')
                self.memory.state(0x126,displacement);target=0x127+displacement;item['dispatch']=target
                if target==0x130:
                    value=self.get();item['kind']='escape'
                    if not value:item['kind']='end';item['output_end_event']=len(self.events);return
                    self.put(value)
                elif target==0x13f:
                    count,value=self.get(),self.get();item['kind']='repeat'
                    if value:self.repeat(value,count)
                    else:item['kind']='repeat-zero-fallthrough-to-packed';self.packed()
                elif target==0x148:item['kind']='packed-dictionary';self.packed()
                elif target==0x15c:
                    count,delta,value=self.get(),self.get(),self.get();self.memory.state(2,delta);item['kind']='subtracting-run'
                    for i in range(count or 256):self.put((value-i*delta)&255)
                elif target==0x173:item['kind']='counted-zeros';self.repeat(0,self.get())
                elif target in (0x17b,0x17c,0x17d,0x17e):
                    item['kind']='short-zeros';self.repeat(0,2+0x17e-target)
                elif target in (0x182,0x183):
                    value=self.memory.read(0x1b9+marker,'short-run constant');assert value
                    item['kind']='short-constant';self.repeat(value,3 if target==0x182 else 2)
                else:raise AssertionError(('Unknown marker target',target))
            item['output_end_event']=len(self.events)
        raise AssertionError('Inner record budget')


class InnerCpuMemory(CpuMemory):
    def __getitem__(self,address):
        assert address not in (0,1),('CPU port read',self.pc,address)
        assert self.known[address],('Unknown inner CPU read',self.pc,address)
        self.reads[address]+=1
        if self.pc==0xfc and address>=0x7f2:self.refills.append(dict(address=address,value=self.data[address]))
        return self.data[address]
    def __setitem__(self,address,value):
        assert address not in (0,1),('CPU port write',self.pc,address)
        self.data[address]=value;self.known[address]=1;self.writes[address]+=1
        if self.pc==0xf0:self.events.append(dict(address=address,value=value));self.output_addresses.add(address)


def inner_main():
    from py65.devices.mpu6502 import MPU
    output=BASE/'decoder-analysis';data,known,outer,outer_record,producer=inner_initial_state()
    source_continuation=bytes(data[0x9fe0:0xa0e0]);data[0x7f2:0x8f2]=source_continuation;known[0x7f2:0x8f2]=bytes([1])*256
    memory=KnownMemory(data,known);decoder=ByteRLE(memory);decoder.decode()
    addresses=[event['address'] for event in decoder.events];first,end=min(addresses),max(addresses)+1
    assert addresses==list(range(end-1,first-1,-1));payload=bytes(data[first:end])
    cpu_data,cpu_known,_,_,_=inner_initial_state();machine=InnerCpuMemory(cpu_data,cpu_known)
    cpu=MPU(memory=machine,pc=0x100);cpu.x=0;cpu.p=cpu.UNUSED|cpu.INTERRUPT;steps=0;counts=Counter();continuation_exact=False
    while cpu.pc!=0x137:
        if cpu.pc==0x109:
            continuation_exact=cpu_data[0x7f2:0x8f2]==source_continuation
            assert continuation_exact
        assert steps<10_000_000 and 0xe8<=cpu.pc<0x188,('Inner CPU budget/address',cpu.pc)
        machine.pc=cpu.pc;op=machine[cpu.pc];assert cpu.instruct[op].__name__!='inst_not_implemented',(cpu.pc,op)
        counts[cpu.pc]+=1;cpu.step();steps+=1
    assert machine.events==decoder.events and machine.refills==decoder.reads
    assert cpu_data[first:end]==payload and continuation_exact
    assert cpu_data[0xfd:0xff]==data[0xfd:0xff] and cpu_data[0xf1:0xf3]==data[0xf1:0xf3]
    differences=[dict(address=a,format_model=data[a],CPU=cpu_data[a],format_model_known=bool(known[a]),CPU_known=bool(cpu_known[a]))
                 for a in range(65536) if data[a]!=cpu_data[a]]
    for name,blob in [('inner-decoded.ram',data),('inner-known-mask.bin',known),
                      ('inner-CPU-final.ram',cpu_data),('inner-output.prg',first.to_bytes(2,'little')+payload)]:
        (output/name).write_bytes(blob)
    for name,value in [('inner-output-events.json',decoder.events),('inner-read-events.json',decoder.reads),('inner-records.json',decoder.records)]:
        (output/name).write_text(json.dumps(value,indent=2)+'\n')
    report=dict(script=record(Path(__file__)),outer_proof=outer_record,outer_producer_source=producer,
        source_output_sha256=outer['high_level_decode']['output_sha256'],
        format_decode=dict(output_first=first,output_end_exclusive=end,output_bytes=len(payload),output_sha256=sha(payload),
            output_stores=len(decoder.events),input_bytes=len(decoder.reads),input_ranges=ranges(item['address'] for item in decoder.reads),
            record_kinds=dict(Counter(item['kind'] for item in decoder.records)),end_marker=decoder.records[-1],
            final_source=memory.word(0xfd),final_destination=memory.word(0xf1)),
        original_CPU_validation=dict(entry=0x100,stop=0x137,completed_instructions=steps,nominal_cycles=cpu.processorCycles,
            all_input_events_exact=True,all_output_events_exact=True,all_output_bytes_exact=True,literal_continuation_copy_exact=True,
            instruction_counts=dict(sorted(counts.items())),read_ranges=ranges(machine.reads),written_ranges=ranges(machine.writes),
            full_RAM_model_vs_CPU_differences=differences,py65_version=importlib.metadata.version('py65'),
            preconditions=['Verified outer output only; all other RAM remains unknown until written.',
                           'File-established0814..0913 relocation to00E8..01E7; X=0 from the original copy loop.',
                           'RAM visible under I/O/ROM as requested by excluded port34 setup; no IRQ or hardware response.',
                           'Decimal clear; original0109DEX/010ATXS establishes SP=FF before subroutine use.']),
        hardware_boundaries=dict(header_port_write=0x806,exit_port_write=0x139,static_handoff=0x2000,
            scope='These port instructions are not executed or mocked. Original CPU runs continuously only inside the declared pure inner fragment.'),
        artifacts=[record(output/name) for name in ('inner-decoded.ram','inner-known-mask.bin','inner-CPU-final.ram','inner-output.prg',
                                                   'inner-output-events.json','inner-read-events.json','inner-records.json')],
        scope='Known-memory byte/RLE format and continuous original pure inner CPU fragment agree. No full bootstrap/native/article-consumer proof.',pass_=True)
    report['pass']=report.pop('pass_');path=output/'inner-proof.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(path.relative_to(ROOT)),sha256=sha(path.read_bytes()),CPU_instructions=steps,**report['format_decode']),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outer',action='store_true',help='Rebuild and validate the outer bit/LZ stage; otherwise validate inner byte/RLE using its saved proven output.')
    args=parser.parse_args()
    outer_main() if args.outer else inner_main()
