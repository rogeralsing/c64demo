#!/usr/bin/env python3
"""Checkpoint source-derived Relax24 resource format; no full decode yet.

This records the actual $991D format and its dead-value dependency boundary.
It performs no CPU, native, hardware or full-resource execution.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'build/research/relax24'
CONSUMER_SHA='e41c974f734065a2fec5d8162f464bb8a6ce0c28154d85f901e4f41129b4ce22'


def sha(data):return hashlib.sha256(data).hexdigest()
def record(path):
    data=Path(path).read_bytes()
    return dict(path=str(Path(path).resolve().relative_to(ROOT)),bytes=len(data),sha256=sha(data))
def checked(item):
    data=(ROOT/item['path']).read_bytes();assert len(data)==item['bytes'] and sha(data)==item['sha256'],item
    return data
def initial_bits(buffer):
    # Its highest one is a sentinel, not a returned payload bit.
    return [(buffer>>bit)&1 for bit in range(max(0,buffer.bit_length()-1))]
def literal_prefix(bits):
    low=high=0;position=0
    while position<len(bits):
        total=2*low+bits[position];position+=1;low=total&255;carry=total>>8
        if low==0 and carry==0:return 0,position
        high=(2*high+carry)&255
        assert position<len(bits),'Checkpoint prefix needs a refill; no byte was invented'
        continuation=bits[position];position+=1
        if not continuation:return high*256+low,position
    raise AssertionError('Incomplete checkpoint prefix')


def main():
    output=BASE/'resource-analysis';output.mkdir(parents=True,exist_ok=True)
    consumer_path=BASE/'article-analysis/consumer-proof.json'
    assert sha(consumer_path.read_bytes())==CONSUMER_SHA
    consumer=json.loads(consumer_path.read_text());assert consumer['pass']
    source=checked(consumer['source'])
    assert source[0x99f2:0x99fe]==bytes.fromhex('b1 d1 a6 ce d0 03 20 d8 00 88 91 d6')
    assert source[0x9900:0x990c]==bytes.fromhex('a5 e1 d0 02 c6 e2 c6 e1 ad 00 00 60')
    packed=source[0x990c:0x991d]
    widths=[((packed[index//2]>>3) if index%2==0 else packed[index//2])&7 for index in range(24)]
    buckets=[]
    for bucket in range(3):
        cumulative=offset=0;entries=[]
        for selector in range(8):
            cumulative+=widths[8*bucket+selector]
            entries.append(dict(selector=selector,total_payload_bits=cumulative,gap_offset=offset,
                                maximum_gap=offset+(1<<cumulative)-1))
            offset+=1<<cumulative
        buckets.append(dict(bucket=bucket,widths=widths[8*bucket:8*bucket+8],entries=entries))
    assert [b['entries'][-1]['maximum_gap'] for b in buckets]==[1143,11247,21999]
    first=next(item for item in consumer['resource_calls'] if item['end_pointer']==0x9f57)
    bits=initial_bits(first['initial_bit_buffer']);length,used=literal_prefix(bits)
    frozen=consumer['strict_resource_call'];state=frozen['format_state']
    assert length==state['0xcf']==4 and state['0xce']==0
    assert frozen['boundary']==['unknown read',0x99f2,0x223]
    report=dict(script=record(Path(__file__)),consumer_proof=record(consumer_path),source=consumer['source'],
        implemented_scope='Source-format checkpoint and arithmetic table derivation only. A complete resource decoder is not yet implemented or validated.',
        resource_descriptors=consumer['resource_calls'],
        bit_reader=dict(entry=0x9a0b,order='LSB first',buffer=0xd3,
            rule='Shift buffer right. If nonzero, return old low bit. Otherwise discard sentinel; if remaining counter is zero, return from991D. Else decrement counter, read one descending byte, set buffer80|(byte>>1), return byte&1.',
            raw_reader=0xd8,raw_pointer=[0xe1,0xe2],remaining_counter=[0xd4,0xd5],
            terminator='Counter exhaustion at a required refill, not an additional encoded EOF marker.'),
        literal_length=dict(low_byte=0xcf,high_byte=0xd0,
            rule='Start low/high0. Append payload bits through the actual byte ROL rule; first zero skips literals. Interleaved control1 continues, control0 ends. Retain low-byte-zero/carry and16-bit wrap edges rather than assuming generic gamma.',
            counter_update='On the valid no-underflow domain, subtract literal length from remaining input before raw literal bytes are copied.'),
        match_length=dict(rule='Append a data bit to n. Stop if n=0 or n>=128; otherwise read continuation1/0. Length=(n+2)&255. Bucket starts0 if n=0 else1, then increments if length&FC is nonzero.',
            normal_classes={'2':0,'3':1,'4..255':2},wrapped_classes={'0':'bucket1; writes no match bytes','1':'bucket1'},
            gap_selector='3 additional bits select within the length bucket.'),
        gap_tables=buckets,
        match_copy=dict(rule='For cursorP, lengthL and decoded gapg: destination[P-L,P), source[P+g,P+g+L); ordinary backward distance=L+g, not g+1.',
            validation_requirement='Preserve16-bit addressing and mutable memory; require every meaningful source byte to be established. Stop on an actually used unknown.'),
        dead_literal_read=dict(instruction=0x99f2,mode_condition='CE=0',
            overwritten_state=['A from the unavailable LDA is replaced by the00D8 reader.',
                               'N/Z from that LDA are replaced by LDX CE before its branch.',
                               'C/V are unaffected by LDA or LDX; no value-dependent addressing follows.'],
            limitation='Only the loaded value and N/Z are dead. The original physical read and its timing still exist. A format abstraction may omit that dependency, but no invented byte may be fed to CPU execution and no continuous CPU pass is claimed.'),
        frozen_prefix_anchor=dict(initial_buffer=first['initial_bit_buffer'],usable_LSB_bits=bits,literal_length=length,bits_consumed=used,
            completed_original_instructions=frozen['completed_instructions'],boundary=frozen['boundary'],
            scope='Arithmetic prefix matches the already frozen original235-instruction result; no new CPU run.'),
        resource_outputs_recovered=0,
        next_action='Implement the functional parser on known block8000..8DF0 with descriptor8DF1..8DF5, retain the dead-read abstraction explicitly, validate used matches, then inspect resultingC000 code. Any CPU fragment proof must state its gaps and must not supply unavailable reads.',
        open_questions=['All five completed resource outputs and their extents.','Post-expansionC000 reader/menu code.','Actual side2 header/filename consumer and original coding-review article.'],
        scope='Checkpoint only: derived original format, literal dependency proof and existing strict boundary. No decoded resource, new CPU/native execution, hardware response or article identity claim.',pass_=True)
    report['pass']=report.pop('pass_');target=output/'format-checkpoint.json';target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(target.relative_to(ROOT)),sha256=sha(target.read_bytes()),resources_decoded=0,
        first_literal=length,maximum_gaps=[b['entries'][-1]['maximum_gap'] for b in buckets]),indent=2))


if __name__=='__main__':main()
