#!/usr/bin/env python3
"""Real DOS transfer, drive math, PREPLINE bytes, inactive bitmap and VIC pixels."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import shutil
import socket
import subprocess
from PIL import Image

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
VERTICES=[(-20,-20,-20),(20,-20,-20),(20,20,-20),(-20,20,-20),
          (-20,-20,20),(20,-20,20),(20,20,20),(-20,20,20)]
EDGES=[(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),
       (0,4),(1,5),(2,6),(3,7)]

def trunc(n,d):
    return (abs(n)//d)*(-1 if n<0 else 1)

def geometry(phase, vertices=VERTICES):
    # Independently evaluate the stated fixed-point transform, not drive RAM.
    q=lambda x: math.floor(x+0.5)
    sy,cy=(q(64*f(phase*math.tau/16)) for f in (math.sin,math.cos))
    sp,cp=(q(64*f((phase*3%16)*math.tau/16)) for f in (math.sin,math.cos))
    rotated=[]
    projected=[]
    for x,y,z in vertices:
        xx=trunc(x*cy,64)+trunc(z*sy,64)
        zz=trunc(z*cy,64)-trunc(x*sy,64)
        yy=trunc(y*cp,64)-trunc(zz*sp,64)
        zz=trunc(zz*cp,64)+trunc(y*sp,64)
        rotated.extend((xx%256,yy%256,zz%256))
        projected.extend((160+trunc(80*xx,96+zz),100+trunc(80*yy,96+zz)))
    packet=projected+[phase]
    checksum=0
    for n in packet:
        checksum^=n
    return bytes(rotated),bytes(packet+[checksum,0xa5])

def drawing(packet,bank):
    points=list(zip(packet[0:16:2],packet[1:16:2]))
    bitmap=bytearray(8192)
    code=bytearray()
    for start,end in EDGES:
        x0,y0=points[start]
        x1,y1=points[end]
        dx,dy=x1-x0,y1-y0
        steps=max(abs(dx),abs(dy))
        for i in range(steps+1):
            # Closed-form rational sampling, independent of CPU accumulators.
            offset=lambda d: (1 if d>=0 else -1)*((i*abs(d)+steps//2)//steps) if steps else 0
            x,y=x0+offset(dx),y0+offset(dy)
            assert 0<=x<256 and 0<=y<200
            address=(y//8)*320+(x//8)*8+y%8
            mask=128>>(x%8)
            bitmap[address]|=mask
            target=0x2000+bank*0x4000+address
            code.extend((0xad,target%256,target//256,0x09,mask,0x8d,target%256,target//256))
    code.append(0x60)
    assert len(code)<0x4000
    return bytes(bitmap),bytes(code)

def image_for(bitmap):
    image=Image.new('RGB',(320,200))
    pixels=image.load()
    for y in range(200):
        for x in range(320):
            if bitmap[y//8*320+x//8*8+y%8] & (128>>(x%8)):
                pixels[x,y]=(255,255,255)
    return image

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--poses',type=int,default=17)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    out=args.output or HERE/'build/verification'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out.mkdir(parents=True,exist_ok=True)
    receipt=out/'verification.json'
    receipt.unlink(missing_ok=True)
    proof={'passed':False,'poses':[],'events':[],'output':str(out)}
    process=monitor=None
    try:
        assert args.poses>=1
        spec=importlib.util.spec_from_file_location('native_common',ROOT/'verify.py')
        common=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(common)
        common.PROMPT=re.compile(rb'\((?:C|8|9|10|11):\$[0-9a-fA-F]{4}\) $')
        labels=common.read_labels(HERE/'build/main.sym')
        drive_labels=common.read_labels(HERE/'drive/build/main.sym')
        program=HERE/'build/example.prg'
        payload=(HERE/'drive/build/example.prg').read_bytes()
        sources=('main.asm','drive/main.asm','verify.py','build.sh','drive/build.sh','run.sh')
        source_hashes={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in sources}
        proof.update(program_sha256=hashlib.sha256(program.read_bytes()).hexdigest(),
                     drive_payload_sha256=hashlib.sha256(payload).hexdigest(),source_sha256=source_hashes)
        assert payload[:2]==b'\x00\x03' and len(payload)==1282
        palette=ROOT/'palettes/colodore.vpl'
        with socket.socket() as reserve:
            reserve.bind(('127.0.0.1',0))
            port=reserve.getsockname()[1]
        command=common.vice_command(shutil.which('x64sc'),program,port,palette)
        command[command.index('+warp')]='-warp'
        command+=['-drive8type','1541','-drive8truedrive','+trapdevice8','-drive8idle','0',
                  '-limitcycles','150000000']
        with (out/'vice.log').open('w') as log:
            process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            with common.connect_monitor(process,port) as connection:
                monitor=common.Monitor(connection)
                connection.settimeout(60)
                monitor.run('r')
                events={}
                for name in ('start','uploadComplete','requestStart','requestSent','coordinatesReady',
                             'clearDone','generateDone','executeDone','bankPublished','framePresented',
                             'faultIdle','capacityStopped'):
                    monitor.run(f'break C:{labels[name]:04x}')
                    events[('C',labels[name])]=name
                for name in ('driveCalcStart','driveCalcDone','driveReturn'):
                    monitor.run(f'break 8:{drive_labels[name]:04x}')
                    events[('8',drive_labels[name])]=name
                # Read physical memory without changing program execution.
                def memory(device,first,last,name):
                    monitor.run(f'device {device}:')
                    if device=='C': monitor.run('bank ram')
                    data=monitor.memory(out/name,first,last)
                    if device=='C': monitor.run('bank cpu')
                    return data
                def byte(name):
                    return memory('C',labels[name],labels[name],'state.bin')[0]
                def front_check(expected,name):
                    bank=byte('displayBank')
                    assert memory('C',0x2000+bank*0x4000,0x3fff+bank*0x4000,name)==expected
                    monitor.run('bank cpu')
                    assert monitor.memory(out/'cia2.bin',0xdd00,0xdd00)[0]&3==3-bank
                    vic=monitor.memory(out/'vic.bin',0xd011,0xd018)
                    assert vic[0]&0x7f==0x3b and vic[5]&0x3f==8 and vic[7]&0xfe==0x18
                old_bitmap=bytes(8192)
                stage={}
                vertices=VERTICES
                drive_entered=drive_done=False
                pictures=[]
                completed=0
                while completed<args.poses+1:
                    response=monitor.run('x')
                    device=re.findall(r'\((C|8):\$[0-9a-fA-F]{4}\) $',response)[-1]
                    regs=monitor.run('r')
                    match=re.search(r'^\.;([0-9a-fA-F]{4})\s+(.*)$',regs,re.M)
                    pc=int(match[1],16)
                    clock=int(match[2].split()[-1])
                    event=events.get((device,pc))
                    assert event, (device,hex(pc),response)
                    observation={'device':device,'stage':event,'clock':clock}
                    if device=='C':
                        observation.update(raster=int(match[2].split()[-3]),cycle=int(match[2].split()[-2]))
                    proof['events'].append(observation)
                    assert event not in ('faultIdle','capacityStopped'),(event,completed)
                    if event=='start':
                        proof['setup_start_c64_clock']=clock
                    elif event=='uploadComplete':
                        assert memory('8',0x300,0x7ff,'uploaded-payload.bin')==payload[2:]
                        proof['upload_complete_c64_clock']=clock
                        proof['setup_upload_c64_clocks']=clock-proof['setup_start_c64_clock']
                    elif event=='requestStart':
                        stage={'requestStart':clock,'phase':byte('phase')}
                        if completed==args.poses:
                            # Explicit synthetic INPUT witness, after normal poses:
                            # change only one real drive-side object coordinate.
                            vertices=[(-12,-20,-20)]+VERTICES[1:]
                            monitor.run('device 8:')
                            monitor.run(f'> {drive_labels["vertices"]:04x} f4')
                            stage['live_drive_vertex_input']={'vertex':0,'x':-12,'normal_x':-20}
                        drive_entered=drive_done=False
                        front_check(old_bitmap,'front-before-request.bin')
                    elif event=='driveCalcStart':
                        phase=memory('8',0x700,0x700,'drive-phase.bin')[0]
                        assert phase==stage['phase']
                        stage['driveCalcStart']=clock
                        drive_entered=True
                        stage['zp_before']=memory('8',0x80,0x9f,'drive-zp-before.bin').hex()
                    elif event=='driveCalcDone':
                        assert drive_entered
                        rotation,packet=geometry(stage['phase'],vertices)
                        actual=memory('8',0x740,0x757,f'pose-{completed:02d}-rotated.bin')
                        assert actual==rotation,(completed,actual.hex(),rotation.hex())
                        actual=memory('8',0x710,0x722,f'pose-{completed:02d}-drive-packet.bin')
                        assert actual==packet,(completed,actual.hex(),packet.hex())
                        stage['driveCalcDone']=clock
                        drive_done=True
                    elif event=='requestSent':
                        stage[event]=clock
                    elif event=='driveReturn':
                        assert memory('8',0x80,0x9f,'drive-zp-restored.bin').hex()==stage['zp_before']
                        stage[event]=clock
                    elif event=='coordinatesReady':
                        assert drive_done
                        rotation,packet=geometry(stage['phase'],vertices)
                        actual=memory('C',labels['packet'],labels['packet']+18,f'pose-{completed:02d}-received.bin')
                        assert actual==packet
                        stage[event]=clock
                        front_check(old_bitmap,'front-after-transfer.bin')
                    elif event=='clearDone':
                        bank=byte('drawBank')
                        assert memory('C',0x2000+bank*0x4000,0x3fff+bank*0x4000,'cleared.bin')==bytes(8192)
                        stage[event]=clock
                    elif event=='generateDone':
                        bank=byte('drawBank')
                        bitmap,code=drawing(geometry(stage['phase'],vertices)[1],bank)
                        actual=memory('C',0x8000,0x8000+len(code)-1,f'pose-{completed:02d}-generated.bin')
                        assert actual==code,(completed,next((i for i,(a,b) in enumerate(zip(actual,code)) if a!=b),None))
                        assert memory('C',0xf9,0xfa,'code-pointer.bin')==bytes(((0x8000+len(code)-1)%256,(0x8000+len(code)-1)//256))
                        stage[event]=clock
                        stage['writer_count']=(len(code)-1)//8
                        stage['generated_bytes']=len(code)
                        front_check(old_bitmap,'front-after-generation.bin')
                    elif event=='executeDone':
                        bank=byte('drawBank')
                        bitmap,code=drawing(geometry(stage['phase'],vertices)[1],bank)
                        assert memory('C',0x2000+bank*0x4000,0x3fff+bank*0x4000,f'pose-{completed:02d}-bitmap.bin')==bitmap
                        front_check(old_bitmap,'front-after-render.bin')
                        stage[event]=clock
                    elif event=='bankPublished':
                        assert byte('shownPhase')==stage['phase']
                        assert observation['raster']==252
                        stage[event]=clock
                    elif event=='framePresented':
                        assert observation['raster']==252
                        assert abs(clock-stage['bankPublished']-19656)<63
                        bank=byte('displayBank')
                        bitmap,code=drawing(geometry(stage['phase'],vertices)[1],bank)
                        assert byte('shownPhase')==stage['phase']
                        assert memory('C',0x0400+bank*0x4000,0x07e7+bank*0x4000,'screen.bin')==b'\x10'*1000
                        monitor.run('io d000')
                        shot=out/f'pose-{completed:02d}.png'
                        monitor.run(f'screenshot "{shot}" 2')
                        actual=Image.open(shot).convert('RGB').crop((32,35,352,235))
                        expected=image_for(bitmap)
                        wrong=sum(a!=b for a,b in zip(actual.get_flattened_data(),expected.get_flattened_data()))
                        assert wrong==0,(completed,'screenshot',wrong)
                        if 'live_drive_vertex_input' in stage:
                            ordinary=drawing(geometry(stage['phase'])[1],bank)[0]
                            assert ordinary!=bitmap
                            assert geometry(stage['phase'])[1][2:16]==geometry(stage['phase'],vertices)[1][2:16]
                            stage['changed_pixels_from_normal_object']=sum((a^b).bit_count() for a,b in zip(ordinary,bitmap))
                        pictures.append(actual)
                        stage[event]=clock
                        stage['drive_compute_clocks']=stage['driveCalcDone']-stage['driveCalcStart']
                        stage['request_to_coordinates_c64_clocks']=stage['coordinatesReady']-stage['requestStart']
                        stage['clear_c64_clocks']=stage['clearDone']-stage['coordinatesReady']
                        stage['generation_c64_clocks']=stage['generateDone']-stage['clearDone']
                        stage['execution_c64_clocks']=stage['executeDone']-stage['generateDone']
                        if proof['poses']:
                            stage['presentation_clocks']=clock-proof['poses'][-1]['framePresented']
                        proof['poses'].append(stage)
                        old_bitmap=bitmap
                        completed+=1
                    # A device memory read changes the monitor's current device.
                    monitor.run(f'device {device}:')
                connection.sendall(b'quit\n')
                process.wait(timeout=5)
                common.save_animation(pictures,out/'poses.gif',300)
        assert process.returncode==0
        assert source_hashes=={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in sources}
        assert proof['program_sha256']==hashlib.sha256(program.read_bytes()).hexdigest()
        assert proof['drive_payload_sha256']==hashlib.sha256((HERE/'drive/build/example.prg').read_bytes()).hexdigest()
        assert [pose['phase'] for pose in proof['poses']]==[n%16 for n in range(args.poses+1)]
        if args.poses>=17:
            assert proof['poses'][0]['phase']==proof['poses'][16]['phase']==0
        proof.update(passed=True,vice_exit_code=process.returncode,
                     normal_presentations=args.poses,synthetic_input_presentations=1,
                     checked_pixels=len(proof['poses'])*64000,
                     limitations=['Own arithmetic and DOS protocol; not Wegi original arithmetic or speed',
                                  'Native PAL VICE true-drive proof; no physical-hardware measurement'])
    except Exception as error:
        proof['error']=repr(error)
        raise
    finally:
        if monitor: (out/'monitor.txt').write_text('\n'.join(monitor.transcript))
        if process and process.poll() is None:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        receipt.write_text(json.dumps(proof,indent=2)+'\n')
        print(json.dumps({'passed':proof['passed'],'receipt':str(receipt),'poses':len(proof['poses'])}))

if __name__=='__main__': main()
