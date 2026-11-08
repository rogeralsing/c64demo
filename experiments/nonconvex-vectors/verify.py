#!/usr/bin/env python3
"""Independent topology, rational coverage, depth and native span-code oracle."""
from collections import Counter
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess

from PIL import Image,ImageChops

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=HERE/'build/verification'
OUTER=22
INNER=10
DEPTH=7
CORNERS=((-1,-1),(1,-1),(1,1),(-1,1))
MODEL=[(sx*radius,sy*radius,z) for z in (-DEPTH,DEPTH) for radius in (OUTER,INNER) for sx,sy in CORNERS]
QUADS=[]
for i in range(4):
    j=(i+1)%4
    QUADS.append((4+i,12+i,12+j,4+j))
for i in range(4):
    j=(i+1)%4
    QUADS.append((i,j,8+j,8+i))
for i in range(4):
    j=(i+1)%4
    QUADS.append((i,4+i,4+j,j))
for i in range(4):
    j=(i+1)%4
    QUADS.append((8+i,8+j,12+j,12+i))
TRIANGLES=[triangle for quad in QUADS for triangle in ((quad[0],quad[1],quad[2]),(quad[0],quad[2],quad[3]))]
COLORS=[2]*8+[1]*8+[3]*16


def product(a,b):
    assert abs(a+b)<=128 and abs(a-b)<=128
    return (a+b)**2//256-(a-b)**2//256


def area(a,b,c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def background(x,y):
    return int((x%8==0 and y%8==0) or (y==64 and x%4<2) or (x==32 and y%4==0))


def topology():
    edges=Counter()
    directions=Counter()
    for quad in QUADS:
        for a,b in zip(quad,quad[1:]+quad[:1]):
            edges[tuple(sorted((a,b)))]+=1
            directions[a,b]+=1
    assert all(count==2 for count in edges.values())
    assert all(directions[a,b]==directions[b,a]==1 for a,b in edges)
    euler=len(MODEL)-len(edges)+len(QUADS)
    assert euler==0
    return dict(vertices=len(MODEL),edges=len(edges),quad_faces=len(QUADS),triangles=len(TRIANGLES),
                euler_characteristic=euler,genus=(2-euler)//2,oriented_closed_manifold=True)


def reference(phase,check_depth=True):
    sine=lambda angle:math.floor(64*math.sin(angle*math.tau/256)+0.5)
    yaw=math.floor(32+18*math.sin(phase*math.tau/64)+0.5)
    pitch=math.floor(18+14*math.sin(phase*math.tau/64+0.4)+0.5)
    sy,cy,sp,cp=sine(yaw),sine(yaw+64),sine(pitch),sine(pitch+64)
    rotated=[];points=[]
    for x,y,z in MODEL:
        rx=product(x,cy)+product(z,sy)
        zz=product(z,cy)-product(x,sy)
        ry=product(y,cp)-product(zz,sp)
        rz=product(y,sp)+product(zz,cp)
        factor=math.floor(112*64/(144+rz)+0.5)
        rotated.append((rx,ry,rz))
        points.append((32+product(rx,factor),64-2*product(ry,factor)))
    assert all(0<=x<64 and 0<=y<128 for x,y in points),(phase,points)
    pixels=[background(x,y) for y in range(128) for x in range(64)]
    nearest=[None]*8192
    spans=[];visibility=[];occluded=0;overlap_pixels=set()
    case_counts=Counter()
    for triangle_id,indices in enumerate(TRIANGLES):
        vertices=[points[i] for i in indices]
        signed_area=area(*vertices)
        visibility.append(int(signed_area>=0))
        if signed_area<0:continue
        rows={}
        for y in range(min(v[1] for v in vertices),max(v[1] for v in vertices)+1):
            crossing=[]
            for a,b in zip(vertices,vertices[1:]+vertices[:1]):
                if a[1]==b[1]:continue
                if a[1]>b[1]:a,b=b,a
                if a[1]<=y<b[1]:
                    crossing.append(Fraction(a[0]*(b[1]-a[1])+(b[0]-a[0])*(y-a[1]),b[1]-a[1]))
            if len(crossing)<2:
                left,right=255,0
            else:
                left=math.ceil(min(crossing));right=math.ceil(max(crossing))
            if left>=right:
                case_counts['empty']+=1
                rows[y]=(left,right)
                continue
            case_counts['same_byte' if left//4==(right-1)//4 else 'positive_span']+=1
            rows[y]=(left,right)
            for x in range(left,right):
                offset=y*64+x
                if triangle_id>=8 and pixels[offset]==2:occluded+=1
                pixels[offset]=COLORS[triangle_id]
                if signed_area<=0:continue
                d=[144+rotated[i][2] for i in indices]
                weights=(area((x,y),vertices[1],vertices[2]),area(vertices[0],(x,y),vertices[2]),area(vertices[0],vertices[1],(x,y)))
                numerator=weights[0]*d[1]*d[2]+weights[1]*d[0]*d[2]+weights[2]*d[0]*d[1]
                denominator=signed_area*d[0]*d[1]*d[2]
                old=nearest[offset]
                if old is not None:overlap_pixels.add(offset)
                if old is None or numerator*old[1]>=old[0]*denominator:
                    nearest[offset]=(numerator,denominator,COLORS[triangle_id],triangle_id)
        spans.append(dict(triangle=triangle_id,rows=rows))
    mismatches=[]
    if check_depth:
        mismatches=[(i%64,i//64,pixels[i],item[2],item[3]) for i,item in enumerate(nearest) if item is not None and pixels[i]!=item[2]]
    canvas=bytearray(2048)
    for y in range(128):
        for x in range(64):canvas[(x//4)*128+y]|=pixels[y*64+x]<<(6-2*(x%4))
    plan=[]
    for item in spans:
        for y,(left,right) in item['rows'].items():
            index=0xf0 if left>=right else ((left//4)<<4)|((right-1)//4)
            plan.append((index,y,COLORS[item['triangle']]*85))
    outer_points=sorted(set(points[i] for i in (0,1,2,3,8,9,10,11)))
    hull=[]
    for point in outer_points:
        while len(hull)>=2 and area(hull[-2],hull[-1],point)<=0:hull.pop()
        hull.append(point)
    lower=len(hull)
    for point in reversed(outer_points[:-1]):
        while len(hull)>lower and area(hull[-2],hull[-1],point)<=0:hull.pop()
        hull.append(point)
    hull=hull[:-1]
    aperture=sum(nearest[y*64+x] is None and all(area(a,b,(x,y))>0 for a,b in zip(hull,hull[1:]+hull[:1]))
                 for y in range(128) for x in range(64))
    return dict(rotated=rotated,points=points,visibility=visibility,pixels=pixels,canvas=canvas,spans=spans,
                depth_mismatches=mismatches,case_counts=dict(case_counts),occluded_inner_pixels=occluded,
                depth_overlap_pixels=len(overlap_pixels),span_plan=plan,aperture_pixels=aperture)


def generated_reference():
    code=bytearray();dispatch=bytearray(1024);cases=[]
    def absolute(opcode,base,column):
        address=base+column*128
        return bytes((opcode,address&255,address>>8))
    for buffer in range(2):
        base=0x2000+buffer*0x800
        for left in range(16):
            for right in range(16):
                pointer=0x9000+len(code)
                index=left*16+right
                dispatch[buffer*512+index]=pointer&255
                dispatch[buffer*512+256+index]=pointer>>8
                start=len(code)
                if left>right:
                    code.append(0x60)
                    kind='empty'
                elif left==right:
                    code+=absolute(0x59,base,left)+bytes((0x25,0x22))
                    code+=absolute(0x59,base,left)+absolute(0x99,base,left)+b'\x60'
                    kind='same_byte'
                else:
                    for column in range(left+1,right):code+=absolute(0x99,base,column)
                    code+=absolute(0x59,base,left)+bytes((0x25,0x20))
                    code+=absolute(0x59,base,left)+absolute(0x99,base,left)+bytes((0xa5,0x23))
                    code+=absolute(0x59,base,right)+bytes((0x25,0x21))
                    code+=absolute(0x59,base,right)+absolute(0x99,base,right)+b'\x60'
                    kind='positive_span'
                cases.append(dict(buffer=buffer,left_byte=left,right_byte=right,address=pointer,
                                  bytes=len(code)-start,kind=kind))
    assert len(code)==9984 and len(cases)==512 and 0x9000+len(code)==0xb700
    return bytes(code),bytes(dispatch),cases


TRACE=re.compile(r'^#\d+ \(Trace\s+(exec|store)\s+([0-9a-f]{4})\)\s+'
                 r'(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\n'
                 r'\.C:([0-9a-f]+)\s+[^\n]*?- A:([0-9a-f]+) X:([0-9a-f]+) Y:([0-9a-f]+) '
                 r'SP:([0-9a-f]+) [^\n]*?\s+(\d+)\n',re.M|re.I)


def image_for(model,palette):
    image=Image.new('RGB',(384,272),palette[0])
    patch=Image.new('RGB',(64,128))
    patch.putdata([palette[(0,6,3,1)[pixel]] for pixel in model['pixels']])
    image.paste(patch.resize((128,128),Image.Resampling.NEAREST),(128,67))
    return image


def prepared_reference(phase,triangle):
    model=reference(phase,check_depth=False)
    vertices=[model['points'][i] for i in TRIANGLES[triangle]]
    left=bytearray([255]*128);right=bytearray(128)
    for a,b in zip(vertices,vertices[1:]+vertices[:1]):
        if a[1]>b[1]:a,b=b,a
        if a[1]==b[1]:continue
        for y in range(a[1],b[1]):
            crossing=math.ceil(Fraction(a[0]*(b[1]-a[1])+(b[0]-a[0])*(y-a[1]),b[1]-a[1]))
            left[y]=min(left[y],crossing);right[y]=max(right[y],crossing)
    return bytes(left+right)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'proof.json').unlink(missing_ok=True)
    spec=importlib.util.spec_from_file_location('shared_monitor',ROOT/'verify.py')
    common=importlib.util.module_from_spec(spec);spec.loader.exec_module(common)
    labels=common.read_labels(HERE/'build/main.sym')
    mesh=topology()
    models=[reference(phase) for phase in range(64)]
    assert all(not model['depth_mismatches'] for model in models)
    assert min(model['occluded_inner_pixels'] for model in models)>0
    assert max(model['aperture_pixels'] for model in models)>0
    code,dispatch,cases=generated_reference()
    palette=[tuple(int(v,16) for v in line.split()[:3]) for line in
             (ROOT/'palettes/colodore.vpl').read_text().splitlines() if line and not line.startswith('#')]
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1',0));port=reservation.getsockname()[1]
    program=HERE/'build/example.prg'
    command=common.vice_command(os.environ.get('VICE','x64sc'),program,port,ROOT/'palettes/colodore.vpl')
    monitor=None
    geometries=[];renders=[];presentations=[];prepared=[];images=[];span_events=[];all_span_events=[];publications=[]
    gen_begin=None;generation_clocks=None
    selected={0,8,16,24,32,40,48,56}
    def value(ram,name,size=1):
        return int.from_bytes(ram[labels[name]:labels[name]+size],'little')
    def compare(ram,name,expected):
        expected=bytes(v&255 for v in expected)
        actual=ram[labels[name]:labels[name]+len(expected)]
        assert actual==expected,(name,[(i,a,b) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b][:8])
    with (OUT/'vice.log').open('w') as log:
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        try:
            monitor=common.Monitor(common.connect_monitor(process,port));monitor.run('r')
            checkpoints={}
            for name in ('generateSpans','generationComplete','geometryPrepared','trianglePrepared','renderComplete','displayFrameComplete'):
                response=monitor.run(f'break {labels[name]:04x}')
                checkpoints[name]=int(re.search(r'BREAK:\s*(\d+)',response)[1])
            condition=' || '.join(f'(@ram:${labels["phase"]:04x} == ${phase:02x})' for phase in sorted(selected))
            monitor.run(f'condition {checkpoints["trianglePrepared"]} if {condition}')
            monitor.run(f'condition {checkpoints["displayFrameComplete"]} if @ram:${labels["publicationCounter"]:04x} != $00')
            monitor.run(f'trace exec {labels["spanDispatch"]:04x}')
            monitor.run('trace store d018')
            for stop in range(700):
                response=monitor.run('x')
                for kind,target,line,cycle,pc,a,x,y,sp,clock in TRACE.findall(response):
                    event=dict(kind=kind,target=int(target,16),raster=int(line),cycle=int(cycle),pc=int(pc,16),
                               a=int(a,16),x=int(x,16),y=int(y,16),clock=int(clock))
                    if kind=='exec':span_events.append(event)
                    elif labels['publication']<=event['pc']<labels['irqEnd']:
                        assert event['raster']<8 and event['a'] in (0x18,0x1a)
                        publications.append(event)
                pc,raster,clock=monitor.registers()
                monitor.run('bank ram')
                ram=monitor.memory(OUT/'latest.ram',0,65535)
                phase=value(ram,'phase')
                model=models[phase]
                field=value(ram,'fieldCounter',2)
                if pc==labels['generateSpans']:
                    gen_begin=clock
                elif pc==labels['generationComplete']:
                    assert gen_begin is not None
                    generation_clocks=clock-gen_begin
                    assert ram[0x9000:0xb700]==code
                    assert ram[0x8000:0x8400]==dispatch
                    assert value(ram,'generationEnd',2)==0xb700
                    (OUT/'generated-spans.bin').write_bytes(ram[0x9000:0xb700])
                    (OUT/'generated-dispatch.bin').write_bytes(ram[0x8000:0x8400])
                elif pc==labels['geometryPrepared']:
                    sequence=len(geometries)+1
                    assert phase==(sequence-1)%64
                    compare(ram,'projectedX',(point[0] for point in model['points']))
                    compare(ram,'projectedY',(point[1] for point in model['points']))
                    for axis,name in enumerate(('rotatedX','rotatedY','rotatedZ')):
                        compare(ram,name,(point[axis] for point in model['rotated']))
                    compare(ram,'triangleVisible',model['visibility'])
                    assert ram[0x9000:0xb700]==code and ram[0x8000:0x8400]==dispatch
                    geometries.append(dict(sequence=sequence,phase=phase,field=field,clock=clock,
                                           visible_triangles=sum(model['visibility']),
                                           occluded_inner_pixels=model['occluded_inner_pixels'],
                                           transparent_aperture_pixels=model['aperture_pixels']))
                elif pc==labels['trianglePrepared']:
                    triangle=value(ram,'triangleIndex')
                    assert model['visibility'][triangle]
                    assert ram[0x4800:0x4900]==prepared_reference(phase,triangle),(phase,triangle,'edge preparation')
                    prepared.append(dict(phase=phase,triangle=triangle,field=field,crossing_bytes=256))
                elif pc==labels['renderComplete']:
                    sequence=len(renders)+1
                    assert phase==(sequence-1)%64
                    actual_plan=[(row['x'],row['y'],row['a']) for row in span_events]
                    assert actual_plan==model['span_plan'],(phase,'actual endpoint-byte dispatch schedule',
                                                            len(actual_plan),len(model['span_plan']),
                                                            [(i,a,b) for i,(a,b) in enumerate(zip(actual_plan,model['span_plan'])) if a!=b][:8])
                    all_span_events.extend(span_events);span_events=[]
                    base=0x2000+(value(ram,'frontBuffer')^1)*0x800
                    actual=ram[base:base+2048]
                    assert actual==model['canvas'],(phase,'hidden charset pixels',
                                                   [(i,a,b) for i,(a,b) in enumerate(zip(actual,model['canvas'])) if a!=b][:8])
                    assert value(ram,'renderReady')==0
                    assert ram[0x9000:0xb700]==code and ram[0x8000:0x8400]==dispatch
                    renders.append(dict(sequence=sequence,phase=phase,field=field,clock=clock,
                                        render_clocks=clock-geometries[sequence-1]['clock'],
                                        span_case_counts=model['case_counts'],span_dispatches=len(actual_plan),
                                        hidden_charset_bytes=2048))
                elif pc==labels['displayFrameComplete']:
                    publication=value(ram,'publicationCounter',2)
                    assert publication==len(presentations)+1
                    shown=(publication-1)%64
                    shown_model=models[shown]
                    assert value(ram,'shownPhase')==shown
                    front=value(ram,'frontBuffer')
                    assert front==publication%2
                    assert ram[0x2000+front*0x800:0x2800+front*0x800]==shown_model['canvas']
                    assert len(publications)==publication
                    assert publications[-1]['a']==(0x1a if front else 0x18)
                    assert value(ram,'renderReady')==0
                    shot=OUT/f'publication-{publication:03d}-phase-{shown:02d}.png'
                    monitor.run(f'screenshot "{shot}" 2')
                    actual=Image.open(shot).convert('RGB')
                    expected=image_for(shown_model,palette)
                    difference=ImageChops.difference(actual,expected)
                    if difference.getbbox():
                        expected.save(OUT/'expected-failed.png');difference.save(OUT/'difference-failed.png')
                        raise AssertionError((publication,shown,'full VICscanout',difference.getbbox(),
                                              sum(a!=b for a,b in zip(actual.get_flattened_data(),expected.get_flattened_data()))))
                    images.append(actual)
                    presentations.append(dict(publication=publication,phase=shown,front_buffer=front,
                                              field=field,clock=clock,screenshot=shot.name))
                    if publication==66:break
                    monitor.run(f'condition {checkpoints["displayFrameComplete"]} if @ram:${labels["publicationCounter"]:04x} != ${publication:02x}')
                else:
                    raise AssertionError(('unexpected stop',hex(pc)))
            else:
                raise AssertionError('Bounded native loop did not reach66publications')
            monitor.connection.sendall(b'quit\n');process.wait(timeout=10)
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=5)
            if monitor:
                (OUT/'monitor.log').write_text('\n'.join(monitor.transcript));monitor.connection.close()
    assert len(presentations)==len(renders)==66
    assert {row['phase'] for row in presentations}==set(range(64))
    intervals=[b['field']-a['field'] for a,b in zip(presentations,presentations[1:])]
    totals=Counter()
    for row in renders:totals.update(row['span_case_counts'])
    assert all(totals[kind]>0 for kind in ('same_byte','positive_span','empty'))
    images[0].save(OUT/'nonconvex-vectors.gif',save_all=True,append_images=images[1:],duration=160,loop=0)
    proof=dict(pass_=True,program_sha256=hashlib.sha256(program.read_bytes()).hexdigest(),command=command,
               process_exit=process.returncode,topology=mesh,published_poses=66,distinct_poses=64,
               runtime_generated_cases=512,runtime_generated_code_bytes=len(code),
               runtime_generated_dispatch_bytes=len(dispatch),generation_clocks=generation_clocks,
               native_span_dispatches=len(all_span_events),native_span_case_counts=dict(totals),
               prepared_triangle_captures=len(prepared),prepared_crossing_bytes_compared=len(prepared)*256,
               hidden_charset_bytes_compared=66*2048,full_screenshot_pixels=66*384*272,
               host_depth_oracle_pixel_mismatches=0,
               genuine_inner_wall_occlusion_range=[min(row['occluded_inner_pixels'] for row in geometries),max(row['occluded_inner_pixels'] for row in geometries)],
               transparent_aperture_range=[min(row['transparent_aperture_pixels'] for row in geometries),max(row['transparent_aperture_pixels'] for row in geometries)],
               PAL_fields_per_publication=intervals,mean_PAL_fields_per_publication=sum(intervals)/len(intervals),
               native_render_clock_range=[min(row['render_clocks'] for row in renders),max(row['render_clocks'] for row in renders)],
               geometries=geometries,renders=renders,presentations=presentations,prepared=prepared,
               publications=publications,generated_cases=cases,span_events=all_span_events,
               limits=['Own closed square-frame prism with16vertices/16quad faces; not the original Sierpinsky/donut mesh.',
                       'Bounded64-pose rocking motion; near-edge-on quantization folds excluded before native implementation.',
                       'Independent depth oracle applies to the actual quantized projected mesh, with later-face priority at exact depth ties.',
                       'Inner-before-outer occlusion is specialized to this box-minus-through-hole shell, not a generic painter for arbitrary meshes.',
                       'PAL VICE8565 bounded output; no original frame-rate or physical-hardware claim.',
                       'Uniform160ms GIF samples do not describe native cadence.'])
    proof['pass']=proof.pop('pass_')
    (OUT/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps({key:value for key,value in proof.items() if key not in
                      ('command','geometries','renders','presentations','prepared','publications','generated_cases','span_events','PAL_fields_per_publication')},indent=2))


if __name__=='__main__':
    main()
