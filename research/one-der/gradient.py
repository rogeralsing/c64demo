#!/usr/bin/env python3
"""Pure integer reconstruction of One-Der's original1770..18EC gradient.

No CPU interpreter, emulator, native process or build runs. Carry-sensitive
arithmetic is expressed as bounded byte/word operations and fixed loops.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/one-der'
CASE = BASE / 'native-01'
OUTPUT_ROOT = BASE / 'gradient-analysis'
PROOF = 'build/research/one-der/analysis/accepted-02/one-der-proof.json'
CASE_SHA = '3264e764ff72ae0744de5c0a3b55beabd7641ac370c79744a8fb3ba0f4b361a9'
PINS = {
    PROOF:'e5eaaa1c454462e84de564b0984b8d587a37993b2b42457cc504bff0925f1532',
    'research/one-der/analyze.py':'8b46d13c021f2d691bacfd87c2194e77450459b8d5c1b3ea24da0e71ed6338f4',
    'build/research/one-der/native-01/part2-ram.bin':'ae274129e0803ae83617c912631fdfa06192e2291b3d5c2793483f8dc4b230a5',
    'build/research/one-der/native-01/events.jsonl':'5278f1776cb7115e39a05831c1acc5668dbf1ea0ecfe6ea207bdacea611eb044',
    'build/research/one-der/native-01/received.bin':'2d006008a4e30e95255a21752146272dc1d490c12e28b08b6dbe620e18aa7b9e',
}
MEMORY = re.compile(r'^>C:([0-9a-f]{4})  ([0-9a-f]{2}(?: [0-9a-f]{2}){0,3})(?=\s{2,}|$)',re.M|re.I)
HEADER = re.compile(r'^#(?P<checkpoint>\d+) \(Trace\s+exec (?P<target>0e53|0e56)\)\s+'
    r'(?P<line>\d+)/\$[0-9a-f]+,\s+(?P<cycle>\d+)/\$[0-9a-f]+\n'
    r'\.C:(?P<pc>0e53|0e56)\s+[^\n]*?- A:(?P<a>[0-9a-f]{2}) X:(?P<x>[0-9a-f]{2}) Y:(?P<y>[0-9a-f]{2}) '
    r'SP:(?P<sp>[0-9a-f]{2}) (?P<flags>[^ ]{8})\s+(?P<clock>\d+)\n',re.M|re.I)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw=path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)),bytes=len(raw),sha256=sha(raw))


def s8(n):
    return n if n<128 else n-256


def s16(n):
    return n if n<32768 else n-65536


def half_difference(a,b):
    """SBC/ROR/EOR80 maps unsigned a-b exactly to floor((a-b)/2)."""
    value=(a-b)&255
    return ((value>>1)|(128 if a>=b else 0))^128


def multiply(a,b):
    """Original17EA signed8x8 complement-bit multiplication, result mod65536."""
    negatives=int(a>=128)+int(b>=128)
    ma=(-a)&255 if a>=128 else a
    mb=(-b)&255 if b>=128 else b
    low=ma^255
    high=0
    bit=low&1
    low>>=1
    for _ in range(8):
        if bit==0:
            high=(high+mb)&255
        carry=high&1
        high>>=1
        bit=low&1
        low=(low>>1)|(carry<<7)
    result=(high<<8)|low
    return (-result)&65535 if negatives==1 else result


def divide(numerator,denominator):
    """Original1853 two fixed eight-step quotient stages, preserving quirks.

    N,D are16-bit stored words. Output26 is integer byte,27 is fraction.
    The guard and zero-divisor behavior are retained rather than idealized.
    """
    negative_n=bool(numerator&32768)
    negative_d=bool(denominator&32768)
    n=(-numerator)&65535 if negative_n else numerator
    d=(-denominator)&65535 if negative_d else denominator
    sign=(int(negative_n)-int(negative_d))&255
    doubled=(n<<1)&65535
    denominator_stored=(d-1)&65535
    integer,fraction=doubled&255,doubled>>8
    remainder_low,remainder_high=fraction,0
    if remainder_low>=denominator_stored:
        return dict(integer=integer,fraction=fraction,denominator_stored=denominator_stored,
            carry=1,mode='early_guard',sign_patch=sign,numerator_abs=n,denominator_abs=d,
            numerator_doubled_mod65536=doubled,remainder=0)
    # ASL26 / ROL28 before the two stages. The latter carry is an input to
    # the first subtraction; it cannot be replaced with an ideal division.
    carry=integer>>7
    integer=(integer<<1)&255
    old=remainder_low
    remainder_low=((remainder_low<<1)|carry)&255
    carry=old>>7
    for stage in range(2):
        for _ in range(8):
            trial=(remainder_high<<8|remainder_low)-denominator_stored-(1-carry)
            accepted=trial>=0
            if accepted:
                remainder_low,remainder_high=trial&255,(trial>>8)&255
            carry=int(accepted)
            if stage==0:
                old=integer
                integer=((integer<<1)|carry)&255
                carry=old>>7
                old=remainder_low
                remainder_low=((remainder_low<<1)|carry)&255
            else:
                fraction=((fraction<<1)|carry)&255
                old=remainder_low
                remainder_low=(remainder_low<<1)&255
            carry=old>>7
            old=remainder_high
            remainder_high=((remainder_high<<1)|carry)&255
            carry=old>>7
    unsigned=(integer<<8)|fraction
    if sign:
        unsigned=(-unsigned)&65535
        carry=int(unsigned==0)
    return dict(integer=unsigned>>8,fraction=unsigned&255,denominator_stored=denominator_stored,
        carry=carry,mode='normal',sign_patch=sign,numerator_abs=n,denominator_abs=d,
        numerator_doubled_mod65536=doubled,remainder=(remainder_high<<8)|remainder_low)


def gradient(triples):
    (x0,y0,z0),(x1,y1,z1),(x2,y2,z2)=triples
    dy21,dy01=(y2-y1)&255,(y0-y1)&255
    dz10,dz21=half_difference(z1,z0),half_difference(z2,z1)
    numerator=(multiply(dy21,dz10)+multiply(dy01,dz21))&65535
    dx10,dx21=(x1-x0)&255,(x2-x1)&255
    denominator=(multiply(dy21,dx10)+multiply(dy01,dx21))&65535
    division=divide(numerator,denominator)
    result=[dy21,dy01,division['fraction'],division['integer'],division['denominator_stored']&255,
            division['denominator_stored']>>8,division['integer'],division['fraction']]
    return dict(result_20_to_27=result,carry=division['carry'],
        dy21_signed=s8(dy21),dy01_signed=s8(dy01),half_dz10_signed=s8(dz10),half_dz21_signed=s8(dz21),
        numerator_word=numerator,numerator_signed=s16(numerator),denominator_word=denominator,
        denominator_signed=s16(denominator),division=division,
        returned_22_23_signed_Q8=s16(result[2]|result[3]<<8))


def captures(proof):
    case_files=[dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(CASE.iterdir()) if p.is_file()]
    assert sha(json.dumps(case_files,sort_keys=True,separators=(',',':')).encode())==CASE_SHA==proof['case_sha256']
    assert proof['pass_'] and proof['gradient_trace']['executed_runtime_gradient_calls']==4
    events=[json.loads(line) for line in (CASE/'events.jsonl').read_text().splitlines()]
    response=next(e for e in events if e['kind']=='response' and e['sequence']==111)
    assert response['command']=='x' and response['status']=='completed'
    wire=(CASE/'received.bin').read_bytes()[response['received_first']:response['received_end']]
    assert wire.decode(errors='replace')==response['response']
    raw=response['response'].replace('\r\n','\n')
    headers=list(HEADER.finditer(raw))
    assert len(headers)==8==len(re.findall(r'^#\d+ \(Trace',raw,re.M))
    parsed=[]
    for index,match in enumerate(headers):
        chunk=raw[match.end():headers[index+1].start() if index+1<len(headers) else len(raw)]
        memory={}
        for line in MEMORY.finditer(chunk):
            address=int(line[1],16)
            for offset,value in enumerate(bytes.fromhex(line[2])):
                assert address+offset not in memory
                memory[address+offset]=value
        before=index%2==0
        assert int(match['pc'],16)==int(match['target'],16)==(0xe53 if before else 0xe56)
        assert int(match['checkpoint'])==(3 if before else 4) and int(match['sp'],16)==0xf4
        assert chunk.startswith('Executing: m 0010 0027'+('; m 0072 0079' if before else '')+'\n')
        assert set(memory)==set(range(0x10,0x28))|(set(range(0x72,0x7a)) if before else set())
        parsed.append(dict(memory=memory,clock=int(match['clock']),carry=int(match['flags'][-1].upper()=='C'),a=int(match['a'],16)))
    results=[]
    for index in range(4):
        before,after=parsed[index*2:index*2+2]
        triples=[[before['memory'][j] for j in range(start,start+3)] for start in (0x10,0x13,0x16)]
        actual=[after['memory'][j] for j in range(0x20,0x28)]
        previous=proof['gradient_trace']['triangles'][index]
        assert triples==previous['vertex_triples'] and actual==previous['result_20_to_27']
        assert after['clock']-before['clock']==previous['elapsed_cycles']
        model=gradient(triples)
        matches=model['result_20_to_27']==actual and model['carry']==after['carry']
        assert after['a']==actual[2]
        results.append(dict(index=index,vertex_triples=triples,native_output_20_to_27=actual,
            native_carry=after['carry'],model=model,all_eight_output_bytes_and_carry_equal=matches,
            entry_clock=before['clock'],return_clock=after['clock']))
    return results,dict(response_sequence=111,received_first=response['received_first'],received_end=response['received_end'],
        accepted_case_sha256=CASE_SHA,full_case_files_rehashed=len(case_files),
        scope='Pinned frozen proof supplies prior full wire/capture custody. This parser rechecks the exact response slice and all entry/return payload bytes.')


def domain_probes():
    for a in range(256):
        for b in range(256):
            assert multiply(a,b)==(s8(a)*s8(b))&65535
            assert s8(half_difference(a,b))==(a-b)//2
    zero_outputs={}
    for n in range(65536):
        result=divide(n,0)
        key=(result['integer'],result['fraction'],result['carry'],result['mode'])
        zero_outputs[key]=zero_outputs.get(key,0)+1
    selected=[(0,1),(1,1),(-1,1),(1,-1),(127,2),(128,2),(255,2),
              (32767,32767),(-32768,640),(490,-485)]
    probes=[]
    for n,d in selected:
        model=divide(n&65535,d&65535)
        exact=((abs(n)*512)//abs(d))*(-1 if (n<0)!=(d<0) else 1)
        observed=s16((model['integer']<<8)|model['fraction'])
        probes.append(dict(numerator=n,denominator=d,model=model,
            ideal_signed_truncation_Q8=exact,stored_signed_Q8=observed,equals_ideal_mod65536=(exact&65535)==(observed&65535)))
    return dict(signed_multiply_exhaustive_cases=65536,half_difference_exhaustive_cases=65536,
        zero_denominator_all_65536_numerators=[dict(integer=k[0],fraction=k[1],carry=k[2],mode=k[3],count=v) for k,v in sorted(zero_outputs.items())],
        selected_guard_sign_and_overflow_probes=probes,
        scope='Pure scalar domain probes, not additional native observations. Nonideal guard/overflow outputs remain recorded without tuning.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUTPUT_ROOT/'accepted-01')
    directory=parser.parse_args().output.expanduser().resolve()
    directory.relative_to(OUTPUT_ROOT.resolve())
    if directory.exists() and any(directory.iterdir()):
        raise SystemExit('Output must be fresh or empty; choose a new --output directory.')
    for path,pin in PINS.items():
        assert sha((ROOT/path).read_bytes())==pin,path
    memory=(CASE/'part2-ram.bin').read_bytes()
    code=memory[0x1770:0x18ed]
    assert memory[0xe53:0xe58]==bytes.fromhex('207017a200')
    assert code[:7]==bytes.fromhex('a51738e5148520') and code[-1]==0x60
    code_bindings=[]
    for stem in ('part2','later-frame','draw-end'):
        observed=(CASE/(stem+'-ram.bin')).read_bytes()[0x1770:0x18ed]
        changed=[i for i,(a,b) in enumerate(zip(code,observed)) if a!=b]
        assert changed in ([],[0x18dc-0x1770]) and observed[0x18dc-0x1770] in (0,1,255)
        code_bindings.append(dict(capture=stem,full_region_bytes=len(observed),
            changed_byte_addresses=[i+0x1770 for i in changed],sign_immediate=observed[0x18dc-0x1770]))
    proof=json.loads((ROOT/PROOF).read_text())
    rows,custody=captures(proof)
    probes=domain_probes()
    directory.mkdir(parents=True,exist_ok=True)
    outputs=[]
    def output(name,raw):
        (directory/name).write_bytes(raw)
        return dict(file=name,bytes=len(raw),sha256=sha(raw))
    outputs.append(output('gradient-original-1770-18ec.bin',code))
    outputs.append(output('gradient.checked.py',Path(__file__).read_bytes()))
    result=dict(pass_=all(r['all_eight_output_bytes_and_carry_equal'] for r in rows),producer=artifact(Path(__file__).resolve()),
        inputs=[artifact(ROOT/path) for path in PINS],custody=custody,
        original_code=dict(start=0x1770,end_inclusive=0x18ec,bytes=len(code),sha256=sha(code),
            accepted_runtime_region_bindings=code_bindings,only_allowed_selfmodification='18DC sign immediate00/01/FF written by STX18DC at187F.'),
        mathematical_contract='Byte-wrapped signed coordinate differences; floor of unsigned intensity differences/2; signed8 products with word-wrapped sums; original carry-sensitive divider; Q8 bytes22fraction/23integer.',
        samples=rows,domain=probes,outputs=outputs,
        limits=['Four native gradient calls only; no edge, full span, image, independent lighting or stock-speed acceptance.',
            'Scalar code does not interpret opcodes, run CPU instructions, model time or invoke an emulator/build.',
            'Native elapsed clocks are retained only to bind existing call pairs; no new timing or speedup claim.',
            'Early guard, sign bypass, modulo overflow and zero-divisor outcomes are original algorithm behavior, not replaced with ideal division.'])
    receipt=output('gradient-proof.json',(json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps(dict(output=str(directory),receipt=receipt,pass_=result['pass_'],samples=[dict(index=r['index'],native=r['native_output_20_to_27'],scalar=r['model']['result_20_to_27'],carry=r['native_carry'],equal=r['all_eight_output_bytes_and_carry_equal']) for r in rows],zero_divisor=probes['zero_denominator_all_65536_numerators']),indent=2))


if __name__=='__main__':
    main()
