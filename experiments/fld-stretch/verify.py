#!/usr/bin/env python3
"""Verify real FLD idle gaps, all eight bitmap source rows and native pixels."""
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
HEIGHTS = tuple(range(8,17)) + tuple(range(15,8,-1))
SELECTORS = (0xf3,0xfb,0xf2,0xfa,0xf1,0xf9,0xf0,0xf8)
EVENT = re.compile(r"#\d+ \(Trace store ([0-9a-fA-F]{4})\)\s+(\d+)/[^\n]*?,\s+(\d+)/[^\n]*\n"
                   r"\.C:([0-9a-fA-F]{4})[^\n]*?- A:([0-9a-fA-F]{2}) X:([0-9a-fA-F]{2})[^\n]*?\s(\d+)\n")


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def image_reference(phase, source, palette):
    gap, height = phase % 8, HEIGHTS[phase]
    top = 107+gap-51
    pixels = []
    for y in range(200):
        for x in range(320):
            color = 0
            if top <= y < top+8*height:
                row = (y-top)//height
                color = 1 if source[row*40+x//8] & (128 >> (x%8)) else 6
            pixels.append(palette[color])
    image = Image.new("RGB", (320,200))
    image.putdata(pixels)
    return image


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "verification.json").unlink(missing_ok=True)
    common = module("native_common", ROOT / "verify.py")
    schema = module("vic_snapshot", ROOT / "research/quondam/snapshot_state.py")
    labels = common.read_labels(HERE / "build/main.sym")
    program = HERE / "build/example.prg"
    source = (HERE / "build/picture.bin").read_bytes()
    assert len(source) == 320 and len({source[i*40:(i+1)*40] for i in range(8)}) == 8
    palette_path = ROOT / "palettes/colodore.vpl"
    palette = [tuple(int(v,16) for v in line.split()[:3])
               for line in palette_path.read_text().splitlines()
               if line.strip() and not line.startswith("#")]
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1",0))
        port = reserve.getsockname()[1]
    command = common.vice_command(shutil.which("x64sc"),program,port,palette_path)
    command += ["-limitcycles","15000000"]
    process, monitor, fields, pictures, observations, timings = None, None, [], [], [], []
    try:
        with (OUT / "vice.log").open("w") as log:
            process = subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            with common.connect_monitor(process,port) as connection:
                monitor = common.Monitor(connection)
                monitor.run("r")
                monitor.run(f"break {labels['fieldComplete']:04x}")
                monitor.run("x")
                monitor.run("trace store d011")
                monitor.run("trace store dd00")
                monitor.run("trace store d018")
                for index in range(33):
                    pc,line,clock = monitor.registers()
                    assert pc == labels["fieldComplete"] and line == 246
                    monitor.run("bank ram")
                    memory = monitor.memory(OUT / f"field-{index:03d}.ram",0,65535)
                    phase = memory[labels["phase"]]
                    assert phase == index%16
                    assert memory[labels["height"]] == HEIGHTS[phase]
                    assert memory[labels["gap"]] == phase%8
                    for row in range(8):
                        assert memory[row*0x2000+0x8c0:row*0x2000+0xa00:8] == source[row*40:(row+1)*40]
                    for bank in range(4):
                        assert memory[bank*0x4000+0x3c00:bank*0x4000+0x3fe8] == bytes([0x16])*1000
                    for cell in range(128):
                        row = cell//HEIGHTS[phase]
                        expected_selector = SELECTORS[row] if row<8 else SELECTORS[0]
                        assert memory[labels["stretchCells"]+15*cell+7] == expected_selector
                    screenshot = OUT / f"field-{index:03d}.png"
                    monitor.run(f'screenshot "{screenshot}" 2')
                    image = Image.open(screenshot).convert("RGB").crop((32,35,352,235))
                    expected = image_reference(phase,source,palette)
                    difference = ImageChops.difference(image,expected)
                    if difference.getbbox():
                        expected.save(OUT / "expected-failed.png")
                        difference.save(OUT / "difference-failed.png")
                        raise AssertionError(f"Native image mismatch at phase {phase}: {difference.getbbox()}")
                    pictures.append(image)
                    fields.append({"index":index,"phase":phase,"clock":clock,"height":HEIGHTS[phase],
                                   "gap":phase%8,"native_pixels":64000,"source_rows":8})
                    if index<32:
                        response = monitor.run("x")
                        (OUT / f"field-{index+1:03d}-trace.txt").write_text(response)
                        events = [{"address":int(address,16),"raster":int(raster),"cycle":int(cycle),
                                   "pc":int(pc,16),"value":int(a,16),"x":int(x,16),"clock":int(clock)}
                                  for address,raster,cycle,pc,a,x,clock in EVENT.findall(response)]
                        next_phase = (phase+1)%16
                        cell_events = [e for e in events if labels["stretchCells"] <= e["pc"] < labels["stretchCells"]+128*15]
                        assert len(cell_events) == 384
                        write_cycle = cell_events[0]["cycle"]
                        assert write_cycle in (58,59)
                        timings.append({"phase":next_phase,"d011_cycle":write_cycle,
                                        "cia2_cycle":(write_cycle+6)%63,"d018_cycle":(write_cycle+10)%63})
                        for cell in range(128):
                            row = cell//HEIGHTS[next_phase]
                            values = cell_events[3*cell:3*cell+3]
                            raster = 106+next_phase%8+cell
                            mode = (0x30 if row<8 else 0x70) | ((raster+1)&7)
                            selector = SELECTORS[row] if row<8 else SELECTORS[0]
                            expected_events = [(0xd011,mode,raster,write_cycle),
                                (0xdd00,selector,raster+1,(write_cycle+6)%63),
                                (0xd018,selector,raster+1,(write_cycle+10)%63)]
                            assert [(e["address"],e["value"],e["raster"],e["cycle"]) for e in values] == expected_events, (next_phase,cell,values)
                            assert values[0]["clock"]-cell_events[0]["clock"] == cell*63
                # Obtain actual RC/cache states during the graphics fetch phase.
                monitor.run("delete")
                def stop(address):
                    monitor.run("delete")
                    monitor.run(f"break {address:04x}")
                    monitor.run("x")
                def snapshot(name):
                    path = OUT / f"{name}.vsf"
                    monitor.run(f'dump "{path}"')
                    return schema.read_snapshot(path)
                stop(labels["fieldComplete"])
                monitor.run("bank ram")
                memory = monitor.memory(OUT / "witness-start.ram",0,65535)
                next_phase = (memory[labels["phase"]]+1)%16
                height = HEIGHTS[next_phase]
                for row in range(8):
                    cell = 1+row*height
                    stop(labels["stretchCells"]+cell*15+3)
                    vic = snapshot(f"source-row-{row}")["vicii"]
                    assert vic["raster_line"] == 107+next_phase%8+row*height
                    assert vic["raster_cycle"] in (54,55)
                    assert (vic["rc"],vic["vcbase"],vic["vc"]) == (0,280,320)
                    assert vic["vbuf"] == [0x16]*40
                    observations.append({"source_row":row,**{k:vic[k] for k in ("raster_line","raster_cycle","rc","vcbase","vc")}})
                # Phase3 has three true FLD idle lines, rather than RC0 repeats.
                stop(labels["fieldComplete"])
                monitor.run("bank ram")
                memory = monitor.memory(OUT / "gap-start.ram",0,65535)
                phase = (memory[labels["phase"]]+1)%16
                while phase%8 < 2:
                    stop(labels["fieldComplete"])
                    phase = (phase+1)%16
                offset = (7-phase%8)*13
                stop(labels["skipCells"]+offset+13+6)
                vic = snapshot("fld-idle-gap")["vicii"]
                assert (vic["rc"],vic["vcbase"],vic["idle_state"],vic["bad_line"]) == (7,280,1,0)
                observations.append({"kind":"fld_idle",**{k:vic[k] for k in ("raster_line","raster_cycle","rc","vcbase","idle_state","bad_line")}})
                connection.sendall(b"quit\n")
                process.wait(timeout=5)
        common.save_animation(pictures,OUT / "fld-stretch.gif",80)
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
    assert process.returncode == 0
    intervals = [b["clock"]-a["clock"] for a,b in zip(fields,fields[1:])]
    assert all(abs(n-19656)<8 for n in intervals)
    proof = {"passed":True,"program_sha256":hashlib.sha256(program.read_bytes()).hexdigest(),
             "fields":fields,"native_pixels":len(fields)*64000,"cell_stores":32*384,
             "publication_intervals":intervals,"hardware_observations":observations,"vice_exit_code":process.returncode}
    proof["cell_timing"] = timings
    (OUT / "verification.json").write_text(json.dumps(proof,indent=2)+"\n")
    print(json.dumps({"passed":True,"fields":len(fields),"native_pixels":proof["native_pixels"],
                      "cell_stores":proof["cell_stores"],"sha256":proof["program_sha256"]}))


if __name__ == "__main__":
    main()
