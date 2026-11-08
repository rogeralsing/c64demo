#!/usr/bin/env python3
"""Verify the bank-$4000 bitmap/idle/sprite scene and its two byte addresses."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
from PIL import Image, ImageChops

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "build/verification"
PATTERNS = (0x81,0xc0,0x60,0x30,0x18,0x0c,0x06,0x03)


def module(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def expected_image(bitmap,masks,phase,palette,idle=None):
    idle = PATTERNS[phase%8] if idle is None else idle
    pixels = [palette[0]]*(384*272)
    for y in range(272):
        for x in range(320):
            color = 14
            if 24<=y<35:
                color = 0
            elif 35<=y<235:
                by = y-35
                byte = bitmap[(by//8)*320+(x//8)*8+by%8]
                color = 1 if byte & (128>>(x%8)) else 6
            elif y>=235:
                color = 0 if idle & (128>>(x%8)) else 14
                if 240<=y<261:
                    sprite,local = divmod(x,48)
                    symbol = local//4
                    byte = masks[phase*512+sprite*64+(y-240)*3+symbol//4]
                    value = (byte>>(6-2*(symbol%4))) & 3
                    if value:
                        color = 0 if value==1 else 14
            pixels[y*384+32+x] = palette[color]
    image = Image.new("RGB",(384,272))
    image.putdata(pixels)
    return image


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT / "verification.json").unlink(missing_ok=True)
    common = module("native_common",ROOT / "verify.py")
    schema = module("vic_snapshot",ROOT / "research/quondam/snapshot_state.py")
    labels = common.read_labels(HERE / "build/main.sym")
    program = HERE / "build/example.prg"
    data = program.read_bytes()
    bitmap = (HERE / "build/bitmap.bin").read_bytes()
    masks = (HERE / "build/masks.bin").read_bytes()
    assert len(bitmap)==8000 and len(masks)==16*512
    palette_path = ROOT / "palettes/colodore.vpl"
    palette = [tuple(int(v,16) for v in line.split()[:3])
               for line in palette_path.read_text().splitlines()
               if line.strip() and not line.startswith("#")]
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1",0))
        port = reserve.getsockname()[1]
    command = common.vice_command(shutil.which("x64sc"),program,port,palette_path)
    command += ["-limitcycles","12000000"]
    process,monitor,fields,pictures,controls = None,None,[],[],[]
    try:
        with (OUT / "vice.log").open("w") as log:
            process = subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            with common.connect_monitor(process,port) as connection:
                monitor = common.Monitor(connection)
                monitor.run("r")
                monitor.run(f"break {labels['frameComplete']:04x}")
                monitor.run("x")
                # The first lower-border opening primes the vertical latch.
                monitor.run("x")
                def capture(name,idle=None):
                    pc,line,clock = monitor.registers()
                    assert pc==labels["frameComplete"] and line==290
                    monitor.run("bank ram")
                    memory = monitor.memory(OUT / f"{name}.ram",0,65535)
                    phase = memory[labels["phase"]]
                    assert memory[0x4000:0x5f40] == bitmap
                    assert memory[0x6400:0x6600] == masks[phase*512:(phase+1)*512]
                    assert memory[0x6000:0x63e8] == bytes([0x16])*1000
                    assert memory[0x63f8:0x6400] == bytes(range(0x90,0x98))
                    assert memory[0x7fff]==0
                    screenshot = OUT / f"{name}.png"
                    monitor.run(f'screenshot "{screenshot}" 2')
                    image = Image.open(screenshot).convert("RGB")
                    expected = expected_image(bitmap,masks,phase,palette,idle)
                    diff = ImageChops.difference(image,expected)
                    if diff.getbbox():
                        expected.save(OUT / "expected-failed.png")
                        diff.save(OUT / "difference-failed.png")
                        raise AssertionError((name,phase,diff.getbbox()))
                    return image,{"phase":phase,"clock":clock,"native_pixels":384*272}
                for index in range(17):
                    image,record = capture(f"field-{index:03d}")
                    assert record["phase"]==(index+1)%16
                    fields.append(record)
                    pictures.append(image)
                    if index<16:
                        monitor.run("x")
                # Change only an unused-bank byte: the complete next image stays
                # normal. Then change the selected ordinary pattern input while
                # leaving that unused-bank byte nonzero: fine idle detail vanishes.
                monitor.run("bank cpu")
                monitor.run("> 3fff ff")
                monitor.run("x")
                image,record = capture("wrong-bank-byte-control")
                controls.append({"kind":"unused_$3fff_changed","pixels":record["native_pixels"],"image_unchanged":True})
                next_phase=(record["phase"]+1)%16
                monitor.run(f"> {labels['idlePatterns']+next_phase%8:04x} 00")
                monitor.run("x")
                image,record = capture("active-pattern-zero-control",0)
                original = expected_image(bitmap,masks,record["phase"],palette)
                changed = sum(a!=b for a,b in zip(image.get_flattened_data(),original.get_flattened_data()))
                assert changed>500
                controls.append({"kind":"active_pattern_zero","changed_native_pixels":changed,"unused_$3fff":255})
                # Stop after the real character-mode restoration, while the
                # banked idle byte is live and sprites are fetching the mask.
                monitor.run("delete")
                load=int.from_bytes(data[:2],"little")
                restore = data.index(bytes.fromhex("a9 1b 8d 11 d0"))-2+load+5
                monitor.run(f"break {restore:04x}")
                monitor.run("x")
                path=OUT / "banked-idle.vsf"
                monitor.run(f'dump "{path}"')
                state=schema.read_snapshot(path)
                vic=state["vicii"]
                assert vic["idle_state"]==1 and vic["vcbase"]==1000 and vic["rc"]==7
                assert vic["vbuf"]==[0x16]*40 and vic["cbuf"]==[0]*40
                assert vic["regs"][0x18]&0xfe==0x80 and vic["sprite_dma"]==255
                monitor.run("bank ram")
                memory=monitor.memory(OUT / "banked-idle.ram",0,65535)
                assert memory[0x7fff]==PATTERNS[memory[labels["phase"]]%8]
                connection.sendall(b"quit\n")
                process.wait(timeout=5)
        common.save_animation(pictures,OUT / "banked-ghost-scene.gif",80)
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
    assert all(abs(n-19656)<10 for n in intervals)
    proof={"passed":True,"program_sha256":hashlib.sha256(data).hexdigest(),"fields":fields,
           "native_pixels":len(fields)*384*272,"controls":controls,"field_intervals":intervals,
           "banked_idle_state":{k:vic[k] for k in ("raster_line","raster_cycle","rc","vcbase","idle_state","sprite_dma")},
           "vice_exit_code":process.returncode,
           "scope":"Own bank-$4000 scene using the documented first-scene anchors; no original scene or timing match"}
    (OUT / "verification.json").write_text(json.dumps(proof,indent=2)+"\n")
    print(json.dumps({"passed":True,"fields":len(fields),"native_pixels":proof["native_pixels"],
                      "controls":controls,"sha256":proof["program_sha256"]}))


if __name__=="__main__":
    main()
