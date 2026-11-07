#!/usr/bin/env python3
"""Independent arithmetic/texture oracle for one original captured half-image.

No CPU instructions, emulator, native process or hardware model are run.
The oracle consumes original stored profile/texture/preset data and captured
input phase state, not the output glyphs, matrix, pointers or coefficients.
"""
from fractions import Fraction
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'build/research/impossible-thing'


def sha(data):return hashlib.sha256(data).hexdigest()
def record(path):
    data=Path(path).read_bytes()
    return dict(path=str(Path(path).resolve().relative_to(ROOT)),bytes=len(data),sha256=sha(data))
def checked(item):
    data=(ROOT/item['path']).read_bytes()
    assert len(data)==item['bytes'] and sha(data)==item['sha256'],item
    return data
def comparison(actual,expected,label):
    assert len(actual)==len(expected)
    differences=[dict(offset=i,expected=b,actual=a) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b]
    return dict(label=label,bytes=len(actual),exact=not differences,
                differences=differences,expected_sha256=sha(expected),actual_sha256=sha(actual))
def quantized_gradient(delta,divisor):
    assert -63<=delta<=63 and 16<=divisor<=79
    return (256*delta)//divisor if delta>=0 else -1-(256*(-delta-1))//divisor
def add_word(word,step,carry=0):
    total=word+(step&65535)+carry
    return total&65535,int(total>=65536)
def negative_column_words(step):
    # Whole-word borrow recurrence, not a byte/instruction interpreter.
    # The original negative-column loops do not reassert SEC per step.
    values=[0];word=0;borrow=0;operand=step&65535
    for _ in range(19):
        total=word-operand-borrow;word=total&65535;borrow=int(total<0);values.append(word)
    return values
def centered_columns(step):
    negative=negative_column_words(step)
    return [negative[19-column] if column<19 else ((column-19)*step)&65535 for column in range(40)]
def pack(word_u,word_v):return ((word_u>>8)&15)|(((word_v>>8)&15)<<4)
def local_offsets(a,b,c,e):
    # a,b are the vertical Q8 increments; c,e the horizontal increments.
    # U's horizontal helper retains the incoming/previous unsigned carry.
    # V's helper explicitly clears it on every horizontal increment.
    row_u=(-256 if c<0 else 0)&65535
    row_v=(-256 if e<0 else 0)&65535
    result=[];u_coordinates=[];v_coordinates=[];initial_carry=0
    for row in range(4):
        word_u=row_u;carry=initial_carry;line=[];line_u=[];line_v=[]
        for column in range(4):
            word_v=(row_v+column*e)&65535
            line.append(pack(word_u,word_v));line_u.append(word_u);line_v.append(word_v)
            if column<3:word_u,carry=add_word(word_u,c,carry)
        result.append(line);u_coordinates.append(line_u);v_coordinates.append(line_v)
        row_u,initial_carry=add_word(row_u,a)
        row_v=(row_v+b)&65535
    return result,u_coordinates,v_coordinates
def cyclic_distance(first,last):
    delta=(first-last)&15
    return min(delta,16-delta)
def reference_metrics(actual_indices,reference_indices,texture):
    mismatches=sum(a!=b for a,b in zip(actual_indices,reference_indices))
    colors=sum(texture[a]!=texture[b] for a,b in zip(actual_indices,reference_indices))
    max_u=max(cyclic_distance(a&15,b&15) for a,b in zip(actual_indices,reference_indices))
    max_v=max(cyclic_distance(a>>4,b>>4) for a,b in zip(actual_indices,reference_indices))
    classes={}
    for axis in ('horizontal','vertical'):
        for kind in ('within_character','across_character_boundary'):
            total=changed=0
            for y in range(100 if axis=='horizontal' else 99):
                for x in range(159 if axis=='horizontal' else 160):
                    across=(x%4==3) if axis=='horizontal' else (y%4==3)
                    if across!=(kind=='across_character_boundary'):continue
                    first=y*160+x;last=first+(1 if axis=='horizontal' else 160)
                    a1,a2=actual_indices[first],actual_indices[last]
                    r1,r2=reference_indices[first],reference_indices[last]
                    actual_delta=((a2-a1)&15,((a2>>4)-(a1>>4))&15)
                    reference_delta=((r2-r1)&15,((r2>>4)-(r1>>4))&15)
                    total+=1;changed+=actual_delta!=reference_delta
            classes[axis+'_'+kind]=dict(pairs=total,different_toroidal_coordinate_steps=changed)
    return dict(logical_samples=len(actual_indices),different_texture_indices=mismatches,
                different_texture_codes=colors,max_cyclic_u_difference=max_u,max_cyclic_v_difference=max_v,
                neighboring_step_comparisons=classes)


def main():
    output=BASE/'affine-analysis';output.mkdir(parents=True,exist_ok=True)
    boot_path=BASE/'binary/boot-proof.json';boot=json.loads(boot_path.read_text());assert boot['pass']
    source_item=next(item for item in boot['artifacts'] if item['path'].endswith('/conditional-unpacked.ram'))
    source=checked(source_item)
    first,end=boot['conditional_decoder']['output_first'],boot['conditional_decoder']['output_end_exclusive']
    assert sha(source[first:end])==boot['conditional_decoder']['output_sha256']
    native_path=BASE/'native-analysis/native-evidence.json';native=json.loads(native_path.read_text());assert native['pass']
    cases={item['name']:item for item in native['captures']}
    before,after=cases['select-01'],cases['select-02'];pre,post=checked(before['ram']),checked(after['ram'])
    assert before['registers']['pc']==after['registers']['pc']==0x227f
    assert before['D018']==0xda and after['D018']==0xc8
    # Pin the non-obvious original carry rules used in the word equations.
    assert source[0x2226:0x222f]==bytes.fromhex('98 65 03 a8 8a 65 02 aa 60')
    assert source[0x222f:0x2239]==bytes.fromhex('98 18 65 07 a8 8a 65 06 aa 60')
    assert source[0x2606:0x260c]==bytes.fromhex('8a 69 40 91 08 c8')
    assert source[0x2596]==source[0x25d1]==0x38 and source[0x25b1]==source[0x25ef]==0x18
    profile=list(source[0x2855:0x2895]);assert len(profile)==64 and min(profile)==0 and max(profile)==63
    wave=profile+profile[::-1]
    assert bytes(wave*4)==pre[0x600:0x800]
    def sample(phase):return wave[phase%128]
    preset=pre[0xb4]-1;assert 0<=preset<64
    assert pre[0x1f00:0x2000]==source[0x1f00:0x2000]
    increments=dict(zoom=source[0x1f00+preset],u=source[0x1f40+preset],v=source[0x1f80+preset])
    assert increments==dict(zoom=pre[0x2283],u=pre[0x2294],v=pre[0x229c])
    old=dict(u=pre[0xb0],v=pre[0xb1],zoom=pre[0xb2])
    phases={key:(old[key]+increments[key])&255 for key in old}
    divisor=16+sample(phases['zoom'])
    u=[sample(phases['u']+offset) for offset in (0,32,64)]
    v=[sample(phases['v']+offset) for offset in (32,64,96)]
    deltas=dict(a=u[0]-u[1],b=v[0]-v[1],c=u[2]-u[1],e=v[2]-v[1])
    q={key:quantized_gradient(delta,divisor) for key,delta in deltas.items()}
    a,b,c,e=(q[key] for key in ('a','b','c','e'))
    local,local_u,local_v=local_offsets(a,b,c,e)
    columns_u,columns_v=centered_columns(4*c),centered_columns(4*e)
    columns=[pack(x,y) for x,y in zip(columns_u,columns_v)]
    rows=[pack(((r-12)*4*a)&65535,((r-12)*4*b)&65535) for r in range(25)]
    matrix=[];screen_carries=[]
    for row in rows:
        carry=0;carry_line=[]
        for column in columns:
            carry_line.append(carry);total=row+column+carry;matrix.append(total&255);carry=int(total>=256)
        screen_carries.append(carry_line)
    texture=bytes(value&3 for value in source[0x2755:0x2855])
    charset=bytearray()
    for origin in range(256):
        for row in local:
            packed=sum(texture[(origin+offset)&255]<<(6-2*column) for column,offset in enumerate(row))
            charset.extend((packed,packed))
    assert len(charset)==2048 and len(matrix)==1000
    checks=[comparison(post[0xe000:0xe800],charset,'All 2048 bytes of the newly generated native charset'),
            comparison(post[0xf000:0xf3e8],bytes(matrix),'All 1000 bytes of the newly generated native screen')]
    pointers=bytes(value for row in local for column,offset in enumerate(row) for value in (offset,0x38+2*column))
    checks.append(comparison(post[0x20:0x40],pointers,'All 32 glyph-local texture pointer bytes'))
    checks.append(comparison(bytes(post[address] for address in range(0x2608,0x26f6,6)),bytes(columns),'All 40 screen-column immediate operands'))
    checks.append(comparison(post[0x40:0x68],bytes(rows+columns[25:]),'All 40 final row/remaining-column scratch bytes'))
    scalar_expected={0xb0:phases['u'],0xb1:phases['v'],0xb2:phases['zoom'],0x2722:divisor,
                     0x12:u[1],0x13:v[1],0x1e:255 if c<0 else 0,0x1f:255 if e<0 else 0}
    for high,low,value in [(0x10,0x11,4*a),(0x14,0x15,4*b),(0x02,0x03,c),(0x06,0x07,e),
                           (0xd2,0xd3,4*c),(0xd6,0xd7,4*e)]:
        scalar_expected[high]=(value>>8)&255;scalar_expected[low]=value&255
    scalar_differences=[dict(address=address,expected=value,actual=post[address])
                        for address,value in scalar_expected.items() if post[address]!=value]
    # An explicitly declared ideal: continuous 2D affine coordinates from
    # the SAME Q8 gradients, rounded only once at each full logical pixel.
    # This is not asserted to be the author's intended sampling contract.
    source_indices=[];ideal_q8=[];ideal_rational=[]
    for y in range(100):
        for x in range(160):
            row,column,ly,lx=y//4,x//4,y%4,x%4
            origin=matrix[row*40+column];source_indices.append((origin+local[ly][lx])&255)
            sx,sy=x-76,y-48
            ideal_q8.append(((c*sx+a*sy)//256&15)|(((e*sx+b*sy)//256&15)<<4))
            ideal_rational.append(((deltas['c']*sx+deltas['a']*sy)//divisor&15)|
                                  (((deltas['e']*sx+deltas['b']*sy)//divisor&15)<<4))
    quantization=[]
    for d in range(16,80):
        for delta in range(-63,64):
            quantization.append(Fraction(quantized_gradient(delta,d),256)-Fraction(delta,d))
    bounds=dict(cases=len(quantization),min_error=str(min(quantization)),max_error=str(max(quantization)),
                scope='Exact rational sweep of the broad source operand domain, not a native angle sweep.')
    outputs=[]
    for name,data in [('predicted-charset.bin',charset),('predicted-screen.bin',bytes(matrix)),
                      ('source-logical-indices.bin',bytes(source_indices))]:
        path=output/name;path.write_bytes(data);outputs.append(record(path))
    report=dict(script=record(Path(__file__)),boot_receipt=record(boot_path),source=source_item,
        corrected_native_receipt=record(native_path),before=before,after=after,
        inputs=dict(active_preset=preset,old_phases=old,phase_increments=increments,new_phases=phases,
                    profile_bytes=profile,wave_period=128,u_samples=u,v_samples=v,divisor=divisor,
                    deltas=deltas,Q8_gradients=q,texture_sha256=sha(texture)),
        local_offsets=local,local_U_words=local_u,local_V_words=local_v,
        column_U_words=columns_u,column_V_words=columns_v,packed_column_offsets=columns,
        packed_row_offsets=rows,screen_carry_inputs=screen_carries,
        comparisons=checks,scalar_expectations={str(address):value for address,value in scalar_expected.items()},
        scalar_differences=scalar_differences,quantization_bounds=bounds,
        declared_ideal_comparisons=dict(
            same_Q8_gradients=reference_metrics(source_indices,ideal_q8,texture),
            exact_rational_sample_differences=reference_metrics(source_indices,ideal_rational,texture),
            scope='Numerical comparison on 160x100 logical samples with independent 16x16 coordinate wrapping. It is not a VIC/raster oracle or a claim that this was the intended output.'),
        artifacts=outputs,
        scope='Independent integer/rational arithmetic and direct texture-byte oracle for one captured initial-preset half-image. No CPU replay, native actions, hardware model, all-angle native validation or 1997 Second Reality inference.',
        pass_=all(item['exact'] for item in checks) and not scalar_differences)
    report['pass']=report.pop('pass_');target=output/'affine-proof.json';target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(target.relative_to(ROOT)),sha256=sha(target.read_bytes()),pass_=report['pass'],
        gradients=q,comparisons=[dict(label=item['label'],bytes=item['bytes'],exact=item['exact'],differences=len(item['differences'])) for item in checks],
        scalar_differences=scalar_differences,ideal_comparisons=report['declared_ideal_comparisons']),indent=2))
    assert report['pass'],'Arithmetic mismatches remain in affine-proof.json'


if __name__=='__main__':main()
