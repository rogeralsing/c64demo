#!/usr/bin/env python3
"""Prepare own point endpoints/depth buckets and immutable text artwork.

The C64 receives positions and size counts, never complete animation bitmaps.
"""
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=HERE/'build'
POINTS=[(x,y,z) for z in (-24,-8,8,24) for y in (-24,-8,8,24) for x in (-24,-8,8,24)
        if max(abs(x),abs(y),abs(z))==24]
assert len(POINTS)==56

GLYPHS={
 'A':(14,17,17,31,17,17,17),'B':(30,17,17,30,17,17,30),
 'C':(15,16,16,16,16,16,15),'D':(30,17,17,17,17,17,30),
 'E':(31,16,16,30,16,16,31),'H':(17,17,17,31,17,17,17),
 'L':(16,16,16,16,16,16,31),'O':(14,17,17,17,17,17,14),
 'P':(30,17,17,30,16,16,16),'T':(31,4,4,4,4,4,4),
 'U':(17,17,17,17,17,17,14),
 '1':(4,12,4,4,4,4,14),'2':(14,17,1,2,4,8,31),
 '3':(30,1,1,14,1,1,30),'4':(2,6,10,18,31,2,2),
 '5':(31,16,16,30,1,1,30),'6':(14,16,16,30,17,17,14),
 '7':(31,1,2,4,8,8,8),'8':(14,17,17,14,17,17,14),
 '9':(14,17,17,15,1,1,14)}


def disk(size,x,y):
    dx,dy=2*x-(size-1),2*y-(size-1)
    return 0<=x<size and 0<=y<size and 4*(dx*dx+dy*dy)<=(2*size-1)**2


def frame(phase):
    turn=phase*math.tau/64
    yaw=turn+0.17
    pitch=0.51+0.27*math.sin(turn+0.29)
    roll=0.31*math.sin(2*turn+0.37)
    sx,cx=math.sin(pitch),math.cos(pitch)
    sy,cy=math.sin(yaw),math.cos(yaw)
    sz,cz=math.sin(roll),math.cos(roll)
    records=[]
    for identity,(x,y,z) in enumerate(POINTS):
        x,y=x*cz-y*sz,x*sz+y*cz
        y,z=y*cx-z*sx,y*sx+z*cx
        x,z=x*cy+z*sy,z*cy-x*sy
        size=max(1,min(9,1+math.floor((42-z)*8/84+0.5)))
        px=math.floor(80.125+140*x/(128+z)-(size-1)/2+0.5)
        py=math.floor(64.375+140*y/(128+z)-(size-1)/2+0.5)
        assert 0<=px<=160-size and 0<=py<=128-size,(phase,identity,px,py,size)
        records.append(dict(identity=identity,x=px,y=py,size=size))
    records.sort(key=lambda p:(p['size'],-((p['y']//8)*20+p['x']//8),p['x']%8,p['y']%8,p['identity']))
    return records


def main():
    OUT.mkdir(exist_ok=True)
    frames=[frame(phase) for phase in range(64)]
    data=bytearray();clear=bytearray(1024)
    max_cells=0
    for records in frames:
        counts=[sum(p['size']==size for p in records) for size in range(1,10)]
        data+=bytes(counts)
        data+=bytes(v for p in records for v in (p['x'],p['y']))
        cells=set()
        for p in records:
            for y in range(p['size']):
                for x in range(p['size']):
                    if disk(p['size'],x,y):
                        address=((p['y']+y)//8+4)*40+(p['x']+x)//8+10
                        cells.add(address);clear[address]=1
        max_cells=max(max_cells,len(cells))
    assert len(data)==64*121 and max_cells<192
    font=bytearray(512);screen=bytearray(1024);colors=bytearray([1]*1000+[0]*24)
    codes={char:192+i for i,char in enumerate(GLYPHS)}
    for char,code in codes.items():
        font[(code-192)*8:(code-192)*8+8]=bytes([row<<1 for row in GLYPHS[char]]+[0])
    next_code=192+len(codes)
    horizontal,vertical,corner=next_code,next_code+1,next_code+2
    font[(horizontal-192)*8+3]=255
    font[(vertical-192)*8:(vertical-192)*8+8]=bytes([16]*8)
    font[(corner-192)*8:(corner-192)*8+8]=bytes((0,0,0,255,16,16,16,16))
    next_code+=3
    title='DEPTH BOB CLOUD'
    for i,char in enumerate(title):
        if char!=' ':screen[40+(40-len(title))//2+i]=codes[char]
        colors[40+(40-len(title))//2+i]=3
    for column in range(9,31):
        for row in (3,20):screen[row*40+column]=horizontal;colors[row*40+column]=6
    for row in range(4,20):
        for column in (9,30):screen[row*40+column]=vertical;colors[row*40+column]=6
        for column in range(10,30):colors[row*40+column]=5
    for row in (3,20):
        for column in (9,30):screen[row*40+column]=corner
    for size in range(1,10):
        column=10+(size-1)*2
        screen[21*40+column]=codes[str(size)];colors[21*40+column]=15
        for cy in range((size+7)//8):
            for cx in range((size+7)//8):
                code=next_code;next_code+=1
                for y in range(8):
                    font[(code-192)*8+y]=sum(128>>x for x in range(8) if disk(size,cx*8+x,cy*8+y))
                screen[(22+cy)*40+column+cx]=code;colors[(22+cy)*40+column+cx]=5
    assert next_code<=256
    assert all(not clear[i] or (screen[i]==0 and colors[i]==5) for i in range(1024))
    for name,value in (('frames.bin',data),('clear-map.bin',clear),('static-font.bin',font),
                       ('base-screen.bin',screen),('colors.bin',colors)):
        (OUT/name).write_bytes(value)
    metadata=dict(point_count=56,pose_count=64,frame_bytes=121,depth_sizes=list(range(1,10)),
                  maximum_private_cells=max_cells,selective_clear_cells=sum(clear),static_codes_used=next_code-192,
                  camera=dict(distance=128,focal_length=140,center=[80.125,64.375]),
                  split='Host rotation/projection/depth buckets; C64pixel-phase stamping, glyph allocation/OR merge and clear/publication')
    (OUT/'prepared.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata,indent=2))


if __name__=='__main__':main()
