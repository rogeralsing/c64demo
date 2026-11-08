#!/usr/bin/env python3
"""Audit real nested call/skip/return events and independently rendered counters."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
from PIL import Image, ImageChops

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=HERE / "build/verification"
EVENT=re.compile(r"#\d+ \(Trace\s+exec [^\n]+\n\.C:([0-9a-fA-F]{4})[^\n]*?"
                 r"- A:([0-9a-fA-F]{2}) X:([0-9a-fA-F]{2}) Y:([0-9a-fA-F]{2}) "
                 r"SP:([0-9a-fA-F]{2})[^\n]*?\s(\d+)\n")


def predicted_screen(initial,starts,finishes,skips,fast,fields,depth,maximum):
    screen=bytearray(initial)
    def number(offset,value):
        screen[offset:offset+4]=f"{value&65535:04X}".encode("ascii")
    for site in range(2):
        for offset,value in ((8,starts[site]),(17,finishes[site]),(26,skips[site])):
            number((6+site*2)*40+offset,value)
    screen[11*40+14]=48+depth
    screen[11*40+27]=48+maximum
    number(20*40+10,fast)
    number(20*40+24,fields)
    return screen


def rendered(screen,font,palette):
    image=Image.new("RGB",(320,200))
    image.putdata([palette[15 if font[screen[(y//8)*40+x//8]*8+y%8] & (128>>(x%8)) else 0]
                   for y in range(200) for x in range(320)])
    return image


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT / "verification.json").unlink(missing_ok=True)
    spec=importlib.util.spec_from_file_location("native_common",ROOT / "verify.py")
    common=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(common)
    labels=common.read_labels(HERE / "build/main.sym")
    program=HERE / "build/example.prg"
    font=(HERE / "build/font.bin").read_bytes()
    initial=(HERE / "build/screen.bin").read_bytes()
    palette_path=ROOT / "palettes/colodore.vpl"
    palette=[tuple(int(v,16) for v in line.split()[:3]) for line in palette_path.read_text().splitlines()
             if line.strip() and not line.startswith("#")]
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1",0))
        port=reserve.getsockname()[1]
    command=common.vice_command(shutil.which("x64sc"),program,port,palette_path)
    command += ["-limitcycles","15000000"]
    starts,finishes,skips=[0,0],[0,0],[0,0]
    active,events,fields,pictures=[],[],[],[]
    expected_matrix=bytearray(initial)
    process,monitor,maximum=None,None,0
    try:
        with (OUT / "vice.log").open("w") as log:
            process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            with common.connect_monitor(process,port) as connection:
                monitor=common.Monitor(connection)
                monitor.run("r")
                monitor.run(f"break {labels['frameTick']:04x}")
                monitor.run("x")
                for name in ("workStarted","siteZeroCompleted","siteOneCompleted","skipZero","skipOne"):
                    monitor.run(f"trace exec {labels[name]:04x}")
                for index in range(101):
                    pc,line,clock=monitor.registers()
                    assert pc==labels["frameTick"] and line==32
                    monitor.run("bank ram")
                    memory=monitor.memory(OUT / f"field-{index:03d}.ram",0,65535)
                    assert memory[0x2000:0x2800]==font
                    assert memory[0x0400:0x0800]==expected_matrix
                    assert int.from_bytes(memory[labels["frameCounter"]:labels["frameCounter"]+2],"little")==index
                    fast=int.from_bytes(memory[labels["fastJobs"]:labels["fastJobs"]+2],"little")
                    assert fast==7*index
                    for name,model in (("starts",starts),("finishes",finishes),("skips",skips)):
                        for site in range(2):
                            value=memory[labels[name]+site]+256*memory[labels[name+"Hi"]+site]
                            assert value==model[site],(index,name,site,value,model[site])
                    flags=[memory[labels[name]+1] for name in ("guardZero","guardOne")]
                    assert flags==[int(site in active) for site in range(2)]
                    assert memory[labels["activeDepth"]]==len(active)
                    assert memory[labels["maximumDepth"]]==maximum
                    if index:
                        path=OUT / f"field-{index:03d}.png"
                        monitor.run(f'screenshot "{path}" 2')
                        image=Image.open(path).convert("RGB").crop((32,35,352,235))
                        reference=rendered(expected_matrix,font,palette)
                        if ImageChops.difference(image,reference).getbbox():
                            reference.save(OUT / "expected-failed.png")
                            raise AssertionError(f"Native counter image differs at field {index}")
                        pictures.append(image)
                    fields.append({"index":index,"clock":clock,"starts":starts.copy(),
                                   "finishes":finishes.copy(),"skips":skips.copy(),
                                   "active_sites":active.copy(),"guard_flags":flags,"fast_jobs":fast})
                    expected_matrix=predicted_screen(initial,starts,finishes,skips,fast+1,index+1,len(active),maximum)
                    if index<100:
                        response=monitor.run("x")
                        (OUT / f"interval-{index:03d}.txt").write_text(response)
                        for pc,a,x,y,sp,clock in EVENT.findall(response):
                            pc,x,sp,clock=int(pc,16),int(x,16),int(sp,16),int(clock)
                            assert sp>=0xdf
                            if pc==labels["workStarted"]:
                                assert x in (0,1) and x not in active
                                active.append(x)
                                starts[x]+=1
                                maximum=max(maximum,len(active))
                                kind,site="start",x
                            elif pc in (labels["siteZeroCompleted"],labels["siteOneCompleted"]):
                                site=int(pc==labels["siteOneCompleted"])
                                assert active and active[-1]==site,(active,site)
                                active.pop()
                                finishes[site]+=1
                                kind="finish"
                            else:
                                assert pc in (labels["skipZero"],labels["skipOne"])
                                site=int(pc==labels["skipOne"])
                                assert site in active
                                skips[site]+=1
                                kind="skip"
                            events.append({"kind":kind,"site":site,"clock":clock,"sp":sp,"active_sites":active.copy()})
                assert maximum==2 and all(n>2 for n in finishes) and all(n>20 for n in skips)
                assert any(e["kind"]=="skip" and len(e["active_sites"])==2 for e in events)
                connection.sendall(b"quit\n")
                process.wait(timeout=5)
        common.save_animation(pictures,OUT / "nested-irq-guards.gif",60)
    finally:
        if monitor:
            (OUT / "monitor.txt").write_text("\n".join(monitor.transcript))
        if process and process.poll() is None:
            process.terminate()
        if process:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    assert process.returncode==0
    intervals=[b["clock"]-a["clock"] for a,b in zip(fields,fields[1:])]
    assert all(abs(n-19656)<16 for n in intervals)
    proof={"passed":True,"program_sha256":hashlib.sha256(program.read_bytes()).hexdigest(),
           "fields":fields,"native_events":events,"maximum_same_routine_concurrency":maximum,
           "starts":starts,"finishes":finishes,"skips":skips,"independent_fast_jobs":700,
           "native_viewport_pixels":len(pictures)*64000,"field_intervals":intervals,"vice_exit_code":process.returncode,
           "contract":"One guard per call site; same-site reentry skipped while a different site may overlap the same routine"}
    (OUT / "verification.json").write_text(json.dumps(proof,indent=2)+"\n")
    print(json.dumps({"passed":True,"fields":100,"native_events":len(events),"starts":starts,
                      "finishes":finishes,"skips":skips,"concurrency":maximum,
                      "native_pixels":proof["native_viewport_pixels"],"sha256":proof["program_sha256"]}))


if __name__=="__main__":
    main()
