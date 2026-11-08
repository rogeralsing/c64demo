#!/usr/bin/env python3
"""Verify native PAL output after running sh build.sh; retain evidence in build/native/."""
import hashlib
import os
import importlib.util
import json
import math
from pathlib import Path
import socket
import subprocess
from PIL import Image

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=HERE/'build/native'
OUT.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('shared_verification',ROOT/'verify.py')
common=importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
labels=common.read_labels(HERE/'build/main.sym')
sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
program=HERE/'build/example.prg'
log=(OUT/'vice.log').open('w')
command=common.vice_command(os.environ.get('VICE','x64sc'),program,port,ROOT/'palettes/colodore.vpl')
process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
palette=[tuple(int(v,16) for v in line.split()[:3]) for line in (ROOT/'palettes/colodore.vpl').read_text().splitlines() if line and not line.startswith('#')]
digit_rows=(0x0e,0x11,0x11,0x0f,1,2,0x1c)
def digit(x,y):
    return 0<=y<21 and 4<=x<19 and bool(digit_rows[y//3]&(16>>((x-4)//3)))
def marker(x,y):
    return 0<=x<24 and 0<=y<21 and (x-11)**2+(y-10)**2<=81
def small(x,y):
    return 0<=x<24 and 0<=y<21 and (x-11)**2+(y-10)**2<=16
def star(x,y):
    dx,dy=abs(x-11),abs(y-10)
    return 0<=x<24 and 0<=y<21 and dx+dy<=10 and (dx<3 or dy<3 or dx==dy)
font=bytes(sum(128>>bit for bit in range(8) if digit(col*8+bit,row*8+line))
           for row in range(3) for col in range(3) for line in range(8))
def expected_scene(frame):
    mode=(frame//128)%2
    marker_x=144+math.floor(64*math.cos(2*math.pi*(frame%256)/256)+0.5)
    slots=[(144 if mode==0 else 176,digit if mode==0 else star,1 if mode==0 else 5),
           (marker_x,marker,2)]+[(x,small,c) for x,c in zip((16,48,80,224,256,288),(6,4,3,8,7,13))]
    image=Image.new('RGB',(320,24),palette[0])
    for y in range(24):
        for x in range(320):
            color=1 if mode and digit(x-144,y) else 0
            for left,shape,ink in reversed(slots):
                if shape(x-left,y):color=ink
            image.putpixel((x,y),palette[color])
    return image,marker_x

selected={0,63,64,65,126,127,128,129,190,191,192,193,254,255,256}
records=[];monitor=None
try:
    monitor=common.Monitor(common.connect_monitor(process,port))
    monitor.run(f'break ${labels["irq"]:04x}')
    for step in range(260):
        monitor.run('x')
        monitor.run('bank ram')
        state=monitor.memory(OUT/'state.bin',labels['shownFrame'],labels['shownMode'])
        frame=int.from_bytes(state[:2],'little')
        if frame not in selected:continue
        name=f'frame-{frame:03d}'
        ram=monitor.memory(OUT/(name+'.ram'),0,65535)
        mode=(frame//128)%2
        assert state[2]==mode,(frame,state)
        assert ram[0x2c00:0x2c48]==font,(frame,'font transpose')
        assert ram[0x2800:0x2808]==bytes(8)
        stamp=[]
        for row in range(3):
            for col in range(3):
                address=0x400+11*40+18+row*40+col
                value=128+row*3+col if mode else 0
                assert ram[address]==value,(frame,address,ram[address],value)
                stamp.append(ram[address])
        assert ram[labels['ready']]==1,(frame,'producer not ready')
        queued=int.from_bytes(ram[labels['packetFrame']:labels['packetFrame']+2],'little')
        assert queued==frame+1,(frame,queued)
        assert ram[labels['packetMode']]==((frame+1)//128)%2
        monitor.run('bank io')
        io=monitor.memory(OUT/(name+'-io.bin'),0xd000,0xd02e)
        color=monitor.memory(OUT/(name+'-color.bin'),0xd800,0xdbff)
        assert io[0x15]==255 and io[0x1b]==0 and io[0x1c]==0 and io[0x1d]==0
        assert io[0x10]==0xc0
        assert all(io[1+2*i]==138 for i in range(8))
        assert io[0]==(168 if mode==0 else 200)
        assert io[0x27]&15==(1 if mode==0 else 5)
        assert ram[0x7f8]==(0x80 if mode==0 else 0x82)
        assert ram[0x7f9:0x800]==bytes((0x81,0x83,0x83,0x83,0x83,0x83,0x83))
        assert all(color[11*40+18+row*40+col]&15==1 for row in range(3) for col in range(3))
        expected,marker_x=expected_scene(frame)
        assert io[2]==marker_x+24
        shot=OUT/(name+'.png')
        monitor.run(f'screenshot "{shot}" 2')
        actual=Image.open(shot).convert('RGB').crop((32,35+88,352,35+88+24))
        mismatch=sum(a!=b for a,b in zip(actual.get_flattened_data(),expected.get_flattened_data()))
        assert mismatch==0,(frame,mismatch)
        records.append({'frame':frame,'mode':mode,'queued_frame':queued,'queued_mode':ram[labels['packetMode']],
            'font_bytes_compared':72,'screen_codes':stamp,'color_cells_compared':9,
            'active_hardware_sprites':8,'digit_representation':'sprite' if mode==0 else 'characters',
            'slot_zero_pointer':ram[0x7f8],'scene_pixels_compared':320*24,'pixel_mismatches':mismatch,
            'screenshot':shot.name,'ram_sha256':hashlib.sha256(ram).hexdigest()})
        if frame==256:break
    assert len(records)==len(selected),(len(records),len(selected))
    monitor.connection.sendall(b'quit\n');process.wait(timeout=10)
finally:
    if process.poll() is None:process.kill();process.wait(timeout=5)
    if monitor:
        (OUT/'monitor.log').write_text('\n'.join(monitor.transcript));monitor.connection.close()
    log.close()
before=Image.open(OUT/'frame-127.png').convert('RGB').crop((176,123,200,147))
after=Image.open(OUT/'frame-128.png').convert('RGB').crop((176,123,200,147))
assert before.tobytes()==after.tobytes()
back=Image.open(OUT/'frame-064.png').convert('RGB').crop((176,123,200,147))
front=Image.open(OUT/'frame-192.png').convert('RGB').crop((176,123,200,147))
priority_pixels=sum(a!=b for a,b in zip(back.get_flattened_data(),front.get_flattened_data()))
expected_priority=sum(digit(x,y) and marker(x,y) for y in range(24) for x in range(24))
assert priority_pixels==expected_priority and priority_pixels>0,(priority_pixels,expected_priority)
proof={'pass':True,'program_sha256':hashlib.sha256(program.read_bytes()).hexdigest(),
    'command':command,'observations':records,'process_exit':process.returncode,
    'total_scene_pixels_compared':len(records)*320*24,'switch_continuity_pixels':24*24,
    'switch_continuity_mismatches':0,'priority_changed_pixels':priority_pixels,
    'limits':['One aligned stamp and authored transition, not Nine ring geometry or fine scrolling',
              'Fifteen captured fields, not every PAL/VIC hardware revision']}
(OUT/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps({k:v for k,v in proof.items() if k not in ('command','observations')},indent=2))
