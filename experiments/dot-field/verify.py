#!/usr/bin/env python3
"""Verify native PAL output after running sh build.sh; retain evidence in build/native/."""
import hashlib
import os
import importlib.util
import json
import math
import re
from pathlib import Path
import socket
import subprocess
from PIL import Image

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=HERE/'build/native'
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'proof.json').unlink(missing_ok=True)
spec=importlib.util.spec_from_file_location('shared_verification',ROOT/'verify.py')
common=importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
labels=common.read_labels(HERE/'build/main.sym')
sock=socket.socket()
sock.bind(('127.0.0.1',0))
port=sock.getsockname()[1]
sock.close()
program=HERE/'build/example.prg'
log=(OUT/'vice.log').open('w')
command=common.vice_command(os.environ.get('VICE','x64sc'),program,port,ROOT/'palettes/colodore.vpl')
monitor=None
records=[]
expected=bytearray(8000)
caches=[[None]*16 for _ in range(16)]
palette=[]
for line in (ROOT/'palettes/colodore.vpl').read_text().splitlines():
    if line and not line.startswith('#'):
        palette.append(tuple(int(v,16) for v in line.split()[:3]))

def wave(phase):
    return math.floor(15*math.sin(2*math.pi*(phase%256)/256)+0.5)

def predict(phase):
    late_clears=overwrites=0
    current=set()
    requests=[]
    for row in range(16):
        for address in caches[row]:
            if address is not None:
                late_clears+=address in current and expected[address]!=0
                expected[address]=0
        step=2+row//2
        origin=(160-15*step)//2
        shift=wave(phase+16*row)//2
        for column in range(16):
            x=origin+column*step+shift
            y=48+7*row+wave(phase+16*row+8*column)
            assert 0<=x<160 and 0<=y<200
            address=(y//8)*320+(x//4)*8+y%8
            value=3<<(6-2*(x%4))
            overwrites+=bool(expected[address] and expected[address]!=value)
            expected[address]=value
            current.add(address)
            requests.append((x,y))
            caches[row][column]=address
    return late_clears,overwrites,requests

process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
try:
    monitor=common.Monitor(common.connect_monitor(process,port))
    def stop_at(label):
        monitor.run('delete')
        monitor.run(f'break ${labels[label]:04x}')
        monitor.run('x')
        return monitor.registers()
    for index in range(32):
        start=stop_at('drawField')
        completed=stop_at('renderComplete')
        shown=stop_at('frameComplete')
        monitor.run('bank ram')
        ram=monitor.memory(OUT/f'iteration-{index:03d}.ram',0,65535)
        phase=ram[labels['phase']]
        iteration=int.from_bytes(ram[labels['iteration']:labels['iteration']+2],'little')
        assert phase==(index*5)%256 and iteration==index,(phase,iteration,index)
        clears,overwrites,requests=predict(phase)
        actual=ram[0x2000:0x2000+8000]
        assert actual==expected,(index,next((i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b),None))
        screenshot=None
        pixel_mismatches=None
        if index in (0,1,7,15,31):
            screenshot=OUT/f'iteration-{index:03d}.png'
            monitor.run(f'screenshot "{screenshot}" 2')
            image=Image.open(screenshot).convert('RGB')
            pixel_mismatches=0
            for y in range(200):
                for x in range(160):
                    address=(y//8)*320+(x//4)*8+y%8
                    selector=(expected[address]>>(6-2*(x%4)))&3
                    color=palette[(0,13,5,1)[selector]]
                    pixel_mismatches+=image.getpixel((32+x*2,35+y))!=color
                    pixel_mismatches+=image.getpixel((33+x*2,35+y))!=color
            assert pixel_mismatches==0,(index,pixel_mismatches)
        assert completed[2]-start[2]<2*19656,(index,completed,start)
        record={'iteration':index,'phase':phase,'requested_points':len(requests),
            'distinct_requested_positions':len(set(requests)),
            'stored_point_lanes':sum(bool((v>>shift)&3) for v in actual for shift in (0,2,4,6)),
            'later_row_clears_of_current_plots':clears,'plot_lane_replacements':overwrites,
            'bitmap_bytes_compared':8000,'bitmap_sha256':hashlib.sha256(actual).hexdigest(),
            'render_elapsed_pal_cycles':completed[2]-start[2],
            'frame_complete_clock':shown[2],'frame_complete_raster':shown[1],
            'screenshot':None if screenshot is None else screenshot.name,
            'screenshot_pixel_mismatches':pixel_mismatches}
        records.append(record)
    monitor.connection.sendall(b'quit\n')
    process.wait(timeout=10)
finally:
    if process.poll() is None:
        process.kill()
        process.wait(timeout=5)
    if monitor:
        (OUT/'monitor.log').write_text('\n'.join(monitor.transcript))
        monitor.connection.close()
    log.close()
proof={'pass':True,'program_sha256':hashlib.sha256(program.read_bytes()).hexdigest(),
    'command':command,'observations':records,'process_exit':process.returncode,
    'total_bitmap_bytes_compared':len(records)*8000,
    'total_native_pixels_compared':sum(r['screenshot'] is not None for r in records)*64000,
    'limits':['32 consecutive updates, not all 256 phases',
              'Five complete endpoint scanouts, not intermediate drawing scanout or physical hardware']}

entries=[]
for line in (OUT/'monitor.log').read_text().splitlines():
    match=re.match(r"^\.;([0-9a-fA-F]{4})\s+(.*)$",line)
    if match and int(match[1],16)==labels['frameComplete']:
        fields=match[2].split()
        entries.append(tuple(map(int,fields[-3:])))
intervals=[(b[2]-a[2])-63*(b[0]-a[0])-(b[1]-a[1]) for a,b in zip(entries,entries[1:])]
assert len(entries)==32 and intervals==[4*19656]*31,(len(entries),intervals)
proof['cadence_check']={'native_stops':len(entries),'pal_fields_per_update':4,
                        'intervals_checked':len(intervals),'beam_phase_corrected':True}

(OUT/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps({k:v for k,v in proof.items() if k not in ('command','observations')},indent=2))
print(json.dumps({'render_cycle_range':[min(r['render_elapsed_pal_cycles'] for r in records),max(r['render_elapsed_pal_cycles'] for r in records)],
    'stored_point_range':[min(r['stored_point_lanes'] for r in records),max(r['stored_point_lanes'] for r in records)],
    'later_clear_total':sum(r['later_row_clears_of_current_plots'] for r in records),
    'plot_replacements_total':sum(r['plot_lane_replacements'] for r in records)},indent=2))
