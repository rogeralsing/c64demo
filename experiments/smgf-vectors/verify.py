#!/usr/bin/env python3
"""Native geometry/priority/gap oracle for the original SMGF panel engine."""
import argparse
from datetime import datetime,timezone
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import shutil
import socket
import subprocess

from PIL import Image,ImageChops

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location("native_c64",ROOT/"verify.py")
common=importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
COLORS=(0,14,4,3,3,4,4,14)
OFFSETS=(9,14,19,24,31)
TIMING_FIELDS={0,4,20,40,60,64}
LINES=(80,88,120,152,184,215,223)


def geometry(phase):
    p=phase*math.pi/8
    y=92+round(4*math.sin(p))
    parameters=(
        ((64,12,0,False),(64,16,0,False),(64,12,.6,True)),
        ((96,8,.7,False),(96,8,2,False),(96,8,0,True)),
        ((168,16,.4,True),(168,16,.5,False),(168,16,1,True)),
        ((232,8,0,True),(232,8,1.8,False),(232,8,.2,True)),
    )
    edges=[[base+round(amplitude*(math.cos if cosine else math.sin)(p+offset))
            for base,amplitude,offset,cosine in group] for group in parameters]
    return (y,y+60,y+120),edges


def edge_x(edge,ys,y):
    y=max(ys[0],min(ys[2],y))
    section=int(y>=ys[1])
    return Fraction(edge[section]) + Fraction((y-ys[section])*(edge[section+1]-edge[section]),
                                               ys[section+1]-ys[section])


def inside(polygon,x,y):
    # A rightward ray with exact rational crossings; no renderer edge stepping.
    hits=0
    for first,second in zip(polygon,polygon[1:]+polygon[:1]):
        x0,y0=first;x1,y1=second
        if y1<y0: x0,y0,x1,y1=x1,y1,x0,y0
        if y0<=y<y1 and (x-x0)*(y1-y0)<(y-y0)*(x1-x0):
            hits+=1
    return bool(hits%2)


def references(phase,palette,colors=COLORS):
    ys,edges=geometry(phase)
    polygons=[list(zip(edges[i],ys))+list(reversed(list(zip(edges[i+1],ys)))) for i in range(3)]
    opaque=Image.new("RGB",(320,200),palette[0])
    sprites=Image.new("RGB",(320,200),palette[0])
    winners=[0]*8
    overlaps=mask_hides=0
    for y in range(80,224):
        active=ys[0]<=y<ys[2]
        positions=[math.ceil(edge_x(edges[i],ys,y)) for i in (3,2,1,0)]+[88,128,152,192]
        for x in range(24,312):
            faces=[i for i,polygon in enumerate(polygons) if inside(polygon,x,y)]
            if len(faces)>1: raise AssertionError("Prepared panels overlap instead of sharing only edges.")
            if faces: opaque.putpixel((x-24,y-51),palette[(3,4,14)[faces[0]]])
            covering=[i for i,left in enumerate(positions) if active and left<=x<left+48]
            if covering:
                winner=min(covering)
                winners[winner]+=1
                overlaps+=int(len(covering)>1)
                mask_hides+=int(winner==0 and len(covering)>1)
                sprites.putpixel((x-24,y-51),palette[colors[winner]])
    if colors==COLORS and ImageChops.difference(opaque,sprites).getbbox():
        raise AssertionError("Sprite priority/gap composition does not equal the three independent polygons.")
    return opaque,sprites,{"winning_pixels":winners,"overlap_pixels":overlaps,"mask_hides_pixels":mask_hides}


def schedule(phase):
    ys,edges=geometry(phase)
    planes=[bytearray() for _ in range(5)]
    for y in range(80,224):
        values=(math.ceil(edge_x(edges[2],ys,y)),math.ceil(edge_x(edges[1],ys,y+1)),
                math.ceil(edge_x(edges[0],ys,y+1)),0x10 if ys[0]<=y+1<ys[2] else 0x20,
                math.ceil(edge_x(edges[3],ys,y+1)))
        for plane,value in zip(planes,values): plane.append(value)
    return b"".join(planes)


def registers(m):
    response=m.run("r")
    match=re.search(r"^\.;([\da-fA-F]{4})\s+(.*)$",response,re.M)
    values=match[2].split()
    return {"pc":int(match[1],16),"a":int(values[0],16),"x":int(values[1],16),
            "raster":int(values[-3]),"cycle":int(values[-2]),"clock":int(values[-1])}


def vic(m):
    text=m.run("io d000")
    values=bytes.fromhex(" ".join(re.findall(
        r">C:d0[0-3]0\s+((?:[\da-fA-F]{2}\s+){15}[\da-fA-F]{2})",text)))
    base=re.search(r"^MCBASE:\s+(.*)$",text,re.M)
    dma=re.search(r"^DMA/dis:\s+(.*)$",text,re.M)
    return {"mcbase":[int(value,16) for value in re.findall(r"\$([\da-f]+)",base[1])],
            "dma":dma[1].split(),"xs":[values[2*i] for i in range(8)],
            "pointers_solid":values[0x18]&0xf0==0x10,"d011":values[0x11],
            "expanded_x":values[0x1d]}


def stop(m,address):
    m.run("delete");m.run(f"break {address:04x}");m.run("x")
    state=registers(m)
    if state["pc"]!=address: raise AssertionError("Unexpected native stop.")
    return state


def capture(m,out,name,expected):
    path=out/(name+".png");m.run(f'screenshot "{path}" 2')
    image=Image.open(path).convert("RGB").crop((32,35,352,235))
    expected.save(out/(name+"-expected.png"))
    diff=ImageChops.difference(image,expected)
    a,b=image.tobytes(),expected.tobytes()
    wrong=sum(a[i:i+3]!=b[i:i+3] for i in range(0,len(a),3))
    if wrong: diff.save(out/(name+"-difference.png"))
    return wrong


def verify(args):
    labels=common.read_labels(HERE/"build/main.sym")
    program=HERE/"build/example.prg";data=program.read_bytes()
    schedules=[schedule(phase) for phase in range(16)]
    if (HERE/"build/poses.bin").read_bytes()!=b"".join(schedules):
        raise AssertionError("Prepared edge commands disagree with exact polygon intersections.")
    palette_path=ROOT/"palettes/colodore.vpl"
    palette=[tuple(int(value,16) for value in line.split()[:3])
             for line in palette_path.read_text().splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    images=[];topology=[]
    for pose in range(16):
        image,_,counts=references(pose,palette)
        images.append(image);topology.append(counts)
    visible_gaps=[sum(item["winning_pixels"][i] for item in topology) for i in range(4,8)]
    if not all(visible_gaps) or not sum(item["mask_hides_pixels"] for item in topology):
        raise AssertionError("The claimed gap sprites or final mask do no visible work.")
    out=HERE/"build/verification"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True)
    receipt={"passed":False,"program_sha256":hashlib.sha256(data).hexdigest(),
             "topology":topology,"visible_gap_pixels":visible_gaps,"fields":[],"timing":[],
             "exact_pixels":0,"live_operand_bytes":0,
             "model":"Exact rational point-in-polygon versus independent eight-sprite priority/rectangle composition"}
    m=None;process=None;log=(out/"vice.log").open("w")
    sock=socket.socket();sock.bind(("127.0.0.1",0));port=sock.getsockname()[1];sock.close()
    try:
        command=common.vice_command(args.vice,program,port,palette_path)
        command[command.index("+warp")]="-warp"
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        m=common.Monitor(common.connect_monitor(process,port));m.run("r");m.run("sidefx off")
        models={labels["kernelARows"]:bytearray(schedules[0]),labels["kernelBRows"]:bytearray(schedules[0])}
        previous_start=None
        for field in range(65):
            pose=field//4%16
            active=labels["kernelARows"] if field//4%2==0 else labels["kernelBRows"]
            inactive=labels["kernelBRows"] if active==labels["kernelARows"] else labels["kernelARows"]
            quarter=field%4
            for plane in range(5):
                first=plane*144+quarter*36
                models[inactive][first:first+36]=schedules[(pose+1)%16][first:first+36]
            if field in TIMING_FIELDS:
                sync=stop(m,labels["prelude"])
                if (sync["raster"],sync["cycle"])!=(55,0): raise AssertionError("Unstable PAL prelude.")
                ys,edges=geometry(pose)
                for line in LINES:
                    address=active+(line-80)*36
                    stop(m,address);m.run("z");falling=registers(m)
                    if (falling["raster"],falling["cycle"])!=(line,15) or falling["a"] or falling["x"]:
                        raise AssertionError("The frozen-row expansion write missed cycle15.")
                    state=stop(m,address+13);hardware=vic(m)
                    if (state["raster"],state["cycle"])!=(line,27) or hardware["mcbase"]!=[53]*8 or hardware["dma"]!=["D/d"]*8:
                        raise AssertionError("Native sprite stretch/DMA or edge-write timing differs.")
                    if hardware["expanded_x"]!=255 or hardware["d011"]&16:
                        raise AssertionError("Unexpected sprite width or badline-enabled display.")
                    if line>80:
                        positions=[math.ceil(edge_x(edges[i],ys,line)) for i in (3,2,1,0)]+[88,128,152,192]
                        if hardware["xs"]!=positions: raise AssertionError("Native X coordinates do not follow polygon boundaries.")
                        if hardware["pointers_solid"]!=(ys[0]<=line<ys[2]):
                            raise AssertionError("Native solid/blank sprite row gate differs.")
                    receipt["timing"].append({"field":field,"line":line,"falling":falling,"edge_write":state,"vic":hardware})
                job_start=stop(m,labels["afterKernel"])
            complete=stop(m,labels["framePresented"])
            if not 251<=complete["raster"]<312: raise AssertionError("Schedule patch job missed its field deadline.")
            field_start=complete["clock"]-complete["raster"]*63-complete["cycle"]
            if previous_start is not None and field_start-previous_start!=19656:
                raise AssertionError("Display missed a PAL field.")
            previous_start=field_start
            m.run("bank ram");ram=m.memory(out/f"field-{field:03d}.bin",0,65535);m.run("bank cpu")
            if ram[labels["fieldCounter"]]!=field or ram[labels["activePose"]]!=pose or ram[labels["patchRow"]]!=(quarter+1)*36:
                raise AssertionError("Native schedule publication differs from four-field model.")
            for address,expected in models.items():
                actual=bytes(ram[address+row*36+offset] for offset in OFFSETS for row in range(144))
                if actual!=expected: raise AssertionError("Native active/inactive raster operands differ.")
                receipt["live_operand_bytes"]+=len(actual)
            if ram[0x4000:0x4080]!=bytes(53)+bytes([255]*3)+bytes(72):
                raise AssertionError("Sprite data changed into software-rendered pixels.")
            wrong=capture(m,out,f"field-{field:03d}",images[pose])
            if wrong: raise AssertionError(f"Native polygon image has {wrong} wrong pixels in field{field}.")
            receipt["exact_pixels"]+=64000
            record={"field":field,"pose":pose,"active_rows":active,"complete":complete,"field_start":field_start}
            if field in TIMING_FIELDS: record["patch_job_clocks"]=complete["clock"]-job_start["clock"]
            receipt["fields"].append(record)
        # Keep geometry and DMA intact; remove only the four colored gap underlays.
        m.run("> d02b 00 00 00 00")
        stop(m,labels["framePresented"])
        _,gap_expected,_=references(0,palette,COLORS[:4]+(0,0,0,0))
        if capture(m,out,"negative-black-gaps",gap_expected):
            raise AssertionError("Hardware gap contribution differs from its independent model.")
        gap_difference=ImageChops.difference(gap_expected,images[0])
        gap_pixels=sum(a!=b for a,b in zip(gap_expected.getdata(),images[0].getdata()))
        if not gap_difference.getbbox(): raise AssertionError("Gap removal has no visible consequence.")
        m.run("> d02b 03 04 04 0e")
        m.run("> d027 02")
        stop(m,labels["framePresented"])
        _,mask_expected,_=references(0,palette,(2,)+COLORS[1:])
        if capture(m,out,"negative-red-right-mask",mask_expected):
            raise AssertionError("Right-mask priority differs from its independent model.")
        mask_pixels=sum(a!=b for a,b in zip(mask_expected.getdata(),images[0].getdata()))
        if not mask_pixels: raise AssertionError("The final mask has no visible consequence.")
        receipt["negative_controls"]={"black_gap_pixels_rejected":gap_pixels,
                                       "red_mask_pixels_rejected":mask_pixels,
                                       "both_hardware_counterfactual_images_exact":True}
        receipt["cadence"]={"pal_clocks_per_field":19656,"new_pose_fields":4,
                           "nominal_new_poses_per_second":12.5,"consecutive_fields":65}
        receipt["passed"]=True
    except Exception as error:
        receipt["error"]=str(error);raise
    finally:
        if m:
            (out/"monitor.txt").write_text("\n".join(m.transcript));m.connection.close()
        if process:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill();process.wait()
        log.close();(out/"verification.json").write_text(json.dumps(receipt,indent=2)+"\n")
        print(out/"verification.json",flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vice",default=shutil.which("x64sc"))
    verify(parser.parse_args())
