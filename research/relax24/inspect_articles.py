#!/usr/bin/env python3
"""Bounded Relax24 consumer map and strict resource-decoder call boundary."""
import hashlib
import importlib.metadata
import json
from pathlib import Path

from py65.devices.mpu6502 import MPU
from py65.disassembler import Disassembler

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'build/research/relax24'
INNER_SHA='d86df447082e7ee3d7d55bf8bfaabdc9abe0ff09784746a28656ba78f43eb9cd'


def sha(data):return hashlib.sha256(data).hexdigest()
def record(path):
    data=Path(path).read_bytes()
    return dict(path=str(Path(path).resolve().relative_to(ROOT)),bytes=len(data),sha256=sha(data))
def checked(item):
    data=(ROOT/item['path']).read_bytes();assert len(data)==item['bytes'] and sha(data)==item['sha256'],item
    return data


class Boundary(Exception):pass
class KnownRam:
    def __init__(self,data,known):self.data,self.known=data,known;self.pc=0;self.writes=[]
    def __getitem__(self,address):
        if address in (0,1) or 0xd000<=address<0xe000:raise Boundary(('hardware-address read',self.pc,address))
        if not self.known[address]:raise Boundary(('unknown read',self.pc,address))
        return self.data[address]
    def __setitem__(self,address,value):
        if address in (0,1) or 0xd000<=address<0xe000:raise Boundary(('hardware-address write',self.pc,address,value))
        self.data[address]=value;self.known[address]=1;self.writes.append(dict(pc=self.pc,address=address,value=value))


def main():
    output=BASE/'article-analysis';output.mkdir(parents=True,exist_ok=True)
    proof_path=BASE/'decoder-analysis/inner-proof.json';assert sha(proof_path.read_bytes())==INNER_SHA
    proof=json.loads(proof_path.read_text());assert proof['pass'] and proof['original_CPU_validation']['all_output_bytes_exact']
    item=next(item for item in proof['artifacts'] if item['path'].endswith('/inner-decoded.ram'))
    original=checked(item);assert sha(original[0x801:0xffff])==proof['format_decode']['output_sha256']
    assert original[0x2000:0x200e]==bytes.fromhex('a5 ba 8d 01 25 8d 5e 25 20 00 25 4c 00 94')
    assert original[0x2500:0x2515]==bytes.fromhex('a2 08 a9 0f a8 20 ba ff a9 00 20 bd ff 20 c0 ff a2 0f 20 c9 ff')
    assert original[0x25a0:0x25a6]==bytes.fromhex('4d 2d 45 00 05 0d')
    resources=[]
    for call,end,condition in [(0x9417,0x8fbf,'Conditional path selected by02A6'),(0x942d,0x9f57,'Initialization'),
                               (0x9438,0xbce7,'Initialization'),(0x9536,0x9d2f,'Continuation'),(0x9572,0x8df6,'Continuation')]:
        assert original[call:call+3]==bytes.fromhex('20 1d 99')
        assert original[call-8:call]==bytes((0xa2,end&255,0xa0,end>>8,0x86,0xae,0x84,0xaf))
        header=original[end-5:end];count=header[1]+256*header[2];destination=header[3]+256*header[4]
        resources.append(dict(call=call,end_pointer=end,descriptor_first=end-5,descriptor=list(header),
            initial_bit_buffer=header[0],remaining_byte_counter=count,initial_destination_cursor=destination,
            inferred_input_span=[end-5-count,end-5],condition=condition,
            scope='Instruction-derived resource descriptor, not an article header or decoded output extent.'))
    assert original[0x9516:0x9519]==bytes.fromhex('4c d0 8e')
    assert original[0x8ecf:0x8ed3]==bytes.fromhex('d0 fb a2 00')
    assert original[0x8eec:0x8eef]==bytes.fromhex('4c 19 95')
    assert original[0x95b8:0x95bb]==bytes.fromhex('4c e0 8f') and original[0x8ff0:0x8ff3]==bytes.fromhex('4c 00 c0')
    assert original[0x8fe0:0x8ff3]==bytes.fromhex('a9 4a 8d 7c ae 8d 81 ae a9 1d 8d 7d ae 8d 82 ae 4c 00 c0')
    # Execute an actual pure callsite, not a synthetic RTS frame. Stop on
    # the first unavailable read; no value is supplied for that address.
    data=bytearray(65536);known=bytearray(65536);data[0x801:0xffff]=original[0x801:0xffff];known[0x801:0xffff]=bytes([1])*(0xffff-0x801)
    memory=KnownRam(data,known);cpu=MPU(memory=memory,pc=0x9425);cpu.p=cpu.UNUSED|cpu.INTERRUPT;cpu.sp=255
    steps=0;boundary=None
    while cpu.pc!=0x9430:
        assert steps<500000,('Instruction budget',cpu.pc)
        memory.pc=cpu.pc
        try:
            opcode=memory[cpu.pc];assert cpu.instruct[opcode].__name__!='inst_not_implemented',(cpu.pc,opcode)
            cpu.step();steps+=1
        except Boundary as error:boundary=list(error.args[0]);break
    state={hex(address):data[address] for address in range(0xce,0xf5) if known[address]}
    # Only source-established instruction intervals, never compressed data.
    dis=Disassembler(MPU(memory=list(original)));lines=[]
    for first,end in [(0x2000,0x200e),(0x2500,0x259b),(0x9400,0x9519),(0x9519,0x9539),
                      (0x956c,0x9575),(0x95b2,0x95bb),(0x8fe0,0x8ff3),(0x991d,0x9a28)]:
        pc=first
        while pc<end:
            length,text=dis.instruction_at(pc);assert text!='???',(pc,text)
            lines.append(f'{pc:04X} {original[pc:pc+length].hex(" "):9} {text}');pc+=length
        assert pc==end,(first,end,pc)
        lines.append('')
    listing=output/'consumer-instructions.txt';listing.write_text('\n'.join(lines)+'\n')
    report=dict(script=record(Path(__file__)),py65_version=importlib.metadata.version('py65'),inner_proof=record(proof_path),source=item,
        installer=dict(entry=0x2500,source=[0x25a8,0x2798],drive_destination=[0x500,0x6f0],bytes=496,
            command=original[0x25a0:0x25a6].hex(' '),first_ROM_call=0x2505,
            scope='Static M-W/M-E sender path only; no KERNAL, drive, IEC or file-load execution.'),
        resource_calls=resources,
        next_code_state_boundary=dict(source_JMPs=[0x95b8,0x8ff0],target=0xc000,pre_expansion_signature=original[0xc000:0xc010].hex(' '),
            scope='C000 interpretation requires the completed resource-expansion state; raw bytes are not promoted to an article consumer.'),
        strict_resource_call=dict(entry=0x9425,intended_return=0x9430,completed_instructions=steps,
            nominal_executed_cycles=cpu.processorCycles,boundary=boundary,format_state=state,
            output_candidate_writes=[event for event in memory.writes if event['pc']==0x99fc],
            preconditions=['Only the independently checked0801..FFFE output is initially known.',
                           'RAM visible except I/O, matching the excluded source request for port15; no IRQ delivery.',
                           'Decimal clear and SP=FF; the actual942D JSR constructs its own return frame.'],
            scope='Strict original CPU prefix only. Unknown, port and I/O reads/writes are never supplied or skipped.'),
        instruction_listing=record(listing),
        open_questions=['Completed991D resource expansion and post-expansionC000 consumer.',
                        'Actual side2 filename/request and five-byte-header interpretation.',
                        'Original article decoding and coding-review identification.'],
        scope='Source consumer checkpoints and strict resource-decoder boundary only. No article header semantics, decoded article, coding-review identity or native behavior claim.',pass_=True)
    report['pass']=report.pop('pass_');target=output/'consumer-proof.json';target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(target.relative_to(ROOT)),sha256=sha(target.read_bytes()),strict_boundary=boundary,
                         prefix_instructions=steps,resource_blocks=len(resources)),indent=2))


if __name__=='__main__':main()
