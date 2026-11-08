#!/usr/bin/env python3
"""Full native20-line interleave and exact per-sprite pointer deadline proof."""
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import subprocess

from PIL import Image,ImageChops

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result
shared=module("native_c64",ROOT/"verify.py")
layout=module("interleave_layout",HERE.parent/"sprite-interleave/verify.py")
DEFAULT_HASH="94709e5bea31d7d9a10cb4c0d4551a059d4a3c6fa5f85e5a0b4a3496e08fe16e"
TRACE=re.compile(r"#\d+ \(Trace store ([0-9a-f]{4})\)\s+(\d+)/[^\n]*\n"
                 r"\.C:([0-9a-f]{4})[^\n]*\b(STA|STX|SAX)\b[^\n]* A:([0-9a-f]{2}) X:([0-9a-f]{2})",re.I)
STORE_ORDER=(0,4,1,5,2,6,3,7)


def events(response):
    result=[]
    for address,raster,pc,opcode,a,x in TRACE.findall(response):
        a,x=int(a,16),int(x,16)
        result.append({"address":int(address,16),"raster":int(raster),"pc":int(pc,16),
                       "value":a&x if opcode.upper()=="SAX" else a if opcode.upper()=="STA" else x})
    return result


def registers(m):
    response=m.run("r");match=re.search(r"^\.;([\da-fA-F]{4})\s+(.*)$",response,re.M)
    values=match[2].split()
    return {"pc":int(match[1],16),"raster":int(values[-3]),"cycle":int(values[-2]),"clock":int(values[-1])}


def stop(m,address):
    m.run("delete");m.run(f"break {address:04x}");m.run("x")
    result=registers(m)
    if result["pc"]!=address: raise AssertionError("Unexpected native stop.")
    return result


def capture(m,out,name,patch,phase,palette):
    path=out/(name+".png");m.run(f'screenshot "{path}" 2')
    native=Image.open(path).convert("RGB")
    if native.size!=(384,272): raise AssertionError("Unexpected full native viewport.")
    expected=Image.new("RGB",native.size,palette[0]);expected.paste(patch,(96+phase,49))
    difference=ImageChops.difference(native,expected)
    a,b=native.tobytes(),expected.tobytes()
    coordinates=[(i%384,i//384) for i in range(384*272) if a[3*i:3*i+3]!=b[3*i:3*i+3]]
    if coordinates:
        expected.save(out/(name+"-expected.png"));difference.save(out/(name+"-difference.png"))
    return coordinates


def main():
    labels=shared.read_labels(HERE/"build/main.sym")
    program=HERE/"build/example.prg";prg=program.read_bytes()
    base=int.from_bytes(prg[:2],"little")
    low,high=labels["pointerStoreLo"]-base+2,labels["pointerStoreHi"]-base+2
    poststores=[prg[low+i]+256*prg[high+i] for i in range(8)]
    packed,duplicates=layout.packed_reference(20,9)
    palette_path=ROOT/"palettes/colodore.vpl"
    palette=[tuple(int(value,16) for value in line.split()[:3])
             for line in palette_path.read_text().splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    patch=Image.new("RGB",(192,168))
    patch.putdata([palette[layout.COLORS[x//24]] if layout.image_byte(x//8,y)&(128>>(x%8))
                   else palette[0] for y in range(168) for x in range(192)])
    out=HERE/"build/verification"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True)
    default=HERE.parent/"sprite-interleave/build/example.prg"
    if hashlib.sha256(default.read_bytes()).hexdigest()!=DEFAULT_HASH:
        raise AssertionError("The default16-line assembled program changed.")
    default_packed,_=layout.packed_reference()
    default_prg=default.read_bytes()
    default_base=int.from_bytes(default_prg[:2],"little")
    first=0x2000-default_base+2
    if default_prg[first:first+len(default_packed)]!=default_packed:
        raise AssertionError("Shared verifier defaults changed the retained16-line data contract.")
    receipt={"passed":False,"program_sha256":hashlib.sha256(prg).hexdigest(),
             "default16_program_sha256":DEFAULT_HASH,"fields":[],"pointer_deadlines":[],
             "exact_pixels":0,"packed_bytes":0,"pointer_stores_checked":0,"y_stores_checked":0,
             "duplicated_overlap_byte_destinations":duplicates,"trace_y_lead_lines":[],
             "timing_method":"Instruction post-store checkpoints, not deferred memory-watchpoint timestamps"}
    m=None;process=None;log=(out/"vice.log").open("w")
    sock=socket.socket();sock.bind(("127.0.0.1",0));port=sock.getsockname()[1];sock.close()
    try:
        command=shared.vice_command(os.environ.get("VICE","x64sc"),program,port,palette_path)
        command[command.index("+warp")]="-warp"
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        m=shared.Monitor(shared.connect_monitor(process,port));m.run("r");m.run("sidefx off")
        m.run(f"break {labels['framePresented']:04x}")
        previous_start=None
        for index in range(33):
            response=m.run("x");state=registers(m)
            field_start=state["clock"]-state["raster"]*63-state["cycle"]
            if previous_start is not None and field_start-previous_start!=19656:
                raise AssertionError("The horizontal motion missed a PAL field.")
            previous_start=field_start
            m.run("bank ram");ram=m.memory(out/f"field-{index:02d}.bin",0,65535);m.run("bank cpu")
            phase=index%32
            if int.from_bytes(ram[labels["frameCounter"]:labels["frameCounter"]+2],"little")!=index+1 or ram[labels["phaseUsed"]]!=phase:
                raise AssertionError("Native motion state differs.")
            if ram[0x2000:0x3200]!=packed: raise AssertionError("Rolled/duplicated source data differs from row ownership.")
            receipt["packed_bytes"]+=len(packed)
            if ram[0x7f8:0x800]!=bytes(range(0xc0,0xc8)):
                raise AssertionError("The last pointer group was not consumed.")
            if ram[0x400:0x7e8]!=bytes(1000) or ram[0x3800:0x3808]!=bytes(8):
                raise AssertionError("Background storage is not blank.")
            vic=m.memory(out/"vic.bin",0xd000,0xd03f)
            if vic[0x15]!=255 or vic[0x18]&0xfe!=0x1e or vic[0x11]&0x7f!=0x1b or vic[0x16]&0x1f!=8:
                raise AssertionError("Native display mode differs.")
            if any(vic[address] for address in (0x17,0x1b,0x1c,0x1d)):
                raise AssertionError("Sprites are not normal-height hires.")
            if vic[0x10]!=(0xc0 if phase>=24 else 0x80):
                raise AssertionError("Horizontal MSB transition differs.")
            for sprite in range(8):
                if vic[2*sprite]!=(88+24*sprite+phase)%256 or vic[2*sprite+1]!=211:
                    raise AssertionError("Sprite positions or21-line restarts differ.")
            if index:
                stores=events(response)
                pointers=[event for event in stores if 0x7f8<=event["address"]<=0x7ff]
                ys=[event for event in stores if 0xd001<=event["address"]<=0xd00f and event["address"]%2]
                expected=[(0x7f8+sprite,0x80+8*block+sprite) for block in range(9) for sprite in STORE_ORDER]
                if [(e["address"],e["value"]) for e in pointers]!=expected:
                    raise AssertionError("Pointer event values/order differ.")
                if [(e["address"],e["value"]) for e in ys]!=[
                    (0xd001+2*sprite,64+21*restart) for restart in range(8) for sprite in range(8)]:
                    raise AssertionError("Y event values/order differ.")
                for event in ys:
                    if event["value"]!=64:
                        lead=event["value"]-event["raster"]
                        if lead<=0: raise AssertionError("A Y update missed its requested restart.")
                        receipt["trace_y_lead_lines"].append(lead)
                receipt["pointer_stores_checked"]+=len(pointers);receipt["y_stores_checked"]+=len(ys)
            if capture(m,out,f"field-{index:02d}",patch,phase,palette):
                raise AssertionError(f"Full sprite DMA pixels differ in motion phase{phase}.")
            receipt["exact_pixels"]+=384*272
            receipt["fields"].append({"index":index,"phase":phase,"field_start":field_start,**state})
            if index==0:
                m.run("trace store 07f8 07ff");m.run("trace store d001 d00f")
        m.run("delete")
        # Cover five motion phases and both D010 regimes using exact CPU stops.
        selected={33,40,48,56,64}
        for index in range(33,65):
            if index in selected:
                for block in range(1,9):
                    entry=stop(m,labels["pointerIRQ"])
                    boundary=64+20*block
                    for order,address in enumerate(poststores):
                        state=stop(m,address)
                        sprite=STORE_ORDER[order]
                        # End-of-instruction state is the cycle after its last write.
                        write_clock=state["clock"]-1
                        start=state["clock"]-state["raster"]*63-state["cycle"]
                        def pointer_fetch(line):
                            offset=(57,59,61,63,65,67,69,71)[sprite]
                            return start+line*63+offset
                        old_fetch=pointer_fetch(boundary-1)
                        new_fetch=pointer_fetch(boundary+1)
                        if not old_fetch<=write_clock<new_fetch:
                            raise AssertionError("A pointer write escaped its one-shared-row ownership interval.")
                        values=m.memory(out/"pointer.bin",0x7f8,0x7ff)
                        if values[sprite]!=0x80+8*block+sprite:
                            raise AssertionError("Post-store pointer memory differs.")
                        receipt["pointer_deadlines"].append({"index":index,"block":block,"sprite":sprite,
                            "boundary":boundary,"irq_entry":entry,"after_store":state,
                            "write_clock":write_clock,"old_nonshared_fetch":old_fetch,
                            "new_nonshared_fetch":new_fetch,"deadline_margin":new_fetch-write_clock})
            state=stop(m,labels["framePresented"])
            if index in selected:
                if capture(m,out,f"timing-field-{index:02d}",patch,index%32,palette):
                    raise AssertionError("Timed pointer field differs from the independent full image.")
                receipt["exact_pixels"]+=384*272
        # Break only the new block's copy of the shared source row20.
        corrupt=0x2000+512+3*20
        m.run(f"> {corrupt:04x} {packed[corrupt-0x2000]^255:02x}")
        stop(m,labels["framePresented"])
        wrong=capture(m,out,"negative-missing-shared-copy",patch,1,palette)
        if len(wrong)!=8 or any(y!=69 or not 97<=x<105 for x,y in wrong):
            raise AssertionError("The shared-row negative did not isolate its eight real DMA pixels.")
        receipt["negative_control"]={"one_new_shared_copy_corrupted":corrupt,
                                     "wrong_pixels":len(wrong),"rejected_as_expected":True}
        receipt["cadence"]={"pal_clocks_per_field":19656,"horizontal_pixels_per_field":1,
                           "motion_period_fields":32}
        receipt["passed"]=True
    except Exception as error:
        receipt["error"]=str(error);raise
    finally:
        if m:
            (out/"monitor.txt").write_text("\n".join(m.transcript));m.connection.close()
        if process:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        log.close();(out/"verification.json").write_text(json.dumps(receipt,indent=2)+"\n")
        print(out/"verification.json",flush=True)


if __name__=="__main__":
    main()
