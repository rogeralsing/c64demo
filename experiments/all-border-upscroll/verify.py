#!/usr/bin/env python3
"""Independent full-border pixels and native timing for the own sprite upscroll."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
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
COLORS=(3,14,7,1,10,8,5,4)
TIMING_PHASES={1,7,16,31,32,33}
TIMING_LINES=(0,16,60,76,77,247,249,251,252,253,287)


def text_pixels(art):
    rows=[set() for _ in range(32)]
    for line,text in enumerate(art["lines"]):
        for character,glyph in enumerate(text):
            for y,bits in enumerate(art["glyph_rows"][glyph]):
                rows[line*8+y].update(character*6+x for x in range(5) if bits&(16>>x))
    return rows


def bank_reference(rows,half):
    # Derive byte placement from individual foreground coordinates.
    bank=bytearray(16384)
    for row in range(16):
        for x in rows[half*16+row]:
            column,bit=divmod(x,24)
            byte,lane=divmod(bit,8)
            bank[64*(row*8+column)+53+byte] |= 128>>lane
        bank[row*1024+1016:row*1024+1024]=bytes(range(row*8,row*8+8))
    return bytes(bank)


def image_reference(rows,phase,palette):
    result=Image.new("RGB",(384,272),palette[0])
    pixels=result.load()
    for y in range(272):
        for x in rows[(y+16+phase)%32]:
            color=palette[COLORS[x//24]]
            for position in (8+2*x,9+2*x):
                if position<384: pixels[position,y]=color
    return result


def registers(m):
    response=m.run("r")
    match=re.search(r"^\.;([\da-fA-F]{4})\s+(.*)$",response,re.M)
    values=match[2].split()
    return {"pc":int(match[1],16),"a":int(values[0],16),"x":int(values[1],16),
            "y":int(values[2],16),"raster":int(values[-3]),"cycle":int(values[-2]),
            "clock":int(values[-1])}


def vic(m):
    response=m.run("io d000")
    bank=re.search(r"Video \$([\da-f]+), Bitmap \$([\da-f]+)",response)
    bases=re.search(r"^MCBASE:\s+(.*)$",response,re.M)
    dma=re.search(r"^DMA/dis:\s+(.*)$",response,re.M)
    groups=re.findall(r">C:d0[0-3]0\s+((?:[\da-fA-F]{2}\s+){15}[\da-fA-F]{2})",response)
    data=bytes.fromhex(" ".join(groups))
    return {"mcbase":[int(value,16) for value in re.findall(r"\$([\da-f]+)",bases[1])],
            "dma":dma[1].split(),"matrix":int(bank[1],16),"bitmap_bank":int(bank[2],16),
            "d011":data[0x11],"d016":data[0x16],"d017":data[0x17],
            "sprite_colors":list(data[0x27:0x2f])}


def stop(m,address):
    m.run("delete")
    m.run(f"break {address:04x}")
    m.run("x")
    state=registers(m)
    if state["pc"]!=address: raise AssertionError("Stopped outside the requested instruction.")
    return state


def capture(m,out,name,expected):
    path=out/(name+".png")
    m.run(f'screenshot "{path}" 2')
    actual=Image.open(path).convert("RGB")
    if actual.size!=(384,272): raise AssertionError("Native full-border viewport changed.")
    expected.save(out/(name+"-expected.png"))
    difference=ImageChops.difference(actual,expected)
    first,second=actual.tobytes(),expected.tobytes()
    coordinates=[(pixel%384,pixel//384) for pixel in range(384*272)
                 if first[pixel*3:pixel*3+3]!=second[pixel*3:pixel*3+3]]
    if coordinates: difference.save(out/(name+"-difference.png"))
    return actual,coordinates


def verify(args):
    labels=common.read_labels(HERE/"build/main.sym")
    program=HERE/"build/example.prg"
    prg=program.read_bytes()
    first=int.from_bytes(prg[:2],"little")
    def table(name):
        low,high=labels[name+"Lo"]-first+2,labels[name+"Hi"]-first+2
        return [prg[low+i]+256*prg[high+i] for i in range(312)]
    crunch={line:address for line,address in zip([(77+i)%312 for i in range(312)],table("crunch"))}
    border={line:address for line,address in zip([(77+i)%312 for i in range(312)],table("border"))}
    art=json.loads((HERE/"artwork.json").read_text())
    rows=text_pixels(art)
    banks=[bank_reference(rows,half) for half in (0,1)]
    for half,data in enumerate(banks):
        if (HERE/f"build/bank{half+1}.bin").read_bytes()!=data:
            raise AssertionError("Prepared sprite data differs from the authored glyph coordinates.")
    palette_path=ROOT/"palettes/colodore.vpl"
    palette=[tuple(int(value,16) for value in line.split()[:3])
             for line in palette_path.read_text().splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    out=HERE/"build/verification"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True)
    receipt={"passed":False,"program_sha256":hashlib.sha256(prg).hexdigest(),"frames":[],
             "timing":[],"exact_pixels":0,"source_bank_bytes":0,
             "model":"Authored font coordinates, 2x sprite X expansion, source-row53 and raster+phase modulo32",
             "viewport":{"width":384,"height":272,"first_raster":16}}
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
        sync=stop(m,labels["prelude"])
        if (sync["raster"],sync["cycle"])!=(55,0): raise AssertionError("Bootstrap is not PAL aligned.")
        # The first partial DMA field is warmup, not a claimed complete image.
        stop(m,labels["framePresented"])
        previous_clock=None
        for phase in range(1,34):
            if phase in TIMING_PHASES:
                for line in TIMING_LINES:
                    before=stop(m,crunch[line])
                    m.run("z")
                    after=registers(m)
                    hardware=vic(m)
                    if (after["raster"],after["cycle"])!=(line,15):
                        raise AssertionError("The expansion falling write missed PAL cycle15.")
                    if after["a"]!=0 or after["x"]!=0 or hardware["mcbase"]!=[53]*8 or hardware["dma"]!=["D/d"]*8:
                        raise AssertionError("The eight continuous frozen-row DMA streams are not active.")
                    row=(line+phase)%32
                    expected_bank=0x4000 if row<16 else 0xc000
                    expected_matrix=0x5c00 if row==31 else expected_bank+(row%16)*1024
                    if hardware["matrix"]!=expected_matrix:
                        raise AssertionError("The displayed row uses the wrong sprite-pointer matrix.")
                    if hardware["d011"]&0x10:
                        raise AssertionError("Unexpected screen DMA during the all-border sprite kernel.")
                    begin=stop(m,border[line])
                    if (begin["raster"],begin["cycle"])!=(line,50):
                        raise AssertionError("Side-border RMW did not start on human cycle51.")
                    m.run("z")
                    finish=registers(m)
                    border_state=vic(m)
                    if (finish["raster"],finish["cycle"])!=(line,56) or border_state["d016"]&15!=7:
                        raise AssertionError("Side-border falling write did not finish on human cycle56.")
                    receipt["timing"].append({"phase":phase,"line":line,"before_crunch":before,
                        "after_crunch":after,"vic":hardware,"border_start":begin,"border_end":finish})
            state=stop(m,labels["framePresented"])
            if (state["raster"],state["cycle"])!=(288,56):
                raise AssertionError("The complete full-border picture was captured too early.")
            if previous_clock is not None and state["clock"]-previous_clock!=19656:
                raise AssertionError("The one-pixel upscroll missed a PAL field.")
            previous_clock=state["clock"]
            m.run("bank ram")
            ram=m.memory(out/f"phase-{phase:02d}.bin",0,65535)
            m.run("bank cpu")
            if ram[labels["nextPhase"]]!=phase: raise AssertionError("Native scroll phase differs.")
            runtime_bank3=bytearray(banks[1])
            runtime_bank3[-2:]=labels["secondIRQ"].to_bytes(2,"little")
            for address,expected in ((0x4000,banks[0]),(0xc000,runtime_bank3)):
                if ram[address:address+16384]!=expected:
                    raise AssertionError("Native source bank differs, including RAM under I/O/ROM.")
                receipt["source_bank_bytes"]+=16384
            expected=image_reference(rows,phase,palette)
            image,wrong=capture(m,out,f"phase-{phase:02d}",expected)
            if wrong: raise AssertionError(f"Full-border model rejects {len(wrong)} pixels in phase{phase}.")
            counts={}
            for name,box in {"top":(0,0,384,35),"bottom":(0,235,384,272),
                             "left":(0,35,32,235),"right":(352,35,384,235)}.items():
                counts[name]=sum(pixel!=palette[0] for pixel in image.crop(box).getdata())
            if not all(counts.values()): raise AssertionError("A claimed border has no visible text pixels.")
            receipt["exact_pixels"]+=384*272
            receipt["frames"].append({"phase":phase,"visible_phase":phase%32,
                                     "border_foreground_pixels":counts,**state})
        receipt["negative_controls"]=[]
        # Same-duration INC preserves CSEL=1 instead of opening one side-border line.
        m.run(f"> {border[99]:04x} ee")
        stop(m,labels["framePresented"])
        _,wrong=capture(m,out,"negative-horizontal",image_reference(rows,34,palette))
        if not wrong or any(y not in (83,84) or 32<=x<352 for x,y in wrong):
            raise AssertionError("The horizontal negative did not isolate the two affected side borders.")
        receipt["negative_controls"].append({"kind":"one cycle56 INC in place of DEC",
                                             "different_pixels":len(wrong),"rejected_as_expected":True})
        m.run(f"> {border[99]:04x} ce")
        # Keep DMA/timing intact; black sprite colors must remove every visible pixel.
        m.run("> d027 00 00 00 00 00 00 00 00")
        stop(m,labels["framePresented"])
        blank=Image.new("RGB",(384,272),palette[0])
        _,wrong=capture(m,out,"negative-black-sprites",blank)
        if wrong: raise AssertionError("A non-sprite source contributes visible pixels.")
        receipt["negative_controls"].append({"kind":"all sprite colors black, DMA unchanged",
                                             "exact_black_pixels":384*272,"no_ghostbyte_contribution":True})
        m.run("> d027 "+" ".join(f"{color:02x}" for color in COLORS))
        # A vertical latch matters when the horizontal latch is briefly closed.
        # First probe the gate with correct RSEL: it reopens on the next left edge.
        m.run(f"> {border[251]:04x} ee")
        stop(m,labels["framePresented"])
        _,gate_wrong=capture(m,out,"vertical-gate-correct-rsel",image_reference(rows,36,palette))
        if not gate_wrong or any(y not in (235,236) or 32<=x<352 for x,y in gate_wrong):
            raise AssertionError("The correct vertical latch did not reopen the horizontal gate.")
        # Repeat the identical gate, omitting only the bottom RSEL change.
        m.run(f"> {labels['bottomBorderValue']:04x} 6b")
        stop(m,labels["framePresented"])
        _,wrong=capture(m,out,"negative-vertical",image_reference(rows,37,palette))
        if not wrong or any(y<235 for x,y in wrong) or not any(y>=236 and 32<=x<352 for x,y in wrong):
            raise AssertionError("The vertical negative did not isolate the closed bottom latch.")
        receipt["negative_controls"].append({"kind":"same horizontal gate with/without bottom RSEL change",
            "correct_rsel_gate_pixels":len(gate_wrong),"wrong_rsel_pixels":len(wrong),
            "wrong_rsel_blocks_bottom_interior":True,"rejected_as_expected":True})
        receipt["cadence"]={"pal_clocks_per_field":19656,"pixels_up_per_field":1,
                            "visible_wrap_fields":32,"consecutive_full_fields":33}
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
