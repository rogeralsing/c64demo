#!/usr/bin/env python3
"""Verify native PAL output after running sh build.sh; retain evidence in build/native/."""
import hashlib
import os
import importlib.util
import json
from pathlib import Path
import socket
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=HERE/'build/native'
OUT.mkdir(parents=True,exist_ok=True)
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
process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
monitor=None
records=[]
try:
    monitor=common.Monitor(common.connect_monitor(process,port))
    monitor.run(f'break ${labels["updateFrame"]:04x}')
    for index in range(321):
        monitor.run('x')
        if index not in (64,192,320):
            continue
        name={64:'combined',192:'idle-only',320:'mask-only'}[index]
        monitor.run('bank ram')
        ram=monitor.memory(OUT/f'{name}.ram',0,65535)
        counter=int.from_bytes(ram[labels['frameCounter']:labels['frameCounter']+2],'little')
        assert counter==index,(index,counter)
        monitor.run(f'screenshot "{OUT/name}.png" 2')
        io=monitor.run('bank io')
        io+=monitor.run('m d000 d02e')
        records.append({'view':name,'counter':counter,'mode':ram[labels['mode']],
                        'idle_byte':ram[0x3fff],'registers':monitor.run('r'),
                        'io':io,'ram_sha256':hashlib.sha256(ram).hexdigest()})
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
(OUT/'capture.json').write_text(json.dumps({'program_sha256':hashlib.sha256(program.read_bytes()).hexdigest(),
    'command':command,'observations':records,'process_exit':process.returncode},indent=2)+'\n')
print(json.dumps({'observations':[{k:v for k,v in r.items() if k not in ('io','registers')} for r in records],
                  'process_exit':process.returncode},indent=2))

from collections import Counter
import hashlib
import json
from pathlib import Path
from PIL import Image

names=('combined','idle-only','mask-only')
images={n:Image.open(OUT/(n+'.png')).convert('RGB') for n in names}
black=(0,0,0)
gray=images['idle-only'].getpixel((33,240))
ram=(OUT/'combined.ram').read_bytes()
def expected(name,x,y):
    idle=0 if name=='mask-only' else 0x81
    background=black if idle&(0x80>>(x&7)) else gray
    if name=='idle-only':
        return background
    sprite=x//48
    column=x%48
    packed=ram[0x2000+sprite*64+y*3+column//16]
    symbol=(packed>>(6-2*((column%16)//4)))&3
    return background if symbol==0 else black if symbol==1 else gray

scores=[]
for top in range(235,245):
    score=0
    for name,im in images.items():
        score+=sum(im.getpixel((32+x,top+y))!=expected(name,x,y) for y in range(21) for x in range(320))
    scores.append((score,top))
best=min(scores)
print({'best_pixel_match':best,'gray':gray,'scores':scores})
assert best[0]==0,best
top=best[1]
counts={n:sum(images[n].getpixel((32+x,top+y))==black for y in range(21) for x in range(320)) for n in names}
changed=sum(images['combined'].getpixel((32+x,top+y))!=images['mask-only'].getpixel((32+x,top+y)) for y in range(21) for x in range(320))
assert changed>0
receipt={'pass':True,'scope':'All 320x21 sprite-covered lower-border pixels in three naturally selected native views',
    'pixels_compared':3*320*21,'sprite_canvas_origin':[32,top],
    'black_pixel_counts':counts,'pixels_added_by_idle_shine_through':changed,
    'independent_contract':'Transparent MC symbols reveal an eight-pixel repeated idle byte; other symbols are four-pixel black or background blocks',
    'screenshots':{n:hashlib.sha256((OUT/(n+'.png')).read_bytes()).hexdigest() for n in names},
    'limitations':['Three captured fields at one eight-pixel alignment, not exhaustive DMA timing or physical hardware proof',
                   'Only lower-border composition is checked; text and upper idle band are observed separately']}
(OUT/'pixel-proof.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
