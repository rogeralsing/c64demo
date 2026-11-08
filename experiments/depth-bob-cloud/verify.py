#!/usr/bin/env python3
"""Independent prepared geometry, allocation/overlap/clear and native VIC proof."""
from collections import Counter
import hashlib
import importlib.util
import itertools
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
TRACE=re.compile(r'^#\d+ \(Trace\s+(exec|store)\s+([0-9a-f]{4})\)\s+'
                 r'(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\n'
                 r'\.C:([0-9a-f]+)\s+[^\n]*?- A:([0-9a-f]+) X:([0-9a-f]+) Y:([0-9a-f]+) '
                 r'SP:([0-9a-f]+) [^\n]*?\s+(\d+)\n',re.M|re.I)


def disk(size,x,y):
    # Independent pixel-center/radius form of the original disk specification.
    center=(size-1)/2
    return 0<=x<size and 0<=y<size and math.hypot(x-center,y-center)<=size/2-0.25


def multiply_matrix(a,b):
    return [[sum(a[row][k]*b[k][col] for k in range(3)) for col in range(3)] for row in range(3)]


def frame_reference(phase):
    angle=math.tau*phase/64
    yaw=angle+0.17
    pitch=0.51+0.27*math.sin(angle+0.29)
    roll=0.31*math.sin(2*angle+0.37)
    a,b=math.cos(yaw),math.sin(yaw)
    c,d=math.cos(pitch),math.sin(pitch)
    e,f=math.cos(roll),math.sin(roll)
    ry=((a,0,b),(0,1,0),(-b,0,a))
    rx=((1,0,0),(0,c,-d),(0,d,c))
    rz=((e,-f,0),(f,e,0),(0,0,1))
    matrix=multiply_matrix(ry,multiply_matrix(rx,rz))
    points=[]
    lattice=[point for point in itertools.product((-24,-8,8,24),repeat=3) if any(abs(v)==24 for v in point)]
    lattice.sort(key=lambda p:(p[2],p[1],p[0]))
    for identity,point in enumerate(lattice):
        x,y,z=[sum(matrix[axis][k]*point[k] for k in range(3)) for axis in range(3)]
        size=max(1,min(9,1+math.floor((42-z)*8/84+0.5)))
        px=math.floor(80.125+140*x/(128+z)-(size-1)/2+0.5)
        py=math.floor(64.375+140*y/(128+z)-(size-1)/2+0.5)
        assert 0<=px<=160-size and 0<=py<=128-size
        points.append(dict(identity=identity,x=px,y=py,size=size))
    points.sort(key=lambda p:(p['size'],-((p['y']//8)*20+p['x']//8),p['x']%8,p['y']%8,p['identity']))
    assert len(points)==56
    encoded=bytes([sum(p['size']==size for p in points) for size in range(1,10)]
                  +[v for p in points for v in (p['x'],p['y'])])
    return points,encoded


def point_cells(point):
    cells={}
    for y in range(point['size']):
        for x in range(point['size']):
            if not disk(point['size'],x,y):continue
            px,py=point['x']+x,point['y']+y
            address=(py//8+4)*40+px//8+10
            cells.setdefault(address,bytearray(8))[py%8]|=128>>(px%8)
    return cells


def pattern_reference():
    return bytes(sum(128>>bit for bit in range(8) if disk(size,column*8+bit-shift,y))
                 for size in range(1,10) for shift in range(8) for column in range(2) for y in range(size))


def stamp_reference(points,font,matrix):
    font=font.copy();matrix=matrix.copy();next_code=1
    point_counts=Counter();pixel_counts=Counter();reused=0
    for point in points:
        cells=point_cells(point)
        # Native column-major stamping visits upper cells before lower ones.
        # Whole cell masks are classified from the disk, not from shifted bytes.
        for address,rows in sorted(cells.items(),key=lambda item:(item[0]%40,item[0]//40)):
            point_counts[address]+=1
            if matrix[address]==0:
                assert next_code<192
                matrix[address]=next_code
                font[next_code*8:next_code*8+8]=bytes(8)
                next_code+=1
            else:
                reused+=1
            code=matrix[address]
            assert 1<=code<192
            for row,bits in enumerate(rows):font[code*8+row]|=bits
        for y in range(point['size']):
            for x in range(point['size']):
                if disk(point['size'],x,y):pixel_counts[point['x']+x,point['y']+y]+=1
    return font,matrix,dict(allocated=next_code-1,reused_cell_touches=reused,
                            cells_shared_by_points=sum(count>1 for count in point_counts.values()),
                            overlapping_pixels=sum(count>1 for count in pixel_counts.values()),
                            point_ink_pixels=sum(pixel_counts.values()),union_ink_pixels=len(pixel_counts))


def generated_clear_reference(clear_map):
    code=bytearray();pointers=[]
    for base in (0x400,0xc00):
        pointers.append(0x7000+len(code))
        for offset,used in enumerate(clear_map):
            if used:
                address=base+offset
                code+=bytes((0x8d,address&255,address>>8))
        code.append(0x60)
    return bytes(code),pointers


def image_for(points,base_font,base_matrix,colors,palette):
    image=Image.new('RGB',(384,272),palette[0])
    for y in range(200):
        for x in range(320):
            cell=(y//8)*40+x//8
            ink=base_font[base_matrix[cell]*8+y%8]&(128>>(x%8))
            if ink:image.putpixel((32+x,35+y),palette[colors[cell]&15])
    for point in points:
        for y in range(point['size']):
            for x in range(point['size']):
                if disk(point['size'],x,y):
                    image.putpixel((32+80+point['x']+x,35+32+point['y']+y),palette[5])
    return image


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'proof.json').unlink(missing_ok=True)
    spec=importlib.util.spec_from_file_location('shared_monitor',ROOT/'verify.py')
    common=importlib.util.module_from_spec(spec);spec.loader.exec_module(common)
    labels=common.read_labels(HERE/'build/main.sym')
    references=[frame_reference(phase) for phase in range(64)]
    encoded=b''.join(frame for points,frame in references)
    assert (HERE/'build/frames.bin').read_bytes()==encoded
    assert {point['size'] for points,frame in references for point in points}==set(range(1,10))
    clear_map=bytearray(1024)
    for points,frame in references:
        for point in points:
            for address in point_cells(point):clear_map[address]=1
    assert (HERE/'build/clear-map.bin').read_bytes()==clear_map
    static_font=(HERE/'build/static-font.bin').read_bytes()
    assert len(static_font)==512
    base_font=bytearray(1536)+bytearray(static_font)
    base_matrix=bytearray((HERE/'build/base-screen.bin').read_bytes())
    colors=(HERE/'build/colors.bin').read_bytes()
    assert len(base_matrix)==len(colors)==1024
    assert all(not used or base_matrix[i]==0 for i,used in enumerate(clear_map))
    fonts=[base_font.copy(),base_font.copy()]
    matrices=[base_matrix.copy(),base_matrix.copy()]
    clear_code,clear_pointers=generated_clear_reference(clear_map)
    patterns=pattern_reference()
    assert len(patterns)==720
    palette=[tuple(int(v,16) for v in line.split()[:3]) for line in
             (ROOT/'palettes/colodore.vpl').read_text().splitlines() if line and not line.startswith('#')]
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1',0));port=reservation.getsockname()[1]
    program=HERE/'build/example.prg'
    command=common.vice_command(os.environ.get('VICE','x64sc'),program,port,ROOT/'palettes/colodore.vpl')
    monitor=None;generation_begin=None;generation_clocks=None
    clear_records=[];renders=[];presentations=[];images=[];points_trace=[];all_points=[];publications=[]
    def value(ram,name,size=1):
        return int.from_bytes(ram[labels[name]:labels[name]+size],'little')
    def check_pairs(ram):
        for buffer in range(2):
            base=0x2000+buffer*0x800;screen=(0x400,0xc00)[buffer]
            assert ram[base:base+2048]==fonts[buffer],('complete font ownership',buffer)
            assert ram[screen:screen+1024]==matrices[buffer],('complete matrix ownership',buffer)
    with (OUT/'vice.log').open('w') as log:
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        try:
            monitor=common.Monitor(common.connect_monitor(process,port));monitor.run('r')
            for name in ('generateClears','generationComplete','clearBegin','clearedBackBuffer','renderComplete','displayComplete','allocationFault'):
                monitor.run(f'break {labels[name]:04x}')
            monitor.run(f'trace exec {labels["pointPrepared"]:04x}')
            monitor.run('trace store d018')
            for stop in range(400):
                response=monitor.run('x')
                for kind,target,line,cycle,pc,a,x,y,sp,clock in TRACE.findall(response):
                    row=dict(kind=kind,target=int(target,16),raster=int(line),cycle=int(cycle),pc=int(pc,16),
                             size=int(a,16),x=int(x,16),y=int(y,16),clock=int(clock))
                    if kind=='exec':points_trace.append(row)
                    elif labels['publishImage']<=row['pc']<labels['displayComplete']:
                        assert row['raster']<8 and row['size'] in (0x18,0x3a)
                        publications.append(row)
                pc,raster,clock=monitor.registers()
                monitor.run('bank ram')
                ram=monitor.memory(OUT/'latest.ram',0,65535)
                assert pc!=labels['allocationFault'],'private glyph capacity/static region fault'
                phase=value(ram,'poseUsed')
                points,frame=references[phase]
                field=value(ram,'frameCounter',2)
                if pc==labels['generateClears']:
                    generation_begin=clock
                    assert ram[0x7000:0x7000+len(clear_code)]!=clear_code
                elif pc==labels['generationComplete']:
                    assert generation_begin is not None
                    generation_clocks=clock-generation_begin
                    assert ram[0x7000:0x7000+len(clear_code)]==clear_code
                    assert value(ram,'clearA',2)==clear_pointers[0]
                    assert value(ram,'clearB',2)==clear_pointers[1]
                    assert value(ram,'clearEnd',2)==0x7000+len(clear_code)
                    assert ram[0x3800:0x3800+720]==patterns
                    check_pairs(ram)
                    (OUT/'generated-clears.bin').write_bytes(clear_code)
                elif pc==labels['clearBegin']:
                    sequence=len(clear_records)+1
                    assert phase==(sequence-1)%64
                    check_pairs(ram)
                    clear_records.append(dict(sequence=sequence,phase=phase,field=field,begin_clock=clock))
                elif pc==labels['clearedBackBuffer']:
                    buffer=(value(ram,'drawFontHigh')-0x20)//8
                    assert buffer==len(clear_records)%2
                    for offset,used in enumerate(clear_map):
                        if used:matrices[buffer][offset]=0
                    assert matrices[buffer]==base_matrix
                    check_pairs(ram)
                    assert ram[0x7000:0x7000+len(clear_code)]==clear_code
                    clear_records[-1].update(buffer=buffer,end_clock=clock,clocks=clock-clear_records[-1]['begin_clock'],
                                             cleared_cells=sum(clear_map),front_pair_preserved=True,
                                             both_fonts_preserved=True)
                elif pc==labels['renderComplete']:
                    sequence=len(renders)+1
                    assert phase==(sequence-1)%64
                    assert [(row['x'],row['y'],row['size']) for row in points_trace]==[
                        (point['x'],point['y'],point['size']) for point in points],('decoded point/size schedule',phase)
                    all_points.extend(points_trace);points_trace=[]
                    buffer=(value(ram,'drawFontHigh')-0x20)//8
                    fonts[buffer],matrices[buffer],metrics=stamp_reference(points,fonts[buffer],matrices[buffer])
                    check_pairs(ram)
                    assert value(ram,'nextCode')==metrics['allocated']+1
                    assert ram[0x4000:0x4000+len(encoded)]==encoded
                    assert ram[0x6000:0x6200]==static_font
                    assert ram[0x3800:0x3800+720]==patterns
                    assert ram[0x7000:0x7000+len(clear_code)]==clear_code
                    renders.append(dict(sequence=sequence,phase=phase,field=field,clock=clock,buffer=buffer,
                                        render_clocks=clock-clear_records[sequence-1]['end_clock'],**metrics))
                elif pc==labels['displayComplete']:
                    sequence=len(presentations)+1
                    assert value(ram,'presentationCounter',2)==sequence
                    assert phase==value(ram,'frontPose')==(sequence-1)%64
                    check_pairs(ram)
                    front=(value(ram,'frontFontHigh')-0x20)//8
                    assert front==sequence%2 and value(ram,'frontScreenHigh')==(4 if front==0 else 12)
                    assert len(publications)==sequence and publications[-1]['size']==(0x18 if front==0 else 0x3a)
                    monitor.run('bank io')
                    native_colors=monitor.memory(OUT/'latest-colors.bin',0xd800,0xdbff)
                    assert bytes(value&15 for value in native_colors)==bytes(value&15 for value in colors)
                    shot=OUT/f'publication-{sequence:03d}-pose-{phase:02d}.png'
                    monitor.run(f'screenshot "{shot}" 2')
                    actual=Image.open(shot).convert('RGB')
                    expected=image_for(points,base_font,base_matrix,colors,palette)
                    difference=ImageChops.difference(actual,expected)
                    if difference.getbbox():
                        expected.save(OUT/'expected-failed.png');difference.save(OUT/'difference-failed.png')
                        raise AssertionError((sequence,phase,'full VICpoint/static image',difference.getbbox(),
                                              sum(a!=b for a,b in zip(actual.get_flattened_data(),expected.get_flattened_data()))))
                    images.append(actual)
                    presentations.append(dict(publication=sequence,pose=phase,front_buffer=front,
                                              field=field,clock=clock,screenshot=shot.name))
                    if sequence==66:break
                else:
                    raise AssertionError(('unexpected stop',hex(pc)))
            else:
                raise AssertionError('Bounded run did not complete66publications')
            monitor.connection.sendall(b'quit\n');process.wait(timeout=10)
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=5)
            if monitor:
                (OUT/'monitor.log').write_text('\n'.join(monitor.transcript));monitor.connection.close()
    assert len(presentations)==len(renders)==len(clear_records)==66
    assert {row['pose'] for row in presentations}==set(range(64))
    assert all(row['cells_shared_by_points']>0 and row['overlapping_pixels']>0 for row in renders)
    assert max(row['allocated'] for row in renders)<192
    intervals=[b['field']-a['field'] for a,b in zip(presentations,presentations[1:])]
    images[0].save(OUT/'depth-bob-cloud.gif',save_all=True,append_images=images[1:],duration=160,loop=0)
    proof=dict(pass_=True,program_sha256=hashlib.sha256(program.read_bytes()).hexdigest(),command=command,
               process_exit=process.returncode,point_count=56,prepared_poses=64,published_poses=66,
               prepared_coordinate_bytes=len(encoded),prepared_geometry='independent composed3x3matrix oracle matches host Euler producer',
               depth_sizes=sorted({row['size'] for row in all_points}),actual_point_stamps=len(all_points),
               selective_clear_cells=sum(clear_map),runtime_generated_clear_bytes=len(clear_code),generation_clocks=generation_clocks,
               allocated_private_glyph_range=[min(row['allocated'] for row in renders),max(row['allocated'] for row in renders)],
               shared_by_points_cell_range=[min(row['cells_shared_by_points'] for row in renders),max(row['cells_shared_by_points'] for row in renders)],
               overlapping_pixel_range=[min(row['overlapping_pixels'] for row in renders),max(row['overlapping_pixels'] for row in renders)],
               complete_pair_bytes_compared_per_stage=2*(2048+1024),pair_stages=len(clear_records)*3,
               full_screenshot_pixels=66*384*272,PAL_fields_per_publication=intervals,
               mean_PAL_fields_per_publication=sum(intervals)/len(intervals),
               clear_clock_range=[min(row['clocks'] for row in clear_records),max(row['clocks'] for row in clear_records)],
               rasterization_clock_range=[min(row['render_clocks'] for row in renders),max(row['render_clocks'] for row in renders)],
               clears=clear_records,renders=renders,presentations=presentations,point_stamps=all_points,publications=publications,
               limits=['Own56-point cage and64prepared poses, not the original98-point stream or assets.',
                       'Host rotation/projection/depth-size grouping; C64does only live stamping/allocation/OR merging/clear/publication.',
                       'Same-ink OR union supplies overlap, not opaque depth-sorted blobs or a general3Drenderer.',
                       'Natural fixed scene uses fewer than192private glyphs; arbitrary overload input is outside this bounded proof.',
                       'PAL VICE8565; no original frame-rate or physical-hardware claim.',
                       'Uniform160ms GIFsamples do not represent native cadence.'])
    proof['pass']=proof.pop('pass_')
    (OUT/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps({key:value for key,value in proof.items() if key not in
                      ('command','clears','renders','presentations','point_stamps','publications','PAL_fields_per_publication')},indent=2))


if __name__=='__main__':main()
