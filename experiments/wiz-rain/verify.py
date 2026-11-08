#!/usr/bin/env python3
"""Native proof of WIZ address wrap and slower C64 gradient/lighting updates."""
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

from PIL import Image, ImageChops

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location("native_c64",ROOT/"verify.py")
common=importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
LIGHTS=((2,0),(2,1),(2,2),(1,2),(0,2),(-1,2),(-2,2),(-2,1),
        (-2,0),(-2,-1),(-2,-2),(-1,-2),(0,-2),(1,-2),(2,-2),(2,-1))
CAPTURES={0,1,2,4,7,8,13,14,15,16,24,32,48,64,80,96,112,128}
TIMINGS={0,1,2,3,4,7,8,15,31,127,128}


def height_reference():
    # Accumulate by destination rather than the producer's sequential painting.
    contributions=[[] for _ in range(1024)]
    for age in range(16):
        for y in range(-7,8):
            for x in range(-8,9):
                radius=math.sqrt(x*x+2.25*y*y)
                distance=radius-(.4+5.2*age/16)
                amplitude=10*(16-age)/16
                contributions[(64*age+x+40*y)&1023].append(
                    amplitude*math.sin(math.pi*distance)/math.exp((distance/1.1)**2))
    return bytes(max(0,min(31,math.floor(15+sum(values)+.5))) for values in contributions)


def lighting(height,stage):
    x,y=LIGHTS[stage]
    return bytes(max(0,min(15,(32+x*(height[(i+1)&1023]-height[(i-1)&1023])
                              +y*(height[(i+40)&1023]-height[(i-40)&1023]))//4))
                 for i in range(1024))


def font_reference():
    thresholds=((0,8,2,10),(12,4,14,6),(3,11,1,9),(15,7,13,5))
    result=bytearray(2048)
    for level in range(16):
        for row in range(8):
            for lane in range(4):
                value=min(3,(16*level+5*thresholds[row%4][lane]+2.5)//80)
                result[level*8+row] |= int(value) << (6-2*lane)
    return bytes(result)


def image_reference(matrix,font,view,palette):
    image=Image.new("RGB",(320,200),palette[0])
    pixels=image.load()
    for y in range(45,200):
        if y>=197:
            for x in range(320): pixels[x,y]=palette[6]
            continue
        row,scan=divmod(y-45,8)
        for column in range(40):
            glyph=matrix[(view+40*row+column)&1023]
            packed=font[glyph*8+scan]
            for lane in range(4):
                color=palette[(6,14,3,1)[(packed>>(6-2*lane))&3]]
                pixels[8*column+lane*2,y]=color
                pixels[8*column+lane*2+1,y]=color
    return image


def registers(m):
    response=m.run("r")
    match=re.search(r"^\.;([\da-fA-F]{4})\s+(.*)$",response,re.M)
    values=match[2].split()
    return {"pc":int(match[1],16),"raster":int(values[-3]),"cycle":int(values[-2]),
            "clock":int(values[-1])}


def vic(m):
    response=m.run("io d000")
    counters=re.search(r"VC \$([\da-f]+), VCBASE \$([\da-f]+), VMLI\s+(\d+)",response)
    scroll=re.search(r"Scroll X/Y: (\d+)/(\d+), RC (\d+), Idle: (\d+)",response)
    mode=re.search(r"Mode: (.*)",response)[1]
    pointers=re.search(r"Video \$([\da-f]+), (?:Charset|Bitmap) \$([\da-f]+)",response)
    return {"vc":int(counters[1],16),"vcbase":int(counters[2],16),
            "rc":int(scroll[3]),"idle":int(scroll[4]),"yscroll":int(scroll[2]),
            "matrix":int(pointers[1],16),"graphics":int(pointers[2],16),"mode":mode}


def stop(m,address):
    m.run("delete")
    m.run(f"break {address:04x}")
    m.run("x")
    state=registers(m)
    if state["pc"]!=address: raise AssertionError("Stopped outside the requested instruction.")
    return state


def screenshot(m,out,name,expected):
    path=out/(name+".png")
    m.run(f'screenshot "{path}" 2')
    native=Image.open(path).convert("RGB").crop((32,35,352,235))
    expected.save(out/(name+"-expected.png"))
    diff=ImageChops.difference(native,expected)
    actual_bytes,expected_bytes=native.tobytes(),expected.tobytes()
    count=sum(actual_bytes[i:i+3]!=expected_bytes[i:i+3]
              for i in range(0,320*200*3,3))
    if count: diff.save(out/(name+"-difference.png"))
    return count


def verify(args):
    labels=common.read_labels(HERE/"build/main.sym")
    program=HERE/"build/example.prg"
    prg=program.read_bytes()
    base=int.from_bytes(prg[:2],"little")
    def table(name,length):
        lo,hi=labels[name+"Lo"]-base+2,labels[name+"Hi"]-base+2
        return [prg[lo+i]+256*prg[hi+i] for i in range(length)]
    falling=table("vspFalling",40)
    crunch=table("crunch",29)
    height=height_reference()
    font=font_reference()
    if (HERE/"build/height.bin").read_bytes()!=height: raise AssertionError("Height equation mismatch.")
    if (HERE/"build/font.bin").read_bytes()!=font: raise AssertionError("Font coverage mismatch.")
    fields=[lighting(height,stage) for stage in range(16)]
    if (HERE/"build/initial.bin").read_bytes()!=fields[0]: raise AssertionError("Initial light mismatch.")
    palette_path=ROOT/"palettes/colodore.vpl"
    palette=[tuple(int(v,16) for v in line.split()[:3])
             for line in palette_path.read_text().splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    out=HERE/"build/verification"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True)
    receipt={"passed":False,"program_sha256":hashlib.sha256(prg).hexdigest(),"fields":[],
             "timing":[],"crunch_slots":[],"exact_pixels":0,"matrix_bytes":0,
             "model":"Independent ripple equation, finite differences, signed dot product and VIC10-bit address model"}
    m=None
    process=None
    log=(out/"vice.log").open("w")
    sock=socket.socket();sock.bind(("127.0.0.1",0));port=sock.getsockname()[1];sock.close()
    try:
        command=common.vice_command(args.vice,program,port,palette_path)
        command[command.index("+warp")]="-warp"
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        m=common.Monitor(common.connect_monitor(process,port))
        m.run("r")
        m.run("sidefx off")
        matrices={0x400:bytearray(fields[0]),0x800:bytearray(fields[0])}
        previous_start=None
        for field in range(129):
            phase=field%16
            view=(120+64*phase)&1023
            x=(-64*phase)%40
            n=(64*phase+x)//40
            stage=(field//8)%16
            active=0x400 if stage%2==0 else 0x800
            work=active^0xc00
            chunk=field%8
            matrices[work][128*chunk:128*(chunk+1)]=fields[(stage+1)%16][128*chunk:128*(chunk+1)]
            if field in TIMINGS:
                sync=stop(m,labels["stableStart"])
                if (sync["raster"],sync["cycle"])!=(47,3): raise AssertionError("Unstable AGSP IRQ phase.")
                before=stop(m,falling[x])
                if (before["raster"],before["cycle"])!=(48,8+x): raise AssertionError("VSP delay did not reach the required PAL cycle.")
                m.run("z")
                after=registers(m)
                if (after["raster"],after["cycle"])!=(48,14+x): raise AssertionError("VSP falling RMW write timing changed.")
                receipt["timing"].append({"field":field,"vsp_x":x,"before_dec":before,"after_dec":after})
            if field==15:
                for slot,address in enumerate(crunch):
                    state=stop(m,address)
                    hardware=vic(m)
                    expected=(120-x+40*min(slot,n))&1023
                    if (state["raster"],state["cycle"])!=(67+slot,4) or hardware["vcbase"]!=expected or hardware["rc"]!=7:
                        raise AssertionError("Linecrunch did not advance/hold the actual VIC counter as specified.")
                    receipt["crunch_slots"].append({"slot":slot,**state,**hardware})
            display=stop(m,labels["displayStart"])
            hardware=vic(m)
            if (display["raster"],display["cycle"])!=(96,4) or hardware["vcbase"]!=view:
                raise AssertionError(f"Wrong native AGSP viewpoint at field{field}: {hardware}.")
            field_start=display["clock"]-96*63-4
            if previous_start is not None and field_start-previous_start!=19656:
                raise AssertionError("Fast viewpoint motion missed a PAL field.")
            previous_start=field_start
            if hardware["matrix"]!=active: raise AssertionError("Wrong completed lighting bank published.")
            if field in TIMINGS:
                beginning=stop(m,labels["lightChunkStart"])
                enabled=vic(m)
                if enabled["graphics"]!=0x3000 or enabled["mode"]!="Multicolor Text (ECM/BMM/MCM=0/0/1)":
                    raise AssertionError("Visible characters do not use the original luminance font.")
                if enabled["rc"]!=(beginning["raster"]-96)%8:
                    raise AssertionError("Display RC does not follow the fixed viewport phase.")
                end=stop(m,labels["lightChunkFinished"])
                if end["raster"]>=256: raise AssertionError("Lighting job exceeded its visible-field budget.")
                receipt["timing"][-1]["light_chunk_start"]=beginning
                receipt["timing"][-1]["light_chunk_end"]=end
                receipt["timing"][-1]["light_chunk_clocks"]=end["clock"]-beginning["clock"]
            complete=stop(m,labels["framePresented"])
            m.run("bank ram")
            ram=m.memory(out/f"field-{field:03d}.bin",0,65535)
            m.run("bank cpu")
            if ram[labels["phase"]]!=phase or ram[labels["activeLight"]]!=stage:
                raise AssertionError("Native movement/light stages differ from the independent schedule.")
            for address,expected in matrices.items():
                if ram[address:address+1024]!=expected:
                    raise AssertionError(f"C64 finite-difference lighting differs at field{field}/matrix{address:04x}.")
                receipt["matrix_bytes"]+=1024
            if ram[labels["heightAtlas"]:labels["heightAtlas"]+1024]!=height or ram[0x3000:0x3800]!=font:
                raise AssertionError("The height atlas or glyph source changed during viewpoint motion.")
            if field in CAPTURES:
                expected=image_reference(fields[stage],font,view,palette)
                wrong=screenshot(m,out,f"field-{field:03d}",expected)
                if wrong: raise AssertionError(f"Independent full-image oracle rejects {wrong} pixels in field{field}.")
                receipt["exact_pixels"]+=64000
            receipt["fields"].append({"field":field,"phase":phase,"light_stage":stage,
                 "viewpoint":view,"vsp_x":x,"linecrunch":n,"active_matrix":active,
                 "display":display,"complete":complete,"field_start":field_start})
        receipt["negative_controls"]=[]
        for field,label,value in ((129,"viewX",0),(130,"viewCrunch",0)):
            phase=field%16
            m.run(f"> {labels[label]+phase:04x} {value:02x}")
            stop(m,labels["displayStart"])
            hardware=vic(m)
            expected_view=(120+phase*64)&1023
            if hardware["vcbase"]==expected_view: raise AssertionError("Negative AGSP control did not alter the VIC viewpoint.")
            stop(m,labels["framePresented"])
            wrong=screenshot(m,out,f"negative-{label}",image_reference(fields[0],font,expected_view,palette))
            if not wrong: raise AssertionError("Negative AGSP control escaped the pixel oracle.")
            receipt["negative_controls"].append({"synthetic_live_ram_table":label,"field":field,
                "expected_view":expected_view,"actual_view":hardware["vcbase"],
                "different_pixels":wrong,"rejected_as_expected":True})
        receipt["cadence"]={"viewpoint_fields":1,"pal_clocks_per_field":19656,
                            "full_bump_light_fields":8,"cells_computed_per_field":128,
                            "consecutive_fields":129}
        receipt["passed"]=True
    except Exception as error:
        receipt["error"]=str(error)
        raise
    finally:
        if m:
            (out/"monitor.txt").write_text("\n".join(m.transcript))
            m.connection.close()
        if process:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill();process.wait()
        log.close()
        (out/"verification.json").write_text(json.dumps(receipt,indent=2)+"\n")
        print(out/"verification.json",flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vice",default=shutil.which("x64sc"))
    verify(parser.parse_args())
