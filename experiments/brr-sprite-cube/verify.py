#!/usr/bin/env python3
"""Independent BRR geometry/rank/pixel and real C64/1541 native observer."""
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess

from PIL import Image, ImageChops

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=HERE/'build/verification'
EDGES=((0,1),(2,3),(4,5),(6,7),(0,2),(1,3),(4,6),(5,7),(0,4),(1,5),(2,6),(3,7))
FACES=((0,2,6,4),(1,3,7,5),(0,1,5,4),(2,3,7,6),(0,1,3,2),(4,5,7,6))
EDGE_LOOKUP={tuple(sorted(pair)):i for i,pair in enumerate(EDGES)}
TRACE=re.compile(r'^#\d+ \(Trace\s+(store|exec)\s+([0-9a-f]{4})\)\s+'
                 r'(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\n'
                 r'\.C:([0-9a-f]+)\s+[^\n]*?- A:([0-9a-f]+) X:([0-9a-f]+) Y:([0-9a-f]+) '
                 r'SP:([0-9a-f]+) [^\n]*?\s+(\d+)\n',re.M|re.I)


def reverse(value):
    return int(f'{value:08b}'[::-1],2)


def product(a,b):
    assert abs(a+b)<=128 and abs(a-b)<=128
    return (a+b)**2//256-(a-b)**2//256


def reference(phase):
    sine=lambda angle:math.floor(64*math.sin(angle*math.tau/256)+0.5)
    yaw=4*phase+3
    pitch=math.floor(32+12*math.sin(phase*math.tau/64)+0.5)
    sy,cy,sp,cp=sine(yaw),sine(yaw+64),sine(pitch),sine(pitch+64)
    points=[];rotated=[]
    for vertex in range(8):
        x,y,z=(15 if vertex&(1<<axis) else -15 for axis in range(3))
        rx=product(x,cy)+product(z,sy)
        zz=product(z,cy)-product(x,sy)
        ry=product(y,cp)-product(zz,sp)
        rz=product(y,sp)+product(zz,cp)
        rotated.append((rx,ry,rz))
        points.append((36+product(rx,48),42-product(ry,96)))
    normals=(-product(sy,cp),sp,product(cy,cp))
    visible=[int(normals[axis]>0) if side==0 else int(normals[axis]<0)
             for axis in range(3) for side in range(2)]
    colors=[0]*12
    for face,corners in enumerate(FACES):
        if not visible[face]:continue
        color=face//2+1
        for first,last in zip(corners,corners[1:]+corners[:1]):
            colors[EDGE_LOOKUP[tuple(sorted((first,last)))]]^=color
    records=[];traces=bytearray(12*84);markers=bytearray(18*84)
    for edge,(first,last) in enumerate(EDGES):
        if not colors[edge]:continue
        (x0,y0),(x1,y1)=points[first],points[last]
        if y0==y1:continue
        if y0>y1:(x0,y0),(x1,y1)=(x1,y1),(x0,y0)
        n=y1-y0;q,r=divmod(x1-x0,n)
        threshold=sorted(reverse(y) for y in range(y0,y1))[r] if r else 0
        path={y:x0+(y-y0)*q+sum(reverse(t)<threshold for t in range(y0,y))
              for y in range(y0,y1)}
        endpoint=x0+n*q+sum(reverse(t)<threshold for t in range(y0,y1))
        assert endpoint==x1
        for y,x in path.items():
            assert 0<=x<72 and 0<=y<84
            traces[edge*84+y]=x
            markers[y*18+x//4]^=colors[edge]<<(6-2*(x%4))
        records.append(dict(edge=edge,first=y0,last=y1,x0=x0,x1=x1,q=q,r=r,n=n,
                            threshold=threshold,path=path))
    packet=bytes([len(records)]+[v for item in records for v in (item['first'],item['last'],item['x0'],item['x1'])])
    results=bytes(value for item in records for value in (item['q']&255,item['threshold']))
    # Direct per-face intervals provide an opaque pixel oracle independent of
    # the C64 XOR-marker prefix filler and packed sprite addressing.
    pixels=[0]*(72*84)
    coverage=[0]*(72*84)
    by_edge={item['edge']:item for item in records}
    for face,corners in enumerate(FACES):
        if not visible[face]:continue
        boundary=[by_edge.get(EDGE_LOOKUP[tuple(sorted((a,b)))])
                  for a,b in zip(corners,corners[1:]+corners[:1])]
        for y in range(84):
            crossings=sorted(item['path'][y] for item in boundary if item and y in item['path'])
            assert len(crossings) in (0,2),(phase,face,y,crossings)
            if not crossings:continue
            for x in range(*crossings):
                coverage[y*72+x]+=1
                pixels[y*72+x]=face//2+1
    overlaps=sum(value>1 for value in coverage)
    # Keep overlap evidence explicit; native completion requires a disjoint
    # bounded motion and will not silently accept XOR colors for overlapped faces.
    canvas=bytearray(1536)
    for y in range(84):
        for x in range(72):
            address=(y//21)*384+(x//12)*64+(y%21)*3+(x%12)//4
            canvas[address]|=pixels[y*72+x]<<(6-2*(x%4))
    return dict(points=points,rotated=rotated,normals=normals,visible=visible,colors=colors,
                records=records,packet=packet,results=results,traces=traces,markers=markers,
                pixels=pixels,canvas=canvas,overlaps=overlaps)


def image_for(model,palette):
    image=Image.new('RGB',(384,272),palette[0])
    patch=Image.new('RGB',(72,84))
    patch.putdata([palette[(0,6,13,3)[pixel]] for pixel in model['pixels']])
    image.paste(patch.resize((288,168),Image.Resampling.NEAREST),(48,49))
    return image


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'proof.json').unlink(missing_ok=True)
    spec=importlib.util.spec_from_file_location('shared_monitor',ROOT/'verify.py')
    common=importlib.util.module_from_spec(spec);spec.loader.exec_module(common)
    labels=common.read_labels(HERE/'build/main.sym')
    models=[reference(phase) for phase in range(64)]
    assert all(model['overlaps']==0 for model in models)
    palette=[tuple(int(v,16) for v in line.split()[:3]) for line in
             (ROOT/'palettes/colodore.vpl').read_text().splitlines() if line and not line.startswith('#')]
    drive_program=(HERE/'drive/build/example.prg').read_bytes()
    assert drive_program[:2]==b'\x00\x03'
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1',0));port=reservation.getsockname()[1]
    program=HERE/'build/example.prg'
    command=common.vice_command(os.environ.get('VICE','x64sc'),program,port,ROOT/'palettes/colodore.vpl')
    command+=['-drive8type','1541','-drive8truedrive','+trapdevice8']
    monitor=None
    requests=[];responses=[];renders=[];presentations=[];images=[];wire_slots=[];display_fields=[]
    active_display=None
    marker_bytes=trace_bytes=canvas_bytes=0
    def value(ram,name,size=1):
        return int.from_bytes(ram[labels[name]:labels[name]+size],'little')
    def compare(ram,name,expected):
        expected=bytes(v&255 for v in expected)
        actual=ram[labels[name]:labels[name]+len(expected)]
        assert actual==expected,(name,[(i,a,b) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b][:8])
    with (OUT/'vice.log').open('w') as log:
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        try:
            monitor=common.Monitor(common.connect_monitor(process,port))
            monitor.connection.settimeout(30)
            monitor.run('r')
            checkpoints={}
            for name in ('requestPrepared','driveResponseReady','renderComplete','displayFrameComplete','protocolFault','uploadFault'):
                response=monitor.run(f'break {labels[name]:04x}')
                checkpoints[name]=int(re.search(r'BREAK:\s*(\d+)',response)[1])
            monitor.run(f'condition {checkpoints["displayFrameComplete"]} if @ram:${labels["publicationCounter"]:04x} != $00')
            monitor.run('trace store d018')
            monitor.run(f'trace exec {labels["wireSlotComplete"]:04x}')
            for stop in range(400):
                response=monitor.run('x')
                for kind,target,line,cycle,pc,a,x,y,sp,clock in TRACE.findall(response):
                    row=dict(kind=kind,target=int(target,16),raster=int(line),cycle=int(cycle),
                             pc=int(pc,16),a=int(a,16),clock=int(clock))
                    if kind=='exec' and row['target']==labels['wireSlotComplete']:
                        assert row['raster']<64,('IEC slot intruded on sprite display',row)
                        wire_slots.append(row)
                        assert active_display is not None
                        active_display['wire_slot']=row
                    elif kind=='store' and row['target']==0xd018:
                        pc=row['pc']
                        if labels['displayTop']<=pc<labels['wireSlotComplete']:
                            if active_display is not None:
                                assert len(active_display['stores'])==4
                                display_fields.append(active_display)
                            assert row['a']==0x1e and row['raster']<6
                            active_display=dict(stores=[row])
                        elif labels['displayBand1']<=pc<labels['displayEnd']:
                            assert active_display is not None
                            index=len(active_display['stores'])
                            assert 1<=index<=3
                            assert row['a']==(0x2e,0x1e,0x2e)[index-1]
                            assert row['raster']==(106,148,190)[index-1],row
                            active_display['stores'].append(row)
                pc,raster,clock=monitor.registers()
                monitor.run('bank ram')
                ram=monitor.memory(OUT/'latest-c64.ram',0,65535)
                assert pc not in (labels['protocolFault'],labels['uploadFault']),('native fault',hex(pc))
                phase=value(ram,'phase')
                model=models[phase]
                field=value(ram,'fieldCounter',2)
                if pc==labels['requestPrepared']:
                    sequence=len(requests)+1
                    assert phase==(sequence-1)%64
                    compare(ram,'projectedX',(point[0] for point in model['points']))
                    compare(ram,'projectedY',(point[1] for point in model['points']))
                    for axis,name in enumerate(('rotatedX','rotatedY','rotatedZ')):
                        compare(ram,name,(point[axis] for point in model['rotated']))
                    compare(ram,'normalZ',model['normals'])
                    compare(ram,'faceVisible',model['visible'])
                    compare(ram,'edgeColors',model['colors'])
                    compare(ram,'requestEdges',(item['edge'] for item in model['records']))
                    compare(ram,'wirePacket',model['packet'])
                    assert value(ram,'requestCount')==len(model['records'])<=9
                    assert value(ram,'packetLength')==len(model['packet'])
                    assert value(ram,'responseLength')==2+len(model['results'])
                    requests.append(dict(sequence=sequence,phase=phase,field=field,clock=clock,
                                         requested_edges=len(model['records'])))
                elif pc==labels['driveResponseReady']:
                    sequence=len(responses)+1
                    assert phase==(sequence-1)%64
                    expected=bytes((sequence&255,len(model['records'])))+model['results']
                    compare(ram,'wireResponse',expected)
                    assert value(ram,'wireState')==4
                    drive_path=OUT/f'drive-response-{sequence:03d}.ram'
                    monitor.run(f'bsave "{drive_path}" 0 8:0000 8:07ff')
                    drive_ram=drive_path.read_bytes()
                    assert len(drive_ram)==2048
                    # All code/padding/table bytes uploaded through real DOS.
                    assert drive_ram[0x300:0x700]==drive_program[2:0x402]
                    assert drive_ram[0x700:0x700+len(model['packet'])-1]==model['packet'][1:]
                    assert drive_ram[0x740:0x740+len(model['results'])]==model['results']
                    diagnostic=bytes(v for item in model['records'] for v in (item['r'],item['n']))
                    assert drive_ram[0x780:0x780+len(diagnostic)]==diagnostic
                    assert drive_ram[0x2f1]==drive_ram[0x2f2]==sequence&255
                    responses.append(dict(sequence=sequence,phase=phase,field=field,clock=clock,
                                          transport_fields=field-requests[sequence-1]['field'],
                                          drive_inputs=len(model['packet'])-1,result_bytes=len(model['results']),
                                          signed_quotients=[item['q'] for item in model['records']],
                                          fractional_ranks=[item['r'] for item in model['records']],
                                          drive_ram_sha256=hashlib.sha256(drive_ram).hexdigest()))
                elif pc==labels['renderComplete']:
                    sequence=len(renders)+1
                    assert phase==(sequence-1)%64
                    compare(ram,'allTraces',model['traces'])
                    assert ram[0x4000:0x4000+1512]==model['markers'],('marker bytes',phase)
                    base=0x2000+(value(ram,'frontBuffer')^1)*0x800
                    assert ram[base:base+1536]==model['canvas'],('hidden sprite bytes',phase)
                    assert value(ram,'drawBaseHi')==base>>8
                    assert value(ram,'renderReady')==0
                    # Full restored generated-code contract, independent of the
                    # C64patcher. Its position stores now target the last edge.
                    last_edge=model['records'][-1]['edge']
                    for row in range(84):
                        target=labels['allTraces']+last_edge*84+row
                        expected=bytes((0x8d,target&255,target>>8,0xe0,reverse(row)+1,0x65,0x26))
                        assert ram[0x5800+row*7:0x5800+(row+1)*7]==expected,(phase,'restored BRRcell',row)
                    marker_bytes+=1512;trace_bytes+=1008;canvas_bytes+=1536
                    renders.append(dict(sequence=sequence,phase=phase,field=field,clock=clock,
                                        render_clocks=clock-responses[sequence-1]['clock'],
                                        marker_bytes=1512,position_bytes=1008,sprite_bytes=1536))
                elif pc==labels['displayFrameComplete']:
                    publication=value(ram,'publicationCounter',2)
                    assert publication==len(presentations)+1
                    shown=(publication-1)%64
                    assert value(ram,'shownPhase')==shown
                    shown_model=models[shown]
                    front=value(ram,'frontBuffer')
                    assert front==publication%2
                    assert ram[0x2000+front*0x800:0x2600+front*0x800]==shown_model['canvas']
                    assert ram[0x7f8:0x7fe]==bytes(0x80+front*32+12+i for i in range(6))
                    assert ram[0xbf8:0xbfe]==bytes(0x80+front*32+18+i for i in range(6))
                    assert active_display is not None and len(active_display['stores'])==4
                    assert field==len(display_fields)+1
                    shot=OUT/f'publication-{publication:03d}-phase-{shown:02d}.png'
                    monitor.run(f'screenshot "{shot}" 2')
                    actual=Image.open(shot).convert('RGB')
                    expected=image_for(shown_model,palette)
                    difference=ImageChops.difference(actual,expected)
                    if difference.getbbox():
                        expected.save(OUT/'expected-failed.png');difference.save(OUT/'difference-failed.png')
                        raise AssertionError((publication,shown,'full sprite scanout',difference.getbbox(),
                                              sum(a!=b for a,b in zip(actual.get_flattened_data(),expected.get_flattened_data()))))
                    images.append(actual)
                    presentations.append(dict(publication=publication,phase=shown,front_buffer=front,
                                              field=field,clock=clock,screenshot=shot.name))
                    if publication==66:break
                    monitor.run(f'condition {checkpoints["displayFrameComplete"]} if @ram:${labels["publicationCounter"]:04x} != ${publication:02x}')
                else:
                    raise AssertionError(('unexpected native stop',hex(pc)))
            else:
                raise AssertionError('Bounded native loop did not complete66publications')
            monitor.connection.sendall(b'quit\n');process.wait(timeout=10)
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=5)
            if monitor:
                (OUT/'monitor.log').write_text('\n'.join(monitor.transcript));monitor.connection.close()
    assert len(presentations)==66 and len(responses)==len(renders)==66
    assert len(requests) in (66,67)
    assert {row['phase'] for row in presentations}==set(range(64))
    intervals=[b['field']-a['field'] for a,b in zip(presentations,presentations[1:])]
    images[0].save(OUT/'brr-sprite-cube.gif',save_all=True,append_images=images[1:],duration=160,loop=0)
    proof=dict(pass_=True,program_sha256=hashlib.sha256(program.read_bytes()).hexdigest(),
               drive_program_sha256=hashlib.sha256(drive_program).hexdigest(),command=command,
               process_exit=process.returncode,published_poses=66,distinct_poses=64,
               drive_request_edges=sum(row['requested_edges'] for row in requests[:66]),
               drive_code_and_table_bytes_compared=66*1024,
               position_bytes_compared=trace_bytes,marker_bytes_compared=marker_bytes,
               hidden_sprite_bytes_compared=canvas_bytes,full_screenshot_pixels=66*384*272,
               continuous_display_fields_checked=len(display_fields)+1,
               actual_D018_stores_checked=(len(display_fields)+1)*4,
               IEC_slots_checked=len(wire_slots),IEC_slot_raster_range=[min(row['raster'] for row in wire_slots),max(row['raster'] for row in wire_slots)],
               PAL_fields_per_publication=intervals,mean_PAL_fields_per_publication=sum(intervals)/len(intervals),
               native_render_clock_range=[min(row['render_clocks'] for row in renders),max(row['render_clocks'] for row in renders)],
               requests=requests,responses=responses,renders=renders,presentations=presentations,
               display_fields=display_fields,wire_slots=wire_slots,
               limits=['Own72x84 logical,288x168 physical multicolor sprite canvas; orthographic live cube, not the original172x172 renderer.',
                       'Own drive quotient/rank selection and custom IEC transport; no original payload or unmeasured50Hz claim.',
                       'Five-cycle CPX/ADC is the arithmetic core only; position stores, setup, fill, transport and raster work remain additional.',
                       'BRR is approximate interpolation; oracle follows its strict rank contract rather than exact ceiling-DDA pixels.',
                       'PAL VICE8565 with a true1541; no physical-hardware or analog-output claim.',
                       'GIF shows sampled poses at uniform160ms and does not represent native cadence.'])
    proof['pass']=proof.pop('pass_')
    (OUT/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps({key:value for key,value in proof.items() if key not in
                      ('command','requests','responses','renders','presentations','display_fields','wire_slots','PAL_fields_per_publication')},indent=2))


if __name__=='__main__':
    main()
